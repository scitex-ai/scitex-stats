#!/usr/bin/env bash
# Runs INSIDE the reused scitex-ci SIF (apptainer exec — invoked via
# exec-in-sif.sh). Builds scitex-stats's wheel + sdist into ./dist/.
#
# WHY build in the SIF: the self-hosted Spartan runner has no Python on the
# bare node (the whole reason the old `actions/setup-python@v5` step failed:
# "version 3.x not found for this OS"). The SIF bakes python 3.11/3.12/3.13 +
# pip + uv at /opt/venv-<ver>, exactly like the working pytest-matrix CI.
#
# Install the build frontend on owned writable scratch and use normal UV
# dependency resolution. The caller supplies its independently resolved source
# and version; archive metadata must never supply the expected identity.
# This application grants no build admission, transfer or publishing authority.
#
# Fail-loud (operator directive): a missing interpreter or a failed build is a
# HARD error, never a silent fallback.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/release-context.sh"
stats_release_require_owned_root

V="${1:?baked Python version required}"
EXPECTED_COMMIT="${2:?preflight-resolved source commit required}"
EXPECTED_VERSION="${3:?preflight-resolved release version required}"
[[ "$#" == 3 ]] || { echo "::error::expected Python, source and version" >&2; exit 1; }
HELPERS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="/opt/venv-$V"
PY="$VENV/bin/python"
test -x "$PY" || {
    echo "::error::baked python missing in $VENV — rebuild the SIF: scitex-container apptainer build ci-cpu"
    exit 1
}

# Refuse mismatched identity before installer/network access or dist deletion.
"$PY" -I "$HELPERS/release-identity.py" verify-source \
    --commit "$EXPECTED_COMMIT" --version "$EXPECTED_VERSION"

export LC_ALL=C.UTF-8 LANG=C.UTF-8

# Writable scratch (the runner's TMPDIR=~/.cache/tmp is a host path that does
# NOT resolve inside the container). Node-local /tmp is writable + ephemeral.
TMPDIR="/tmp/build-scitex_stats-${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-0}-$V"
export TMPDIR
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR/site" "$TMPDIR/uv-cache"

# Keep installer caches below the dispatcher-owned temporary root.
export UV_CACHE_DIR="$TMPDIR/uv-cache"
export XDG_CACHE_HOME="$TMPDIR"
export PIP_CACHE_DIR="$TMPDIR/pip-cache"

# A VIRTUAL_ENV leaked from the runner profile (~/.env-3.11) is a broken
# symlink in here; unset it so no tool follows it.
unset VIRTUAL_ENV || true

export PATH="$VENV/bin:$PATH"
echo "build: py=$("$PY" -V) target=$TMPDIR/site"

# Install the PEP 517 build frontend into the writable target with uv,
# then build with its uv installer. A failed installation stops the job. Clean dist/ first so only the freshly
# built artifacts are uploaded.
uv pip install --python "$PY" --target="$TMPDIR/site" build

export PYTHONPATH="$TMPDIR/site${PYTHONPATH:+:$PYTHONPATH}"

rm -rf dist
"$PY" -m build --installer uv --outdir dist

echo "=== built artifacts ==="
ls -l dist
# fail-loud: refuse to continue the pipeline with an empty dist/.
test -n "$(ls -A dist 2>/dev/null)" || {
    echo "::error::python -m build produced no artifacts in dist/"
    exit 1
}

# Keep transfer outside this application. A failed archive or installed-surface
# check propagates to the dispatcher; success requires both independent proofs.
"$PY" -I "$HELPERS/release-identity.py" write-proof \
    --commit "$EXPECTED_COMMIT" --version "$EXPECTED_VERSION" --dist dist
"$PY" -I "$HELPERS/probe-wheel.py" --dist dist \
    --expected-version "$EXPECTED_VERSION"
"$PY" -I "$HELPERS/release-identity.py" verify-proof \
    --commit "$EXPECTED_COMMIT" --version "$EXPECTED_VERSION" --dist dist

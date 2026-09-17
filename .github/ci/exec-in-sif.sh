#!/usr/bin/env bash
# Outer apptainer-exec wrapper for scitex-tex's self-hosted (Spartan) CI.
#
# Runs ON THE RUNNER (outside the SIF). Resolves the apptainer shim + SIF image
# from the repo Actions Variables, then `apptainer exec`s the SIF and hands off
# to an INNER script (run inside the container). Keeps every workflow job's YAML
# down to one line — `bash .github/ci/exec-in-sif.sh <inner-script> [args...]` —
# and concentrates all the HPC/SIF plumbing (shim PATH, ~-expansion, scratch,
# binds) in one version-controlled place.
#
# Required env (set by the workflow from repo Actions Variables):
#   SCITEX_CI_APPTAINER   path to the apptainer shim   (e.g. ~/.env-3.11/bin/apptainer)
#   SCITEX_CI_SIF         path to the CI SIF image     (e.g. ~/.scitex/dev/containers/ci-cpu.sif)
#
# Usage:
#   bash .github/ci/exec-in-sif.sh run-in-sif.sh 3.12
#
# Fail-loud (operator directive): a missing shim or SIF is a HARD error — never
# a silent fallback to a bare-runner install.
set -euo pipefail

INNER="${1:?inner script name required (relative to .github/ci/)}"
shift || true

# The runner's job shell is --noprofile --norc (no Lmod), so the apptainer shim
# must be put on PATH explicitly; it execs the real Apptainer binary directly.
# ~-expand the Actions-Variable paths: a quoted "~/…" is NOT tilde-expanded by
# the shell, so substitute a leading ~ with $HOME ourselves.
APPTAINER="${SCITEX_CI_APPTAINER:?SCITEX_CI_APPTAINER not set (repo Actions Variable)}"
SIF="${SCITEX_CI_SIF:?SCITEX_CI_SIF not set (repo Actions Variable)}"
APPTAINER="${APPTAINER/#\~/$HOME}"
SIF="${SIF/#\~/$HOME}"
export PATH="$HOME/.env-3.11/bin:$PATH"

[ -x "$APPTAINER" ] || {
    echo "::error::apptainer shim not executable at $APPTAINER"
    exit 1
}
[ -f "$SIF" ] || {
    echo "::error::CI SIF missing at $SIF — rebuild it: scitex-container apptainer build ci-cpu"
    exit 1
}

# apptainer scratch: NODE-LOCAL, derived from the runner's own scratch.
# The previous hardcoded /data/gpfs/projects/punim0264/... exists only on the
# Spartan nodes; on any other runner `mkdir -p` dies with "Permission denied"
# and, because this line runs before anything else, it took the whole build
# stage down AFTER every test leg had passed (measured 2026-09-17 on
# actions-runner-org-04: three green test legs, build dead at
# `mkdir: cannot create directory '/data': Permission denied`).
# RUNNER_TEMP is the runner's own scratch dir (GitHub sets it on both hosted
# and self-hosted runners); /tmp is the fallback for a bare shell run.
export APPTAINER_TMPDIR="${RUNNER_TEMP:-/tmp}/apptainer-tmp-$$"
mkdir -p "$APPTAINER_TMPDIR" || {
    echo "::error::cannot create apptainer scratch at $APPTAINER_TMPDIR"
    exit 1
}

# --bind punim0264 ONLY where it exists: $HOME/.scitex is a symlink into
# punim0264 on the Spartan nodes, so the bind is what makes it resolve inside
# the container. On a node without that tree there is no symlink to resolve and
# binding a non-existent path is at best noise, at worst a hard failure.
BIND_ARGS=()
if [ -d /data/gpfs/projects/punim0264 ]; then
    BIND_ARGS=(--bind /data/gpfs/projects/punim0264)
fi

# --pwd "$PWD" keeps the checkout as cwd.
exec "$APPTAINER" exec --pwd "$PWD" "${BIND_ARGS[@]+"${BIND_ARGS[@]}"}" \
    "$SIF" bash ".github/ci/$INNER" "$@"

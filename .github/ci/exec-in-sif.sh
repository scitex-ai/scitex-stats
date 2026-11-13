#!/usr/bin/env bash
# Execute a retained Stats CI script only with the configured runtime/image bytes.
# The expected digests come from reviewed runtime admission, not a live-file
# checksum used to bless an unknown runtime. These checks grant no admission.
set -euo pipefail

INNER="${1:?inner script name required (relative to .github/ci/)}"
shift
[[ "$INNER" =~ ^[a-z][a-z0-9._-]*[.]sh$ ]] && [ -f ".github/ci/$INNER" ] || {
    echo "::error::inner script must be an existing .github/ci/ shell basename" >&2
    exit 1
}

APPTAINER="${SCITEX_CI_APPTAINER:?SCITEX_CI_APPTAINER must name the reviewed runtime}"
SIF="${SCITEX_CI_SIF:?SCITEX_CI_SIF must name the reviewed image}"
RUNTIME_SHA256="${SCITEX_CI_APPTAINER_SHA256:?SCITEX_CI_APPTAINER_SHA256 is required}"
SIF_SHA256="${SCITEX_CI_SIF_SHA256:?SCITEX_CI_SIF_SHA256 is required}"
case "$APPTAINER" in "~/"*) APPTAINER="$HOME/${APPTAINER:2}" ;; esac
case "$SIF" in "~/"*) SIF="$HOME/${SIF:2}" ;; esac
[[ "$APPTAINER" == /* && "$SIF" == /* ]] || {
    echo "::error::configured runtime and image paths must be absolute" >&2
    exit 1
}
[[ "$RUNTIME_SHA256" =~ ^[a-f0-9]{64}$ && "$SIF_SHA256" =~ ^[a-f0-9]{64}$ ]] || {
    echo "::error::runtime and image digests must be lowercase SHA-256 values" >&2
    exit 1
}
[ -f "$APPTAINER" ] && [ -x "$APPTAINER" ] || {
    echo "::error::configured runtime is not executable: $APPTAINER" >&2
    exit 1
}
[ -f "$SIF" ] || {
    echo "::error::configured image is missing: $SIF" >&2
    exit 1
}
ACTUAL_RUNTIME_SHA256="$(sha256sum "$APPTAINER" | awk '{print $1}')"
[ "$ACTUAL_RUNTIME_SHA256" = "$RUNTIME_SHA256" ] || {
    echo "::error::configured runtime digest mismatch" >&2
    exit 1
}
ACTUAL_SIF_SHA256="$(sha256sum "$SIF" | awk '{print $1}')"
[ "$ACTUAL_SIF_SHA256" = "$SIF_SHA256" ] || {
    echo "::error::configured image digest mismatch" >&2
    exit 1
}

# Retain the existing scratch and optional GPFS bindings. Private job state,
# capacity and runner/image admission remain separate caller responsibilities.
export APPTAINER_TMPDIR="${RUNNER_TEMP:-/tmp}/apptainer-tmp-$$"
mkdir -p "$APPTAINER_TMPDIR"
BIND_ARGS=()
if [ -d /data/gpfs/projects/punim0264 ]; then
    BIND_ARGS=(--bind /data/gpfs/projects/punim0264)
fi
echo "exec-in-sif: configured runtime and image SHA-256 verified"
exec "$APPTAINER" exec --pwd "$PWD" "${BIND_ARGS[@]+"${BIND_ARGS[@]}"}" \
    "$SIF" bash ".github/ci/$INNER" "$@"

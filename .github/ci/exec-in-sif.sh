#!/usr/bin/env bash
# Execute a retained Stats CI script only with the configured runtime/image bytes.
# The expected digests come from reviewed runtime admission, not a live-file
# checksum used to bless an unknown runtime. These checks grant no admission.
set -euo pipefail

INNER="${1:?inner script name required (relative to .github/ci/)}"
shift
INNER_ARGS=("$@")
[[ "$INNER" =~ ^[a-z][a-z0-9._-]*[.]sh$ ]] && [ -f ".github/ci/$INNER" ] || {
    echo "::error::inner script must be an existing .github/ci/ shell basename" >&2
    exit 1
}

case "$INNER" in
    run-in-sif.sh|build-in-sif.sh|probe-wheel-in-sif.sh) ;;
    *) echo "::error::only non-publishing test/build/probe applications are supported" >&2; exit 1 ;;
esac

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

# The caller stages this exact shared resource from scitex-dev@41b907f7.
# Its fixed digest binds the consumer to the qualified generic lifecycle.
RESOURCE="${SCITEX_CI_OWNED_CONTEXT:?SCITEX_CI_OWNED_CONTEXT must name the staged shared resource}"
[[ "$RESOURCE" == /* && ! -L "$RESOURCE" && -f "$RESOURCE" ]] || {
    echo "::error::shared owned context must be an absolute regular non-symlink file" >&2
    exit 1
}
RESOURCE_SUM="$(/usr/bin/sha256sum -- "$RESOURCE")"
[[ "${RESOURCE_SUM%% *}" == a795678455d409e076a1c93a4a810b50c89499fcb83ae4c90a8d31a19e90e5d1 ]] || {
    echo "::error::shared owned context digest mismatch" >&2
    exit 1
}
source "$RESOURCE"
owned_context_init "${RUNNER_TEMP:-/tmp}" scitex-stats-release-
for binding in "$OWNED_TMPDIR" "$PWD"; do
case "$binding" in
    *:*|*,*|*$'\n'*) echo "::error::owned path cannot contain container bind separators" >&2; exit 1 ;;
esac
done
echo "exec-in-sif: owned_root=$OWNED_TMPDIR" >&2
BIND_ARGS=()
if [ -d /data/gpfs/projects/punim0264 ]; then
    BIND_ARGS=(--bind /data/gpfs/projects/punim0264)
fi

driver_body() {
    local home="$OWNED_TMPDIR/home" temporary="$OWNED_TMPDIR/container"
    local work="$OWNED_TMPDIR/apptainer" cache="$OWNED_TMPDIR/apptainer-cache" identity=''
    /usr/bin/mkdir -m 700 -- "$home" "$temporary" "$work" "$cache"
    identity="$(/usr/bin/stat -c '%d:%i:%u:%a' -- "$temporary")"
    /usr/bin/env -i HOME="$home" PATH=/usr/local/bin:/usr/bin:/bin \
        USER="$(id -un)" LOGNAME="$(id -un)" LANG=C.UTF-8 LC_ALL=C.UTF-8 \
        TMPDIR="$work" APPTAINER_TMPDIR="$work" APPTAINER_CACHEDIR="$cache" \
        "$APPTAINER" exec --cleanenv --home "$home:/home/scitex-release" \
        --pwd "$PWD" --bind "$temporary:/tmp" --bind "$temporary:/var/tmp" \
        --bind "$PWD:$PWD" "${BIND_ARGS[@]+"${BIND_ARGS[@]}"}" \
        --env "TMPDIR=/tmp,SCITEX_STATS_JOB_ROOT_ID=$identity" \
        "$SIF" bash ".github/ci/run-owned-in-sif.sh" "$INNER" "${INNER_ARGS[@]}"
}
echo "exec-in-sif: runtime, image and shared lifecycle SHA-256 verified"
run_owned_body

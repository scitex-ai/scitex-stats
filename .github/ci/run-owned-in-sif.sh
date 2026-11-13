#!/usr/bin/env bash
# Runs inside the pinned image after the outer wrapper binds owned scratch.
set -euo pipefail
INNER="${1:?non-publishing inner driver required}"
shift
case "$INNER" in
    run-in-sif.sh|build-in-sif.sh|probe-wheel-in-sif.sh) ;;
    *) echo "::error::unsupported non-publishing application" >&2; exit 1 ;;
esac
source "$(dirname "${BASH_SOURCE[0]}")/release-context.sh"
stats_release_require_owned_root
EXPECTED="$SCITEX_STATS_JOB_ROOT_ID"
V="${1:-3.12}"
[[ "$V" =~ ^3[.](11|12|13)$ ]] || { echo "::error::unqualified Python version" >&2; exit 1; }
stats_release_context /tmp "/opt/venv-$V"
STATS_RELEASE_ENV+=("SCITEX_STATS_JOB_ROOT_ID=$EXPECTED")
stats_release_run bash "$(dirname "${BASH_SOURCE[0]}")/$INNER" "$@"

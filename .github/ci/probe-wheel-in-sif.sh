#!/usr/bin/env bash
# Run inside the retained CI SIF; never use a bare-runner interpreter.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/release-context.sh"
stats_release_require_owned_root
V="${1:?baked Python version required}"
shift
PY="/opt/venv-$V/bin/python"
test -x "$PY" || {
    echo "::error::baked Python missing at $PY" >&2
    exit 1
}
export TMPDIR=/tmp
exec "$PY" -I "$(dirname "$0")/probe-wheel.py" "$@"

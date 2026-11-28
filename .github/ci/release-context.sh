#!/usr/bin/env bash
# Stats release-state policy. The caller owns root lifecycle and admission.
# Source in a dedicated strict Bash shell before invoking release applications.
[[ "${BASH_SOURCE[0]}" != "$0" ]] || { echo "::error::source this CI resource" >&2; exit 1; }
STATS_RELEASE_ENV=()
STATS_RELEASE_READY=0

stats_release_context() {
    local scratch="${1:-}" venv="${2:-}" identity='' state='' refused='' encoded=''
    [[ "$STATS_RELEASE_READY" == 0 && "$scratch" == /* && "$venv" == /* ]] || return 1
    [[ ! -L "$scratch" && -d "$scratch" && -w "$scratch" && -x "$venv/bin/python" ]] || return 1
    identity="$(stat -c '%u:%a' -- "$scratch")" || return 1
    [[ "$identity" == "$(id -u):700" ]] || return 1
    state="$scratch/stats-state"
    # Exclusive creation refuses a pre-existing or symlinked state tree.
    mkdir -m 700 -- "$state" || return 1
    mkdir -m 700 -- "$state/home" "$state/scitex" "$state/cache" \
        "$state/xdg-data" "$state/xdg-config" "$state/runtime" \
        "$state/pip-cache" "$state/uv-cache" "$state/mpl" || return 1
    refused="$state/refused-postgres"
    encoded="$(/usr/bin/env -i "$venv/bin/python" -I -S -c \
        'import sys; from urllib.parse import quote; print(quote(sys.argv[1], safe=""))' \
        "$refused")" || return 1
    STATS_RELEASE_ENV=(
        "PATH=$venv/bin:/usr/local/bin:/usr/bin:/bin"
        "LANG=C.UTF-8" "LC_ALL=C.UTF-8"
        "HOME=$state/home" "TMPDIR=$scratch"
        "SCITEX_DIR=$state/scitex" "SCITEX_LOGGING_FORMAT=default"
        "SCITEX_TESTMON_CACHE_ROOT=$state/cache/testmon"
        "XDG_CACHE_HOME=$state/cache" "XDG_DATA_HOME=$state/xdg-data"
        "XDG_CONFIG_HOME=$state/xdg-config" "XDG_RUNTIME_DIR=$state/runtime"
        "UV_CACHE_DIR=$state/uv-cache" "UV_NO_CONFIG=1"
        "PIP_CACHE_DIR=$state/pip-cache" "PIP_CONFIG_FILE=/dev/null"
        "PYTHONNOUSERSITE=1" "PYTHONDONTWRITEBYTECODE=1"
        "GIT_CONFIG_GLOBAL=/dev/null" "GIT_CONFIG_NOSYSTEM=1"
        "MPLBACKEND=Agg" "MPLCONFIGDIR=$state/mpl"
        "PGHOST=$refused" "PGPORT=1"
        "PGUSER=release-refused" "PGDATABASE=release-refused"
        "SCITEX_STORE_DSN=postgresql://release-refused@/release-refused?host=$encoded&port=1&connect_timeout=1"
    )
    STATS_RELEASE_READY=1
}

stats_release_run() {
    [[ "$STATS_RELEASE_READY" == 1 && "${#STATS_RELEASE_ENV[@]}" -gt 0 ]] || {
        echo "::error::Stats release context was not initialized" >&2
        return 1
    }
    /usr/bin/env -i "${STATS_RELEASE_ENV[@]}" "$@"
}

# Shared by the dispatcher and every retained inner application. A normal host
# /tmp is not an acceptable release root, even when its identity is supplied.
stats_release_require_owned_root() {
    local expected="${SCITEX_STATS_JOB_ROOT_ID:-}" actual=''
    [[ "$expected" =~ ^[0-9]+:[0-9]+:[0-9]+:700$ ]] || {
        echo "::error::outer owned scratch identity required" >&2
        return 1
    }
    actual="$(/usr/bin/stat -c '%d:%i:%u:%a' -- /tmp)" || return 1
    [[ ! -L /tmp && "$actual" == "$expected" && "${actual##*:}" == 700 &&
       "$(/usr/bin/stat -c '%u' -- /tmp)" == "$(id -u)" ]] || {
        echo "::error::container temporary root identity mismatch (expected=$expected actual=$actual)" >&2
        return 1
    }
}

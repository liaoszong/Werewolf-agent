#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release}"
WORK_DIR="${WORK_DIR:-$REPO_ROOT/.tmp/pyinstaller-build}"
SPEC_FILE="$REPO_ROOT/scripts/release/werewolf-agent.spec"
PYINSTALLER_EXE="${PYINSTALLER_EXE:-$VENV_DIR/Scripts/pyinstaller.exe}"

to_windows_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$1"
    elif [[ "$1" =~ ^/mnt/([a-zA-Z])/(.*)$ ]]; then
        local drive="${BASH_REMATCH[1]}"
        local rest="${BASH_REMATCH[2]//\//\\}"
        printf '%s:\\%s\n' "$(printf '%s' "$drive" | tr '[:lower:]' '[:upper:]')" "$rest"
    else
        printf '%s\n' "$1"
    fi
}

echo "=== Building Werewolf-agent bootstrapper ==="
cd "$REPO_ROOT"
"$PYINSTALLER_EXE" -y \
    --distpath "$(to_windows_path "$OUTPUT_DIR")" \
    --workpath "$(to_windows_path "$WORK_DIR")" \
    "$(to_windows_path "$SPEC_FILE")"

cp "$REPO_ROOT/VERSION" "$OUTPUT_DIR/Werewolf-agent/VERSION"
echo "=== Bootstrapper at $OUTPUT_DIR/Werewolf-agent/ ==="

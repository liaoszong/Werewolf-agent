#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release/runtime}"
SPEC_FILE="$REPO_ROOT/scripts/release/observer-server.spec"

source "$VENV_DIR/Scripts/activate"

echo "=== Building frozen observer server ==="
cd "$REPO_ROOT"
pyinstaller --distpath "$OUTPUT_DIR" --workpath "$REPO_ROOT/.tmp/pyi-server-build" "$SPEC_FILE"

# Copy VERSION alongside the executable (PyInstaller COLLECT puts data files in _internal/)
cp "$REPO_ROOT/VERSION" "$OUTPUT_DIR/observer-server/VERSION"

echo "=== Frozen server at $OUTPUT_DIR/observer-server/ ==="
ls -la "$OUTPUT_DIR/observer-server/"

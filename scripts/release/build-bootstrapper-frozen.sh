#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release}"
SPEC_FILE="$REPO_ROOT/scripts/release/werewolf-agent.spec"

source "$VENV_DIR/Scripts/activate"

echo "=== Building frozen bootstrapper ==="
cd "$REPO_ROOT"
pyinstaller --distpath "$OUTPUT_DIR" --workpath "$REPO_ROOT/.tmp/pyi-bootstrapper-build" "$SPEC_FILE"

echo "=== Copying VERSION to dist root (PyInstaller onedir places it in _internal/) ==="
cp "$REPO_ROOT/VERSION" "$OUTPUT_DIR/Werewolf-agent/VERSION"

echo "=== Bootstrapper at $OUTPUT_DIR/Werewolf-agent/ ==="
ls -la "$OUTPUT_DIR/Werewolf-agent/"

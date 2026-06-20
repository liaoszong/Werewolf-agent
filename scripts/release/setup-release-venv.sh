#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv-release"

echo "=== Creating release venv ==="
python -m venv "$VENV_DIR"

source "$VENV_DIR/Scripts/activate"
pip install --upgrade pip
pip install pyinstaller

echo "=== Release venv ready at $VENV_DIR ==="
echo "PyInstaller version: $(pyinstaller --version)"

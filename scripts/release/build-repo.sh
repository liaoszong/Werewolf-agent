#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG_DIR="$REPO_ROOT/.tmp/ifw-package"
REPO_DIR="$REPO_ROOT/.tmp/ifw-repo/stable"
IFW_BIN="F:/Qt/Tools/QtInstallerFramework/4.11/bin"

echo "=== Building online repository ==="
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"

"$IFW_BIN/repogen.exe" \
    -p "$PKG_DIR" \
    "$REPO_DIR"

echo "=== Repository at $REPO_DIR ==="
ls -la "$REPO_DIR"

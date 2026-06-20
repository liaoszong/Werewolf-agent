#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG_DIR="$REPO_ROOT/.tmp/ifw-package"
CONFIG_DIR="$REPO_ROOT/.tmp/ifw-config"
IFW_BIN="F:/Qt/Tools/QtInstallerFramework/4.11/bin"

IFW_VERSION="${IFW_VERSION:-0.2.0}"
REPOSITORY_URL="${REPOSITORY_URL:-file:///$REPO_ROOT/.tmp/ifw-repo/stable}"
RELEASE_DATE="${RELEASE_DATE:-$(date +%Y-%m-%d)}"

# Prepare config
mkdir -p "$CONFIG_DIR"
cat "$REPO_ROOT/scripts/release/ifw/config/config.xml.in" \
    | sed "s/\${IFW_VERSION}/$IFW_VERSION/g" \
    | sed "s|\${REPOSITORY_URL}|$REPOSITORY_URL|g" \
    > "$CONFIG_DIR/config.xml"

echo "=== Building installer ==="
"$IFW_BIN/binarycreator.exe" \
    -c "$CONFIG_DIR/config.xml" \
    -p "$PKG_DIR" \
    "$REPO_ROOT/.tmp/release/Werewolf-agent-${IFW_VERSION}-installer.exe"

echo "=== Installer: .tmp/release/Werewolf-agent-${IFW_VERSION}-installer.exe ==="

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RELEASE_DIR="$REPO_ROOT/.tmp/release"
PKG_DIR="$REPO_ROOT/.tmp/ifw-package/com.werewolfagent.app"
META_DIR="$PKG_DIR/meta"
DATA_DIR="$PKG_DIR/data"

IFW_VERSION="${IFW_VERSION:-0.2.0}"
RELEASE_DATE="${RELEASE_DATE:-$(date +%Y-%m-%d)}"

echo "=== Assembling IFW package ==="
rm -rf "$PKG_DIR"
mkdir -p "$META_DIR" "$DATA_DIR"

# Copy payload
cp -r "$RELEASE_DIR/Werewolf-agent/Werewolf-agent.exe" "$DATA_DIR/"
cp "$RELEASE_DIR/Werewolf-agent/VERSION" "$DATA_DIR/"
cp -r "$RELEASE_DIR/Werewolf-agent/_internal" "$DATA_DIR/"
cp -r "$RELEASE_DIR/app" "$DATA_DIR/"
cp -r "$RELEASE_DIR/runtime/observer-server" "$DATA_DIR/runtime"

# Copy metadata (with variable substitution)
cat "$REPO_ROOT/scripts/release/ifw/packages/com.werewolfagent.app/meta/package.xml" \
    | sed "s/\${IFW_VERSION}/$IFW_VERSION/g" \
    | sed "s/\${RELEASE_DATE}/$RELEASE_DATE/g" \
    > "$META_DIR/package.xml"

cp "$REPO_ROOT/scripts/release/ifw/packages/com.werewolfagent.app/meta/installscript.qs" "$META_DIR/"
cp "$REPO_ROOT/scripts/release/ifw/packages/com.werewolfagent.app/meta/license.txt" "$META_DIR/"

echo "=== Package assembled at $PKG_DIR ==="

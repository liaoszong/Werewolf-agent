#!/usr/bin/env bash
# R0: Publish IFW repository contents to GitHub Pages
# Prerequisites:
#   - Build artifacts in .tmp/ifw-repo/ (from scripts/release/build-repo.sh)
#   - A separate GitHub repo (e.g. werewolf-agent-updates) configured for GitHub Pages
#   - SSH access to the update repo
#
# Usage:
#   UPDATE_REPO=git@github.com:USER/werewolf-agent-updates.git bash scripts/release/publish-to-github-pages.sh
#
# Environment variables:
#   UPDATE_REPO  - SSH URL of the GitHub Pages update repo
#                  (default: git@github.com:liaoszong/werewolf-agent-updates.git)
#   CHANNEL      - Update channel (default: stable)
#   IFW_VERSION  - IFW component version (default: 0.2.0)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO_DIR="$REPO_ROOT/.tmp/ifw-repo"
UPDATE_REPO="${UPDATE_REPO:-git@github.com:liaoszong/werewolf-agent-updates.git}"
CHANNEL="${CHANNEL:-stable}"
IFW_VERSION="${IFW_VERSION:-0.2.0}"

echo "=== Publishing to GitHub Pages ==="
echo "  Channel:      $CHANNEL"
echo "  IFW version:  $IFW_VERSION"
echo "  Update repo:  $UPDATE_REPO"

# ── Generate distribution manifest ──────────────────────────────
echo "--- Generating distribution-manifest.json ---"
GIT_COMMIT=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
BUILD_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

DIST_MANIFEST="$REPO_ROOT/.tmp/release/distribution-manifest.json"
cat > "$DIST_MANIFEST" << EOF
{
  "schema_version": 1,
  "release_version": "0.2.0",
  "channel": "${CHANNEL}",
  "git_commit": "${GIT_COMMIT}",
  "build_timestamp": "${BUILD_TS}",
  "ifw_component_version": "${IFW_VERSION}",
  "components": {
    "com.werewolfagent.app": "${IFW_VERSION}"
  }
}
EOF
echo "  Wrote $DIST_MANIFEST"

# ── Clone update repo ───────────────────────────────────────────
echo "--- Cloning update repo ---"
TMP_CLONE="$REPO_ROOT/.tmp/updates-clone"
rm -rf "$TMP_CLONE"
git clone "$UPDATE_REPO" "$TMP_CLONE"
echo "  Cloned into $TMP_CLONE"

# ── Copy repository contents ────────────────────────────────────
echo "--- Copying repository contents ---"
rm -rf "$TMP_CLONE/$CHANNEL"
cp -r "$REPO_DIR/$CHANNEL" "$TMP_CLONE/"
# Also copy distribution manifest
cp "$DIST_MANIFEST" "$TMP_CLONE/"
echo "  Copied $CHANNEL/ and distribution-manifest.json"

# ── Commit and push ─────────────────────────────────────────────
echo "--- Committing and pushing ---"
cd "$TMP_CLONE"

# Check if there are any changes before committing
if git diff --quiet && git diff --cached --quiet; then
    echo "  No changes to commit"
else
    git add "$CHANNEL/" distribution-manifest.json 2>/dev/null || git add "$CHANNEL/"
    git commit -m "Release v${IFW_VERSION} ${CHANNEL}"
    echo "  Pushing to origin main..."
    git push origin main
fi

# ── Output URL ──────────────────────────────────────────────────
echo ""
echo "=== Published to GitHub Pages ==="
echo "  Updates.xml: https://$(echo "$UPDATE_REPO" | sed 's|.*github.com[/:]||;s|\.git$||' | tr ':' '/')/werewolf-agent-updates/${CHANNEL}/Updates.xml"
echo "  (Assuming repo is published at https://USER.github.io/werewolf-agent-updates/)"

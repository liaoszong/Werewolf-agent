#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/velopack-release/Releases}"
REPO_URL="${REPO_URL:-https://github.com/liaoszong/Werewolf-agent}"
GH_REPO="${GH_REPO:-liaoszong/Werewolf-agent}"
VPK_EXE="${VPK_EXE:-vpk}"
TAG="${TAG:-v$(tr -d '\r\n' < "$REPO_ROOT/VERSION")}"
RELEASE_NAME="${RELEASE_NAME:-Werewolf-agent $TAG}"
PUBLISH="${PUBLISH:-false}"
NOTES_FILE="$REPO_ROOT/scripts/release/release-notes.md"

to_vpk_path() {
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

if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "Release output directory not found: $OUTPUT_DIR" >&2
    exit 1
fi
if [[ ! -f "$NOTES_FILE" ]]; then
    echo "release-notes.md not found" >&2
    exit 1
fi
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "GITHUB_TOKEN is required for upload; it is passed only to vpk and is not logged." >&2
    exit 1
fi

"$VPK_EXE" upload github \
    --outputDir "$(to_vpk_path "$OUTPUT_DIR")" \
    --repoUrl "$REPO_URL" \
    --token "$GITHUB_TOKEN" \
    --tag "$TAG" \
    --releaseName "$RELEASE_NAME" \
    --publish "$PUBLISH" \
    --pre false

if command -v gh >/dev/null 2>&1; then
    gh release edit "$TAG" --repo "$GH_REPO" --notes-file "$NOTES_FILE" >/dev/null
fi

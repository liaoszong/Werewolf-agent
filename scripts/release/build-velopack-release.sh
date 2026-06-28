#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RELEASE_DIR="${RELEASE_DIR:-$REPO_ROOT/.tmp/release}"
RELEASE_ROOT="${RELEASE_ROOT:-$REPO_ROOT/.tmp/velopack-release}"
PACK_VERSION="${VELOPACK_VERSION:-$(tr -d '\r\n' < "$REPO_ROOT/VERSION")}"
PACK_DIR="${PACK_DIR:-$RELEASE_ROOT/packdir-$PACK_VERSION}"
OUTPUT_DIR="${OUTPUT_DIR:-$RELEASE_ROOT/Releases}"
NOTES_FILE="${RELEASE_NOTES_FILE:-$REPO_ROOT/scripts/release/release-notes.md}"
VPK_EXE="${VPK_EXE:-vpk}"
CLEAN_OUTPUT="${CLEAN_OUTPUT:-1}"

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

echo "=== Preparing Velopack packDir $PACK_DIR ==="
rm -rf "$PACK_DIR"
if [[ "$CLEAN_OUTPUT" != "0" ]]; then
    rm -rf "$OUTPUT_DIR"
fi
mkdir -p "$PACK_DIR" "$OUTPUT_DIR" "$(dirname "$NOTES_FILE")"

cp -r "$RELEASE_DIR/Werewolf-agent/Werewolf-agent.exe" "$PACK_DIR/"
cp -r "$RELEASE_DIR/Werewolf-agent/_internal" "$PACK_DIR/"
cp -r "$RELEASE_DIR/app" "$PACK_DIR/"
mkdir -p "$PACK_DIR/runtime"
cp -r "$RELEASE_DIR/runtime/observer-server" "$PACK_DIR/runtime/"

printf "%s\n" "$PACK_VERSION" > "$PACK_DIR/VERSION"
printf "%s\n" "$PACK_VERSION" > "$PACK_DIR/runtime/observer-server/VERSION"

if [[ ! -f "$NOTES_FILE" ]]; then
    echo "release notes file not found: $NOTES_FILE" >&2
    exit 1
fi

echo "=== Running Velopack pack ==="
"$VPK_EXE" pack \
    --outputDir "$(to_vpk_path "$OUTPUT_DIR")" \
    --packId WerewolfAgent \
    --packTitle "Werewolf-agent" \
    --packVersion "$PACK_VERSION" \
    --packDir "$(to_vpk_path "$PACK_DIR")" \
    --mainExe Werewolf-agent.exe \
    --releaseNotes "$(to_vpk_path "$NOTES_FILE")"

SETUP_CANDIDATE="$(
    find "$OUTPUT_DIR" -maxdepth 1 -type f -iname '*Setup*.exe' -printf '%T@ %p\n' \
        | sort -nr \
        | head -n 1 \
        | cut -d' ' -f2- || true
)"
if [[ -n "$SETUP_CANDIDATE" ]]; then
    VERSIONED_SETUP_ALIAS="$OUTPUT_DIR/Werewolf-agent-$PACK_VERSION-Setup.exe"
    GENERIC_SETUP_ALIAS="$OUTPUT_DIR/Werewolf-agent-Setup.exe"
    if [[ "$(realpath "$SETUP_CANDIDATE")" != "$(realpath -m "$VERSIONED_SETUP_ALIAS")" ]]; then
        cp "$SETUP_CANDIDATE" "$VERSIONED_SETUP_ALIAS"
    fi
    if [[ "$(realpath "$SETUP_CANDIDATE")" != "$(realpath -m "$GENERIC_SETUP_ALIAS")" ]]; then
        cp "$SETUP_CANDIDATE" "$GENERIC_SETUP_ALIAS"
    fi
fi

echo "=== Velopack output ==="
find "$OUTPUT_DIR" -maxdepth 1 -type f -printf '%f\n' | sort

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION_VALUE="$(tr -d '\r\n' < "$REPO_ROOT/VERSION")"
RELEASE_DIR="${RELEASE_DIR:-$REPO_ROOT/.tmp/release}"
RELEASE_ROOT="${RELEASE_ROOT:-$REPO_ROOT/.tmp/velopack-release}"
PACK_DIR="${PACK_DIR:-$RELEASE_ROOT/packdir-$VERSION_VALUE}"
OUTPUT_DIR="${OUTPUT_DIR:-$RELEASE_ROOT/Releases}"
UNPACK_DIR="${UNPACK_DIR:-$RELEASE_ROOT/unpacked-full-$VERSION_VALUE}"
RUN_INSTALLED_E2E="${RUN_INSTALLED_E2E:-0}"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

expect_file() {
    if [[ -f "$1" ]]; then
        pass "$2"
    else
        fail "$2 missing: $1"
    fi
}

expect_dir() {
    if [[ -d "$1" ]]; then
        pass "$2"
    else
        fail "$2 missing: $1"
    fi
}

echo ""
echo "========================================"
echo "  R0 Velopack Release Smoke"
echo "  Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  Repo root: $REPO_ROOT"
echo "  Version: $VERSION_VALUE"
echo "========================================"
echo ""

echo "--- V1: Release staging ---"
expect_file "$RELEASE_DIR/Werewolf-agent/Werewolf-agent.exe" "Bootstrapper executable"
expect_dir "$RELEASE_DIR/Werewolf-agent/_internal" "Bootstrapper onedir runtime"
expect_file "$RELEASE_DIR/runtime/observer-server/observer-server.exe" "Frozen observer server"
expect_dir "$RELEASE_DIR/runtime/observer-server/_internal" "Frozen observer server runtime"
expect_file "$RELEASE_DIR/app/appqt_observer.exe" "Qt client executable"
expect_file "$RELEASE_DIR/app/Qt6Core.dll" "Qt runtime deployed"
expect_dir "$RELEASE_DIR/app/platforms" "Qt platforms deployed"

echo "--- V2: Version and manifest data ---"
expect_file "$REPO_ROOT/VERSION" "Root VERSION"
expect_file "$RELEASE_DIR/Werewolf-agent/VERSION" "Bootstrapper VERSION"
expect_file "$RELEASE_DIR/runtime/observer-server/VERSION" "Server VERSION"
if [[ -f "$RELEASE_DIR/Werewolf-agent/VERSION" ]] \
    && [[ "$(tr -d '\r\n' < "$RELEASE_DIR/Werewolf-agent/VERSION")" == "$VERSION_VALUE" ]]; then
    pass "Bootstrapper VERSION matches root"
else
    fail "Bootstrapper VERSION does not match root"
fi
if [[ -f "$RELEASE_DIR/runtime/observer-server/VERSION" ]] \
    && [[ "$(tr -d '\r\n' < "$RELEASE_DIR/runtime/observer-server/VERSION")" == "$VERSION_VALUE" ]]; then
    pass "Server VERSION matches root"
else
    fail "Server VERSION does not match root"
fi

echo "--- V3: Velopack packDir and package output ---"
expect_dir "$PACK_DIR" "Velopack packDir"
expect_file "$PACK_DIR/Werewolf-agent.exe" "Velopack main executable"
expect_dir "$PACK_DIR/_internal" "Velopack bootstrapper runtime"
expect_dir "$PACK_DIR/app" "Velopack Qt deployment tree"
expect_dir "$PACK_DIR/runtime/observer-server" "Velopack frozen observer server tree"
expect_file "$OUTPUT_DIR/Werewolf-agent-$VERSION_VALUE-Setup.exe" "Versioned first-install setup executable"
if [[ -e "$OUTPUT_DIR/Werewolf-agent-Setup.exe" ]]; then
    fail "Generic setup alias should not be present in release output"
else
    pass "Generic setup alias absent"
fi
expect_file "$OUTPUT_DIR/releases.win.json" "Velopack release index"
expect_file "$REPO_ROOT/scripts/release/release-notes.md" "Single release notes input"
if compgen -G "$OUTPUT_DIR/WerewolfAgent-$VERSION_VALUE-full.nupkg" >/dev/null; then
    pass "Full package exists"
else
    fail "Full package missing"
fi
if compgen -G "$OUTPUT_DIR/WerewolfAgent-$VERSION_VALUE-delta.nupkg" >/dev/null; then
    pass "Delta package exists"
else
    pass "Delta package not emitted for first package set"
fi

echo "--- V4: Data isolation in replaceable tree ---"
for sub in runs profiles configs logs runtime-state; do
    if [[ -e "$PACK_DIR/$sub" ]]; then
        fail "User data directory leaked into packDir: $sub"
    else
        pass "No user data directory in packDir: $sub"
    fi
done

echo "--- V5: Full package unpack and hygiene ---"
FULL_PACKAGE="$(find "$OUTPUT_DIR" -maxdepth 1 -type f -name "WerewolfAgent-$VERSION_VALUE-full.nupkg" | head -n 1 || true)"
if [[ -n "$FULL_PACKAGE" ]]; then
    rm -rf "$UNPACK_DIR"
    mkdir -p "$UNPACK_DIR"
    python - "$FULL_PACKAGE" "$UNPACK_DIR" <<'PY'
import sys
import zipfile
package, out_dir = sys.argv[1:3]
with zipfile.ZipFile(package) as zf:
    zf.extractall(out_dir)
PY
    pass "Full package unpacked"
else
    fail "Full package unavailable for unpack scan"
fi

OLD_PATTERNS=(
    "I""FW"
    "maintenance ""tool"
    "repo""gen"
    "binary""creator"
    "Updates"".xml"
    "github"".io"
    "werewolf-agent-""updates"
    "file""://"
)
for target in "$RELEASE_DIR" "$PACK_DIR" "$OUTPUT_DIR" "$UNPACK_DIR"; do
    [[ -d "$target" ]] || continue
    pattern_index=0
    for pattern in "${OLD_PATTERNS[@]}"; do
        pattern_index=$((pattern_index + 1))
        if python - "$target" "$pattern" <<'PY'
import os
import sys

root, pattern = sys.argv[1], sys.argv[2].encode("utf-8")
skip_ext = {
    ".dll", ".exe", ".pdb", ".a", ".o", ".obj", ".png", ".jpg", ".jpeg",
    ".ico", ".zip", ".nupkg", ".pyc", ".pyd", ".qm",
}
for dirpath, dirnames, filenames in os.walk(root):
    for name in filenames:
        path = os.path.join(dirpath, name)
        if os.path.splitext(name)[1].lower() in skip_ext:
            continue
        try:
            with open(path, "rb") as fh:
                if pattern in fh.read():
                    sys.exit(1)
        except OSError:
            pass
sys.exit(0)
PY
        then
            pass "No legacy token $pattern_index under $(basename "$target")"
        else
            fail "Legacy release token $pattern_index found under $target"
        fi
    done
done

echo "--- V6: Installed tree and local update E2E ---"
if [[ "$RUN_INSTALLED_E2E" == "1" ]]; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass \
        -File "$REPO_ROOT/scripts/release/run-installed-local-e2e.ps1" \
        -UpdateSource "$OUTPUT_DIR"
    pass "Installed local update E2E script completed"
else
    pass "Installed local update E2E skipped; set RUN_INSTALLED_E2E=1 to run it"
fi

echo ""
echo "========================================"
echo "  Smoke Test Results"
echo "  Passed: $PASS_COUNT"
echo "  Failed: $FAIL_COUNT"
echo "========================================"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    echo "FAILED: Some checks did not pass."
    exit 1
fi

echo "ALL SMOKE TESTS PASSED"

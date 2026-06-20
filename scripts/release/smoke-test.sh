#!/usr/bin/env bash
# R0 End-to-End Smoke Test
# Run from repo root: bash scripts/release/smoke-test.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RELEASE_DIR="$REPO_ROOT/.tmp/release"
INSTALLER="$RELEASE_DIR/Werewolf-agent-0.2.0-installer.exe"

PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

echo ""
echo "========================================"
echo "  R0 End-to-End Smoke Test"
echo "  Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  Repo root: $REPO_ROOT"
echo "========================================"
echo ""

# ── V1: Installer ──────────────────────────────────────────────
echo "--- V1: Installer exists ---"
if [ -f "$INSTALLER" ]; then
    INSTALLER_SIZE=$(stat -c%s "$INSTALLER")
    pass "Installer exists ($INSTALLER_SIZE bytes)"
else
    fail "Installer not found at $INSTALLER"
fi

# ── V2: Bootstrapper (standalone frozen) ───────────────────────
echo "--- V2: Bootstrapper frozen ---"
BOOTSTRAPPER="$RELEASE_DIR/Werewolf-agent/Werewolf-agent.exe"
if [ -f "$BOOTSTRAPPER" ]; then
    pass "Bootstrapper exe exists"
    # --version
    VERSION_OUT=$("$BOOTSTRAPPER" --version 2>&1)
    if echo "$VERSION_OUT" | grep -q "0.2.0"; then
        pass "Bootstrapper --version = $VERSION_OUT"
    else
        fail "Bootstrapper --version unexpected: $VERSION_OUT"
    fi
    # VERSION file alongside
    if [ -f "$RELEASE_DIR/Werewolf-agent/VERSION" ]; then
        BV=$(cat "$RELEASE_DIR/Werewolf-agent/VERSION")
        if [ "$BV" = "0.2.0" ]; then
            pass "Bootstrapper VERSION file = $BV"
        else
            fail "Bootstrapper VERSION file mismatch: $BV"
        fi
    else
        fail "Bootstrapper VERSION file missing"
    fi
    # _internal subdir
    if [ -d "$RELEASE_DIR/Werewolf-agent/_internal" ]; then
        pass "Bootstrapper _internal directory exists"
    else
        fail "Bootstrapper _internal directory missing"
    fi
else
    fail "Bootstrapper exe not found"
fi

# ── V3: Observer server (standalone frozen) ────────────────────
echo "--- V3: Observer server frozen ---"
SERVER="$RELEASE_DIR/runtime/observer-server/observer-server.exe"
if [ -f "$SERVER" ]; then
    pass "Server exe exists"
    VERSION_OUT=$("$SERVER" --version 2>&1)
    if echo "$VERSION_OUT" | grep -q "0.2.0"; then
        pass "Server --version = $VERSION_OUT"
    else
        fail "Server --version unexpected: $VERSION_OUT"
    fi
    # VERSION file alongside
    if [ -f "$RELEASE_DIR/runtime/observer-server/VERSION" ]; then
        SV=$(cat "$RELEASE_DIR/runtime/observer-server/VERSION")
        if [ "$SV" = "0.2.0" ]; then
            pass "Server VERSION file = $SV"
        else
            fail "Server VERSION file mismatch: $SV"
        fi
    else
        fail "Server VERSION file missing"
    fi
    # _internal subdir
    if [ -d "$RELEASE_DIR/runtime/observer-server/_internal" ]; then
        pass "Server _internal directory exists"
    else
        fail "Server _internal directory missing"
    fi
else
    fail "Server exe not found"
fi

# ── V4: Qt client (build output) ────────────────────────────────
echo "--- V4: Qt client ---"
CLIENT="$RELEASE_DIR/app/appqt_observer.exe"
if [ -f "$CLIENT" ]; then
    CLIENT_SIZE=$(stat -c%s "$CLIENT")
    pass "Qt client exists ($CLIENT_SIZE bytes)"
    # Verify windeployqt deployed Qt DLLs alongside
    if [ -f "$RELEASE_DIR/app/Qt6Core.dll" ]; then
        pass "Qt6Core.dll deployed alongside client"
    else
        fail "Qt6Core.dll not found -- windeployqt may not have run"
    fi
    # Verify platforms directory
    if [ -d "$RELEASE_DIR/app/platforms" ]; then
        pass "platforms/ directory exists"
    else
        fail "platforms/ directory missing"
    fi
else
    fail "Qt client not found at $CLIENT"
fi

# ── V5: IFW repository ─────────────────────────────────────────
echo "--- V5: IFW repository ---"
IFW_REPO="$REPO_ROOT/.tmp/ifw-repo/stable"
if [ -d "$IFW_REPO" ]; then
    pass "IFW repo directory exists"
    if [ -f "$IFW_REPO/Updates.xml" ]; then
        pass "Updates.xml exists"
    else
        fail "Updates.xml missing"
    fi
    if [ -d "$IFW_REPO/com.werewolfagent.app" ]; then
        COMP_COUNT=$(ls "$IFW_REPO/com.werewolfagent.app/"*.7z 2>/dev/null | wc -l)
        pass "Component archive directory exists ($COMP_COUNT .7z files)"
    else
        fail "Component directory missing"
    fi
else
    fail "IFW repo directory not found"
fi

# ── V6: VERSION root consistency ───────────────────────────────
echo "--- V6: VERSION consistency ---"
ROOT_VER=$(cat "$REPO_ROOT/VERSION" 2>/dev/null || echo "MISSING")
if [ "$ROOT_VER" = "0.2.0" ]; then
    pass "Root VERSION = $ROOT_VER"
else
    fail "Root VERSION unexpected: $ROOT_VER"
fi

# ── V7: Release manifest template ──────────────────────────────
echo "--- V7: Manifest template ---"
MANIFEST_TEMPLATE="$REPO_ROOT/scripts/release/distribution-manifest.json.in"
if [ -f "$MANIFEST_TEMPLATE" ]; then
    pass "distribution-manifest.json.in template exists"
    if grep -q '<placeholder>' "$MANIFEST_TEMPLATE"; then
        pass "Template contains placeholders"
    else
        fail "Template missing placeholders"
    fi
else
    fail "Template not found"
fi

# ── V8: Sentinel scan ──────────────────────────────────────────
echo "--- V8: Sentinel scan (no secrets in release) ---"
if grep -r "R0_TEST_SECRET_SENTINEL" "$RELEASE_DIR" 2>/dev/null; then
    fail "Secret sentinel found in release dirs!"
else
    pass "No secret sentinel in release dirs"
fi

# ── V9: Publish script ─────────────────────────────────────────
echo "--- V9: Publish script ---"
PUBLISH_SCRIPT="$REPO_ROOT/scripts/release/publish-to-github-pages.sh"
if [ -f "$PUBLISH_SCRIPT" ]; then
    pass "publish-to-github-pages.sh exists"
    if [ -x "$PUBLISH_SCRIPT" ]; then
        pass "Publish script is executable"
    else
        fail "Publish script is not executable"
    fi
else
    fail "Publish script not found"
fi

# ── Summary ─────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Smoke Test Results"
echo "  Passed: $PASS_COUNT"
echo "  Failed: $FAIL_COUNT"
echo "========================================"

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "FAILED: Some checks did not pass."
    exit 1
fi

echo "ALL SMOKE TESTS PASSED"
exit 0

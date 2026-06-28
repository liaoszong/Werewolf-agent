#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/.tmp/qt-observer-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release/app}"

QT_MOUNT_ROOT="${QT_MOUNT_ROOT:-/mnt/f/Qt}"
if [[ ! -d "$QT_MOUNT_ROOT" && -d /f/Qt ]]; then
    QT_MOUNT_ROOT="/f/Qt"
fi

QT_ROOT="${QT_ROOT:-$QT_MOUNT_ROOT/6.10.0/mingw_64}"
MINGW_ROOT="${MINGW_ROOT:-$QT_MOUNT_ROOT/Tools/mingw1310_64}"
CMAKE_EXE="${CMAKE_EXE:-$QT_MOUNT_ROOT/Tools/CMake_64/bin/cmake.exe}"
WINDEPLOYQT_EXE="${WINDEPLOYQT_EXE:-$QT_ROOT/bin/windeployqt.exe}"
MAKE_EXE="${MAKE_EXE:-$MINGW_ROOT/bin/mingw32-make.exe}"

to_windows_path() {
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

echo "=== Configuring Release build ==="
"$CMAKE_EXE" \
    -S "$(to_windows_path "$REPO_ROOT/clients/qt_observer")" \
    -B "$(to_windows_path "$BUILD_DIR")" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="$(to_windows_path "$QT_ROOT")" \
    -DCMAKE_MAKE_PROGRAM="$(to_windows_path "$MAKE_EXE")" \
    -G "MinGW Makefiles"

echo "=== Building ==="
"$CMAKE_EXE" --build "$(to_windows_path "$BUILD_DIR")" --config Release

echo "=== Deploying with windeployqt ==="
mkdir -p "$OUTPUT_DIR"
cp "$BUILD_DIR/appqt_observer.exe" "$OUTPUT_DIR/"

"$WINDEPLOYQT_EXE" \
    --release \
    --qmldir "$(to_windows_path "$REPO_ROOT/clients/qt_observer/qml")" \
    --compiler-runtime \
    "$(to_windows_path "$OUTPUT_DIR/appqt_observer.exe")"

echo "=== Qt deployment tree ready at $OUTPUT_DIR ==="
ls -la "$OUTPUT_DIR"

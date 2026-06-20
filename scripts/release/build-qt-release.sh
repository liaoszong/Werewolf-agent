#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/.tmp/qt-observer-release"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.tmp/release/app}"

export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:/f/Qt/Tools/CMake_64/bin:$PATH"

echo "=== Configuring Release build ==="
cmake -S "$REPO_ROOT/clients/qt_observer" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -G "MinGW Makefiles"

echo "=== Building ==="
cmake --build "$BUILD_DIR" --config Release

echo "=== Deploying with windeployqt ==="
mkdir -p "$OUTPUT_DIR"
cp "$BUILD_DIR/appqt_observer.exe" "$OUTPUT_DIR/"

windeployqt.exe \
    --release \
    --qmldir "$REPO_ROOT/clients/qt_observer/qml" \
    --compiler-runtime \
    "$OUTPUT_DIR/appqt_observer.exe"

echo "=== Qt deployment tree ready at $OUTPUT_DIR ==="
ls -la "$OUTPUT_DIR"

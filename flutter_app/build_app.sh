#!/usr/bin/env bash
# Build Flutter app for current platform (Linux/macOS)
set -euo pipefail

echo "============================================"
echo " Build Flutter App"
echo "============================================"

cd "$(dirname "$0")/flutter_app"

# Detect platform
UNAME_S="$(uname -s)"

case "$UNAME_S" in
    Linux)
        echo "[Platform: Linux]"
        flutter build linux --release
        echo ""
        echo "Build artifacts: build/linux/x64/release/bundle/flutter_app"
        ;;
    Darwin)
        echo "[Platform: macOS]"
        flutter build macos --release
        echo ""
        echo "Build artifacts: build/macos/Build/Products/Release/flutter_app.app"
        ;;
    *)
        echo "[ERROR] Unsupported platform: $UNAME_S"
        exit 1
        ;;
esac

echo "============================================"
echo " Flutter build SUCCESS"
echo "============================================"
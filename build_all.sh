#!/usr/bin/env bash
# FileConverter Full Build Script (Linux/macOS)
set -euo pipefail

echo "============================================"
echo " FileConverter Full Build Script"
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Detect platform
UNAME_S="$(uname -s)"
case "$UNAME_S" in
    Linux)   PLATFORM="linux" ;;
    Darwin)  PLATFORM="macos" ;;
    *)
        echo "[ERROR] Unsupported platform: $UNAME_S"
        exit 1
        ;;
esac
echo "[Platform: $PLATFORM]"
echo ""

# ── Step 1: Package Python Backend ──
echo "[1/4] Packaging Python backend..."
bash build_backend.sh
echo "[1/4] Python backend build SUCCESS"
echo ""

# ── Step 2: Build Flutter Release ──
echo "[2/4] Building Flutter Release..."
cd "$SCRIPT_DIR/flutter_app"
if [ "$PLATFORM" = "linux" ]; then
    flutter build linux --release
    FLUTTER_OUT="$SCRIPT_DIR/flutter_app/build/linux/x64/release/bundle"
elif [ "$PLATFORM" = "macos" ]; then
    flutter build macos --release
    FLUTTER_OUT="$SCRIPT_DIR/flutter_app/build/macos/Build/Products/Release"
fi
echo "[2/4] Flutter Release build SUCCESS"
echo ""

# ── Step 3: Copy backend into Flutter output ──
echo "[3/4] Copying backend into Flutter release directory..."
rm -rf "$FLUTTER_OUT/backend"
cp -r "$SCRIPT_DIR/dist/backend" "$FLUTTER_OUT/backend"
echo "[3/4] Backend copied to Flutter release directory"
echo ""

# ── Step 4: Package installer (platform-specific) ──
echo "[4/4] Packaging installer..."
cd "$SCRIPT_DIR"

if [ "$PLATFORM" = "linux" ]; then
    # Create a simple .tar.gz bundle (or use AppImage tool if available)
    BUNDLE_NAME="FileConverter-$PLATFORM-x64"
    BUNDLE_DIR="$SCRIPT_DIR/output/$BUNDLE_NAME"
    mkdir -p "$BUNDLE_DIR"
    cp -r "$FLUTTER_OUT"/* "$BUNDLE_DIR/"
    # Create launcher script
    cat > "$BUNDLE_DIR/FileConverter.sh" << 'LAUNCHER'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/flutter_app" &
LAUNCHER
    chmod +x "$BUNDLE_DIR/FileConverter.sh"
    # Create .tar.gz
    cd "$SCRIPT_DIR/output"
    tar -czf "$BUNDLE_NAME.tar.gz" "$BUNDLE_NAME"
    echo "[4/4] Bundle created: output/$BUNDLE_NAME.tar.gz"

elif [ "$PLATFORM" = "macos" ]; then
    # Create .dmg if create-dmg is available, otherwise .tar.gz
    if command -v create-dmg &>/dev/null; then
        create-dmg \
            --volname "FileConverter" \
            --window-pos 200 120 \
            --window-size 640 400 \
            --app-drop-link 480 200 \
            "output/FileConverter-$PLATFORM-x64.dmg" \
            "$FLUTTER_OUT"
        echo "[4/4] DMG created: output/FileConverter-$PLATFORM-x64.dmg"
    else
        BUNDLE_NAME="FileConverter-$PLATFORM-x64"
        BUNDLE_DIR="$SCRIPT_DIR/output/$BUNDLE_NAME"
        mkdir -p "$BUNDLE_DIR"
        cp -r "$FLUTTER_OUT"/* "$BUNDLE_DIR/"
        cd "$SCRIPT_DIR/output"
        tar -czf "$BUNDLE_NAME.tar.gz" "$BUNDLE_NAME"
        echo "[4/4] Bundle created: output/$BUNDLE_NAME.tar.gz"
        echo "  (install create-dmg for .dmg: brew install create-dmg)"
    fi
fi

echo ""
echo "============================================"
echo "  BUILD COMPLETE!"
echo ""
echo "  Output directory: $SCRIPT_DIR/output/"
echo "============================================"
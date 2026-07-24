#!/usr/bin/env bash
# Package Python Backend with PyInstaller (Linux/macOS)
set -euo pipefail

echo "============================================"
echo " Package Python Backend - PyInstaller"
echo "============================================"

cd "$(dirname "$0")"

# Check PyInstaller
if ! command -v pyinstaller &>/dev/null; then
    echo "[Installing PyInstaller]..."
    pip install pyinstaller
fi

# Clean old build
rm -rf dist/backend build/pyinstaller

echo "[Starting PyInstaller]..."
pyinstaller \
    --onedir \
    --name backend \
    --distpath dist \
    --workpath build/pyinstaller \
    --add-data "converters:converters" \
    --hidden-import=uvicorn.logging \
    --hidden-import=uvicorn.protocols.http.auto \
    --hidden-import=uvicorn.protocols.websockets.auto \
    --hidden-import=pdfplumber \
    --hidden-import=openpyxl \
    --hidden-import=docx \
    --hidden-import=bs4 \
    --hidden-import=lxml \
    --hidden-import=pydantic \
    --collect-all=pdfplumber \
    --collect-all=openpyxl \
    --collect-all=docx \
    --collect-all=bs4 \
    --exclude-module=tkinter \
    --exclude-module=test \
    --exclude-module=unittest \
    --exclude-module=pdb \
    --exclude-module=doctest \
    --exclude-module=win32com \
    python_backend/main.py

echo ""
echo "============================================"
echo " Backend packaged: dist/backend/backend"
echo "============================================"
@echo off
chcp 65001 >nul
title 打包 Python 后端

echo ============================================
echo  打包 Python 后端 - PyInstaller
echo ============================================

cd /d "%~dp0"

REM 检查 PyInstaller
where pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [安装 PyInstaller]...
    pip install pyinstaller
)

REM 清理旧构建
if exist "dist\backend" (
    echo [清理旧构建]...
    rmdir /s /q "dist\backend"
)
if exist "build\pyinstaller" (
    rmdir /s /q "build\pyinstaller"
)

echo [开始打包]...
pyinstaller ^
    --onedir ^
    --name backend ^
    --distpath dist ^
    --workpath build\pyinstaller ^
    --add-data "converters;converters" ^
    --hidden-import=uvicorn.logging ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.protocols.websockets.auto ^
    --hidden-import=win32com ^
    --hidden-import=win32com.client ^
    --collect-submodules=win32com ^
    --exclude-module=tkinter ^
    --exclude-module=test ^
    --exclude-module=unittest ^
    --exclude-module=pdb ^
    --exclude-module=doctest ^
    --noconfirm ^
    python_backend\main.py

if %ERRORLEVEL% neq 0 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo ============================================
echo  打包成功！
echo  输出目录: dist\backend\
echo  backend.exe 已生成
echo ============================================
pause
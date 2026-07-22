@echo off
chcp 65001 >nul
title FileConverter 全量构建

echo ============================================
echo  FileConverter Full Build Script
echo ============================================
echo.

REM ── Step 1: 构建 Flutter Release ──
echo [1/4] Building Flutter Release...
cd /d "%~dp0flutter_app"
call flutter build windows --release
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Flutter build failed!
    pause
    exit /b 1
)
echo [1/4] Flutter Release build SUCCESS
echo.

REM ── Step 2: 打包 Python 后端 ──
echo [2/4] Packaging Python backend...
cd /d "%~dp0"
call build_backend.bat
REM build_backend.bat 末尾有 pause，这里不需要重复
echo [2/4] Python backend build SUCCESS
echo.

REM ── Step 3: 编译 Inno Setup 安装包 ──
echo [3/4] Compiling installer...
set "ISCC="
REM 查找 Inno Setup 编译器
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
if exist "C:\Program Files\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 5\ISCC.exe"

if "%ISCC%"=="" (
echo [WARN] Inno Setup compiler (ISCC.exe) not found.
echo Please install Inno Setup: https://jrsoftware.org/isdl.php
echo Or manually compile: iscc installer\FileConverter.iss
pause
) else (
    "%ISCC%" "%~dp0installer\FileConverter.iss"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Installer compilation failed!
        pause
        exit /b 1
    )
    echo [3/4] Installer compiled SUCCESS
)
echo.

REM ── Step 4: 输出汇总 ──
echo [4/4] BUILD COMPLETE!
echo.
echo ============================================
echo  Artifacts:
echo.
echo  Flutter Release:
echo    %~dp0flutter_app\build\windows\x64\runner\Release\flutter_app.exe
echo.
echo  Python Backend:
echo    %~dp0dist\backend\backend.exe
echo.
echo  Installer:
if exist "%~dp0installer\FileConverter_Setup_v*.exe" (
    dir /b "%~dp0installer\FileConverter_Setup_v*.exe"
) else (
    echo    (not built - ISCC not found)
)
echo.
echo ============================================

pause
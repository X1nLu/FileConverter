@echo off
chcp 65001 >nul
title FileConverter Full Build

echo ============================================
echo  FileConverter Full Build Script
echo ============================================
echo.

REM ── Step 1: Package Python Backend ──
echo [1/4] Packaging Python backend...
cd /d "%~dp0"
call build_backend.bat --no-pause
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Backend packaging failed!
    exit /b 1
)
echo [1/4] Python backend build SUCCESS
echo.

REM ── Step 2: Build Flutter Release ──
echo [2/4] Building Flutter Release...
cd /d "%~dp0flutter_app"
call flutter build windows --release
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Flutter build failed!
    exit /b 1
)
echo [2/4] Flutter Release build SUCCESS
echo.

REM ── Step 3: Copy backend into Flutter output ──
echo [3/4] Copying backend into Flutter release directory...
set FLUTTER_OUT=%~dp0flutter_app\build\windows\x64\runner\Release
if exist "%FLUTTER_OUT%\backend" (
    rmdir /s /q "%FLUTTER_OUT%\backend"
)
xcopy /e /i /q "%~dp0dist\backend" "%FLUTTER_OUT%\backend"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to copy backend!
    exit /b 1
)
echo [3/4] Backend copied to Flutter release directory
echo.

REM ── Step 4: Compile Inno Setup Installer ──
echo [4/4] Compiling installer...
REM Check common ISCC installation paths
set ISCC_EXE=
dir "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" >nul 2>nul && set ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if defined ISCC_EXE goto :run_iscc
dir "C:\Program Files\Inno Setup 6\ISCC.exe" >nul 2>nul && set ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe
if defined ISCC_EXE goto :run_iscc
dir "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" >nul 2>nul && set ISCC_EXE=C:\Program Files (x86)\Inno Setup 5\ISCC.exe
if defined ISCC_EXE goto :run_iscc
dir "C:\Program Files\Inno Setup 5\ISCC.exe" >nul 2>nul && set ISCC_EXE=C:\Program Files\Inno Setup 5\ISCC.exe
if defined ISCC_EXE goto :run_iscc
goto :no_iscc
:run_iscc
"%ISCC_EXE%" "%~dp0installer\FileConverter.iss"
if errorlevel 1 goto :iscc_failed
echo [4/4] Installer compiled SUCCESS
goto :after_installer
:iscc_failed
echo [ERROR] Installer compilation failed!
exit /b 1
:no_iscc
echo [WARN] Inno Setup compiler (ISCC.exe) not found.
echo Please install Inno Setup: https://jrsoftware.org/isdl.php
echo Or manually compile: iscc installer\FileConverter.iss
:after_installer
echo.

REM ── Summary ──
echo ============================================
echo  BUILD COMPLETE!
echo.
echo  Standalone portable:
echo    %FLUTTER_OUT%\flutter_app.exe
echo    (with backend at %%FLUTTER_OUT%%\backend\backend.exe)
echo.
echo  Installer:
if exist "%~dp0installer\FileConverter_Setup_v*.exe" (
    dir /b "%~dp0installer\FileConverter_Setup_v*.exe"
) else (
    echo    (not built - ISCC not found)
)
echo.
echo  You can run flutter_app.exe directly from:
echo    %FLUTTER_OUT%
echo.
echo ============================================
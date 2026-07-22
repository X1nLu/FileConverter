@echo off
chcp 65001 >nul
title FileConverter 全量构建

echo ============================================
echo  FileConverter 全量构建脚本
echo ============================================
echo.

REM ── Step 1: 构建 Flutter Release ──
echo [1/4] 构建 Flutter Release...
cd /d "%~dp0flutter_app"
call flutter build windows --release
if %ERRORLEVEL% neq 0 (
    echo [错误] Flutter 构建失败！
    pause
    exit /b 1
)
echo [1/4] Flutter Release 构建成功
echo.

REM ── Step 2: 打包 Python 后端 ──
echo [2/4] 打包 Python 后端...
cd /d "%~dp0"
call build_backend.bat
REM build_backend.bat 末尾有 pause，这里不需要重复
echo [2/4] Python 后端打包成功
echo.

REM ── Step 3: 编译 Inno Setup 安装包 ──
echo [3/4] 编译安装包...
set "ISCC="
REM 查找 Inno Setup 编译器
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
if exist "C:\Program Files\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 5\ISCC.exe"

if "%ISCC%"=="" (
    echo [警告] 未找到 Inno Setup 编译器 (ISCC.exe)
    echo 请手动编译 installer\FileConverter.iss
    echo 或安装 Inno Setup: https://jrsoftware.org/isdl.php
) else (
    "%ISCC%" "%~dp0installer\FileConverter.iss"
    if %ERRORLEVEL% neq 0 (
        echo [错误] 安装包编译失败！
        pause
        exit /b 970
    )
    echo [3/4] 安装包编译成功
)
echo.

REM ── Step 4: 输出汇总 ──
echo [4/4] 构建完成！
echo.
echo ============================================
echo  构建产物：
echo.
echo  Flutter Release:
echo    %~dp0flutter_app\build\windows\runner\Release\file_converter.exe
echo.
echo  Python 后端:
echo    %~dp0dist\backend\backend.exe
echo.
echo  安装包:
if exist "%~dp0installer\FileConverter_Setup_v*.exe" (
    dir /b "%~dp0installer\FileConverter_Setup_v*.exe"
)
echo.
echo ============================================

pause
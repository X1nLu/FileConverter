@echo off
cd /d "D:\WWW\Python\FileConverter\flutter_app"
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" 2>nul
flutter build windows --debug
echo EXIT_CODE=%ERRORLEVEL%
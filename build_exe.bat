@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
python scripts\build_release.py
if errorlevel 1 exit /b 1
endlocal

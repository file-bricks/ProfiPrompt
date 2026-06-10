@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden! Bitte Python installieren.
    pause
    exit /b 1
)
set PYTHONIOENCODING=utf-8
echo Starte ProfiPrompt...
python "src\profiprompt.py"
if errorlevel 1 pause

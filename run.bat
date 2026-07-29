@echo off
title 0xVoice2Text Widget Launcher
cd /d "%~dp0"

echo ===================================================
echo   0xVoice2Text — Win7 Aero Glass Voice-to-Text Widget
echo ===================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo Starting 0xVoice2Text Widget...
start "" pythonw main.py
if %errorlevel% neq 0 (
    python main.py
)

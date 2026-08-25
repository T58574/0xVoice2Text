@echo off
title 0xVoice2Text Launcher
cd /d "%~dp0"

echo ===================================================
echo   0xVoice2Text - Real-Time Voice AI Assistant Hub
echo ===================================================
echo.

set "PY_EXE="
set "PYW_EXE="

:: 1. Check local venv
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0venv\Scripts\python.exe"
    set "PYW_EXE=%~dp0venv\Scripts\pythonw.exe"
    echo [+] Using virtual environment: .\venv
    goto :found_python
)

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
    set "PYW_EXE=%~dp0.venv\Scripts\pythonw.exe"
    echo [+] Using virtual environment: .\.venv
    goto :found_python
)

:: 2. Check system python
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    set "PYW_EXE=pythonw"
    echo [!] Using system Python (no local venv detected)
    goto :found_python
)

echo [CRIT] Python is not installed or not in PATH!
echo Please install Python 3.10+ and create venv: python -m venv venv
echo.
pause
exit /b 1

:found_python

:: Check for debug or console flag
if "%~1"=="--debug" goto :run_debug
if "%~1"=="-d" goto :run_debug
if "%~1"=="debug" goto :run_debug
if "%~1"=="--console" goto :run_debug
if "%~1"=="-c" goto :run_debug

:: Standard background launch (windowless via pythonw)
echo [*] Launching 0xVoice2Text Widget in background...
start "" "%PYW_EXE%" main.py
if %errorlevel% neq 0 (
    echo [WARN] pythonw failed to spawn. Falling back to foreground console mode...
    goto :run_debug
)
echo [OK] 0xVoice2Text started successfully.
ping 127.0.0.1 -n 2 >nul 2>&1
exit /b 0

:run_debug
echo [*] Running 0xVoice2Text in interactive console mode...
echo.
"%PY_EXE%" main.py
if %errorlevel% neq 0 (
    echo.
    echo [FAIL] Application exited with error code %errorlevel%.
    pause
)

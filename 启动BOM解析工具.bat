@echo off
title BOM Tool

cd /d "%~dp0"

:: Check Python
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=py
) else (
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Python not found. Please install Python 3.8+
        echo https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON=python
)

:: Venv config
set VENV_PYTHON=%~dp0venv\Scripts\python.exe

:: First run: create venv and install dependencies
if not exist "%VENV_PYTHON%" (
    echo [INFO] First run, creating virtual environment...
    %PYTHON% -m venv "%~dp0venv"
    if %errorlevel% neq 0 (
        echo [FAIL] Cannot create virtual environment
        pause
        exit /b 1
    )
    echo [INFO] Installing dependencies...
    "%VENV_PYTHON%" -m pip install --upgrade pip -q
    "%VENV_PYTHON%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if %errorlevel% neq 0 (
        echo [FAIL] Dependencies install failed
        pause
        exit /b 1
    )
    echo [INFO] Setup complete
)

:: Start
"%VENV_PYTHON%" main.py
pause

@echo off
setlocal

set "PYTHON_CMD=python"
python --version >nul 2>nul
if errorlevel 1 (
    set "PYTHON_CMD=py"
)

%PYTHON_CMD% --version >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer and add it to PATH.
    pause
    exit /b 1
)

echo Installing project dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 (
    echo Could not install dependencies.
    pause
    exit /b 1
)

echo Dependencies are installed.
pause

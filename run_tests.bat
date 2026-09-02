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

%PYTHON_CMD% -c "import reportlab" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies from requirements.txt...
    %PYTHON_CMD% -m pip install -r requirements.txt --disable-pip-version-check
    if errorlevel 1 (
        echo Could not install dependencies. Try running install_requirements.bat.
        pause
        exit /b 1
    )
)

%PYTHON_CMD% -m unittest discover -s tests -v
pause

@echo off
REM install_remote.bat - One-click setup and run the remote agent on Windows

echo Setting up remote agent...

echo Current directory: %cd%
echo Looking for vm_agent.py at: %cd%\vm_agent.py

REM Check if the file exists
if not exist "%cd%\vm_agent.py" (
    echo Error: vm_agent.py not found at %cd%\vm_agent.py
    echo Please ensure the files are in the correct folder.
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Installing Python...
    REM Try winget first (Windows 10/11)
    winget --version >nul 2>&1
    if not errorlevel 1 (
        echo Installing Python via winget...
        winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
    ) else (
        echo Winget not available. Please install Python manually from https://python.org
        pause
        exit /b 1
    )
    REM Refresh PATH
    call refreshenv.cmd >nul 2>&1 || set PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts
)

REM Check if Git is available
git --version >nul 2>&1
if errorlevel 1 (
    echo Git not found. Installing Git...
    REM Try winget first
    winget --version >nul 2>&1
    if not errorlevel 1 (
        echo Installing Git via winget...
        winget install Git.Git --accept-source-agreements --accept-package-agreements
    ) else (
        echo Winget not available. Please install Git manually from https://git-scm.com
        pause
        exit /b 1
    )
    REM Refresh PATH
    call refreshenv.cmd >nul 2>&1 || set PATH=%PATH%;C:\Program Files\Git\cmd
)

REM Ensure pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Pip not available. Installing pip...
    python -m ensurepip --upgrade
)

REM Install required packages
echo Installing dependencies...
pip install pillow pyautogui

REM Run the agent
echo Starting remote agent on port 8000...
python vm_agent.py --port 8000

pause
@echo off
REM install_orchestrator.bat - Install web dependencies for Riko Orchestrator

echo Installing Riko Orchestrator Web UI dependencies...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python first.
    pause
    exit /b 1
)

REM Install web requirements
echo Installing Flask and dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements-web.txt

echo.
echo Installation complete!
echo.
echo To start the orchestrator:
echo   python orchestrator_web.py
echo.
echo Then open your browser to: http://localhost:5000
echo.
pause
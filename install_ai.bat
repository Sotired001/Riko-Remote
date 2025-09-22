@echo off
REM install_ai.bat - Install AI dependencies for Riko Orchestrator

echo Installing AI Assistant dependencies...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python first.
    pause
    exit /b 1
)

echo.
echo Installing Python packages...
python -m pip install --upgrade pip
python -m pip install requests

echo.
echo Checking for Ollama...

REM Check if Ollama is installed
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Ollama not found. Installing Ollama...
    
    REM Try to download and install Ollama
    echo Downloading Ollama installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://ollama.ai/download/OllamaSetup.exe' -OutFile 'OllamaSetup.exe'"
    
    if exist "OllamaSetup.exe" (
        echo Running Ollama installer...
        start /wait OllamaSetup.exe
        del OllamaSetup.exe
        
        echo.
        echo Please restart your terminal and run this script again.
        echo After restart, Ollama will download the AI model automatically.
        pause
        exit /b 0
    ) else (
        echo Failed to download Ollama installer.
        echo Please install manually from: https://ollama.ai
        pause
        exit /b 1
    )
) else (
    echo ✅ Ollama found!
)

echo.
echo Pulling AI model (this may take a few minutes)...
ollama pull llama3.2

if errorlevel 1 (
    echo Failed to pull AI model. Trying smaller model...
    ollama pull llama3.2:1b
    
    if errorlevel 1 (
        echo Failed to pull AI models. Please check your internet connection.
        pause
        exit /b 1
    )
)

echo.
echo ✅ AI Assistant setup complete!
echo.
echo To test the AI assistant:
echo   python ai_assistant.py
echo.
echo To use with the web orchestrator:
echo   python orchestrator_web.py
echo   Then open http://localhost:5000
echo.
pause
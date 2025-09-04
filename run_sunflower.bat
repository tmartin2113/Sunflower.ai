@echo off
REM Sunflower AI Windows Quick Launcher
REM Easy one-click setup for Windows users

setlocal enabledelayedexpansion

REM Set console colors
color 0A

REM Clear screen and show header
cls
echo ============================================================
echo           SUNFLOWER AI EDUCATION SYSTEM
echo           Windows Quick Start Launcher v6.2
echo ============================================================
echo.

REM Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Not running as Administrator
    echo Some features may require admin privileges
    echo.
)

REM Check Python installation
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo.
    echo Please install Python 3.11+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    pause
    start https://www.python.org/downloads/
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo       Found Python !PYTHON_VERSION!
)

REM Check available memory
echo [2/7] Checking system requirements...
for /f "skip=1" %%p in ('wmic computersystem get TotalPhysicalMemory') do (
    set MEM=%%p
    goto :mem_found
)
:mem_found
set /a MEM_GB=!MEM:~0,-9!
if !MEM_GB! LSS 4 (
    echo       [WARNING] Low RAM detected: !MEM_GB!GB
    echo       Minimum 4GB recommended for optimal performance
) else (
    echo       RAM: !MEM_GB!GB [OK]
)

REM Check Docker Desktop
echo [3/7] Checking Docker Desktop...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       Docker Desktop not found
    echo.
    choice /C YN /M "Would you like to use Docker for easier setup?"
    if !errorlevel! equ 1 (
        echo.
        echo Opening Docker Desktop download page...
        start https://www.docker.com/products/docker-desktop
        echo.
        echo Please install Docker Desktop and restart this script
        pause
        exit /b 0
    ) else (
        echo       Proceeding without Docker (standalone mode)
        set USE_DOCKER=0
    )
) else (
    echo       Docker Desktop found
    set USE_DOCKER=1
    
    REM Check if Docker is running
    docker ps >nul 2>&1
    if !errorlevel! neq 0 (
        echo       Starting Docker Desktop...
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        echo       Waiting for Docker to start (this may take a minute)...
        
        :wait_docker
        timeout /t 5 /nobreak >nul
        docker ps >nul 2>&1
        if !errorlevel! neq 0 goto wait_docker
        
        echo       Docker Desktop started successfully
    )
)

REM Check/Install Ollama
echo [4/7] Checking Ollama installation...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       Ollama not found
    echo.
    echo Downloading Ollama installer...
    
    REM Download Ollama installer
    if not exist "temp" mkdir temp
    powershell -Command "Invoke-WebRequest -Uri 'https://ollama.ai/download/OllamaSetup.exe' -OutFile 'temp\OllamaSetup.exe'"
    
    if exist "temp\OllamaSetup.exe" (
        echo Installing Ollama (please follow the installer)...
        start /wait temp\OllamaSetup.exe
        
        REM Verify installation
        ollama --version >nul 2>&1
        if !errorlevel! neq 0 (
            echo.
            echo [ERROR] Ollama installation failed
            echo Please install manually from: https://ollama.ai/download/windows
            pause
            exit /b 1
        ) else (
            echo       Ollama installed successfully
        )
    ) else (
        echo [ERROR] Failed to download Ollama
        echo Please install manually from: https://ollama.ai/download/windows
        pause
        exit /b 1
    )
) else (
    echo       Ollama is installed
)

REM Install Python dependencies
echo [5/7] Installing Python dependencies...
pip install --quiet --upgrade pip
pip install --quiet requests psutil

REM Create necessary directories
echo [6/7] Setting up directory structure...
if not exist "models" mkdir models
if not exist "config" mkdir config
if not exist "local_data" mkdir local_data
if not exist "local_data\profiles" mkdir local_data\profiles
if not exist "local_data\conversations" mkdir local_data\conversations
if not exist "logs" mkdir logs
echo       Directories created

REM Choose setup method
echo.
echo ============================================================
echo                    SETUP METHOD
echo ============================================================
echo.
echo How would you like to run Sunflower AI?
echo.
echo [1] Quick Start with Docker (Recommended)
echo [2] Run with Python Script
echo [3] Manual Setup (Advanced)
echo [4] Exit
echo.
choice /C 1234 /M "Select option"

if !errorlevel! equ 1 goto docker_setup
if !errorlevel! equ 2 goto python_setup
if !errorlevel! equ 3 goto manual_setup
if !errorlevel! equ 4 goto end

:docker_setup
echo.
echo [7/7] Starting Sunflower AI with Docker...
echo.

REM Start services with Docker Compose
if exist "docker-compose.dev.yml" (
    echo Starting Docker services...
    docker-compose -f docker-compose.dev.yml up -d
    
    echo.
    echo Waiting for services to initialize...
    timeout /t 10 /nobreak >nul
    
    echo.
    echo ============================================================
    echo           SUNFLOWER AI IS STARTING!
    echo ============================================================
    echo.
    echo Web Interface: http://localhost:8080
    echo Parent Dashboard: http://localhost:8081
    echo.
    echo Demo Login: parent / demo123
    echo.
    echo Opening browser in 5 seconds...
    timeout /t 5 /nobreak >nul
    start http://localhost:8080
    
    echo.
    echo Press any key to stop all services...
    pause >nul
    
    echo.
    echo Stopping services...
    docker-compose -f docker-compose.dev.yml down
) else (
    echo [ERROR] docker-compose.dev.yml not found
    echo Please ensure you're in the Sunflower AI directory
    pause
)
goto end

:python_setup
echo.
echo [7/7] Starting Sunflower AI with Python...
echo.

REM Check if run_local.py exists
if exist "run_local.py" (
    echo Launching Sunflower AI...
    python run_local.py
) else (
    echo [ERROR] run_local.py not found
    echo Please ensure you're in the Sunflower AI directory
    pause
)
goto end

:manual_setup
echo.
echo [7/7] Manual Setup Instructions
echo ============================================================
echo.
echo 1. Start Ollama service:
echo    ollama serve
echo.
echo 2. Load Sunflower models:
echo    ollama create sunflower-kids -f models\sunflower-kids.modelfile
echo    ollama create sunflower-educator -f models\sunflower-educator.modelfile
echo.
echo 3. Run Open WebUI:
echo    - With Docker:
echo      docker run -d -p 8080:8080 ghcr.io/open-webui/open-webui:main
echo.
echo    - From source:
echo      git clone https://github.com/open-webui/open-webui.git
echo      cd open-webui
echo      python backend\main.py
echo.
echo 4. Open browser to: http://localhost:8080
echo.
pause
goto end

:end
echo.
echo ============================================================
echo           Thank you for using Sunflower AI!
echo ============================================================
echo.
echo For support and documentation:
echo - Quick Start Guide: QUICK_START.md
echo - Testing Guide: TESTING_GUIDE.md
echo - Troubleshooting: logs\sunflower_local.log
echo.
pause
exit /b 0

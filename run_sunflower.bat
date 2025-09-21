@echo off
REM ============================================================================
REM Sunflower AI Windows Quick Launcher
REM Version: 6.2 - Production Ready (No ANSI Colors)
REM Purpose: Easy one-click setup for Windows users
REM Location: Repository root directory
REM ============================================================================

setlocal enabledelayedexpansion

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
    echo          Some features may require admin privileges
    echo.
)

REM ============================================================================
REM SYSTEM REQUIREMENTS CHECK
REM ============================================================================

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
    echo       [OK] Found Python !PYTHON_VERSION!
)

REM Check available memory
echo [2/7] Checking system requirements...
for /f "skip=1" %%p in ('wmic computersystem get TotalPhysicalMemory') do (
    set MEM=%%p
    goto :mem_found
)
:mem_found
set /a MEM_GB=!MEM:~0,-9! 2>nul
if !MEM_GB! LSS 4 (
    echo       [WARNING] Low RAM detected: !MEM_GB!GB
    echo                 Minimum 4GB recommended for optimal performance
) else (
    echo       [OK] RAM: !MEM_GB!GB
)

REM Check Docker Desktop
echo [3/7] Checking Docker Desktop...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       [INFO] Docker Desktop not found
    echo.
    choice /C YN /M "Would you like to use Docker for easier setup?"
    if !errorlevel! equ 1 (
        echo.
        echo [INFO] Opening Docker Desktop download page...
        start https://www.docker.com/products/docker-desktop
        echo.
        echo Please install Docker Desktop and restart this script
        pause
        exit /b 0
    ) else (
        echo       [INFO] Proceeding without Docker (standalone mode)
        set USE_DOCKER=0
    )
) else (
    echo       [OK] Docker Desktop found
    set USE_DOCKER=1
    
    REM Check if Docker is running
    docker ps >nul 2>&1
    if !errorlevel! neq 0 (
        echo       [INFO] Starting Docker Desktop...
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        echo             Waiting for Docker to start (this may take a minute)...
        
        :wait_docker
        timeout /t 5 /nobreak >nul
        docker ps >nul 2>&1
        if !errorlevel! neq 0 goto wait_docker
        
        echo       [OK] Docker Desktop started successfully
    )
)

REM Check/Install Ollama
echo [4/7] Checking Ollama installation...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       [INFO] Ollama not found
    echo.
    choice /C YN /M "Install Ollama now? (Required for AI models)"
    if !errorlevel! equ 1 (
        echo.
        echo [INFO] Downloading Ollama installer...
        powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'OllamaSetup.exe'"
        
        if exist OllamaSetup.exe (
            echo [INFO] Running Ollama installer...
            start /wait OllamaSetup.exe
            del OllamaSetup.exe
            echo [OK] Ollama installed successfully
        ) else (
            echo [ERROR] Failed to download Ollama installer
            echo        Please install manually from: https://ollama.com
            pause
            exit /b 1
        )
    ) else (
        echo [WARNING] Ollama is required for AI models
        echo           Install from: https://ollama.com
    )
) else (
    echo       [OK] Ollama is installed
)

REM Check for required Python packages
echo [5/7] Checking Python dependencies...
python -c "import psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [INFO] Installing required Python packages...
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo       [WARNING] Some packages may not have installed correctly
    ) else (
        echo       [OK] Python packages installed
    )
) else (
    echo       [OK] Core dependencies found
)

REM Check for model files
echo [6/7] Checking AI models...
ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo       [WARNING] Cannot check models - Ollama not running
    echo [INFO] Starting Ollama service...
    start /min cmd /c "ollama serve"
    timeout /t 3 /nobreak >nul
)

ollama list | findstr /i "sunflower-kids" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [INFO] Sunflower models not found - will download on first run
) else (
    echo       [OK] Sunflower models found
)

REM ============================================================================
REM MAIN MENU
REM ============================================================================

:menu
cls
echo ============================================================
echo           SUNFLOWER AI EDUCATION SYSTEM
echo ============================================================
echo.
echo Select your preferred setup method:
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

REM ============================================================================
REM DOCKER SETUP
REM ============================================================================

:docker_setup
echo.
echo [7/7] Starting Sunflower AI with Docker...
echo.

REM Start services with Docker Compose
if exist "docker-compose.dev.yml" (
    echo [INFO] Starting Docker services...
    docker-compose -f docker-compose.dev.yml up -d
    
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to start Docker services
        echo        Check the error messages above
        pause
        goto menu
    )
    
    echo.
    echo [INFO] Waiting for services to initialize...
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
    echo [INFO] Opening browser in 5 seconds...
    timeout /t 5 /nobreak >nul
    start http://localhost:8080
    
    echo.
    echo Press any key to stop all services...
    pause >nul
    
    echo.
    echo [INFO] Stopping services...
    docker-compose -f docker-compose.dev.yml down
    echo [OK] Services stopped
) else (
    echo [ERROR] docker-compose.dev.yml not found
    echo        Please ensure you're in the Sunflower AI directory
    pause
)
goto end

REM ============================================================================
REM PYTHON SETUP
REM ============================================================================

:python_setup
echo.
echo [7/7] Starting Sunflower AI with Python...
echo.

REM Check if run_local.py exists
if exist "run_local.py" (
    echo [INFO] Launching Sunflower AI...
    python run_local.py
    if !errorlevel! neq 0 (
        echo.
        echo [ERROR] Application exited with errors
        echo        Check the error messages above
        pause
    )
) else (
    echo [ERROR] run_local.py not found
    echo        Please ensure you're in the Sunflower AI directory
    pause
)
goto end

REM ============================================================================
REM MANUAL SETUP
REM ============================================================================

:manual_setup
echo.
echo ============================================================
echo                 MANUAL SETUP INSTRUCTIONS
echo ============================================================
echo.
echo Follow these steps to set up Sunflower AI manually:
echo.
echo STEP 1: Start Ollama service
echo --------------------------------
echo Run in a new terminal:
echo    ollama serve
echo.
echo STEP 2: Load Sunflower models
echo --------------------------------
echo Run these commands:
echo    ollama create sunflower-kids -f modelfiles\sunflower-kids.modelfile
echo    ollama create sunflower-educator -f modelfiles\sunflower-educator.modelfile
echo.
echo STEP 3: Run Open WebUI
echo --------------------------------
echo Option A - With Docker:
echo    docker run -d -p 8080:8080 ghcr.io/open-webui/open-webui:main
echo.
echo Option B - From source:
echo    git clone https://github.com/open-webui/open-webui.git
echo    cd open-webui
echo    python backend\main.py
echo.
echo STEP 4: Open your browser
echo --------------------------------
echo Navigate to: http://localhost:8080
echo.
echo ============================================================
echo.
pause
goto menu

REM ============================================================================
REM EXIT
REM ============================================================================

:end
echo.
echo ============================================================
echo           Thank you for using Sunflower AI!
echo ============================================================
echo.
echo For support and documentation:
echo - Quick Start Guide: docs\QUICK_START.txt
echo - Testing Guide: docs\TESTING_GUIDE.txt
echo - Troubleshooting: logs\sunflower_local.log
echo.
echo Report issues: https://github.com/sunflowerai/issues
echo.
pause
exit /b 0

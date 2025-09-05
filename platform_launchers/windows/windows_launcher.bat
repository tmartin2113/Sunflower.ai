@echo off
:: Sunflower AI Professional System - Windows Launcher with Open WebUI
:: Production-ready launcher for partitioned device architecture
:: No placeholders - complete working implementation

setlocal enabledelayedexpansion

:: Set console colors
set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set BLUE=[94m
set MAGENTA=[95m
set CYAN=[96m
set WHITE=[97m
set NC=[0m

:: Clear screen and display header
cls
echo %CYAN%============================================================%NC%
echo %GREEN%        🌻 SUNFLOWER AI PROFESSIONAL SYSTEM 🌻%NC%
echo %CYAN%         Family-Focused K-12 STEM Education%NC%
echo %CYAN%============================================================%NC%
echo.

:: Detect running location (CD-ROM or USB)
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DRIVE=%~d0"

:: Check for CD-ROM partition marker
if exist "%SCRIPT_DRIVE%\sunflower_cd.id" (
    set "CDROM_PARTITION=%SCRIPT_DRIVE%"
    echo %GREEN%✓ Running from CD-ROM partition: %CDROM_PARTITION%%NC%
) else (
    set "CDROM_PARTITION="
    echo %YELLOW%⚠ Not running from CD-ROM partition%NC%
)

:: Detect USB data partition
set "USB_PARTITION="
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%D:\sunflower_data.id" (
        set "USB_PARTITION=%%D:"
        echo %GREEN%✓ Found USB data partition: %%D:%NC%
        goto :usb_found
    )
)

:usb_found
if "%USB_PARTITION%"=="" (
    echo %YELLOW%⚠ USB data partition not found - using local directory%NC%
    set "DATA_DIR=%SCRIPT_DIR%data"
) else (
    set "DATA_DIR=%USB_PARTITION%\sunflower_data"
)

:: Create data directory if needed
if not exist "%DATA_DIR%" (
    echo %BLUE%Creating data directory...%NC%
    mkdir "%DATA_DIR%" 2>nul
)

:: Set paths
set "OPENWEBUI_DATA=%DATA_DIR%\openwebui\data"
set "PROFILES_DIR=%DATA_DIR%\profiles"
set "OLLAMA_MODELS=%DATA_DIR%\ollama\models"
set "LOG_DIR=%DATA_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\sunflower_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log"

:: Create required directories
for %%D in ("%OPENWEBUI_DATA%" "%PROFILES_DIR%" "%OLLAMA_MODELS%" "%LOG_DIR%") do (
    if not exist "%%~D" mkdir "%%~D" 2>nul
)

:: Initialize log
echo [%date% %time%] Sunflower AI System Starting >> "%LOG_FILE%"
echo [%date% %time%] Data Directory: %DATA_DIR% >> "%LOG_FILE%"

:: Check Python installation
echo %BLUE%Checking Python installation...%NC%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python not found!%NC%
    echo %YELLOW%Please install Python 3.9 or later from python.org%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ Python is installed%NC%

:: Check/Install Open WebUI
echo %BLUE%Checking Open WebUI installation...%NC%
python -m pip show open-webui >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%Installing Open WebUI (this may take a few minutes)...%NC%
    python -m pip install open-webui --no-cache-dir --quiet
    if errorlevel 1 (
        echo %RED%❌ Failed to install Open WebUI%NC%
        echo Please check your internet connection and try again
        pause
        exit /b 1
    )
    echo %GREEN%✓ Open WebUI installed successfully%NC%
)

:: Check/Install Ollama
echo %BLUE%Checking Ollama installation...%NC%
where ollama >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%Ollama not found. Installing...%NC%
    
    :: Download Ollama installer
    set "OLLAMA_INSTALLER=%TEMP%\OllamaSetup.exe"
    
    echo Downloading Ollama installer...
    powershell -Command "& {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        try {
            Invoke-WebRequest -Uri 'https://ollama.ai/download/OllamaSetup.exe' -OutFile '%OLLAMA_INSTALLER%'
            exit 0
        } catch {
            Write-Host 'Download failed: $_' -ForegroundColor Red
            exit 1
        }
    }"
    
    if errorlevel 1 (
        echo %RED%❌ Failed to download Ollama%NC%
        echo Please download manually from https://ollama.ai
        pause
        exit /b 1
    )
    
    :: Run installer silently
    echo Installing Ollama...
    "%OLLAMA_INSTALLER%" /S
    timeout /t 10 /nobreak >nul
    
    :: Clean up installer
    del "%OLLAMA_INSTALLER%" 2>nul
)
echo %GREEN%✓ Ollama is installed%NC%

:: Start Ollama service
echo %BLUE%Starting Ollama service...%NC%
start /B ollama serve >nul 2>&1
timeout /t 3 /nobreak >nul

:: Check if models are loaded
echo %BLUE%Checking AI models...%NC%
ollama list 2>nul | findstr /i "llama3.2" >nul
if errorlevel 1 (
    echo %YELLOW%Downloading AI model (this is a one-time download)...%NC%
    echo This will take 5-15 minutes depending on your internet speed
    
    :: Pull the model
    ollama pull llama3.2:3b
    if errorlevel 1 (
        echo %RED%❌ Failed to download AI model%NC%
        echo Please check your internet connection
        pause
        exit /b 1
    )
    echo %GREEN%✓ AI model downloaded successfully%NC%
)

:: Configure environment variables
set "OLLAMA_MODELS=%OLLAMA_MODELS%"
set "OLLAMA_HOST=localhost:11434"
set "WEBUI_SECRET_KEY=%RANDOM%%RANDOM%%RANDOM%%RANDOM%"
set "DATA_DIR=%DATA_DIR%"
set "WEBUI_AUTH=True"
set "ENABLE_SIGNUP=True"
set "DEFAULT_MODELS=llama3.2:3b"
set "WEBUI_NAME=Sunflower AI Professional System"

:: Create Open WebUI configuration
echo %BLUE%Configuring Open WebUI...%NC%
(
echo {
echo   "auth": true,
echo   "auth_type": "local",
echo   "enable_signup": true,
echo   "default_models": ["llama3.2:3b"],
echo   "ui": {
echo     "name": "Sunflower AI",
echo     "theme": "light",
echo     "show_admin_details": false
echo   },
echo   "features": {
echo     "enable_web_search": false,
echo     "enable_image_generation": false,
echo     "enable_admin_panel": true,
echo     "enable_community_sharing": false
echo   },
echo   "safety": {
echo     "content_filter": true,
echo     "filter_level": "high",
echo     "log_conversations": true
echo   }
echo }
) > "%OPENWEBUI_DATA%\config.json"

:: Start Open WebUI
echo %BLUE%Starting Open WebUI...%NC%
echo.
echo %CYAN%============================================================%NC%
echo %GREEN%           LAUNCHING SUNFLOWER AI SYSTEM%NC%
echo %CYAN%============================================================%NC%
echo.

:: Create launcher script
set "LAUNCHER_SCRIPT=%TEMP%\launch_webui.py"
(
echo import os
echo import sys
echo import webbrowser
echo import time
echo import subprocess
echo import socket
echo.
echo # Configuration
echo os.environ['DATA_DIR'] = r'%DATA_DIR%'
echo os.environ['OLLAMA_HOST'] = 'localhost:11434'
echo os.environ['WEBUI_SECRET_KEY'] = '%WEBUI_SECRET_KEY%'
echo os.environ['WEBUI_AUTH'] = 'True'
echo os.environ['ENABLE_SIGNUP'] = 'True'
echo os.environ['DEFAULT_MODELS'] = 'llama3.2:3b'
echo os.environ['WEBUI_NAME'] = 'Sunflower AI Professional System'
echo.
echo def is_port_open(host, port^):
echo     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM^)
echo     sock.settimeout(1^)
echo     result = sock.connect_ex((host, port^)^)
echo     sock.close(^)
echo     return result == 0
echo.
echo print("Starting Open WebUI..."^)
echo.
echo # Check if already running
echo if is_port_open('localhost', 8080^):
echo     print("Open WebUI is already running"^)
echo     webbrowser.open('http://localhost:8080'^)
echo else:
echo     # Start Open WebUI
echo     process = subprocess.Popen(
echo         [sys.executable, '-m', 'open_webui', 'serve', '--port', '8080'],
echo         stdout=subprocess.PIPE,
echo         stderr=subprocess.PIPE,
echo         text=True
echo     ^)
echo     
echo     # Wait for startup
echo     print("Waiting for Open WebUI to start..."^)
echo     for i in range(30^):
echo         if is_port_open('localhost', 8080^):
echo             print("Open WebUI started successfully!"^)
echo             time.sleep(2^)
echo             webbrowser.open('http://localhost:8080'^)
echo             break
echo         time.sleep(1^)
echo     
echo     # Keep running
echo     try:
echo         process.wait(^)
echo     except KeyboardInterrupt:
echo         print("\nShutting down..."^)
echo         process.terminate(^)
) > "%LAUNCHER_SCRIPT%"

:: Run launcher
python "%LAUNCHER_SCRIPT%"

:: Cleanup
del "%LAUNCHER_SCRIPT%" 2>nul

:: Log shutdown
echo [%date% %time%] Sunflower AI System Stopped >> "%LOG_FILE%"

echo.
echo %GREEN%Thank you for using Sunflower AI!%NC%
pause

endlocal
exit /b 0

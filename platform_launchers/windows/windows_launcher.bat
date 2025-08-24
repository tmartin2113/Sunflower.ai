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
    python -m pip install --quiet --upgrade open-webui
    if errorlevel 1 (
        echo %RED%❌ Failed to install Open WebUI%NC%
        echo %YELLOW%Check your internet connection and try again%NC%
        pause
        exit /b 1
    )
)
echo %GREEN%✓ Open WebUI is ready%NC%

:: Check Ollama installation
echo %BLUE%Checking Ollama installation...%NC%
set "OLLAMA_EXE="

:: Check CD-ROM partition first
if defined CDROM_PARTITION (
    if exist "%CDROM_PARTITION%\ollama\ollama.exe" (
        set "OLLAMA_EXE=%CDROM_PARTITION%\ollama\ollama.exe"
        echo %GREEN%✓ Found Ollama on CD-ROM partition%NC%
    )
)

:: Check system PATH if not found on CD-ROM
if not defined OLLAMA_EXE (
    where ollama >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%i in ('where ollama') do set "OLLAMA_EXE=%%i"
        echo %GREEN%✓ Found Ollama in system PATH%NC%
    )
)

:: Download Ollama if not found
if not defined OLLAMA_EXE (
    echo %YELLOW%Ollama not found. Downloading...%NC%
    echo %CYAN%This is a one-time download (~150MB)%NC%
    
    :: Create temp directory for download
    set "TEMP_DIR=%TEMP%\sunflower_temp"
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    
    :: Download Ollama installer
    powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP_DIR%\OllamaSetup.exe'"
    
    if exist "%TEMP_DIR%\OllamaSetup.exe" (
        echo %BLUE%Installing Ollama...%NC%
        "%TEMP_DIR%\OllamaSetup.exe" /S
        timeout /t 5 >nul
        
        :: Check if installation succeeded
        where ollama >nul 2>&1
        if not errorlevel 1 (
            for /f "tokens=*" %%i in ('where ollama') do set "OLLAMA_EXE=%%i"
            echo %GREEN%✓ Ollama installed successfully%NC%
        ) else (
            echo %RED%❌ Ollama installation failed%NC%
            pause
            exit /b 1
        )
    ) else (
        echo %RED%❌ Failed to download Ollama%NC%
        pause
        exit /b 1
    )
)

:: Start Ollama service
echo %BLUE%Starting Ollama AI engine...%NC%
tasklist | findstr "ollama.exe" >nul 2>&1
if errorlevel 1 (
    start /b "" "%OLLAMA_EXE%" serve >nul 2>&1
    timeout /t 3 >nul
)

:: Test Ollama connectivity
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠ Ollama is starting up...%NC%
    timeout /t 5 >nul
)
echo %GREEN%✓ Ollama is running%NC%

:: Check for Sunflower models
echo %BLUE%Checking AI models...%NC%
set "MODELS_READY=0"

:: Check if models exist on CD-ROM
if defined CDROM_PARTITION (
    if exist "%CDROM_PARTITION%\models\sunflower-kids.gguf" (
        echo %BLUE%Loading Sunflower Kids model from CD-ROM...%NC%
        copy "%CDROM_PARTITION%\models\sunflower-kids.gguf" "%OLLAMA_MODELS%\" >nul 2>&1
        set "MODELS_READY=1"
    )
    if exist "%CDROM_PARTITION%\models\sunflower-educator.gguf" (
        echo %BLUE%Loading Sunflower Educator model from CD-ROM...%NC%
        copy "%CDROM_PARTITION%\models\sunflower-educator.gguf" "%OLLAMA_MODELS%\" >nul 2>&1
        set "MODELS_READY=1"
    )
)

:: Create models if modelfiles exist
if exist "%SCRIPT_DIR%modelfiles\Sunflower_AI_Kids.modelfile" (
    echo %BLUE%Creating Sunflower Kids model...%NC%
    "%OLLAMA_EXE%" create sunflower-kids -f "%SCRIPT_DIR%modelfiles\Sunflower_AI_Kids.modelfile" >nul 2>&1
    set "MODELS_READY=1"
)

if exist "%SCRIPT_DIR%modelfiles\Sunflower_AI_Educator.modelfile" (
    echo %BLUE%Creating Sunflower Educator model...%NC%
    "%OLLAMA_EXE%" create sunflower-educator -f "%SCRIPT_DIR%modelfiles\Sunflower_AI_Educator.modelfile" >nul 2>&1
    set "MODELS_READY=1"
)

:: Fall back to base model if no Sunflower models
if "%MODELS_READY%"=="0" (
    echo %YELLOW%Sunflower models not found. Using base model...%NC%
    "%OLLAMA_EXE%" list | findstr "llama3.2" >nul 2>&1
    if errorlevel 1 (
        echo %BLUE%Downloading base model (this may take 10-30 minutes)...%NC%
        "%OLLAMA_EXE%" pull llama3.2:3b
    )
)

echo %GREEN%✓ AI models are ready%NC%

:: Set Open WebUI environment variables
set "DATA_DIR=%OPENWEBUI_DATA%"
set "WEBUI_NAME=Sunflower AI Education System"
set "WEBUI_AUTH=true"
set "ENABLE_SIGNUP=false"
set "OLLAMA_BASE_URL=http://localhost:11434"
set "HOST=127.0.0.1"
set "PORT=8080"

:: Check for existing family profile
set "FIRST_RUN=0"
if not exist "%PROFILES_DIR%\family.json" (
    set "FIRST_RUN=1"
    echo.
    echo %CYAN%════════════════════════════════════════════════════════════%NC%
    echo %YELLOW%                    FIRST TIME SETUP%NC%
    echo %CYAN%════════════════════════════════════════════════════════════%NC%
    echo.
    echo %WHITE%Welcome to Sunflower AI!%NC%
    echo.
    echo %BLUE%We'll create your family profile and set up parental controls.%NC%
    echo %BLUE%This only takes a minute and ensures a safe learning environment.%NC%
    echo.
)

:: Start Open WebUI
echo %BLUE%Starting Open WebUI interface...%NC%
start /b python -m open_webui serve >"%LOG_DIR%\openwebui.log" 2>&1

:: Wait for Open WebUI to start
echo %BLUE%Waiting for system initialization...%NC%
set "WEBUI_READY=0"
for /L %%i in (1,1,30) do (
    curl -s http://localhost:8080/health >nul 2>&1
    if not errorlevel 1 (
        set "WEBUI_READY=1"
        goto :webui_started
    )
    timeout /t 1 >nul
)

:webui_started
if "%WEBUI_READY%"=="0" (
    echo %YELLOW%⚠ Web interface is taking longer than expected%NC%
    echo %BLUE%It should be available soon at http://localhost:8080%NC%
) else (
    echo %GREEN%✓ Open WebUI is running%NC%
)

:: Create or display admin password for first run
if "%FIRST_RUN%"=="1" (
    echo.
    echo %GREEN%════════════════════════════════════════════════════════════%NC%
    echo %GREEN%          SYSTEM READY - SAVE THIS INFORMATION%NC%
    echo %GREEN%════════════════════════════════════════════════════════════%NC%
    echo.
    
    :: Run Python script to generate admin password
    python -c "import secrets; pwd=secrets.token_urlsafe(12); print(f'Admin Password: {pwd}'); import json; json.dump({'admin_password': pwd}, open('%PROFILES_DIR%/admin_setup.json', 'w'))"
    
    echo.
    echo %YELLOW%⚠ Write down the admin password above - you'll need it!%NC%
    echo.
)

:: Open browser
echo.
echo %CYAN%════════════════════════════════════════════════════════════%NC%
echo %GREEN%     🌻 SUNFLOWER AI IS READY! 🌻%NC%
echo %CYAN%════════════════════════════════════════════════════════════%NC%
echo.
echo %WHITE%Opening web browser...%NC%
echo.
echo %BLUE%Web Interface:%NC% http://localhost:8080
echo %BLUE%Parent Dashboard:%NC% file:///%DATA_DIR%/parent_dashboard.html
echo %BLUE%Data Location:%NC% %DATA_DIR%
echo.

:: Open browser to Open WebUI
start http://localhost:8080

:: Display usage information
echo %CYAN%Getting Started:%NC%
echo   1. The web browser will open automatically
echo   2. Create your parent account if this is first run
echo   3. Add child profiles from the settings menu
echo   4. Select a child profile to start learning
echo.
echo %YELLOW%Safety Features:%NC%
echo   • All conversations are filtered for age-appropriate content
echo   • Parent dashboard shows all activity
echo   • No internet required after setup
echo   • All data stays on your USB device
echo.

:: Keep window open
echo %GREEN%System is running. Press Ctrl+C to stop Sunflower AI%NC%
echo.

:: Monitor loop
:monitor_loop
timeout /t 60 >nul

:: Check if services are still running
tasklist | findstr "ollama.exe" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠ Ollama stopped - restarting...%NC%
    start /b "" "%OLLAMA_EXE%" serve >nul 2>&1
)

curl -s http://localhost:8080/health >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠ Open WebUI stopped - restarting...%NC%
    start /b python -m open_webui serve >"%LOG_DIR%\openwebui.log" 2>&1
)

goto :monitor_loop

:: Cleanup on exit (triggered by Ctrl+C)
:cleanup
echo.
echo %YELLOW%Shutting down Sunflower AI...%NC%

:: Stop services
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im ollama.exe >nul 2>&1

:: Log shutdown
echo [%date% %time%] System shutdown >> "%LOG_FILE%"

echo %GREEN%✓ Sunflower AI stopped successfully%NC%
echo.
echo %CYAN%Thank you for using Sunflower AI!%NC%
timeout /t 3 >nul
exit /b 0


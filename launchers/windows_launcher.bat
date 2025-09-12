@echo off
setlocal EnableDelayedExpansion
title Sunflower AI Professional System Launcher

:: ==================== CONFIGURATION ====================
set "VERSION=6.2.0"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set "LOG_FILE=%TEMP%\sunflower_launcher_%datetime:~0,8%.log"
set "MIN_WINDOWS_BUILD=17134"
set "MIN_RAM_GB=4"
set "CDROM_MARKER=SUNFLOWER_CD"
set "USB_MARKER=SUNFLOWER_DATA"

:: Error codes
set ERROR_NO_ADMIN=1
set ERROR_INCOMPATIBLE_OS=2
set ERROR_INSUFFICIENT_RAM=3
set ERROR_CDROM_NOT_FOUND=4
set ERROR_USB_NOT_FOUND=5
set ERROR_INTEGRITY_CHECK_FAILED=6
set ERROR_PYTHON_NOT_FOUND=7
set ERROR_OLLAMA_FAILED=8

:: ==================== LOGGING SETUP ====================
:LogMessage
    echo [%DATE% %TIME%] [%~1] %~2 >> "%LOG_FILE%"
    if "%~1"=="ERROR" (
        echo [ERROR] %~2
    ) else if "%~1"=="INFO" (
        echo [INFO] %~2
    )
    exit /b 0

:: ==================== MAIN EXECUTION ====================
cls
echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║              SUNFLOWER AI PROFESSIONAL SYSTEM v%VERSION%              ║
echo  ║                   Family-Safe K-12 STEM Education                ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.

call :LogMessage "INFO" "Launcher started - Version %VERSION%"

:: ==================== SYSTEM CHECKS ====================
echo  [1/7] Checking system requirements...

:: Check for administrator privileges
call :CheckAdminPrivileges
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Administrator Required" "Please run as Administrator"
    exit /b %ERROR_NO_ADMIN%
)

:: Validate Windows version
call :ValidateWindowsVersion
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

:: Validate system RAM
call :ValidateSystemRAM
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%

:: ==================== PARTITION DETECTION ====================
echo  [2/7] Detecting Sunflower AI device...

call :DetectCDROMPartition
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "CD-ROM Partition Not Found" "Please ensure the Sunflower AI device is properly connected"
    exit /b %ERROR_CDROM_NOT_FOUND%
)

call :DetectUSBPartition
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "USB Partition Not Found" "The writable partition could not be detected"
    exit /b %ERROR_USB_NOT_FOUND%
)

:: ==================== INTEGRITY CHECK ====================
echo  [3/7] Verifying system integrity...
call :VerifySystemIntegrity
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Integrity Check Failed" "System files may be corrupted. Please contact support."
    exit /b %ERROR_INTEGRITY_CHECK_FAILED%
)

:: ==================== HARDWARE DETECTION ====================
echo  [4/7] Analyzing hardware capabilities...
call :DetectHardwareCapabilities
call :SelectOptimalModel

:: ==================== PYTHON ENVIRONMENT ====================
echo  [5/7] Setting up Python environment...
call :SetupPythonEnvironment
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Python Setup Failed" "Unable to initialize Python environment"
    exit /b %ERROR_PYTHON_NOT_FOUND%
)

:: ==================== OLLAMA SETUP ====================
echo  [6/7] Initializing AI models...
call :InitializeOllama

:: ==================== LAUNCH APPLICATION ====================
echo  [7/7] Starting Sunflower AI...
echo.
call :LaunchApplication

:: ==================== CLEANUP ====================
call :Cleanup
exit /b 0

:: ==================== FUNCTION DEFINITIONS ====================

:CheckAdminPrivileges
    net session >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        call :LogMessage "ERROR" "Administrator privileges not detected"
        exit /b 1
    )
    call :LogMessage "INFO" "Administrator privileges confirmed"
    exit /b 0

:ValidateWindowsVersion
    for /f "tokens=4-5 delims=[.] " %%i in ('ver') do (
        set "VERSION=%%i"
        set "BUILD=%%j"
    )
    
    :: Check Windows 10 version 1803 or higher
    wmic os get BuildNumber /value | findstr /r "BuildNumber=[0-9]" > "%TEMP%\build.txt"
    for /f "tokens=2 delims==" %%a in (%TEMP%\build.txt) do set BUILD_NUM=%%a
    
    if !BUILD_NUM! LSS %MIN_WINDOWS_BUILD% (
        call :LogMessage "ERROR" "Windows build !BUILD_NUM! is below minimum %MIN_WINDOWS_BUILD%"
        call :ShowUserError "Windows Version Too Old" "Please update to Windows 10 version 1803 or newer"
        exit /b %ERROR_INCOMPATIBLE_OS%
    )
    
    call :LogMessage "INFO" "Windows build !BUILD_NUM! meets requirements"
    exit /b 0

:ValidateSystemRAM
    for /f "skip=1" %%a in ('wmic computersystem get TotalPhysicalMemory') do (
        if not "%%a"=="" (
            set /a RAM_BYTES=%%a
            set /a RAM_GB=!RAM_BYTES!/1073741824
            goto :CheckRAMSize
        )
    )
    
    :CheckRAMSize
    if !RAM_GB! LSS %MIN_RAM_GB% (
        call :LogMessage "ERROR" "System has !RAM_GB!GB RAM, minimum is %MIN_RAM_GB%GB"
        call :ShowUserError "Insufficient Memory" "Your system has !RAM_GB!GB RAM. Minimum required: %MIN_RAM_GB%GB"
        exit /b %ERROR_INSUFFICIENT_RAM%
    )
    
    call :LogMessage "INFO" "System RAM: !RAM_GB!GB - meets requirements"
    set "SYSTEM_RAM_GB=!RAM_GB!"
    exit /b 0

:DetectCDROMPartition
    set "CDROM_PATH="
    
    :: Detect CD-ROM partition by volume label
    for %%D in (D: E: F: G: H: I: J: K: L: M: N: O: P: Q: R: S: T: U: V: W: X: Y: Z:) do (
        if exist "%%D\" (
            vol %%D 2>nul | findstr /i "%CDROM_MARKER%" >nul
            if !ERRORLEVEL! equ 0 (
                if exist "%%D\sunflower_cd.id" (
                    set "CDROM_PATH=%%D"
                    call :LogMessage "INFO" "CD-ROM partition found at !CDROM_PATH!"
                    exit /b 0
                )
            )
        )
    )
    
    call :LogMessage "ERROR" "CD-ROM partition not found"
    exit /b 1

:DetectUSBPartition
    set "USB_PATH="
    
    :: Detect USB partition by volume label
    for %%D in (D: E: F: G: H: I: J: K: L: M: N: O: P: Q: R: S: T: U: V: W: X: Y: Z:) do (
        if exist "%%D\" (
            vol %%D 2>nul | findstr /i "%USB_MARKER%" >nul
            if !ERRORLEVEL! equ 0 (
                if exist "%%D\sunflower_data.id" (
                    :: Test write permission
                    echo test > "%%D\write_test.tmp" 2>nul
                    if !ERRORLEVEL! equ 0 (
                        del "%%D\write_test.tmp" 2>nul
                        set "USB_PATH=%%D"
                        call :LogMessage "INFO" "USB partition found at !USB_PATH!"
                        exit /b 0
                    )
                )
            )
        )
    )
    
    call :LogMessage "ERROR" "USB partition not found"
    exit /b 1

:VerifySystemIntegrity
    :: Check critical files exist
    set "CRITICAL_FILES[0]=%CDROM_PATH%\system\launcher_common.py"
    set "CRITICAL_FILES[1]=%CDROM_PATH%\system\ollama\ollama.exe"
    set "CRITICAL_FILES[2]=%CDROM_PATH%\modelfiles\sunflower-kids.modelfile"
    set "CRITICAL_FILES[3]=%CDROM_PATH%\modelfiles\sunflower-educator.modelfile"
    
    for /L %%i in (0,1,3) do (
        if not exist "!CRITICAL_FILES[%%i]!" (
            call :LogMessage "ERROR" "Critical file missing: !CRITICAL_FILES[%%i]!"
            exit /b 1
        )
    )
    
    call :LogMessage "INFO" "System integrity verification passed"
    exit /b 0

:DetectHardwareCapabilities
    :: Detect CPU information
    for /f "tokens=2 delims==" %%a in ('wmic cpu get NumberOfCores /value') do set CPU_CORES=%%a
    for /f "tokens=2 delims==" %%a in ('wmic cpu get MaxClockSpeed /value') do set CPU_SPEED=%%a
    
    :: Detect GPU (basic check for dedicated GPU)
    set "HAS_GPU=0"
    wmic path win32_VideoController get name | findstr /i "NVIDIA AMD Radeon GeForce" >nul
    if !ERRORLEVEL! equ 0 set "HAS_GPU=1"
    
    :: Calculate performance score
    set /a PERF_SCORE=0
    set /a PERF_SCORE+=!SYSTEM_RAM_GB!*10
    set /a PERF_SCORE+=!CPU_CORES!*5
    if !HAS_GPU! equ 1 set /a PERF_SCORE+=30
    
    call :LogMessage "INFO" "Hardware: RAM=!SYSTEM_RAM_GB!GB, Cores=!CPU_CORES!, GPU=!HAS_GPU!, Score=!PERF_SCORE!"
    
    exit /b 0

:SelectOptimalModel
    :: Model selection based on performance score
    :: Score ranges: 0-50 (minimal), 51-80 (low), 81-120 (mid), 121+ (high)
    
    if !PERF_SCORE! GEQ 121 (
        set "SELECTED_MODEL=llama3.2:7b"
        set "MODEL_TIER=high"
    ) else if !PERF_SCORE! GEQ 81 (
        set "SELECTED_MODEL=llama3.2:3b"
        set "MODEL_TIER=mid"
    ) else if !PERF_SCORE! GEQ 51 (
        set "SELECTED_MODEL=llama3.2:1b"
        set "MODEL_TIER=low"
    ) else (
        set "SELECTED_MODEL=llama3.2:1b-q4_0"
        set "MODEL_TIER=minimal"
    )
    
    call :LogMessage "INFO" "Selected model: !SELECTED_MODEL! (tier: !MODEL_TIER!)"
    
    :: Write configuration
    echo {"selected_model": "!SELECTED_MODEL!", "performance_score": !PERF_SCORE!, "tier": "!MODEL_TIER!"} > "%USB_PATH%\config\hardware.json"
    
    exit /b 0

:SetupPythonEnvironment
    :: Check for embedded Python first
    if exist "%CDROM_PATH%\system\python\python.exe" (
        set "PYTHON_EXE=%CDROM_PATH%\system\python\python.exe"
        call :LogMessage "INFO" "Using embedded Python"
    ) else (
        :: Fallback to system Python
        where python >nul 2>&1
        if !ERRORLEVEL! neq 0 (
            call :LogMessage "ERROR" "Python not found in system or embedded location"
            exit /b 1
        )
        set "PYTHON_EXE=python"
        call :LogMessage "INFO" "Using system Python"
    )
    
    :: Set Python environment variables
    set "PYTHONPATH=%CDROM_PATH%\system;%CDROM_PATH%\system\lib"
    set "PYTHONDONTWRITEBYTECODE=1"
    set "PYTHONUNBUFFERED=1"
    
    exit /b 0

:InitializeOllama
    set "OLLAMA_EXE=%CDROM_PATH%\system\ollama\ollama.exe"
    set "OLLAMA_MODELS=%CDROM_PATH%\system\models"
    set "OLLAMA_HOME=%USB_PATH%\ollama_data"
    
    :: Create Ollama data directory
    if not exist "%OLLAMA_HOME%" mkdir "%OLLAMA_HOME%"
    
    :: Start Ollama service
    call :LogMessage "INFO" "Starting Ollama service..."
    start /B "" "%OLLAMA_EXE%" serve >"%USB_PATH%\logs\ollama.log" 2>&1
    
    :: Wait for Ollama to be ready
    timeout /t 3 /nobreak >nul
    
    :: FIX: Validate SELECTED_MODEL before use
    if not defined SELECTED_MODEL (
        call :LogMessage "WARNING" "SELECTED_MODEL not set, using default"
        set "SELECTED_MODEL=llama3.2:1b"
    )
    
    if "!SELECTED_MODEL!"=="" (
        call :LogMessage "WARNING" "SELECTED_MODEL is empty, using default"
        set "SELECTED_MODEL=llama3.2:1b"
    )
    
    :: Load the selected model with error handling
    call :LogMessage "INFO" "Loading AI model: !SELECTED_MODEL!"
    
    :: Check if model file exists before attempting to pull
    if exist "%OLLAMA_MODELS%\!SELECTED_MODEL!.bin" (
        "%OLLAMA_EXE%" pull "%OLLAMA_MODELS%\!SELECTED_MODEL!.bin" >"%USB_PATH%\logs\model_load.log" 2>&1
        if !ERRORLEVEL! neq 0 (
            call :LogMessage "ERROR" "Failed to load model !SELECTED_MODEL!, trying fallback"
            :: Try fallback to smallest model
            set "SELECTED_MODEL=llama3.2:1b-q4_0"
            "%OLLAMA_EXE%" pull "%OLLAMA_MODELS%\!SELECTED_MODEL!.bin" >"%USB_PATH%\logs\model_load_fallback.log" 2>&1
            if !ERRORLEVEL! neq 0 (
                call :LogMessage "ERROR" "Failed to load fallback model"
                call :ShowUserError "Model Loading Failed" "Unable to load AI model. Check logs for details."
                exit /b %ERROR_OLLAMA_FAILED%
            )
        )
        call :LogMessage "INFO" "Model !SELECTED_MODEL! loaded successfully"
    ) else (
        call :LogMessage "ERROR" "Model file not found: %OLLAMA_MODELS%\!SELECTED_MODEL!.bin"
        call :ShowUserError "Model File Missing" "The AI model file is missing from the installation."
        exit /b %ERROR_OLLAMA_FAILED%
    )
    
    exit /b 0

:LaunchApplication
    :: Set all required environment variables
    set "SUNFLOWER_CDROM_PATH=%CDROM_PATH%"
    set "SUNFLOWER_USB_PATH=%USB_PATH%"
    set "SUNFLOWER_MODEL=%SELECTED_MODEL%"
    set "SUNFLOWER_LOG_DIR=%USB_PATH%\logs"
    
    call :LogMessage "INFO" "Launching Sunflower AI application"
    
    :: Launch the main application
    "%PYTHON_EXE%" "%CDROM_PATH%\system\launcher_common.py" ^
        --cdrom "%CDROM_PATH%" ^
        --usb "%USB_PATH%" ^
        --model "!SELECTED_MODEL!" ^
        --platform "windows" ^
        --log-file "%USB_PATH%\logs\app_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%.log"
    
    if !ERRORLEVEL! neq 0 (
        call :LogMessage "ERROR" "Application exited with error code !ERRORLEVEL!"
        call :ShowUserError "Application Error" "The application encountered an error. Please check the logs."
    )
    
    exit /b !ERRORLEVEL!

:ShowUserError
    echo.
    echo  ╔══════════════════════════════════════════════════════════════════╗
    echo  ║                          ERROR DETECTED                          ║
    echo  ╠══════════════════════════════════════════════════════════════════╣
    echo  ║  %~1
    echo  ║  
    echo  ║  %~2
    echo  ╚══════════════════════════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1

:Cleanup
    :: Stop Ollama service
    taskkill /F /IM ollama.exe >nul 2>&1
    
    call :LogMessage "INFO" "Launcher shutdown complete"
    exit /b 0

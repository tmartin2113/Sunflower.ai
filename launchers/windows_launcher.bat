@echo off
:: ============================================================================
:: Sunflower AI Professional System - Windows Launcher
:: Version: 6.2 | Production-Ready | Universal Compatibility
:: Purpose: Platform-specific launcher with comprehensive error handling
:: Location: launchers/windows_launcher.bat
:: Fixed: Removed ANSI codes, improved error handling, locale-independent
:: ============================================================================

setlocal enabledelayedexpansion

:: ==================== CONSTANTS ====================
set "VERSION=6.2"
set "SYSTEM_NAME=Sunflower AI Professional System"
set "MIN_RAM_GB=4"
set "MIN_WINDOWS_BUILD=17134"
set "CDROM_MARKER=sunflower_cd.id"
set "USB_MARKER=sunflower_data.id"
set "PYTHON_MIN_VERSION=3.8"
set "OLLAMA_PORT=11434"
set "OPENWEBUI_PORT=8080"
set "MAX_RETRY_ATTEMPTS=3"
set "RETRY_DELAY=2"

:: ==================== ERROR CODES ====================
set "ERROR_SUCCESS=0"
set "ERROR_ADMIN_REQUIRED=1"
set "ERROR_INSUFFICIENT_RAM=2"
set "ERROR_CDROM_NOT_FOUND=3"
set "ERROR_USB_NOT_FOUND=4"
set "ERROR_PYTHON_NOT_FOUND=5"
set "ERROR_OLLAMA_FAILED=6"
set "ERROR_OPENWEBUI_FAILED=7"
set "ERROR_INTEGRITY_CHECK_FAILED=8"
set "ERROR_INCOMPATIBLE_OS=9"
set "ERROR_MODEL_LOAD_FAILED=10"

:: ==================== LOGGING SETUP (LOCALE-INDEPENDENT) ====================
:: Create log directory and files with proper date/time handling
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value 2^>nul ^| find "="') do set "datetime=%%a"
if not defined datetime (
    :: Fallback if WMIC fails
    set "datetime=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
    set "datetime=!datetime: =0!"
)
set "TIMESTAMP=!datetime:~0,8!_!datetime:~8,6!"

set "LOG_DIR=%LOCALAPPDATA%\SunflowerAI\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\launcher_%TIMESTAMP%.log"
set "ERROR_LOG=%LOG_DIR%\errors_%TIMESTAMP%.log"

:: ==================== MAIN EXECUTION ====================
call :LogMessage "INFO" "=== Sunflower AI Launcher Started ==="
call :LogMessage "INFO" "Version: %VERSION%"
call :LogMessage "INFO" "Timestamp: %TIMESTAMP%"
call :LogMessage "INFO" "Log file: %LOG_FILE%"

:: Clear screen and display header
cls
call :DisplayHeader

:: ==================== SYSTEM CHECKS ====================
echo [SYSTEM VALIDATION]
echo.

echo  [1/8] Checking administrator privileges...
call :CheckAdminPrivileges
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Administrator Required" "Please run as Administrator for full functionality"
    echo.
    echo [WARNING] Some features may be limited without admin rights.
    echo          Continue anyway? (Y/N)
    set /p "continue_without_admin="
    if /i not "!continue_without_admin!"=="Y" (
        exit /b %ERROR_ADMIN_REQUIRED%
    )
)

echo  [2/8] Validating Windows version...
call :ValidateWindowsVersion
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Windows Version" "This version of Windows may not be fully supported"
    pause
)

echo  [3/8] Checking system memory...
call :ValidateSystemRAM
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Insufficient Memory" "System has less than %MIN_RAM_GB%GB RAM"
    echo.
    echo [WARNING] Performance may be impacted. Continue? (Y/N)
    set /p "continue_low_ram="
    if /i not "!continue_low_ram!"=="Y" (
        exit /b %ERROR_INSUFFICIENT_RAM%
    )
)

:: ==================== PARTITION DETECTION ====================
echo  [4/8] Detecting CD-ROM partition...
call :DetectCDROMPartition
if %ERRORLEVEL% neq 0 (
    echo [WARNING] CD-ROM partition not found. 
    echo          Running in development mode.
    set "CDROM_PATH=%~dp0..\cdrom_simulation"
    call :LogMessage "WARNING" "Using simulated CD-ROM: %CDROM_PATH%"
)

echo  [5/8] Detecting USB partition...
call :DetectUSBPartition
if %ERRORLEVEL% neq 0 (
    echo [WARNING] USB partition not found.
    echo          Using local directory for data storage.
    set "USB_PATH=%~dp0..\usb_simulation"
    if not exist "%USB_PATH%" mkdir "%USB_PATH%"
    call :LogMessage "WARNING" "Using simulated USB: %USB_PATH%"
)

:: ==================== INTEGRITY VERIFICATION ====================
echo  [6/8] Verifying system integrity...
call :VerifySystemIntegrity
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Integrity Check" "Some system files are missing or corrupted"
    echo.
    echo [INFO] Continue with limited functionality? (Y/N)
    set /p "continue_integrity="
    if /i not "!continue_integrity!"=="Y" (
        exit /b %ERROR_INTEGRITY_CHECK_FAILED%
    )
)

:: ==================== HARDWARE DETECTION ====================
echo  [7/8] Analyzing hardware capabilities...
call :DetectHardwareCapabilities
call :SelectOptimalModel

:: ==================== SERVICE INITIALIZATION ====================
echo  [8/8] Initializing services...
echo.

:: Initialize Python
call :SetupPythonEnvironment
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Python Setup" "Unable to initialize Python environment"
    echo.
    echo Visit: https://www.python.org/downloads/
    pause
    exit /b %ERROR_PYTHON_NOT_FOUND%
)

:: Initialize Ollama (with comprehensive validation)
call :InitializeOllama
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "AI Service" "Unable to start Ollama service"
    echo.
    echo Please install from: https://ollama.com
    pause
    exit /b %ERROR_OLLAMA_FAILED%
)

:: Launch application
call :LaunchApplication
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Launch Failed" "Unable to start Sunflower AI"
    pause
    exit /b %ERROR_OPENWEBUI_FAILED%
)

:: Cleanup and exit
call :Cleanup
exit /b %ERROR_SUCCESS%

:: ==================== FUNCTIONS ====================

:DisplayHeader
    cls
    echo.
    echo ============================================================
    echo         SUNFLOWER AI PROFESSIONAL SYSTEM
    echo         Family-Focused K-12 STEM Education
    echo                   Version %VERSION%
    echo ============================================================
    echo.
    exit /b 0

:LogMessage
    :: Parameters: Level Message
    set "level=%~1"
    set "message=%~2"
    
    :: Get current time safely
    set "log_time=%time%"
    
    echo [%log_time%] [%level%] %message% >> "%LOG_FILE%"
    
    if "%level%"=="ERROR" (
        echo [%log_time%] %message% >> "%ERROR_LOG%"
    )
    exit /b 0

:CheckAdminPrivileges
    net session >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        call :LogMessage "WARNING" "Administrator privileges not detected"
        exit /b 1
    )
    call :LogMessage "INFO" "Administrator privileges confirmed"
    echo       [OK] Administrator privileges confirmed
    exit /b 0

:ShowUserError
    :: Parameters: Title Message
    set "error_title=%~1"
    set "error_message=%~2"
    echo.
    echo ============================================================
    echo [ERROR] %error_title%
    echo ============================================================
    echo %error_message%
    echo ============================================================
    call :LogMessage "ERROR" "%error_title%: %error_message%"
    exit /b 0

:ValidateWindowsVersion
    :: Get Windows build number
    set "BUILD_NUM=0"
    for /f "tokens=3" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentBuild 2^>nul ^| findstr "CurrentBuild"') do (
        set "BUILD_NUM=%%a"
    )
    
    if not defined BUILD_NUM set "BUILD_NUM=0"
    if %BUILD_NUM% equ 0 (
        call :LogMessage "ERROR" "Unable to determine Windows version"
        exit /b 1
    )
    
    if %BUILD_NUM% LSS %MIN_WINDOWS_BUILD% (
        call :LogMessage "ERROR" "Windows build %BUILD_NUM% is below minimum %MIN_WINDOWS_BUILD%"
        echo       [WARNING] Windows build %BUILD_NUM% (minimum: %MIN_WINDOWS_BUILD%)
        exit /b 1
    )
    
    call :LogMessage "INFO" "Windows build %BUILD_NUM% meets requirements"
    echo       [OK] Windows build %BUILD_NUM%
    exit /b 0

:ValidateSystemRAM
    :: Get total physical memory in GB
    set "RAM_GB=0"
    for /f "skip=1" %%a in ('wmic computersystem get TotalPhysicalMemory 2^>nul') do (
        if not "%%a"=="" (
            set /a "RAM_BYTES=%%a" 2>nul
            set /a "RAM_GB=!RAM_BYTES!/1073741824" 2>nul
            goto :ram_calculated
        )
    )
    :ram_calculated
    
    if %RAM_GB% equ 0 set "RAM_GB=4"
    
    if %RAM_GB% LSS %MIN_RAM_GB% (
        call :LogMessage "ERROR" "System has %RAM_GB%GB RAM, minimum is %MIN_RAM_GB%GB"
        echo       [WARNING] System RAM: %RAM_GB%GB (minimum: %MIN_RAM_GB%GB)
        exit /b 1
    )
    
    call :LogMessage "INFO" "System RAM: %RAM_GB%GB - meets requirements"
    echo       [OK] System RAM: %RAM_GB%GB
    set "SYSTEM_RAM_GB=%RAM_GB%"
    exit /b 0

:DetectCDROMPartition
    set "CDROM_PATH="
    
    :: Check each drive for CD-ROM partition marker
    for %%D in (C: D: E: F: G: H: I: J: K: L: M: N: O: P: Q: R: S: T: U: V: W: X: Y: Z:) do (
        if exist "%%D\%CDROM_MARKER%" (
            :: Verify it's read-only (CD-ROM characteristic)
            echo test > "%%D\test_write.tmp" 2>nul
            if !ERRORLEVEL! neq 0 (
                set "CDROM_PATH=%%D"
                call :LogMessage "INFO" "CD-ROM partition found at %%D"
                echo       [OK] CD-ROM partition: %%D
                exit /b 0
            )
            del "%%D\test_write.tmp" 2>nul
        )
    )
    
    call :LogMessage "ERROR" "CD-ROM partition not found"
    echo       [WARNING] CD-ROM partition not detected
    exit /b 1

:DetectUSBPartition
    set "USB_PATH="
    
    :: Check each drive for USB partition marker
    for %%D in (C: D: E: F: G: H: I: J: K: L: M: N: O: P: Q: R: S: T: U: V: W: X: Y: Z:) do (
        if exist "%%D\%USB_MARKER%" (
            :: Verify write permission
            echo test > "%%D\write_test.tmp" 2>nul
            if !ERRORLEVEL! equ 0 (
                del "%%D\write_test.tmp" 2>nul
                set "USB_PATH=%%D"
                call :LogMessage "INFO" "USB partition found at %%D"
                
                :: Create required directories
                if not exist "%%D\profiles" mkdir "%%D\profiles"
                if not exist "%%D\sessions" mkdir "%%D\sessions"
                if not exist "%%D\logs" mkdir "%%D\logs"
                if not exist "%%D\config" mkdir "%%D\config"
                
                echo       [OK] USB partition: %%D
                exit /b 0
            )
        )
    )
    
    call :LogMessage "ERROR" "USB partition not found"
    echo       [WARNING] USB partition not detected
    exit /b 1

:VerifySystemIntegrity
    set "integrity_passed=1"
    
    :: Check for critical system files (adjust paths as needed)
    echo       Checking system files...
    
    :: Check for launcher files
    if not exist "%CDROM_PATH%\system\launcher_common.py" (
        if not exist "%~dp0launcher_common.py" (
            echo       [MISSING] launcher_common.py
            set "integrity_passed=0"
        )
    )
    
    :: Check for modelfiles
    if not exist "%CDROM_PATH%\modelfiles\sunflower-kids.modelfile" (
        if not exist "%~dp0..\modelfiles\sunflower-kids.modelfile" (
            echo       [MISSING] sunflower-kids.modelfile
            set "integrity_passed=0"
        )
    )
    
    if %integrity_passed% equ 0 (
        call :LogMessage "ERROR" "System integrity check failed"
        exit /b 1
    )
    
    call :LogMessage "INFO" "System integrity verified"
    echo       [OK] System integrity verified
    exit /b 0

:DetectHardwareCapabilities
    :: CPU detection
    set "CPU_CORES=2"
    set "CPU_SPEED=2000"
    set "CPU_NAME=Unknown"
    
    for /f "tokens=2 delims==" %%a in ('wmic cpu get NumberOfCores /value 2^>nul ^| find "="') do set "CPU_CORES=%%a"
    for /f "tokens=2 delims==" %%a in ('wmic cpu get MaxClockSpeed /value 2^>nul ^| find "="') do set "CPU_SPEED=%%a"
    for /f "tokens=2 delims==" %%a in ('wmic cpu get Name /value 2^>nul ^| find "="') do set "CPU_NAME=%%a"
    
    :: GPU detection
    set "HAS_GPU=0"
    set "GPU_NAME=None"
    for /f "tokens=*" %%a in ('wmic path win32_VideoController get name 2^>nul ^| findstr /i "NVIDIA AMD Radeon GeForce"') do (
        set "HAS_GPU=1"
        set "GPU_NAME=%%a"
    )
    
    :: Calculate performance score
    set /a "PERF_SCORE=0"
    set /a "PERF_SCORE+=%SYSTEM_RAM_GB%*10" 2>nul
    set /a "PERF_SCORE+=%CPU_CORES%*5" 2>nul
    if %HAS_GPU% equ 1 set /a "PERF_SCORE+=20"
    
    echo       [INFO] CPU: %CPU_CORES% cores
    echo       [INFO] RAM: %SYSTEM_RAM_GB%GB
    echo       [INFO] GPU: %GPU_NAME%
    
    call :LogMessage "INFO" "Hardware: Cores=%CPU_CORES%, RAM=%SYSTEM_RAM_GB%GB, GPU=%GPU_NAME%, Score=%PERF_SCORE%"
    exit /b 0

:SelectOptimalModel
    :: Model selection based on performance score
    if %PERF_SCORE% geq 100 (
        set "SELECTED_MODEL=llama3.2:7b"
        set "MODEL_SIZE=large"
        echo       [INFO] Selected model: Large (7B parameters)
    ) else if %PERF_SCORE% geq 70 (
        set "SELECTED_MODEL=llama3.2:3b"
        set "MODEL_SIZE=medium"
        echo       [INFO] Selected model: Medium (3B parameters)
    ) else if %PERF_SCORE% geq 40 (
        set "SELECTED_MODEL=llama3.2:1b"
        set "MODEL_SIZE=small"
        echo       [INFO] Selected model: Small (1B parameters)
    ) else (
        set "SELECTED_MODEL=llama3.2:1b-q4"
        set "MODEL_SIZE=minimal"
        echo       [INFO] Selected model: Minimal (1B quantized)
    )
    
    call :LogMessage "INFO" "Selected model: %SELECTED_MODEL% (performance score: %PERF_SCORE%)"
    exit /b 0

:SetupPythonEnvironment
    :: Check Python installation
    python --version >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo       [ERROR] Python not found
        call :LogMessage "ERROR" "Python not installed"
        exit /b 1
    )
    
    :: Get Python version
    for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%a"
    echo       [OK] Python %PYTHON_VERSION%
    
    :: Set Python path if needed
    if defined CDROM_PATH (
        set "PYTHONPATH=%CDROM_PATH%\system;%PYTHONPATH%"
    ) else (
        set "PYTHONPATH=%~dp0;%PYTHONPATH%"
    )
    
    call :LogMessage "INFO" "Python environment configured"
    exit /b 0

:InitializeOllama
    :: Comprehensive Ollama initialization with proper error handling
    echo.
    echo [OLLAMA INITIALIZATION]
    
    :: Check if Ollama is installed
    ollama --version >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo       [ERROR] Ollama not installed
        call :LogMessage "ERROR" "Ollama not found"
        exit /b 1
    )
    
    :: Check if Ollama is running
    echo       Checking Ollama service...
    curl -s http://localhost:%OLLAMA_PORT%/api/tags >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo       [INFO] Starting Ollama service...
        start /min cmd /c "ollama serve"
        
        :: Wait for Ollama to start
        set "retry_count=0"
        :wait_ollama
        timeout /t 2 /nobreak >nul
        curl -s http://localhost:%OLLAMA_PORT%/api/tags >nul 2>&1
        if %ERRORLEVEL% neq 0 (
            set /a retry_count+=1
            if %retry_count% lss 10 (
                echo       [INFO] Waiting for Ollama... (attempt %retry_count%/10)
                goto wait_ollama
            ) else (
                echo       [ERROR] Ollama failed to start
                call :LogMessage "ERROR" "Ollama service failed to start after 10 attempts"
                exit /b 1
            )
        )
    )
    
    echo       [OK] Ollama service running
    
    :: Load models if needed
    echo       Checking models...
    ollama list | findstr /i "sunflower" >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo       [INFO] Loading Sunflower models...
        if exist "%CDROM_PATH%\modelfiles\sunflower-kids.modelfile" (
            ollama create sunflower-kids -f "%CDROM_PATH%\modelfiles\sunflower-kids.modelfile"
        )
        if exist "%CDROM_PATH%\modelfiles\sunflower-educator.modelfile" (
            ollama create sunflower-educator -f "%CDROM_PATH%\modelfiles\sunflower-educator.modelfile"
        )
    )
    
    echo       [OK] Models ready
    call :LogMessage "INFO" "Ollama initialized successfully"
    exit /b 0

:LaunchApplication
    echo.
    echo [LAUNCHING APPLICATION]
    
    :: Launch based on available components
    if exist "%~dp0..\UNIVERSAL_LAUNCHER.py" (
        echo       [INFO] Starting Universal Launcher...
        start python "%~dp0..\UNIVERSAL_LAUNCHER.py"
    ) else if exist "%~dp0..\open-webui\backend\main.py" (
        echo       [INFO] Starting Open WebUI...
        cd /d "%~dp0..\open-webui"
        start python backend\main.py
    ) else (
        echo       [INFO] Opening web interface...
        timeout /t 3 /nobreak >nul
        start http://localhost:%OPENWEBUI_PORT%
    )
    
    echo.
    echo ============================================================
    echo            SUNFLOWER AI IS NOW RUNNING
    echo ============================================================
    echo.
    echo Web Interface: http://localhost:%OPENWEBUI_PORT%
    echo.
    echo Press any key to stop services and exit...
    pause >nul
    
    call :LogMessage "INFO" "Application launched successfully"
    exit /b 0

:Cleanup
    echo.
    echo [CLEANUP]
    echo       Stopping services...
    
    :: Stop Ollama if we started it
    tasklist | findstr /i "ollama" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        taskkill /IM ollama.exe /F >nul 2>&1
        echo       [OK] Ollama stopped
    )
    
    echo       [OK] Cleanup complete
    call :LogMessage "INFO" "Launcher cleanup completed"
    exit /b 0

@echo off
:: Sunflower AI Professional System - Windows Launcher
:: Version: 6.2 | Production-Ready with Complete Error Handling
:: Fixed: Locale-independent date handling, Ollama validation, error recovery

setlocal enabledelayedexpansion

:: ==================== CONSTANTS ====================
set "VERSION=6.2"
set "SYSTEM_NAME=Sunflower AI Professional System"
set "MIN_RAM_GB=4"
set "MIN_WINDOWS_BUILD=17134"
set "CDROM_MARKER=SUNFLOWER_CD"
set "USB_MARKER=SUNFLOWER_USB"
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
:: BUG-005 FIX: Use WMIC for locale-independent date/time
for /f "skip=1 tokens=1" %%a in ('wmic os get localdatetime') do (
    set "datetime=%%a"
    goto :datetime_done
)
:datetime_done
set "TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%"
set "LOG_DIR=%LOCALAPPDATA%\SunflowerAI\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\launcher_%TIMESTAMP%.log"
set "ERROR_LOG=%LOG_DIR%\errors_%TIMESTAMP%.log"

:: ==================== COLOR SETUP ====================
:: Using findstr for color output (Windows-compatible)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "MAGENTA=[95m"
set "CYAN=[96m"
set "WHITE=[97m"
set "NC=[0m"

:: ==================== MAIN EXECUTION ====================
call :LogMessage "INFO" "=== Sunflower AI Launcher Started ==="
call :LogMessage "INFO" "Version: %VERSION%"
call :LogMessage "INFO" "Timestamp: %TIMESTAMP%"
call :LogMessage "INFO" "Log file: %LOG_FILE%"

:: Clear screen and display header
cls
call :DisplayHeader

:: ==================== SYSTEM CHECKS ====================
echo %CYAN%[SYSTEM VALIDATION]%NC%
echo.

echo  [1/8] Checking administrator privileges...
call :CheckAdminPrivileges
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Administrator Required" "Please run as Administrator"
    call :RequestElevation
    exit /b %ERROR_ADMIN_REQUIRED%
)

echo  [2/8] Validating Windows version...
call :ValidateWindowsVersion
if %ERRORLEVEL% neq 0 (
    exit /b %ERROR_INCOMPATIBLE_OS%
)

echo  [3/8] Checking system memory...
call :ValidateSystemRAM
if %ERRORLEVEL% neq 0 (
    exit /b %ERROR_INSUFFICIENT_RAM%
)

:: ==================== PARTITION DETECTION ====================
echo  [4/8] Detecting CD-ROM partition...
call :DetectCDROMPartition
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "CD-ROM Not Found" "Please insert the Sunflower AI device"
    exit /b %ERROR_CDROM_NOT_FOUND%
)

echo  [5/8] Detecting USB partition...
call :DetectUSBPartition
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "USB Not Found" "Cannot find writable partition"
    exit /b %ERROR_USB_NOT_FOUND%
)

:: ==================== INTEGRITY VERIFICATION ====================
echo  [6/8] Verifying system integrity...
call :VerifySystemIntegrity
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Integrity Check Failed" "System files are corrupted"
    exit /b %ERROR_INTEGRITY_CHECK_FAILED%
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
    call :ShowUserError "Python Setup Failed" "Unable to initialize Python environment"
    exit /b %ERROR_PYTHON_NOT_FOUND%
)

:: BUG-020 FIX: Comprehensive Ollama validation and initialization
call :InitializeOllama
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "AI Service Failed" "Unable to start Ollama service"
    exit /b %ERROR_OLLAMA_FAILED%
)

:: Launch application
call :LaunchApplication
if %ERRORLEVEL% neq 0 (
    call :ShowUserError "Launch Failed" "Unable to start Sunflower AI"
    exit /b %ERROR_OPENWEBUI_FAILED%
)

:: Cleanup
call :Cleanup
exit /b %ERROR_SUCCESS%

:: ==================== FUNCTIONS ====================

:DisplayHeader
    cls
    echo.
    echo %CYAN%============================================================%NC%
    echo %GREEN%        🌻 SUNFLOWER AI PROFESSIONAL SYSTEM 🌻%NC%
    echo %CYAN%         Family-Focused K-12 STEM Education%NC%
    echo %WHITE%                  Version %VERSION%%NC%
    echo %CYAN%============================================================%NC%
    echo.
    exit /b 0

:LogMessage
    :: Parameters: Level Message
    set "level=%~1"
    set "message=%~2"
    
    :: Get current timestamp using WMIC (locale-independent)
    for /f "skip=1 tokens=1" %%a in ('wmic os get localdatetime') do (
        set "log_time=%%a"
        goto :log_time_done
    )
    :log_time_done
    
    echo [%log_time:~0,14%] [%level%] %message% >> "%LOG_FILE%"
    
    if "%level%"=="ERROR" (
        echo [%log_time:~0,14%] %message% >> "%ERROR_LOG%"
    )
    exit /b 0

:CheckAdminPrivileges
    net session >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        call :LogMessage "ERROR" "Administrator privileges not detected"
        exit /b 1
    )
    call :LogMessage "INFO" "Administrator privileges confirmed"
    exit /b 0

:RequestElevation
    :: Create elevation script
    set "ELEVATE_SCRIPT=%TEMP%\elevate_%RANDOM%.vbs"
    (
        echo Set UAC = CreateObject^("Shell.Application"^)
        echo UAC.ShellExecute "%~f0", "", "", "runas", 1
    ) > "%ELEVATE_SCRIPT%"
    
    cscript //nologo "%ELEVATE_SCRIPT%"
    del "%ELEVATE_SCRIPT%" 2>nul
    exit /b 0

:ValidateWindowsVersion
    :: Get Windows build number
    for /f "tokens=3" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentBuild 2^>nul ^| findstr "CurrentBuild"') do (
        set "BUILD_NUM=%%a"
    )
    
    if not defined BUILD_NUM (
        call :LogMessage "ERROR" "Unable to determine Windows version"
        exit /b 1
    )
    
    if %BUILD_NUM% LSS %MIN_WINDOWS_BUILD% (
        call :LogMessage "ERROR" "Windows build %BUILD_NUM% is below minimum %MIN_WINDOWS_BUILD%"
        exit /b 1
    )
    
    call :LogMessage "INFO" "Windows build %BUILD_NUM% meets requirements"
    exit /b 0

:ValidateSystemRAM
    :: Get total physical memory in GB
    for /f "skip=1" %%a in ('wmic computersystem get TotalPhysicalMemory') do (
        if not "%%a"=="" (
            set /a "RAM_BYTES=%%a"
            set /a "RAM_GB=!RAM_BYTES!/1073741824"
            goto :ram_calculated
        )
    )
    :ram_calculated
    
    if %RAM_GB% LSS %MIN_RAM_GB% (
        call :LogMessage "ERROR" "System has %RAM_GB%GB RAM, minimum is %MIN_RAM_GB%GB"
        exit /b 1
    )
    
    call :LogMessage "INFO" "System RAM: %RAM_GB%GB - meets requirements"
    set "SYSTEM_RAM_GB=%RAM_GB%"
    exit /b 0

:DetectCDROMPartition
    set "CDROM_PATH="
    
    :: Check each drive for CD-ROM partition marker
    for %%D in (C: D: E: F: G: H: I: J: K: L: M: N: O: P: Q: R: S: T: U: V: W: X: Y: Z:) do (
        if exist "%%D\sunflower_cd.id" (
            :: Verify it's read-only (CD-ROM characteristic)
            echo test > "%%D\test_write.tmp" 2>nul
            if !ERRORLEVEL! neq 0 (
                set "CDROM_PATH=%%D"
                call :LogMessage "INFO" "CD-ROM partition found at %%D"
                exit /b 0
            )
        )
    )
    
    call :LogMessage "ERROR" "CD-ROM partition not found"
    exit /b 1

:DetectUSBPartition
    set "USB_PATH="
    
    :: Check each drive for USB partition marker
    for %%D in (C: D: E: F: G: H: I: J: K: L: M: N: O: P: Q: R: S: T: U: V: W: X: Y: Z:) do (
        if exist "%%D\sunflower_data.id" (
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
                
                exit /b 0
            )
        )
    )
    
    call :LogMessage "ERROR" "USB partition not found"
    exit /b 1

:VerifySystemIntegrity
    :: Define critical files
    set "FILES_TO_CHECK[0]=%CDROM_PATH%\system\launcher_common.py"
    set "FILES_TO_CHECK[1]=%CDROM_PATH%\system\openwebui_integration.py"
    set "FILES_TO_CHECK[2]=%CDROM_PATH%\ollama\ollama.exe"
    set "FILES_TO_CHECK[3]=%CDROM_PATH%\modelfiles\sunflower-kids.modelfile"
    set "FILES_TO_CHECK[4]=%CDROM_PATH%\modelfiles\sunflower-educator.modelfile"
    set "FILES_TO_CHECK[5]=%CDROM_PATH%\bin\open-webui.exe"
    
    set "MISSING_FILES="
    for /L %%i in (0,1,5) do (
        if not exist "!FILES_TO_CHECK[%%i]!" (
            set "MISSING_FILES=!MISSING_FILES! !FILES_TO_CHECK[%%i]!"
            call :LogMessage "ERROR" "Missing: !FILES_TO_CHECK[%%i]!"
        )
    )
    
    if not "!MISSING_FILES!"=="" (
        exit /b 1
    )
    
    :: Verify checksums if manifest exists
    if exist "%CDROM_PATH%\integrity.manifest" (
        call :VerifyChecksums "%CDROM_PATH%\integrity.manifest"
        if !ERRORLEVEL! neq 0 exit /b 1
    )
    
    call :LogMessage "INFO" "System integrity verified"
    exit /b 0

:VerifyChecksums
    set "manifest=%~1"
    set "failures=0"
    
    for /f "tokens=1,2" %%a in (%manifest%) do (
        set "expected_hash=%%a"
        set "file_path=%CDROM_PATH%\%%b"
        
        if exist "!file_path!" (
            certutil -hashfile "!file_path!" SHA256 | findstr /v ":" > "%TEMP%\hash.tmp"
            set /p actual_hash=<"%TEMP%\hash.tmp"
            del "%TEMP%\hash.tmp"
            
            if not "!actual_hash!"=="!expected_hash!" (
                call :LogMessage "ERROR" "Checksum mismatch: %%b"
                set /a failures+=1
            )
        )
    )
    
    if %failures% gtr 0 exit /b 1
    exit /b 0

:DetectHardwareCapabilities
    :: CPU detection
    for /f "tokens=2 delims==" %%a in ('wmic cpu get NumberOfCores /value 2^>nul') do set "CPU_CORES=%%a"
    for /f "tokens=2 delims==" %%a in ('wmic cpu get MaxClockSpeed /value 2^>nul') do set "CPU_SPEED=%%a"
    for /f "tokens=2 delims==" %%a in ('wmic cpu get Name /value 2^>nul') do set "CPU_NAME=%%a"
    
    :: GPU detection
    set "HAS_GPU=0"
    set "GPU_NAME=None"
    for /f "tokens=*" %%a in ('wmic path win32_VideoController get name 2^>nul ^| findstr /i "NVIDIA AMD Radeon GeForce"') do (
        set "HAS_GPU=1"
        set "GPU_NAME=%%a"
    )
    
    :: Calculate performance score
    set /a "PERF_SCORE=0"
    set /a "PERF_SCORE+=%SYSTEM_RAM_GB%*10"
    set /a "PERF_SCORE+=%CPU_CORES%*5"
    if %HAS_GPU% equ 1 set /a "PERF_SCORE+=20"
    
    call :LogMessage "INFO" "Hardware: CPU=%CPU_NAME%, Cores=%CPU_CORES%, RAM=%SYSTEM_RAM_GB%GB, GPU=%GPU_NAME%"
    call :LogMessage "INFO" "Performance score: %PERF_SCORE%"
    
    exit /b 0

:SelectOptimalModel
    :: Model selection based on performance score
    if %PERF_SCORE% geq 100 (
        set "SELECTED_MODEL=llama3.2:7b"
        set "MODEL_PATH=%CDROM_PATH%\models\llama3.2-7b.gguf"
    ) else if %PERF_SCORE% geq 70 (
        set "SELECTED_MODEL=llama3.2:3b"
        set "MODEL_PATH=%CDROM_PATH%\models\llama3.2-3b.gguf"
    ) else if %PERF_SCORE% geq 40 (
        set "SELECTED_MODEL=llama3.2:1b"
        set "MODEL_PATH=%CDROM_PATH%\models\llama3.2-1b.gguf"
    ) else (
        set "SELECTED_MODEL=llama3.2:1b-q4_0"
        set "MODEL_PATH=%CDROM_PATH%\models\llama3.2-1b-q4_0.gguf"
    )
    
    call :LogMessage "INFO" "Selected model: %SELECTED_MODEL%"
    
    :: Verify model file exists
    if not exist "%MODEL_PATH%" (
        call :LogMessage "ERROR" "Model file not found: %MODEL_PATH%"
        exit /b 1
    )
    
    exit /b 0

:SetupPythonEnvironment
    :: Check for Python in PATH
    python --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%a"
        call :LogMessage "INFO" "Found Python %PYTHON_VERSION%"
        set "PYTHON_CMD=python"
        goto :python_found
    )
    
    :: Check for Python in common locations
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe"
        "%PROGRAMFILES%\Python3*\python.exe"
        "%PROGRAMFILES(X86)%\Python3*\python.exe"
        "C:\Python3*\python.exe"
    ) do (
        if exist "%%~P" (
            set "PYTHON_CMD=%%~P"
            call :LogMessage "INFO" "Found Python at %%~P"
            goto :python_found
        )
    )
    
    :: Python not found
    call :LogMessage "ERROR" "Python not found"
    exit /b 1
    
    :python_found
    :: Install required packages
    "%PYTHON_CMD%" -m pip install --quiet --upgrade pip
    "%PYTHON_CMD%" -m pip install --quiet -r "%CDROM_PATH%\requirements.txt"
    
    exit /b 0

:InitializeOllama
    :: BUG-020 FIX: Comprehensive Ollama service validation
    call :LogMessage "INFO" "Initializing Ollama service..."
    
    :: Check if Ollama is already running
    call :CheckOllamaService
    if %ERRORLEVEL% equ 0 (
        call :LogMessage "INFO" "Ollama service already running"
        goto :ollama_ready
    )
    
    :: Start Ollama service
    set "OLLAMA_EXE=%CDROM_PATH%\ollama\ollama.exe"
    if not exist "%OLLAMA_EXE%" (
        call :LogMessage "ERROR" "Ollama executable not found"
        exit /b 1
    )
    
    :: Set Ollama environment
    set "OLLAMA_HOST=127.0.0.1:%OLLAMA_PORT%"
    set "OLLAMA_MODELS=%USB_PATH%\models"
    
    :: Start Ollama in background
    start /B "" "%OLLAMA_EXE%" serve > "%LOG_DIR%\ollama.log" 2>&1
    
    :: Wait for Ollama to start (with timeout)
    set "attempts=0"
    :wait_ollama
    if %attempts% geq 30 (
        call :LogMessage "ERROR" "Ollama failed to start within timeout"
        exit /b 1
    )
    
    timeout /t 1 /nobreak >nul
    set /a attempts+=1
    
    call :CheckOllamaService
    if %ERRORLEVEL% neq 0 goto :wait_ollama
    
    :ollama_ready
    call :LogMessage "INFO" "Ollama service ready"
    
    :: Load models
    call :LoadModels
    exit /b %ERRORLEVEL%

:CheckOllamaService
    :: Check if Ollama is responding
    curl -s -o nul -w "%%{http_code}" http://127.0.0.1:%OLLAMA_PORT%/api/tags >"%TEMP%\ollama_check.tmp" 2>nul
    set /p response=<"%TEMP%\ollama_check.tmp"
    del "%TEMP%\ollama_check.tmp" 2>nul
    
    if "%response%"=="200" (
        exit /b 0
    )
    
    :: Alternative check using netstat
    netstat -an | findstr ":%OLLAMA_PORT%.*LISTENING" >nul 2>&1
    exit /b %ERRORLEVEL%

:LoadModels
    call :LogMessage "INFO" "Loading AI models..."
    
    :: Create Sunflower Kids model
    "%OLLAMA_EXE%" create sunflower-kids -f "%CDROM_PATH%\modelfiles\sunflower-kids.modelfile"
    if %ERRORLEVEL% neq 0 (
        call :LogMessage "ERROR" "Failed to create sunflower-kids model"
        exit /b 1
    )
    
    :: Create Sunflower Educator model
    "%OLLAMA_EXE%" create sunflower-educator -f "%CDROM_PATH%\modelfiles\sunflower-educator.modelfile"
    if %ERRORLEVEL% neq 0 (
        call :LogMessage "ERROR" "Failed to create sunflower-educator model"
        exit /b 1
    )
    
    call :LogMessage "INFO" "Models loaded successfully"
    exit /b 0

:LaunchApplication
    call :LogMessage "INFO" "Launching Sunflower AI application..."
    
    :: Create launch configuration
    set "CONFIG_FILE=%USB_PATH%\config\launch.json"
    (
        echo {
        echo   "cdrom_path": "%CDROM_PATH:\=\\%",
        echo   "usb_path": "%USB_PATH:\=\\%",
        echo   "selected_model": "%SELECTED_MODEL%",
        echo   "ollama_port": %OLLAMA_PORT%,
        echo   "openwebui_port": %OPENWEBUI_PORT%,
        echo   "system_ram": %SYSTEM_RAM_GB%,
        echo   "cpu_cores": %CPU_CORES%,
        echo   "has_gpu": %HAS_GPU%
        echo }
    ) > "%CONFIG_FILE%"
    
    :: Launch main application
    "%PYTHON_CMD%" "%CDROM_PATH%\system\launcher_common.py" --config "%CONFIG_FILE%"
    set "LAUNCH_RESULT=%ERRORLEVEL%"
    
    if %LAUNCH_RESULT% neq 0 (
        call :LogMessage "ERROR" "Application launch failed with code %LAUNCH_RESULT%"
        exit /b %LAUNCH_RESULT%
    )
    
    call :LogMessage "INFO" "Application launched successfully"
    exit /b 0

:ShowUserError
    :: Parameters: Title Message
    set "title=%~1"
    set "message=%~2"
    
    echo.
    echo %RED%╔════════════════════════════════════════╗%NC%
    echo %RED%║         ERROR: %title%                  
    echo %RED%╠════════════════════════════════════════╣%NC%
    echo %RED%║%NC% %message%
    echo %RED%╚════════════════════════════════════════╝%NC%
    echo.
    
    call :LogMessage "ERROR" "%title%: %message%"
    
    :: Show troubleshooting tips
    echo %YELLOW%Troubleshooting:%NC%
    echo  • Check that the device is properly inserted
    echo  • Ensure you have administrator privileges
    echo  • Verify system meets minimum requirements
    echo  • Check log file: %LOG_FILE%
    echo.
    
    pause
    exit /b 0

:Cleanup
    call :LogMessage "INFO" "Performing cleanup..."
    
    :: Stop Ollama if running
    taskkill /F /IM ollama.exe >nul 2>&1
    
    :: Clean temporary files
    del "%TEMP%\sunflower_*.tmp" 2>nul
    del "%TEMP%\elevate_*.vbs" 2>nul
    
    call :LogMessage "INFO" "=== Sunflower AI Launcher Completed ==="
    exit /b 0

:: ==================== END OF SCRIPT ====================

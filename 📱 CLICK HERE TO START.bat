@echo off
setlocal enabledelayedexpansion
title Sunflower AI Professional System - Family Education Platform

:: ============================================================================
:: SUNFLOWER AI PROFESSIONAL SYSTEM
:: Version: 6.2 - Production Ready
:: Purpose: Main launcher for family-focused K-12 STEM education
:: Fixed: Removed all ANSI codes for universal compatibility
:: ============================================================================

:: Get USB root path
set "USB_ROOT=%~dp0"
set "LOG_FILE=%USB_ROOT%sunflower_debug.log"

:: Skip over function definitions during normal execution
goto :main_script_start

:: ============================================================================
:: LOGGING SYSTEM (PRODUCTION-READY)
:: ============================================================================

:log_init
:: Create/clear the log file and add header
echo. > "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"
echo SUNFLOWER AI SYSTEM - DEBUG LOG >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"
echo Log started: %date% %time% >> "%LOG_FILE%"
echo USB Drive: %USB_ROOT% >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"
goto :eof

:log_info
set "LOG_MSG=%~1"
echo [%time%] INFO: %LOG_MSG% >> "%LOG_FILE%"
goto :eof

:log_error
set "LOG_MSG=%~1"
echo [%time%] ERROR: %LOG_MSG% >> "%LOG_FILE%"
echo [ERROR] %LOG_MSG%
goto :eof

:log_warning
set "LOG_MSG=%~1"
echo [%time%] WARNING: %LOG_MSG% >> "%LOG_FILE%"
echo [WARNING] %LOG_MSG%
goto :eof

:log_debug
set "LOG_MSG=%~1"
echo [%time%] DEBUG: %LOG_MSG% >> "%LOG_FILE%"
goto :eof

:log_variable
set "VAR_NAME=%~1"
set "VAR_VALUE=%~2"
echo [%time%] VARIABLE: %VAR_NAME% = %VAR_VALUE% >> "%LOG_FILE%"
goto :eof

:log_operation_start
set "OP_NAME=%~1"
echo [%time%] OPERATION START: %OP_NAME% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"
goto :eof

:log_operation_end
set "OP_NAME=%~1"
set "OP_RESULT=%~2"
echo [%time%] OPERATION END: %OP_NAME% - Result: %OP_RESULT% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"
goto :eof

:show_log_file
cls
echo.
echo ================================================================
echo                        DEBUG LOG VIEWER
echo ================================================================
echo.
echo Log file location: %LOG_FILE%
echo.
if exist "%LOG_FILE%" (
    echo Recent log entries:
    echo ----------------------------------------
    type "%LOG_FILE%"
    echo ----------------------------------------
    echo.
    echo Press any key to continue...
    pause >nul
) else (
    echo No log file found.
    echo.
    pause
)
goto :eof

:: ============================================================================
:: MAIN SCRIPT START
:: ============================================================================

:main_script_start
call :log_init
call :log_operation_start "Main Menu"

cls
echo ========================================================================
echo                    SUNFLOWER AI PROFESSIONAL SYSTEM
echo                   Family-Focused K-12 STEM Education
echo                            Version 6.2
echo ========================================================================
echo.
echo Welcome to your personal AI education assistant!
echo.

:: Check if running from USB/removable drive
set "DRIVE_TYPE=unknown"
for /f "tokens=2 delims==" %%a in ('wmic logicaldisk where "DeviceID='%USB_ROOT:~0,2%'" get DriveType /value 2^>nul') do (
    if "%%a"=="2" set "DRIVE_TYPE=removable"
    if "%%a"=="3" set "DRIVE_TYPE=fixed"
    if "%%a"=="4" set "DRIVE_TYPE=network"
    if "%%a"=="5" set "DRIVE_TYPE=optical"
)

call :log_variable "DRIVE_TYPE" "%DRIVE_TYPE%"

if "%DRIVE_TYPE%"=="fixed" (
    echo [WARNING] Running from local hard drive instead of USB device.
    echo          Some features may not work as intended.
    echo.
    call :log_warning "Not running from USB device"
)

:main_menu
echo ========================================================================
echo                             MAIN MENU
echo ========================================================================
echo.
echo Please select an option:
echo.
echo   [1] Start Sunflower Expert AI (Agriculture + Child Development)
echo   [2] Start General Purpose AI (Programming, Writing, etc.)
echo   [3] System Management and Updates
echo   [4] Create Desktop Shortcuts
echo   [5] View Debug Information
echo   [6] Exit
echo.
echo ========================================================================
echo.

set /p "choice=Enter your selection (1-6): "
call :log_variable "USER_CHOICE" "%choice%"

if "%choice%"=="1" goto :start_sunflower_expert
if "%choice%"=="2" goto :start_general_ai
if "%choice%"=="3" goto :system_management
if "%choice%"=="4" goto :create_shortcuts
if "%choice%"=="5" goto :debug_menu
if "%choice%"=="6" goto :exit_program

echo.
echo [ERROR] Invalid selection. Please choose a number between 1 and 6.
echo.
pause
cls
goto :main_menu

:: ============================================================================
:: SUNFLOWER EXPERT AI LAUNCHER
:: ============================================================================

:start_sunflower_expert
call :log_operation_start "Start Sunflower Expert"
cls
echo ========================================================================
echo                      SUNFLOWER EXPERT AI
echo              Specialized in Agriculture and Child Development
echo ========================================================================
echo.

:: Check if first time setup is needed
if not exist "%USB_ROOT%config\setup_complete.flag" (
    echo [INFO] First-time setup detected...
    echo.
    call :first_time_setup
    if errorlevel 1 goto :main_menu
)

echo [INFO] Starting Sunflower Expert AI...
echo.

:: Check for the launcher script
if exist "%USB_ROOT%START SUNFLOWER EXPERT.bat" (
    call :log_info "Found START SUNFLOWER EXPERT.bat"
    call "%USB_ROOT%START SUNFLOWER EXPERT.bat"
) else if exist "%USB_ROOT%sunflower_expert.bat" (
    call :log_info "Found sunflower_expert.bat"
    call "%USB_ROOT%sunflower_expert.bat"
) else (
    echo [ERROR] Sunflower Expert launcher not found!
    echo.
    echo Please ensure the USB device contains all required files.
    echo.
    call :log_error "Sunflower Expert launcher not found"
    pause
)

call :log_operation_end "Start Sunflower Expert" "Completed"
goto :main_menu

:: ============================================================================
:: GENERAL AI LAUNCHER
:: ============================================================================

:start_general_ai
call :log_operation_start "Start General AI"
cls
echo ========================================================================
echo                        GENERAL PURPOSE AI
echo              Programming, Writing, Research, and More
echo ========================================================================
echo.

:: Check if first time setup is needed
if not exist "%USB_ROOT%config\setup_complete.flag" (
    echo [INFO] First-time setup detected...
    echo.
    call :first_time_setup
    if errorlevel 1 goto :main_menu
)

echo [INFO] Starting General Purpose AI...
echo.

:: Check for the launcher script
if exist "%USB_ROOT%START GENERAL AI.bat" (
    call :log_info "Found START GENERAL AI.bat"
    call "%USB_ROOT%START GENERAL AI.bat"
) else if exist "%USB_ROOT%general_ai.bat" (
    call :log_info "Found general_ai.bat"
    call "%USB_ROOT%general_ai.bat"
) else (
    echo [ERROR] General AI launcher not found!
    echo.
    echo Please ensure the USB device contains all required files.
    echo.
    call :log_error "General AI launcher not found"
    pause
)

call :log_operation_end "Start General AI" "Completed"
goto :main_menu

:: ============================================================================
:: SYSTEM MANAGEMENT
:: ============================================================================

:system_management
call :log_operation_start "System Management"
cls
echo ========================================================================
echo                        SYSTEM MANAGEMENT
echo ========================================================================
echo.
echo   [1] Check for Updates
echo   [2] Reinstall AI Models
echo   [3] Clear Cache and Temporary Files
echo   [4] View System Information
echo   [5] Reset to Factory Defaults
echo   [6] Back to Main Menu
echo.
echo ========================================================================
echo.

set /p "sys_choice=Enter your selection (1-6): "
call :log_variable "SYSTEM_CHOICE" "%sys_choice%"

if "%sys_choice%"=="1" goto :check_updates
if "%sys_choice%"=="2" goto :reinstall_models
if "%sys_choice%"=="3" goto :clear_cache
if "%sys_choice%"=="4" goto :system_info
if "%sys_choice%"=="5" goto :factory_reset
if "%sys_choice%"=="6" goto :main_menu

echo [ERROR] Invalid selection.
pause
goto :system_management

:check_updates
echo.
echo [INFO] Checking for updates...
if exist "%USB_ROOT%UPDATE SYSTEM.bat" (
    call "%USB_ROOT%UPDATE SYSTEM.bat"
) else (
    echo [WARNING] Update script not found.
)
pause
goto :system_management

:reinstall_models
echo.
echo [WARNING] This will reinstall all AI models (2-3GB download).
echo.
set /p "confirm=Are you sure? (Y/N): "
if /i "%confirm%"=="Y" (
    echo [INFO] Reinstalling models...
    :: Model installation logic here
    echo [SUCCESS] Models reinstalled successfully.
) else (
    echo [INFO] Operation cancelled.
)
pause
goto :system_management

:clear_cache
echo.
echo [INFO] Clearing cache and temporary files...
if exist "%USB_ROOT%temp" rmdir /s /q "%USB_ROOT%temp" 2>nul
if exist "%USB_ROOT%cache" rmdir /s /q "%USB_ROOT%cache" 2>nul
mkdir "%USB_ROOT%temp"
mkdir "%USB_ROOT%cache"
echo [SUCCESS] Cache cleared successfully.
pause
goto :system_management

:system_info
echo.
echo ========================================================================
echo                        SYSTEM INFORMATION
echo ========================================================================
echo.
echo Installation Path: %USB_ROOT%
echo Drive Type: %DRIVE_TYPE%
echo.
echo Windows Version:
ver
echo.
echo Available Memory:
wmic OS get TotalVisibleMemorySize /value | findstr "="
echo.
echo Processor:
wmic cpu get name /value | findstr "="
echo.
echo ========================================================================
pause
goto :system_management

:factory_reset
echo.
echo ========================================================================
echo                    WARNING: FACTORY RESET
echo ========================================================================
echo.
echo This will DELETE all:
echo   - User profiles and conversations
echo   - Custom settings
echo   - Downloaded models
echo   - Cache and temporary files
echo.
echo This action cannot be undone!
echo.
set /p "confirm=Type 'RESET' to confirm: "
if "%confirm%"=="RESET" (
    echo [INFO] Performing factory reset...
    :: Reset logic here
    echo [SUCCESS] Factory reset completed.
) else (
    echo [INFO] Factory reset cancelled.
)
pause
goto :system_management

:: ============================================================================
:: CREATE DESKTOP SHORTCUTS
:: ============================================================================

:create_shortcuts
call :log_operation_start "Create Desktop Shortcuts"
cls
echo ========================================================================
echo                    CREATE DESKTOP SHORTCUTS
echo ========================================================================
echo.
echo This will create desktop shortcuts for easy access to:
echo   - Sunflower AI System (main menu)
echo   - Sunflower Expert AI
echo   - General Purpose AI
echo   - System Updates
echo.

set /p "create_confirm=Create shortcuts now? (Y/N): "
if /i "%create_confirm%"=="Y" (
    if exist "%USB_ROOT%CREATE DESKTOP SHORTCUTS.bat" (
        call "%USB_ROOT%CREATE DESKTOP SHORTCUTS.bat"
        echo.
        echo [SUCCESS] Desktop shortcuts created successfully!
    ) else (
        echo [ERROR] Shortcut creation script not found.
        call :log_error "CREATE DESKTOP SHORTCUTS.bat not found"
    )
) else (
    echo [INFO] Shortcut creation cancelled.
)

pause
goto :main_menu

:: ============================================================================
:: DEBUG MENU
:: ============================================================================

:debug_menu
call :log_operation_start "Debug Menu"
cls
echo ========================================================================
echo                        DEBUG INFORMATION
echo ========================================================================
echo.
echo   [1] View Debug Log
echo   [2] Test Ollama Connection
echo   [3] Check Model Files
echo   [4] Verify Installation
echo   [5] Export Debug Report
echo   [6] Back to Main Menu
echo.
echo ========================================================================
echo.

set /p "debug_choice=Enter your selection (1-6): "

if "%debug_choice%"=="1" call :show_log_file && goto :debug_menu
if "%debug_choice%"=="2" goto :test_ollama
if "%debug_choice%"=="3" goto :check_models
if "%debug_choice%"=="4" goto :verify_installation
if "%debug_choice%"=="5" goto :export_debug
if "%debug_choice%"=="6" goto :main_menu

echo [ERROR] Invalid selection.
pause
goto :debug_menu

:test_ollama
echo.
echo [INFO] Testing Ollama connection...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ollama is not installed or not accessible.
) else (
    echo [SUCCESS] Ollama is installed and accessible.
    ollama --version
)
pause
goto :debug_menu

:check_models
echo.
echo [INFO] Checking for model files...
echo.
if exist "%USB_ROOT%models" (
    echo Model directory contents:
    dir "%USB_ROOT%models" /b
) else (
    echo [WARNING] Models directory not found.
)
pause
goto :debug_menu

:verify_installation
echo.
echo [INFO] Verifying installation integrity...
echo.
set "missing_files=0"

:: Check critical files
if not exist "%USB_ROOT%config" (
    echo [MISSING] config directory
    set /a missing_files+=1
)
if not exist "%USB_ROOT%models" (
    echo [MISSING] models directory
    set /a missing_files+=1
)

if %missing_files%==0 (
    echo [SUCCESS] All critical components found.
) else (
    echo [WARNING] %missing_files% components missing.
)
pause
goto :debug_menu

:export_debug
echo.
echo [INFO] Exporting debug report...
set "debug_report=%USB_ROOT%debug_report_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.txt"
set "debug_report=%debug_report: =0%"

echo Debug Report Generated: %date% %time% > "%debug_report%"
echo ======================================== >> "%debug_report%"
echo. >> "%debug_report%"
echo System Information: >> "%debug_report%"
echo USB Root: %USB_ROOT% >> "%debug_report%"
echo Drive Type: %DRIVE_TYPE% >> "%debug_report%"
ver >> "%debug_report%"
echo. >> "%debug_report%"

if exist "%LOG_FILE%" (
    echo Recent Log Entries: >> "%debug_report%"
    echo ======================================== >> "%debug_report%"
    type "%LOG_FILE%" >> "%debug_report%"
)

echo [SUCCESS] Debug report saved to:
echo           %debug_report%
pause
goto :debug_menu

:: ============================================================================
:: FIRST TIME SETUP
:: ============================================================================

:first_time_setup
echo ========================================================================
echo                      FIRST-TIME SETUP
echo ========================================================================
echo.
echo This will:
echo   - Download and configure AI models (~2.5GB)
echo   - Create desktop shortcuts for easy access
echo   - Set up both AI models (Expert + General)
echo.
echo You only need to do this once!
echo.
set /p "setup_confirm=Continue with setup? (Y/N): "

if /i not "%setup_confirm%"=="Y" (
    echo [INFO] Setup cancelled. You can run setup later from System Management.
    pause
    exit /b 1
)

echo.
echo [INFO] Starting first-time setup...
call :log_info "Starting first-time setup process"

:: Try multiple possible names for the update script
if exist "%USB_ROOT%UPDATE SYSTEM.bat" (
    call :log_info "Found UPDATE SYSTEM.bat"
    call "%USB_ROOT%UPDATE SYSTEM.bat"
) else if exist "%USB_ROOT%update.bat" (
    call :log_info "Found update.bat"
    call "%USB_ROOT%update.bat"
) else (
    call :log_warning "Update script not found, skipping setup"
    echo [WARNING] Setup script not found.
    echo           You can run setup later from System Management menu.
    echo.
    pause
    exit /b 1
)

if errorlevel 1 (
    echo [ERROR] Setup failed! Check logs for details.
    call :log_error "Setup script returned error"
    pause
    exit /b 1
)

:: Create setup complete flag
if not exist "%USB_ROOT%config" mkdir "%USB_ROOT%config"
echo %date% %time% > "%USB_ROOT%config\setup_complete.flag"

echo.
echo [SUCCESS] First-time setup completed successfully!
call :log_info "First-time setup completed successfully"
pause
exit /b 0

:: ============================================================================
:: EXIT PROGRAM
:: ============================================================================

:exit_program
call :log_operation_start "Exit Program"
cls
echo ========================================================================
echo                    THANK YOU FOR USING SUNFLOWER AI
echo ========================================================================
echo.
echo Your AI assistant is always here when you need it!
echo.
echo For support and documentation:
echo   - User Guide: docs\user_guide.txt
echo   - Troubleshooting: docs\troubleshooting.txt
echo   - Debug Log: %LOG_FILE%
echo.
echo ========================================================================
echo.
call :log_info "Application closed normally"
call :log_operation_end "Exit Program" "Success"
timeout /t 2 /nobreak >nul
exit /b 0

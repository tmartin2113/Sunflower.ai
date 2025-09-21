@echo off
:: ============================================================================
:: Sunflower AI Desktop Shortcut Creator
:: Version: 6.2 - Production Ready (No ANSI Colors)
:: Purpose: Creates desktop shortcuts for easy access to Sunflower AI
:: Location: Root directory of USB device
:: Fixed: Removed all ANSI codes, improved compatibility and error handling
:: ============================================================================

setlocal enabledelayedexpansion
title Sunflower AI - Desktop Shortcut Creator

:: Get USB root path (current directory)
set "USB_ROOT=%~dp0"
:: Remove trailing backslash for consistency
if "%USB_ROOT:~-1%"=="\" set "USB_ROOT=%USB_ROOT:~0,-1%"

:: ============================================================================
:: INITIALIZATION
:: ============================================================================

cls
echo ========================================================================
echo                  SUNFLOWER AI SHORTCUT CREATOR
echo                 Create Desktop Shortcuts for Easy Access
echo                            Version 6.2
echo ========================================================================
echo.

:: Check if running from USB/removable drive
set "DRIVE_TYPE=unknown"
set "DRIVE_LETTER=%USB_ROOT:~0,2%"
for /f "tokens=2 delims==" %%a in ('wmic logicaldisk where "DeviceID='%DRIVE_LETTER%'" get DriveType /value 2^>nul') do (
    if "%%a"=="2" set "DRIVE_TYPE=removable"
    if "%%a"=="3" set "DRIVE_TYPE=fixed"
    if "%%a"=="4" set "DRIVE_TYPE=network"
)

if "%DRIVE_TYPE%"=="fixed" (
    echo [WARNING] Not running from USB device
    echo          Shortcuts will point to fixed drive location
    echo          They may not work if files are moved
    echo.
)

:: ============================================================================
:: DESKTOP DETECTION
:: ============================================================================

echo [INFO] Detecting desktop location...
echo.

:: Method 1: Query registry for Desktop folder
set "DESKTOP="
for /f "usebackq tokens=3*" %%i in (`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop 2^>nul`) do (
    set "DESKTOP=%%j"
)

:: Method 2: If that failed, try User Shell Folders
if not defined DESKTOP (
    for /f "usebackq tokens=3*" %%i in (`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop 2^>nul`) do (
        set "DESKTOP=%%j"
    )
)

:: Method 3: Fallback to standard location
if not defined DESKTOP (
    set "DESKTOP=%USERPROFILE%\Desktop"
)

:: Expand environment variables in the path
call set "DESKTOP=%DESKTOP%"

:: Verify desktop exists
if not exist "%DESKTOP%" (
    echo [ERROR] Cannot locate desktop folder
    echo        Attempted path: %DESKTOP%
    echo.
    echo You can create shortcuts manually:
    echo   1. Right-click on your desktop
    echo   2. Select New - Shortcut
    echo   3. Browse to %USB_ROOT%
    echo   4. Select the desired .bat file
    echo.
    pause
    exit /b 1
)

echo [OK] Desktop found: %DESKTOP%
echo.

:: ============================================================================
:: CONFIRM SHORTCUT CREATION
:: ============================================================================

echo This will create the following desktop shortcuts:
echo.
echo   1. Sunflower AI System      - Main menu and launcher
echo   2. Sunflower Expert AI      - Agriculture and Child Development
echo   3. General Purpose AI       - Programming, Writing, etc.
echo   4. Update Sunflower AI      - System updates and maintenance
echo.
echo Existing shortcuts with the same names will be replaced.
echo.

set /p "confirm=Do you want to continue? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo.
    echo [INFO] Shortcut creation cancelled
    pause
    exit /b 0
)

echo.
echo ========================================================================
echo                       CREATING SHORTCUTS
echo ========================================================================
echo.

:: ============================================================================
:: CREATE SHORTCUTS USING POWERSHELL
:: ============================================================================

:: Counter for successful shortcuts
set "success_count=0"
set "fail_count=0"

:: Shortcut 1: Main System
echo [1/4] Creating main system shortcut...
call :CreateShortcut ^
    "Sunflower AI System" ^
    "%USB_ROOT%\📱 CLICK HERE TO START.bat" ^
    "Launch the Sunflower AI Education System" ^
    "%USB_ROOT%" ^
    "%USB_ROOT%\resources\sunflower.ico"
if %ERRORLEVEL% equ 0 (
    echo       [OK] Main system shortcut created
    set /a success_count+=1
) else (
    echo       [FAILED] Could not create main shortcut
    set /a fail_count+=1
)

:: Shortcut 2: Sunflower Expert
echo [2/4] Creating Sunflower Expert shortcut...
call :CreateShortcut ^
    "Sunflower Expert AI" ^
    "%USB_ROOT%\🌻 START SUNFLOWER EXPERT.bat" ^
    "Specialized AI for Agriculture and Child Development" ^
    "%USB_ROOT%" ^
    "%USB_ROOT%\resources\sunflower.ico"
if %ERRORLEVEL% equ 0 (
    echo       [OK] Sunflower Expert shortcut created
    set /a success_count+=1
) else (
    echo       [FAILED] Could not create expert shortcut
    set /a fail_count+=1
)

:: Shortcut 3: General AI
echo [3/4] Creating General AI shortcut...
call :CreateShortcut ^
    "General Purpose AI" ^
    "%USB_ROOT%\🧠 START GENERAL AI.bat" ^
    "General Purpose AI for Programming, Writing, and More" ^
    "%USB_ROOT%" ^
    "%USB_ROOT%\resources\ai_general.ico"
if %ERRORLEVEL% equ 0 (
    echo       [OK] General AI shortcut created
    set /a success_count+=1
) else (
    echo       [FAILED] Could not create general AI shortcut
    set /a fail_count+=1
)

:: Shortcut 4: Update System
echo [4/4] Creating update shortcut...
call :CreateShortcut ^
    "Update Sunflower AI" ^
    "%USB_ROOT%\🔄 UPDATE SYSTEM.bat" ^
    "Update and Maintain Sunflower AI System" ^
    "%USB_ROOT%" ^
    "%USB_ROOT%\resources\update.ico"
if %ERRORLEVEL% equ 0 (
    echo       [OK] Update shortcut created
    set /a success_count+=1
) else (
    echo       [FAILED] Could not create update shortcut
    set /a fail_count+=1
)

:: ============================================================================
:: CREATE REMOVAL SCRIPT
:: ============================================================================

echo.
echo [INFO] Creating shortcut removal script...

set "removal_script=%USB_ROOT%\🗑️ REMOVE DESKTOP SHORTCUTS.bat"
(
    echo @echo off
    echo :: Sunflower AI Shortcut Removal Script
    echo :: Auto-generated by CREATE DESKTOP SHORTCUTS.bat
    echo.
    echo echo Removing Sunflower AI desktop shortcuts...
    echo.
    echo set "DESKTOP=%%USERPROFILE%%\Desktop"
    echo.
    echo if exist "%%DESKTOP%%\Sunflower AI System.lnk" del "%%DESKTOP%%\Sunflower AI System.lnk"
    echo if exist "%%DESKTOP%%\Sunflower Expert AI.lnk" del "%%DESKTOP%%\Sunflower Expert AI.lnk"
    echo if exist "%%DESKTOP%%\General Purpose AI.lnk" del "%%DESKTOP%%\General Purpose AI.lnk"
    echo if exist "%%DESKTOP%%\Update Sunflower AI.lnk" del "%%DESKTOP%%\Update Sunflower AI.lnk"
    echo.
    echo echo [OK] Desktop shortcuts removed
    echo pause
) > "%removal_script%"

if exist "%removal_script%" (
    echo       [OK] Removal script created
) else (
    echo       [WARNING] Could not create removal script
)

:: ============================================================================
:: SUMMARY AND COMPLETION
:: ============================================================================

echo.
echo ========================================================================
echo                         SUMMARY
echo ========================================================================
echo.
echo Shortcuts created successfully: %success_count%
echo Shortcuts failed: %fail_count%
echo.

if %success_count% gtr 0 (
    echo [SUCCESS] Desktop shortcuts are ready to use!
    echo.
    echo You can now:
    echo   - Launch Sunflower AI directly from your desktop
    echo   - Pin shortcuts to your taskbar for faster access
    echo   - Run the removal script to clean up shortcuts later
    echo.
) else (
    echo [ERROR] No shortcuts were created successfully
    echo.
    echo Troubleshooting:
    echo   - Ensure you have write permissions to the desktop
    echo   - Try running as Administrator
    echo   - Create shortcuts manually using right-click menu
    echo.
)

:: ============================================================================
:: OPTIONAL: TASKBAR PINNING INSTRUCTIONS
:: ============================================================================

if %success_count% gtr 0 (
    echo ========================================================================
    echo                    TASKBAR PINNING (OPTIONAL)
    echo ========================================================================
    echo.
    echo To pin shortcuts to your taskbar:
    echo.
    echo Method 1 - Right-Click:
    echo   1. Right-click on any desktop shortcut
    echo   2. Select "Pin to taskbar"
    echo.
    echo Method 2 - Drag and Drop:
    echo   1. Drag the shortcut from desktop to taskbar
    echo   2. Drop when you see "Pin to taskbar"
    echo.
)

echo ========================================================================
echo.
pause
exit /b 0

:: ============================================================================
:: FUNCTIONS
:: ============================================================================

:CreateShortcut
:: Parameters: Name, Target, Description, WorkingDir, IconPath
:: Creates a shortcut using PowerShell
set "shortcut_name=%~1"
set "target_path=%~2"
set "description=%~3"
set "working_dir=%~4"
set "icon_path=%~5"

:: Check if target exists
if not exist "%target_path%" (
    :: Try without emoji prefix
    set "alt_target=%target_path:📱 =%"
    set "alt_target=!alt_target:🌻 =!"
    set "alt_target=!alt_target:🧠 =!"
    set "alt_target=!alt_target:🔄 =!"
    
    if not exist "!alt_target!" (
        exit /b 1
    ) else (
        set "target_path=!alt_target!"
    )
)

:: Default icon if not specified or doesn't exist
if not exist "%icon_path%" (
    set "icon_path=%SystemRoot%\System32\shell32.dll,3"
)

:: Create PowerShell script for shortcut creation
set "ps_script=%TEMP%\create_shortcut_%RANDOM%.ps1"

(
    echo # Create shortcut
    echo $WshShell = New-Object -ComObject WScript.Shell
    echo $Shortcut = $WshShell.CreateShortcut^("%DESKTOP%\%shortcut_name%.lnk"^)
    echo $Shortcut.TargetPath = "%target_path%"
    echo $Shortcut.WorkingDirectory = "%working_dir%"
    echo $Shortcut.Description = "%description%"
    echo $Shortcut.IconLocation = "%icon_path%"
    echo $Shortcut.WindowStyle = 1
    echo $Shortcut.Save^(^)
    echo.
    echo # Verify creation
    echo if ^(Test-Path "%DESKTOP%\%shortcut_name%.lnk"^) {
    echo     exit 0
    echo } else {
    echo     exit 1
    echo }
) > "%ps_script%"

:: Execute PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%ps_script%" >nul 2>&1
set "result=%ERRORLEVEL%"

:: Clean up temporary script
del "%ps_script%" 2>nul

exit /b %result%

:: ============================================================================
:: END OF SCRIPT
:: ============================================================================

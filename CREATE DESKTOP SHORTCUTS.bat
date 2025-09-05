@echo off
setlocal enabledelayedexpansion
title Desktop Shortcut Creator - Sunflower AI System

:: Colors for output
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "WHITE=[97m"
set "RED=[91m"
set "NC=[0m"

:: Get USB root and desktop paths
set "USB_ROOT=%~dp0"
set "LOG_FILE=%USB_ROOT%system.log"

cls
echo.
echo %CYAN%╔═══════════════════════════════════════════════════════════════╗%NC%
echo %CYAN%║                                                               ║%NC%
echo %CYAN%║              🔗 DESKTOP SHORTCUT CREATOR                      ║%NC%
echo %CYAN%║                                                               ║%NC%
echo %CYAN%║          Create easy-access shortcuts for Sunflower AI       ║%NC%
echo %CYAN%║                                                               ║%NC%
echo %CYAN%╚═══════════════════════════════════════════════════════════════╝%NC%
echo.

:: Log start
echo [%date% %time%] Desktop shortcut creation started >> "%LOG_FILE%"

:: Detect desktop location with multiple fallback methods
call :detect_desktop_location
if errorlevel 1 goto :desktop_detection_failed

echo %BLUE%Desktop Location:%NC% %DESKTOP%
echo %BLUE%USB Location:%NC% %USB_ROOT%
echo.

:: Check if shortcuts already exist and handle appropriately
call :check_existing_shortcuts
if errorlevel 1 goto :user_cancelled

:: Create all shortcuts with comprehensive error handling
call :create_all_shortcuts
if errorlevel 1 goto :shortcut_creation_failed

:: Create removal script for user convenience
call :create_removal_script

:: Show success and offer additional options
call :show_success_and_options

echo [%date% %time%] Desktop shortcuts created successfully >> "%LOG_FILE%"
exit /b 0

:: ============================================================================
:: DESKTOP LOCATION DETECTION
:: ============================================================================

:detect_desktop_location
echo %BLUE%🔍 Detecting desktop location...%NC%

:: Method 1: Current user shell folders registry
for /f "usebackq tokens=3*" %%i in (`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop 2^>nul`) do (
    set "DESKTOP=%%j"
    goto :expand_desktop_path
)

:: Method 2: User shell folders with environment variables
for /f "usebackq tokens=3*" %%i in (`reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop 2^>nul`) do (
    set "DESKTOP=%%j"
    goto :expand_desktop_path
)

:: Method 3: Standard location fallback
set "DESKTOP=%USERPROFILE%\Desktop"
goto :expand_desktop_path

:expand_desktop_path
:: Expand any environment variables in the path
call set "DESKTOP=%DESKTOP%"

:: Verify desktop exists
if not exist "%DESKTOP%" (
    echo %RED%❌ Desktop folder not found at: %DESKTOP%%NC%
    echo.
    echo Trying alternative location...
    
    :: Try OneDrive desktop
    if exist "%USERPROFILE%\OneDrive\Desktop" (
        set "DESKTOP=%USERPROFILE%\OneDrive\Desktop"
        echo %GREEN%✓ Found OneDrive Desktop%NC%
    ) else (
        :: Create desktop folder if it doesn't exist
        mkdir "%USERPROFILE%\Desktop" 2>nul
        set "DESKTOP=%USERPROFILE%\Desktop"
        echo %YELLOW%Created desktop folder%NC%
    )
)

echo %GREEN%✓ Desktop detected: %DESKTOP%%NC%
exit /b 0

:desktop_detection_failed
echo %RED%❌ Failed to detect desktop location%NC%
echo.
echo Please create shortcuts manually by:
echo 1. Right-click on the .bat files in %USB_ROOT%
echo 2. Select "Send to" → "Desktop (create shortcut)"
echo.
pause
exit /b 1

:: ============================================================================
:: CHECK EXISTING SHORTCUTS
:: ============================================================================

:check_existing_shortcuts
echo %BLUE%🔎 Checking for existing shortcuts...%NC%

set "EXISTING_COUNT=0"
set "EXISTING_FILES="

:: Check each potential shortcut
for %%F in (
    "🌻 Sunflower AI System.lnk"
    "🌻 Sunflower Expert AI.lnk"
    "🧠 General Purpose AI.lnk"
    "🔄 Update Sunflower AI.lnk"
) do (
    if exist "%DESKTOP%\%%~F" (
        set /a "EXISTING_COUNT+=1"
        set "EXISTING_FILES=!EXISTING_FILES!  • %%~F\n"
    )
)

if %EXISTING_COUNT% GTR 0 (
    echo %YELLOW%⚠️  Found %EXISTING_COUNT% existing shortcut(s):%NC%
    echo !EXISTING_FILES!
    echo.
    echo What would you like to do?
    echo [1] Replace existing shortcuts
    echo [2] Create shortcuts with unique names
    echo [3] Cancel
    echo.
    set /p "CHOICE=Enter your choice (1-3): "
    
    if "!CHOICE!"=="1" (
        echo %YELLOW%Removing existing shortcuts...%NC%
        call :remove_existing_shortcuts
    ) else if "!CHOICE!"=="2" (
        echo %BLUE%Creating uniquely named shortcuts...%NC%
        set "USE_UNIQUE_NAMES=1"
    ) else (
        echo %YELLOW%Cancelled by user%NC%
        exit /b 1
    )
)

exit /b 0

:user_cancelled
echo.
echo %YELLOW%Operation cancelled%NC%
pause
exit /b 1

:remove_existing_shortcuts
for %%F in (
    "🌻 Sunflower AI System.lnk"
    "🌻 Sunflower Expert AI.lnk"
    "🧠 General Purpose AI.lnk"
    "🔄 Update Sunflower AI.lnk"
) do (
    if exist "%DESKTOP%\%%~F" (
        del "%DESKTOP%\%%~F" 2>nul
    )
)
exit /b 0

:: ============================================================================
:: CREATE ALL SHORTCUTS
:: ============================================================================

:create_all_shortcuts
echo.
echo %CYAN%📌 Creating desktop shortcuts...%NC%
echo.

set "SHORTCUTS_CREATED=0"

:: Define shortcut names (with unique names if requested)
if defined USE_UNIQUE_NAMES (
    set "MAIN_SHORTCUT_NAME=🌻 Sunflower AI System (%date:~-4,4%)"
    set "EXPERT_SHORTCUT_NAME=🌻 Sunflower Expert AI (%date:~-4,4%)"
    set "GENERAL_SHORTCUT_NAME=🧠 General Purpose AI (%date:~-4,4%)"
    set "UPDATE_SHORTCUT_NAME=🔄 Update Sunflower AI (%date:~-4,4%)"
) else (
    set "MAIN_SHORTCUT_NAME=🌻 Sunflower AI System"
    set "EXPERT_SHORTCUT_NAME=🌻 Sunflower Expert AI"
    set "GENERAL_SHORTCUT_NAME=🧠 General Purpose AI"
    set "UPDATE_SHORTCUT_NAME=🔄 Update Sunflower AI"
)

:: Create main system shortcut
echo %YELLOW%[1/4]%NC% Creating main system launcher...
call :create_shortcut "%MAIN_SHORTCUT_NAME%" "📱 CLICK HERE TO START.bat" "Professional AI System - Agricultural Expert + Child Development Specialist"
if not errorlevel 1 (
    echo %GREEN%✅ Main system shortcut created%NC%
    set /a "SHORTCUTS_CREATED+=1"
) else (
    echo %RED%❌ Failed to create main system shortcut%NC%
)

:: Create Sunflower Expert shortcut
echo %YELLOW%[2/4]%NC% Creating Sunflower expert launcher...
call :create_shortcut "%EXPERT_SHORTCUT_NAME%" "🌻 START SUNFLOWER EXPERT.bat" "Combined Agriculture + Child Development Specialist AI"
if not errorlevel 1 (
    echo %GREEN%✅ Sunflower expert shortcut created%NC%
    set /a "SHORTCUTS_CREATED+=1"
) else (
    echo %RED%❌ Failed to create Sunflower expert shortcut%NC%
)

:: Create General AI shortcut
echo %YELLOW%[3/4]%NC% Creating general purpose AI launcher...
call :create_shortcut "%GENERAL_SHORTCUT_NAME%" "🧠 START GENERAL AI.bat" "General Purpose AI for everyday tasks"
if not errorlevel 1 (
    echo %GREEN%✅ General AI shortcut created%NC%
    set /a "SHORTCUTS_CREATED+=1"
) else (
    echo %RED%❌ Failed to create General AI shortcut%NC%
)

:: Create Update shortcut
echo %YELLOW%[4/4]%NC% Creating update launcher...
call :create_shortcut "%UPDATE_SHORTCUT_NAME%" "🔄 UPDATE SYSTEM.bat" "Update Sunflower AI System"
if not errorlevel 1 (
    echo %GREEN%✅ Update shortcut created%NC%
    set /a "SHORTCUTS_CREATED+=1"
) else (
    echo %RED%❌ Failed to create update shortcut%NC%
)

echo.
if %SHORTCUTS_CREATED% EQU 4 (
    echo %GREEN%✅ All shortcuts created successfully!%NC%
    exit /b 0
) else if %SHORTCUTS_CREATED% GTR 0 (
    echo %YELLOW%⚠️  Created %SHORTCUTS_CREATED% of 4 shortcuts%NC%
    exit /b 0
) else (
    echo %RED%❌ No shortcuts were created%NC%
    exit /b 1
)

:shortcut_creation_failed
echo.
echo %RED%❌ Failed to create shortcuts%NC%
echo.
echo You can create shortcuts manually:
echo 1. Navigate to: %USB_ROOT%
echo 2. Right-click each .bat file
echo 3. Select "Send to" → "Desktop (create shortcut)"
echo.
pause
exit /b 1

:: ============================================================================
:: SHORTCUT CREATION METHODS
:: ============================================================================

:create_shortcut
:: Try multiple methods to create shortcut
:: Parameters: %1=shortcut name, %2=target file, %3=description

:: Method 1: PowerShell (most reliable)
call :create_shortcut_powershell %1 %2 %3
if not errorlevel 1 exit /b 0

:: Method 2: VBScript
call :create_shortcut_vbs %1 %2 %3
if not errorlevel 1 exit /b 0

:: Method 3: WSH via command line
call :create_shortcut_wscript %1 %2 %3
if not errorlevel 1 exit /b 0

:: All methods failed
exit /b 1

:create_shortcut_powershell
set "ps_shortcut_name=%~1"
set "ps_target_file=%~2"
set "ps_description=%~3"

powershell -NoProfile -Command "& { ^
    try { ^
        $WScriptShell = New-Object -ComObject WScript.Shell; ^
        $Shortcut = $WScriptShell.CreateShortcut('%DESKTOP%\%ps_shortcut_name%.lnk'); ^
        $Shortcut.TargetPath = '%USB_ROOT%%ps_target_file%'; ^
        $Shortcut.WorkingDirectory = '%USB_ROOT%'; ^
        $Shortcut.Description = '%ps_description%'; ^
        if (Test-Path '%USB_ROOT%sunflower.ico') { ^
            $Shortcut.IconLocation = '%USB_ROOT%sunflower.ico'; ^
        } ^
        $Shortcut.Save(); ^
        Write-Host 'SUCCESS'; ^
        exit 0; ^
    } catch { ^
        Write-Host 'FAILED'; ^
        exit 1; ^
    } ^
}" 2>nul | findstr "SUCCESS" >nul

exit /b %errorlevel%

:create_shortcut_vbs
set "vbs_shortcut_name=%~1"
set "vbs_target_file=%~2"
set "vbs_description=%~3"
set "vbs_file=%TEMP%\create_shortcut_%RANDOM%.vbs"

(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%DESKTOP%\%vbs_shortcut_name%.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%USB_ROOT%%vbs_target_file%"
echo oLink.WorkingDirectory = "%USB_ROOT%"
echo oLink.Description = "%vbs_description%"
echo If objFSO.FileExists^("%USB_ROOT%sunflower.ico"^) Then
echo     oLink.IconLocation = "%USB_ROOT%sunflower.ico"
echo End If
echo oLink.Save
echo WScript.Echo "SUCCESS"
) > "%vbs_file%"

cscript //nologo "%vbs_file%" 2>nul | findstr "SUCCESS" >nul
set "vbs_result=%errorlevel%"
del "%vbs_file%" >nul 2>&1
exit /b %vbs_result%

:create_shortcut_wscript
:: Fallback method using mklink if available
set "ws_shortcut_name=%~1"
set "ws_target_file=%~2"

:: Check if mklink is available (requires admin on older Windows)
mklink >nul 2>&1
if %errorlevel% EQU 9009 (
    exit /b 1
)

:: Try to create symbolic link
mklink "%DESKTOP%\%ws_shortcut_name%.lnk" "%USB_ROOT%%ws_target_file%" >nul 2>&1
exit /b %errorlevel%

:: ============================================================================
:: REMOVAL SCRIPT CREATION
:: ============================================================================

:create_removal_script
echo %BLUE%📝 Creating shortcut removal script...%NC%

(
echo @echo off
echo title Remove Sunflower AI Desktop Shortcuts
echo.
echo echo Removing Sunflower AI desktop shortcuts...
echo echo.
echo del "%DESKTOP%\🌻 Sunflower AI System.lnk" 2^>nul
echo del "%DESKTOP%\🌻 Sunflower Expert AI.lnk" 2^>nul  
echo del "%DESKTOP%\🧠 General Purpose AI.lnk" 2^>nul
echo del "%DESKTOP%\🔄 Update Sunflower AI.lnk" 2^>nul
echo.
echo :: Also remove any uniquely named versions
echo for %%%%f in ^("%DESKTOP%\🌻 Sunflower AI System ^(*^).lnk"^) do del "%%%%f" 2^>nul
echo for %%%%f in ^("%DESKTOP%\🌻 Sunflower Expert AI ^(*^).lnk"^) do del "%%%%f" 2^>nul
echo for %%%%f in ^("%DESKTOP%\🧠 General Purpose AI ^(*^).lnk"^) do del "%%%%f" 2^>nul
echo for %%%%f in ^("%DESKTOP%\🔄 Update Sunflower AI ^(*^).lnk"^) do del "%%%%f" 2^>nul
echo.
echo echo Desktop shortcuts removed.
echo echo.
echo pause
) > "%USB_ROOT%🗑️ REMOVE DESKTOP SHORTCUTS.bat"

if exist "%USB_ROOT%🗑️ REMOVE DESKTOP SHORTCUTS.bat" (
    echo %GREEN%✅ Removal script created%NC%
) else (
    echo %YELLOW%⚠️  Could not create removal script%NC%
)
exit /b 0

:: ============================================================================
:: SUCCESS AND OPTIONS
:: ============================================================================

:show_success_and_options
echo.
echo %GREEN%╔═══════════════════════════════════════════════════════════════╗%NC%
echo %GREEN%║                                                               ║%NC%
echo %GREEN%║                    ✅ SHORTCUTS CREATED!                      ║%NC%
echo %GREEN%║                                                               ║%NC%
echo %GREEN%╚═══════════════════════════════════════════════════════════════╝%NC%
echo.
echo Your desktop shortcuts are ready to use:
echo.
echo   %CYAN%🌻 Sunflower AI System%NC% - Main menu and setup
echo   %CYAN%🌻 Sunflower Expert AI%NC% - Agricultural + Child Development
echo   %CYAN%🧠 General Purpose AI%NC% - Everyday assistant
echo   %CYAN%🔄 Update Sunflower AI%NC% - Check for updates
echo.
echo %YELLOW%💡 Tips:%NC%
echo   • Double-click any shortcut to start
echo   • Right-click and "Pin to taskbar" for quick access
echo   • To remove shortcuts, run: 🗑️ REMOVE DESKTOP SHORTCUTS.bat
echo.
echo %BLUE%Next steps:%NC%
echo   1. Close this window
echo   2. Go to your desktop
echo   3. Double-click "🌻 Sunflower AI System" to begin!
echo.
echo %GREEN%Press any key to finish...%NC%
pause >nul
exit /b 0

:: ============================================================================
:: ERROR HANDLERS
:: ============================================================================

:error_no_desktop
echo %RED%ERROR: Could not find desktop folder%NC%
echo Please create shortcuts manually
pause
exit /b 1

:error_no_usb
echo %RED%ERROR: Not running from USB drive%NC%
echo Please run this from the Sunflower AI USB drive
pause
exit /b 1

:error_creation_failed
echo %RED%ERROR: Failed to create shortcuts%NC%
echo This may require administrator privileges
echo.
echo Try right-clicking this file and selecting "Run as administrator"
pause
exit /b 1

endlocal

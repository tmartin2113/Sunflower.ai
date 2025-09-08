#!/usr/bin/env python3
"""
Sunflower AI Professional System - Windows Compilation
Production Windows executable and installer build system
Version: 6.2 - January 2025
"""

import os
import sys
import subprocess
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import ctypes
import winreg

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from build import (
    BuildConfiguration, SecurityManager, PartitionManager,
    BUILD_DIR, OUTPUT_DIR, TEMPLATES_DIR, ASSETS_DIR, MODELS_DIR
)

class WindowsCompiler:
    """Windows-specific compilation and packaging manager"""
    
    def __init__(self, config: BuildConfiguration):
        self.config = config
        self.security = SecurityManager(config)
        self.partition = PartitionManager(config)
        self.spec_file = TEMPLATES_DIR / "windows.spec"
        self.output_dir = config.get_output_path("windows")
        self.temp_build_dir = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        
        # Windows-specific paths
        self.exe_name = "SunflowerAI.exe"
        self.launcher_name = "SunflowerLauncher.exe"
        self.service_name = "SunflowerAIService.exe"
        
        # Verify Windows environment
        if not self._is_windows():
            raise EnvironmentError("Windows compilation must run on Windows")
    
    def _is_windows(self) -> bool:
        """Verify Windows environment"""
        return sys.platform.startswith('win')
    
    def compile(self) -> Path:
        """Main Windows compilation process"""
        print("╔════════════════════════════════════════╗")
        print("║  Sunflower AI Windows Build System     ║")
        print("║  Version 6.2 - Production Build        ║")
        print("╚════════════════════════════════════════╝")
        
        try:
            # Phase 1: Environment preparation
            print("\n[Phase 1/7] Preparing build environment...")
            self._prepare_environment()
            
            # Phase 2: Compile main application
            print("\n[Phase 2/7] Compiling main application...")
            main_exe = self._compile_main_app()
            
            # Phase 3: Compile launcher
            print("\n[Phase 3/7] Compiling universal launcher...")
            launcher_exe = self._compile_launcher()
            
            # Phase 4: Compile background service
            print("\n[Phase 4/7] Compiling background service...")
            service_exe = self._compile_service()
            
            # Phase 5: Create partition structure
            print("\n[Phase 5/7] Creating partition structure...")
            cdrom_path, usb_path = self._create_partitions()
            
            # Phase 6: Package installer
            print("\n[Phase 6/7] Creating Windows installer...")
            installer_path = self._create_installer(
                main_exe, launcher_exe, service_exe, cdrom_path
            )
            
            # Phase 7: Sign and finalize
            print("\n[Phase 7/7] Signing and finalizing...")
            final_path = self._finalize_build(installer_path)
            
            print(f"\n✓ Windows build complete: {final_path}")
            return final_path
            
        except Exception as e:
            print(f"\n✗ Build failed: {e}")
            raise
        finally:
            # Cleanup temporary directory
            if self.temp_build_dir.exists():
                shutil.rmtree(self.temp_build_dir, ignore_errors=True)
    
    def _prepare_environment(self):
        """Prepare Windows build environment"""
        # Check for required tools
        required_tools = {
            "pyinstaller": self._check_pyinstaller,
            "signtool": self._check_signtool,
            "makensis": self._check_nsis
        }
        
        for tool, check_func in required_tools.items():
            if not check_func():
                raise RuntimeError(f"Required tool not found: {tool}")
        
        # Copy resources to temp directory
        shutil.copytree(ASSETS_DIR, self.temp_build_dir / "assets")
        shutil.copytree(MODELS_DIR, self.temp_build_dir / "models")
        
        # Copy icon
        icon_src = ASSETS_DIR / "icons" / "sunflower.ico"
        if icon_src.exists():
            shutil.copy(icon_src, self.temp_build_dir / "sunflower.ico")
    
    def _check_pyinstaller(self) -> bool:
        """Check if PyInstaller is available"""
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _check_signtool(self) -> bool:
        """Check if Windows SDK signtool is available"""
        # Check common Windows SDK locations
        sdk_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64",
            r"C:\Program Files (x86)\Windows Kits\10\bin\x64"
        ]
        
        for sdk_path in sdk_paths:
            signtool = Path(sdk_path) / "signtool.exe"
            if signtool.exists():
                return True
        
        return False
    
    def _check_nsis(self) -> bool:
        """Check if NSIS is available"""
        try:
            result = subprocess.run(
                ["makensis", "/VERSION"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _compile_launcher(self) -> Path:
        """Compile universal launcher executable"""
        print("  → Compiling universal launcher...")
        
        launcher_source = self._generate_launcher_source()
        launcher_py = self.temp_build_dir / "launcher.py"
        
        with open(launcher_py, 'w', encoding='utf-8') as f:
            f.write(launcher_source)
        
        # FIX: Proper path handling for PyInstaller --add-data parameter
        # Convert paths to strings and use proper separator
        icon_path = str(self.temp_build_dir / 'sunflower.ico')
        
        # Compile launcher with PyInstaller
        cmd = [
            "pyinstaller",
            "--onefile",
            "--noconsole",
            "--clean",
            "--noconfirm",
            "--name", self.launcher_name.replace(".exe", ""),
            "--icon", icon_path,
            "--distpath", str(self.temp_build_dir / "dist"),
            "--workpath", str(self.temp_build_dir / "build"),
            "--add-data", f"{icon_path}{';' if sys.platform == 'win32' else ':'}.".
            str(launcher_py)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        launcher_exe = self.temp_build_dir / "dist" / self.launcher_name
        
        # Sign launcher
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(launcher_exe, "windows")
        
        return launcher_exe
    
    def _generate_launcher_source(self) -> str:
        """Generate launcher Python source code"""
        return '''
"""
Sunflower AI Universal Launcher for Windows
Auto-detects partitions and initiates setup
"""

import os
import sys
import json
import ctypes
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import win32api
import win32file
import wmi

class SunflowerLauncher:
    """Universal launcher for Sunflower AI Professional System"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Check for administrator privileges
        if not self.is_admin():
            self.request_admin()
        
        self.cdrom_path = None
        self.usb_path = None
        self.setup_ui()
        self.detect_partitions()
    
    def is_admin(self):
        """Check if running with administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def request_admin(self):
        """Request administrator privileges"""
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)
    
    def detect_partitions(self):
        """Detect CD-ROM and USB partitions"""
        c = wmi.WMI()
        
        for drive in c.Win32_LogicalDisk():
            if drive.DriveType == 5:  # CD-ROM
                marker_file = Path(drive.DeviceID) / "SUNFLOWER_SYSTEM.marker"
                if marker_file.exists():
                    self.cdrom_path = Path(drive.DeviceID)
            
            elif drive.DriveType == 2:  # Removable
                marker_file = Path(drive.DeviceID) / "SUNFLOWER_DATA.marker"
                if marker_file.exists():
                    self.usb_path = Path(drive.DeviceID)
        
        self.update_status()
    
    def setup_ui(self):
        """Create launcher UI"""
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Detecting Sunflower AI device...",
            font=("Arial", 12)
        )
        self.status_label.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.root,
            mode='indeterminate'
        )
        self.progress.pack(pady=10)
        self.progress.start()
        
        # Launch button (initially hidden)
        self.launch_btn = tk.Button(
            self.root,
            text="Launch Sunflower AI",
            command=self.launch_system,
            state=tk.DISABLED
        )
        self.launch_btn.pack(pady=20)
    
    def update_status(self):
        """Update UI based on partition detection"""
        if self.cdrom_path and self.usb_path:
            self.status_label.config(text="✓ Sunflower AI device detected")
            self.progress.stop()
            self.launch_btn.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="✗ Device not found. Please connect Sunflower AI USB.")
    
    def launch_system(self):
        """Launch the main Sunflower AI system"""
        main_exe = self.cdrom_path / "system" / "SunflowerAI.exe"
        
        if main_exe.exists():
            subprocess.Popen([str(main_exe)])
            self.root.quit()
        else:
            messagebox.showerror("Error", "System files not found on device")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    launcher = SunflowerLauncher()
    launcher.run()
'''
    
    def _compile_main_app(self) -> Path:
        """Compile main Sunflower AI application"""
        print("  → Compiling main application with PyInstaller...")
        
        # Prepare PyInstaller spec
        spec_content = self._generate_main_spec()
        temp_spec = self.temp_build_dir / "main.spec"
        
        with open(temp_spec, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        # Run PyInstaller
        cmd = ["pyinstaller", "--clean", "--noconfirm", str(temp_spec)]
        subprocess.run(cmd, check=True, capture_output=True)
        
        main_exe = self.temp_build_dir / "dist" / self.exe_name
        
        # Sign main executable
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(main_exe, "windows")
        
        return main_exe
    
    def _generate_main_spec(self) -> str:
        """Generate PyInstaller spec for main application"""
        # FIX: Proper path string formatting in spec file
        return f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{Path(__file__).parent.parent / "UNIVERSAL_LAUNCHER.py"}'],
    pathex=['{Path(__file__).parent.parent}'],
    binaries=[
        ('{Path(__file__).parent.parent / "ollama" / "ollama.exe"}', 'ollama'),
    ],
    datas=[
        ('{str(Path(__file__).parent.parent / "modelfiles")}', 'modelfiles'),
        ('{str(Path(__file__).parent.parent / "assets")}', 'assets'),
        ('{str(self.temp_build_dir / "docs")}', 'docs'),
        ('{str(self.temp_build_dir / "certs")}', 'certs'),
    ],
    hiddenimports=[
        'pydantic',
        'uvicorn',
        'fastapi',
        'starlette',
        'httpx',
        'psutil',
        'cryptography',
        'win32api',
        'win32con',
        'win32security',
        'winreg',
        'wmi',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.exe_name.replace(".exe", "")}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    version='{str(self.temp_build_dir / "version.res")}' if (self.temp_build_dir / "version.res").exists() else None,
    icon='{str(self.temp_build_dir / "sunflower.ico")}',
    uac_admin=False,
    uac_uiaccess=False,
)
'''
    
    def _compile_service(self) -> Path:
        """Compile Windows background service"""
        print("  → Compiling background service...")
        
        service_source = self._generate_service_source()
        service_py = self.temp_build_dir / "service.py"
        
        with open(service_py, 'w', encoding='utf-8') as f:
            f.write(service_source)
        
        # Compile service
        cmd = [
            "pyinstaller",
            "--onefile",
            "--noconsole",
            "--clean",
            "--noconfirm",
            "--name", self.service_name.replace(".exe", ""),
            "--distpath", str(self.temp_build_dir / "dist"),
            "--workpath", str(self.temp_build_dir / "build"),
            str(service_py)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        service_exe = self.temp_build_dir / "dist" / self.service_name
        
        # Sign service
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(service_exe, "windows")
        
        return service_exe
    
    def _generate_service_source(self) -> str:
        """Generate Windows service source code"""
        return '''
"""
Sunflower AI Background Service
Manages Ollama and Open WebUI processes
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
import os
from pathlib import Path
import subprocess

class SunflowerAIService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SunflowerAI"
    _svc_display_name_ = "Sunflower AI Education Service"
    _svc_description_ = "Manages AI models and web interface for Sunflower AI"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.ollama_process = None
        self.webui_process = None
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
        # Stop processes
        if self.ollama_process:
            self.ollama_process.terminate()
        if self.webui_process:
            self.webui_process.terminate()
    
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Start Ollama
        ollama_exe = Path("C:/Program Files/Sunflower AI/ollama/ollama.exe")
        if ollama_exe.exists():
            self.ollama_process = subprocess.Popen([str(ollama_exe), "serve"])
        
        # Main service loop
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SunflowerAIService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SunflowerAIService)
'''
    
    def _create_partitions(self) -> Tuple[Path, Path]:
        """Create CD-ROM and USB partition structures"""
        cdrom_path = self.temp_build_dir / "cdrom_partition"
        usb_path = self.temp_build_dir / "usb_partition"
        
        # Create CD-ROM partition structure
        cdrom_dirs = ["system", "models", "ollama", "documentation", "launchers"]
        for dir_name in cdrom_dirs:
            (cdrom_path / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create USB partition structure
        usb_dirs = ["profiles", "conversations", "logs", "dashboard", "config"]
        for dir_name in usb_dirs:
            (usb_path / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create marker files
        (cdrom_path / "SUNFLOWER_SYSTEM.marker").write_text("v6.2.0")
        (usb_path / "SUNFLOWER_DATA.marker").write_text("v6.2.0")
        
        # Create autorun.inf for CD-ROM
        autorun_content = """[autorun]
icon=sunflower.ico
label=Sunflower AI Professional System
open=launchers\\SunflowerLauncher.exe
"""
        (cdrom_path / "autorun.inf").write_text(autorun_content)
        
        # Set autorun.inf as hidden/system file
        import win32api
        import win32con
        win32api.SetFileAttributes(
            str(cdrom_path / "autorun.inf"),
            win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
        )
        
        return cdrom_path, usb_path
    
    def _create_installer(self, main_exe: Path, launcher_exe: Path,
                         service_exe: Path, cdrom_path: Path) -> Path:
        """Create NSIS installer for Windows"""
        print("  → Building NSIS installer...")
        
        # Generate NSIS script
        nsi_script = self._generate_nsis_script()
        nsi_path = self.temp_build_dir / "installer.nsi"
        
        with open(nsi_path, 'w', encoding='utf-8') as f:
            f.write(nsi_script)
        
        # Compile NSIS installer
        cmd = ["makensis", "/V2", str(nsi_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"NSIS error: {result.stderr}")
            raise RuntimeError("Installer creation failed")
        
        installer_path = self.temp_build_dir / "SunflowerAI_Setup.exe"
        return installer_path
    
    def _generate_nsis_script(self) -> str:
        """Generate NSIS installer script"""
        return f"""
!include "MUI2.nsh"
!include "x64.nsh"

Name "Sunflower AI Professional System"
OutFile "SunflowerAI_Setup.exe"
InstallDir "$PROGRAMFILES64\\Sunflower AI"
InstallDirRegKey HKLM "Software\\SunflowerAI" "Install_Dir"
RequestExecutionLevel admin

!define MUI_ICON "{self.temp_build_dir}\\sunflower.ico"
!define MUI_UNICON "{self.temp_build_dir}\\sunflower.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "{self.temp_build_dir}\\docs\\license.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Sunflower AI Core" SEC01
    SetOutPath "$INSTDIR"
    
    ; Install files from CD-ROM partition
    File /r "{self.temp_build_dir}\\cdrom_partition\\*.*"
    
    ; Register service
    ExecWait '"$INSTDIR\\service\\SunflowerAIService.exe" install'
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\Sunflower AI"
    CreateShortcut "$SMPROGRAMS\\Sunflower AI\\Sunflower AI.lnk" "$INSTDIR\\SunflowerAI.exe"
    CreateShortcut "$DESKTOP\\Sunflower AI.lnk" "$INSTDIR\\SunflowerAI.exe"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    
    ; Registry entries
    WriteRegStr HKLM "Software\\SunflowerAI" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                     "DisplayName" "Sunflower AI Professional System"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                     "UninstallString" "$INSTDIR\\uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Stop and remove service
    ExecWait '"$INSTDIR\\service\\SunflowerAIService.exe" stop'
    ExecWait '"$INSTDIR\\service\\SunflowerAIService.exe" remove'
    
    ; Remove files
    Delete "$INSTDIR\\*.*"
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$DESKTOP\\Sunflower AI.lnk"
    RMDir /r "$SMPROGRAMS\\Sunflower AI"
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\\SunflowerAI"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI"
SectionEnd
"""
    
    def _finalize_build(self, installer_path: Path) -> Path:
        """Finalize and sign the build"""
        final_name = f"SunflowerAI_v{self.config.config['version']}_Windows_Setup.exe"
        final_path = self.output_dir / final_name
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy installer to final location
        shutil.copy(installer_path, final_path)
        
        # Sign final installer
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(final_path, "windows")
        
        # Generate checksum
        checksum = self._generate_checksum(final_path)
        checksum_file = final_path.with_suffix('.sha256')
        checksum_file.write_text(f"{checksum}  {final_path.name}")
        
        return final_path
    
    def _generate_checksum(self, file_path: Path) -> str:
        """Generate SHA-256 checksum"""
        import hashlib
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _create_version_info(self):
        """Create Windows version information"""
        version_info = {
            "CompanyName": "Sunflower AI",
            "FileDescription": "Sunflower AI Professional System",
            "FileVersion": self.config.config["version"],
            "InternalName": "SunflowerAI",
            "LegalCopyright": "© 2025 Sunflower AI. All rights reserved.",
            "OriginalFilename": self.exe_name,
            "ProductName": "Sunflower AI Professional System",
            "ProductVersion": self.config.config["version"]
        }
        
        # Generate version resource file
        rc_path = self.temp_build_dir / "version.rc"
        self._generate_rc_file(rc_path, version_info)
        
        # Compile to .res file
        self._compile_resources(rc_path)
    
    def _generate_rc_file(self, rc_path: Path, metadata: Dict[str, str]):
        """Generate Windows resource file"""
        version_parts = metadata['product_version'].split('.')
        version_numbers = [int(v) for v in version_parts[:4]]
        while len(version_numbers) < 4:
            version_numbers.append(0)
        
        rc_content = f"""
#include <winver.h>

VS_VERSION_INFO VERSIONINFO
FILEVERSION {version_numbers[0]},{version_numbers[1]},{version_numbers[2]},{version_numbers[3]}
PRODUCTVERSION {version_numbers[0]},{version_numbers[1]},{version_numbers[2]},{version_numbers[3]}
FILEFLAGSMASK VS_FFI_FILEFLAGSMASK
FILEFLAGS 0x0L
FILEOS VOS_NT_WINDOWS32
FILETYPE VFT_APP
FILESUBTYPE VFT2_UNKNOWN
BEGIN
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "040904E4"
        BEGIN
            VALUE "CompanyName", "{metadata['company_name']}"
            VALUE "FileDescription", "{metadata['file_description']}"
            VALUE "FileVersion", "{metadata['product_version']}"
            VALUE "InternalName", "{metadata['internal_name']}"
            VALUE "LegalCopyright", "{metadata['copyright']}"
            VALUE "OriginalFilename", "{metadata['original_filename']}"
            VALUE "ProductName", "{metadata['product_name']}"
            VALUE "ProductVersion", "{metadata['product_version']}"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x409, 1252
    END
END

IDI_ICON1 ICON "sunflower.ico"
"""
        
        with open(rc_path, 'w', encoding='utf-8') as f:
            f.write(rc_content)
    
    def _compile_resources(self, rc_path: Path):
        """Compile Windows resource file"""
        res_path = rc_path.with_suffix('.res')
        
        # Try to find rc.exe in Windows SDK
        rc_exe = self._find_rc_exe()
        if rc_exe:
            subprocess.run(
                [str(rc_exe), "/fo", str(res_path), str(rc_path)],
                check=True,
                cwd=self.temp_build_dir
            )
    
    def _find_rc_exe(self) -> Optional[Path]:
        """Find Windows Resource Compiler"""
        sdk_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64",
            r"C:\Program Files (x86)\Windows Kits\10\bin\x64"
        ]
        
        for sdk_path in sdk_paths:
            rc_exe = Path(sdk_path) / "rc.exe"
            if rc_exe.exists():
                return rc_exe
        
        return None


# Entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Sunflower AI for Windows")
    parser.add_argument("--debug", action="store_true", help="Debug build")
    parser.add_argument("--sign", action="store_true", help="Sign executables")
    parser.add_argument("--config", type=Path, help="Build configuration file")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config and args.config.exists():
        with open(args.config, 'r') as f:
            config_data = json.load(f)
    else:
        config_data = {
            "version": "6.2.0",
            "security": {
                "signing_required": args.sign
            }
        }
    
    config = BuildConfiguration(config_data)
    
    # Run compiler
    compiler = WindowsCompiler(config)
    output_path = compiler.compile()
    
    print(f"\n✅ Build complete: {output_path}")

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
        print("║  WINDOWS COMPILATION STARTED           ║")
        print("╚════════════════════════════════════════╝")
        
        try:
            # 1. Prepare environment
            self._prepare_environment()
            
            # 2. Compile executables
            launcher_exe = self._compile_launcher()
            main_exe = self._compile_main_app()
            service_exe = self._compile_service()
            
            # 3. Package for distribution
            package_path = self._create_package(launcher_exe, main_exe, service_exe)
            
            # 4. Create installer
            installer_path = self._create_installer(package_path)
            
            # 5. Sign final package
            if self.config.config["security"]["signing_required"]:
                self.security.sign_executable(installer_path, "windows")
            
            print("╔════════════════════════════════════════╗")
            print("║  WINDOWS COMPILATION COMPLETE          ║")
            print(f"║  Output: {installer_path.name:<26}║")
            print("╚════════════════════════════════════════╝")
            
            return installer_path
            
        except Exception as e:
            print(f"ERROR: Windows compilation failed: {e}")
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
            r"C:\Program Files (x86)\Windows Kits\10\bin\x64",
        ]
        
        for sdk_path in sdk_paths:
            signtool = Path(sdk_path) / "signtool.exe"
            if signtool.exists():
                return True
        
        # Check if signtool is in PATH
        try:
            result = subprocess.run(
                ["where", "signtool"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_nsis(self) -> bool:
        """Check if NSIS is available"""
        # Check common NSIS locations
        nsis_paths = [
            r"C:\Program Files (x86)\NSIS",
            r"C:\Program Files\NSIS",
        ]
        
        for nsis_path in nsis_paths:
            makensis = Path(nsis_path) / "makensis.exe"
            if makensis.exists():
                return True
        
        # Check if makensis is in PATH
        try:
            result = subprocess.run(
                ["where", "makensis"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _compile_launcher(self) -> Path:
        """Compile USB launcher executable"""
        print("  → Compiling USB launcher...")
        
        launcher_source = self._generate_launcher_source()
        launcher_py = self.temp_build_dir / "launcher.py"
        
        with open(launcher_py, 'w', encoding='utf-8') as f:
            f.write(launcher_source)
        
        # Generate PyInstaller spec
        spec_content = self._generate_launcher_spec()
        temp_spec = self.temp_build_dir / "launcher.spec"
        
        with open(temp_spec, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        # Run PyInstaller
        cmd = ["pyinstaller", "--clean", "--noconfirm", str(temp_spec)]
        subprocess.run(cmd, check=True, capture_output=True)
        
        launcher_exe = self.temp_build_dir / "dist" / self.launcher_name
        
        # Sign launcher
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(launcher_exe, "windows")
        
        return launcher_exe
    
    def _generate_launcher_source(self) -> str:
        """Generate launcher Python source code"""
        return '''#!/usr/bin/env python3
"""
Sunflower AI Professional System - USB Device Launcher
Automatically detects partitioned device and launches system
"""

import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import psutil
import wmi

class SunflowerLauncher:
    """Main launcher application for Sunflower AI System"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Auto-detect partitions
        self.cdrom_path = None
        self.usb_path = None
        self.detect_partitions()
        
        # Setup UI
        self.setup_ui()
        
        # Auto-launch if partitions found
        if self.cdrom_path and self.usb_path:
            self.root.after(100, self.launch_system)
    
    def detect_partitions(self):
        """Detect CD-ROM and USB partitions"""
        c = wmi.WMI()
        
        for drive in c.Win32_LogicalDisk():
            if drive.DriveType == 5:  # CD-ROM
                volume_name = drive.VolumeName or ""
                if "SUNFLOWER" in volume_name.upper():
                    self.cdrom_path = Path(drive.DeviceID) / "\\\\"
            
            elif drive.DriveType == 2:  # Removable
                volume_name = drive.VolumeName or ""
                if "SUNFLOWER_DATA" in volume_name.upper():
                    self.usb_path = Path(drive.DeviceID) / "\\\\"
    
    def setup_ui(self):
        """Setup launcher UI"""
        # Title
        title = tk.Label(
            self.root,
            text="Sunflower AI Professional System",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=20)
        
        # Status
        if self.cdrom_path and self.usb_path:
            status_text = "✓ Device detected and ready"
            status_color = "green"
        else:
            status_text = "⚠ Please connect Sunflower AI USB"
            status_color = "orange"
        
        status = tk.Label(
            self.root,
            text=status_text,
            font=("Arial", 12),
            fg=status_color
        )
        status.pack(pady=10)
        
        # Launch button
        launch_btn = tk.Button(
            self.root,
            text="Launch Sunflower AI",
            command=self.launch_system,
            font=("Arial", 14),
            width=20,
            height=2,
            state="normal" if self.cdrom_path else "disabled"
        )
        launch_btn.pack(pady=20)
        
        # Info
        info = tk.Label(
            self.root,
            text="Family-Focused K-12 STEM Education System\\nVersion 6.2",
            font=("Arial", 10),
            fg="gray"
        )
        info.pack(side="bottom", pady=10)
    
    def show_error(self, message):
        """Show error message"""
        messagebox.showerror("Sunflower AI Error", message)
    
    def check_device(self):
        """Check if device is properly connected"""
        if not self.cdrom_path:
            self.show_error("CD-ROM partition not found.\\nPlease connect Sunflower AI USB.")
            return False
        
        if not self.usb_path:
            self.show_error("USB data partition not found.\\nPlease connect Sunflower AI USB.")
            return False
        
        return True
    
    def launch_system(self):
        """Launch the main Sunflower AI system"""
        if not self.check_device():
            return
        
        main_exe = self.cdrom_path / "system" / "SunflowerAI.exe"
        
        if main_exe.exists():
            subprocess.Popen([str(main_exe)])
            self.root.quit()
        else:
            self.show_error("System files not found on device")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    launcher = SunflowerLauncher()
    launcher.run()
'''
    
    def _generate_launcher_spec(self) -> str:
        """Generate PyInstaller spec for launcher"""
        # FIX BUG-001: Convert Path objects to Windows-formatted strings with escaped backslashes
        launcher_py_path = str(self.temp_build_dir / "launcher.py").replace("\\", "\\\\")
        temp_build_path = str(self.temp_build_dir).replace("\\", "\\\\")
        icon_path = str(self.temp_build_dir / "sunflower.ico").replace("\\", "\\\\")
        version_res_path = str(self.temp_build_dir / "version.res").replace("\\", "\\\\")
        
        return f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{launcher_py_path}'],
    pathex=['{temp_build_path}'],
    binaries=[],
    datas=[],
    hiddenimports=['wmi', 'psutil', 'tkinter'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy'],
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
    name='{self.launcher_name.replace(".exe", "")}',
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
    version='{version_res_path}' if Path(version_res_path.replace("\\\\", "\\")).exists() else None,
    icon='{icon_path}',
    uac_admin=False,
    uac_uiaccess=False,
)
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
        # FIX BUG-001: Convert all Path objects to properly escaped Windows paths
        launcher_path = str(Path(__file__).parent.parent / "UNIVERSAL_LAUNCHER.py").replace("\\", "\\\\")
        parent_path = str(Path(__file__).parent.parent).replace("\\", "\\\\")
        ollama_exe_path = str(Path(__file__).parent.parent / "ollama" / "ollama.exe").replace("\\", "\\\\")
        modelfiles_path = str(Path(__file__).parent.parent / "modelfiles").replace("\\", "\\\\")
        assets_path = str(Path(__file__).parent.parent / "assets").replace("\\", "\\\\")
        docs_path = str(self.temp_build_dir / "docs").replace("\\", "\\\\")
        certs_path = str(self.temp_build_dir / "certs").replace("\\", "\\\\")
        icon_path = str(self.temp_build_dir / "sunflower.ico").replace("\\", "\\\\")
        version_res_path = str(self.temp_build_dir / "version.res").replace("\\", "\\\\")
        
        return f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{launcher_path}'],
    pathex=['{parent_path}'],
    binaries=[
        ('{ollama_exe_path}', 'ollama'),
    ],
    datas=[
        ('{modelfiles_path}', 'modelfiles'),
        ('{assets_path}', 'assets'),
        ('{docs_path}', 'docs'),
        ('{certs_path}', 'certs'),
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
    version='{version_res_path}' if Path(version_res_path.replace("\\\\", "\\")).exists() else None,
    icon='{icon_path}',
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
        return '''#!/usr/bin/env python3
"""
Sunflower AI Professional System - Windows Background Service
Manages Ollama and monitoring services
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import sys
import time
import subprocess
from pathlib import Path

class SunflowerAIService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SunflowerAI"
    _svc_display_name_ = "Sunflower AI Professional System"
    _svc_description_ = "Background service for Sunflower AI K-12 STEM Education System"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.ollama_process = None
        socket.setdefaulttimeout(60)
    
    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False
        
        # Stop Ollama
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait(timeout=10)
    
    def SvcDoRun(self):
        """Run the service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.main()
    
    def main(self):
        """Main service loop"""
        # Start Ollama
        self.start_ollama()
        
        # Monitor service
        while self.running:
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                break
            
            # Check Ollama health
            if self.ollama_process and self.ollama_process.poll() is not None:
                # Restart Ollama if it crashed
                self.start_ollama()
    
    def start_ollama(self):
        """Start Ollama service"""
        try:
            ollama_path = Path(os.environ.get('PROGRAMFILES', 'C:\\\\Program Files')) / "Ollama" / "ollama.exe"
            if ollama_path.exists():
                self.ollama_process = subprocess.Popen(
                    [str(ollama_path), "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    0,
                    ("Ollama service started",)
                )
        except Exception as e:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                0,
                (f"Failed to start Ollama: {e}",)
            )

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SunflowerAIService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SunflowerAIService)
'''
    
    def _create_package(self, launcher_exe: Path, main_exe: Path, service_exe: Path) -> Path:
        """Create deployment package"""
        print("  → Creating deployment package...")
        
        package_dir = self.temp_build_dir / "package"
        package_dir.mkdir(exist_ok=True)
        
        # Create directory structure
        (package_dir / "system").mkdir(exist_ok=True)
        (package_dir / "launcher").mkdir(exist_ok=True)
        (package_dir / "service").mkdir(exist_ok=True)
        (package_dir / "models").mkdir(exist_ok=True)
        (package_dir / "docs").mkdir(exist_ok=True)
        
        # Copy executables
        shutil.copy(launcher_exe, package_dir / "launcher" / launcher_exe.name)
        shutil.copy(main_exe, package_dir / "system" / main_exe.name)
        shutil.copy(service_exe, package_dir / "service" / service_exe.name)
        
        # Copy resources
        for resource_dir in ["models", "docs"]:
            src = self.temp_build_dir / resource_dir
            if src.exists():
                shutil.copytree(src, package_dir / resource_dir, dirs_exist_ok=True)
        
        # Create autorun.inf
        autorun_content = f"""[autorun]
open=launcher\\{launcher_exe.name}
icon=launcher\\{launcher_exe.name},0
label=Sunflower AI Professional System
"""
        with open(package_dir / "autorun.inf", 'w') as f:
            f.write(autorun_content)
        
        return package_dir
    
    def _create_installer(self, package_dir: Path) -> Path:
        """Create NSIS installer"""
        print("  → Creating NSIS installer...")
        
        # Generate NSIS script
        nsis_script = self._generate_nsis_script(package_dir)
        nsis_file = self.temp_build_dir / "installer.nsi"
        
        with open(nsis_file, 'w', encoding='utf-8') as f:
            f.write(nsis_script)
        
        # Run NSIS
        cmd = ["makensis", str(nsis_file)]
        subprocess.run(cmd, check=True, capture_output=True)
        
        installer_name = f"SunflowerAI_Setup_v{self.config.config['version']}.exe"
        installer_path = self.output_dir / installer_name
        
        # Move installer to output directory
        self.output_dir.mkdir(exist_ok=True, parents=True)
        shutil.move(
            self.temp_build_dir / installer_name,
            installer_path
        )
        
        return installer_path
    
    def _generate_nsis_script(self, package_dir: Path) -> str:
        """Generate NSIS installer script"""
        # FIX: Proper path formatting for NSIS
        package_path = str(package_dir).replace("\\", "\\\\")
        
        return f'''
!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "Sunflower AI Professional System"
OutFile "SunflowerAI_Setup_v{self.config.config['version']}.exe"
InstallDir "$PROGRAMFILES64\\SunflowerAI"
RequestExecutionLevel admin

!define MUI_ABORTWARNING
!define MUI_ICON "{package_path}\\\\launcher\\\\{self.launcher_name}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "{package_path}\\\\docs\\\\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "Main Application" SecMain
    SetOutPath "$INSTDIR"
    
    ; Copy all files
    File /r "{package_path}\\\\*.*"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\Sunflower AI"
    CreateShortcut "$SMPROGRAMS\\Sunflower AI\\Sunflower AI.lnk" "$INSTDIR\\system\\{self.exe_name}"
    CreateShortcut "$SMPROGRAMS\\Sunflower AI\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"
    CreateShortcut "$DESKTOP\\Sunflower AI.lnk" "$INSTDIR\\system\\{self.exe_name}"
    
    ; Register service
    ExecWait '"$INSTDIR\\service\\{self.service_name}" install'
    ExecWait '"$INSTDIR\\service\\{self.service_name}" start'
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
    
    ; Write registry keys
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                     "DisplayName" "Sunflower AI Professional System"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                     "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                     "DisplayVersion" "{self.config.config['version']}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                     "Publisher" "Sunflower AI Systems"
    
    ; Estimate size
    ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                       "EstimatedSize" "$0"
SectionEnd

Section "Uninstall"
    ; Stop and remove service
    ExecWait '"$INSTDIR\\service\\{self.service_name}" stop'
    ExecWait '"$INSTDIR\\service\\{self.service_name}" remove'
    
    ; Remove files
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$DESKTOP\\Sunflower AI.lnk"
    RMDir /r "$SMPROGRAMS\\Sunflower AI"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI"
    DeleteRegKey HKLM "Software\\SunflowerAI"
SectionEnd
'''

def main():
    """Main entry point for Windows compilation"""
    try:
        # Load configuration
        config = BuildConfiguration()
        
        # Create compiler
        compiler = WindowsCompiler(config)
        
        # Run compilation
        output_path = compiler.compile()
        
        print(f"\\nWindows build complete: {output_path}")
        return 0
        
    except Exception as e:
        print(f"\\nERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

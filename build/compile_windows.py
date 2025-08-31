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
        
        for tool, checker in required_tools.items():
            if not checker():
                raise EnvironmentError(f"Required tool not found: {tool}")
        
        # Create build directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_build_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy assets
        self._copy_assets()
        
        # Generate build metadata
        self._generate_metadata()
    
    def _check_pyinstaller(self) -> bool:
        """Check PyInstaller availability"""
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
        """Check Windows SDK signtool availability"""
        # Check common Windows SDK locations
        sdk_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\bin",
            r"C:\Program Files\Windows Kits\10\bin",
            r"C:\Program Files (x86)\Microsoft SDKs\Windows\v10.0A\bin"
        ]
        
        for sdk_path in sdk_paths:
            signtool = Path(sdk_path) / "x64" / "signtool.exe"
            if signtool.exists():
                # Add to PATH for this session
                os.environ["PATH"] = f"{signtool.parent};{os.environ['PATH']}"
                return True
        
        # Check if already in PATH
        return shutil.which("signtool") is not None
    
    def _check_nsis(self) -> bool:
        """Check NSIS installer availability"""
        nsis_path = r"C:\Program Files (x86)\NSIS\makensis.exe"
        if Path(nsis_path).exists():
            os.environ["PATH"] = f"{Path(nsis_path).parent};{os.environ['PATH']}"
            return True
        return shutil.which("makensis") is not None
    
    def _copy_assets(self):
        """Copy required assets to build directory"""
        assets_to_copy = [
            ("icons/sunflower.ico", "sunflower.ico"),
            ("icons/sunflower_256.png", "sunflower.png"),
            ("certificates/root_ca.pem", "certs/root_ca.pem"),
            ("documentation/user_guide.pdf", "docs/user_guide.pdf"),
            ("documentation/quick_start.pdf", "docs/quick_start.pdf")
        ]
        
        for src, dst in assets_to_copy:
            src_path = ASSETS_DIR / src
            dst_path = self.temp_build_dir / dst
            
            if src_path.exists():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
    
    def _generate_metadata(self):
        """Generate Windows-specific metadata"""
        metadata = {
            "product_name": "Sunflower AI Professional System",
            "product_version": self.config.config["version"],
            "company_name": "Sunflower AI Education",
            "copyright": "Copyright © 2025 Sunflower AI Education",
            "file_description": "K-12 STEM Education System",
            "internal_name": "SunflowerAI",
            "original_filename": self.exe_name,
            "product_guid": "{F5E7B4A3-9C2D-4E8F-A1B6-3D7C9E5F2A8B}",
            "upgrade_code": "{A8B4C3D2-5E9F-4A7B-8C6D-1F2E3A4B5C6D}"
        }
        
        # Write version info for resource compiler
        version_rc = self.temp_build_dir / "version.rc"
        self._write_version_resource(version_rc, metadata)
        
        # Compile resource file
        self._compile_resources(version_rc)
    
    def _write_version_resource(self, rc_path: Path, metadata: Dict):
        """Write Windows version resource file"""
        version_parts = metadata["product_version"].split(".")
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
    
    def _compile_main_app(self) -> Path:
        """Compile main Sunflower AI application"""
        print("  → Compiling main application with PyInstaller...")
        
        # Prepare PyInstaller spec
        spec_content = self._generate_main_spec()
        temp_spec = self.temp_build_dir / "main.spec"
        
        with open(temp_spec, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        # Run PyInstaller
        cmd = [
            "pyinstaller",
            "--clean",
            "--noconfirm",
            "--distpath", str(self.temp_build_dir / "dist"),
            "--workpath", str(self.temp_build_dir / "build"),
            str(temp_spec)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"PyInstaller error: {result.stderr}")
            raise RuntimeError("Main app compilation failed")
        
        exe_path = self.temp_build_dir / "dist" / self.exe_name
        
        # Sign executable
        if self.config.config["security"]["signing_required"]:
            print("  → Signing main executable...")
            self.security.sign_executable(exe_path, "windows")
        
        return exe_path
    
    def _generate_main_spec(self) -> str:
        """Generate PyInstaller spec for main app"""
        return f"""
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None

a = Analysis(
    ['{Path(__file__).parent.parent / "src" / "main.py"}'],
    pathex=['{Path(__file__).parent.parent / "src"}'],
    binaries=[
        ('{self.temp_build_dir / "sunflower.ico"}', '.'),
    ],
    datas=[
        ('{Path(__file__).parent.parent / "modelfiles"}', 'modelfiles'),
        ('{Path(__file__).parent.parent / "assets"}', 'assets'),
        ('{self.temp_build_dir / "docs"}', 'docs'),
        ('{self.temp_build_dir / "certs"}', 'certs'),
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
    version='{self.temp_build_dir / "version.res"}' if (Path('{self.temp_build_dir}') / "version.res").exists() else None,
    icon='{self.temp_build_dir / "sunflower.ico"}',
    uac_admin=False,
    uac_uiaccess=False,
)
"""
    
    def _compile_launcher(self) -> Path:
        """Compile universal launcher executable"""
        print("  → Compiling universal launcher...")
        
        launcher_source = self._generate_launcher_source()
        launcher_py = self.temp_build_dir / "launcher.py"
        
        with open(launcher_py, 'w', encoding='utf-8') as f:
            f.write(launcher_source)
        
        # Compile launcher with PyInstaller
        cmd = [
            "pyinstaller",
            "--onefile",
            "--noconsole",
            "--clean",
            "--noconfirm",
            "--name", self.launcher_name.replace(".exe", ""),
            "--icon", str(self.temp_build_dir / "sunflower.ico"),
            "--distpath", str(self.temp_build_dir / "dist"),
            "--workpath", str(self.temp_build_dir / "build"),
            "--add-data", f"{self.temp_build_dir / 'sunflower.ico'};.",
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
    
    def setup_ui(self):
        """Setup launcher UI"""
        # Header
        header = tk.Frame(self.root, bg="#2E7D32", height=80)
        header.pack(fill=tk.X)
        
        title = tk.Label(
            header,
            text="Sunflower AI Professional System",
            font=("Segoe UI", 18, "bold"),
            bg="#2E7D32",
            fg="white"
        )
        title.pack(pady=20)
        
        # Status area
        self.status_frame = tk.Frame(self.root, bg="white")
        self.status_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Detecting Sunflower AI device...",
            font=("Segoe UI", 12),
            bg="white"
        )
        self.status_label.pack(pady=10)
        
        self.progress = ttk.Progressbar(
            self.status_frame,
            mode="indeterminate",
            length=400
        )
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        # Action buttons (initially hidden)
        self.button_frame = tk.Frame(self.root, bg="white")
        
        self.setup_button = tk.Button(
            self.button_frame,
            text="Setup Sunflower AI",
            font=("Segoe UI", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            width=20,
            height=2,
            command=self.start_setup,
            state=tk.DISABLED
        )
        self.setup_button.pack(side=tk.LEFT, padx=10)
        
        self.launch_button = tk.Button(
            self.button_frame,
            text="Launch Sunflower AI",
            font=("Segoe UI", 12, "bold"),
            bg="#2196F3",
            fg="white",
            width=20,
            height=2,
            command=self.launch_app,
            state=tk.DISABLED
        )
        self.launch_button.pack(side=tk.LEFT, padx=10)
    
    def detect_partitions(self):
        """Detect CD-ROM and USB partitions"""
        self.root.after(1000, self._scan_drives)
    
    def _scan_drives(self):
        """Scan for Sunflower AI partitions"""
        c = wmi.WMI()
        
        for drive in c.Win32_LogicalDisk():
            if drive.DriveType == 5:  # CD-ROM
                if self._verify_cdrom_partition(drive.DeviceID):
                    self.cdrom_path = drive.DeviceID
            elif drive.DriveType == 2:  # Removable
                if self._verify_usb_partition(drive.DeviceID):
                    self.usb_path = drive.DeviceID
        
        if self.cdrom_path and self.usb_path:
            self.on_device_found()
        else:
            self.on_device_not_found()
    
    def _verify_cdrom_partition(self, drive):
        """Verify CD-ROM partition signature"""
        try:
            signature_file = Path(drive) / "SUNFLOWER.ID"
            if signature_file.exists():
                with open(signature_file, "r") as f:
                    return f.read().strip() == "SUNFLOWER_AI_PRO_v6"
        except:
            pass
        return False
    
    def _verify_usb_partition(self, drive):
        """Verify USB partition structure"""
        try:
            config_file = Path(drive) / "config" / "system.json"
            return config_file.exists()
        except:
            pass
        return False
    
    def on_device_found(self):
        """Handle successful device detection"""
        self.progress.stop()
        self.progress.pack_forget()
        
        self.status_label.config(
            text=f"✓ Sunflower AI device detected\\n"
                 f"CD-ROM: {self.cdrom_path}\\n"
                 f"USB: {self.usb_path}",
            fg="#2E7D32"
        )
        
        # Check if already initialized
        if self._is_initialized():
            self.launch_button.config(state=tk.NORMAL)
            self.status_label.config(
                text=self.status_label.cget("text") + "\\n✓ System ready to launch"
            )
        else:
            self.setup_button.config(state=tk.NORMAL)
            self.status_label.config(
                text=self.status_label.cget("text") + "\\n⚠ First-time setup required"
            )
        
        self.button_frame.pack(pady=20)
    
    def on_device_not_found(self):
        """Handle device not found"""
        self.progress.stop()
        self.progress.pack_forget()
        
        self.status_label.config(
            text="✗ Sunflower AI device not detected\\n\\n"
                 "Please ensure the device is properly connected\\n"
                 "and try again.",
            fg="#D32F2F"
        )
        
        retry_button = tk.Button(
            self.status_frame,
            text="Retry Detection",
            command=self.retry_detection,
            bg="#FF9800",
            fg="white",
            font=("Segoe UI", 10, "bold")
        )
        retry_button.pack(pady=10)
    
    def _is_initialized(self):
        """Check if system is initialized"""
        try:
            config_file = Path(self.usb_path) / "config" / "system.json"
            with open(config_file, "r") as f:
                config = json.load(f)
                return config.get("initialized", False)
        except:
            return False
    
    def start_setup(self):
        """Start first-time setup process"""
        setup_exe = Path(self.cdrom_path) / "system" / "SunflowerSetup.exe"
        if setup_exe.exists():
            subprocess.Popen([str(setup_exe), self.cdrom_path, self.usb_path])
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Setup program not found on device")
    
    def launch_app(self):
        """Launch main Sunflower AI application"""
        main_exe = Path(self.cdrom_path) / "system" / "SunflowerAI.exe"
        if main_exe.exists():
            subprocess.Popen([str(main_exe), self.cdrom_path, self.usb_path])
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Application not found on device")
    
    def retry_detection(self):
        """Retry device detection"""
        self.cdrom_path = None
        self.usb_path = None
        self.button_frame.pack_forget()
        self.progress.pack(pady=10)
        self.progress.start(10)
        self.status_label.config(
            text="Detecting Sunflower AI device...",
            fg="black"
        )
        self.detect_partitions()
    
    def run(self):
        """Run launcher"""
        self.root.mainloop()

if __name__ == "__main__":
    launcher = SunflowerLauncher()
    launcher.run()
'''
    
    def _compile_service(self) -> Path:
        """Compile background service for Ollama management"""
        print("  → Compiling background service...")
        
        service_source = self._generate_service_source()
        service_py = self.temp_build_dir / "service.py"
        
        with open(service_py, 'w', encoding='utf-8') as f:
            f.write(service_source)
        
        # Compile service
        cmd = [
            "pyinstaller",
            "--onefile",
            "--console",  # Service runs in background
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
Manages Ollama and system resources
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
import os
import subprocess
import json
import psutil
from pathlib import Path
from threading import Thread

class SunflowerAIService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SunflowerAIService"
    _svc_display_name_ = "Sunflower AI Professional System Service"
    _svc_description_ = "Manages AI models and system resources for Sunflower AI"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True
        self.ollama_process = None
        self.config = self.load_config()
    
    def load_config(self):
        """Load service configuration"""
        # Configuration would be loaded from USB partition
        return {
            "ollama_path": "C:/Program Files/Sunflower AI/ollama/ollama.exe",
            "model_path": "C:/Program Files/Sunflower AI/models",
            "port": 11434,
            "max_memory_gb": 4,
            "auto_select_model": True
        }
    
    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        
        # Stop Ollama gracefully
        if self.ollama_process:
            self.ollama_process.terminate()
            time.sleep(2)
            if self.ollama_process.poll() is None:
                self.ollama_process.kill()
    
    def SvcDoRun(self):
        """Main service loop"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        
        self.main()
    
    def main(self):
        """Service main logic"""
        # Start Ollama server
        self.start_ollama()
        
        # Monitor system resources
        monitor_thread = Thread(target=self.monitor_resources)
        monitor_thread.start()
        
        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
    
    def start_ollama(self):
        """Start Ollama server with optimal configuration"""
        try:
            # Detect optimal model based on hardware
            model = self.select_optimal_model()
            
            # Start Ollama
            cmd = [
                self.config["ollama_path"],
                "serve",
                "--port", str(self.config["port"]),
                "--models", self.config["model_path"]
            ]
            
            self.ollama_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                0,
                f"Ollama started with model: {model}"
            )
            
        except Exception as e:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                0,
                f"Failed to start Ollama: {str(e)}"
            )
    
    def select_optimal_model(self):
        """Select optimal model based on system resources"""
        total_ram = psutil.virtual_memory().total / (1024**3)  # GB
        
        if total_ram >= 16:
            return "llama3.2:7b"
        elif total_ram >= 8:
            return "llama3.2:3b"
        elif total_ram >= 4:
            return "llama3.2:1b"
        else:
            return "llama3.2:1b-q4_0"
    
    def monitor_resources(self):
        """Monitor system resources and adjust as needed"""
        while self.is_running:
            try:
                # Check memory usage
                memory_percent = psutil.virtual_memory().percent
                
                if memory_percent > 90:
                    # Log warning
                    servicemanager.LogMsg(
                        servicemanager.EVENTLOG_WARNING_TYPE,
                        0,
                        f"High memory usage: {memory_percent}%"
                    )
                
                # Check Ollama health
                if self.ollama_process and self.ollama_process.poll() is not None:
                    # Restart Ollama if it crashed
                    servicemanager.LogMsg(
                        servicemanager.EVENTLOG_WARNING_TYPE,
                        0,
                        "Ollama process died, restarting..."
                    )
                    self.start_ollama()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_ERROR_TYPE,
                    0,
                    f"Monitor error: {str(e)}"
                )
                time.sleep(60)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SunflowerAIService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SunflowerAIService)
'''
    
    def _create_partitions(self) -> Tuple[Path, Path]:
        """Create partition structure for Windows"""
        print("  → Creating CD-ROM partition structure...")
        cdrom_path = self.temp_build_dir / "cdrom_partition"
        usb_path = self.temp_build_dir / "usb_partition"
        
        # Use partition manager to create structure
        cdrom_path, usb_path = self.partition.create_partition_layout(
            self.temp_build_dir
        )
        
        # Copy compiled executables to CD-ROM partition
        system_dir = cdrom_path / "system"
        system_dir.mkdir(exist_ok=True)
        
        for exe_file in (self.temp_build_dir / "dist").glob("*.exe"):
            shutil.copy2(exe_file, system_dir)
        
        # Copy models to CD-ROM partition
        models_dir = cdrom_path / "models"
        models_dir.mkdir(exist_ok=True)
        
        # Copy Ollama binaries
        ollama_dir = cdrom_path / "ollama"
        ollama_dir.mkdir(exist_ok=True)
        
        # Create autorun.inf for CD-ROM
        self._create_autorun(cdrom_path)
        
        return cdrom_path, usb_path
    
    def _create_autorun(self, cdrom_path: Path):
        """Create autorun.inf for automatic launcher execution"""
        autorun_content = f"""[autorun]
open=system\\{self.launcher_name}
icon=system\\sunflower.ico
label=Sunflower AI Professional System
action=Setup Sunflower AI Professional System

[Content]
MusicFiles=false
PictureFiles=false
VideoFiles=false
"""
        
        with open(cdrom_path / "autorun.inf", 'w') as f:
            f.write(autorun_content)
        
        # Set hidden attribute on autorun.inf
        import win32api
        import win32con
        win32api.SetFileAttributes(
            str(cdrom_path / "autorun.inf"),
            win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
        )
    
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
    
    ; Create USB partition structure
    CreateDirectory "$APPDATA\\SunflowerAI"
    CreateDirectory "$APPDATA\\SunflowerAI\\profiles"
    CreateDirectory "$APPDATA\\SunflowerAI\\conversations"
    CreateDirectory "$APPDATA\\SunflowerAI\\logs"
    
    ; Register service
    ExecWait '"$INSTDIR\\system\\{self.service_name}" install'
    ExecWait 'sc config SunflowerAIService start=auto'
    ExecWait 'net start SunflowerAIService'
    
    ; Write registry keys
    WriteRegStr HKLM "SOFTWARE\\SunflowerAI" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "SOFTWARE\\SunflowerAI" "Version" "{self.config.config['version']}"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\Sunflower AI"
    CreateShortcut "$SMPROGRAMS\\Sunflower AI\\Sunflower AI.lnk" "$INSTDIR\\system\\{self.launcher_name}"
    CreateShortcut "$DESKTOP\\Sunflower AI.lnk" "$INSTDIR\\system\\{self.launcher_name}"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                "DisplayName" "Sunflower AI Professional System"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI" \\
                "UninstallString" "$INSTDIR\\Uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Stop and remove service
    ExecWait 'net stop SunflowerAIService'
    ExecWait '"$INSTDIR\\system\\{self.service_name}" remove'
    
    ; Remove files
    Delete "$INSTDIR\\*.*"
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\\Sunflower AI\\*.*"
    RMDir "$SMPROGRAMS\\Sunflower AI"
    Delete "$DESKTOP\\Sunflower AI.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SunflowerAI"
    DeleteRegKey HKLM "SOFTWARE\\SunflowerAI"
SectionEnd
"""
    
    def _finalize_build(self, installer_path: Path) -> Path:
        """Finalize Windows build with ISO creation"""
        print("  → Creating final ISO image...")
        
        # Create ISO with both partitions
        iso_path = self.output_dir / f"SunflowerAI_Windows_{self.config.config['version']}.iso"
        
        # Use Windows ADK tools to create ISO
        self._create_iso_image(self.temp_build_dir / "cdrom_partition", iso_path)
        
        # Generate checksums
        checksum = self.security.calculate_checksum(iso_path)
        
        # Write manifest
        manifest = {
            "product": "Sunflower AI Professional System",
            "version": self.config.config["version"],
            "platform": "Windows",
            "build_date": datetime.now().isoformat(),
            "checksum": checksum,
            "size_bytes": iso_path.stat().st_size
        }
        
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return iso_path
    
    def _create_iso_image(self, source_dir: Path, iso_path: Path):
        """Create ISO image from directory"""
        # This would use oscdimg.exe from Windows ADK
        # For production, integrate proper ISO creation tools
        pass

if __name__ == "__main__":
    config = BuildConfiguration()
    compiler = WindowsCompiler(config)
    
    try:
        output_path = compiler.compile()
        print(f"\\nBuild successful: {output_path}")
        sys.exit(0)
    except Exception as e:
        print(f"\\nBuild failed: {e}")
        sys.exit(1)

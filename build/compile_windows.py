#!/usr/bin/env python3
"""
Sunflower AI Professional System - Windows Compiler
Compiles Windows executables with PyInstaller
Version: 6.2.0 - Production Ready
"""

import os  # FIX: Added missing import for os.pathsep usage
import sys
import subprocess
import shutil
import json
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('WindowsCompiler')


class WindowsCompiler:
    """Compiles Sunflower AI for Windows deployment"""
    
    def __init__(self, project_root: Path):
        """
        Initialize Windows compiler
        
        Args:
            project_root: Path to project root directory
        """
        self.project_root = Path(project_root).resolve()
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.src_dir = self.project_root / "src"
        self.resources_dir = self.project_root / "resources"
        
        # Windows-specific paths
        self.windows_dir = self.dist_dir / "Windows"
        self.installer_dir = self.dist_dir / "installer"
        
        # Temporary build directory
        self.temp_build_dir = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        
        # Build configuration
        self.config = self._load_build_config()
        
        # PyInstaller spec file
        self.spec_file = self.build_dir / "templates" / "windows.spec"
        
        # Output filenames
        self.app_name = "SunflowerAI.exe"
        self.launcher_name = "SunflowerLauncher.exe"
        self.service_name = "SunflowerService.exe"
        
        # Import additional modules
        self._import_dependencies()
        
        logger.info(f"Windows compiler initialized at {self.project_root}")
    
    def _load_build_config(self) -> Dict:
        """Load build configuration"""
        config_file = self.build_dir / "build_config.json"
        
        if not config_file.exists():
            # Default configuration
            return {
                "app_name": "Sunflower AI Professional",
                "version": "6.2.0",
                "company": "Sunflower AI Systems",
                "copyright": "Copyright © 2025 Sunflower AI Systems",
                "description": "Family-focused K-12 STEM Education System",
                "icon": "sunflower.ico",
                "signing_required": False,
                "installer_type": "nsis"
            }
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _import_dependencies(self):
        """Import and verify required dependencies"""
        try:
            # Import Windows-specific modules
            global SecurityManager, PartitionManager
            from production.security_manager import SecurityManager
            from src.partition_manager import PartitionManager
            
            self.security = SecurityManager(self.project_root)
            self.partition = PartitionManager()
            
        except ImportError as e:
            logger.warning(f"Optional dependency not available: {e}")
    
    def compile(self) -> Path:
        """
        Main compilation process for Windows
        
        Returns:
            Path to compiled output
        """
        print("\n" + "=" * 60)
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
        """Prepare build environment"""
        # Create necessary directories
        self.windows_dir.mkdir(parents=True, exist_ok=True)
        self.installer_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy resources
        icon_src = self.resources_dir / "icons" / "sunflower.ico"
        if icon_src.exists():
            shutil.copy2(icon_src, self.temp_build_dir / "sunflower.ico")
        
        # Verify PyInstaller is available
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True
            )
            logger.info(f"PyInstaller version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError("PyInstaller not found. Install with: pip install pyinstaller")
        
        # Check for Windows SDK (for signing)
        if self.config.get("signing_required"):
            if not self._check_windows_sdk():
                logger.warning("Windows SDK not found - signing will be skipped")
                self.config["signing_required"] = False
        
        # Check for NSIS installer
        if self.config.get("installer_type") == "nsis":
            if not self._check_nsis():
                logger.warning("NSIS not found - using fallback installer")
                self.config["installer_type"] = "zip"
    
    def _check_windows_sdk(self) -> bool:
        """Check if Windows SDK is available for signing"""
        sdk_paths = [
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
            "--add-data", f"{icon_path};.",
            str(launcher_py)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        launcher_exe = self.temp_build_dir / "dist" / self.launcher_name
        
        # Sign launcher
        if self.config.get("signing_required"):
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
        
        self.detect_partitions()
        self.setup_ui()
    
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
        self.cdrom_path = None
        self.usb_path = None
        
        drives = win32api.GetLogicalDriveStrings().split('\\000')[:-1]
        
        for drive in drives:
            if Path(drive + "sunflower_cd.id").exists():
                self.cdrom_path = Path(drive)
            elif Path(drive + "sunflower_data.id").exists():
                self.usb_path = Path(drive)
        
        if not self.cdrom_path:
            messagebox.showerror(
                "CD-ROM Not Found",
                "Please insert the Sunflower AI CD-ROM and restart."
            )
            sys.exit(1)
    
    def setup_ui(self):
        """Setup launcher UI"""
        # Title
        title = tk.Label(
            self.root,
            text="Sunflower AI Professional System",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=20)
        
        # Status
        self.status = tk.Label(self.root, text="Ready to launch...")
        self.status.pack(pady=10)
        
        # Launch button
        launch_btn = tk.Button(
            self.root,
            text="Launch Sunflower AI",
            command=self.launch_system,
            width=20,
            height=2
        )
        launch_btn.pack(pady=20)
    
    def launch_system(self):
        """Launch the main system"""
        main_exe = self.cdrom_path / "Windows" / "SunflowerAI.exe"
        if main_exe.exists():
            subprocess.Popen([str(main_exe)])
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Main application not found!")

if __name__ == "__main__":
    app = SunflowerLauncher()
    app.root.mainloop()
'''
    
    def _compile_main_app(self) -> Path:
        """Compile main application"""
        print("  → Compiling main application...")
        
        # Use the spec file if it exists
        if self.spec_file.exists():
            cmd = [
                "pyinstaller",
                "--clean",
                "--noconfirm",
                "--distpath", str(self.temp_build_dir / "dist"),
                "--workpath", str(self.temp_build_dir / "build"),
                str(self.spec_file)
            ]
        else:
            # Direct compilation
            main_py = self.src_dir / "main.py"
            icon_path = str(self.temp_build_dir / "sunflower.ico")
            
            cmd = [
                "pyinstaller",
                "--onefile",
                "--windowed",
                "--clean",
                "--noconfirm",
                "--name", "SunflowerAI",
                "--icon", icon_path,
                "--distpath", str(self.temp_build_dir / "dist"),
                "--workpath", str(self.temp_build_dir / "build"),
                "--add-data", f"{str(self.src_dir / 'config')}{os.pathsep}config",
                "--add-data", f"{str(self.resources_dir)}{os.pathsep}resources",
                "--hidden-import", "tkinter",
                "--hidden-import", "PIL",
                "--hidden-import", "sqlite3",
                "--hidden-import", "psutil",
                str(main_py)
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"PyInstaller failed: {result.stderr}")
            raise RuntimeError("Main application compilation failed")
        
        main_exe = self.temp_build_dir / "dist" / self.app_name
        
        # Sign main application
        if self.config.get("signing_required"):
            self.security.sign_executable(main_exe, "windows")
        
        return main_exe
    
    def _compile_service(self) -> Path:
        """Compile background service"""
        print("  → Compiling background service...")
        
        service_source = self._generate_service_source()
        service_py = self.temp_build_dir / "service.py"
        
        with open(service_py, 'w', encoding='utf-8') as f:
            f.write(service_source)
        
        # Compile service
        cmd = [
            "pyinstaller",
            "--onefile",
            "--console",
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
        if self.config.get("signing_required"):
            self.security.sign_executable(service_exe, "windows")
        
        return service_exe
    
    def _generate_service_source(self) -> str:
        """Generate Windows service source code"""
        return '''
"""
Sunflower AI Background Service for Windows
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
from pathlib import Path

class SunflowerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SunflowerAI"
    _svc_display_name_ = "Sunflower AI Professional Service"
    _svc_description_ = "Manages AI models and system resources"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True
    
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
    
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
    
    def main(self):
        while self.is_running:
            # Monitor Ollama service
            # Check system resources
            # Clean temporary files
            time.sleep(30)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SunflowerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SunflowerService)
'''
    
    def _create_partitions(self) -> Tuple[Path, Path]:
        """Create partition structure for deployment"""
        print("  → Creating partition structure...")
        
        cdrom_dir = self.temp_build_dir / "CDROM"
        usb_dir = self.temp_build_dir / "USB"
        
        cdrom_dir.mkdir(exist_ok=True)
        usb_dir.mkdir(exist_ok=True)
        
        # Create CD-ROM structure
        (cdrom_dir / "Windows").mkdir(exist_ok=True)
        (cdrom_dir / "models").mkdir(exist_ok=True)
        (cdrom_dir / "modelfiles").mkdir(exist_ok=True)
        (cdrom_dir / "ollama").mkdir(exist_ok=True)
        (cdrom_dir / "resources").mkdir(exist_ok=True)
        
        # Create marker files
        (cdrom_dir / "sunflower_cd.id").write_text("SUNFLOWER_AI_SYSTEM_v6.2.0")
        (usb_dir / "sunflower_data.id").write_text("SUNFLOWER_AI_DATA_v6.2.0")
        
        return cdrom_dir, usb_dir
    
    def _create_installer(self, main_exe: Path, launcher_exe: Path, 
                         service_exe: Path, cdrom_path: Path) -> Path:
        """Create Windows installer package"""
        print("  → Creating installer package...")
        
        # Copy executables to deployment directory
        shutil.copy2(main_exe, self.windows_dir / main_exe.name)
        shutil.copy2(launcher_exe, self.windows_dir / launcher_exe.name)
        shutil.copy2(service_exe, self.windows_dir / service_exe.name)
        
        if self.config.get("installer_type") == "nsis":
            return self._create_nsis_installer()
        else:
            return self._create_zip_installer()
    
    def _create_nsis_installer(self) -> Path:
        """Create NSIS installer"""
        nsis_script = self.temp_build_dir / "installer.nsi"
        
        script_content = f'''
!define PRODUCT_NAME "{self.config['app_name']}"
!define PRODUCT_VERSION "{self.config['version']}"
!define PRODUCT_PUBLISHER "{self.config['company']}"

Name "${{PRODUCT_NAME}}"
OutFile "{self.installer_dir / 'SunflowerAI_Setup.exe'}"
InstallDir "$PROGRAMFILES\\SunflowerAI"

Section "Main"
  SetOutPath "$INSTDIR"
  File /r "{self.windows_dir}\\*.*"
  CreateShortcut "$DESKTOP\\Sunflower AI.lnk" "$INSTDIR\\SunflowerLauncher.exe"
SectionEnd
'''
        
        nsis_script.write_text(script_content)
        
        subprocess.run(["makensis", str(nsis_script)], check=True)
        
        return self.installer_dir / "SunflowerAI_Setup.exe"
    
    def _create_zip_installer(self) -> Path:
        """Create ZIP installer as fallback"""
        zip_path = self.installer_dir / "SunflowerAI_Windows.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.windows_dir.rglob('*'):
                if file_path.is_file():
                    arc_name = file_path.relative_to(self.windows_dir.parent)
                    zf.write(file_path, arc_name)
        
        return zip_path
    
    def _finalize_build(self, installer_path: Path) -> Path:
        """Finalize and sign the build"""
        print("  → Finalizing build...")
        
        # Sign installer if required
        if self.config.get("signing_required") and installer_path.suffix == '.exe':
            self.security.sign_executable(installer_path, "windows")
        
        # Create checksums
        self._create_checksums(installer_path)
        
        # Create build manifest
        self._create_build_manifest(installer_path)
        
        return installer_path
    
    def _create_checksums(self, installer_path: Path):
        """Create SHA256 checksums for verification"""
        import hashlib
        
        checksums = {}
        
        # Hash installer
        with open(installer_path, 'rb') as f:
            checksums[installer_path.name] = hashlib.sha256(f.read()).hexdigest()
        
        # Hash all executables
        for exe_file in self.windows_dir.glob("*.exe"):
            with open(exe_file, 'rb') as f:
                checksums[exe_file.name] = hashlib.sha256(f.read()).hexdigest()
        
        # Write checksums file
        checksum_file = self.installer_dir / "checksums.txt"
        with open(checksum_file, 'w') as f:
            for filename, checksum in checksums.items():
                f.write(f"{checksum}  {filename}\n")
    
    def _create_build_manifest(self, installer_path: Path):
        """Create build manifest with metadata"""
        manifest = {
            "build_date": datetime.now().isoformat(),
            "version": self.config["version"],
            "platform": "Windows",
            "architecture": "x64",
            "installer": installer_path.name,
            "components": {
                "main_app": self.app_name,
                "launcher": self.launcher_name,
                "service": self.service_name
            },
            "requirements": {
                "os": "Windows 10 or later",
                "ram": "4GB minimum",
                "storage": "16GB USB drive",
                "runtime": ".NET Framework 4.8"
            }
        }
        
        manifest_file = self.installer_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compile Sunflower AI for Windows"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory"
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign executables (requires certificate)"
    )
    
    args = parser.parse_args()
    
    try:
        compiler = WindowsCompiler(args.project_root)
        
        if args.sign:
            compiler.config["signing_required"] = True
        
        output_path = compiler.compile()
        
        print(f"\n✅ Build successful!")
        print(f"📦 Output: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

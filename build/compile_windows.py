#!/usr/bin/env python3
"""
Sunflower AI Professional System - Windows Compilation Module
Production-ready build system for Windows platform
Version: 6.2.0
FIXED: BUG-001 - Proper path handling for PyInstaller specs
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import build utilities
from build import BuildConfiguration, SecurityManager


class WindowsCompiler:
    """Windows-specific compilation and packaging system"""
    
    def __init__(self, config: BuildConfiguration):
        self.config = config
        self.security = SecurityManager(config)
        self.platform = "windows"
        self.arch = "x86_64"
        
        # Define build paths
        self.build_dir = Path(__file__).parent
        self.root_dir = self.build_dir.parent
        self.dist_dir = self.root_dir / "dist" / "windows"
        self.temp_build_dir = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        
        # Windows-specific settings
        self.exe_name = "SunflowerAI.exe"
        self.launcher_name = "SunflowerLauncher.exe"
        self.service_name = "SunflowerService.exe"
        
        # Ensure output directories exist
        self.dist_dir.mkdir(parents=True, exist_ok=True)
    
    def compile_all(self) -> Path:
        """Execute complete Windows compilation process"""
        try:
            print("\n" + "="*60)
            print("SUNFLOWER AI - WINDOWS BUILD SYSTEM")
            print("="*60)
            print(f"Build Version: {self.config.config['version']}")
            print(f"Architecture: {self.arch}")
            print(f"Output Directory: {self.dist_dir}")
            print("="*60 + "\n")
            
            # Phase 1: Prepare resources
            print("[Phase 1/7] Preparing resources...")
            self._prepare_resources()
            
            # Phase 2: Compile launcher
            print("\n[Phase 2/7] Compiling launcher...")
            launcher_exe = self._compile_launcher()
            
            # Phase 3: Compile main application
            print("\n[Phase 3/7] Compiling main application...")
            main_exe = self._compile_main_app()
            
            # Phase 4: Create partition structure
            print("\n[Phase 4/7] Creating partition structure...")
            cdrom_path, usb_path = self._create_partitions()
            
            # Phase 5: Package components
            print("\n[Phase 5/7] Packaging components...")
            package_path = self._package_components(
                launcher_exe, main_exe, cdrom_path, usb_path
            )
            
            # Phase 6: Sign executables
            print("\n[Phase 6/7] Signing executables...")
            self._sign_all_executables()
            
            # Phase 7: Create installer
            print("\n[Phase 7/7] Creating installer...")
            installer_path = self._create_installer()
            
            print(f"\n✅ Windows build complete: {installer_path}")
            return installer_path
            
        except Exception as e:
            print(f"\n❌ Build failed: {e}")
            raise
        finally:
            # Cleanup temporary directory
            if self.temp_build_dir.exists():
                shutil.rmtree(self.temp_build_dir, ignore_errors=True)
    
    def _prepare_resources(self):
        """Prepare Windows-specific resources"""
        # Copy icon file
        icon_source = self.root_dir / "assets" / "icons" / "sunflower.ico"
        if icon_source.exists():
            shutil.copy(icon_source, self.temp_build_dir / "sunflower.ico")
        
        # Create version resource file
        self._create_version_resource()
        
        # Copy required DLLs
        self._copy_runtime_dlls()
    
    def _create_version_resource(self):
        """Create Windows version resource file"""
        version_info = {
            "CompanyName": "Sunflower AI Education",
            "FileDescription": "Sunflower AI Professional System",
            "FileVersion": self.config.config["version"],
            "InternalName": "SunflowerAI",
            "LegalCopyright": "Copyright © 2025 Sunflower AI Education",
            "OriginalFilename": self.exe_name,
            "ProductName": "Sunflower AI Professional System",
            "ProductVersion": self.config.config["version"]
        }
        
        # Generate version resource script
        rc_content = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({','.join(self.config.config['version'].split('.'))}),
    prodvers=({','.join(self.config.config['version'].split('.'))}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(u'040904B0', [
        StringStruct(u'CompanyName', u'{version_info["CompanyName"]}'),
        StringStruct(u'FileDescription', u'{version_info["FileDescription"]}'),
        StringStruct(u'FileVersion', u'{version_info["FileVersion"]}'),
        StringStruct(u'InternalName', u'{version_info["InternalName"]}'),
        StringStruct(u'LegalCopyright', u'{version_info["LegalCopyright"]}'),
        StringStruct(u'OriginalFilename', u'{version_info["OriginalFilename"]}'),
        StringStruct(u'ProductName', u'{version_info["ProductName"]}'),
        StringStruct(u'ProductVersion', u'{version_info["ProductVersion"]}')
      ])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
        
        # Save version resource
        version_rc = self.temp_build_dir / "version.rc"
        version_rc.write_text(rc_content)
        
        # Compile to .res file
        try:
            subprocess.run(
                ["rc", "/fo", str(self.temp_build_dir / "version.res"), str(version_rc)],
                check=True,
                capture_output=True
            )
        except:
            # If rc.exe not available, PyInstaller will handle it
            pass
    
    def _copy_runtime_dlls(self):
        """Copy required Windows runtime DLLs"""
        required_dlls = [
            "msvcp140.dll",
            "vcruntime140.dll",
            "vcruntime140_1.dll",
            "api-ms-win-crt-runtime-l1-1-0.dll"
        ]
        
        system32 = Path("C:/Windows/System32")
        for dll in required_dlls:
            dll_path = system32 / dll
            if dll_path.exists():
                shutil.copy(dll_path, self.temp_build_dir)
    
    def _compile_launcher(self) -> Path:
        """Compile launcher executable"""
        print("  → Generating launcher source...")
        launcher_source = self._generate_launcher_source()
        launcher_py = self.temp_build_dir / "launcher.py"
        
        with open(launcher_py, 'w', encoding='utf-8') as f:
            f.write(launcher_source)
        
        print("  → Creating PyInstaller spec...")
        spec_content = self._generate_launcher_spec()
        temp_spec = self.temp_build_dir / "launcher.spec"
        
        with open(temp_spec, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print("  → Running PyInstaller...")
        cmd = ["pyinstaller", "--clean", "--noconfirm", str(temp_spec)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"PyInstaller error: {result.stderr}")
            raise RuntimeError("Launcher compilation failed")
        
        launcher_exe = self.temp_build_dir / "dist" / self.launcher_name
        
        if not launcher_exe.exists():
            raise FileNotFoundError(f"Launcher executable not found: {launcher_exe}")
        
        # Sign launcher if configured
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
                    self.cdrom_path = Path(drive.DeviceID) / "/"
            elif drive.DriveType in [2, 3]:  # Removable or Fixed
                if drive.FileSystem in ["FAT32", "exFAT", "NTFS"]:
                    test_file = Path(drive.DeviceID) / "sunflower_data.id"
                    if test_file.exists():
                        self.usb_path = Path(drive.DeviceID) / "/"
    
    def setup_ui(self):
        """Setup launcher UI"""
        # Main frame
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True)
        
        # Logo/Title
        title = tk.Label(
            main_frame,
            text="Sunflower AI Professional System",
            font=("Segoe UI", 18, "bold"),
            bg="#f0f0f0"
        )
        title.pack(pady=30)
        
        # Status
        status_text = "Detecting device..." if not self.cdrom_path else "Ready to launch"
        self.status_label = tk.Label(
            main_frame,
            text=status_text,
            font=("Segoe UI", 12),
            bg="#f0f0f0"
        )
        self.status_label.pack(pady=20)
        
        # Launch button
        self.launch_btn = tk.Button(
            main_frame,
            text="Launch Sunflower AI",
            command=self.launch_system,
            font=("Segoe UI", 12),
            bg="#4CAF50",
            fg="white",
            padx=30,
            pady=10
        )
        self.launch_btn.pack(pady=20)
        
        if not self.cdrom_path:
            self.launch_btn.config(state="disabled")
    
    def check_device(self):
        """Check if device is properly connected"""
        if not self.cdrom_path:
            self.show_error("CD-ROM partition not found.\\nPlease insert Sunflower AI device.")
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
    
    def show_error(self, message):
        """Show error message"""
        messagebox.showerror("Error", message)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    launcher = SunflowerLauncher()
    launcher.run()
'''
    
    def _generate_launcher_spec(self) -> str:
        """Generate PyInstaller spec for launcher with FIXED path handling"""
        # FIX BUG-001: Use Path.as_posix() for cross-platform compatibility in specs
        launcher_py = self.temp_build_dir / "launcher.py"
        icon_path = self.temp_build_dir / "sunflower.ico"
        version_res = self.temp_build_dir / "version.res"
        
        # Convert paths to forward slashes for PyInstaller compatibility
        launcher_py_str = launcher_py.as_posix()
        temp_build_str = self.temp_build_dir.as_posix()
        icon_path_str = icon_path.as_posix() if icon_path.exists() else ''
        version_res_str = version_res.as_posix() if version_res.exists() else ''
        
        spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{launcher_py_str}'],
    pathex=['{temp_build_str}'],
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
    version='{version_res_str}' if '{version_res_str}' else None,
    icon='{icon_path_str}' if '{icon_path_str}' else None,
    uac_admin=False,
    uac_uiaccess=False,
)
'''
        return spec_content
    
    def _compile_main_app(self) -> Path:
        """Compile main Sunflower AI application"""
        print("  → Preparing main application...")
        
        # Prepare PyInstaller spec
        spec_content = self._generate_main_spec()
        temp_spec = self.temp_build_dir / "main.spec"
        
        with open(temp_spec, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print("  → Running PyInstaller for main app...")
        cmd = ["pyinstaller", "--clean", "--noconfirm", str(temp_spec)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"PyInstaller error: {result.stderr}")
            raise RuntimeError("Main app compilation failed")
        
        main_exe = self.temp_build_dir / "dist" / self.exe_name
        
        if not main_exe.exists():
            raise FileNotFoundError(f"Main executable not found: {main_exe}")
        
        # Sign main executable
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(main_exe, "windows")
        
        return main_exe
    
    def _generate_main_spec(self) -> str:
        """Generate PyInstaller spec for main application with FIXED path handling"""
        # FIX BUG-001: Properly handle all paths using Path.as_posix()
        launcher_py = self.root_dir / "UNIVERSAL_LAUNCHER.py"
        icon_path = self.temp_build_dir / "sunflower.ico"
        version_res = self.temp_build_dir / "version.res"
        
        # Collect paths for data files
        ollama_exe = self.root_dir / "ollama" / "ollama.exe"
        modelfiles_dir = self.root_dir / "modelfiles"
        assets_dir = self.root_dir / "assets"
        docs_dir = self.temp_build_dir / "docs"
        
        # Convert all paths to forward slashes
        launcher_py_str = launcher_py.as_posix()
        parent_path_str = self.root_dir.as_posix()
        icon_path_str = icon_path.as_posix() if icon_path.exists() else ''
        version_res_str = version_res.as_posix() if version_res.exists() else ''
        
        # Build datas list with proper path handling
        datas_list = []
        if ollama_exe.exists():
            datas_list.append(f"('{ollama_exe.as_posix()}', 'ollama')")
        if modelfiles_dir.exists():
            datas_list.append(f"('{modelfiles_dir.as_posix()}', 'modelfiles')")
        if assets_dir.exists():
            datas_list.append(f"('{assets_dir.as_posix()}', 'assets')")
        if docs_dir.exists():
            datas_list.append(f"('{docs_dir.as_posix()}', 'docs')")
        
        datas_str = ",\n        ".join(datas_list) if datas_list else ""
        
        spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{launcher_py_str}'],
    pathex=['{parent_path_str}'],
    binaries=[],
    datas=[
        {datas_str}
    ],
    hiddenimports=[
        'tkinter',
        'psutil',
        'wmi',
        'cryptography',
        'sqlite3',
        'json',
        'hashlib',
        'pathlib',
        'subprocess',
        'threading',
        'socket'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas'],
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
    upx_exclude=['vcruntime140.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    version='{version_res_str}' if '{version_res_str}' else None,
    icon='{icon_path_str}' if '{icon_path_str}' else None,
    uac_admin=False,
    uac_uiaccess=False,
)
'''
        return spec_content
    
    def _create_partitions(self) -> Tuple[Path, Path]:
        """Create CD-ROM and USB partition structures"""
        cdrom_path = self.dist_dir / "SUNFLOWER_CD"
        usb_path = self.dist_dir / "SUNFLOWER_DATA"
        
        # Create CD-ROM structure (read-only)
        cdrom_dirs = [
            "system",
            "models",
            "ollama",
            "documentation",
            "security"
        ]
        
        for dir_name in cdrom_dirs:
            (cdrom_path / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create USB structure (writable)
        usb_dirs = [
            "profiles",
            "sessions",
            "logs",
            "config"
        ]
        
        for dir_name in usb_dirs:
            (usb_path / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create marker files
        (cdrom_path / "sunflower_cd.id").write_text("SUNFLOWER_AI_SYSTEM_v6.2.0")
        (usb_path / "sunflower_data.id").write_text("SUNFLOWER_AI_DATA_v6.2.0")
        
        return cdrom_path, usb_path
    
    def _package_components(self, launcher_exe: Path, main_exe: Path,
                           cdrom_path: Path, usb_path: Path) -> Path:
        """Package all components into distribution structure"""
        # Copy executables to CD-ROM partition
        shutil.copy(launcher_exe, cdrom_path / "system" / launcher_exe.name)
        shutil.copy(main_exe, cdrom_path / "system" / main_exe.name)
        
        # Copy models
        models_source = self.root_dir / "models"
        if models_source.exists():
            shutil.copytree(models_source, cdrom_path / "models", dirs_exist_ok=True)
        
        # Copy Ollama
        ollama_source = self.root_dir / "ollama"
        if ollama_source.exists():
            shutil.copytree(ollama_source, cdrom_path / "ollama", dirs_exist_ok=True)
        
        # Create manifest
        manifest = self.security.create_integrity_manifest(cdrom_path)
        
        return cdrom_path
    
    def _sign_all_executables(self):
        """Sign all executables in distribution"""
        exe_files = list(self.dist_dir.rglob("*.exe"))
        
        for exe_file in exe_files:
            print(f"  → Signing {exe_file.name}...")
            if not self.security.sign_executable(exe_file, "windows"):
                print(f"    Warning: Failed to sign {exe_file.name}")
    
    def _create_installer(self) -> Path:
        """Create NSIS installer for Windows"""
        installer_script = self._generate_nsis_script()
        nsis_script = self.temp_build_dir / "installer.nsi"
        
        with open(nsis_script, 'w', encoding='utf-8') as f:
            f.write(installer_script)
        
        # Run NSIS compiler
        installer_exe = self.dist_dir / f"SunflowerAI_Setup_{self.config.config['version']}.exe"
        
        try:
            cmd = ["makensis", "/DVERSION=" + self.config.config['version'], str(nsis_script)]
            subprocess.run(cmd, check=True, capture_output=True)
        except FileNotFoundError:
            print("  Warning: NSIS not found, skipping installer creation")
            return self.dist_dir
        except subprocess.CalledProcessError as e:
            print(f"  Warning: NSIS compilation failed: {e}")
            return self.dist_dir
        
        if installer_exe.exists() and self.config.config["security"]["signing_required"]:
            self.security.sign_executable(installer_exe, "windows")
        
        return installer_exe if installer_exe.exists() else self.dist_dir
    
    def _generate_nsis_script(self) -> str:
        """Generate NSIS installer script"""
        # Convert paths to Windows format for NSIS
        dist_dir_win = str(self.dist_dir).replace('/', '\\')
        
        return f'''
!define PRODUCT_NAME "Sunflower AI Professional System"
!define PRODUCT_VERSION "{self.config.config['version']}"
!define PRODUCT_PUBLISHER "Sunflower AI Education"

Name "${{PRODUCT_NAME}} ${{PRODUCT_VERSION}}"
OutFile "{dist_dir_win}\\SunflowerAI_Setup_${{PRODUCT_VERSION}}.exe"
InstallDir "$PROGRAMFILES64\\Sunflower AI"
RequestExecutionLevel admin

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "{dist_dir_win}\\SUNFLOWER_CD\\system\\sunflower.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "{dist_dir_win}\\SUNFLOWER_CD\\documentation\\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  
  File /r "{dist_dir_win}\\SUNFLOWER_CD\\*.*"
  
  CreateDirectory "$APPDATA\\Sunflower AI"
  CreateShortcut "$DESKTOP\\Sunflower AI.lnk" "$INSTDIR\\system\\SunflowerLauncher.exe"
  CreateShortcut "$SMPROGRAMS\\Sunflower AI.lnk" "$INSTDIR\\system\\SunflowerLauncher.exe"
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\\*.*"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\\Sunflower AI.lnk"
  Delete "$SMPROGRAMS\\Sunflower AI.lnk"
  RMDir /r "$APPDATA\\Sunflower AI"
SectionEnd
'''


def main():
    """Main entry point for Windows compilation"""
    try:
        # Load configuration
        config = BuildConfiguration()
        
        # Create compiler instance
        compiler = WindowsCompiler(config)
        
        # Run compilation
        output_path = compiler.compile_all()
        
        print(f"\n✅ Build successful!")
        print(f"📦 Output: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

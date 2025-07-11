#!/usr/bin/env python3
"""
Windows executable compilation with security and protection.
Creates production-ready SunflowerAI.exe for CD-ROM distribution.
"""

import os
import sys
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
import json

class WindowsCompiler:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.src_dir = self.root_dir / "src"
        self.staging_dir = self.root_dir / "cdrom_staging" / "Windows"
        self.temp_dir = Path(tempfile.mkdtemp())
        self.batch_id = self.generate_batch_id()
        
    def generate_batch_id(self):
        """Generate unique batch identifier for this build"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_bytes = os.urandom(8).hex()
        return f"BATCH-{timestamp}-{random_bytes}"
    
    def prepare_build_environment(self):
        """Set up temporary build environment"""
        print("📁 Preparing build environment...")
        
        # Copy source files
        shutil.copytree(self.src_dir, self.temp_dir / "src")
        
        # Copy resources
        shutil.copytree(self.root_dir / "resources", self.temp_dir / "resources")
        
        # Create security config
        security_config = {
            "batch_id": self.batch_id,
            "build_date": datetime.now().isoformat(),
            "cdrom_required": True,
            "usb_validation": True
        }
        
        with open(self.temp_dir / "security_config.json", "w") as f:
            json.dump(security_config, f)
    
    def create_spec_file(self):
        """Generate PyInstaller spec file with security features"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = pyi_crypto.PyiBlockCipher(key='{os.urandom(16).hex()}')

a = Analysis(
    ['src/app.py'],
    pathex=['{self.temp_dir}'],
    binaries=[
        ('{self.root_dir}/platform_launchers/windows/ollama.exe', 'ollama'),
    ],
    datas=[
        ('resources', 'resources'),
        ('security_config.json', '.'),
        ('src/web', 'web'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineWidgets',
        'psutil',
        'cryptography',
        'wmi',
        'win32api',
        'win32file',
        'httpx',
        'aiofiles',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=['runtime_security.py'],
    excludes=[
        'matplotlib',
        'notebook',
        'pytest',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Inject security checks
a.scripts.insert(0, ('security_check', '''
import sys
import os
from pathlib import Path

def verify_cdrom_execution():
    """Ensure running from CD-ROM partition"""
    try:
        import win32file
        exe_path = Path(sys.executable)
        drive = str(exe_path.drive) + "\\\\"
        drive_type = win32file.GetDriveType(drive)
        
        if drive_type != win32file.DRIVE_CDROM:
            return False
            
        # Check for security marker
        security_marker = exe_path.parent / ".security" / "fingerprint.sig"
        return security_marker.exists()
    except:
        return False

if not verify_cdrom_execution():
    import ctypes
    ctypes.windll.user32.MessageBoxW(0, 
        "This application must be run from the original Sunflower AI USB.", 
        "Security Check Failed", 0x10)
    sys.exit(1)
''', 'PYSOURCE'))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SunflowerAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='{self.root_dir}/resources/icons/sunflower.ico'
)
'''
        
        spec_path = self.temp_dir / "sunflower.spec"
        with open(spec_path, "w") as f:
            f.write(spec_content)
            
        return spec_path
    
    def create_version_info(self):
        """Create Windows version information file"""
        version_info = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Sunflower AI'),
        StringStruct(u'FileDescription', u'Sunflower AI Educational System'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'SunflowerAI'),
        StringStruct(u'LegalCopyright', u'Copyright 2025 Sunflower AI. All rights reserved.'),
        StringStruct(u'OriginalFilename', u'SunflowerAI.exe'),
        StringStruct(u'ProductName', u'Sunflower AI'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
        
        with open(self.temp_dir / "version_info.txt", "w") as f:
            f.write(version_info)
    
    def create_runtime_security(self):
        """Create runtime security hook"""
        runtime_security = '''
import os
import sys
import ctypes
from pathlib import Path

# Anti-debugging
if sys.gettrace() is not None:
    ctypes.windll.kernel32.ExitProcess(1)

# Prevent DLL injection
ctypes.windll.kernel32.SetDllDirectoryW("")

# Set process as critical
ctypes.windll.ntdll.RtlSetProcessIsCritical(True, None, False)
'''
        
        with open(self.temp_dir / "runtime_security.py", "w") as f:
            f.write(runtime_security)
    
    def compile_executable(self, spec_path):
        """Run PyInstaller compilation"""
        print("🔨 Compiling Windows executable...")
        
        cmd = [
            sys.executable,
            "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath", str(self.temp_dir / "dist"),
            "--workpath", str(self.temp_dir / "build"),
            str(spec_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Compilation failed:\n{result.stderr}")
            raise RuntimeError("PyInstaller compilation failed")
            
        print("✅ Compilation successful")
    
    def apply_post_compilation_protection(self, exe_path):
        """Apply additional protection to compiled executable"""
        print("🔒 Applying post-compilation protection...")
        
        # Calculate executable hash
        with open(exe_path, "rb") as f:
            exe_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Store hash for integrity checking
        integrity_data = {
            "executable_hash": exe_hash,
            "batch_id": self.batch_id,
            "build_date": datetime.now().isoformat()
        }
        
        integrity_path = self.staging_dir.parent / ".security" / "integrity.json"
        integrity_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(integrity_path, "w") as f:
            json.dump(integrity_data, f)
    
    def stage_build(self):
        """Move compiled files to staging directory"""
        print("📦 Staging build files...")
        
        # Create staging directory
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy executable
        exe_source = self.temp_dir / "dist" / "SunflowerAI.exe"
        exe_dest = self.staging_dir / "SunflowerAI.exe"
        shutil.copy2(exe_source, exe_dest)
        
        # Apply protection
        self.apply_post_compilation_protection(exe_dest)
        
        # Copy Ollama
        ollama_source = self.root_dir / "platform_launchers" / "windows" / "ollama"
        ollama_dest = self.staging_dir / "ollama"
        if ollama_source.exists():
            shutil.copytree(ollama_source, ollama_dest, dirs_exist_ok=True)
        
        # Create autorun.inf
        autorun_content = '''[autorun]
icon=SunflowerAI.exe
label=Sunflower AI Education System
action=Start Sunflower AI
open=SunflowerAI.exe
'''
        with open(self.staging_dir / "autorun.inf", "w") as f:
            f.write(autorun_content)
        
        # Set file attributes to hidden/system for autorun
        import win32file
        import win32con
        
        win32file.SetFileAttributes(
            str(self.staging_dir / "autorun.inf"),
            win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
        )
    
    def cleanup(self):
        """Clean up temporary files"""
        print("🧹 Cleaning up...")
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def build(self):
        """Execute full build process"""
        print(f"🌻 Sunflower AI Windows Build System")
        print(f"📅 Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔖 Batch ID: {self.batch_id}")
        print("-" * 50)
        
        try:
            self.prepare_build_environment()
            self.create_version_info()
            self.create_runtime_security()
            spec_path = self.create_spec_file()
            self.compile_executable(spec_path)
            self.stage_build()
            
            print("\n✅ Windows build completed successfully!")
            print(f"📁 Output: {self.staging_dir}")
            
            # Save build record
            build_record = {
                "platform": "windows",
                "batch_id": self.batch_id,
                "build_date": datetime.now().isoformat(),
                "output_path": str(self.staging_dir),
                "success": True
            }
            
            records_dir = self.root_dir / "manufacturing" / "batch_records"
            records_dir.mkdir(parents=True, exist_ok=True)
            
            with open(records_dir / f"windows_{self.batch_id}.json", "w") as f:
                json.dump(build_record, f, indent=2)
                
        except Exception as e:
            print(f"\n❌ Build failed: {e}")
            raise
        finally:
            self.cleanup()


if __name__ == "__main__":
    compiler = WindowsCompiler()
    compiler.build()

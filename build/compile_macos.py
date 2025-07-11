#!/usr/bin/env python3
"""
macOS application compilation with security and protection.
Creates production-ready SunflowerAI.app for CD-ROM distribution.
"""

import os
import sys
import shutil
import hashlib
import tempfile
import subprocess
import plistlib
from pathlib import Path
from datetime import datetime
import json

class MacOSCompiler:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.src_dir = self.root_dir / "src"
        self.staging_dir = self.root_dir / "cdrom_staging" / "macOS"
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
        """Generate PyInstaller spec file for macOS"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = pyi_crypto.PyiBlockCipher(key='{os.urandom(16).hex()}')

a = Analysis(
    ['src/app.py'],
    pathex=['{self.temp_dir}'],
    binaries=[
        ('{self.root_dir}/platform_launchers/macos/ollama-darwin', 'ollama'),
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
import subprocess
from pathlib import Path

def verify_cdrom_execution():
    """Ensure running from read-only volume"""
    try:
        exe_path = Path(sys.executable).resolve()
        
        # Check mount information
        result = subprocess.run(
            ['mount'], 
            capture_output=True, 
            text=True
        )
        
        # Look for read-only mount
        for line in result.stdout.split('\\n'):
            if str(exe_path).startswith('/Volumes/') and 'read-only' in line:
                # Check for security marker
                app_bundle = exe_path.parent.parent.parent
                security_marker = app_bundle.parent / ".security" / "fingerprint.sig"
                return security_marker.exists()
                
        return False
    except:
        return False

if not verify_cdrom_execution():
    import tkinter.messagebox
    tkinter.messagebox.showerror(
        "Security Check Failed",
        "This application must be run from the original Sunflower AI USB."
    )
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
    entitlements_file='entitlements.plist',
)

app = BUNDLE(
    exe,
    name='SunflowerAI.app',
    icon='{self.root_dir}/resources/icons/sunflower.icns',
    bundle_identifier='com.sunflowerai.education',
    version='1.0.0',
    info_plist={{
        'CFBundleName': 'Sunflower AI',
        'CFBundleDisplayName': 'Sunflower AI Education System',
        'CFBundleGetInfoString': "Sunflower AI Education System",
        'CFBundleIdentifier': 'com.sunflowerai.education',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleSignature': 'SNFL',
        'CFBundleExecutable': 'SunflowerAI',
        'CFBundleIconFile': 'sunflower.icns',
        'LSMinimumSystemVersion': '10.14.0',
        'LSApplicationCategoryType': 'public.app-category.education',
        'NSHumanReadableCopyright': 'Copyright © 2025 Sunflower AI. All rights reserved.',
        'NSHighResolutionCapable': True,
        'LSRequiresNativeExecution': True,
        'NSRequiresAquaSystemAppearance': False,
        'NSMicrophoneUsageDescription': 'Sunflower AI needs microphone access for voice interaction.',
        'NSCameraUsageDescription': 'Sunflower AI needs camera access for video features.',
    }},
)
'''
        
        spec_path = self.temp_dir / "sunflower.spec"
        with open(spec_path, "w") as f:
            f.write(spec_content)
            
        return spec_path
    
    def create_entitlements(self):
        """Create macOS entitlements file"""
        entitlements = {
            'com.apple.security.cs.allow-unsigned-executable-memory': True,
            'com.apple.security.cs.allow-jit': True,
            'com.apple.security.cs.disable-library-validation': True,
            'com.apple.security.device.audio-input': True,
            'com.apple.security.device.camera': True,
            'com.apple.security.files.user-selected.read-only': True,
            'com.apple.security.files.user-selected.read-write': True,
        }
        
        with open(self.temp_dir / "entitlements.plist", "wb") as f:
            plistlib.dump(entitlements, f)
    
    def create_runtime_security(self):
        """Create runtime security hook for macOS"""
        runtime_security = '''
import os
import sys
from pathlib import Path

# Anti-debugging
if sys.gettrace() is not None:
    sys.exit(1)

# Verify code signature
try:
    import subprocess
    app_path = Path(sys.executable).parent.parent.parent
    result = subprocess.run(
        ['codesign', '-v', str(app_path)],
        capture_output=True
    )
    if result.returncode != 0:
        sys.exit(1)
except:
    pass
'''
        
        with open(self.temp_dir / "runtime_security.py", "w") as f:
            f.write(runtime_security)
    
    def compile_app(self, spec_path):
        """Run PyInstaller compilation"""
        print("🔨 Compiling macOS application...")
        
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
    
    def sign_app(self, app_path):
        """Code sign the application"""
        print("✏️ Signing application...")
        
        # Check if we have a signing identity
        result = subprocess.run(
            ['security', 'find-identity', '-v', '-p', 'codesigning'],
            capture_output=True,
            text=True
        )
        
        if "Developer ID Application" in result.stdout:
            # We have a signing certificate
            cmd = [
                'codesign',
                '--deep',
                '--force',
                '--verify',
                '--verbose',
                '--sign', 'Developer ID Application',
                '--options', 'runtime',
                '--entitlements', str(self.temp_dir / "entitlements.plist"),
                str(app_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Application signed successfully")
            else:
                print(f"⚠️ Signing failed: {result.stderr}")
                print("⚠️ Continuing without signature (development build)")
        else:
            print("⚠️ No signing certificate found (development build)")
    
    def apply_post_compilation_protection(self, app_path):
        """Apply additional protection to compiled app"""
        print("🔒 Applying post-compilation protection...")
        
        # Calculate app bundle hash
        import hashlib
        hasher = hashlib.sha256()
        
        for root, dirs, files in os.walk(app_path):
            for file in sorted(files):
                file_path = Path(root) / file
                with open(file_path, "rb") as f:
                    hasher.update(f.read())
        
        app_hash = hasher.hexdigest()
        
        # Store hash for integrity checking
        integrity_data = {
            "app_bundle_hash": app_hash,
            "batch_id": self.batch_id,
            "build_date": datetime.now().isoformat()
        }
        
        integrity_path = self.staging_dir.parent / ".security" / "integrity_mac.json"
        integrity_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(integrity_path, "w") as f:
            json.dump(integrity_data, f)
    
    def stage_build(self):
        """Move compiled files to staging directory"""
        print("📦 Staging build files...")
        
        # Create staging directory
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy app bundle
        app_source = self.temp_dir / "dist" / "SunflowerAI.app"
        app_dest = self.staging_dir / "SunflowerAI.app"
        
        if app_dest.exists():
            shutil.rmtree(app_dest)
            
        shutil.copytree(app_source, app_dest)
        
        # Apply protection
        self.apply_post_compilation_protection(app_dest)
        
        # Copy Ollama
        ollama_source = self.root_dir / "platform_launchers" / "macos" / "ollama-darwin"
        ollama_dest = self.staging_dir / "ollama-darwin"
        if ollama_source.exists():
            shutil.copy2(ollama_source, ollama_dest)
            # Make executable
            os.chmod(ollama_dest, 0o755)
    
    def cleanup(self):
        """Clean up temporary files"""
        print("🧹 Cleaning up...")
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def build(self):
        """Execute full build process"""
        print(f"🌻 Sunflower AI macOS Build System")
        print(f"📅 Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔖 Batch ID: {self.batch_id}")
        print("-" * 50)
        
        try:
            self.prepare_build_environment()
            self.create_entitlements()
            self.create_runtime_security()
            spec_path = self.create_spec_file()
            self.compile_app(spec_path)
            
            app_path = self.temp_dir / "dist" / "SunflowerAI.app"
            self.sign_app(app_path)
            
            self.stage_build()
            
            print("\n✅ macOS build completed successfully!")
            print(f"📁 Output: {self.staging_dir}")
            
            # Save build record
            build_record = {
                "platform": "macos",
                "batch_id": self.batch_id,
                "build_date": datetime.now().isoformat(),
                "output_path": str(self.staging_dir),
                "success": True
            }
            
            records_dir = self.root_dir / "manufacturing" / "batch_records"
            records_dir.mkdir(parents=True, exist_ok=True)
            
            with open(records_dir / f"macos_{self.batch_id}.json", "w") as f:
                json.dump(build_record, f, indent=2)
                
        except Exception as e:
            print(f"\n❌ Build failed: {e}")
            raise
        finally:
            self.cleanup()


if __name__ == "__main__":
    compiler = MacOSCompiler()
    compiler.build()

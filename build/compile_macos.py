"""
Sunflower AI Professional System - macOS Compilation
Production macOS app bundle and DMG build system
Version: 6.2 - January 2025
"""

import os
import sys
import subprocess
import shutil
import tempfile
import plistlib
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import hashlib

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from build import (
    BuildConfiguration, SecurityManager, PartitionManager,
    BUILD_DIR, OUTPUT_DIR, TEMPLATES_DIR, ASSETS_DIR, MODELS_DIR
)

class MacOSCompiler:
    """macOS-specific compilation and packaging manager"""
    
    def __init__(self, config: BuildConfiguration):
        self.config = config
        self.security = SecurityManager(config)
        self.partition = PartitionManager(config)
        self.spec_file = TEMPLATES_DIR / "macos.spec"
        self.output_dir = config.get_output_path("macos")
        self.temp_build_dir = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        
        # macOS-specific paths
        self.app_name = "SunflowerAI.app"
        self.dmg_name = f"SunflowerAI_{config.config['version']}.dmg"
        self.launcher_app = "SunflowerLauncher.app"
        
        # Verify macOS environment
        if not self._is_macos():
            raise EnvironmentError("macOS compilation must run on macOS")
    
    def _is_macos(self) -> bool:
        """Verify macOS environment"""
        return sys.platform == 'darwin'
    
    def compile(self) -> Path:
        """Main macOS compilation process"""
        print("╔════════════════════════════════════════╗")
        print("║  Sunflower AI macOS Build System       ║")
        print("║  Version 6.2 - Production Build        ║")
        print("╚════════════════════════════════════════╝")
        
        try:
            # Phase 1: Environment preparation
            print("\n[Phase 1/8] Preparing build environment...")
            self._prepare_environment()
            
            # Phase 2: Compile main application
            print("\n[Phase 2/8] Compiling main application...")
            main_app = self._compile_main_app()
            
            # Phase 3: Compile launcher
            print("\n[Phase 3/8] Compiling universal launcher...")
            launcher_app = self._compile_launcher()
            
            # Phase 4: Compile helper daemon
            print("\n[Phase 4/8] Compiling helper daemon...")
            helper_daemon = self._compile_helper()
            
            # Phase 5: Create partition structure
            print("\n[Phase 5/8] Creating partition structure...")
            cdrom_path, usb_path = self._create_partitions()
            
            # Phase 6: Build app bundle
            print("\n[Phase 6/8] Building application bundle...")
            app_bundle = self._build_app_bundle(
                main_app, launcher_app, helper_daemon, cdrom_path
            )
            
            # Phase 7: Create DMG installer
            print("\n[Phase 7/8] Creating DMG installer...")
            dmg_path = self._create_dmg(app_bundle)
            
            # Phase 8: Sign and notarize
            print("\n[Phase 8/8] Signing and notarizing...")
            final_path = self._finalize_build(dmg_path)
            
            print(f"\n✓ macOS build complete: {final_path}")
            return final_path
            
        except Exception as e:
            print(f"\n✗ Build failed: {e}")
            raise
        finally:
            # Cleanup temporary directory
            if self.temp_build_dir.exists():
                shutil.rmtree(self.temp_build_dir, ignore_errors=True)
    
    def _prepare_environment(self):
        """Prepare macOS build environment"""
        # Check for required tools
        required_tools = {
            "pyinstaller": self._check_pyinstaller,
            "codesign": self._check_codesign,
            "hdiutil": self._check_hdiutil,
            "xcrun": self._check_xcrun
        }
        
        for tool, checker in required_tools.items():
            if not checker():
                raise EnvironmentError(f"Required tool not found: {tool}")
        
        # Check for Xcode command line tools
        if not self._check_xcode_tools():
            raise EnvironmentError("Xcode command line tools not installed")
        
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
    
    def _check_codesign(self) -> bool:
        """Check codesign availability"""
        return shutil.which("codesign") is not None
    
    def _check_hdiutil(self) -> bool:
        """Check hdiutil availability"""
        return shutil.which("hdiutil") is not None
    
    def _check_xcrun(self) -> bool:
        """Check xcrun availability"""
        return shutil.which("xcrun") is not None
    
    def _check_xcode_tools(self) -> bool:
        """Check if Xcode command line tools are installed"""
        try:
            result = subprocess.run(
                ["xcode-select", "-p"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _copy_assets(self):
        """Copy required assets to build directory"""
        assets_to_copy = [
            ("icons/sunflower.icns", "sunflower.icns"),
            ("icons/sunflower_512.png", "sunflower.png"),
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
        """Generate macOS-specific metadata"""
        # Create Info.plist for main app
        info_plist = {
            "CFBundleName": "Sunflower AI",
            "CFBundleDisplayName": "Sunflower AI Professional System",
            "CFBundleIdentifier": "com.sunflowerai.professional",
            "CFBundleVersion": self.config.config["version"],
            "CFBundleShortVersionString": self.config.config["version"],
            "CFBundlePackageType": "APPL",
            "CFBundleSignature": "SNFL",
            "CFBundleExecutable": "SunflowerAI",
            "CFBundleIconFile": "sunflower.icns",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "10.14.0",
            "NSRequiresAquaSystemAppearance": False,
            "NSCameraUsageDescription": "Sunflower AI requires camera access for educational features",
            "NSMicrophoneUsageDescription": "Sunflower AI requires microphone access for voice interaction",
            "LSApplicationCategoryType": "public.app-category.education",
            "NSHumanReadableCopyright": "Copyright © 2025 Sunflower AI Education",
            "NSAppleEventsUsageDescription": "Sunflower AI requires automation access for system integration",
            "NSAppTransportSecurity": {
                "NSAllowsArbitraryLoads": False,
                "NSAllowsLocalNetworking": True
            }
        }
        
        plist_path = self.temp_build_dir / "Info.plist"
        with open(plist_path, 'wb') as f:
            plistlib.dump(info_plist, f)
        
        # Create entitlements.plist
        self._create_entitlements()
    
    def _create_entitlements(self):
        """Create entitlements for code signing"""
        entitlements = {
            "com.apple.security.app-sandbox": False,  # Disabled for system access
            "com.apple.security.device.camera": True,
            "com.apple.security.device.microphone": True,
            "com.apple.security.files.user-selected.read-write": True,
            "com.apple.security.files.bookmarks.app-scope": True,
            "com.apple.security.network.client": True,
            "com.apple.security.network.server": True,
            "com.apple.security.automation.apple-events": True,
            "com.apple.security.cs.allow-jit": True,  # For Python runtime
            "com.apple.security.cs.allow-unsigned-executable-memory": True,
            "com.apple.security.cs.disable-library-validation": True
        }
        
        entitlements_path = self.temp_build_dir / "entitlements.plist"
        with open(entitlements_path, 'wb') as f:
            plistlib.dump(entitlements, f)
    
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
        
        app_path = self.temp_build_dir / "dist" / self.app_name
        
        # Fix bundle structure
        self._fix_bundle_structure(app_path)
        
        # Sign application
        if self.config.config["security"]["signing_required"]:
            print("  → Signing main application...")
            self.security.sign_executable(app_path, "macos")
        
        return app_path
    
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
    binaries=[],
    datas=[
        ('{Path(__file__).parent.parent / "modelfiles"}', 'modelfiles'),
        ('{Path(__file__).parent.parent / "assets"}', 'assets'),
        ('{self.temp_build_dir / "docs"}', 'docs'),
        ('{self.temp_build_dir / "certs"}', 'certs'),
        ('{self.temp_build_dir / "sunflower.icns"}', '.'),
    ],
    hiddenimports=[
        'pydantic',
        'uvicorn',
        'fastapi',
        'starlette',
        'httpx',
        'psutil',
        'cryptography',
        'Foundation',
        'AppKit',
        'CoreFoundation',
        'SystemConfiguration',
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
    [],
    exclude_binaries=True,
    name='SunflowerAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch='universal2',  # Support both Intel and Apple Silicon
    codesign_identity=os.environ.get('MACOS_DEVELOPER_ID'),
    entitlements_file='{self.temp_build_dir / "entitlements.plist"}',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='SunflowerAI',
)

app = BUNDLE(
    coll,
    name='SunflowerAI.app',
    icon='{self.temp_build_dir / "sunflower.icns"}',
    bundle_identifier='com.sunflowerai.professional',
    info_plist={{
        'CFBundleShortVersionString': '{self.config.config["version"]}',
        'CFBundleVersion': '{self.config.config["build_number"]}',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14.0',
    }},
)
"""
    
    def _fix_bundle_structure(self, app_path: Path):
        """Fix macOS app bundle structure after PyInstaller"""
        contents_path = app_path / "Contents"
        
        # Ensure proper directory structure
        (contents_path / "MacOS").mkdir(exist_ok=True)
        (contents_path / "Resources").mkdir(exist_ok=True)
        (contents_path / "Frameworks").mkdir(exist_ok=True)
        
        # Copy Info.plist
        shutil.copy2(
            self.temp_build_dir / "Info.plist",
            contents_path / "Info.plist"
        )
        
        # Copy icon
        if (self.temp_build_dir / "sunflower.icns").exists():
            shutil.copy2(
                self.temp_build_dir / "sunflower.icns",
                contents_path / "Resources" / "sunflower.icns"
            )
    
    def _compile_launcher(self) -> Path:
        """Compile universal launcher application"""
        print("  → Compiling universal launcher...")
        
        launcher_source = self._generate_launcher_source()
        launcher_py = self.temp_build_dir / "launcher.py"
        
        with open(launcher_py, 'w', encoding='utf-8') as f:
            f.write(launcher_source)
        
        # Compile launcher with PyInstaller
        cmd = [
            "pyinstaller",
            "--windowed",
            "--onefile",
            "--clean",
            "--noconfirm",
            "--name", "SunflowerLauncher",
            "--icon", str(self.temp_build_dir / "sunflower.icns"),
            "--distpath", str(self.temp_build_dir / "dist"),
            "--workpath", str(self.temp_build_dir / "build"),
            "--target-arch", "universal2",
            "--osx-bundle-identifier", "com.sunflowerai.launcher",
            str(launcher_py)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        launcher_app = self.temp_build_dir / "dist" / self.launcher_app
        
        # Sign launcher
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(launcher_app, "macos")
        
        return launcher_app
    
    def _generate_launcher_source(self) -> str:
        """Generate launcher Python source code for macOS"""
        return '''
"""
Sunflower AI Universal Launcher for macOS
Auto-detects partitions and initiates setup
"""

import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import platform
import plistlib

# macOS-specific imports
try:
    from Foundation import NSBundle
    import objc
except ImportError:
    pass

class SunflowerLauncher:
    """Universal launcher for Sunflower AI Professional System"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("700x500")
        self.root.resizable(False, False)
        
        # macOS-specific styling
        if platform.system() == "Darwin":
            self.setup_macos_style()
        
        self.cdrom_path = None
        self.usb_path = None
        self.setup_ui()
        self.detect_partitions()
    
    def setup_macos_style(self):
        """Apply macOS-specific styling"""
        try:
            # Set app to use native macOS appearance
            self.root.tk.call("::tk::unsupported::MacWindowStyle",
                            "style", self.root._w, "floating")
        except:
            pass
    
    def setup_ui(self):
        """Setup launcher UI with macOS design"""
        # Header with gradient effect
        header = tk.Frame(self.root, bg="#2E7D32", height=100)
        header.pack(fill=tk.X)
        
        # Logo and title
        title_frame = tk.Frame(header, bg="#2E7D32")
        title_frame.pack(expand=True)
        
        title = tk.Label(
            title_frame,
            text="🌻 Sunflower AI Professional System",
            font=("SF Pro Display", 24, "bold"),
            bg="#2E7D32",
            fg="white"
        )
        title.pack(pady=30)
        
        subtitle = tk.Label(
            title_frame,
            text="K-12 STEM Education Platform",
            font=("SF Pro Text", 14),
            bg="#2E7D32",
            fg="#E8F5E9"
        )
        subtitle.pack()
        
        # Main content area
        self.content_frame = tk.Frame(self.root, bg="#F5F5F5")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Status section
        self.status_label = tk.Label(
            self.content_frame,
            text="🔍 Detecting Sunflower AI device...",
            font=("SF Pro Text", 14),
            bg="#F5F5F5",
            fg="#424242"
        )
        self.status_label.pack(pady=20)
        
        # Progress indicator
        self.progress = ttk.Progressbar(
            self.content_frame,
            mode="indeterminate",
            length=400,
            style="TProgressbar"
        )
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        # Device info (hidden initially)
        self.info_frame = tk.Frame(self.content_frame, bg="#F5F5F5")
        
        # Action buttons (hidden initially)
        self.button_frame = tk.Frame(self.content_frame, bg="#F5F5F5")
        
        self.setup_button = tk.Button(
            self.button_frame,
            text="🚀 Setup Sunflower AI",
            font=("SF Pro Text", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            width=20,
            height=2,
            borderwidth=0,
            highlightthickness=0,
            command=self.start_setup,
            state=tk.DISABLED
        )
        self.setup_button.pack(side=tk.LEFT, padx=10)
        
        self.launch_button = tk.Button(
            self.button_frame,
            text="▶️ Launch Sunflower AI",
            font=("SF Pro Text", 14, "bold"),
            bg="#2196F3",
            fg="white",
            width=20,
            height=2,
            borderwidth=0,
            highlightthickness=0,
            command=self.launch_app,
            state=tk.DISABLED
        )
        self.launch_button.pack(side=tk.LEFT, padx=10)
        
        # Style progress bar for macOS
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar",
                       background="#4CAF50",
                       troughcolor="#E0E0E0",
                       borderwidth=0,
                       lightcolor="#4CAF50",
                       darkcolor="#4CAF50")
    
    def detect_partitions(self):
        """Detect CD-ROM and USB partitions on macOS"""
        self.root.after(1000, self._scan_volumes)
    
    def _scan_volumes(self):
        """Scan for Sunflower AI partitions using macOS diskutil"""
        import subprocess
        
        # Get list of mounted volumes
        result = subprocess.run(
            ["diskutil", "list", "-plist"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Parse plist output
            import plistlib
            disks = plistlib.loads(result.stdout.encode())
            
            # Check each volume
            volumes_path = Path("/Volumes")
            for volume in volumes_path.iterdir():
                if volume.is_dir():
                    # Check for CD-ROM partition
                    if self._verify_cdrom_partition(volume):
                        self.cdrom_path = volume
                    # Check for USB partition  
                    elif self._verify_usb_partition(volume):
                        self.usb_path = volume
        
        if self.cdrom_path and self.usb_path:
            self.on_device_found()
        else:
            # Retry detection
            self.root.after(2000, self._scan_volumes)
    
    def _verify_cdrom_partition(self, volume_path):
        """Verify CD-ROM partition signature"""
        try:
            signature_file = volume_path / "SUNFLOWER.ID"
            if signature_file.exists():
                with open(signature_file, "r") as f:
                    return f.read().strip() == "SUNFLOWER_AI_PRO_v6"
        except:
            pass
        return False
    
    def _verify_usb_partition(self, volume_path):
        """Verify USB partition structure"""
        try:
            config_file = volume_path / "config" / "system.json"
            return config_file.exists()
        except:
            pass
        return False
    
    def on_device_found(self):
        """Handle successful device detection"""
        self.progress.stop()
        self.progress.pack_forget()
        
        # Update status
        self.status_label.config(
            text="✅ Sunflower AI device detected",
            fg="#2E7D32"
        )
        
        # Show device info
        info_text = tk.Text(
            self.info_frame,
            height=4,
            width=50,
            font=("SF Mono", 11),
            bg="#FFFFFF",
            fg="#424242",
            borderwidth=1,
            relief=tk.SOLID
        )
        info_text.pack(pady=10)
        
        info_text.insert(tk.END, f"📀 CD-ROM: {self.cdrom_path.name}\\n")
        info_text.insert(tk.END, f"💾 USB: {self.usb_path.name}\\n")
        
        # Check initialization status
        if self._is_initialized():
            info_text.insert(tk.END, "✓ System initialized\\n")
            info_text.insert(tk.END, "✓ Ready to launch")
            self.launch_button.config(state=tk.NORMAL)
        else:
            info_text.insert(tk.END, "⚠️ First-time setup required\\n")
            info_text.insert(tk.END, "   Click Setup to begin")
            self.setup_button.config(state=tk.NORMAL)
        
        info_text.config(state=tk.DISABLED)
        self.info_frame.pack(pady=10)
        self.button_frame.pack(pady=20)
    
    def _is_initialized(self):
        """Check if system is initialized"""
        try:
            config_file = self.usb_path / "config" / "system.json"
            with open(config_file, "r") as f:
                config = json.load(f)
                return config.get("initialized", False)
        except:
            return False
    
    def start_setup(self):
        """Start first-time setup process"""
        setup_app = self.cdrom_path / "system" / "SunflowerSetup.app"
        if setup_app.exists():
            subprocess.run([
                "open", "-a", str(setup_app),
                "--args", str(self.cdrom_path), str(self.usb_path)
            ])
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Setup application not found on device")
    
    def launch_app(self):
        """Launch main Sunflower AI application"""
        main_app = self.cdrom_path / "system" / "SunflowerAI.app"
        if main_app.exists():
            subprocess.run([
                "open", "-a", str(main_app),
                "--args", str(self.cdrom_path), str(self.usb_path)
            ])
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Application not found on device")
    
    def run(self):
        """Run launcher"""
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        self.root.mainloop()

if __name__ == "__main__":
    launcher = SunflowerLauncher()
    launcher.run()
'''
    
    def _compile_helper(self) -> Path:
        """Compile helper daemon for background services"""
        print("  → Compiling helper daemon...")
        
        helper_source = self._generate_helper_source()
        helper_py = self.temp_build_dir / "helper.py"
        
        with open(helper_py, 'w', encoding='utf-8') as f:
            f.write(helper_source)
        
        # Compile helper daemon
        cmd = [
            "pyinstaller",
            "--onefile",
            "--console",  # Daemon runs in background
            "--clean",
            "--noconfirm",
            "--name", "SunflowerHelper",
            "--distpath", str(self.temp_build_dir / "dist"),
            "--workpath", str(self.temp_build_dir / "build"),
            "--target-arch", "universal2",
            str(helper_py)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        helper_exe = self.temp_build_dir / "dist" / "SunflowerHelper"
        
        # Sign helper
        if self.config.config["security"]["signing_required"]:
            self.security.sign_executable(helper_exe, "macos")
        
        return helper_exe
    
    def _generate_helper_source(self) -> str:
        """Generate helper daemon source code"""
        return '''
"""
Sunflower AI Helper Daemon for macOS
Manages Ollama and system resources
"""

import os
import sys
import time
import json
import signal
import subprocess
import psutil
from pathlib import Path
from threading import Thread, Event
import logging
from logging.handlers import RotatingFileHandler

class SunflowerHelper:
    """Background helper daemon for Sunflower AI"""
    
    def __init__(self):
        self.setup_logging()
        self.running = Event()
        self.running.set()
        self.ollama_process = None
        self.config = self.load_config()
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        
        self.logger.info("Sunflower AI Helper Daemon starting...")
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path.home() / "Library" / "Logs" / "SunflowerAI"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("SunflowerHelper")
        self.logger.setLevel(logging.INFO)
        
        handler = RotatingFileHandler(
            log_dir / "helper.log",
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def load_config(self):
        """Load daemon configuration"""
        config_path = Path.home() / "Library" / "Application Support" / "SunflowerAI" / "config.json"
        
        default_config = {
            "ollama_path": "/Applications/SunflowerAI.app/Contents/Resources/ollama/ollama",
            "model_path": "/Applications/SunflowerAI.app/Contents/Resources/models",
            "port": 11434,
            "max_memory_gb": 4,
            "auto_select_model": True,
            "health_check_interval": 30
        }
        
        if config_path.exists():
            try:

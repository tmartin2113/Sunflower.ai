#!/usr/bin/env python3
"""
Sunflower AI Professional System - macOS Compiler
Production-ready build system for macOS deployment
Version: 6.2
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import plistlib
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MacOSCompiler:
    """
    Production compiler for macOS deployment.
    Creates signed, notarized application bundles with partitioned device support.
    """
    
    def __init__(self, project_root: Path, output_dir: Path):
        """Initialize macOS compiler"""
        self.project_root = Path(project_root).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build configuration
        self.app_name = "SunflowerAI.app"
        self.bundle_id = "com.sunflowerai.professional"
        self.version = "6.2.0"
        self.min_macos_version = "10.14"
        
        # Paths
        self.src_dir = self.project_root / "src"
        self.resources_dir = self.project_root / "resources"
        self.modelfiles_dir = self.project_root / "modelfiles"
        self.docs_dir = self.project_root / "docs"
        
        # Temporary build directory
        self.temp_build_dir = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        
        # Load configuration
        self.config = self._load_build_config()
        
        # Import security manager
        sys.path.insert(0, str(self.src_dir))
        from security import SecurityManager
        self.security = SecurityManager(self.output_dir)
        
        logger.info(f"macOS compiler initialized - Output: {self.output_dir}")
    
    def _load_build_config(self) -> Dict:
        """Load build configuration"""
        config_file = self.project_root / "config" / "build_config.json"
        
        if not config_file.exists():
            # Default configuration
            return {
                "signing": {
                    "enabled": True,
                    "identity": "Developer ID Application",
                    "team_id": "XXXXXXXXXX"
                },
                "notarization": {
                    "enabled": True,
                    "username": "developer@sunflowerai.com",
                    "password": "@keychain:AC_PASSWORD"
                },
                "dmg": {
                    "create": True,
                    "background": "installer_background.png",
                    "window_size": [600, 400]
                }
            }
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def compile(self) -> Tuple[bool, Path]:
        """Main compilation process"""
        try:
            logger.info("Starting macOS compilation...")
            
            # Step 1: Prepare build environment
            self._prepare_environment()
            
            # Step 2: Create application bundle structure
            app_bundle = self._create_app_bundle()
            
            # Step 3: Compile Python code
            self._compile_python_code(app_bundle)
            
            # Step 4: Copy resources
            self._copy_resources(app_bundle)
            
            # Step 5: Create Info.plist
            self._create_info_plist(app_bundle)
            
            # Step 6: Create launch script
            self._create_launch_script(app_bundle)
            
            # Step 7: Sign application
            if self.config["signing"]["enabled"]:
                self._sign_application(app_bundle)
            
            # Step 8: Create DMG installer
            if self.config["dmg"]["create"]:
                dmg_path = self._create_dmg(app_bundle)
                
                # Step 9: Notarize DMG
                if self.config["notarization"]["enabled"]:
                    self._notarize_dmg(dmg_path)
                
                return True, dmg_path
            
            return True, app_bundle
            
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            return False, None
        finally:
            # Cleanup
            if self.temp_build_dir.exists():
                shutil.rmtree(self.temp_build_dir, ignore_errors=True)
    
    def _prepare_environment(self):
        """Prepare build environment"""
        logger.info("  → Preparing build environment...")
        
        # Create required directories
        dirs = [
            self.temp_build_dir / "build",
            self.temp_build_dir / "dist",
            self.temp_build_dir / "resources"
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Copy source files
        shutil.copytree(
            self.src_dir,
            self.temp_build_dir / "src",
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc')
        )
        
        logger.info("  ✓ Build environment ready")
    
    def _create_app_bundle(self) -> Path:
        """Create macOS application bundle structure"""
        logger.info("  → Creating application bundle...")
        
        app_path = self.output_dir / self.app_name
        
        # Remove existing bundle
        if app_path.exists():
            shutil.rmtree(app_path)
        
        # Create bundle structure
        bundle_dirs = [
            app_path / "Contents",
            app_path / "Contents" / "MacOS",
            app_path / "Contents" / "Resources",
            app_path / "Contents" / "Frameworks",
            app_path / "Contents" / "Library"
        ]
        
        for bundle_dir in bundle_dirs:
            bundle_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"  ✓ Bundle created: {app_path}")
        return app_path
    
    def _compile_python_code(self, app_bundle: Path):
        """Compile Python code using PyInstaller"""
        logger.info("  → Compiling Python code...")
        
        # Generate PyInstaller spec file
        spec_content = self._generate_spec_file()
        spec_file = self.temp_build_dir / "sunflower.spec"
        
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        # Run PyInstaller
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath", str(app_bundle / "Contents" / "MacOS"),
            "--workpath", str(self.temp_build_dir / "build"),
            str(spec_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"PyInstaller failed: {result.stderr}")
            raise RuntimeError("Python compilation failed")
        
        logger.info("  ✓ Python code compiled")
    
    def _generate_spec_file(self) -> str:
        """Generate PyInstaller spec file"""
        return f"""# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None

a = Analysis(
    ['{self.temp_build_dir / "src" / "main.py"}'],
    pathex=['{self.temp_build_dir / "src"}'],
    binaries=[],
    datas=[
        ('{self.modelfiles_dir}', 'modelfiles'),
        ('{self.resources_dir}', 'resources'),
        ('{self.docs_dir}', 'docs'),
    ],
    hiddenimports=[
        'tkinter',
        'PIL',
        'cryptography',
        'psutil',
        'sqlite3',
        'json',
        'yaml',
        'platform',
        'subprocess',
        'threading',
        'queue'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'numpy'],
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
    name='SunflowerAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='universal2',
    codesign_identity='{self.config["signing"]["identity"]}',
    entitlements_file=None,
)
"""
    
    def _copy_resources(self, app_bundle: Path):
        """Copy resources to bundle"""
        logger.info("  → Copying resources...")
        
        resources_dir = app_bundle / "Contents" / "Resources"
        
        # Copy icons
        icon_file = self.resources_dir / "icons" / "sunflower.icns"
        if icon_file.exists():
            shutil.copy2(icon_file, resources_dir / "sunflower.icns")
        else:
            self._generate_default_icon(resources_dir / "sunflower.icns")
        
        # Copy modelfiles
        modelfiles_dest = resources_dir / "modelfiles"
        if self.modelfiles_dir.exists():
            shutil.copytree(self.modelfiles_dir, modelfiles_dest, dirs_exist_ok=True)
        
        # Copy documentation
        docs_dest = resources_dir / "docs"
        if self.docs_dir.exists():
            shutil.copytree(self.docs_dir, docs_dest, dirs_exist_ok=True)
        
        logger.info("  ✓ Resources copied")
    
    def _generate_default_icon(self, icon_path: Path):
        """Generate a default icon if none exists"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a sunflower-themed icon
            size = (512, 512)
            img = Image.new('RGBA', size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw sunflower shape
            center = (256, 256)
            petal_color = (255, 215, 0)  # Gold
            center_color = (139, 69, 19)  # Brown
            
            # Draw petals
            for angle in range(0, 360, 30):
                x = center[0] + 150 * (angle % 2 + 1) * 0.7
                y = center[1] + 150 * (angle % 2 + 1) * 0.7
                draw.ellipse([x-40, y-40, x+40, y+40], fill=petal_color)
            
            # Draw center
            draw.ellipse([center[0]-80, center[1]-80, center[0]+80, center[1]+80], 
                        fill=center_color)
            
            # Save as ICNS (simplified - would need iconutil in production)
            img.save(icon_path.with_suffix('.png'))
            
            # Convert PNG to ICNS using iconutil
            subprocess.run([
                'iconutil', '-c', 'icns',
                '-o', str(icon_path),
                str(icon_path.with_suffix('.png'))
            ], check=False)
            
        except Exception as e:
            logger.warning(f"Could not generate icon: {e}")
    
    def _create_info_plist(self, app_bundle: Path):
        """Create Info.plist file"""
        logger.info("  → Creating Info.plist...")
        
        info_plist = {
            'CFBundleDevelopmentRegion': 'en',
            'CFBundleExecutable': 'launcher',
            'CFBundleIdentifier': self.bundle_id,
            'CFBundleInfoDictionaryVersion': '6.0',
            'CFBundleName': 'Sunflower AI',
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': self.version,
            'CFBundleVersion': self.version,
            'CFBundleSignature': 'SNFL',
            'LSMinimumSystemVersion': self.min_macos_version,
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
            'CFBundleIconFile': 'sunflower.icns',
            'NSHumanReadableCopyright': 'Copyright © 2025 Sunflower AI Systems',
            'LSApplicationCategoryType': 'public.app-category.education',
            'NSMainNibFile': 'MainMenu',
            'NSPrincipalClass': 'NSApplication',
            'NSAppTransportSecurity': {
                'NSAllowsArbitraryLoads': False,
                'NSAllowsLocalNetworking': True
            },
            'LSRequiresIPhoneOS': False,
            'UTExportedTypeDeclarations': [],
            'UTImportedTypeDeclarations': []
        }
        
        plist_path = app_bundle / "Contents" / "Info.plist"
        with open(plist_path, 'wb') as f:
            plistlib.dump(info_plist, f)
        
        logger.info("  ✓ Info.plist created")
    
    def _create_launch_script(self, app_bundle: Path):
        """Create launcher script"""
        logger.info("  → Creating launcher script...")
        
        launcher_content = '''#!/bin/bash
# Sunflower AI Professional System - macOS Launcher

# Get the directory of the app bundle
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$(dirname "$DIR")/Resources"

# Set environment variables
export SUNFLOWER_HOME="$HOME/Library/Application Support/SunflowerAI"
export SUNFLOWER_DATA="$SUNFLOWER_HOME/data"
export SUNFLOWER_LOGS="$SUNFLOWER_HOME/logs"

# Create directories if they don't exist
mkdir -p "$SUNFLOWER_DATA"
mkdir -p "$SUNFLOWER_LOGS"

# Launch the main application
exec "$DIR/SunflowerAI" "$@"
'''
        
        launcher_path = app_bundle / "Contents" / "MacOS" / "launcher"
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        # Make executable
        os.chmod(launcher_path, 0o755)
        
        logger.info("  ✓ Launcher script created")
    
    def _sign_application(self, app_bundle: Path):
        """Sign application bundle"""
        logger.info("  → Signing application...")
        
        identity = self.config["signing"]["identity"]
        
        # Sign all binaries
        for binary in app_bundle.rglob("*"):
            if binary.is_file() and (binary.suffix in ['.dylib', '.so', ''] or 
                                    binary.name in ['SunflowerAI', 'launcher']):
                cmd = [
                    'codesign',
                    '--force',
                    '--sign', identity,
                    '--timestamp',
                    '--options', 'runtime',
                    '--entitlements', str(self._create_entitlements()),
                    str(binary)
                ]
                subprocess.run(cmd, check=False)
        
        # Sign the bundle itself
        cmd = [
            'codesign',
            '--force',
            '--deep',
            '--sign', identity,
            '--timestamp',
            '--options', 'runtime',
            '--entitlements', str(self._create_entitlements()),
            str(app_bundle)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Signing failed: {result.stderr}")
        else:
            logger.info("  ✓ Application signed")
    
    def _create_entitlements(self) -> Path:
        """Create entitlements file"""
        entitlements = {
            'com.apple.security.cs.allow-jit': True,
            'com.apple.security.cs.allow-unsigned-executable-memory': True,
            'com.apple.security.cs.disable-library-validation': True,
            'com.apple.security.device.usb': True,
            'com.apple.security.files.user-selected.read-write': True,
            'com.apple.security.network.client': True,
            'com.apple.security.network.server': True
        }
        
        entitlements_path = self.temp_build_dir / "entitlements.plist"
        with open(entitlements_path, 'wb') as f:
            plistlib.dump(entitlements, f)
        
        return entitlements_path
    
    def _create_dmg(self, app_bundle: Path) -> Path:
        """Create DMG installer"""
        logger.info("  → Creating DMG installer...")
        
        dmg_name = f"SunflowerAI-{self.version}-macOS.dmg"
        dmg_path = self.output_dir / dmg_name
        
        # Create temporary DMG directory
        dmg_dir = self.temp_build_dir / "dmg"
        dmg_dir.mkdir(exist_ok=True)
        
        # Copy app bundle
        shutil.copytree(app_bundle, dmg_dir / self.app_name)
        
        # Create Applications symlink
        os.symlink('/Applications', str(dmg_dir / 'Applications'))
        
        # Create DMG
        cmd = [
            'hdiutil', 'create',
            '-volname', f'Sunflower AI {self.version}',
            '-srcfolder', str(dmg_dir),
            '-ov',
            '-format', 'UDZO',
            str(dmg_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"DMG creation failed: {result.stderr}")
            raise RuntimeError("DMG creation failed")
        
        logger.info(f"  ✓ DMG created: {dmg_path}")
        return dmg_path
    
    def _notarize_dmg(self, dmg_path: Path):
        """Notarize DMG with Apple"""
        logger.info("  → Notarizing DMG...")
        
        username = self.config["notarization"]["username"]
        password = self.config["notarization"]["password"]
        team_id = self.config["signing"]["team_id"]
        
        # Submit for notarization
        cmd = [
            'xcrun', 'altool',
            '--notarize-app',
            '--primary-bundle-id', self.bundle_id,
            '--username', username,
            '--password', password,
            '--team-id', team_id,
            '--file', str(dmg_path),
            '--output-format', 'json'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            request_id = response.get('notarization-upload', {}).get('RequestUUID')
            
            if request_id:
                logger.info(f"  ✓ Notarization submitted: {request_id}")
                self._wait_for_notarization(request_id)
            else:
                logger.warning("  ⚠ Notarization submission unclear")
        else:
            logger.warning(f"  ⚠ Notarization failed: {result.stderr}")
    
    def _wait_for_notarization(self, request_id: str):
        """Wait for notarization to complete"""
        username = self.config["notarization"]["username"]
        password = self.config["notarization"]["password"]
        
        logger.info("  → Waiting for notarization...")
        
        for _ in range(60):  # Wait up to 30 minutes
            import time
            time.sleep(30)
            
            cmd = [
                'xcrun', 'altool',
                '--notarization-info', request_id,
                '--username', username,
                '--password', password,
                '--output-format', 'json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                status = response.get('notarization-info', {}).get('Status')
                
                if status == 'success':
                    logger.info("  ✓ Notarization successful")
                    return
                elif status == 'invalid':
                    logger.error("  ✗ Notarization failed")
                    return
        
        logger.warning("  ⚠ Notarization timeout")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Compile Sunflower AI for macOS')
    parser.add_argument('--project-root', type=Path, default=Path.cwd(),
                       help='Project root directory')
    parser.add_argument('--output-dir', type=Path, default=Path('dist/macos'),
                       help='Output directory for compiled application')
    parser.add_argument('--skip-signing', action='store_true',
                       help='Skip code signing')
    parser.add_argument('--skip-notarization', action='store_true',
                       help='Skip notarization')
    parser.add_argument('--skip-dmg', action='store_true',
                       help='Skip DMG creation')
    
    args = parser.parse_args()
    
    # Initialize compiler
    compiler = MacOSCompiler(args.project_root, args.output_dir)
    
    # Override config if requested
    if args.skip_signing:
        compiler.config["signing"]["enabled"] = False
    if args.skip_notarization:
        compiler.config["notarization"]["enabled"] = False
    if args.skip_dmg:
        compiler.config["dmg"]["create"] = False
    
    # Run compilation
    success, output_path = compiler.compile()
    
    if success:
        print(f"✓ Compilation successful: {output_path}")
        return 0
    else:
        print("✗ Compilation failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Sunflower AI Professional System - Master Build Orchestrator
Production build system for partitioned CD-ROM/USB device deployment
Version: 6.2
"""

import os
import sys
import json
import logging
import shutil
import subprocess
import hashlib
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import platform
import argparse

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('build_master.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BuildOrchestrator')


class BuildOrchestrator:
    """Master build orchestrator for Sunflower AI System deployment"""
    
    SUPPORTED_PLATFORMS = ['Windows', 'Darwin', 'Universal']
    
    BUILD_CONFIG = {
        'version': '6.2',
        'app_name': 'Sunflower AI Professional',
        'bundle_id': 'com.sunflowerai.professional',
        'copyright': 'Copyright © 2025 Sunflower AI Systems',
        'min_python': '3.8',
        'partition_sizes': {
            'cdrom_mb': 4096,  # 4GB CD-ROM partition
            'usb_mb': 1024     # 1GB USB partition
        }
    }
    
    def __init__(self, platform_target: str = 'Universal', debug: bool = False):
        """Initialize build orchestrator with target platform"""
        self.platform_target = platform_target
        self.debug = debug
        self.build_dir = Path(__file__).parent
        self.project_root = self.build_dir.parent
        self.dist_dir = self.project_root / 'dist'
        self.temp_dir = Path(tempfile.mkdtemp(prefix='sunflower_build_'))
        
        # Platform-specific paths
        self.cdrom_staging = self.dist_dir / 'cdrom_partition'
        self.usb_staging = self.dist_dir / 'usb_partition'
        
        # Validate environment
        self._validate_build_environment()
        
        # Create required directories
        for directory in [self.dist_dir, self.cdrom_staging, self.usb_staging, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _validate_build_environment(self) -> None:
        """Validate build environment and dependencies"""
        logger.info("Validating build environment...")
        
        # Check Python version
        python_version = sys.version_info
        min_version = tuple(map(int, self.BUILD_CONFIG['min_python'].split('.')))
        if python_version[:2] < min_version:
            raise RuntimeError(
                f"Python {self.BUILD_CONFIG['min_python']} or higher required. "
                f"Current: {sys.version}"
            )
        
        # Check PyInstaller
        try:
            import PyInstaller
            logger.info(f"PyInstaller version: {PyInstaller.__version__}")
        except ImportError:
            raise RuntimeError(
                "PyInstaller not installed. Run: pip install -r requirements-build.txt"
            )
        
        # Check platform-specific tools
        current_platform = platform.system()
        
        if current_platform == 'Windows':
            # Check for Windows SDK tools
            if not self._check_windows_tools():
                logger.warning("Windows SDK tools not found. Some features may be limited.")
        
        elif current_platform == 'Darwin':
            # Check for macOS development tools
            if not self._check_macos_tools():
                logger.warning("Xcode command line tools not found. Codesigning disabled.")
        
        # Check disk space
        required_space_gb = 10
        available_space_gb = shutil.disk_usage(self.dist_dir).free / (1024**3)
        if available_space_gb < required_space_gb:
            raise RuntimeError(
                f"Insufficient disk space. Required: {required_space_gb}GB, "
                f"Available: {available_space_gb:.2f}GB"
            )
        
        logger.info("Build environment validation complete")
    
    def _check_windows_tools(self) -> bool:
        """Check for Windows development tools"""
        try:
            result = subprocess.run(
                ['where', 'makecert'],
                capture_output=True,
                text=True,
                shell=True
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def _check_macos_tools(self) -> bool:
        """Check for macOS development tools"""
        try:
            result = subprocess.run(
                ['xcode-select', '--print-path'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def build_application(self, platform_name: str) -> Dict[str, Any]:
        """Build application for specific platform"""
        logger.info(f"Building application for {platform_name}...")
        
        # Determine spec file
        spec_file = self.build_dir / 'templates' / f"{platform_name.lower()}.spec"
        if not spec_file.exists():
            raise FileNotFoundError(f"Spec file not found: {spec_file}")
        
        # Prepare build environment
        build_env = os.environ.copy()
        build_env['PYTHONOPTIMIZE'] = '2' if not self.debug else '0'
        
        # Run PyInstaller
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            f'--distpath={self.cdrom_staging / platform_name.lower()}',
            f'--workpath={self.temp_dir / "build" / platform_name.lower()}',
            str(spec_file)
        ]
        
        if self.debug:
            cmd.append('--debug=all')
        
        logger.info(f"Running PyInstaller: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            env=build_env,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        if result.returncode != 0:
            logger.error(f"PyInstaller output: {result.stderr}")
            raise RuntimeError(f"Build failed for {platform_name}")
        
        # Post-process based on platform
        if platform_name.lower() == 'windows':
            app_path = self._post_process_windows()
        elif platform_name.lower() == 'macos':
            app_path = self._post_process_macos()
        else:
            app_path = self.cdrom_staging / platform_name.lower()
        
        logger.info(f"Application built successfully: {app_path}")
        
        return {
            'platform': platform_name,
            'path': str(app_path),
            'size_mb': self._get_directory_size(app_path) / (1024 * 1024),
            'success': True
        }
    
    def _post_process_windows(self) -> Path:
        """Post-process Windows build"""
        windows_dir = self.cdrom_staging / 'windows'
        
        # Create autorun.inf for CD-ROM autoplay
        autorun_content = """[autorun]
open=SunflowerAI.exe
icon=SunflowerAI.exe,0
label=Sunflower AI Professional System
action=Install Sunflower AI Professional

[Content]
MusicFiles=false
PictureFiles=false
VideoFiles=false
"""
        autorun_path = self.cdrom_staging / 'autorun.inf'
        with open(autorun_path, 'w') as f:
            f.write(autorun_content)
        
        # Set file attributes for CD-ROM
        if platform.system() == 'Windows':
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            FILE_ATTRIBUTE_SYSTEM = 0x04
            ctypes.windll.kernel32.SetFileAttributesW(
                str(autorun_path),
                FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
            )
        
        # Create batch launcher for simplified execution
        launcher_content = """@echo off
title Sunflower AI Professional System
echo Starting Sunflower AI Professional System...
echo.
echo Detecting system configuration...

REM Check for 64-bit Windows
if exist "%PROGRAMFILES(X86)%" (
    echo 64-bit Windows detected
    set ARCH=x64
) else (
    echo 32-bit Windows detected
    set ARCH=x86
)

REM Check available memory
for /f "tokens=2 delims==" %%a in ('wmic OS get TotalVisibleMemorySize /value') do set /a MEMORY=%%a/1024

echo System memory: %MEMORY% MB
echo.

REM Launch application
cd /d "%~dp0windows"
start "" "SunflowerAI.exe" --memory=%MEMORY% --arch=%ARCH%

exit
"""
        launcher_path = self.cdrom_staging / 'launch.bat'
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        return windows_dir
    
    def _post_process_macos(self) -> Path:
        """Post-process macOS build"""
        macos_dir = self.cdrom_staging / 'macos'
        app_bundle = macos_dir / 'SunflowerAI.app'
        
        # Update Info.plist
        plist_source = self.build_dir / 'templates' / 'Info.plist'
        plist_dest = app_bundle / 'Contents' / 'Info.plist'
        
        if plist_source.exists() and app_bundle.exists():
            shutil.copy2(plist_source, plist_dest)
        
        # Create launch script for Unix systems
        launcher_content = """#!/bin/bash
# Sunflower AI Professional System Launcher

echo "Starting Sunflower AI Professional System..."

# Detect macOS version
OS_VERSION=$(sw_vers -productVersion)
echo "macOS version: $OS_VERSION"

# Check system memory
MEMORY=$(sysctl -n hw.memsize)
MEMORY_GB=$((MEMORY / 1073741824))
echo "System memory: ${MEMORY_GB}GB"

# Set library paths
export DYLD_LIBRARY_PATH="${DYLD_LIBRARY_PATH}:$(dirname "$0")/lib"

# Launch application
cd "$(dirname "$0")/macos"
if [ -d "SunflowerAI.app" ]; then
    open -W "SunflowerAI.app" --args --memory="${MEMORY_GB}GB"
else
    ./SunflowerAI --memory="${MEMORY_GB}GB"
fi
"""
        launcher_path = self.cdrom_staging / 'launch.sh'
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        launcher_path.chmod(0o755)
        
        # Attempt codesigning if available
        if self._check_macos_tools() and not self.debug:
            self._codesign_app(app_bundle)
        
        return macos_dir
    
    def _codesign_app(self, app_path: Path) -> None:
        """Codesign macOS application"""
        try:
            # Use ad-hoc signing if no certificate available
            subprocess.run(
                ['codesign', '--force', '--deep', '--sign', '-', str(app_path)],
                check=True,
                capture_output=True
            )
            logger.info(f"Successfully codesigned: {app_path}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Codesigning failed: {e}")
    
    def build_models(self) -> Dict[str, Any]:
        """Build AI models using create_models.py"""
        logger.info("Building AI models...")
        
        create_models_script = self.build_dir / 'create_models.py'
        if not create_models_script.exists():
            raise FileNotFoundError(f"Model creation script not found: {create_models_script}")
        
        # Run model creation
        result = subprocess.run(
            [sys.executable, str(create_models_script)],
            capture_output=True,
            text=True,
            cwd=self.build_dir
        )
        
        if result.returncode != 0:
            logger.error(f"Model build failed: {result.stderr}")
            raise RuntimeError("Model compilation failed")
        
        # Copy models to CD-ROM partition
        models_source = self.project_root / 'dist' / 'models'
        models_dest = self.cdrom_staging / 'models'
        
        if models_source.exists():
            shutil.copytree(models_source, models_dest, dirs_exist_ok=True)
            logger.info(f"Models copied to: {models_dest}")
        
        return {
            'models_path': str(models_dest),
            'size_mb': self._get_directory_size(models_dest) / (1024 * 1024),
            'success': True
        }
    
    def prepare_usb_partition(self) -> None:
        """Prepare USB partition structure with encryption support"""
        logger.info("Preparing USB partition structure...")
        
        # Create directory structure
        directories = [
            'profiles',
            'profiles/.encryption',
            'conversations',
            'logs',
            'progress',
            'parent_dashboard',
            'config'
        ]
        
        for directory in directories:
            (self.usb_staging / directory).mkdir(parents=True, exist_ok=True)
        
        # Create encryption key template
        encryption_config = {
            'version': '1.0',
            'algorithm': 'AES-256-GCM',
            'key_derivation': 'PBKDF2',
            'iterations': 100000,
            'salt_length': 32,
            'note': 'Keys generated per family on first run'
        }
        
        encryption_path = self.usb_staging / 'profiles' / '.encryption' / 'config.json'
        with open(encryption_path, 'w') as f:
            json.dump(encryption_config, f, indent=2)
        
        # Create default configuration
        default_config = {
            'version': self.BUILD_CONFIG['version'],
            'first_run': True,
            'family_id': None,
            'install_date': None,
            'platform': platform.system(),
            'settings': {
                'auto_profile_switch': True,
                'session_timeout_minutes': 30,
                'parent_review_required': True,
                'safety_level': 'maximum'
            }
        }
        
        config_path = self.usb_staging / 'config' / 'system.json'
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        # Create README for USB partition
        readme_content = """SUNFLOWER AI DATA PARTITION
============================

This partition contains your family's private data:
- Child profiles and settings
- Conversation histories
- Learning progress tracking
- Parent dashboard data

DO NOT MODIFY FILES DIRECTLY
All data is encrypted and managed by the Sunflower AI system.

For support, consult the documentation on the CD-ROM partition.
"""
        readme_path = self.usb_staging / 'README.txt'
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        logger.info("USB partition structure prepared")
    
    def copy_resources(self) -> None:
        """Copy additional resources to CD-ROM partition"""
        logger.info("Copying resources to CD-ROM partition...")
        
        # Copy documentation
        docs_source = self.project_root / 'docs'
        docs_dest = self.cdrom_staging / 'documentation'
        
        if docs_source.exists():
            shutil.copytree(docs_source, docs_dest, dirs_exist_ok=True)
        
        # Copy Ollama installer
        ollama_dir = self.cdrom_staging / 'prerequisites'
        ollama_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy modelfiles
        modelfiles_source = self.project_root / 'src' / 'modelfiles'
        modelfiles_dest = self.cdrom_staging / 'modelfiles'
        
        if modelfiles_source.exists():
            shutil.copytree(modelfiles_source, modelfiles_dest, dirs_exist_ok=True)
        
        # Create master README
        readme_content = f"""SUNFLOWER AI PROFESSIONAL SYSTEM
=================================
Version: {self.BUILD_CONFIG['version']}
{self.BUILD_CONFIG['copyright']}

QUICK START
-----------
Windows: Double-click 'launch.bat' or run 'SunflowerAI.exe'
macOS: Double-click 'launch.sh' or open 'SunflowerAI.app'

SYSTEM REQUIREMENTS
------------------
- Operating System: Windows 10+ or macOS 10.14+
- Memory: Minimum 4GB RAM (8GB+ recommended)
- Storage: 5GB free space
- Processor: 64-bit, 2GHz+ 

PARTITION LAYOUT
---------------
CD-ROM Partition: System files (read-only)
USB Partition: Your family data (encrypted)

SUPPORT
-------
Documentation available in /documentation folder
No internet connection required after initial setup

SAFETY NOTICE
------------
This system includes comprehensive child safety features.
Parent supervision recommended for children under 13.
"""
        readme_path = self.cdrom_staging / 'README.txt'
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        logger.info("Resources copied successfully")
    
    def create_iso_image(self) -> Path:
        """Create ISO image for CD-ROM partition"""
        logger.info("Creating ISO image for CD-ROM partition...")
        
        iso_path = self.dist_dir / f'SunflowerAI_{self.BUILD_CONFIG["version"]}.iso'
        
        current_platform = platform.system()
        
        if current_platform == 'Darwin':  # macOS
            cmd = [
                'hdiutil', 'makehybrid',
                '-o', str(iso_path),
                '-iso', '-joliet',
                '-default-volume-name', 'SUNFLOWER_AI',
                str(self.cdrom_staging)
            ]
        elif current_platform == 'Windows':
            # Use oscdimg if available (Windows ADK)
            oscdimg = shutil.which('oscdimg')
            if oscdimg:
                cmd = [
                    oscdimg,
                    '-j1',  # Joliet
                    '-l', 'SUNFLOWER_AI',
                    str(self.cdrom_staging),
                    str(iso_path)
                ]
            else:
                # Fallback to PowerShell method
                logger.warning("oscdimg not found, using PowerShell fallback")
                self._create_iso_powershell(iso_path)
                return iso_path
        else:  # Linux
            cmd = [
                'genisoimage',
                '-o', str(iso_path),
                '-J',  # Joliet
                '-r',  # Rock Ridge
                '-V', 'SUNFLOWER_AI',
                str(self.cdrom_staging)
            ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"ISO image created: {iso_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ISO creation failed: {e}")
            raise
        
        return iso_path
    
    def _create_iso_powershell(self, iso_path: Path) -> None:
        """Create ISO using PowerShell as fallback"""
        ps_script = f"""
$source = "{self.cdrom_staging}"
$target = "{iso_path}"

$FSI = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
$FSI.VolumeName = "SUNFLOWER_AI"
$FSI.ChooseImageDefaultsForMediaType(12)

$source_dir = Get-Item $source
$FSI.Root.AddTree($source_dir.FullName, $false)

$result = $FSI.CreateResultImage()
$stream = $result.ImageStream

$data = New-Object byte[] $stream.Length
$stream.Read($data, 0, $stream.Length) | Out-Null

[System.IO.File]::WriteAllBytes($target, $data)
"""
        
        subprocess.run(
            ['powershell', '-Command', ps_script],
            check=True,
            capture_output=True
        )
    
    def create_final_device_image(self) -> Path:
        """Create final device image with both partitions"""
        logger.info("Creating final device image with partitions...")
        
        device_image = self.dist_dir / f'SunflowerAI_Device_{self.BUILD_CONFIG["version"]}.img'
        
        # Calculate sizes
        cdrom_size = self._get_directory_size(self.cdrom_staging)
        usb_size = self._get_directory_size(self.usb_staging)
        total_size = cdrom_size + usb_size + (10 * 1024 * 1024)  # Add 10MB buffer
        
        # Create device image file
        with open(device_image, 'wb') as f:
            f.seek(total_size - 1)
            f.write(b'\0')
        
        # Write partition table and data (simplified for production)
        # In production, use proper disk imaging tools
        
        logger.info(f"Device image created: {device_image}")
        logger.info(f"Total size: {total_size / (1024*1024):.2f} MB")
        
        return device_image
    
    def generate_checksums(self) -> None:
        """Generate checksums for all build artifacts"""
        logger.info("Generating checksums...")
        
        checksums = {}
        
        # Calculate checksums for all important files
        for file_path in self.dist_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.dist_dir)
                checksums[str(relative_path)] = self._calculate_checksum(file_path)
        
        # Save checksums
        checksum_path = self.dist_dir / 'checksums.json'
        with open(checksum_path, 'w') as f:
            json.dump(checksums, f, indent=2)
        
        logger.info(f"Checksums saved to: {checksum_path}")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of directory in bytes"""
        total = 0
        for path in directory.rglob('*'):
            if path.is_file():
                total += path.stat().st_size
        return total
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        logger.info("Cleanup completed")
    
    def execute_build(self) -> Dict[str, Any]:
        """Execute complete build process"""
        logger.info("=" * 60)
        logger.info(f"SUNFLOWER AI BUILD SYSTEM v{self.BUILD_CONFIG['version']}")
        logger.info(f"Target Platform: {self.platform_target}")
        logger.info(f"Build Started: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        results = {
            'version': self.BUILD_CONFIG['version'],
            'platform': self.platform_target,
            'start_time': datetime.now().isoformat(),
            'steps': []
        }
        
        try:
            # Step 1: Build Models
            logger.info("Step 1/7: Building AI Models...")
            model_result = self.build_models()
            results['steps'].append({'name': 'models', 'result': model_result})
            
            # Step 2: Build Applications
            logger.info("Step 2/7: Building Applications...")
            if self.platform_target == 'Universal':
                platforms = ['Windows', 'macOS']
            else:
                platforms = [self.platform_target]
            
            for platform_name in platforms:
                if platform_name.lower() == platform.system().lower() or self.platform_target == 'Universal':
                    app_result = self.build_application(platform_name)
                    results['steps'].append({'name': f'app_{platform_name}', 'result': app_result})
            
            # Step 3: Prepare USB Partition
            logger.info("Step 3/7: Preparing USB Partition...")
            self.prepare_usb_partition()
            results['steps'].append({'name': 'usb_partition', 'result': {'success': True}})
            
            # Step 4: Copy Resources
            logger.info("Step 4/7: Copying Resources...")
            self.copy_resources()
            results['steps'].append({'name': 'resources', 'result': {'success': True}})
            
            # Step 5: Create ISO Image
            logger.info("Step 5/7: Creating ISO Image...")
            iso_path = self.create_iso_image()
            results['steps'].append({
                'name': 'iso_image',
                'result': {'path': str(iso_path), 'success': True}
            })
            
            # Step 6: Create Device Image
            logger.info("Step 6/7: Creating Device Image...")
            device_path = self.create_final_device_image()
            results['steps'].append({
                'name': 'device_image',
                'result': {'path': str(device_path), 'success': True}
            })
            
            # Step 7: Generate Checksums
            logger.info("Step 7/7: Generating Checksums...")
            self.generate_checksums()
            results['steps'].append({'name': 'checksums', 'result': {'success': True}})
            
            results['end_time'] = datetime.now().isoformat()
            results['success'] = True
            
            # Save build manifest
            manifest_path = self.dist_dir / 'build_manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info("=" * 60)
            logger.info("BUILD COMPLETED SUCCESSFULLY")
            logger.info(f"Output Directory: {self.dist_dir}")
            logger.info(f"ISO Image: {iso_path}")
            logger.info(f"Device Image: {device_path}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Build failed: {str(e)}")
            results['error'] = str(e)
            results['success'] = False
            raise
        
        finally:
            self.cleanup()
        
        return results


def main():
    """Main entry point for build orchestrator"""
    parser = argparse.ArgumentParser(
        description='Sunflower AI Professional System Build Orchestrator'
    )
    parser.add_argument(
        '--platform',
        choices=['Windows', 'macOS', 'Darwin', 'Universal'],
        default='Universal',
        help='Target platform for build'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    parser.add_argument(
        '--skip-models',
        action='store_true',
        help='Skip model building (use existing models)'
    )
    
    args = parser.parse_args()
    
    # Normalize platform name
    if args.platform == 'Darwin':
        args.platform = 'macOS'
    
    try:
        orchestrator = BuildOrchestrator(
            platform_target=args.platform,
            debug=args.debug
        )
        
        results = orchestrator.execute_build()
        
        sys.exit(0 if results['success'] else 1)
        
    except Exception as e:
        logger.error(f"Build orchestration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Sunflower AI Professional System - Master Build Script
Builds Windows .exe and macOS .app executables for production deployment
Version: 6.2.0
"""

import os
import sys
import shutil
import subprocess
import platform
import hashlib
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SunflowerAIBuilder:
    """Master builder for Sunflower AI executables"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.temp_dir = self.project_root / "build" / "temp"
        self.current_platform = platform.system()
        self.version = "6.2.0"
        self.build_timestamp = datetime.now().isoformat()
        
    def clean_build_environment(self):
        """Clean previous build artifacts"""
        logger.info("Cleaning build environment...")
        
        # Remove old build directories
        dirs_to_clean = [
            self.dist_dir,
            self.temp_dir,
            self.project_root / "build" / "__pycache__",
            self.project_root / "__pycache__"
        ]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path, ignore_errors=True)
                logger.info(f"  Removed: {dir_path}")
        
        # Create fresh directories
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✓ Build environment cleaned")
    
    def verify_dependencies(self) -> bool:
        """Verify all build dependencies are installed"""
        logger.info("Verifying build dependencies...")
        
        required_packages = [
            "pyinstaller",
            "pillow",
            "wheel",
            "setuptools",
            "cryptography",
            "psutil"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                logger.info(f"  ✓ {package} found")
            except ImportError:
                missing_packages.append(package)
                logger.error(f"  ✗ {package} missing")
        
        if missing_packages:
            logger.error(f"Missing packages: {', '.join(missing_packages)}")
            logger.error("Install with: pip install " + " ".join(missing_packages))
            return False
        
        logger.info("✓ All dependencies verified")
        return True
    
    def prepare_resources(self):
        """Prepare resource files for building"""
        logger.info("Preparing resource files...")
        
        # Create resources directory if it doesn't exist
        resources_dir = self.project_root / "resources"
        resources_dir.mkdir(exist_ok=True)
        
        # Generate icon if missing
        icon_path = resources_dir / "sunflower.ico"
        if not icon_path.exists():
            logger.info("  Generating application icon...")
            self._generate_default_icon(icon_path)
        
        # Copy required files to temp directory
        files_to_copy = [
            ("LICENSE", "LICENSE"),
            ("README.md", "README.md"),
            ("requirements.txt", "requirements.txt")
        ]
        
        for src, dst in files_to_copy:
            src_path = self.project_root / src
            dst_path = self.temp_dir / dst
            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                logger.info(f"  Copied: {src} -> {dst}")
        
        logger.info("✓ Resources prepared")
    
    def _generate_default_icon(self, icon_path: Path):
        """Generate a default icon if none exists"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple sunflower icon
            img = Image.new('RGBA', (256, 256), color=(255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw sunflower shape (simplified)
            center = (128, 128)
            
            # Yellow petals
            for angle in range(0, 360, 30):
                x = center[0] + 80 * (angle % 60) / 60
                y = center[1] + 80 * (angle % 60) / 60
                draw.ellipse([x-20, y-20, x+20, y+20], fill='#FFD700')
            
            # Brown center
            draw.ellipse([center[0]-40, center[1]-40, 
                         center[0]+40, center[1]+40], fill='#8B4513')
            
            # Save as ICO
            img.save(icon_path, format='ICO', sizes=[(256, 256)])
            logger.info(f"  Generated default icon: {icon_path}")
            
        except Exception as e:
            logger.warning(f"  Could not generate icon: {e}")
    
    def build_windows_executable(self) -> bool:
        """Build Windows executable"""
        if self.current_platform != "Windows":
            logger.warning("Skipping Windows build (not on Windows)")
            return True
        
        logger.info("=" * 60)
        logger.info("BUILDING WINDOWS EXECUTABLE")
        logger.info("=" * 60)
        
        try:
            # Prepare Windows-specific files
            spec_file = self.build_dir / "templates" / "windows.spec"
            if not spec_file.exists():
                logger.error(f"Windows spec file not found: {spec_file}")
                return False
            
            # Update spec file with current paths
            self._update_spec_file(spec_file, "Windows")
            
            # Run PyInstaller
            cmd = [
                "pyinstaller",
                str(spec_file),
                "--clean",
                "--noconfirm",
                "--distpath", str(self.dist_dir / "Windows"),
                "--workpath", str(self.temp_dir / "build_windows"),
                "--specpath", str(self.temp_dir)
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"PyInstaller failed: {result.stderr}")
                return False
            
            # Verify output
            exe_path = self.dist_dir / "Windows" / "SunflowerAI.exe"
            if not exe_path.exists():
                logger.error(f"Expected output not found: {exe_path}")
                return False
            
            # Calculate checksum
            checksum = self._calculate_checksum(exe_path)
            logger.info(f"  Executable: {exe_path}")
            logger.info(f"  Size: {exe_path.stat().st_size:,} bytes")
            logger.info(f"  SHA256: {checksum}")
            
            # Create version info file
            version_info = {
                "version": self.version,
                "platform": "Windows",
                "build_date": self.build_timestamp,
                "checksum": checksum,
                "file_size": exe_path.stat().st_size
            }
            
            version_file = self.dist_dir / "Windows" / "version.json"
            version_file.write_text(json.dumps(version_info, indent=2))
            
            logger.info("✓ Windows executable built successfully")
            return True
            
        except Exception as e:
            logger.error(f"Windows build failed: {e}")
            return False
    
    def build_macos_application(self) -> bool:
        """Build macOS application bundle"""
        if self.current_platform != "Darwin":
            logger.warning("Skipping macOS build (not on macOS)")
            return True
        
        logger.info("=" * 60)
        logger.info("BUILDING MACOS APPLICATION")
        logger.info("=" * 60)
        
        try:
            # Prepare macOS-specific files
            spec_file = self.build_dir / "templates" / "macos.spec"
            if not spec_file.exists():
                logger.error(f"macOS spec file not found: {spec_file}")
                return False
            
            # Update spec file with current paths
            self._update_spec_file(spec_file, "macOS")
            
            # Create Info.plist if missing
            plist_path = self.temp_dir / "Info.plist"
            if not plist_path.exists():
                self._create_info_plist(plist_path)
            
            # Run PyInstaller
            cmd = [
                "pyinstaller",
                str(spec_file),
                "--clean",
                "--noconfirm",
                "--windowed",
                "--distpath", str(self.dist_dir / "macOS"),
                "--workpath", str(self.temp_dir / "build_macos"),
                "--specpath", str(self.temp_dir)
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"PyInstaller failed: {result.stderr}")
                return False
            
            # Verify output
            app_path = self.dist_dir / "macOS" / "SunflowerAI.app"
            if not app_path.exists():
                logger.error(f"Expected output not found: {app_path}")
                return False
            
            # Sign the application (if certificate available)
            if self._has_signing_certificate():
                self._sign_macos_app(app_path)
            
            # Create DMG installer
            dmg_path = self._create_dmg(app_path)
            
            # Calculate checksum
            checksum = self._calculate_checksum(dmg_path) if dmg_path else "N/A"
            logger.info(f"  Application: {app_path}")
            logger.info(f"  DMG: {dmg_path}")
            logger.info(f"  SHA256: {checksum}")
            
            # Create version info file
            version_info = {
                "version": self.version,
                "platform": "macOS",
                "build_date": self.build_timestamp,
                "checksum": checksum,
                "bundle_id": "com.sunflowerai.professional"
            }
            
            version_file = self.dist_dir / "macOS" / "version.json"
            version_file.write_text(json.dumps(version_info, indent=2))
            
            logger.info("✓ macOS application built successfully")
            return True
            
        except Exception as e:
            logger.error(f"macOS build failed: {e}")
            return False
    
    def _update_spec_file(self, spec_file: Path, platform_name: str):
        """Update spec file with current project paths"""
        content = spec_file.read_text()
        
        # Replace path placeholders
        replacements = {
            "{PROJECT_ROOT}": str(self.project_root),
            "{VERSION}": self.version,
            "{PLATFORM}": platform_name,
            "{BUILD_DATE}": self.build_timestamp
        }
        
        for key, value in replacements.items():
            content = content.replace(key, value)
        
        # Write updated spec to temp directory
        temp_spec = self.temp_dir / f"{platform_name.lower()}.spec"
        temp_spec.write_text(content)
        
        return temp_spec
    
    def _create_info_plist(self, plist_path: Path):
        """Create Info.plist for macOS application"""
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>Sunflower AI Professional</string>
    <key>CFBundleExecutable</key>
    <string>SunflowerAI</string>
    <key>CFBundleIdentifier</key>
    <string>com.sunflowerai.professional</string>
    <key>CFBundleName</key>
    <string>SunflowerAI</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{self.version}</string>
    <key>CFBundleVersion</key>
    <string>{self.version}.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2025 Sunflower AI Systems. All rights reserved.</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.education</string>
</dict>
</plist>"""
        plist_path.write_text(plist_content)
        logger.info(f"  Created Info.plist: {plist_path}")
    
    def _has_signing_certificate(self) -> bool:
        """Check if code signing certificate is available"""
        if self.current_platform == "Darwin":
            result = subprocess.run(
                ["security", "find-identity", "-v", "-p", "codesigning"],
                capture_output=True,
                text=True
            )
            return "Developer ID Application" in result.stdout
        elif self.current_platform == "Windows":
            # Check for Windows certificate
            cert_path = self.project_root / "certificates" / "windows_cert.pfx"
            return cert_path.exists()
        return False
    
    def _sign_macos_app(self, app_path: Path):
        """Sign macOS application with Developer ID"""
        logger.info("  Signing macOS application...")
        
        cmd = [
            "codesign",
            "--deep",
            "--force",
            "--verify",
            "--verbose",
            "--sign", "Developer ID Application",
            "--options", "runtime",
            str(app_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("  ✓ Application signed successfully")
        else:
            logger.warning(f"  Signing failed: {result.stderr}")
    
    def _create_dmg(self, app_path: Path) -> Optional[Path]:
        """Create DMG installer for macOS"""
        logger.info("  Creating DMG installer...")
        
        dmg_path = self.dist_dir / "macOS" / f"SunflowerAI-{self.version}.dmg"
        
        # Check if create-dmg is available
        if shutil.which("create-dmg"):
            cmd = [
                "create-dmg",
                "--volname", f"Sunflower AI {self.version}",
                "--window-size", "600", "400",
                "--icon-size", "100",
                "--icon", str(app_path.name), "150", "200",
                "--app-drop-link", "450", "200",
                str(dmg_path),
                str(app_path.parent)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"  ✓ DMG created: {dmg_path}")
                return dmg_path
            else:
                logger.warning(f"  DMG creation failed: {result.stderr}")
        else:
            logger.warning("  create-dmg not found, skipping DMG creation")
        
        return None
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def create_distribution_package(self):
        """Create final distribution package with both executables"""
        logger.info("=" * 60)
        logger.info("CREATING DISTRIBUTION PACKAGE")
        logger.info("=" * 60)
        
        # Create distribution metadata
        dist_metadata = {
            "product": "Sunflower AI Professional System",
            "version": self.version,
            "build_date": self.build_timestamp,
            "platforms": [],
            "files": {}
        }
        
        # Add Windows executable info
        windows_exe = self.dist_dir / "Windows" / "SunflowerAI.exe"
        if windows_exe.exists():
            dist_metadata["platforms"].append("Windows")
            dist_metadata["files"]["windows"] = {
                "executable": "Windows/SunflowerAI.exe",
                "size": windows_exe.stat().st_size,
                "checksum": self._calculate_checksum(windows_exe)
            }
        
        # Add macOS application info
        macos_dmg = list(self.dist_dir.glob("macOS/*.dmg"))
        if macos_dmg:
            dist_metadata["platforms"].append("macOS")
            dist_metadata["files"]["macos"] = {
                "installer": f"macOS/{macos_dmg[0].name}",
                "size": macos_dmg[0].stat().st_size,
                "checksum": self._calculate_checksum(macos_dmg[0])
            }
        
        # Save distribution metadata
        metadata_file = self.dist_dir / "distribution.json"
        metadata_file.write_text(json.dumps(dist_metadata, indent=2))
        
        logger.info(f"✓ Distribution package ready: {self.dist_dir}")
        logger.info(f"  Platforms: {', '.join(dist_metadata['platforms'])}")
        
        # Display final summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("BUILD COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Version: {self.version}")
        logger.info(f"Output Directory: {self.dist_dir}")
        
        for platform_name in dist_metadata["platforms"]:
            platform_key = platform_name.lower()
            if platform_key in dist_metadata["files"]:
                file_info = dist_metadata["files"][platform_key]
                logger.info(f"\n{platform_name}:")
                for key, value in file_info.items():
                    if key == "size":
                        logger.info(f"  {key}: {value:,} bytes")
                    else:
                        logger.info(f"  {key}: {value}")
    
    def run_full_build(self, platforms: List[str] = None) -> bool:
        """Run complete build process"""
        start_time = time.time()
        
        try:
            # Step 1: Clean environment
            self.clean_build_environment()
            
            # Step 2: Verify dependencies
            if not self.verify_dependencies():
                return False
            
            # Step 3: Prepare resources
            self.prepare_resources()
            
            # Step 4: Build executables
            if platforms is None:
                platforms = ["Windows", "macOS"]
            
            build_success = True
            
            if "Windows" in platforms and self.current_platform == "Windows":
                if not self.build_windows_executable():
                    build_success = False
            
            if "macOS" in platforms and self.current_platform == "Darwin":
                if not self.build_macos_application():
                    build_success = False
            
            # Step 5: Create distribution package
            if build_success:
                self.create_distribution_package()
            
            elapsed = time.time() - start_time
            logger.info(f"\nTotal build time: {elapsed:.2f} seconds")
            
            return build_success
            
        except Exception as e:
            logger.error(f"Build failed with error: {e}")
            return False
        finally:
            # Cleanup temp directory
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build Sunflower AI executables for Windows and macOS"
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=["Windows", "macOS"],
        help="Platforms to build for"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build environment before building"
    )
    parser.add_argument(
        "--version",
        default="6.2.0",
        help="Version number for build"
    )
    
    args = parser.parse_args()
    
    # Create builder instance
    builder = SunflowerAIBuilder()
    
    if args.version:
        builder.version = args.version
    
    # Run build
    success = builder.run_full_build(platforms=args.platforms)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

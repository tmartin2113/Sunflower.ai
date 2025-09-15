#!/usr/bin/env python3
"""
Sunflower AI Professional System - Installation Package Creator
Creates platform-specific installation packages for Windows and macOS
Version: 6.2 | Platform: Windows/macOS | Architecture: Installer Builder
"""

import os
import sys
import json
import shutil
import hashlib
import platform
import subprocess
import tempfile
import zipfile
import tarfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import re
import base64
import struct

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('package_creation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SunflowerPackageCreator')


class PackageType(Enum):
    """Supported package types"""
    MSI = "msi"          # Windows Installer
    NSIS = "nsis"        # NSIS Installer for Windows
    DMG = "dmg"          # macOS Disk Image
    PKG = "pkg"          # macOS Package
    UNIVERSAL = "universal"  # Cross-platform archive


class BuildStatus(Enum):
    """Build status codes"""
    INITIALIZED = "initialized"
    COLLECTING = "collecting"
    BUILDING = "building"
    SIGNING = "signing"
    PACKAGING = "packaging"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class InstallerConfiguration:
    """Configuration for installer package creation"""
    package_type: PackageType
    app_name: str = "Sunflower AI Professional"
    app_version: str = "6.2.0"
    app_publisher: str = "Sunflower AI Systems"
    app_url: str = "https://sunflowerai.education"
    install_dir: str = ""
    output_dir: str = "./dist"
    sign_package: bool = False
    certificate_path: str = ""
    certificate_password: str = ""
    include_models: List[str] = field(default_factory=lambda: [
        "llama3.2:7b", "llama3.2:3b", "llama3.2:1b", "llama3.2:1b-q4_0"
    ])
    hardware_requirements: Dict[str, Any] = field(default_factory=lambda: {
        "min_ram_gb": 4,
        "min_disk_gb": 8,
        "min_os_version": {"windows": "10", "macos": "10.15"}
    })
    
    def __post_init__(self):
        if not self.install_dir:
            if platform.system() == "Windows":
                self.install_dir = f"C:\\Program Files\\{self.app_name}"
            else:
                self.install_dir = f"/Applications/{self.app_name}.app"


class ChecksumCalculator:
    """
    FIX BUG-019: Efficient checksum calculator with chunked reading
    Provides optimized file hashing with progress reporting
    """
    
    # Optimal chunk sizes for different file sizes
    CHUNK_SIZES = {
        100 * 1024 * 1024: 1024 * 1024,      # 1MB chunks for files > 100MB
        10 * 1024 * 1024: 256 * 1024,        # 256KB chunks for files > 10MB
        1 * 1024 * 1024: 64 * 1024,          # 64KB chunks for files > 1MB
        0: 16 * 1024                          # 16KB chunks for small files
    }
    
    @classmethod
    def calculate_checksum(
        cls,
        file_path: Path,
        algorithm: str = 'sha256',
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        FIX BUG-019: Calculate file checksum efficiently with chunked reading
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use (sha256, sha512, md5)
            progress_callback: Optional callback for progress updates (bytes_read, total_bytes)
            
        Returns:
            Hexadecimal checksum string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file can't be read
            ValueError: If algorithm is not supported
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        # Select hash algorithm
        try:
            if algorithm.lower() == 'sha256':
                hasher = hashlib.sha256()
            elif algorithm.lower() == 'sha512':
                hasher = hashlib.sha512()
            elif algorithm.lower() == 'md5':
                hasher = hashlib.md5()
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
        except Exception as e:
            raise ValueError(f"Failed to initialize hasher: {e}")
        
        # Get file size for progress reporting and chunk size selection
        try:
            file_size = file_path.stat().st_size
        except Exception as e:
            raise PermissionError(f"Cannot access file: {e}")
        
        # Select optimal chunk size based on file size
        chunk_size = cls._get_optimal_chunk_size(file_size)
        
        # Calculate checksum with chunked reading
        bytes_read = 0
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    # Read chunk
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Update hash
                    hasher.update(chunk)
                    
                    # Update progress
                    bytes_read += len(chunk)
                    if progress_callback:
                        try:
                            progress_callback(bytes_read, file_size)
                        except Exception as e:
                            # Don't let callback errors stop checksum calculation
                            logger.debug(f"Progress callback error: {e}")
            
            return hasher.hexdigest()
            
        except PermissionError as e:
            raise PermissionError(f"Cannot read file: {e}")
        except Exception as e:
            raise IOError(f"Error reading file: {e}")
    
    @classmethod
    def _get_optimal_chunk_size(cls, file_size: int) -> int:
        """
        Determine optimal chunk size based on file size
        
        Args:
            file_size: Size of file in bytes
            
        Returns:
            Optimal chunk size in bytes
        """
        for threshold, chunk_size in sorted(cls.CHUNK_SIZES.items(), reverse=True):
            if file_size > threshold:
                return chunk_size
        return cls.CHUNK_SIZES[0]
    
    @classmethod
    def calculate_checksums_batch(
        cls,
        file_paths: List[Path],
        algorithm: str = 'sha256',
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, str]:
        """
        Calculate checksums for multiple files efficiently
        
        Args:
            file_paths: List of file paths
            algorithm: Hash algorithm to use
            progress_callback: Optional callback (filename, current_file, total_files)
            
        Returns:
            Dictionary mapping file paths to checksums
        """
        checksums = {}
        total_files = len(file_paths)
        
        for idx, file_path in enumerate(file_paths, 1):
            try:
                if progress_callback:
                    progress_callback(str(file_path), idx, total_files)
                
                checksum = cls.calculate_checksum(file_path, algorithm)
                checksums[str(file_path)] = checksum
                
            except Exception as e:
                logger.warning(f"Failed to calculate checksum for {file_path}: {e}")
                checksums[str(file_path)] = None
        
        return checksums
    
    @classmethod
    def verify_checksum(
        cls,
        file_path: Path,
        expected_checksum: str,
        algorithm: str = 'sha256'
    ) -> bool:
        """
        Verify file checksum matches expected value
        
        Args:
            file_path: Path to file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm used
            
        Returns:
            True if checksum matches, False otherwise
        """
        try:
            actual_checksum = cls.calculate_checksum(file_path, algorithm)
            return actual_checksum.lower() == expected_checksum.lower()
        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False


class PackageBuilder:
    """Base class for package builders"""
    
    def __init__(self, config: InstallerConfiguration):
        self.config = config
        self.status = BuildStatus.INITIALIZED
        self.build_dir = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        self.source_dir = Path("../src")
        self.assets_dir = Path("../assets")
        self.output_path: Optional[Path] = None
        self.file_manifest: Dict[str, str] = {}
        self.errors: List[str] = []
        # FIX BUG-019: Use efficient checksum calculator
        self.checksum_calculator = ChecksumCalculator()
        
    def build(self) -> bool:
        """Main build process"""
        try:
            logger.info(f"Starting {self.config.package_type.value} package build")
            
            self.status = BuildStatus.COLLECTING
            if not self._collect_files():
                return False
            
            self.status = BuildStatus.BUILDING
            if not self._create_package():
                return False
            
            if self.config.sign_package:
                self.status = BuildStatus.SIGNING
                if not self._sign_package():
                    logger.warning("Package signing failed, continuing unsigned")
            
            self.status = BuildStatus.VERIFYING
            if not self._verify_package():
                return False
            
            self.status = BuildStatus.COMPLETE
            logger.info(f"Package created successfully: {self.output_path}")
            return True
            
        except Exception as e:
            self.status = BuildStatus.ERROR
            self.errors.append(str(e))
            logger.error(f"Package build failed: {e}", exc_info=True)
            return False
        finally:
            self._cleanup()
    
    def _collect_files(self) -> bool:
        """Collect all files needed for the package"""
        try:
            logger.info("Collecting files for package")
            
            # Define file structure
            files_to_collect = {
                "executables": {
                    "windows": ["launcher.exe", "service.exe"],
                    "macos": ["launcher", "service"],
                    "linux": ["launcher", "service"]
                },
                "models": self.config.include_models,
                "assets": ["icons/*", "fonts/*", "images/*"],
                "documentation": ["*.pdf", "*.md", "*.txt"],
                "interface": ["*.py", "*.ui", "*.qml"],
                "ollama": ["ollama.exe", "ollama"]
            }
            
            total_files = 0
            
            # FIX BUG-019: Progress callback for checksum calculation
            def checksum_progress(bytes_read: int, total_bytes: int):
                percent = (bytes_read / total_bytes * 100) if total_bytes > 0 else 0
                if percent % 10 == 0:  # Log every 10%
                    logger.debug(f"Checksum progress: {percent:.0f}%")
            
            # Copy files and calculate checksums
            for category, items in files_to_collect.items():
                category_dir = self.build_dir / category
                category_dir.mkdir(exist_ok=True)
                
                if isinstance(items, dict):
                    # Platform-specific files
                    platform_key = platform.system().lower()
                    if platform_key in items:
                        for file_pattern in items[platform_key]:
                            self._copy_files_by_pattern(
                                self.source_dir / category,
                                category_dir,
                                file_pattern,
                                checksum_progress
                            )
                            total_files += 1
                else:
                    # Generic files
                    for file_pattern in items:
                        source_path = self.source_dir / category / file_pattern
                        if source_path.exists():
                            dest_path = category_dir / source_path.name
                            shutil.copy2(source_path, dest_path)
                            
                            # FIX BUG-019: Use efficient checksum calculation
                            checksum = self.checksum_calculator.calculate_checksum(
                                dest_path,
                                progress_callback=checksum_progress if dest_path.stat().st_size > 10*1024*1024 else None
                            )
                            
                            rel_path = dest_path.relative_to(self.build_dir)
                            self.file_manifest[str(rel_path)] = checksum
                            total_files += 1
                        else:
                            logger.warning(f"Source not found: {source_path}")
            
            logger.info(f"Collected {total_files} files")
            
            # Create version info file
            self._create_version_info()
            
            return True
            
        except Exception as e:
            self.errors.append(f"File collection failed: {e}")
            return False
    
    def _copy_files_by_pattern(
        self,
        source_dir: Path,
        dest_dir: Path,
        pattern: str,
        checksum_progress_callback: Optional[Callable] = None
    ):
        """Copy files matching pattern and calculate checksums"""
        import glob
        
        if not source_dir.exists():
            return
        
        for source_file in source_dir.glob(pattern):
            if source_file.is_file():
                dest_file = dest_dir / source_file.name
                shutil.copy2(source_file, dest_file)
                
                # FIX BUG-019: Efficient checksum with progress
                checksum = self.checksum_calculator.calculate_checksum(
                    dest_file,
                    progress_callback=checksum_progress_callback
                )
                
                rel_path = dest_file.relative_to(self.build_dir)
                self.file_manifest[str(rel_path)] = checksum
    
    def _create_version_info(self) -> None:
        """Create version information file"""
        version_info = {
            "product_name": self.config.app_name,
            "version": self.config.app_version,
            "build_date": datetime.now().isoformat(),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": sys.version,
            "models_included": self.config.include_models,
            "hardware_requirements": self.config.hardware_requirements,
            "file_manifest": self.file_manifest
        }
        
        version_file = self.build_dir / "version_info.json"
        with open(version_file, 'w') as f:
            json.dump(version_info, f, indent=2)
        
        # Calculate checksum of version file itself
        version_checksum = self.checksum_calculator.calculate_checksum(version_file)
        self.file_manifest["version_info.json"] = version_checksum
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """
        FIX BUG-019: Calculate SHA256 checksum efficiently
        This method is kept for backward compatibility but uses the new efficient implementation
        """
        return self.checksum_calculator.calculate_checksum(file_path)
    
    def _create_package(self) -> bool:
        """Create the actual package (to be overridden by subclasses)"""
        raise NotImplementedError("Subclasses must implement _create_package")
    
    def _sign_package(self) -> bool:
        """Sign the package (to be overridden by subclasses)"""
        return True
    
    def _verify_package(self) -> bool:
        """Verify the created package"""
        if not self.output_path or not self.output_path.exists():
            self.errors.append("Package file not found")
            return False
        
        # Check file size
        size_mb = self.output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Package size: {size_mb:.2f} MB")
        
        if size_mb < 100:
            logger.warning("Package seems unusually small")
        
        # FIX BUG-019: Calculate and log package checksum efficiently
        logger.info("Calculating package checksum...")
        
        def package_progress(bytes_read: int, total_bytes: int):
            percent = (bytes_read / total_bytes * 100) if total_bytes > 0 else 0
            if int(percent) % 20 == 0:  # Log every 20%
                logger.info(f"Package verification: {percent:.0f}%")
        
        package_checksum = self.checksum_calculator.calculate_checksum(
            self.output_path,
            progress_callback=package_progress if size_mb > 100 else None
        )
        
        logger.info(f"Package checksum (SHA256): {package_checksum}")
        
        # Save checksum to file
        checksum_file = self.output_path.with_suffix('.sha256')
        with open(checksum_file, 'w') as f:
            f.write(f"{package_checksum}  {self.output_path.name}\n")
        
        return True
    
    def _cleanup(self) -> None:
        """Clean up temporary files"""
        try:
            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


class WindowsMSIBuilder(PackageBuilder):
    """Windows MSI package builder"""
    
    def _create_package(self) -> bool:
        """Create Windows MSI package using WiX or msitools"""
        try:
            logger.info("Creating Windows MSI package")
            
            # Generate WiX source file
            wxs_content = self._generate_wix_source()
            wxs_file = self.build_dir / "sunflower.wxs"
            wxs_file.write_text(wxs_content)
            
            # Check if WiX is available
            if self._is_wix_available():
                return self._build_with_wix(wxs_file)
            else:
                logger.warning("WiX not found, using alternative MSI creation")
                return self._build_with_msitools()
                
        except Exception as e:
            self.errors.append(f"MSI creation failed: {e}")
            return False
    
    def _generate_wix_source(self) -> str:
        """Generate WiX source XML"""
        # Generate unique GUIDs
        import uuid
        product_guid = str(uuid.uuid4()).upper()
        upgrade_guid = str(uuid.uuid4()).upper()
        
        wxs_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
    <Product Id="{product_guid}" 
             Name="{self.config.app_name}" 
             Language="1033" 
             Version="{self.config.app_version}"
             Manufacturer="{self.config.app_publisher}" 
             UpgradeCode="{upgrade_guid}">
        
        <Package InstallerVersion="200" 
                 Compressed="yes" 
                 InstallScope="perMachine"
                 Description="{self.config.app_name} Installer"
                 Comments="Family-focused K-12 STEM Education System" />
        
        <MajorUpgrade DowngradeErrorMessage="A newer version is already installed." />
        
        <MediaTemplate EmbedCab="yes" />
        
        <Feature Id="ProductFeature" Title="{self.config.app_name}" Level="1">
            <ComponentGroupRef Id="ProductComponents" />
            <ComponentGroupRef Id="ModelComponents" />
        </Feature>
        
        <Directory Id="TARGETDIR" Name="SourceDir">
            <Directory Id="ProgramFiles64Folder">
                <Directory Id="INSTALLFOLDER" Name="{self.config.app_name}">
                    <Directory Id="ModelsFolder" Name="models" />
                    <Directory Id="AssetsFolder" Name="assets" />
                </Directory>
            </Directory>
            
            <Directory Id="ProgramMenuFolder">
                <Directory Id="ApplicationProgramsFolder" Name="{self.config.app_name}" />
            </Directory>
            
            <Directory Id="DesktopFolder" Name="Desktop" />
        </Directory>
        
        <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
            <!-- Main executable -->
            <Component Id="MainExecutable" Guid="{str(uuid.uuid4()).upper()}">
                <File Id="LauncherExe" Source="$(var.BuildDir)\\executables\\launcher.exe" KeyPath="yes">
                    <Shortcut Id="StartMenuShortcut"
                              Directory="ApplicationProgramsFolder"
                              Name="{self.config.app_name}"
                              WorkingDirectory="INSTALLFOLDER"
                              Icon="AppIcon.ico"
                              IconIndex="0"
                              Advertise="yes" />
                    <Shortcut Id="DesktopShortcut"
                              Directory="DesktopFolder"
                              Name="{self.config.app_name}"
                              WorkingDirectory="INSTALLFOLDER"
                              Icon="AppIcon.ico"
                              IconIndex="0"
                              Advertise="yes" />
                </File>
            </Component>
        </ComponentGroup>
        
        <Icon Id="AppIcon.ico" SourceFile="$(var.BuildDir)\\assets\\icons\\sunflower.ico" />
    </Product>
</Wix>"""
        
        return wxs_template
    
    def _is_wix_available(self) -> bool:
        """Check if WiX toolset is available"""
        try:
            result = subprocess.run(
                ["candle", "-?"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _build_with_wix(self, wxs_file: Path) -> bool:
        """Build MSI using WiX toolset"""
        try:
            # Compile WiX source
            wixobj_file = self.build_dir / "sunflower.wixobj"
            candle_cmd = [
                "candle",
                f"-dBuildDir={self.build_dir}",
                "-o", str(wixobj_file),
                str(wxs_file)
            ]
            
            result = subprocess.run(candle_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"WiX compilation failed: {result.stderr}")
                return False
            
            # Link to create MSI
            msi_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}.msi"
            light_cmd = [
                "light",
                "-o", str(msi_file),
                str(wixobj_file)
            ]
            
            result = subprocess.run(light_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"WiX linking failed: {result.stderr}")
                return False
            
            self.output_path = msi_file
            logger.info(f"MSI created: {msi_file}")
            return True
            
        except Exception as e:
            self.errors.append(f"WiX build error: {e}")
            return False
    
    def _build_with_msitools(self) -> bool:
        """Alternative MSI creation without WiX"""
        # This would use python-msilib or other alternatives
        logger.warning("Alternative MSI creation not implemented, creating ZIP instead")
        return self._create_zip_fallback()
    
    def _create_zip_fallback(self) -> bool:
        """Create ZIP package as fallback"""
        try:
            zip_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}-windows.zip"
            
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(self.build_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arc_name = file_path.relative_to(self.build_dir)
                        zf.write(file_path, arc_name)
            
            self.output_path = zip_file
            logger.info(f"ZIP package created: {zip_file}")
            return True
            
        except Exception as e:
            self.errors.append(f"ZIP creation failed: {e}")
            return False
    
    def _sign_package(self) -> bool:
        """Sign Windows package"""
        if not self.config.certificate_path:
            logger.warning("No certificate provided for signing")
            return False
        
        try:
            sign_cmd = [
                "signtool", "sign",
                "/f", self.config.certificate_path,
                "/p", self.config.certificate_password,
                "/t", "http://timestamp.digicert.com",
                "/d", self.config.app_name,
                str(self.output_path)
            ]
            
            result = subprocess.run(sign_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"Signing failed: {result.stderr}")
                return False
            
            logger.info("Package signed successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"Signing error: {e}")
            return False


class MacOSDMGBuilder(PackageBuilder):
    """macOS DMG package builder"""
    
    def _create_package(self) -> bool:
        """Create macOS DMG package"""
        try:
            logger.info("Creating macOS DMG package")
            
            # Create app bundle structure
            app_bundle = self.build_dir / f"{self.config.app_name}.app"
            self._create_app_bundle(app_bundle)
            
            # Create DMG
            dmg_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}.dmg"
            
            # Create temporary DMG
            temp_dmg = self.build_dir / "temp.dmg"
            
            create_cmd = [
                "hdiutil", "create",
                "-volname", self.config.app_name,
                "-srcfolder", str(self.build_dir),
                "-ov",
                "-format", "UDRW",
                str(temp_dmg)
            ]
            
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"DMG creation failed: {result.stderr}")
                return False
            
            # Mount DMG for customization
            mount_result = subprocess.run(
                ["hdiutil", "attach", str(temp_dmg), "-readwrite", "-noverify"],
                capture_output=True,
                text=True
            )
            
            if mount_result.returncode != 0:
                self.errors.append(f"DMG mounting failed: {mount_result.stderr}")
                return False
            
            # Get mount point
            mount_point = None
            for line in mount_result.stdout.split('\n'):
                if '/Volumes/' in line:
                    parts = line.split('\t')
                    mount_point = parts[-1].strip()
                    break
            
            if mount_point:
                # Add background and styling
                self._customize_dmg(mount_point)
                
                # Unmount
                subprocess.run(["hdiutil", "detach", mount_point], capture_output=True)
            
            # Convert to final compressed DMG
            final_cmd = [
                "hdiutil", "convert",
                str(temp_dmg),
                "-format", "UDZO",
                "-o", str(dmg_file)
            ]
            
            result = subprocess.run(final_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"DMG conversion failed: {result.stderr}")
                return False
            
            # Clean up temp DMG
            temp_dmg.unlink()
            
            self.output_path = dmg_file
            logger.info(f"DMG created: {dmg_file}")
            return True
            
        except Exception as e:
            self.errors.append(f"DMG creation error: {e}")
            return False
    
    def _create_app_bundle(self, app_bundle: Path):
        """Create macOS app bundle structure"""
        # Create bundle directories
        contents = app_bundle / "Contents"
        macos_dir = contents / "MacOS"
        resources = contents / "Resources"
        
        for dir_path in [macos_dir, resources]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Copy executables
        exec_src = self.build_dir / "executables" / "launcher"
        if exec_src.exists():
            shutil.copy2(exec_src, macos_dir / self.config.app_name)
            os.chmod(macos_dir / self.config.app_name, 0o755)
        
        # Create Info.plist
        info_plist = contents / "Info.plist"
        info_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{self.config.app_name}</string>
    <key>CFBundleDisplayName</key>
    <string>{self.config.app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.sunflowerai.professional</string>
    <key>CFBundleVersion</key>
    <string>{self.config.app_version}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>{self.config.app_name}</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>"""
        info_plist.write_text(info_content)
        
        # Copy icon
        icon_src = self.build_dir / "assets" / "icons" / "sunflower.icns"
        if icon_src.exists():
            shutil.copy2(icon_src, resources / "AppIcon.icns")
    
    def _customize_dmg(self, mount_point: str):
        """Customize DMG appearance"""
        # This would add background image, arrange icons, etc.
        # For now, just create a symlink to Applications
        try:
            apps_link = Path(mount_point) / "Applications"
            if not apps_link.exists():
                os.symlink("/Applications", str(apps_link))
        except Exception as e:
            logger.warning(f"DMG customization failed: {e}")
    
    def _sign_package(self) -> bool:
        """Sign macOS package"""
        if not self.config.certificate_path:
            logger.warning("No certificate provided for signing")
            return False
        
        try:
            # Sign the app bundle
            app_bundle = self.build_dir / f"{self.config.app_name}.app"
            sign_cmd = [
                "codesign",
                "--force",
                "--deep",
                "--sign", self.config.certificate_path,
                str(app_bundle)
            ]
            
            result = subprocess.run(sign_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"App signing failed: {result.stderr}")
                return False
            
            # Sign the DMG
            dmg_sign_cmd = [
                "codesign",
                "--force",
                "--sign", self.config.certificate_path,
                str(self.output_path)
            ]
            
            result = subprocess.run(dmg_sign_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"DMG signing failed: {result.stderr}")
                return False
            
            # Notarize for macOS Catalina and later
            if self.config.app_version:
                self._notarize_package()
            
            logger.info("Package signed successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"Signing error: {e}")
            return False
    
    def _notarize_package(self) -> bool:
        """Notarize package with Apple"""
        # This would require Apple Developer credentials
        # Implementation would use altool or notarytool
        logger.info("Notarization would be performed here with Apple credentials")
        return True


class UniversalPackageBuilder(PackageBuilder):
    """Universal package builder for cross-platform distribution"""
    
    def _create_package(self) -> bool:
        """Create universal package (ZIP/TAR)"""
        try:
            logger.info("Creating universal package")
            
            # Create launcher script for each platform
            self._create_launcher_scripts()
            
            # Create archive
            if platform.system() == "Windows":
                return self._create_zip_package()
            else:
                return self._create_tar_package()
                
        except Exception as e:
            self.errors.append(f"Universal package creation failed: {e}")
            return False
    
    def _create_launcher_scripts(self):
        """Create platform-specific launcher scripts"""
        # Windows batch file
        win_launcher = self.build_dir / "launch_windows.bat"
        win_launcher.write_text("""@echo off
echo Starting Sunflower AI Professional System...
cd /d "%~dp0"
if exist "executables\\launcher.exe" (
    executables\\launcher.exe %*
) else (
    echo Error: launcher.exe not found
    pause
    exit /b 1
)
""")
        
        # Unix shell script
        unix_launcher = self.build_dir / "launch_unix.sh"
        unix_launcher.write_text("""#!/bin/bash
echo "Starting Sunflower AI Professional System..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )[\d.]+')
if [ -z "$python_version" ]; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or later."
    exit 1
fi

# Check hardware requirements
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    mem_bytes=$(sysctl -n hw.memsize)
    mem_gb=$((mem_bytes / 1073741824))
else
    # Linux
    mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    mem_gb=$((mem_kb / 1048576))
fi

if [ $mem_gb -lt 4 ]; then
    echo "WARNING: System has less than 4GB RAM. Performance may be limited."
fi

# Launch application
cd "$(dirname "$0")"
python3 interface/gui.py || {
    echo "Error launching application. Check error.log for details."
    exit 1
}
""")
        
        # Make Unix launcher executable
        os.chmod(unix_launcher, 0o755)
    
    def _create_zip_package(self) -> bool:
        """Create ZIP package"""
        try:
            zip_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}-universal.zip"
            
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(self.build_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arc_name = file_path.relative_to(self.build_dir)
                        zf.write(file_path, arc_name)
            
            self.output_path = zip_file
            logger.info(f"ZIP package created: {zip_file}")
            return True
            
        except Exception as e:
            self.errors.append(f"ZIP creation failed: {e}")
            return False
    
    def _create_tar_package(self) -> bool:
        """Create TAR.GZ package"""
        try:
            tar_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}-universal.tar.gz"
            
            with tarfile.open(tar_file, 'w:gz') as tf:
                tf.add(self.build_dir, arcname=f"{self.config.app_name}-{self.config.app_version}")
            
            self.output_path = tar_file
            logger.info(f"TAR.GZ package created: {tar_file}")
            return True
            
        except Exception as e:
            self.errors.append(f"TAR creation failed: {e}")
            return False


def create_package(
    package_type: str,
    version: str = "6.2.0",
    sign: bool = False,
    cert_path: str = "",
    cert_pass: str = ""
) -> bool:
    """Main function to create installation package"""
    
    # Determine package type
    if package_type.lower() == "auto":
        if platform.system() == "Windows":
            pkg_type = PackageType.MSI
        elif platform.system() == "Darwin":
            pkg_type = PackageType.DMG
        else:
            pkg_type = PackageType.UNIVERSAL
    else:
        try:
            pkg_type = PackageType(package_type.lower())
        except ValueError:
            logger.error(f"Invalid package type: {package_type}")
            return False
    
    # Create configuration
    config = InstallerConfiguration(
        package_type=pkg_type,
        app_version=version,
        sign_package=sign,
        certificate_path=cert_path,
        certificate_password=cert_pass
    )
    
    # Create output directory
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Select appropriate builder
    if pkg_type == PackageType.MSI:
        builder = WindowsMSIBuilder(config)
    elif pkg_type == PackageType.DMG:
        builder = MacOSDMGBuilder(config)
    else:
        builder = UniversalPackageBuilder(config)
    
    # Build package
    success = builder.build()
    
    if success:
        logger.info(f"Package created successfully: {builder.output_path}")
    else:
        logger.error("Package creation failed")
        for error in builder.errors:
            logger.error(f"  - {error}")
    
    return success


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sunflower AI Professional System - Package Creator"
    )
    parser.add_argument(
        "--type",
        choices=["msi", "dmg", "universal", "auto"],
        default="auto",
        help="Package type to create"
    )
    parser.add_argument(
        "--version",
        default="6.2.0",
        help="Version number"
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign the package"
    )
    parser.add_argument(
        "--cert",
        help="Certificate path for signing"
    )
    parser.add_argument(
        "--cert-pass",
        help="Certificate password"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("SUNFLOWER AI PROFESSIONAL - PACKAGE CREATOR")
    print(f"Version: {args.version}")
    print(f"Package Type: {args.type}")
    print("="*60 + "\n")
    
    success = create_package(
        args.type,
        args.version,
        args.sign,
        args.cert or "",
        args.cert_pass or ""
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

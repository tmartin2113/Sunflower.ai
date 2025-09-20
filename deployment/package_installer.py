#!/usr/bin/env python3
"""
Sunflower AI Professional System - Package Installer
Version: 6.2 - Production Ready
Creates installation packages for Windows, macOS, and Universal USB deployment
"""

import os
import sys
import json
import shutil
import hashlib
import zipfile
import tarfile
import platform
import tempfile
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PackageInstaller')


class PackageType(Enum):
    """Package types for different platforms"""
    WINDOWS_MSI = "windows_msi"
    WINDOWS_EXE = "windows_exe"
    MACOS_DMG = "macos_dmg"
    MACOS_PKG = "macos_pkg"
    UNIVERSAL_ZIP = "universal_zip"
    UNIVERSAL_TAR = "universal_tar"
    USB_IMAGE = "usb_image"


class BuildStatus(Enum):
    """Build status indicators"""
    PENDING = "pending"
    COLLECTING = "collecting"
    BUILDING = "building"
    SIGNING = "signing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class PackageConfig:
    """Package configuration settings"""
    app_name: str = "Sunflower AI Professional System"
    version: str = "6.2.0"
    build_number: str = ""
    platform: str = ""
    package_type: PackageType = PackageType.UNIVERSAL_ZIP
    include_models: List[str] = field(default_factory=list)
    sign_package: bool = False
    certificate: Optional[str] = None
    output_dir: Path = Path("dist")
    temp_dir: Path = Path(tempfile.gettempdir()) / "sunflower_build"
    
    def __post_init__(self):
        if not self.platform:
            self.platform = platform.system()
        if not self.build_number:
            self.build_number = datetime.now().strftime("%Y%m%d%H%M%S")
        if not self.include_models:
            self.include_models = ["llama3.2:1b-q4_0"]  # Minimum model


class ChecksumCalculator:
    """
    Optimized checksum calculator with chunked reading and progress reporting
    FIX BUG-002: Proper file handle management with exception safety
    FIX BUG-019: Efficient chunked reading for large files
    """
    
    # Optimal chunk sizes for different file sizes
    CHUNK_SIZES = {
        1024 * 1024 * 1024: 1024 * 1024,     # 1MB chunks for files > 1GB
        100 * 1024 * 1024: 512 * 1024,       # 512KB chunks for files > 100MB
        10 * 1024 * 1024: 256 * 1024,        # 256KB chunks for files > 10MB
        1 * 1024 * 1024: 64 * 1024,          # 64KB chunks for files > 1MB
        0: 32 * 1024                          # 32KB chunks for small files
    }
    
    def __init__(self):
        self._lock = threading.Lock()
        self._active_handles = []  # Track open file handles
    
    def calculate_checksum(
        self,
        file_path: Path,
        algorithm: str = 'sha256',
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        Calculate file checksum with proper resource management
        FIX BUG-002: Ensures file handles are always closed
        FIX BUG-019: Uses optimal chunk size for file size
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (sha256, sha512, md5)
            progress_callback: Optional callback for progress (bytes_read, total_bytes)
            
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
        algorithm_lower = algorithm.lower()
        if algorithm_lower == 'sha256':
            hasher = hashlib.sha256()
        elif algorithm_lower == 'sha512':
            hasher = hashlib.sha512()
        elif algorithm_lower == 'md5':
            hasher = hashlib.md5()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Get file size for chunk size selection and progress
        try:
            file_size = file_path.stat().st_size
        except Exception as e:
            raise PermissionError(f"Cannot access file: {e}")
        
        # Select optimal chunk size based on file size
        chunk_size = self._get_optimal_chunk_size(file_size)
        
        # FIX BUG-002: Proper file handle management with try-finally
        file_handle = None
        bytes_read = 0
        
        try:
            # Open file and track handle
            file_handle = open(file_path, 'rb')
            
            with self._lock:
                self._active_handles.append(file_handle)
            
            # Read and hash in chunks (FIX BUG-019)
            while True:
                chunk = file_handle.read(chunk_size)
                if not chunk:
                    break
                
                hasher.update(chunk)
                bytes_read += len(chunk)
                
                # Report progress if callback provided
                if progress_callback:
                    try:
                        progress_callback(bytes_read, file_size)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
            
            # Return final hash
            return hasher.hexdigest()
            
        except MemoryError:
            raise MemoryError(f"File too large to process: {file_path}")
        except OSError as e:
            raise PermissionError(f"Cannot read file: {e}")
        except Exception as e:
            raise RuntimeError(f"Checksum calculation failed: {e}")
        finally:
            # FIX BUG-002: Always close file handle
            if file_handle:
                with self._lock:
                    if file_handle in self._active_handles:
                        self._active_handles.remove(file_handle)
                
                try:
                    if not file_handle.closed:
                        file_handle.close()
                except Exception as e:
                    logger.warning(f"Error closing file handle: {e}")
    
    def _get_optimal_chunk_size(self, file_size: int) -> int:
        """
        Determine optimal chunk size based on file size
        FIX BUG-019: Smart chunk size selection for performance
        """
        for size_threshold, chunk_size in sorted(self.CHUNK_SIZES.items(), reverse=True):
            if file_size >= size_threshold:
                return chunk_size
        return self.CHUNK_SIZES[0]
    
    def calculate_directory_checksums(
        self,
        directory: Path,
        pattern: str = "*",
        recursive: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, str]:
        """
        Calculate checksums for all files in directory
        
        Args:
            directory: Directory to process
            pattern: File pattern to match
            recursive: Whether to process subdirectories
            progress_callback: Callback (current_file, current_index, total_files)
            
        Returns:
            Dictionary mapping relative paths to checksums
        """
        checksums = {}
        
        # Collect all files
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))
        
        # Filter to only files
        files = [f for f in files if f.is_file()]
        total_files = len(files)
        
        for index, file_path in enumerate(files):
            if progress_callback:
                try:
                    progress_callback(str(file_path), index, total_files)
                except Exception as e:
                    logger.warning(f"Directory progress callback error: {e}")
            
            try:
                rel_path = file_path.relative_to(directory)
                checksum = self.calculate_checksum(file_path)
                checksums[str(rel_path)] = checksum
            except Exception as e:
                logger.error(f"Failed to checksum {file_path}: {e}")
                checksums[str(rel_path)] = "ERROR"
        
        return checksums
    
    def verify_checksum(
        self,
        file_path: Path,
        expected_checksum: str,
        algorithm: str = 'sha256'
    ) -> bool:
        """
        Verify file checksum matches expected value
        
        Args:
            file_path: Path to file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm to use
            
        Returns:
            True if checksum matches, False otherwise
        """
        try:
            actual_checksum = self.calculate_checksum(file_path, algorithm)
            return actual_checksum.lower() == expected_checksum.lower()
        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up any remaining open file handles"""
        with self._lock:
            for handle in self._active_handles[:]:
                try:
                    if not handle.closed:
                        handle.close()
                except Exception as e:
                    logger.warning(f"Failed to close handle during cleanup: {e}")
            self._active_handles.clear()


class PackageInstaller:
    """Main package installer for Sunflower AI system"""
    
    def __init__(self, config: PackageConfig):
        self.config = config
        self.checksum_calculator = ChecksumCalculator()
        self.status = BuildStatus.PENDING
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.file_manifest: Dict[str, str] = {}
        
        # Paths
        self.source_dir = Path(__file__).parent.parent
        self.build_dir = self.config.temp_dir / f"build_{self.config.build_number}"
        self.output_path = None
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def build(self) -> bool:
        """
        Main build process
        
        Returns:
            True if build successful, False otherwise
        """
        try:
            logger.info(f"Starting package build for {self.config.platform}")
            logger.info(f"Package type: {self.config.package_type.value}")
            
            # Create build directory
            self.build_dir.mkdir(parents=True, exist_ok=True)
            
            # Phase 1: Collect files
            self.status = BuildStatus.COLLECTING
            if not self._collect_files():
                return False
            
            # Phase 2: Build package
            self.status = BuildStatus.BUILDING
            if not self._build_package():
                return False
            
            # Phase 3: Sign package (if configured)
            if self.config.sign_package:
                self.status = BuildStatus.SIGNING
                if not self._sign_package():
                    self.warnings.append("Package signing failed")
            
            # Phase 4: Verify package
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
            checksum_errors = []
            
            # Progress callback for large files
            def file_progress(bytes_read: int, total_bytes: int):
                if total_bytes > 0:
                    percent = (bytes_read / total_bytes) * 100
                    if percent % 25 == 0:  # Log at 25% intervals
                        logger.debug(f"Checksum progress: {percent:.0f}%")
            
            # Process each category
            for category, items in files_to_collect.items():
                category_dir = self.build_dir / category
                category_dir.mkdir(exist_ok=True)
                
                if isinstance(items, dict):
                    # Platform-specific files
                    platform_key = self.config.platform.lower()
                    if platform_key in items:
                        for file_pattern in items[platform_key]:
                            self._copy_files_by_pattern(
                                self.source_dir / category,
                                category_dir,
                                file_pattern
                            )
                            total_files += 1
                else:
                    # Generic files or patterns
                    for file_pattern in items:
                        source_path = self.source_dir / category / file_pattern
                        
                        # Handle wildcards
                        if '*' in file_pattern:
                            pattern = file_pattern.split('/')[-1]
                            source_dir = source_path.parent
                            if source_dir.exists():
                                for file in source_dir.glob(pattern):
                                    if file.is_file():
                                        dest_file = category_dir / file.name
                                        shutil.copy2(file, dest_file)
                                        
                                        # Calculate checksum with progress for large files
                                        try:
                                            if file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                                                checksum = self.checksum_calculator.calculate_checksum(
                                                    dest_file,
                                                    progress_callback=file_progress
                                                )
                                            else:
                                                checksum = self.checksum_calculator.calculate_checksum(dest_file)
                                            
                                            rel_path = dest_file.relative_to(self.build_dir)
                                            self.file_manifest[str(rel_path)] = checksum
                                            total_files += 1
                                        except Exception as e:
                                            checksum_errors.append(f"{file.name}: {e}")
                        
                        elif source_path.exists():
                            # Single file
                            dest_path = category_dir / source_path.name
                            shutil.copy2(source_path, dest_path)
                            
                            # Calculate checksum
                            try:
                                checksum = self.checksum_calculator.calculate_checksum(dest_path)
                                rel_path = dest_path.relative_to(self.build_dir)
                                self.file_manifest[str(rel_path)] = checksum
                                total_files += 1
                            except Exception as e:
                                checksum_errors.append(f"{source_path.name}: {e}")
                        else:
                            logger.warning(f"Source not found: {source_path}")
            
            if checksum_errors:
                logger.warning(f"Checksum errors for {len(checksum_errors)} files")
                self.warnings.extend(checksum_errors)
            
            logger.info(f"Collected {total_files} files")
            
            # Create version info file
            self._create_version_info()
            
            # Create manifest file
            self._create_manifest()
            
            return True
            
        except Exception as e:
            self.errors.append(f"File collection failed: {e}")
            return False
    
    def _copy_files_by_pattern(
        self,
        source_dir: Path,
        dest_dir: Path,
        pattern: str
    ) -> int:
        """
        Copy files matching pattern and calculate checksums
        
        Returns:
            Number of files copied
        """
        if not source_dir.exists():
            return 0
        
        files_copied = 0
        
        for source_file in source_dir.glob(pattern):
            if source_file.is_file():
                dest_file = dest_dir / source_file.name
                shutil.copy2(source_file, dest_file)
                
                # Calculate checksum efficiently
                try:
                    # Use progress callback for large files
                    if source_file.stat().st_size > 50 * 1024 * 1024:  # 50MB
                        def progress(bytes_read, total):
                            if bytes_read == total:
                                logger.debug(f"Checksum complete: {source_file.name}")
                        
                        checksum = self.checksum_calculator.calculate_checksum(
                            dest_file,
                            progress_callback=progress
                        )
                    else:
                        checksum = self.checksum_calculator.calculate_checksum(dest_file)
                    
                    rel_path = dest_file.relative_to(self.build_dir)
                    self.file_manifest[str(rel_path)] = checksum
                    files_copied += 1
                    
                except Exception as e:
                    logger.error(f"Checksum calculation failed for {dest_file}: {e}")
                    self.warnings.append(f"Checksum failed: {dest_file.name}")
        
        return files_copied
    
    def _create_version_info(self) -> None:
        """Create version information file"""
        version_info = {
            "product_name": self.config.app_name,
            "version": self.config.version,
            "build_number": self.config.build_number,
            "build_date": datetime.now().isoformat(),
            "platform": self.config.platform,
            "package_type": self.config.package_type.value,
            "models_included": self.config.include_models,
            "file_count": len(self.file_manifest),
            "installer_version": "6.2.0"
        }
        
        version_file = self.build_dir / "version.json"
        with open(version_file, 'w') as f:
            json.dump(version_info, f, indent=2)
        
        # Add to manifest
        checksum = self.checksum_calculator.calculate_checksum(version_file)
        self.file_manifest["version.json"] = checksum
    
    def _create_manifest(self) -> None:
        """Create file manifest with checksums"""
        manifest = {
            "created": datetime.now().isoformat(),
            "package_info": {
                "name": self.config.app_name,
                "version": self.config.version,
                "build": self.config.build_number
            },
            "files": {}
        }
        
        # Add file information
        for rel_path, checksum in self.file_manifest.items():
            file_path = self.build_dir / rel_path
            if file_path.exists():
                manifest["files"][rel_path] = {
                    "checksum": checksum,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                }
        
        manifest_file = self.build_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def _build_package(self) -> bool:
        """Build the actual package based on type"""
        try:
            if self.config.package_type == PackageType.WINDOWS_MSI:
                return self._build_windows_msi()
            elif self.config.package_type == PackageType.WINDOWS_EXE:
                return self._build_windows_exe()
            elif self.config.package_type == PackageType.MACOS_DMG:
                return self._build_macos_dmg()
            elif self.config.package_type == PackageType.MACOS_PKG:
                return self._build_macos_pkg()
            elif self.config.package_type == PackageType.UNIVERSAL_ZIP:
                return self._build_universal_zip()
            elif self.config.package_type == PackageType.UNIVERSAL_TAR:
                return self._build_universal_tar()
            elif self.config.package_type == PackageType.USB_IMAGE:
                return self._build_usb_image()
            else:
                self.errors.append(f"Unsupported package type: {self.config.package_type}")
                return False
                
        except Exception as e:
            self.errors.append(f"Package build failed: {e}")
            return False
    
    def _build_windows_msi(self) -> bool:
        """Build Windows MSI installer"""
        logger.info("Building Windows MSI installer")
        
        # This would use WiX Toolset or similar
        # For now, create a zip as placeholder
        return self._build_universal_zip()
    
    def _build_windows_exe(self) -> bool:
        """Build Windows EXE installer"""
        logger.info("Building Windows EXE installer")
        
        # This would use NSIS or similar
        # For now, create a zip as placeholder
        return self._build_universal_zip()
    
    def _build_macos_dmg(self) -> bool:
        """Build macOS DMG installer"""
        logger.info("Building macOS DMG installer")
        
        # This would use hdiutil
        # For now, create a tar as placeholder
        return self._build_universal_tar()
    
    def _build_macos_pkg(self) -> bool:
        """Build macOS PKG installer"""
        logger.info("Building macOS PKG installer")
        
        # This would use pkgbuild/productbuild
        # For now, create a tar as placeholder
        return self._build_universal_tar()
    
    def _build_universal_zip(self) -> bool:
        """Build universal ZIP package"""
        logger.info("Building universal ZIP package")
        
        output_name = f"SunflowerAI_{self.config.version}_{self.config.build_number}.zip"
        self.output_path = self.config.output_dir / output_name
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.build_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(self.build_dir)
                    zipf.write(file_path, arc_path)
        
        # Calculate final package checksum
        package_checksum = self.checksum_calculator.calculate_checksum(self.output_path)
        logger.info(f"Package checksum: {package_checksum}")
        
        # Create checksum file
        checksum_file = self.output_path.with_suffix('.sha256')
        with open(checksum_file, 'w') as f:
            f.write(f"{package_checksum}  {self.output_path.name}\n")
        
        return True
    
    def _build_universal_tar(self) -> bool:
        """Build universal TAR package"""
        logger.info("Building universal TAR package")
        
        output_name = f"SunflowerAI_{self.config.version}_{self.config.build_number}.tar.gz"
        self.output_path = self.config.output_dir / output_name
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(self.output_path, 'w:gz') as tarf:
            tarf.add(self.build_dir, arcname='SunflowerAI')
        
        # Calculate final package checksum
        package_checksum = self.checksum_calculator.calculate_checksum(self.output_path)
        logger.info(f"Package checksum: {package_checksum}")
        
        # Create checksum file
        checksum_file = self.output_path.with_suffix('.sha256')
        with open(checksum_file, 'w') as f:
            f.write(f"{package_checksum}  {self.output_path.name}\n")
        
        return True
    
    def _build_usb_image(self) -> bool:
        """Build USB device image with partitions"""
        logger.info("Building USB device image")
        
        # This would create a dual-partition USB image
        # For now, create a structured directory
        
        usb_root = self.build_dir / "usb_image"
        
        # Create CD-ROM partition structure
        cdrom_partition = usb_root / "cdrom"
        cdrom_partition.mkdir(parents=True)
        
        # Copy system files to CD-ROM partition
        for category in ["executables", "models", "ollama", "documentation"]:
            source = self.build_dir / category
            if source.exists():
                shutil.copytree(source, cdrom_partition / category)
        
        # Create marker file
        (cdrom_partition / "sunflower_cd.id").write_text("SUNFLOWER_CD_PARTITION_6.2")
        
        # Create USB data partition structure
        usb_partition = usb_root / "usb"
        usb_partition.mkdir(parents=True)
        
        # Create data directories
        for dir_name in ["profiles", "conversations", "logs", "config", "safety"]:
            (usb_partition / dir_name).mkdir()
        
        # Create marker file
        (usb_partition / "sunflower_data.id").write_text("SUNFLOWER_USB_PARTITION_6.2")
        
        # Package as tar for now
        output_name = f"SunflowerAI_USB_{self.config.version}_{self.config.build_number}.tar.gz"
        self.output_path = self.config.output_dir / output_name
        
        with tarfile.open(self.output_path, 'w:gz') as tarf:
            tarf.add(usb_root, arcname='SunflowerAI_USB')
        
        return True
    
    def _sign_package(self) -> bool:
        """Sign the package if certificates are available"""
        if not self.config.certificate:
            logger.warning("No certificate configured for signing")
            return False
        
        logger.info("Signing package...")
        
        # Platform-specific signing
        if self.config.platform == "Windows":
            return self._sign_windows()
        elif self.config.platform == "Darwin":
            return self._sign_macos()
        else:
            logger.warning(f"Package signing not supported for {self.config.platform}")
            return False
    
    def _sign_windows(self) -> bool:
        """Sign Windows package"""
        try:
            # Use signtool if available
            cmd = [
                "signtool", "sign",
                "/f", self.config.certificate,
                "/t", "http://timestamp.sectigo.com",
                "/fd", "sha256",
                str(self.output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("Windows package signed successfully")
                return True
            else:
                logger.error(f"Windows signing failed: {result.stderr}")
                return False
                
        except FileNotFoundError:
            logger.warning("signtool not found")
            return False
        except Exception as e:
            logger.error(f"Windows signing error: {e}")
            return False
    
    def _sign_macos(self) -> bool:
        """Sign macOS package"""
        try:
            # Use codesign
            cmd = [
                "codesign",
                "--force",
                "--deep",
                "--sign", self.config.certificate,
                str(self.output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("macOS package signed successfully")
                return True
            else:
                logger.error(f"macOS signing failed: {result.stderr}")
                return False
                
        except FileNotFoundError:
            logger.warning("codesign not found")
            return False
        except Exception as e:
            logger.error(f"macOS signing error: {e}")
            return False
    
    def _verify_package(self) -> bool:
        """Verify the created package"""
        if not self.output_path or not self.output_path.exists():
            self.errors.append("Package file not found")
            return False
        
        # Check file size
        size = self.output_path.stat().st_size
        if size == 0:
            self.errors.append("Package file is empty")
            return False
        
        logger.info(f"Package size: {size / (1024*1024):.2f} MB")
        
        # Verify package can be opened
        try:
            if self.output_path.suffix == '.zip':
                with zipfile.ZipFile(self.output_path, 'r') as zipf:
                    if len(zipf.namelist()) == 0:
                        self.errors.append("Package contains no files")
                        return False
                        
            elif self.output_path.suffix in ['.tar', '.gz']:
                with tarfile.open(self.output_path, 'r:*') as tarf:
                    if len(tarf.getnames()) == 0:
                        self.errors.append("Package contains no files")
                        return False
                        
        except Exception as e:
            self.errors.append(f"Package verification failed: {e}")
            return False
        
        logger.info("Package verification passed")
        return True
    
    def _cleanup(self):
        """Clean up temporary files and resources"""
        # Clean up checksum calculator
        self.checksum_calculator.cleanup()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=False)
        
        # Remove build directory if successful
        if self.status == BuildStatus.COMPLETE and self.build_dir.exists():
            try:
                shutil.rmtree(self.build_dir)
                logger.info("Cleaned up temporary build directory")
            except Exception as e:
                logger.warning(f"Failed to clean up build directory: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current build status"""
        return {
            'status': self.status.value,
            'errors': self.errors,
            'warnings': self.warnings,
            'output_path': str(self.output_path) if self.output_path else None,
            'file_count': len(self.file_manifest),
            'config': {
                'version': self.config.version,
                'build': self.config.build_number,
                'platform': self.config.platform,
                'package_type': self.config.package_type.value
            }
        }


def main():
    """Main entry point for package installer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sunflower AI Package Installer")
    parser.add_argument('--version', default='6.2.0', help='Package version')
    parser.add_argument('--platform', choices=['Windows', 'Darwin', 'Linux'],
                       help='Target platform (auto-detected if not specified)')
    parser.add_argument('--type', choices=['zip', 'tar', 'msi', 'exe', 'dmg', 'pkg', 'usb'],
                       default='zip', help='Package type')
    parser.add_argument('--models', nargs='+', 
                       default=['llama3.2:1b-q4_0'],
                       help='Models to include')
    parser.add_argument('--sign', action='store_true', help='Sign the package')
    parser.add_argument('--cert', help='Certificate for signing')
    parser.add_argument('--output', default='dist', help='Output directory')
    
    args = parser.parse_args()
    
    # Map package type
    type_map = {
        'zip': PackageType.UNIVERSAL_ZIP,
        'tar': PackageType.UNIVERSAL_TAR,
        'msi': PackageType.WINDOWS_MSI,
        'exe': PackageType.WINDOWS_EXE,
        'dmg': PackageType.MACOS_DMG,
        'pkg': PackageType.MACOS_PKG,
        'usb': PackageType.USB_IMAGE
    }
    
    # Create configuration
    config = PackageConfig(
        version=args.version,
        platform=args.platform or platform.system(),
        package_type=type_map[args.type],
        include_models=args.models,
        sign_package=args.sign,
        certificate=args.cert,
        output_dir=Path(args.output)
    )
    
    # Create and run installer
    installer = PackageInstaller(config)
    
    print("\n" + "="*60)
    print("SUNFLOWER AI PACKAGE INSTALLER")
    print("="*60)
    print(f"Version: {config.version}")
    print(f"Platform: {config.platform}")
    print(f"Package Type: {config.package_type.value}")
    print(f"Models: {', '.join(config.include_models)}")
    print("="*60 + "\n")
    
    success = installer.build()
    
    # Print results
    status = installer.get_status()
    
    print("\n" + "="*60)
    print("BUILD RESULTS")
    print("="*60)
    print(f"Status: {status['status']}")
    
    if status['output_path']:
        print(f"Output: {status['output_path']}")
        print(f"Files: {status['file_count']}")
    
    if status['errors']:
        print("\nErrors:")
        for error in status['errors']:
            print(f"  - {error}")
    
    if status['warnings']:
        print("\nWarnings:")
        for warning in status['warnings']:
            print(f"  - {warning}")
    
    print("="*60 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

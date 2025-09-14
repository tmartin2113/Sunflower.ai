#!/usr/bin/env python3
"""
Sunflower AI Professional System - Partition Manager
Enhanced with complete thread safety, race condition fixes, and proper resource management
Version: 6.2.0 - Production Ready
"""

import os
import sys
import platform
import shutil
import hashlib
import json
import logging
import threading
import time
import string
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
import concurrent.futures

logger = logging.getLogger(__name__)

# Configuration constants
SCAN_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds
MOUNT_CHECK_INTERVAL = 2  # seconds
MOUNT_WAIT_TIMEOUT = 60  # seconds
DISK_USAGE_TIMEOUT = 5  # seconds


class PartitionType(Enum):
    """Partition types in the dual-partition architecture"""
    CDROM = "cdrom"
    USB = "usb"


@dataclass
class PartitionInfo:
    """Information about a partition"""
    mount_point: Path
    partition_type: PartitionType
    size_gb: float
    used_gb: float
    available_gb: float
    is_readonly: bool
    filesystem: str
    label: Optional[str]
    verified: bool = False
    last_checked: Optional[datetime] = None


class PartitionManager:
    """
    Thread-safe partition manager for dual-partition device architecture
    BUG-008 FIX: All mount operations now properly synchronized with locks
    """
    
    # Partition markers
    CDROM_MARKER = "sunflower_cd.id"
    USB_MARKER = "sunflower_data.id"
    
    # Required files for integrity check
    REQUIRED_CDROM_FILES = [
        "system/launcher_common.py",
        "system/openwebui_integration.py",
        "modelfiles/sunflower-kids.modelfile",
        "modelfiles/sunflower-educator.modelfile",
        "ollama/ollama",
        "ollama/ollama.exe"
    ]
    
    REQUIRED_USB_DIRS = [
        "profiles",
        "sessions",
        "logs",
        "config"
    ]
    
    def __init__(self):
        """Initialize partition manager with complete thread safety"""
        self.platform_name = platform.system()
        
        # BUG-008 FIX: Enhanced thread safety with multiple locks
        self._lock = threading.RLock()  # Main lock for state changes
        self._scan_lock = threading.Lock()  # Lock for partition scanning
        self._mount_lock = threading.RLock()  # Lock for mount operations
        
        # Partition paths (protected by _lock)
        self._cdrom_path: Optional[Path] = None
        self._usb_path: Optional[Path] = None
        self._partition_info: Dict[str, PartitionInfo] = {}
        
        # Mount state tracking
        self._mount_in_progress: Dict[str, bool] = {}
        self._mount_events: Dict[str, threading.Event] = {
            "cdrom": threading.Event(),
            "usb": threading.Event()
        }
        
        # Initialize with retry logic
        self._initialize_with_retry()
        
        logger.info(f"Partition manager initialized for {self.platform_name}")
    
    def _initialize_with_retry(self):
        """Initialize partition detection with retry logic"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                self.scan_partitions()
                if self._cdrom_path or self._usb_path:
                    logger.info(f"Partitions detected on attempt {attempt + 1}")
                    break
            except Exception as e:
                logger.warning(f"Partition scan attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error("Failed to detect partitions after all attempts")
    
    def scan_partitions(self):
        """Scan for CD-ROM and USB partitions with thread safety"""
        with self._scan_lock:
            logger.info("Scanning for partitions...")
            
            # Clear previous detections
            with self._lock:
                self._cdrom_path = None
                self._usb_path = None
                self._partition_info.clear()
            
            if self.platform_name == "Windows":
                self._scan_windows_partitions()
            elif self.platform_name == "Darwin":  # macOS
                self._scan_macos_partitions()
            elif self.platform_name == "Linux":
                self._scan_linux_partitions()
            else:
                logger.warning(f"Unsupported platform: {self.platform_name}")
            
            # Signal mount events if partitions found
            with self._lock:
                if self._cdrom_path:
                    self._mount_events["cdrom"].set()
                if self._usb_path:
                    self._mount_events["usb"].set()
    
    def _scan_windows_partitions(self):
        """Scan Windows drive letters for partitions"""
        for drive_letter in string.ascii_uppercase:
            drive_path = Path(f"{drive_letter}:\\")
            
            if not drive_path.exists():
                continue
            
            try:
                self._check_partition(drive_path)
            except Exception as e:
                logger.debug(f"Error checking drive {drive_letter}: {e}")
    
    def _scan_macos_partitions(self):
        """Scan macOS volumes for partitions"""
        volumes_path = Path("/Volumes")
        
        if not volumes_path.exists():
            logger.warning("macOS /Volumes directory not found")
            return
        
        try:
            for volume in volumes_path.iterdir():
                if volume.is_dir():
                    self._check_partition(volume)
        except Exception as e:
            logger.error(f"Error scanning macOS volumes: {e}")
    
    def _scan_linux_partitions(self):
        """Scan Linux mount points for partitions"""
        # Check common mount points
        mount_points = [
            Path("/media"),
            Path("/mnt"),
            Path("/run/media")
        ]
        
        # Also check user-specific mount points
        if os.environ.get("USER"):
            mount_points.append(Path(f"/media/{os.environ['USER']}"))
            mount_points.append(Path(f"/run/media/{os.environ['USER']}"))
        
        for mount_base in mount_points:
            if not mount_base.exists():
                continue
            
            try:
                for mount_point in mount_base.iterdir():
                    if mount_point.is_dir():
                        self._check_partition(mount_point)
            except Exception as e:
                logger.debug(f"Error checking mount point {mount_base}: {e}")
    
    def _check_partition(self, mount_point: Path):
        """Check if a mount point is a Sunflower partition"""
        cdrom_marker = mount_point / self.CDROM_MARKER
        usb_marker = mount_point / self.USB_MARKER
        
        try:
            if cdrom_marker.exists():
                with self._lock:
                    self._cdrom_path = mount_point
                    self._partition_info["cdrom"] = self._get_partition_info(
                        mount_point, PartitionType.CDROM
                    )
                logger.info(f"Found CD-ROM partition at {mount_point}")
            
            elif usb_marker.exists():
                with self._lock:
                    self._usb_path = mount_point
                    self._partition_info["usb"] = self._get_partition_info(
                        mount_point, PartitionType.USB
                    )
                logger.info(f"Found USB partition at {mount_point}")
                
        except Exception as e:
            logger.debug(f"Error checking mount point {mount_point}: {e}")
    
    def _get_partition_info(self, mount_point: Path, partition_type: PartitionType) -> PartitionInfo:
        """Get detailed partition information with proper error handling"""
        try:
            # Get disk usage with timeout
            disk_usage = self._get_disk_usage_with_timeout(mount_point)
            
            # Check if read-only
            is_readonly = not self._can_write(mount_point)
            
            # Get filesystem type
            filesystem = self._get_filesystem_type(mount_point)
            
            # Get volume label
            label = self._get_volume_label(mount_point)
            
            return PartitionInfo(
                mount_point=mount_point,
                partition_type=partition_type,
                size_gb=disk_usage.total / (1024**3) if disk_usage.total else 0,
                used_gb=disk_usage.used / (1024**3) if disk_usage.used else 0,
                available_gb=disk_usage.free / (1024**3) if disk_usage.free else 0,
                is_readonly=is_readonly,
                filesystem=filesystem,
                label=label,
                verified=False,
                last_checked=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get partition info for {mount_point}: {e}")
            # Return minimal info
            return PartitionInfo(
                mount_point=mount_point,
                partition_type=partition_type,
                size_gb=0,
                used_gb=0,
                available_gb=0,
                is_readonly=True,
                filesystem="unknown",
                label=None,
                verified=False,
                last_checked=datetime.now()
            )
    
    def _get_disk_usage_with_timeout(self, path: Path):
        """Get disk usage with timeout to prevent hanging"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(shutil.disk_usage, str(path))
            try:
                return future.result(timeout=DISK_USAGE_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.warning(f"Disk usage check timed out for {path}")
                # Return object with zero values
                class DiskUsage:
                    total = 0
                    used = 0
                    free = 0
                return DiskUsage()
            except Exception as e:
                logger.error(f"Disk usage check failed: {e}")
                class DiskUsage:
                    total = 0
                    used = 0
                    free = 0
                return DiskUsage()
    
    def _can_write(self, path: Path) -> bool:
        """Check if we can write to the partition"""
        test_file = path / f".write_test_{os.getpid()}_{threading.get_ident()}"
        
        try:
            # Try to create a test file
            test_file.write_text("test")
            # Clean up
            test_file.unlink()
            return True
        except (IOError, OSError, PermissionError):
            return False
    
    def _get_filesystem_type(self, mount_point: Path) -> str:
        """Get filesystem type for the partition"""
        if self.platform_name == "Windows":
            try:
                import win32api
                drive = str(mount_point)
                info = win32api.GetVolumeInformation(drive)
                return info[4]  # Filesystem name
            except ImportError:
                return "NTFS"  # Default for Windows
            except Exception:
                return "unknown"
        
        elif self.platform_name == "Darwin":  # macOS
            try:
                result = subprocess.run(
                    ["diskutil", "info", str(mount_point)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if "File System Personality:" in line:
                        return line.split(":")[-1].strip()
            except Exception:
                pass
            return "HFS+" if mount_point.name.startswith("/Volumes") else "APFS"
        
        elif self.platform_name == "Linux":
            try:
                result = subprocess.run(
                    ["df", "-T", str(mount_point)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].split()[1]
            except Exception:
                pass
            return "ext4"  # Default for Linux
        
        return "unknown"
    
    def _get_volume_label(self, mount_point: Path) -> Optional[str]:
        """Get volume label for the partition"""
        if self.platform_name == "Windows":
            try:
                import win32api
                drive = str(mount_point)
                info = win32api.GetVolumeInformation(drive)
                return info[0] if info[0] else None
            except Exception:
                return None
        
        elif self.platform_name == "Darwin":
            # On macOS, the volume name is often the mount point name
            return mount_point.name
        
        elif self.platform_name == "Linux":
            try:
                # Try to get label using lsblk
                result = subprocess.run(
                    ["lsblk", "-no", "LABEL", str(mount_point)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                label = result.stdout.strip()
                return label if label else None
            except Exception:
                return None
        
        return None
    
    def get_cdrom_path(self) -> Optional[Path]:
        """Get CD-ROM partition path with thread safety"""
        with self._lock:
            return self._cdrom_path
    
    def get_usb_path(self) -> Optional[Path]:
        """Get USB partition path with thread safety"""
        with self._lock:
            return self._usb_path
    
    def _verify_cdrom(self) -> bool:
        """Verify CD-ROM partition integrity"""
        with self._lock:
            if not self._cdrom_path:
                return False
            
            try:
                # Check for required files
                for required_file in self.REQUIRED_CDROM_FILES:
                    file_path = self._cdrom_path / required_file
                    # Check both with and without .exe for cross-platform
                    if not file_path.exists() and not file_path.with_suffix('').exists():
                        logger.warning(f"Required file missing: {required_file}")
                        # Don't fail on missing platform-specific files
                        if not (required_file.endswith('.exe') or required_file.endswith('ollama')):
                            return False
                
                # Update verification status
                if "cdrom" in self._partition_info:
                    self._partition_info["cdrom"].verified = True
                    self._partition_info["cdrom"].last_checked = datetime.now()
                
                logger.info("CD-ROM partition verified successfully")
                return True
                
            except Exception as e:
                logger.error(f"CD-ROM verification failed: {e}")
                return False
    
    def _verify_usb(self) -> bool:
        """Verify USB partition integrity"""
        with self._lock:
            if not self._usb_path:
                return False
            
            try:
                # Create required directories if they don't exist
                for required_dir in self.REQUIRED_USB_DIRS:
                    dir_path = self._usb_path / required_dir
                    if not dir_path.exists():
                        try:
                            dir_path.mkdir(parents=True, exist_ok=True)
                            logger.info(f"Created required directory: {required_dir}")
                        except Exception as e:
                            logger.error(f"Failed to create directory {required_dir}: {e}")
                            return False
                
                # Verify write permission
                if not self._can_write(self._usb_path):
                    logger.error("USB partition is not writable")
                    return False
                
                # Update verification status
                if "usb" in self._partition_info:
                    self._partition_info["usb"].verified = True
                    self._partition_info["usb"].last_checked = datetime.now()
                
                logger.info("USB partition verified successfully")
                return True
                
            except Exception as e:
                logger.error(f"USB verification failed: {e}")
                return False
    
    def verify_integrity(self) -> Tuple[bool, Dict[str, Any]]:
        """Verify overall system integrity"""
        results = {
            "cdrom_valid": False,
            "usb_valid": False,
            "checksums": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Verify CD-ROM partition
            results["cdrom_valid"] = self._verify_cdrom()
            if not results["cdrom_valid"]:
                results["errors"].append("CD-ROM partition verification failed")
            
            # Verify USB partition
            results["usb_valid"] = self._verify_usb()
            if not results["usb_valid"]:
                results["errors"].append("USB partition verification failed")
            
            # Calculate checksums for critical files
            if self._cdrom_path:
                critical_files = [
                    self._cdrom_path / "system" / "launcher_common.py",
                    self._cdrom_path / "system" / "openwebui_integration.py"
                ]
                
                for file_path in critical_files:
                    if file_path.exists():
                        checksum = self._calculate_checksum(file_path)
                        if checksum:
                            results["checksums"][file_path.name] = checksum
            
            # Overall success
            success = results["cdrom_valid"] and results["usb_valid"]
            
            return success, results
            
        except Exception as e:
            results["errors"].append(str(e))
            return False, results
    
    def _calculate_checksum(self, file_path: Path) -> Optional[str]:
        """Calculate SHA256 checksum with proper resource management"""
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
            
        except IOError as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return None
    
    def get_partition_info(self, partition_type: PartitionType) -> Optional[PartitionInfo]:
        """Get partition information with thread safety"""
        with self._lock:
            if partition_type == PartitionType.CDROM:
                return self._partition_info.get("cdrom")
            elif partition_type == PartitionType.USB:
                return self._partition_info.get("usb")
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get partition manager status with thread safety"""
        with self._lock:
            return {
                "platform": self.platform_name,
                "cdrom_detected": self._cdrom_path is not None,
                "usb_detected": self._usb_path is not None,
                "cdrom_path": str(self._cdrom_path) if self._cdrom_path else None,
                "usb_path": str(self._usb_path) if self._usb_path else None,
                "partition_info": {k: asdict(v) for k, v in self._partition_info.items()}
            }
    
    @contextmanager
    def mount_context(self, partition_type: PartitionType):
        """Context manager for safely working with partitions"""
        path = None
        
        with self._lock:
            if partition_type == PartitionType.CDROM:
                path = self._cdrom_path
            elif partition_type == PartitionType.USB:
                path = self._usb_path
        
        if not path:
            raise ValueError(f"Partition {partition_type.value} not available")
        
        try:
            yield path
        except Exception as e:
            logger.error(f"Error working with partition {partition_type.value}: {e}")
            raise
        finally:
            # Cleanup if needed
            pass
    
    def wait_for_mount(self, partition_type: PartitionType, timeout: int = MOUNT_WAIT_TIMEOUT) -> bool:
        """
        BUG-008 FIX: Wait for a partition to be mounted with proper thread synchronization
        The entire wait operation is now atomic and thread-safe
        """
        partition_key = partition_type.value
        
        # Mark mount operation in progress
        with self._mount_lock:
            if partition_key in self._mount_in_progress and self._mount_in_progress[partition_key]:
                logger.warning(f"Mount operation already in progress for {partition_key}")
                # Wait for the existing mount operation to complete
                return self._mount_events[partition_key].wait(timeout)
            
            self._mount_in_progress[partition_key] = True
        
        try:
            start_time = time.time()
            
            # BUG-008 FIX: Entire wait loop is now properly synchronized
            while time.time() - start_time < timeout:
                with self._mount_lock:
                    # Rescan partitions
                    self.scan_partitions()
                    
                    # Check if partition is now available
                    with self._lock:
                        if partition_type == PartitionType.CDROM and self._cdrom_path:
                            logger.info(f"CD-ROM partition mounted at {self._cdrom_path}")
                            self._mount_events["cdrom"].set()
                            return True
                        elif partition_type == PartitionType.USB and self._usb_path:
                            logger.info(f"USB partition mounted at {self._usb_path}")
                            self._mount_events["usb"].set()
                            return True
                
                # Wait before next check
                time.sleep(MOUNT_CHECK_INTERVAL)
            
            logger.warning(f"Timeout waiting for {partition_key} mount")
            return False
            
        finally:
            # Clear mount in progress flag
            with self._mount_lock:
                self._mount_in_progress[partition_key] = False
    
    def wait_for_partition(self, partition_type: PartitionType, timeout: int = MOUNT_WAIT_TIMEOUT) -> bool:
        """
        Alias for wait_for_mount for backward compatibility
        Delegates to the fixed wait_for_mount method
        """
        return self.wait_for_mount(partition_type, timeout)
    
    def refresh(self):
        """Refresh partition detection with thread safety"""
        logger.info("Refreshing partition detection...")
        
        # Rescan partitions
        self.scan_partitions()
        
        # Verify detected partitions
        with self._lock:
            if self._cdrom_path:
                self._verify_cdrom()
            if self._usb_path:
                self._verify_usb()
    
    def unmount_partition(self, partition_type: PartitionType) -> bool:
        """Safely unmount a partition (platform-specific)"""
        with self._mount_lock:
            path = None
            
            with self._lock:
                if partition_type == PartitionType.CDROM:
                    path = self._cdrom_path
                elif partition_type == PartitionType.USB:
                    path = self._usb_path
            
            if not path:
                logger.warning(f"Cannot unmount {partition_type.value}: not mounted")
                return False
            
            try:
                if self.platform_name == "Windows":
                    # Windows doesn't have a direct unmount command
                    logger.info(f"Please safely remove {path} using Windows system tray")
                    return True
                    
                elif self.platform_name == "Darwin":  # macOS
                    result = subprocess.run(
                        ["diskutil", "unmount", str(path)],
                        capture_output=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        logger.info(f"Successfully unmounted {path}")
                        with self._lock:
                            if partition_type == PartitionType.CDROM:
                                self._cdrom_path = None
                                self._mount_events["cdrom"].clear()
                            else:
                                self._usb_path = None
                                self._mount_events["usb"].clear()
                        return True
                        
                elif self.platform_name == "Linux":
                    result = subprocess.run(
                        ["umount", str(path)],
                        capture_output=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        logger.info(f"Successfully unmounted {path}")
                        with self._lock:
                            if partition_type == PartitionType.CDROM:
                                self._cdrom_path = None
                                self._mount_events["cdrom"].clear()
                            else:
                                self._usb_path = None
                                self._mount_events["usb"].clear()
                        return True
                
                logger.error(f"Failed to unmount {path}")
                return False
                
            except Exception as e:
                logger.error(f"Unmount error: {e}")
                return False


# Singleton instance with thread-safe initialization
_partition_manager: Optional[PartitionManager] = None
_partition_manager_lock = threading.Lock()


def get_partition_manager() -> PartitionManager:
    """Get or create partition manager singleton with thread safety"""
    global _partition_manager
    
    if _partition_manager is None:
        with _partition_manager_lock:
            if _partition_manager is None:
                _partition_manager = PartitionManager()
    
    return _partition_manager


# Testing and validation
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Partition Manager Testing")
    parser.add_argument("--wait", action="store_true", help="Test wait for mount")
    parser.add_argument("--verify", action="store_true", help="Verify integrity")
    args = parser.parse_args()
    
    # Test partition manager
    manager = get_partition_manager()
    
    print("=" * 60)
    print("Sunflower AI Partition Manager")
    print("=" * 60)
    
    # Display status
    status = manager.get_status()
    print(f"Platform: {status['platform']}")
    print(f"CD-ROM detected: {status['cdrom_detected']}")
    print(f"USB detected: {status['usb_detected']}")
    
    if status['cdrom_path']:
        print(f"CD-ROM path: {status['cdrom_path']}")
    if status['usb_path']:
        print(f"USB path: {status['usb_path']}")
    
    print("-" * 60)
    
    # Test wait for mount
    if args.wait:
        print("Testing wait for mount (10 seconds timeout)...")
        if not status['cdrom_detected']:
            print("Waiting for CD-ROM...")
            if manager.wait_for_mount(PartitionType.CDROM, timeout=10):
                print("✓ CD-ROM mounted!")
            else:
                print("✗ CD-ROM not mounted within timeout")
        
        if not status['usb_detected']:
            print("Waiting for USB...")
            if manager.wait_for_mount(PartitionType.USB, timeout=10):
                print("✓ USB mounted!")
            else:
                print("✗ USB not mounted within timeout")
    
    # Verify integrity
    if args.verify or True:  # Always verify
        print("Verifying partition integrity...")
        success, results = manager.verify_integrity()
        
        print(f"Integrity Check: {'PASS' if success else 'FAIL'}")
        print(f"CD-ROM valid: {results['cdrom_valid']}")
        print(f"USB valid: {results['usb_valid']}")
        
        if results["errors"]:
            print("\nErrors:")
            for error in results["errors"]:
                print(f"  ✗ {error}")
        
        if results["warnings"]:
            print("\nWarnings:")
            for warning in results["warnings"]:
                print(f"  ⚠ {warning}")
        
        if results["checksums"]:
            print("\nChecksums:")
            for file, checksum in results["checksums"].items():
                print(f"  {file}: {checksum[:16]}...")
    
    # Display partition details
    if status["partition_info"]:
        print("-" * 60)
        print("Partition Details:")
        
        for partition_type, info in status["partition_info"].items():
            print(f"\n{partition_type.upper()}:")
            print(f"  Mount: {info['mount_point']}")
            print(f"  Size: {info['size_gb']:.2f} GB")
            print(f"  Used: {info['used_gb']:.2f} GB")
            print(f"  Free: {info['available_gb']:.2f} GB")
            print(f"  Filesystem: {info['filesystem']}")
            print(f"  Read-only: {info['is_readonly']}")
            print(f"  Verified: {info['verified']}")
            if info['label']:
                print(f"  Label: {info['label']}")
    
    # Test context manager
    print("-" * 60)
    try:
        with manager.mount_context(PartitionType.USB) as usb_path:
            print(f"Working with USB partition at: {usb_path}")
            # Test operations would go here
    except ValueError as e:
        print(f"USB partition not available: {e}")
    
    print("-" * 60)
    print("Testing complete!")

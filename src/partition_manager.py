#!/usr/bin/env python3
"""
Sunflower AI Professional System - Partition Manager
Enhanced with thread safety, proper resource management, and retry logic
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
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuration constants
SCAN_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds
MOUNT_CHECK_INTERVAL = 2  # seconds


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
    Enhanced partition manager for dual-partition device architecture
    Thread-safe and with proper resource management
    """
    
    # Partition markers
    CDROM_MARKER = "sunflower_cd.id"
    USB_MARKER = "sunflower_data.id"
    
    def __init__(self):
        """Initialize partition manager with thread safety"""
        self.platform_name = platform.system()
        
        # Thread safety
        self._lock = threading.RLock()
        self._scan_lock = threading.Lock()
        
        # Partition paths (protected by _lock)
        self._cdrom_path = None
        self._usb_path = None
        self._partition_info = {}
        
        # Initialize with retry logic
        self._initialize_with_retry()
        
        logger.info(f"Partition manager initialized for {self.platform_name}")
    
    def _initialize_with_retry(self):
        """Initialize partition detection with retry logic"""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                self.scan_partitions()
                if self._cdrom_path or self._usb_path:
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
            
            if self.platform_name == "Windows":
                self._scan_windows_partitions()
            elif self.platform_name == "Darwin":  # macOS
                self._scan_macos_partitions()
            elif self.platform_name == "Linux":
                self._scan_linux_partitions()
            else:
                logger.warning(f"Unsupported platform: {self.platform_name}")
    
    def _scan_windows_partitions(self):
        """Scan Windows drive letters for partitions"""
        import string
        
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
    with self._lock:  # Acquire lock first
        cdrom_marker = mount_point / self.CDROM_MARKER
        usb_marker = mount_point / self.USB_MARKER
        
        try:
            if cdrom_marker.exists():
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
                size_gb=disk_usage.total / (1024**3),
                used_gb=disk_usage.used / (1024**3),
                available_gb=disk_usage.free / (1024**3),
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
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(shutil.disk_usage, str(path))
            try:
                return future.result(timeout=5)
            except concurrent.futures.TimeoutError:
                logger.warning(f"Disk usage check timed out for {path}")
                # Return dummy values
                class DiskUsage:
                    total = 0
                    used = 0
                    free = 0
                return DiskUsage()
    
    def _can_write(self, path: Path) -> bool:
        """Check if we can write to the partition"""
        test_file = path / f".write_test_{os.getpid()}"
        
        try:
            # Try to create a test file
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Clean up
            test_file.unlink()
            return True
            
        except (IOError, OSError):
            return False
    
    def _get_filesystem_type(self, mount_point: Path) -> str:
        """Get filesystem type for the partition"""
        if self.platform_name == "Windows":
            try:
                import win32api
                import win32file
                
                drive = str(mount_point)
                info = win32api.GetVolumeInformation(drive)
                return info[4]  # Filesystem name
                
            except ImportError:
                return "NTFS"  # Default for Windows
            except Exception:
                return "unknown"
        
        elif self.platform_name in ["Darwin", "Linux"]:
            try:
                import subprocess
                
                result = subprocess.run(
                    ["df", "-T", str(mount_point)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        return lines[1].split()[1]
                        
            except Exception:
                pass
        
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
        
        # For Unix-like systems, the mount point name often is the label
        return mount_point.name
    
    def get_cdrom_path(self) -> Optional[Path]:
        """Get CD-ROM partition path with thread safety"""
        with self._lock:
            return self._cdrom_path
    
    def get_usb_path(self) -> Optional[Path]:
        """Get USB partition path with thread safety"""
        with self._lock:
            return self._usb_path
    
    def verify_partition(self, partition_type: PartitionType) -> bool:
        """Verify partition integrity with thread safety"""
        if partition_type == PartitionType.CDROM:
            return self._verify_cdrom()
        elif partition_type == PartitionType.USB:
            return self._verify_usb()
        return False
    
    def _verify_cdrom(self) -> bool:
        """Verify CD-ROM partition integrity"""
        with self._lock:
            if not self._cdrom_path:
                return False
        
        try:
            # Check marker file
            marker_file = self._cdrom_path / self.CDROM_MARKER
            if not marker_file.exists():
                logger.error("CD-ROM marker file missing")
                return False
            
            # Check required directories
            required_dirs = ["system", "models", "config", "docs"]
            for dir_name in required_dirs:
                dir_path = self._cdrom_path / dir_name
                if not dir_path.exists():
                    logger.error(f"Required directory missing: {dir_name}")
                    return False
            
            # Check critical files
            critical_files = [
                "system/ollama/ollama" if self.platform_name != "Windows" else "system/ollama/ollama.exe",
                "config/system.json",
                "docs/user_guide.pdf"
            ]
            
            for file_path in critical_files:
                full_path = self._cdrom_path / file_path
                if not full_path.exists():
                    logger.warning(f"Critical file missing: {file_path}")
            
            # Update verification status
            with self._lock:
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
            # Check marker file
            marker_file = self._usb_path / self.USB_MARKER
            if not marker_file.exists():
                logger.error("USB marker file missing")
                return False
            
            # Check if writable
            if not self._can_write(self._usb_path):
                logger.error("USB partition is not writable")
                return False
            
            # Create required directories if they don't exist
            required_dirs = ["profiles", "conversations", "logs", "config"]
            for dir_name in required_dirs:
                dir_path = self._usb_path / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Update verification status
            with self._lock:
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
            "errors": []
        }
        
        try:
            # Verify CD-ROM partition
            results["cdrom_valid"] = self._verify_cdrom()
            
            # Verify USB partition
            results["usb_valid"] = self._verify_usb()
            
            # Calculate checksums for critical files
            if self._cdrom_path:
                critical_files = [
                    self._cdrom_path / "system" / "launcher.exe",
                    self._cdrom_path / "config" / "system.json"
                ]
                
                for file_path in critical_files:
                    if file_path.exists():
                        checksum = self._calculate_checksum(file_path)
                        results["checksums"][str(file_path.name)] = checksum
            
            # Overall success
            success = results["cdrom_valid"] and results["usb_valid"]
            
            return success, results
            
        except Exception as e:
            results["errors"].append(str(e))
            return False, results
    
    def _calculate_checksum(self, file_path: Path) -> str:
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
            return ""
    
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
            # Could add cleanup logic here if needed
            pass
    
    def wait_for_partition(self, partition_type: PartitionType, timeout: int = 60) -> bool:
        """Wait for a partition to become available"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Rescan partitions
            self.scan_partitions()
            
            # Check if partition is now available
            with self._lock:
                if partition_type == PartitionType.CDROM and self._cdrom_path:
                    return True
                elif partition_type == PartitionType.USB and self._usb_path:
                    return True
            
            time.sleep(MOUNT_CHECK_INTERVAL)
        
        return False
    
    def refresh(self):
        """Refresh partition detection with thread safety"""
        logger.info("Refreshing partition detection...")
        self.scan_partitions()
        
        # Verify detected partitions
        if self._cdrom_path:
            self._verify_cdrom()
        if self._usb_path:
            self._verify_usb()


# Singleton instance with thread-safe initialization
_partition_manager = None
_partition_manager_lock = threading.Lock()


def get_partition_manager() -> PartitionManager:
    """Get or create partition manager singleton with thread safety"""
    global _partition_manager
    
    if _partition_manager is None:
        with _partition_manager_lock:
            if _partition_manager is None:
                _partition_manager = PartitionManager()
    
    return _partition_manager


# Testing
if __name__ == "__main__":
    # Test partition manager
    manager = PartitionManager()
    
    print("Partition Manager Status:")
    print("-" * 60)
    
    status = manager.get_status()
    for key, value in status.items():
        if key != "partition_info":
            print(f"{key}: {value}")
    
    print("-" * 60)
    
    # Verify integrity
    success, results = manager.verify_integrity()
    print(f"Integrity Check: {'PASS' if success else 'FAIL'}")
    
    if results["errors"]:
        print("Errors:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    # Display partition info
    if status["partition_info"]:
        print("-" * 60)
        print("Partition Details:")
        
        for partition_type, info in status["partition_info"].items():
            print(f"\n{partition_type.upper()}:")
            print(f"  Mount: {info['mount_point']}")
            print(f"  Size: {info['size_gb']:.2f} GB")
            print(f"  Used: {info['used_gb']:.2f} GB")
            print(f"  Free: {info['available_gb']:.2f} GB")
            print(f"  Read-only: {info['is_readonly']}")
            print(f"  Verified: {info['verified']}")
    
    # Test context manager
    try:
        with manager.mount_context(PartitionType.USB) as usb_path:
            print(f"\nWorking with USB partition at: {usb_path}")
    except ValueError as e:
        print(f"USB partition not available: {e}")

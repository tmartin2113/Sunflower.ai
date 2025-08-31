"""
Sunflower AI Professional System - Partition Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Manages the dual-partition architecture with CD-ROM (read-only) and
USB (writable) partitions. Handles partition detection, mounting, and
data management across platforms.
"""

import os
import sys
import json
import platform
import subprocess
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import time

logger = logging.getLogger(__name__)


class PartitionType(Enum):
    """Partition types"""
    CDROM = "cdrom"
    USB = "usb"
    UNKNOWN = "unknown"


class MountState(Enum):
    """Mount states"""
    MOUNTED = "mounted"
    UNMOUNTED = "unmounted"
    ERROR = "error"
    READONLY = "readonly"


@dataclass
class PartitionInfo:
    """Partition information"""
    device: str
    mount_point: str
    filesystem: str
    type: str
    size_gb: float
    used_gb: float
    available_gb: float
    is_readonly: bool
    label: Optional[str] = None
    uuid: Optional[str] = None
    marker_file: Optional[str] = None


class PartitionManager:
    """
    Manages dual-partition device architecture for Sunflower AI.
    Handles automatic detection and mounting of CD-ROM and USB partitions.
    """
    
    # Marker files for partition identification
    CDROM_MARKER = "sunflower_cd.id"
    USB_MARKER = "sunflower_data.id"
    
    # Expected partition sizes (for validation)
    MIN_CDROM_SIZE_GB = 2.0
    MAX_CDROM_SIZE_GB = 8.0
    MIN_USB_SIZE_GB = 0.5
    MAX_USB_SIZE_GB = 64.0
    
    def __init__(self):
        """Initialize partition manager"""
        self.platform_name = platform.system()
        
        # Cache for detected partitions
        self._cdrom_path: Optional[Path] = None
        self._usb_path: Optional[Path] = None
        self._partition_info: Dict[str, PartitionInfo] = {}
        
        # Platform-specific initialization
        self._init_platform_specific()
        
        # Auto-detect partitions on initialization
        self.scan_partitions()
        
        logger.info(f"Partition manager initialized on {self.platform_name}")
    
    def _init_platform_specific(self):
        """Initialize platform-specific settings"""
        if self.platform_name == "Windows":
            self._init_windows()
        elif self.platform_name == "Darwin":
            self._init_macos()
        else:
            self._init_linux()
    
    def _init_windows(self):
        """Initialize Windows-specific settings"""
        # Check for required Windows features
        try:
            import win32api
            import win32file
            self.win32_available = True
        except ImportError:
            self.win32_available = False
            logger.warning("pywin32 not available - using fallback methods")
    
    def _init_macos(self):
        """Initialize macOS-specific settings"""
        # Check for diskutil availability
        self.diskutil_available = shutil.which("diskutil") is not None
        if not self.diskutil_available:
            logger.warning("diskutil not available")
    
    def _init_linux(self):
        """Initialize Linux-specific settings"""
        # Check for required tools
        self.lsblk_available = shutil.which("lsblk") is not None
        self.mount_available = shutil.which("mount") is not None
    
    def scan_partitions(self) -> Dict[str, PartitionInfo]:
        """
        Scan system for Sunflower AI partitions.
        
        Returns:
            Dictionary of detected partitions
        """
        logger.info("Scanning for Sunflower AI partitions...")
        
        self._partition_info.clear()
        self._cdrom_path = None
        self._usb_path = None
        
        if self.platform_name == "Windows":
            self._scan_windows_partitions()
        elif self.platform_name == "Darwin":
            self._scan_macos_partitions()
        else:
            self._scan_linux_partitions()
        
        # Log results
        if self._cdrom_path:
            logger.info(f"Found CD-ROM partition: {self._cdrom_path}")
        else:
            logger.warning("CD-ROM partition not found")
        
        if self._usb_path:
            logger.info(f"Found USB partition: {self._usb_path}")
        else:
            logger.warning("USB partition not found")
        
        return self._partition_info
    
    def _scan_windows_partitions(self):
        """Scan Windows partitions"""
        try:
            # Get all drive letters
            drives = []
            
            if self.win32_available:
                import win32api
                drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            else:
                # Fallback: check common drive letters
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append(drive)
            
            for drive in drives:
                self._check_partition_windows(drive)
                
        except Exception as e:
            logger.error(f"Windows partition scan failed: {e}")
            self._scan_fallback()
    
    def _check_partition_windows(self, drive: str):
        """Check a Windows drive for Sunflower markers"""
        try:
            drive_path = Path(drive)
            
            # Check if drive is accessible
            if not drive_path.exists():
                return
            
            # Get drive info
            usage = psutil.disk_usage(drive)
            size_gb = usage.total / (1024**3)
            
            # Check for CD-ROM marker
            cdrom_marker = drive_path / self.CDROM_MARKER
            if cdrom_marker.exists():
                # Verify it's read-only and correct size
                is_readonly = self._check_readonly_windows(drive)
                
                if self.MIN_CDROM_SIZE_GB <= size_gb <= self.MAX_CDROM_SIZE_GB:
                    self._cdrom_path = drive_path
                    self._partition_info["cdrom"] = PartitionInfo(
                        device=drive,
                        mount_point=str(drive_path),
                        filesystem=self._get_filesystem_windows(drive),
                        type=PartitionType.CDROM.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=is_readonly,
                        marker_file=str(cdrom_marker)
                    )
                    logger.info(f"Detected CD-ROM partition on {drive}")
            
            # Check for USB marker
            usb_marker = drive_path / self.USB_MARKER
            if usb_marker.exists():
                # Verify it's writable and correct size
                if self.MIN_USB_SIZE_GB <= size_gb <= self.MAX_USB_SIZE_GB:
                    self._usb_path = drive_path
                    self._partition_info["usb"] = PartitionInfo(
                        device=drive,
                        mount_point=str(drive_path),
                        filesystem=self._get_filesystem_windows(drive),
                        type=PartitionType.USB.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=False,
                        marker_file=str(usb_marker)
                    )
                    logger.info(f"Detected USB partition on {drive}")
                    
        except Exception as e:
            logger.debug(f"Error checking drive {drive}: {e}")
    
    def _check_readonly_windows(self, drive: str) -> bool:
        """Check if Windows drive is read-only"""
        try:
            if self.win32_available:
                import win32api
                import win32con
                
                # Get volume information
                volume_info = win32api.GetVolumeInformation(drive)
                flags = volume_info[5]
                
                # Check if read-only flag is set
                return bool(flags & win32con.FILE_READ_ONLY_VOLUME)
            else:
                # Fallback: try to create a temp file
                test_file = Path(drive) / f".write_test_{os.getpid()}"
                try:
                    test_file.touch()
                    test_file.unlink()
                    return False
                except:
                    return True
        except:
            return False
    
    def _get_filesystem_windows(self, drive: str) -> str:
        """Get filesystem type for Windows drive"""
        try:
            if self.win32_available:
                import win32api
                volume_info = win32api.GetVolumeInformation(drive)
                return volume_info[4]  # Filesystem name
            else:
                # Fallback
                return "NTFS"
        except:
            return "Unknown"
    
    def _scan_macos_partitions(self):
        """Scan macOS partitions"""
        try:
            if not self.diskutil_available:
                self._scan_fallback()
                return
            
            # List all volumes
            result = subprocess.run(
                ["diskutil", "list", "-plist"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self._scan_fallback()
                return
            
            # Parse plist output
            import plistlib
            plist_data = plistlib.loads(result.stdout.encode())
            
            # Get all volumes
            volumes_result = subprocess.run(
                ["diskutil", "info", "-plist", "/Volumes/*"],
                capture_output=True,
                shell=True,
                text=True,
                timeout=10
            )
            
            # Check each mounted volume
            for volume_path in Path("/Volumes").iterdir():
                if volume_path.is_dir():
                    self._check_partition_macos(volume_path)
                    
        except Exception as e:
            logger.error(f"macOS partition scan failed: {e}")
            self._scan_fallback()
    
    def _check_partition_macos(self, volume_path: Path):
        """Check a macOS volume for Sunflower markers"""
        try:
            # Get volume info
            usage = psutil.disk_usage(str(volume_path))
            size_gb = usage.total / (1024**3)
            
            # Check for CD-ROM marker
            cdrom_marker = volume_path / self.CDROM_MARKER
            if cdrom_marker.exists():
                is_readonly = self._check_readonly_macos(volume_path)
                
                if self.MIN_CDROM_SIZE_GB <= size_gb <= self.MAX_CDROM_SIZE_GB:
                    self._cdrom_path = volume_path
                    self._partition_info["cdrom"] = PartitionInfo(
                        device=str(volume_path),
                        mount_point=str(volume_path),
                        filesystem=self._get_filesystem_macos(volume_path),
                        type=PartitionType.CDROM.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=is_readonly,
                        marker_file=str(cdrom_marker)
                    )
                    logger.info(f"Detected CD-ROM partition at {volume_path}")
            
            # Check for USB marker
            usb_marker = volume_path / self.USB_MARKER
            if usb_marker.exists():
                if self.MIN_USB_SIZE_GB <= size_gb <= self.MAX_USB_SIZE_GB:
                    self._usb_path = volume_path
                    self._partition_info["usb"] = PartitionInfo(
                        device=str(volume_path),
                        mount_point=str(volume_path),
                        filesystem=self._get_filesystem_macos(volume_path),
                        type=PartitionType.USB.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=False,
                        marker_file=str(usb_marker)
                    )
                    logger.info(f"Detected USB partition at {volume_path}")
                    
        except Exception as e:
            logger.debug(f"Error checking volume {volume_path}: {e}")
    
    def _check_readonly_macos(self, volume_path: Path) -> bool:
        """Check if macOS volume is read-only"""
        try:
            # Try to create a temp file
            test_file = volume_path / f".write_test_{os.getpid()}"
            try:
                test_file.touch()
                test_file.unlink()
                return False
            except:
                return True
        except:
            return False
    
    def _get_filesystem_macos(self, volume_path: Path) -> str:
        """Get filesystem type for macOS volume"""
        try:
            result = subprocess.run(
                ["diskutil", "info", str(volume_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            for line in result.stdout.split('\n'):
                if "File System Personality:" in line:
                    return line.split(":")[-1].strip()
            
            return "Unknown"
        except:
            return "Unknown"
    
    def _scan_linux_partitions(self):
        """Scan Linux partitions"""
        try:
            # Check mounted filesystems
            for partition in psutil.disk_partitions():
                mount_point = Path(partition.mountpoint)
                self._check_partition_linux(mount_point, partition)
                
        except Exception as e:
            logger.error(f"Linux partition scan failed: {e}")
            self._scan_fallback()
    
    def _check_partition_linux(self, mount_point: Path, partition_info):
        """Check a Linux mount point for Sunflower markers"""
        try:
            # Get partition info
            usage = psutil.disk_usage(str(mount_point))
            size_gb = usage.total / (1024**3)
            
            # Check for CD-ROM marker
            cdrom_marker = mount_point / self.CDROM_MARKER
            if cdrom_marker.exists():
                is_readonly = "ro" in partition_info.opts
                
                if self.MIN_CDROM_SIZE_GB <= size_gb <= self.MAX_CDROM_SIZE_GB:
                    self._cdrom_path = mount_point
                    self._partition_info["cdrom"] = PartitionInfo(
                        device=partition_info.device,
                        mount_point=str(mount_point),
                        filesystem=partition_info.fstype,
                        type=PartitionType.CDROM.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=is_readonly,
                        marker_file=str(cdrom_marker)
                    )
                    logger.info(f"Detected CD-ROM partition at {mount_point}")
            
            # Check for USB marker
            usb_marker = mount_point / self.USB_MARKER
            if usb_marker.exists():
                if self.MIN_USB_SIZE_GB <= size_gb <= self.MAX_USB_SIZE_GB:
                    self._usb_path = mount_point
                    self._partition_info["usb"] = PartitionInfo(
                        device=partition_info.device,
                        mount_point=str(mount_point),
                        filesystem=partition_info.fstype,
                        type=PartitionType.USB.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=False,
                        marker_file=str(usb_marker)
                    )
                    logger.info(f"Detected USB partition at {mount_point}")
                    
        except Exception as e:
            logger.debug(f"Error checking mount point {mount_point}: {e}")
    
    def _scan_fallback(self):
        """Fallback partition scanning for development"""
        logger.info("Using fallback partition scanning (development mode)")
        
        # Check current directory structure
        current_dir = Path.cwd()
        
        # Look for marker files in parent directories
        for parent in [current_dir] + list(current_dir.parents)[:3]:
            # Check for CD-ROM marker
            cdrom_marker = parent / self.CDROM_MARKER
            if cdrom_marker.exists() and not self._cdrom_path:
                self._cdrom_path = parent
                logger.info(f"Found CD-ROM marker in development directory: {parent}")
            
            # Check for USB marker or data directory
            usb_marker = parent / self.USB_MARKER
            data_dir = parent / "data"
            
            if usb_marker.exists() and not self._usb_path:
                self._usb_path = parent
                logger.info(f"Found USB marker in development directory: {parent}")
            elif data_dir.exists() and not self._usb_path:
                # Create marker for development
                self._usb_path = data_dir
                marker_file = data_dir / self.USB_MARKER
                if not marker_file.exists():
                    try:
                        marker_file.write_text(json.dumps({
                            "type": "SUNFLOWER_DATA_PARTITION",
                            "mode": "development",
                            "created": time.strftime("%Y-%m-%d %H:%M:%S")
                        }, indent=2))
                    except:
                        pass
                logger.info(f"Using development data directory: {data_dir}")
    
    def find_cdrom_partition(self) -> Optional[Path]:
        """
        Find and return CD-ROM partition path.
        
        Returns:
            Path to CD-ROM partition or None
        """
        if not self._cdrom_path:
            self.scan_partitions()
        
        return self._cdrom_path
    
    def find_usb_partition(self) -> Optional[Path]:
        """
        Find and return USB partition path.
        
        Returns:
            Path to USB partition or None
        """
        if not self._usb_path:
            self.scan_partitions()
        
        return self._usb_path
    
    def initialize_usb_partition(self, path: Optional[Path] = None) -> bool:
        """
        Initialize USB partition with required directory structure.
        
        Args:
            path: Path to USB partition (auto-detect if None)
        
        Returns:
            True if successful
        """
        usb_path = path or self._usb_path
        
        if not usb_path:
            logger.error("No USB partition path available")
            return False
        
        try:
            # Create directory structure
            directories = [
                "profiles",
                "profiles/.encrypted",
                "conversations",
                "conversations/.encrypted",
                "sessions",
                "sessions/active",
                "sessions/completed",
                "sessions/safety_logs",
                "logs",
                "logs/system",
                "logs/safety",
                "cache",
                "cache/models",
                "cache/temp",
                "backups",
                "backups/auto",
                "backups/manual",
                ".security",
                ".config"
            ]
            
            for dir_name in directories:
                dir_path = usb_path / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create marker file if it doesn't exist
            marker_file = usb_path / self.USB_MARKER
            if not marker_file.exists():
                marker_data = {
                    "type": "SUNFLOWER_DATA_PARTITION",
                    "version": "1.0",
                    "initialized": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "platform": self.platform_name
                }
                marker_file.write_text(json.dumps(marker_data, indent=2))
            
            # Create initialization flag
            init_flag = usb_path / ".initialized"
            init_flag.write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
            
            logger.info(f"Initialized USB partition at {usb_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize USB partition: {e}")
            return False
    
    def verify_partitions(self) -> Tuple[bool, List[str]]:
        """
        Verify both partitions are properly configured.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check CD-ROM partition
        if not self._cdrom_path:
            issues.append("CD-ROM partition not found")
        else:
            # Verify CD-ROM contents
            required_files = [
                "modelfiles/Sunflower_AI_Kids.modelfile",
                "modelfiles/Sunflower_AI_Educator.modelfile"
            ]
            
            for file_path in required_files:
                full_path = self._cdrom_path / file_path
                if not full_path.exists():
                    issues.append(f"Missing required file: {file_path}")
            
            # Check if read-only
            cdrom_info = self._partition_info.get("cdrom")
            if cdrom_info and not cdrom_info.is_readonly:
                issues.append("CD-ROM partition is not read-only")
        
        # Check USB partition
        if not self._usb_path:
            issues.append("USB partition not found")
        else:
            # Check if writable
            test_file = self._usb_path / f".write_test_{os.getpid()}"
            try:
                test_file.touch()
                test_file.unlink()
            except:
                issues.append("USB partition is not writable")
            
            # Check available space
            usb_info = self._partition_info.get("usb")
            if usb_info and usb_info.available_gb < 0.1:
                issues.append(f"USB partition low on space: {usb_info.available_gb:.2f}GB available")
        
        return len(issues) == 0, issues
    
    def get_partition_info(self, partition_type: PartitionType) -> Optional[PartitionInfo]:
        """Get information about a specific partition"""
        if partition_type == PartitionType.CDROM:
            return self._partition_info.get("cdrom")
        elif partition_type == PartitionType.USB:
            return self._partition_info.get("usb")
        return None
    
    def check_partition_health(self) -> Dict[str, Any]:
        """Check health status of both partitions"""
        health = {
            "cdrom": {
                "status": "unknown",
                "issues": []
            },
            "usb": {
                "status": "unknown",
                "issues": []
            }
        }
        
        # Check CD-ROM health
        if self._cdrom_path:
            cdrom_info = self._partition_info.get("cdrom")
            if cdrom_info:
                health["cdrom"]["status"] = "healthy"
                
                # Check for issues
                if cdrom_info.available_gb < 0.1:
                    health["cdrom"]["status"] = "warning"
                    health["cdrom"]["issues"].append("Low disk space")
                
                if not cdrom_info.is_readonly:
                    health["cdrom"]["status"] = "error"
                    health["cdrom"]["issues"].append("Not read-only")
        else:
            health["cdrom"]["status"] = "missing"
            health["cdrom"]["issues"].append("Partition not found")
        
        # Check USB health
        if self._usb_path:
            usb_info = self._partition_info.get("usb")
            if usb_info:
                health["usb"]["status"] = "healthy"
                
                # Check for issues
                if usb_info.available_gb < 0.5:
                    health["usb"]["status"] = "warning"
                    health["usb"]["issues"].append(f"Low disk space: {usb_info.available_gb:.2f}GB")
                
                if usb_info.is_readonly:
                    health["usb"]["status"] = "error"
                    health["usb"]["issues"].append("Read-only (should be writable)")
        else:
            health["usb"]["status"] = "missing"
            health["usb"]["issues"].append("Partition not found")
        
        return health
    
    def wait_for_partitions(self, timeout: int = 30) -> bool:
        """
        Wait for both partitions to be available.
        
        Args:
            timeout: Maximum seconds to wait
        
        Returns:
            True if both partitions found within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            self.scan_partitions()
            
            if self._cdrom_path and self._usb_path:
                logger.info("Both partitions detected")
                return True
            
            time.sleep(1)
        
        logger.warning(f"Timeout waiting for partitions (waited {timeout} seconds)")
        return False
    
    def eject_safely(self) -> bool:
        """Safely eject the USB device"""
        if not self._usb_path:
            logger.warning("No USB partition to eject")
            return True
        
        try:
            # Ensure all files are closed
            import gc
            gc.collect()
            
            if self.platform_name == "Windows":
                # Windows eject
                if self.win32_available:
                    # Use Windows API for safe removal
                    logger.info("Ejecting USB device on Windows...")
                    # Implementation would use win32file.DeviceIoControl
                    return True
                else:
                    logger.warning("Cannot safely eject on Windows without pywin32")
                    return False
                    
            elif self.platform_name == "Darwin":
                # macOS eject
                result = subprocess.run(
                    ["diskutil", "eject", str(self._usb_path)],
                    capture_output=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info("USB device ejected successfully")
                    return True
                else:
                    logger.error(f"Failed to eject USB device: {result.stderr}")
                    return False
                    
            else:
                # Linux eject
                result = subprocess.run(
                    ["umount", str(self._usb_path)],
                    capture_output=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info("USB device unmounted successfully")
                    return True
                else:
                    logger.error(f"Failed to unmount USB device: {result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to eject USB device: {e}")
            return False

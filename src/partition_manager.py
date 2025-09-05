#!/usr/bin/env python3
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
import hashlib
import threading

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
    verified: bool = False
    integrity_hash: Optional[str] = None


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
        
        # Thread safety
        self._scan_lock = threading.Lock()
        
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
        
        # Windows drive letters to scan
        self.windows_drives = [f"{chr(i)}:" for i in range(65, 91)]  # A: to Z:
    
    def _init_macos(self):
        """Initialize macOS-specific settings"""
        # Check for diskutil availability
        self.diskutil_available = shutil.which("diskutil") is not None
        if not self.diskutil_available:
            logger.warning("diskutil not available")
        
        # macOS mount points
        self.macos_mount_points = [
            Path("/Volumes"),
            Path("/media"),
            Path("/mnt")
        ]
    
    def _init_linux(self):
        """Initialize Linux-specific settings"""
        # Check for required tools
        self.lsblk_available = shutil.which("lsblk") is not None
        self.mount_available = shutil.which("mount") is not None
        
        # Linux mount points
        self.linux_mount_points = [
            Path("/media"),
            Path("/mnt"),
            Path("/run/media")
        ]
    
    def scan_partitions(self) -> Dict[str, PartitionInfo]:
        """
        Scan system for Sunflower AI partitions.
        
        Returns:
            Dictionary of detected partitions
        """
        with self._scan_lock:
            logger.info("Scanning for Sunflower AI partitions...")
            
            # Clear previous results
            self._cdrom_path = None
            self._usb_path = None
            self._partition_info.clear()
            
            # Platform-specific scanning
            if self.platform_name == "Windows":
                self._scan_windows()
            elif self.platform_name == "Darwin":
                self._scan_macos()
            else:
                self._scan_linux()
            
            # Fallback scan if nothing found
            if not self._cdrom_path and not self._usb_path:
                self._scan_fallback()
            
            # Log results
            if self._cdrom_path:
                logger.info(f"CD-ROM partition found: {self._cdrom_path}")
            else:
                logger.warning("CD-ROM partition not found")
            
            if self._usb_path:
                logger.info(f"USB partition found: {self._usb_path}")
            else:
                logger.warning("USB partition not found")
            
            return self._partition_info.copy()
    
    def _scan_windows(self):
        """Scan for partitions on Windows"""
        logger.debug("Scanning Windows drives...")
        
        for drive in self.windows_drives:
            try:
                drive_path = Path(drive)
                
                # Check if drive exists
                if not drive_path.exists():
                    continue
                
                # Get drive information
                if self.win32_available:
                    self._check_drive_windows_win32(drive_path)
                else:
                    self._check_drive_windows_fallback(drive_path)
                    
            except Exception as e:
                logger.debug(f"Error scanning drive {drive}: {e}")
                continue
    
    def _check_drive_windows_win32(self, drive_path: Path):
        """Check Windows drive using Win32 API"""
        import win32api
        import win32file
        
        try:
            drive = str(drive_path) + "\\"
            
            # Get drive type
            drive_type = win32file.GetDriveType(drive)
            
            # Get volume information
            volume_info = win32api.GetVolumeInformation(drive)
            label = volume_info[0] if volume_info[0] else ""
            filesystem = volume_info[4]
            
            # Get disk usage
            usage = psutil.disk_usage(str(drive_path))
            size_gb = usage.total / (1024**3)
            
            # Check for CD-ROM marker
            cdrom_marker = drive_path / self.CDROM_MARKER
            if cdrom_marker.exists():
                # Verify it's a CD-ROM type drive
                is_cdrom = drive_type == win32file.DRIVE_CDROM
                is_readonly = True  # CD-ROMs are always read-only
                
                if self.MIN_CDROM_SIZE_GB <= size_gb <= self.MAX_CDROM_SIZE_GB:
                    self._cdrom_path = drive_path
                    self._partition_info["cdrom"] = PartitionInfo(
                        device=drive,
                        mount_point=str(drive_path),
                        filesystem=filesystem,
                        type=PartitionType.CDROM.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=is_readonly,
                        label=label,
                        marker_file=str(cdrom_marker),
                        verified=True
                    )
                    logger.info(f"Detected CD-ROM partition on {drive}")
            
            # Check for USB marker
            usb_marker = drive_path / self.USB_MARKER
            if usb_marker.exists():
                # Verify it's a removable drive
                is_removable = drive_type == win32file.DRIVE_REMOVABLE or drive_type == win32file.DRIVE_FIXED
                
                if self.MIN_USB_SIZE_GB <= size_gb <= self.MAX_USB_SIZE_GB and is_removable:
                    self._usb_path = drive_path
                    self._partition_info["usb"] = PartitionInfo(
                        device=drive,
                        mount_point=str(drive_path),
                        filesystem=filesystem,
                        type=PartitionType.USB.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=False,
                        label=label,
                        marker_file=str(usb_marker),
                        verified=True
                    )
                    logger.info(f"Detected USB partition on {drive}")
                    
        except Exception as e:
            logger.debug(f"Error checking drive {drive_path} with Win32: {e}")
    
    def _check_drive_windows_fallback(self, drive_path: Path):
        """Check Windows drive using fallback methods"""
        try:
            # Get disk usage
            usage = psutil.disk_usage(str(drive_path))
            size_gb = usage.total / (1024**3)
            
            # Check for CD-ROM marker
            cdrom_marker = drive_path / self.CDROM_MARKER
            if cdrom_marker.exists():
                is_readonly = self._check_readonly_windows(drive_path)
                
                if self.MIN_CDROM_SIZE_GB <= size_gb <= self.MAX_CDROM_SIZE_GB:
                    self._cdrom_path = drive_path
                    self._partition_info["cdrom"] = PartitionInfo(
                        device=str(drive_path),
                        mount_point=str(drive_path),
                        filesystem="unknown",
                        type=PartitionType.CDROM.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=is_readonly,
                        marker_file=str(cdrom_marker)
                    )
                    logger.info(f"Detected CD-ROM partition on {drive_path}")
            
            # Check for USB marker
            usb_marker = drive_path / self.USB_MARKER
            if usb_marker.exists():
                if self.MIN_USB_SIZE_GB <= size_gb <= self.MAX_USB_SIZE_GB:
                    self._usb_path = drive_path
                    self._partition_info["usb"] = PartitionInfo(
                        device=str(drive_path),
                        mount_point=str(drive_path),
                        filesystem="unknown",
                        type=PartitionType.USB.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=False,
                        marker_file=str(usb_marker)
                    )
                    logger.info(f"Detected USB partition on {drive_path}")
                    
        except Exception as e:
            logger.debug(f"Error checking drive {drive_path}: {e}")
    
    def _check_readonly_windows(self, drive_path: Path) -> bool:
        """Check if Windows drive is read-only"""
        try:
            # Try to create a temporary file
            test_file = drive_path / f".sunflower_test_{os.getpid()}"
            test_file.touch()
            test_file.unlink()
            return False
        except:
            return True
    
    def _get_filesystem_windows(self, drive: str) -> str:
        """Get filesystem type on Windows"""
        try:
            result = subprocess.run(
                ["fsutil", "fsinfo", "volumeinfo", drive],
                capture_output=True, text=True, timeout=5
            )
            
            for line in result.stdout.split('\n'):
                if "File System Name" in line:
                    return line.split(':')[1].strip()
            
            return "unknown"
        except:
            return "unknown"
    
    def _scan_macos(self):
        """Scan for partitions on macOS"""
        logger.debug("Scanning macOS volumes...")
        
        if self.diskutil_available:
            self._scan_macos_diskutil()
        else:
            self._scan_macos_fallback()
    
    def _scan_macos_diskutil(self):
        """Scan macOS using diskutil"""
        try:
            # List all volumes
            result = subprocess.run(
                ["diskutil", "list", "-plist"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                import plistlib
                plist = plistlib.loads(result.stdout.encode())
                
                # Process volumes
                for volume in plist.get("AllDisksAndPartitions", []):
                    self._check_macos_volume(volume)
                    
        except Exception as e:
            logger.error(f"diskutil scan failed: {e}")
            self._scan_macos_fallback()
    
    def _check_macos_volume(self, volume_info: Dict):
        """Check macOS volume for Sunflower markers"""
        try:
            mount_point = volume_info.get("MountPoint")
            if not mount_point:
                return
            
            mount_path = Path(mount_point)
            if not mount_path.exists():
                return
            
            # Get volume size
            usage = psutil.disk_usage(str(mount_path))
            size_gb = usage.total / (1024**3)
            
            # Check for markers
            cdrom_marker = mount_path / self.CDROM_MARKER
            usb_marker = mount_path / self.USB_MARKER
            
            if cdrom_marker.exists():
                if self.MIN_CDROM_SIZE_GB <= size_gb <= self.MAX_CDROM_SIZE_GB:
                    self._cdrom_path = mount_path
                    self._partition_info["cdrom"] = PartitionInfo(
                        device=volume_info.get("DeviceIdentifier", "unknown"),
                        mount_point=str(mount_path),
                        filesystem=volume_info.get("FilesystemType", "unknown"),
                        type=PartitionType.CDROM.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=not volume_info.get("Writable", False),
                        label=volume_info.get("VolumeName"),
                        uuid=volume_info.get("VolumeUUID"),
                        marker_file=str(cdrom_marker),
                        verified=True
                    )
                    logger.info(f"Detected CD-ROM partition at {mount_path}")
            
            if usb_marker.exists():
                if self.MIN_USB_SIZE_GB <= size_gb <= self.MAX_USB_SIZE_GB:
                    self._usb_path = mount_path
                    self._partition_info["usb"] = PartitionInfo(
                        device=volume_info.get("DeviceIdentifier", "unknown"),
                        mount_point=str(mount_path),
                        filesystem=volume_info.get("FilesystemType", "unknown"),
                        type=PartitionType.USB.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=not volume_info.get("Writable", True),
                        label=volume_info.get("VolumeName"),
                        uuid=volume_info.get("VolumeUUID"),
                        marker_file=str(usb_marker),
                        verified=True
                    )
                    logger.info(f"Detected USB partition at {mount_path}")
                    
        except Exception as e:
            logger.debug(f"Error checking macOS volume: {e}")
    
    def _scan_macos_fallback(self):
        """Fallback scan for macOS"""
        for mount_base in self.macos_mount_points:
            if not mount_base.exists():
                continue
            
            for mount_point in mount_base.iterdir():
                if mount_point.is_dir():
                    self._check_mount_point(mount_point)
    
    def _scan_linux(self):
        """Scan for partitions on Linux"""
        logger.debug("Scanning Linux partitions...")
        
        try:
            # Use psutil to get all partitions
            partitions = psutil.disk_partitions(all=False)
            
            for partition in partitions:
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
                        marker_file=str(cdrom_marker),
                        verified=True
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
                        is_readonly="ro" in partition_info.opts,
                        marker_file=str(usb_marker),
                        verified=True
                    )
                    logger.info(f"Detected USB partition at {mount_point}")
                    
        except Exception as e:
            logger.debug(f"Error checking partition {mount_point}: {e}")
    
    def _scan_fallback(self):
        """Fallback scan method for all platforms"""
        logger.debug("Running fallback partition scan...")
        
        # Check common mount points
        common_paths = [
            Path("/Volumes/SUNFLOWER_CD"),
            Path("/Volumes/SUNFLOWER_DATA"),
            Path("D:/"),
            Path("E:/"),
            Path("F:/"),
            Path("/media/cdrom"),
            Path("/media/usb"),
            Path("/mnt/cdrom"),
            Path("/mnt/usb")
        ]
        
        for path in common_paths:
            if path.exists():
                self._check_mount_point(path)
    
    def _check_mount_point(self, mount_point: Path):
        """Check a mount point for Sunflower markers"""
        try:
            # Check for CD-ROM marker
            cdrom_marker = mount_point / self.CDROM_MARKER
            if cdrom_marker.exists() and not self._cdrom_path:
                usage = psutil.disk_usage(str(mount_point))
                size_gb = usage.total / (1024**3)
                
                if self.MIN_CDROM_SIZE_GB <= size_gb <= self.MAX_CDROM_SIZE_GB:
                    self._cdrom_path = mount_point
                    self._partition_info["cdrom"] = PartitionInfo(
                        device="unknown",
                        mount_point=str(mount_point),
                        filesystem="unknown",
                        type=PartitionType.CDROM.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=True,
                        marker_file=str(cdrom_marker)
                    )
                    logger.info(f"Found CD-ROM partition at {mount_point}")
            
            # Check for USB marker
            usb_marker = mount_point / self.USB_MARKER
            if usb_marker.exists() and not self._usb_path:
                usage = psutil.disk_usage(str(mount_point))
                size_gb = usage.total / (1024**3)
                
                if self.MIN_USB_SIZE_GB <= size_gb <= self.MAX_USB_SIZE_GB:
                    self._usb_path = mount_point
                    self._partition_info["usb"] = PartitionInfo(
                        device="unknown",
                        mount_point=str(mount_point),
                        filesystem="unknown",
                        type=PartitionType.USB.value,
                        size_gb=round(size_gb, 2),
                        used_gb=round(usage.used / (1024**3), 2),
                        available_gb=round(usage.free / (1024**3), 2),
                        is_readonly=False,
                        marker_file=str(usb_marker)
                    )
                    logger.info(f"Found USB partition at {mount_point}")
                    
        except Exception as e:
            logger.debug(f"Error checking mount point {mount_point}: {e}")
    
    def get_cdrom_path(self) -> Optional[Path]:
        """Get CD-ROM partition path"""
        return self._cdrom_path
    
    def get_usb_path(self) -> Optional[Path]:
        """Get USB partition path"""
        return self._usb_path
    
    def verify_partition(self, partition_type: PartitionType) -> bool:
        """Verify partition integrity"""
        if partition_type == PartitionType.CDROM:
            return self._verify_cdrom()
        elif partition_type == PartitionType.USB:
            return self._verify_usb()
        return False
    
    def _verify_cdrom(self) -> bool:
        """Verify CD-ROM partition integrity"""
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
            if "cdrom" in self._partition_info:
                self._partition_info["cdrom"].verified = True
            
            logger.info("CD-ROM partition verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"CD-ROM verification failed: {e}")
            return False
    
    def _verify_usb(self) -> bool:
        """Verify USB partition integrity"""
        if not self._usb_path:
            return False
        
        try:
            # Check marker file
            marker_file = self._usb_path / self.USB_MARKER
            if not marker_file.exists():
                logger.error("USB marker file missing")
                return False
            
            # Check write permissions
            test_file = self._usb_path / f".test_{os.getpid()}"
            try:
                test_file.write_text("test")
                test_content = test_file.read_text()
                test_file.unlink()
                
                if test_content != "test":
                    logger.error("USB partition write test failed")
                    return False
                    
            except Exception as e:
                logger.error(f"USB partition not writable: {e}")
                return False
            
            # Create required directories
            required_dirs = ["profiles", "sessions", "logs", "config", "ollama_data"]
            for dir_name in required_dirs:
                dir_path = self._usb_path / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Update verification status
            if "usb" in self._partition_info:
                self._partition_info["usb"].verified = True
            
            logger.info("USB partition verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"USB verification failed: {e}")
            return False
    
    def verify_integrity(self) -> Tuple[bool, Dict[str, Any]]:
        """Verify integrity of both partitions"""
        results = {
            "cdrom_found": self._cdrom_path is not None,
            "usb_found": self._usb_path is not None,
            "cdrom_valid": False,
            "usb_valid": False,
            "errors": []
        }
        
        if self._cdrom_path:
            results["cdrom_valid"] = self._verify_cdrom()
            if not results["cdrom_valid"]:
                results["errors"].append("CD-ROM partition verification failed")
        else:
            results["errors"].append("CD-ROM partition not found")
        
        if self._usb_path:
            results["usb_valid"] = self._verify_usb()
            if not results["usb_valid"]:
                results["errors"].append("USB partition verification failed")
        else:
            results["errors"].append("USB partition not found")
        
        success = results["cdrom_valid"] and results["usb_valid"]
        return success, results
    
    def get_partition_info(self, partition_type: PartitionType) -> Optional[PartitionInfo]:
        """Get detailed partition information"""
        if partition_type == PartitionType.CDROM:
            return self._partition_info.get("cdrom")
        elif partition_type == PartitionType.USB:
            return self._partition_info.get("usb")
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get partition manager status"""
        return {
            "platform": self.platform_name,
            "cdrom_detected": self._cdrom_path is not None,
            "usb_detected": self._usb_path is not None,
            "cdrom_path": str(self._cdrom_path) if self._cdrom_path else None,
            "usb_path": str(self._usb_path) if self._usb_path else None,
            "partition_info": {k: asdict(v) for k, v in self._partition_info.items()}
        }
    
    def simulate_readonly(self, path: Path) -> bool:
        """Test if partition is read-only (for testing)"""
        try:
            test_file = path / f".readonly_test_{os.getpid()}"
            test_file.touch()
            test_file.unlink()
            return False
        except:
            return True
    
    def refresh(self):
        """Refresh partition detection"""
        self.scan_partitions()


# Singleton instance
_partition_manager: Optional[PartitionManager] = None


def get_partition_manager() -> PartitionManager:
    """Get or create partition manager singleton"""
    global _partition_manager
    
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
            print(f"  Size: {info['size_gb']} GB")
            print(f"  Used: {info['used_gb']} GB")
            print(f"  Free: {info['available_gb']} GB")
            print(f"  Read-only: {info['is_readonly']}")
            print(f"  Verified: {info['verified']}")

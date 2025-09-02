#!/usr/bin/env python3
"""
Sunflower AI Professional System - Partitioned Device Creation Tool
Creates dual-partition devices with CD-ROM (read-only) and USB (writeable) sections
Version: 6.2 | Platform: Windows/macOS | Architecture: Partitioned Device
"""

import os
import sys
import json
import time
import shutil
import hashlib
import platform
import subprocess
import tempfile
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import secrets
import struct

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('device_creation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SunflowerDeviceCreator')


class PartitionType(Enum):
    """Partition types for device creation"""
    CDROM = "cdrom"
    USB = "usb"
    HYBRID = "hybrid"


class DeviceStatus(Enum):
    """Device creation status codes"""
    NOT_STARTED = "not_started"
    PREPARING = "preparing"
    CREATING_PARTITIONS = "creating_partitions"
    COPYING_SYSTEM = "copying_system"
    CONFIGURING = "configuring"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class DeviceConfiguration:
    """Configuration for partitioned device creation"""
    device_path: str
    cdrom_size_mb: int = 4096  # 4GB CD-ROM partition
    usb_size_mb: int = 1024     # 1GB USB partition
    volume_label: str = "SUNFLOWER_AI"
    device_id: str = ""
    creation_date: str = ""
    platform_type: str = ""
    model_variants: List[str] = None
    encryption_key: str = ""
    
    def __post_init__(self):
        if not self.device_id:
            self.device_id = self._generate_device_id()
        if not self.creation_date:
            self.creation_date = datetime.now().isoformat()
        if not self.platform_type:
            self.platform_type = platform.system().lower()
        if self.model_variants is None:
            self.model_variants = ["llama3.2:7b", "llama3.2:3b", "llama3.2:1b", "llama3.2:1b-q4_0"]
        if not self.encryption_key:
            self.encryption_key = secrets.token_hex(32)
    
    def _generate_device_id(self) -> str:
        """Generate unique device identifier"""
        timestamp = int(time.time() * 1000)
        random_component = secrets.token_hex(8)
        return f"SUNFLOWER-{timestamp}-{random_component}".upper()


class PartitionedDeviceCreator:
    """Creates partitioned devices for Sunflower AI distribution"""
    
    def __init__(self, config: DeviceConfiguration):
        self.config = config
        self.status = DeviceStatus.NOT_STARTED
        self.progress = 0.0
        self.current_operation = ""
        self.errors: List[str] = []
        self.checksums: Dict[str, str] = {}
        self.manifest: Dict[str, Any] = {}
        
        # Platform-specific command mapping
        self.platform = platform.system().lower()
        self.commands = self._get_platform_commands()
        
        # Paths for content
        self.source_dir = Path("../build")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sunflower_"))
        
    def _get_platform_commands(self) -> Dict[str, str]:
        """Get platform-specific commands for device operations"""
        if self.platform == "windows":
            return {
                "list_disks": "wmic diskdrive get Name,Size,Model",
                "partition": "diskpart",
                "format_cdrom": "format {device} /FS:CDFS /V:{label} /Q",
                "format_usb": "format {device} /FS:exFAT /V:{label}_DATA /Q",
                "mount": "mountvol {device} {path}",
                "unmount": "mountvol {path} /D",
                "verify": "chkdsk {device} /F"
            }
        elif self.platform == "darwin":  # macOS
            return {
                "list_disks": "diskutil list",
                "partition": "diskutil",
                "format_cdrom": "diskutil eraseVolume UDRO {label} {device}",
                "format_usb": "diskutil eraseVolume ExFAT {label}_DATA {device}",
                "mount": "diskutil mount {device}",
                "unmount": "diskutil unmount {device}",
                "verify": "diskutil verifyVolume {device}"
            }
        else:  # Linux
            return {
                "list_disks": "lsblk -o NAME,SIZE,MODEL",
                "partition": "parted",
                "format_cdrom": "mkisofs -o {device} -V {label} -r",
                "format_usb": "mkfs.exfat -n {label}_DATA {device}",
                "mount": "mount {device} {path}",
                "unmount": "umount {device}",
                "verify": "fsck {device}"
            }
    
    def create_device(self) -> bool:
        """Main method to create partitioned device"""
        try:
            logger.info(f"Starting device creation for: {self.config.device_path}")
            self.status = DeviceStatus.PREPARING
            
            # Verify device is available and suitable
            if not self._verify_device():
                return False
            
            # Create partition layout
            self.status = DeviceStatus.CREATING_PARTITIONS
            if not self._create_partitions():
                return False
            
            # Copy system files to CD-ROM partition
            self.status = DeviceStatus.COPYING_SYSTEM
            if not self._copy_system_files():
                return False
            
            # Configure USB partition
            self.status = DeviceStatus.CONFIGURING
            if not self._configure_usb_partition():
                return False
            
            # Verify integrity
            self.status = DeviceStatus.VERIFYING
            if not self._verify_integrity():
                return False
            
            # Create manifest
            self._create_manifest()
            
            self.status = DeviceStatus.COMPLETE
            self.progress = 100.0
            logger.info("Device creation completed successfully")
            return True
            
        except Exception as e:
            self.status = DeviceStatus.ERROR
            self.errors.append(str(e))
            logger.error(f"Device creation failed: {e}", exc_info=True)
            return False
        finally:
            self._cleanup()
    
    def _verify_device(self) -> bool:
        """Verify target device is suitable for partitioning"""
        try:
            self.current_operation = "Verifying device availability"
            
            # Check if device exists
            if not os.path.exists(self.config.device_path):
                self.errors.append(f"Device not found: {self.config.device_path}")
                return False
            
            # Get device size
            device_size = self._get_device_size()
            required_size = (self.config.cdrom_size_mb + self.config.usb_size_mb) * 1024 * 1024
            
            if device_size < required_size:
                self.errors.append(f"Device too small. Required: {required_size/(1024**3):.1f}GB, Available: {device_size/(1024**3):.1f}GB")
                return False
            
            # Confirm device is removable (safety check)
            if not self._is_removable_device():
                response = input(f"WARNING: {self.config.device_path} may not be a removable device. Continue? (yes/no): ")
                if response.lower() != 'yes':
                    self.errors.append("User cancelled operation on non-removable device")
                    return False
            
            self.progress = 10.0
            return True
            
        except Exception as e:
            self.errors.append(f"Device verification failed: {e}")
            return False
    
    def _get_device_size(self) -> int:
        """Get device size in bytes"""
        if self.platform == "windows":
            import win32file
            import win32api
            
            handle = win32file.CreateFile(
                self.config.device_path,
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            
            try:
                info = win32file.GetDriveGeometry(handle)
                size = info[0] * info[1] * info[2] * info[3]
                return size
            finally:
                win32file.CloseHandle(handle)
                
        elif self.platform == "darwin":
            result = subprocess.run(
                ["diskutil", "info", self.config.device_path],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'Total Size' in line:
                    # Parse size from format: "Total Size: 8.0 GB (8012390400 Bytes)"
                    size_str = line.split('(')[1].split(' ')[0]
                    return int(size_str)
        else:
            with open(self.config.device_path, 'rb') as f:
                f.seek(0, 2)  # Seek to end
                return f.tell()
        
        return 0
    
    def _is_removable_device(self) -> bool:
        """Check if device is removable (USB/external)"""
        if self.platform == "windows":
            import win32file
            drive_type = win32file.GetDriveType(self.config.device_path[:3])
            return drive_type == win32file.DRIVE_REMOVABLE
            
        elif self.platform == "darwin":
            result = subprocess.run(
                ["diskutil", "info", self.config.device_path],
                capture_output=True,
                text=True
            )
            return "Removable Media: Yes" in result.stdout
            
        else:
            # Linux: Check if device is USB
            device_name = Path(self.config.device_path).name
            removable_path = f"/sys/block/{device_name}/removable"
            if os.path.exists(removable_path):
                with open(removable_path, 'r') as f:
                    return f.read().strip() == "1"
        
        return False
    
    def _create_partitions(self) -> bool:
        """Create CD-ROM and USB partitions on device"""
        try:
            self.current_operation = "Creating partition layout"
            logger.info(f"Creating partitions: CD-ROM={self.config.cdrom_size_mb}MB, USB={self.config.usb_size_mb}MB")
            
            if self.platform == "windows":
                return self._create_partitions_windows()
            elif self.platform == "darwin":
                return self._create_partitions_macos()
            else:
                return self._create_partitions_linux()
                
        except Exception as e:
            self.errors.append(f"Partition creation failed: {e}")
            return False
    
    def _create_partitions_windows(self) -> bool:
        """Create partitions on Windows using diskpart"""
        script_content = f"""
select disk {self._get_disk_number()}
clean
convert mbr
create partition primary size={self.config.cdrom_size_mb}
format fs=cdfs label="{self.config.volume_label}" quick
assign letter=X
create partition primary
format fs=exfat label="{self.config.volume_label}_DATA" quick
assign letter=Y
exit
"""
        
        script_path = self.temp_dir / "partition_script.txt"
        script_path.write_text(script_content)
        
        result = subprocess.run(
            ["diskpart", "/s", str(script_path)],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode != 0:
            self.errors.append(f"Diskpart failed: {result.stderr}")
            return False
        
        self.progress = 30.0
        return True
    
    def _create_partitions_macos(self) -> bool:
        """Create partitions on macOS using diskutil"""
        # Unmount device first
        subprocess.run(["diskutil", "unmountDisk", self.config.device_path])
        
        # Create partition scheme
        result = subprocess.run([
            "diskutil", "partitionDisk", self.config.device_path,
            "2", "MBR",
            "MS-DOS", self.config.volume_label, f"{self.config.cdrom_size_mb}M",
            "ExFAT", f"{self.config.volume_label}_DATA", f"{self.config.usb_size_mb}M"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            self.errors.append(f"Diskutil failed: {result.stderr}")
            return False
        
        self.progress = 30.0
        return True
    
    def _create_partitions_linux(self) -> bool:
        """Create partitions on Linux using parted"""
        commands = [
            f"parted {self.config.device_path} mklabel msdos",
            f"parted {self.config.device_path} mkpart primary fat32 1MiB {self.config.cdrom_size_mb}MiB",
            f"parted {self.config.device_path} mkpart primary fat32 {self.config.cdrom_size_mb}MiB 100%",
            f"mkfs.vfat -n {self.config.volume_label} {self.config.device_path}1",
            f"mkfs.exfat -n {self.config.volume_label}_DATA {self.config.device_path}2"
        ]
        
        for cmd in commands:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"Command failed: {cmd}\nError: {result.stderr}")
                return False
        
        self.progress = 30.0
        return True
    
    def _get_disk_number(self) -> int:
        """Get disk number for Windows diskpart"""
        if self.platform != "windows":
            return -1
        
        # Extract disk number from path like \\.\PhysicalDrive2
        import re
        match = re.search(r'PhysicalDrive(\d+)', self.config.device_path)
        if match:
            return int(match.group(1))
        return -1
    
    def _copy_system_files(self) -> bool:
        """Copy system files to CD-ROM partition"""
        try:
            self.current_operation = "Copying system files"
            logger.info("Beginning system file copy to CD-ROM partition")
            
            # Mount CD-ROM partition
            cdrom_mount = self._mount_partition(0)  # First partition
            if not cdrom_mount:
                return False
            
            # Define source structure
            source_files = {
                "launchers": ["windows_launcher.exe", "macos_launcher.app"],
                "models": self.config.model_variants,
                "ollama": ["ollama_windows.exe", "ollama_macos"],
                "modelfiles": ["Sunflower_AI_Kids.modelfile", "Sunflower_AI_Educator.modelfile"],
                "interface": ["gui.py", "cli.py", "web_interface.py"],
                "documentation": ["user_guide.pdf", "quick_start.pdf"],
                "security": ["manifest.json", "checksums.sha256"]
            }
            
            total_files = sum(len(files) for files in source_files.values())
            files_copied = 0
            
            for category, files in source_files.items():
                category_dir = Path(cdrom_mount) / category
                category_dir.mkdir(parents=True, exist_ok=True)
                
                for file_name in files:
                    source_path = self.source_dir / category / file_name
                    dest_path = category_dir / file_name
                    
                    if source_path.exists():
                        # Copy with progress tracking
                        self._copy_with_progress(source_path, dest_path)
                        
                        # Calculate checksum
                        checksum = self._calculate_checksum(dest_path)
                        self.checksums[str(dest_path.relative_to(cdrom_mount))] = checksum
                        
                        files_copied += 1
                        self.progress = 30 + (40 * files_copied / total_files)
                    else:
                        logger.warning(f"Source file not found: {source_path}")
            
            # Write device configuration
            config_path = Path(cdrom_mount) / "device_config.json"
            config_data = {
                "device_id": self.config.device_id,
                "creation_date": self.config.creation_date,
                "platform": self.config.platform_type,
                "models": self.config.model_variants,
                "version": "6.2"
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Create autorun for Windows
            if self.platform == "windows":
                autorun_path = Path(cdrom_mount) / "autorun.inf"
                autorun_content = f"""[autorun]
open=launchers\\windows_launcher.exe
icon=sunflower.ico
label={self.config.volume_label}
"""
                autorun_path.write_text(autorun_content)
            
            # Unmount partition
            self._unmount_partition(cdrom_mount)
            
            self.progress = 70.0
            return True
            
        except Exception as e:
            self.errors.append(f"System file copy failed: {e}")
            return False
    
    def _copy_with_progress(self, source: Path, dest: Path, chunk_size: int = 1024*1024) -> None:
        """Copy file with progress tracking"""
        file_size = source.stat().st_size
        copied = 0
        
        with open(source, 'rb') as src, open(dest, 'wb') as dst:
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                dst.write(chunk)
                copied += len(chunk)
                
                # Update operation status
                percent = (copied / file_size) * 100
                self.current_operation = f"Copying {source.name}: {percent:.1f}%"
    
    def _configure_usb_partition(self) -> bool:
        """Configure writable USB partition with initial structure"""
        try:
            self.current_operation = "Configuring USB partition"
            logger.info("Setting up USB partition structure")
            
            # Mount USB partition
            usb_mount = self._mount_partition(1)  # Second partition
            if not usb_mount:
                return False
            
            # Create directory structure
            directories = [
                "family_profiles",
                "conversation_logs",
                "learning_progress",
                "parent_dashboard",
                "runtime_config",
                "backup"
            ]
            
            for dir_name in directories:
                dir_path = Path(usb_mount) / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create initial configuration
            runtime_config = {
                "device_id": self.config.device_id,
                "first_run": True,
                "encryption_enabled": True,
                "encryption_key_hash": hashlib.sha256(self.config.encryption_key.encode()).hexdigest(),
                "created": self.config.creation_date,
                "last_accessed": None,
                "family_count": 0
            }
            
            config_path = Path(usb_mount) / "runtime_config" / "config.json"
            with open(config_path, 'w') as f:
                json.dump(runtime_config, f, indent=2)
            
            # Create README for users
            readme_content = """
SUNFLOWER AI PROFESSIONAL SYSTEM - USER DATA PARTITION
======================================================

This partition stores your family's data and learning progress.

Directory Structure:
- family_profiles/     Your family member profiles
- conversation_logs/   Conversation history for each child
- learning_progress/   Educational progress tracking
- parent_dashboard/    Parent monitoring and reports
- runtime_config/      System configuration
- backup/             Backup of important data

IMPORTANT: Do not modify files in runtime_config directory.
For support, consult the user guide on the system partition.

Device ID: {device_id}
Created: {date}
""".format(device_id=self.config.device_id, date=self.config.creation_date)
            
            readme_path = Path(usb_mount) / "README.txt"
            readme_path.write_text(readme_content)
            
            # Unmount partition
            self._unmount_partition(usb_mount)
            
            self.progress = 85.0
            return True
            
        except Exception as e:
            self.errors.append(f"USB partition configuration failed: {e}")
            return False
    
    def _mount_partition(self, partition_index: int) -> Optional[str]:
        """Mount a partition and return mount point"""
        try:
            if self.platform == "windows":
                # Windows partitions are already assigned drive letters
                if partition_index == 0:
                    return "X:\\"
                else:
                    return "Y:\\"
                    
            elif self.platform == "darwin":
                # macOS: Find partition device
                device = f"{self.config.device_path}s{partition_index + 1}"
                mount_point = f"/Volumes/SUNFLOWER_{partition_index}"
                
                subprocess.run(["diskutil", "mount", device])
                return mount_point
                
            else:
                # Linux
                device = f"{self.config.device_path}{partition_index + 1}"
                mount_point = self.temp_dir / f"mount_{partition_index}"
                mount_point.mkdir(exist_ok=True)
                
                result = subprocess.run(
                    ["mount", device, str(mount_point)],
                    capture_output=True
                )
                
                if result.returncode == 0:
                    return str(mount_point)
                    
        except Exception as e:
            self.errors.append(f"Failed to mount partition {partition_index}: {e}")
            
        return None
    
    def _unmount_partition(self, mount_point: str) -> bool:
        """Unmount a partition"""
        try:
            if self.platform == "windows":
                # Windows doesn't need explicit unmounting for removable drives
                return True
                
            elif self.platform == "darwin":
                subprocess.run(["diskutil", "unmount", mount_point])
                return True
                
            else:
                subprocess.run(["umount", mount_point])
                return True
                
        except Exception as e:
            logger.warning(f"Failed to unmount {mount_point}: {e}")
            return False
    
    def _verify_integrity(self) -> bool:
        """Verify device integrity and create final manifest"""
        try:
            self.current_operation = "Verifying device integrity"
            logger.info("Running integrity verification")
            
            # Mount both partitions
            cdrom_mount = self._mount_partition(0)
            usb_mount = self._mount_partition(1)
            
            if not cdrom_mount or not usb_mount:
                self.errors.append("Failed to mount partitions for verification")
                return False
            
            # Verify CD-ROM files
            verification_errors = []
            for rel_path, expected_checksum in self.checksums.items():
                file_path = Path(cdrom_mount) / rel_path
                if file_path.exists():
                    actual_checksum = self._calculate_checksum(file_path)
                    if actual_checksum != expected_checksum:
                        verification_errors.append(f"Checksum mismatch: {rel_path}")
                else:
                    verification_errors.append(f"Missing file: {rel_path}")
            
            # Verify USB structure
            required_dirs = ["family_profiles", "conversation_logs", "learning_progress"]
            for dir_name in required_dirs:
                if not (Path(usb_mount) / dir_name).exists():
                    verification_errors.append(f"Missing directory: {dir_name}")
            
            # Unmount partitions
            self._unmount_partition(cdrom_mount)
            self._unmount_partition(usb_mount)
            
            if verification_errors:
                self.errors.extend(verification_errors)
                return False
            
            self.progress = 95.0
            return True
            
        except Exception as e:
            self.errors.append(f"Integrity verification failed: {e}")
            return False
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _create_manifest(self) -> None:
        """Create device manifest with all metadata"""
        self.manifest = {
            "device_id": self.config.device_id,
            "creation_date": self.config.creation_date,
            "platform": self.config.platform_type,
            "version": "6.2",
            "partitions": {
                "cdrom": {
                    "size_mb": self.config.cdrom_size_mb,
                    "filesystem": "CDFS" if self.platform == "windows" else "ISO9660",
                    "label": self.config.volume_label
                },
                "usb": {
                    "size_mb": self.config.usb_size_mb,
                    "filesystem": "exFAT",
                    "label": f"{self.config.volume_label}_DATA"
                }
            },
            "models": self.config.model_variants,
            "checksums": self.checksums,
            "creation_log": {
                "errors": self.errors,
                "warnings": logger.handlers[0].baseFilename if logger.handlers else None
            }
        }
        
        # Save manifest
        manifest_path = self.temp_dir / f"manifest_{self.config.device_id}.json"
        with open(manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
        
        logger.info(f"Manifest saved to: {manifest_path}")
    
    def _cleanup(self) -> None:
        """Clean up temporary files and resources"""
        try:
            # Keep manifest and logs, remove other temp files
            for item in self.temp_dir.iterdir():
                if not item.name.startswith("manifest_") and not item.suffix == ".log":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get current status report"""
        return {
            "status": self.status.value,
            "progress": self.progress,
            "current_operation": self.current_operation,
            "errors": self.errors,
            "device_id": self.config.device_id if self.config else None
        }


def main():
    """Main entry point for device creation"""
    print("\n" + "="*60)
    print("SUNFLOWER AI PROFESSIONAL SYSTEM - DEVICE CREATOR")
    print("Version 6.2 - Partitioned Device Architecture")
    print("="*60 + "\n")
    
    # Check for admin/root privileges
    if platform.system() == "Windows":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("ERROR: Administrator privileges required.")
            print("Please run this script as Administrator.")
            sys.exit(1)
    elif os.geteuid() != 0:
        print("ERROR: Root privileges required.")
        print("Please run this script with sudo.")
        sys.exit(1)
    
    # Get device path
    print("Available devices:")
    if platform.system() == "Windows":
        subprocess.run("wmic diskdrive get Name,Size,Model", shell=True)
    elif platform.system() == "Darwin":
        subprocess.run(["diskutil", "list"])
    else:
        subprocess.run(["lsblk", "-o", "NAME,SIZE,MODEL"])
    
    print("\n" + "-"*40)
    device_path = input("Enter device path (e.g., \\\\.\\PhysicalDrive2 on Windows, /dev/disk2 on macOS): ").strip()
    
    if not device_path:
        print("ERROR: No device path provided")
        sys.exit(1)
    
    # Confirm operation
    print(f"\n{'WARNING':^40}")
    print("="*40)
    print(f"Device: {device_path}")
    print("This will ERASE ALL DATA on the device!")
    print("="*40)
    
    confirm = input("\nType 'YES' to continue: ").strip()
    if confirm != "YES":
        print("Operation cancelled.")
        sys.exit(0)
    
    # Create configuration
    config = DeviceConfiguration(
        device_path=device_path,
        cdrom_size_mb=4096,
        usb_size_mb=1024,
        volume_label="SUNFLOWER_AI"
    )
    
    # Create device
    creator = PartitionedDeviceCreator(config)
    
    # Progress monitoring thread
    def monitor_progress():
        while creator.status not in [DeviceStatus.COMPLETE, DeviceStatus.ERROR]:
            status = creator.get_status_report()
            print(f"\rProgress: {status['progress']:.1f}% - {status['current_operation'][:50]:<50}", end="")
            time.sleep(0.5)
    
    monitor_thread = threading.Thread(target=monitor_progress)
    monitor_thread.start()
    
    # Execute device creation
    success = creator.create_device()
    monitor_thread.join()
    
    print("\n" + "="*60)
    if success:
        print("SUCCESS: Device created successfully!")
        print(f"Device ID: {config.device_id}")
        print(f"Manifest: {creator.temp_dir}/manifest_{config.device_id}.json")
    else:
        print("ERROR: Device creation failed!")
        print("Errors:")
        for error in creator.errors:
            print(f"  - {error}")
    print("="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

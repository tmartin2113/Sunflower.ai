#!/usr/bin/env python3
"""
Sunflower AI Professional System - USB Device Creation
Creates the dual-partition USB device for Sunflower AI distribution
Version: 6.2.0 - Production Ready
"""

import os
import sys
import json
import time
import shutil
import hashlib
import platform
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import standardized path configuration
from config.path_config import PathConfiguration

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class USBDeviceCreator:
    """Creates Sunflower AI dual-partition USB devices"""
    
    def __init__(self, config: Dict):
        """Initialize USB device creator with configuration"""
        self.config = config
        self.platform = platform.system()
        self.source_dir = Path(__file__).parent.parent
        self.temp_dir = Path("/tmp/sunflower_usb_build") if self.platform != "Windows" else Path("C:/temp/sunflower_usb_build")
        self.errors = []
        self.progress = 0.0
        self.current_operation = ""
        
        # Initialize path configuration
        self.path_config = PathConfiguration(auto_detect=False)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate the provided configuration"""
        required_fields = ['device_path', 'device_size_gb', 'batch_id']
        
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required configuration field: {field}")
        
        # Set defaults
        self.config.setdefault('cdrom_size_gb', 4)
        self.config.setdefault('usb_size_gb', 1)
        self.config.setdefault('device_id', self._generate_device_id())
        self.config.setdefault('encryption_key', self._generate_encryption_key())
        self.config.setdefault('creation_date', datetime.now().isoformat())
    
    def _generate_device_id(self) -> str:
        """Generate unique device identifier"""
        import uuid
        return f"SAI-{self.config['batch_id']}-{uuid.uuid4().hex[:8].upper()}"
    
    def _generate_encryption_key(self) -> str:
        """Generate device-specific encryption key"""
        import secrets
        return secrets.token_hex(32)
    
    def create_device(self) -> bool:
        """Main method to create the USB device"""
        try:
            logger.info(f"Starting USB device creation for batch {self.config['batch_id']}")
            
            # Step 1: Prepare temporary build directory
            self.current_operation = "Preparing build environment"
            self._prepare_build_environment()
            self.progress = 10.0
            
            # Step 2: Partition the device
            self.current_operation = "Creating partitions"
            if not self._create_partitions():
                return False
            self.progress = 25.0
            
            # Step 3: Format partitions
            self.current_operation = "Formatting partitions"
            if not self._format_partitions():
                return False
            self.progress = 40.0
            
            # Step 4: Copy system files to CD-ROM partition
            self.current_operation = "Installing system files"
            if not self._copy_system_files():
                return False
            self.progress = 70.0
            
            # Step 5: Configure USB partition
            self.current_operation = "Configuring user partition"
            if not self._configure_usb_partition():
                return False
            self.progress = 85.0
            
            # Step 6: Verify and finalize
            self.current_operation = "Verifying device"
            if not self._verify_device():
                return False
            self.progress = 100.0
            
            logger.info("USB device created successfully")
            return True
            
        except Exception as e:
            self.errors.append(str(e))
            logger.error(f"Device creation failed: {e}")
            return False
    
    def _prepare_build_environment(self):
        """Prepare temporary build directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for staging
        (self.temp_dir / "cdrom").mkdir()
        (self.temp_dir / "usb").mkdir()
        
        logger.info(f"Build environment prepared at {self.temp_dir}")
    
    def _create_partitions(self) -> bool:
        """Create dual partitions on the USB device"""
        try:
            if self.platform == "Windows":
                return self._create_partitions_windows()
            elif self.platform == "Darwin":
                return self._create_partitions_macos()
            else:
                return self._create_partitions_linux()
                
        except Exception as e:
            self.errors.append(f"Partition creation failed: {e}")
            return False
    
    def _create_partitions_windows(self) -> bool:
        """Create partitions on Windows using diskpart"""
        diskpart_script = f"""
select disk {self._get_disk_number()}
clean
create partition primary size={self.config['cdrom_size_gb'] * 1024}
format fs=ntfs label="{self.path_config.CDROM_PARTITION_NAME}" quick
assign
create partition primary
format fs=fat32 label="{self.path_config.USB_PARTITION_NAME}" quick
assign
exit
"""
        
        script_path = self.temp_dir / "diskpart_script.txt"
        script_path.write_text(diskpart_script)
        
        result = subprocess.run(
            ["diskpart", "/s", str(script_path)],
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
    
    def _create_partitions_macos(self) -> bool:
        """Create partitions on macOS using diskutil"""
        device = self.config['device_path']
        
        # Unmount device first
        subprocess.run(["diskutil", "unmountDisk", device])
        
        # Create partitions
        cdrom_size = f"{self.config['cdrom_size_gb']}G"
        
        result = subprocess.run([
            "diskutil", "partitionDisk", device, "2",
            "MBR",
            "FAT32", self.path_config.CDROM_PARTITION_NAME, cdrom_size,
            "FAT32", self.path_config.USB_PARTITION_NAME, "0"
        ], capture_output=True)
        
        return result.returncode == 0
    
    def _create_partitions_linux(self) -> bool:
        """Create partitions on Linux using parted"""
        device = self.config['device_path']
        
        commands = [
            ["parted", "-s", device, "mklabel", "msdos"],
            ["parted", "-s", device, "mkpart", "primary", "fat32", "1MiB", f"{self.config['cdrom_size_gb']}GiB"],
            ["parted", "-s", device, "mkpart", "primary", "fat32", f"{self.config['cdrom_size_gb']}GiB", "100%"],
            ["parted", "-s", device, "set", "1", "hidden", "on"]
        ]
        
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                return False
        
        return True
    
    def _format_partitions(self) -> bool:
        """Format the created partitions"""
        try:
            if self.platform == "Windows":
                # Windows formatting is done in diskpart script
                return True
            elif self.platform == "Darwin":
                # macOS formatting is done in diskutil command
                return True
            else:
                # Linux formatting
                device = self.config['device_path']
                
                # Format CD-ROM partition as FAT32
                result1 = subprocess.run(
                    ["mkfs.vfat", "-n", self.path_config.CDROM_PARTITION_NAME, f"{device}1"],
                    capture_output=True
                )
                
                # Format USB partition as FAT32
                result2 = subprocess.run(
                    ["mkfs.vfat", "-n", self.path_config.USB_PARTITION_NAME, f"{device}2"],
                    capture_output=True
                )
                
                return result1.returncode == 0 and result2.returncode == 0
                
        except Exception as e:
            self.errors.append(f"Formatting failed: {e}")
            return False
    
    def _get_disk_number(self) -> int:
        """Get disk number for Windows diskpart"""
        if self.platform != "Windows":
            return -1
        
        # Extract disk number from path like \\.\PhysicalDrive2
        import re
        match = re.search(r'PhysicalDrive(\d+)', self.config['device_path'])
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
            
            # Create CD-ROM marker file
            marker_file = Path(cdrom_mount) / self.path_config.CDROM_MARKER_FILE
            marker_content = {
                "type": self.path_config.CDROM_MARKER_CONTENT,
                "batch_id": self.config['batch_id'],
                "device_id": self.config['device_id'],
                "created": self.config['creation_date'],
                "version": "6.2.0"
            }
            with open(marker_file, 'w') as f:
                json.dump(marker_content, f, indent=2)
            
            # Copy directory structure based on PathConfiguration
            for dir_key, dir_name in self.path_config.CDROM_STRUCTURE.items():
                source_path = self.source_dir / dir_name
                if source_path.exists():
                    dest_path = Path(cdrom_mount) / dir_name
                    
                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                    
                    logger.info(f"Copied {dir_key}: {source_path} -> {dest_path}")
            
            # Copy launcher at root
            launcher_source = self.source_dir / "UNIVERSAL_LAUNCHER.py"
            if launcher_source.exists():
                shutil.copy2(launcher_source, Path(cdrom_mount) / "UNIVERSAL_LAUNCHER.py")
            
            # Copy configuration directory
            config_source = self.source_dir / "config"
            if config_source.exists():
                shutil.copytree(config_source, Path(cdrom_mount) / "config", dirs_exist_ok=True)
            
            # Unmount partition
            self._unmount_partition(cdrom_mount)
            
            logger.info("System files copied successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"System file copy failed: {e}")
            logger.error(f"Failed to copy system files: {e}")
            return False
    
    def _configure_usb_partition(self) -> bool:
        """Configure writable USB partition with initial structure"""
        try:
            self.current_operation = "Configuring USB partition"
            logger.info("Setting up USB partition structure")
            
            # Mount USB partition
            usb_mount = self._mount_partition(1)  # Second partition
            if not usb_mount:
                return False
            
            # Create USB marker file
            marker_file = Path(usb_mount) / self.path_config.USB_MARKER_FILE
            marker_content = {
                "type": self.path_config.USB_MARKER_CONTENT,
                "batch_id": self.config['batch_id'],
                "device_id": self.config['device_id'],
                "created": self.config['creation_date'],
                "version": "6.2.0",
                "writable": True
            }
            with open(marker_file, 'w') as f:
                json.dump(marker_content, f, indent=2)
            
            # Create directory structure based on PathConfiguration
            for dir_key, dir_name in self.path_config.USB_STRUCTURE.items():
                dir_path = Path(usb_mount) / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created USB directory: {dir_path}")
            
            # Create initial configuration
            config_dir = Path(usb_mount) / self.path_config.USB_STRUCTURE['config']
            config_dir.mkdir(parents=True, exist_ok=True)
            
            runtime_config = {
                "device_id": self.config['device_id'],
                "first_run": True,
                "encryption_enabled": True,
                "encryption_key_hash": hashlib.sha256(self.config['encryption_key'].encode()).hexdigest(),
                "created": self.config['creation_date'],
                "last_accessed": None,
                "family_count": 0
            }
            
            config_path = config_dir / "runtime_config.json"
            with open(config_path, 'w') as f:
                json.dump(runtime_config, f, indent=2)
            
            # Create README for users
            readme_content = f"""
SUNFLOWER AI PROFESSIONAL SYSTEM - USER DATA PARTITION
======================================================

This partition stores your family's data and learning progress.

Directory Structure:
{chr(10).join(f"- {dir_name:<20} {self._get_dir_description(key)}" for key, dir_name in self.path_config.USB_STRUCTURE.items())}

IMPORTANT: Do not modify files in .config or .security directories.
For support, consult the user guide on the system partition.

Device ID: {self.config['device_id']}
Created: {self.config['creation_date']}
"""
            
            readme_path = Path(usb_mount) / "README.txt"
            readme_path.write_text(readme_content)
            
            # Unmount partition
            self._unmount_partition(usb_mount)
            
            logger.info("USB partition configured successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"USB partition configuration failed: {e}")
            logger.error(f"Failed to configure USB partition: {e}")
            return False
    
    def _get_dir_description(self, dir_key: str) -> str:
        """Get description for directory"""
        descriptions = {
            'profiles': 'Family and child profiles',
            'conversations': 'Conversation history',
            'sessions': 'Learning sessions',
            'logs': 'System and safety logs',
            'safety': 'Safety incident data',
            'progress': 'Learning progress',
            'backups': 'Data backups',
            'cache': 'Temporary cache files',
            'config': 'Configuration files',
            'security': 'Security data'
        }
        return descriptions.get(dir_key, 'System directory')
    
    def _mount_partition(self, partition_index: int) -> Optional[str]:
        """Mount a partition and return mount point"""
        try:
            if self.platform == "Windows":
                # Windows partitions are already assigned drive letters
                # We need to find them
                import win32api
                drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                
                # Look for our partition by marker file
                marker_file = self.path_config.CDROM_MARKER_FILE if partition_index == 0 else self.path_config.USB_MARKER_FILE
                
                for drive in drives:
                    marker_path = Path(drive) / marker_file
                    if marker_path.exists():
                        return drive
                
                return None
                    
            elif self.platform == "Darwin":
                # macOS: Find partition device
                device = f"{self.config['device_path']}s{partition_index + 1}"
                
                # Mount the partition
                result = subprocess.run(["diskutil", "mount", device], capture_output=True)
                
                if result.returncode == 0:
                    # Find mount point
                    result = subprocess.run(["diskutil", "info", device], capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if "Mount Point:" in line:
                            mount_point = line.split(":")[-1].strip()
                            return mount_point
                
            else:
                # Linux
                device = f"{self.config['device_path']}{partition_index + 1}"
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
    
    def _unmount_partition(self, mount_point: str):
        """Unmount a partition"""
        try:
            if self.platform == "Windows":
                # Windows doesn't need explicit unmounting for removable drives
                pass
            elif self.platform == "Darwin":
                subprocess.run(["diskutil", "unmount", mount_point])
            else:
                subprocess.run(["umount", mount_point])
        except Exception as e:
            logger.warning(f"Failed to unmount {mount_point}: {e}")
    
    def _verify_device(self) -> bool:
        """Verify the created device"""
        try:
            logger.info("Verifying device integrity")
            
            # Mount both partitions
            cdrom_mount = self._mount_partition(0)
            usb_mount = self._mount_partition(1)
            
            if not cdrom_mount or not usb_mount:
                self.errors.append("Failed to mount partitions for verification")
                return False
            
            # Verify CD-ROM partition
            cdrom_marker = Path(cdrom_mount) / self.path_config.CDROM_MARKER_FILE
            if not cdrom_marker.exists():
                self.errors.append("CD-ROM marker file not found")
                return False
            
            # Verify USB partition
            usb_marker = Path(usb_mount) / self.path_config.USB_MARKER_FILE
            if not usb_marker.exists():
                self.errors.append("USB marker file not found")
                return False
            
            # Verify directory structures
            for dir_name in self.path_config.USB_STRUCTURE.values():
                dir_path = Path(usb_mount) / dir_name
                if not dir_path.exists():
                    self.errors.append(f"Missing USB directory: {dir_name}")
                    return False
            
            # Unmount partitions
            self._unmount_partition(cdrom_mount)
            self._unmount_partition(usb_mount)
            
            logger.info("Device verification successful")
            return True
            
        except Exception as e:
            self.errors.append(f"Verification failed: {e}")
            return False
    
    def get_progress(self) -> Tuple[float, str]:
        """Get current progress and operation"""
        return self.progress, self.current_operation
    
    def get_errors(self) -> List[str]:
        """Get list of errors encountered"""
        return self.errors


def main():
    """Main entry point for USB device creation"""
    parser = argparse.ArgumentParser(description='Create Sunflower AI USB Device')
    parser.add_argument('--device', required=True, help='Device path (e.g., /dev/sdb or \\\\.\\PhysicalDrive2)')
    parser.add_argument('--batch-id', required=True, help='Batch identifier')
    parser.add_argument('--size', type=int, default=16, help='Device size in GB')
    parser.add_argument('--cdrom-size', type=int, default=4, help='CD-ROM partition size in GB')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without writing')
    
    args = parser.parse_args()
    
    # Confirm with user
    print("⚠️  WARNING: This will completely erase the device!")
    print(f"Device: {args.device}")
    print(f"Total Size: {args.size} GB")
    print(f"CD-ROM Partition: {args.cdrom_size} GB")
    print(f"USB Partition: {args.size - args.cdrom_size} GB")
    
    if not args.dry_run:
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Operation cancelled")
            return
    
    # Create configuration
    config = {
        'device_path': args.device,
        'device_size_gb': args.size,
        'cdrom_size_gb': args.cdrom_size,
        'usb_size_gb': args.size - args.cdrom_size,
        'batch_id': args.batch_id
    }
    
    # Create device
    creator = USBDeviceCreator(config)
    
    if args.dry_run:
        print("\nDry run mode - no actual changes will be made")
        print("Configuration:", json.dumps(config, indent=2))
    else:
        success = creator.create_device()
        
        if success:
            print("✅ USB device created successfully!")
        else:
            print("❌ Device creation failed!")
            print("Errors:")
            for error in creator.get_errors():
                print(f"  - {error}")
            sys.exit(1)


if __name__ == "__main__":
    main()

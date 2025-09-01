#!/usr/bin/env python3
"""
Sunflower AI Professional System - USB Partition Preparation
Prepares writable FAT32 partition for user data and profiles.

Copyright (c) 2025 Sunflower AI Corporation
Version: 6.2.0
"""

import os
import sys
import json
import shutil
import platform
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import ctypes
import struct

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from __init__ import (
    DeviceSpecification,
    PartitionType,
    ProductionStage,
    PartitionError,
    calculate_checksum,
    logger
)

class USBPartitionManager:
    """Manages creation and preparation of USB writable partition."""
    
    def __init__(self):
        """Initialize USB partition manager."""
        self.system_platform = platform.system().lower()
        self.template_path = Path(__file__).parent.parent / 'templates' / 'usb_partition'
        
        # Platform-specific disk management tools
        self.disk_tools = self._detect_disk_tools()
        
        # Encryption key for family data (in production, use hardware-derived key)
        self.encryption_key = os.environ.get('SUNFLOWER_ENCRYPTION_KEY', 'default_encryption_key_2025')
    
    def _detect_disk_tools(self) -> Dict[str, Path]:
        """Detect available disk management tools."""
        tools = {}
        
        if self.system_platform == 'darwin':  # macOS
            diskutil = shutil.which('diskutil')
            if diskutil:
                tools['diskutil'] = Path(diskutil)
                logger.info(f"Found diskutil at {diskutil}")
            
            newfs_msdos = shutil.which('newfs_msdos')
            if newfs_msdos:
                tools['newfs_msdos'] = Path(newfs_msdos)
                logger.info(f"Found newfs_msdos at {newfs_msdos}")
        
        elif self.system_platform == 'windows':
            # Windows uses diskpart and format commands
            diskpart = Path('C:/Windows/System32/diskpart.exe')
            if diskpart.exists():
                tools['diskpart'] = diskpart
                logger.info(f"Found diskpart at {diskpart}")
            
            format_cmd = Path('C:/Windows/System32/format.com')
            if format_cmd.exists():
                tools['format'] = format_cmd
                logger.info(f"Found format at {format_cmd}")
        
        else:  # Linux
            for tool_name in ['fdisk', 'parted', 'mkfs.vfat']:
                tool_path = shutil.which(tool_name)
                if tool_path:
                    tools[tool_name] = Path(tool_path)
                    logger.info(f"Found {tool_name} at {tool_path}")
        
        if not tools:
            logger.warning("Limited disk tools found. Some operations may fail.")
        
        return tools
    
    def prepare_partition_template(self, device_spec: DeviceSpecification) -> Path:
        """
        Prepare template directory structure for USB partition.
        
        Args:
            device_spec: Device specification
            
        Returns:
            Path to prepared template directory
        """
        logger.info(f"Preparing USB partition template for device {device_spec.device_id}")
        
        # Create template directory
        template_dir = Path(f"/tmp/sunflower_usb_{device_spec.device_id}")
        if template_dir.exists():
            shutil.rmtree(template_dir)
        template_dir.mkdir(parents=True)
        
        try:
            # Create directory structure
            self._create_directory_structure(template_dir)
            
            # Initialize configuration files
            self._initialize_configuration(template_dir, device_spec)
            
            # Create encryption keys
            self._setup_encryption(template_dir, device_spec)
            
            # Create placeholder files
            self._create_placeholder_files(template_dir)
            
            # Set permissions (platform-specific)
            self._set_permissions(template_dir)
            
            return template_dir
            
        except Exception as e:
            # Clean up on error
            if template_dir.exists():
                shutil.rmtree(template_dir, ignore_errors=True)
            raise PartitionError(
                f"Failed to prepare partition template: {str(e)}",
                ProductionStage.PARTITION_CREATION,
                device_spec.device_id
            )
    
    def _create_directory_structure(self, template_dir: Path):
        """Create standard directory structure for USB partition."""
        directories = [
            'profiles',           # Family profiles
            'profiles/.system',   # System profile data
            'conversations',      # Conversation histories
            'progress',          # Learning progress tracking
            'logs',              # Session logs
            'backups',           # Profile backups
            'temp',              # Temporary files
            '.config'            # Hidden configuration
        ]
        
        for dir_name in directories:
            dir_path = template_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
        
        # Create .sunflower_device marker file
        marker_file = template_dir / '.sunflower_device'
        with open(marker_file, 'w') as f:
            f.write("SUNFLOWER AI PROFESSIONAL SYSTEM\n")
            f.write("Version: 6.2.0\n")
            f.write(f"Created: {datetime.now().isoformat()}\n")
        
        logger.info("Created USB partition directory structure")
    
    def _initialize_configuration(self, template_dir: Path, device_spec: DeviceSpecification):
        """Initialize configuration files for USB partition."""
        config_dir = template_dir / '.config'
        
        # Partition configuration
        partition_config = {
            'version': '6.2.0',
            'device_id': device_spec.device_id,
            'batch_id': device_spec.batch_id,
            'partition_type': 'usb_writable',
            'filesystem': 'FAT32',
            'encryption': {
                'enabled': True,
                'algorithm': 'AES-256-CBC',
                'key_derivation': 'PBKDF2'
            },
            'capacity': {
                'total_mb': device_spec.usb_size_mb,
                'reserved_mb': 50,  # Reserved for system use
                'available_mb': device_spec.usb_size_mb - 50
            },
            'limits': {
                'max_profiles': 10,
                'max_conversations_per_profile': 1000,
                'max_backup_versions': 3
            },
            'initialized': datetime.now().isoformat()
        }
        
        config_path = config_dir / 'partition.json'
        with open(config_path, 'w') as f:
            json.dump(partition_config, f, indent=2)
        
        # Profile template
        profile_template = {
            'version': '1.0',
            'profile_id': '',
            'child_name': '',
            'age': 0,
            'grade_level': '',
            'created': '',
            'last_accessed': '',
            'parent_pin_hash': '',
            'preferences': {
                'difficulty_level': 'auto',
                'subjects': ['science', 'technology', 'engineering', 'mathematics'],
                'learning_style': 'interactive',
                'session_duration_minutes': 30
            },
            'restrictions': {
                'content_filter': 'strict',
                'age_appropriate': True,
                'require_parent_review': False
            },
            'progress': {
                'total_sessions': 0,
                'total_minutes': 0,
                'topics_explored': [],
                'achievements': []
            }
        }
        
        template_path = config_dir / 'profile_template.json'
        with open(template_path, 'w') as f:
            json.dump(profile_template, f, indent=2)
        
        logger.info("Initialized USB partition configuration")
    
    def _setup_encryption(self, template_dir: Path, device_spec: DeviceSpecification):
        """Set up encryption for sensitive data."""
        config_dir = template_dir / '.config'
        
        # Generate device-specific salt
        salt = os.urandom(32)
        salt_hex = salt.hex()
        
        # Store salt (in production, this would be encrypted with hardware key)
        salt_file = config_dir / '.salt'
        with open(salt_file, 'wb') as f:
            f.write(salt)
        
        # Create key derivation configuration
        kdf_config = {
            'algorithm': 'PBKDF2',
            'hash_function': 'SHA256',
            'iterations': 100000,
            'salt': salt_hex,
            'key_length': 32
        }
        
        kdf_path = config_dir / 'kdf.json'
        with open(kdf_path, 'w') as f:
            json.dump(kdf_config, f, indent=2)
        
        # Initialize encryption metadata
        encryption_meta = {
            'version': '1.0',
            'device_id': device_spec.device_id,
            'initialized': datetime.now().isoformat(),
            'algorithm': 'AES-256-CBC',
            'mode': 'CBC',
            'padding': 'PKCS7',
            'files_encrypted': []
        }
        
        meta_path = config_dir / 'encryption.json'
        with open(meta_path, 'w') as f:
            json.dump(encryption_meta, f, indent=2)
        
        logger.info("Set up encryption for USB partition")
    
    def _create_placeholder_files(self, template_dir: Path):
        """Create placeholder files for USB partition."""
        # Create README for users
        readme_content = """SUNFLOWER AI PROFESSIONAL SYSTEM - USER DATA PARTITION
======================================================

This partition contains your family's profiles and learning data.

IMPORTANT:
- Do not modify files in the .config directory
- Profile data is encrypted for privacy
- Backups are created automatically
- Maximum 10 family profiles supported

Directory Structure:
- profiles/       : Family member profiles
- conversations/  : Chat histories (encrypted)
- progress/       : Learning progress tracking
- logs/          : Session logs for parent review
- backups/       : Automatic profile backups

For support, refer to the documentation on the CD-ROM partition.

Version: 6.2.0
© 2025 Sunflower AI Corporation
"""
        
        readme_path = template_dir / 'README.txt'
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        # Create empty database for quick profile lookup
        db_path = template_dir / 'profiles' / '.system' / 'profiles.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Simple JSON database (in production, use SQLite)
        profile_db = {
            'version': '1.0',
            'profiles': [],
            'last_updated': datetime.now().isoformat()
        }
        
        with open(db_path, 'w') as f:
            json.dump(profile_db, f, indent=2)
        
        logger.info("Created placeholder files")
    
    def _set_permissions(self, template_dir: Path):
        """Set appropriate permissions for partition contents."""
        if self.system_platform == 'windows':
            # Windows-specific permissions
            try:
                import win32security
                import win32api
                import ntsecuritycon as con
                
                # Set hidden attribute for .config directory
                config_dir = str(template_dir / '.config')
                win32api.SetFileAttributes(config_dir, win32api.FILE_ATTRIBUTE_HIDDEN)
                
                logger.info("Set Windows permissions")
            except ImportError:
                logger.warning("pywin32 not available, skipping Windows permissions")
        
        else:  # Unix-like systems
            # Set Unix permissions
            import stat
            
            # Make .config directory less visible
            config_dir = template_dir / '.config'
            os.chmod(config_dir, stat.S_IRWXU)  # 700 - owner only
            
            # Set appropriate permissions for other directories
            for dir_path in template_dir.iterdir():
                if dir_path.is_dir() and not dir_path.name.startswith('.'):
                    os.chmod(dir_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)  # 750
            
            logger.info("Set Unix permissions")
    
    def format_partition(self, device_path: str, size_mb: int) -> bool:
        """
        Format partition as FAT32.
        
        Args:
            device_path: Path to device partition
            size_mb: Size in megabytes
            
        Returns:
            True if successful
        """
        logger.info(f"Formatting partition {device_path} as FAT32 ({size_mb}MB)")
        
        if self.system_platform == 'darwin':
            return self._format_partition_macos(device_path, size_mb)
        elif self.system_platform == 'windows':
            return self._format_partition_windows(device_path, size_mb)
        else:
            return self._format_partition_linux(device_path, size_mb)
    
    def _format_partition_macos(self, device_path: str, size_mb: int) -> bool:
        """Format partition on macOS."""
        if 'diskutil' not in self.disk_tools:
            raise PartitionError(
                "diskutil not found",
                ProductionStage.PARTITION_CREATION
            )
        
        # Unmount if mounted
        subprocess.run(
            [str(self.disk_tools['diskutil']), 'unmount', device_path],
            capture_output=True
        )
        
        # Format as FAT32
        cmd = [
            str(self.disk_tools['diskutil']),
            'eraseDisk',
            'FAT32',
            'SUNFLOWER_USB',
            'MBRFormat',
            device_path
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Format failed: {result.stderr}")
            return False
        
        logger.info("Partition formatted successfully")
        return True
    
    def _format_partition_windows(self, device_path: str, size_mb: int) -> bool:
        """Format partition on Windows."""
        if 'diskpart' not in self.disk_tools:
            raise PartitionError(
                "diskpart not found",
                ProductionStage.PARTITION_CREATION
            )
        
        # Create diskpart script
        script_content = f"""select disk {device_path}
clean
create partition primary size={size_mb}
select partition 1
active
format fs=fat32 label="SUNFLOWER_USB" quick
assign
exit
"""
        
        script_path = Path('temp_diskpart.txt')
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        try:
            # Run diskpart with script
            cmd = [str(self.disk_tools['diskpart']), '/s', str(script_path)]
            
            logger.info(f"Running diskpart with script")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode != 0:
                logger.error(f"Format failed: {result.stderr}")
                return False
            
            logger.info("Partition formatted successfully")
            return True
            
        finally:
            # Clean up script file
            if script_path.exists():
                script_path.unlink()
    
    def _format_partition_linux(self, device_path: str, size_mb: int) -> bool:
        """Format partition on Linux."""
        if 'mkfs.vfat' not in self.disk_tools:
            raise PartitionError(
                "mkfs.vfat not found",
                ProductionStage.PARTITION_CREATION
            )
        
        # Format as FAT32
        cmd = [
            str(self.disk_tools['mkfs.vfat']),
            '-F', '32',
            '-n', 'SUNFLOWER_USB',
            '-s', '1',  # Sectors per cluster
            device_path
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Format failed: {result.stderr}")
            return False
        
        logger.info("Partition formatted successfully")
        return True
    
    def copy_template_to_partition(self, template_dir: Path, mount_point: Path) -> bool:
        """
        Copy template files to mounted partition.
        
        Args:
            template_dir: Source template directory
            mount_point: Mounted partition path
            
        Returns:
            True if successful
        """
        logger.info(f"Copying template to partition at {mount_point}")
        
        try:
            # Copy all files and directories
            for item in template_dir.iterdir():
                src = template_dir / item.name
                dst = mount_point / item.name
                
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                
                logger.debug(f"Copied {item.name}")
            
            # Verify files were copied
            expected_files = list(template_dir.rglob('*'))
            copied_files = list(mount_point.rglob('*'))
            
            if len(copied_files) < len(expected_files):
                logger.warning(f"File count mismatch: expected {len(expected_files)}, got {len(copied_files)}")
                return False
            
            logger.info(f"Successfully copied {len(copied_files)} items to partition")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy template: {str(e)}")
            return False
    
    def verify_partition(self, mount_point: Path) -> bool:
        """
        Verify partition is correctly prepared.
        
        Args:
            mount_point: Mounted partition path
            
        Returns:
            True if verification passes
        """
        logger.info(f"Verifying partition at {mount_point}")
        
        # Check required directories exist
        required_dirs = [
            'profiles',
            'conversations',
            'progress',
            'logs',
            '.config'
        ]
        
        for dir_name in required_dirs:
            dir_path = mount_point / dir_name
            if not dir_path.exists():
                logger.error(f"Required directory missing: {dir_name}")
                return False
        
        # Check configuration files
        config_files = [
            '.config/partition.json',
            '.config/profile_template.json',
            '.config/encryption.json',
            '.config/kdf.json'
        ]
        
        for file_path in config_files:
            full_path = mount_point / file_path
            if not full_path.exists():
                logger.error(f"Required config file missing: {file_path}")
                return False
            
            # Verify JSON files are valid
            if file_path.endswith('.json'):
                try:
                    with open(full_path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON file: {file_path}")
                    return False
        
        # Check marker file
        marker_file = mount_point / '.sunflower_device'
        if not marker_file.exists():
            logger.error("Device marker file missing")
            return False
        
        logger.info("Partition verification passed")
        return True


def main():
    """Main entry point for USB partition preparation."""
    parser = argparse.ArgumentParser(
        description='Prepare USB partition for Sunflower AI device'
    )
    parser.add_argument(
        '--device-path',
        help='Device path (e.g., /dev/disk2s2 or E:)'
    )
    parser.add_argument(
        '--batch-id',
        required=True,
        help='Batch ID for production run'
    )
    parser.add_argument(
        '--device-id',
        required=True,
        help='Device ID'
    )
    parser.add_argument(
        '--size-mb',
        type=int,
        default=1024,
        help='Partition size in MB (default: 1024)'
    )
    parser.add_argument(
        '--format',
        action='store_true',
        help='Format the partition (WARNING: destroys data)'
    )
    parser.add_argument(
        '--template-only',
        action='store_true',
        help='Create template only, do not write to device'
    )
    parser.add_argument(
        '--mount-point',
        type=Path,
        help='Mount point for partition (if already mounted)'
    )
    
    args = parser.parse_args()
    
    # Create device specification
    device_spec = DeviceSpecification(
        device_id=args.device_id,
        batch_id=args.batch_id,
        capacity_gb=8,
        cdrom_size_mb=4096,
        usb_size_mb=args.size_mb,
        platform='universal',
        model_variant='auto',
        creation_timestamp=datetime.now(),
        validation_checksum='',
        hardware_token='',
        production_stage=ProductionStage.PARTITION_CREATION
    )
    
    # Initialize manager
    manager = USBPartitionManager()
    
    try:
        # Prepare template
        template_dir = manager.prepare_partition_template(device_spec)
        logger.info(f"Template prepared at: {template_dir}")
        
        if args.template_only:
            print(f"SUCCESS: Template created at {template_dir}")
            return 0
        
        # Format partition if requested
        if args.format and args.device_path:
            if not manager.format_partition(args.device_path, args.size_mb):
                raise PartitionError(
                    "Failed to format partition",
                    ProductionStage.PARTITION_CREATION,
                    device_spec.device_id
                )
        
        # Copy to partition if mount point provided
        if args.mount_point:
            if not manager.copy_template_to_partition(template_dir, args.mount_point):
                raise PartitionError(
                    "Failed to copy template to partition",
                    ProductionStage.FILE_DEPLOYMENT,
                    device_spec.device_id
                )
            
            # Verify partition
            if not manager.verify_partition(args.mount_point):
                raise PartitionError(
                    "Partition verification failed",
                    ProductionStage.VALIDATION,
                    device_spec.device_id
                )
            
            print(f"SUCCESS: USB partition prepared at {args.mount_point}")
        else:
            print(f"SUCCESS: Template prepared. Mount device and copy from {template_dir}")
        
        return 0
        
    except Exception as e:
        logger.error(f"USB partition preparation failed: {str(e)}")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1
        
    finally:
        # Clean up template if not needed
        if not args.template_only and template_dir.exists():
            shutil.rmtree(template_dir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

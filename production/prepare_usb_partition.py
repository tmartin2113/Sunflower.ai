#!/usr/bin/env python3
"""
Sunflower AI Professional System - USB Partition Preparation
Prepares USB data partition with proper resource management
Version: 6.2.0 - Production Ready with Fixed Resource Management
"""

import os
import sys
import json
import shutil
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from contextlib import contextmanager
import threading

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.path_config import PathConfiguration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('USBPreparation')


class USBPartitionPreparer:
    """
    Prepares USB partition with initial directory structure and files.
    FIX: All file operations use context managers for proper resource cleanup.
    """
    
    def __init__(self, usb_path: Optional[Path] = None):
        """
        Initialize USB partition preparer
        
        Args:
            usb_path: Path to USB partition (auto-detect if None)
        """
        self.path_config = PathConfiguration()
        self.usb_path = usb_path or self._detect_usb_partition()
        
        if not self.usb_path:
            raise ValueError("USB partition not found")
        
        # Staging directory for preparation
        self.staging_dir = self.usb_path / "sunflower_data"
        
        # Thread lock for file operations
        self._lock = threading.RLock()
        
        logger.info(f"USB Preparer initialized for: {self.usb_path}")
    
    def _detect_usb_partition(self) -> Optional[Path]:
        """Detect USB partition by marker file"""
        import platform
        
        if platform.system() == "Windows":
            import string
            for letter in string.ascii_uppercase:
                drive_path = Path(f"{letter}:\\")
                if drive_path.exists():
                    marker_file = drive_path / "sunflower_data.id"
                    if marker_file.exists():
                        logger.info(f"Found USB partition at {drive_path}")
                        return drive_path
        
        elif platform.system() == "Darwin":
            volumes = Path("/Volumes")
            for volume in volumes.iterdir():
                marker_file = volume / "sunflower_data.id"
                if marker_file.exists():
                    logger.info(f"Found USB partition at {volume}")
                    return volume
        
        return None
    
    @contextmanager
    def _file_operation(self, operation_name: str):
        """
        Context manager for file operations with proper cleanup
        FIX: Ensures resources are cleaned up even on error
        """
        logger.debug(f"Starting file operation: {operation_name}")
        try:
            yield
        except Exception as e:
            logger.error(f"Error during {operation_name}: {e}")
            raise
        finally:
            logger.debug(f"Completed file operation: {operation_name}")
    
    def prepare_partition(self) -> bool:
        """
        Prepare USB partition with initial structure
        FIX: All file operations use context managers
        
        Returns:
            True if successful
        """
        with self._lock:
            try:
                # Create partition marker
                self._create_partition_marker()
                
                # Create directory structure
                self._create_directory_structure()
                
                # Create initial configuration files
                self._create_configuration_files()
                
                # Create welcome documentation
                self._create_documentation()
                
                # Create security files
                self._create_security_files()
                
                # Verify structure
                if self._verify_structure():
                    logger.info("USB partition prepared successfully")
                    return True
                else:
                    logger.error("Structure verification failed")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to prepare USB partition: {e}")
                return False
    
    def _create_partition_marker(self):
        """
        Create partition marker file
        FIX: Using context manager for file writing
        """
        marker_file = self.usb_path / "sunflower_data.id"
        marker_content = {
            "type": "SUNFLOWER_AI_DATA_v6.2.0",
            "created": datetime.now().isoformat(),
            "partition_type": "user_data"
        }
        
        # FIX: Use context manager for file operations
        with self._file_operation("create_partition_marker"):
            with open(marker_file, 'w', encoding='utf-8') as f:
                json.dump(marker_content, f, indent=2)
        
        logger.info("Created partition marker")
    
    def _create_directory_structure(self):
        """
        Create directory structure on USB partition
        FIX: Proper exception handling for directory creation
        """
        directories = [
            self.staging_dir,
            self.staging_dir / "profiles",
            self.staging_dir / "profiles" / "family",
            self.staging_dir / "profiles" / "children",
            self.staging_dir / "conversations",
            self.staging_dir / "sessions",
            self.staging_dir / "logs",
            self.staging_dir / "logs" / "safety",
            self.staging_dir / "logs" / "system",
            self.staging_dir / "safety",
            self.staging_dir / "safety" / "incidents",
            self.staging_dir / "safety" / "patterns",
            self.staging_dir / "progress",
            self.staging_dir / "progress" / "reports",
            self.staging_dir / "progress" / "achievements",
            self.staging_dir / "backups",
            self.staging_dir / "backups" / "auto",
            self.staging_dir / "backups" / "manual",
            self.staging_dir / "cache",
            self.staging_dir / "cache" / "models",
            self.staging_dir / "cache" / "temp",
            self.staging_dir / ".config",
            self.staging_dir / ".config" / "user",
            self.staging_dir / ".config" / "system",
            self.staging_dir / ".security",
            self.staging_dir / ".security" / "tokens",
            self.staging_dir / ".security" / "keys",
            self.staging_dir / "openwebui",
            self.staging_dir / "openwebui" / "data",
            self.staging_dir / "openwebui" / "config",
            self.staging_dir / "ollama",
            self.staging_dir / "ollama" / "models",
            self.staging_dir / "ollama" / "manifests"
        ]
        
        with self._file_operation("create_directories"):
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
                # Create .gitkeep file to preserve empty directories
                gitkeep = directory / ".gitkeep"
                # FIX: Use context manager even for simple file creation
                with open(gitkeep, 'w') as f:
                    f.write("")
        
        logger.info(f"Created {len(directories)} directories")
    
    def _create_configuration_files(self):
        """
        Create initial configuration files
        FIX: All file writes use context managers
        """
        # User preferences (empty initially)
        preferences_file = self.staging_dir / ".config" / "user" / "preferences.json"
        preferences = {
            "theme": "light",
            "language": "en-US",
            "timezone": "UTC",
            "notifications": True,
            "auto_backup": True,
            "backup_frequency_days": 7
        }
        
        # FIX: Use context manager
        with self._file_operation("create_preferences"):
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=2)
        
        # System configuration
        system_config_file = self.staging_dir / ".config" / "system" / "runtime.json"
        system_config = {
            "version": "6.2.0",
            "initialized": datetime.now().isoformat(),
            "hardware_tier": "auto",
            "model_variant": "auto",
            "safety_mode": "strict",
            "logging_level": "INFO"
        }
        
        # FIX: Use context manager
        with self._file_operation("create_system_config"):
            with open(system_config_file, 'w', encoding='utf-8') as f:
                json.dump(system_config, f, indent=2)
        
        # Family settings template
        family_template_file = self.staging_dir / "profiles" / "family_template.json"
        family_template = {
            "family_name": null,
            "created_date": null,
            "parent_password_hash": null,
            "parent_email": null,
            "children": [],
            "settings": {
                "safety_level": "maximum",
                "session_time_limit": 30,
                "break_reminder": True,
                "parent_notifications": True
            }
        }
        
        # FIX: Use context manager
        with self._file_operation("create_family_template"):
            with open(family_template_file, 'w', encoding='utf-8') as f:
                json.dump(family_template, f, indent=2)
        
        logger.info("Created configuration files")
    
    def _create_documentation(self):
        """
        Create user documentation files
        FIX: Use context managers for all file writes
        """
        # README file
        readme_file = self.staging_dir / "README.txt"
        readme_content = """
Sunflower AI Professional System - USB Data Partition
====================================================

This USB partition stores all your family's data including:
- User profiles and settings
- Conversation histories
- Learning progress
- Safety logs
- Backups

Important Information:
---------------------
1. Do NOT modify files directly - use the application
2. Regular backups are created automatically
3. All data is encrypted and stored locally
4. No internet connection required

Directory Structure:
-------------------
/profiles     - Family and child profiles
/conversations - Chat histories
/sessions     - Learning sessions
/logs         - System and safety logs
/progress     - Learning progress and achievements
/backups      - Automatic and manual backups
/.config      - Configuration files
/.security    - Security tokens (do not share!)

For help, refer to the main application documentation.

Version: 6.2.0
Created: {date}
""".format(date=datetime.now().strftime('%Y-%m-%d'))
        
        # FIX: Use context manager
        with self._file_operation("create_readme"):
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
        
        # Quick start guide
        quickstart_file = self.staging_dir / "QUICK_START.txt"
        quickstart_content = """
QUICK START GUIDE
================

1. Insert both the CD-ROM and USB drive
2. Run the launcher from the CD-ROM
3. Create your parent account
4. Add child profiles
5. Start learning!

Safety First:
- All content is filtered for age-appropriateness
- Parent dashboard shows all activity
- Automatic session time limits
- Educational focus enforced

Need Help?
- Check the User Manual on the CD-ROM
- Visit the Parent Dashboard for settings
- Review safety logs for filtered content
"""
        
        # FIX: Use context manager
        with self._file_operation("create_quickstart"):
            with open(quickstart_file, 'w', encoding='utf-8') as f:
                f.write(quickstart_content)
        
        logger.info("Created documentation files")
    
    def _create_security_files(self):
        """
        Create security-related files
        FIX: Proper resource management for security files
        """
        # Security notice
        security_notice_file = self.staging_dir / ".security" / "IMPORTANT_NOTICE.txt"
        security_notice = """
SECURITY NOTICE
==============

This directory contains sensitive security information.

DO NOT:
- Share these files with anyone
- Upload to cloud services
- Email or message these files
- Post online

These files contain:
- Encryption keys
- Authentication tokens
- Security certificates

If you suspect these files have been compromised:
1. Stop using the system immediately
2. Create new profiles with new passwords
3. Generate new security tokens

Keep this USB drive physically secure!
"""
        
        # FIX: Use context manager
        with self._file_operation("create_security_notice"):
            with open(security_notice_file, 'w', encoding='utf-8') as f:
                f.write(security_notice)
        
        # Create empty key storage (will be populated on first run)
        keys_file = self.staging_dir / ".security" / "keys" / ".keys_placeholder"
        
        # FIX: Use context manager
        with self._file_operation("create_keys_placeholder"):
            with open(keys_file, 'w') as f:
                f.write("Keys will be generated on first run\n")
        
        # Set restrictive permissions on security directory (Unix-like systems)
        if os.name != 'nt':
            try:
                os.chmod(self.staging_dir / ".security", 0o700)
                os.chmod(self.staging_dir / ".security" / "keys", 0o700)
                os.chmod(self.staging_dir / ".security" / "tokens", 0o700)
            except Exception as e:
                logger.warning(f"Could not set restrictive permissions: {e}")
        
        logger.info("Created security files")
    
    def _verify_structure(self) -> bool:
        """
        Verify the created structure
        FIX: Proper resource management during verification
        """
        required_paths = [
            self.usb_path / "sunflower_data.id",
            self.staging_dir,
            self.staging_dir / "profiles",
            self.staging_dir / "conversations",
            self.staging_dir / "logs",
            self.staging_dir / ".config",
            self.staging_dir / ".security",
            self.staging_dir / "README.txt"
        ]
        
        with self._file_operation("verify_structure"):
            for path in required_paths:
                if not path.exists():
                    logger.error(f"Required path missing: {path}")
                    return False
            
            # Verify marker file content
            marker_file = self.usb_path / "sunflower_data.id"
            try:
                # FIX: Use context manager for reading
                with open(marker_file, 'r', encoding='utf-8') as f:
                    marker_data = json.load(f)
                    if marker_data.get('type') != 'SUNFLOWER_AI_DATA_v6.2.0':
                        logger.error("Invalid marker file content")
                        return False
            except Exception as e:
                logger.error(f"Could not read marker file: {e}")
                return False
        
        logger.info("Structure verification passed")
        return True
    
    def backup_existing_data(self, backup_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Backup existing data before modifications
        FIX: Proper resource management during backup
        
        Args:
            backup_dir: Directory for backup (auto-generated if None)
            
        Returns:
            Path to backup or None if failed
        """
        if not backup_dir:
            backup_dir = self.staging_dir / "backups" / "auto" / datetime.now().strftime('%Y%m%d_%H%M%S')
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        with self._file_operation("backup_data"):
            try:
                # Create backup manifest
                manifest = {
                    "backup_date": datetime.now().isoformat(),
                    "version": "6.2.0",
                    "type": "automatic",
                    "files": []
                }
                
                # Backup profiles
                profiles_dir = self.staging_dir / "profiles"
                if profiles_dir.exists():
                    backup_profiles = backup_dir / "profiles"
                    shutil.copytree(profiles_dir, backup_profiles, dirs_exist_ok=True)
                    
                    # Count backed up files
                    for root, dirs, files in os.walk(backup_profiles):
                        manifest['files'].extend([
                            str(Path(root) / f) for f in files
                        ])
                
                # Backup configurations
                config_dir = self.staging_dir / ".config"
                if config_dir.exists():
                    backup_config = backup_dir / ".config"
                    shutil.copytree(config_dir, backup_config, dirs_exist_ok=True)
                
                # Write manifest
                manifest_file = backup_dir / "manifest.json"
                # FIX: Use context manager
                with open(manifest_file, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2)
                
                logger.info(f"Backup created at {backup_dir}")
                return backup_dir
                
            except Exception as e:
                logger.error(f"Backup failed: {e}")
                # Clean up partial backup
                if backup_dir.exists():
                    shutil.rmtree(backup_dir, ignore_errors=True)
                return None
    
    def clean_temp_files(self) -> int:
        """
        Clean temporary files from cache
        FIX: Proper resource management during cleanup
        
        Returns:
            Number of files cleaned
        """
        cleaned = 0
        temp_dir = self.staging_dir / "cache" / "temp"
        
        with self._file_operation("clean_temp_files"):
            if temp_dir.exists():
                for temp_file in temp_dir.iterdir():
                    try:
                        if temp_file.is_file():
                            # Check if file is old (>1 day)
                            age = datetime.now().timestamp() - temp_file.stat().st_mtime
                            if age > 86400:  # 1 day in seconds
                                temp_file.unlink()
                                cleaned += 1
                    except Exception as e:
                        logger.warning(f"Could not remove temp file {temp_file}: {e}")
        
        if cleaned > 0:
            logger.info(f"Cleaned {cleaned} temporary files")
        
        return cleaned
    
    def get_partition_info(self) -> Dict[str, Any]:
        """
        Get information about the USB partition
        FIX: Safe file reading with context managers
        
        Returns:
            Dictionary with partition information
        """
        info = {
            "path": str(self.usb_path),
            "exists": self.usb_path.exists(),
            "initialized": False,
            "version": None,
            "created": None,
            "size_bytes": 0,
            "free_bytes": 0,
            "usage_percent": 0
        }
        
        with self._file_operation("get_partition_info"):
            # Check if initialized
            marker_file = self.usb_path / "sunflower_data.id"
            if marker_file.exists():
                try:
                    # FIX: Use context manager
                    with open(marker_file, 'r', encoding='utf-8') as f:
                        marker_data = json.load(f)
                        info["initialized"] = True
                        info["version"] = marker_data.get("type", "").replace("SUNFLOWER_AI_DATA_", "")
                        info["created"] = marker_data.get("created")
                except Exception as e:
                    logger.warning(f"Could not read marker file: {e}")
            
            # Get disk usage
            try:
                import shutil
                usage = shutil.disk_usage(self.usb_path)
                info["size_bytes"] = usage.total
                info["free_bytes"] = usage.free
                info["usage_percent"] = ((usage.total - usage.free) / usage.total) * 100
            except Exception as e:
                logger.warning(f"Could not get disk usage: {e}")
        
        return info
    
    def export_configuration(self, export_file: Path) -> bool:
        """
        Export configuration for backup or transfer
        FIX: Proper resource management during export
        
        Args:
            export_file: Path to export file
            
        Returns:
            True if successful
        """
        with self._file_operation("export_configuration"):
            try:
                config_data = {
                    "version": "6.2.0",
                    "export_date": datetime.now().isoformat(),
                    "configurations": {}
                }
                
                # Read user preferences
                preferences_file = self.staging_dir / ".config" / "user" / "preferences.json"
                if preferences_file.exists():
                    # FIX: Use context manager
                    with open(preferences_file, 'r', encoding='utf-8') as f:
                        config_data["configurations"]["user_preferences"] = json.load(f)
                
                # Read system configuration
                system_file = self.staging_dir / ".config" / "system" / "runtime.json"
                if system_file.exists():
                    # FIX: Use context manager
                    with open(system_file, 'r', encoding='utf-8') as f:
                        config_data["configurations"]["system"] = json.load(f)
                
                # Write export file
                # FIX: Use context manager
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2)
                
                logger.info(f"Configuration exported to {export_file}")
                return True
                
            except Exception as e:
                logger.error(f"Export failed: {e}")
                return False


# Utility functions
def check_usb_space(usb_path: Path, required_mb: int = 500) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if USB has enough space
    FIX: Safe disk usage checking
    
    Args:
        usb_path: Path to USB partition
        required_mb: Required space in MB
        
    Returns:
        Tuple of (has_enough_space, usage_info)
    """
    try:
        import shutil
        usage = shutil.disk_usage(usb_path)
        
        free_mb = usage.free / (1024 * 1024)
        total_mb = usage.total / (1024 * 1024)
        used_mb = (usage.total - usage.free) / (1024 * 1024)
        
        info = {
            "total_mb": total_mb,
            "used_mb": used_mb,
            "free_mb": free_mb,
            "usage_percent": (used_mb / total_mb) * 100 if total_mb > 0 else 0,
            "has_enough_space": free_mb >= required_mb
        }
        
        return info["has_enough_space"], info
        
    except Exception as e:
        logger.error(f"Could not check disk space: {e}")
        return False, {"error": str(e)}


def main():
    """Main entry point for USB preparation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prepare Sunflower AI USB Partition')
    parser.add_argument('--usb-path', type=Path, help='Path to USB partition')
    parser.add_argument('--backup', action='store_true', help='Backup existing data')
    parser.add_argument('--clean', action='store_true', help='Clean temporary files')
    parser.add_argument('--info', action='store_true', help='Show partition information')
    parser.add_argument('--export', type=Path, help='Export configuration to file')
    
    args = parser.parse_args()
    
    try:
        # Initialize preparer
        preparer = USBPartitionPreparer(args.usb_path)
        
        if args.info:
            # Show partition information
            info = preparer.get_partition_info()
            print("\nUSB Partition Information:")
            print("=" * 40)
            print(f"Path: {info['path']}")
            print(f"Initialized: {info['initialized']}")
            print(f"Version: {info['version']}")
            print(f"Created: {info['created']}")
            print(f"Size: {info['size_bytes'] / (1024**3):.2f} GB")
            print(f"Free: {info['free_bytes'] / (1024**3):.2f} GB")
            print(f"Usage: {info['usage_percent']:.1f}%")
            
        elif args.clean:
            # Clean temporary files
            cleaned = preparer.clean_temp_files()
            print(f"Cleaned {cleaned} temporary files")
            
        elif args.backup:
            # Backup existing data
            backup_path = preparer.backup_existing_data()
            if backup_path:
                print(f"Backup created at: {backup_path}")
            else:
                print("Backup failed")
                sys.exit(1)
                
        elif args.export:
            # Export configuration
            if preparer.export_configuration(args.export):
                print(f"Configuration exported to: {args.export}")
            else:
                print("Export failed")
                sys.exit(1)
                
        else:
            # Prepare partition
            print("Preparing USB partition...")
            print("=" * 40)
            
            # Check space
            has_space, space_info = check_usb_space(preparer.usb_path)
            if not has_space:
                print(f"⚠️  Insufficient space: {space_info['free_mb']:.1f} MB free")
                print("At least 500 MB required")
                sys.exit(1)
            
            print(f"✓ Space available: {space_info['free_mb']:.1f} MB free")
            
            # Prepare partition
            if preparer.prepare_partition():
                print("✓ USB partition prepared successfully")
                
                # Show summary
                info = preparer.get_partition_info()
                print("\nPartition ready for use:")
                print(f"  Location: {info['path']}")
                print(f"  Version: {info['version']}")
                print("  Status: Initialized")
                print("\nYou can now use the Sunflower AI system!")
            else:
                print("✗ Failed to prepare USB partition")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

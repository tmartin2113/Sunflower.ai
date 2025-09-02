#!/usr/bin/env python3
"""
Sunflower AI Professional System - Version Update Manager
Handles new version installations and data migration (new device purchases only)
Version: 6.2 | Platform: Windows/macOS | Architecture: Version Management
"""

import os
import sys
import json
import shutil
import hashlib
import platform
import subprocess
import logging
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import re
import sqlite3
import threading
import time

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('update_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SunflowerUpdateManager')


class UpdateType(Enum):
    """Types of updates available"""
    MAJOR_VERSION = "major"      # New device purchase required
    DATA_MIGRATION = "migration" # Transfer family data to new device
    MODEL_UPDATE = "model"       # Update AI models only
    REPAIR = "repair"           # Repair installation


class MigrationStatus(Enum):
    """Migration status codes"""
    NOT_STARTED = "not_started"
    SCANNING = "scanning"
    BACKING_UP = "backing_up"
    TRANSFERRING = "transferring"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class VersionInfo:
    """Version information for Sunflower AI system"""
    version: str
    build_number: int
    release_date: str
    platform: str
    models: List[str]
    features: List[str]
    hardware_requirements: Dict[str, Any]
    
    def __post_init__(self):
        # Parse version string (e.g., "6.2.0")
        parts = self.version.split('.')
        self.major = int(parts[0]) if len(parts) > 0 else 0
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0
    
    def is_newer_than(self, other: 'VersionInfo') -> bool:
        """Check if this version is newer than another"""
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        return self.patch > other.patch


@dataclass
class FamilyData:
    """Family data structure for migration"""
    family_id: str
    profiles: List[Dict[str, Any]]
    conversations: Dict[str, List[Dict]]
    learning_progress: Dict[str, Dict]
    settings: Dict[str, Any]
    created_date: str
    last_accessed: str
    total_size_mb: float


class UpdateManager:
    """Manages version updates and data migration for Sunflower AI"""
    
    def __init__(self, current_install_path: str = None):
        self.current_install_path = Path(current_install_path or self._detect_install_path())
        self.current_version = self._get_current_version()
        self.data_path = self._get_data_path()
        self.backup_path = Path.home() / "SunflowerAI_Backups"
        self.migration_status = MigrationStatus.NOT_STARTED
        self.migration_progress = 0.0
        self.errors: List[str] = []
        
        # Ensure backup directory exists
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"UpdateManager initialized - Version: {self.current_version.version}")
    
    def _detect_install_path(self) -> Path:
        """Detect current Sunflower AI installation path"""
        if platform.system() == "Windows":
            possible_paths = [
                Path("C:/Program Files/Sunflower AI Professional"),
                Path("C:/Program Files (x86)/Sunflower AI Professional"),
                Path(os.environ.get("PROGRAMFILES", "")) / "Sunflower AI Professional",
            ]
        else:  # macOS/Linux
            possible_paths = [
                Path("/Applications/Sunflower AI Professional.app"),
                Path.home() / "Applications/Sunflower AI Professional.app",
                Path("/usr/local/sunflowerai"),
            ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # If not found, use current directory
        return Path.cwd()
    
    def _get_data_path(self) -> Path:
        """Get path to user data (USB partition when device is connected)"""
        # Check for mounted Sunflower device
        if platform.system() == "Windows":
            # Check drive letters for SUNFLOWER_AI_DATA volume
            for drive in "DEFGHIJKLMNOPQRSTUVWXYZ":
                volume_path = Path(f"{drive}:/")
                if volume_path.exists():
                    volume_info = self._get_volume_info(volume_path)
                    if volume_info and "SUNFLOWER_AI_DATA" in volume_info.get("label", ""):
                        return volume_path
        else:
            # Check mounted volumes on macOS/Linux
            volumes_path = Path("/Volumes") if platform.system() == "Darwin" else Path("/media")
            for volume in volumes_path.iterdir():
                if "SUNFLOWER_AI_DATA" in volume.name:
                    return volume
        
        # Fallback to local data directory
        return self.current_install_path / "data"
    
    def _get_volume_info(self, path: Path) -> Optional[Dict[str, str]]:
        """Get volume information for a path"""
        try:
            if platform.system() == "Windows":
                import win32api
                volume_info = win32api.GetVolumeInformation(str(path))
                return {
                    "label": volume_info[0],
                    "serial": volume_info[1],
                    "filesystem": volume_info[4]
                }
            else:
                # Use diskutil on macOS or df on Linux
                result = subprocess.run(
                    ["diskutil", "info", str(path)] if platform.system() == "Darwin" else ["df", "-T", str(path)],
                    capture_output=True,
                    text=True
                )
                # Parse output for volume info
                return {"label": path.name}
        except:
            return None
    
    def _get_current_version(self) -> VersionInfo:
        """Get current installed version information"""
        version_file = self.current_install_path / "version_info.json"
        
        if version_file.exists():
            with open(version_file, 'r') as f:
                data = json.load(f)
                return VersionInfo(**data)
        
        # Default version if file not found
        return VersionInfo(
            version="6.2.0",
            build_number=1000,
            release_date=datetime.now().isoformat(),
            platform=platform.system(),
            models=["llama3.2:7b", "llama3.2:3b", "llama3.2:1b"],
            features=["Family Profiles", "Parent Dashboard", "Offline Mode"],
            hardware_requirements={"min_ram_gb": 4, "min_disk_gb": 8}
        )
    
    def check_for_updates(self) -> Optional[VersionInfo]:
        """
        Check for available updates
        Note: Per design, updates are new device purchases, not online updates
        This checks if a new device is connected with a newer version
        """
        logger.info("Checking for new version devices")
        
        # Look for connected Sunflower devices
        new_devices = self._scan_for_devices()
        
        for device_path in new_devices:
            device_version = self._get_device_version(device_path)
            if device_version and device_version.is_newer_than(self.current_version):
                logger.info(f"Found newer version device: {device_version.version}")
                return device_version
        
        logger.info("No newer version devices found")
        return None
    
    def _scan_for_devices(self) -> List[Path]:
        """Scan for connected Sunflower devices"""
        devices = []
        
        if platform.system() == "Windows":
            # Scan removable drives
            import win32file
            drives = [f"{d}:/" for d in "DEFGHIJKLMNOPQRSTUVWXYZ" 
                     if os.path.exists(f"{d}:/")]
            
            for drive in drives:
                drive_type = win32file.GetDriveType(drive)
                if drive_type == win32file.DRIVE_REMOVABLE or drive_type == win32file.DRIVE_CDROM:
                    device_config = Path(drive) / "device_config.json"
                    if device_config.exists():
                        devices.append(Path(drive))
        else:
            # Scan mounted volumes
            volumes_path = Path("/Volumes") if platform.system() == "Darwin" else Path("/media")
            for volume in volumes_path.iterdir():
                device_config = volume / "device_config.json"
                if device_config.exists():
                    devices.append(volume)
        
        return devices
    
    def _get_device_version(self, device_path: Path) -> Optional[VersionInfo]:
        """Get version information from a device"""
        try:
            version_file = device_path / "version_info.json"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    data = json.load(f)
                    return VersionInfo(**data)
            
            # Try device_config.json as fallback
            config_file = device_path / "device_config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return VersionInfo(
                        version=config.get("version", "0.0.0"),
                        build_number=0,
                        release_date=config.get("creation_date", ""),
                        platform=config.get("platform", ""),
                        models=config.get("models", []),
                        features=[],
                        hardware_requirements={}
                    )
        except Exception as e:
            logger.error(f"Failed to read device version: {e}")
        
        return None
    
    def backup_family_data(self) -> Optional[Path]:
        """Create backup of all family data"""
        try:
            self.migration_status = MigrationStatus.BACKING_UP
            logger.info("Starting family data backup")
            
            # Create timestamped backup directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.backup_path / f"backup_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Collect family data
            family_data = self._collect_family_data()
            
            if not family_data:
                logger.warning("No family data found to backup")
                return None
            
            # Save data to backup
            for family in family_data:
                family_backup = backup_dir / family.family_id
                family_backup.mkdir(exist_ok=True)
                
                # Save profiles
                profiles_file = family_backup / "profiles.json"
                with open(profiles_file, 'w') as f:
                    json.dump(family.profiles, f, indent=2)
                
                # Save conversations
                conversations_dir = family_backup / "conversations"
                conversations_dir.mkdir(exist_ok=True)
                for child_name, convos in family.conversations.items():
                    convo_file = conversations_dir / f"{child_name}.json"
                    with open(convo_file, 'w') as f:
                        json.dump(convos, f, indent=2)
                
                # Save learning progress
                progress_file = family_backup / "learning_progress.json"
                with open(progress_file, 'w') as f:
                    json.dump(family.learning_progress, f, indent=2)
                
                # Save settings
                settings_file = family_backup / "settings.json"
                with open(settings_file, 'w') as f:
                    json.dump(family.settings, f, indent=2)
                
                self.migration_progress = 50.0
            
            # Create backup manifest
            manifest = {
                "backup_date": datetime.now().isoformat(),
                "source_version": self.current_version.version,
                "families_count": len(family_data),
                "total_size_mb": sum(f.total_size_mb for f in family_data),
                "checksums": {}
            }
            
            # Calculate checksums
            for file_path in backup_dir.rglob("*.json"):
                checksum = self._calculate_checksum(file_path)
                rel_path = file_path.relative_to(backup_dir)
                manifest["checksums"][str(rel_path)] = checksum
            
            manifest_file = backup_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create compressed archive
            archive_path = self.backup_path / f"sunflower_backup_{timestamp}.zip"
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in backup_dir.rglob("*"):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(backup_dir)
                        zf.write(file_path, arc_name)
            
            self.migration_progress = 100.0
            logger.info(f"Backup completed: {archive_path}")
            return archive_path
            
        except Exception as e:
            self.migration_status = MigrationStatus.ERROR
            self.errors.append(f"Backup failed: {e}")
            logger.error(f"Backup failed: {e}", exc_info=True)
            return None
    
    def _collect_family_data(self) -> List[FamilyData]:
        """Collect all family data from current installation"""
        families = []
        
        try:
            # Look for family profiles
            profiles_dir = self.data_path / "family_profiles"
            if not profiles_dir.exists():
                return families
            
            for family_dir in profiles_dir.iterdir():
                if not family_dir.is_dir():
                    continue
                
                family_id = family_dir.name
                
                # Load profiles
                profiles = []
                profiles_file = family_dir / "profiles.json"
                if profiles_file.exists():
                    with open(profiles_file, 'r') as f:
                        profiles = json.load(f)
                
                # Load conversations
                conversations = {}
                conv_dir = self.data_path / "conversation_logs" / family_id
                if conv_dir.exists():
                    for conv_file in conv_dir.glob("*.json"):
                        child_name = conv_file.stem
                        with open(conv_file, 'r') as f:
                            conversations[child_name] = json.load(f)
                
                # Load learning progress
                progress = {}
                progress_dir = self.data_path / "learning_progress" / family_id
                if progress_dir.exists():
                    for prog_file in progress_dir.glob("*.json"):
                        with open(prog_file, 'r') as f:
                            progress[prog_file.stem] = json.load(f)
                
                # Load settings
                settings = {}
                settings_file = family_dir / "settings.json"
                if settings_file.exists():
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                
                # Calculate total size
                total_size = sum(
                    f.stat().st_size for f in family_dir.rglob("*") if f.is_file()
                )
                
                family_data = FamilyData(
                    family_id=family_id,
                    profiles=profiles,
                    conversations=conversations,
                    learning_progress=progress,
                    settings=settings,
                    created_date=settings.get("created_date", ""),
                    last_accessed=settings.get("last_accessed", ""),
                    total_size_mb=total_size / (1024 * 1024)
                )
                
                families.append(family_data)
                
        except Exception as e:
            logger.error(f"Error collecting family data: {e}", exc_info=True)
        
        return families
    
    def migrate_to_new_device(self, new_device_path: Path, backup_path: Optional[Path] = None) -> bool:
        """Migrate family data to a new device"""
        try:
            self.migration_status = MigrationStatus.TRANSFERRING
            logger.info(f"Starting migration to new device: {new_device_path}")
            
            # Use provided backup or create new one
            if not backup_path:
                backup_path = self.backup_family_data()
                if not backup_path:
                    self.errors.append("Failed to create backup for migration")
                    return False
            
            # Verify new device is writable
            test_file = new_device_path / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except:
                self.errors.append(f"Cannot write to new device: {new_device_path}")
                return False
            
            # Extract backup to new device
            with zipfile.ZipFile(backup_path, 'r') as zf:
                # Find data partition on new device
                data_path = self._find_data_partition(new_device_path)
                if not data_path:
                    self.errors.append("Cannot find data partition on new device")
                    return False
                
                # Extract to temporary location first
                temp_dir = Path(tempfile.mkdtemp())
                zf.extractall(temp_dir)
                
                # Verify manifest
                manifest_file = temp_dir / "manifest.json"
                if not manifest_file.exists():
                    self.errors.append("Invalid backup: missing manifest")
                    return False
                
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                
                # Verify checksums
                self.migration_status = MigrationStatus.VERIFYING
                for rel_path, expected_checksum in manifest["checksums"].items():
                    file_path = temp_dir / rel_path
                    if file_path.exists():
                        actual_checksum = self._calculate_checksum(file_path)
                        if actual_checksum != expected_checksum:
                            self.errors.append(f"Checksum mismatch: {rel_path}")
                            return False
                
                # Copy to new device
                for family_dir in temp_dir.iterdir():
                    if family_dir.name == "manifest.json":
                        continue
                    
                    # Copy family data
                    dest_family = data_path / "family_profiles" / family_dir.name
                    if family_dir.is_dir():
                        shutil.copytree(family_dir, dest_family, dirs_exist_ok=True)
                    
                    # Copy conversations
                    conv_src = family_dir / "conversations"
                    if conv_src.exists():
                        conv_dest = data_path / "conversation_logs" / family_dir.name
                        conv_dest.mkdir(parents=True, exist_ok=True)
                        for conv_file in conv_src.glob("*.json"):
                            shutil.copy2(conv_file, conv_dest)
                    
                    # Copy learning progress
                    prog_src = family_dir / "learning_progress.json"
                    if prog_src.exists():
                        prog_dest = data_path / "learning_progress" / family_dir.name
                        prog_dest.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(prog_src, prog_dest / "progress.json")
                
                # Clean up temp directory
                shutil.rmtree(temp_dir)
                
                # Update migration record
                migration_record = {
                    "migration_date": datetime.now().isoformat(),
                    "source_version": self.current_version.version,
                    "target_version": self._get_device_version(new_device_path).version,
                    "families_migrated": manifest["families_count"],
                    "backup_used": str(backup_path)
                }
                
                record_file = data_path / "migration_history.json"
                history = []
                if record_file.exists():
                    with open(record_file, 'r') as f:
                        history = json.load(f)
                history.append(migration_record)
                
                with open(record_file, 'w') as f:
                    json.dump(history, f, indent=2)
                
                self.migration_status = MigrationStatus.COMPLETE
                self.migration_progress = 100.0
                logger.info("Migration completed successfully")
                return True
                
        except Exception as e:
            self.migration_status = MigrationStatus.ERROR
            self.errors.append(f"Migration failed: {e}")
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False
    
    def _find_data_partition(self, device_path: Path) -> Optional[Path]:
        """Find the data partition on a device"""
        # Look for SUNFLOWER_AI_DATA partition
        if platform.system() == "Windows":
            # On Windows, partitions might be on different drive letters
            device_id = self._get_device_id(device_path)
            for drive in "DEFGHIJKLMNOPQRSTUVWXYZ":
                volume_path = Path(f"{drive}:/")
                if volume_path.exists():
                    volume_info = self._get_volume_info(volume_path)
                    if volume_info and "SUNFLOWER_AI_DATA" in volume_info.get("label", ""):
                        # Verify it's the same device
                        config_file = volume_path / "runtime_config" / "config.json"
                        if config_file.exists():
                            with open(config_file, 'r') as f:
                                config = json.load(f)
                                if config.get("device_id") == device_id:
                                    return volume_path
        else:
            # On Unix systems, look for data subdirectory
            data_path = device_path / "data"
            if data_path.exists():
                return data_path
            
            # Or look for separate partition mount
            device_name = device_path.name
            data_name = f"{device_name}_DATA"
            data_path = device_path.parent / data_name
            if data_path.exists():
                return data_path
        
        return None
    
    def _get_device_id(self, device_path: Path) -> Optional[str]:
        """Get device ID from device configuration"""
        config_file = device_path / "device_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get("device_id")
        return None
    
    def repair_installation(self) -> bool:
        """Repair current installation"""
        try:
            logger.info("Starting installation repair")
            errors_fixed = 0
            
            # Verify directory structure
            required_dirs = [
                "models",
                "modelfiles",
                "interface",
                "documentation",
                "data/family_profiles",
                "data/conversation_logs",
                "data/learning_progress",
                "data/parent_dashboard"
            ]
            
            for dir_path in required_dirs:
                full_path = self.current_install_path / dir_path
                if not full_path.exists():
                    logger.info(f"Creating missing directory: {dir_path}")
                    full_path.mkdir(parents=True, exist_ok=True)
                    errors_fixed += 1
            
            # Verify critical files
            critical_files = {
                "modelfiles/Sunflower_AI_Kids.modelfile": self._create_default_kids_modelfile,
                "modelfiles/Sunflower_AI_Educator.modelfile": self._create_default_educator_modelfile,
                "version_info.json": self._create_version_info
            }
            
            for file_path, create_func in critical_files.items():
                full_path = self.current_install_path / file_path
                if not full_path.exists():
                    logger.info(f"Recreating missing file: {file_path}")
                    create_func(full_path)
                    errors_fixed += 1
            
            # Verify models
            models_dir = self.current_install_path / "models"
            if not any(models_dir.glob("*.bin")):
                logger.warning("No models found. Models need to be reinstalled from device.")
            
            # Check and fix permissions
            if platform.system() != "Windows":
                # Fix permissions on Unix systems
                for path in self.current_install_path.rglob("*"):
                    if path.is_dir():
                        os.chmod(path, 0o755)
                    elif path.suffix in [".sh", ".command"]:
                        os.chmod(path, 0o755)
                    else:
                        os.chmod(path, 0o644)
            
            # Verify configuration
            config_file = self.current_install_path / "data" / "runtime_config" / "config.json"
            if not config_file.exists():
                config_file.parent.mkdir(parents=True, exist_ok=True)
                default_config = {
                    "first_run": False,
                    "version": self.current_version.version,
                    "last_repair": datetime.now().isoformat(),
                    "family_count": 0
                }
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                errors_fixed += 1
            
            logger.info(f"Repair completed. Fixed {errors_fixed} issues.")
            return True
            
        except Exception as e:
            logger.error(f"Repair failed: {e}", exc_info=True)
            return False
    
    def _create_default_kids_modelfile(self, path: Path) -> None:
        """Create default Kids modelfile"""
        content = """# Sunflower AI Kids Model
FROM llama3.2:1b

SYSTEM You are Sunflower AI, a friendly and safe educational assistant for children.
Always provide age-appropriate, educational responses focused on STEM topics.
Redirect any inappropriate topics to safe, educational alternatives.

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    
    def _create_default_educator_modelfile(self, path: Path) -> None:
        """Create default Educator modelfile"""
        content = """# Sunflower AI Educator Model
FROM llama3.2:3b

SYSTEM You are Sunflower AI Professional, an educational assistant for parents and educators.
Provide comprehensive STEM education support and monitor children's learning progress.

PARAMETER temperature 0.8
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.0
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    
    def _create_version_info(self, path: Path) -> None:
        """Create version info file"""
        version_data = asdict(self.current_version)
        with open(path, 'w') as f:
            json.dump(version_data, f, indent=2)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def verify_system_integrity(self) -> Dict[str, Any]:
        """Verify complete system integrity"""
        logger.info("Running system integrity check")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "version": self.current_version.version,
            "status": "healthy",
            "issues": [],
            "warnings": [],
            "statistics": {}
        }
        
        # Check installation structure
        if not self.current_install_path.exists():
            report["issues"].append("Installation directory not found")
            report["status"] = "critical"
            return report
        
        # Check critical components
        components = {
            "models": self.current_install_path / "models",
            "modelfiles": self.current_install_path / "modelfiles",
            "interface": self.current_install_path / "interface",
            "documentation": self.current_install_path / "documentation"
        }
        
        for name, path in components.items():
            if not path.exists():
                report["issues"].append(f"Missing component: {name}")
                report["status"] = "degraded"
        
        # Check data integrity
        families = self._collect_family_data()
        report["statistics"]["families"] = len(families)
        report["statistics"]["total_conversations"] = sum(
            len(f.conversations) for f in families
        )
        report["statistics"]["data_size_mb"] = sum(
            f.total_size_mb for f in families
        )
        
        # Check available disk space
        stat = shutil.disk_usage(self.current_install_path)
        free_gb = stat.free / (1024**3)
        report["statistics"]["free_disk_gb"] = round(free_gb, 2)
        
        if free_gb < 1:
            report["warnings"].append("Low disk space (< 1GB free)")
        
        # Check model files
        models_dir = self.current_install_path / "models"
        if models_dir.exists():
            model_files = list(models_dir.glob("*.bin"))
            report["statistics"]["models_installed"] = len(model_files)
            
            if len(model_files) == 0:
                report["issues"].append("No AI models installed")
                report["status"] = "degraded"
        
        # Set final status
        if report["issues"]:
            report["status"] = "degraded" if len(report["issues"]) < 3 else "critical"
        elif report["warnings"]:
            report["status"] = "warning"
        
        return report


def main():
    """Main entry point for update manager"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sunflower AI Professional - Update Manager"
    )
    parser.add_argument(
        "--action",
        choices=["check", "backup", "migrate", "repair", "verify"],
        default="check",
        help="Action to perform"
    )
    parser.add_argument(
        "--device",
        help="Path to new device for migration"
    )
    parser.add_argument(
        "--backup",
        help="Path to backup file for restoration"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("SUNFLOWER AI PROFESSIONAL - UPDATE MANAGER")
    print("Version 6.2 - Zero-Maintenance System")
    print("="*60 + "\n")
    
    manager = UpdateManager()
    
    if args.action == "check":
        print("Checking for new version devices...")
        new_version = manager.check_for_updates()
        if new_version:
            print(f"\nNew version available: {new_version.version}")
            print(f"Current version: {manager.current_version.version}")
            print("\nTo upgrade, purchase the new device and use --action migrate")
        else:
            print(f"Current version {manager.current_version.version} is up to date")
    
    elif args.action == "backup":
        print("Creating backup of family data...")
        backup_path = manager.backup_family_data()
        if backup_path:
            print(f"Backup created successfully: {backup_path}")
        else:
            print("Backup failed. Check logs for details.")
    
    elif args.action == "migrate":
        if not args.device:
            print("ERROR: --device path required for migration")
            return 1
        
        device_path = Path(args.device)
        if not device_path.exists():
            print(f"ERROR: Device not found: {device_path}")
            return 1
        
        print(f"Migrating data to new device: {device_path}")
        
        backup_path = Path(args.backup) if args.backup else None
        success = manager.migrate_to_new_device(device_path, backup_path)
        
        if success:
            print("Migration completed successfully!")
            print("You can now use the new device with all your family data.")
        else:
            print("Migration failed. Errors:")
            for error in manager.errors:
                print(f"  - {error}")
    
    elif args.action == "repair":
        print("Repairing installation...")
        success = manager.repair_installation()
        if success:
            print("Repair completed successfully")
        else:
            print("Repair failed. Manual intervention may be required.")
    
    elif args.action == "verify":
        print("Verifying system integrity...")
        report = manager.verify_system_integrity()
        
        print(f"\nSystem Status: {report['status'].upper()}")
        print(f"Version: {report['version']}")
        
        if report['issues']:
            print("\nIssues Found:")
            for issue in report['issues']:
                print(f"  ✗ {issue}")
        
        if report['warnings']:
            print("\nWarnings:")
            for warning in report['warnings']:
                print(f"  ⚠ {warning}")
        
        print("\nStatistics:")
        for key, value in report['statistics'].items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")
        
        if report['status'] == "healthy":
            print("\n✓ System is healthy and functioning properly")
        elif report['status'] == "degraded":
            print("\n⚠ System is degraded. Run --action repair to fix issues")
        else:
            print("\n✗ System has critical issues. Consider reinstallation")
    
    print("\n" + "="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

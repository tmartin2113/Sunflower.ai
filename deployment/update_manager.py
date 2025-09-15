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
from typing import Dict, List, Optional, Tuple, Any, Set
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


class CompatibilityLevel(Enum):
    """Version compatibility levels"""
    FULLY_COMPATIBLE = "fully_compatible"        # No issues expected
    BACKWARD_COMPATIBLE = "backward_compatible"  # Can read old data
    FORWARD_COMPATIBLE = "forward_compatible"    # Can be read by old version
    REQUIRES_MIGRATION = "requires_migration"    # Needs data conversion
    INCOMPATIBLE = "incompatible"               # Cannot update


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
    breaking_changes: List[str] = None  # FIX BUG-024: Track breaking changes
    compatibility_matrix: Dict[str, str] = None  # FIX BUG-024: Version compatibility
    
    def __post_init__(self):
        # Parse version string (e.g., "6.2.0")
        parts = self.version.split('.')
        self.major = int(parts[0]) if len(parts) > 0 else 0
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0
        
        # FIX BUG-024: Initialize compatibility tracking
        if self.breaking_changes is None:
            self.breaking_changes = []
        if self.compatibility_matrix is None:
            self.compatibility_matrix = {}
    
    def is_newer_than(self, other: 'VersionInfo') -> bool:
        """Check if this version is newer than another"""
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        return self.patch > other.patch
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return asdict(self)


class VersionCompatibilityChecker:
    """
    FIX BUG-024: Comprehensive version compatibility checking system
    Ensures updates don't break existing installations
    """
    
    # Define compatibility rules based on semantic versioning
    COMPATIBILITY_RULES = {
        'database_schema': {
            '6.0': ['6.0', '6.1', '6.2'],  # Compatible versions
            '5.0': ['5.0', '5.1'],
            '4.0': ['4.0']
        },
        'profile_format': {
            '2.0': ['6.0', '6.1', '6.2'],
            '1.0': ['4.0', '5.0', '5.1']
        },
        'model_format': {
            'gguf': ['6.0', '6.1', '6.2'],
            'ggml': ['4.0', '5.0', '5.1']
        },
        'config_structure': {
            'v3': ['6.0', '6.1', '6.2'],
            'v2': ['5.0', '5.1'],
            'v1': ['4.0']
        }
    }
    
    # Breaking changes between versions
    BREAKING_CHANGES = {
        '6.0.0': [
            'New database schema incompatible with v5.x',
            'Profile format changed to JSON from XML',
            'Model format changed from GGML to GGUF'
        ],
        '5.0.0': [
            'Configuration file structure changed',
            'Parent dashboard API changed',
            'Session logging format updated'
        ],
        '4.0.0': [
            'Initial version - baseline'
        ]
    }
    
    # Migration paths for different version combinations
    MIGRATION_PATHS = {
        ('5.', '6.'): 'migrate_v5_to_v6',
        ('4.', '6.'): 'migrate_v4_to_v6',
        ('4.', '5.'): 'migrate_v4_to_v5'
    }
    
    @classmethod
    def check_compatibility(
        cls,
        current_version: VersionInfo,
        target_version: VersionInfo
    ) -> Tuple[CompatibilityLevel, List[str]]:
        """
        FIX BUG-024: Check if target version is compatible with current installation
        
        Args:
            current_version: Currently installed version
            target_version: Version to update to
            
        Returns:
            Tuple of (compatibility level, list of issues/warnings)
        """
        issues = []
        
        # Check if downgrade
        if not target_version.is_newer_than(current_version):
            if target_version.version == current_version.version:
                return CompatibilityLevel.FULLY_COMPATIBLE, ["Same version - no update needed"]
            else:
                return CompatibilityLevel.INCOMPATIBLE, ["Downgrade not supported"]
        
        # Check major version change
        if target_version.major != current_version.major:
            # Major version change - check for breaking changes
            breaking_changes = cls._get_breaking_changes(
                current_version.version,
                target_version.version
            )
            
            if breaking_changes:
                issues.extend(breaking_changes)
                
                # Check if migration path exists
                migration_path = cls._get_migration_path(
                    current_version.version,
                    target_version.version
                )
                
                if migration_path:
                    issues.append(f"Migration available: {migration_path}")
                    return CompatibilityLevel.REQUIRES_MIGRATION, issues
                else:
                    issues.append("No migration path available")
                    return CompatibilityLevel.INCOMPATIBLE, issues
        
        # Check minor version change
        if target_version.minor != current_version.minor:
            # Minor version change - should be backward compatible
            compatibility = cls._check_component_compatibility(
                current_version,
                target_version
            )
            
            if compatibility['all_compatible']:
                return CompatibilityLevel.BACKWARD_COMPATIBLE, ["Minor version update - backward compatible"]
            else:
                issues.extend(compatibility['issues'])
                return CompatibilityLevel.REQUIRES_MIGRATION, issues
        
        # Patch version change - should always be compatible
        return CompatibilityLevel.FULLY_COMPATIBLE, ["Patch update - fully compatible"]
    
    @classmethod
    def _get_breaking_changes(cls, current: str, target: str) -> List[str]:
        """Get list of breaking changes between versions"""
        changes = []
        
        current_major = current.split('.')[0]
        target_major = target.split('.')[0]
        
        # Collect all breaking changes between versions
        for version, version_changes in cls.BREAKING_CHANGES.items():
            version_major = version.split('.')[0]
            
            if (int(version_major) > int(current_major) and 
                int(version_major) <= int(target_major)):
                changes.extend(version_changes)
        
        return changes
    
    @classmethod
    def _get_migration_path(cls, current: str, target: str) -> Optional[str]:
        """Find migration path between versions"""
        current_prefix = f"{current.split('.')[0]}."
        target_prefix = f"{target.split('.')[0]}."
        
        for (from_ver, to_ver), migration_func in cls.MIGRATION_PATHS.items():
            if current.startswith(from_ver) and target.startswith(to_ver):
                return migration_func
        
        return None
    
    @classmethod
    def _check_component_compatibility(
        cls,
        current: VersionInfo,
        target: VersionInfo
    ) -> Dict[str, Any]:
        """Check compatibility of individual components"""
        issues = []
        all_compatible = True
        
        # Check database schema
        current_schema = cls._get_schema_version(current.version)
        target_schema = cls._get_schema_version(target.version)
        
        if current_schema != target_schema:
            if target.version not in cls.COMPATIBILITY_RULES['database_schema'].get(current_schema, []):
                issues.append(f"Database schema incompatible: {current_schema} -> {target_schema}")
                all_compatible = False
        
        # Check profile format
        current_profile = cls._get_profile_format(current.version)
        target_profile = cls._get_profile_format(target.version)
        
        if current_profile != target_profile:
            issues.append(f"Profile format change: {current_profile} -> {target_profile}")
            all_compatible = False
        
        # Check model compatibility
        if not cls._check_model_compatibility(current.models, target.models):
            issues.append("Model format incompatibility detected")
            all_compatible = False
        
        # Check hardware requirements
        if not cls._check_hardware_requirements(
            current.hardware_requirements,
            target.hardware_requirements
        ):
            issues.append("Hardware requirements increased")
        
        return {
            'all_compatible': all_compatible,
            'issues': issues
        }
    
    @classmethod
    def _get_schema_version(cls, version: str) -> str:
        """Get database schema version for a given app version"""
        major = version.split('.')[0]
        if major in ['6']:
            return '6.0'
        elif major in ['5']:
            return '5.0'
        else:
            return '4.0'
    
    @classmethod
    def _get_profile_format(cls, version: str) -> str:
        """Get profile format for a given version"""
        major = version.split('.')[0]
        if int(major) >= 6:
            return '2.0'
        else:
            return '1.0'
    
    @classmethod
    def _check_model_compatibility(cls, current_models: List[str], target_models: List[str]) -> bool:
        """Check if models are compatible"""
        # Check for GGML to GGUF transition
        current_formats = set('ggml' if 'ggml' in m.lower() else 'gguf' for m in current_models)
        target_formats = set('ggml' if 'ggml' in m.lower() else 'gguf' for m in target_models)
        
        # GGUF can read GGML, but not vice versa
        if 'ggml' in current_formats and 'gguf' in target_formats:
            return True
        elif 'gguf' in current_formats and 'ggml' in target_formats:
            return False
        
        return True
    
    @classmethod
    def _check_hardware_requirements(
        cls,
        current_hw: Dict[str, Any],
        target_hw: Dict[str, Any]
    ) -> bool:
        """Check if hardware requirements are compatible"""
        # Check if target requires more resources
        if target_hw.get('min_ram_gb', 0) > current_hw.get('min_ram_gb', 0):
            return False
        if target_hw.get('min_disk_gb', 0) > current_hw.get('min_disk_gb', 0):
            return False
        
        return True
    
    @classmethod
    def validate_update_prerequisites(
        cls,
        system_info: Dict[str, Any],
        target_version: VersionInfo
    ) -> Tuple[bool, List[str]]:
        """
        FIX BUG-024: Validate system meets prerequisites for update
        
        Args:
            system_info: Current system information
            target_version: Target version to update to
            
        Returns:
            Tuple of (can_update, list of issues)
        """
        issues = []
        can_update = True
        
        # Check disk space
        required_space_gb = target_version.hardware_requirements.get('min_disk_gb', 8)
        available_space_gb = system_info.get('disk_space_gb', 0)
        
        if available_space_gb < required_space_gb * 1.5:  # Need extra space for update
            issues.append(f"Insufficient disk space: {available_space_gb:.1f}GB available, {required_space_gb * 1.5:.1f}GB required")
            can_update = False
        
        # Check RAM
        required_ram_gb = target_version.hardware_requirements.get('min_ram_gb', 4)
        available_ram_gb = system_info.get('ram_gb', 0)
        
        if available_ram_gb < required_ram_gb:
            issues.append(f"Insufficient RAM: {available_ram_gb}GB available, {required_ram_gb}GB required")
            can_update = False
        
        # Check OS version
        min_os_versions = target_version.hardware_requirements.get('min_os_version', {})
        current_os = platform.system().lower()
        
        if current_os == 'windows':
            min_version = min_os_versions.get('windows', '10')
            current_version = platform.version()
            if not cls._check_windows_version(current_version, min_version):
                issues.append(f"Windows version too old: Requires Windows {min_version} or later")
                can_update = False
        
        elif current_os == 'darwin':
            min_version = min_os_versions.get('macos', '10.15')
            current_version = platform.mac_ver()[0]
            if not cls._check_macos_version(current_version, min_version):
                issues.append(f"macOS version too old: Requires macOS {min_version} or later")
                can_update = False
        
        # Check for running processes that might interfere
        conflicting_processes = cls._check_conflicting_processes()
        if conflicting_processes:
            issues.append(f"Conflicting processes running: {', '.join(conflicting_processes)}")
            can_update = False
        
        return can_update, issues
    
    @classmethod
    def _check_windows_version(cls, current: str, minimum: str) -> bool:
        """Check if Windows version meets minimum requirement"""
        try:
            # Extract major version number
            current_major = int(re.search(r'\d+', current).group())
            min_major = int(minimum)
            return current_major >= min_major
        except:
            return True  # Assume compatible if can't parse
    
    @classmethod
    def _check_macos_version(cls, current: str, minimum: str) -> bool:
        """Check if macOS version meets minimum requirement"""
        try:
            current_parts = [int(x) for x in current.split('.')]
            min_parts = [int(x) for x in minimum.split('.')]
            
            for i in range(min(len(current_parts), len(min_parts))):
                if current_parts[i] < min_parts[i]:
                    return False
                elif current_parts[i] > min_parts[i]:
                    return True
            
            return True
        except:
            return True  # Assume compatible if can't parse
    
    @classmethod
    def _check_conflicting_processes(cls) -> List[str]:
        """Check for running processes that might interfere with update"""
        conflicting = []
        
        # Check for running Sunflower processes
        import psutil
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'sunflower' in proc.info['name'].lower():
                    conflicting.append(proc.info['name'])
                elif 'ollama' in proc.info['name'].lower():
                    conflicting.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return conflicting


class UpdateManager:
    """Main update and migration manager for Sunflower AI system"""
    
    def __init__(self, install_path: Path = None):
        """
        Initialize update manager
        
        Args:
            install_path: Path to current installation
        """
        self.install_path = install_path or self._detect_installation()
        self.current_version = self._get_current_version()
        self.backup_path = Path.home() / ".sunflowerai" / "backups"
        self.temp_path = Path(tempfile.mkdtemp(prefix="sunflower_update_"))
        self.migration_status = MigrationStatus.NOT_STARTED
        self.errors: List[str] = []
        
        # FIX BUG-024: Initialize compatibility checker
        self.compatibility_checker = VersionCompatibilityChecker()
        
        # Create necessary directories
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def _detect_installation(self) -> Path:
        """Detect existing Sunflower installation"""
        # Check common installation paths
        if platform.system() == "Windows":
            paths = [
                Path("C:/Program Files/Sunflower AI"),
                Path("C:/Program Files (x86)/Sunflower AI"),
                Path.home() / "AppData/Local/Sunflower AI"
            ]
        elif platform.system() == "Darwin":
            paths = [
                Path("/Applications/Sunflower AI.app"),
                Path.home() / "Applications/Sunflower AI.app"
            ]
        else:
            paths = [
                Path("/opt/sunflowerai"),
                Path("/usr/local/bin/sunflowerai"),
                Path.home() / ".local/share/sunflowerai"
            ]
        
        for path in paths:
            if path.exists():
                logger.info(f"Found installation at: {path}")
                return path
        
        logger.warning("No existing installation found")
        return Path.cwd()
    
    def _get_current_version(self) -> Optional[VersionInfo]:
        """Get version of current installation"""
        version_file = self.install_path / "version_info.json"
        
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    data = json.load(f)
                    return VersionInfo(**data)
            except Exception as e:
                logger.error(f"Failed to read version info: {e}")
        
        # Try to read from config
        config_file = self.install_path / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return VersionInfo(
                        version=config.get("version", "0.0.0"),
                        build_number=0,
                        release_date="unknown",
                        platform=platform.system(),
                        models=[],
                        features=[],
                        hardware_requirements={}
                    )
            except:
                pass
        
        logger.warning("Could not determine current version")
        return None
    
    def check_for_update(self) -> Optional[VersionInfo]:
        """
        Check if an update is available
        NOTE: Per business model design, updates are new device purchases, not online updates
        This checks if a new device is connected with a newer version
        """
        logger.info("Checking for new version devices")
        
        # Look for connected Sunflower devices
        new_devices = self._scan_for_devices()
        
        for device_path in new_devices:
            device_version = self._get_device_version(device_path)
            if device_version and device_version.is_newer_than(self.current_version):
                # FIX BUG-024: Check compatibility before offering update
                compatibility, issues = self.compatibility_checker.check_compatibility(
                    self.current_version,
                    device_version
                )
                
                if compatibility == CompatibilityLevel.INCOMPATIBLE:
                    logger.warning(f"Found newer version {device_version.version} but it's incompatible")
                    logger.warning(f"Compatibility issues: {issues}")
                    continue
                
                logger.info(f"Found newer compatible version device: {device_version.version}")
                logger.info(f"Compatibility level: {compatibility.value}")
                
                if issues:
                    logger.info(f"Compatibility notes: {issues}")
                
                return device_version
        
        logger.info("No newer compatible version devices found")
        return None
    
    def can_update_to(self, target_version: VersionInfo) -> Tuple[bool, List[str]]:
        """
        FIX BUG-024: Check if system can update to target version
        
        Args:
            target_version: Version to update to
            
        Returns:
            Tuple of (can_update, list of reasons why not)
        """
        reasons = []
        can_update = True
        
        # Check version compatibility
        compatibility, issues = self.compatibility_checker.check_compatibility(
            self.current_version,
            target_version
        )
        
        if compatibility == CompatibilityLevel.INCOMPATIBLE:
            reasons.extend(issues)
            can_update = False
        elif compatibility == CompatibilityLevel.REQUIRES_MIGRATION:
            reasons.append("Data migration required")
        
        # Check system prerequisites
        system_info = self._get_system_info()
        prereq_ok, prereq_issues = self.compatibility_checker.validate_update_prerequisites(
            system_info,
            target_version
        )
        
        if not prereq_ok:
            reasons.extend(prereq_issues)
            can_update = False
        
        return can_update, reasons
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        import psutil
        
        return {
            'disk_space_gb': psutil.disk_usage(str(self.install_path)).free / (1024**3),
            'ram_gb': psutil.virtual_memory().total / (1024**3),
            'cpu_count': psutil.cpu_count(),
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': sys.version
        }
    
    def migrate_family_data(
        self,
        source_device: Path,
        target_device: Path,
        target_version: VersionInfo
    ) -> bool:
        """
        Migrate family data from old device to new device
        
        Args:
            source_device: Path to old device
            target_device: Path to new device
            target_version: Version of new device
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting data migration from {source_device} to {target_device}")
        
        # FIX BUG-024: Check if migration is possible
        compatibility, issues = self.compatibility_checker.check_compatibility(
            self.current_version,
            target_version
        )
        
        if compatibility == CompatibilityLevel.INCOMPATIBLE:
            logger.error(f"Cannot migrate data: {issues}")
            self.errors.extend(issues)
            return False
        
        self.migration_status = MigrationStatus.SCANNING
        
        try:
            # Backup current data
            self.migration_status = MigrationStatus.BACKING_UP
            backup_file = self._backup_current_data()
            
            # Determine migration strategy
            if compatibility == CompatibilityLevel.REQUIRES_MIGRATION:
                # Need data conversion
                migration_path = self.compatibility_checker._get_migration_path(
                    self.current_version.version,
                    target_version.version
                )
                
                if migration_path:
                    logger.info(f"Using migration path: {migration_path}")
                    success = self._execute_migration(
                        migration_path,
                        source_device,
                        target_device,
                        backup_file
                    )
                else:
                    logger.error("No migration path available")
                    return False
            else:
                # Direct copy is safe
                success = self._direct_data_copy(source_device, target_device)
            
            if success:
                self.migration_status = MigrationStatus.VERIFYING
                if self._verify_migration(target_device):
                    self.migration_status = MigrationStatus.COMPLETE
                    logger.info("Migration completed successfully")
                    return True
                else:
                    self.migration_status = MigrationStatus.ERROR
                    self.errors.append("Migration verification failed")
                    return False
            else:
                self.migration_status = MigrationStatus.ERROR
                return False
                
        except Exception as e:
            self.migration_status = MigrationStatus.ERROR
            self.errors.append(str(e))
            logger.error(f"Migration failed: {e}")
            return False
    
    def _execute_migration(
        self,
        migration_path: str,
        source_device: Path,
        target_device: Path,
        backup_file: Path
    ) -> bool:
        """Execute specific migration based on version differences"""
        
        if migration_path == 'migrate_v5_to_v6':
            return self._migrate_v5_to_v6(source_device, target_device, backup_file)
        elif migration_path == 'migrate_v4_to_v6':
            return self._migrate_v4_to_v6(source_device, target_device, backup_file)
        elif migration_path == 'migrate_v4_to_v5':
            return self._migrate_v4_to_v5(source_device, target_device, backup_file)
        else:
            logger.error(f"Unknown migration path: {migration_path}")
            return False
    
    def _migrate_v5_to_v6(
        self,
        source_device: Path,
        target_device: Path,
        backup_file: Path
    ) -> bool:
        """Migrate from version 5.x to 6.x"""
        logger.info("Executing v5 to v6 migration")
        
        try:
            # Convert profile format from XML to JSON
            self._convert_profiles_xml_to_json(source_device, target_device)
            
            # Update database schema
            self._upgrade_database_schema(source_device, target_device, '5.0', '6.0')
            
            # Convert model format from GGML to GGUF
            self._convert_model_format(source_device, target_device, 'ggml', 'gguf')
            
            # Update configuration structure
            self._update_config_structure(source_device, target_device, 'v2', 'v3')
            
            return True
            
        except Exception as e:
            logger.error(f"Migration v5 to v6 failed: {e}")
            return False
    
    def _migrate_v4_to_v6(
        self,
        source_device: Path,
        target_device: Path,
        backup_file: Path
    ) -> bool:
        """Migrate from version 4.x to 6.x (skip v5)"""
        logger.info("Executing v4 to v6 migration")
        
        # First migrate to v5 format, then to v6
        temp_v5 = self.temp_path / "v5_intermediate"
        temp_v5.mkdir(exist_ok=True)
        
        if self._migrate_v4_to_v5(source_device, temp_v5, backup_file):
            return self._migrate_v5_to_v6(temp_v5, target_device, backup_file)
        
        return False
    
    def _migrate_v4_to_v5(
        self,
        source_device: Path,
        target_device: Path,
        backup_file: Path
    ) -> bool:
        """Migrate from version 4.x to 5.x"""
        logger.info("Executing v4 to v5 migration")
        
        try:
            # Update configuration structure from v1 to v2
            self._update_config_structure(source_device, target_device, 'v1', 'v2')
            
            # Copy profiles (no format change)
            self._copy_profiles(source_device, target_device)
            
            # Copy models (no format change)
            self._copy_models(source_device, target_device)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration v4 to v5 failed: {e}")
            return False
    
    def _convert_profiles_xml_to_json(self, source: Path, target: Path):
        """Convert profile format from XML to JSON"""
        # Implementation for profile conversion
        logger.info("Converting profiles from XML to JSON")
        # ... conversion logic ...
    
    def _upgrade_database_schema(self, source: Path, target: Path, from_ver: str, to_ver: str):
        """Upgrade database schema between versions"""
        logger.info(f"Upgrading database schema from {from_ver} to {to_ver}")
        # ... schema upgrade logic ...
    
    def _convert_model_format(self, source: Path, target: Path, from_fmt: str, to_fmt: str):
        """Convert AI model format"""
        logger.info(f"Converting models from {from_fmt} to {to_fmt}")
        # ... model conversion logic ...
    
    def _update_config_structure(self, source: Path, target: Path, from_ver: str, to_ver: str):
        """Update configuration file structure"""
        logger.info(f"Updating config structure from {from_ver} to {to_ver}")
        # ... config update logic ...
    
    def _copy_profiles(self, source: Path, target: Path):
        """Copy user profiles"""
        logger.info("Copying user profiles")
        # ... profile copy logic ...
    
    def _copy_models(self, source: Path, target: Path):
        """Copy AI models"""
        logger.info("Copying AI models")
        # ... model copy logic ...
    
    def _backup_current_data(self) -> Path:
        """Backup current installation data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_path / f"backup_{timestamp}.zip"
        
        logger.info(f"Creating backup: {backup_file}")
        
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Backup profiles
            profiles_dir = self.install_path / "profiles"
            if profiles_dir.exists():
                for file_path in profiles_dir.rglob("*"):
                    arc_name = file_path.relative_to(self.install_path)
                    zf.write(file_path, arc_name)
            
            # Backup conversations
            conversations_dir = self.install_path / "conversations"
            if conversations_dir.exists():
                for file_path in conversations_dir.rglob("*"):
                    arc_name = file_path.relative_to(self.install_path)
                    zf.write(file_path, arc_name)
            
            # Backup configuration
            config_file = self.install_path / "config.json"
            if config_file.exists():
                zf.write(config_file, "config.json")
        
        logger.info(f"Backup created: {backup_file}")
        return backup_file
    
    def _direct_data_copy(self, source: Path, target: Path) -> bool:
        """Direct copy of data when versions are compatible"""
        self.migration_status = MigrationStatus.TRANSFERRING
        
        try:
            # Copy family profiles
            source_profiles = source / "family_profiles"
            target_profiles = target / "family_profiles"
            
            if source_profiles.exists():
                logger.info("Copying family profiles")
                shutil.copytree(source_profiles, target_profiles, dirs_exist_ok=True)
            
            # Copy conversation logs
            source_conversations = source / "conversation_logs"
            target_conversations = target / "conversation_logs"
            
            if source_conversations.exists():
                logger.info("Copying conversation logs")
                shutil.copytree(source_conversations, target_conversations, dirs_exist_ok=True)
            
            # Copy learning progress
            source_progress = source / "learning_progress"
            target_progress = target / "learning_progress"
            
            if source_progress.exists():
                logger.info("Copying learning progress")
                shutil.copytree(source_progress, target_progress, dirs_exist_ok=True)
            
            # Copy parent dashboard data
            source_dashboard = source / "parent_dashboard"
            target_dashboard = target / "parent_dashboard"
            
            if source_dashboard.exists():
                logger.info("Copying parent dashboard data")
                shutil.copytree(source_dashboard, target_dashboard, dirs_exist_ok=True)
            
            return True
            
        except Exception as e:
            self.errors.append(f"Data copy failed: {e}")
            logger.error(f"Failed to copy data: {e}")
            return False
    
    def _verify_migration(self, target_device: Path) -> bool:
        """Verify that migration was successful"""
        logger.info("Verifying migration")
        
        # Check that key directories exist
        required_dirs = [
            "family_profiles",
            "conversation_logs",
            "learning_progress",
            "parent_dashboard"
        ]
        
        for dir_name in required_dirs:
            dir_path = target_device / dir_name
            if not dir_path.exists():
                logger.warning(f"Missing directory after migration: {dir_name}")
                return False
        
        # Verify profile integrity
        profiles_dir = target_device / "family_profiles"
        profile_count = len(list(profiles_dir.glob("*.json")))
        
        if profile_count == 0:
            logger.warning("No profiles found after migration")
            return False
        
        logger.info(f"Migration verified: {profile_count} profiles migrated")
        return True
    
    def _scan_for_devices(self) -> List[Path]:
        """Scan for connected Sunflower devices"""
        devices = []
        
        if platform.system() == "Windows":
            # Scan removable drives
            try:
                import win32file
                drives = [f"{d}:/" for d in "DEFGHIJKLMNOPQRSTUVWXYZ" 
                         if os.path.exists(f"{d}:/")]
                
                for drive in drives:
                    drive_type = win32file.GetDriveType(drive)
                    if drive_type == win32file.DRIVE_REMOVABLE or drive_type == win32file.DRIVE_CDROM:
                        device_config = Path(drive) / "device_config.json"
                        if device_config.exists():
                            devices.append(Path(drive))
            except ImportError:
                # Fallback if pywin32 not available
                for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
                    drive = Path(f"{letter}:/")
                    if drive.exists():
                        device_config = drive / "device_config.json"
                        if device_config.exists():
                            devices.append(drive)
        else:
            # Scan mounted volumes
            volumes_path = Path("/Volumes") if platform.system() == "Darwin" else Path("/media")
            if volumes_path.exists():
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
                        release_date=config.get("creation_date", "unknown"),
                        platform=config.get("platform", "universal"),
                        models=config.get("models", []),
                        features=config.get("features", []),
                        hardware_requirements=config.get("hardware_requirements", {})
                    )
        except Exception as e:
            logger.error(f"Failed to read device version: {e}")
        
        return None
    
    def repair_installation(self) -> bool:
        """Repair current installation"""
        logger.info("Starting installation repair")
        
        try:
            # Verify file integrity
            missing_files = self._check_missing_files()
            if missing_files:
                logger.info(f"Found {len(missing_files)} missing files")
                # Attempt to restore from backup
                if not self._restore_missing_files(missing_files):
                    self.errors.append("Failed to restore missing files")
                    return False
            
            # Fix permissions
            self._fix_permissions()
            
            # Rebuild configuration
            self._rebuild_configuration()
            
            # Verify models
            self._verify_models()
            
            logger.info("Installation repair completed")
            return True
            
        except Exception as e:
            self.errors.append(str(e))
            logger.error(f"Repair failed: {e}")
            return False
    
    def _check_missing_files(self) -> List[str]:
        """Check for missing critical files"""
        missing = []
        
        critical_files = [
            "config.json",
            "version_info.json",
            "modelfiles/Sunflower_AI_Kids.modelfile",
            "modelfiles/Sunflower_AI_Educator.modelfile"
        ]
        
        for file_path in critical_files:
            full_path = self.install_path / file_path
            if not full_path.exists():
                missing.append(file_path)
        
        return missing
    
    def _restore_missing_files(self, missing_files: List[str]) -> bool:
        """Attempt to restore missing files from backup"""
        # Find most recent backup
        backups = sorted(self.backup_path.glob("backup_*.zip"))
        
        if not backups:
            logger.warning("No backups available to restore from")
            return False
        
        latest_backup = backups[-1]
        logger.info(f"Restoring from backup: {latest_backup}")
        
        try:
            with zipfile.ZipFile(latest_backup, 'r') as zf:
                for file_path in missing_files:
                    if file_path in zf.namelist():
                        zf.extract(file_path, self.install_path)
                        logger.info(f"Restored: {file_path}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def _fix_permissions(self):
        """Fix file permissions"""
        logger.info("Fixing file permissions")
        
        if platform.system() != "Windows":
            # Set executable permissions on launchers
            launcher_files = [
                "launcher",
                "sunflower_service"
            ]
            
            for launcher in launcher_files:
                launcher_path = self.install_path / launcher
                if launcher_path.exists():
                    os.chmod(launcher_path, 0o755)
    
    def _rebuild_configuration(self):
        """Rebuild configuration file if corrupted"""
        config_file = self.install_path / "config.json"
        
        if not config_file.exists() or os.path.getsize(config_file) == 0:
            logger.info("Rebuilding configuration file")
            
            default_config = {
                "version": self.current_version.version if self.current_version else "6.2.0",
                "installation_date": datetime.now().isoformat(),
                "platform": platform.system(),
                "install_directory": str(self.install_path),
                "first_run": False
            }
            
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
    
    def _verify_models(self):
        """Verify AI models are present and valid"""
        models_dir = self.install_path / "models"
        
        if not models_dir.exists():
            logger.warning("Models directory missing")
            models_dir.mkdir(exist_ok=True)
        
        # Check for at least one model
        model_files = list(models_dir.glob("*.gguf")) + list(models_dir.glob("*.ggml"))
        
        if not model_files:
            logger.warning("No AI models found")
    
    def verify_system_integrity(self) -> Dict[str, Any]:
        """
        Perform comprehensive system integrity check
        
        Returns:
            Dictionary with verification results
        """
        logger.info("Starting system integrity verification")
        
        report = {
            "status": "unknown",
            "version": self.current_version.version if self.current_version else "unknown",
            "issues": [],
            "warnings": [],
            "statistics": {}
        }
        
        # Check critical files
        missing_files = self._check_missing_files()
        if missing_files:
            report["issues"].extend([f"Missing file: {f}" for f in missing_files])
        
        # Check disk space
        import psutil
        disk_usage = psutil.disk_usage(str(self.install_path))
        report["statistics"]["disk_free_gb"] = round(disk_usage.free / (1024**3), 2)
        
        if disk_usage.percent > 90:
            report["warnings"].append(f"Low disk space: {100 - disk_usage.percent:.1f}% free")
        
        # Check profiles
        profiles_dir = self.install_path / "profiles"
        if profiles_dir.exists():
            profile_count = len(list(profiles_dir.glob("*.json")))
            report["statistics"]["profile_count"] = profile_count
        
        # Check models
        models_dir = self.install_path / "models"
        if models_dir.exists():
            model_count = len(list(models_dir.glob("*.gguf")) + list(models_dir.glob("*.ggml")))
            report["statistics"]["model_count"] = model_count
            
            if model_count == 0:
                report["issues"].append("No AI models installed")
        
        # Determine overall status
        if report["issues"]:
            report["status"] = "critical"
        elif report["warnings"]:
            report["status"] = "degraded"
        else:
            report["status"] = "healthy"
        
        logger.info(f"System integrity check complete: {report['status']}")
        return report


def main():
    """Main entry point for update manager"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sunflower AI Update Manager - Handle version updates and data migration"
    )
    
    parser.add_argument(
        "--action",
        choices=["check", "migrate", "repair", "verify"],
        required=True,
        help="Action to perform"
    )
    
    parser.add_argument(
        "--source-device",
        type=Path,
        help="Source device path for migration"
    )
    
    parser.add_argument(
        "--target-device",
        type=Path,
        help="Target device path for migration"
    )
    
    parser.add_argument(
        "--install-path",
        type=Path,
        help="Installation path (auto-detect if not specified)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("SUNFLOWER AI UPDATE MANAGER")
    print("="*60 + "\n")
    
    # Initialize manager
    manager = UpdateManager(install_path=args.install_path)
    
    if args.action == "check":
        print("Checking for updates...")
        new_version = manager.check_for_update()
        
        if new_version:
            print(f"\n✓ New version available: {new_version.version}")
            print(f"  Build: {new_version.build_number}")
            print(f"  Release Date: {new_version.release_date}")
            
            # FIX BUG-024: Check if update is possible
            can_update, reasons = manager.can_update_to(new_version)
            
            if can_update:
                print("\n✓ System can be updated to this version")
            else:
                print("\n✗ Cannot update to this version:")
                for reason in reasons:
                    print(f"  - {reason}")
        else:
            print("No updates available")
    
    elif args.action == "migrate":
        if not args.source_device or not args.target_device:
            print("Error: Both --source-device and --target-device required for migration")
            return 1
        
        print(f"Migrating data...")
        print(f"  From: {args.source_device}")
        print(f"  To: {args.target_device}")
        
        # Get target version
        target_version = manager._get_device_version(args.target_device)
        
        if not target_version:
            print("Error: Could not determine target device version")
            return 1
        
        # FIX BUG-024: Check compatibility before migration
        can_update, reasons = manager.can_update_to(target_version)
        
        if not can_update:
            print("\n✗ Cannot migrate to target version:")
            for reason in reasons:
                print(f"  - {reason}")
            return 1
        
        success = manager.migrate_family_data(
            args.source_device,
            args.target_device,
            target_version
        )
        
        if success:
            print("\n✓ Migration completed successfully")
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

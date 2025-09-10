#!/usr/bin/env python3
"""
Sunflower AI Professional System - Configuration Manager
Centralized configuration management with thread safety and proper resource handling
Version: 6.2.0 - Production Ready

BUGS FIXED:
1. BUG-004: Fixed file handle leak in partition detection (CRITICAL)
2. BUG-009: Added thread synchronization for config loading (HIGH)
3. BUG-018: Fixed null value handling in get() method (HIGH)
"""

import os
import sys
import json
import yaml
import threading
import platform
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """Configuration types"""
    SYSTEM = "system"
    SAFETY = "safety"
    MODEL = "model"
    NETWORK = "network"
    SECURITY = "security"
    USER = "user"


@dataclass
class SystemConfig:
    """System configuration"""
    version: str
    platform: str
    architecture: str
    debug_mode: bool = False
    offline_mode: bool = False
    data_retention_days: int = 90
    session_timeout_minutes: int = 60
    max_concurrent_sessions: int = 5


@dataclass
class SafetyConfig:
    """Safety configuration"""
    enabled: bool = True
    filter_level: str = "maximum"
    age_verification: bool = True
    content_logging: bool = True
    incident_reporting: bool = True
    parent_alerts: bool = True
    blocked_terms_update: bool = False


@dataclass
class ModelConfig:
    """Model configuration"""
    name: str
    variant: str
    path: str
    size_mb: int
    requires_gpu: bool = False
    min_ram_gb: int = 4
    context_length: int = 2048
    temperature: float = 0.7


@dataclass
class NetworkConfig:
    """Network configuration"""
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    webui_host: str = "localhost"
    webui_port: int = 8080
    api_timeout: int = 30
    max_retries: int = 3
    offline_mode: bool = False
    proxy_enabled: bool = False


@dataclass
class SecurityConfig:
    """Security configuration"""
    require_authentication: bool = True
    encryption_enabled: bool = True
    session_timeout_minutes: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    require_parent_pin: bool = True
    pin_length: int = 6
    two_factor_enabled: bool = False
    audit_logging: bool = True
    secure_erase: bool = True


# Sentinel object for distinguishing None from missing values (FIX for BUG-018)
_MISSING = object()


class ConfigurationManager:
    """
    Enhanced configuration manager with thread safety and resource management
    """
    
    def __init__(self, cdrom_path: Optional[Path] = None, usb_path: Optional[Path] = None):
        """
        Initialize configuration manager
        
        Args:
            cdrom_path: Path to CD-ROM partition
            usb_path: Path to USB partition
        """
        self.cdrom_path = Path(cdrom_path) if cdrom_path else self._detect_cdrom()
        self.usb_path = Path(usb_path) if usb_path else self._detect_usb()
        
        # Configuration storage
        self._configs = {}
        self._env_vars = {}
        
        # FIX for BUG-009: Add thread lock for thread-safe operations
        self._lock = threading.RLock()
        
        # Configuration paths
        self.system_config_path = self.cdrom_path / "config" if self.cdrom_path else Path("config")
        self.user_config_path = self.usb_path / "config" if self.usb_path else Path("user_config")
        self.model_config_path = self.cdrom_path / "modelfiles" if self.cdrom_path else Path("modelfiles")
        self.safety_config_path = self.usb_path / "safety" if self.usb_path else Path("safety")
        
        # Create necessary directories
        self.user_config_path.mkdir(parents=True, exist_ok=True)
        self.safety_config_path.mkdir(parents=True, exist_ok=True)
        
        # Load configurations with thread safety
        self._load_all_configs()
        
        logger.info("Configuration manager initialized")
    
    def _detect_cdrom(self) -> Optional[Path]:
        """Detect CD-ROM partition (FIX for BUG-004: Proper error handling)"""
        if platform.system() == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                marker_file = drive_path / "sunflower_cd.id"
                
                # FIX for BUG-004: Proper exception handling for file operations
                try:
                    if marker_file.exists():
                        logger.info(f"Found CD-ROM partition at {drive_path}")
                        return drive_path
                except (OSError, PermissionError) as e:
                    logger.debug(f"Cannot access drive {drive}: {e}")
                    continue
        
        elif platform.system() == "Darwin":  # macOS
            volumes = Path("/Volumes")
            
            # FIX for BUG-004: Safe iteration with error handling
            try:
                for volume in volumes.iterdir():
                    marker_file = volume / "sunflower_cd.id"
                    try:
                        if marker_file.exists():
                            logger.info(f"Found CD-ROM partition at {volume}")
                            return volume
                    except (OSError, PermissionError) as e:
                        logger.debug(f"Cannot access volume {volume}: {e}")
                        continue
            except (OSError, PermissionError) as e:
                logger.warning(f"Cannot access /Volumes: {e}")
        
        return None
    
    def _detect_usb(self) -> Optional[Path]:
        """Detect USB partition (FIX for BUG-004: Proper error handling)"""
        if platform.system() == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                marker_file = drive_path / "sunflower_data.id"
                
                # FIX for BUG-004: Proper exception handling for file operations
                try:
                    if marker_file.exists():
                        logger.info(f"Found USB partition at {drive_path}")
                        return drive_path
                except (OSError, PermissionError) as e:
                    logger.debug(f"Cannot access drive {drive}: {e}")
                    continue
        
        elif platform.system() == "Darwin":  # macOS
            volumes = Path("/Volumes")
            
            # FIX for BUG-004: Safe iteration with error handling
            try:
                for volume in volumes.iterdir():
                    marker_file = volume / "sunflower_data.id"
                    try:
                        if marker_file.exists():
                            logger.info(f"Found USB partition at {volume}")
                            return volume
                    except (OSError, PermissionError) as e:
                        logger.debug(f"Cannot access volume {volume}: {e}")
                        continue
            except (OSError, PermissionError) as e:
                logger.warning(f"Cannot access /Volumes: {e}")
        
        return None
    
    def _load_all_configs(self):
        """Load all configurations (FIX for BUG-009: Thread-safe loading)"""
        # FIX for BUG-009: Use lock for thread-safe configuration loading
        with self._lock:
            try:
                self._load_system_config()
                self._load_safety_config()
                self._load_model_config()
                self._load_network_config()
                self._load_security_config()
                self._load_user_preferences()
                logger.info("All configurations loaded successfully")
            except Exception as e:
                logger.error(f"Error loading configurations: {e}")
                # Load defaults if configs fail
                self._load_defaults()
    
    def _load_system_config(self):
        """Load system configuration"""
        config_file = self.system_config_path / "system.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._configs[ConfigType.SYSTEM] = SystemConfig(**config_data)
                logger.info(f"Loaded system config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load system config: {e}")
                self._load_default_system_config()
        else:
            self._load_default_system_config()
    
    def _load_default_system_config(self):
        """Load default system configuration"""
        self._configs[ConfigType.SYSTEM] = SystemConfig(
            version="6.2.0",
            platform=platform.system(),
            architecture=platform.machine(),
            debug_mode=False,
            offline_mode=False
        )
    
    def _load_safety_config(self):
        """Load safety configuration"""
        config_file = self.safety_config_path / "safety_config.yaml"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._configs[ConfigType.SAFETY] = SafetyConfig(**config_data)
                logger.info(f"Loaded safety config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load safety config: {e}")
                self._load_default_safety_config()
        else:
            self._load_default_safety_config()
    
    def _load_default_safety_config(self):
        """Load default safety configuration"""
        self._configs[ConfigType.SAFETY] = SafetyConfig()
    
    def _load_model_config(self):
        """Load model configurations"""
        self._configs[ConfigType.MODEL] = {}
        
        if self.model_config_path.exists():
            for model_file in self.model_config_path.glob("*.json"):
                try:
                    with open(model_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        model_name = model_file.stem
                        self._configs[ConfigType.MODEL][model_name] = ModelConfig(**config_data)
                    logger.info(f"Loaded model config: {model_file}")
                except Exception as e:
                    logger.error(f"Failed to load model config {model_file}: {e}")
        
        if not self._configs[ConfigType.MODEL]:
            self._load_default_model_config()
    
    def _load_default_model_config(self):
        """Load default model configuration"""
        self._configs[ConfigType.MODEL] = {
            "sunflower-kids": ModelConfig(
                name="sunflower-kids",
                variant="llama3.2:3b",
                path="models/sunflower-kids.gguf",
                size_mb=2048,
                requires_gpu=False,
                min_ram_gb=4
            ),
            "sunflower-educator": ModelConfig(
                name="sunflower-educator",
                variant="llama3.2:7b",
                path="models/sunflower-educator.gguf",
                size_mb=4096,
                requires_gpu=False,
                min_ram_gb=8
            )
        }
    
    def _load_network_config(self):
        """Load network configuration"""
        config_file = self.user_config_path / "network.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._configs[ConfigType.NETWORK] = NetworkConfig(**config_data)
                logger.info(f"Loaded network config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load network config: {e}")
                self._load_default_network_config()
        else:
            self._load_default_network_config()
    
    def _load_default_network_config(self):
        """Load default network configuration"""
        self._configs[ConfigType.NETWORK] = NetworkConfig()
    
    def _load_security_config(self):
        """Load security configuration"""
        config_file = self.user_config_path / "security.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._configs[ConfigType.SECURITY] = SecurityConfig(**config_data)
                logger.info(f"Loaded security config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load security config: {e}")
                self._load_default_security_config()
        else:
            self._load_default_security_config()
    
    def _load_default_security_config(self):
        """Load default security configuration"""
        self._configs[ConfigType.SECURITY] = SecurityConfig()
    
    def _load_user_preferences(self):
        """Load user preferences"""
        prefs_file = self.user_config_path / "preferences.json"
        
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.USER] = json.load(f)
                logger.info(f"Loaded user preferences: {prefs_file}")
            except Exception as e:
                logger.error(f"Failed to load user preferences: {e}")
                self._load_default_user_preferences()
        else:
            self._load_default_user_preferences()
    
    def _load_default_user_preferences(self):
        """Load default user preferences"""
        self._configs[ConfigType.USER] = {
            "theme": "light",
            "language": "en",
            "font_size": "medium",
            "auto_save": True,
            "notifications": True,
            "sound_effects": True,
            "animation_speed": "normal",
            "session_timeout": 60,
            "auto_logout": True
        }
    
    def _load_defaults(self):
        """Load all default configurations"""
        self._load_default_system_config()
        self._load_default_safety_config()
        self._load_default_model_config()
        self._load_default_network_config()
        self._load_default_security_config()
        self._load_default_user_preferences()
        logger.info("Loaded default configurations")
    
    def get(self, config_type: ConfigType, key: Optional[str] = None, default=_MISSING) -> Any:
        """
        Get configuration value (FIX for BUG-018: Proper null/missing value handling)
        
        Args:
            config_type: Type of configuration
            key: Optional specific key within configuration
            default: Default value if key is missing (use _MISSING sentinel)
            
        Returns:
            Configuration value, None if exists but is None, or default if missing
            
        Raises:
            KeyError: If key is missing and no default provided
        """
        with self._lock:
            config = self._configs.get(config_type)
            
            # FIX for BUG-018: Distinguish between None value and missing key
            if config is None:
                if default is _MISSING:
                    raise KeyError(f"Configuration type {config_type} not found")
                return default
            
            if key is None:
                return config
            
            if isinstance(config, dict):
                if key in config:
                    # Key exists, return its value (even if None)
                    return config[key]
                else:
                    # Key doesn't exist
                    if default is _MISSING:
                        raise KeyError(f"Key '{key}' not found in {config_type.value} configuration")
                    return default
            
            # For dataclass configs, use getattr
            if hasattr(config, key):
                return getattr(config, key)
            else:
                if default is _MISSING:
                    raise KeyError(f"Attribute '{key}' not found in {config_type.value} configuration")
                return default
    
    def set(self, config_type: ConfigType, key: str, value: Any):
        """
        Set configuration value (thread-safe)
        
        Args:
            config_type: Type of configuration
            key: Configuration key
            value: New value
        """
        with self._lock:
            if config_type not in self._configs:
                self._configs[config_type] = {}
            
            if isinstance(self._configs[config_type], dict):
                self._configs[config_type][key] = value
                self._save_config(config_type)
            else:
                # For dataclass configs
                setattr(self._configs[config_type], key, value)
                self._save_config(config_type)
    
    def update(self, config_type: ConfigType, updates: Dict[str, Any]):
        """
        Update multiple configuration values (thread-safe)
        
        Args:
            config_type: Type of configuration
            updates: Dictionary of updates
        """
        with self._lock:
            if config_type not in self._configs:
                self._configs[config_type] = {}
            
            if isinstance(self._configs[config_type], dict):
                self._configs[config_type].update(updates)
                self._save_config(config_type)
            else:
                # For dataclass configs
                for key, value in updates.items():
                    if hasattr(self._configs[config_type], key):
                        setattr(self._configs[config_type], key, value)
                self._save_config(config_type)
    
    def _save_config(self, config_type: ConfigType):
        """Save configuration to disk (thread-safe)"""
        try:
            # Determine save path based on config type
            if config_type == ConfigType.SYSTEM:
                # System config is read-only on CD-ROM
                logger.warning("Cannot save system config to CD-ROM")
                return
            
            elif config_type == ConfigType.SAFETY:
                save_path = self.safety_config_path / "safety_config.yaml"
                config = self._configs[config_type]
                
                if isinstance(config, SafetyConfig):
                    config_dict = asdict(config)
                else:
                    config_dict = config
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, default_flow_style=False)
            
            elif config_type == ConfigType.MODEL:
                # Model configs are read-only
                logger.warning("Cannot save model config to CD-ROM")
                return
            
            elif config_type == ConfigType.NETWORK:
                save_path = self.user_config_path / "network.json"
                config = self._configs[config_type]
                
                if isinstance(config, NetworkConfig):
                    config_dict = asdict(config)
                else:
                    config_dict = config
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2)
            
            elif config_type == ConfigType.SECURITY:
                save_path = self.user_config_path / "security.json"
                config = self._configs[config_type]
                
                if isinstance(config, SecurityConfig):
                    config_dict = asdict(config)
                else:
                    config_dict = config
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2)
            
            elif config_type == ConfigType.USER:
                save_path = self.user_config_path / "preferences.json"
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(self._configs[config_type], f, indent=2)
            
            logger.info(f"Saved {config_type.value} configuration to {save_path}")
            
        except Exception as e:
            logger.error(f"Failed to save {config_type.value} configuration: {e}")
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable (thread-safe)"""
        with self._lock:
            return self._env_vars.get(key, os.environ.get(key, default))
    
    def set_env(self, key: str, value: str):
        """Set environment variable (thread-safe)"""
        with self._lock:
            self._env_vars[key] = value
            os.environ[key] = value
    
    def reload(self):
        """Reload all configurations (thread-safe)"""
        logger.info("Reloading configurations...")
        self._load_all_configs()
    
    def get_all(self) -> Dict[ConfigType, Any]:
        """Get all configurations (thread-safe)"""
        with self._lock:
            return dict(self._configs)
    
    def export(self, output_file: Optional[Path] = None) -> Path:
        """Export configuration to file (thread-safe)"""
        with self._lock:
            if not output_file:
                output_file = self.user_config_path / f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {}
            for config_type, config in self._configs.items():
                if isinstance(config, (SystemConfig, SafetyConfig, ModelConfig, NetworkConfig, SecurityConfig)):
                    export_data[config_type.value] = asdict(config)
                else:
                    export_data[config_type.value] = config
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Configuration exported to {output_file}")
            return output_file


# Singleton instance with thread safety
_config_instance: Optional[ConfigurationManager] = None
_instance_lock = threading.Lock()


def get_config() -> ConfigurationManager:
    """Get singleton configuration manager instance (thread-safe)"""
    global _config_instance
    
    if _config_instance is None:
        with _instance_lock:
            # Double-check locking pattern
            if _config_instance is None:
                _config_instance = ConfigurationManager()
    
    return _config_instance


def reset_config() -> None:
    """Reset configuration manager (mainly for testing)"""
    global _config_instance
    with _instance_lock:
        _config_instance = None

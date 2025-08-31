"""
Sunflower AI Professional System - Configuration Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Centralized configuration management for system settings, user preferences,
and runtime parameters. Handles both read-only CD-ROM configs and writable
USB partition overrides.
"""

import os
import sys
import json
import yaml
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import configparser
from threading import Lock

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """Configuration types"""
    SYSTEM = "system"          # Read-only system config from CD-ROM
    USER = "user"              # User overrides from USB
    RUNTIME = "runtime"        # Runtime settings (temporary)
    FAMILY = "family"          # Family profile settings
    SAFETY = "safety"          # Safety and content filters
    MODEL = "model"            # AI model configuration
    HARDWARE = "hardware"      # Hardware optimization settings


@dataclass
class ModelConfig:
    """AI model configuration"""
    name: str
    variant: str
    path: Optional[Path] = None
    size_gb: float = 0.0
    ram_required: int = 4
    parameters: Dict[str, Any] = field(default_factory=dict)
    context_length: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    seed: Optional[int] = None


@dataclass
class SafetyConfig:
    """Safety and content filtering configuration"""
    enabled: bool = True
    age_verification: bool = True
    content_filters: List[str] = field(default_factory=lambda: [
        "violence", "inappropriate", "personal_info", "dangerous"
    ])
    severity_threshold: float = 0.7
    alert_parents: bool = True
    log_incidents: bool = True
    educational_exemptions: List[str] = field(default_factory=lambda: [
        "biology", "history", "science"
    ])
    max_session_minutes: int = 60
    break_reminder_minutes: int = 30


@dataclass
class HardwareConfig:
    """Hardware optimization configuration"""
    tier: str = "standard"
    cpu_cores: int = 2
    ram_gb: int = 4
    gpu_available: bool = False
    gpu_memory_gb: float = 0.0
    optimal_model: str = "llama3.2:1b"
    thread_count: int = 2
    batch_size: int = 512
    use_mmap: bool = True
    use_mlock: bool = False


class ConfigurationManager:
    """
    Manages all system and user configuration with proper precedence:
    1. Runtime overrides (highest priority)
    2. User configuration from USB
    3. System defaults from CD-ROM (lowest priority)
    """
    
    def __init__(self, cdrom_path: Optional[Path] = None, usb_path: Optional[Path] = None):
        """Initialize configuration manager"""
        self.cdrom_path = cdrom_path or self._find_cdrom_path()
        self.usb_path = usb_path or self._find_usb_path()
        self._lock = Lock()
        
        # Configuration storage
        self._configs: Dict[ConfigType, Dict[str, Any]] = {
            ConfigType.SYSTEM: {},
            ConfigType.USER: {},
            ConfigType.RUNTIME: {},
            ConfigType.FAMILY: {},
            ConfigType.SAFETY: {},
            ConfigType.MODEL: {},
            ConfigType.HARDWARE: {}
        }
        
        # Load configurations
        self._load_all_configs()
        
        # Cache for merged configuration
        self._merged_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        
        logger.info(f"Configuration manager initialized - CD-ROM: {self.cdrom_path}, USB: {self.usb_path}")
    
    def _find_cdrom_path(self) -> Optional[Path]:
        """Find CD-ROM partition path"""
        try:
            from .partition_manager import PartitionManager
            pm = PartitionManager()
            return pm.find_cdrom_partition()
        except Exception as e:
            logger.warning(f"Could not find CD-ROM partition: {e}")
            # Development fallback
            dev_path = Path(__file__).parent.parent
            if (dev_path / "config").exists():
                return dev_path
            return None
    
    def _find_usb_path(self) -> Optional[Path]:
        """Find USB data partition path"""
        try:
            from .partition_manager import PartitionManager
            pm = PartitionManager()
            return pm.find_usb_partition()
        except Exception as e:
            logger.warning(f"Could not find USB partition: {e}")
            # Development fallback
            dev_path = Path(__file__).parent.parent / "data"
            if not dev_path.exists():
                dev_path.mkdir(parents=True, exist_ok=True)
            return dev_path
    
    def _load_all_configs(self):
        """Load all configuration files"""
        # Load system configuration from CD-ROM
        if self.cdrom_path:
            self._load_system_config()
            self._load_safety_config()
            self._load_model_config()
        
        # Load user configuration from USB
        if self.usb_path:
            self._load_user_config()
            self._load_family_config()
        
        # Detect and load hardware configuration
        self._load_hardware_config()
    
    def _load_system_config(self):
        """Load read-only system configuration from CD-ROM"""
        config_file = self.cdrom_path / "config" / "version.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.SYSTEM] = json.load(f)
                logger.info(f"Loaded system config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load system config: {e}")
        
        # Load environment variables
        env_file = self.cdrom_path / "config" / "default.env"
        if env_file.exists():
            self._load_env_file(env_file)
    
    def _load_env_file(self, env_file: Path):
        """Load environment variables from .env file"""
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
            logger.info(f"Loaded environment variables from: {env_file}")
        except Exception as e:
            logger.error(f"Failed to load env file: {e}")
    
    def _load_safety_config(self):
        """Load safety and content filtering configuration"""
        config_file = self.cdrom_path / "config" / "safety_patterns.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._configs[ConfigType.SAFETY] = data
                logger.info(f"Loaded safety config with {len(data.get('patterns', []))} patterns")
            except Exception as e:
                logger.error(f"Failed to load safety config: {e}")
        
        # Apply defaults if not loaded
        if not self._configs[ConfigType.SAFETY]:
            self._configs[ConfigType.SAFETY] = asdict(SafetyConfig())
    
    def _load_model_config(self):
        """Load AI model configuration"""
        config_file = self.cdrom_path / "config" / "model_registry.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.MODEL] = json.load(f)
                logger.info(f"Loaded model registry with {len(self._configs[ConfigType.MODEL].get('models', []))} models")
            except Exception as e:
                logger.error(f"Failed to load model config: {e}")
    
    def _load_user_config(self):
        """Load user configuration overrides from USB"""
        config_dir = self.usb_path / ".config"
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / "user_preferences.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.USER] = json.load(f)
                logger.info(f"Loaded user preferences: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load user config: {e}")
    
    def _load_family_config(self):
        """Load family profile configuration from USB"""
        config_file = self.usb_path / "profiles" / "family.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.FAMILY] = json.load(f)
                logger.info(f"Loaded family config with {len(self._configs[ConfigType.FAMILY].get('children', []))} children")
            except Exception as e:
                logger.error(f"Failed to load family config: {e}")
    
    def _load_hardware_config(self):
        """Detect and load hardware configuration"""
        try:
            from .hardware_detector import HardwareDetector
            detector = HardwareDetector()
            hw_info = detector.get_system_info()
            
            self._configs[ConfigType.HARDWARE] = {
                "tier": detector.get_hardware_tier(),
                "cpu_cores": hw_info["cpu"]["cores"],
                "ram_gb": hw_info["memory"]["total_gb"],
                "gpu_available": hw_info["gpu"]["available"],
                "gpu_memory_gb": hw_info["gpu"].get("memory_gb", 0),
                "optimal_model": detector.get_optimal_model(),
                "thread_count": detector.get_optimal_threads(),
                "batch_size": 512 if hw_info["memory"]["total_gb"] >= 8 else 256
            }
            logger.info(f"Hardware config: {self._configs[ConfigType.HARDWARE]['tier']} tier, {self._configs[ConfigType.HARDWARE]['optimal_model']} model")
        except Exception as e:
            logger.error(f"Failed to detect hardware: {e}")
            self._configs[ConfigType.HARDWARE] = asdict(HardwareConfig())
    
    def get(self, key: str, default: Any = None, config_type: Optional[ConfigType] = None) -> Any:
        """
        Get configuration value with proper precedence.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if not found
            config_type: Specific config type to query
        
        Returns:
            Configuration value or default
        """
        with self._lock:
            if config_type:
                return self._get_nested(self._configs.get(config_type, {}), key, default)
            
            # Check precedence: Runtime > User > System
            for cfg_type in [ConfigType.RUNTIME, ConfigType.USER, ConfigType.SYSTEM]:
                value = self._get_nested(self._configs.get(cfg_type, {}), key, None)
                if value is not None:
                    return value
            
            # Check other config types
            for cfg_type in [ConfigType.FAMILY, ConfigType.SAFETY, ConfigType.MODEL, ConfigType.HARDWARE]:
                value = self._get_nested(self._configs.get(cfg_type, {}), key, None)
                if value is not None:
                    return value
            
            return default
    
    def _get_nested(self, data: Dict, key: str, default: Any) -> Any:
        """Get nested dictionary value using dot notation"""
        keys = key.split('.')
        value = data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, config_type: ConfigType = ConfigType.RUNTIME, persist: bool = False):
        """
        Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            config_type: Config type to update
            persist: Whether to save to disk (USB partition only)
        """
        with self._lock:
            self._set_nested(self._configs[config_type], key, value)
            self._merged_cache = None  # Invalidate cache
            
            if persist and config_type == ConfigType.USER and self.usb_path:
                self._save_user_config()
    
    def _set_nested(self, data: Dict, key: str, value: Any):
        """Set nested dictionary value using dot notation"""
        keys = key.split('.')
        current = data
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _save_user_config(self):
        """Save user configuration to USB partition"""
        if not self.usb_path:
            logger.warning("Cannot save user config: USB path not available")
            return
        
        config_dir = self.usb_path / ".config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / "user_preferences.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._configs[ConfigType.USER], f, indent=2)
            logger.info(f"Saved user preferences to: {config_file}")
        except Exception as e:
            logger.error(f"Failed to save user config: {e}")
    
    def get_merged_config(self) -> Dict[str, Any]:
        """Get fully merged configuration with proper precedence"""
        with self._lock:
            # Check cache
            if self._merged_cache and self._cache_timestamp:
                if datetime.now() - self._cache_timestamp < timedelta(seconds=60):
                    return self._merged_cache.copy()
            
            # Merge all configurations
            merged = {}
            
            # Apply in order of precedence (lowest to highest)
            for cfg_type in [ConfigType.SYSTEM, ConfigType.MODEL, ConfigType.SAFETY, 
                           ConfigType.HARDWARE, ConfigType.FAMILY, ConfigType.USER, 
                           ConfigType.RUNTIME]:
                self._deep_merge(merged, self._configs.get(cfg_type, {}))
            
            self._merged_cache = merged
            self._cache_timestamp = datetime.now()
            
            return merged.copy()
    
    def _deep_merge(self, target: Dict, source: Dict):
        """Deep merge source dictionary into target"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def get_optimal_model(self) -> str:
        """Get optimal AI model for current hardware"""
        return self.get("optimal_model", "llama3.2:1b", ConfigType.HARDWARE)
    
    def get_safety_config(self) -> SafetyConfig:
        """Get safety configuration as dataclass"""
        data = self._configs.get(ConfigType.SAFETY, {})
        return SafetyConfig(**{k: v for k, v in data.items() if k in SafetyConfig.__annotations__})
    
    def get_hardware_config(self) -> HardwareConfig:
        """Get hardware configuration as dataclass"""
        data = self._configs.get(ConfigType.HARDWARE, {})
        return HardwareConfig(**{k: v for k, v in data.items() if k in HardwareConfig.__annotations__})
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required system files
        if not self.cdrom_path:
            errors.append("CD-ROM partition not found")
        
        if not self.usb_path:
            errors.append("USB data partition not found")
        
        # Check minimum hardware
        hw_config = self.get_hardware_config()
        if hw_config.ram_gb < 4:
            errors.append(f"Insufficient RAM: {hw_config.ram_gb}GB (minimum 4GB required)")
        
        if hw_config.cpu_cores < 2:
            errors.append(f"Insufficient CPU cores: {hw_config.cpu_cores} (minimum 2 required)")
        
        # Check model availability
        model_name = self.get_optimal_model()
        if not self._check_model_available(model_name):
            errors.append(f"Selected model not available: {model_name}")
        
        return len(errors) == 0, errors
    
    def _check_model_available(self, model_name: str) -> bool:
        """Check if model is available"""
        models = self._configs.get(ConfigType.MODEL, {}).get("models", [])
        return any(m.get("name") == model_name for m in models)
    
    def export_config(self, output_path: Path):
        """Export current configuration for debugging"""
        try:
            config = {
                "timestamp": datetime.now().isoformat(),
                "version": self.get("version", "unknown"),
                "merged_config": self.get_merged_config(),
                "individual_configs": {
                    cfg_type.value: data 
                    for cfg_type, data in self._configs.items()
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=str)
            
            logger.info(f"Exported configuration to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return False
    
    def reset_to_defaults(self, config_type: ConfigType = ConfigType.USER):
        """Reset configuration to defaults"""
        with self._lock:
            if config_type == ConfigType.USER:
                self._configs[ConfigType.USER] = {}
                self._save_user_config()
            elif config_type == ConfigType.RUNTIME:
                self._configs[ConfigType.RUNTIME] = {}
            
            self._merged_cache = None
            logger.info(f"Reset {config_type.value} configuration to defaults")


# Singleton instance
_config_manager: Optional[ConfigurationManager] = None


def get_config() -> ConfigurationManager:
    """Get or create configuration manager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


# Convenience functions
def get_setting(key: str, default: Any = None) -> Any:
    """Get configuration setting"""
    return get_config().get(key, default)


def set_setting(key: str, value: Any, persist: bool = False):
    """Set configuration setting"""
    get_config().set(key, value, persist=persist)


def get_optimal_model() -> str:
    """Get optimal model for current hardware"""
    return get_config().get_optimal_model()


def validate_config() -> Tuple[bool, List[str]]:
    """Validate configuration"""
    return get_config().validate_configuration()

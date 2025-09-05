#!/usr/bin/env python3
"""
Sunflower AI Professional System - Configuration Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Manages all system configuration including hardware detection,
model selection, safety settings, and user preferences.
"""

import os
import sys
import json
import yaml
import platform
import logging
import hashlib
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import configparser
import threading

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """Configuration types"""
    SYSTEM = "system"
    SAFETY = "safety"
    MODEL = "model"
    USER = "user"
    FAMILY = "family"
    HARDWARE = "hardware"
    NETWORK = "network"
    SECURITY = "security"


class ConfigSource(Enum):
    """Configuration source locations"""
    CDROM = "cdrom"  # Read-only system configs
    USB = "usb"      # Writable user configs
    MEMORY = "memory"  # Runtime configs
    DEFAULT = "default"  # Built-in defaults


@dataclass
class ModelConfig:
    """Model configuration"""
    name: str
    base_model: str
    size_gb: float
    min_ram_gb: float
    recommended_ram_gb: float
    context_size: int
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    max_tokens: int
    gpu_layers: int = -1
    threads: int = 4
    use_mmap: bool = True
    use_mlock: bool = False
    seed: Optional[int] = None


@dataclass
class SafetyConfig:
    """Safety configuration"""
    enabled: bool = True
    filter_level: str = "high"
    age_verification: bool = True
    content_logging: bool = True
    parent_alerts: bool = True
    max_safety_strikes: int = 3
    cooldown_minutes: int = 30
    blocked_categories: List[str] = field(default_factory=list)
    custom_filters: Dict[str, List[str]] = field(default_factory=dict)
    educational_mode: bool = True
    homework_mode: bool = False


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
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None


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


class ConfigurationManager:
    """
    Centralized configuration management for Sunflower AI.
    Handles all configuration loading, validation, and updates.
    """
    
    def __init__(self, cdrom_path: Optional[Path] = None, usb_path: Optional[Path] = None):
        """Initialize configuration manager"""
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        
        # Configuration storage
        self._configs: Dict[ConfigType, Dict] = {}
        self._config_lock = threading.RLock()
        
        # Environment variables
        self._env_vars: Dict[str, str] = {}
        
        # Initialize paths
        self._initialize_paths()
        
        # Load all configurations
        self._load_all_configs()
        
        logger.info(f"Configuration manager initialized - CD-ROM: {cdrom_path}, USB: {usb_path}")
    
    def _initialize_paths(self):
        """Initialize configuration paths"""
        # System config paths (CD-ROM)
        if self.cdrom_path:
            self.system_config_path = self.cdrom_path / "config"
            self.model_config_path = self.cdrom_path / "models" / "config"
            self.safety_config_path = self.cdrom_path / "safety"
        else:
            self.system_config_path = Path(__file__).parent.parent / "config"
            self.model_config_path = Path(__file__).parent.parent / "models" / "config"
            self.safety_config_path = Path(__file__).parent.parent / "safety"
        
        # User config paths (USB)
        if self.usb_path:
            self.user_config_path = self.usb_path / "config"
            self.family_config_path = self.usb_path / "families"
        else:
            # Development fallback
            dev_path = Path(__file__).parent.parent / "data"
            if not dev_path.exists():
                dev_path.mkdir(parents=True, exist_ok=True)
            self.user_config_path = dev_path / "config"
            self.family_config_path = dev_path / "families"
        
        # Ensure user directories exist
        self.user_config_path.mkdir(parents=True, exist_ok=True)
        self.family_config_path.mkdir(parents=True, exist_ok=True)
    
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
        
        # Load network configuration
        self._load_network_config()
        
        # Load security configuration
        self._load_security_config()
    
    def _load_system_config(self):
        """Load read-only system configuration from CD-ROM"""
        config_file = self.system_config_path / "system.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.SYSTEM] = json.load(f)
                logger.info(f"Loaded system config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load system config: {e}")
                self._load_default_system_config()
        else:
            self._load_default_system_config()
        
        # Load environment variables
        env_file = self.system_config_path / "default.env"
        if env_file.exists():
            self._load_env_file(env_file)
    
    def _load_default_system_config(self):
        """Load default system configuration"""
        self._configs[ConfigType.SYSTEM] = {
            "version": "6.2.0",
            "name": "Sunflower AI Professional System",
            "build_date": "2025-01-15",
            "platform": platform.system(),
            "architecture": platform.machine(),
            "min_ram_gb": 4,
            "min_disk_gb": 8,
            "supported_platforms": ["Windows", "Darwin"],
            "model_variants": ["llama3.2:7b", "llama3.2:3b", "llama3.2:1b", "llama3.2:1b-q4_0"],
            "features": {
                "voice_interaction": False,
                "multi_language": False,
                "cloud_sync": False,
                "api_access": False
            }
        }
    
    def _load_env_file(self, env_file: Path):
        """Load environment variables from .env file"""
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        os.environ[key] = value
                        self._env_vars[key] = value
            
            logger.info(f"Loaded {len(self._env_vars)} environment variables from: {env_file}")
        except Exception as e:
            logger.error(f"Failed to load environment file: {e}")
    
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
        self._configs[ConfigType.SAFETY] = SafetyConfig(
            enabled=True,
            filter_level="high",
            age_verification=True,
            content_logging=True,
            parent_alerts=True,
            max_safety_strikes=3,
            cooldown_minutes=30,
            blocked_categories=[
                "violence", "adult_content", "dangerous_activities",
                "personal_information", "self_harm", "hate_speech"
            ],
            educational_mode=True
        )
    
    def _load_model_config(self):
        """Load model configuration"""
        config_file = self.model_config_path / "models.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    models_data = json.load(f)
                    
                    self._configs[ConfigType.MODEL] = {}
                    for model_name, model_data in models_data.items():
                        self._configs[ConfigType.MODEL][model_name] = ModelConfig(**model_data)
                
                logger.info(f"Loaded {len(self._configs[ConfigType.MODEL])} model configs")
            except Exception as e:
                logger.error(f"Failed to load model config: {e}")
                self._load_default_model_config()
        else:
            self._load_default_model_config()
    
    def _load_default_model_config(self):
        """Load default model configurations"""
        self._configs[ConfigType.MODEL] = {
            "sunflower-kids": ModelConfig(
                name="sunflower-kids",
                base_model="llama3.2:3b",
                size_gb=3.0,
                min_ram_gb=4,
                recommended_ram_gb=8,
                context_size=4096,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                max_tokens=150,
                gpu_layers=-1,
                threads=4
            ),
            "sunflower-educator": ModelConfig(
                name="sunflower-educator",
                base_model="llama3.2:7b",
                size_gb=7.0,
                min_ram_gb=8,
                recommended_ram_gb=16,
                context_size=8192,
                temperature=0.8,
                top_p=0.95,
                top_k=50,
                repeat_penalty=1.05,
                max_tokens=500,
                gpu_layers=-1,
                threads=8
            )
        }
    
    def _load_user_config(self):
        """Load user configuration from USB"""
        config_file = self.user_config_path / "user_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.USER] = json.load(f)
                logger.info(f"Loaded user config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load user config: {e}")
                self._configs[ConfigType.USER] = {}
        else:
            self._configs[ConfigType.USER] = {}
    
    def _load_family_config(self):
        """Load family configuration"""
        config_file = self.family_config_path / "family_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.FAMILY] = json.load(f)
                logger.info(f"Loaded family config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load family config: {e}")
                self._configs[ConfigType.FAMILY] = {}
        else:
            self._configs[ConfigType.FAMILY] = {}
    
    def _load_hardware_config(self):
        """Load hardware configuration by detecting system capabilities"""
        try:
            import psutil
            
            hardware_config = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "cpu_count": psutil.cpu_count(logical=False),
                "cpu_threads": psutil.cpu_count(logical=True),
                "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 1),
                "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 1),
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 1),
                "gpu_available": self._detect_gpu(),
                "performance_tier": self._determine_performance_tier()
            }
            
            self._configs[ConfigType.HARDWARE] = hardware_config
            logger.info(f"Hardware detected: {hardware_config['performance_tier']} tier")
            
        except Exception as e:
            logger.error(f"Failed to detect hardware: {e}")
            self._configs[ConfigType.HARDWARE] = {
                "platform": platform.system(),
                "performance_tier": "standard"
            }
    
    def _detect_gpu(self) -> bool:
        """Detect if GPU is available"""
        try:
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True, text=True, timeout=5
                )
                return "NVIDIA" in result.stdout or "AMD" in result.stdout or "Intel" in result.stdout
            
            elif platform.system() == "Darwin":
                import subprocess
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True, text=True, timeout=5
                )
                return "GPU" in result.stdout or "Metal" in result.stdout
            
            else:
                # Linux
                try:
                    import subprocess
                    result = subprocess.run(
                        ["lspci"], capture_output=True, text=True, timeout=5
                    )
                    return "VGA" in result.stdout or "3D" in result.stdout
                except:
                    return False
                    
        except Exception as e:
            logger.debug(f"GPU detection failed: {e}")
            return False
    
    def _determine_performance_tier(self) -> str:
        """Determine system performance tier"""
        try:
            import psutil
            
            ram_gb = psutil.virtual_memory().total / (1024**3)
            cpu_threads = psutil.cpu_count(logical=True)
            
            if ram_gb >= 16 and cpu_threads >= 8:
                return "ultra"
            elif ram_gb >= 8 and cpu_threads >= 4:
                return "high"
            elif ram_gb >= 4 and cpu_threads >= 2:
                return "standard"
            else:
                return "minimum"
                
        except:
            return "standard"
    
    def _load_network_config(self):
        """Load network configuration"""
        config_file = self.user_config_path / "network.yaml"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._configs[ConfigType.NETWORK] = NetworkConfig(**config_data)
                logger.info(f"Loaded network config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load network config: {e}")
                self._configs[ConfigType.NETWORK] = NetworkConfig()
        else:
            self._configs[ConfigType.NETWORK] = NetworkConfig()
    
    def _load_security_config(self):
        """Load security configuration"""
        config_file = self.system_config_path / "security.yaml"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._configs[ConfigType.SECURITY] = SecurityConfig(**config_data)
                logger.info(f"Loaded security config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load security config: {e}")
                self._configs[ConfigType.SECURITY] = SecurityConfig()
        else:
            self._configs[ConfigType.SECURITY] = SecurityConfig()
    
    def get_config(self, config_type: ConfigType) -> Any:
        """Get configuration by type"""
        with self._config_lock:
            return self._configs.get(config_type)
    
    def get_value(self, config_type: ConfigType, key: str, default: Any = None) -> Any:
        """Get specific configuration value"""
        with self._config_lock:
            config = self._configs.get(config_type)
            if config:
                if isinstance(config, dict):
                    return config.get(key, default)
                elif hasattr(config, key):
                    return getattr(config, key, default)
            return default
    
    def set_value(self, config_type: ConfigType, key: str, value: Any):
        """Set configuration value"""
        with self._config_lock:
            if config_type not in self._configs:
                self._configs[config_type] = {}
            
            config = self._configs[config_type]
            if isinstance(config, dict):
                config[key] = value
            elif hasattr(config, key):
                setattr(config, key, value)
            
            # Save if it's a user config
            if config_type in [ConfigType.USER, ConfigType.FAMILY]:
                self._save_user_config()
    
    def _save_user_config(self):
        """Save user configuration to USB"""
        if not self.user_config_path:
            return
        
        try:
            # Save user config
            if ConfigType.USER in self._configs:
                user_file = self.user_config_path / "user_config.json"
                with open(user_file, 'w', encoding='utf-8') as f:
                    json.dump(self._configs[ConfigType.USER], f, indent=2)
            
            # Save family config
            if ConfigType.FAMILY in self._configs:
                family_file = self.family_config_path / "family_config.json"
                with open(family_file, 'w', encoding='utf-8') as f:
                    json.dump(self._configs[ConfigType.FAMILY], f, indent=2)
            
            logger.info("User configuration saved")
            
        except Exception as e:
            logger.error(f"Failed to save user config: {e}")
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for specific model"""
        models = self.get_config(ConfigType.MODEL)
        if models and model_name in models:
            return models[model_name]
        return None
    
    def get_optimal_model(self) -> str:
        """Get optimal model based on hardware"""
        hardware = self.get_config(ConfigType.HARDWARE)
        if not hardware:
            return "llama3.2:1b"
        
        tier = hardware.get("performance_tier", "standard")
        
        tier_models = {
            "ultra": "llama3.2:7b",
            "high": "llama3.2:3b",
            "standard": "llama3.2:1b",
            "minimum": "llama3.2:1b-q4_0"
        }
        
        return tier_models.get(tier, "llama3.2:1b")
    
    def get_safety_config(self) -> SafetyConfig:
        """Get safety configuration"""
        config = self.get_config(ConfigType.SAFETY)
        if not config:
            config = SafetyConfig()
            self._configs[ConfigType.SAFETY] = config
        return config
    
    def update_safety_config(self, **kwargs):
        """Update safety configuration"""
        config = self.get_safety_config()
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Save to user config
        if self.user_config_path:
            config_file = self.user_config_path / "safety_overrides.yaml"
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(asdict(config), f)
            
            logger.info("Safety configuration updated")
    
    def get_env_var(self, key: str, default: str = "") -> str:
        """Get environment variable"""
        return self._env_vars.get(key, os.environ.get(key, default))
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """Validate all configurations"""
        errors = []
        
        # Check system requirements
        hardware = self.get_config(ConfigType.HARDWARE)
        system = self.get_config(ConfigType.SYSTEM)
        
        if hardware and system:
            # Check RAM
            ram_gb = hardware.get("ram_total_gb", 0)
            min_ram = system.get("min_ram_gb", 4)
            if ram_gb < min_ram:
                errors.append(f"Insufficient RAM: {ram_gb}GB < {min_ram}GB required")
            
            # Check disk space
            disk_gb = hardware.get("disk_free_gb", 0)
            min_disk = system.get("min_disk_gb", 8)
            if disk_gb < min_disk:
                errors.append(f"Insufficient disk space: {disk_gb}GB < {min_disk}GB required")
            
            # Check platform
            platform_name = hardware.get("platform", "")
            supported = system.get("supported_platforms", [])
            if platform_name not in supported:
                errors.append(f"Unsupported platform: {platform_name}")
        
        # Check model availability
        models = self.get_config(ConfigType.MODEL)
        if not models:
            errors.append("No model configurations found")
        
        # Check safety config
        safety = self.get_config(ConfigType.SAFETY)
        if not safety or not safety.enabled:
            errors.append("Safety filter is disabled - not recommended for children")
        
        # Check network config
        network = self.get_config(ConfigType.NETWORK)
        if not network:
            errors.append("Network configuration missing")
        
        valid = len(errors) == 0
        return valid, errors
    
    def export_config(self, output_path: Path):
        """Export all configurations to file"""
        export_data = {}
        
        with self._config_lock:
            for config_type, config in self._configs.items():
                if isinstance(config, (ModelConfig, SafetyConfig, NetworkConfig, SecurityConfig)):
                    export_data[config_type.value] = asdict(config)
                else:
                    export_data[config_type.value] = config
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Configuration exported to: {output_path}")
    
    def reset_to_defaults(self, config_type: Optional[ConfigType] = None):
        """Reset configuration to defaults"""
        if config_type:
            # Reset specific config type
            if config_type == ConfigType.SAFETY:
                self._load_default_safety_config()
            elif config_type == ConfigType.MODEL:
                self._load_default_model_config()
            elif config_type == ConfigType.SYSTEM:
                self._load_default_system_config()
            
            logger.info(f"Reset {config_type.value} configuration to defaults")
        else:
            # Reset all configurations
            self._load_default_system_config()
            self._load_default_safety_config()
            self._load_default_model_config()
            self._configs[ConfigType.USER] = {}
            self._configs[ConfigType.FAMILY] = {}
            
            logger.info("All configurations reset to defaults")
        
        # Save changes
        self._save_user_config()
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status"""
        return {
            "loaded_configs": list(self._configs.keys()),
            "env_vars_count": len(self._env_vars),
            "cdrom_path": str(self.cdrom_path) if self.cdrom_path else None,
            "usb_path": str(self.usb_path) if self.usb_path else None,
            "hardware_tier": self.get_value(ConfigType.HARDWARE, "performance_tier", "unknown"),
            "optimal_model": self.get_optimal_model(),
            "safety_enabled": self.get_safety_config().enabled,
            "validation": self.validate_configuration()
        }


# Singleton instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(cdrom_path: Optional[Path] = None, 
                       usb_path: Optional[Path] = None) -> ConfigurationManager:
    """Get or create configuration manager singleton"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigurationManager(cdrom_path, usb_path)
    
    return _config_manager


# Testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test configuration manager
        config_mgr = ConfigurationManager(
            cdrom_path=Path(tmpdir) / "cdrom",
            usb_path=Path(tmpdir) / "usb"
        )
        
        # Test configuration
        print("Configuration Status:")
        print("-" * 60)
        
        status = config_mgr.get_status()
        for key, value in status.items():
            print(f"{key}: {value}")
        
        print("-" * 60)
        
        # Validate
        valid, errors = config_mgr.validate_configuration()
        if valid:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration errors:")
            for error in errors:
                print(f"  - {error}")

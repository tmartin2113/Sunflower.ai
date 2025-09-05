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
        self._lock = threading.RLock()
        
        # Configuration paths
        self.system_config_path = self.cdrom_path / "config" if self.cdrom_path else Path("config")
        self.user_config_path = self.usb_path / "config" if self.usb_path else Path("user_config")
        self.model_config_path = self.cdrom_path / "modelfiles" if self.cdrom_path else Path("modelfiles")
        self.safety_config_path = self.usb_path / "safety" if self.usb_path else Path("safety")
        
        # Create necessary directories
        self.user_config_path.mkdir(parents=True, exist_ok=True)
        self.safety_config_path.mkdir(parents=True, exist_ok=True)
        
        # Load configurations
        self._load_all_configs()
        
        logger.info("Configuration manager initialized")
    
    def _detect_cdrom(self) -> Optional[Path]:
        """Detect CD-ROM partition"""
        if platform.system() == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                marker_file = drive_path / "sunflower_cd.id"
                if marker_file.exists():
                    logger.info(f"Found CD-ROM partition at {drive_path}")
                    return drive_path
        
        elif platform.system() == "Darwin":  # macOS
            volumes = Path("/Volumes")
            for volume in volumes.iterdir():
                marker_file = volume / "sunflower_cd.id"
                if marker_file.exists():
                    logger.info(f"Found CD-ROM partition at {volume}")
                    return volume
        
        return None
    
    def _detect_usb(self) -> Optional[Path]:
        """Detect USB partition"""
        if platform.system() == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                marker_file = drive_path / "sunflower_data.id"
                if marker_file.exists():
                    logger.info(f"Found USB partition at {drive_path}")
                    return drive_path
        
        elif platform.system() == "Darwin":  # macOS
            volumes = Path("/Volumes")
            for volume in volumes.iterdir():
                marker_file = volume / "sunflower_data.id"
                if marker_file.exists():
                    logger.info(f"Found USB partition at {volume}")
                    return volume
        
        return None
    
    def _load_all_configs(self):
        """Load all configuration files"""
        with self._lock:
            try:
                self._load_system_config()
                self._load_environment_vars()
                self._load_safety_config()
                self._load_model_config()
                self._load_network_config()
                self._load_security_config()
                self._load_user_preferences()
                logger.info("All configurations loaded successfully")
            except Exception as e:
                logger.error(f"Error loading configurations: {e}")
                self._load_defaults()
    
    def _load_system_config(self):
        """Load system configuration"""
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
    
    def _load_default_system_config(self):
        """Load default system configuration"""
        self._configs[ConfigType.SYSTEM] = {
            "app_name": "Sunflower AI Professional System",
            "version": "6.2.0",
            "platform": platform.system().lower(),
            "min_python_version": "3.8",
            "required_ram_gb": 4,
            "recommended_ram_gb": 8,
            "install_date": datetime.now().isoformat(),
            "update_channel": "stable",
            "telemetry_enabled": False,
            "offline_mode": True
        }
    
    def _load_environment_vars(self):
        """Load environment variables"""
        env_file = self.user_config_path / ".env"
        
        if not env_file.exists():
            # Create default .env file
            default_env = """# Sunflower AI Environment Configuration
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
WEBUI_HOST=localhost
WEBUI_PORT=8080
LOG_LEVEL=INFO
DEBUG_MODE=False
SAFETY_FILTER=high
DEFAULT_MODEL=llama3.2:3b
"""
            env_file.write_text(default_env)
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            self._env_vars[key.strip()] = value.strip()
            
            logger.info(f"Loaded {len(self._env_vars)} environment variables")
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
        """Load default model configuration"""
        self._configs[ConfigType.MODEL] = {
            'sunflower_kids': ModelConfig(
                name='sunflower_kids',
                base_model='llama3.2:3b',
                size_gb=2.0,
                min_ram_gb=4,
                recommended_ram_gb=8,
                context_size=4096,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                max_tokens=500,
                gpu_layers=-1,
                threads=4,
                use_mmap=True,
                use_mlock=False
            ),
            'sunflower_educator': ModelConfig(
                name='sunflower_educator',
                base_model='llama3.2:7b',
                size_gb=4.0,
                min_ram_gb=8,
                recommended_ram_gb=16,
                context_size=8192,
                temperature=0.8,
                top_p=0.95,
                top_k=50,
                repeat_penalty=1.05,
                max_tokens=1000,
                gpu_layers=-1,
                threads=8,
                use_mmap=True,
                use_mlock=False
            ),
            'sunflower_minimal': ModelConfig(
                name='sunflower_minimal',
                base_model='llama3.2:1b',
                size_gb=0.7,
                min_ram_gb=2,
                recommended_ram_gb=4,
                context_size=2048,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                max_tokens=300,
                gpu_layers=-1,
                threads=2,
                use_mmap=True,
                use_mlock=False
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
        self._configs[ConfigType.NETWORK] = NetworkConfig(
            ollama_host="localhost",
            ollama_port=11434,
            webui_host="localhost",
            webui_port=8080,
            api_timeout=30,
            max_retries=3,
            offline_mode=False,
            proxy_enabled=False
        )
    
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
        self._configs[ConfigType.SECURITY] = SecurityConfig(
            require_authentication=True,
            encryption_enabled=True,
            session_timeout_minutes=60,
            max_login_attempts=5,
            lockout_duration_minutes=30,
            require_parent_pin=True,
            pin_length=6,
            two_factor_enabled=False,
            audit_logging=True,
            secure_erase=True
        )
    
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
    
    def get(self, config_type: ConfigType, key: Optional[str] = None) -> Any:
        """
        Get configuration value
        
        Args:
            config_type: Type of configuration
            key: Optional specific key within configuration
            
        Returns:
            Configuration value or entire config object
        """
        with self._lock:
            config = self._configs.get(config_type)
            
            if key and isinstance(config, dict):
                return config.get(key)
            
            return config
    
    def set(self, config_type: ConfigType, key: str, value: Any):
        """
        Set configuration value
        
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
                logger.error(f"Cannot set key on non-dict config type: {config_type}")
    
    def update(self, config_type: ConfigType, updates: Dict[str, Any]):
        """
        Update multiple configuration values
        
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
                logger.error(f"Cannot update non-dict config type: {config_type}")
    
    def _save_config(self, config_type: ConfigType):
        """Save configuration to disk"""
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
                save_path = self.user_config_path / "models.json"
                config = self._configs[config_type]
                
                config_dict = {}
                for name, model_config in config.items():
                    if isinstance(model_config, ModelConfig):
                        config_dict[name] = asdict(model_config)
                    else:
                        config_dict[name] = model_config
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2)
            
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
        """Get environment variable"""
        return self._env_vars.get(key, os.environ.get(key, default))
    
    def set_env(self, key: str, value: str):
        """Set environment variable"""
        self._env_vars[key] = value
        os.environ[key] = value
        
        # Save to .env file
        env_file = self.user_config_path / ".env"
        lines = []
        
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        # Update or add the key
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        
        if not found:
            lines.append(f"{key}={value}\n")
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def validate_hardware(self) -> Tuple[bool, List[str]]:
        """
        Validate hardware requirements
        
        Returns:
            Tuple of (meets_requirements, list_of_issues)
        """
        issues = []
        
        try:
            import psutil
            
            # Check RAM
            total_ram_gb = psutil.virtual_memory().total / (1024**3)
            required_ram = self._configs[ConfigType.SYSTEM].get('required_ram_gb', 4)
            
            if total_ram_gb < required_ram:
                issues.append(f"Insufficient RAM: {total_ram_gb:.1f}GB < {required_ram}GB required")
            
            # Check disk space
            if self.usb_path:
                disk_usage = psutil.disk_usage(str(self.usb_path))
                free_gb = disk_usage.free / (1024**3)
                
                if free_gb < 1:
                    issues.append(f"Low disk space on USB: {free_gb:.1f}GB free")
            
            # Check CPU cores
            cpu_count = psutil.cpu_count(logical=False)
            if cpu_count < 2:
                issues.append(f"Low CPU core count: {cpu_count} cores")
            
        except ImportError:
            logger.warning("psutil not available for hardware validation")
        except Exception as e:
            logger.error(f"Hardware validation error: {e}")
            issues.append(f"Hardware validation error: {e}")
        
        meets_requirements = len(issues) == 0
        return meets_requirements, issues
    
    def get_optimal_model(self) -> str:
        """
        Get optimal model based on hardware capabilities
        
        Returns:
            Model name suitable for current hardware
        """
        try:
            import psutil
            
            total_ram_gb = psutil.virtual_memory().total / (1024**3)
            
            models = self._configs.get(ConfigType.MODEL, {})
            
            # Find best model for available RAM
            suitable_models = []
            for name, config in models.items():
                if isinstance(config, ModelConfig):
                    if total_ram_gb >= config.min_ram_gb:
                        suitable_models.append((name, config.recommended_ram_gb))
                elif isinstance(config, dict):
                    min_ram = config.get('min_ram_gb', 4)
                    rec_ram = config.get('recommended_ram_gb', 8)
                    if total_ram_gb >= min_ram:
                        suitable_models.append((name, rec_ram))
            
            if suitable_models:
                # Sort by recommended RAM (descending) and return best fit
                suitable_models.sort(key=lambda x: x[1], reverse=True)
                
                for name, rec_ram in suitable_models:
                    if total_ram_gb >= rec_ram:
                        return name
                
                # Return the model with lowest requirements if none ideal
                return suitable_models[-1][0]
            
            # Default to minimal model
            return 'sunflower_minimal'
            
        except Exception as e:
            logger.error(f"Error selecting optimal model: {e}")
            return 'sunflower_minimal'
    
    def export_config(self, output_path: Path):
        """Export all configuration to file"""
        export_data = {
            'version': self._configs[ConfigType.SYSTEM].get('version', 'unknown'),
            'export_date': datetime.now().isoformat(),
            'configurations': {}
        }
        
        with self._lock:
            for config_type in ConfigType:
                config = self._configs.get(config_type)
                
                if config:
                    if hasattr(config, '__dict__'):
                        export_data['configurations'][config_type.value] = asdict(config)
                    else:
                        export_data['configurations'][config_type.value] = config
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported configuration to {output_path}")
    
    def import_config(self, input_path: Path):
        """Import configuration from file"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            configurations = import_data.get('configurations', {})
            
            with self._lock:
                for config_type_str, config_data in configurations.items():
                    try:
                        config_type = ConfigType(config_type_str)
                        
                        # Don't import system config
                        if config_type == ConfigType.SYSTEM:
                            continue
                        
                        self._configs[config_type] = config_data
                        self._save_config(config_type)
                        
                    except ValueError:
                        logger.warning(f"Unknown config type: {config_type_str}")
            
            logger.info(f"Imported configuration from {input_path}")
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            raise


# Singleton instance
_config_manager = None
_config_lock = threading.Lock()


def get_config_manager(cdrom_path: Optional[Path] = None, 
                       usb_path: Optional[Path] = None) -> ConfigurationManager:
    """
    Get singleton configuration manager instance
    
    Args:
        cdrom_path: Optional CD-ROM path
        usb_path: Optional USB path
        
    Returns:
        ConfigurationManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                _config_manager = ConfigurationManager(cdrom_path, usb_path)
    
    return _config_manager


# Testing
if __name__ == "__main__":
    import tempfile
    
    # Test with temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create test structure
        cdrom = tmp_path / "cdrom"
        usb = tmp_path / "usb"
        cdrom.mkdir()
        usb.mkdir()
        
        # Create marker files
        (cdrom / "sunflower_cd.id").touch()
        (usb / "sunflower_data.id").touch()
        
        # Initialize config manager
        config = ConfigurationManager(cdrom, usb)
        
        # Test getting configurations
        print("System Config:", config.get(ConfigType.SYSTEM))
        print("Safety Config:", config.get(ConfigType.SAFETY))
        print("Optimal Model:", config.get_optimal_model())
        
        # Test hardware validation
        meets_req, issues = config.validate_hardware()
        print(f"Hardware OK: {meets_req}")
        if issues:
            print("Issues:", issues)
        
        # Test export
        export_file = tmp_path / "config_export.json"
        config.export_config(export_file)
        print(f"Configuration exported to {export_file}")

#!/usr/bin/env python3
"""
Sunflower AI Professional System - Configuration Manager
Thread-safe configuration loading and management
Version: 6.2.0 - Production Ready
"""

import os
import sys
import json
import yaml
import platform
import threading
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
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
    educational_mode: bool = True


@dataclass
class ModelConfig:
    """Model configuration"""
    name: str
    size: str
    ram_required_gb: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    context_length: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    repeat_penalty: float = 1.1


@dataclass
class NetworkConfig:
    """Network configuration"""
    ollama_host: str = "localhost"
    ollama_port: int = 11434
    webui_host: str = "0.0.0.0"
    webui_port: int = 8080
    timeout_seconds: int = 30
    retry_attempts: int = 3
    ssl_enabled: bool = False


@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    password_min_length: int = 8
    session_timeout_minutes: int = 30
    max_login_attempts: int = 3
    lockout_duration_minutes: int = 15
    require_parent_auth: bool = True


class ConfigurationManager:
    """
    Thread-safe configuration manager.
    Handles all configuration loading, validation, and updates.
    """
    
    def __init__(self, cdrom_path: Optional[Path] = None, usb_path: Optional[Path] = None):
        """
        Initialize configuration manager with proper thread safety
        
        Args:
            cdrom_path: Path to CD-ROM partition
            usb_path: Path to USB partition
        """
        # FIX: Initialize lock FIRST before any other operations
        self._lock = threading.RLock()
        
        # FIX: Wrap all initialization in lock to prevent race conditions
        with self._lock:
            # Initialize paths
            self.cdrom_path = Path(cdrom_path) if cdrom_path else self._detect_cdrom()
            self.usb_path = Path(usb_path) if usb_path else self._detect_usb()
            
            # Configuration storage
            self._configs = {}
            self._env_vars = {}
            self._cache = {}
            self._cache_timestamps = {}
            
            # Configuration paths
            self.system_config_path = self.cdrom_path / "config" if self.cdrom_path else Path("config")
            self.user_config_path = self.usb_path / "config" if self.usb_path else Path("user_config")
            self.model_config_path = self.cdrom_path / "modelfiles" if self.cdrom_path else Path("modelfiles")
            self.safety_config_path = self.usb_path / "safety" if self.usb_path else Path("safety")
            
            # Create necessary directories
            self.user_config_path.mkdir(parents=True, exist_ok=True)
            self.safety_config_path.mkdir(parents=True, exist_ok=True)
            
            # Load configurations within lock
            self._load_all_configs()
            
            logger.info("Configuration manager initialized with thread safety")
    
    def _detect_cdrom(self) -> Optional[Path]:
        """Detect CD-ROM partition"""
        with self._lock:  # FIX: Add thread safety to detection
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
        with self._lock:  # FIX: Add thread safety to detection
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
        """Load all configuration files - called within lock during init"""
        # Note: This is now always called within the lock from __init__
        try:
            self._load_system_config()
            self._load_environment_config()
            self._load_safety_config()
            self._load_model_config()
            self._load_network_config()
            self._load_security_config()
            self._load_user_config()
            
            logger.info("All configurations loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            # Load defaults for critical configs
            self._load_default_configs()
    
    def _load_default_configs(self):
        """Load default configurations as fallback"""
        self._configs[ConfigType.SYSTEM] = {
            "version": "6.2.0",
            "platform": platform.system(),
            "required_ram_gb": 4,
            "debug": False
        }
        
        self._configs[ConfigType.SAFETY] = SafetyConfig()
        self._configs[ConfigType.MODEL] = {}
        self._configs[ConfigType.NETWORK] = NetworkConfig()
        self._configs[ConfigType.SECURITY] = SecurityConfig()
        self._configs[ConfigType.USER] = {}
        
        logger.info("Loaded default configurations")
    
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
                self._configs[ConfigType.SYSTEM] = {}
        else:
            self._configs[ConfigType.SYSTEM] = {}
    
    def _load_environment_config(self):
        """Load environment variables from .env file"""
        env_file = self.system_config_path / "default.env"
        
        if not env_file.exists():
            env_file = self.user_config_path / ".env"
        
        try:
            if env_file.exists():
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
        """Load default model configurations"""
        self._configs[ConfigType.MODEL] = {
            "sunflower-kids": ModelConfig(
                name="sunflower-kids",
                size="1b",
                ram_required_gb=4.0,
                parameters={"temperature": 0.7, "top_p": 0.9},
                context_length=4096
            ),
            "sunflower-educator": ModelConfig(
                name="sunflower-educator",
                size="3b",
                ram_required_gb=6.0,
                parameters={"temperature": 0.8, "top_p": 0.95},
                context_length=8192
            )
        }
    
    def _load_network_config(self):
        """Load network configuration"""
        config_file = self.system_config_path / "network.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._configs[ConfigType.NETWORK] = NetworkConfig(**config_data)
                logger.info(f"Loaded network config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load network config: {e}")
                self._configs[ConfigType.NETWORK] = NetworkConfig()
        else:
            self._configs[ConfigType.NETWORK] = NetworkConfig()
    
    def _load_security_config(self):
        """Load security configuration"""
        config_file = self.system_config_path / "security.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._configs[ConfigType.SECURITY] = SecurityConfig(**config_data)
                logger.info(f"Loaded security config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load security config: {e}")
                self._configs[ConfigType.SECURITY] = SecurityConfig()
        else:
            self._configs[ConfigType.SECURITY] = SecurityConfig()
    
    def _load_user_config(self):
        """Load user preferences"""
        config_file = self.user_config_path / "preferences.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.USER] = json.load(f)
                logger.info(f"Loaded user preferences: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load user preferences: {e}")
                self._configs[ConfigType.USER] = {}
        else:
            self._configs[ConfigType.USER] = {}
    
    def get(self, config_type: ConfigType, key: Optional[str] = None) -> Any:
        """
        Thread-safe configuration getter
        
        Args:
            config_type: Type of configuration
            key: Optional specific key within configuration
            
        Returns:
            Configuration value
        """
        with self._lock:  # FIX: Ensure thread-safe access
            config = self._configs.get(config_type)
            
            if config is None:
                return None
            
            if key is None:
                return config
            
            if isinstance(config, dict):
                return config.get(key)
            elif hasattr(config, key):
                return getattr(config, key)
            
            return None
    
    def set(self, config_type: ConfigType, key: str, value: Any):
        """
        Thread-safe configuration setter
        
        Args:
            config_type: Type of configuration
            key: Configuration key
            value: New value
        """
        with self._lock:  # FIX: Ensure thread-safe modification
            if config_type not in self._configs:
                self._configs[config_type] = {}
            
            config = self._configs[config_type]
            
            if isinstance(config, dict):
                config[key] = value
            elif hasattr(config, key):
                setattr(config, key, value)
            
            # Clear cache for this config type
            cache_key = f"{config_type.value}:{key}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            # Save to disk
            self._save_config(config_type)
    
    def _save_config(self, config_type: ConfigType):
        """Save configuration to disk - must be called within lock"""
        try:
            if config_type == ConfigType.SYSTEM:
                # System config is read-only on CD-ROM
                logger.debug("System config is read-only")
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
        """Thread-safe environment variable getter"""
        with self._lock:
            return self._env_vars.get(key, os.environ.get(key, default))
    
    def set_env(self, key: str, value: str):
        """Thread-safe environment variable setter"""
        with self._lock:
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
        Thread-safe hardware validation
        
        Returns:
            Tuple of (meets_requirements, list_of_issues)
        """
        with self._lock:  # FIX: Thread-safe hardware check
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
        Get optimal model based on hardware capabilities with caching
        
        Returns:
            Model name suitable for current hardware
        """
        with self._lock:  # FIX: Thread-safe model selection
            import time
            
            # Check cache first
            cache_key = "optimal_model"
            if cache_key in self._cache:
                cache_time = self._cache_timestamps.get(cache_key, 0)
                if time.time() - cache_time < 60:  # Cache for 60 seconds
                    return self._cache[cache_key]
            
            try:
                import psutil
                
                total_ram_gb = psutil.virtual_memory().total / (1024**3)
                
                # Select model based on available RAM
                if total_ram_gb >= 16:
                    model = "llama3.2:7b"
                elif total_ram_gb >= 8:
                    model = "llama3.2:3b"
                elif total_ram_gb >= 4:
                    model = "llama3.2:1b"
                else:
                    model = "llama3.2:1b-q4_0"
                
                # Update cache
                self._cache[cache_key] = model
                self._cache_timestamps[cache_key] = time.time()
                
                logger.info(f"Selected optimal model: {model} for {total_ram_gb:.1f}GB RAM")
                return model
                
            except ImportError:
                logger.warning("psutil not available, using default model")
                return "llama3.2:1b"
            except Exception as e:
                logger.error(f"Error selecting optimal model: {e}")
                return "llama3.2:1b"
    
    def export_config(self, output_path: Path):
        """
        Thread-safe configuration export
        
        Args:
            output_path: Path to export configuration
        """
        with self._lock:  # FIX: Thread-safe export
            try:
                export_data = {
                    "version": "6.2.0",
                    "export_date": datetime.now().isoformat(),
                    "platform": platform.system(),
                    "configurations": {}
                }
                
                for config_type in ConfigType:
                    config = self._configs.get(config_type)
                    if config:
                        if hasattr(config, '__dict__'):
                            export_data["configurations"][config_type.value] = asdict(config)
                        else:
                            export_data["configurations"][config_type.value] = config
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                logger.info(f"Exported configuration to {output_path}")
                
            except Exception as e:
                logger.error(f"Failed to export configuration: {e}")
                raise
    
    def import_config(self, input_path: Path):
        """
        Thread-safe configuration import
        
        Args:
            input_path: Path to import configuration from
        """
        with self._lock:  # FIX: Thread-safe import
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                # Validate version compatibility
                import_version = import_data.get("version", "0.0.0")
                if not self._is_compatible_version(import_version):
                    raise ValueError(f"Incompatible version: {import_version}")
                
                # Import configurations
                configurations = import_data.get("configurations", {})
                
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
                
                # Clear cache after import
                self._cache.clear()
                self._cache_timestamps.clear()
                
                logger.info(f"Imported configuration from {input_path}")
                
            except Exception as e:
                logger.error(f"Failed to import configuration: {e}")
                raise
    
    def _is_compatible_version(self, version: str) -> bool:
        """Check if version is compatible for import"""
        try:
            major, minor, patch = version.split('.')
            current_major, current_minor, _ = "6.2.0".split('.')
            
            # Compatible if same major version and minor version >= current
            return major == current_major and int(minor) >= int(current_minor)
        except:
            return False


# Singleton instance with thread-safe initialization
_config_manager = None
_config_lock = threading.Lock()


def get_config_manager(cdrom_path: Optional[Path] = None, 
                       usb_path: Optional[Path] = None) -> ConfigurationManager:
    """
    Get singleton configuration manager instance with thread safety
    
    Args:
        cdrom_path: Optional CD-ROM path
        usb_path: Optional USB path
        
    Returns:
        ConfigurationManager instance
    """
    global _config_manager
    
    # FIX: Double-checked locking pattern for thread safety
    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                _config_manager = ConfigurationManager(cdrom_path, usb_path)
    
    return _config_manager


# Testing
if __name__ == "__main__":
    import tempfile
    import concurrent.futures
    
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
        
        # Test thread safety with concurrent access
        def test_thread_safety(thread_id):
            """Test concurrent access to configuration manager"""
            config = get_config_manager(cdrom, usb)
            
            # Perform various operations
            for i in range(10):
                config.set(ConfigType.USER, f"thread_{thread_id}_key_{i}", f"value_{i}")
                value = config.get(ConfigType.USER, f"thread_{thread_id}_key_{i}")
                assert value == f"value_{i}", f"Thread {thread_id} failed at iteration {i}"
            
            return f"Thread {thread_id} completed successfully"
        
        # Run concurrent tests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(test_thread_safety, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            for result in results:
                print(result)
        
        # Test basic functionality
        config = get_config_manager(cdrom, usb)
        
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
        
        print("\nAll thread safety tests passed!")

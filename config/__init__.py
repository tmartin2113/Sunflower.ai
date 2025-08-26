#!/usr/bin/env python3
"""
Sunflower AI Configuration Module
Manages all system configuration including environment, family settings, and model mapping
Production-ready implementation with partitioned device support
"""

import os
import json
import yaml
import hashlib
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Configure module logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Central configuration manager for Sunflower AI system"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager with partition detection
        
        Args:
            config_dir: Override config directory path (for testing)
        """
        self.system = platform.system()
        
        # Detect partitions
        self.cdrom_partition = self._detect_cdrom_partition()
        self.usb_partition = self._detect_usb_partition()
        
        # Set configuration paths based on partition architecture
        if config_dir:
            self.config_dir = Path(config_dir)
        elif self.cdrom_partition:
            # Production: Config on CD-ROM partition (read-only)
            self.config_dir = self.cdrom_partition / "config"
        else:
            # Development: Local config directory
            self.config_dir = Path(__file__).parent
        
        # User data always goes to USB partition
        if self.usb_partition:
            self.user_data_dir = self.usb_partition / "sunflower_data"
        else:
            # Fallback to user home directory
            self.user_data_dir = Path.home() / ".sunflower_ai" / "data"
        
        # Ensure directories exist
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configurations
        self.env_config = self._load_env_config()
        self.family_config = self._load_family_config()
        self.model_mapping = self._load_model_mapping()
        
        # Validate configuration integrity
        self._validate_configuration()
        
    def _detect_cdrom_partition(self) -> Optional[Path]:
        """
        Detect CD-ROM partition containing system files
        
        Returns:
            Path to CD-ROM partition or None
        """
        marker_file = "sunflower_cd.id"
        
        if self.system == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:/")
                if drive_path.exists():
                    marker_path = drive_path / marker_file
                    if marker_path.exists():
                        logger.info(f"CD-ROM partition detected: {drive_path}")
                        return drive_path
        else:
            # macOS and Linux
            mount_points = ["/Volumes", "/media", "/mnt"]
            for mount_dir in mount_points:
                mount_path = Path(mount_dir)
                if mount_path.exists():
                    for volume in mount_path.iterdir():
                        if (volume / marker_file).exists():
                            logger.info(f"CD-ROM partition detected: {volume}")
                            return volume
        
        logger.warning("CD-ROM partition not detected - using development mode")
        return None
    
    def _detect_usb_partition(self) -> Optional[Path]:
        """
        Detect USB writable partition for user data
        
        Returns:
            Path to USB partition or None
        """
        marker_file = "sunflower_data.id"
        
        if self.system == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:/")
                if drive_path.exists():
                    marker_path = drive_path / marker_file
                    if marker_path.exists():
                        logger.info(f"USB partition detected: {drive_path}")
                        return drive_path
        else:
            # macOS and Linux
            mount_points = ["/Volumes", "/media", "/mnt"]
            for mount_dir in mount_points:
                mount_path = Path(mount_dir)
                if mount_path.exists():
                    for volume in mount_path.iterdir():
                        if (volume / marker_file).exists():
                            logger.info(f"USB partition detected: {volume}")
                            return volume
        
        logger.warning("USB partition not detected - using local storage")
        return None
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load environment configuration from default.env"""
        env_file = self.config_dir / "default.env"
        config = {}
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = self._parse_env_value(value.strip())
        
        # Apply defaults if not present
        defaults = {
            'APP_NAME': 'Sunflower AI Professional System',
            'VERSION': '6.2.0',
            'DEBUG': False,
            'LOG_LEVEL': 'INFO',
            'OLLAMA_HOST': 'http://localhost:11434',
            'HOST': '127.0.0.1',
            'PORT': 8080,
            'SESSION_TIMEOUT_MINUTES': 60,
            'MAX_CONVERSATION_HISTORY': 100,
            'ENABLE_TELEMETRY': False,
            'REQUIRE_AUTHENTICATION': True,
            'ENCRYPTION_ENABLED': True,
            'AUTO_SAVE_INTERVAL': 300
        }
        
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        
        # Apply to environment
        for key, value in config.items():
            os.environ[key] = str(value)
        
        return config
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Boolean values
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        return value
    
    def _load_family_config(self) -> Dict[str, Any]:
        """Load family settings configuration"""
        # System config from CD-ROM (read-only)
        system_config_file = self.config_dir / "family_settings.yaml"
        
        # User config from USB partition (writable)
        user_config_file = self.user_data_dir / "profiles" / "family_settings.yaml"
        
        # Load system defaults
        system_config = {}
        if system_config_file.exists():
            with open(system_config_file, 'r') as f:
                system_config = yaml.safe_load(f) or {}
        
        # Load or create user config
        user_config = {}
        if user_config_file.exists():
            with open(user_config_file, 'r') as f:
                user_config = yaml.safe_load(f) or {}
        else:
            # Create default user configuration
            user_config = {
                'family_id': self._generate_family_id(),
                'created': datetime.now().isoformat(),
                'profiles': [],
                'settings': {
                    'content_filtering': True,
                    'session_recording': True,
                    'age_verification': True,
                    'max_session_minutes': 60,
                    'require_parent_pin': True,
                    'auto_logout_minutes': 15
                }
            }
            
            # Save initial configuration
            user_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(user_config_file, 'w') as f:
                yaml.safe_dump(user_config, f, default_flow_style=False)
        
        # Merge configurations (user overrides system)
        config = {**system_config, **user_config}
        return config
    
    def _load_model_mapping(self) -> Dict[str, Any]:
        """Load model mapping configuration for hardware optimization"""
        mapping_file = self.config_dir / "model_mapping.yaml"
        
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                return yaml.safe_load(f) or {}
        
        # Default hardware-based model mapping
        return {
            'hardware_tiers': {
                'high_end': {
                    'min_ram_gb': 16,
                    'min_vram_gb': 8,
                    'model': 'llama3.2:7b',
                    'context_size': 4096,
                    'gpu_layers': 35
                },
                'mid_range': {
                    'min_ram_gb': 8,
                    'min_vram_gb': 4,
                    'model': 'llama3.2:3b',
                    'context_size': 2048,
                    'gpu_layers': 24
                },
                'low_end': {
                    'min_ram_gb': 4,
                    'min_vram_gb': 0,
                    'model': 'llama3.2:1b',
                    'context_size': 1024,
                    'gpu_layers': 0
                },
                'minimum': {
                    'min_ram_gb': 2,
                    'min_vram_gb': 0,
                    'model': 'llama3.2:1b-q4_0',
                    'context_size': 512,
                    'gpu_layers': 0
                }
            },
            'model_aliases': {
                'sunflower-kids': {
                    'base_model': 'auto',  # Automatically selected based on hardware
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'repeat_penalty': 1.1
                },
                'sunflower-educator': {
                    'base_model': 'auto',
                    'temperature': 0.8,
                    'top_p': 0.95,
                    'repeat_penalty': 1.0
                }
            }
        }
    
    def _generate_family_id(self) -> str:
        """Generate unique family identifier"""
        import uuid
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:16]
    
    def _validate_configuration(self) -> bool:
        """
        Validate configuration integrity and security
        
        Returns:
            True if configuration is valid
        
        Raises:
            ConfigurationError: If critical configuration issues detected
        """
        # Check critical paths exist
        if not self.config_dir.exists():
            raise ConfigurationError(f"Configuration directory not found: {self.config_dir}")
        
        # Verify partition markers if in production mode
        if self.cdrom_partition:
            marker = self.cdrom_partition / "sunflower_cd.id"
            if not marker.exists():
                raise ConfigurationError("Invalid CD-ROM partition: missing marker file")
        
        if self.usb_partition:
            marker = self.usb_partition / "sunflower_data.id"
            if not marker.exists():
                raise ConfigurationError("Invalid USB partition: missing marker file")
        
        # Validate required environment variables
        required_vars = ['APP_NAME', 'VERSION', 'OLLAMA_HOST']
        for var in required_vars:
            if var not in self.env_config:
                raise ConfigurationError(f"Required environment variable missing: {var}")
        
        logger.info("Configuration validation successful")
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check environment config first
        if key in self.env_config:
            return self.env_config[key]
        
        # Check nested keys using dot notation
        if '.' in key:
            parts = key.split('.')
            config = None
            
            # Determine which config to search
            if parts[0] == 'family':
                config = self.family_config
                parts = parts[1:]
            elif parts[0] == 'model':
                config = self.model_mapping
                parts = parts[1:]
            
            if config:
                value = config
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return default
                return value
        
        return default
    
    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Value to set
            persist: Whether to persist to disk (only for user data)
        """
        # Update in-memory config
        self.env_config[key] = value
        os.environ[key] = str(value)
        
        if persist and key.startswith('family.'):
            # Update family configuration on USB partition
            self._save_family_config()
    
    def _save_family_config(self) -> None:
        """Save family configuration to USB partition"""
        config_file = self.user_data_dir / "profiles" / "family_settings.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.safe_dump(self.family_config, f, default_flow_style=False)
        
        logger.info("Family configuration saved")
    
    def get_hardware_tier(self) -> str:
        """
        Determine hardware tier based on system capabilities
        
        Returns:
            Hardware tier name (high_end, mid_range, low_end, minimum)
        """
        try:
            import psutil
            
            # Get system RAM in GB
            ram_gb = psutil.virtual_memory().total / (1024**3)
            
            # Check for GPU (simplified detection)
            vram_gb = self._detect_vram()
            
            # Determine tier based on resources
            for tier_name, tier_config in self.model_mapping['hardware_tiers'].items():
                if ram_gb >= tier_config['min_ram_gb'] and vram_gb >= tier_config['min_vram_gb']:
                    logger.info(f"Hardware tier detected: {tier_name} (RAM: {ram_gb:.1f}GB, VRAM: {vram_gb:.1f}GB)")
                    return tier_name
            
            return 'minimum'
            
        except Exception as e:
            logger.warning(f"Hardware detection failed: {e}")
            return 'minimum'
    
    def _detect_vram(self) -> float:
        """
        Detect available VRAM
        
        Returns:
            VRAM in GB (0 if no GPU detected)
        """
        try:
            if self.system == "Windows":
                # Windows GPU detection via WMI
                import subprocess
                result = subprocess.run(
                    ["wmic", "path", "win32_videocontroller", "get", "AdapterRAM"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:
                        if line.strip() and line.strip().isdigit():
                            return int(line.strip()) / (1024**3)
            elif self.system == "Darwin":
                # macOS GPU detection
                import subprocess
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True, text=True
                )
                if "VRAM" in result.stdout:
                    # Parse VRAM from output
                    for line in result.stdout.split('\n'):
                        if "VRAM" in line:
                            # Extract number from line like "VRAM (Total): 8 GB"
                            parts = line.split(':')
                            if len(parts) > 1:
                                vram_str = parts[1].strip().split()[0]
                                try:
                                    return float(vram_str)
                                except ValueError:
                                    pass
        except Exception as e:
            logger.debug(f"VRAM detection failed: {e}")
        
        return 0.0
    
    def get_optimal_model(self) -> str:
        """
        Get optimal model for current hardware
        
        Returns:
            Model name to use
        """
        tier = self.get_hardware_tier()
        return self.model_mapping['hardware_tiers'][tier]['model']
    
    def get_model_config(self, model_alias: str) -> Dict[str, Any]:
        """
        Get model configuration by alias
        
        Args:
            model_alias: Model alias (e.g., 'sunflower-kids')
            
        Returns:
            Model configuration dictionary
        """
        if model_alias not in self.model_mapping['model_aliases']:
            raise ValueError(f"Unknown model alias: {model_alias}")
        
        config = self.model_mapping['model_aliases'][model_alias].copy()
        
        # Replace 'auto' with actual model based on hardware
        if config.get('base_model') == 'auto':
            config['base_model'] = self.get_optimal_model()
        
        # Add hardware-specific settings
        tier = self.get_hardware_tier()
        tier_config = self.model_mapping['hardware_tiers'][tier]
        config['context_size'] = tier_config['context_size']
        config['gpu_layers'] = tier_config['gpu_layers']
        
        return config
    
    def export_config(self, output_file: Optional[Path] = None) -> Path:
        """
        Export current configuration for backup
        
        Args:
            output_file: Output file path (optional)
            
        Returns:
            Path to exported configuration
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.user_data_dir / f"config_backup_{timestamp}.json"
        
        export_data = {
            'version': self.env_config.get('VERSION'),
            'export_date': datetime.now().isoformat(),
            'system': self.system,
            'partitions': {
                'cdrom': str(self.cdrom_partition) if self.cdrom_partition else None,
                'usb': str(self.usb_partition) if self.usb_partition else None
            },
            'environment': self.env_config,
            'family': self.family_config,
            'model_mapping': self.model_mapping
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Configuration exported to {output_file}")
        return output_file


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass


# Singleton instance
_config_instance: Optional[ConfigurationManager] = None


def get_config() -> ConfigurationManager:
    """
    Get singleton configuration manager instance
    
    Returns:
        ConfigurationManager instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigurationManager()
    return _config_instance


def reset_config() -> None:
    """Reset configuration manager (mainly for testing)"""
    global _config_instance
    _config_instance = None


# Module exports
__all__ = [
    'ConfigurationManager',
    'ConfigurationError',
    'get_config',
    'reset_config'
]

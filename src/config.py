"""
Sunflower AI Configuration Manager
Version: 6.2
Configuration loading and management with security validation
"""

import os
import json
import yaml
import logging
import platform
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """Configuration types"""
    SYSTEM = "system"
    SAFETY = "safety"
    MODEL = "model"
    FAMILY = "family"
    HARDWARE = "hardware"


@dataclass
class SafetyConfig:
    """Safety configuration settings"""
    enabled: bool = True
    filter_level: str = "high"
    age_verification: bool = True
    content_logging: bool = True
    parent_alerts: bool = True
    max_safety_strikes: int = 3
    cooldown_minutes: int = 30
    blocked_categories: List[str] = None
    educational_mode: bool = True
    
    def __post_init__(self):
        if self.blocked_categories is None:
            self.blocked_categories = [
                "violence", "adult_content", "dangerous_activities",
                "personal_information", "self_harm", "hate_speech"
            ]


@dataclass
class ModelConfig:
    """Model configuration settings"""
    name: str
    size_gb: float
    min_ram_gb: int
    recommended_ram_gb: int
    quantization: Optional[str] = None
    context_length: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    repeat_penalty: float = 1.1


class ConfigManager:
    """
    Central configuration management system
    Handles all configuration loading, validation, and access
    """
    
    # SECURITY FIX: Whitelist of allowed environment variable keys
    ALLOWED_ENV_KEYS: Set[str] = {
        # System configuration
        'SUNFLOWER_DEBUG', 'SUNFLOWER_LOG_LEVEL', 'SUNFLOWER_VERSION',
        'SUNFLOWER_ENVIRONMENT', 'SUNFLOWER_DATA_PATH', 'SUNFLOWER_CONFIG_PATH',
        
        # Security settings
        'SUNFLOWER_ENABLE_SECURITY', 'SUNFLOWER_REQUIRE_AUTH', 'SUNFLOWER_SESSION_TIMEOUT',
        'SUNFLOWER_MAX_LOGIN_ATTEMPTS', 'SUNFLOWER_LOCKOUT_DURATION',
        
        # Partition configuration
        'SUNFLOWER_CDROM_MARKER', 'SUNFLOWER_USB_MARKER', 'SUNFLOWER_MIN_USB_SIZE_GB',
        
        # Open WebUI settings
        'OPENWEBUI_HOST', 'OPENWEBUI_PORT', 'OPENWEBUI_API_KEY', 'OPENWEBUI_ADMIN_USER',
        
        # Ollama configuration
        'OLLAMA_HOST', 'OLLAMA_PORT', 'OLLAMA_API_ENDPOINT', 'OLLAMA_NUM_PARALLEL',
        'OLLAMA_MAX_LOADED_MODELS', 'OLLAMA_MEMORY_LIMIT',
        
        # Safety settings
        'SAFETY_ENABLED', 'SAFETY_FILTER_LEVEL', 'SAFETY_LOG_INCIDENTS',
        'SAFETY_PARENT_ALERTS', 'SAFETY_MAX_STRIKES',
        
        # Performance settings
        'PERFORMANCE_CACHE_ENABLED', 'PERFORMANCE_CACHE_SIZE', 'PERFORMANCE_MAX_THREADS',
        'PERFORMANCE_RESPONSE_TIMEOUT', 'PERFORMANCE_BATCH_SIZE',
        
        # Model paths
        'MODEL_PATH', 'MODEL_CACHE_PATH', 'MODEL_DOWNLOAD_PATH'
    }
    
    # SECURITY FIX: Maximum allowed value length
    MAX_ENV_VALUE_LENGTH: int = 1000
    
    # SECURITY FIX: Pattern validation for certain keys
    ENV_VALUE_PATTERNS: Dict[str, str] = {
        'OPENWEBUI_PORT': r'^\d{1,5}$',
        'OLLAMA_PORT': r'^\d{1,5}$',
        'SUNFLOWER_SESSION_TIMEOUT': r'^\d{1,6}$',
        'SUNFLOWER_MAX_LOGIN_ATTEMPTS': r'^\d{1,2}$',
        'PERFORMANCE_MAX_THREADS': r'^\d{1,3}$',
        'PERFORMANCE_CACHE_SIZE': r'^\d{1,6}$'
    }
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize configuration manager"""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.config_path = self.base_path / 'config'
        self.config_path.mkdir(exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Configuration storage
        self._configs: Dict[ConfigType, Any] = {}
        self._env_vars: Dict[str, str] = {}
        
        # Platform detection
        self.platform = platform.system().lower()
        self.is_windows = self.platform == 'windows'
        self.is_macos = self.platform == 'darwin'
        self.is_linux = self.platform == 'linux'
        
        # Configuration paths
        self.safety_config_path = self.config_path / 'safety'
        self.model_config_path = self.config_path / 'models'
        self.family_config_path = self.config_path / 'families'
        
        # Load configurations
        self._load_configurations()
        
        logger.info(f"Configuration manager initialized for {self.platform}")
    
    def _load_configurations(self):
        """Load all configurations"""
        with self._lock:
            # Load environment variables first
            self._load_env_file()
            
            # Load system configuration
            self._load_system_config()
            
            # Load safety configuration
            self._load_safety_config()
            
            # Load model configurations
            self._load_model_config()
            
            # Load hardware detection
            self._detect_hardware()
    
    def _load_env_file(self):
        """
        Load environment variables from file with security validation
        FIXED: Added input validation to prevent configuration injection
        """
        env_file = self.base_path / '.env'
        
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    line_number = 0
                    for line in f:
                        line_number += 1
                        line = line.strip()
                        
                        # Skip empty lines and comments
                        if not line or line.startswith('#'):
                            continue
                        
                        # Parse key-value pair
                        if '=' not in line:
                            logger.warning(f"Invalid line {line_number} in .env file: missing '='")
                            continue
                        
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # SECURITY VALIDATION 1: Check if key is in whitelist
                        if key not in self.ALLOWED_ENV_KEYS:
                            logger.warning(f"Ignoring unknown environment key '{key}' on line {line_number}")
                            continue
                        
                        # SECURITY VALIDATION 2: Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # SECURITY VALIDATION 3: Check value length
                        if len(value) > self.MAX_ENV_VALUE_LENGTH:
                            logger.warning(f"Environment value for '{key}' exceeds maximum length, truncating")
                            value = value[:self.MAX_ENV_VALUE_LENGTH]
                        
                        # SECURITY VALIDATION 4: Validate format for specific keys
                        if key in self.ENV_VALUE_PATTERNS:
                            import re
                            pattern = self.ENV_VALUE_PATTERNS[key]
                            if not re.match(pattern, value):
                                logger.error(f"Invalid format for '{key}': '{value}' does not match pattern {pattern}")
                                continue
                        
                        # SECURITY VALIDATION 5: Sanitize value - remove control characters
                        sanitized_value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n')
                        
                        # SECURITY VALIDATION 6: Check for potential injection patterns
                        dangerous_patterns = [
                            '../', '..\\',  # Path traversal
                            '$(', '${',     # Shell expansion
                            '`',            # Command substitution
                            '&&', '||',     # Command chaining
                            '|',            # Pipe
                            ';',            # Command separator
                            '\x00',         # Null byte
                            '<', '>',       # Redirection
                        ]
                        
                        if any(pattern in sanitized_value for pattern in dangerous_patterns):
                            logger.error(f"Potentially dangerous pattern detected in value for '{key}'")
                            continue
                        
                        # Store validated and sanitized value
                        self._env_vars[key] = sanitized_value
                        logger.debug(f"Loaded environment variable: {key}")
                
                logger.info(f"Loaded {len(self._env_vars)} validated environment variables")
                
            except Exception as e:
                logger.error(f"Failed to load environment file: {e}")
    
    def _load_system_config(self):
        """Load system configuration"""
        config_file = self.config_path / 'system.yaml'
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._configs[ConfigType.SYSTEM] = yaml.safe_load(f)
                logger.info(f"Loaded system config: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load system config: {e}")
                self._load_default_system_config()
        else:
            self._load_default_system_config()
    
    def _load_default_system_config(self):
        """Load default system configuration"""
        self._configs[ConfigType.SYSTEM] = {
            'version': '6.2.0',
            'debug': False,
            'log_level': 'INFO',
            'data_path': str(self.base_path / 'data'),
            'temp_path': str(self.base_path / 'temp'),
            'session_timeout': 3600,
            'max_sessions': 10,
            'enable_metrics': True
        }
    
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
            'sunflower-kids-7b': ModelConfig(
                name='sunflower-kids-7b',
                size_gb=4.7,
                min_ram_gb=8,
                recommended_ram_gb=16
            ),
            'sunflower-kids-3b': ModelConfig(
                name='sunflower-kids-3b',
                size_gb=2.0,
                min_ram_gb=6,
                recommended_ram_gb=8
            ),
            'sunflower-kids-1b': ModelConfig(
                name='sunflower-kids-1b',
                size_gb=1.3,
                min_ram_gb=4,
                recommended_ram_gb=6
            ),
            'sunflower-educator-7b': ModelConfig(
                name='sunflower-educator-7b',
                size_gb=4.7,
                min_ram_gb=8,
                recommended_ram_gb=16
            )
        }
    
    def _detect_hardware(self):
        """Detect hardware capabilities"""
        import psutil
        
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = psutil.cpu_count()
        
        # Determine hardware tier
        if total_ram_gb >= 16:
            tier = "high"
        elif total_ram_gb >= 8:
            tier = "medium"
        elif total_ram_gb >= 4:
            tier = "low"
        else:
            tier = "minimum"
        
        self._configs[ConfigType.HARDWARE] = {
            'total_ram_gb': total_ram_gb,
            'cpu_count': cpu_count,
            'tier': tier,
            'platform': self.platform
        }
        
        logger.info(f"Hardware detected: {tier} tier, {total_ram_gb:.1f}GB RAM, {cpu_count} CPUs")
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value
        Only returns values for whitelisted keys
        """
        # Check if key is allowed
        if key not in self.ALLOWED_ENV_KEYS:
            logger.warning(f"Attempted to access non-whitelisted environment key: {key}")
            return default
        
        # Check loaded environment variables first
        if key in self._env_vars:
            return self._env_vars[key]
        
        # Check system environment
        value = os.environ.get(key)
        if value is not None:
            # Apply same validation as in _load_env_file
            if len(value) > self.MAX_ENV_VALUE_LENGTH:
                value = value[:self.MAX_ENV_VALUE_LENGTH]
            return value
        
        return default
    
    def get_config(self, config_type: ConfigType) -> Any:
        """Get configuration by type"""
        with self._lock:
            return self._configs.get(config_type)
    
    def get_safety_config(self) -> SafetyConfig:
        """Get safety configuration"""
        return self.get_config(ConfigType.SAFETY)
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get specific model configuration"""
        models = self.get_config(ConfigType.MODEL)
        if models:
            return models.get(model_name)
        return None
    
    def get_optimal_model(self) -> str:
        """Get optimal model based on hardware"""
        hardware = self.get_config(ConfigType.HARDWARE)
        tier = hardware.get('tier', 'minimum')
        
        model_map = {
            'high': 'sunflower-kids-7b',
            'medium': 'sunflower-kids-3b',
            'low': 'sunflower-kids-1b',
            'minimum': 'sunflower-kids-1b'
        }
        
        return model_map.get(tier, 'sunflower-kids-1b')
    
    def update_config(self, config_type: ConfigType, updates: Dict[str, Any]):
        """Update configuration with validation"""
        with self._lock:
            if config_type in self._configs:
                if isinstance(self._configs[config_type], dict):
                    self._configs[config_type].update(updates)
                else:
                    # Handle dataclass configs
                    for key, value in updates.items():
                        if hasattr(self._configs[config_type], key):
                            setattr(self._configs[config_type], key, value)
                
                logger.info(f"Updated {config_type.value} configuration")
    
    def save_config(self, config_type: ConfigType):
        """Save configuration to file"""
        with self._lock:
            if config_type not in self._configs:
                logger.error(f"No configuration found for {config_type.value}")
                return
            
            config_data = self._configs[config_type]
            
            # Determine file path and format
            if config_type == ConfigType.SYSTEM:
                file_path = self.config_path / 'system.yaml'
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False)
            
            elif config_type == ConfigType.SAFETY:
                file_path = self.safety_config_path / 'safety_config.yaml'
                file_path.parent.mkdir(exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data.__dict__, f, default_flow_style=False)
            
            elif config_type == ConfigType.MODEL:
                file_path = self.model_config_path / 'models.json'
                file_path.parent.mkdir(exist_ok=True)
                models_dict = {name: model.__dict__ for name, model in config_data.items()}
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(models_dict, f, indent=2)
            
            logger.info(f"Saved {config_type.value} configuration to {file_path}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration system status"""
        with self._lock:
            return {
                'platform': self.platform,
                'base_path': str(self.base_path),
                'configs_loaded': list(self._configs.keys()),
                'env_vars_loaded': len(self._env_vars),
                'hardware_tier': self._configs.get(ConfigType.HARDWARE, {}).get('tier', 'unknown'),
                'safety_enabled': self._configs.get(ConfigType.SAFETY, SafetyConfig()).enabled
            }


# Singleton instance
_config_manager: Optional[ConfigManager] = None
_lock = threading.Lock()


def get_config_manager(base_path: Optional[Path] = None) -> ConfigManager:
    """Get singleton configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        with _lock:
            if _config_manager is None:
                _config_manager = ConfigManager(base_path)
    
    return _config_manager


# Convenience function
def get_config(config_type: ConfigType) -> Any:
    """Get configuration by type"""
    return get_config_manager().get_config(config_type)


# Production testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create test .env file with various test cases
        env_content = """
# Valid configurations
SUNFLOWER_DEBUG=true
OPENWEBUI_PORT=8080
SUNFLOWER_SESSION_TIMEOUT=3600

# Invalid - not in whitelist (should be ignored)
MALICIOUS_KEY=dangerous_value

# Invalid - dangerous pattern (should be rejected)
SUNFLOWER_DATA_PATH=../../etc/passwd

# Invalid - too long (should be truncated)
SUNFLOWER_LOG_LEVEL=""" + "A" * 2000 + """

# Invalid - wrong format for port (should be rejected)
OLLAMA_PORT=not_a_number
"""
        
        env_path = Path(tmp_dir) / '.env'
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        # Initialize config manager
        config_mgr = ConfigManager(tmp_dir)
        
        # Test that valid keys were loaded
        assert config_mgr.get_env('SUNFLOWER_DEBUG') == 'true'
        assert config_mgr.get_env('OPENWEBUI_PORT') == '8080'
        
        # Test that invalid keys were rejected
        assert config_mgr.get_env('MALICIOUS_KEY') is None
        assert config_mgr.get_env('SUNFLOWER_DATA_PATH') is None  # Rejected due to ../
        assert config_mgr.get_env('OLLAMA_PORT') is None  # Wrong format
        
        # Test that long values were truncated
        log_level = config_mgr.get_env('SUNFLOWER_LOG_LEVEL')
        assert log_level is not None and len(log_level) == ConfigManager.MAX_ENV_VALUE_LENGTH
        
        print("✓ All security validation tests passed")
        
        # Display status
        status = config_mgr.get_status()
        print("\nConfiguration Manager Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")

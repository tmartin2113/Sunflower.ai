"""
Configuration management for Sunflower AI
Handles all application settings and paths
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
import logging


class Config:
    """Central configuration management"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.is_frozen = getattr(sys, 'frozen', False)
        self.is_usb_mode = self._detect_usb_mode()
        
        # Load partition information
        from platform.partition_detector import PartitionDetector
        self.detector = PartitionDetector()
        
        # Set up paths based on environment
        self._setup_paths()
        
        # Load configuration
        self._load_config()
    
    def _detect_usb_mode(self):
        """Check if running from USB with CD-ROM partition"""
        security_marker = self.root_dir / ".security" / "fingerprint.sig"
        return security_marker.exists()
    
    def _setup_paths(self):
        """Setup all application paths"""
        if self.is_usb_mode and self.detector.cdrom_path:
            # Running from USB - use detected partitions
            self.cdrom_path = self.detector.cdrom_path
            self.data_path = self.detector.usb_path or self._get_local_data_path()
        else:
            # Development or local installation
            self.cdrom_path = self.root_dir
            self.data_path = self._get_local_data_path()
        
        # Read-only paths (from CD-ROM or development)
        self.models_path = self.cdrom_path / "models"
        self.resources_path = self.cdrom_path / "resources"
        self.web_path = self.cdrom_path / "src" / "web"
        
        # Platform-specific paths
        if os.environ.get('SUNFLOWER_PLATFORM') == 'Windows':
            self.ollama_path = self.cdrom_path / "Windows" / "ollama" / "ollama.exe"
        else:
            self.ollama_path = self.cdrom_path / "macOS" / "ollama-darwin"
        
        # Writable paths (always on data partition or local)
        self.profiles_path = self.data_path / "profiles"
        self.conversations_path = self.data_path / "conversations"
        self.logs_path = self.data_path / "logs"
        self.cache_path = self.data_path / "cache"
        self.settings_path = self.data_path / "settings.json"
        
        # Ensure writable directories exist
        self._ensure_directories()
    
    def get_app_dir(self) -> Path:
        """Returns the root application data directory."""
        return self.data_path

    def get_config_path(self) -> Path:
        """Returns the path to the configuration directory."""
        # In a real app, this might be different from the root.
        # Here, we assume config files are at the root.
        return self.root_dir / "config"

    def _get_local_data_path(self):
        """Get local data path for non-USB installations"""
        if os.environ.get('SUNFLOWER_PLATFORM') == 'Windows':
            base_path = Path(os.environ['APPDATA']) / "SunflowerAI"
        else:
            base_path = Path.home() / ".sunflowerai"
        
        return base_path
    
    def _ensure_directories(self):
        """Create necessary directories"""
        dirs = [
            self.profiles_path,
            self.conversations_path,
            self.logs_path,
            self.cache_path
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self):
        """Load configuration from file"""
        self.settings = {
            'theme': 'default',
            'auto_save_interval': 300,  # 5 minutes
            'session_timeout': 1800,    # 30 minutes
            'max_conversation_history': 100,
            'safety_level': 'maximum',
            'model_preferences': {
                'auto_select': True,
                'preferred_quality': 'balanced'
            },
            'ui_preferences': {
                'font_size': 12,
                'show_timestamps': True,
                'sound_enabled': True
            }
        }
        
        # Load saved settings if they exist
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r') as f:
                    saved_settings = json.load(f)
                    
                    # Deep update for nested dictionaries
                    for key, value in saved_settings.items():
                        if isinstance(value, dict) and isinstance(self.settings.get(key), dict):
                            self.settings[key].update(value)
                        else:
                            self.settings[key] = value

            except Exception:
                pass  # Use defaults if loading fails
    
    def save(self):
        """Save current settings to file"""
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get_setting(self, key: str, default=None):
        """
        Get a setting value using dot notation for nested keys.
        Example: get_setting('ui_preferences.font_size')
        """
        keys = key.split('.')
        value = self.settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set_setting(self, key: str, value):
        """
        Set a setting value using dot notation for nested keys.
        Example: set_setting('ui_preferences.font_size', 14)
        """
        keys = key.split('.')
        d = self.settings
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def get_model_config(self):
        """Get model configuration"""
        model_manifest_path = self.models_path / "model_manifest.json"
        
        if model_manifest_path.exists():
            with open(model_manifest_path, 'r') as f:
                return json.load(f)
        
        # Default configuration if manifest not found
        return {
            'base_models': ['llama3.2:1b'],
            'variants': ['kids', 'educator'],
            'models': []
        }
    
    def get_theme_path(self, theme_name=None):
        """Get path to theme CSS file"""
        if theme_name is None:
            theme_name = self.settings.get('theme', 'default')
        
        return self.web_path / "css" / "themes" / f"{theme_name}.css"
    
    def get_icon(self, name):
        """Get path to icon file"""
        return self.resources_path / "icons" / name
    
    def get_font(self, name):
        """Get path to font file"""
        return self.resources_path / "fonts" / name

_config_instance = None

def get_config():
    """Singleton accessor for the Config object"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def get_model_registry():
    """
    Loads and returns the model registry from the JSON file.

    The model registry contains metadata about all available models,
    including their hardware requirements.

    Returns:
        dict: A dictionary containing the model registry data, or an
              empty dictionary if the file cannot be read.
    """
    config = get_config()
    registry_path = config.get_config_path() / 'model_registry.json'
    
    if not registry_path.exists():
        logging.error(f"Model registry not found at: {registry_path}")
        return {}
    
    try:
        with open(registry_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Failed to load or parse model registry: {e}")
        return {}

#!/usr/bin/env python3
"""
Configuration management for Sunflower AI
Handles all application settings, paths, and Open WebUI integration
"""

import os
import json
import sys
import platform
import secrets
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Optional, Any


class Config:
    """Central configuration management for Sunflower AI with Open WebUI"""
    
    # Application metadata
    APP_NAME = "Sunflower AI Professional System"
    APP_VERSION = "1.0.0"
    COMPANY = "Sunflower AI"
    
    # Open WebUI settings
    WEBUI_PORT = 8080
    WEBUI_HOST = "127.0.0.1"
    OLLAMA_PORT = 11434
    
    def __init__(self):
        """Initialize configuration system"""
        self.root_dir = Path(__file__).parent.parent
        self.is_frozen = getattr(sys, 'frozen', False)
        self.system = platform.system()
        
        # Detect if running from USB/CD-ROM
        self.is_usb_mode = self._detect_usb_mode()
        
        # Load partition information
        self._detect_partitions()
        
        # Set up all paths
        self._setup_paths()
        
        # Load configuration
        self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize Open WebUI settings
        self._setup_openwebui_config()
    
    def _detect_usb_mode(self) -> bool:
        """Check if running from USB with CD-ROM partition"""
        # Check for CD-ROM marker
        cdrom_marker = self.root_dir.parent / "sunflower_cd.id"
        if cdrom_marker.exists():
            return True
            
        # Check for USB marker
        usb_marker = self.root_dir.parent / "sunflower_data.id"
        if usb_marker.exists():
            return True
            
        # Check for security fingerprint
        security_marker = self.root_dir / ".security" / "fingerprint.sig"
        return security_marker.exists()
    
    def _detect_partitions(self):
        """Detect CD-ROM and USB partitions"""
        self.cdrom_path = None
        self.usb_path = None
        
        try:
            from src.platform.partition_detector import PartitionDetector
            detector = PartitionDetector()
            self.cdrom_path = detector.cdrom_path
            self.usb_path = detector.usb_path
        except ImportError:
            # Fallback to manual detection
            self._manual_partition_detection()
    
    def _manual_partition_detection(self):
        """Manually detect partitions without partition_detector module"""
        if self.system == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:/")
                if drive_path.exists():
                    # Check for CD-ROM marker
                    if (drive_path / "sunflower_cd.id").exists():
                        self.cdrom_path = drive_path
                    # Check for USB marker
                    if (drive_path / "sunflower_data.id").exists():
                        self.usb_path = drive_path
        else:
            # macOS/Linux
            for volume_base in ["/Volumes", "/media", "/mnt"]:
                volume_path = Path(volume_base)
                if volume_path.exists():
                    for mount in volume_path.iterdir():
                        if (mount / "sunflower_cd.id").exists():
                            self.cdrom_path = mount
                        if (mount / "sunflower_data.id").exists():
                            self.usb_path = mount
    
    def _setup_paths(self):
        """Setup all application paths including Open WebUI"""
        # Determine base paths
        if self.is_usb_mode:
            # Running from USB - use detected partitions
            if self.cdrom_path:
                self.app_path = self.cdrom_path
            else:
                self.app_path = self.root_dir
                
            if self.usb_path:
                self.data_path = self.usb_path / "sunflower_data"
            else:
                self.data_path = self._get_local_data_path()
        else:
            # Development or local installation
            self.app_path = self.root_dir
            self.data_path = self._get_local_data_path()
        
        # Read-only paths (from CD-ROM or development)
        self.models_path = self.app_path / "models"
        self.modelfiles_path = self.app_path / "modelfiles"
        self.resources_path = self.app_path / "resources"
        self.launchers_path = self.app_path / "launchers"
        
        # Platform-specific executable paths
        if self.system == "Windows":
            self.ollama_path = self.app_path / "ollama" / "ollama.exe"
            self.platform_launcher = self.launchers_path / "windows_launcher.bat"
        else:
            self.ollama_path = self.app_path / "ollama" / "ollama"
            self.platform_launcher = self.launchers_path / "macos_launcher.sh"
        
        # Open WebUI specific paths (writable)
        self.openwebui_dir = self.data_path / "openwebui"
        self.openwebui_data = self.openwebui_dir / "data"
        self.openwebui_config = self.openwebui_dir / "config"
        self.openwebui_db = self.openwebui_data / "webui.db"
        self.openwebui_uploads = self.openwebui_data / "uploads"
        self.openwebui_cache = self.openwebui_data / "cache"
        
        # User data paths (writable)
        self.profiles_path = self.data_path / "profiles"
        self.conversations_path = self.data_path / "conversations"
        self.sessions_path = self.data_path / "sessions"
        self.logs_path = self.data_path / "logs"
        self.cache_path = self.data_path / "cache"
        self.backups_path = self.data_path / "backups"
        
        # Configuration files
        self.settings_path = self.data_path / "settings.json"
        self.family_config_path = self.profiles_path / "family.json"
        self.safety_config_path = self.data_path / "safety_config.json"
        
        # Security paths
        self.security_path = self.data_path / ".security"
        self.tokens_path = self.security_path / "tokens.json"
        self.certificates_path = self.security_path / "certificates"
        
        # Ollama paths
        self.ollama_models_path = self.data_path / "ollama" / "models"
        self.ollama_manifests_path = self.data_path / "ollama" / "manifests"
        
        # Parent dashboard
        self.dashboard_path = self.data_path / "parent_dashboard.html"
        
        # Ensure all writable directories exist
        self._ensure_directories()
    
    def _get_local_data_path(self) -> Path:
        """Get local data path based on OS"""
        if self.system == "Windows":
            # Use AppData on Windows
            app_data = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
            return app_data / "SunflowerAI" / "data"
        else:
            # Use home directory on macOS/Linux
            return Path.home() / ".sunflower_ai" / "data"
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.data_path,
            self.openwebui_dir,
            self.openwebui_data,
            self.openwebui_config,
            self.openwebui_uploads,
            self.openwebui_cache,
            self.profiles_path,
            self.conversations_path,
            self.sessions_path,
            self.logs_path,
            self.cache_path,
            self.backups_path,
            self.security_path,
            self.certificates_path,
            self.ollama_models_path,
            self.ollama_manifests_path,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self):
        """Load or create configuration file"""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r') as f:
                    self.settings = json.load(f)
            except json.JSONDecodeError:
                self.settings = self._get_default_settings()
                self._save_config()
        else:
            self.settings = self._get_default_settings()
            self._save_config()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings"""
        return {
            "version": self.APP_VERSION,
            "first_run": True,
            "device_id": secrets.token_hex(16),
            "created": datetime.now().isoformat(),
            "safety": {
                "enabled": True,
                "level": "high",
                "log_incidents": True,
                "notify_parents": True
            },
            "session": {
                "timeout_minutes": 60,
                "auto_save": True,
                "recording": True
            },
            "models": {
                "default": "sunflower-kids",
                "available": ["sunflower-kids", "sunflower-educator"],
                "auto_select": True
            },
            "ui": {
                "theme": "light",
                "language": "en",
                "show_tips": True
            },
            "ollama": {
                "host": "localhost",
                "port": self.OLLAMA_PORT,
                "keep_alive": "5m",
                "num_parallel": 1
            },
            "openwebui": {
                "host": self.WEBUI_HOST,
                "port": self.WEBUI_PORT,
                "auth_enabled": True,
                "signup_enabled": False
            }
        }
    
    def _save_config(self):
        """Save configuration to file"""
        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = self.logs_path / f"sunflower_{datetime.now():%Y%m%d}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("SunflowerAI.Config")
        self.logger.info(f"Configuration initialized - Version {self.APP_VERSION}")
    
    def _setup_openwebui_config(self):
        """Setup Open WebUI specific configuration"""
        self.openwebui_env = {
            # Core settings
            "DATA_DIR": str(self.openwebui_data),
            "WEBUI_NAME": self.APP_NAME,
            "WEBUI_VERSION": self.APP_VERSION,
            
            # Network settings
            "HOST": self.WEBUI_HOST,
            "PORT": str(self.WEBUI_PORT),
            "WEBUI_URL": f"http://{self.WEBUI_HOST}:{self.WEBUI_PORT}",
            
            # Authentication
            "WEBUI_AUTH": "true",
            "ENABLE_SIGNUP": "false",
            "DEFAULT_USER_ROLE": "user",
            
            # Ollama integration
            "OLLAMA_BASE_URL": f"http://localhost:{self.OLLAMA_PORT}",
            "ENABLE_OLLAMA_API": "true",
            "OLLAMA_API_BASE_URL": f"http://localhost:{self.OLLAMA_PORT}/api",
            
            # Model settings
            "DEFAULT_MODELS": "sunflower-kids,sunflower-educator",
            "MODEL_FILTER_ENABLED": "true",
            "MODEL_FILTER_LIST": "sunflower-kids,sunflower-educator,llama3.2:3b,llama3.2:1b",
            
            # Features
            "ENABLE_MODEL_FILTER": "true",
            "ENABLE_COMMUNITY_SHARING": "false",
            "ENABLE_ADMIN_EXPORT": "true",
            "ENABLE_MESSAGE_RATING": "true",
            "SHOW_ADMIN_DETAILS": "false",
            
            # Security
            "WEBUI_SESSION_COOKIE_SAME_SITE": "lax",
            "WEBUI_SESSION_COOKIE_SECURE": "false",  # Local use only
            
            # Paths
            "UPLOAD_DIR": str(self.openwebui_uploads),
            "CACHE_DIR": str(self.openwebui_cache),
            "STATIC_DIR": str(self.resources_path),
            
            # Database
            "DATABASE_URL": f"sqlite:///{self.openwebui_db}",
            
            # Logging
            "LOG_LEVEL": "INFO",
            "LOG_DIR": str(self.logs_path),
        }
    
    # Public methods for configuration access
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        target = self.settings
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
        self._save_config()
    
    def get_openwebui_env(self) -> Dict[str, str]:
        """Get Open WebUI environment variables"""
        return self.openwebui_env.copy()
    
    def apply_openwebui_env(self):
        """Apply Open WebUI environment variables to current process"""
        for key, value in self.openwebui_env.items():
            os.environ[key] = value
    
    def is_first_run(self) -> bool:
        """Check if this is the first run"""
        return self.get("first_run", True)
    
    def mark_first_run_complete(self):
        """Mark first run as complete"""
        self.set("first_run", False)
    
    def get_device_id(self) -> str:
        """Get unique device identifier"""
        return self.get("device_id")
    
    def get_safety_level(self) -> str:
        """Get current safety level"""
        return self.get("safety.level", "high")
    
    def set_safety_level(self, level: str):
        """Set safety level (maximum, high, moderate, standard)"""
        valid_levels = ["maximum", "high", "moderate", "standard"]
        if level in valid_levels:
            self.set("safety.level", level)
    
    def get_default_model(self) -> str:
        """Get default AI model"""
        return self.get("models.default", "sunflower-kids")
    
    def get_available_models(self) -> list:
        """Get list of available models"""
        return self.get("models.available", ["sunflower-kids"])
    
    def get_ollama_url(self) -> str:
        """Get Ollama API URL"""
        host = self.get("ollama.host", "localhost")
        port = self.get("ollama.port", self.OLLAMA_PORT)
        return f"http://{host}:{port}"
    
    def get_webui_url(self) -> str:
        """Get Open WebUI URL"""
        host = self.get("openwebui.host", self.WEBUI_HOST)
        port = self.get("openwebui.port", self.WEBUI_PORT)
        return f"http://{host}:{port}"
    
    def validate_paths(self) -> bool:
        """Validate all critical paths exist"""
        critical_paths = [
            self.data_path,
            self.logs_path,
            self.profiles_path
        ]
        
        for path in critical_paths:
            if not path.exists():
                self.logger.error(f"Critical path missing: {path}")
                return False
        
        return True
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for diagnostics"""
        return {
            "app_version": self.APP_VERSION,
            "platform": self.system,
            "python_version": sys.version,
            "is_frozen": self.is_frozen,
            "is_usb_mode": self.is_usb_mode,
            "cdrom_detected": self.cdrom_path is not None,
            "usb_detected": self.usb_path is not None,
            "app_path": str(self.app_path),
            "data_path": str(self.data_path),
            "ollama_exists": self.ollama_path.exists() if self.ollama_path else False,
            "device_id": self.get_device_id()
        }
    
    def export_config(self, output_path: Path):
        """Export configuration for backup"""
        export_data = {
            "settings": self.settings,
            "system_info": self.get_system_info(),
            "export_date": datetime.now().isoformat(),
            "version": self.APP_VERSION
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def import_config(self, input_path: Path):
        """Import configuration from backup"""
        with open(input_path, 'r') as f:
            import_data = json.load(f)
        
        if "settings" in import_data:
            self.settings = import_data["settings"]
            self._save_config()
            self.logger.info(f"Configuration imported from {input_path}")


# Singleton instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get or create configuration singleton"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# Convenience exports
if __name__ == "__main__":
    # Test configuration
    config = get_config()
    
    print("Sunflower AI Configuration")
    print("=" * 50)
    print(f"Version: {config.APP_VERSION}")
    print(f"Platform: {config.system}")
    print(f"USB Mode: {config.is_usb_mode}")
    print(f"Data Path: {config.data_path}")
    print(f"OpenWebUI Path: {config.openwebui_data}")
    print(f"First Run: {config.is_first_run()}")
    print(f"Device ID: {config.get_device_id()}")
    print("\nSystem Info:")
    for key, value in config.get_system_info().items():
        print(f"  {key}: {value}")

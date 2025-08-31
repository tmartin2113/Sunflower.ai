"""
Sunflower AI Professional System - Core Source Package
Version: 6.2
Copyright (c) 2025 Sunflower AI

Main source package providing core functionality for the educational system.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Package metadata
__version__ = "6.2.0"
__author__ = "Sunflower AI"
__copyright__ = "Copyright (c) 2025 Sunflower AI"
__license__ = "Proprietary"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sunflower_ai.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# System constants
CDROM_MARKER = "sunflower_cd.id"
USB_MARKER = "sunflower_data.id"
MIN_PYTHON_VERSION = (3, 8)
SUPPORTED_PLATFORMS = ["Windows", "Darwin", "Linux"]

# Hardware tiers for model selection
HARDWARE_TIERS = {
    "ultra": {"ram": 16, "cores": 8, "model": "llama3.2:7b"},
    "high": {"ram": 8, "cores": 4, "model": "llama3.2:3b"},
    "standard": {"ram": 4, "cores": 2, "model": "llama3.2:1b"},
    "minimum": {"ram": 4, "cores": 2, "model": "llama3.2:1b-q4_0"}
}

# Age groups for content adaptation
AGE_GROUPS = {
    "early": {"min": 2, "max": 7, "name": "Early Learner"},
    "elementary": {"min": 8, "max": 10, "name": "Elementary"},
    "middle": {"min": 11, "max": 13, "name": "Middle School"},
    "high": {"min": 14, "max": 18, "name": "High School"}
}


class SunflowerAIError(Exception):
    """Base exception for Sunflower AI system"""
    pass


class PartitionError(SunflowerAIError):
    """Raised when partition operations fail"""
    pass


class ProfileError(SunflowerAIError):
    """Raised when profile operations fail"""
    pass


class SecurityError(SunflowerAIError):
    """Raised when security operations fail"""
    pass


class ModelError(SunflowerAIError):
    """Raised when model operations fail"""
    pass


def check_python_version():
    """Verify Python version meets requirements"""
    if sys.version_info < MIN_PYTHON_VERSION:
        raise RuntimeError(
            f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} or higher required. "
            f"Current version: {sys.version_info.major}.{sys.version_info.minor}"
        )


def check_platform():
    """Verify platform is supported"""
    current_platform = platform.system()
    if current_platform not in SUPPORTED_PLATFORMS:
        raise RuntimeError(
            f"Unsupported platform: {current_platform}. "
            f"Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}"
        )
    return current_platform


def get_app_directory() -> Path:
    """Get application root directory"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent.parent


def get_data_directory() -> Path:
    """Get user data directory (on USB partition)"""
    from .partition_manager import PartitionManager
    pm = PartitionManager()
    usb_path = pm.find_usb_partition()
    if not usb_path:
        raise PartitionError("USB data partition not found")
    return usb_path


def get_config_path() -> Path:
    """Get configuration file path"""
    return get_app_directory() / "config"


def load_system_config() -> Dict[str, Any]:
    """Load system configuration from CD-ROM partition"""
    config_path = get_config_path() / "version.json"
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {config_path}")
        return get_default_config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Get default system configuration"""
    return {
        "version": __version__,
        "app_name": "Sunflower AI Professional",
        "company": "Sunflower AI",
        "build_date": datetime.now().isoformat(),
        "features": {
            "offline_mode": True,
            "multi_profile": True,
            "parent_dashboard": True,
            "age_adaptation": True,
            "safety_filter": True
        },
        "requirements": {
            "min_ram_gb": 4,
            "min_cores": 2,
            "min_python": "3.8",
            "platforms": SUPPORTED_PLATFORMS
        }
    }


def initialize_system() -> bool:
    """Initialize the Sunflower AI system"""
    try:
        logger.info("=" * 60)
        logger.info("Sunflower AI Professional System Initializing")
        logger.info(f"Version: {__version__}")
        logger.info("=" * 60)
        
        # Check Python version
        check_python_version()
        logger.info(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}")
        
        # Check platform
        platform_name = check_platform()
        logger.info(f"✓ Platform: {platform_name}")
        
        # Load configuration
        config = load_system_config()
        logger.info(f"✓ Configuration loaded: {config['app_name']} v{config['version']}")
        
        # Initialize partition manager
        from .partition_manager import PartitionManager
        pm = PartitionManager()
        
        # Find CD-ROM partition
        cdrom = pm.find_cdrom_partition()
        if cdrom:
            logger.info(f"✓ CD-ROM partition found: {cdrom}")
        else:
            logger.warning("⚠ CD-ROM partition not found - development mode")
        
        # Find USB partition
        usb = pm.find_usb_partition()
        if usb:
            logger.info(f"✓ USB partition found: {usb}")
        else:
            logger.warning("⚠ USB partition not found - will create on first run")
        
        # Detect hardware
        from .hardware_detector import HardwareDetector
        hw = HardwareDetector()
        tier = hw.get_hardware_tier()
        logger.info(f"✓ Hardware tier: {tier}")
        
        # Initialize security
        from .security import SecurityManager
        sm = SecurityManager()
        if sm.initialize():
            logger.info("✓ Security system initialized")
        
        logger.info("=" * 60)
        logger.info("System initialization complete")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        return False


# Auto-initialize on import in production mode
if os.environ.get('SUNFLOWER_ENV') != 'development':
    try:
        import platform
        # Only auto-initialize if not being imported by build tools
        if not any(tool in sys.argv[0] for tool in ['pyinstaller', 'setup.py', 'pip']):
            initialize_system()
    except Exception as e:
        logger.warning(f"Auto-initialization skipped: {e}")


# Public API exports
__all__ = [
    '__version__',
    'SunflowerAIError',
    'PartitionError', 
    'ProfileError',
    'SecurityError',
    'ModelError',
    'HARDWARE_TIERS',
    'AGE_GROUPS',
    'initialize_system',
    'get_app_directory',
    'get_data_directory',
    'get_config_path',
    'load_system_config'
]

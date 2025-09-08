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
import platform  # FIX: Added missing import
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
    current_platform = platform.system()  # Now 'platform' is properly imported
    if current_platform not in SUPPORTED_PLATFORMS:
        raise RuntimeError(
            f"Unsupported platform: {current_platform}. "
            f"Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}"
        )
    return current_platform


def get_hardware_tier():
    """Determine hardware tier based on system capabilities"""
    try:
        import psutil
        
        # Get system RAM in GB
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        
        # Get CPU core count
        cpu_cores = psutil.cpu_count(logical=False) or 2
        
        # Determine tier
        if ram_gb >= 16 and cpu_cores >= 8:
            return "ultra"
        elif ram_gb >= 8 and cpu_cores >= 4:
            return "high"
        elif ram_gb >= 4:
            return "standard"
        else:
            return "minimum"
            
    except ImportError:
        logger.warning("psutil not available, defaulting to standard tier")
        return "standard"
    except Exception as e:
        logger.error(f"Error determining hardware tier: {e}")
        return "standard"


def get_age_group(age: int) -> Dict[str, Any]:
    """Get age group configuration for a given age"""
    for group_key, group_config in AGE_GROUPS.items():
        if group_config["min"] <= age <= group_config["max"]:
            return {
                "key": group_key,
                **group_config
            }
    
    # Default to high school for ages above 18
    return {
        "key": "high",
        **AGE_GROUPS["high"]
    }


def initialize_system():
    """Initialize the Sunflower AI system"""
    logger.info("=" * 60)
    logger.info(f"Sunflower AI Professional System v{__version__}")
    logger.info(f"Copyright {__copyright__}")
    logger.info("=" * 60)
    
    # Check Python version
    check_python_version()
    logger.info(f"Python version: {sys.version}")
    
    # Check platform
    platform_name = check_platform()
    logger.info(f"Platform: {platform_name}")
    
    # Determine hardware tier
    hardware_tier = get_hardware_tier()
    logger.info(f"Hardware tier: {hardware_tier}")
    logger.info(f"Selected model: {HARDWARE_TIERS[hardware_tier]['model']}")
    
    return {
        "version": __version__,
        "platform": platform_name,
        "hardware_tier": hardware_tier,
        "model": HARDWARE_TIERS[hardware_tier]["model"]
    }


# Export main components
__all__ = [
    'SunflowerAIError',
    'PartitionError',
    'ProfileError',
    'SecurityError',
    'ModelError',
    'check_python_version',
    'check_platform',
    'get_hardware_tier',
    'get_age_group',
    'initialize_system',
    'HARDWARE_TIERS',
    'AGE_GROUPS',
    '__version__'
]

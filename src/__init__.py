"""
Sunflower AI STEM Education System

A family-friendly AI-powered STEM education platform for K-12 students.
Designed for offline operation with USB authentication and comprehensive
parent controls.

Key Features:
- Multi-child family profiles
- Age-adaptive AI responses
- Complete STEM curriculum coverage
- Parent dashboard for monitoring
- USB-based authentication
- Offline operation after setup
"""

# Import main packages
from . import profiles
from . import security
from . import platform

# Package metadata
__version__ = '6.1.0'
__author__ = 'Sunflower AI'
__license__ = 'Commercial'

# System requirements
SYSTEM_REQUIREMENTS = {
    'python_min': '3.7',
    'ram_min_gb': 4,
    'ram_recommended_gb': 8,
    'disk_space_gb': 10,
    'platforms': ['Windows 10+', 'macOS 10.15+']
}

# Default configuration
DEFAULT_CONFIG = {
    'app_name': 'Sunflower AI',
    'app_dir': '.sunflower-ai',
    'log_level': 'INFO',
    'max_children_per_family': 10,
    'session_timeout_minutes': 60,
    'safety_mode': 'strict'
}

def get_version():
    """Get the current version of Sunflower AI"""
    return __version__

def check_requirements():
    """Check if system meets minimum requirements"""
    import sys
    import platform
    
    # Check Python version
    python_version = sys.version_info
    min_version = tuple(map(int, SYSTEM_REQUIREMENTS['python_min'].split('.')))
    
    if python_version < min_version:
        return False, f"Python {SYSTEM_REQUIREMENTS['python_min']}+ required"
    
    # Check platform
    current_platform = platform.system()
    if current_platform not in ['Windows', 'Darwin']:
        return False, f"Unsupported platform: {current_platform}"
    
    return True, "All requirements met"

# Public API
__all__ = [
    'profiles',
    'security',
    'platform',
    'get_version',
    'check_requirements',
    'SYSTEM_REQUIREMENTS',
    'DEFAULT_CONFIG'
]

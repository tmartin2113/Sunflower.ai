"""
Sunflower AI Platform Integration Package

This package handles platform-specific features:
- Hardware detection and capability assessment
- Model selection based on system resources
- OS-specific integration (shortcuts, notifications, etc.)
- Performance monitoring and tuning
- Partition detection for USB/CD-ROM drives
"""

from .hardware_detector import HardwareDetector
from .os_integration import OSIntegration, get_os_integration
from .partition_detector import PartitionDetector
from .base import BasePlatform, PlatformFactory

# Import platform-specific implementations if available
try:
    from .windows import WindowsPlatform
except ImportError:
    WindowsPlatform = None

try:
    from .macos import MacOSPlatform
except ImportError:
    MacOSPlatform = None

__all__ = [
    'HardwareDetector',
    'OSIntegration',
    'PartitionDetector',
    'BasePlatform',
    'PlatformFactory',
    'get_os_integration',
    'WindowsPlatform',
    'MacOSPlatform',
]

# Package version
__version__ = '1.0.0'

# Platform constants
SUPPORTED_PLATFORMS = ['Windows', 'Darwin']  # Windows and macOS
MIN_PYTHON_VERSION = (3, 7)
MIN_RAM_GB = 4
RECOMMENDED_RAM_GB = 8

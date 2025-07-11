"""
Sunflower AI Platform Integration Package

This package handles platform-specific features:
- Hardware detection and capability assessment
- Model optimization based on system resources
- OS-specific integration (shortcuts, notifications, etc.)
- Performance monitoring and tuning
"""

from .hardware_detector import HardwareDetector
from .model_optimizer import ModelOptimizer
from .os_integration import OSIntegration

__all__ = [
    'HardwareDetector',
    'ModelOptimizer',
    'OSIntegration'
]

# Package version
__version__ = '1.0.0'

# Platform constants
SUPPORTED_PLATFORMS = ['Windows', 'Darwin']  # Windows and macOS
MIN_PYTHON_VERSION = (3, 7)
MIN_RAM_GB = 4
RECOMMENDED_RAM_GB = 8

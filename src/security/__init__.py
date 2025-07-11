"""
Sunflower AI Security Package

This package handles USB authentication and token management:
- USB drive detection and validation
- Authentication token verification
- Token generation for manufacturing
- Hardware-based security
"""

from .usb_auth import USBAuthenticator, USBTokenValidator
from .token_generator import TokenGenerator, ProductionTokenGenerator

__all__ = [
    'USBAuthenticator',
    'USBTokenValidator',
    'TokenGenerator',
    'ProductionTokenGenerator'
]

# Package version
__version__ = '1.0.0'

# Security constants
TOKEN_VERSION = '6.1'
PRODUCT_ID = 'SUNFLOWER_AI_STEM_EDU'

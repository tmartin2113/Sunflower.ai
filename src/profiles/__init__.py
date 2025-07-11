"""
Sunflower AI Profile Management Package

This package handles all family profile management including:
- Parent account management with password protection
- Child profile creation and management
- Session logging and tracking
- Parent dashboard for monitoring
- Secure storage with encryption
"""

from .profile_manager import ProfileManager
from .session_logger import SessionLogger, SessionEntry
from .parent_dashboard import ParentDashboard
from .profile_storage import ProfileStorage

__all__ = [
    'ProfileManager',
    'SessionLogger',
    'SessionEntry',
    'ParentDashboard',
    'ProfileStorage'
]

# Package version
__version__ = '1.0.0'

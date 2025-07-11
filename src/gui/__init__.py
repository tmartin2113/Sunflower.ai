"""
Sunflower AI GUI Package
Family-friendly graphical interfaces for STEM education
"""

from .main_window import MainWindow
from .login_dialog import LoginDialog
from .profile_manager_dialog import ProfileManagerDialog
from .parent_dashboard import ParentDashboard
from .settings_dialog import SettingsDialog

__all__ = [
    'MainWindow',
    'LoginDialog', 
    'ProfileManagerDialog',
    'ParentDashboard',
    'SettingsDialog'
]

# GUI Version
__version__ = '6.2.0'

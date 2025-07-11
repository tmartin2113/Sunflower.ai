#!/usr/bin/env python3
"""
Base platform interface for OS-specific implementations.
Defines the abstract interface that all platform implementations must follow.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class BasePlatform(ABC):
    """
    Abstract base class for platform-specific implementations.
    All platform modules (Windows, macOS, Linux) should inherit from this class
    and implement the required methods.
    """
    
    def __init__(self):
        """Initialize the platform handler"""
        self.platform_name = self.__class__.__name__.replace('Platform', '')
        logger.info(f"Initializing {self.platform_name} platform handler")
    
    # File System Operations
    
    @abstractmethod
    def show_in_file_manager(self, path: str) -> bool:
        """
        Open the system file manager at the specified path.
        
        Args:
            path: Directory or file path to show
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_special_folder(self, folder_id: str) -> Optional[Path]:
        """
        Get path to system special folders.
        
        Args:
            folder_id: Folder identifier (desktop, documents, etc.)
            
        Returns:
            Path to the folder or None if not found
        """
        pass
    
    # Shortcut/Alias Operations
    
    @abstractmethod
    def create_shortcut(self, target: str, location: str, name: str, 
                       description: str = "", icon: str = None,
                       arguments: str = "") -> bool:
        """
        Create a system shortcut/alias.
        
        Args:
            target: Path to the target executable or file
            location: Directory where shortcut will be created
            name: Name of the shortcut
            description: Optional description/tooltip
            icon: Optional path to icon file
            arguments: Optional command line arguments
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def create_desktop_shortcut(self, target: str, name: str, **kwargs) -> bool:
        """
        Create a shortcut on the desktop.
        
        Args:
            target: Path to target executable or file
            name: Shortcut name
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    # Startup/Login Items
    
    @abstractmethod
    def add_to_startup(self, app_name: str, app_path: str, **kwargs) -> bool:
        """
        Add application to system startup.
        
        Args:
            app_name: Name of the application
            app_path: Full path to the executable
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_from_startup(self, app_name: str) -> bool:
        """
        Remove application from system startup.
        
        Args:
            app_name: Name of the application
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    # System Information
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            Dictionary containing system information
        """
        pass
    
    def get_platform_name(self) -> str:
        """
        Get the platform name.
        
        Returns:
            Platform name (Windows, macOS, Linux, etc.)
        """
        return self.platform_name
    
    # Preferences/Settings
    
    @abstractmethod
    def get_preference(self, domain: str, key: str) -> Optional[Any]:
        """
        Get a system preference value.
        
        Args:
            domain: Preference domain/section
            key: Preference key
            
        Returns:
            The preference value or None if not found
        """
        pass
    
    @abstractmethod
    def set_preference(self, domain: str, key: str, value: Any, 
                      pref_type: str = 'string') -> bool:
        """
        Set a system preference value.
        
        Args:
            domain: Preference domain/section
            key: Preference key
            value: Value to set
            pref_type: Type of preference value
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    # Notifications
    
    @abstractmethod
    def show_notification(self, title: str, message: str, **kwargs) -> bool:
        """
        Show a system notification.
        
        Args:
            title: Notification title
            message: Notification message
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    # Drive/Volume Information
    
    @abstractmethod
    def get_volume_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all mounted volumes/drives.
        
        Returns:
            List of volume information dictionaries
        """
        pass
    
    # Optional Methods (with default implementations)
    
    def is_admin(self) -> bool:
        """
        Check if the current process has administrator/root privileges.
        
        Returns:
            True if running with elevated privileges, False otherwise
        """
        logger.warning(f"{self.platform_name} does not implement is_admin check")
        return False
    
    def request_admin_privileges(self, **kwargs) -> bool:
        """
        Request administrator/root privileges.
        
        Args:
            **kwargs: Platform-specific arguments
            
        Returns:
            True if privileges granted, False otherwise
        """
        logger.warning(f"{self.platform_name} does not implement admin privilege request")
        return False
    
    def is_dark_mode(self) -> bool:
        """
        Check if the system is in dark mode.
        
        Returns:
            True if dark mode is enabled, False otherwise
        """
        return False
    
    def cleanup(self):
        """
        Clean up any platform-specific resources.
        Called when the application is shutting down.
        """
        pass
    
    # Utility Methods
    
    def validate_path(self, path: str) -> Optional[Path]:
        """
        Validate and resolve a path.
        
        Args:
            path: Path string to validate
            
        Returns:
            Resolved Path object or None if invalid
        """
        try:
            p = Path(path)
            if p.exists():
                return p.resolve()
            return None
        except Exception as e:
            logger.error(f"Invalid path {path}: {e}")
            return None
    
    def ensure_directory(self, path: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path
            
        Returns:
            True if directory exists or was created, False otherwise
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False


class PlatformFactory:
    """
    Factory class for creating platform-specific implementations.
    """
    
    _platforms = {}
    
    @classmethod
    def register_platform(cls, name: str, platform_class: type):
        """
        Register a platform implementation.
        
        Args:
            name: Platform name (e.g., 'Windows', 'Darwin')
            platform_class: Platform implementation class
        """
        cls._platforms[name] = platform_class
    
    @classmethod
    def create_platform(cls, platform_name: Optional[str] = None) -> BasePlatform:
        """
        Create a platform-specific implementation.
        
        Args:
            platform_name: Platform name (auto-detected if None)
            
        Returns:
            Platform implementation instance
            
        Raises:
            ValueError: If platform is not supported
        """
        if platform_name is None:
            import platform
            platform_name = platform.system()
        
        platform_class = cls._platforms.get(platform_name)
        
        if platform_class is None:
            raise ValueError(f"Unsupported platform: {platform_name}")
        
        return platform_class()
    
    @classmethod
    def get_current_platform(cls) -> BasePlatform:
        """
        Get the platform implementation for the current system.
        
        Returns:
            Platform implementation instance
        """
        return cls.create_platform()


# Auto-register platforms when they're imported
def auto_register_platforms():
    """Automatically register available platform implementations"""
    import platform
    current_system = platform.system()
    
    if current_system == 'Windows':
        try:
            from .windows import WindowsPlatform
            PlatformFactory.register_platform('Windows', WindowsPlatform)
        except ImportError:
            logger.warning("Windows platform module not available")
    
    elif current_system == 'Darwin':
        try:
            from .macos import MacOSPlatform
            PlatformFactory.register_platform('Darwin', MacOSPlatform)
        except ImportError:
            logger.warning("macOS platform module not available")
    
    elif current_system == 'Linux':
        try:
            from .linux import LinuxPlatform
            PlatformFactory.register_platform('Linux', LinuxPlatform)
        except ImportError:
            logger.warning("Linux platform module not available")


# Module initialization
auto_register_platforms()

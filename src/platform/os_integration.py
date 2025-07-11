#!/usr/bin/env python3
"""
OS Integration for Sunflower AI
Provides a unified interface for platform-specific functionality.
Uses the platform-specific implementations from windows.py and macos.py.
"""

import platform
from typing import Optional, Dict, List, Any
from pathlib import Path
import logging

from .base import BasePlatform, PlatformFactory

logger = logging.getLogger(__name__)


class OSIntegration:
    """
    A facade that provides a unified interface for OS-specific tasks,
    delegating the actual work to platform-specific implementations.
    """

    def __init__(self):
        """
        Initialize the integration layer and load the correct
        implementation for the current operating system.
        """
        self.system = platform.system()
        
        try:
            # Use the factory to create the appropriate platform implementation
            self.impl = PlatformFactory.get_current_platform()
            logger.info(f"OS Integration loaded for: {self.system}")
        except ValueError as e:
            logger.error(f"Failed to load platform implementation: {e}")
            # Fallback to a generic implementation
            self.impl = GenericPlatform()
    
    def __getattr__(self, name):
        """
        Delegate any undefined method calls to the platform implementation.
        This allows OSIntegration to act as a transparent proxy.
        """
        return getattr(self.impl, name)
    
    # Core methods with additional error handling
    
    def show_in_file_manager(self, path: str) -> bool:
        """
        Opens the system's file manager to the specified path.

        Args:
            path: The directory or file path to show.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.impl.show_in_file_manager(path)
        except Exception as e:
            logger.error(f"Failed to show in file manager: {e}")
            return False

    def create_desktop_shortcut(self, target_executable: str, name: str, 
                               **kwargs) -> bool:
        """
        Creates a desktop shortcut for the application.

        Args:
            target_executable: The path to the application's launcher.
            name: The desired name for the shortcut.
            **kwargs: Additional platform-specific arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.impl.create_desktop_shortcut(target_executable, name, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create desktop shortcut: {e}")
            return False
    
    def add_to_startup(self, app_name: str, app_path: str, **kwargs) -> bool:
        """
        Add application to system startup.
        
        Args:
            app_name: Name of the application
            app_path: Path to the executable
            **kwargs: Platform-specific arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.impl.add_to_startup(app_name, app_path, **kwargs)
        except Exception as e:
            logger.error(f"Failed to add to startup: {e}")
            return False
    
    def get_special_folder(self, folder_id: str) -> Optional[Path]:
        """
        Get path to system special folders.
        
        Args:
            folder_id: Folder identifier (desktop, documents, etc.)
            
        Returns:
            Path to the folder or None
        """
        try:
            return self.impl.get_special_folder(folder_id)
        except Exception as e:
            logger.error(f"Failed to get special folder: {e}")
            return None
    
    def show_notification(self, title: str, message: str, **kwargs) -> bool:
        """
        Show a system notification.
        
        Args:
            title: Notification title
            message: Notification message
            **kwargs: Platform-specific arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.impl.show_notification(title, message, **kwargs)
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.
        
        Returns:
            Dictionary with system information
        """
        try:
            return self.impl.get_system_info()
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Clean up platform-specific resources"""
        if hasattr(self.impl, 'cleanup'):
            self.impl.cleanup()


class GenericPlatform(BasePlatform):
    """
    Generic fallback implementation for unsupported platforms.
    Provides basic functionality where possible.
    """
    
    def __init__(self):
        super().__init__()
        logger.warning("Using generic platform implementation - some features may not work")
    
    def show_in_file_manager(self, path: str) -> bool:
        """Try to open file manager using xdg-open (Linux) or print path"""
        try:
            import subprocess
            import shutil
            
            if shutil.which('xdg-open'):
                subprocess.run(['xdg-open', path], check=True)
                return True
            else:
                print(f"Please open: {path}")
                return False
        except Exception:
            return False
    
    def create_shortcut(self, target: str, location: str, name: str, 
                       description: str = "", icon: str = None,
                       arguments: str = "") -> bool:
        """Create a basic .desktop file for Linux"""
        try:
            desktop_file = Path(location) / f"{name}.desktop"
            
            content = f"""[Desktop Entry]
Name={name}
Exec={target} {arguments}
Type=Application
Terminal=false
"""
            if description:
                content += f"Comment={description}\n"
            if icon:
                content += f"Icon={icon}\n"
            
            desktop_file.write_text(content)
            desktop_file.chmod(0o755)
            
            return True
        except Exception:
            return False
    
    def create_desktop_shortcut(self, target: str, name: str, **kwargs) -> bool:
        """Create shortcut on desktop"""
        desktop = Path.home() / 'Desktop'
        if not desktop.exists():
            desktop = Path.home()
        
        return self.create_shortcut(target, str(desktop), name, **kwargs)
    
    def add_to_startup(self, app_name: str, app_path: str, **kwargs) -> bool:
        """Add to XDG autostart if available"""
        try:
            autostart = Path.home() / '.config' / 'autostart'
            autostart.mkdir(parents=True, exist_ok=True)
            
            return self.create_shortcut(
                app_path, 
                str(autostart), 
                app_name,
                description=f"Start {app_name} automatically"
            )
        except Exception:
            return False
    
    def remove_from_startup(self, app_name: str) -> bool:
        """Remove from XDG autostart"""
        try:
            autostart_file = Path.home() / '.config' / 'autostart' / f"{app_name}.desktop"
            if autostart_file.exists():
                autostart_file.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_preference(self, domain: str, key: str) -> Optional[Any]:
        """Use a simple JSON file for preferences"""
        try:
            pref_file = Path.home() / '.config' / 'sunflower-ai' / 'preferences.json'
            if pref_file.exists():
                import json
                with open(pref_file) as f:
                    prefs = json.load(f)
                return prefs.get(domain, {}).get(key)
        except Exception:
            return None
    
    def set_preference(self, domain: str, key: str, value: Any, 
                      pref_type: str = 'string') -> bool:
        """Save preference to JSON file"""
        try:
            import json
            pref_dir = Path.home() / '.config' / 'sunflower-ai'
            pref_dir.mkdir(parents=True, exist_ok=True)
            
            pref_file = pref_dir / 'preferences.json'
            
            prefs = {}
            if pref_file.exists():
                with open(pref_file) as f:
                    prefs = json.load(f)
            
            if domain not in prefs:
                prefs[domain] = {}
            
            prefs[domain][key] = value
            
            with open(pref_file, 'w') as f:
                json.dump(prefs, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def show_notification(self, title: str, message: str, **kwargs) -> bool:
        """Try to use notify-send if available"""
        try:
            import subprocess
            import shutil
            
            if shutil.which('notify-send'):
                subprocess.run(['notify-send', title, message], check=True)
                return True
            else:
                print(f"Notification: {title} - {message}")
                return False
        except Exception:
            return False
    
    def get_special_folder(self, folder_id: str) -> Optional[Path]:
        """Get common folder paths"""
        folders = {
            'desktop': Path.home() / 'Desktop',
            'documents': Path.home() / 'Documents',
            'downloads': Path.home() / 'Downloads',
            'home': Path.home(),
            'temp': Path('/tmp'),
        }
        
        folder = folders.get(folder_id.lower())
        if folder and folder.exists():
            return folder
        return None
    
    def get_volume_info(self) -> List[Dict[str, Any]]:
        """Basic volume info using df"""
        volumes = []
        try:
            import subprocess
            result = subprocess.run(
                ['df', '-h'], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 6:
                        volumes.append({
                            'device': parts[0],
                            'size': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'percent': parts[4],
                            'mount': parts[5]
                        })
        except Exception:
            pass
        
        return volumes
    
    def get_system_info(self) -> Dict[str, Any]:
        """Basic system information"""
        import platform
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
        }


# Convenience function for quick access
def get_os_integration() -> OSIntegration:
    """Get or create the global OS integration instance"""
    if not hasattr(get_os_integration, '_instance'):
        get_os_integration._instance = OSIntegration()
    return get_os_integration._instance


# Module-level convenience functions
def show_in_file_manager(path: str) -> bool:
    """Show path in system file manager"""
    return get_os_integration().show_in_file_manager(path)

def create_desktop_shortcut(target: str, name: str, **kwargs) -> bool:
    """Create desktop shortcut"""
    return get_os_integration().create_desktop_shortcut(target, name, **kwargs)

def get_special_folder(folder_id: str) -> Optional[Path]:
    """Get special system folder"""
    return get_os_integration().get_special_folder(folder_id)

def show_notification(title: str, message: str, **kwargs) -> bool:
    """Show system notification"""
    return get_os_integration().show_notification(title, message, **kwargs)

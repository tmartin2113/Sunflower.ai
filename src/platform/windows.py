#!/usr/bin/env python3
"""
Windows-specific implementations for OS integration tasks.
Handles Windows-specific functionality like shortcuts, registry, and system integration.
"""

import os
import sys
import ctypes
import winreg
import subprocess
from pathlib import Path
import win32com.client
import win32api
import win32con
import win32file
import win32security
import pythoncom
from typing import Optional, Dict, List, Tuple, Any
import logging

from .base import BasePlatform

logger = logging.getLogger(__name__)


class WindowsPlatform(BasePlatform):
    """Windows-specific platform implementation"""
    
    def __init__(self):
        """Initialize Windows platform handler"""
        super().__init__()
        self.shell = None
        try:
            pythoncom.CoInitialize()
            self.shell = win32com.client.Dispatch("WScript.Shell")
        except Exception as e:
            logger.error(f"Failed to initialize Windows COM: {e}")
    
    def show_in_file_manager(self, path: str) -> bool:
        """
        Open Windows Explorer at the specified path.
        
        Args:
            path: Directory or file path to show
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(path).resolve()
            
            if path.is_file():
                # Select the file in Explorer
                subprocess.run(['explorer', '/select,', str(path)], check=True)
            else:
                # Open the directory
                os.startfile(str(path))
            
            logger.info(f"Opened Explorer at: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open Explorer: {e}")
            return False
    
    def create_shortcut(self, target: str, location: str, name: str, 
                       description: str = "", icon: str = None,
                       arguments: str = "") -> bool:
        """
        Create a Windows shortcut (.lnk file).
        
        Args:
            target: Path to the target executable
            location: Directory where shortcut will be created
            name: Name of the shortcut (without .lnk)
            description: Shortcut description/tooltip
            icon: Path to icon file (optional)
            arguments: Command line arguments (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.shell:
                raise RuntimeError("Windows COM not initialized")
            
            shortcut_path = Path(location) / f"{name}.lnk"
            shortcut = self.shell.CreateShortCut(str(shortcut_path))
            
            shortcut.TargetPath = str(target)
            shortcut.WorkingDirectory = str(Path(target).parent)
            shortcut.Arguments = arguments
            
            if description:
                shortcut.Description = description
            
            if icon:
                shortcut.IconLocation = str(icon)
            else:
                shortcut.IconLocation = str(target)
            
            shortcut.save()
            
            logger.info(f"Created shortcut: {shortcut_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create shortcut: {e}")
            return False
    
    def create_desktop_shortcut(self, target: str, name: str, **kwargs) -> bool:
        """
        Create a shortcut on the Windows desktop.
        
        Args:
            target: Path to target executable
            name: Shortcut name
            **kwargs: Additional arguments for create_shortcut
            
        Returns:
            True if successful, False otherwise
        """
        try:
            desktop = Path(os.environ['USERPROFILE']) / 'Desktop'
            return self.create_shortcut(target, str(desktop), name, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create desktop shortcut: {e}")
            return False
    
    def add_to_startup(self, app_name: str, app_path: str) -> bool:
        """
        Add application to Windows startup.
        
        Args:
            app_name: Name of the application
            app_path: Full path to the executable
            
        Returns:
            True if successful, False otherwise
        """
        try:
            startup_folder = Path(os.environ['APPDATA']) / \
                           'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
            
            return self.create_shortcut(
                app_path, 
                str(startup_folder), 
                app_name,
                description=f"Start {app_name} with Windows"
            )
            
        except Exception as e:
            logger.error(f"Failed to add to startup: {e}")
            return False
    
    def remove_from_startup(self, app_name: str) -> bool:
        """
        Remove application from Windows startup.
        
        Args:
            app_name: Name of the application
            
        Returns:
            True if successful, False otherwise
        """
        try:
            startup_folder = Path(os.environ['APPDATA']) / \
                           'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
            shortcut_path = startup_folder / f"{app_name}.lnk"
            
            if shortcut_path.exists():
                shortcut_path.unlink()
                logger.info(f"Removed from startup: {app_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove from startup: {e}")
            return False
    
    def set_registry_value(self, key_path: str, value_name: str, 
                          value_data: any, value_type: int = winreg.REG_SZ) -> bool:
        """
        Set a Windows registry value.
        
        Args:
            key_path: Registry key path (e.g., r"SOFTWARE\SunflowerAI")
            value_name: Name of the value
            value_data: Data to store
            value_type: Registry value type (REG_SZ, REG_DWORD, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open or create the key
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_WRITE
            )
            
            # Set the value
            winreg.SetValueEx(key, value_name, 0, value_type, value_data)
            winreg.CloseKey(key)
            
            logger.info(f"Set registry value: {key_path}\\{value_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set registry value: {e}")
            return False
    
    def get_registry_value(self, key_path: str, value_name: str) -> Optional[any]:
        """
        Get a Windows registry value.
        
        Args:
            key_path: Registry key path
            value_name: Name of the value
            
        Returns:
            The value data or None if not found
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_READ
            )
            
            value, _ = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            
            return value
            
        except Exception:
            return None
    
    def get_special_folder(self, folder_id: str) -> Optional[Path]:
        """
        Get path to Windows special folders.
        
        Args:
            folder_id: Folder identifier (desktop, documents, appdata, etc.)
            
        Returns:
            Path to the folder or None
        """
        folders = {
            'desktop': Path(os.environ['USERPROFILE']) / 'Desktop',
            'documents': Path(os.environ['USERPROFILE']) / 'Documents',
            'downloads': Path(os.environ['USERPROFILE']) / 'Downloads',
            'appdata': Path(os.environ['APPDATA']),
            'localappdata': Path(os.environ['LOCALAPPDATA']),
            'programfiles': Path(os.environ['PROGRAMFILES']),
            'temp': Path(os.environ['TEMP']),
        }
        
        return folders.get(folder_id.lower())
    
    def get_drive_info(self) -> List[Dict]:
        """
        Get information about all drives.
        
        Returns:
            List of drive information dictionaries
        """
        drives = []
        
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    drive_type = win32file.GetDriveType(drive)
                    
                    # Get volume information
                    volume_info = win32api.GetVolumeInformation(drive)
                    
                    # Get space information
                    total, free = win32api.GetDiskFreeSpaceEx(drive)[:2]
                    
                    drives.append({
                        'letter': letter,
                        'path': drive,
                        'type': self._get_drive_type_name(drive_type),
                        'label': volume_info[0] or f"Drive {letter}",
                        'filesystem': volume_info[4],
                        'total_space': total,
                        'free_space': free,
                        'serial': volume_info[1]
                    })
                    
                except Exception as e:
                    logger.debug(f"Could not get info for drive {letter}: {e}")
        
        return drives
    
    def _get_drive_type_name(self, drive_type: int) -> str:
        """Convert Windows drive type constant to readable name"""
        types = {
            win32file.DRIVE_UNKNOWN: "Unknown",
            win32file.DRIVE_NO_ROOT_DIR: "Invalid",
            win32file.DRIVE_REMOVABLE: "Removable",
            win32file.DRIVE_FIXED: "Fixed",
            win32file.DRIVE_REMOTE: "Network",
            win32file.DRIVE_CDROM: "CD-ROM",
            win32file.DRIVE_RAMDISK: "RAM Disk"
        }
        return types.get(drive_type, "Unknown")
    
    def is_admin(self) -> bool:
        """
        Check if the current process has administrator privileges.
        
        Returns:
            True if running as admin, False otherwise
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    
    def request_admin_restart(self, exe_path: str = None) -> bool:
        """
        Restart the application with administrator privileges.
        
        Args:
            exe_path: Path to executable (defaults to sys.executable)
            
        Returns:
            True if restart initiated, False if failed or cancelled
        """
        try:
            if exe_path is None:
                exe_path = sys.executable
            
            # Get command line arguments
            args = ' '.join(sys.argv[1:])
            
            # Request elevation
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                exe_path,
                args,
                None,
                1  # SW_NORMAL
            )
            
            if ret > 32:
                # Success - exit current process
                sys.exit(0)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to request admin restart: {e}")
            return False
    
    def show_notification(self, title: str, message: str, 
                         duration: int = 5000) -> bool:
        """
        Show a Windows toast notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Duration in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use Windows 10 toast notifications if available
            from win10toast import ToastNotifier
            
            toaster = ToastNotifier()
            toaster.show_toast(
                title,
                message,
                duration=duration // 1000,
                threaded=True
            )
            return True
            
        except ImportError:
            # Fallback to balloon tip
            try:
                ctypes.windll.user32.MessageBoxW(
                    0, 
                    message, 
                    title,
                    0x40  # MB_ICONINFORMATION
                )
                return True
            except Exception:
                return False
    
    def cleanup(self):
        """Clean up Windows COM objects"""
        if self.shell:
            pythoncom.CoUninitialize()


# Module-level instance
_platform = WindowsPlatform()

# Export functions for backward compatibility
def show_in_file_manager(path: str) -> bool:
    return _platform.show_in_file_manager(path)

def create_desktop_shortcut(target: str, name: str, **kwargs) -> bool:
    return _platform.create_desktop_shortcut(target, name, **kwargs)

def add_to_startup(app_name: str, app_path: str) -> bool:
    return _platform.add_to_startup(app_name, app_path)

def is_admin() -> bool:
    return _platform.is_admin()

def get_special_folder(folder_id: str) -> Optional[Path]:
    return _platform.get_special_folder(folder_id)

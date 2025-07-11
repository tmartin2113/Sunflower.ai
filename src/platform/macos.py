#!/usr/bin/env python3
"""
macOS-specific implementations for OS integration tasks.
Handles macOS-specific functionality like aliases, plists, and system integration.
"""

import os
import sys
import subprocess
import plistlib
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import logging
import tempfile
import json

from .base import BasePlatform

logger = logging.getLogger(__name__)


class MacOSPlatform(BasePlatform):
    """macOS-specific platform implementation"""
    
    def __init__(self):
        """Initialize macOS platform handler"""
        super().__init__()
        self.osascript_available = shutil.which('osascript') is not None
        if not self.osascript_available:
            logger.warning("osascript not available - some features may not work")
    
    def show_in_file_manager(self, path: str) -> bool:
        """
        Open Finder at the specified path.
        
        Args:
            path: Directory or file path to show
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(path).resolve()
            
            if path.is_file():
                # Reveal the file in Finder
                subprocess.run(['open', '-R', str(path)], check=True)
            else:
                # Open the directory
                subprocess.run(['open', str(path)], check=True)
            
            logger.info(f"Opened Finder at: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open Finder: {e}")
            return False
    
    def create_shortcut(self, target: str, location: str, name: str, 
                       description: str = "", icon: str = None,
                       arguments: str = "") -> bool:
        """
        Create a macOS alias (similar to shortcut).
        
        Args:
            target: Path to the target file/folder
            location: Directory where alias will be created
            name: Name of the alias
            description: Not used on macOS (for interface compatibility)
            icon: Path to icon (used if creating app bundle)
            arguments: Not used for aliases (for interface compatibility)
            
        Returns:
            True if successful, False otherwise
        """
        # For Python scripts, we might want to create an app bundle
        if str(target).endswith('.py') and (icon or arguments):
            app_bundle = self.create_app_bundle(target, name, icon_path=icon)
            if app_bundle:
                dest = Path(location) / app_bundle.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(app_bundle), str(location))
                return True
        
        # Otherwise create a regular alias
        return self.create_alias(target, location, name)
    
    def create_alias(self, target: str, location: str, name: str) -> bool:
        """
        Create a macOS alias (similar to shortcut).
        
        Args:
            target: Path to the target file/folder
            location: Directory where alias will be created
            name: Name of the alias
            
        Returns:
            True if successful, False otherwise
        """
        try:
            target_path = Path(target).resolve()
            alias_path = Path(location) / name
            
            # Use osascript to create alias
            script = f'''
            tell application "Finder"
                make alias file to POSIX file "{target_path}" at POSIX file "{location}"
                set name of result to "{name}"
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Created alias: {alias_path}")
                return True
            else:
                logger.error(f"Failed to create alias: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create alias: {e}")
            return False
    
    def create_app_bundle(self, script_path: str, app_name: str, 
                         icon_path: Optional[str] = None,
                         version: str = "1.0") -> Optional[Path]:
        """
        Create a macOS .app bundle from a Python script.
        
        Args:
            script_path: Path to the Python script
            app_name: Name of the application
            icon_path: Path to .icns icon file (optional)
            version: Application version
            
        Returns:
            Path to created .app bundle or None if failed
        """
        try:
            # Create app bundle structure
            app_dir = Path(f"{app_name}.app")
            contents_dir = app_dir / "Contents"
            macos_dir = contents_dir / "MacOS"
            resources_dir = contents_dir / "Resources"
            
            # Create directories
            macos_dir.mkdir(parents=True, exist_ok=True)
            resources_dir.mkdir(exist_ok=True)
            
            # Create launcher script
            launcher_path = macos_dir / app_name
            launcher_content = f'''#!/bin/bash
cd "$(dirname "$0")"
exec /usr/bin/python3 "{script_path}" "$@"
'''
            
            launcher_path.write_text(launcher_content)
            launcher_path.chmod(0o755)
            
            # Create Info.plist
            info_plist = {
                'CFBundleName': app_name,
                'CFBundleDisplayName': app_name,
                'CFBundleIdentifier': f'com.sunflowerai.{app_name.lower()}',
                'CFBundleVersion': version,
                'CFBundleShortVersionString': version,
                'CFBundleExecutable': app_name,
                'CFBundlePackageType': 'APPL',
                'CFBundleSignature': '????',
                'LSMinimumSystemVersion': '10.14.0',
                'NSHighResolutionCapable': True,
                'NSSupportsAutomaticGraphicsSwitching': True,
            }
            
            if icon_path and Path(icon_path).exists():
                # Copy icon
                icon_dest = resources_dir / "AppIcon.icns"
                shutil.copy2(icon_path, icon_dest)
                info_plist['CFBundleIconFile'] = 'AppIcon'
            
            # Write Info.plist
            plist_path = contents_dir / "Info.plist"
            with open(plist_path, 'wb') as f:
                plistlib.dump(info_plist, f)
            
            logger.info(f"Created app bundle: {app_dir}")
            return app_dir
            
        except Exception as e:
            logger.error(f"Failed to create app bundle: {e}")
            return None
    
    def create_desktop_shortcut(self, target: str, name: str, 
                               icon: Optional[str] = None) -> bool:
        """
        Create an alias on the macOS desktop.
        
        Args:
            target: Path to target file/app
            name: Alias name
            icon: Path to icon (used if creating app bundle)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            desktop = Path.home() / 'Desktop'
            
            # If target is a Python script, create app bundle first
            if target.endswith('.py'):
                app_bundle = self.create_app_bundle(
                    target, 
                    name,
                    icon_path=icon
                )
                if app_bundle:
                    # Move to desktop
                    dest = desktop / app_bundle.name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.move(str(app_bundle), str(desktop))
                    return True
            else:
                # Create alias for existing app/file
                return self.create_alias(target, str(desktop), name)
                
        except Exception as e:
            logger.error(f"Failed to create desktop shortcut: {e}")
            return False
    
    def add_to_startup(self, app_name: str, app_path: str, **kwargs) -> bool:
        """
        Add application to macOS login items (startup).
        
        Args:
            app_name: Name of the application
            app_path: Path to the application
            **kwargs: Additional arguments (e.g., hidden=True)
            
        Returns:
            True if successful, False otherwise
        """
        hidden = kwargs.get('hidden', False)
        return self.add_to_login_items(app_path, hidden)
    
    def remove_from_startup(self, app_name: str) -> bool:
        """
        Remove application from macOS login items.
        
        Args:
            app_name: Name of the application
            
        Returns:
            True if successful, False otherwise
        """
        return self.remove_from_login_items(app_name)
    
    def add_to_login_items(self, app_path: str, hidden: bool = False) -> bool:
        """
        Add application to macOS login items (startup).
        
        Args:
            app_path: Path to the application
            hidden: Whether to hide the app on startup
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use osascript to add login item
            script = f'''
            tell application "System Events"
                make login item at end with properties {{path:"{app_path}", hidden:{str(hidden).lower()}}}
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Added to login items: {app_path}")
                return True
            else:
                logger.error(f"Failed to add login item: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to add to login items: {e}")
            return False
    
    def remove_from_login_items(self, app_name: str) -> bool:
        """
        Remove application from macOS login items.
        
        Args:
            app_name: Name of the application
            
        Returns:
            True if successful, False otherwise
        """
        try:
            script = f'''
            tell application "System Events"
                delete login item "{app_name}"
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Removed from login items: {app_name}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove from login items: {e}")
            return False
    
    def get_preference(self, domain: str, key: str) -> Optional[any]:
        """
        Get a macOS preference value using defaults.
        
        Args:
            domain: Preference domain (e.g., 'com.sunflowerai.app')
            key: Preference key
            
        Returns:
            The preference value or None
        """
        try:
            result = subprocess.run(
                ['defaults', 'read', domain, key],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                value = result.stdout.strip()
                
                # Try to parse as JSON for complex types
                try:
                    return json.loads(value)
                except:
                    return value
                    
        except Exception:
            pass
        
        return None
    
    def set_preference(self, domain: str, key: str, value: any, 
                      pref_type: str = 'string') -> bool:
        """
        Set a macOS preference value using defaults.
        
        Args:
            domain: Preference domain
            key: Preference key
            value: Value to set
            pref_type: Type (string, int, float, bool, array, dict)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert Python types to defaults types
            type_map = {
                'string': '-string',
                'int': '-int',
                'float': '-float',
                'bool': '-bool',
                'array': '-array',
                'dict': '-dict'
            }
            
            defaults_type = type_map.get(pref_type, '-string')
            
            # Special handling for bool
            if pref_type == 'bool':
                value = 'YES' if value else 'NO'
            
            cmd = ['defaults', 'write', domain, key, defaults_type]
            
            # Add value(s)
            if isinstance(value, (list, dict)):
                cmd.extend(str(v) for v in value)
            else:
                cmd.append(str(value))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Set preference: {domain}.{key}")
                return True
            else:
                logger.error(f"Failed to set preference: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set preference: {e}")
            return False
    
    def get_special_folder(self, folder_id: str) -> Optional[Path]:
        """
        Get path to macOS special folders.
        
        Args:
            folder_id: Folder identifier
            
        Returns:
            Path to the folder or None
        """
        folders = {
            'desktop': Path.home() / 'Desktop',
            'documents': Path.home() / 'Documents',
            'downloads': Path.home() / 'Downloads',
            'applications': Path('/Applications'),
            'user_applications': Path.home() / 'Applications',
            'library': Path.home() / 'Library',
            'preferences': Path.home() / 'Library' / 'Preferences',
            'cache': Path.home() / 'Library' / 'Caches',
            'logs': Path.home() / 'Library' / 'Logs',
            'temp': Path(tempfile.gettempdir()),
        }
        
        return folders.get(folder_id.lower())
    
    def get_volume_info(self) -> List[Dict]:
        """
        Get information about all mounted volumes.
        
        Returns:
            List of volume information dictionaries
        """
        volumes = []
        
        try:
            # Use diskutil to get volume information
            result = subprocess.run(
                ['diskutil', 'list', '-plist'],
                capture_output=True,
                text=False
            )
            
            if result.returncode == 0:
                plist_data = plistlib.loads(result.stdout)
                
                # Get all volumes
                for disk in plist_data.get('AllDisksAndPartitions', []):
                    self._parse_disk_info(disk, volumes)
                    
        except Exception as e:
            logger.error(f"Failed to get volume info: {e}")
        
        return volumes
    
    def _parse_disk_info(self, disk: Dict, volumes: List[Dict]):
        """Parse disk information from diskutil"""
        if 'MountPoint' in disk:
            volumes.append({
                'name': disk.get('VolumeName', 'Unnamed'),
                'path': disk.get('MountPoint'),
                'device': disk.get('DeviceIdentifier'),
                'size': disk.get('Size', 0),
                'free_space': disk.get('FreeSpace', 0),
                'filesystem': disk.get('FilesystemType', 'Unknown'),
                'removable': disk.get('Removable', False),
                'writable': disk.get('Writable', True),
            })
        
        # Check partitions
        for partition in disk.get('Partitions', []):
            self._parse_disk_info(partition, volumes)
    
    def show_notification(self, title: str, message: str, 
                         subtitle: Optional[str] = None,
                         sound: Optional[str] = None) -> bool:
        """
        Show a macOS notification.
        
        Args:
            title: Notification title
            message: Notification message
            subtitle: Optional subtitle
            sound: Optional sound name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            script_parts = [
                f'display notification "{message}"',
                f'with title "{title}"'
            ]
            
            if subtitle:
                script_parts.append(f'subtitle "{subtitle}"')
            
            if sound:
                script_parts.append(f'sound name "{sound}"')
            
            script = ' '.join(script_parts)
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
            return False
    
    def request_accessibility_permissions(self, app_name: str) -> bool:
        """
        Request accessibility permissions for the app.
        
        Args:
            app_name: Name of the application
            
        Returns:
            True if permissions granted, False otherwise
        """
        try:
            # Open accessibility preferences
            subprocess.run([
                'osascript', '-e',
                'tell application "System Preferences" to reveal anchor "Privacy_Accessibility" of pane "com.apple.preference.security"'
            ])
            
            subprocess.run([
                'osascript', '-e',
                'tell application "System Preferences" to activate'
            ])
            
            logger.info("Opened accessibility preferences")
            return True
            
        except Exception as e:
            logger.error(f"Failed to request accessibility permissions: {e}")
            return False
    
    def is_dark_mode(self) -> bool:
        """
        Check if macOS is in dark mode.
        
        Returns:
            True if dark mode is enabled, False otherwise
        """
        try:
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0 and 'Dark' in result.stdout
            
        except Exception:
            return False
    
    def get_system_info(self) -> Dict:
        """
        Get macOS system information.
        
        Returns:
            Dictionary with system information
        """
        info = {}
        
        try:
            # Get macOS version
            result = subprocess.run(
                ['sw_vers'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
            
            # Get hardware info
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType', '-json'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                hardware = data['SPHardwareDataType'][0]
                info.update({
                    'model': hardware.get('machine_model', 'Unknown'),
                    'cpu': hardware.get('cpu_type', 'Unknown'),
                    'memory': hardware.get('physical_memory', 'Unknown'),
                    'serial': hardware.get('serial_number', 'Unknown'),
                })
                
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
        
        return info


# Module-level instance
_platform = MacOSPlatform()

# Export functions for backward compatibility
def show_in_file_manager(path: str) -> bool:
    return _platform.show_in_file_manager(path)

def create_desktop_shortcut(target: str, name: str, **kwargs) -> bool:
    return _platform.create_desktop_shortcut(target, name, **kwargs)

def add_to_login_items(app_path: str, hidden: bool = False) -> bool:
    return _platform.add_to_login_items(app_path, hidden)

def show_notification(title: str, message: str, **kwargs) -> bool:
    return _platform.show_notification(title, message, **kwargs)

def get_special_folder(folder_id: str) -> Optional[Path]:
    return _platform.get_special_folder(folder_id)

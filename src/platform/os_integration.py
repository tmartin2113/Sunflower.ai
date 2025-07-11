#!/usr/bin/env python3
"""
OS Integration for Sunflower AI
Provides a common interface for platform-specific functionality.
"""

import platform
from typing import Optional

# --- Platform-specific implementations ---
# These are placeholder classes. In a real application, they would
# contain the logic for each OS.

class WindowsIntegration:
    """Windows-specific OS integration."""
    def show_in_file_manager(self, path: str):
        print(f"Windows: Opening explorer at {path}")
        # import os
        # os.startfile(path)

    def create_shortcut(self, target: str, location: str, name: str):
        print(f"Windows: Creating shortcut for {target} at {location}/{name}.lnk")

class MacOSIntegration:
    """macOS-specific OS integration."""
    def show_in_file_manager(self, path: str):
        print(f"macOS: Opening Finder at {path}")
        # import subprocess
        # subprocess.run(["open", path])

    def create_shortcut(self, target: str, location: str, name: str):
        print(f"macOS: Creating alias for {target} at {location}/{name}.alias")

class LinuxIntegration:
    """Linux-specific OS integration."""
    def show_in_file_manager(self, path: str):
        print(f"Linux: Opening file manager at {path}")
        # import subprocess
        # subprocess.run(["xdg-open", path])

    def create_shortcut(self, target: str, location: str, name: str):
        print(f"Linux: Creating .desktop file for {target} at {location}/{name}.desktop")


# --- Facade Class ---

class OSIntegration:
    """
    A facade that provides a unified interface for OS-specific tasks,
    delegating the actual work to a platform-specific implementation.
    """

    def __init__(self):
        """
        Initialize the integration layer and load the correct
        implementation for the current operating system.
        """
        system = platform.system()
        if system == "Windows":
            self.impl = WindowsIntegration()
        elif system == "Darwin":
            self.impl = MacOSIntegration()
        else:
            # Default to Linux/generic implementation
            self.impl = LinuxIntegration()
            
        print(f"OS Integration loaded for: {system}")

    def show_in_file_manager(self, path: str):
        """
        Opens the system's file manager to the specified path.

        Args:
            path: The directory or file path to show.
        """
        self.impl.show_in_file_manager(path)

    def create_desktop_shortcut(self, target_executable: str, name: str):
        """
        Creates a desktop shortcut for the application.

        Args:
            target_executable: The path to the application's launcher.
            name: The desired name for the shortcut.
        """
        import os
        desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop') \
            if platform.system() == "Windows" else os.path.join(os.path.expanduser('~'), 'Desktop')
        
        self.impl.create_shortcut(target_executable, desktop_path, name)

if __name__ == '__main__':
    print("--- Testing OS Integration ---")
    
    # This will automatically pick the right implementation
    os_integrator = OSIntegration()

    # Test showing a path
    # In a real run, this would be a valid path from the application
    test_path = "." 
    print(f"\nAttempting to show path: {test_path}")
    os_integrator.show_in_file_manager(test_path)
    
    # Test creating a shortcut
    test_exe = "C:\\path\\to\\SunflowerAI.exe" if platform.system() == "Windows" else "/Applications/SunflowerAI.app"
    print(f"\nAttempting to create shortcut for: {test_exe}")
    os_integrator.create_desktop_shortcut(test_exe, "Sunflower AI")

    print("\n--- Test Complete ---")

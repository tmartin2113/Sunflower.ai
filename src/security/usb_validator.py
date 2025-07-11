#!/usr/bin/env python3
"""
USB Validator for Sunflower AI
Verifies the integrity and writability of the user data partition.
"""

import os
from pathlib import Path
from typing import List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class USBValidator:
    """
    Validates the 'SunflowerData' partition to ensure it is present,
    writable, and has the correct directory structure.
    """

    def __init__(self, usb_path: Path):
        """
        Initialize the validator.

        Args:
            usb_path: The path to the mounted USB drive (data partition).
        """
        self.usb_path = usb_path
        self.required_dirs = [
            "profiles",
            "logs",
            "conversations",
            "cache"
        ]
        self.errors: List[str] = []

    def validate(self) -> bool:
        """
        Runs all validation checks on the USB partition.

        Returns:
            True if all checks pass, False otherwise.
        """
        self.errors.clear()

        if not self.usb_path or not self.usb_path.exists():
            self.errors.append("USB data path does not exist.")
            return False

        self._check_writable()
        self._check_directory_structure()

        return not self.errors

    def _check_writable(self):
        """Verify that the partition is mounted as writable."""
        if not os.access(self.usb_path, os.W_OK):
            self.errors.append(f"USB path '{self.usb_path}' is not writable.")
            return
            
        # Also check with psutil if available for more robust check
        if PSUTIL_AVAILABLE:
            is_rw = False
            for part in psutil.disk_partitions(all=True):
                if self.usb_path.as_posix().startswith(part.mountpoint):
                    if 'ro' not in part.opts.lower():
                        is_rw = True
                        break
            if not is_rw:
                self.errors.append(f"Partition at '{self.usb_path}' is not mounted as read-write.")

    def _check_directory_structure(self):
        """Verify that the essential directories for storing data exist."""
        for dir_name in self.required_dirs:
            dir_path = self.usb_path / dir_name
            if not dir_path.exists() or not dir_path.is_dir():
                self.errors.append(f"Required directory not found or is not a directory: {dir_name}")

    def get_errors(self) -> List[str]:
        """Returns a list of all validation errors found."""
        return self.errors

if __name__ == '__main__':
    # --- Example Usage ---
    # This requires creating a dummy setup.
    dummy_usb_path = Path("./dummy_usb")
    dummy_usb_path.mkdir(exist_ok=True)

    print("--- Running Validation Test (Initial) ---")
    validator = USBValidator(dummy_usb_path)
    if not validator.validate():
        print("Validation correctly failed (missing directories).")
        print("Errors:")
        for error in validator.get_errors():
            print(f"  - {error}")
    
    # Create the required directories
    for dir_name in validator.required_dirs:
        (dummy_usb_path / dir_name).mkdir()
        
    print("\n--- Running Validation Test (After creating dirs) ---")
    validator2 = USBValidator(dummy_usb_path)
    if validator2.validate():
        print("Validation successful!")
    else:
        print("Validation failed:")
        for error in validator2.get_errors():
            print(f"  - {error}")
            
    # Cleanup
    import shutil
    shutil.rmtree(dummy_usb_path)

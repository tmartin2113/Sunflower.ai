#!/usr/bin/env python3
"""
High-level Integrity Checker for Sunflower AI
Orchestrates multiple validation checks for the entire application environment.
"""

from pathlib import Path
from typing import List, Dict

from .cdrom_validator import CDROMValidator
from .usb_validator import USBValidator


class IntegrityChecker:
    """
    A facade that runs all critical validation checks to ensure the
    application environment is secure and correctly set up.
    """

    def __init__(self, cdrom_path: Path, usb_path: Path, file_manifest: Dict[str, str]):
        """
        Initialize the integrity checker.

        Args:
            cdrom_path: The path to the 'SunflowerAI' (CD-ROM) partition.
            usb_path: The path to the 'SunflowerData' (USB) partition.
            file_manifest: A dictionary of filenames and their expected hashes.
        """
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        self.file_manifest = file_manifest
        self.errors: List[str] = []

    def run_all_checks(self) -> bool:
        """
        Executes all registered validation routines.

        Returns:
            True if the system is valid, False otherwise.
        """
        self.errors.clear()

        # --- CD-ROM Validation ---
        cd_validator = CDROMValidator(self.cdrom_path, self.file_manifest)
        if not cd_validator.validate():
            self.errors.extend(cd_validator.get_errors())

        # --- USB Validation ---
        usb_validator = USBValidator(self.usb_path)
        if not usb_validator.validate():
            self.errors.extend(usb_validator.get_errors())
            
        return not self.errors

    def get_errors(self) -> List[str]:
        """Returns a consolidated list of all errors found during checks."""
        return self.errors

if __name__ == '__main__':
    # --- Example Usage ---
    # This requires creating a dummy setup for both CD-ROM and USB.
    print("--- Setting up dummy environment ---")
    dummy_cd_path = Path("./dummy_cdrom")
    dummy_usb_path = Path("./dummy_usb")
    dummy_cd_path.mkdir(exist_ok=True)
    dummy_usb_path.mkdir(exist_ok=True)
    
    # Setup CD-ROM file and manifest
    (dummy_cd_path / "app").mkdir(exist_ok=True)
    dummy_file_path = dummy_cd_path / "app" / "main.exe"
    with open(dummy_file_path, "w") as f: f.write("app code")
    manifest = {"app/main.exe": CDROMValidator._hash_file(dummy_file_path)}
    
    # Setup USB directories
    for dir_name in ["profiles", "logs", "conversations", "cache"]:
        (dummy_usb_path / dir_name).mkdir(exist_ok=True)

    print("--- Running Integrity Check (Should Pass) ---")
    checker = IntegrityChecker(dummy_cd_path, dummy_usb_path, manifest)
    if checker.run_all_checks():
        print("SUCCESS: All integrity checks passed.")
    else:
        print("FAILURE: Integrity checks failed.")
        for error in checker.get_errors():
            print(f"  - {error}")
            
    # --- Test a failure case (e.g., tampered file) ---
    print("\n--- Running Integrity Check (Should Fail) ---")
    with open(dummy_file_path, "w") as f: f.write("tampered code")
    checker_fail = IntegrityChecker(dummy_cd_path, dummy_usb_path, manifest)
    if not checker_fail.run_all_checks():
        print("SUCCESS: Correctly detected tampered file.")
        print("Errors found:")
        for error in checker_fail.get_errors():
            print(f"  - {error}")

    # Cleanup
    import shutil
    shutil.rmtree(dummy_cd_path)
    shutil.rmtree(dummy_usb_path)

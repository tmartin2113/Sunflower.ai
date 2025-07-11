#!/usr/bin/env python3
"""
CD-ROM Validator for Sunflower AI
Verifies the integrity and read-only status of the application partition.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Dict, List

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class CDROMValidator:
    """
    Validates the 'SunflowerAI' partition to ensure it is authentic and
    has not been tampered with.
    """

    def __init__(self, cdrom_path: Path, manifest: Dict[str, str]):
        """
        Initialize the validator.

        Args:
            cdrom_path: The path to the mounted CD-ROM (app partition).
            manifest: A dictionary mapping relative file paths to their
                      expected SHA-256 hashes.
        """
        self.cdrom_path = cdrom_path
        self.manifest = manifest
        self.errors: List[str] = []

    def validate(self) -> bool:
        """
        Runs all validation checks on the CD-ROM partition.

        Returns:
            True if all checks pass, False otherwise.
        """
        self.errors.clear()

        if not self.cdrom_path or not self.cdrom_path.exists():
            self.errors.append("CD-ROM path does not exist.")
            return False

        self._check_read_only()
        self._check_file_hashes()

        return not self.errors

    def _check_read_only(self):
        """Verify that the partition is mounted as read-only."""
        if not PSUTIL_AVAILABLE:
            print("Warning: psutil not found, cannot verify read-only status.")
            return

        is_ro = False
        for part in psutil.disk_partitions(all=True):
            # Find the partition corresponding to our path
            if self.cdrom_path.as_posix().startswith(part.mountpoint):
                if 'ro' in part.opts.lower():
                    is_ro = True
                    break
        
        if not is_ro:
            self.errors.append("CD-ROM partition is not mounted as read-only.")

    def _check_file_hashes(self):
        """Verify the integrity of critical files using a hash manifest."""
        if not self.manifest:
            self.errors.append("File hash manifest is empty or not provided.")
            return

        for relative_path, expected_hash in self.manifest.items():
            file_path = self.cdrom_path / relative_path
            
            if not file_path.exists():
                self.errors.append(f"File not found for hashing: {relative_path}")
                continue

            actual_hash = self._hash_file(file_path)
            if actual_hash != expected_hash:
                self.errors.append(f"Hash mismatch for {relative_path}. File may be corrupt or tampered with.")

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        """
        Calculates the SHA-256 hash of a file.

        Args:
            file_path: The path to the file to hash.

        Returns:
            The hex digest of the hash.
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read and update hash in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError as e:
            return f"Error reading file: {e}"

    def get_errors(self) -> List[str]:
        """Returns a list of all validation errors found."""
        return self.errors

if __name__ == '__main__':
    # --- Example Usage ---
    # This requires creating a dummy setup.
    # 1. Create a dummy directory to act as the "CD-ROM"
    dummy_cd_path = Path("./dummy_cdrom")
    dummy_cd_path.mkdir(exist_ok=True)

    # 2. Create a dummy file to be hashed
    dummy_file_path = dummy_cd_path / "app" / "main.exe"
    (dummy_cd_path / "app").mkdir(exist_ok=True)
    with open(dummy_file_path, "w") as f:
        f.write("This is the main application file.")

    # 3. Calculate its hash to create the manifest
    expected_hash = CDROMValidator._hash_file(dummy_file_path)
    manifest = {
        "app/main.exe": expected_hash
    }

    print("--- Running Validation Test ---")
    validator = CDROMValidator(dummy_cd_path, manifest)
    
    # We can't easily test the read-only check without mounting a real image,
    # so we focus on the hashing part.
    if validator.validate():
        print("Validation successful (hash check passed).")
    else:
        print("Validation failed:")
        for error in validator.get_errors():
            print(f"  - {error}")
            
    # Test with a bad hash
    print("\n--- Testing with a bad hash ---")
    bad_manifest = {"app/main.exe": "thisisabadhash"}
    bad_validator = CDROMValidator(dummy_cd_path, bad_manifest)
    if not bad_validator.validate():
        print("Validation correctly failed for bad hash.")
        print(f"Errors: {bad_validator.get_errors()}")

    # Cleanup
    import shutil
    shutil.rmtree(dummy_cd_path)

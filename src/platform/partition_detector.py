#!/usr/bin/env python3
"""
Partition Detector for Sunflower AI
Locates the special 'SunflowerAI' (CD-ROM) and 'SunflowerData' (USB) partitions.
"""

import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class PartitionDetector:
    """
    Scans the system for the required Sunflower AI partitions.
    - 'SunflowerAI': The read-only application/model partition (CD-ROM).
    - 'SunflowerData': The writable user data partition (USB).
    """

    def __init__(self):
        """Initialize the partition detector."""
        self.cdrom_path: Optional[Path] = None
        self.usb_path: Optional[Path] = None
        self.partitions_found = False
        self._find_partitions()

    def _find_partitions(self):
        """
        Main method to find the required partitions.
        Uses psutil for reliable, cross-platform partition discovery.
        """
        if not PSUTIL_AVAILABLE:
            # As a last resort, scan common drive letters/mount points
            self._scan_fallback_paths()
            return

        partitions = psutil.disk_partitions()
        for p in partitions:
            mountpoint = Path(p.mountpoint)
            try:
                # Check for CD-ROM by looking for a specific, unique file.
                # Volume labels can be unreliable across OSes.
                if (mountpoint / "sunflower_cd.id").exists():
                    self.cdrom_path = mountpoint
                    # Verify it's read-only
                    if 'ro' not in p.opts:
                        print(f"Warning: SunflowerAI partition at {mountpoint} is not read-only.")

                # Check for the data partition by looking for its unique ID file.
                if (mountpoint / "sunflower_data.id").exists():
                    self.usb_path = mountpoint
                    # Verify it's writable
                    if 'ro' in p.opts or not os.access(mountpoint, os.W_OK):
                         print(f"Warning: SunflowerData partition at {mountpoint} is not writable.")

            except (PermissionError, FileNotFoundError):
                # This can happen with system-reserved or unmounted drives.
                continue
        
        if self.cdrom_path and self.usb_path:
            self.partitions_found = True

    def _scan_fallback_paths(self):
        """
        Fallback method to scan for partitions if psutil is not available.
        This is less reliable and intended for emergency use.
        """
        print("Warning: `psutil` not found. Falling back to manual drive scan.")
        
        # Windows drive letters
        if os.name == 'nt':
            possible_drives = [f"{chr(c)}:\\" for c in range(ord('D'), ord('Z') + 1)]
        # macOS and Linux mount points
        else:
            possible_drives = [f"/media/{os.getlogin()}/", "/Volumes/"]
            possible_drives += [os.path.join(d, '') for d in os.listdir('/media/')]
        
        for drive in possible_drives:
            mountpoint = Path(drive)
            if not mountpoint.exists():
                continue
            
            if (mountpoint / "sunflower_cd.id").exists():
                self.cdrom_path = mountpoint
            if (mountpoint / "sunflower_data.id").exists():
                self.usb_path = mountpoint
        
        if self.cdrom_path and self.usb_path:
            self.partitions_found = True

    def get_paths(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Returns the found paths for the CD-ROM and USB partitions."""
        return self.cdrom_path, self.usb_path

    def get_app_root(self) -> Optional[Path]:
        """Returns the root directory of the application on the CD-ROM."""
        return self.cdrom_path

    def get_data_root(self) -> Optional[Path]:
        """Returns the root directory for user data on the USB drive."""
        return self.usb_path

    def generate_report(self) -> str:
        """Generate a human-readable report of the findings."""
        report = "--- Sunflower AI Partition Report ---\n"
        if PSUTIL_AVAILABLE:
            report += "Mode: psutil (Reliable)\n"
        else:
            report += "Mode: Fallback Scan (Less Reliable)\n"
        
        if self.partitions_found:
            report += "Status: SUCCESS - All partitions found.\n"
            report += f"  - Application (CD-ROM): {self.cdrom_path}\n"
            report += f"  - User Data (USB):      {self.usb_path}\n"
        else:
            report += "Status: FAILED - Could not find required partitions.\n"
            if not self.cdrom_path:
                report += "  - Missing: 'SunflowerAI' application partition.\n"
            if not self.usb_path:
                report += "  - Missing: 'SunflowerData' user data partition.\n"
        report += "-----------------------------------"
        return report

if __name__ == '__main__':
    # To test this, you would need to create dummy files:
    # On a test drive (e.g., E:\):
    #   - E:\sunflower_cd.id
    #   - F:\sunflower_data.id
    detector = PartitionDetector()
    print(detector.generate_report())

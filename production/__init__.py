#!/usr/bin/env python3
"""
Sunflower AI Production Package

Manufacturing and production tools for creating Sunflower AI USB devices.
This package contains all scripts needed for mass production of the
dual-partition USB drives.

Main Components:
- create_iso.py: Builds CD-ROM ISO images
- prepare_usb_partition.py: Prepares USB data partitions
- batch_generator.py: Orchestrates complete batch production

Usage:
    # Create a single ISO
    python -m production.create_iso --version 1.0.0
    
    # Prepare USB partition
    python -m production.prepare_usb_partition --size 1024
    
    # Generate complete batch
    python -m production.batch_generator --size 100 --version 1.0.0
"""

import sys
from pathlib import Path

# Add production directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import main classes
from .create_iso import ISOCreator
from .prepare_usb_partition import USBPartitionPreparer
from .batch_generator import BatchManufacturingGenerator

# Package metadata
__version__ = "1.0.0"
__author__ = "Sunflower AI"

# Public API
__all__ = [
    "ISOCreator",
    "USBPartitionPreparer", 
    "BatchManufacturingGenerator",
    "create_iso",
    "prepare_usb",
    "generate_batch"
]

# Convenience functions
def create_iso(version="1.0.0", batch_id=None):
    """Create a Sunflower AI ISO image"""
    creator = ISOCreator(version=version, batch_id=batch_id)
    return creator.create()

def prepare_usb(batch_id=None, size_mb=1024, output_format="directory"):
    """Prepare a Sunflower AI USB partition"""
    preparer = USBPartitionPreparer(batch_id=batch_id, partition_size_mb=size_mb)
    return preparer.prepare(output_format=output_format)

def generate_batch(size=100, version="1.0.0"):
    """Generate a complete manufacturing batch"""
    generator = BatchManufacturingGenerator(batch_size=size, version=version)
    return generator.generate()

# Production constants
MINIMUM_USB_SIZE_GB = 16
RECOMMENDED_USB_SIZE_GB = 32
ISO_MAX_SIZE_GB = 8
USB_PARTITION_SIZE_MB = 1024

# Quality standards
QC_PASS_THRESHOLD = 1.0  # 100% pass rate required
PERFORMANCE_THRESHOLDS = {
    "read_speed_mbps": 80,
    "write_speed_mbps": 40,
    "response_time_ms": 20
}

# File patterns
REQUIRED_ISO_FILES = [
    "sunflower_cd.id",
    "manifest.json",
    "checksums.sha256",
    "Windows/SunflowerAI.exe",
    "macOS/SunflowerAI.app"
]

REQUIRED_USB_FILES = [
    "sunflower_data.id",
    ".initialized",
    "profiles/README.txt",
    ".security/device_token.json"
]

if __name__ == "__main__":
    print("Sunflower AI Production Tools")
    print(f"Version: {__version__}")
    print("\nAvailable commands:")
    print("  python -m production.create_iso")
    print("  python -m production.prepare_usb_partition") 
    print("  python -m production.batch_generator")
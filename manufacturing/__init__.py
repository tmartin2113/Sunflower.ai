"""
Sunflower AI Manufacturing Package

Production automation, quality control, and USB manufacturing systems
for the Sunflower AI Professional System commercial product.

Key Components:
- Master USB File Builder
- USB Validation and Quality Control
- Production Reporting
- Batch Tracking

This package contains all manufacturing automation and quality control
systems for producing commercial Sunflower AI USB drives.

Security Note:
This package handles authentication token generation and master file creation.
All security-sensitive operations are logged and audited.
"""

# Import main classes when available
# Note: These imports will fail if the actual .py files don't exist yet
# Remove the try/except once you create the actual module files

try:
    from .scripts.build_master_usb import MasterUSBBuilder
except ImportError:
    # Module not created yet - this is expected during initial setup
    MasterUSBBuilder = None

try:
    from .scripts.validate_usb import USBValidator
except ImportError:
    USBValidator = None

try:
    from .scripts.manufacturing_report import ManufacturingReporter
except ImportError:
    ManufacturingReporter = None

# Package version
__version__ = "4.2.0"

# Public API for manufacturing package
__all__ = [
    "MasterUSBBuilder",
    "USBValidator",
    "ManufacturingReporter"
]

# Manufacturing configuration
MASTER_FILES_DIR = "master_files"
CURRENT_VERSION_DIR = "current"
SCRIPTS_DIR = "scripts"

# Quality control standards
MINIMUM_USB_SIZE = 1024 * 1024 * 1024  # 1GB minimum
RECOMMENDED_USB_SIZE = 2 * 1024 * 1024 * 1024  # 2GB recommended
MAXIMUM_FILE_COUNT = 50  # Maximum files per USB

# Production settings
DEFAULT_BATCH_SIZE = 100
QUALITY_SAMPLE_RATE = 0.1  # 10% sampling for quality control
REQUIRED_PASS_RATE = 1.0   # 100% pass rate required

# Security settings
GENERATE_UNIQUE_TOKENS = True
ENABLE_FILE_INTEGRITY_CHECKING = True
REQUIRE_AUTHENTICATION_VALIDATION = True

# File patterns for master USB
REQUIRED_FILES = [
    "MAIN_LAUNCHER.bat",
    "UPDATE_SYSTEM.bat",
    "README_ABOUT_SUNFLOWER_AI.txt",
    "sunflower.ico"
]

OPTIONAL_FILES = [
    "ollama.exe"
]

GENERATED_FILES = [
    "autorun.inf",
    "security.manifest", 
    "checksums.sha256",
    "manifest.json"
]

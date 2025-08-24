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

Version History:
- 4.2.0: Original proprietary GUI version
- 5.0.0: Open WebUI integration update
"""

# Import main classes when available
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

# Package version - Updated for Open WebUI
__version__ = "5.0.0"

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
MAXIMUM_FILE_COUNT = 100  # Increased for Open WebUI components

# Production settings
DEFAULT_BATCH_SIZE = 100
QUALITY_SAMPLE_RATE = 0.1  # 10% sampling for quality control
REQUIRED_PASS_RATE = 1.0   # 100% pass rate required

# Security settings
GENERATE_UNIQUE_TOKENS = True
ENABLE_FILE_INTEGRITY_CHECKING = True
REQUIRE_AUTHENTICATION_VALIDATION = True

# ===================================================================
# FILE PATTERNS FOR MASTER USB - UPDATED FOR OPEN WEBUI
# ===================================================================

# Core launcher files (required for system operation)
REQUIRED_FILES = [
    # Main launchers
    "UNIVERSAL_LAUNCHER.py",              # Cross-platform GUI launcher
    "openwebui_integration.py",          # Core Open WebUI integration
    "launchers/windows_launcher.bat",    # Windows-specific launcher
    "launchers/macos_launcher.sh",       # macOS-specific launcher
    
    # Configuration and safety
    "openwebui_config.py",               # Open WebUI configuration manager
    "safety_filter.py",                  # Content moderation system
    "src/config.py",                     # Main configuration file
    
    # Documentation
    "README.md",                          # Main documentation
    "quickstart_guide.md",               # Quick start guide
    
    # Resources
    "resources/sunflower.ico",          # Application icon
    "data/parent_dashboard.html",       # Parent monitoring interface
    
    # Dependencies
    "requirements.txt"                   # Python dependencies
]

# Platform-specific executables (optional, downloaded if not present)
OPTIONAL_FILES = [
    # Ollama executables
    "ollama/ollama.exe",                # Windows Ollama binary
    "ollama/ollama",                    # macOS/Linux Ollama binary
    
    # Compiled applications (if pre-built)
    "Windows/SunflowerAI.exe",          # Windows compiled app
    "macOS/SunflowerAI.app",           # macOS application bundle
    
    # Pre-built models (large files)
    "models/sunflower-kids.gguf",       # Kids model binary
    "models/sunflower-educator.gguf",   # Educator model binary
]

# Files generated during manufacturing process
GENERATED_FILES = [
    # Auto-generated system files
    "autorun.inf",                      # Windows autorun configuration
    "security.manifest",                # Security verification manifest
    "checksums.sha256",                 # File integrity checksums
    "manifest.json",                    # Complete file manifest
    
    # Batch-specific files
    "batch_info.json",                  # Batch metadata
    "serial_numbers.csv",               # Device serial numbers
    "qc_checklist.pdf",                 # Quality control checklist
]

# Critical modelfiles that define AI behavior
MODELFILES = [
    "modelfiles/Sunflower_AI_Kids.modelfile",      # Kids AI definition
    "modelfiles/Sunflower_AI_Educator.modelfile",  # Educator AI definition
]

# Directory structure for CD-ROM partition
CDROM_STRUCTURE = {
    "root": [
        "sunflower_cd.id",              # CD-ROM partition marker
        "UNIVERSAL_LAUNCHER.py",        # Main launcher at root
        "README.md"
    ],
    "launchers": REQUIRED_FILES[2:4],   # Platform launchers
    "modelfiles": MODELFILES,
    "resources": ["sunflower.ico", "logo.png"],
    "docs": ["user_manual.pdf", "safety_guide.pdf"]
}

# Directory structure for USB data partition
USB_STRUCTURE = {
    "root": [
        "sunflower_data.id"             # USB partition marker
    ],
    "sunflower_data": {
        "profiles": [],                 # User profiles (created on first run)
        "openwebui": {
            "data": [],                 # Open WebUI database
            "config": []                # Open WebUI configuration
        },
        "ollama": {
            "models": [],               # Downloaded/created models
            "manifests": []             # Model manifests
        },
        "sessions": [],                 # Session logs
        "logs": [],                     # System logs
        "cache": [],                    # Temporary cache
        "backups": []                   # Automatic backups
    }
}

# Validation requirements for quality control
VALIDATION_REQUIREMENTS = {
    "cdrom_partition": {
        "read_only": True,
        "filesystem": "ISO9660",
        "min_files": len(REQUIRED_FILES),
        "max_size_mb": 4096,           # 4GB max for CD-ROM partition
        "required_markers": ["sunflower_cd.id"]
    },
    "usb_partition": {
        "read_write": True,
        "filesystem": ["FAT32", "exFAT", "NTFS"],
        "min_free_space_mb": 500,      # 500MB minimum free space
        "max_size_mb": 32768,          # 32GB max USB size
        "required_markers": ["sunflower_data.id"]
    }
}

# Manufacturing batch configuration
BATCH_CONFIG = {
    "id_format": "SF{version}-{date}-{batch:04d}",  # e.g., SF500-20250115-0001
    "label_format": "Sunflower AI v{version} - S/N: {serial}",
    "serial_prefix": "SAI",
    "serial_length": 12,
    "security_key_length": 32
}

# Quality control test requirements
QC_TESTS = {
    "partition_detection": {
        "required": True,
        "timeout_seconds": 30
    },
    "file_integrity": {
        "required": True,
        "verify_checksums": True
    },
    "launcher_execution": {
        "required": True,
        "platforms": ["Windows", "macOS"]
    },
    "model_loading": {
        "required": False,  # Optional since models can be downloaded
        "timeout_seconds": 60
    },
    "webui_startup": {
        "required": True,
        "port": 8080,
        "timeout_seconds": 120
    }
}

# Production statistics tracking
PRODUCTION_METRICS = {
    "track_build_time": True,
    "track_failure_rate": True,
    "track_qc_results": True,
    "generate_reports": True,
    "report_format": ["json", "csv", "pdf"]
}

# Helper functions for manufacturing processes

def generate_serial_number(batch_id: str, unit_number: int) -> str:
    """
    Generate a unique serial number for a device
    
    Args:
        batch_id: Batch identifier
        unit_number: Unit number within batch
        
    Returns:
        Formatted serial number
    """
    import hashlib
    
    # Create unique identifier
    unique_string = f"{batch_id}-{unit_number:05d}"
    hash_value = hashlib.sha256(unique_string.encode()).hexdigest()[:8].upper()
    
    return f"{BATCH_CONFIG['serial_prefix']}-{hash_value}-{unit_number:05d}"

def validate_file_structure(path: str, required_files: list) -> tuple:
    """
    Validate that all required files exist
    
    Args:
        path: Root path to check
        required_files: List of required file paths
        
    Returns:
        Tuple of (is_valid, missing_files)
    """
    import os
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(path, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
    
    is_valid = len(missing_files) == 0
    return is_valid, missing_files

def calculate_partition_size(file_list: list, base_path: str) -> int:
    """
    Calculate total size of files for partition
    
    Args:
        file_list: List of file paths
        base_path: Base directory path
        
    Returns:
        Total size in bytes
    """
    import os
    
    total_size = 0
    for file_path in file_list:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            if os.path.isfile(full_path):
                total_size += os.path.getsize(full_path)
            elif os.path.isdir(full_path):
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        total_size += os.path.getsize(os.path.join(root, file))
    
    return total_size

# Export version for external tools
MANUFACTURING_VERSION = __version__

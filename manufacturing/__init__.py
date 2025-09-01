"""
Sunflower AI Professional System - Manufacturing Package
Version: 6.2.0
Copyright (c) 2025 Sunflower AI Corporation

Manufacturing subsystem for production of partitioned USB devices with
CD-ROM and writable partitions for educational STEM learning system.
"""

import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Configure manufacturing logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('manufacturing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('sunflower.manufacturing')

# Version and build information
__version__ = '6.2.0'
__build_date__ = '2025-01-15'
__manufacturer__ = 'Sunflower AI Corporation'

class PartitionType(Enum):
    """Enumeration of partition types for the device."""
    CDROM = "iso9660"
    USB = "fat32"
    HYBRID = "hybrid"

class ProductionStage(Enum):
    """Manufacturing production stages."""
    PREPARATION = "preparation"
    PARTITION_CREATION = "partition_creation"
    FILE_DEPLOYMENT = "file_deployment"
    VALIDATION = "validation"
    PACKAGING = "packaging"
    QUALITY_CONTROL = "quality_control"
    COMPLETE = "complete"

@dataclass
class DeviceSpecification:
    """Specifications for manufactured device."""
    device_id: str
    batch_id: str
    capacity_gb: int
    cdrom_size_mb: int
    usb_size_mb: int
    platform: str  # windows, macos, universal
    model_variant: str  # 7b, 3b, 1b, 1b-q4_0
    creation_timestamp: datetime
    validation_checksum: str
    hardware_token: str
    production_stage: ProductionStage
    
    def to_dict(self) -> Dict:
        """Convert specification to dictionary for serialization."""
        spec_dict = asdict(self)
        spec_dict['creation_timestamp'] = self.creation_timestamp.isoformat()
        spec_dict['production_stage'] = self.production_stage.value
        return spec_dict
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DeviceSpecification':
        """Create specification from dictionary."""
        data['creation_timestamp'] = datetime.fromisoformat(data['creation_timestamp'])
        data['production_stage'] = ProductionStage(data['production_stage'])
        return cls(**data)

class ManufacturingError(Exception):
    """Base exception for manufacturing errors."""
    def __init__(self, message: str, stage: ProductionStage, device_id: Optional[str] = None):
        self.message = message
        self.stage = stage
        self.device_id = device_id
        self.timestamp = datetime.now()
        super().__init__(self.format_error())
    
    def format_error(self) -> str:
        """Format error message with context."""
        error_msg = f"Manufacturing Error at {self.stage.value}: {self.message}"
        if self.device_id:
            error_msg += f" (Device: {self.device_id})"
        return error_msg
    
    def to_log_entry(self) -> Dict:
        """Convert error to log entry."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'stage': self.stage.value,
            'device_id': self.device_id,
            'message': self.message,
            'error_type': self.__class__.__name__
        }

class PartitionError(ManufacturingError):
    """Error during partition creation."""
    pass

class ValidationError(ManufacturingError):
    """Error during validation stage."""
    pass

class DeploymentError(ManufacturingError):
    """Error during file deployment."""
    pass

def generate_device_id(batch_id: str, sequence: int) -> str:
    """
    Generate unique device identifier.
    
    Args:
        batch_id: Batch identifier
        sequence: Sequence number in batch
        
    Returns:
        Unique device identifier
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw_id = f"SUNFLOWER-{batch_id}-{sequence:06d}-{timestamp}"
    hash_suffix = hashlib.sha256(raw_id.encode()).hexdigest()[:8].upper()
    return f"{batch_id}-{sequence:06d}-{hash_suffix}"

def generate_hardware_token(device_id: str, secret_key: bytes) -> str:
    """
    Generate hardware authentication token.
    
    Args:
        device_id: Device identifier
        secret_key: Manufacturing secret key
        
    Returns:
        Hardware authentication token
    """
    import hmac
    
    message = f"{device_id}-{__version__}-{__build_date__}".encode()
    token = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
    return token.upper()

def calculate_checksum(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    Calculate file checksum for validation.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm to use
        
    Returns:
        Hexadecimal checksum string
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()

def validate_platform_requirements(platform: str) -> bool:
    """
    Validate platform-specific requirements.
    
    Args:
        platform: Target platform (windows, macos, universal)
        
    Returns:
        True if requirements are met
    """
    valid_platforms = {'windows', 'macos', 'universal'}
    
    if platform not in valid_platforms:
        raise ValueError(f"Invalid platform: {platform}. Must be one of {valid_platforms}")
    
    # Check platform-specific tools
    if platform == 'windows' or platform == 'universal':
        # Check for Windows ISO tools
        if not Path('tools/mkisofs.exe').exists() and sys.platform == 'win32':
            logger.warning("Windows ISO tools not found")
            return False
    
    if platform == 'macos' or platform == 'universal':
        # Check for macOS tools
        if not Path('tools/hdiutil').exists() and sys.platform == 'darwin':
            logger.warning("macOS disk utility tools not found")
            return False
    
    return True

def load_manufacturing_config() -> Dict:
    """
    Load manufacturing configuration.
    
    Returns:
        Configuration dictionary
    """
    config_path = Path(__file__).parent / 'config' / 'manufacturing.json'
    
    if not config_path.exists():
        # Return default configuration
        return {
            'batch_size': 100,
            'cdrom_size_mb': 4096,
            'usb_size_mb': 1024,
            'default_platform': 'universal',
            'model_variants': ['7b', '3b', '1b', '1b-q4_0'],
            'quality_control': {
                'sample_rate': 0.1,  # 10% sampling
                'full_validation_threshold': 10,  # Full validation every 10 devices
                'checksum_algorithm': 'sha256'
            },
            'paths': {
                'master_files': 'master_files/current',
                'output': 'output',
                'logs': 'logs',
                'reports': 'reports'
            }
        }
    
    with open(config_path, 'r') as f:
        return json.load(f)

def initialize_manufacturing_environment() -> bool:
    """
    Initialize manufacturing environment with necessary directories.
    
    Returns:
        True if initialization successful
    """
    required_dirs = [
        'production',
        'scripts',
        'master_files/current',
        'quality_control',
        'output',
        'logs',
        'reports',
        'config',
        'tools'
    ]
    
    base_path = Path(__file__).parent
    
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized directory: {dir_path}")
    
    # Create default configuration if not exists
    config_path = base_path / 'config' / 'manufacturing.json'
    if not config_path.exists():
        config = load_manufacturing_config()
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Created default manufacturing configuration")
    
    return True

class ProductionMetrics:
    """Track production metrics and statistics."""
    
    def __init__(self):
        self.devices_created = 0
        self.devices_validated = 0
        self.devices_failed = 0
        self.start_time = datetime.now()
        self.errors: List[ManufacturingError] = []
        self.batch_statistics: Dict[str, Dict] = {}
    
    def record_device(self, device_spec: DeviceSpecification, success: bool = True):
        """Record device production outcome."""
        if success:
            self.devices_created += 1
            if device_spec.production_stage == ProductionStage.COMPLETE:
                self.devices_validated += 1
        else:
            self.devices_failed += 1
        
        # Update batch statistics
        if device_spec.batch_id not in self.batch_statistics:
            self.batch_statistics[device_spec.batch_id] = {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'start_time': datetime.now().isoformat()
            }
        
        batch_stats = self.batch_statistics[device_spec.batch_id]
        batch_stats['total'] += 1
        if success:
            batch_stats['successful'] += 1
        else:
            batch_stats['failed'] += 1
    
    def record_error(self, error: ManufacturingError):
        """Record manufacturing error."""
        self.errors.append(error)
        logger.error(f"Manufacturing error recorded: {error.format_error()}")
    
    def get_production_rate(self) -> float:
        """Calculate production rate (devices per hour)."""
        elapsed_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        if elapsed_hours > 0:
            return self.devices_created / elapsed_hours
        return 0.0
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.devices_created + self.devices_failed
        if total > 0:
            return (self.devices_created / total) * 100
        return 0.0
    
    def generate_report(self) -> Dict:
        """Generate production metrics report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'duration_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
            'devices_created': self.devices_created,
            'devices_validated': self.devices_validated,
            'devices_failed': self.devices_failed,
            'production_rate': self.get_production_rate(),
            'success_rate': self.get_success_rate(),
            'batch_statistics': self.batch_statistics,
            'error_count': len(self.errors),
            'recent_errors': [e.to_log_entry() for e in self.errors[-10:]]  # Last 10 errors
        }

# Initialize module on import
if __name__ != "__main__":
    logger.info(f"Sunflower AI Manufacturing System v{__version__} initialized")
    logger.info(f"Build date: {__build_date__}")
    
    # Ensure environment is properly set up
    if not initialize_manufacturing_environment():
        logger.error("Failed to initialize manufacturing environment")
        sys.exit(1)

# Export public API
__all__ = [
    'DeviceSpecification',
    'PartitionType',
    'ProductionStage',
    'ManufacturingError',
    'PartitionError',
    'ValidationError',
    'DeploymentError',
    'ProductionMetrics',
    'generate_device_id',
    'generate_hardware_token',
    'calculate_checksum',
    'validate_platform_requirements',
    'load_manufacturing_config',
    'initialize_manufacturing_environment',
    '__version__',
    '__build_date__',
    '__manufacturer__'
]try:
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

"""
Sunflower AI Professional System - Build Package
Production build system for partitioned CD-ROM/USB educational device
Version: 6.2 - January 2025
"""

import os
import sys
import platform
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

# Build configuration constants
BUILD_VERSION = "6.2.0"
BUILD_DATE = datetime.now().strftime("%Y%m%d")
BUILD_NUMBER = f"{BUILD_VERSION}.{BUILD_DATE}"

# Platform detection
PLATFORM = platform.system().lower()
ARCH = platform.machine().lower()
IS_WINDOWS = PLATFORM == "windows"
IS_MACOS = PLATFORM == "darwin"

# Directory structure
BASE_DIR = Path(__file__).parent.parent.absolute()
BUILD_DIR = Path(__file__).parent.absolute()
TEMPLATES_DIR = BUILD_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "dist"
CACHE_DIR = BASE_DIR / ".build_cache"
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = BASE_DIR / "models"

# Partition configuration
CDROM_PARTITION_SIZE_MB = 4096  # 4GB CD-ROM partition
USB_PARTITION_SIZE_MB = 1024    # 1GB USB partition
PARTITION_SIGNATURE = "SUNFLOWER_AI_PRO_v6"

# Model variants for hardware optimization
MODEL_VARIANTS = {
    "high_end": {
        "name": "llama3.2:7b",
        "size_gb": 3.8,
        "min_ram_gb": 16,
        "min_vram_gb": 8,
        "performance": "optimal"
    },
    "mid_range": {
        "name": "llama3.2:3b",
        "size_gb": 1.9,
        "min_ram_gb": 8,
        "min_vram_gb": 4,
        "performance": "balanced"
    },
    "low_end": {
        "name": "llama3.2:1b",
        "size_gb": 0.7,
        "min_ram_gb": 4,
        "min_vram_gb": 2,
        "performance": "standard"
    },
    "minimum": {
        "name": "llama3.2:1b-q4_0",
        "size_gb": 0.4,
        "min_ram_gb": 4,
        "min_vram_gb": 0,
        "performance": "basic"
    }
}

# Security configuration
SECURITY_CONFIG = {
    "signing_required": True,
    "encryption_algorithm": "AES-256-GCM",
    "integrity_check": "SHA-256",
    "device_authentication": True,
    "tamper_detection": True
}

# Build targets
BUILD_TARGETS = {
    "windows": {
        "executable": "SunflowerAI.exe",
        "installer": "SunflowerAI_Setup.msi",
        "spec_file": "windows.spec",
        "icon": "sunflower.ico",
        "min_os_version": "Windows 10 1809"
    },
    "macos": {
        "app_bundle": "SunflowerAI.app",
        "installer": "SunflowerAI.dmg",
        "spec_file": "macos.spec",
        "icon": "sunflower.icns",
        "min_os_version": "10.14"  # macOS Mojave
    }
}

class BuildConfiguration:
    """Centralized build configuration management"""
    
    def __init__(self):
        self.config = self._load_configuration()
        self.validate_environment()
    
    def _load_configuration(self) -> Dict:
        """Load build configuration from file or defaults"""
        config_file = BUILD_DIR / "build_config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                    # Merge with defaults
                    config = {
                        "version": BUILD_VERSION,
                        "build_number": BUILD_NUMBER,
                        "platform": PLATFORM,
                        "architecture": ARCH,
                        "models": MODEL_VARIANTS,
                        "security": SECURITY_CONFIG,
                        "targets": BUILD_TARGETS,
                        "debug_mode": False,
                        "optimization_level": "maximum",
                        "compression": "lzma2",
                        "strip_debug_symbols": True
                    }
                    config.update(custom_config)
                    return config
            except Exception as e:
                print(f"Warning: Could not load custom config: {e}")
        
        # Return default configuration
        return {
            "version": BUILD_VERSION,
            "build_number": BUILD_NUMBER,
            "platform": PLATFORM,
            "architecture": ARCH,
            "models": MODEL_VARIANTS,
            "security": SECURITY_CONFIG,
            "targets": BUILD_TARGETS,
            "debug_mode": False,
            "optimization_level": "maximum",
            "compression": "lzma2",
            "strip_debug_symbols": True
        }
    
    def validate_environment(self) -> bool:
        """Validate build environment requirements"""
        errors = []
        
        # Check Python version
        if sys.version_info < (3, 9):
            errors.append(f"Python 3.9+ required, found {sys.version}")
        
        # Check platform support
        if not (IS_WINDOWS or IS_MACOS):
            errors.append(f"Unsupported platform: {PLATFORM}")
        
        # Check required directories
        for dir_path in [BUILD_DIR, TEMPLATES_DIR]:
            if not dir_path.exists():
                errors.append(f"Required directory missing: {dir_path}")
        
        # Check for required tools
        required_tools = []
        if IS_WINDOWS:
            required_tools = ["pyinstaller", "signtool", "makensis"]
        elif IS_MACOS:
            required_tools = ["pyinstaller", "codesign", "hdiutil"]
        
        for tool in required_tools:
            if not self._check_tool_available(tool):
                errors.append(f"Required tool not found: {tool}")
        
        if errors:
            print("Build Environment Validation Failed:")
            for error in errors:
                print(f"  ✗ {error}")
            return False
        
        print("Build Environment Validation Successful")
        return True
    
    def _check_tool_available(self, tool: str) -> bool:
        """Check if a build tool is available in PATH"""
        import shutil
        return shutil.which(tool) is not None
    
    def get_output_path(self, artifact_type: str) -> Path:
        """Get output path for build artifact"""
        artifact_dir = OUTPUT_DIR / self.config["platform"] / artifact_type
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir
    
    def generate_build_manifest(self) -> Dict:
        """Generate comprehensive build manifest"""
        return {
            "build_info": {
                "version": self.config["version"],
                "build_number": self.config["build_number"],
                "timestamp": datetime.now().isoformat(),
                "platform": self.config["platform"],
                "architecture": self.config["architecture"],
                "builder": os.environ.get("USER", "unknown")
            },
            "partition_layout": {
                "cdrom": {
                    "size_mb": CDROM_PARTITION_SIZE_MB,
                    "filesystem": "ISO9660/UDF",
                    "read_only": True,
                    "signature": PARTITION_SIGNATURE
                },
                "usb": {
                    "size_mb": USB_PARTITION_SIZE_MB,
                    "filesystem": "exFAT",
                    "read_only": False,
                    "encryption": "AES-256"
                }
            },
            "included_models": list(self.config["models"].keys()),
            "security": self.config["security"],
            "checksums": {}
        }

class SecurityManager:
    """Handle code signing, encryption, and integrity verification"""
    
    def __init__(self, config: BuildConfiguration):
        self.config = config
        self.checksums = {}
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum for file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        checksum = sha256_hash.hexdigest()
        self.checksums[str(file_path)] = checksum
        return checksum
    
    def generate_device_token(self) -> str:
        """Generate unique device authentication token"""
        import secrets
        token = secrets.token_hex(32)
        # Additional hardware fingerprinting would go here
        return token
    
    def sign_executable(self, exe_path: Path, platform: str) -> bool:
        """Sign executable for platform"""
        try:
            if platform == "windows":
                return self._sign_windows_exe(exe_path)
            elif platform == "macos":
                return self._sign_macos_app(exe_path)
            return False
        except Exception as e:
            print(f"Signing failed: {e}")
            return False
    
    def _sign_windows_exe(self, exe_path: Path) -> bool:
        """Sign Windows executable with Authenticode"""
        import subprocess
        
        cert_path = os.environ.get("WINDOWS_CERT_PATH")
        cert_password = os.environ.get("WINDOWS_CERT_PASSWORD")
        
        if not cert_path:
            print("Warning: No Windows signing certificate configured")
            return False
        
        cmd = [
            "signtool", "sign",
            "/f", cert_path,
            "/p", cert_password,
            "/fd", "SHA256",
            "/tr", "http://timestamp.digicert.com",
            "/td", "SHA256",
            "/d", "Sunflower AI Professional System",
            str(exe_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def _sign_macos_app(self, app_path: Path) -> bool:
        """Sign macOS application bundle"""
        import subprocess
        
        developer_id = os.environ.get("MACOS_DEVELOPER_ID")
        if not developer_id:
            print("Warning: No macOS Developer ID configured")
            return False
        
        cmd = [
            "codesign",
            "--force",
            "--deep",
            "--sign", developer_id,
            "--entitlements", str(TEMPLATES_DIR / "entitlements.plist"),
            "--options", "runtime",
            str(app_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def create_integrity_manifest(self, build_dir: Path) -> Path:
        """Create integrity verification manifest"""
        manifest = {
            "version": self.config.config["version"],
            "timestamp": datetime.now().isoformat(),
            "files": {}
        }
        
        for file_path in build_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(build_dir)
                manifest["files"][str(relative_path)] = {
                    "size": file_path.stat().st_size,
                    "checksum": self.calculate_checksum(file_path),
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                }
        
        manifest_path = build_dir / "integrity.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        # Sign the manifest itself
        manifest_checksum = self.calculate_checksum(manifest_path)
        signature_path = build_dir / "integrity.sig"
        with open(signature_path, 'w', encoding='utf-8') as f:
            f.write(manifest_checksum)
        
        return manifest_path

class PartitionManager:
    """Manage dual-partition device creation"""
    
    def __init__(self, config: BuildConfiguration):
        self.config = config
    
    def create_partition_layout(self, output_path: Path) -> Tuple[Path, Path]:
        """Create CD-ROM and USB partition structure"""
        cdrom_path = output_path / "cdrom_partition"
        usb_path = output_path / "usb_partition"
        
        # Create partition directories
        cdrom_path.mkdir(parents=True, exist_ok=True)
        usb_path.mkdir(parents=True, exist_ok=True)
        
        # Create CD-ROM partition structure
        self._create_cdrom_structure(cdrom_path)
        
        # Create USB partition structure
        self._create_usb_structure(usb_path)
        
        return cdrom_path, usb_path
    
    def _create_cdrom_structure(self, cdrom_path: Path):
        """Create read-only CD-ROM partition structure"""
        directories = [
            "system",
            "models",
            "ollama",
            "documentation",
            "launchers"
        ]
        
        for dir_name in directories:
            (cdrom_path / dir_name).mkdir(exist_ok=True)
        
        # Create partition identifier
        with open(cdrom_path / "SUNFLOWER.ID", 'w') as f:
            f.write(PARTITION_SIGNATURE)
    
    def _create_usb_structure(self, usb_path: Path):
        """Create writeable USB partition structure"""
        directories = [
            "profiles",
            "conversations",
            "logs",
            "dashboard",
            "config"
        ]
        
        for dir_name in directories:
            (usb_path / dir_name).mkdir(exist_ok=True)
        
        # Create initial configuration
        initial_config = {
            "version": self.config.config["version"],
            "initialized": False,
            "family_id": None,
            "profiles": []
        }
        
        with open(usb_path / "config" / "system.json", 'w') as f:
            json.dump(initial_config, f, indent=2)

# Export main components
__all__ = [
    'BuildConfiguration',
    'SecurityManager',
    'PartitionManager',
    'BUILD_VERSION',
    'BUILD_DIR',
    'OUTPUT_DIR',
    'MODEL_VARIANTS',
    'PLATFORM',
    'IS_WINDOWS',
    'IS_MACOS'
]

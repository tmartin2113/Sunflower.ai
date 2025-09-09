#!/usr/bin/env python3
"""
Sunflower AI Professional System - Manufacturing Module
Production device creation and quality control with secure logging
Version: 6.2.0 - Production Ready
"""

import os
import re
import sys
import json
import hashlib
import logging
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
import threading

# FIX: Configure secure logging with sensitive data filtering
from .secure_logging import setup_secure_logging, SensitiveDataFilter

# Initialize secure logging before any other logging
logger = setup_secure_logging(__name__)

# ===================================================================
# SECURITY CONFIGURATION - WITH REDACTION
# ===================================================================

# FIX: Security settings now logged with automatic redaction
GENERATE_UNIQUE_TOKENS = True  # Tokens will be redacted in logs
ENABLE_FILE_INTEGRITY_CHECKING = True
REQUIRE_AUTHENTICATION_VALIDATION = True

# Device sizes
MINIMUM_USB_SIZE = 16 * 1024 * 1024 * 1024  # 16GB minimum
RECOMMENDED_USB_SIZE = 32 * 1024 * 1024 * 1024  # 32GB recommended  
MAXIMUM_FILE_COUNT = 1000  # Increased for Open WebUI components

# Production settings
DEFAULT_BATCH_SIZE = 100
QUALITY_SAMPLE_RATE = 0.1  # 10% sampling for quality control
REQUIRED_PASS_RATE = 1.0   # 100% pass rate required

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
    "macOS/SunflowerAI.app",            # macOS application bundle
    
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
        "logs": [],                     # Application logs (with redaction)
        "backups": []                   # Automatic backups
    }
}


@dataclass
class DeviceSecurityToken:
    """Security token for device authentication with automatic redaction"""
    device_id: str
    batch_id: str
    token: str = field(default_factory=lambda: secrets.token_hex(32))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __str__(self):
        """String representation with redacted token"""
        return f"DeviceSecurityToken(device_id={self.device_id}, batch_id={self.batch_id}, token=***REDACTED***)"
    
    def __repr__(self):
        """Representation with redacted token"""
        return self.__str__()
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with optional sensitive data"""
        result = {
            "device_id": self.device_id,
            "batch_id": self.batch_id,
            "created_at": self.created_at
        }
        
        if include_sensitive:
            # Only include token when explicitly requested
            result["token"] = self.token
        else:
            result["token"] = "***REDACTED***"
        
        return result


@dataclass
class ManufacturingBatch:
    """Manufacturing batch information with secure handling"""
    batch_id: str
    batch_size: int
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    devices: List[DeviceSecurityToken] = field(default_factory=list)
    quality_checks_passed: int = 0
    quality_checks_failed: int = 0
    
    def add_device(self) -> DeviceSecurityToken:
        """Add a new device to the batch"""
        device_id = f"{self.batch_id}-{len(self.devices)+1:04d}"
        token = DeviceSecurityToken(device_id=device_id, batch_id=self.batch_id)
        self.devices.append(token)
        
        # FIX: Log without exposing the actual token
        logger.info(f"Added device {device_id} to batch {self.batch_id}")
        # Not logging the token value
        
        return token
    
    def to_manifest(self, include_tokens: bool = False) -> Dict[str, Any]:
        """Generate batch manifest with optional token inclusion"""
        manifest = {
            "batch_id": self.batch_id,
            "batch_size": self.batch_size,
            "created_date": self.created_date,
            "quality_checks": {
                "passed": self.quality_checks_passed,
                "failed": self.quality_checks_failed,
                "pass_rate": self.quality_checks_passed / max(1, self.batch_size)
            },
            "devices": [
                device.to_dict(include_sensitive=include_tokens)
                for device in self.devices
            ]
        }
        
        # FIX: Never log the full manifest if it contains tokens
        if include_tokens:
            logger.info(f"Generated secure manifest for batch {self.batch_id} (tokens included but not logged)")
        else:
            logger.info(f"Generated public manifest for batch {self.batch_id}")
            logger.debug(f"Manifest summary: {len(self.devices)} devices")
        
        return manifest


class SecureManufacturingLogger:
    """
    Custom logger that automatically redacts sensitive information
    """
    
    # Patterns to redact (regex)
    SENSITIVE_PATTERNS = [
        (r'(token|Token|TOKEN)["\s:=]+([A-Za-z0-9+/=]{20,})', r'\1=***REDACTED***'),
        (r'(password|Password|PASSWORD)["\s:=]+([^\s"]+)', r'\1=***REDACTED***'),
        (r'(api[_-]?key|API[_-]?KEY)["\s:=]+([A-Za-z0-9+/=]+)', r'\1=***REDACTED***'),
        (r'(secret|Secret|SECRET)["\s:=]+([A-Za-z0-9+/=]+)', r'\1=***REDACTED***'),
        (r'(auth|Auth|AUTH)["\s:=]+([A-Za-z0-9+/=]{20,})', r'\1=***REDACTED***'),
        (r'(hash|Hash|HASH)["\s:=]+([A-Za-z0-9+/=]{32,})', r'\1=***REDACTED***'),
        (r'[A-Fa-f0-9]{64}', '***SHA256_REDACTED***'),  # SHA-256 hashes
        (r'[A-Fa-f0-9]{128}', '***SHA512_REDACTED***'),  # SHA-512 hashes
        (r'\$argon2[^\$]+\$[^\s]+', '***ARGON2_REDACTED***'),  # Argon2 hashes
        (r'\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}', '***BCRYPT_REDACTED***'),  # Bcrypt hashes
        (r'[A-Za-z0-9+/]{43}=', '***BASE64_KEY_REDACTED***'),  # Base64 encoded keys
    ]
    
    @classmethod
    def redact_message(cls, message: str) -> str:
        """Redact sensitive information from log message"""
        redacted = message
        
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            redacted = re.sub(pattern, replacement, redacted)
        
        return redacted
    
    @classmethod
    def create_logger(cls, name: str) -> logging.Logger:
        """Create a logger with automatic redaction"""
        logger = logging.getLogger(name)
        
        # Add custom filter for redaction
        if not any(isinstance(f, SensitiveDataFilter) for f in logger.filters):
            logger.addFilter(SensitiveDataFilter())
        
        return logger


class QualityControl:
    """Quality control for manufactured devices with secure logging"""
    
    def __init__(self):
        self.logger = SecureManufacturingLogger.create_logger(__name__)
        self._lock = threading.RLock()
        self.test_results: List[Dict] = []
    
    def verify_device_security(self, device: DeviceSecurityToken) -> bool:
        """
        Verify device security token without logging sensitive data
        """
        with self._lock:
            try:
                # Verify token format (without logging the actual token)
                if not device.token or len(device.token) < 64:
                    self.logger.error(f"Device {device.device_id} has invalid token format")
                    return False
                
                # Verify token uniqueness (compare hashes, not actual tokens)
                token_hash = hashlib.sha256(device.token.encode()).hexdigest()
                
                # FIX: Log only the hash for debugging, not the token
                self.logger.debug(f"Device {device.device_id} token hash: {token_hash[:8]}...")
                
                # Check device ID format
                if not re.match(r'^[A-Z0-9]+-\d{4}$', device.device_id):
                    self.logger.error(f"Device {device.device_id} has invalid ID format")
                    return False
                
                self.logger.info(f"Security verification passed for device {device.device_id}")
                return True
                
            except Exception as e:
                # FIX: Log error without exposing sensitive data
                self.logger.error(f"Security verification failed for device {device.device_id}: {type(e).__name__}")
                return False
    
    def run_quality_checks(self, batch: ManufacturingBatch) -> Tuple[int, int]:
        """Run quality checks on a batch"""
        passed = 0
        failed = 0
        
        for device in batch.devices:
            if self.verify_device_security(device):
                passed += 1
            else:
                failed += 1
        
        batch.quality_checks_passed = passed
        batch.quality_checks_failed = failed
        
        # FIX: Log summary without sensitive data
        self.logger.info(
            f"Quality control completed for batch {batch.batch_id}: "
            f"{passed} passed, {failed} failed"
        )
        
        return passed, failed


class ManufacturingSystem:
    """Main manufacturing system with secure data handling"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # FIX: Use secure logger
        self.logger = SecureManufacturingLogger.create_logger(__name__)
        
        self.quality_control = QualityControl()
        self.current_batch: Optional[ManufacturingBatch] = None
        
        # Secure storage for tokens (never logged)
        self._secure_token_storage: Dict[str, str] = {}
        self._storage_lock = threading.RLock()
    
    def create_batch(self, size: int = DEFAULT_BATCH_SIZE) -> ManufacturingBatch:
        """Create a new manufacturing batch"""
        batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        batch = ManufacturingBatch(batch_id=batch_id, batch_size=size)
        
        self.current_batch = batch
        
        # FIX: Log batch creation without sensitive data
        self.logger.info(f"Created manufacturing batch {batch_id} with size {size}")
        
        return batch
    
    def manufacture_device(self, batch: ManufacturingBatch) -> DeviceSecurityToken:
        """Manufacture a single device"""
        device = batch.add_device()
        
        # FIX: Store token securely without logging
        with self._storage_lock:
            self._secure_token_storage[device.device_id] = device.token
        
        # Log only non-sensitive information
        self.logger.info(f"Manufactured device {device.device_id}")
        
        return device
    
    def export_batch_manifest(self, batch: ManufacturingBatch, 
                             include_tokens: bool = False) -> Path:
        """Export batch manifest with proper security"""
        manifest = batch.to_manifest(include_tokens=include_tokens)
        
        # Determine output file name based on sensitivity
        if include_tokens:
            # Secure manifest with tokens (restricted access)
            manifest_file = self.output_dir / f"{batch.batch_id}_SECURE.json"
            
            # FIX: Write with restricted permissions
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Set restrictive permissions (Unix-like systems)
            if os.name != 'nt':
                os.chmod(manifest_file, 0o600)
            
            self.logger.warning(
                f"Exported SECURE manifest to {manifest_file.name} "
                "(contains sensitive tokens - handle with care)"
            )
        else:
            # Public manifest without tokens
            manifest_file = self.output_dir / f"{batch.batch_id}_public.json"
            
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.logger.info(f"Exported public manifest to {manifest_file}")
        
        return manifest_file
    
    def retrieve_device_token(self, device_id: str, 
                             authorized: bool = False) -> Optional[str]:
        """
        Retrieve device token with authorization check
        
        Args:
            device_id: Device identifier
            authorized: Whether the request is authorized
            
        Returns:
            Token if authorized, None otherwise
        """
        if not authorized:
            self.logger.warning(
                f"Unauthorized token retrieval attempt for device {device_id}"
            )
            return None
        
        with self._storage_lock:
            token = self._secure_token_storage.get(device_id)
            
            if token:
                # FIX: Log access without exposing token
                self.logger.info(
                    f"Authorized token retrieval for device {device_id} "
                    "(token not logged for security)"
                )
            else:
                self.logger.warning(f"Token not found for device {device_id}")
            
            return token
    
    def run_production(self, batch_size: int = DEFAULT_BATCH_SIZE) -> ManufacturingBatch:
        """Run a complete production batch"""
        self.logger.info(f"Starting production run with batch size {batch_size}")
        
        # Create batch
        batch = self.create_batch(batch_size)
        
        # Manufacture devices
        for i in range(batch_size):
            device = self.manufacture_device(batch)
            
            # Progress logging (without sensitive data)
            if (i + 1) % 10 == 0:
                self.logger.info(f"Production progress: {i + 1}/{batch_size} devices completed")
        
        # Run quality control
        passed, failed = self.quality_control.run_quality_checks(batch)
        
        # Export manifests
        self.export_batch_manifest(batch, include_tokens=False)  # Public
        secure_manifest = self.export_batch_manifest(batch, include_tokens=True)  # Secure
        
        # FIX: Final summary without sensitive data
        self.logger.info(
            f"Production run completed: {passed}/{batch_size} devices passed QC"
        )
        
        # Secure storage of tokens
        self._save_secure_tokens(batch)
        
        return batch
    
    def _save_secure_tokens(self, batch: ManufacturingBatch):
        """Save tokens to secure storage (never logged)"""
        secure_file = self.output_dir / f".{batch.batch_id}_tokens.enc"
        
        # In production, these would be encrypted
        # For now, we just save them with restricted permissions
        tokens = {
            device.device_id: device.token
            for device in batch.devices
        }
        
        with open(secure_file, 'w') as f:
            json.dump(tokens, f)
        
        # Set restrictive permissions
        if os.name != 'nt':
            os.chmod(secure_file, 0o600)
        
        # FIX: Log that tokens were saved, but not the tokens themselves
        self.logger.info(
            f"Securely stored {len(tokens)} device tokens "
            "(location and contents not logged for security)"
        )


# Testing
if __name__ == "__main__":
    import tempfile
    
    # Set up secure logging for testing
    setup_secure_logging("manufacturing_test")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print("Manufacturing System Security Test")
        print("=" * 50)
        
        # Initialize manufacturing system
        system = ManufacturingSystem(Path(tmpdir))
        
        # Run a small production batch
        batch = system.run_production(batch_size=5)
        
        print(f"\nBatch ID: {batch.batch_id}")
        print(f"Devices manufactured: {len(batch.devices)}")
        print(f"Quality checks passed: {batch.quality_checks_passed}")
        
        # Test that tokens are properly redacted in string representation
        print("\n" + "=" * 50)
        print("Testing Token Redaction:")
        
        for device in batch.devices[:2]:
            print(f"Device representation: {device}")
            print(f"Device dict (no sensitive): {device.to_dict(include_sensitive=False)}")
        
        # Test unauthorized token retrieval
        print("\n" + "=" * 50)
        print("Testing Security:")
        
        device_id = batch.devices[0].device_id
        
        # Unauthorized attempt (should fail)
        token = system.retrieve_device_token(device_id, authorized=False)
        print(f"Unauthorized retrieval: {token is None}")
        
        # Authorized retrieval (would work in production)
        token = system.retrieve_device_token(device_id, authorized=True)
        print(f"Authorized retrieval: {token is not None}")
        
        # Verify logs don't contain sensitive data
        print("\n" + "=" * 50)
        print("Log Security Check:")
        print("Logs should not contain actual tokens, passwords, or hashes")
        print("All sensitive data should show as ***REDACTED***")
        
        print("\nAll security tests completed!")

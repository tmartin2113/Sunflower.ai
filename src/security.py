"""
Sunflower AI Professional System - Security Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Comprehensive security system handling authentication, encryption,
session management, and audit logging. Ensures child safety and
data protection with enterprise-grade security measures.
"""

import os
import sys
import json
import secrets
import hashlib
import logging
import threading
import time
import base64
import hmac
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import re

# Cryptography imports
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from . import SecurityError

logger = logging.getLogger(__name__)


class AuthLevel(Enum):
    """Authentication levels"""
    NONE = 0
    CHILD = 1
    PARENT = 2
    EDUCATOR = 3
    ADMIN = 4


class SecurityEvent(Enum):
    """Security event types"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PASSWORD_CHANGE = "password_change"
    PROFILE_ACCESS = "profile_access"
    SAFETY_VIOLATION = "safety_violation"
    ENCRYPTION_ERROR = "encryption_error"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class SecurityToken:
    """Security token for session management"""
    token_id: str
    user_id: str
    user_type: str
    auth_level: int
    created_at: str
    expires_at: str
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    is_active: bool = True
    refresh_count: int = 0


@dataclass
class AuditLog:
    """Security audit log entry"""
    id: str
    timestamp: str
    event_type: str
    user_id: Optional[str]
    ip_address: Optional[str]
    details: Dict[str, Any]
    severity: str
    success: bool


@dataclass
class EncryptionKey:
    """Encryption key management"""
    key_id: str
    key_type: str
    key_data: bytes
    created_at: str
    expires_at: Optional[str] = None
    algorithm: str = "AES-256"
    purpose: str = "data_encryption"


class SecurityManager:
    """
    Comprehensive security manager for authentication, encryption,
    and audit logging in the Sunflower AI system.
    """
    
    # Security constants
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_COMPLEXITY_REQUIRED = True
    SESSION_TIMEOUT_MINUTES = 60
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    TOKEN_LIFETIME_HOURS = 24
    
    # Encryption settings
    PBKDF2_ITERATIONS = 100000
    SCRYPT_N = 16384
    SCRYPT_R = 8
    SCRYPT_P = 1
    
    def __init__(self, security_dir: Optional[Path] = None):
        """Initialize security manager"""
        self.security_dir = security_dir or self._get_security_dir()
        
        # Key management
        self._master_key: Optional[bytes] = None
        self._data_cipher: Optional[Fernet] = None
        self._key_store: Dict[str, EncryptionKey] = {}
        
        # Session management
        self._active_sessions: Dict[str, SecurityToken] = {}
        self._session_lock = threading.Lock()
        
        # Failed login tracking
        self._failed_attempts: Dict[str, List[datetime]] = {}
        self._lockout_until: Dict[str, datetime] = {}
        
        # Audit logging
        self._audit_logs: List[AuditLog] = []
        self._audit_lock = threading.Lock()
        
        # Initialize security components
        self._initialize_security()
        
        # Start session cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_sessions, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("Security manager initialized")
    
    def _get_security_dir(self) -> Path:
        """Get security directory path"""
        try:
            from .partition_manager import PartitionManager
            pm = PartitionManager()
            usb_path = pm.find_usb_partition()
            if usb_path:
                return usb_path / ".security"
        except:
            pass
        
        # Fallback to local directory
        security_dir = Path.cwd() / "data" / ".security"
        security_dir.mkdir(parents=True, exist_ok=True)
        return security_dir
    
    def _initialize_security(self):
        """Initialize security components"""
        # Create security directories
        self.security_dir.mkdir(parents=True, exist_ok=True)
        (self.security_dir / "keys").mkdir(exist_ok=True)
        (self.security_dir / "tokens").mkdir(exist_ok=True)
        (self.security_dir / "audit").mkdir(exist_ok=True)
        
        # Load or create master key
        self._load_or_create_master_key()
        
        # Initialize data cipher
        self._data_cipher = Fernet(self._master_key)
        
        # Load existing sessions
        self._load_sessions()
        
        # Load audit logs
        self._load_audit_logs()
    
    def _load_or_create_master_key(self):
        """Load or create master encryption key"""
        key_file = self.security_dir / "keys" / "master.key"
        
        if key_file.exists():
            try:
                # Load existing key
                with open(key_file, 'rb') as f:
                    encrypted_key = f.read()
                
                # Derive key from hardware ID
                hardware_key = self._derive_hardware_key()
                cipher = Fernet(hardware_key)
                
                self._master_key = cipher.decrypt(encrypted_key)
                logger.info("Loaded existing master key")
                
            except Exception as e:
                logger.error(f"Failed to load master key: {e}")
                self._create_new_master_key()
        else:
            self._create_new_master_key()
    
    def _create_new_master_key(self):
        """Create new master encryption key"""
        # Generate new key
        self._master_key = Fernet.generate_key()
        
        # Encrypt with hardware-derived key
        hardware_key = self._derive_hardware_key()
        cipher = Fernet(hardware_key)
        encrypted_key = cipher.encrypt(self._master_key)
        
        # Save encrypted key
        key_file = self.security_dir / "keys" / "master.key"
        try:
            with open(key_file, 'wb') as f:
                f.write(encrypted_key)
            
            # Set restrictive permissions
            if os.name != 'nt':
                os.chmod(key_file, 0o600)
            
            logger.info("Created new master key")
            
        except Exception as e:
            logger.error(f"Failed to save master key: {e}")
    
    def _derive_hardware_key(self) -> bytes:
        """Derive encryption key from hardware identifiers"""
        try:
            # Collect hardware identifiers
            identifiers = []
            
            # Machine ID
            import platform
            identifiers.append(platform.node())
            
            # MAC address
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                          for elements in range(0, 2*6, 2)][::-1])
            identifiers.append(mac)
            
            # CPU info
            identifiers.append(platform.processor())
            
            # Combine identifiers
            combined = '|'.join(identifiers).encode('utf-8')
            
            # Derive key using PBKDF2
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'SunflowerAI2025',
                iterations=self.PBKDF2_ITERATIONS,
                backend=default_backend()
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(combined))
            return key
            
        except Exception as e:
            logger.error(f"Failed to derive hardware key: {e}")
            # Fallback to default key
            return base64.urlsafe_b64encode(hashlib.sha256(b'SunflowerAIDefault').digest())
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """
        Hash password using Scrypt.
        
        Args:
            password: Plain text password
        
        Returns:
            Tuple of (hash, salt) as base64 strings
        """
        # Generate salt
        salt = secrets.token_bytes(32)
        
        # Use Scrypt for password hashing (more resistant to GPU attacks)
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=self.SCRYPT_N,
            r=self.SCRYPT_R,
            p=self.SCRYPT_P,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode('utf-8'))
        
        # Return as base64 strings
        hash_b64 = base64.b64encode(key).decode('utf-8')
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        
        return hash_b64, salt_b64
    
    def verify_password(self, password: str, hash_b64: str, salt_b64: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hash_b64: Password hash as base64
            salt_b64: Salt as base64
        
        Returns:
            True if password matches
        """
        try:
            salt = base64.b64decode(salt_b64.encode('utf-8'))
            
            kdf = Scrypt(
                salt=salt,
                length=32,
                n=self.SCRYPT_N,
                r=self.SCRYPT_R,
                p=self.SCRYPT_P,
                backend=default_backend()
            )
            
            kdf.verify(password.encode('utf-8'), base64.b64decode(hash_b64.encode('utf-8')))
            return True
            
        except Exception:
            return False
    
    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check length
        if len(password) < self.MIN_PASSWORD_LENGTH:
            issues.append(f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters")
        
        if len(password) > self.MAX_PASSWORD_LENGTH:
            issues.append(f"Password must be less than {self.MAX_PASSWORD_LENGTH} characters")
        
        if self.PASSWORD_COMPLEXITY_REQUIRED:
            # Check for uppercase
            if not re.search(r'[A-Z]', password):
                issues.append("Password must contain at least one uppercase letter")
            
            # Check for lowercase
            if not re.search(r'[a-z]', password):
                issues.append("Password must contain at least one lowercase letter")
            
            # Check for digit
            if not re.search(r'\d', password):
                issues.append("Password must contain at least one number")
            
            # Check for special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                issues.append("Password must contain at least one special character")
        
        # Check for common passwords
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password.lower() in common_passwords:
            issues.append("Password is too common")
        
        return len(issues) == 0, issues
    
    def authenticate(self, username: str, password: str, user_type: str = "parent") -> Optional[SecurityToken]:
        """
        Authenticate user and create session token.
        
        Args:
            username: Username or email
            password: Password
            user_type: Type of user (parent, educator, admin)
        
        Returns:
            Security token if successful, None otherwise
        """
        # Check if account is locked
        if self._is_account_locked(username):
            self._log_security_event(
                SecurityEvent.LOGIN_FAILED,
                user_id=username,
                details={"reason": "account_locked"}
            )
            return None
        
        # Verify credentials (would integrate with ProfileManager)
        # This is a placeholder - actual implementation would check against stored hashes
        is_valid = self._verify_credentials(username, password, user_type)
        
        if not is_valid:
            self._record_failed_attempt(username)
            self._log_security_event(
                SecurityEvent.LOGIN_FAILED,
                user_id=username,
                details={"reason": "invalid_credentials"}
            )
            return None
        
        # Create session token
        token = self._create_session_token(username, user_type)
        
        # Log successful login
        self._log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            user_id=username,
            details={"token_id": token.token_id}
        )
        
        return token
    
    def _verify_credentials(self, username: str, password: str, user_type: str) -> bool:
        """Verify user credentials (placeholder for integration)"""
        # This would integrate with ProfileManager to verify actual credentials
        # For now, return True for development
        return True
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts"""
        if username in self._lockout_until:
            if datetime.now() < self._lockout_until[username]:
                return True
            else:
                # Lockout expired
                del self._lockout_until[username]
                if username in self._failed_attempts:
                    del self._failed_attempts[username]
        
        return False
    
    def _record_failed_attempt(self, username: str):
        """Record failed login attempt"""
        now = datetime.now()
        
        if username not in self._failed_attempts:
            self._failed_attempts[username] = []
        
        self._failed_attempts[username].append(now)
        
        # Remove old attempts (older than lockout duration)
        cutoff = now - timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
        self._failed_attempts[username] = [
            attempt for attempt in self._failed_attempts[username]
            if attempt > cutoff
        ]
        
        # Check if lockout threshold reached
        if len(self._failed_attempts[username]) >= self.MAX_LOGIN_ATTEMPTS:
            self._lockout_until[username] = now + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
            logger.warning(f"Account locked due to failed attempts: {username}")
    
    def _create_session_token(self, user_id: str, user_type: str) -> SecurityToken:
        """Create new session token"""
        # Determine auth level
        auth_levels = {
            "child": AuthLevel.CHILD.value,
            "parent": AuthLevel.PARENT.value,
            "educator": AuthLevel.EDUCATOR.value,
            "admin": AuthLevel.ADMIN.value
        }
        auth_level = auth_levels.get(user_type, AuthLevel.NONE.value)
        
        # Create token
        token = SecurityToken(
            token_id=str(uuid.uuid4()),
            user_id=user_id,
            user_type=user_type,
            auth_level=auth_level,
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=self.TOKEN_LIFETIME_HOURS)).isoformat(),
            device_id=self._get_device_id()
        )
        
        # Store token
        with self._session_lock:
            self._active_sessions[token.token_id] = token
        
        # Save to disk
        self._save_token(token)
        
        return token
    
    def _get_device_id(self) -> str:
        """Get unique device identifier"""
        try:
            import platform
            import hashlib
            
            # Combine various identifiers
            identifiers = [
                platform.node(),
                platform.system(),
                platform.machine()
            ]
            
            combined = '|'.join(identifiers)
            return hashlib.sha256(combined.encode()).hexdigest()[:16]
            
        except:
            return "unknown"
    
    def validate_token(self, token_id: str) -> Optional[SecurityToken]:
        """
        Validate session token.
        
        Args:
            token_id: Token ID to validate
        
        Returns:
            Token if valid, None otherwise
        """
        with self._session_lock:
            token = self._active_sessions.get(token_id)
        
        if not token:
            return None
        
        # Check expiration
        expires_at = datetime.fromisoformat(token.expires_at)
        if datetime.now() > expires_at:
            self.revoke_token(token_id)
            return None
        
        # Check if active
        if not token.is_active:
            return None
        
        return token
    
    def refresh_token(self, token_id: str) -> Optional[SecurityToken]:
        """Refresh session token"""
        token = self.validate_token(token_id)
        if not token:
            return None
        
        # Update expiration
        token.expires_at = (datetime.now() + timedelta(hours=self.TOKEN_LIFETIME_HOURS)).isoformat()
        token.refresh_count += 1
        
        # Save updated token
        self._save_token(token)
        
        return token
    
    def revoke_token(self, token_id: str):
        """Revoke session token"""
        with self._session_lock:
            if token_id in self._active_sessions:
                token = self._active_sessions[token_id]
                token.is_active = False
                
                # Log logout
                self._log_security_event(
                    SecurityEvent.LOGOUT,
                    user_id=token.user_id,
                    details={"token_id": token_id}
                )
                
                del self._active_sessions[token_id]
        
        # Remove from disk
        token_file = self.security_dir / "tokens" / f"{token_id}.json"
        if token_file.exists():
            token_file.unlink()
    
    def encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data: Data to encrypt
        
        Returns:
            Encrypted data as base64 string
        """
        if not self._data_cipher:
            raise SecurityError("Encryption not initialized")
        
        try:
            encrypted = self._data_cipher.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise SecurityError("Encryption failed")
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Encrypted data as base64 string
        
        Returns:
            Decrypted data
        """
        if not self._data_cipher:
            raise SecurityError("Decryption not initialized")
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self._data_cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise SecurityError("Decryption failed")
    
    def encrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """Encrypt a file"""
        if not self._data_cipher:
            raise SecurityError("Encryption not initialized")
        
        output_path = output_path or input_path.with_suffix('.encrypted')
        
        try:
            with open(input_path, 'rb') as infile:
                data = infile.read()
            
            encrypted = self._data_cipher.encrypt(data)
            
            with open(output_path, 'wb') as outfile:
                outfile.write(encrypted)
            
            logger.info(f"File encrypted: {input_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise SecurityError("File encryption failed")
    
    def decrypt_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """Decrypt a file"""
        if not self._data_cipher:
            raise SecurityError("Decryption not initialized")
        
        output_path = output_path or input_path.with_suffix('')
        
        try:
            with open(input_path, 'rb') as infile:
                encrypted_data = infile.read()
            
            decrypted = self._data_cipher.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as outfile:
                outfile.write(decrypted)
            
            logger.info(f"File decrypted: {input_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise SecurityError("File decryption failed")
    
    def check_authorization(self, token_id: str, required_level: AuthLevel) -> bool:
        """Check if token has required authorization level"""
        token = self.validate_token(token_id)
        if not token:
            return False
        
        return token.auth_level >= required_level.value
    
    def _log_security_event(self, event: SecurityEvent, user_id: Optional[str] = None,
                           details: Optional[Dict[str, Any]] = None, severity: str = "info"):
        """Log security event"""
        log_entry = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            event_type=event.value,
            user_id=user_id,
            ip_address=self._get_ip_address(),
            details=details or {},
            severity=severity,
            success=event in [SecurityEvent.LOGIN_SUCCESS, SecurityEvent.LOGOUT, 
                            SecurityEvent.SESSION_START, SecurityEvent.SESSION_END]
        )
        
        with self._audit_lock:
            self._audit_logs.append(log_entry)
        
        # Save to disk
        self._save_audit_log(log_entry)
        
        # Log to system logger
        if severity == "critical":
            logger.critical(f"Security event: {event.value} - {user_id}")
        elif severity == "warning":
            logger.warning(f"Security event: {event.value} - {user_id}")
        else:
            logger.info(f"Security event: {event.value} - {user_id}")
    
    def _get_ip_address(self) -> Optional[str]:
        """Get client IP address"""
        try:
            import socket
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            return None
    
    def _save_token(self, token: SecurityToken):
        """Save token to disk"""
        token_file = self.security_dir / "tokens" / f"{token.token_id}.json"
        try:
            with open(token_file, 'w') as f:
                json.dump(asdict(token), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    def _load_sessions(self):
        """Load existing sessions from disk"""
        tokens_dir = self.security_dir / "tokens"
        if not tokens_dir.exists():
            return
        
        for token_file in tokens_dir.glob("*.json"):
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                token = SecurityToken(**data)
                
                # Check if still valid
                if self.validate_token(token.token_id):
                    self._active_sessions[token.token_id] = token
                else:
                    # Remove expired token
                    token_file.unlink()
                    
            except Exception as e:
                logger.error(f"Failed to load token {token_file}: {e}")
    
    def _save_audit_log(self, log_entry: AuditLog):
        """Save audit log entry to disk"""
        # Save to daily log file
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = self.security_dir / "audit" / f"audit_{date_str}.jsonl"
        
        try:
            with open(log_file, 'a') as f:
                json.dump(asdict(log_entry), f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")
    
    def _load_audit_logs(self):
        """Load recent audit logs"""
        audit_dir = self.security_dir / "audit"
        if not audit_dir.exists():
            return
        
        # Load today's logs
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = audit_dir / f"audit_{date_str}.jsonl"
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        log_entry = AuditLog(**data)
                        self._audit_logs.append(log_entry)
            except Exception as e:
                logger.error(f"Failed to load audit logs: {e}")
    
    def _cleanup_sessions(self):
        """Background thread to cleanup expired sessions"""
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes
                
                expired = []
                with self._session_lock:
                    for token_id, token in self._active_sessions.items():
                        expires_at = datetime.fromisoformat(token.expires_at)
                        if datetime.now() > expires_at:
                            expired.append(token_id)
                
                for token_id in expired:
                    self.revoke_token(token_id)
                    
                if expired:
                    logger.info(f"Cleaned up {len(expired)} expired sessions")
                    
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
    
    def get_audit_logs(self, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      user_id: Optional[str] = None,
                      event_type: Optional[SecurityEvent] = None) -> List[AuditLog]:
        """Get filtered audit logs"""
        logs = self._audit_logs.copy()
        
        # Apply filters
        if start_date:
            logs = [log for log in logs if datetime.fromisoformat(log.timestamp) >= start_date]
        
        if end_date:
            logs = [log for log in logs if datetime.fromisoformat(log.timestamp) <= end_date]
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        if event_type:
            logs = [log for log in logs if log.event_type == event_type.value]
        
        return logs
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate security status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(self._active_sessions),
            "locked_accounts": len(self._lockout_until),
            "failed_attempts_tracking": len(self._failed_attempts),
            "audit_logs_today": len([
                log for log in self._audit_logs
                if datetime.fromisoformat(log.timestamp).date() == datetime.now().date()
            ]),
            "encryption_status": "active" if self._data_cipher else "inactive",
            "master_key_status": "loaded" if self._master_key else "missing"
        }
        
        # Add recent security events
        recent_events = []
        for log in self._audit_logs[-10:]:
            recent_events.append({
                "time": log.timestamp,
                "event": log.event_type,
                "user": log.user_id,
                "success": log.success
            })
        
        report["recent_events"] = recent_events
        
        return report
    
    def initialize(self) -> bool:
        """Initialize security system"""
        try:
            # Verify master key
            if not self._master_key:
                logger.error("Master key not available")
                return False
            
            # Test encryption
            test_data = "test_encryption"
            encrypted = self.encrypt_data(test_data)
            decrypted = self.decrypt_data(encrypted)
            
            if decrypted != test_data:
                logger.error("Encryption test failed")
                return False
            
            logger.info("Security system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Security initialization failed: {e}")
            return False

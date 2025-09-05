#!/usr/bin/env python3
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
import sqlite3
from contextlib import contextmanager

# Cryptography imports
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_EXPORT = "data_export"
    SETTINGS_CHANGE = "settings_change"


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
    last_activity: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires
    
    def is_valid(self) -> bool:
        """Check if token is valid"""
        return self.is_active and not self.is_expired()


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


class SecurityError(Exception):
    """Security-related exception"""
    pass


class SecurityManager:
    """
    Comprehensive security manager for authentication, encryption,
    and audit logging in the Sunflower AI system.
    """
    
    # Security constants
    TOKEN_EXPIRY_HOURS = 2
    SESSION_TIMEOUT_MINUTES = 60
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    MIN_PASSWORD_LENGTH = 8
    SALT_LENGTH = 32
    KEY_ITERATIONS = 100000
    
    def __init__(self, usb_path: Path):
        """Initialize security manager"""
        self.usb_path = Path(usb_path)
        
        # Security paths
        self.security_dir = self.usb_path / ".security"
        self.keys_dir = self.security_dir / "keys"
        self.audit_dir = self.security_dir / "audit"
        self.db_path = self.security_dir / "security.db"
        
        # Create directories
        self.security_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.keys_dir.mkdir(exist_ok=True, mode=0o700)
        self.audit_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Initialize database
        self._init_database()
        
        # Encryption
        self._master_key = self._load_or_create_master_key()
        self._data_cipher = Fernet(self._master_key)
        
        # Session management
        self._active_sessions: Dict[str, SecurityToken] = {}
        self._session_lock = threading.RLock()
        
        # Failed login tracking
        self._failed_attempts: Dict[str, int] = {}
        self._lockout_until: Dict[str, datetime] = {}
        
        # Audit logging
        self._audit_logs: List[AuditLog] = []
        self._audit_lock = threading.Lock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        logger.info("Security manager initialized")
    
    def _init_database(self):
        """Initialize security database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    auth_level INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TEXT,
                    two_factor_secret TEXT,
                    security_questions TEXT
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT,
                    ip_address TEXT,
                    device_id TEXT,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Audit logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    details TEXT,
                    severity TEXT,
                    success INTEGER
                )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_username ON users (username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_token ON sessions (token_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs (timestamp)")
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _load_or_create_master_key(self) -> bytes:
        """Load or create master encryption key"""
        key_file = self.keys_dir / "master.key"
        
        if key_file.exists():
            # Load existing key
            try:
                with open(key_file, 'rb') as f:
                    key_data = f.read()
                
                # Validate key
                if len(key_data) == 44:  # Base64-encoded 32-byte key
                    logger.info("Loaded existing master key")
                    return key_data
                else:
                    logger.error("Invalid master key format")
                    raise SecurityError("Invalid master key")
                    
            except Exception as e:
                logger.error(f"Failed to load master key: {e}")
                raise SecurityError("Failed to load master key")
        else:
            # Generate new key
            key = Fernet.generate_key()
            
            # Save key with restricted permissions
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Set file permissions (Unix-like systems)
            if os.name != 'nt':
                os.chmod(key_file, 0o600)
            
            logger.info("Generated new master key")
            return key
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup():
            while True:
                try:
                    self._cleanup_expired_sessions()
                    self._cleanup_old_logs()
                    time.sleep(3600)  # Run hourly
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
        
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with self._session_lock:
            expired = []
            for token_id, token in self._active_sessions.items():
                if token.is_expired():
                    expired.append(token_id)
            
            for token_id in expired:
                del self._active_sessions[token_id]
                self._log_security_event(
                    SecurityEvent.SESSION_END,
                    user_id=self._active_sessions.get(token_id, SecurityToken).user_id,
                    details={"reason": "expired"}
                )
        
        # Clean database
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions 
                SET is_active = 0 
                WHERE expires_at < ? AND is_active = 1
            """, (datetime.now().isoformat(),))
            conn.commit()
    
    def _cleanup_old_logs(self):
        """Clean up old audit logs"""
        # Keep logs for 90 days
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_logs WHERE timestamp < ?", (cutoff,))
            conn.commit()
    
    def create_user(self, username: str, password: str, auth_level: AuthLevel) -> str:
        """Create new user account"""
        # Validate password
        if not self._validate_password(password):
            raise SecurityError("Password does not meet requirements")
        
        # Generate salt and hash
        salt = secrets.token_hex(self.SALT_LENGTH)
        password_hash = self._hash_password(password, salt)
        
        user_id = str(uuid.uuid4())
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                raise SecurityError("Username already exists")
            
            # Create user
            cursor.execute("""
                INSERT INTO users (
                    id, username, password_hash, salt, auth_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, username, password_hash, salt,
                auth_level.value, datetime.now().isoformat()
            ))
            
            conn.commit()
        
        self._log_security_event(
            SecurityEvent.PROFILE_ACCESS,
            user_id=user_id,
            details={"action": "user_created", "auth_level": auth_level.value}
        )
        
        logger.info(f"Created user: {username} (level: {auth_level.value})")
        return user_id
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return token"""
        # Check lockout
        if username in self._lockout_until:
            if datetime.now() < self._lockout_until[username]:
                remaining = (self._lockout_until[username] - datetime.now()).seconds // 60
                self._log_security_event(
                    SecurityEvent.LOGIN_FAILED,
                    details={"username": username, "reason": "account_locked"}
                )
                raise SecurityError(f"Account locked for {remaining} minutes")
            else:
                del self._lockout_until[username]
                self._failed_attempts[username] = 0
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, password_hash, salt, auth_level, is_active
                FROM users WHERE username = ?
            """, (username,))
            
            user = cursor.fetchone()
            
            if not user:
                self._record_failed_login(username)
                raise SecurityError("Invalid credentials")
            
            if not user['is_active']:
                raise SecurityError("Account disabled")
            
            # Verify password
            if not self._verify_password(password, user['salt'], user['password_hash']):
                self._record_failed_login(username)
                raise SecurityError("Invalid credentials")
            
            # Create session token
            token = self.create_session(
                user['id'],
                AuthLevel(user['auth_level'])
            )
            
            # Update last login
            cursor.execute("""
                UPDATE users 
                SET last_login = ?, failed_attempts = 0
                WHERE id = ?
            """, (datetime.now().isoformat(), user['id']))
            
            conn.commit()
        
        # Reset failed attempts
        self._failed_attempts[username] = 0
        
        self._log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            user_id=user['id'],
            details={"username": username}
        )
        
        return token
    
    def _validate_password(self, password: str) -> bool:
        """Validate password requirements"""
        if len(password) < self.MIN_PASSWORD_LENGTH:
            return False
        
        # Must contain at least one of each
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        return has_upper and has_lower and has_digit and has_special
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=self.KEY_ITERATIONS,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode())
        return base64.b64encode(key).decode()
    
    def _verify_password(self, password: str, salt: str, hash: str) -> bool:
        """Verify password against hash"""
        try:
            calculated_hash = self._hash_password(password, salt)
            return hmac.compare_digest(calculated_hash, hash)
        except Exception:
            return False
    
    def _record_failed_login(self, username: str):
        """Record failed login attempt"""
        if username not in self._failed_attempts:
            self._failed_attempts[username] = 0
        
        self._failed_attempts[username] += 1
        
        if self._failed_attempts[username] >= self.MAX_LOGIN_ATTEMPTS:
            self._lockout_until[username] = datetime.now() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
            
            self._log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,
                details={"username": username, "action": "account_locked"},
                severity="warning"
            )
            
            logger.warning(f"Account locked: {username}")
        
        self._log_security_event(
            SecurityEvent.LOGIN_FAILED,
            details={"username": username, "attempts": self._failed_attempts[username]}
        )
    
    def create_session(self, user_id: str, auth_level: AuthLevel) -> str:
        """Create new session token"""
        token_id = secrets.token_urlsafe(32)
        
        token = SecurityToken(
            token_id=token_id,
            user_id=user_id,
            user_type=auth_level.name,
            auth_level=auth_level.value,
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=self.TOKEN_EXPIRY_HOURS)).isoformat(),
            ip_address=self._get_ip_address(),
            device_id=self._get_device_id()
        )
        
        # Store in memory
        with self._session_lock:
            self._active_sessions[token_id] = token
        
        # Store in database
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (
                    token_id, user_id, created_at, expires_at,
                    ip_address, device_id, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                token_id, user_id, token.created_at, token.expires_at,
                token.ip_address, token.device_id, 1
            ))
            conn.commit()
        
        self._log_security_event(
            SecurityEvent.SESSION_START,
            user_id=user_id,
            details={"token_id": token_id[:8] + "..."}
        )
        
        return token_id
    
    def validate_token(self, token_id: str) -> Optional[SecurityToken]:
        """Validate session token"""
        with self._session_lock:
            # Check memory cache
            if token_id in self._active_sessions:
                token = self._active_sessions[token_id]
                if token.is_valid():
                    # Update last activity
                    token.last_activity = datetime.now().isoformat()
                    return token
                else:
                    del self._active_sessions[token_id]
        
        # Check database
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE token_id = ? AND is_active = 1
            """, (token_id,))
            
            row = cursor.fetchone()
            if row:
                token = SecurityToken(
                    token_id=row['token_id'],
                    user_id=row['user_id'],
                    user_type="",  # Would need to join with users table
                    auth_level=0,  # Would need to join with users table
                    created_at=row['created_at'],
                    expires_at=row['expires_at'],
                    ip_address=row['ip_address'],
                    device_id=row['device_id'],
                    last_activity=row['last_activity']
                )
                
                if token.is_valid():
                    # Cache in memory
                    with self._session_lock:
                        self._active_sessions[token_id] = token
                    
                    # Update last activity
                    cursor.execute("""
                        UPDATE sessions 
                        SET last_activity = ?
                        WHERE token_id = ?
                    """, (datetime.now().isoformat(), token_id))
                    conn.commit()
                    
                    return token
        
        return None
    
    def revoke_token(self, token_id: str):
        """Revoke session token"""
        # Remove from memory
        with self._session_lock:
            if token_id in self._active_sessions:
                user_id = self._active_sessions[token_id].user_id
                del self._active_sessions[token_id]
            else:
                user_id = None
        
        # Update database
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions 
                SET is_active = 0 
                WHERE token_id = ?
            """, (token_id,))
            conn.commit()
        
        self._log_security_event(
            SecurityEvent.LOGOUT,
            user_id=user_id,
            details={"token_id": token_id[:8] + "..."}
        )
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted = self._data_cipher.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise SecurityError("Encryption failed")
    
    def decrypt_data(self, encrypted: str) -> str:
        """Decrypt sensitive data"""
        try:
            decoded = base64.b64decode(encrypted.encode())
            decrypted = self._data_cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise SecurityError("Decryption failed")
    
    def encrypt_file(self, input_path: Path, output_path: Path):
        """Encrypt a file"""
        try:
            with open(input_path, 'rb') as f:
                data = f.read()
            
            encrypted = self._data_cipher.encrypt(data)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted)
            
            logger.info(f"File encrypted: {input_path} -> {output_path}")
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise SecurityError("File encryption failed")
    
    def decrypt_file(self, input_path: Path, output_path: Path):
        """Decrypt a file"""
        try:
            with open(input_path, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self._data_cipher.decrypt(encrypted)
            
            with open(output_path, 'wb') as f:
                f.write(decrypted)
            
            logger.info(f"File decrypted: {input_path} -> {output_path}")
            
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise SecurityError("File decryption failed")
    
    def check_authorization(self, token_id: str, required_level: AuthLevel) -> bool:
        """Check if token has required authorization level"""
        token = self.validate_token(token_id)
        if not token:
            return False
        
        return token.auth_level >= required_level.value
    
    def change_password(self, user_id: str, old_password: str, new_password: str):
        """Change user password"""
        # Validate new password
        if not self._validate_password(new_password):
            raise SecurityError("New password does not meet requirements")
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current password
            cursor.execute("""
                SELECT password_hash, salt FROM users WHERE id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                raise SecurityError("User not found")
            
            # Verify old password
            if not self._verify_password(old_password, user['salt'], user['password_hash']):
                raise SecurityError("Current password is incorrect")
            
            # Generate new salt and hash
            new_salt = secrets.token_hex(self.SALT_LENGTH)
            new_hash = self._hash_password(new_password, new_salt)
            
            # Update password
            cursor.execute("""
                UPDATE users 
                SET password_hash = ?, salt = ?
                WHERE id = ?
            """, (new_hash, new_salt, user_id))
            
            conn.commit()
        
        self._log_security_event(
            SecurityEvent.PASSWORD_CHANGE,
            user_id=user_id,
            details={"success": True}
        )
        
        logger.info(f"Password changed for user: {user_id}")
    
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
        
        # Store in memory
        with self._audit_lock:
            self._audit_logs.append(log_entry)
            # Keep only last 1000 logs in memory
            if len(self._audit_logs) > 1000:
                self._audit_logs = self._audit_logs[-1000:]
        
        # Save to database
        self._save_audit_log(log_entry)
        
        # Log to system logger
        if severity == "critical":
            logger.critical(f"Security event: {event.value} - {user_id}")
        elif severity == "warning":
            logger.warning(f"Security event: {event.value} - {user_id}")
        else:
            logger.info(f"Security event: {event.value} - {user_id}")
    
    def _save_audit_log(self, log_entry: AuditLog):
        """Save audit log to database"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs (
                        id, timestamp, event_type, user_id,
                        ip_address, details, severity, success
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry.id,
                    log_entry.timestamp,
                    log_entry.event_type,
                    log_entry.user_id,
                    log_entry.ip_address,
                    json.dumps(log_entry.details),
                    log_entry.severity,
                    int(log_entry.success)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")
    
    def _get_ip_address(self) -> Optional[str]:
        """Get client IP address"""
        try:
            import socket
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            return None
    
    def _get_device_id(self) -> str:
        """Get device identifier"""
        try:
            import platform
            return hashlib.sha256(
                f"{platform.node()}{platform.machine()}".encode()
            ).hexdigest()[:16]
        except:
            return "unknown"
    
    def get_audit_logs(self, user_id: Optional[str] = None, 
                      event_type: Optional[SecurityEvent] = None,
                      limit: int = 100) -> List[AuditLog]:
        """Get audit logs"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            logs = []
            for row in cursor.fetchall():
                logs.append(AuditLog(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    event_type=row['event_type'],
                    user_id=row['user_id'],
                    ip_address=row['ip_address'],
                    details=json.loads(row['details'] or '{}'),
                    severity=row['severity'],
                    success=bool(row['success'])
                ))
            
            return logs
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate security status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(self._active_sessions),
            "locked_accounts": len(self._lockout_until),
            "failed_attempts_tracking": len(self._failed_attempts),
            "encryption_status": "active" if self._data_cipher else "inactive",
            "master_key_status": "loaded" if self._master_key else "missing"
        }
        
        # Add statistics
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            report["total_users"] = cursor.fetchone()[0]
            
            # Active sessions in database
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
            report["db_active_sessions"] = cursor.fetchone()[0]
            
            # Recent security events
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM audit_logs
                WHERE timestamp > ?
                GROUP BY event_type
            """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
            
            events = {}
            for row in cursor.fetchall():
                events[row[0]] = row[1]
            
            report["recent_events"] = events
        
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
    
    def shutdown(self):
        """Shutdown security manager"""
        # Clear active sessions
        with self._session_lock:
            self._active_sessions.clear()
        
        # Final log
        self._log_security_event(
            SecurityEvent.LOGOUT,
            details={"action": "system_shutdown"}
        )
        
        logger.info("Security manager shutdown complete")


# Testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create security manager
        security = SecurityManager(Path(tmpdir))
        
        # Initialize
        if security.initialize():
            print("✓ Security system initialized")
        
        # Create test user
        try:
            user_id = security.create_user(
                "test_parent",
                "SecureP@ssw0rd!",
                AuthLevel.PARENT
            )
            print(f"✓ Created user: {user_id}")
        except SecurityError as e:
            print(f"✗ Failed to create user: {e}")
        
        # Test authentication
        try:
            token = security.authenticate("test_parent", "SecureP@ssw0rd!")
            print(f"✓ Authentication successful: {token[:8]}...")
        except SecurityError as e:
            print(f"✗ Authentication failed: {e}")
        
        # Test encryption
        test_data = "Sensitive information"
        encrypted = security.encrypt_data(test_data)
        decrypted = security.decrypt_data(encrypted)
        
        if decrypted == test_data:
            print("✓ Encryption/Decryption successful")
        else:
            print("✗ Encryption/Decryption failed")
        
        # Generate report
        report = security.generate_security_report()
        print(f"\nSecurity Report:")
        print(f"  Active sessions: {report['active_sessions']}")
        print(f"  Total users: {report['total_users']}")
        print(f"  Encryption: {report['encryption_status']}")
        
        # Shutdown
        security.shutdown()
        print("✓ Security system shutdown")

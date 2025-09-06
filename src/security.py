#!/usr/bin/env python3
"""
Sunflower AI Professional System - Security Module
Enhanced with thread safety, proper resource management, timeouts, and retry logic
Version: 6.2.0 - Production Ready
"""

import os
import sys
import json
import hashlib
import secrets
import logging
import threading
import time
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from enum import Enum
from contextlib import contextmanager
import base64

logger = logging.getLogger(__name__)

# Configuration constants with timeout values
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds
DB_TIMEOUT = 30  # seconds for database operations
SESSION_TIMEOUT = 3600  # 1 hour


class SecurityLevel(Enum):
    """Security levels for the system"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


class SecurityEvent(Enum):
    """Security event types for logging"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PROFILE_ACCESS = "profile_access"
    PROFILE_DENIED = "profile_denied"
    ENCRYPTION = "encryption"
    DECRYPTION = "decryption"
    VIOLATION = "violation"
    LOCKOUT = "lockout"


@dataclass
class SessionToken:
    """Session token with metadata"""
    token_id: str
    user_id: str
    profile_type: str  # 'parent' or 'child'
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityManager:
    """
    Enhanced security manager with thread safety and resource management
    """
    
    def __init__(self, usb_path: Optional[Path] = None):
        """Initialize security manager with thread safety"""
        self.usb_path = Path(usb_path) if usb_path else Path.home() / ".sunflower"
        self.security_path = self.usb_path / "security"
        self.security_path.mkdir(parents=True, exist_ok=True)
        
        # Thread safety locks
        self._session_lock = threading.RLock()
        self._db_lock = threading.RLock()
        self._cipher_lock = threading.RLock()
        
        # Initialize components
        self._master_key = self._load_or_generate_master_key()
        self._data_cipher = self._create_cipher(self._master_key)
        
        # Session management with thread-safe dictionary
        self._active_sessions = {}  # Protected by _session_lock
        
        # Failed login tracking with thread safety
        self._failed_attempts = {}  # Protected by _session_lock
        self._lockout_until = {}    # Protected by _session_lock
        
        # Initialize database
        self.db_path = self.security_path / "security.db"
        self._init_database()
        
        # Start session cleanup thread
        self._cleanup_thread = threading.Thread(target=self._session_cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("Security manager initialized with enhanced safety features")
    
    @contextmanager
    def _get_db_connection(self):
        """Thread-safe database connection context manager"""
        conn = None
        try:
            with self._db_lock:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=DB_TIMEOUT,
                    isolation_level='IMMEDIATE'
                )
                conn.row_factory = sqlite3.Row
                yield conn
                conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Initialize security database with proper resource management"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    lockout_until TEXT,
                    failed_attempts INTEGER DEFAULT 0
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Security events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    severity TEXT,
                    ip_address TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON security_events(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON security_events(event_type)")
    
    def _load_or_generate_master_key(self) -> bytes:
        """Load or generate master encryption key with proper file handling"""
        key_file = self.security_path / ".master.key"
        
        try:
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Generate new master key
                key = Fernet.generate_key()
                
                # Write with proper permissions
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                # Set restrictive permissions (Unix-like systems)
                if hasattr(os, 'chmod'):
                    os.chmod(key_file, 0o600)
                
                return key
                
        except IOError as e:
            logger.error(f"Failed to handle master key file: {e}")
            raise SecurityError("Failed to initialize encryption")
    
    def _create_cipher(self, key: bytes) -> Fernet:
        """Create cipher instance with thread safety"""
        return Fernet(key)
    
    def _retry_operation(self, operation, *args, **kwargs):
        """Execute operation with retry logic"""
        last_exception = None
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    logger.warning(f"Retrying operation {operation.__name__} (attempt {attempt + 2})")
                else:
                    logger.error(f"Operation {operation.__name__} failed after {MAX_RETRY_ATTEMPTS} attempts")
        
        raise last_exception
    
    def authenticate_parent(self, username: str, password: str) -> Optional[str]:
        """Authenticate parent with retry logic and lockout protection"""
        with self._session_lock:
            # Check lockout
            if username in self._lockout_until:
                lockout_time = self._lockout_until[username]
                if datetime.now() < lockout_time:
                    remaining = (lockout_time - datetime.now()).seconds
                    logger.warning(f"Account {username} is locked out for {remaining} seconds")
                    return None
                else:
                    # Clear lockout
                    del self._lockout_until[username]
                    if username in self._failed_attempts:
                        del self._failed_attempts[username]
        
        # Perform authentication with retry
        try:
            result = self._retry_operation(self._do_authenticate, username, password)
            
            if result:
                # Clear failed attempts on success
                with self._session_lock:
                    if username in self._failed_attempts:
                        del self._failed_attempts[username]
                
                # Create session
                token = self.create_session(result['user_id'], 'parent')
                
                # Log successful login
                self._log_security_event(
                    SecurityEvent.LOGIN_SUCCESS,
                    user_id=result['user_id'],
                    details={"username": username}
                )
                
                return token
            else:
                # Track failed attempt
                with self._session_lock:
                    if username not in self._failed_attempts:
                        self._failed_attempts[username] = 0
                    self._failed_attempts[username] += 1
                    
                    # Check for lockout
                    if self._failed_attempts[username] >= 5:
                        self._lockout_until[username] = datetime.now() + timedelta(minutes=30)
                        logger.warning(f"Account {username} locked out due to multiple failed attempts")
                        
                        self._log_security_event(
                            SecurityEvent.LOCKOUT,
                            details={"username": username, "attempts": self._failed_attempts[username]}
                        )
                
                self._log_security_event(
                    SecurityEvent.LOGIN_FAILURE,
                    details={"username": username}
                )
                
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def _do_authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Perform actual authentication check"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, password_hash, salt, role 
                FROM users 
                WHERE username = ? AND is_active = 1
            """, (username,))
            
            user = cursor.fetchone()
            
            if user:
                # Verify password
                stored_hash = user['password_hash']
                salt = user['salt']
                
                # Hash provided password with salt
                kdf = PBKDF2(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt.encode(),
                    iterations=100000,
                    backend=default_backend()
                )
                
                provided_hash = base64.b64encode(kdf.derive(password.encode())).decode()
                
                # Constant-time comparison
                if secrets.compare_digest(stored_hash, provided_hash):
                    # Update last login
                    cursor.execute("""
                        UPDATE users 
                        SET last_login = ? 
                        WHERE user_id = ?
                    """, (datetime.now().isoformat(), user['user_id']))
                    
                    return dict(user)
        
        return None
    
    def create_session(self, user_id: str, profile_type: str) -> str:
        """Create a new session with thread safety"""
        token_id = secrets.token_urlsafe(32)
        created_at = datetime.now()
        expires_at = created_at + timedelta(seconds=SESSION_TIMEOUT)
        
        session = SessionToken(
            token_id=token_id,
            user_id=user_id,
            profile_type=profile_type,
            created_at=created_at,
            expires_at=expires_at,
            last_activity=created_at
        )
        
        # Store in memory with thread safety
        with self._session_lock:
            self._active_sessions[token_id] = session
        
        # Store in database
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (
                    token_id, user_id, created_at, expires_at, last_activity, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                token_id,
                user_id,
                created_at.isoformat(),
                expires_at.isoformat(),
                created_at.isoformat(),
                json.dumps({"profile_type": profile_type})
            ))
        
        return token_id
    
    def validate_session(self, token_id: str) -> Optional[SessionToken]:
        """Validate session with thread safety"""
        with self._session_lock:
            # Check memory cache first
            if token_id in self._active_sessions:
                session = self._active_sessions[token_id]
                
                # Check expiration
                if datetime.now() > session.expires_at:
                    del self._active_sessions[token_id]
                    return None
                
                # Update last activity
                session.last_activity = datetime.now()
                
                # Update database asynchronously
                threading.Thread(
                    target=self._update_session_activity,
                    args=(token_id,),
                    daemon=True
                ).start()
                
                return session
        
        # Check database if not in memory
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE token_id = ? AND is_active = 1
            """, (token_id,))
            
            row = cursor.fetchone()
            
            if row:
                expires_at = datetime.fromisoformat(row['expires_at'])
                
                if datetime.now() > expires_at:
                    # Session expired
                    cursor.execute("""
                        UPDATE sessions 
                        SET is_active = 0 
                        WHERE token_id = ?
                    """, (token_id,))
                    return None
                
                # Recreate session object
                session = SessionToken(
                    token_id=row['token_id'],
                    user_id=row['user_id'],
                    profile_type=json.loads(row['metadata']).get('profile_type', 'child'),
                    created_at=datetime.fromisoformat(row['created_at']),
                    expires_at=expires_at,
                    last_activity=datetime.now()
                )
                
                # Cache in memory
                with self._session_lock:
                    self._active_sessions[token_id] = session
                
                return session
        
        return None
    
    def _update_session_activity(self, token_id: str):
        """Update session activity in database"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions 
                    SET last_activity = ? 
                    WHERE token_id = ?
                """, (datetime.now().isoformat(), token_id))
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
    
    def _session_cleanup_worker(self):
        """Background worker to clean up expired sessions"""
        while True:
            try:
                time.sleep(60)  # Check every minute
                
                expired_tokens = []
                
                with self._session_lock:
                    for token_id, session in list(self._active_sessions.items()):
                        if datetime.now() > session.expires_at:
                            expired_tokens.append(token_id)
                    
                    # Remove expired sessions
                    for token_id in expired_tokens:
                        del self._active_sessions[token_id]
                
                # Update database
                if expired_tokens:
                    with self._get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.executemany("""
                            UPDATE sessions 
                            SET is_active = 0 
                            WHERE token_id = ?
                        """, [(t,) for t in expired_tokens])
                    
                    logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
                    
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
    
    def revoke_session(self, token_id: str):
        """Revoke a session with thread safety"""
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
        
        self._log_security_event(
            SecurityEvent.LOGOUT,
            user_id=user_id,
            details={"token_id": token_id[:8] + "..."}
        )
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data with thread safety"""
        with self._cipher_lock:
            try:
                encrypted = self._data_cipher.encrypt(data.encode())
                return base64.b64encode(encrypted).decode()
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                raise SecurityError("Encryption failed")
    
    def decrypt_data(self, encrypted: str) -> str:
        """Decrypt data with thread safety"""
        with self._cipher_lock:
            try:
                decoded = base64.b64decode(encrypted.encode())
                decrypted = self._data_cipher.decrypt(decoded)
                return decrypted.decode()
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                raise SecurityError("Decryption failed")
    
    def encrypt_file(self, input_path: Path, output_path: Path):
        """Encrypt file with proper resource management"""
        try:
            with open(input_path, 'rb') as input_file:
                data = input_file.read()
            
            with self._cipher_lock:
                encrypted = self._data_cipher.encrypt(data)
            
            with open(output_path, 'wb') as output_file:
                output_file.write(encrypted)
            
            logger.info(f"File encrypted: {input_path} -> {output_path}")
            
        except IOError as e:
            logger.error(f"File encryption failed: {e}")
            raise SecurityError("File encryption failed")
    
    def decrypt_file(self, input_path: Path, output_path: Path):
        """Decrypt file with proper resource management"""
        try:
            with open(input_path, 'rb') as input_file:
                encrypted = input_file.read()
            
            with self._cipher_lock:
                decrypted = self._data_cipher.decrypt(encrypted)
            
            with open(output_path, 'wb') as output_file:
                output_file.write(decrypted)
            
            logger.info(f"File decrypted: {input_path} -> {output_path}")
            
        except IOError as e:
            logger.error(f"File decryption failed: {e}")
            raise SecurityError("File decryption failed")
    
    def _log_security_event(self, event_type: SecurityEvent, user_id: Optional[str] = None, 
                           details: Optional[Dict] = None):
        """Log security event with proper error handling"""
        try:
            event_id = secrets.token_hex(16)
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO security_events (
                        event_id, event_type, user_id, timestamp, details, severity
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    event_type.value,
                    user_id,
                    datetime.now().isoformat(),
                    json.dumps(details) if details else None,
                    self._get_event_severity(event_type)
                ))
            
            logger.info(f"Security event logged: {event_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def _get_event_severity(self, event_type: SecurityEvent) -> str:
        """Get severity level for security event"""
        severity_map = {
            SecurityEvent.LOGIN_SUCCESS: "info",
            SecurityEvent.LOGIN_FAILURE: "warning",
            SecurityEvent.LOGOUT: "info",
            SecurityEvent.PROFILE_ACCESS: "info",
            SecurityEvent.PROFILE_DENIED: "warning",
            SecurityEvent.ENCRYPTION: "info",
            SecurityEvent.DECRYPTION: "info",
            SecurityEvent.VIOLATION: "critical",
            SecurityEvent.LOCKOUT: "critical"
        }
        
        return severity_map.get(event_type, "info")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        with self._session_lock:
            active_session_count = len(self._active_sessions)
            locked_accounts = len(self._lockout_until)
        
        # Get recent security events
        recent_events = []
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_type, timestamp, severity 
                FROM security_events 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                recent_events.append({
                    'type': row['event_type'],
                    'time': row['timestamp'],
                    'severity': row['severity']
                })
        
        return {
            'active_sessions': active_session_count,
            'locked_accounts': locked_accounts,
            'recent_events': recent_events,
            'encryption_enabled': True,
            'security_level': SecurityLevel.HIGH.value
        }
    
    def create_parent_account(self, username: str, password: str) -> bool:
        """Create a new parent account with proper security"""
        try:
            # Generate salt
            salt = secrets.token_hex(16)
            
            # Hash password with PBKDF2
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
                backend=default_backend()
            )
            
            password_hash = base64.b64encode(kdf.derive(password.encode())).decode()
            
            # Generate user ID
            user_id = secrets.token_hex(16)
            
            # Store in database
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (
                        user_id, username, password_hash, salt, role, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    username,
                    password_hash,
                    salt,
                    'parent',
                    datetime.now().isoformat()
                ))
            
            logger.info(f"Parent account created: {username}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"Account already exists: {username}")
            return False
        except Exception as e:
            logger.error(f"Failed to create parent account: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Security manager shutting down...")
        
        # Clear active sessions
        with self._session_lock:
            self._active_sessions.clear()
        
        # Mark all sessions as inactive in database
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sessions SET is_active = 0")
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")


class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass


# Testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize security manager
        sm = SecurityManager(tmpdir)
        
        # Create parent account
        print("Creating parent account...")
        sm.create_parent_account("parent@family.com", "SecurePassword123!")
        
        # Test authentication
        print("Testing authentication...")
        token = sm.authenticate_parent("parent@family.com", "SecurePassword123!")
        
        if token:
            print(f"✓ Authentication successful: {token[:20]}...")
            
            # Validate session
            session = sm.validate_session(token)
            if session:
                print(f"✓ Session valid for user: {session.user_id}")
            
            # Test encryption
            test_data = "Sensitive family information"
            encrypted = sm.encrypt_data(test_data)
            decrypted = sm.decrypt_data(encrypted)
            
            print(f"✓ Encryption test: {test_data == decrypted}")
            
            # Get security status
            status = sm.get_security_status()
            print(f"✓ Security status: {status}")
            
            # Revoke session
            sm.revoke_session(token)
            print("✓ Session revoked")
        else:
            print("✗ Authentication failed")
        
        # Cleanup
        sm.cleanup()
        print("✓ Security manager cleaned up")

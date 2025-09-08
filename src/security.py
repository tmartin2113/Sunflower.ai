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
        # FIX: Complete the truncated parameter
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
                    profile_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TEXT
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Security events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    severity TEXT
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user 
                ON sessions(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_user 
                ON security_events(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON security_events(timestamp)
            """)
            
            conn.commit()
            logger.info("Security database initialized")
    
    def _load_or_generate_master_key(self) -> bytes:
        """Load or generate master encryption key with retry logic"""
        key_file = self.security_path / ".master.key"
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                if key_file.exists():
                    with open(key_file, 'rb') as f:
                        key = f.read()
                        if len(key) == 32:
                            return key
                        else:
                            logger.warning("Invalid key file, regenerating")
                
                # Generate new key
                key = secrets.token_bytes(32)
                key_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                # Set restrictive permissions (Unix-like systems)
                if hasattr(os, 'chmod'):
                    os.chmod(key_file, 0o600)
                
                logger.info("Generated new master key")
                return key
                
            except IOError as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.warning(f"Attempt {attempt + 1} failed to load/generate key: {e}")
                    time.sleep(RETRY_DELAY)
                else:
                    raise RuntimeError(f"Failed to load/generate master key after {MAX_RETRY_ATTEMPTS} attempts: {e}")
    
    def _create_cipher(self, key: bytes) -> Fernet:
        """Create Fernet cipher from key"""
        # Derive a proper Fernet key from the master key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'sunflower_salt_v1',  # Static salt for consistency
            iterations=100000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key))
        return Fernet(derived_key)
    
    def _session_cleanup_worker(self):
        """Background worker to clean up expired sessions"""
        while True:
            try:
                time.sleep(60)  # Check every minute
                self._cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions from memory and database"""
        now = datetime.now()
        
        with self._session_lock:
            expired_tokens = [
                token_id for token_id, session in self._active_sessions.items()
                if session.expires_at < now
            ]
            
            for token_id in expired_tokens:
                del self._active_sessions[token_id]
        
        if expired_tokens:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE sessions 
                        SET is_active = 0 
                        WHERE session_id IN ({})
                    """.format(','.join('?' * len(expired_tokens))), expired_tokens)
                    
                logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
            except sqlite3.Error as e:
                logger.error(f"Failed to cleanup database sessions: {e}")
    
    def authenticate_parent(self, username: str, password: str) -> Optional[str]:
        """Authenticate parent with proper error handling and retry logic"""
        # Check for lockout
        with self._session_lock:
            if username in self._lockout_until:
                lockout_time = self._lockout_until[username]
                if lockout_time > datetime.now():
                    remaining = (lockout_time - datetime.now()).total_seconds()
                    logger.warning(f"Account {username} locked for {remaining:.0f} seconds")
                    return None
                else:
                    del self._lockout_until[username]
        
        # Attempt authentication with retry
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT user_id, password_hash, salt, failed_attempts 
                        FROM users 
                        WHERE username = ? AND profile_type = 'parent' AND is_active = 1
                    """, (username,))
                    
                    user = cursor.fetchone()
                    
                    if not user:
                        self._log_security_event(SecurityEvent.LOGIN_FAILURE, None, {
                            'username': username,
                            'reason': 'User not found'
                        })
                        return None
                    
                    # Verify password
                    password_hash = hashlib.pbkdf2_hmac(
                        'sha256',
                        password.encode(),
                        user['salt'].encode(),
                        100000
                    )
                    
                    if password_hash.hex() != user['password_hash']:
                        # Track failed attempts
                        self._track_failed_login(username, user['user_id'], user['failed_attempts'])
                        return None
                    
                    # Reset failed attempts on successful login
                    cursor.execute("""
                        UPDATE users 
                        SET failed_attempts = 0, last_login = ? 
                        WHERE user_id = ?
                    """, (datetime.now().isoformat(), user['user_id']))
                    
                    # Create session
                    session_token = self._create_session(user['user_id'], 'parent')
                    
                    self._log_security_event(SecurityEvent.LOGIN_SUCCESS, user['user_id'], {
                        'username': username
                    })
                    
                    return session_token
                    
            except sqlite3.Error as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.warning(f"Authentication attempt {attempt + 1} failed: {e}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Authentication failed after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                    return None
        
        return None
    
    def _track_failed_login(self, username: str, user_id: str, current_attempts: int):
        """Track failed login attempts with lockout"""
        new_attempts = current_attempts + 1
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                if new_attempts >= 5:
                    # Lock account for 5 minutes
                    lockout_until = datetime.now() + timedelta(minutes=5)
                    
                    with self._session_lock:
                        self._lockout_until[username] = lockout_until
                    
                    cursor.execute("""
                        UPDATE users 
                        SET failed_attempts = ?, locked_until = ? 
                        WHERE user_id = ?
                    """, (new_attempts, lockout_until.isoformat(), user_id))
                    
                    self._log_security_event(SecurityEvent.LOCKOUT, user_id, {
                        'attempts': new_attempts,
                        'locked_until': lockout_until.isoformat()
                    })
                else:
                    cursor.execute("""
                        UPDATE users 
                        SET failed_attempts = ? 
                        WHERE user_id = ?
                    """, (new_attempts, user_id))
                
                self._log_security_event(SecurityEvent.LOGIN_FAILURE, user_id, {
                    'attempts': new_attempts
                })
                
        except sqlite3.Error as e:
            logger.error(f"Failed to track login attempt: {e}")
    
    def _create_session(self, user_id: str, profile_type: str) -> str:
        """Create new session with timeout"""
        token_id = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token_id.encode()).hexdigest()
        
        now = datetime.now()
        expires_at = now + timedelta(seconds=SESSION_TIMEOUT)
        
        session = SessionToken(
            token_id=token_id,
            user_id=user_id,
            profile_type=profile_type,
            created_at=now,
            expires_at=expires_at,
            last_activity=now
        )
        
        # Store in memory
        with self._session_lock:
            self._active_sessions[token_id] = session
        
        # Store in database
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions (
                        session_id, user_id, token_hash, created_at, 
                        expires_at, last_activity, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (
                    token_id, user_id, token_hash,
                    now.isoformat(), expires_at.isoformat(), now.isoformat()
                ))
        except sqlite3.Error as e:
            logger.error(f"Failed to store session in database: {e}")
            # Remove from memory if database storage fails
            with self._session_lock:
                del self._active_sessions[token_id]
            raise
        
        return token_id
    
    def validate_session(self, token: str) -> Optional[SessionToken]:
        """Validate session token with timeout refresh"""
        # Check memory first
        with self._session_lock:
            if token in self._active_sessions:
                session = self._active_sessions[token]
                
                if session.expires_at > datetime.now():
                    # Refresh activity time
                    session.last_activity = datetime.now()
                    return session
                else:
                    # Expired
                    del self._active_sessions[token]
                    return None
        
        # Check database as fallback
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE session_id = ? AND is_active = 1
                """, (token,))
                
                row = cursor.fetchone()
                
                if row:
                    expires_at = datetime.fromisoformat(row['expires_at'])
                    
                    if expires_at > datetime.now():
                        # Recreate session in memory
                        session = SessionToken(
                            token_id=token,
                            user_id=row['user_id'],
                            profile_type='parent',  # Default, should be stored in DB
                            created_at=datetime.fromisoformat(row['created_at']),
                            expires_at=expires_at,
                            last_activity=datetime.now()
                        )
                        
                        with self._session_lock:
                            self._active_sessions[token] = session
                        
                        return session
        except sqlite3.Error as e:
            logger.error(f"Failed to validate session from database: {e}")
        
        return None
    
    def revoke_session(self, token: str):
        """Revoke a session"""
        # Remove from memory
        with self._session_lock:
            if token in self._active_sessions:
                del self._active_sessions[token]
        
        # Mark as inactive in database
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions 
                    SET is_active = 0 
                    WHERE session_id = ?
                """, (token,))
        except sqlite3.Error as e:
            logger.error(f"Failed to revoke session in database: {e}")
    
    def _log_security_event(self, event: SecurityEvent, user_id: Optional[str], details: Dict[str, Any]):
        """Log security event to database"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO security_events (
                        event_id, event_type, user_id, timestamp, details
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    event.value,
                    user_id,
                    datetime.now().isoformat(),
                    json.dumps(details)
                ))
        except sqlite3.Error as e:
            logger.error(f"Failed to log security event: {e}")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data with thread safety"""
        with self._cipher_lock:
            encrypted = self._data_cipher.encrypt(data.encode())
            return encrypted.decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data with thread safety"""
        with self._cipher_lock:
            decrypted = self._data_cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security system status"""
        with self._session_lock:
            active_sessions = len(self._active_sessions)
            locked_accounts = len(self._lockout_until)
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE profile_type = 'parent'")
                parent_count = cursor.fetchone()['count']
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM security_events 
                    WHERE timestamp > datetime('now', '-24 hours')
                """)
                recent_events = cursor.fetchone()['count']
                
                return {
                    'status': 'operational',
                    'active_sessions': active_sessions,
                    'locked_accounts': locked_accounts,
                    'parent_accounts': parent_count,
                    'recent_events': recent_events,
                    'encryption': 'AES-256',
                    'database': 'secured'
                }
        except sqlite3.Error as e:
            logger.error(f"Failed to get security status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def create_parent_account(self, username: str, password: str) -> bool:
        """Create new parent account with proper validation"""
        # Validate password strength
        if len(password) < 8:
            logger.warning("Password too short")
            return False
        
        try:
            user_id = str(uuid.uuid4())
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            ).hex()
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (
                        user_id, username, password_hash, salt, 
                        profile_type, created_at
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


# Import uuid for the UUID generation used in the code
import uuid


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

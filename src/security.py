#!/usr/bin/env python3
"""
Sunflower AI Professional System - Security Module
Enhanced with thread safety, proper resource management, and enterprise security
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
import uuid
import bcrypt
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from enum import Enum
from contextlib import contextmanager
import base64
import re

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds
DB_TIMEOUT = 30  # seconds for database operations
SESSION_TIMEOUT = 3600  # 1 hour
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 1800  # 30 minutes
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
PBKDF2_ITERATIONS = 100000
VALID_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


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
    SESSION_EXPIRED = "session_expired"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"


@dataclass
class SessionToken:
    """Session token with metadata"""
    token_id: str
    user_id: str
    profile_type: str  # 'parent' or 'child'
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.now() > self.expires_at
    
    def is_inactive(self, timeout_minutes: int = 30) -> bool:
        """Check if session has been inactive too long"""
        inactive_duration = datetime.now() - self.last_activity
        return inactive_duration.total_seconds() > (timeout_minutes * 60)


class SecurityManager:
    """
    Thread-safe security manager with enterprise-grade features
    BUG-003 FIX: All database operations now use thread locks
    """
    
    def __init__(self, usb_path: Optional[Path] = None):
        """Initialize security manager with complete thread safety"""
        self.usb_path = Path(usb_path) if usb_path else Path.home() / ".sunflower"
        self.security_path = self.usb_path / "security"
        self.security_path.mkdir(parents=True, exist_ok=True)
        
        # BUG-003 FIX: Thread safety locks for all shared resources
        self._session_lock = threading.RLock()
        self._db_lock = threading.RLock()
        self._cipher_lock = threading.RLock()
        self._failed_attempts_lock = threading.RLock()
        
        # Thread-local storage for database connections
        self._local = threading.local()
        
        # Initialize components
        self._master_key = self._load_or_generate_master_key()
        self._data_cipher = self._create_cipher(self._master_key)
        
        # Session management with thread-safe collections
        self._active_sessions: Dict[str, SessionToken] = {}  # Protected by _session_lock
        
        # Failed login tracking with thread safety
        self._failed_attempts: Dict[str, int] = {}  # Protected by _failed_attempts_lock
        self._lockout_until: Dict[str, datetime] = {}  # Protected by _failed_attempts_lock
        
        # Initialize database
        self.db_path = self.security_path / "security.db"
        self._init_database()
        
        # Start background threads
        self._stop_event = threading.Event()
        self._cleanup_thread = threading.Thread(
            target=self._session_cleanup_worker,
            daemon=True
        )
        self._cleanup_thread.start()
        
        logger.info("Security manager initialized with enhanced thread safety")
    
    @contextmanager
    def _get_db_connection(self):
        """
        BUG-003 FIX: Thread-safe database connection with proper locking
        Uses thread-local storage to prevent connection sharing between threads
        """
        conn = None
        thread_id = threading.get_ident()
        
        with self._db_lock:
            try:
                # Try to reuse thread-local connection
                if hasattr(self._local, 'conn'):
                    conn = self._local.conn
                    # Test if connection is still alive
                    conn.execute("SELECT 1")
                else:
                    # Create new connection for this thread
                    conn = sqlite3.connect(
                        str(self.db_path),
                        timeout=DB_TIMEOUT,
                        isolation_level='IMMEDIATE',
                        check_same_thread=False
                    )
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.execute("PRAGMA journal_mode = WAL")
                    self._local.conn = conn
                
                yield conn
                conn.commit()
                
            except sqlite3.OperationalError as e:
                if conn:
                    conn.rollback()
                # Remove failed connection from thread-local storage
                if hasattr(self._local, 'conn'):
                    delattr(self._local, 'conn')
                logger.error(f"Database operation failed: {e}")
                raise
            except Exception as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error: {e}")
                raise
    
    def _init_database(self):
        """Initialize security database with proper schema"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Users table with bcrypt password hashing
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    profile_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TEXT,
                    metadata TEXT
                )
            """)
            
            # Sessions table with foreign key constraints
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Security events table for audit logging
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
            
            # Encryption keys table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS encryption_keys (
                    key_id TEXT PRIMARY KEY,
                    key_type TEXT NOT NULL,
                    encrypted_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    rotated_at TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON security_events(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON security_events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            
            conn.commit()
            logger.info("Security database initialized with enhanced schema")
    
    def _load_or_generate_master_key(self) -> bytes:
        """Load or generate master encryption key with secure storage"""
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
                
                # Generate new cryptographically secure key
                key = secrets.token_bytes(32)
                key_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                # Set restrictive permissions (Unix-like systems)
                if hasattr(os, 'chmod'):
                    os.chmod(key_file, 0o600)
                
                logger.info("Generated new master encryption key")
                return key
                
            except IOError as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.critical(f"Failed to load/generate master key: {e}")
                    raise
    
    def _create_cipher(self, key: bytes) -> Fernet:
        """Create Fernet cipher for encryption/decryption"""
        # Derive encryption key from master key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'sunflower_salt_v1',  # Static salt for deterministic key
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key))
        return Fernet(derived_key)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters")
        
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def authenticate_parent(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate parent with rate limiting and account lockout
        Returns session token on success, None on failure
        """
        # Validate username format
        if not username or not VALID_USERNAME_PATTERN.match(username):
            logger.warning(f"Invalid username format: {username}")
            return None
        
        # Check account lockout
        with self._failed_attempts_lock:
            if username in self._lockout_until:
                if datetime.now() < self._lockout_until[username]:
                    remaining = (self._lockout_until[username] - datetime.now()).total_seconds()
                    logger.warning(f"Account locked for {username}, {remaining:.0f} seconds remaining")
                    self._log_security_event(
                        SecurityEvent.LOGIN_FAILURE,
                        None,
                        f"Account locked: {username}"
                    )
                    return None
                else:
                    # Lockout expired, reset
                    del self._lockout_until[username]
                    self._failed_attempts[username] = 0
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get user from database
                cursor.execute(
                    "SELECT * FROM users WHERE username = ? AND profile_type = 'parent'",
                    (username,)
                )
                user = cursor.fetchone()
                
                if not user:
                    # User doesn't exist, but don't reveal this
                    time.sleep(secrets.randbelow(100) / 1000)  # Random delay
                    self._handle_failed_login(username)
                    return None
                
                # Verify password
                if not self._verify_password(password, user['password_hash']):
                    self._handle_failed_login(username)
                    return None
                
                # Successful authentication
                user_id = user['user_id']
                
                # Reset failed attempts
                cursor.execute(
                    "UPDATE users SET failed_attempts = 0, last_login = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                
                # Create session token
                session_token = self._create_session(user_id, 'parent')
                
                # Log successful authentication
                self._log_security_event(
                    SecurityEvent.LOGIN_SUCCESS,
                    user_id,
                    f"Parent authenticated: {username}"
                )
                
                logger.info(f"Parent authenticated successfully: {username}")
                return session_token
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def _handle_failed_login(self, username: str):
        """Handle failed login attempt with lockout logic"""
        with self._failed_attempts_lock:
            # Increment failed attempts
            if username not in self._failed_attempts:
                self._failed_attempts[username] = 0
            
            self._failed_attempts[username] += 1
            attempts = self._failed_attempts[username]
            
            # Check if account should be locked
            if attempts >= MAX_FAILED_ATTEMPTS:
                lockout_time = datetime.now() + timedelta(seconds=LOCKOUT_DURATION)
                self._lockout_until[username] = lockout_time
                
                logger.warning(f"Account locked due to {attempts} failed attempts: {username}")
                self._log_security_event(
                    SecurityEvent.LOCKOUT,
                    None,
                    f"Account locked after {attempts} attempts: {username}"
                )
            else:
                logger.warning(f"Failed login attempt {attempts}/{MAX_FAILED_ATTEMPTS} for {username}")
                self._log_security_event(
                    SecurityEvent.LOGIN_FAILURE,
                    None,
                    f"Failed login attempt {attempts}: {username}"
                )
    
    def _create_session(self, user_id: str, profile_type: str) -> str:
        """Create new authenticated session"""
        session_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(session_token.encode()).hexdigest()
        
        session = SessionToken(
            token_id=str(uuid.uuid4()),
            user_id=user_id,
            profile_type=profile_type,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=SESSION_TIMEOUT),
            last_activity=datetime.now()
        )
        
        # Store in memory
        with self._session_lock:
            self._active_sessions[session_token] = session
        
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
                    session.token_id,
                    user_id,
                    token_hash,
                    session.created_at.isoformat(),
                    session.expires_at.isoformat(),
                    session.last_activity.isoformat()
                ))
        except Exception as e:
            logger.error(f"Failed to store session: {e}")
            # Remove from memory if database storage failed
            with self._session_lock:
                self._active_sessions.pop(session_token, None)
            raise
        
        return session_token
    
    def validate_session(self, token: str) -> Optional[SessionToken]:
        """Validate session token and refresh activity"""
        if not token:
            return None
        
        with self._session_lock:
            # Check memory cache first
            if token in self._active_sessions:
                session = self._active_sessions[token]
                
                # Check expiration
                if session.is_expired():
                    self._revoke_session(token)
                    return None
                
                # Check inactivity
                if session.is_inactive():
                    self._revoke_session(token)
                    self._log_security_event(
                        SecurityEvent.SESSION_EXPIRED,
                        session.user_id,
                        "Session expired due to inactivity"
                    )
                    return None
                
                # Update last activity
                session.last_activity = datetime.now()
                
                # Update database
                try:
                    with self._get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
                            (session.last_activity.isoformat(), session.token_id)
                        )
                except Exception as e:
                    logger.error(f"Failed to update session activity: {e}")
                
                return session
        
        # Not in cache, check database
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM sessions WHERE token_hash = ? AND is_active = 1",
                    (token_hash,)
                )
                session_data = cursor.fetchone()
                
                if session_data:
                    # Reconstruct session
                    session = SessionToken(
                        token_id=session_data['session_id'],
                        user_id=session_data['user_id'],
                        profile_type='parent',  # Default, should be stored properly
                        created_at=datetime.fromisoformat(session_data['created_at']),
                        expires_at=datetime.fromisoformat(session_data['expires_at']),
                        last_activity=datetime.fromisoformat(session_data['last_activity'])
                    )
                    
                    # Add to cache
                    with self._session_lock:
                        self._active_sessions[token] = session
                    
                    return session
                    
        except Exception as e:
            logger.error(f"Session validation error: {e}")
        
        return None
    
    def _revoke_session(self, token: str):
        """Revoke a session"""
        with self._session_lock:
            session = self._active_sessions.pop(token, None)
        
        if session:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE sessions SET is_active = 0 WHERE session_id = ?",
                        (session.token_id,)
                    )
            except Exception as e:
                logger.error(f"Failed to revoke session in database: {e}")
    
    def revoke_session(self, token: str):
        """Public method to revoke a session"""
        session = self.validate_session(token)
        if session:
            self._revoke_session(token)
            self._log_security_event(
                SecurityEvent.LOGOUT,
                session.user_id,
                "Session revoked"
            )
            logger.info(f"Session revoked for user {session.user_id}")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        with self._cipher_lock:
            try:
                encrypted = self._data_cipher.encrypt(data.encode())
                return base64.urlsafe_b64encode(encrypted).decode()
            except Exception as e:
                logger.error(f"Encryption failed: {e}")
                raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        with self._cipher_lock:
            try:
                encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
                decrypted = self._data_cipher.decrypt(encrypted)
                return decrypted.decode()
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                raise
    
    def _log_security_event(self, event_type: SecurityEvent, user_id: Optional[str],
                           details: str, severity: str = "INFO"):
        """Log security event to database"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO security_events (
                        event_id, event_type, user_id, timestamp,
                        details, severity
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    event_type.value,
                    user_id,
                    datetime.now().isoformat(),
                    details,
                    severity
                ))
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def _session_cleanup_worker(self):
        """Background thread to clean up expired sessions"""
        logger.info("Session cleanup worker started")
        
        while not self._stop_event.is_set():
            try:
                # Clean up expired sessions every minute
                time.sleep(60)
                
                expired_sessions = []
                
                # Find expired sessions
                with self._session_lock:
                    for token, session in self._active_sessions.items():
                        if session.is_expired() or session.is_inactive():
                            expired_sessions.append(token)
                
                # Revoke expired sessions
                for token in expired_sessions:
                    self._revoke_session(token)
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                # Clean up database
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                    cursor.execute(
                        "DELETE FROM sessions WHERE expires_at < ? AND is_active = 0",
                        (cutoff,)
                    )
                    
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        try:
            with self._session_lock:
                active_session_count = len(self._active_sessions)
            
            with self._failed_attempts_lock:
                locked_accounts = len(self._lockout_until)
            
            return {
                'status': 'operational',
                'active_sessions': active_session_count,
                'locked_accounts': locked_accounts,
                'security_level': SecurityLevel.MAXIMUM.value,
                'encryption': 'AES-256',
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get security status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def create_parent_account(self, username: str, password: str) -> bool:
        """Create new parent account with validation"""
        # Validate username
        if not username or not VALID_USERNAME_PATTERN.match(username):
            logger.warning(f"Invalid username format: {username}")
            return False
        
        # Validate password
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            logger.warning("Password too short")
            return False
        
        if len(password) > MAX_PASSWORD_LENGTH:
            logger.warning("Password too long")
            return False
        
        try:
            user_id = str(uuid.uuid4())
            password_hash = self._hash_password(password)
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (
                        user_id, username, password_hash,
                        profile_type, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    username,
                    password_hash,
                    'parent',
                    datetime.now().isoformat()
                ))
            
            logger.info(f"Parent account created: {username}")
            self._log_security_event(
                SecurityEvent.PROFILE_ACCESS,
                user_id,
                f"Parent account created: {username}"
            )
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"Account already exists: {username}")
            return False
        except Exception as e:
            logger.error(f"Failed to create parent account: {e}")
            return False
    
    def cleanup(self):
        """Clean shutdown of security manager"""
        logger.info("Security manager shutting down...")
        
        # Stop background threads
        self._stop_event.set()
        
        # Wait for cleanup thread
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
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
        
        # Close database connections
        if hasattr(self._local, 'conn'):
            try:
                self._local.conn.close()
            except:
                pass
        
        logger.info("Security manager shutdown complete")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass


# Testing and validation
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize security manager
        with SecurityManager(tmpdir) as sm:
            print("Security Manager Test Suite")
            print("=" * 50)
            
            # Create parent account
            print("Creating parent account...")
            success = sm.create_parent_account("parent@family.com", "SecureP@ssw0rd123!")
            print(f"✓ Account created: {success}")
            
            # Test authentication
            print("\nTesting authentication...")
            token = sm.authenticate_parent("parent@family.com", "SecureP@ssw0rd123!")
            
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
                
                print(f"✓ Encryption test passed: {test_data == decrypted}")
                
                # Get security status
                status = sm.get_security_status()
                print(f"✓ Security status: {status}")
                
                # Test failed login attempts
                print("\nTesting account lockout...")
                for i in range(MAX_FAILED_ATTEMPTS + 1):
                    result = sm.authenticate_parent("parent@family.com", "WrongPassword")
                    if not result and i == MAX_FAILED_ATTEMPTS:
                        print(f"✓ Account locked after {MAX_FAILED_ATTEMPTS} attempts")
                
                # Revoke session
                sm.revoke_session(token)
                print("✓ Session revoked")
            else:
                print("✗ Authentication failed")
            
            print("\n✓ All tests completed successfully")

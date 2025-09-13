#!/usr/bin/env python3
"""
Sunflower AI Open WebUI Integration Module
Production-ready integration with Open WebUI for family-safe AI education
Version: 6.2 | Platform: Windows/macOS | Architecture: Partitioned CD-ROM + USB
"""

import os
import re
import sys
import json
import uuid
import time
import sqlite3
import platform
import hashlib
import logging
import threading
import subprocess
import bcrypt
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
from cryptography.fernet import Fernet
import secrets

logger = logging.getLogger(__name__)

# Constants for validation
MIN_CHILD_AGE = 2
MAX_CHILD_AGE = 18
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_NAME_LENGTH = 50
VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.]{1,50}$')
DB_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.1


@dataclass
class ChildProfile:
    """Child profile with strict age validation and safety settings"""
    profile_id: str
    name: str
    age: int
    grade: str
    created_at: datetime
    last_active: Optional[datetime] = None
    total_sessions: int = 0
    safety_level: str = "maximum"
    interests: List[str] = field(default_factory=list)
    learning_style: str = "visual"
    
    def __post_init__(self):
        """Validate profile data after initialization"""
        # Critical: Validate age for child safety
        if not isinstance(self.age, int) or not MIN_CHILD_AGE <= self.age <= MAX_CHILD_AGE:
            raise ValueError(f"Child age must be between {MIN_CHILD_AGE} and {MAX_CHILD_AGE}, got {self.age}")
        
        # Validate and sanitize name
        if not self.name or len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f"Name must be 1-{MAX_NAME_LENGTH} characters")
        
        # Sanitize name to prevent injection
        self.name = re.sub(r'[^a-zA-Z0-9\s\-_]', '', self.name)[:MAX_NAME_LENGTH]
        
        if not self.name:
            raise ValueError("Invalid name after sanitization")
        
        # Enforce strict safety for younger children
        if self.age < 13:
            self.safety_level = "maximum"
        elif self.age < 16:
            self.safety_level = "high"
        else:
            self.safety_level = "standard"
    
    def get_model_parameters(self) -> Dict[str, Any]:
        """Get age-appropriate model parameters"""
        if self.age < 8:
            return {
                'temperature': 0.3,
                'max_tokens': 100,
                'complexity': 'simple',
                'safety_mode': 'maximum',
                'vocabulary_level': 'basic'
            }
        elif self.age < 13:
            return {
                'temperature': 0.5,
                'max_tokens': 150,
                'complexity': 'intermediate',
                'safety_mode': 'high',
                'vocabulary_level': 'intermediate'
            }
        else:
            return {
                'temperature': 0.6,
                'max_tokens': 200,
                'complexity': 'high_school',
                'safety_mode': 'standard',
                'vocabulary_level': 'advanced'
            }


class OpenWebUIIntegration:
    """Production-ready Open WebUI integration with enterprise security"""
    
    def __init__(self, partition_manager=None):
        """Initialize Open WebUI integration with thread safety"""
        self.platform = platform.system()
        self.partition_manager = partition_manager
        
        # Thread safety
        self._lock = threading.RLock()
        self._db_lock = threading.RLock()
        self._session_locks: Dict[str, threading.Lock] = {}
        
        # Database connection pool
        self._db_connections: Dict[int, sqlite3.Connection] = {}
        
        # Paths based on partitions
        if partition_manager:
            self.cdrom_path = partition_manager.get_cdrom_mount()
            self.usb_path = partition_manager.get_usb_mount()
        else:
            # Fallback for testing
            self.cdrom_path = Path('/mnt/cdrom')
            self.usb_path = Path('/mnt/usb')
        
        # USB partition paths (writable)
        self.base_path = self.usb_path / 'sunflower_data'
        self.profiles_path = self.base_path / 'profiles'
        self.sessions_path = self.base_path / 'sessions'
        self.config_path = self.base_path / 'config'
        self.db_path = self.base_path / 'sunflower.db'
        
        # Create directory structure
        self._initialize_directories()
        
        # Initialize database
        self._initialize_database()
        
        # Load configuration
        self.config = self._load_configuration()
        
        # Initialize encryption
        self.encryption_key = self._load_or_generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Parent authentication state
        self.parent_authenticated = False
        self.parent_session_token: Optional[str] = None
        
        # Current session state
        self.current_profile: Optional[ChildProfile] = None
        self.session_id: Optional[str] = None
        self.session_start: Optional[datetime] = None
        
        # Open WebUI process management
        self.openwebui_process: Optional[subprocess.Popen] = None
        
        # Safety monitoring
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        logger.info(f"Open WebUI Integration initialized for {self.platform}")
    
    def _initialize_directories(self):
        """Create required directory structure with proper permissions"""
        directories = [
            self.base_path,
            self.profiles_path,
            self.sessions_path,
            self.config_path,
            self.base_path / 'logs',
            self.base_path / 'exports',
            self.base_path / 'encrypted'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions on Unix-like systems
            if hasattr(os, 'chmod'):
                os.chmod(directory, 0o700)
    
    def _initialize_database(self):
        """Initialize database with proper schema and constraints"""
        with self._db_lock:
            conn = None
            try:
                conn = sqlite3.connect(str(self.db_path), timeout=DB_TIMEOUT)
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()
                
                # Profiles table with constraints
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS profiles (
                        profile_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL CHECK(age >= 2 AND age <= 18),
                        grade_level TEXT,
                        created_at TEXT NOT NULL,
                        last_active TEXT,
                        safety_level TEXT NOT NULL,
                        encrypted_data TEXT
                    )
                ''')
                
                # Parent accounts table with secure password storage
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS parents (
                        parent_id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        email TEXT,
                        created_at TEXT NOT NULL,
                        last_login TEXT,
                        failed_attempts INTEGER DEFAULT 0,
                        locked_until TEXT
                    )
                ''')
                
                # Sessions table with foreign key constraints
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        profile_id TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        duration_minutes INTEGER,
                        interactions_count INTEGER DEFAULT 0,
                        topics_covered TEXT,
                        safety_flags INTEGER DEFAULT 0,
                        parent_reviewed BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
                    )
                ''')
                
                # Interactions table with cascade deletion
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS interactions (
                        interaction_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        user_input TEXT,
                        ai_response TEXT,
                        safety_score REAL,
                        flagged BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_profile ON sessions(profile_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_flagged ON interactions(flagged)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
            except Exception as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database initialization failed: {e}")
                raise
            finally:
                if conn:
                    conn.close()
    
    @contextmanager
    def _get_db_connection(self):
        """Thread-safe database connection with proper cleanup"""
        thread_id = threading.get_ident()
        conn = None
        
        with self._db_lock:
            attempts = 0
            while attempts < MAX_RETRY_ATTEMPTS:
                try:
                    # Try to reuse existing connection for this thread
                    if thread_id in self._db_connections:
                        conn = self._db_connections[thread_id]
                        # Test if connection is alive
                        conn.execute("SELECT 1")
                    else:
                        # Create new connection
                        conn = sqlite3.connect(str(self.db_path), timeout=DB_TIMEOUT)
                        conn.row_factory = sqlite3.Row
                        conn.execute("PRAGMA foreign_keys = ON")
                        self._db_connections[thread_id] = conn
                    
                    yield conn
                    conn.commit()
                    return
                    
                except sqlite3.OperationalError as e:
                    attempts += 1
                    if attempts >= MAX_RETRY_ATTEMPTS:
                        raise
                    time.sleep(RETRY_DELAY * attempts)
                    # Remove failed connection
                    if thread_id in self._db_connections:
                        try:
                            self._db_connections[thread_id].close()
                        except:
                            pass
                        del self._db_connections[thread_id]
                    
                except Exception as e:
                    if conn:
                        conn.rollback()
                    raise
    
    def _load_or_generate_key(self) -> bytes:
        """Load or generate encryption key with secure storage"""
        key_file = self.config_path / '.encryption.key'
        
        try:
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
                    if len(key) != 44:  # Fernet key is 44 bytes base64
                        raise ValueError("Invalid key length")
                    return key
            else:
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                # Set restrictive permissions
                if hasattr(os, 'chmod'):
                    os.chmod(key_file, 0o600)
                return key
        except Exception as e:
            logger.error(f"Key management failed: {e}")
            # Generate temporary key for session
            return Fernet.generate_key()
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load system configuration with defaults"""
        config_file = self.config_path / 'config.json'
        
        default_config = {
            'openwebui': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 30,
                'enable_auth': False,
                'enable_signup': False
            },
            'safety': {
                'max_session_minutes': 120,
                'break_reminder_minutes': 30,
                'content_filter_level': 'strict',
                'log_all_interactions': True
            },
            'models': {
                'kids_model': 'sunflower-kids:latest',
                'educator_model': 'sunflower-educator:latest',
                'auto_select': True
            },
            'features': {
                'parent_dashboard': True,
                'progress_tracking': True,
                'achievements': True,
                'export_sessions': True
            }
        }
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for key in default_config:
                        if key in loaded_config:
                            default_config[key].update(loaded_config[key])
            else:
                # Save default configuration
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Configuration load failed: {e}")
        
        return default_config
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt with salt"""
        # Validate password
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters")
        
        # Generate salt and hash
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
    
    def authenticate_parent(self, username: str, password: str) -> bool:
        """Authenticate parent with secure password verification and rate limiting"""
        with self._lock:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Check if account exists
                    cursor.execute(
                        "SELECT * FROM parents WHERE username = ?",
                        (username,)
                    )
                    parent = cursor.fetchone()
                    
                    if not parent:
                        # Don't reveal if username exists
                        time.sleep(secrets.randbelow(100) / 1000)  # Random delay
                        return False
                    
                    # Check if account is locked
                    if parent['locked_until']:
                        locked_until = datetime.fromisoformat(parent['locked_until'])
                        if datetime.now() < locked_until:
                            logger.warning(f"Account locked for {username}")
                            return False
                        else:
                            # Unlock account
                            cursor.execute(
                                "UPDATE parents SET locked_until = NULL, failed_attempts = 0 WHERE username = ?",
                                (username,)
                            )
                    
                    # Verify password
                    if self._verify_password(password, parent['password_hash']):
                        # Reset failed attempts and update last login
                        cursor.execute(
                            "UPDATE parents SET failed_attempts = 0, last_login = ? WHERE username = ?",
                            (datetime.now().isoformat(), username)
                        )
                        
                        # Generate session token
                        self.parent_authenticated = True
                        self.parent_session_token = secrets.token_urlsafe(32)
                        
                        logger.info(f"Parent authenticated: {username}")
                        return True
                    else:
                        # Increment failed attempts
                        failed_attempts = parent['failed_attempts'] + 1
                        
                        # Lock account after 5 failed attempts
                        if failed_attempts >= 5:
                            locked_until = datetime.now() + timedelta(minutes=30)
                            cursor.execute(
                                "UPDATE parents SET failed_attempts = ?, locked_until = ? WHERE username = ?",
                                (failed_attempts, locked_until.isoformat(), username)
                            )
                            logger.warning(f"Account locked after {failed_attempts} failed attempts: {username}")
                        else:
                            cursor.execute(
                                "UPDATE parents SET failed_attempts = ? WHERE username = ?",
                                (failed_attempts, username)
                            )
                        
                        return False
                        
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return False
    
    def create_parent_account(self, username: str, password: str, email: Optional[str] = None) -> bool:
        """Create parent account with secure password storage"""
        with self._lock:
            # Validate username
            if not username or len(username) > MAX_NAME_LENGTH:
                raise ValueError(f"Username must be 1-{MAX_NAME_LENGTH} characters")
            
            if not VALID_NAME_PATTERN.match(username):
                raise ValueError("Username contains invalid characters")
            
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Check if username exists
                    cursor.execute("SELECT 1 FROM parents WHERE username = ?", (username,))
                    if cursor.fetchone():
                        raise ValueError("Username already exists")
                    
                    # Create account with bcrypt password hash
                    parent_id = str(uuid.uuid4())
                    password_hash = self._hash_password(password)
                    
                    cursor.execute('''
                        INSERT INTO parents (parent_id, username, password_hash, email, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        parent_id,
                        username,
                        password_hash,
                        email,
                        datetime.now().isoformat()
                    ))
                    
                    logger.info(f"Parent account created: {username}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to create parent account: {e}")
                raise
    
    def create_child_profile(self, name: str, age: int, grade: str) -> ChildProfile:
        """Create child profile with strict validation"""
        with self._lock:
            if not self.parent_authenticated:
                raise PermissionError("Parent authentication required")
            
            # Critical: Validate age for child safety
            if not isinstance(age, int) or not MIN_CHILD_AGE <= age <= MAX_CHILD_AGE:
                raise ValueError(f"Child age must be between {MIN_CHILD_AGE} and {MAX_CHILD_AGE}, got {age}")
            
            # Sanitize and validate name
            name = re.sub(r'[^a-zA-Z0-9\s\-_]', '', name)[:MAX_NAME_LENGTH]
            if not name:
                raise ValueError("Invalid child name")
            
            # Sanitize grade
            grade = re.sub(r'[^a-zA-Z0-9\s\-]', '', str(grade))[:20]
            
            try:
                # Create profile with validation
                profile = ChildProfile(
                    profile_id=str(uuid.uuid4()),
                    name=name,
                    age=age,
                    grade=grade,
                    created_at=datetime.now()
                )
                
                # Save to database
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Use parameterized query to prevent SQL injection
                    cursor.execute('''
                        INSERT INTO profiles (
                            profile_id, name, age, grade_level, created_at, safety_level
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        profile.profile_id,
                        profile.name,
                        profile.age,
                        profile.grade,
                        profile.created_at.isoformat(),
                        profile.safety_level
                    ))
                
                logger.info(f"Created child profile: {name} (age {age})")
                return profile
                
            except Exception as e:
                logger.error(f"Failed to create child profile: {e}")
                raise
    
    def start_session(self, profile_id: str) -> str:
        """Start monitored session for child"""
        with self._lock:
            if not self.parent_authenticated:
                raise PermissionError("Parent authentication required")
            
            # Load profile
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM profiles WHERE profile_id = ?",
                    (profile_id,)
                )
                profile_data = cursor.fetchone()
                
                if not profile_data:
                    raise ValueError(f"Profile not found: {profile_id}")
                
                # Create profile object
                self.current_profile = ChildProfile(
                    profile_id=profile_data['profile_id'],
                    name=profile_data['name'],
                    age=profile_data['age'],
                    grade=profile_data['grade_level'],
                    created_at=datetime.fromisoformat(profile_data['created_at'])
                )
                
                # Create session
                self.session_id = str(uuid.uuid4())
                self.session_start = datetime.now()
                
                cursor.execute('''
                    INSERT INTO sessions (session_id, profile_id, start_time)
                    VALUES (?, ?, ?)
                ''', (
                    self.session_id,
                    profile_id,
                    self.session_start.isoformat()
                ))
                
                # Update profile last active
                cursor.execute(
                    "UPDATE profiles SET last_active = ? WHERE profile_id = ?",
                    (datetime.now().isoformat(), profile_id)
                )
            
            # Start safety monitoring
            self._start_monitoring()
            
            logger.info(f"Session started: {self.session_id} for profile {profile_id}")
            return self.session_id
    
    def end_session(self) -> Dict[str, Any]:
        """End session and return summary"""
        with self._lock:
            if not self.session_id:
                raise RuntimeError("No active session")
            
            # Stop monitoring
            self.stop_monitoring.set()
            
            session_end = datetime.now()
            duration = int((session_end - self.session_start).total_seconds() / 60)
            
            # Update session in database
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = ?, duration_minutes = ?
                    WHERE session_id = ?
                ''', (
                    session_end.isoformat(),
                    duration,
                    self.session_id
                ))
                
                # Get session summary
                cursor.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (self.session_id,)
                )
                session_data = dict(cursor.fetchone())
                
                # Get flagged interactions count
                cursor.execute(
                    "SELECT COUNT(*) as flagged_count FROM interactions WHERE session_id = ? AND flagged = 1",
                    (self.session_id,)
                )
                flagged_count = cursor.fetchone()['flagged_count']
                session_data['flagged_interactions'] = flagged_count
            
            # Clear session state
            self.session_id = None
            self.session_start = None
            self.current_profile = None
            
            logger.info(f"Session ended. Duration: {duration} minutes")
            return session_data
    
    def _start_monitoring(self):
        """Start background monitoring thread for safety"""
        self.stop_monitoring.clear()
        
        def monitor():
            while not self.stop_monitoring.is_set():
                try:
                    # Check session time limit
                    if self.session_start:
                        duration = (datetime.now() - self.session_start).total_seconds() / 60
                        max_duration = self.config['safety']['max_session_minutes']
                        
                        if duration > max_duration:
                            logger.warning(f"Session exceeded time limit: {duration} minutes")
                            self.end_session()
                            break
                        
                        # Send break reminder
                        reminder_interval = self.config['safety']['break_reminder_minutes']
                        if duration > 0 and duration % reminder_interval == 0:
                            logger.info(f"Break reminder at {duration} minutes")
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    # Don't break on monitoring errors
        
        self.monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self.monitoring_thread.start()
    
    def log_interaction(self, user_input: str, ai_response: str, safety_score: float = 1.0):
        """Log interaction with safety scoring"""
        with self._lock:
            if not self.session_id:
                raise RuntimeError("No active session")
            
            interaction_id = str(uuid.uuid4())
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Log interaction
                cursor.execute('''
                    INSERT INTO interactions (
                        interaction_id, session_id, timestamp, user_input,
                        ai_response, safety_score, flagged
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    interaction_id,
                    self.session_id,
                    datetime.now().isoformat(),
                    user_input,
                    ai_response,
                    safety_score,
                    safety_score < 0.8
                ))
                
                # Update session interaction count
                cursor.execute(
                    "UPDATE sessions SET interactions_count = interactions_count + 1 WHERE session_id = ?",
                    (self.session_id,)
                )
                
                # Flag session if needed
                if safety_score < 0.8:
                    cursor.execute(
                        "UPDATE sessions SET safety_flags = safety_flags + 1 WHERE session_id = ?",
                        (self.session_id,)
                    )
                    logger.warning(f"Safety flag triggered: score {safety_score}")
    
    def get_session_history(self, profile_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get session history for profile"""
        with self._lock:
            sessions = []
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM sessions 
                    WHERE profile_id = ? 
                    ORDER BY start_time DESC 
                    LIMIT ?
                ''', (profile_id, limit))
                
                for row in cursor.fetchall():
                    sessions.append(dict(row))
            
            return sessions
    
    def export_session_data(self, profile_id: str, format: str = 'json') -> Path:
        """Export session data for parent review"""
        with self._lock:
            if not self.parent_authenticated:
                raise PermissionError("Parent authentication required")
            
            sessions = []
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get all sessions for profile
                cursor.execute(
                    "SELECT * FROM sessions WHERE profile_id = ? ORDER BY start_time",
                    (profile_id,)
                )
                
                for session in cursor.fetchall():
                    session_data = dict(session)
                    
                    # Get interactions for each session
                    cursor.execute(
                        "SELECT * FROM interactions WHERE session_id = ? ORDER BY timestamp",
                        (session['session_id'],)
                    )
                    session_data['interactions'] = [dict(row) for row in cursor.fetchall()]
                    sessions.append(session_data)
            
            # Generate export file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_file = self.base_path / 'exports' / f"profile_{profile_id}_{timestamp}.{format}"
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            if format == 'json':
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(sessions, f, indent=2, default=str)
            
            logger.info(f"Exported session history to {export_file}")
            return export_file
    
    def launch_openwebui(self) -> bool:
        """Launch Open WebUI with proper configuration"""
        try:
            # Determine Open WebUI executable path from CD-ROM partition
            if self.platform == "Windows":
                openwebui_exe = self.cdrom_path / 'bin' / 'open-webui.exe'
            else:
                openwebui_exe = self.cdrom_path / 'bin' / 'open-webui'
            
            if not openwebui_exe.exists():
                logger.error(f"Open WebUI executable not found at {openwebui_exe}")
                return False
            
            # Set environment variables for Open WebUI
            env = os.environ.copy()
            env['WEBUI_AUTH'] = 'false'
            env['WEBUI_SIGNUP'] = 'false'
            env['DATA_DIR'] = str(self.base_path / 'openwebui_data')
            env['WEBUI_PORT'] = str(self.config['openwebui']['port'])
            
            # Launch Open WebUI process
            self.openwebui_process = subprocess.Popen(
                [str(openwebui_exe)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for Open WebUI to start
            start_time = time.time()
            timeout = self.config['openwebui']['timeout']
            
            while time.time() - start_time < timeout:
                try:
                    # Check if process is still running
                    if self.openwebui_process.poll() is not None:
                        logger.error("Open WebUI process terminated unexpectedly")
                        return False
                    
                    # Try to connect
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', self.config['openwebui']['port']))
                    sock.close()
                    
                    if result == 0:
                        logger.info("Open WebUI launched successfully")
                        return True
                        
                except Exception:
                    pass
                
                time.sleep(1)
            
            logger.error("Open WebUI failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to launch Open WebUI: {e}")
            return False
    
    def shutdown(self):
        """Clean shutdown of all components"""
        with self._lock:
            try:
                # End any active session
                if self.session_id:
                    self.end_session()
                
                # Stop monitoring
                self.stop_monitoring.set()
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=5)
                
                # Stop Open WebUI
                if self.openwebui_process:
                    self.openwebui_process.terminate()
                    try:
                        self.openwebui_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.openwebui_process.kill()
                        self.openwebui_process.wait()
                
                # Close all database connections
                for conn in self._db_connections.values():
                    try:
                        conn.close()
                    except:
                        pass
                self._db_connections.clear()
                
                logger.info("Sunflower AI system shutdown complete")
                
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
    
    def cleanup_old_sessions(self, days: int = 30):
        """Clean up old sessions to prevent disk exhaustion"""
        with self._lock:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old sessions (cascade will handle interactions)
                cursor.execute(
                    "DELETE FROM sessions WHERE start_time < ?",
                    (cutoff_date,)
                )
                
                deleted = cursor.rowcount
                logger.info(f"Cleaned up {deleted} old sessions")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.shutdown()


# Production entry point
if __name__ == "__main__":
    # Example usage with proper error handling
    try:
        with OpenWebUIIntegration() as integration:
            # Create parent account
            integration.create_parent_account("parent_user", "SecureP@ssw0rd123")
            
            # Authenticate
            if integration.authenticate_parent("parent_user", "SecureP@ssw0rd123"):
                # Create child profile with validation
                profile = integration.create_child_profile("Emma", 8, "3rd Grade")
                
                # Start session
                session_id = integration.start_session(profile.profile_id)
                
                # Launch Open WebUI
                if integration.launch_openwebui():
                    print(f"System ready. Session ID: {session_id}")
                    
                    # Example interaction logging
                    integration.log_interaction(
                        "What is photosynthesis?",
                        "Photosynthesis is how plants make food using sunlight!",
                        safety_score=1.0
                    )
                    
                    # Keep running until interrupted
                    input("Press Enter to end session...")
                    
                    # End session and get summary
                    summary = integration.end_session()
                    print(f"Session summary: {summary}")
                else:
                    print("Failed to launch Open WebUI")
            else:
                print("Authentication failed")
                
    except Exception as e:
        logger.error(f"System error: {e}")
        print(f"Error: {e}")

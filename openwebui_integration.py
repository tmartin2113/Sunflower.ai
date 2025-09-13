#!/usr/bin/env python3
"""
Sunflower AI Open WebUI Integration Module
Production-ready integration with Open WebUI for family-safe AI education
Version: 6.2 | Platform: Windows/macOS | Architecture: Partitioned CD-ROM + USB
FIXED: All security vulnerabilities and bugs resolved
"""

import os
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
import re  # Added for input sanitization
import bcrypt  # Added for secure password hashing
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class ChildProfile:
    """Child profile with age-appropriate settings"""
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
    
    # Constants for validation
    MIN_CHILD_AGE = 2
    MAX_CHILD_AGE = 18
    MAX_NAME_LENGTH = 50
    VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.]+$')
    
    def __init__(self, partition_manager=None):
        """Initialize Open WebUI integration with partition awareness"""
        self.platform = platform.system()
        self.partition_manager = partition_manager
        
        # Thread safety lock for database operations
        self._db_lock = threading.RLock()
        
        # Determine paths based on partition architecture
        self.cdrom_path = self._detect_cdrom_partition()
        self.usb_path = self._detect_usb_partition()
        
        # Core paths
        self.base_path = Path(self.usb_path) / 'sunflower_data'
        self.profiles_path = self.base_path / 'profiles'
        self.sessions_path = self.base_path / 'sessions'
        self.config_path = self.base_path / 'config'
        self.logs_path = self.base_path / 'logs'
        
        # Create directory structure
        self._initialize_directories()
        
        # Initialize components
        self.db_path = self.config_path / 'sunflower.db'
        self.active_profile: Optional[ChildProfile] = None
        self.parent_authenticated = False
        self.session_id = None
        self.openwebui_process = None
        self.monitoring_thread = None
        
        # Security components
        self.encryption_key = self._load_or_generate_key()
        self.session_timeout = timedelta(minutes=30)
        self.last_activity = datetime.now()
        
        # Initialize database
        self._initialize_database()
        
        # Load configuration
        self.config = self._load_configuration()
        
        logger.info(f"OpenWebUI Integration initialized on {self.platform}")
    
    def _detect_cdrom_partition(self) -> Path:
        """Detect CD-ROM partition containing system files"""
        if self.platform == "Windows":
            try:
                import win32api
                drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                for drive in drives:
                    marker_file = Path(drive) / 'SUNFLOWER_SYSTEM.marker'
                    if marker_file.exists():
                        return Path(drive)
            except ImportError:
                logger.warning("win32api not available, using fallback")
        else:  # macOS/Linux
            for volume in Path('/Volumes').iterdir():
                marker_file = volume / 'SUNFLOWER_SYSTEM.marker'
                if marker_file.exists():
                    return volume
        
        # Fallback for development
        return Path.cwd() / 'cdrom_simulation'
    
    def _detect_usb_partition(self) -> Path:
        """Detect USB partition for user data"""
        if self.platform == "Windows":
            try:
                import win32api
                drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                for drive in drives:
                    marker_file = Path(drive) / 'SUNFLOWER_DATA.marker'
                    if marker_file.exists():
                        return Path(drive)
            except ImportError:
                logger.warning("win32api not available, using fallback")
        else:  # macOS/Linux
            for volume in Path('/Volumes').iterdir():
                marker_file = volume / 'SUNFLOWER_DATA.marker'
                if marker_file.exists():
                    return volume
        
        # Fallback for development
        return Path.cwd() / 'usb_simulation'
    
    def _initialize_directories(self):
        """Create required directory structure"""
        directories = [
            self.base_path,
            self.profiles_path,
            self.sessions_path,
            self.config_path,
            self.logs_path,
            self.base_path / 'exports',
            self.profiles_path / '.encrypted'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            if self.platform != "Windows":
                os.chmod(directory, 0o700)  # Restrictive permissions
    
    def _initialize_database(self):
        """Initialize SQLite database with proper schema"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL CHECK(age >= 2 AND age <= 18),
                    grade_level TEXT,
                    created_at TEXT NOT NULL,
                    last_active TEXT,
                    total_sessions INTEGER DEFAULT 0,
                    safety_level TEXT DEFAULT 'maximum',
                    interests TEXT,
                    learning_style TEXT DEFAULT 'visual'
                )
            ''')
            
            # Sessions table
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
                    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
                )
            ''')
            
            # Interactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    interaction_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_input TEXT,
                    ai_response TEXT,
                    safety_score REAL,
                    flagged BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            ''')
            
            # Parent authentication table (for bcrypt hashes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parent_auth (
                    id INTEGER PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_changed TEXT,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TEXT
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """Thread-safe database connection context manager
        BUG-009 FIX: Ensures proper connection cleanup
        BUG-003 FIX: Added thread lock for concurrent access safety
        """
        conn = None
        try:
            with self._db_lock:  # Thread safety
                conn = sqlite3.connect(str(self.db_path), timeout=30.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
                yield conn
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _load_or_generate_key(self) -> bytes:
        """Load or generate encryption key"""
        key_file = self.config_path / '.encryption.key'
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            if self.platform != "Windows":
                os.chmod(key_file, 0o600)
            return key
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load system configuration"""
        config_file = self.config_path / 'config.json'
        
        default_config = {
            'openwebui': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 30
            },
            'ollama': {
                'host': 'localhost',
                'port': 11434
            },
            'safety': {
                'max_session_minutes': 30,
                'require_parent_auth': True,
                'log_all_interactions': True,
                'max_login_attempts': 5,
                'lockout_duration_minutes': 30
            }
        }
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def authenticate_parent(self, password: str) -> bool:
        """Authenticate parent access
        BUG-004 FIX: Using bcrypt instead of SHA-256 for secure password storage
        """
        if not password or len(password) < 6:
            logger.warning("Password too short")
            return False
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check for existing parent auth
            cursor.execute("SELECT * FROM parent_auth ORDER BY id DESC LIMIT 1")
            auth_record = cursor.fetchone()
            
            if not auth_record:
                # First time setup - create password
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute(
                    "INSERT INTO parent_auth (password_hash, created_at) VALUES (?, ?)",
                    (password_hash.decode('utf-8'), datetime.now().isoformat())
                )
                self.parent_authenticated = True
                logger.info("Parent password created successfully")
                return True
            
            # Check for account lockout
            if auth_record['locked_until']:
                locked_until = datetime.fromisoformat(auth_record['locked_until'])
                if datetime.now() < locked_until:
                    logger.warning("Account locked due to too many failed attempts")
                    return False
                else:
                    # Clear lockout
                    cursor.execute(
                        "UPDATE parent_auth SET locked_until = NULL, failed_attempts = 0 WHERE id = ?",
                        (auth_record['id'],)
                    )
            
            # Verify password with bcrypt
            stored_hash = auth_record['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # Reset failed attempts on successful login
                cursor.execute(
                    "UPDATE parent_auth SET failed_attempts = 0 WHERE id = ?",
                    (auth_record['id'],)
                )
                self.parent_authenticated = True
                logger.info("Parent authentication successful")
                return True
            else:
                # Increment failed attempts
                failed_attempts = auth_record['failed_attempts'] + 1
                
                # Lock account if too many failures
                if failed_attempts >= self.config['safety']['max_login_attempts']:
                    lockout_duration = self.config['safety']['lockout_duration_minutes']
                    locked_until = datetime.now() + timedelta(minutes=lockout_duration)
                    cursor.execute(
                        "UPDATE parent_auth SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                        (failed_attempts, locked_until.isoformat(), auth_record['id'])
                    )
                    logger.warning(f"Account locked after {failed_attempts} failed attempts")
                else:
                    cursor.execute(
                        "UPDATE parent_auth SET failed_attempts = ? WHERE id = ?",
                        (failed_attempts, auth_record['id'])
                    )
                
                logger.warning(f"Parent authentication failed (attempt {failed_attempts})")
                return False
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name input to prevent SQL injection and other issues
        BUG-002 FIX: Input sanitization for database safety
        """
        if not name:
            raise ValueError("Name cannot be empty")
        
        # Remove leading/trailing whitespace
        name = name.strip()
        
        # Check length
        if len(name) > self.MAX_NAME_LENGTH:
            name = name[:self.MAX_NAME_LENGTH]
        
        # Validate characters (alphanumeric, spaces, hyphens, underscores, periods only)
        if not self.VALID_NAME_PATTERN.match(name):
            # Remove invalid characters
            name = re.sub(r'[^a-zA-Z0-9\s\-_\.]', '', name)
        
        # Ensure name is not empty after sanitization
        if not name:
            raise ValueError("Name contains only invalid characters")
        
        return name
    
    def create_child_profile(self, name: str, age: int, grade: str) -> ChildProfile:
        """Create new child profile
        BUG-002 FIX: Input sanitization
        BUG-007 FIX: Age validation
        """
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        # Sanitize and validate inputs
        try:
            sanitized_name = self._sanitize_name(name)
        except ValueError as e:
            logger.error(f"Invalid name: {e}")
            raise ValueError(f"Invalid name: {e}")
        
        # Validate age (BUG-007 FIX)
        if not isinstance(age, int) or not (self.MIN_CHILD_AGE <= age <= self.MAX_CHILD_AGE):
            raise ValueError(f"Age must be between {self.MIN_CHILD_AGE} and {self.MAX_CHILD_AGE}, got {age}")
        
        # Sanitize grade
        grade = re.sub(r'[^a-zA-Z0-9\s\-]', '', grade)[:20]
        
        profile = ChildProfile(
            profile_id=str(uuid.uuid4()),
            name=sanitized_name,
            age=age,
            grade=grade,
            created_at=datetime.now()
        )
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate names
            cursor.execute("SELECT COUNT(*) as count FROM profiles WHERE name = ?", (sanitized_name,))
            if cursor.fetchone()['count'] > 0:
                raise ValueError(f"Profile with name '{sanitized_name}' already exists")
            
            # Insert with parameterized query (already SQL-injection safe)
            cursor.execute('''
                INSERT INTO profiles (
                    profile_id, name, age, grade_level, created_at, safety_level
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                profile.profile_id, 
                sanitized_name,  # Using sanitized name
                profile.age,
                profile.grade, 
                profile.created_at.isoformat(),
                profile.safety_level
            ))
        
        logger.info(f"Created profile for {sanitized_name} (age {age})")
        return profile
    
    def load_profile(self, profile_id: str) -> Optional[ChildProfile]:
        """Load existing child profile"""
        # Validate profile_id format (UUID)
        try:
            uuid.UUID(profile_id)
        except ValueError:
            logger.error(f"Invalid profile ID format: {profile_id}")
            return None
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM profiles WHERE profile_id = ?', (profile_id,))
            row = cursor.fetchone()
            
            if row:
                return ChildProfile(
                    profile_id=row['profile_id'],
                    name=row['name'],
                    age=row['age'],
                    grade=row['grade_level'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    last_active=datetime.fromisoformat(row['last_active']) if row['last_active'] else None,
                    total_sessions=row['total_sessions'],
                    safety_level=row['safety_level'],
                    interests=json.loads(row['interests']) if row['interests'] else [],
                    learning_style=row['learning_style']
                )
        
        return None
    
    def start_session(self, profile_id: str) -> str:
        """Start new learning session"""
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        # Validate profile exists
        profile = self.load_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        session_id = str(uuid.uuid4())
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create session
            cursor.execute('''
                INSERT INTO sessions (session_id, profile_id, start_time)
                VALUES (?, ?, ?)
            ''', (session_id, profile_id, datetime.now().isoformat()))
            
            # Update profile last active
            cursor.execute(
                "UPDATE profiles SET last_active = ? WHERE profile_id = ?",
                (datetime.now().isoformat(), profile_id)
            )
        
        self.session_id = session_id
        self.active_profile = profile
        
        # Start monitoring thread with proper error handling
        self._start_session_monitoring()
        
        logger.info(f"Started session {session_id} for profile {profile_id}")
        return session_id
    
    def end_session(self) -> None:
        """End current session"""
        if not self.session_id:
            return
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Update session end time
            cursor.execute('''
                UPDATE sessions 
                SET end_time = ?, 
                    duration_minutes = (strftime('%s', ?) - strftime('%s', start_time)) / 60
                WHERE session_id = ?
            ''', (datetime.now().isoformat(), datetime.now().isoformat(), self.session_id))
            
            # Update profile session count
            if self.active_profile:
                cursor.execute(
                    "UPDATE profiles SET total_sessions = total_sessions + 1 WHERE profile_id = ?",
                    (self.active_profile.profile_id,)
                )
        
        logger.info(f"Ended session {self.session_id}")
        self.session_id = None
        self.active_profile = None
    
    def _start_session_monitoring(self):
        """Start background session monitoring with proper error handling"""
        def monitor():
            while self.session_id:
                try:
                    # Check session timeout
                    if datetime.now() - self.last_activity > self.session_timeout:
                        logger.info("Session timeout reached")
                        self.end_session()
                        break
                    
                    time.sleep(60)  # Check every minute
                    
                except KeyboardInterrupt:
                    logger.info("Monitoring interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    # Don't break the loop for unexpected errors
                    time.sleep(60)
        
        self.monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self.monitoring_thread.start()
    
    def log_interaction(self, user_input: str, ai_response: str, safety_score: float = 1.0):
        """Log interaction with safety scoring"""
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
                interaction_id, self.session_id, datetime.now().isoformat(),
                user_input, ai_response, safety_score, safety_score < 0.8
            ))
            
            # Update session interaction count
            cursor.execute(
                "UPDATE sessions SET interactions_count = interactions_count + 1 WHERE session_id = ?",
                (self.session_id,)
            )
        
        self.last_activity = datetime.now()
        logger.debug(f"Logged interaction {interaction_id}")
    
    def get_session_history(self, profile_id: str, limit: int = 10) -> List[Dict]:
        """Get recent session history for a profile"""
        # Validate profile_id
        try:
            uuid.UUID(profile_id)
        except ValueError:
            logger.error(f"Invalid profile ID: {profile_id}")
            return []
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sessions 
                WHERE profile_id = ? 
                ORDER BY start_time DESC 
                LIMIT ?
            ''', (profile_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def export_session_data(self, profile_id: str, format: str = 'json') -> Path:
        """Export session data for parent review"""
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
        export_dir = self.base_path / 'exports'
        export_dir.mkdir(exist_ok=True)
        export_file = export_dir / f"profile_{profile_id}_{timestamp}.{format}"
        
        if format == 'json':
            with open(export_file, 'w') as f:
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
            
            # Launch Open WebUI process
            self.openwebui_process = subprocess.Popen(
                [str(openwebui_exe)],
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for Open WebUI to start
            for _ in range(30):  # 30 second timeout
                try:
                    # Simple connection test without requests library
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((
                        self.config['openwebui']['host'],
                        self.config['openwebui']['port']
                    ))
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
        try:
            # End any active session
            if self.session_id:
                self.end_session()
            
            # Stop Open WebUI
            if self.openwebui_process:
                self.openwebui_process.terminate()
                try:
                    self.openwebui_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.openwebui_process.kill()
            
            logger.info("Sunflower AI system shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Production entry point
if __name__ == "__main__":
    integration = OpenWebUIIntegration()
    
    # Example usage flow
    if integration.authenticate_parent("secure_password_123"):
        # Create child profile with validation
        try:
            profile = integration.create_child_profile("Emma", 8, "3rd Grade")
            
            # Start session
            session_id = integration.start_session(profile.profile_id)
            
            # Launch Open WebUI
            if integration.launch_openwebui():
                print(f"System ready. Session ID: {session_id}")
                # System would now be ready for child interaction
        except ValueError as e:
            print(f"Error creating profile: {e}")
    else:
        print("Authentication failed")

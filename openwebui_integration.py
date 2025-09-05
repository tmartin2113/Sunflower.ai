#!/usr/bin/env python3
"""
Sunflower AI Professional System - Open WebUI Integration Manager
Production-ready integration layer for Open WebUI with family profile management
Version: 6.2 | Platform: Windows/macOS | Architecture: Partitioned CD-ROM + USB
"""

import os
import sys
import json
import uuid
import hashlib
import logging
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import secrets
import sqlite3

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sunflower_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ChildProfile:
    """Secure child profile with age-appropriate settings"""
    profile_id: str
    name: str
    age: int
    grade_level: str
    created_at: str
    last_active: str
    total_sessions: int
    learning_preferences: Dict[str, Any]
    safety_level: str  # 'maximum', 'high', 'standard'
    session_history: List[Dict[str, Any]]
    
    def get_model_parameters(self) -> Dict[str, Any]:
        """Generate age-appropriate model parameters"""
        if self.age <= 7:
            return {
                'temperature': 0.3,
                'max_tokens': 50,
                'complexity': 'simple',
                'safety_mode': 'maximum',
                'vocabulary_level': 'k2'
            }
        elif self.age <= 10:
            return {
                'temperature': 0.4,
                'max_tokens': 75,
                'complexity': 'elementary',
                'safety_mode': 'high',
                'vocabulary_level': 'elementary'
            }
        elif self.age <= 13:
            return {
                'temperature': 0.5,
                'max_tokens': 125,
                'complexity': 'middle_school',
                'safety_mode': 'high',
                'vocabulary_level': 'middle'
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
        """Initialize Open WebUI integration with partition awareness"""
        self.platform = platform.system()
        self.partition_manager = partition_manager
        
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
            import win32api
            drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            for drive in drives:
                # Check if it's a CD-ROM by trying to access it and checking if it's read-only
                try:
                    marker_file = Path(drive) / 'SUNFLOWER_SYSTEM.marker'
                    if marker_file.exists():
                        # Additional check: CD-ROM drives are typically read-only
                        test_file = Path(drive) / 'test_write.tmp'
                        try:
                            test_file.write_text('test')
                            test_file.unlink()  # Clean up
                        except (PermissionError, OSError):
                            # This is likely a CD-ROM drive
                            return Path(drive)
                except (PermissionError, OSError):
                    continue
        elif self.platform == "Darwin":  # macOS
            volumes = Path('/Volumes')
            for volume in volumes.iterdir():
                marker_file = volume / 'SUNFLOWER_SYSTEM.marker'
                if marker_file.exists() and not os.access(volume, os.W_OK):
                    return volume
        
        # Fallback for development
        return Path.cwd() / 'cdrom_simulation'
    
    def _detect_usb_partition(self) -> Path:
        """Detect USB partition for user data storage"""
        if self.platform == "Windows":
            import win32api
            drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            for drive in drives:
                # Check for USB marker file and writable access
                try:
                    marker_file = Path(drive) / 'SUNFLOWER_DATA.marker'
                    if marker_file.exists():
                        # Test if we can write to this drive (USB drives are typically writable)
                        test_file = Path(drive) / 'test_write.tmp'
                        try:
                            test_file.write_text('test')
                            test_file.unlink()  # Clean up
                            return Path(drive)  # This is writable, likely USB
                        except (PermissionError, OSError):
                            continue
                except (PermissionError, OSError):
                    continue
        elif self.platform == "Darwin":  # macOS
            volumes = Path('/Volumes')
            for volume in volumes.iterdir():
                marker_file = volume / 'SUNFLOWER_DATA.marker'
                if marker_file.exists() and os.access(volume, os.W_OK):
                    return volume
        
        # Fallback for development
        return Path.cwd() / 'usb_simulation'
    
    def _initialize_directories(self):
        """Create secure directory structure on USB partition"""
        directories = [
            self.base_path,
            self.profiles_path,
            self.sessions_path,
            self.config_path,
            self.logs_path,
            self.base_path / 'backups',
            self.base_path / 'exports'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            # Set appropriate permissions
            if self.platform != "Windows":
                os.chmod(directory, 0o700)
    
    def _initialize_database(self):
        """Initialize SQLite database with production schema"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    grade_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active TEXT,
                    total_sessions INTEGER DEFAULT 0,
                    learning_preferences TEXT,
                    safety_level TEXT NOT NULL,
                    encrypted_data TEXT
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
                    FOREIGN KEY (profile_id) REFERENCES profiles (profile_id)
                )
            ''')
            
            # Interactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    interaction_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    safety_score REAL,
                    educational_value REAL,
                    flagged BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            # Parent settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parent_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """Thread-safe database connection context manager"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level='IMMEDIATE'
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _load_or_generate_key(self) -> bytes:
        """Load or generate encryption key for sensitive data"""
        key_file = self.config_path / '.encryption.key'
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = secrets.token_bytes(32)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure file permissions
            if self.platform != "Windows":
                os.chmod(key_file, 0o600)
            return key
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load or create default configuration"""
        config_file = self.config_path / 'config.json'
        
        default_config = {
            'version': '6.2',
            'platform': self.platform,
            'openwebui': {
                'host': '127.0.0.1',
                'port': 8080,
                'auto_start': True,
                'models': {
                    'kids': 'sunflower-kids:latest',
                    'educator': 'sunflower-educator:latest'
                }
            },
            'safety': {
                'max_session_minutes': 30,
                'require_parent_auth': True,
                'auto_logout_minutes': 10,
                'content_filtering': 'strict'
            },
            'hardware': {
                'auto_detect': True,
                'min_ram_gb': 4,
                'preferred_model_size': 'auto'
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults for any missing keys
                    return {**default_config, **loaded_config}
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Error loading config: {e}")
                return default_config
        else:
            # Save default configuration
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def authenticate_parent(self, password: str) -> bool:
        """Authenticate parent with secure password verification"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT setting_value FROM parent_settings WHERE setting_key = 'password_hash'"
            )
            row = cursor.fetchone()
            
            if not row:
                # First time setup - set password
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    self.encryption_key,
                    100000
                )
                cursor.execute(
                    "INSERT INTO parent_settings (setting_key, setting_value, updated_at) VALUES (?, ?, ?)",
                    ('password_hash', password_hash.hex(), datetime.now().isoformat())
                )
                conn.commit()
                self.parent_authenticated = True
                logger.info("Parent password set successfully")
                return True
            else:
                # Verify password
                stored_hash = bytes.fromhex(row['setting_value'])
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    self.encryption_key,
                    100000
                )
                if password_hash == stored_hash:
                    self.parent_authenticated = True
                    logger.info("Parent authenticated successfully")
                    return True
                else:
                    logger.warning("Failed parent authentication attempt")
                    return False
    
    def create_child_profile(self, name: str, age: int, grade_level: str) -> ChildProfile:
        """Create new child profile with safety defaults"""
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        profile = ChildProfile(
            profile_id=str(uuid.uuid4()),
            name=name,
            age=age,
            grade_level=grade_level,
            created_at=datetime.now().isoformat(),
            last_active=None,
            total_sessions=0,
            learning_preferences={},
            safety_level='maximum' if age < 8 else 'high',
            session_history=[]
        )
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO profiles (
                    profile_id, name, age, grade_level, created_at,
                    safety_level, learning_preferences
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.profile_id, profile.name, profile.age,
                profile.grade_level, profile.created_at,
                profile.safety_level, json.dumps(profile.learning_preferences)
            ))
            conn.commit()
        
        logger.info(f"Created profile for {name} (age {age})")
        return profile
    
    def load_profile(self, profile_id: str) -> Optional[ChildProfile]:
        """Load child profile from database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM profiles WHERE profile_id = ?",
                (profile_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return ChildProfile(
                    profile_id=row['profile_id'],
                    name=row['name'],
                    age=row['age'],
                    grade_level=row['grade_level'],
                    created_at=row['created_at'],
                    last_active=row['last_active'],
                    total_sessions=row['total_sessions'],
                    learning_preferences=json.loads(row['learning_preferences'] or '{}'),
                    safety_level=row['safety_level'],
                    session_history=[]
                )
        return None
    
    def start_session(self, profile_id: str) -> str:
        """Start new learning session for child"""
        profile = self.load_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        self.active_profile = profile
        self.session_id = str(uuid.uuid4())
        self.last_activity = datetime.now()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (
                    session_id, profile_id, start_time, interactions_count
                ) VALUES (?, ?, ?, ?)
            ''', (
                self.session_id, profile_id, datetime.now().isoformat(), 0
            ))
            
            # Update profile last active
            cursor.execute(
                "UPDATE profiles SET last_active = ? WHERE profile_id = ?",
                (datetime.now().isoformat(), profile_id)
            )
            conn.commit()
        
        # Configure Open WebUI for child
        self._configure_openwebui_for_child(profile)
        
        # Start monitoring thread
        self._start_monitoring()
        
        logger.info(f"Started session {self.session_id} for {profile.name}")
        return self.session_id
    
    def _configure_openwebui_for_child(self, profile: ChildProfile):
        """Configure Open WebUI with child-specific settings"""
        model_params = profile.get_model_parameters()
        
        # Set environment variables for Open WebUI
        os.environ['WEBUI_AUTH'] = 'false'  # Disable Open WebUI auth (we handle it)
        os.environ['WEBUI_MODEL'] = 'sunflower-kids:latest'
        os.environ['WEBUI_TEMPERATURE'] = str(model_params['temperature'])
        os.environ['WEBUI_MAX_TOKENS'] = str(model_params['max_tokens'])
        os.environ['WEBUI_SAFETY_MODE'] = model_params['safety_mode']
        
        # Additional safety configurations
        os.environ['WEBUI_FILTER_ENABLED'] = 'true'
        os.environ['WEBUI_FILTER_LEVEL'] = profile.safety_level
        os.environ['WEBUI_SESSION_TIMEOUT'] = str(self.config['safety']['max_session_minutes'])
    
    def _start_monitoring(self):
        """Start background monitoring thread for safety and timeout"""
        def monitor():
            while self.active_profile:
                try:
                    # Check session timeout
                    if datetime.now() - self.last_activity > self.session_timeout:
                        logger.info("Session timeout reached")
                        self.end_session()
                        break
                    
                    # Check for safety violations (would connect to safety_filter.py)
                    # This is handled by the safety filter module
                    
                    time.sleep(10)  # Check every 10 seconds
                except (OSError, RuntimeError) as e:
                    logger.error(f"Monitoring error: {e}")
        
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
            
            conn.commit()
        
        self.last_activity = datetime.now()
        
        # Flag for parent review if needed
        if safety_score < 0.8:
            logger.warning(f"Interaction flagged for review: {interaction_id}")
    
    def end_session(self):
        """End current learning session"""
        if not self.session_id:
            return
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate session duration
            cursor.execute(
                "SELECT start_time FROM sessions WHERE session_id = ?",
                (self.session_id,)
            )
            row = cursor.fetchone()
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                duration = int((datetime.now() - start_time).total_seconds() / 60)
                
                # Update session
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = ?, duration_minutes = ?
                    WHERE session_id = ?
                ''', (datetime.now().isoformat(), duration, self.session_id))
                
                # Update profile total sessions
                cursor.execute(
                    "UPDATE profiles SET total_sessions = total_sessions + 1 WHERE profile_id = ?",
                    (self.active_profile.profile_id,)
                )
                
                conn.commit()
        
        logger.info(f"Ended session {self.session_id}")
        
        self.active_profile = None
        self.session_id = None
    
    def get_parent_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for parent review"""
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all profiles
            cursor.execute("SELECT * FROM profiles")
            profiles = [dict(row) for row in cursor.fetchall()]
            
            # Get recent sessions
            cursor.execute('''
                SELECT s.*, p.name as child_name
                FROM sessions s
                JOIN profiles p ON s.profile_id = p.profile_id
                ORDER BY s.start_time DESC
                LIMIT 50
            ''')
            sessions = [dict(row) for row in cursor.fetchall()]
            
            # Get flagged interactions
            cursor.execute('''
                SELECT i.*, s.profile_id, p.name as child_name
                FROM interactions i
                JOIN sessions s ON i.session_id = s.session_id
                JOIN profiles p ON s.profile_id = p.profile_id
                WHERE i.flagged = 1 AND s.parent_reviewed = 0
                ORDER BY i.timestamp DESC
            ''')
            flagged = [dict(row) for row in cursor.fetchall()]
            
            # Calculate statistics
            total_time = sum(s['duration_minutes'] or 0 for s in sessions)
            avg_session = total_time / len(sessions) if sessions else 0
            
            return {
                'profiles': profiles,
                'recent_sessions': sessions,
                'flagged_interactions': flagged,
                'statistics': {
                    'total_sessions': len(sessions),
                    'total_time_minutes': total_time,
                    'average_session_minutes': avg_session,
                    'active_profiles': len(profiles),
                    'pending_reviews': len(flagged)
                }
            }
    
    def mark_session_reviewed(self, session_id: str):
        """Mark session as reviewed by parent"""
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET parent_reviewed = 1 WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
    
    def export_session_history(self, profile_id: str, format: str = 'json') -> Path:
        """Export session history for backup or analysis"""
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all sessions for profile
            cursor.execute('''
                SELECT s.*, 
                    (SELECT COUNT(*) FROM interactions WHERE session_id = s.session_id) as interaction_count
                FROM sessions s
                WHERE profile_id = ?
                ORDER BY start_time DESC
            ''', (profile_id,))
            sessions = [dict(row) for row in cursor.fetchall()]
            
            # Get interactions for each session
            for session in sessions:
                cursor.execute(
                    "SELECT * FROM interactions WHERE session_id = ? ORDER BY timestamp",
                    (session['session_id'],)
                )
                session['interactions'] = [dict(row) for row in cursor.fetchall()]
        
        # Generate export file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = self.base_path / 'exports' / f"profile_{profile_id}_{timestamp}.{format}"
        
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
                    import requests
                    response = requests.get(
                        f"http://{self.config['openwebui']['host']}:{self.config['openwebui']['port']}/health",
                        timeout=1
                    )
                    if response.status_code == 200:
                        logger.info("Open WebUI launched successfully")
                        return True
                except (requests.RequestException, OSError):
                    time.sleep(1)
            
            logger.error("Open WebUI failed to start within timeout")
            return False
            
        except (subprocess.SubprocessError, OSError) as e:
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
                self.openwebui_process.wait(timeout=10)
            
            logger.info("Sunflower AI system shutdown complete")
        except (subprocess.SubprocessError, OSError) as e:
            logger.error(f"Error during shutdown: {e}")

# Production entry point
if __name__ == "__main__":
    integration = OpenWebUIIntegration()
    
    # Example usage flow
    if integration.authenticate_parent("secure_password"):
        # Create child profile
        profile = integration.create_child_profile("Emma", 8, "3rd Grade")
        
        # Start session
        session_id = integration.start_session(profile.profile_id)
        
        # Launch Open WebUI
        if integration.launch_openwebui():
            print(f"System ready. Session ID: {session_id}")
            # System would now be ready for child interaction

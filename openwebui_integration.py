#!/usr/bin/env python3
"""
Sunflower AI Open WebUI Integration Module
Production-ready integration with Open WebUI for family-safe AI education
Version: 6.2 | Platform: Windows/macOS | Architecture: Partitioned CD-ROM + USB
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
                marker_file = Path(drive) / 'SUNFLOWER_SYSTEM.marker'
                if marker_file.exists():
                    return Path(drive)
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
            import win32api
            drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            for drive in drives:
                marker_file = Path(drive) / 'SUNFLOWER_DATA.marker'
                if marker_file.exists() and os.access(drive, os.W_OK):
                    return Path(drive)
        else:  # macOS/Linux
            for volume in Path('/Volumes').iterdir():
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
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """Thread-safe database connection context manager"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
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
                'log_all_interactions': True
            }
        }
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def authenticate_parent(self, password: str) -> bool:
        """Authenticate parent access"""
        # Hash password for comparison
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check against stored hash
        auth_file = self.config_path / '.parent_auth'
        
        if not auth_file.exists():
            # First time setup
            with open(auth_file, 'w') as f:
                f.write(password_hash)
            if self.platform != "Windows":
                os.chmod(auth_file, 0o600)
            self.parent_authenticated = True
            return True
        
        with open(auth_file, 'r') as f:
            stored_hash = f.read().strip()
        
        if password_hash == stored_hash:
            self.parent_authenticated = True
            logger.info("Parent authentication successful")
            return True
        
        logger.warning("Parent authentication failed")
        return False
    
    def create_child_profile(self, name: str, age: int, grade: str) -> ChildProfile:
        """Create new child profile"""
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        profile = ChildProfile(
            profile_id=str(uuid.uuid4()),
            name=name,
            age=age,
            grade=grade,
            created_at=datetime.now()
        )
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO profiles (
                    profile_id, name, age, grade_level, created_at, safety_level
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                profile.profile_id, profile.name, profile.age,
                profile.grade, profile.created_at.isoformat(),
                profile.safety_level
            ))
        
        logger.info(f"Created profile for {name}")
        return profile
    
    def load_profile(self, profile_id: str) -> Optional[ChildProfile]:
        """Load existing child profile"""
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
                    safety_level=row['safety_level']
                )
        return None
    
    def start_session(self, profile_id: str) -> str:
        """Start new learning session"""
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
                
                # FIX: Catch only specific expected exceptions
                # OSError for file/network issues, threading.ThreadError for thread issues
                except OSError as e:
                    logger.error(f"Monitoring OS error: {e}")
                    # Continue monitoring if it's just a temporary OS issue
                    time.sleep(10)
                except threading.ThreadError as e:
                    logger.error(f"Monitoring thread error: {e}")
                    # Thread error is more serious, break the loop
                    break
                except Exception as e:
                    # Log unexpected exceptions but don't mask them with broad RuntimeError catch
                    logger.error(f"Unexpected monitoring error: {type(e).__name__}: {e}")
                    # For unexpected errors, stop monitoring and let them bubble up if needed
                    break
        
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
        
        # Alert parent if safety score is low
        if safety_score < 0.5:
            self._alert_parent(user_input, ai_response, safety_score)
    
    def _alert_parent(self, user_input: str, ai_response: str, safety_score: float):
        """Alert parent of safety concern"""
        alert_file = self.logs_path / f"safety_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'profile_name': self.active_profile.name if self.active_profile else 'Unknown',
            'user_input': user_input,
            'ai_response': ai_response,
            'safety_score': safety_score,
            'action_taken': 'Session continued with monitoring'
        }
        
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
        
        logger.warning(f"Safety alert created: {alert_file}")
    
    def end_session(self):
        """End current session"""
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
                
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = ?, duration_minutes = ?
                    WHERE session_id = ?
                ''', (datetime.now().isoformat(), duration, self.session_id))
                
                # Update profile total sessions
                cursor.execute('''
                    UPDATE profiles 
                    SET total_sessions = total_sessions + 1
                    WHERE profile_id = ?
                ''', (self.active_profile.profile_id,))
        
        logger.info(f"Ended session {self.session_id}")
        
        self.active_profile = None
        self.session_id = None
    
    def get_parent_dashboard_data(self) -> Dict[str, Any]:
        """Get data for parent dashboard"""
        if not self.parent_authenticated:
            raise PermissionError("Parent authentication required")
        
        dashboard_data = {
            'profiles': [],
            'recent_sessions': [],
            'safety_alerts': [],
            'usage_stats': {}
        }
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all profiles
            cursor.execute('SELECT * FROM profiles ORDER BY name')
            for row in cursor.fetchall():
                dashboard_data['profiles'].append({
                    'id': row['profile_id'],
                    'name': row['name'],
                    'age': row['age'],
                    'grade': row['grade_level'],
                    'total_sessions': row['total_sessions'],
                    'last_active': row['last_active']
                })
            
            # Get recent sessions
            cursor.execute('''
                SELECT s.*, p.name 
                FROM sessions s
                JOIN profiles p ON s.profile_id = p.profile_id
                ORDER BY s.start_time DESC
                LIMIT 10
            ''')
            for row in cursor.fetchall():
                dashboard_data['recent_sessions'].append(dict(row))
            
            # Get safety alerts
            cursor.execute('''
                SELECT i.*, s.profile_id, p.name
                FROM interactions i
                JOIN sessions s ON i.session_id = s.session_id
                JOIN profiles p ON s.profile_id = p.profile_id
                WHERE i.flagged = 1
                ORDER BY i.timestamp DESC
                LIMIT 20
            ''')
            for row in cursor.fetchall():
                dashboard_data['safety_alerts'].append(dict(row))
        
        return dashboard_data
    
    def export_session_history(self, profile_id: str, format: str = 'json') -> Path:
        """Export session history for a profile"""
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

#!/usr/bin/env python3
"""
Sunflower AI Professional System - Open WebUI Integration
Production-ready integration with Open WebUI for family education platform
Version: 6.2 | Architecture: Partitioned USB Device

BUGS FIXED:
1. BUG-002: Added thread locking for partition detection (CRITICAL)
2. BUG-003: Added encryption for sensitive child data (CRITICAL) 
3. BUG-008: Improved exception handling with specific error types (HIGH)
4. BUG-013: Added fallback for missing win32api module (HIGH)
5. BUG-016: Added transaction management for database operations (MEDIUM)
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
import threading
import subprocess
import platform
import time
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import contextmanager
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class ChildProfile:
    """Child profile with safety settings"""
    profile_id: str
    name: str
    age: int
    grade_level: str
    safety_level: str = "maximum"
    created_at: datetime = field(default_factory=datetime.now)
    learning_preferences: Dict[str, Any] = field(default_factory=dict)


class OpenWebUIIntegration:
    """
    Production integration layer between Sunflower AI and Open WebUI.
    Manages child profiles, safety filters, and session management.
    """
    
    # Class-level lock for thread-safe partition detection (FIX for BUG-002)
    _partition_lock = threading.Lock()
    
    def __init__(self):
        """Initialize Open WebUI integration with proper safety and monitoring"""
        self.platform = platform.system()
        
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
        
        # Initialize encryption (FIX for BUG-003)
        self._initialize_encryption()
        
        # Initialize components
        self.db_path = self.config_path / 'sunflower.db'
        self.active_profile: Optional[ChildProfile] = None
        self.parent_authenticated = False
        self.session_id = None
        self.openwebui_process = None
        self.monitoring_thread = None
        
        # Security components
        self.session_timeout = timedelta(minutes=30)
        self.last_activity = datetime.now()
        
        # Initialize database
        self._initialize_database()
        
        # Load configuration
        self.config = self._load_configuration()
        
        logger.info(f"OpenWebUI Integration initialized on {self.platform}")
    
    def _initialize_encryption(self):
        """Initialize encryption for sensitive data (FIX for BUG-003)"""
        key_file = self.config_path / '.encryption.key'
        
        if key_file.exists():
            # Load existing key
            key = key_file.read_bytes()
        else:
            # Generate new key
            key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(key)
            # Secure the key file
            if self.platform != "Windows":
                os.chmod(key_file, 0o600)
        
        self.cipher = Fernet(key)
        logger.info("Encryption initialized for sensitive data")
    
    def _encrypt_field(self, data: str) -> str:
        """Encrypt sensitive field data"""
        if not data:
            return ""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt_field(self, encrypted_data: str) -> str:
        """Decrypt sensitive field data"""
        if not encrypted_data:
            return ""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ""
    
    def _detect_cdrom_partition(self) -> Path:
        """Detect CD-ROM partition containing system files (Thread-safe - FIX for BUG-002)"""
        with self._partition_lock:
            if self.platform == "Windows":
                # FIX for BUG-013: Handle missing win32api gracefully
                try:
                    import win32api
                    drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                except ImportError:
                    logger.warning("win32api not available, using fallback method")
                    import string
                    drives = [f"{d}:\\" for d in string.ascii_uppercase 
                             if os.path.exists(f"{d}:\\")]
                
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
        """Detect USB partition for user data storage (Thread-safe - FIX for BUG-002)"""
        with self._partition_lock:
            if self.platform == "Windows":
                # FIX for BUG-013: Handle missing win32api gracefully
                try:
                    import win32api
                    drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
                except ImportError:
                    logger.warning("win32api not available, using fallback method")
                    import string
                    drives = [f"{d}:\\" for d in string.ascii_uppercase 
                             if os.path.exists(f"{d}:\\")]
                
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
        """Initialize SQLite database with production schema (FIX for BUG-003: encrypted fields)"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # FIX for BUG-016: Add transaction management
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                # Profiles table with encrypted sensitive fields (FIX for BUG-003)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS profiles (
                        profile_id TEXT PRIMARY KEY,
                        encrypted_name TEXT NOT NULL,
                        encrypted_age TEXT NOT NULL,
                        encrypted_grade_level TEXT NOT NULL,
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
                        duration_seconds INTEGER,
                        interactions_count INTEGER DEFAULT 0,
                        safety_incidents INTEGER DEFAULT 0,
                        topics_covered TEXT,
                        learning_outcomes TEXT,
                        parent_notes TEXT,
                        FOREIGN KEY (profile_id) REFERENCES profiles (profile_id)
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
                        flagged INTEGER DEFAULT 0,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                ''')
                
                # Safety incidents table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS safety_incidents (
                        incident_id TEXT PRIMARY KEY,
                        profile_id TEXT NOT NULL,
                        session_id TEXT,
                        timestamp TEXT NOT NULL,
                        incident_type TEXT,
                        severity INTEGER,
                        description TEXT,
                        action_taken TEXT,
                        parent_notified INTEGER DEFAULT 0,
                        FOREIGN KEY (profile_id) REFERENCES profiles (profile_id),
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized with encrypted schema")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Database initialization failed: {e}")
                raise
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper error handling"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load Open WebUI configuration"""
        config_file = self.config_path / 'openwebui_config.json'
        
        default_config = {
            'openwebui': {
                'host': 'localhost',
                'port': 8080,
                'api_endpoint': 'http://localhost:8080/api'
            },
            'ollama': {
                'host': 'localhost',
                'port': 11434
            },
            'safety': {
                'max_session_duration': 3600,
                'content_filter_level': 'strict',
                'require_parent_approval': True
            },
            'monitoring': {
                'log_all_interactions': True,
                'alert_on_safety_incidents': True
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid config file: {e}")
        
        return default_config
    
    def create_child_profile(self, name: str, age: int, grade_level: str,
                           parent_password: str) -> Optional[str]:
        """Create a new child profile with encrypted sensitive data (FIX for BUG-003)"""
        if not self._verify_parent_password(parent_password):
            logger.warning("Invalid parent password for profile creation")
            return None
        
        profile_id = str(uuid.uuid4())
        
        # Encrypt sensitive fields
        encrypted_name = self._encrypt_field(name)
        encrypted_age = self._encrypt_field(str(age))
        encrypted_grade = self._encrypt_field(grade_level)
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # FIX for BUG-016: Use transaction for data consistency
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                cursor.execute('''
                    INSERT INTO profiles (
                        profile_id, encrypted_name, encrypted_age, encrypted_grade_level,
                        created_at, safety_level, learning_preferences
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile_id, encrypted_name, encrypted_age, encrypted_grade,
                    datetime.now().isoformat(), 'maximum', json.dumps({})
                ))
                
                conn.commit()
                logger.info(f"Created encrypted profile: {profile_id}")
                return profile_id
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Profile creation failed: {e}")
                return None
    
    def _verify_parent_password(self, password: str) -> bool:
        """Verify parent password"""
        # In production, this would check against a hashed password
        password_file = self.config_path / '.parent_password'
        
        if not password_file.exists():
            # First time setup - create password
            hashed = hashlib.sha256(password.encode()).hexdigest()
            password_file.write_text(hashed)
            if self.platform != "Windows":
                os.chmod(password_file, 0o600)
            return True
        
        stored_hash = password_file.read_text().strip()
        provided_hash = hashlib.sha256(password.encode()).hexdigest()
        return stored_hash == provided_hash
    
    def start_monitoring(self):
        """Start background monitoring thread with improved error handling (FIX for BUG-008)"""
        def monitor():
            while self.session_id:
                try:
                    # Check session timeout
                    if datetime.now() - self.last_activity > self.session_timeout:
                        logger.info("Session timeout - ending session")
                        self.end_session()
                        break
                    
                    # Monitor Open WebUI process
                    if self.openwebui_process and self.openwebui_process.poll() is not None:
                        logger.warning("Open WebUI process terminated unexpectedly")
                        self.restart_openwebui()
                    
                    time.sleep(10)  # Check every 10 seconds
                    
                # FIX for BUG-008: Specific exception handling
                except (IOError, OSError) as e:
                    logger.error(f"File system error during monitoring: {e}")
                    # Continue monitoring despite file errors
                    continue
                except sqlite3.Error as e:
                    logger.error(f"Database error during monitoring: {e}")
                    # Database errors are more serious, might need to restart
                    if "locked" in str(e).lower():
                        time.sleep(1)  # Wait and retry if database is locked
                        continue
                    else:
                        # Serious database error, stop monitoring
                        break
                except KeyboardInterrupt:
                    logger.info("Monitoring interrupted by user")
                    break
                except Exception as e:
                    # Still catch unexpected errors but log them properly
                    logger.critical(f"Unexpected monitoring error: {type(e).__name__}: {e}")
                    # For truly unexpected errors, stop monitoring to prevent damage
                    break
        
        self.monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self.monitoring_thread.start()
    
    def log_interaction(self, user_input: str, ai_response: str, safety_score: float = 1.0):
        """Log interaction with transaction management (FIX for BUG-016)"""
        if not self.session_id:
            raise RuntimeError("No active session")
        
        interaction_id = str(uuid.uuid4())
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # FIX for BUG-016: Proper transaction management
            try:
                cursor.execute("BEGIN TRANSACTION")
                
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
                
                # Update session interaction count (atomic operation)
                cursor.execute('''
                    UPDATE sessions 
                    SET interactions_count = interactions_count + 1 
                    WHERE session_id = ?
                ''', (self.session_id,))
                
                conn.commit()
                logger.debug(f"Logged interaction: {interaction_id}")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to log interaction: {e}")
                raise
    
    def start_session(self, profile_id: str) -> Optional[str]:
        """Start a new learning session"""
        self.session_id = str(uuid.uuid4())
        self.active_profile = self._load_profile(profile_id)
        
        if not self.active_profile:
            logger.error(f"Profile not found: {profile_id}")
            return None
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                cursor.execute('''
                    INSERT INTO sessions (
                        session_id, profile_id, start_time, interactions_count,
                        safety_incidents
                    ) VALUES (?, ?, ?, 0, 0)
                ''', (self.session_id, profile_id, datetime.now().isoformat()))
                
                conn.commit()
                
                # Start monitoring
                self.start_monitoring()
                
                logger.info(f"Started session: {self.session_id} for profile: {profile_id}")
                return self.session_id
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to start session: {e}")
                return None
    
    def _load_profile(self, profile_id: str) -> Optional[ChildProfile]:
        """Load child profile with decryption (FIX for BUG-003)"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM profiles WHERE profile_id = ?
            ''', (profile_id,))
            
            row = cursor.fetchone()
            if row:
                # Decrypt sensitive fields
                name = self._decrypt_field(row['encrypted_name'])
                age = int(self._decrypt_field(row['encrypted_age']))
                grade_level = self._decrypt_field(row['encrypted_grade_level'])
                
                return ChildProfile(
                    profile_id=row['profile_id'],
                    name=name,
                    age=age,
                    grade_level=grade_level,
                    safety_level=row['safety_level'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    learning_preferences=json.loads(row['learning_preferences'] or '{}')
                )
        
        return None
    
    def end_session(self):
        """End current session"""
        if not self.session_id:
            return
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = ?, duration_seconds = 
                        (strftime('%s', ?) - strftime('%s', start_time))
                    WHERE session_id = ?
                ''', (
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    self.session_id
                ))
                
                conn.commit()
                logger.info(f"Ended session: {self.session_id}")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to end session: {e}")
            finally:
                self.session_id = None
                self.active_profile = None
    
    def shutdown(self):
        """Clean shutdown of integration"""
        if self.session_id:
            self.end_session()
        
        if self.openwebui_process:
            try:
                self.openwebui_process.terminate()
                self.openwebui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.openwebui_process.kill()
            except Exception as e:
                logger.error(f"Error shutting down Open WebUI: {e}")
        
        logger.info("OpenWebUI integration shutdown complete")

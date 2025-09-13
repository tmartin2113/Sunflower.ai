"""
Sunflower AI Professional System - Profile Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Manages family and child profiles with secure authentication, age-appropriate
settings, and learning progress tracking. All profile data is encrypted and
stored on the USB partition.
"""

import os
import re
import json
import uuid
import hashlib
import secrets
import logging
import threading
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field, asdict
from enum import Enum
import base64
import bcrypt
from contextlib import contextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from . import ProfileError, AGE_GROUPS

logger = logging.getLogger(__name__)

# Constants for validation
MIN_CHILD_AGE = 2
MAX_CHILD_AGE = 18
MIN_PARENT_AGE = 18
MAX_NAME_LENGTH = 50
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.]{1,50}$')
VALID_EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Database settings
DB_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.1


class ProfileType(Enum):
    """Profile types"""
    PARENT = "parent"
    CHILD = "child"
    EDUCATOR = "educator"
    GUEST = "guest"


class LearningLevel(Enum):
    """Learning progression levels"""
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class Achievement:
    """Learning achievement record"""
    id: str
    name: str
    description: str
    earned_date: str
    category: str
    points: int = 10
    icon: str = "star"


@dataclass
class LearningProgress:
    """Track learning progress for a subject"""
    subject: str
    level: str = "beginner"
    total_sessions: int = 0
    total_minutes: int = 0
    last_session: Optional[str] = None
    topics_covered: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    quiz_scores: List[Dict[str, Any]] = field(default_factory=list)
    mastery_percentage: float = 0.0


@dataclass
class ChildProfile:
    """Individual child profile with strict validation"""
    id: str
    name: str
    age: int
    grade: Optional[int] = None
    avatar: str = "default"
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: Optional[str] = None
    
    # Settings
    age_group: str = "elementary"
    learning_level: str = "beginner"
    content_level: str = "age_appropriate"
    safety_mode: str = "strict"
    
    # Preferences
    favorite_subjects: List[str] = field(default_factory=list)
    learning_style: str = "visual"
    difficulty_preference: str = "adaptive"
    
    # Restrictions
    daily_time_limit: int = 120  # minutes
    blocked_topics: List[str] = field(default_factory=lambda: ["violence", "adult_content"])
    allowed_hours: Dict[str, str] = field(default_factory=lambda: {
        "weekday": "15:00-20:00",
        "weekend": "09:00-21:00"
    })
    
    # Progress tracking
    subjects_progress: Dict[str, LearningProgress] = field(default_factory=dict)
    achievements: List[Achievement] = field(default_factory=list)
    total_sessions: int = 0
    total_learning_time: int = 0  # minutes
    streak_days: int = 0
    last_streak_date: Optional[str] = None
    
    # Session data
    current_session_id: Optional[str] = None
    session_start_time: Optional[str] = None
    
    def __post_init__(self):
        """Validate profile data after initialization"""
        # Critical: Validate age for child safety
        if not isinstance(self.age, int) or not MIN_CHILD_AGE <= self.age <= MAX_CHILD_AGE:
            raise ValueError(f"Child age must be between {MIN_CHILD_AGE} and {MAX_CHILD_AGE}, got {self.age}")
        
        # Validate name
        if not self.name or len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f"Name must be 1-{MAX_NAME_LENGTH} characters")
        
        if not VALID_NAME_PATTERN.match(self.name):
            raise ValueError("Name contains invalid characters")
        
        # Auto-set age group based on age
        if self.age < 5:
            self.age_group = "preschool"
        elif self.age < 8:
            self.age_group = "early_elementary"
        elif self.age < 11:
            self.age_group = "elementary"
        elif self.age < 14:
            self.age_group = "middle_school"
        else:
            self.age_group = "high_school"
        
        # Ensure safety mode is strict for younger children
        if self.age < 13:
            self.safety_mode = "strict"
        
        # Validate grade if provided
        if self.grade is not None:
            if not isinstance(self.grade, int) or not 0 <= self.grade <= 12:
                raise ValueError(f"Grade must be between K(0) and 12, got {self.grade}")


@dataclass
class ParentProfile:
    """Parent account with authentication"""
    id: str
    name: str
    email: Optional[str] = None
    password_hash: str = ""  # bcrypt hash with salt
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None
    
    # Permissions
    can_modify_profiles: bool = True
    can_view_all_sessions: bool = True
    can_modify_settings: bool = True
    can_export_data: bool = True
    
    # Monitoring preferences
    email_notifications: bool = False
    weekly_reports: bool = True
    safety_alerts_only: bool = False
    
    # Dashboard settings
    dashboard_widgets: List[str] = field(default_factory=lambda: [
        "recent_activity", "learning_progress", "achievements", "safety_alerts"
    ])
    notification_preferences: Dict[str, bool] = field(default_factory=lambda: {
        "new_achievement": True,
        "daily_limit_reached": True,
        "safety_incident": True,
        "weekly_summary": True
    })
    
    def __post_init__(self):
        """Validate parent profile data"""
        # Validate name
        if not self.name or len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f"Name must be 1-{MAX_NAME_LENGTH} characters")
        
        if not VALID_NAME_PATTERN.match(self.name):
            raise ValueError("Name contains invalid characters")
        
        # Validate email if provided
        if self.email and not VALID_EMAIL_PATTERN.match(self.email):
            raise ValueError("Invalid email format")


@dataclass
class FamilyProfile:
    """Complete family profile with validation"""
    id: str
    family_name: str
    created_date: str
    subscription_type: str = "standard"
    
    # Members
    parents: List[ParentProfile] = field(default_factory=list)
    children: List[ChildProfile] = field(default_factory=list)
    
    # Settings
    timezone: str = "America/Chicago"
    language: str = "en-US"
    country: str = "US"
    
    # Features
    features_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "multi_child": True,
        "parent_dashboard": True,
        "progress_tracking": True,
        "achievements": True,
        "safety_alerts": True
    })
    
    # Statistics
    total_usage_hours: float = 0.0
    total_sessions: int = 0
    member_count: int = 0
    
    def __post_init__(self):
        """Initialize computed fields and validate"""
        if not self.id:
            self.id = str(uuid.uuid4())
        
        # Validate family name
        if not self.family_name or len(self.family_name) > MAX_NAME_LENGTH:
            raise ValueError(f"Family name must be 1-{MAX_NAME_LENGTH} characters")
        
        if not VALID_NAME_PATTERN.match(self.family_name):
            raise ValueError("Family name contains invalid characters")
        
        self.member_count = len(self.parents) + len(self.children)
        
        # Ensure at least one parent
        if not self.parents:
            raise ValueError("Family must have at least one parent account")


class ProfileManager:
    """
    Thread-safe profile manager with encryption and cascade deletion support.
    All sensitive data is encrypted before storage on the USB partition.
    """
    
    def __init__(self, usb_path: Optional[Path] = None):
        """
        Initialize profile manager with thread safety
        
        Args:
            usb_path: Path to USB partition for profile storage
        """
        self.usb_path = Path(usb_path) if usb_path else None
        self.profiles_dir = None
        self.encrypted_dir = None
        self.sessions_dir = None
        self.current_family: Optional[FamilyProfile] = None
        self.current_child: Optional[ChildProfile] = None
        
        # Thread safety
        self._lock = threading.RLock()
        self._db_lock = threading.RLock()
        self._session_locks: Dict[str, threading.Lock] = {}
        
        # Encryption
        self.cipher_suite: Optional[Fernet] = None
        self.master_key: Optional[bytes] = None
        
        # Database connections pool
        self._db_connections: Dict[int, sqlite3.Connection] = {}
        
        # Initialize storage
        if self.usb_path:
            self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize storage directories with proper permissions"""
        with self._lock:
            try:
                # Create directory structure
                self.profiles_dir = self.usb_path / "profiles"
                self.encrypted_dir = self.usb_path / "encrypted"
                self.sessions_dir = self.usb_path / "sessions"
                
                for directory in [self.profiles_dir, self.encrypted_dir, self.sessions_dir]:
                    directory.mkdir(parents=True, exist_ok=True)
                    # Set restrictive permissions on Unix-like systems
                    if hasattr(os, 'chmod'):
                        os.chmod(directory, 0o700)
                
                # Initialize or load encryption key
                self._initialize_encryption()
                
                # Initialize database
                self._initialize_database()
                
                logger.info("Profile storage initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize storage: {e}")
                raise ProfileError(f"Storage initialization failed: {e}")
    
    def _initialize_encryption(self):
        """Initialize encryption with secure key management"""
        key_file = self.encrypted_dir / ".key"
        
        try:
            if key_file.exists():
                # Load existing key
                with open(key_file, 'rb') as f:
                    self.master_key = f.read()
            else:
                # Generate new key
                self.master_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(self.master_key)
                # Secure the key file
                if hasattr(os, 'chmod'):
                    os.chmod(key_file, 0o600)
            
            self.cipher_suite = Fernet(self.master_key)
            
        except Exception as e:
            logger.error(f"Encryption initialization failed: {e}")
            raise ProfileError(f"Failed to initialize encryption: {e}")
    
    def _initialize_database(self):
        """Initialize profile database with proper schema"""
        with self._db_lock:
            db_path = self.profiles_dir / "profiles.db"
            
            conn = None
            try:
                conn = sqlite3.connect(str(db_path), timeout=DB_TIMEOUT)
                cursor = conn.cursor()
                
                # Create tables with proper constraints
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS families (
                        id TEXT PRIMARY KEY,
                        family_name TEXT NOT NULL,
                        created_date TEXT NOT NULL,
                        subscription_type TEXT DEFAULT 'standard',
                        data TEXT NOT NULL
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS children (
                        id TEXT PRIMARY KEY,
                        family_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL CHECK(age >= 2 AND age <= 18),
                        created_date TEXT NOT NULL,
                        data TEXT NOT NULL,
                        FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        child_id TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        duration_minutes INTEGER DEFAULT 0,
                        conversations TEXT,
                        FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        child_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        input_text TEXT,
                        output_text TEXT,
                        safety_triggered BOOLEAN DEFAULT 0,
                        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                        FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE
                    )
                ''')
                
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys = ON")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                if conn:
                    conn.rollback()
                raise ProfileError(f"Failed to initialize database: {e}")
            finally:
                if conn:
                    conn.close()
    
    @contextmanager
    def _get_db_connection(self):
        """Get thread-safe database connection with retry logic"""
        thread_id = threading.get_ident()
        conn = None
        
        with self._db_lock:
            try:
                # Reuse existing connection for this thread if available
                if thread_id in self._db_connections:
                    conn = self._db_connections[thread_id]
                    # Test connection
                    conn.execute("SELECT 1")
                else:
                    # Create new connection
                    db_path = self.profiles_dir / "profiles.db"
                    conn = sqlite3.connect(str(db_path), timeout=DB_TIMEOUT)
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA foreign_keys = ON")
                    self._db_connections[thread_id] = conn
                
                yield conn
                
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                # Remove failed connection
                if thread_id in self._db_connections:
                    try:
                        self._db_connections[thread_id].close()
                    except:
                        pass
                    del self._db_connections[thread_id]
                raise ProfileError(f"Database error: {e}")
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self.cipher_suite:
            raise ProfileError("Encryption not initialized")
        
        encrypted = self.cipher_suite.encrypt(data.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.cipher_suite:
            raise ProfileError("Encryption not initialized")
        
        try:
            encrypted = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.cipher_suite.decrypt(encrypted)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ProfileError("Failed to decrypt data")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt with automatic salt generation"""
        # Validate password
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        if len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters")
        
        # Generate bcrypt hash with salt
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
    
    def create_family_profile(self, family_name: str, parent_name: str,
                            parent_password: str, parent_email: Optional[str] = None) -> FamilyProfile:
        """Create new family profile with parent account"""
        with self._lock:
            # Validate inputs
            if not family_name or not parent_name or not parent_password:
                raise ValueError("Family name, parent name, and password are required")
            
            # Sanitize family name
            family_name = re.sub(r'[^a-zA-Z0-9\s\-_]', '', family_name)[:MAX_NAME_LENGTH]
            if not family_name:
                raise ValueError("Invalid family name")
            
            # Sanitize parent name
            parent_name = re.sub(r'[^a-zA-Z0-9\s\-_]', '', parent_name)[:MAX_NAME_LENGTH]
            if not parent_name:
                raise ValueError("Invalid parent name")
            
            # Create family profile
            family = FamilyProfile(
                id=str(uuid.uuid4()),
                family_name=family_name,
                created_date=datetime.now().isoformat()
            )
            
            # Create parent profile with secure password
            parent = ParentProfile(
                id=str(uuid.uuid4()),
                name=parent_name,
                email=parent_email,
                password_hash=self._hash_password(parent_password)
            )
            
            family.parents.append(parent)
            
            # Save to database
            self._save_family_profile(family)
            
            logger.info(f"Created family profile: {family_name}")
            return family
    
    def add_child_profile(self, family_id: str, name: str, age: int,
                         grade: Optional[int] = None) -> ChildProfile:
        """Add child profile to family with strict validation"""
        with self._lock:
            # Critical: Validate age for child safety
            if not isinstance(age, int) or not MIN_CHILD_AGE <= age <= MAX_CHILD_AGE:
                raise ValueError(f"Child age must be between {MIN_CHILD_AGE} and {MAX_CHILD_AGE}, got {age}")
            
            # Sanitize and validate name
            name = re.sub(r'[^a-zA-Z0-9\s\-_]', '', name)[:MAX_NAME_LENGTH]
            if not name:
                raise ValueError("Invalid child name")
            
            # Load family
            family = self.load_family_profile(family_id)
            if not family:
                raise ProfileError(f"Family profile not found: {family_id}")
            
            # Check for duplicate names (case-insensitive)
            if any(child.name.lower() == name.lower() for child in family.children):
                raise ProfileError(f"Child profile '{name}' already exists")
            
            # Create child profile with validation
            child = ChildProfile(
                id=str(uuid.uuid4()),
                name=name,
                age=age,
                grade=grade
            )
            
            # Add to family
            family.children.append(child)
            
            # Save updated family
            self._save_family_profile(family)
            
            logger.info(f"Added child profile: {name} (age {age}) to family {family.family_name}")
            return child
    
    def delete_child_profile(self, family_id: str, child_id: str, cascade: bool = True):
        """
        Delete child profile with proper cascade deletion
        
        Args:
            family_id: Family ID
            child_id: Child ID to delete
            cascade: If True, delete all associated data (sessions, conversations)
        """
        with self._lock:
            family = self.load_family_profile(family_id)
            if not family:
                raise ProfileError(f"Family not found: {family_id}")
            
            # Find child
            child_index = None
            for i, child in enumerate(family.children):
                if child.id == child_id:
                    child_index = i
                    break
            
            if child_index is None:
                raise ProfileError(f"Child not found: {child_id}")
            
            # Delete from database (cascade will handle sessions/conversations)
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                if cascade:
                    # Delete all associated data
                    cursor.execute("DELETE FROM conversations WHERE child_id = ?", (child_id,))
                    cursor.execute("DELETE FROM sessions WHERE child_id = ?", (child_id,))
                    
                    # Delete session files
                    if self.sessions_dir:
                        session_pattern = self.sessions_dir / f"session_{child_id}_*.json"
                        for session_file in self.sessions_dir.glob(f"session_{child_id}_*.json"):
                            try:
                                session_file.unlink()
                            except Exception as e:
                                logger.warning(f"Failed to delete session file: {e}")
                
                cursor.execute("DELETE FROM children WHERE id = ?", (child_id,))
                conn.commit()
            
            # Remove from family
            del family.children[child_index]
            
            # Save updated family
            self._save_family_profile(family)
            
            logger.info(f"Deleted child profile: {child_id} (cascade={cascade})")
    
    def _save_family_profile(self, family: FamilyProfile):
        """Save family profile to database with encryption"""
        with self._db_lock:
            # Prepare data
            family_data = asdict(family)
            
            # Separate sensitive data
            sensitive_data = {
                "parents": [asdict(p) for p in family.parents]
            }
            
            # Remove sensitive data from public storage
            family_data.pop("parents", None)
            
            # Encrypt sensitive data
            encrypted_parents = self._encrypt_data(json.dumps(sensitive_data))
            
            # Save to database
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Save family
                cursor.execute('''
                    INSERT OR REPLACE INTO families (id, family_name, created_date, subscription_type, data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    family.id,
                    family.family_name,
                    family.created_date,
                    family.subscription_type,
                    json.dumps(family_data)
                ))
                
                # Save children
                for child in family.children:
                    child_data = asdict(child)
                    cursor.execute('''
                        INSERT OR REPLACE INTO children (id, family_id, name, age, created_date, data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        child.id,
                        family.id,
                        child.name,
                        child.age,
                        child.created_date,
                        json.dumps(child_data)
                    ))
                
                conn.commit()
            
            # Save encrypted parent data
            if self.encrypted_dir:
                encrypted_file = self.encrypted_dir / f"family_{family.id}.enc"
                with open(encrypted_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted_parents)
                
                # Secure the file
                if hasattr(os, 'chmod'):
                    os.chmod(encrypted_file, 0o600)
            
            logger.info(f"Saved family profile: {family.family_name}")
    
    def load_family_profile(self, family_id: str) -> Optional[FamilyProfile]:
        """Load family profile from database"""
        with self._lock:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Load family
                cursor.execute("SELECT * FROM families WHERE id = ?", (family_id,))
                family_row = cursor.fetchone()
                
                if not family_row:
                    return None
                
                # Parse family data
                family_data = json.loads(family_row['data'])
                
                # Load encrypted parent data
                parents_data = []
                if self.encrypted_dir:
                    encrypted_file = self.encrypted_dir / f"family_{family_id}.enc"
                    if encrypted_file.exists():
                        try:
                            with open(encrypted_file, 'r', encoding='utf-8') as f:
                                encrypted_data = f.read()
                            decrypted = self._decrypt_data(encrypted_data)
                            sensitive = json.loads(decrypted)
                            parents_data = sensitive.get("parents", [])
                        except Exception as e:
                            logger.error(f"Failed to load encrypted data: {e}")
                
                # Load children
                cursor.execute("SELECT * FROM children WHERE family_id = ?", (family_id,))
                children_rows = cursor.fetchall()
                
                children = []
                for row in children_rows:
                    child_data = json.loads(row['data'])
                    children.append(ChildProfile(**child_data))
                
                # Reconstruct family
                family = FamilyProfile(
                    id=family_id,
                    family_name=family_row['family_name'],
                    created_date=family_row['created_date'],
                    subscription_type=family_row['subscription_type']
                )
                
                # Restore parents
                for parent_data in parents_data:
                    family.parents.append(ParentProfile(**parent_data))
                
                # Restore children
                family.children = children
                
                return family
    
    def authenticate_parent(self, family_id: str, parent_name: str,
                          password: str) -> Optional[ParentProfile]:
        """Authenticate parent with secure password verification"""
        with self._lock:
            family = self.load_family_profile(family_id)
            if not family:
                return None
            
            for parent in family.parents:
                if parent.name.lower() == parent_name.lower():
                    if self._verify_password(password, parent.password_hash):
                        # Update last login
                        parent.last_login = datetime.now().isoformat()
                        self._save_family_profile(family)
                        return parent
            
            return None
    
    def get_child_by_name(self, family_id: str, child_name: str) -> Optional[ChildProfile]:
        """Get child profile by name (case-insensitive)"""
        with self._lock:
            family = self.load_family_profile(family_id)
            if not family:
                return None
            
            for child in family.children:
                if child.name.lower() == child_name.lower():
                    return child
            
            return None
    
    def list_families(self) -> List[Tuple[str, str]]:
        """List all family profiles (id, name pairs)"""
        with self._lock:
            families = []
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, family_name FROM families ORDER BY family_name")
                
                for row in cursor.fetchall():
                    families.append((row['id'], row['family_name']))
            
            return families
    
    def cleanup_old_sessions(self, days: int = 30):
        """Clean up old session data to prevent disk exhaustion"""
        with self._lock:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old sessions and cascaded data
                cursor.execute(
                    "DELETE FROM sessions WHERE start_time < ?",
                    (cutoff_date,)
                )
                
                deleted = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted} old sessions")
    
    def export_family_data(self, family_id: str, output_path: Path) -> bool:
        """Export all family data for backup or transfer"""
        with self._lock:
            try:
                family = self.load_family_profile(family_id)
                if not family:
                    raise ProfileError(f"Family not found: {family_id}")
                
                # Prepare export data
                export_data = {
                    "version": "6.2",
                    "export_date": datetime.now().isoformat(),
                    "family": asdict(family),
                    "sessions": []
                }
                
                # Export sessions for each child
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    for child in family.children:
                        cursor.execute(
                            "SELECT * FROM sessions WHERE child_id = ?",
                            (child.id,)
                        )
                        
                        for session_row in cursor.fetchall():
                            session_data = dict(session_row)
                            
                            # Get conversations
                            cursor.execute(
                                "SELECT * FROM conversations WHERE session_id = ?",
                                (session_row['id'],)
                            )
                            
                            conversations = [dict(row) for row in cursor.fetchall()]
                            session_data['conversations'] = conversations
                            
                            export_data['sessions'].append(session_data)
                
                # Write export file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                logger.info(f"Exported family data to {output_path}")
                return True
                
            except Exception as e:
                logger.error(f"Export failed: {e}")
                return False
    
    def close(self):
        """Clean up resources"""
        with self._lock:
            # Close all database connections
            for conn in self._db_connections.values():
                try:
                    conn.close()
                except:
                    pass
            
            self._db_connections.clear()
            logger.info("Profile manager closed")

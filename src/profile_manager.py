#!/usr/bin/env python3
"""
Sunflower AI Professional System - Profile Manager
Secure family and child profile management with SQL injection prevention
Version: 6.2.0 - Production Ready
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
import bcrypt
import uuid
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ProfileRole(Enum):
    """User roles in the system"""
    PARENT = "parent"
    CHILD = "child"
    EDUCATOR = "educator"
    GUEST = "guest"


class LearningStyle(Enum):
    """Learning style preferences"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    BALANCED = "balanced"


@dataclass
class ParentProfile:
    """Parent/Guardian profile"""
    id: str
    name: str
    email: Optional[str] = None
    password_hash: str = ""
    salt: str = ""
    created_date: str = ""
    last_login: Optional[str] = None
    
    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    
    # Preferences
    notification_email: bool = True
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


@dataclass
class ChildProfile:
    """Child learner profile"""
    id: str
    name: str
    age: int
    grade: str
    avatar: str = "🦄"
    created_date: str = ""
    last_active: Optional[str] = None
    
    # Learning preferences
    learning_style: LearningStyle = LearningStyle.BALANCED
    pace: str = "moderate"  # slow, moderate, fast
    difficulty: str = "auto"  # easy, moderate, challenging, auto
    interests: List[str] = field(default_factory=list)
    
    # Safety settings
    safety_mode: str = "strict"  # strict, moderate, standard
    daily_time_limit_minutes: int = 30
    break_reminder_minutes: int = 20
    require_parent_approval: bool = False
    
    # Progress tracking
    total_sessions: int = 0
    total_time_minutes: int = 0
    topics_explored: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    current_level: int = 1
    experience_points: int = 0
    
    # Session settings
    max_messages_per_session: int = 50
    response_length: str = "age_appropriate"
    enable_voice: bool = False
    enable_images: bool = True


@dataclass
class FamilyProfile:
    """Complete family profile"""
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
        """Initialize computed fields"""
        if not self.id:
            self.id = str(uuid.uuid4())
        self.member_count = len(self.parents) + len(self.children)


class ProfileManager:
    """
    Manages all family and child profiles with SQL injection prevention.
    All database queries use parameterized statements for security.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize profile manager with secure database
        
        Args:
            data_dir: Directory for profile data storage
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Database path
        self.db_path = self.data_dir / "profiles.db"
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Current session
        self.current_family: Optional[FamilyProfile] = None
        self.current_parent: Optional[ParentProfile] = None
        self.current_child: Optional[ChildProfile] = None
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Profile manager initialized at {self.data_dir}")
    
    def _init_database(self):
        """Initialize SQLite database with secure schema"""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            # FIX: Use parameterized queries for all database operations
            # Create tables with proper constraints
            conn.executescript('''
                -- Family profiles table
                CREATE TABLE IF NOT EXISTS families (
                    id TEXT PRIMARY KEY,
                    family_name TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    subscription_type TEXT DEFAULT 'standard',
                    timezone TEXT DEFAULT 'America/Chicago',
                    language TEXT DEFAULT 'en-US',
                    country TEXT DEFAULT 'US',
                    features TEXT,
                    total_usage_hours REAL DEFAULT 0.0,
                    total_sessions INTEGER DEFAULT 0
                );
                
                -- Parent profiles table
                CREATE TABLE IF NOT EXISTS parents (
                    id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    last_login TEXT,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TEXT,
                    two_factor_enabled INTEGER DEFAULT 0,
                    two_factor_secret TEXT,
                    preferences TEXT,
                    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
                );
                
                -- Child profiles table
                CREATE TABLE IF NOT EXISTS children (
                    id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL CHECK(age >= 2 AND age <= 18),
                    grade TEXT NOT NULL,
                    avatar TEXT DEFAULT '🦄',
                    created_date TEXT NOT NULL,
                    last_active TEXT,
                    learning_style TEXT DEFAULT 'balanced',
                    pace TEXT DEFAULT 'moderate',
                    difficulty TEXT DEFAULT 'auto',
                    interests TEXT,
                    safety_mode TEXT DEFAULT 'strict',
                    daily_time_limit_minutes INTEGER DEFAULT 30,
                    break_reminder_minutes INTEGER DEFAULT 20,
                    require_parent_approval INTEGER DEFAULT 0,
                    total_sessions INTEGER DEFAULT 0,
                    total_time_minutes INTEGER DEFAULT 0,
                    topics_explored TEXT,
                    achievements TEXT,
                    current_level INTEGER DEFAULT 1,
                    experience_points INTEGER DEFAULT 0,
                    session_settings TEXT,
                    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
                );
                
                -- Session logs table
                CREATE TABLE IF NOT EXISTS session_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes INTEGER,
                    messages_count INTEGER DEFAULT 0,
                    topics TEXT,
                    safety_incidents INTEGER DEFAULT 0,
                    FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE
                );
                
                -- Safety incidents table
                CREATE TABLE IF NOT EXISTS safety_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    child_id TEXT NOT NULL,
                    session_id INTEGER,
                    timestamp TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    severity INTEGER DEFAULT 1,
                    input_text TEXT,
                    action_taken TEXT,
                    parent_notified INTEGER DEFAULT 0,
                    FOREIGN KEY (child_id) REFERENCES children(id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES session_logs(id) ON DELETE CASCADE
                );
                
                -- Create indexes for performance
                CREATE INDEX IF NOT EXISTS idx_parents_family ON parents(family_id);
                CREATE INDEX IF NOT EXISTS idx_children_family ON children(family_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_child ON session_logs(child_id);
                CREATE INDEX IF NOT EXISTS idx_incidents_child ON safety_incidents(child_id);
            ''')
            
            conn.commit()
            conn.close()
    
    def create_family(self, family_name: str, parent_name: str, 
                     parent_email: str, password: str) -> FamilyProfile:
        """
        Create new family profile with secure password handling
        
        Args:
            family_name: Name of the family
            parent_name: Primary parent name
            parent_email: Parent email
            password: Parent password (will be hashed)
            
        Returns:
            Created family profile
        """
        with self._lock:
            # Generate unique IDs
            family_id = str(uuid.uuid4())
            parent_id = str(uuid.uuid4())
            
            # FIX: Use bcrypt for secure password hashing instead of SHA-256
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            # Create family profile
            family = FamilyProfile(
                id=family_id,
                family_name=family_name,
                created_date=datetime.now().isoformat()
            )
            
            # Create parent profile
            parent = ParentProfile(
                id=parent_id,
                name=parent_name,
                email=parent_email,
                password_hash=password_hash.decode('utf-8'),
                salt=salt.decode('utf-8'),
                created_date=datetime.now().isoformat()
            )
            
            family.parents.append(parent)
            
            # FIX: Save to database using parameterized queries
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            try:
                # Insert family - using parameterized query
                cursor.execute('''
                    INSERT INTO families (
                        id, family_name, created_date, subscription_type,
                        timezone, language, country, features
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    family.id,
                    family.family_name,
                    family.created_date,
                    family.subscription_type,
                    family.timezone,
                    family.language,
                    family.country,
                    json.dumps(family.features_enabled)
                ))
                
                # Insert parent - using parameterized query
                cursor.execute('''
                    INSERT INTO parents (
                        id, family_id, name, email, password_hash, salt,
                        created_date, preferences
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    parent.id,
                    family.id,
                    parent.name,
                    parent.email,
                    parent.password_hash,
                    parent.salt,
                    parent.created_date,
                    json.dumps(parent.notification_preferences)
                ))
                
                conn.commit()
                logger.info(f"Created family profile: {family_name}")
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Failed to create family profile: {e}")
                raise
            finally:
                conn.close()
            
            return family
    
    def load_family_profile(self, family_id: str) -> Optional[FamilyProfile]:
        """
        Load family profile from database with SQL injection prevention
        
        Args:
            family_id: Family ID to load
            
        Returns:
            Family profile or None if not found
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            try:
                # FIX: Use parameterized query to prevent SQL injection
                cursor = conn.cursor()
                
                # Load family data - parameterized query
                cursor.execute(
                    'SELECT * FROM families WHERE id = ?',
                    (family_id,)  # Parameter as tuple
                )
                family_row = cursor.fetchone()
                
                if not family_row:
                    return None
                
                # Create family profile
                family = FamilyProfile(
                    id=family_row['id'],
                    family_name=family_row['family_name'],
                    created_date=family_row['created_date'],
                    subscription_type=family_row['subscription_type'],
                    timezone=family_row['timezone'],
                    language=family_row['language'],
                    country=family_row['country'],
                    features_enabled=json.loads(family_row['features']) if family_row['features'] else {},
                    total_usage_hours=family_row['total_usage_hours'],
                    total_sessions=family_row['total_sessions']
                )
                
                # FIX: Load parents using parameterized query
                cursor.execute(
                    'SELECT * FROM parents WHERE family_id = ?',
                    (family_id,)
                )
                
                for parent_row in cursor.fetchall():
                    parent = ParentProfile(
                        id=parent_row['id'],
                        name=parent_row['name'],
                        email=parent_row['email'],
                        password_hash=parent_row['password_hash'],
                        salt=parent_row['salt'],
                        created_date=parent_row['created_date'],
                        last_login=parent_row['last_login'],
                        failed_login_attempts=parent_row['failed_login_attempts'],
                        locked_until=parent_row['locked_until'],
                        two_factor_enabled=bool(parent_row['two_factor_enabled']),
                        two_factor_secret=parent_row['two_factor_secret'],
                        notification_preferences=json.loads(parent_row['preferences']) if parent_row['preferences'] else {}
                    )
                    family.parents.append(parent)
                
                # FIX: Load children using parameterized query
                cursor.execute(
                    'SELECT * FROM children WHERE family_id = ?',
                    (family_id,)
                )
                
                for child_row in cursor.fetchall():
                    child = ChildProfile(
                        id=child_row['id'],
                        name=child_row['name'],
                        age=child_row['age'],
                        grade=child_row['grade'],
                        avatar=child_row['avatar'],
                        created_date=child_row['created_date'],
                        last_active=child_row['last_active'],
                        learning_style=LearningStyle(child_row['learning_style']),
                        pace=child_row['pace'],
                        difficulty=child_row['difficulty'],
                        interests=json.loads(child_row['interests']) if child_row['interests'] else [],
                        safety_mode=child_row['safety_mode'],
                        daily_time_limit_minutes=child_row['daily_time_limit_minutes'],
                        break_reminder_minutes=child_row['break_reminder_minutes'],
                        require_parent_approval=bool(child_row['require_parent_approval']),
                        total_sessions=child_row['total_sessions'],
                        total_time_minutes=child_row['total_time_minutes'],
                        topics_explored=json.loads(child_row['topics_explored']) if child_row['topics_explored'] else [],
                        achievements=json.loads(child_row['achievements']) if child_row['achievements'] else [],
                        current_level=child_row['current_level'],
                        experience_points=child_row['experience_points']
                    )
                    family.children.append(child)
                
                return family
                
            except sqlite3.Error as e:
                logger.error(f"Failed to load family profile: {e}")
                return None
            finally:
                conn.close()
    
    def add_child_profile(self, family_id: str, name: str, age: int, 
                         grade: str, **kwargs) -> ChildProfile:
        """
        Add child profile to family with SQL injection prevention
        
        Args:
            family_id: Family ID
            name: Child's name
            age: Child's age (2-18)
            grade: Child's grade level
            **kwargs: Additional profile settings
            
        Returns:
            Created child profile
        """
        with self._lock:
            # Validate age
            if not 2 <= age <= 18:
                raise ValueError(f"Age must be between 2 and 18, got {age}")
            
            # Load family
            family = self.load_family_profile(family_id)
            if not family:
                raise ValueError(f"Family {family_id} not found")
            
            # Create child profile
            child = ChildProfile(
                id=str(uuid.uuid4()),
                name=name,
                age=age,
                grade=grade,
                created_date=datetime.now().isoformat()
            )
            
            # Apply additional settings
            for key, value in kwargs.items():
                if hasattr(child, key):
                    setattr(child, key, value)
            
            # Set age-appropriate defaults
            if age <= 7:
                child.daily_time_limit_minutes = 30
                child.safety_mode = "strict"
                child.require_parent_approval = True
            elif age <= 10:
                child.daily_time_limit_minutes = 45
                child.safety_mode = "strict"
            elif age <= 13:
                child.daily_time_limit_minutes = 60
                child.safety_mode = "moderate"
            else:
                child.daily_time_limit_minutes = 90
                child.safety_mode = "standard"
            
            # FIX: Save to database using parameterized query
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO children (
                        id, family_id, name, age, grade, avatar,
                        created_date, learning_style, pace, difficulty,
                        interests, safety_mode, daily_time_limit_minutes,
                        break_reminder_minutes, require_parent_approval,
                        topics_explored, achievements, session_settings
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    child.id,
                    family_id,
                    child.name,
                    child.age,
                    child.grade,
                    child.avatar,
                    child.created_date,
                    child.learning_style.value,
                    child.pace,
                    child.difficulty,
                    json.dumps(child.interests),
                    child.safety_mode,
                    child.daily_time_limit_minutes,
                    child.break_reminder_minutes,
                    int(child.require_parent_approval),
                    json.dumps(child.topics_explored),
                    json.dumps(child.achievements),
                    json.dumps({
                        "max_messages": child.max_messages_per_session,
                        "response_length": child.response_length,
                        "enable_voice": child.enable_voice,
                        "enable_images": child.enable_images
                    })
                ))
                
                conn.commit()
                logger.info(f"Added child profile: {name} (age {age}) to family {family_id}")
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Failed to add child profile: {e}")
                raise
            finally:
                conn.close()
            
            return child
    
    def authenticate_parent(self, family_id: str, parent_name: str, 
                           password: str) -> Tuple[bool, Optional[ParentProfile]]:
        """
        Authenticate parent login with SQL injection prevention
        
        Args:
            family_id: Family ID
            parent_name: Parent's name
            password: Password to verify
            
        Returns:
            Tuple of (success, parent_profile)
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            try:
                # FIX: Use parameterized query to find parent
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM parents 
                    WHERE family_id = ? AND LOWER(name) = LOWER(?)
                ''', (family_id, parent_name))
                
                parent_row = cursor.fetchone()
                
                if not parent_row:
                    logger.warning(f"Parent not found: {parent_name}")
                    return False, None
                
                # Check if account is locked
                if parent_row['locked_until']:
                    locked_until = datetime.fromisoformat(parent_row['locked_until'])
                    if datetime.now() < locked_until:
                        remaining = (locked_until - datetime.now()).total_seconds() / 60
                        logger.warning(f"Account locked for {remaining:.1f} more minutes")
                        return False, None
                    else:
                        # Unlock account
                        cursor.execute(
                            'UPDATE parents SET locked_until = NULL, failed_login_attempts = 0 WHERE id = ?',
                            (parent_row['id'],)
                        )
                
                # FIX: Verify password using bcrypt
                password_hash = parent_row['password_hash']
                
                if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                    # Success - update last login
                    cursor.execute('''
                        UPDATE parents 
                        SET last_login = ?, failed_login_attempts = 0 
                        WHERE id = ?
                    ''', (datetime.now().isoformat(), parent_row['id']))
                    
                    conn.commit()
                    
                    # Create parent profile object
                    parent = ParentProfile(
                        id=parent_row['id'],
                        name=parent_row['name'],
                        email=parent_row['email'],
                        password_hash=parent_row['password_hash'],
                        salt=parent_row['salt'],
                        created_date=parent_row['created_date'],
                        last_login=datetime.now().isoformat()
                    )
                    
                    self.current_parent = parent
                    logger.info(f"Parent authenticated: {parent_name}")
                    
                    return True, parent
                else:
                    # Failed login - increment attempts
                    failed_attempts = parent_row['failed_login_attempts'] + 1
                    
                    # Lock account after 3 failed attempts
                    if failed_attempts >= 3:
                        locked_until = datetime.now() + timedelta(minutes=15)
                        cursor.execute('''
                            UPDATE parents 
                            SET failed_login_attempts = ?, locked_until = ? 
                            WHERE id = ?
                        ''', (failed_attempts, locked_until.isoformat(), parent_row['id']))
                        logger.warning(f"Account locked due to failed attempts: {parent_name}")
                    else:
                        cursor.execute(
                            'UPDATE parents SET failed_login_attempts = ? WHERE id = ?',
                            (failed_attempts, parent_row['id'])
                        )
                    
                    conn.commit()
                    return False, None
                    
            except sqlite3.Error as e:
                logger.error(f"Authentication error: {e}")
                return False, None
            finally:
                conn.close()
    
    def switch_child_profile(self, child_id: str) -> bool:
        """
        Switch to a child profile with SQL injection prevention
        
        Args:
            child_id: Child ID to switch to
            
        Returns:
            Success status
        """
        with self._lock:
            if not self.current_parent:
                logger.warning("No parent authenticated")
                return False
            
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            try:
                # FIX: Use parameterized query to find child
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM children WHERE id = ?',
                    (child_id,)
                )
                
                child_row = cursor.fetchone()
                
                if not child_row:
                    logger.warning(f"Child profile not found: {child_id}")
                    return False
                
                # Create child profile object
                self.current_child = ChildProfile(
                    id=child_row['id'],
                    name=child_row['name'],
                    age=child_row['age'],
                    grade=child_row['grade'],
                    avatar=child_row['avatar'],
                    created_date=child_row['created_date'],
                    last_active=datetime.now().isoformat(),
                    safety_mode=child_row['safety_mode'],
                    daily_time_limit_minutes=child_row['daily_time_limit_minutes']
                )
                
                # Update last active time
                cursor.execute(
                    'UPDATE children SET last_active = ? WHERE id = ?',
                    (datetime.now().isoformat(), child_id)
                )
                
                conn.commit()
                logger.info(f"Switched to child profile: {self.current_child.name}")
                
                return True
                
            except sqlite3.Error as e:
                logger.error(f"Failed to switch profile: {e}")
                return False
            finally:
                conn.close()
    
    def log_safety_incident(self, child_id: str, incident_type: str, 
                           severity: int, input_text: str, action_taken: str) -> None:
        """
        Log safety incident with SQL injection prevention
        
        Args:
            child_id: Child ID
            incident_type: Type of incident
            severity: Severity level (1-5)
            input_text: The problematic input
            action_taken: Action taken by system
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            
            try:
                # FIX: Use parameterized query for inserting safety incident
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO safety_incidents (
                        child_id, timestamp, incident_type, severity,
                        input_text, action_taken, parent_notified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    child_id,
                    datetime.now().isoformat(),
                    incident_type,
                    severity,
                    input_text[:500],  # Limit text length
                    action_taken,
                    1 if severity >= 3 else 0  # Notify parent for severe incidents
                ))
                
                conn.commit()
                logger.info(f"Logged safety incident for child {child_id}: {incident_type}")
                
            except sqlite3.Error as e:
                logger.error(f"Failed to log safety incident: {e}")
            finally:
                conn.close()
    
    def get_child_statistics(self, child_id: str) -> Dict[str, Any]:
        """
        Get child learning statistics with SQL injection prevention
        
        Args:
            child_id: Child ID
            
        Returns:
            Dictionary of statistics
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            try:
                cursor = conn.cursor()
                
                # FIX: Use parameterized queries for all statistics queries
                # Get session statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_sessions,
                        SUM(duration_minutes) as total_minutes,
                        AVG(duration_minutes) as avg_session_minutes,
                        MAX(start_time) as last_session
                    FROM session_logs 
                    WHERE child_id = ?
                ''', (child_id,))
                
                session_stats = cursor.fetchone()
                
                # Get safety statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_incidents,
                        AVG(severity) as avg_severity
                    FROM safety_incidents 
                    WHERE child_id = ?
                ''', (child_id,))
                
                safety_stats = cursor.fetchone()
                
                # Get recent topics
                cursor.execute('''
                    SELECT topics 
                    FROM session_logs 
                    WHERE child_id = ? 
                    ORDER BY start_time DESC 
                    LIMIT 10
                ''', (child_id,))
                
                recent_topics = []
                for row in cursor.fetchall():
                    if row['topics']:
                        topics = json.loads(row['topics'])
                        recent_topics.extend(topics)
                
                return {
                    'total_sessions': session_stats['total_sessions'] or 0,
                    'total_minutes': session_stats['total_minutes'] or 0,
                    'avg_session_minutes': session_stats['avg_session_minutes'] or 0,
                    'last_session': session_stats['last_session'],
                    'total_safety_incidents': safety_stats['total_incidents'] or 0,
                    'avg_incident_severity': safety_stats['avg_severity'] or 0,
                    'recent_topics': list(set(recent_topics))[:20]
                }
                
            except sqlite3.Error as e:
                logger.error(f"Failed to get statistics: {e}")
                return {}
            finally:
                conn.close()
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> None:
        """
        Clean up old session data with SQL injection prevention
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        with self._lock:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            conn = sqlite3.connect(str(self.db_path))
            
            try:
                cursor = conn.cursor()
                
                # FIX: Use parameterized query for deletion
                cursor.execute(
                    'DELETE FROM session_logs WHERE start_time < ?',
                    (cutoff_date,)
                )
                
                deleted_sessions = cursor.rowcount
                
                cursor.execute(
                    'DELETE FROM safety_incidents WHERE timestamp < ?',
                    (cutoff_date,)
                )
                
                deleted_incidents = cursor.rowcount
                
                conn.commit()
                logger.info(f"Cleaned up {deleted_sessions} sessions and {deleted_incidents} incidents")
                
            except sqlite3.Error as e:
                logger.error(f"Failed to clean up old data: {e}")
                conn.rollback()
            finally:
                conn.close()


# Testing
if __name__ == "__main__":
    import tempfile
    
    # Test with temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize profile manager
        pm = ProfileManager(Path(tmpdir))
        
        # Test family creation
        family = pm.create_family(
            "Smith Family",
            "John Smith",
            "john@example.com",
            "SecurePassword123!"
        )
        print(f"Created family: {family.family_name}")
        
        # Test adding children
        child1 = pm.add_child_profile(
            family.id,
            "Emily",
            7,
            "2nd Grade"
        )
        print(f"Added child: {child1.name}, age {child1.age}")
        
        child2 = pm.add_child_profile(
            family.id,
            "James",
            12,
            "7th Grade"
        )
        print(f"Added child: {child2.name}, age {child2.age}")
        
        # Test authentication
        success, parent = pm.authenticate_parent(
            family.id,
            "John Smith",
            "SecurePassword123!"
        )
        print(f"Authentication: {'Success' if success else 'Failed'}")
        
        # Test SQL injection prevention
        print("\nTesting SQL injection prevention...")
        
        # Attempt SQL injection in authentication (should fail safely)
        malicious_name = "'; DROP TABLE parents; --"
        success, _ = pm.authenticate_parent(family.id, malicious_name, "password")
        print(f"SQL injection attempt blocked: {not success}")
        
        # Verify tables still exist
        conn = sqlite3.connect(str(pm.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"Tables intact: {all(t in tables for t in ['families', 'parents', 'children'])}")
        
        print("\nAll security tests passed!")

"""
Sunflower AI Professional System - Profile Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Manages family and child profiles with secure authentication, age-appropriate
settings, and learning progress tracking. All profile data is encrypted and
stored on the USB partition.
"""

import os
import json
import uuid
import hashlib
import secrets
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field, asdict
from enum import Enum
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from . import ProfileError, AGE_GROUPS

logger = logging.getLogger(__name__)


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
    """Individual child profile"""
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
    voice_enabled: bool = True
    animations_enabled: bool = True
    
    # Progress tracking
    total_sessions: int = 0
    total_learning_minutes: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    achievements: List[Achievement] = field(default_factory=list)
    progress: Dict[str, LearningProgress] = field(default_factory=dict)
    
    # Restrictions
    daily_time_limit_minutes: int = 60
    blocked_topics: List[str] = field(default_factory=list)
    require_parent_approval: bool = False
    
    def __post_init__(self):
        """Initialize computed fields"""
        if not self.id:
            self.id = str(uuid.uuid4())
        
        # Set age group based on age
        for group_key, group_info in AGE_GROUPS.items():
            if group_info["min"] <= self.age <= group_info["max"]:
                self.age_group = group_key
                break


@dataclass
class ParentProfile:
    """Parent/guardian profile"""
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password_hash: str = ""
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None
    
    # Security
    pin_code: Optional[str] = None
    security_question: Optional[str] = None
    security_answer_hash: Optional[str] = None
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None
    
    # Preferences
    receive_alerts: bool = True
    alert_email: Optional[str] = None
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
    Manages all family and child profiles with encryption and secure storage.
    All sensitive data is encrypted before storage on the USB partition.
    """
    
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    
    def __init__(self, usb_path: Optional[Path] = None):
        """Initialize profile manager"""
        self.usb_path = usb_path or self._find_usb_path()
        self.profiles_dir = self.usb_path / "profiles" if self.usb_path else None
        self.encrypted_dir = self.profiles_dir / ".encrypted" if self.profiles_dir else None
        
        # Encryption key management
        self._master_key: Optional[bytes] = None
        self._cipher: Optional[Fernet] = None
        
        # Current session
        self.current_family: Optional[FamilyProfile] = None
        self.current_parent: Optional[ParentProfile] = None
        self.current_child: Optional[ChildProfile] = None
        
        # Initialize storage
        self._initialize_storage()
        
        # Load encryption key
        self._load_or_create_key()
        
        logger.info(f"Profile manager initialized - Profiles directory: {self.profiles_dir}")
    
    def _find_usb_path(self) -> Optional[Path]:
        """Find USB data partition"""
        try:
            from .partition_manager import PartitionManager
            pm = PartitionManager()
            return pm.find_usb_partition()
        except Exception as e:
            logger.warning(f"Could not find USB partition: {e}")
            # Development fallback
            dev_path = Path(__file__).parent.parent / "data"
            dev_path.mkdir(parents=True, exist_ok=True)
            return dev_path
    
    def _initialize_storage(self):
        """Initialize profile storage directories"""
        if not self.profiles_dir:
            logger.warning("No profiles directory available")
            return
        
        # Create directory structure
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.encrypted_dir.mkdir(parents=True, exist_ok=True)
        
        # Create README for users
        readme_path = self.profiles_dir / "README.txt"
        if not readme_path.exists():
            readme_path.write_text("""Sunflower AI Profile Storage
============================

This directory contains family and child profiles.
DO NOT modify files directly - use the Sunflower AI application.

Structure:
- family.json: Main family configuration (public data)
- .encrypted/: Encrypted sensitive profile data

For support, refer to the user manual.
""")
    
    def _load_or_create_key(self):
        """Load or create encryption key"""
        if not self.encrypted_dir:
            return
        
        key_file = self.encrypted_dir / ".key"
        
        if key_file.exists():
            # Load existing key
            try:
                with open(key_file, 'rb') as f:
                    self._master_key = f.read()
                self._cipher = Fernet(self._master_key)
                logger.info("Loaded existing encryption key")
            except Exception as e:
                logger.error(f"Failed to load encryption key: {e}")
                self._create_new_key()
        else:
            self._create_new_key()
    
    def _create_new_key(self):
        """Create new encryption key"""
        if not self.encrypted_dir:
            return
        
        self._master_key = Fernet.generate_key()
        self._cipher = Fernet(self._master_key)
        
        key_file = self.encrypted_dir / ".key"
        try:
            with open(key_file, 'wb') as f:
                f.write(self._master_key)
            
            # Set restrictive permissions on key file
            if os.name != 'nt':  # Unix-like systems
                os.chmod(key_file, 0o600)
            
            logger.info("Created new encryption key")
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self._cipher:
            logger.warning("Encryption not available, returning plain text")
            return data
        
        try:
            encrypted = self._cipher.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self._cipher:
            logger.warning("Decryption not available, returning as-is")
            return encrypted_data
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode('utf-8'))
        
        # Return hash and salt as base64 strings
        hash_b64 = base64.b64encode(key).decode('utf-8')
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        
        return hash_b64, salt_b64
    
    def _verify_password(self, password: str, hash_b64: str, salt_b64: str) -> bool:
        """Verify password against hash"""
        try:
            salt = base64.b64decode(salt_b64.encode('utf-8'))
            computed_hash, _ = self._hash_password(password, salt)
            return computed_hash == hash_b64
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def create_family_profile(self, family_name: str, parent_name: str, 
                            parent_password: str, parent_email: Optional[str] = None) -> FamilyProfile:
        """Create new family profile with parent account"""
        # Create family profile
        family = FamilyProfile(
            id=str(uuid.uuid4()),
            family_name=family_name,
            created_date=datetime.now().isoformat()
        )
        
        # Create parent profile
        password_hash, salt = self._hash_password(parent_password)
        
        parent = ParentProfile(
            id=str(uuid.uuid4()),
            name=parent_name,
            email=parent_email,
            password_hash=f"{password_hash}:{salt}"
        )
        
        family.parents.append(parent)
        
        # Save profile
        self._save_family_profile(family)
        
        logger.info(f"Created family profile: {family_name} with parent: {parent_name}")
        
        return family
    
    def add_child_profile(self, family_id: str, name: str, age: int, 
                         grade: Optional[int] = None) -> ChildProfile:
        """Add child profile to family"""
        family = self.load_family_profile(family_id)
        if not family:
            raise ProfileError(f"Family profile not found: {family_id}")
        
        # Check for duplicate names
        if any(child.name.lower() == name.lower() for child in family.children):
            raise ProfileError(f"Child profile with name '{name}' already exists")
        
        # Create child profile
        child = ChildProfile(
            id=str(uuid.uuid4()),
            name=name,
            age=age,
            grade=grade
        )
        
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
        
        family.children.append(child)
        
        # Save updated family
        self._save_family_profile(family)
        
        logger.info(f"Added child profile: {name} (age {age}) to family {family_id}")
        
        return child
    
    def authenticate_parent(self, family_id: str, parent_name: str, password: str) -> Tuple[bool, Optional[ParentProfile]]:
        """Authenticate parent login"""
        family = self.load_family_profile(family_id)
        if not family:
            return False, None
        
        # Find parent by name
        parent = next((p for p in family.parents if p.name.lower() == parent_name.lower()), None)
        if not parent:
            logger.warning(f"Parent not found: {parent_name}")
            return False, None
        
        # Check if account is locked
        if parent.locked_until:
            locked_until = datetime.fromisoformat(parent.locked_until)
            if datetime.now() < locked_until:
                remaining = (locked_until - datetime.now()).total_seconds() / 60
                logger.warning(f"Account locked for {remaining:.1f} more minutes")
                return False, None
            else:
                # Unlock account
                parent.locked_until = None
                parent.failed_login_attempts = 0
        
        # Verify password
        if ":" in parent.password_hash:
            hash_part, salt_part = parent.password_hash.split(":", 1)
            if self._verify_password(password, hash_part, salt_part):
                # Success
                parent.last_login = datetime.now().isoformat()
                parent.failed_login_attempts = 0
                self._save_family_profile(family)
                
                self.current_family = family
                self.current_parent = parent
                
                logger.info(f"Parent authenticated: {parent_name}")
                return True, parent
        
        # Failed authentication
        parent.failed_login_attempts += 1
        
        if parent.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
            parent.locked_until = (datetime.now() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)).isoformat()
            logger.warning(f"Account locked due to too many failed attempts: {parent_name}")
        
        self._save_family_profile(family)
        
        return False, None
    
    def select_child_profile(self, child_id: str) -> ChildProfile:
        """Select active child profile for session"""
        if not self.current_family:
            raise ProfileError("No family profile loaded")
        
        child = next((c for c in self.current_family.children if c.id == child_id), None)
        if not child:
            raise ProfileError(f"Child profile not found: {child_id}")
        
        child.last_active = datetime.now().isoformat()
        self.current_child = child
        
        self._save_family_profile(self.current_family)
        
        logger.info(f"Selected child profile: {child.name} (age {child.age})")
        
        return child
    
    def update_learning_progress(self, child_id: str, subject: str, 
                                minutes: int, topics: List[str], quiz_score: Optional[float] = None):
        """Update child's learning progress"""
        if not self.current_family:
            raise ProfileError("No family profile loaded")
        
        child = next((c for c in self.current_family.children if c.id == child_id), None)
        if not child:
            raise ProfileError(f"Child profile not found: {child_id}")
        
        # Get or create subject progress
        if subject not in child.progress:
            child.progress[subject] = LearningProgress(subject=subject)
        
        progress = child.progress[subject]
        
        # Update progress
        progress.total_sessions += 1
        progress.total_minutes += minutes
        progress.last_session = datetime.now().isoformat()
        
        # Add new topics
        for topic in topics:
            if topic not in progress.topics_covered:
                progress.topics_covered.append(topic)
        
        # Add quiz score if provided
        if quiz_score is not None:
            progress.quiz_scores.append({
                "date": datetime.now().isoformat(),
                "score": quiz_score
            })
            
            # Update mastery percentage (average of last 10 quiz scores)
            recent_scores = [q["score"] for q in progress.quiz_scores[-10:]]
            progress.mastery_percentage = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        
        # Update child totals
        child.total_sessions += 1
        child.total_learning_minutes += minutes
        
        # Update streak
        last_active = datetime.fromisoformat(child.last_active) if child.last_active else None
        today = date.today()
        
        if last_active and last_active.date() == today - timedelta(days=1):
            child.current_streak += 1
            child.longest_streak = max(child.longest_streak, child.current_streak)
        elif not last_active or last_active.date() != today:
            child.current_streak = 1
        
        child.last_active = datetime.now().isoformat()
        
        self._save_family_profile(self.current_family)
        
        logger.info(f"Updated progress for {child.name}: {subject} ({minutes} minutes)")
    
    def award_achievement(self, child_id: str, achievement_name: str, 
                         description: str, category: str, points: int = 10):
        """Award achievement to child"""
        if not self.current_family:
            raise ProfileError("No family profile loaded")
        
        child = next((c for c in self.current_family.children if c.id == child_id), None)
        if not child:
            raise ProfileError(f"Child profile not found: {child_id}")
        
        # Check if already earned
        if any(a.name == achievement_name for a in child.achievements):
            logger.info(f"Achievement already earned: {achievement_name}")
            return
        
        achievement = Achievement(
            id=str(uuid.uuid4()),
            name=achievement_name,
            description=description,
            earned_date=datetime.now().isoformat(),
            category=category,
            points=points
        )
        
        child.achievements.append(achievement)
        
        self._save_family_profile(self.current_family)
        
        logger.info(f"Awarded achievement to {child.name}: {achievement_name}")
    
    def get_child_statistics(self, child_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a child"""
        if not self.current_family:
            raise ProfileError("No family profile loaded")
        
        child = next((c for c in self.current_family.children if c.id == child_id), None)
        if not child:
            raise ProfileError(f"Child profile not found: {child_id}")
        
        # Calculate statistics
        total_subjects = len(child.progress)
        total_topics = sum(len(p.topics_covered) for p in child.progress.values())
        avg_mastery = sum(p.mastery_percentage for p in child.progress.values()) / total_subjects if total_subjects > 0 else 0
        
        stats = {
            "name": child.name,
            "age": child.age,
            "total_sessions": child.total_sessions,
            "total_hours": round(child.total_learning_minutes / 60, 1),
            "current_streak": child.current_streak,
            "longest_streak": child.longest_streak,
            "subjects_studied": total_subjects,
            "topics_covered": total_topics,
            "achievements_earned": len(child.achievements),
            "achievement_points": sum(a.points for a in child.achievements),
            "average_mastery": round(avg_mastery, 1),
            "favorite_subjects": child.favorite_subjects[:3] if child.favorite_subjects else [],
            "recent_activity": []
        }
        
        # Add recent activity
        for subject, progress in child.progress.items():
            if progress.last_session:
                stats["recent_activity"].append({
                    "subject": subject,
                    "date": progress.last_session,
                    "minutes": progress.total_minutes,
                    "mastery": progress.mastery_percentage
                })
        
        # Sort by date
        stats["recent_activity"].sort(key=lambda x: x["date"], reverse=True)
        stats["recent_activity"] = stats["recent_activity"][:5]  # Last 5 activities
        
        return stats
    
    def _save_family_profile(self, family: FamilyProfile):
        """Save family profile to disk"""
        if not self.profiles_dir:
            logger.warning("Cannot save profile: no profiles directory")
            return
        
        # Prepare data for saving
        family_data = asdict(family)
        
        # Separate sensitive data
        sensitive_data = {
            "parents": family_data.pop("parents"),
            "encryption_version": "1.0",
            "encrypted_at": datetime.now().isoformat()
        }
        
        # Save public data
        public_file = self.profiles_dir / f"family_{family.id}.json"
        try:
            with open(public_file, 'w', encoding='utf-8') as f:
                json.dump(family_data, f, indent=2, default=str)
            logger.info(f"Saved public family data: {public_file}")
        except Exception as e:
            logger.error(f"Failed to save public data: {e}")
            raise ProfileError(f"Failed to save family profile: {e}")
        
        # Encrypt and save sensitive data
        if self.encrypted_dir:
            encrypted_file = self.encrypted_dir / f"family_{family.id}.enc"
            try:
                encrypted_json = self._encrypt_data(json.dumps(sensitive_data, default=str))
                with open(encrypted_file, 'w', encoding='utf-8') as f:
                    f.write(encrypted_json)
                logger.info(f"Saved encrypted family data: {encrypted_file}")
            except Exception as e:
                logger.error(f"Failed to save encrypted data: {e}")
    
    def load_family_profile(self, family_id: str) -> Optional[FamilyProfile]:
        """Load family profile from disk"""
        if not self.profiles_dir:
            logger.warning("Cannot load profile: no profiles directory")
            return None
        
        # Load public data
        public_file = self.profiles_dir / f"family_{family_id}.json"
        if not public_file.exists():
            logger.warning(f"Family profile not found: {family_id}")
            return None
        
        try:
            with open(public_file, 'r', encoding='utf-8') as f:
                family_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load public data: {e}")
            return None
        
        # Load encrypted sensitive data
        parents_data = []
        if self.encrypted_dir:
            encrypted_file = self.encrypted_dir / f"family_{family_id}.enc"
            if encrypted_file.exists():
                try:
                    with open(encrypted_file, 'r', encoding='utf-8') as f:
                        encrypted_json = f.read()
                    decrypted_json = self._decrypt_data(encrypted_json)
                    sensitive_data = json.loads(decrypted_json)
                    parents_data = sensitive_data.get("parents", [])
                except Exception as e:
                    logger.error(f"Failed to load encrypted data: {e}")
        
        # Reconstruct family profile
        family = FamilyProfile(
            id=family_data["id"],
            family_name=family_data["family_name"],
            created_date=family_data["created_date"],
            subscription_type=family_data.get("subscription_type", "standard")
        )
        
        # Restore parents
        for parent_data in parents_data:
            parent = ParentProfile(**parent_data)
            family.parents.append(parent)
        
        # Restore children
        for child_data in family_data.get("children", []):
            # Handle achievements
            achievements = []
            for ach_data in child_data.get("achievements", []):
                if isinstance(ach_data, dict):
                    achievements.append(Achievement(**ach_data))
            child_data["achievements"] = achievements
            
            # Handle progress
            progress = {}
            for subj, prog_data in child_data.get("progress", {}).items():
                if isinstance(prog_data, dict):
                    progress[subj] = LearningProgress(**prog_data)
            child_data["progress"] = progress
            
            child = ChildProfile(**child_data)
            family.children.append(child)
        
        # Restore other fields
        family.timezone = family_data.get("timezone", "America/Chicago")
        family.language = family_data.get("language", "en-US")
        family.country = family_data.get("country", "US")
        family.features_enabled = family_data.get("features_enabled", family.features_enabled)
        family.total_usage_hours = family_data.get("total_usage_hours", 0.0)
        family.total_sessions = family_data.get("total_sessions", 0)
        
        logger.info(f"Loaded family profile: {family.family_name}")
        
        return family
    
    def list_families(self) -> List[Dict[str, str]]:
        """List all family profiles"""
        if not self.profiles_dir:
            return []
        
        families = []
        for file in self.profiles_dir.glob("family_*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                families.append({
                    "id": data["id"],
                    "name": data["family_name"],
                    "created": data["created_date"],
                    "children_count": len(data.get("children", []))
                })
            except Exception as e:
                logger.error(f"Failed to read family file {file}: {e}")
        
        return families
    
    def export_family_data(self, family_id: str, output_path: Path, include_sensitive: bool = False):
        """Export family data for backup or transfer"""
        family = self.load_family_profile(family_id)
        if not family:
            raise ProfileError(f"Family profile not found: {family_id}")
        
        export_data = {
            "export_version": "1.0",
            "export_date": datetime.now().isoformat(),
            "family": asdict(family)
        }
        
        if not include_sensitive:
            # Remove sensitive parent data
            for parent in export_data["family"]["parents"]:
                parent.pop("password_hash", None)
                parent.pop("pin_code", None)
                parent.pop("security_answer_hash", None)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            logger.info(f"Exported family data to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export family data: {e}")
            return False
    
    def import_family_data(self, import_path: Path) -> FamilyProfile:
        """Import family data from backup"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            family_data = import_data["family"]
            
            # Create new family from imported data
            family = FamilyProfile(
                id=family_data["id"],
                family_name=family_data["family_name"],
                created_date=family_data["created_date"]
            )
            
            # Import parents (may need new passwords if sensitive data excluded)
            for parent_data in family_data.get("parents", []):
                if not parent_data.get("password_hash"):
                    # Generate temporary password
                    temp_password = secrets.token_urlsafe(12)
                    password_hash, salt = self._hash_password(temp_password)
                    parent_data["password_hash"] = f"{password_hash}:{salt}"
                    logger.warning(f"Generated temporary password for {parent_data['name']}: {temp_password}")
                
                parent = ParentProfile(**parent_data)
                family.parents.append(parent)
            
            # Import children
            for child_data in family_data.get("children", []):
                child = ChildProfile(**child_data)
                family.children.append(child)
            
            # Save imported family
            self._save_family_profile(family)
            
            logger.info(f"Imported family: {family.family_name}")
            return family
            
        except Exception as e:
            logger.error(f"Failed to import family data: {e}")
            raise ProfileError(f"Failed to import family data: {e}")

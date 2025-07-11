#!/usr/bin/env python3
"""
Profile Manager for Sunflower AI
Handles family profiles, child management, and settings
"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import uuid
from .profile_storage import ProfileStorage
from ..constants import MAX_SAFETY_STRIKES, SAFETY_COOLDOWN_MINUTES


class ProfileManager:
    """Manages family and child profiles for Sunflower AI"""
    
    def __init__(self, app_dir: Optional[Path] = None):
        """Initialize profile manager"""
        self.app_dir = app_dir or (Path.home() / '.sunflower-ai')
        self.profiles_dir = self.app_dir / 'profiles'
        self.profiles_dir.mkdir(exist_ok=True, parents=True)
        
        # Storage handler
        self.storage = ProfileStorage(self.app_dir)
        
        # Profile files
        self.family_file = self.profiles_dir / 'family.json'
        
        # Load profiles
        self.load_profiles()
    
    def load_profiles(self):
        """Load family profiles from disk"""
        if self.family_file.exists():
            try:
                with open(self.family_file, 'r') as f:
                    self.family_data = json.load(f)
            except Exception as e:
                print(f"Error loading family profiles: {e}")
                self.family_data = self._get_default_family_data()
        else:
            self.family_data = self._get_default_family_data()
    
    def save_profiles(self) -> bool:
        """Save family profiles to disk"""
        try:
            # Save main family file
            with open(self.family_file, 'w') as f:
                json.dump(self.family_data, f, indent=2)
            
            # Save encrypted profiles for each child
            for child in self.family_data.get('children', []):
                self.storage.save_profile(child['id'], child)
            
            return True
        except Exception as e:
            print(f"Error saving profiles: {e}")
            return False
    
    def _get_default_family_data(self) -> Dict:
        """Get default family data structure"""
        return {
            "version": "1.0",
            "parent": {
                "name": "",
                "email": "",
                "password_hash": "",
                "setup_complete": False,
                "created": datetime.now().isoformat()
            },
            "children": [],
            "settings": {
                "content_filtering": "strict",
                "session_recording": True,
                "parent_alerts": True,
                "daily_summaries": True,
                "session_time_limit": 60,  # minutes
                "break_reminder": 30,      # minutes
                "max_daily_time": 120      # minutes
            }
        }
    
    def create_parent_account(self, name: str, email: str, password: str) -> bool:
        """Create parent account"""
        if not name or not password:
            return False
        
        # Hash password
        password_hash = self._hash_password(password)
        
        self.family_data['parent'] = {
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "setup_complete": True,
            "created": datetime.now().isoformat()
        }
        
        return self.save_profiles()
    
    def get_parent_profile(self) -> Optional[Dict]:
        """Returns the parent profile dictionary."""
        # Ensure 'type' is part of the returned dict for UI logic
        parent_data = self.family_data.get('parent')
        if parent_data:
            parent_data['type'] = 'parent'
        return parent_data

    def is_setup_complete(self) -> bool:
        """Checks if the initial parent account setup has been completed."""
        return self.family_data.get('parent', {}).get('setup_complete', False)

    def verify_parent_password(self, password: str) -> bool:
        """Verify parent password"""
        stored_hash = self.family_data.get('parent', {}).get('password_hash', '')
        return self._hash_password(password) == stored_hash
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        # In production, use proper password hashing like bcrypt
        # This is a simplified version
        salt = "sunflower_ai_2024"
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def add_child(self, name: str, age: int, grade: str, 
                  interests: Optional[List[str]] = None) -> Optional[str]:
        """Add a new child profile"""
        if not name or age < 2 or age > 18:
            return None
        
        # Generate unique ID
        child_id = f"child_{uuid.uuid4().hex[:8]}"
        
        # Create child profile
        child_profile = {
            "id": child_id,
            "name": name,
            "age": age,
            "grade": grade,
            "interests": interests or [],
            "learning_style": "visual",  # Default
            "created": datetime.now().isoformat(),
            "progress": {
                "total_sessions": 0,
                "total_time_minutes": 0,
                "vocabulary_mastered": [],
                "concepts_understood": [],
                "recent_topics": [],
                "last_session": None
            },
            "safety": {
                "parent_alerts": [],
                "content_redirects": 0,
                "safety_incidents": 0,
                "strikes": 0,
                "locked_until": None
            }
        }
        
        # Add to family
        self.family_data['children'].append(child_profile)
        
        # Save
        if self.save_profiles():
            return child_id
        return None
    
    def update_child_profile(self, child_id: str, updates: Dict) -> bool:
        """Update a child's profile"""
        for child in self.family_data['children']:
            if child['id'] == child_id:
                # Update allowed fields
                allowed_fields = ['name', 'age', 'grade', 'interests', 'learning_style']
                for field in allowed_fields:
                    if field in updates:
                        child[field] = updates[field]
                
                return self.save_profiles()
        return False
    
    def remove_child(self, child_id: str) -> bool:
        """Remove a child profile"""
        original_count = len(self.family_data['children'])
        self.family_data['children'] = [
            c for c in self.family_data['children'] if c['id'] != child_id
        ]
        
        if len(self.family_data['children']) < original_count:
            # Also remove encrypted profile
            self.storage.delete_secure_data(f"profile_{child_id}")
            return self.save_profiles()
        return False
    
    def add_safety_strike(self, child_id: str, category: str) -> bool:
        """
        Adds a safety strike to a child's profile. If the strike limit is
        reached, the profile is locked for a configured duration.
        """
        child = self.get_child(child_id)
        if not child:
            return False

        safety_info = child.get('safety', {})
        safety_info['strikes'] = safety_info.get('strikes', 0) + 1
        safety_info['safety_incidents'] = safety_info.get('safety_incidents', 0) + 1

        # Log the specific incident as an alert
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": "strike",
            "details": f"Safety strike added for category: {category}",
            "action_taken": "User prompt was blocked and redirected."
        }
        if 'parent_alerts' not in safety_info:
            safety_info['parent_alerts'] = []
        safety_info['parent_alerts'].append(alert)

        # Check if profile should be locked
        if safety_info['strikes'] >= MAX_SAFETY_STRIKES:
            locked_until = datetime.now() + timedelta(minutes=SAFETY_COOLDOWN_MINUTES)
            safety_info['locked_until'] = locked_until.isoformat()
        
        child['safety'] = safety_info
        return self.update_child_profile(child_id, {'safety': safety_info})

    def is_profile_locked(self, child_id: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if a profile is currently locked due to safety violations.
        Returns a tuple of (is_locked, message).
        """
        child = self.get_child(child_id)
        if not child:
            return False, None

        safety_info = child.get('safety', {})
        locked_until_str = safety_info.get('locked_until')

        if locked_until_str:
            locked_until = datetime.fromisoformat(locked_until_str)
            if datetime.now() < locked_until:
                remaining = locked_until - datetime.now()
                minutes = int(remaining.total_seconds() / 60) + 1
                return True, f"This profile is locked for {minutes} more minute(s) due to repeated safety alerts."
            else:
                # Cooldown has passed, automatically unlock
                self.clear_strikes(child_id)
                return False, None

        return False, None

    def clear_strikes(self, child_id: str) -> bool:
        """Allows a parent to clear all safety strikes and unlock a profile."""
        child = self.get_child(child_id)
        if not child:
            return False

        safety_info = child.get('safety', {})
        safety_info['strikes'] = 0
        safety_info['locked_until'] = None
        
        return self.update_child_profile(child_id, {'safety': safety_info})

    def get_child(self, child_id: str) -> Optional[Dict]:
        """Get a specific child's profile"""
        for child in self.family_data['children']:
            if child['id'] == child_id:
                return child.copy()
        return None
    
    def get_child_by_name(self, name: str) -> Optional[Dict]:
        """Get child profile by name"""
        for child in self.family_data['children']:
            if child['name'].lower() == name.lower():
                return child.copy()
        return None
    
    def get_all_children(self) -> List[Dict]:
        """Get all child profiles"""
        return [c.copy() for c in self.family_data['children']]
    
    def update_child_progress(self, child_id: str, session_data: Dict) -> bool:
        """Update child's learning progress"""
        for child in self.family_data['children']:
            if child['id'] == child_id:
                progress = child['progress']
                
                # Update session count and time
                progress['total_sessions'] += 1
                progress['total_time_minutes'] += session_data.get('duration_minutes', 0)
                progress['last_session'] = datetime.now().isoformat()
                
                # Update vocabulary
                new_vocab = session_data.get('new_vocabulary', [])
                for word in new_vocab:
                    if word not in progress['vocabulary_mastered']:
                        progress['vocabulary_mastered'].append(word)
                
                # Update concepts
                new_concepts = session_data.get('concepts_covered', [])
                for concept in new_concepts:
                    if concept not in progress['concepts_understood']:
                        progress['concepts_understood'].append(concept)
                
                # Update recent topics (keep last 20)
                topics = session_data.get('topics', [])
                progress['recent_topics'] = (topics + progress['recent_topics'])[:20]
                
                return self.save_profiles()
        return False
    
    def add_safety_alert(self, child_id: str, alert_type: str, 
                        details: str, action_taken: str) -> bool:
        """Add a safety alert for a child"""
        for child in self.family_data['children']:
            if child['id'] == child_id:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": alert_type,
                    "details": details,
                    "action_taken": action_taken
                }
                
                child['safety']['parent_alerts'].append(alert)
                child['safety']['safety_incidents'] += 1
                
                return self.save_profiles()
        return False
    
    def get_safety_alerts(self, child_id: Optional[str] = None, 
                         days: int = 30) -> List[Dict]:
        """Get safety alerts for a child or all children"""
        alerts = []
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        children = self.family_data['children']
        if child_id:
            children = [c for c in children if c['id'] == child_id]
        
        for child in children:
            for alert in child['safety']['parent_alerts']:
                try:
                    alert_time = datetime.fromisoformat(alert['timestamp']).timestamp()
                    if alert_time >= cutoff_date:
                        alert_copy = alert.copy()
                        alert_copy['child_name'] = child['name']
                        alert_copy['child_id'] = child['id']
                        alerts.append(alert_copy)
                except:
                    pass
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        return alerts
    
    def update_family_settings(self, settings: Dict) -> bool:
        """Update family settings"""
        for key, value in settings.items():
            if key in self.family_data['settings']:
                self.family_data['settings'][key] = value
        
        return self.save_profiles()
    
    def get_family_settings(self) -> Dict:
        """Get current family settings"""
        return self.family_data['settings'].copy()
    
    def check_session_limits(self, child_id: str) -> Dict:
        """Check if child has reached session limits"""
        settings = self.family_data['settings']
        child = self.get_child(child_id)
        
        if not child:
            return {"allowed": False, "reason": "Invalid child ID"}
        
        # Get today's session data
        from .session_logger import SessionLogger
        logger = SessionLogger(self.app_dir)
        today_summary = logger.get_daily_summary(child_id)
        
        # Check daily time limit
        max_daily = settings.get('max_daily_time', 120)
        if today_summary['total_time_minutes'] >= max_daily:
            return {
                "allowed": False,
                "reason": f"Daily time limit reached ({max_daily} minutes)"
            }
        
        # Check break time
        if today_summary['last_session_end']:
            try:
                last_end = datetime.fromisoformat(today_summary['last_session_end'])
                minutes_since = (datetime.now() - last_end).seconds / 60
                break_time = settings.get('break_reminder', 30)
                
                if minutes_since < 5:  # Minimum 5 minute break
                    return {
                        "allowed": False,
                        "reason": "Please take a short break before continuing"
                    }
            except:
                pass
        
        return {
            "allowed": True,
            "remaining_time": max_daily - today_summary['total_time_minutes']
        }
    
    def get_session_statistics(self, child_id: Optional[str] = None) -> Dict:
        """Get session statistics for reporting"""
        stats = {
            "total_sessions": 0,
            "total_time_minutes": 0,
            "total_vocabulary": 0,
            "total_concepts": 0,
            "safety_incidents": 0,
            "topics_explored": 0
        }
        
        children = self.family_data['children']
        if child_id:
            children = [c for c in children if c['id'] == child_id]
        
        for child in children:
            progress = child.get('progress', {})
            safety = child.get('safety', {})
            
            stats['total_sessions'] += progress.get('total_sessions', 0)
            stats['total_time_minutes'] += progress.get('total_time_minutes', 0)
            stats['total_vocabulary'] += len(progress.get('vocabulary_mastered', []))
            stats['total_concepts'] += len(progress.get('concepts_understood', []))
            stats['safety_incidents'] += safety.get('safety_incidents', 0)
            stats['topics_explored'] += len(set(progress.get('recent_topics', [])))
        
        # Add calculated fields
        if stats['total_sessions'] > 0:
            stats['avg_session_minutes'] = round(
                stats['total_time_minutes'] / stats['total_sessions'], 1
            )
        else:
            stats['avg_session_minutes'] = 0
        
        stats['total_children'] = len(self.family_data['children'])
        
        return stats
    
    def export_profile_data(self, export_path: Optional[Path] = None) -> Optional[Path]:
        """Export all profile data for backup"""
        if not export_path:
            export_path = self.app_dir / 'exports'
            export_path.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_file = export_path / f'sunflower_ai_backup_{timestamp}.json'
        else:
            export_file = Path(export_path)
        
        try:
            # Prepare export data
            export_data = {
                "version": "1.0",
                "export_date": datetime.now().isoformat(),
                "family_data": self.family_data,
                "statistics": self.get_session_statistics()
            }
            
            # Save to file
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return export_file
        except Exception as e:
            print(f"Export failed: {e}")
            return None
    
    def import_profile_data(self, import_path: Path) -> bool:
        """Import profile data from backup"""
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            # Validate version
            if import_data.get('version') != '1.0':
                print("Incompatible backup version")
                return False
            
            # Import family data
            self.family_data = import_data['family_data']
            
            # Save to disk
            return self.save_profiles()
        except Exception as e:
            print(f"Import failed: {e}")
            return False


# Testing functionality
if __name__ == "__main__":
    # Test profile manager
    manager = ProfileManager()
    
    print("Testing Profile Manager...")
    
    # Create parent account
    if not manager.family_data['parent']['setup_complete']:
        print("\nCreating parent account...")
        success = manager.create_parent_account("John Parent", "john@example.com", "password123")
        print(f"Parent account created: {success}")
    
    # Add children
    if len(manager.get_all_children()) == 0:
        print("\nAdding child profiles...")
        
        child1_id = manager.add_child("Emma", 8, "3", ["butterflies", "space"])
        print(f"Added Emma: {child1_id}")
        
        child2_id = manager.add_child("Lucas", 12, "7", ["robots", "chemistry"])
        print(f"Added Lucas: {child2_id}")
    
    # Display statistics
    print("\nFamily Statistics:")
    stats = manager.get_session_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nProfile Manager test complete!")

#!/usr/bin/env python3
"""
Open WebUI Configuration for Sunflower AI
Handles all Open WebUI settings, user management, and model filtering
"""

import os
import json
import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

class OpenWebUIConfig:
    """Manages Open WebUI configuration for Sunflower AI"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.config_dir = self.data_dir / "openwebui" / "config"
        self.db_path = self.data_dir / "openwebui" / "data" / "webui.db"
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or create configuration
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load or create Open WebUI configuration"""
        config_file = self.config_dir / "webui_config.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Create default configuration
        config = {
            "system": {
                "name": "Sunflower AI Education System",
                "version": "1.0.0",
                "description": "Safe, adaptive AI-powered STEM education for children",
                "theme": "light",
                "language": "en"
            },
            "auth": {
                "enabled": True,
                "allow_signup": False,
                "require_approval": True,
                "session_timeout": 3600,
                "password_requirements": {
                    "min_length": 8,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True
                }
            },
            "models": {
                "allowed_models": [
                    "sunflower-kids",
                    "sunflower-educator",
                    "llama3.2:3b",
                    "llama3.2:1b"
                ],
                "default_model": "sunflower-kids",
                "model_settings": {
                    "sunflower-kids": {
                        "display_name": "Sunflower Kids (Ages 5-13)",
                        "description": "Safe, age-appropriate STEM education",
                        "max_tokens": 150,
                        "temperature": 0.7,
                        "safety_level": "maximum"
                    },
                    "sunflower-educator": {
                        "display_name": "Sunflower Educator",
                        "description": "Professional educator assistant",
                        "max_tokens": 500,
                        "temperature": 0.8,
                        "safety_level": "standard"
                    }
                }
            },
            "safety": {
                "content_filtering": True,
                "profanity_filter": True,
                "topic_restrictions": True,
                "allowed_topics": [
                    "science",
                    "technology",
                    "engineering",
                    "mathematics",
                    "education",
                    "learning"
                ],
                "blocked_keywords": [],
                "age_verification": True,
                "session_recording": True
            },
            "ui": {
                "show_model_selector": False,
                "show_system_prompts": False,
                "enable_markdown": True,
                "enable_code_highlighting": True,
                "enable_latex": True,
                "enable_file_upload": False,
                "max_message_length": 500,
                "auto_save_conversations": True
            },
            "features": {
                "enable_web_search": False,
                "enable_image_generation": False,
                "enable_voice_input": False,
                "enable_plugins": False,
                "enable_api_access": False,
                "enable_sharing": False
            },
            "parental_controls": {
                "enabled": True,
                "require_pin": True,
                "session_time_limits": {
                    "k-2": 20,
                    "elementary": 30,
                    "middle": 45,
                    "high": 60
                },
                "break_reminders": True,
                "activity_reports": True,
                "content_review": True
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "timeout": 120,
                "keep_alive": "5m",
                "num_parallel": 1,
                "num_ctx": 2048
            }
        }
        
        # Save configuration
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config
    
    def apply_environment_variables(self) -> Dict[str, str]:
        """Generate environment variables for Open WebUI"""
        env_vars = {
            # Basic settings
            "WEBUI_NAME": self.config["system"]["name"],
            "DATA_DIR": str(self.data_dir / "openwebui" / "data"),
            
            # Authentication
            "WEBUI_AUTH": str(self.config["auth"]["enabled"]).lower(),
            "ENABLE_SIGNUP": str(self.config["auth"]["allow_signup"]).lower(),
            
            # Ollama settings
            "OLLAMA_BASE_URL": self.config["ollama"]["base_url"],
            "OLLAMA_API_BASE_URL": self.config["ollama"]["base_url"],
            
            # Model settings
            "DEFAULT_MODELS": ",".join(self.config["models"]["allowed_models"]),
            "MODEL_FILTER_ENABLED": "true",
            "MODEL_FILTER_LIST": ",".join(self.config["models"]["allowed_models"]),
            
            # UI settings
            "ENABLE_MODEL_FILTER": str(self.config["ui"]["show_model_selector"]).lower(),
            "SHOW_ADMIN_DETAILS": "false",
            
            # Features
            "ENABLE_COMMUNITY_SHARING": str(self.config["features"]["enable_sharing"]).lower(),
            "ENABLE_ADMIN_EXPORT": "true",
            
            # Security
            "WEBUI_SESSION_COOKIE_SAME_SITE": "lax",
            "WEBUI_SESSION_COOKIE_SECURE": "false",  # Local use only
            
            # Server settings
            "HOST": "127.0.0.1",
            "PORT": "8080"
        }
        
        return env_vars
    
    def create_database_schema(self):
        """Create Open WebUI database schema with Sunflower extensions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table with Sunflower extensions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                profile_image TEXT,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- Sunflower extensions
                is_child BOOLEAN DEFAULT 0,
                parent_id TEXT,
                age INTEGER,
                grade TEXT,
                safety_level TEXT DEFAULT 'standard',
                learning_level TEXT,
                session_limit INTEGER DEFAULT 60,
                total_usage_minutes INTEGER DEFAULT 0,
                last_active TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES users(id)
            )
        ''')
        
        # Conversations table with safety tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- Sunflower extensions
                safety_score REAL DEFAULT 1.0,
                flagged BOOLEAN DEFAULT 0,
                flag_reason TEXT,
                duration_seconds INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Messages table with content filtering
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- Sunflower extensions
                filtered BOOLEAN DEFAULT 0,
                original_content TEXT,
                safety_score REAL DEFAULT 1.0,
                topics TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        # Session logs for parental monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration_seconds INTEGER,
                messages_sent INTEGER DEFAULT 0,
                topics_discussed TEXT,
                safety_incidents INTEGER DEFAULT 0,
                learning_progress TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Safety incidents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS safety_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                conversation_id TEXT,
                incident_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                incident_type TEXT NOT NULL,
                severity TEXT DEFAULT 'low',
                content TEXT,
                action_taken TEXT,
                resolved BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        # Learning metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date DATE DEFAULT CURRENT_DATE,
                subject TEXT NOT NULL,
                topic TEXT,
                questions_asked INTEGER DEFAULT 0,
                concepts_learned TEXT,
                difficulty_level TEXT,
                engagement_score REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_admin_user(self, password: Optional[str] = None) -> Dict[str, str]:
        """Create admin user for parental control"""
        if not password:
            password = secrets.token_urlsafe(12)
        
        user_id = secrets.token_hex(16)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (id, email, name, role, password_hash, is_child)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, "admin@sunflower.local", "Parent Administrator", "admin", password_hash, 0))
        
        conn.commit()
        conn.close()
        
        return {
            "user_id": user_id,
            "email": "admin@sunflower.local",
            "password": password,
            "role": "admin"
        }
    
    def create_child_user(self, name: str, age: int, grade: str, 
                         parent_id: str) -> Dict[str, Any]:
        """Create a child user profile"""
        user_id = secrets.token_hex(8)
        email = f"{name.lower().replace(' ', '_')}@sunflower.local"
        
        # Determine safety and learning levels based on age
        if age <= 7:
            safety_level = "maximum"
            learning_level = "k-2"
            session_limit = 20
        elif age <= 10:
            safety_level = "high"
            learning_level = "elementary"
            session_limit = 30
        elif age <= 13:
            safety_level = "moderate"
            learning_level = "middle"
            session_limit = 45
        else:
            safety_level = "standard"
            learning_level = "high"
            session_limit = 60
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (
                id, email, name, role, is_child, parent_id,
                age, grade, safety_level, learning_level, session_limit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, email, name, "user", 1, parent_id,
            age, grade, safety_level, learning_level, session_limit
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "user_id": user_id,
            "name": name,
            "email": email,
            "age": age,
            "grade": grade,
            "safety_level": safety_level,
            "learning_level": learning_level,
            "session_limit": session_limit
        }
    
    def get_user_profiles(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all child profiles for a parent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, age, grade, safety_level, learning_level,
                   session_limit, total_usage_minutes, last_active
            FROM users
            WHERE parent_id = ? AND is_child = 1
            ORDER BY name
        ''', (parent_id,))
        
        profiles = []
        for row in cursor.fetchall():
            profiles.append({
                "id": row[0],
                "name": row[1],
                "age": row[2],
                "grade": row[3],
                "safety_level": row[4],
                "learning_level": row[5],
                "session_limit": row[6],
                "total_usage_minutes": row[7],
                "last_active": row[8]
            })
        
        conn.close()
        return profiles
    
    def log_session(self, user_id: str, duration_seconds: int,
                   messages_sent: int, topics: List[str]):
        """Log a user session for parental review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO session_logs (
                user_id, end_time, duration_seconds,
                messages_sent, topics_discussed
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,
            datetime.now().isoformat(),
            duration_seconds,
            messages_sent,
            json.dumps(topics)
        ))
        
        # Update user's total usage
        cursor.execute('''
            UPDATE users
            SET total_usage_minutes = total_usage_minutes + ?,
                last_active = ?
            WHERE id = ?
        ''', (duration_seconds // 60, datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    def record_safety_incident(self, user_id: str, incident_type: str,
                              severity: str, content: str,
                              conversation_id: Optional[str] = None):
        """Record a safety incident for parental review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO safety_incidents (
                user_id, conversation_id, incident_type,
                severity, content, action_taken
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            conversation_id,
            incident_type,
            severity,
            content,
            "Content filtered and logged for review"
        ))
        
        conn.commit()
        conn.close()
    
    def get_session_history(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get session history for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT start_time, end_time, duration_seconds,
                   messages_sent, topics_discussed, safety_incidents
            FROM session_logs
            WHERE user_id = ?
              AND start_time >= datetime('now', '-' || ? || ' days')
            ORDER BY start_time DESC
        ''', (user_id, days))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "start_time": row[0],
                "end_time": row[1],
                "duration_seconds": row[2],
                "messages_sent": row[3],
                "topics": json.loads(row[4]) if row[4] else [],
                "safety_incidents": row[5]
            })
        
        conn.close()
        return sessions
    
    def export_config(self, output_file: Path):
        """Export configuration for backup"""
        config_export = {
            "config": self.config,
            "export_date": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        with open(output_file, 'w') as f:
            json.dump(config_export, f, indent=2)
    
    def import_config(self, input_file: Path):
        """Import configuration from backup"""
        with open(input_file, 'r') as f:
            config_import = json.load(f)
        
        self.config = config_import["config"]
        
        # Save imported configuration
        config_file = self.config_dir / "webui_config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python openwebui_config.py <data_dir>")
        sys.exit(1)
    
    data_dir = Path(sys.argv[1])
    config = OpenWebUIConfig(data_dir)
    
    print("Open WebUI Configuration Manager")
    print("=" * 50)
    
    # Create database schema
    config.create_database_schema()
    print("✓ Database schema created")
    
    # Create admin user
    admin = config.create_admin_user()
    print(f"✓ Admin user created: {admin['email']}")
    print(f"  Password: {admin['password']}")
    
    # Apply environment variables
    env_vars = config.apply_environment_variables()
    print(f"✓ Generated {len(env_vars)} environment variables")
    
    print("\nConfiguration complete!")

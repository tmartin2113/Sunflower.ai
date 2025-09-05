#!/usr/bin/env python3
"""
Sunflower AI Professional System - Common Launcher Components
Shared components for Windows and macOS launchers
Version: 6.2
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
import logging
import platform
import subprocess
import psutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import threading
import queue
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ==================== ENUMS ====================
class SafetyLevel(Enum):
    """Safety levels for child profiles"""
    MAXIMUM = "maximum"  # Ages 5-7
    HIGH = "high"        # Ages 8-10
    MODERATE = "moderate" # Ages 11-13  
    STANDARD = "standard" # Ages 14-17


class ModelTier(Enum):
    """Model performance tiers"""
    HIGH = "llama3.2:7b"
    MID = "llama3.2:3b"
    LOW = "llama3.2:1b"
    MINIMAL = "llama3.2:1b-q4_0"


class SystemStatus(Enum):
    """System operation status"""
    INITIALIZING = "initializing"
    READY = "ready"
    LOADING = "loading"
    RUNNING = "running"
    ERROR = "error"
    SHUTDOWN = "shutdown"


# ==================== DATA CLASSES ====================
@dataclass
class ChildProfile:
    """Child profile information"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    age: int = 10
    grade_level: int = 5
    safety_level: SafetyLevel = SafetyLevel.HIGH
    interests: List[str] = field(default_factory=list)
    learning_style: str = "visual"
    created_at: datetime = field(default_factory=datetime.now)
    last_active: Optional[datetime] = None
    total_sessions: int = 0
    total_learning_time: timedelta = timedelta()
    blocked_topics: List[str] = field(default_factory=list)
    vocabulary_level: str = "grade_appropriate"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "grade_level": self.grade_level,
            "safety_level": self.safety_level.value,
            "interests": json.dumps(self.interests),
            "learning_style": self.learning_style,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "total_sessions": self.total_sessions,
            "total_learning_time": self.total_learning_time.total_seconds(),
            "blocked_topics": json.dumps(self.blocked_topics),
            "vocabulary_level": self.vocabulary_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChildProfile':
        """Create from dictionary"""
        profile = cls()
        profile.id = data.get("id", str(uuid.uuid4()))
        profile.name = data.get("name", "")
        profile.age = data.get("age", 10)
        profile.grade_level = data.get("grade_level", 5)
        profile.safety_level = SafetyLevel(data.get("safety_level", "high"))
        profile.interests = json.loads(data.get("interests", "[]"))
        profile.learning_style = data.get("learning_style", "visual")
        profile.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        if data.get("last_active"):
            profile.last_active = datetime.fromisoformat(data["last_active"])
        profile.total_sessions = data.get("total_sessions", 0)
        profile.total_learning_time = timedelta(seconds=data.get("total_learning_time", 0))
        profile.blocked_topics = json.loads(data.get("blocked_topics", "[]"))
        profile.vocabulary_level = data.get("vocabulary_level", "grade_appropriate")
        return profile


@dataclass
class FamilyAccount:
    """Family account information"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    family_name: str = ""
    parent_email: str = ""
    password_hash: str = ""
    salt: str = ""
    children: List[ChildProfile] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    subscription_tier: str = "standard"
    device_id: str = ""
    security_questions: Dict[str, str] = field(default_factory=dict)
    two_factor_enabled: bool = False
    session_timeout_minutes: int = 60
    max_children: int = 10


# ==================== PROFILE MANAGER ====================
class ProfileManager:
    """Manages family profiles and child accounts"""
    
    def __init__(self, usb_path: Path):
        self.usb_path = usb_path
        self.db_path = usb_path / "profiles" / "family_profiles.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.logger = logging.getLogger(__name__)
        
        # Security
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.failed_attempts = {}
        self.lockout_until = {}
    
    def _init_database(self):
        """Initialize the profiles database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create families table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS families (
                id TEXT PRIMARY KEY,
                family_name TEXT NOT NULL,
                parent_email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                subscription_tier TEXT DEFAULT 'standard',
                device_id TEXT,
                security_questions TEXT,
                two_factor_enabled INTEGER DEFAULT 0,
                session_timeout_minutes INTEGER DEFAULT 60,
                max_children INTEGER DEFAULT 10
            )
        """)
        
        # Create children table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS children (
                id TEXT PRIMARY KEY,
                family_id TEXT NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                grade_level INTEGER NOT NULL,
                safety_level TEXT NOT NULL,
                interests TEXT,
                learning_style TEXT DEFAULT 'visual',
                created_at TEXT NOT NULL,
                last_active TEXT,
                total_sessions INTEGER DEFAULT 0,
                total_learning_time REAL DEFAULT 0,
                blocked_topics TEXT,
                vocabulary_level TEXT DEFAULT 'grade_appropriate',
                FOREIGN KEY (family_id) REFERENCES families (id) ON DELETE CASCADE
            )
        """)
        
        # Create sessions table for audit trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                child_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                topics_covered TEXT,
                safety_incidents INTEGER DEFAULT 0,
                parent_reviewed INTEGER DEFAULT 0,
                FOREIGN KEY (child_id) REFERENCES children (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_family_email ON families (parent_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_child_family ON children (family_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_child ON sessions (child_id)")
        
        conn.commit()
        conn.close()
    
    def create_family(self, family_name: str, parent_email: str, password: str) -> str:
        """Create new family account"""
        # Check if email already exists
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM families WHERE parent_email = ?", (parent_email,))
        if cursor.fetchone():
            conn.close()
            raise ValueError("Email already registered")
        
        # Generate salt and hash password
        salt = secrets.token_hex(32)
        password_hash = self._hash_password(password, salt)
        
        # Create family account
        family_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO families (id, family_name, parent_email, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (family_id, family_name, parent_email, password_hash, salt, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created family account: {family_name} ({parent_email})")
        return family_id
    
    def authenticate_parent(self, email: str, password: str) -> Optional[str]:
        """Authenticate parent login"""
        # Check lockout
        if email in self.lockout_until:
            if datetime.now() < self.lockout_until[email]:
                remaining = (self.lockout_until[email] - datetime.now()).seconds // 60
                self.logger.warning(f"Account locked: {email} ({remaining} minutes remaining)")
                return None
            else:
                del self.lockout_until[email]
                self.failed_attempts[email] = 0
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, password_hash, salt FROM families WHERE parent_email = ?
        """, (email,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            self._record_failed_attempt(email)
            return None
        
        family_id, stored_hash, salt = result
        
        # Verify password
        if self._hash_password(password, salt) == stored_hash:
            # Update last login
            cursor.execute("""
                UPDATE families SET last_login = ? WHERE id = ?
            """, (datetime.now().isoformat(), family_id))
            conn.commit()
            conn.close()
            
            # Reset failed attempts
            self.failed_attempts[email] = 0
            
            self.logger.info(f"Successful login: {email}")
            return family_id
        else:
            conn.close()
            self._record_failed_attempt(email)
            return None
    
    def _record_failed_attempt(self, email: str):
        """Record failed login attempt"""
        if email not in self.failed_attempts:
            self.failed_attempts[email] = 0
        
        self.failed_attempts[email] += 1
        
        if self.failed_attempts[email] >= self.max_login_attempts:
            self.lockout_until[email] = datetime.now() + self.lockout_duration
            self.logger.warning(f"Account locked due to failed attempts: {email}")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2"""
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return key.hex()
    
    def add_child(self, family_id: str, child: ChildProfile) -> str:
        """Add child profile to family"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Check family exists
        cursor.execute("SELECT id FROM families WHERE id = ?", (family_id,))
        if not cursor.fetchone():
            conn.close()
            raise ValueError("Family not found")
        
        # Check child limit
        cursor.execute("SELECT COUNT(*) FROM children WHERE family_id = ?", (family_id,))
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT max_children FROM families WHERE id = ?", (family_id,))
        max_children = cursor.fetchone()[0]
        
        if count >= max_children:
            conn.close()
            raise ValueError(f"Maximum number of children ({max_children}) reached")
        
        # Add child
        cursor.execute("""
            INSERT INTO children (
                id, family_id, name, age, grade_level, safety_level,
                interests, learning_style, created_at, total_sessions,
                total_learning_time, blocked_topics, vocabulary_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            child.id, family_id, child.name, child.age, child.grade_level,
            child.safety_level.value, json.dumps(child.interests),
            child.learning_style, child.created_at.isoformat(),
            child.total_sessions, child.total_learning_time.total_seconds(),
            json.dumps(child.blocked_topics), child.vocabulary_level
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Added child profile: {child.name} to family {family_id}")
        return child.id
    
    def get_children(self, family_id: str) -> List[ChildProfile]:
        """Get all children for a family"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM children WHERE family_id = ? ORDER BY name
        """, (family_id,))
        
        children = []
        for row in cursor.fetchall():
            child = ChildProfile(
                id=row[0],
                name=row[2],
                age=row[3],
                grade_level=row[4],
                safety_level=SafetyLevel(row[5]),
                interests=json.loads(row[6] or "[]"),
                learning_style=row[7],
                created_at=datetime.fromisoformat(row[8]),
                last_active=datetime.fromisoformat(row[9]) if row[9] else None,
                total_sessions=row[10],
                total_learning_time=timedelta(seconds=row[11]),
                blocked_topics=json.loads(row[12] or "[]"),
                vocabulary_level=row[13]
            )
            children.append(child)
        
        conn.close()
        return children
    
    def update_child(self, child: ChildProfile):
        """Update child profile"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE children SET
                name = ?, age = ?, grade_level = ?, safety_level = ?,
                interests = ?, learning_style = ?, last_active = ?,
                total_sessions = ?, total_learning_time = ?,
                blocked_topics = ?, vocabulary_level = ?
            WHERE id = ?
        """, (
            child.name, child.age, child.grade_level, child.safety_level.value,
            json.dumps(child.interests), child.learning_style,
            child.last_active.isoformat() if child.last_active else None,
            child.total_sessions, child.total_learning_time.total_seconds(),
            json.dumps(child.blocked_topics), child.vocabulary_level,
            child.id
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Updated child profile: {child.name}")
    
    def start_session(self, child_id: str) -> str:
        """Start learning session for child"""
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create session record
        cursor.execute("""
            INSERT INTO sessions (id, child_id, start_time)
            VALUES (?, ?, ?)
        """, (session_id, child_id, datetime.now().isoformat()))
        
        # Update child's last active
        cursor.execute("""
            UPDATE children SET last_active = ? WHERE id = ?
        """, (datetime.now().isoformat(), child_id))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Started session {session_id} for child {child_id}")
        return session_id
    
    def end_session(self, session_id: str, topics_covered: List[str] = None, 
                   safety_incidents: int = 0):
        """End learning session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get session start time
        cursor.execute("SELECT start_time, child_id FROM sessions WHERE id = ?", (session_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return
        
        start_time = datetime.fromisoformat(result[0])
        child_id = result[1]
        duration = (datetime.now() - start_time).total_seconds()
        
        # Update session
        cursor.execute("""
            UPDATE sessions SET
                end_time = ?, duration_seconds = ?, topics_covered = ?, safety_incidents = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(), duration,
            json.dumps(topics_covered or []), safety_incidents, session_id
        ))
        
        # Update child stats
        cursor.execute("""
            UPDATE children SET
                total_sessions = total_sessions + 1,
                total_learning_time = total_learning_time + ?
            WHERE id = ?
        """, (duration, child_id))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Ended session {session_id} (duration: {duration:.0f}s)")
    
    def get_session_history(self, child_id: str, limit: int = 50) -> List[Dict]:
        """Get session history for child"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sessions 
            WHERE child_id = ? 
            ORDER BY start_time DESC 
            LIMIT ?
        """, (child_id, limit))
        
        sessions = []
        for row in cursor.fetchall():
            session = {
                "id": row[0],
                "child_id": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "duration_seconds": row[4],
                "topics_covered": json.loads(row[5] or "[]"),
                "safety_incidents": row[6],
                "parent_reviewed": bool(row[7])
            }
            sessions.append(session)
        
        conn.close()
        return sessions
    
    def mark_session_reviewed(self, session_id: str):
        """Mark session as reviewed by parent"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions SET parent_reviewed = 1 WHERE id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Session {session_id} marked as reviewed")


# ==================== HARDWARE DETECTOR ====================
class HardwareDetector:
    """Detects system hardware capabilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform = platform.system()
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {
            "platform": self.platform,
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 1),
            "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 1),
            "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 1),
            "gpu_available": self._detect_gpu(),
            "performance_score": self._calculate_performance_score()
        }
        
        self.logger.info(f"System info: {info}")
        return info
    
    def _detect_gpu(self) -> bool:
        """Detect if GPU is available"""
        try:
            if self.platform == "Windows":
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True, text=True, timeout=5
                )
                return "NVIDIA" in result.stdout or "AMD" in result.stdout
            elif self.platform == "Darwin":
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True, text=True, timeout=5
                )
                return "GPU" in result.stdout or "Metal" in result.stdout
            else:
                # Linux
                try:
                    result = subprocess.run(
                        ["lspci"], capture_output=True, text=True, timeout=5
                    )
                    return "VGA" in result.stdout or "3D" in result.stdout
                except:
                    return False
        except:
            return False
    
    def _calculate_performance_score(self) -> int:
        """Calculate system performance score (0-100)"""
        score = 0
        
        # CPU score (max 40 points)
        cpu_threads = psutil.cpu_count(logical=True)
        score += min(cpu_threads * 5, 40)
        
        # RAM score (max 40 points)
        ram_gb = psutil.virtual_memory().total / (1024**3)
        score += min(ram_gb * 2.5, 40)
        
        # GPU bonus (20 points)
        if self._detect_gpu():
            score += 20
        
        return min(score, 100)
    
    def select_optimal_model(self) -> ModelTier:
        """Select optimal model based on hardware"""
        info = self.get_system_info()
        score = info["performance_score"]
        ram_gb = info["ram_gb"]
        
        if score >= 80 and ram_gb >= 16:
            return ModelTier.HIGH
        elif score >= 60 and ram_gb >= 8:
            return ModelTier.MID
        elif score >= 40 and ram_gb >= 4:
            return ModelTier.LOW
        else:
            return ModelTier.MINIMAL


# ==================== OLLAMA MANAGER ====================
class OllamaManager:
    """Manages Ollama service and model operations"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path, model: str):
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        self.model = model
        self.platform = platform.system()
        
        # Determine Ollama executable path
        if self.platform == "Windows":
            self.ollama_exe = cdrom_path / "system" / "ollama" / "ollama.exe"
        else:
            self.ollama_exe = cdrom_path / "system" / "ollama" / "ollama"
        
        self.ollama_home = usb_path / "ollama_data"
        self.ollama_home.mkdir(exist_ok=True)
        self.process = None
        self.logger = logging.getLogger(__name__)
        self.service_ready = False
    
    def start_service(self) -> bool:
        """Start Ollama service"""
        if not self.ollama_exe.exists():
            self.logger.error(f"Ollama executable not found: {self.ollama_exe}")
            return False
        
        env = os.environ.copy()
        env["OLLAMA_HOME"] = str(self.ollama_home)
        env["OLLAMA_MODELS"] = str(self.cdrom_path / "system" / "models")
        
        try:
            self.process = subprocess.Popen(
                [str(self.ollama_exe), "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for service to be ready
            import requests
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get("http://localhost:11434/api/tags", timeout=1)
                    if response.status_code == 200:
                        self.service_ready = True
                        self.logger.info("Ollama service started successfully")
                        return True
                except:
                    pass
                time.sleep(1)
            
            self.logger.error("Ollama service failed to start in time")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start Ollama: {e}")
            return False
    
    def stop_service(self):
        """Stop Ollama service"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except:
                self.process.kill()
            self.process = None
            self.service_ready = False
            self.logger.info("Ollama service stopped")
    
    def load_model(self) -> bool:
        """Load the specified model"""
        if not self.service_ready:
            self.logger.error("Ollama service not ready")
            return False
        
        try:
            import requests
            
            # Check if model exists
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                
                if self.model in model_names:
                    self.logger.info(f"Model {self.model} is available")
                    return True
                else:
                    # Try to load from file
                    model_file = self.cdrom_path / "system" / "models" / f"{self.model}.gguf"
                    if model_file.exists():
                        return self._import_model(model_file)
                    else:
                        self.logger.error(f"Model {self.model} not found")
                        return False
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False
    
    def _import_model(self, model_file: Path) -> bool:
        """Import model from file"""
        try:
            result = subprocess.run(
                [str(self.ollama_exe), "create", self.model, "-f", str(model_file)],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                self.logger.info(f"Model {self.model} imported successfully")
                return True
            else:
                self.logger.error(f"Model import failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to import model: {e}")
            return False
    
    def test_model(self) -> bool:
        """Test model with a simple query"""
        if not self.service_ready:
            return False
        
        try:
            import requests
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": "Hello",
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info("Model test successful")
                return True
            else:
                self.logger.error(f"Model test failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Model test failed: {e}")
            return False


# ==================== MAIN LAUNCHER UI ====================
class SunflowerLauncherUI:
    """Main launcher user interface"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        
        # Initialize components
        self.profile_manager = ProfileManager(usb_path)
        self.hardware_detector = HardwareDetector()
        self.model_tier = self.hardware_detector.select_optimal_model()
        self.ollama_manager = OllamaManager(cdrom_path, usb_path, self.model_tier.value)
        
        # Current session
        self.current_family_id = None
        self.current_child_id = None
        self.current_session_id = None
        
        # Initialize UI
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # Apply modern styling
        self.setup_styles()
        
        # Build UI
        self.build_ui()
        
        # Start background services
        self.start_services()
    
    def setup_styles(self):
        """Configure modern UI styling"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        colors = {
            'bg': '#f0f4f8',
            'primary': '#5e72e4',
            'success': '#2dce89',
            'warning': '#fb6340',
            'text': '#32325d'
        }
        
        self.root.configure(bg=colors['bg'])
        
        # Configure styles
        style.configure('Title.TLabel', font=('Helvetica', 24, 'bold'))
        style.configure('Heading.TLabel', font=('Helvetica', 14, 'bold'))
        style.configure('Primary.TButton', font=('Helvetica', 11))
    
    def build_ui(self):
        """Build the main UI"""
        self.show_login_screen()
    
    def show_login_screen(self):
        """Display the login/registration screen"""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="50")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Title
        title = ttk.Label(main_frame, text="Welcome to Sunflower AI", style='Title.TLabel')
        title.pack(pady=20)
        
        subtitle = ttk.Label(main_frame, text="Family-Focused K-12 STEM Education")
        subtitle.pack(pady=10)
        
        # Login frame
        login_frame = ttk.LabelFrame(main_frame, text="Parent Login", padding="20")
        login_frame.pack(pady=20)
        
        # Email
        ttk.Label(login_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar()
        email_entry = ttk.Entry(login_frame, textvariable=self.email_var, width=30)
        email_entry.grid(row=0, column=1, pady=5)
        
        # Password
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(login_frame, textvariable=self.password_var, show="*", width=30)
        password_entry.grid(row=1, column=1, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(login_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Login", command=self.handle_login, style='Primary.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Register", command=self.show_registration, style='Primary.TButton').pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="System Ready", foreground="green")
        self.status_label.pack(pady=10)
    
    def show_registration(self):
        """Show registration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Family Account")
        dialog.geometry("400x300")
        
        fields = {}
        
        ttk.Label(dialog, text="Family Name:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=10)
        fields['family'] = ttk.Entry(dialog, width=30)
        fields['family'].grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(dialog, text="Parent Email:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=10)
        fields['email'] = ttk.Entry(dialog, width=30)
        fields['email'].grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(dialog, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=10)
        fields['password'] = ttk.Entry(dialog, show="*", width=30)
        fields['password'].grid(row=2, column=1, pady=5, padx=10)
        
        ttk.Label(dialog, text="Confirm Password:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=10)
        fields['confirm'] = ttk.Entry(dialog, show="*", width=30)
        fields['confirm'].grid(row=3, column=1, pady=5, padx=10)
        
        def register():
            if fields['password'].get() != fields['confirm'].get():
                messagebox.showerror("Error", "Passwords don't match")
                return
            
            if len(fields['password'].get()) < 8:
                messagebox.showerror("Error", "Password must be at least 8 characters")
                return
            
            try:
                family_id = self.profile_manager.create_family(
                    fields['family'].get(),
                    fields['email'].get(),
                    fields['password'].get()
                )
                messagebox.showinfo("Success", "Account created! You can now login.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(dialog, text="Register", command=register).grid(row=4, column=0, columnspan=2, pady=20)
    
    def handle_login(self):
        """Handle parent login"""
        family_id = self.profile_manager.authenticate_parent(
            self.email_var.get(),
            self.password_var.get()
        )
        
        if family_id:
            self.current_family_id = family_id
            self.show_child_selection()
        else:
            messagebox.showerror("Login Failed", "Invalid email or password")
    
    def show_child_selection(self):
        """Show child profile selection screen"""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Title
        title = ttk.Label(main_frame, text="Select Child Profile", style='Title.TLabel')
        title.pack(pady=20)
        
        # Get children
        children = self.profile_manager.get_children(self.current_family_id)
        
        if not children:
            # No children yet, show add child
            ttk.Label(main_frame, text="No child profiles found. Please add a child.").pack(pady=20)
            ttk.Button(main_frame, text="Add Child", command=self.show_add_child).pack()
        else:
            # List children
            for child in children:
                frame = ttk.Frame(main_frame)
                frame.pack(pady=10, fill=tk.X)
                
                btn = ttk.Button(frame, text=f"{child.name} (Age {child.age})",
                               command=lambda c=child: self.start_child_session(c))
                btn.pack(side=tk.LEFT, padx=10)
                
                info = f"Grade {child.grade_level} | {child.total_sessions} sessions"
                ttk.Label(frame, text=info).pack(side=tk.LEFT)
            
            # Add child button
            ttk.Button(main_frame, text="Add Another Child", command=self.show_add_child).pack(pady=20)
        
        # Parent dashboard button
        ttk.Button(main_frame, text="Parent Dashboard", command=self.show_parent_dashboard).pack(pady=10)
        
        # Logout button
        ttk.Button(main_frame, text="Logout", command=self.show_login_screen).pack(pady=10)
    
    def show_add_child(self):
        """Show add child dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Child Profile")
        dialog.geometry("400x400")
        
        fields = {}
        
        ttk.Label(dialog, text="Child's Name:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=10)
        fields['name'] = ttk.Entry(dialog, width=30)
        fields['name'].grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(dialog, text="Age:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=10)
        fields['age'] = ttk.Spinbox(dialog, from_=5, to=17, width=10)
        fields['age'].grid(row=1, column=1, pady=5, padx=10, sticky=tk.W)
        
        ttk.Label(dialog, text="Grade Level:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=10)
        fields['grade'] = ttk.Spinbox(dialog, from_=0, to=12, width=10)
        fields['grade'].grid(row=2, column=1, pady=5, padx=10, sticky=tk.W)
        
        ttk.Label(dialog, text="Learning Style:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=10)
        fields['style'] = ttk.Combobox(dialog, values=["Visual", "Auditory", "Kinesthetic", "Reading/Writing"])
        fields['style'].set("Visual")
        fields['style'].grid(row=3, column=1, pady=5, padx=10)
        
        def add_child():
            profile = ChildProfile(
                name=fields['name'].get(),
                age=int(fields['age'].get()),
                grade_level=int(fields['grade'].get()),
                learning_style=fields['style'].get().lower()
            )
            
            # Set safety level based on age
            if profile.age <= 7:
                profile.safety_level = SafetyLevel.MAXIMUM
            elif profile.age <= 10:
                profile.safety_level = SafetyLevel.HIGH
            elif profile.age <= 13:
                profile.safety_level = SafetyLevel.MODERATE
            else:
                profile.safety_level = SafetyLevel.STANDARD
            
            try:
                self.profile_manager.add_child(self.current_family_id, profile)
                messagebox.showinfo("Success", f"Added {profile.name} to your family!")
                dialog.destroy()
                self.show_child_selection()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(dialog, text="Add Child", command=add_child).grid(row=4, column=0, columnspan=2, pady=20)
    
    def start_child_session(self, child: ChildProfile):
        """Start a learning session for a child"""
        self.current_child_id = child.id
        self.current_session_id = self.profile_manager.start_session(child.id)
        self.show_learning_interface(child)
    
    def show_learning_interface(self, child: ChildProfile):
        """Show the main learning interface"""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Header
        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X, pady=10)
        
        ttk.Label(header, text=f"Welcome, {child.name}!", style='Heading.TLabel').pack(side=tk.LEFT)
        ttk.Button(header, text="End Session", command=self.end_session).pack(side=tk.RIGHT)
        
        # Launch button
        launch_frame = ttk.Frame(main_frame)
        launch_frame.pack(expand=True)
        
        ttk.Button(launch_frame, text="Launch Sunflower AI", 
                  command=self.launch_ai_interface, style='Primary.TButton').pack()
        
        self.status_label = ttk.Label(launch_frame, text="Ready to learn!", foreground="green")
        self.status_label.pack(pady=10)
    
    def launch_ai_interface(self):
        """Launch the main AI interface"""
        # This would normally open the Open WebUI interface
        # For now, show status
        self.status_label.config(text="AI Interface launching... Opening browser to http://localhost:8080")
        
        # Open browser
        import webbrowser
        webbrowser.open("http://localhost:8080")
    
    def show_parent_dashboard(self):
        """Show parent dashboard"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Parent Dashboard")
        dialog.geometry("800x600")
        
        notebook = ttk.Notebook(dialog)
        notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Children tab
        children_frame = ttk.Frame(notebook)
        notebook.add(children_frame, text="Children")
        
        children = self.profile_manager.get_children(self.current_family_id)
        for child in children:
            frame = ttk.LabelFrame(children_frame, text=child.name, padding="10")
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            info = f"""Age: {child.age} | Grade: {child.grade_level}
Safety Level: {child.safety_level.value}
Total Sessions: {child.total_sessions}
Total Learning Time: {child.total_learning_time}"""
            ttk.Label(frame, text=info).pack()
        
        # Sessions tab
        sessions_frame = ttk.Frame(notebook)
        notebook.add(sessions_frame, text="Recent Sessions")
        
        # Settings tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
    
    def end_session(self):
        """End current session"""
        if self.current_session_id:
            self.profile_manager.end_session(self.current_session_id)
            self.current_session_id = None
        
        self.show_child_selection()
    
    def start_services(self):
        """Start background services"""
        def start():
            self.status_label.config(text="Starting services...")
            if self.ollama_manager.start_service():
                if self.ollama_manager.load_model():
                    self.status_label.config(text="System Ready", foreground="green")
                else:
                    self.status_label.config(text="Model loading failed", foreground="red")
            else:
                self.status_label.config(text="Service start failed", foreground="red")
        
        # Run in background thread
        thread = threading.Thread(target=start, daemon=True)
        thread.start()
    
    def on_closing(self):
        """Handle window closing"""
        if self.current_session_id:
            self.profile_manager.end_session(self.current_session_id)
        
        self.ollama_manager.stop_service()
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        self.root.mainloop()


# ==================== MAIN ENTRY POINT ====================
def main():
    """Main entry point for launcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sunflower AI Launcher')
    parser.add_argument('--cdrom-path', type=Path, help='CD-ROM partition path')
    parser.add_argument('--usb-path', type=Path, help='USB partition path')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Detect partitions if not provided
    if not args.cdrom_path or not args.usb_path:
        # Try to auto-detect
        cdrom_path = Path("/Volumes/SUNFLOWER_CD") if platform.system() == "Darwin" else Path("D:\\")
        usb_path = Path("/Volumes/SUNFLOWER_DATA") if platform.system() == "Darwin" else Path("E:\\")
        
        if not cdrom_path.exists() or not usb_path.exists():
            print("Error: Could not detect partitions. Please specify paths.")
            sys.exit(1)
    else:
        cdrom_path = args.cdrom_path
        usb_path = args.usb_path
    
    # Launch UI
    launcher = SunflowerLauncherUI(cdrom_path, usb_path)
    launcher.run()


if __name__ == "__main__":
    main()

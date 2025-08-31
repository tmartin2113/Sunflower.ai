#!/usr/bin/env python3
"""
Sunflower AI Professional System - Common Launcher Utilities
Version: 6.2.0
Copyright (c) 2025 Sunflower AI Educational Systems
Production-Ready Cross-Platform Launcher Module
"""

import os
import sys
import json
import time
import uuid
import shutil
import hashlib
import logging
import argparse
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import secrets
import base64

# Try to import platform-specific modules
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# ==================== CONSTANTS ====================
SYSTEM_VERSION = "6.2.0"
PROFILE_DB_VERSION = 1
SESSION_TIMEOUT_MINUTES = 30
MAX_CHILDREN_PER_FAMILY = 10
MIN_PASSWORD_LENGTH = 8
MAX_CONVERSATION_HISTORY = 1000

# ==================== ENUMS ====================
class ModelTier(Enum):
    """AI model performance tiers"""
    MINIMAL = "llama3.2:1b-q4_0"
    LOW = "llama3.2:1b"
    MID = "llama3.2:3b"
    HIGH = "llama3.2:7b"

class UserRole(Enum):
    """User roles in the system"""
    PARENT = "parent"
    CHILD = "child"
    EDUCATOR = "educator"

class SafetyLevel(Enum):
    """Content safety levels"""
    MAXIMUM = "maximum"  # K-2
    HIGH = "high"        # Elementary
    MODERATE = "moderate" # Middle school
    STANDARD = "standard" # High school

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
            "total_learning_time": self.total_learning_time.total_seconds()
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

# ==================== PROFILE MANAGER ====================
class ProfileManager:
    """Manages family profiles and child accounts"""
    
    def __init__(self, usb_path: Path):
        self.usb_path = usb_path
        self.db_path = usb_path / "profiles" / "family_profiles.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """Initialize the profiles database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create tables
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
                device_id TEXT
            )
        """)
        
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
                FOREIGN KEY (family_id) REFERENCES families (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                child_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                conversations_count INTEGER DEFAULT 0,
                topics_covered TEXT,
                safety_incidents INTEGER DEFAULT 0,
                FOREIGN KEY (child_id) REFERENCES children (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                safety_filtered BOOLEAN DEFAULT 0,
                topic_category TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id),
                FOREIGN KEY (child_id) REFERENCES children (id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_children_family ON children(family_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_child ON sessions(child_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """Hash a password with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                           password.encode('utf-8'),
                                           salt.encode('utf-8'),
                                           100000)
        return base64.b64encode(password_hash).decode('utf-8'), salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify a password against hash"""
        test_hash = hashlib.pbkdf2_hmac('sha256',
                                       password.encode('utf-8'),
                                       salt.encode('utf-8'),
                                       100000)
        return base64.b64encode(test_hash).decode('utf-8') == password_hash
    
    def create_family(self, family_name: str, parent_email: str, password: str) -> str:
        """Create a new family account"""
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        password_hash, salt = self.hash_password(password)
        family_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO families (id, family_name, parent_email, password_hash, salt, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (family_id, family_name, parent_email, password_hash, salt, datetime.now().isoformat()))
            conn.commit()
            self.logger.info(f"Created family account: {family_name}")
            return family_id
        except sqlite3.IntegrityError:
            raise ValueError(f"Email {parent_email} is already registered")
        finally:
            conn.close()
    
    def authenticate_parent(self, email: str, password: str) -> Optional[str]:
        """Authenticate parent login"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, password_hash, salt FROM families WHERE parent_email = ?
        """, (email,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and self.verify_password(password, result[1], result[2]):
            # Update last login
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE families SET last_login = ? WHERE id = ?
            """, (datetime.now().isoformat(), result[0]))
            conn.commit()
            conn.close()
            return result[0]
        
        return None
    
    def add_child(self, family_id: str, profile: ChildProfile) -> str:
        """Add a child profile to a family"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Check child count
        cursor.execute("SELECT COUNT(*) FROM children WHERE family_id = ?", (family_id,))
        count = cursor.fetchone()[0]
        
        if count >= MAX_CHILDREN_PER_FAMILY:
            conn.close()
            raise ValueError(f"Maximum {MAX_CHILDREN_PER_FAMILY} children per family")
        
        cursor.execute("""
            INSERT INTO children (id, family_id, name, age, grade_level, safety_level, 
                                interests, learning_style, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (profile.id, family_id, profile.name, profile.age, profile.grade_level,
              profile.safety_level.value, json.dumps(profile.interests),
              profile.learning_style, profile.created_at.isoformat()))
        
        conn.commit()
        conn.close()
        self.logger.info(f"Added child profile: {profile.name}")
        return profile.id
    
    def get_children(self, family_id: str) -> List[ChildProfile]:
        """Get all children for a family"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM children WHERE family_id = ? ORDER BY name
        """, (family_id,))
        
        children = []
        for row in cursor.fetchall():
            child_data = {
                "id": row[0],
                "name": row[2],
                "age": row[3],
                "grade_level": row[4],
                "safety_level": row[5],
                "interests": row[6],
                "learning_style": row[7],
                "created_at": row[8],
                "last_active": row[9],
                "total_sessions": row[10],
                "total_learning_time": row[11]
            }
            children.append(ChildProfile.from_dict(child_data))
        
        conn.close()
        return children
    
    def start_session(self, child_id: str) -> str:
        """Start a new learning session"""
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (id, child_id, start_time)
            VALUES (?, ?, ?)
        """, (session_id, child_id, datetime.now().isoformat()))
        
        # Update child last active
        cursor.execute("""
            UPDATE children SET last_active = ? WHERE id = ?
        """, (datetime.now().isoformat(), child_id))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Started session {session_id} for child {child_id}")
        return session_id
    
    def end_session(self, session_id: str):
        """End a learning session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get session start time
        cursor.execute("SELECT start_time, child_id FROM sessions WHERE id = ?", (session_id,))
        result = cursor.fetchone()
        
        if result:
            start_time = datetime.fromisoformat(result[0])
            child_id = result[1]
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update session
            cursor.execute("""
                UPDATE sessions SET end_time = ?, duration_seconds = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), duration, session_id))
            
            # Update child stats
            cursor.execute("""
                UPDATE children 
                SET total_sessions = total_sessions + 1,
                    total_learning_time = total_learning_time + ?
                WHERE id = ?
            """, (duration, child_id))
            
            conn.commit()
        
        conn.close()
        self.logger.info(f"Ended session {session_id}")
    
    def log_conversation(self, session_id: str, child_id: str, user_message: str, 
                        ai_response: str, safety_filtered: bool = False, 
                        topic_category: str = "general"):
        """Log a conversation exchange"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        conversation_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO conversations (id, session_id, child_id, timestamp, 
                                     user_message, ai_response, safety_filtered, topic_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (conversation_id, session_id, child_id, datetime.now().isoformat(),
              user_message, ai_response, int(safety_filtered), topic_category))
        
        # Update session conversation count
        cursor.execute("""
            UPDATE sessions SET conversations_count = conversations_count + 1
            WHERE id = ?
        """, (session_id,))
        
        if safety_filtered:
            cursor.execute("""
                UPDATE sessions SET safety_incidents = safety_incidents + 1
                WHERE id = ?
            """, (session_id,))
        
        conn.commit()
        conn.close()

# ==================== HARDWARE DETECTOR ====================
class HardwareDetector:
    """Cross-platform hardware detection and model selection"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.logger = logging.getLogger(__name__)
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {
            "platform": self.platform,
            "cpu_cores": os.cpu_count() or 4,
            "ram_gb": self._get_ram_gb(),
            "has_gpu": self._detect_gpu(),
            "performance_score": 0
        }
        
        # Calculate performance score
        score = info["ram_gb"] * 10
        score += info["cpu_cores"] * 5
        if info["has_gpu"]:
            score += 30
        
        # Platform-specific bonuses
        if self.platform == "macos":
            # Check for Apple Silicon
            try:
                result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                      capture_output=True, text=True)
                if "Apple" in result.stdout:
                    score += 20
            except:
                pass
        
        info["performance_score"] = score
        return info
    
    def _get_ram_gb(self) -> int:
        """Get system RAM in GB"""
        try:
            if self.platform == "windows":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulong = ctypes.c_ulong
                class MEMORYSTATUS(ctypes.Structure):
                    _fields_ = [("dwLength", c_ulong),
                              ("dwMemoryLoad", c_ulong),
                              ("dwTotalPhys", ctypes.c_ulonglong)]
                memoryStatus = MEMORYSTATUS()
                memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUS)
                kernel32.GlobalMemoryStatus(ctypes.byref(memoryStatus))
                return memoryStatus.dwTotalPhys // (1024**3)
            else:
                # Unix-like systems
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if line.startswith('MemTotal'):
                            return int(line.split()[1]) // (1024**2)
        except:
            return 4  # Default fallback
        return 4
    
    def _detect_gpu(self) -> bool:
        """Detect if system has a capable GPU"""
        try:
            if self.platform == "windows":
                result = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"],
                                      capture_output=True, text=True)
                gpu_text = result.stdout.lower()
            else:
                result = subprocess.run(["lspci"], capture_output=True, text=True)
                gpu_text = result.stdout.lower()
            
            return any(gpu in gpu_text for gpu in ["nvidia", "amd", "radeon", "geforce"])
        except:
            return False
    
    def select_model(self) -> ModelTier:
        """Select optimal model based on hardware"""
        info = self.get_system_info()
        score = info["performance_score"]
        
        if score >= 121:
            return ModelTier.HIGH
        elif score >= 81:
            return ModelTier.MID
        elif score >= 51:
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
        self.ollama_exe = cdrom_path / "system" / "ollama" / ("ollama.exe" if sys.platform == "win32" else "ollama")
        self.ollama_home = usb_path / "ollama_data"
        self.ollama_home.mkdir(exist_ok=True)
        self.process = None
        self.logger = logging.getLogger(__name__)
    
    def start_service(self) -> bool:
        """Start Ollama service"""
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
            for _ in range(max_attempts):
                try:
                    response = requests.get("http://localhost:11434/api/tags")
                    if response.status_code == 200:
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
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.logger.info("Ollama service stopped")
    
    def chat(self, prompt: str, context: Dict = None) -> str:
        """Send chat message to model"""
        import requests
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if context:
            payload["context"] = context
        
        try:
            response = requests.post("http://localhost:11434/api/generate", json=payload)
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            self.logger.error(f"Chat request failed: {e}")
        
        return "I'm having trouble processing that request. Please try again."

# ==================== GUI APPLICATION ====================
class SunflowerAIApp:
    """Main GUI application"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path, model: str, platform: str):
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        self.model = model
        self.platform = platform
        
        # Initialize managers
        self.profile_manager = ProfileManager(usb_path)
        self.ollama_manager = OllamaManager(cdrom_path, usb_path, model)
        
        # Session state
        self.current_family_id = None
        self.current_child_id = None
        self.current_session_id = None
        
        # Setup logging
        log_file = usb_path / "logs" / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Start Ollama
        if not self.ollama_manager.start_service():
            self.show_error("Failed to start AI service")
            sys.exit(1)
        
        # Initialize GUI
        if GUI_AVAILABLE:
            self.setup_gui()
        else:
            self.logger.warning("GUI not available, running in CLI mode")
            self.run_cli()
    
    def setup_gui(self):
        """Setup the GUI interface"""
        self.root = tk.Tk()
        self.root.title(f"Sunflower AI Professional System v{SYSTEM_VERSION}")
        self.root.geometry("1024x768")
        
        # Apply modern styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom colors
        style.configure('Title.TLabel', font=('Helvetica', 24, 'bold'))
        style.configure('Heading.TLabel', font=('Helvetica', 14, 'bold'))
        
        # Start with login screen
        self.show_login_screen()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
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
        
        ttk.Button(button_frame, text="Login", command=self.handle_login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Register Family", command=self.show_registration).pack(side=tk.LEFT, padx=5)
    
    def show_registration(self):
        """Show family registration dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Register New Family")
        dialog.geometry("400x300")
        
        # Registration fields
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
                messagebox.showerror("Error", "Passwords do not match")
                return
            
            try:
                family_id = self.profile_manager.create_family(
                    fields['family'].get(),
                    fields['email'].get(),
                    fields['password'].get()
                )
                messagebox.showinfo("Success", "Family registered successfully! You can now login.")
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
        # Implementation continues with chat interface...
        # This would include the chat window, subject selection, etc.
        pass
    
    def show_parent_dashboard(self):
        """Show parent monitoring dashboard"""
        # Implementation for parent dashboard
        pass
    
    def run_cli(self):
        """Run in CLI mode if GUI not available"""
        print(f"Sunflower AI Professional System v{SYSTEM_VERSION}")
        print("Running in CLI mode - GUI libraries not available")
        print("\nStarting AI service...")
        
        # Basic CLI interface
        while True:
            command = input("\nEnter command (help/exit): ").strip().lower()
            if command == "exit":
                break
            elif command == "help":
                print("Available commands: help, exit")
            else:
                print(f"Unknown command: {command}")
    
    def show_error(self, message: str):
        """Show error message"""
        if GUI_AVAILABLE:
            messagebox.showerror("Error", message)
        else:
            print(f"ERROR: {message}")
    
    def on_closing(self):
        """Handle application closing"""
        if self.current_session_id:
            self.profile_manager.end_session(self.current_session_id)
        
        self.ollama_manager.stop_service()
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        if GUI_AVAILABLE:
            self.root.mainloop()
        else:
            self.run_cli()

# ==================== MAIN ENTRY POINT ====================
def main():
    """Main entry point for the launcher"""
    parser = argparse.ArgumentParser(description="Sunflower AI Professional System Launcher")
    parser.add_argument("--cdrom", required=True, help="Path to CD-ROM partition")
    parser.add_argument("--usb", required=True, help="Path to USB partition")
    parser.add_argument("--model", required=True, help="Selected AI model")
    parser.add_argument("--platform", required=True, choices=["windows", "macos"], help="Platform")
    parser.add_argument("--log-file", help="Log file path")
    
    args = parser.parse_args()
    
    # Convert paths
    cdrom_path = Path(args.cdrom)
    usb_path = Path(args.usb)
    
    # Validate paths
    if not cdrom_path.exists():
        print(f"Error: CD-ROM path does not exist: {cdrom_path}")
        sys.exit(1)
    
    if not usb_path.exists():
        print(f"Error: USB path does not exist: {usb_path}")
        sys.exit(1)
    
    # Create and run application
    app = SunflowerAIApp(cdrom_path, usb_path, args.model, args.platform)
    app.run()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Sunflower AI Professional System - Common Launcher Module
Shared functionality for Windows and macOS launchers
Version: 6.2.0 - Production Ready
"""

import os
import sys
import platform
import subprocess
import json
import time
import psutil
import socket
import hashlib
import sqlite3
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import webbrowser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SunflowerLauncher')


@dataclass
class SystemConfig:
    """System configuration data"""
    platform: str
    cdrom_path: Path
    usb_path: Path
    model_variant: str
    hardware_tier: str
    ram_gb: float
    cpu_cores: int
    ollama_port: int = 11434
    webui_port: int = 8080


class PartitionDetector:
    """Detect and validate partitioned device"""
    
    def __init__(self):
        self.platform = platform.system()
        self.cdrom_path = None
        self.usb_path = None
    
    def detect_partitions(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect CD-ROM and USB partitions"""
        if self.platform == "Windows":
            return self._detect_windows()
        elif self.platform == "Darwin":
            return self._detect_macos()
        else:
            return self._detect_linux()
    
    def _detect_windows(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect partitions on Windows"""
        import win32api
        import win32file
        
        cdrom_path = None
        usb_path = None
        
        drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
        
        for drive in drives:
            drive_type = win32file.GetDriveType(drive)
            
            # Check for CD-ROM partition marker
            marker_file = Path(drive) / "sunflower_cd.id"
            if marker_file.exists():
                cdrom_path = Path(drive)
                logger.info(f"Found CD-ROM partition: {cdrom_path}")
            
            # Check for USB data partition marker
            data_marker = Path(drive) / "sunflower_data.id"
            if data_marker.exists():
                usb_path = Path(drive)
                logger.info(f"Found USB partition: {usb_path}")
        
        return cdrom_path, usb_path
    
    def _detect_macos(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect partitions on macOS"""
        cdrom_path = None
        usb_path = None
        
        volumes_path = Path("/Volumes")
        
        for volume in volumes_path.iterdir():
            if volume.is_dir():
                # Check for partition markers
                cd_marker = volume / "sunflower_cd.id"
                data_marker = volume / "sunflower_data.id"
                
                if cd_marker.exists():
                    cdrom_path = volume
                    logger.info(f"Found CD-ROM partition: {cdrom_path}")
                
                if data_marker.exists():
                    usb_path = volume
                    logger.info(f"Found USB partition: {usb_path}")
        
        return cdrom_path, usb_path
    
    def _detect_linux(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect partitions on Linux"""
        cdrom_path = None
        usb_path = None
        
        # Check common mount points
        mount_points = [
            Path("/media"),
            Path("/mnt"),
            Path("/run/media") / os.environ.get("USER", "")
        ]
        
        for mount_base in mount_points:
            if not mount_base.exists():
                continue
            
            for mount in mount_base.iterdir():
                if mount.is_dir():
                    cd_marker = mount / "sunflower_cd.id"
                    data_marker = mount / "sunflower_data.id"
                    
                    if cd_marker.exists():
                        cdrom_path = mount
                        logger.info(f"Found CD-ROM partition: {cdrom_path}")
                    
                    if data_marker.exists():
                        usb_path = mount
                        logger.info(f"Found USB partition: {usb_path}")
        
        return cdrom_path, usb_path


class HardwareDetector:
    """Detect hardware capabilities for model selection"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'ram_gb': psutil.virtual_memory().total / (1024**3),
            'ram_available_gb': psutil.virtual_memory().available / (1024**3),
            'cpu_cores': psutil.cpu_count(logical=False),
            'cpu_threads': psutil.cpu_count(logical=True),
            'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            'disk_free_gb': psutil.disk_usage('/').free / (1024**3)
        }
        
        # Determine hardware tier
        ram_gb = info['ram_gb']
        cpu_cores = info['cpu_cores']
        
        if ram_gb >= 16 and cpu_cores >= 8:
            info['tier'] = 'high'
            info['recommended_model'] = 'llama3.2:7b'
        elif ram_gb >= 8 and cpu_cores >= 4:
            info['tier'] = 'medium'
            info['recommended_model'] = 'llama3.2:3b'
        elif ram_gb >= 4:
            info['tier'] = 'low'
            info['recommended_model'] = 'llama3.2:1b'
        else:
            info['tier'] = 'minimum'
            info['recommended_model'] = 'llama3.2:1b-q4_0'
        
        return info


class OllamaManager:
    """Manage Ollama service lifecycle"""
    
    def __init__(self, cdrom_path: Path, config: SystemConfig):
        self.cdrom_path = cdrom_path
        self.config = config
        self.process = None
        self.ollama_path = self._find_ollama_executable()
    
    def _find_ollama_executable(self) -> Optional[Path]:
        """Find Ollama executable on CD-ROM partition"""
        if self.config.platform == "Windows":
            ollama_exe = self.cdrom_path / "ollama" / "ollama.exe"
        else:
            ollama_exe = self.cdrom_path / "ollama" / "ollama"
        
        if ollama_exe.exists():
            return ollama_exe
        
        # Try root of CD-ROM
        if self.config.platform == "Windows":
            ollama_exe = self.cdrom_path / "ollama.exe"
        else:
            ollama_exe = self.cdrom_path / "ollama"
        
        if ollama_exe.exists():
            return ollama_exe
        
        logger.warning("Ollama executable not found on CD-ROM")
        return None
    
    def start_service(self) -> bool:
        """Start Ollama service"""
        if not self.ollama_path:
            logger.error("Cannot start Ollama - executable not found")
            return False
        
        try:
            # Check if already running
            if self.is_running():
                logger.info("Ollama already running")
                return True
            
            # Start Ollama service
            env = os.environ.copy()
            env['OLLAMA_HOST'] = f"0.0.0.0:{self.config.ollama_port}"
            env['OLLAMA_MODELS'] = str(self.cdrom_path / "models")
            
            self.process = subprocess.Popen(
                [str(self.ollama_path), "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if self.config.platform == "Windows" else 0
            )
            
            # Wait for service to be ready
            for _ in range(30):
                if self.is_running():
                    logger.info("Ollama service started successfully")
                    return True
                time.sleep(1)
            
            logger.error("Ollama service failed to start")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if Ollama is running"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', self.config.ollama_port))
            sock.close()
            return result == 0
        except:
            return False
    
    def stop_service(self):
        """Stop Ollama service"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                if self.config.platform == "Windows":
                    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], 
                                 capture_output=True)
                else:
                    subprocess.run(["pkill", "-f", "ollama"], 
                                 capture_output=True)
            self.process = None
            logger.info("Ollama service stopped")
    
    def load_model(self, model_name: Optional[str] = None) -> bool:
        """Load specified model or auto-detect best model"""
        if not model_name:
            model_name = self.config.model_variant
        
        try:
            # Check if model exists
            model_path = self.cdrom_path / "models" / f"{model_name}.gguf"
            if not model_path.exists():
                logger.warning(f"Model file not found: {model_path}")
                # Try to pull from Ollama library if online
                result = subprocess.run(
                    [str(self.ollama_path), "pull", model_name],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    return False
            
            # Load the model
            result = subprocess.run(
                [str(self.ollama_path), "run", model_name, "hello"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


class ProfileManager:
    """Manage family and child profiles"""
    
    def __init__(self, usb_path: Path):
        self.usb_path = usb_path
        self.profiles_dir = usb_path / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.profiles_dir / "profiles.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize profiles database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS family (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_name TEXT NOT NULL,
                parent_password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                grade TEXT,
                avatar TEXT,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES family (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration_minutes INTEGER,
                interactions INTEGER DEFAULT 0,
                topics TEXT,
                FOREIGN KEY (child_id) REFERENCES children (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def authenticate_parent(self, password: str) -> bool:
        """Verify parent password"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT parent_password_hash FROM family LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        stored_hash = result[0]
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == stored_hash
    
    def create_family(self, family_name: str, password: str) -> bool:
        """Create new family account"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Check if family already exists
        cursor.execute("SELECT COUNT(*) FROM family")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return False
        
        # Create family
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO family (family_name, parent_password_hash) VALUES (?, ?)",
            (family_name, password_hash)
        )
        
        conn.commit()
        conn.close()
        return True
    
    def add_child_profile(self, name: str, age: int, grade: str = None, 
                         avatar: str = "🦄") -> int:
        """Add a child profile"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get family ID
        cursor.execute("SELECT id FROM family LIMIT 1")
        family_id = cursor.fetchone()[0]
        
        # Add child
        cursor.execute(
            "INSERT INTO children (family_id, name, age, grade, avatar) VALUES (?, ?, ?, ?, ?)",
            (family_id, name, age, grade, avatar)
        )
        
        child_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return child_id
    
    def get_children(self) -> List[Dict]:
        """Get all child profiles"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, age, grade, avatar FROM children")
        children = []
        for row in cursor.fetchall():
            children.append({
                'id': row[0],
                'name': row[1],
                'age': row[2],
                'grade': row[3],
                'avatar': row[4]
            })
        
        conn.close()
        return children
    
    def start_session(self, child_id: int) -> int:
        """Start a new session for a child"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO sessions (child_id) VALUES (?)",
            (child_id,)
        )
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def end_session(self, session_id: int):
        """End a session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE sessions SET end_time = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
        
        conn.commit()
        conn.close()


class SunflowerLauncherUI:
    """Main launcher user interface"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        
        # Initialize system configuration
        hardware_info = HardwareDetector.get_system_info()
        self.config = SystemConfig(
            platform=platform.system(),
            cdrom_path=cdrom_path,
            usb_path=usb_path,
            model_variant=hardware_info['recommended_model'],
            hardware_tier=hardware_info['tier'],
            ram_gb=hardware_info['ram_gb'],
            cpu_cores=hardware_info['cpu_cores']
        )
        
        # Initialize managers
        self.ollama_manager = OllamaManager(cdrom_path, self.config)
        self.profile_manager = ProfileManager(usb_path)
        
        # Session tracking
        self.current_session_id = None
        
        # Create UI
        self.create_ui()
    
    def create_ui(self):
        """Create the main user interface"""
        self.root = tk.Tk()
        self.root.title("🌻 Sunflower AI Professional System")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # Apply styling
        self.setup_styles()
        
        # Create header
        self.create_header()
        
        # Create main content area
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Check if family exists
        if not self.check_family_exists():
            self.show_family_setup()
        else:
            self.show_login()
        
        # Create status bar
        self.create_status_bar()
        
        # Start background services
        self.start_services()
    
    def setup_styles(self):
        """Configure UI styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Header.TFrame', background='#5e72e4')
        style.configure('Header.TLabel', background='#5e72e4', foreground='white',
                       font=('Segoe UI', 18, 'bold'))
        style.configure('Success.TButton', foreground='green')
        style.configure('Warning.TButton', foreground='orange')
    
    def create_header(self):
        """Create application header"""
        header_frame = ttk.Frame(self.root, style='Header.TFrame', height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = ttk.Label(
            header_frame,
            text="🌻 Sunflower AI Professional System",
            style='Header.TLabel'
        )
        title_label.pack(pady=20)
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Family-Focused K-12 STEM Education",
            style='Header.TLabel',
            font=('Segoe UI', 11)
        )
        subtitle_label.pack()
    
    def create_status_bar(self):
        """Create status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            status_frame,
            text=f"Hardware: {self.config.hardware_tier.upper()} | Model: {self.config.model_variant}",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def check_family_exists(self) -> bool:
        """Check if a family account exists"""
        db_path = self.usb_path / "profiles" / "profiles.db"
        if not db_path.exists():
            return False
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM family")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def show_family_setup(self):
        """Show family setup screen"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        setup_frame = ttk.Frame(self.content_frame)
        setup_frame.pack(pady=50)
        
        ttk.Label(
            setup_frame,
            text="Welcome! Let's set up your family account",
            font=('Segoe UI', 14, 'bold')
        ).grid(row=0, column=0, columnspan=2, pady=20)
        
        ttk.Label(setup_frame, text="Family Name:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.family_name_entry = ttk.Entry(setup_frame, width=30)
        self.family_name_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(setup_frame, text="Parent Password:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.password_entry = ttk.Entry(setup_frame, width=30, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(setup_frame, text="Confirm Password:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.confirm_password_entry = ttk.Entry(setup_frame, width=30, show="*")
        self.confirm_password_entry.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Button(
            setup_frame,
            text="Create Family Account",
            command=self.create_family_account
        ).grid(row=4, column=0, columnspan=2, pady=20)
    
    def create_family_account(self):
        """Create new family account"""
        family_name = self.family_name_entry.get()
        password = self.password_entry.get()
        confirm = self.confirm_password_entry.get()
        
        if not family_name or not password:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return
        
        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters")
            return
        
        if self.profile_manager.create_family(family_name, password):
            messagebox.showinfo("Success", "Family account created successfully!")
            self.show_child_setup()
        else:
            messagebox.showerror("Error", "Failed to create family account")
    
    def show_login(self):
        """Show parent login screen"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        login_frame = ttk.Frame(self.content_frame)
        login_frame.pack(pady=100)
        
        ttk.Label(
            login_frame,
            text="Parent Login",
            font=('Segoe UI', 16, 'bold')
        ).grid(row=0, column=0, columnspan=2, pady=20)
        
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.login_password_entry = ttk.Entry(login_frame, width=30, show="*")
        self.login_password_entry.grid(row=1, column=1, padx=5, pady=5)
        self.login_password_entry.bind('<Return>', lambda e: self.parent_login())
        
        ttk.Button(
            login_frame,
            text="Login",
            command=self.parent_login
        ).grid(row=2, column=0, columnspan=2, pady=20)
    
    def parent_login(self):
        """Authenticate parent"""
        password = self.login_password_entry.get()
        
        if self.profile_manager.authenticate_parent(password):
            self.show_child_selection()
        else:
            messagebox.showerror("Error", "Invalid password")
    
    def show_child_setup(self):
        """Show child profile setup"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        setup_frame = ttk.Frame(self.content_frame)
        setup_frame.pack(pady=50)
        
        ttk.Label(
            setup_frame,
            text="Add Your First Child",
            font=('Segoe UI', 14, 'bold')
        ).grid(row=0, column=0, columnspan=2, pady=20)
        
        ttk.Label(setup_frame, text="Child's Name:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.child_name_entry = ttk.Entry(setup_frame, width=30)
        self.child_name_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(setup_frame, text="Age:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.age_spinbox = ttk.Spinbox(setup_frame, from_=2, to=18, width=10)
        self.age_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(setup_frame, text="Grade:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.grade_combo = ttk.Combobox(setup_frame, width=27, values=[
            "Pre-K", "Kindergarten", "1st Grade", "2nd Grade", "3rd Grade",
            "4th Grade", "5th Grade", "6th Grade", "7th Grade", "8th Grade",
            "9th Grade", "10th Grade", "11th Grade", "12th Grade"
        ])
        self.grade_combo.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(setup_frame, text="Avatar:").grid(row=4, column=0, sticky=tk.E, padx=5, pady=5)
        avatar_frame = ttk.Frame(setup_frame)
        avatar_frame.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        self.avatar_var = tk.StringVar(value="🦄")
        avatars = ["🦄", "🚀", "🎮", "🎨", "🏀", "🎭", "🎸", "🦖"]
        for i, avatar in enumerate(avatars):
            ttk.Radiobutton(
                avatar_frame,
                text=avatar,
                variable=self.avatar_var,
                value=avatar
            ).grid(row=0, column=i, padx=2)
        
        button_frame = ttk.Frame(setup_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame,
            text="Add Child",
            command=self.add_child
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Skip for Now",
            command=self.show_main_menu
        ).pack(side=tk.LEFT, padx=5)
    
    def add_child(self):
        """Add a child profile"""
        name = self.child_name_entry.get()
        age = int(self.age_spinbox.get())
        grade = self.grade_combo.get()
        avatar = self.avatar_var.get()
        
        if not name:
            messagebox.showerror("Error", "Please enter child's name")
            return
        
        child_id = self.profile_manager.add_child_profile(name, age, grade, avatar)
        messagebox.showinfo("Success", f"{name}'s profile created!")
        
        # Ask if they want to add another child
        if messagebox.askyesno("Add Another", "Would you like to add another child?"):
            self.child_name_entry.delete(0, tk.END)
            self.age_spinbox.set(2)
            self.grade_combo.set("")
        else:
            self.show_child_selection()
    
    def show_child_selection(self):
        """Show child profile selection screen"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        selection_frame = ttk.Frame(self.content_frame)
        selection_frame.pack(pady=50)
        
        ttk.Label(
            selection_frame,
            text="Who's Learning Today?",
            font=('Segoe UI', 16, 'bold')
        ).pack(pady=20)
        
        children = self.profile_manager.get_children()
        
        if not children:
            ttk.Label(
                selection_frame,
                text="No child profiles found. Please add a child first.",
                font=('Segoe UI', 11)
            ).pack(pady=20)
            
            ttk.Button(
                selection_frame,
                text="Add Child",
                command=self.show_child_setup
            ).pack(pady=10)
        else:
            # Create grid of child buttons
            button_frame = ttk.Frame(selection_frame)
            button_frame.pack(pady=20)
            
            for i, child in enumerate(children):
                row = i // 3
                col = i % 3
                
                btn = tk.Button(
                    button_frame,
                    text=f"{child['avatar']}\n{child['name']}\nAge {child['age']}",
                    width=15,
                    height=5,
                    font=('Segoe UI', 11),
                    command=lambda c=child: self.select_child(c)
                )
                btn.grid(row=row, column=col, padx=10, pady=10)
            
            # Add parent options
            parent_frame = ttk.Frame(selection_frame)
            parent_frame.pack(pady=30)
            
            ttk.Button(
                parent_frame,
                text="Add New Child",
                command=self.show_child_setup
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                parent_frame,
                text="Parent Dashboard",
                command=self.show_parent_dashboard
            ).pack(side=tk.LEFT, padx=5)
    
    def select_child(self, child: Dict):
        """Select a child profile and start session"""
        # Start session
        self.current_session_id = self.profile_manager.start_session(child['id'])
        
        # Launch appropriate interface based on age
        if child['age'] <= 13:
            model = "sunflower-kids"
        else:
            model = "sunflower-educator"
        
        # Configure and launch
        self.launch_ai_interface(child, model)
    
    def launch_ai_interface(self, child: Dict, model: str):
        """Launch the AI interface for selected child"""
        # Update status
        self.status_label.config(
            text=f"Loading AI for {child['name']} (Age {child['age']})..."
        )
        
        # Ensure Ollama is running
        if not self.ollama_manager.is_running():
            self.ollama_manager.start_service()
        
        # Load appropriate model
        self.ollama_manager.load_model(model)
        
        # Open web interface
        webbrowser.open(f"http://localhost:{self.config.webui_port}")
        
        # Show session controls
        self.show_session_controls(child)
    
    def show_session_controls(self, child: Dict):
        """Show session control panel"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        control_frame = ttk.Frame(self.content_frame)
        control_frame.pack(pady=50)
        
        ttk.Label(
            control_frame,
            text=f"{child['avatar']} {child['name']} is Learning!",
            font=('Segoe UI', 18, 'bold')
        ).pack(pady=20)
        
        ttk.Label(
            control_frame,
            text="The AI interface has opened in your browser.",
            font=('Segoe UI', 11)
        ).pack(pady=10)
        
        ttk.Label(
            control_frame,
            text=f"Web Interface: http://localhost:{self.config.webui_port}",
            font=('Segoe UI', 10),
            foreground='blue'
        ).pack(pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=30)
        
        ttk.Button(
            button_frame,
            text="End Session",
            command=self.end_session,
            style='Warning.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Switch Child",
            command=self.end_session
        ).pack(side=tk.LEFT, padx=5)
    
    def show_parent_dashboard(self):
        """Show parent dashboard"""
        dashboard_path = self.cdrom_path / "data" / "parent_dashboard.html"
        if dashboard_path.exists():
            webbrowser.open(f"file://{dashboard_path}")
        else:
            messagebox.showinfo("Dashboard", "Parent dashboard will be available soon!")
    
    def show_main_menu(self):
        """Show main menu"""
        self.show_child_selection()
    
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
        detector = PartitionDetector()
        cdrom_path, usb_path = detector.detect_partitions()
        
        if not cdrom_path or not usb_path:
            # Try manual fallback paths
            if platform.system() == "Windows":
                cdrom_path = Path("D:\\")
                usb_path = Path("E:\\")
            elif platform.system() == "Darwin":
                cdrom_path = Path("/Volumes/SUNFLOWER_CD")
                usb_path = Path("/Volumes/SUNFLOWER_DATA")
            else:
                cdrom_path = Path("/media/SUNFLOWER_CD")
                usb_path = Path("/media/SUNFLOWER_DATA")
        
        if not cdrom_path.exists() or not usb_path.exists():
            messagebox.showerror(
                "Partition Detection Failed",
                "Could not detect Sunflower AI partitions.\n\n"
                "Please ensure the device is properly connected and try again."
            )
            sys.exit(1)
    else:
        cdrom_path = args.cdrom_path
        usb_path = args.usb_path
    
    # Launch UI
    launcher = SunflowerLauncherUI(cdrom_path, usb_path)
    launcher.run()


if __name__ == "__main__":
    main()

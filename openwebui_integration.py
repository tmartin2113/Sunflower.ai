#!/usr/bin/env python3
"""
Sunflower AI Open WebUI Integration Manager
Complete integration of Open WebUI with family profiles and partitioned device architecture
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import hashlib
import secrets
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import logging

class OpenWebUIIntegrator:
    """Manages Open WebUI integration with Sunflower AI system"""
    
    def __init__(self):
        self.system = platform.system()
        self.root_dir = Path(__file__).parent
        
        # Detect partitions
        self.cdrom_partition = self.detect_cdrom_partition()
        self.usb_partition = self.detect_usb_partition()
        
        # Set paths based on partitions
        if self.cdrom_partition:
            self.app_dir = self.cdrom_partition
        else:
            self.app_dir = self.root_dir
            
        if self.usb_partition:
            self.data_dir = self.usb_partition / "sunflower_data"
        else:
            self.data_dir = self.root_dir / "data"
            
        # Open WebUI specific paths
        self.openwebui_dir = self.data_dir / "openwebui"
        self.openwebui_data = self.openwebui_dir / "data"
        self.openwebui_config = self.openwebui_dir / "config"
        self.openwebui_db = self.openwebui_data / "webui.db"
        
        # Family profile paths
        self.profiles_dir = self.data_dir / "profiles"
        self.family_config = self.profiles_dir / "family.json"
        self.session_logs = self.data_dir / "sessions"
        
        # Ollama paths
        self.ollama_dir = self.data_dir / "ollama"
        self.models_dir = self.ollama_dir / "models"
        
        # Setup logging
        self.setup_logging()
        
    def detect_cdrom_partition(self) -> Optional[Path]:
        """Detect CD-ROM partition containing system files"""
        # Check for CD-ROM marker file
        marker_file = "sunflower_cd.id"
        
        if self.system == "Windows":
            # Check all drives for CD-ROM partition
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                if drive_path.exists():
                    marker_path = drive_path / marker_file
                    if marker_path.exists():
                        return drive_path
        else:
            # macOS/Linux: Check mounted volumes
            volumes = ["/Volumes", "/media", "/mnt"]
            for volume_dir in volumes:
                if Path(volume_dir).exists():
                    for mount in Path(volume_dir).iterdir():
                        marker_path = mount / marker_file
                        if marker_path.exists():
                            return mount
        return None
        
    def detect_usb_partition(self) -> Optional[Path]:
        """Detect USB write-able partition for user data"""
        marker_file = "sunflower_data.id"
        
        if self.system == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                if drive_path.exists():
                    marker_path = drive_path / marker_file
                    if marker_path.exists():
                        return drive_path
        else:
            # macOS/Linux
            volumes = ["/Volumes", "/media", "/mnt"]
            for volume_dir in volumes:
                if Path(volume_dir).exists():
                    for mount in Path(volume_dir).iterdir():
                        marker_path = mount / marker_file
                        if marker_path.exists():
                            return mount
        return None
        
    def setup_logging(self):
        """Configure logging system"""
        log_dir = self.data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"openwebui_{datetime.now():%Y%m%d}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("OpenWebUIIntegrator")
        
    def initialize_directory_structure(self):
        """Create required directory structure on USB partition"""
        directories = [
            self.openwebui_dir,
            self.openwebui_data,
            self.openwebui_config,
            self.profiles_dir,
            self.session_logs,
            self.ollama_dir,
            self.models_dir,
            self.data_dir / "backups",
            self.data_dir / "cache"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        self.logger.info(f"Initialized directory structure at {self.data_dir}")
        
    def install_open_webui(self) -> bool:
        """Install Open WebUI with proper configuration"""
        try:
            # Check if Open WebUI is already installed
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "open-webui"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                self.logger.info("Installing Open WebUI...")
                
                # Install Open WebUI
                subprocess.run([
                    sys.executable, "-m", "pip", "install", 
                    "--quiet", "--upgrade", "open-webui"
                ], check=True)
                
                self.logger.info("Open WebUI installed successfully")
            else:
                self.logger.info("Open WebUI already installed")
                
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install Open WebUI: {e}")
            return False
            
    def configure_open_webui(self):
        """Configure Open WebUI for Sunflower AI system"""
        # Create Open WebUI configuration
        config = {
            "WEBUI_NAME": "Sunflower AI Education System",
            "WEBUI_URL": "http://localhost:8080",
            "DATA_DIR": str(self.openwebui_data),
            "ENABLE_SIGNUP": False,  # Disable public signup
            "DEFAULT_MODELS": "sunflower-kids,sunflower-educator",
            "DEFAULT_USER_ROLE": "user",
            "WEBUI_AUTH": True,
            "WEBUI_AUTH_TRUSTED_EMAIL_HEADER": "",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "ENABLE_OLLAMA_API": True,
            "ENABLE_MODEL_FILTER": True,
            "MODEL_FILTER_LIST": "sunflower-kids,sunflower-educator,llama3.2:3b,llama3.2:1b",
            "WEBUI_SESSION_COOKIE_SAME_SITE": "lax",
            "WEBUI_SESSION_COOKIE_SECURE": False,  # For local usage
            "ENABLE_ADMIN_EXPORT": True,
            "ENABLE_COMMUNITY_SHARING": False,
            "ENABLE_MESSAGE_RATING": True,
            "SHOW_ADMIN_DETAILS": False,
            "WEBUI_BANNERS": [],
            "ENABLE_SIGNUP": False,
            "USER_PERMISSIONS": {
                "chat": {
                    "deletion": True,
                    "editing": True,
                    "temporary": False
                }
            }
        }
        
        # Write configuration
        config_file = self.openwebui_config / "config.json"
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
            
        # Set environment variables
        for key, value in config.items():
            os.environ[key] = str(value)
            
        self.logger.info("Open WebUI configured for Sunflower AI")
        
    def setup_authentication(self) -> Dict[str, str]:
        """Setup family authentication system"""
        # Generate secure admin password if not exists
        if not self.family_config.exists():
            admin_password = secrets.token_urlsafe(12)
            family_data = {
                "family_id": secrets.token_hex(16),
                "created": datetime.now().isoformat(),
                "admin_password_hash": hashlib.sha256(admin_password.encode()).hexdigest(),
                "admin_password_temp": admin_password,  # Store temporarily for first setup
                "profiles": [],
                "settings": {
                    "content_filtering": True,
                    "session_recording": True,
                    "age_verification": True,
                    "max_session_minutes": 60
                }
            }
            
            with open(self.family_config, "w") as f:
                json.dump(family_data, f, indent=2)
                
            self.logger.info(f"Created family profile with admin password: {admin_password}")
            return {"admin_password": admin_password, "status": "created"}
        else:
            with open(self.family_config, "r") as f:
                family_data = json.load(f)
                
            # Check if temporary password exists (first run)
            if "admin_password_temp" in family_data:
                admin_password = family_data["admin_password_temp"]
                # Remove temporary password after retrieval
                del family_data["admin_password_temp"]
                with open(self.family_config, "w") as f:
                    json.dump(family_data, f, indent=2)
                return {"admin_password": admin_password, "status": "retrieved"}
                
            return {"status": "exists"}
            
    def create_child_profile(self, name: str, age: int, grade: str) -> bool:
        """Create a child profile with appropriate settings"""
        try:
            with open(self.family_config, "r") as f:
                family_data = json.load(f)
                
            # Create child profile
            profile = {
                "id": secrets.token_hex(8),
                "name": name,
                "age": age,
                "grade": grade,
                "created": datetime.now().isoformat(),
                "settings": self.get_age_appropriate_settings(age),
                "learning_level": self.determine_learning_level(age, grade),
                "safety_level": self.determine_safety_level(age)
            }
            
            family_data["profiles"].append(profile)
            
            with open(self.family_config, "w") as f:
                json.dump(family_data, f, indent=2)
                
            # Create Open WebUI user for child
            self.create_webui_user(profile)
            
            self.logger.info(f"Created profile for {name} (age {age})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create child profile: {e}")
            return False
            
    def get_age_appropriate_settings(self, age: int) -> Dict:
        """Get age-appropriate settings for child"""
        if age <= 7:  # K-2
            return {
                "max_response_length": 50,
                "complexity_level": "simple",
                "safety_filter": "maximum",
                "allowed_topics": ["basic_science", "math", "reading"],
                "session_time_limit": 20
            }
        elif age <= 10:  # Elementary
            return {
                "max_response_length": 75,
                "complexity_level": "elementary",
                "safety_filter": "high",
                "allowed_topics": ["science", "math", "technology", "engineering"],
                "session_time_limit": 30
            }
        elif age <= 13:  # Middle School
            return {
                "max_response_length": 125,
                "complexity_level": "intermediate",
                "safety_filter": "moderate",
                "allowed_topics": ["all_stem"],
                "session_time_limit": 45
            }
        else:  # High School
            return {
                "max_response_length": 200,
                "complexity_level": "advanced",
                "safety_filter": "standard",
                "allowed_topics": ["all_stem", "research"],
                "session_time_limit": 60
            }
            
    def determine_learning_level(self, age: int, grade: str) -> str:
        """Determine appropriate learning level"""
        if age <= 7:
            return "early-elementary"
        elif age <= 10:
            return "elementary"
        elif age <= 13:
            return "middle-school"
        else:
            return "high-school"
            
    def determine_safety_level(self, age: int) -> str:
        """Determine appropriate safety level"""
        if age <= 10:
            return "maximum"
        elif age <= 13:
            return "high"
        else:
            return "standard"
            
    def create_webui_user(self, profile: Dict):
        """Create user in Open WebUI database"""
        try:
            # Connect to Open WebUI database
            conn = sqlite3.connect(self.openwebui_db)
            cursor = conn.cursor()
            
            # Create users table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    role TEXT DEFAULT 'user',
                    profile_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert user
            user_id = profile["id"]
            email = f"{profile['name'].lower().replace(' ', '_')}@sunflower.local"
            
            cursor.execute('''
                INSERT OR REPLACE INTO users (id, name, email, role, profile_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                profile["name"],
                email,
                "user",
                json.dumps(profile)
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created Open WebUI user for {profile['name']}")
            
        except Exception as e:
            self.logger.error(f"Failed to create WebUI user: {e}")
            
    def start_ollama(self) -> bool:
        """Start Ollama service"""
        try:
            # Check if Ollama is already running
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self.logger.info("Ollama already running")
                return True
                
            # Start Ollama based on platform
            if self.system == "Windows":
                ollama_exe = self.app_dir / "ollama" / "ollama.exe"
                if not ollama_exe.exists():
                    ollama_exe = shutil.which("ollama")
                    
                if ollama_exe:
                    subprocess.Popen([str(ollama_exe), "serve"], 
                                   env={**os.environ, "OLLAMA_MODELS": str(self.models_dir)})
                else:
                    self.logger.error("Ollama executable not found")
                    return False
                    
            else:  # macOS/Linux
                ollama_bin = shutil.which("ollama")
                if ollama_bin:
                    subprocess.Popen([ollama_bin, "serve"],
                                   env={**os.environ, "OLLAMA_MODELS": str(self.models_dir)})
                else:
                    self.logger.error("Ollama not found in PATH")
                    return False
                    
            # Wait for Ollama to start
            for _ in range(30):
                time.sleep(1)
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:11434/api/tags"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    self.logger.info("Ollama started successfully")
                    return True
                    
            self.logger.error("Ollama failed to start within timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start Ollama: {e}")
            return False
            
    def load_models(self) -> bool:
        """Load Sunflower AI models"""
        try:
            models_to_load = []
            
            # Check for pre-built models on CD-ROM partition
            if self.cdrom_partition:
                cdrom_models = self.cdrom_partition / "models"
                if cdrom_models.exists():
                    for model_file in cdrom_models.glob("*.gguf"):
                        dest = self.models_dir / model_file.name
                        if not dest.exists():
                            shutil.copy2(model_file, dest)
                            self.logger.info(f"Copied model: {model_file.name}")
                            
            # Load Sunflower modelfiles
            modelfiles_dir = self.app_dir / "modelfiles"
            if modelfiles_dir.exists():
                for modelfile in modelfiles_dir.glob("*.modelfile"):
                    model_name = modelfile.stem.lower().replace("_", "-")
                    
                    # Create model using Ollama
                    result = subprocess.run([
                        "ollama", "create", model_name, "-f", str(modelfile)
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        self.logger.info(f"Created model: {model_name}")
                    else:
                        self.logger.warning(f"Failed to create model {model_name}: {result.stderr}")
                        
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")
            return False
            
    def start_open_webui(self) -> bool:
        """Start Open WebUI server"""
        try:
            # Set environment variables
            env = os.environ.copy()
            env.update({
                "DATA_DIR": str(self.openwebui_data),
                "WEBUI_NAME": "Sunflower AI",
                "WEBUI_AUTH": "true",
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "HOST": "127.0.0.1",
                "PORT": "8080"
            })
            
            # Start Open WebUI
            cmd = [sys.executable, "-m", "open_webui", "serve"]
            
            self.webui_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for startup
            for _ in range(30):
                time.sleep(1)
                try:
                    import requests
                    response = requests.get("http://localhost:8080/health", timeout=1)
                    if response.status_code == 200:
                        self.logger.info("Open WebUI started successfully")
                        return True
                except:
                    continue
                    
            self.logger.error("Open WebUI failed to start within timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start Open WebUI: {e}")
            return False
            
    def monitor_session(self, profile_id: str):
        """Monitor and log child's session"""
        session_file = self.session_logs / f"{profile_id}_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        session_data = {
            "profile_id": profile_id,
            "start_time": datetime.now().isoformat(),
            "conversations": [],
            "safety_alerts": [],
            "learning_metrics": {}
        }
        
        # This would be called periodically to update session data
        # In production, this would interface with Open WebUI's API
        
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)
            
        self.logger.info(f"Session logged: {session_file}")
        
    def create_parent_dashboard(self):
        """Create parent dashboard for monitoring"""
        dashboard_file = self.data_dir / "parent_dashboard.html"
        
        dashboard_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunflower AI - Parent Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .profile-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .profile-card {
            border: 2px solid #e1e4e8;
            border-radius: 10px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .profile-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        .profile-name {
            font-size: 1.3em;
            font-weight: bold;
            color: #5e72e4;
            margin-bottom: 10px;
        }
        .profile-info {
            color: #666;
            line-height: 1.6;
        }
        .session-stats {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e1e4e8;
        }
        .stat-item {
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
        }
        .action-buttons {
            margin-top: 20px;
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        .btn-primary {
            background: #5e72e4;
            color: white;
        }
        .btn-primary:hover {
            background: #4c63d2;
        }
        .btn-secondary {
            background: #f4f5f7;
            color: #333;
        }
        .btn-secondary:hover {
            background: #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌻 Sunflower AI Parent Dashboard</h1>
        
        <div class="profile-grid" id="profileGrid">
            <!-- Profiles will be loaded here -->
        </div>
        
        <div class="action-buttons">
            <button class="btn btn-primary" onclick="addChildProfile()">Add Child Profile</button>
            <button class="btn btn-secondary" onclick="viewAllSessions()">View All Sessions</button>
            <button class="btn btn-secondary" onclick="exportData()">Export Data</button>
        </div>
    </div>
    
    <script>
        // Load family profiles
        async function loadProfiles() {
            try {
                const response = await fetch('/api/profiles');
                const profiles = await response.json();
                
                const grid = document.getElementById('profileGrid');
                grid.innerHTML = profiles.map(profile => `
                    <div class="profile-card">
                        <div class="profile-name">${profile.name}</div>
                        <div class="profile-info">
                            <div>Age: ${profile.age} years</div>
                            <div>Grade: ${profile.grade}</div>
                            <div>Safety Level: ${profile.safety_level}</div>
                        </div>
                        <div class="session-stats">
                            <div class="stat-item">
                                <span>Total Sessions:</span>
                                <strong>${profile.total_sessions || 0}</strong>
                            </div>
                            <div class="stat-item">
                                <span>Learning Time:</span>
                                <strong>${profile.total_hours || 0} hours</strong>
                            </div>
                            <div class="stat-item">
                                <span>Last Active:</span>
                                <strong>${profile.last_active || 'Never'}</strong>
                            </div>
                        </div>
                        <div class="action-buttons">
                            <button class="btn btn-primary" onclick="viewSessions('${profile.id}')">
                                View Sessions
                            </button>
                            <button class="btn btn-secondary" onclick="editProfile('${profile.id}')">
                                Edit
                            </button>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Failed to load profiles:', error);
            }
        }
        
        function addChildProfile() {
            window.location.href = '/add-profile';
        }
        
        function viewSessions(profileId) {
            window.location.href = `/sessions/${profileId}`;
        }
        
        function editProfile(profileId) {
            window.location.href = `/edit-profile/${profileId}`;
        }
        
        function viewAllSessions() {
            window.location.href = '/all-sessions';
        }
        
        function exportData() {
            window.location.href = '/export';
        }
        
        // Load profiles on page load
        document.addEventListener('DOMContentLoaded', loadProfiles);
    </script>
</body>
</html>"""
        
        with open(dashboard_file, "w") as f:
            f.write(dashboard_html)
            
        self.logger.info(f"Parent dashboard created: {dashboard_file}")
        
    def run(self):
        """Main execution flow"""
        print("🌻 Sunflower AI - Open WebUI Integration")
        print("=" * 50)
        
        # Initialize directory structure
        print("Initializing directory structure...")
        self.initialize_directory_structure()
        
        # Install Open WebUI
        print("Installing Open WebUI...")
        if not self.install_open_webui():
            print("❌ Failed to install Open WebUI")
            return False
            
        # Configure Open WebUI
        print("Configuring Open WebUI...")
        self.configure_open_webui()
        
        # Setup authentication
        print("Setting up family authentication...")
        auth_result = self.setup_authentication()
        
        if auth_result.get("admin_password"):
            print(f"\n⚠️  IMPORTANT - Save this admin password: {auth_result['admin_password']}\n")
            
        # Start Ollama
        print("Starting Ollama AI engine...")
        if not self.start_ollama():
            print("❌ Failed to start Ollama")
            return False
            
        # Load models
        print("Loading AI models...")
        self.load_models()
        
        # Create parent dashboard
        print("Creating parent dashboard...")
        self.create_parent_dashboard()
        
        # Start Open WebUI
        print("Starting Open WebUI server...")
        if not self.start_open_webui():
            print("❌ Failed to start Open WebUI")
            return False
            
        print("\n✅ Sunflower AI is ready!")
        print(f"🌐 Open WebUI: http://localhost:8080")
        print(f"📊 Parent Dashboard: file://{self.data_dir}/parent_dashboard.html")
        print("\nPress Ctrl+C to stop the system")
        
        try:
            # Keep running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down Sunflower AI...")
            if hasattr(self, 'webui_process'):
                self.webui_process.terminate()
            subprocess.run(["pkill", "-f", "ollama"], capture_output=True)
            print("Goodbye! 👋")
            
        return True

if __name__ == "__main__":
    integrator = OpenWebUIIntegrator()
    integrator.run()

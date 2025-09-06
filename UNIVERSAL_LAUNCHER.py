#!/usr/bin/env python3
"""
Sunflower AI Universal Launcher
Main entry point that automatically detects OS and launches appropriate interface
Version: 6.2.0 - Production Ready
"""

import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
import webbrowser
import json
import time
import subprocess
import threading
import socket
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SunflowerLauncher')


class SunflowerLauncher:
    """Universal launcher with GUI for Sunflower AI system"""
    
    def __init__(self):
        self.system = platform.system()
        self.root_dir = Path(__file__).parent.resolve()
        self.data_dir = None
        self.setup_complete = False
        self.ollama_process = None
        self.webui_process = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("700x550")
        self.root.resizable(False, False)
        
        # Set icon if available
        icon_path = self.root_dir / "resources" / "sunflower.ico"
        if icon_path.exists():
            if self.system == "Windows":
                self.root.iconbitmap(str(icon_path))
            elif self.system == "Darwin":
                # macOS icon handling
                try:
                    img = tk.PhotoImage(file=str(icon_path.with_suffix('.png')))
                    self.root.iconphoto(True, img)
                except:
                    pass
        
        # Apply modern styling
        self.setup_styles()
        
        # Create UI
        self.create_ui()
        
        # Start initialization in background
        self.init_thread = threading.Thread(target=self.initialize_system, daemon=True)
        self.init_thread.start()
        
        # Bind cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Configure modern UI styling"""
        style = ttk.Style()
        
        # Configure colors
        self.colors = {
            'bg': '#f0f4f8',
            'primary': '#5e72e4',
            'success': '#2dce89',
            'warning': '#fb6340',
            'info': '#11cdef',
            'text': '#32325d',
            'text_light': '#8898aa',
            'border': '#dee2e6'
        }
        
        # Set background
        self.root.configure(bg=self.colors['bg'])
        
        # Configure ttk styles
        style.theme_use('clam')
        
        # Configure button style
        style.configure(
            'Primary.TButton',
            background=self.colors['primary'],
            foreground='white',
            borderwidth=0,
            focuscolor='none',
            padding=(20, 10)
        )
        style.map(
            'Primary.TButton',
            background=[('active', '#4c63d2')]
        )
        
        # Configure success button
        style.configure(
            'Success.TButton',
            background=self.colors['success'],
            foreground='white',
            borderwidth=0,
            focuscolor='none',
            padding=(20, 10)
        )
        style.map(
            'Success.TButton',
            background=[('active', '#26b877')]
        )
        
        # Configure progress bar
        style.configure(
            'Custom.Horizontal.TProgressbar',
            background=self.colors['primary'],
            troughcolor=self.colors['border'],
            borderwidth=0,
            lightcolor=self.colors['primary'],
            darkcolor=self.colors['primary']
        )
    
    def create_ui(self):
        """Create the user interface"""
        # Header frame
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=100)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Title with emoji
        title_label = tk.Label(
            header_frame,
            text="🌻 Sunflower AI Professional System",
            font=('Segoe UI', 20, 'bold'),
            bg=self.colors['primary'],
            fg='white'
        )
        title_label.pack(pady=25)
        
        # Subtitle
        subtitle_label = tk.Label(
            header_frame,
            text="Family-Focused K-12 STEM Education",
            font=('Segoe UI', 11),
            bg=self.colors['primary'],
            fg='white'
        )
        subtitle_label.pack()
        
        # Main content frame
        self.content_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Status frame
        self.status_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        self.status_frame.pack(fill=tk.X, pady=10)
        
        # Status label
        self.status_label = tk.Label(
            self.status_frame,
            text="Initializing system...",
            font=('Segoe UI', 11),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        self.status_label.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.status_frame,
            style='Custom.Horizontal.TProgressbar',
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        # Info frame (hidden initially)
        self.info_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        
        # Buttons frame (hidden initially)
        self.button_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        
        # Footer frame
        footer_frame = tk.Frame(self.root, bg=self.colors['border'], height=50)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        # Footer text
        footer_label = tk.Label(
            footer_frame,
            text=f"Version 6.2.0 | {self.system} | © 2025 Sunflower AI",
            font=('Segoe UI', 9),
            bg=self.colors['border'],
            fg=self.colors['text_light']
        )
        footer_label.pack(pady=15)
    
    def initialize_system(self):
        """Initialize the system in background"""
        try:
            # Step 1: Detect partitions
            self.update_status("Detecting device partitions...")
            self.detect_partitions()
            
            # Step 2: Check Python
            self.update_status("Checking Python installation...")
            if not self.check_python():
                self.show_error("Python 3.8+ required", "Please install Python from python.org")
                return
            
            # Step 3: Check/Install dependencies
            self.update_status("Checking dependencies...")
            self.check_dependencies()
            
            # Step 4: Check Ollama
            self.update_status("Checking Ollama installation...")
            if not self.check_ollama():
                self.update_status("Installing Ollama...")
                self.install_ollama()
            
            # Step 5: Check models
            self.update_status("Checking AI models...")
            self.check_models()
            
            # Step 6: Initialize configuration
            self.update_status("Loading configuration...")
            self.load_configuration()
            
            # Mark setup complete
            self.setup_complete = True
            
            # Show ready UI
            self.root.after(0, self.show_ready_ui)
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self.root.after(0, lambda: self.show_error("Initialization Failed", str(e)))
    
    def detect_partitions(self):
        """Detect CD-ROM and USB partitions"""
        if self.system == "Windows":
            import string
            
            # Find CD-ROM partition
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                if (drive_path / "sunflower_cd.id").exists():
                    self.cdrom_path = drive_path
                    logger.info(f"Found CD-ROM partition: {drive_path}")
                    break
            
            # Find USB partition
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:\\")
                if (drive_path / "sunflower_data.id").exists():
                    self.usb_path = drive_path
                    self.data_dir = drive_path / "sunflower_data"
                    logger.info(f"Found USB partition: {drive_path}")
                    break
                    
        elif self.system == "Darwin":  # macOS
            volumes = Path("/Volumes")
            
            # Find CD-ROM partition
            for volume in volumes.iterdir():
                if (volume / "sunflower_cd.id").exists():
                    self.cdrom_path = volume
                    logger.info(f"Found CD-ROM partition: {volume}")
                    break
            
            # Find USB partition
            for volume in volumes.iterdir():
                if (volume / "sunflower_data.id").exists():
                    self.usb_path = volume
                    self.data_dir = volume / "sunflower_data"
                    logger.info(f"Found USB partition: {volume}")
                    break
        
        # Fallback to local directory
        if not self.data_dir:
            self.data_dir = self.root_dir / "data"
            logger.warning("Using local data directory")
        
        # Create data directory structure
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "profiles").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "ollama" / "models").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "openwebui" / "data").mkdir(parents=True, exist_ok=True)
    
    def check_python(self) -> bool:
        """Check Python version"""
        version = sys.version_info
        return version.major >= 3 and version.minor >= 8
    
    def check_dependencies(self):
        """Check and install required Python packages"""
        required_packages = [
            'open-webui',
            'requests',
            'psutil',
            'cryptography'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                logger.info(f"Package {package} is installed")
            except ImportError:
                logger.info(f"Installing {package}...")
                self.update_status(f"Installing {package}...")
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', package, '--quiet'],
                    check=False,
                    capture_output=True
                )
    
    def check_ollama(self) -> bool:
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install_ollama(self):
        """Install Ollama based on platform"""
        if self.system == "Windows":
            # Download and install Ollama for Windows
            installer_url = "https://ollama.ai/download/OllamaSetup.exe"
            installer_path = Path.home() / "Downloads" / "OllamaSetup.exe"
            
            # Download installer
            import urllib.request
            urllib.request.urlretrieve(installer_url, installer_path)
            
            # Run installer
            subprocess.run([str(installer_path), '/S'], check=False)
            
        elif self.system == "Darwin":
            # Install Ollama for macOS
            subprocess.run(['brew', 'install', 'ollama'], check=False)
        
        elif self.system == "Linux":
            # Install Ollama for Linux
            subprocess.run(
                ['curl', '-fsSL', 'https://ollama.ai/install.sh', '|', 'sh'],
                shell=True,
                check=False
            )
    
    def check_models(self):
        """Check and pull required models"""
        try:
            # Start Ollama service
            self.start_ollama_service()
            time.sleep(3)  # Wait for service to start
            
            # Check for models
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if 'llama3.2:3b' not in result.stdout:
                self.update_status("Downloading AI model (this may take a while)...")
                subprocess.run(['ollama', 'pull', 'llama3.2:3b'], check=False)
                
        except Exception as e:
            logger.error(f"Model check failed: {e}")
    
    def start_ollama_service(self):
        """Start Ollama service in background"""
        if not self.ollama_process:
            self.ollama_process = subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("Ollama service started")
    
    def load_configuration(self):
        """Load system configuration"""
        config_file = self.data_dir / "config" / "system.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        else:
            # Create default configuration
            self.config = {
                'version': '6.2.0',
                'first_run': True,
                'theme': 'light',
                'safety_level': 'high',
                'default_model': 'llama3.2:3b',
                'webui_port': 8080,
                'ollama_port': 11434
            }
            
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
    
    def update_status(self, message: str):
        """Update status label in UI thread"""
        self.root.after(0, lambda: self.status_label.config(text=message))
    
    def show_ready_ui(self):
        """Show the ready UI with action buttons"""
        # Stop progress bar
        self.progress.stop()
        self.progress.pack_forget()
        
        # Update status
        self.status_label.config(
            text="✅ System Ready",
            fg=self.colors['success'],
            font=('Segoe UI', 12, 'bold')
        )
        
        # Show info
        self.info_frame.pack(fill=tk.X, pady=20)
        
        info_text = f"""
System Information:
• Platform: {self.system}
• Data Directory: {self.data_dir}
• Model: {self.config['default_model']}
• Safety Level: {self.config['safety_level'].upper()}
• Web UI Port: {self.config['webui_port']}
"""
        
        info_label = tk.Label(
            self.info_frame,
            text=info_text,
            font=('Segoe UI', 10),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            justify=tk.LEFT
        )
        info_label.pack()
        
        # Show buttons
        self.button_frame.pack(fill=tk.X, pady=20)
        
        # Launch button
        launch_btn = ttk.Button(
            self.button_frame,
            text="🚀 Launch Sunflower AI",
            style='Success.TButton',
            command=self.launch_application
        )
        launch_btn.pack(pady=5)
        
        # Settings button
        settings_btn = ttk.Button(
            self.button_frame,
            text="⚙️ Settings",
            style='Primary.TButton',
            command=self.open_settings
        )
        settings_btn.pack(pady=5)
        
        # Documentation button
        docs_btn = ttk.Button(
            self.button_frame,
            text="📚 Documentation",
            command=self.open_documentation
        )
        docs_btn.pack(pady=5)
    
    def launch_application(self):
        """Launch the main application"""
        self.update_status("Starting Open WebUI...")
        
        # Start Web UI in background
        def start_webui():
            try:
                # Set environment variables
                os.environ['DATA_DIR'] = str(self.data_dir)
                os.environ['OLLAMA_HOST'] = f"localhost:{self.config['ollama_port']}"
                os.environ['WEBUI_SECRET_KEY'] = 'sunflower-secret-key-2025'
                os.environ['WEBUI_AUTH'] = 'True'
                os.environ['DEFAULT_MODELS'] = self.config['default_model']
                
                # Start Open WebUI
                self.webui_process = subprocess.Popen(
                    [sys.executable, '-m', 'open_webui', 'serve', 
                     '--port', str(self.config['webui_port'])],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # Wait for startup
                time.sleep(5)
                
                # Check if port is open
                for _ in range(30):
                    if self.is_port_open('localhost', self.config['webui_port']):
                        # Open browser
                        self.root.after(0, lambda: webbrowser.open(
                            f"http://localhost:{self.config['webui_port']}"
                        ))
                        self.root.after(0, lambda: self.update_status("✅ Sunflower AI is running"))
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Failed to start Web UI: {e}")
                self.root.after(0, lambda: self.show_error("Launch Failed", str(e)))
        
        # Start in thread
        thread = threading.Thread(target=start_webui, daemon=True)
        thread.start()
    
    def is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    
    def open_settings(self):
        """Open settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x400")
        settings_window.configure(bg=self.colors['bg'])
        
        # Settings content
        settings_label = tk.Label(
            settings_window,
            text="⚙️ Settings",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        settings_label.pack(pady=20)
        
        # Add settings options here
        settings_text = """
Safety Level: [High ▼]
Default Model: [llama3.2:3b ▼]
Theme: [Light ▼]
Auto-Start: [✓]
        """
        
        settings_content = tk.Label(
            settings_window,
            text=settings_text,
            font=('Segoe UI', 11),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        settings_content.pack(pady=20)
        
        # Close button
        close_btn = ttk.Button(
            settings_window,
            text="Close",
            command=settings_window.destroy
        )
        close_btn.pack(pady=20)
    
    def open_documentation(self):
        """Open documentation"""
        docs_path = self.root_dir / "docs" / "index.html"
        if docs_path.exists():
            webbrowser.open(f"file://{docs_path}")
        else:
            webbrowser.open("https://sunflowerai.com/docs")
    
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        messagebox.showerror(title, message)
        self.status_label.config(
            text=f"❌ {title}",
            fg=self.colors['warning']
        )
        self.progress.stop()
        self.progress.pack_forget()
    
    def on_closing(self):
        """Handle window closing"""
        # Stop services
        if self.ollama_process:
            self.ollama_process.terminate()
            logger.info("Stopped Ollama service")
        
        if self.webui_process:
            self.webui_process.terminate()
            logger.info("Stopped Web UI")
        
        # Save configuration
        if hasattr(self, 'config') and self.data_dir:
            config_file = self.data_dir / "config" / "system.json"
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        
        # Destroy window
        self.root.destroy()
    
    def run(self):
        """Run the launcher"""
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Start main loop
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        # Create and run launcher
        launcher = SunflowerLauncher()
        launcher.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        
        # Show error dialog
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Sunflower AI Launch Error",
            f"Failed to start Sunflower AI:\n\n{e}\n\nPlease check the logs for details."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

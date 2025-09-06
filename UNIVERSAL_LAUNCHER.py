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
import threading
import socket
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Add config directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import standardized path configuration
from config.path_config import get_path_config, ensure_paths_available, get_usb_path, get_cdrom_path

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
        
        # Initialize path configuration
        self.path_config = get_path_config()
        
        # Verify partitions are available
        if not ensure_paths_available():
            self._show_partition_error()
            sys.exit(1)
        
        # Get partition paths
        self.cdrom_path = self.path_config.cdrom_path
        self.usb_path = self.path_config.usb_path
        self.data_dir = get_usb_path('profiles')
        
        # Ensure data directory exists
        if self.data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.setup_complete = False
        self.ollama_process = None
        self.webui_process = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("700x550")
        self.root.resizable(False, False)
        
        # Set icon if available
        icon_path = get_cdrom_path('resources') / "sunflower.ico"
        if icon_path and icon_path.exists():
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
    
    def _show_partition_error(self):
        """Show error dialog when partitions are not detected"""
        error_msg = (
            "Sunflower AI partitions not detected!\n\n"
            "Please ensure:\n"
            "1. The Sunflower USB device is properly connected\n"
            "2. Both partitions (CD-ROM and USB) are mounted\n"
            "3. You have the necessary permissions\n\n"
            f"Looking for:\n"
            f"- CD-ROM marker: {self.path_config.CDROM_MARKER_FILE}\n"
            f"- USB marker: {self.path_config.USB_MARKER_FILE}"
        )
        
        if self.system == "Windows":
            error_msg += "\n\nOn Windows, try running as Administrator."
        
        messagebox.showerror("Partition Detection Failed", error_msg)
    
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
        
        self.status_label = tk.Label(
            self.status_frame,
            text="🔄 Initializing system...",
            font=('Segoe UI', 11),
            bg=self.colors['bg'],
            fg=self.colors['text']
        )
        self.status_label.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.content_frame,
            style='Custom.Horizontal.TProgressbar',
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=20)
        self.progress.start(10)
        
        # Info frame (hidden initially)
        self.info_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        
        # Button frame (hidden initially)
        self.button_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        
        # Path info at bottom
        path_info_frame = tk.Frame(self.root, bg=self.colors['bg'])
        path_info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        path_label = tk.Label(
            path_info_frame,
            text=f"CD-ROM: {self.cdrom_path} | USB: {self.usb_path}",
            font=('Segoe UI', 9),
            bg=self.colors['bg'],
            fg=self.colors['text_light']
        )
        path_label.pack()
    
    def update_status(self, message: str, color: str = None):
        """Update status message"""
        self.status_label.config(text=message)
        if color:
            self.status_label.config(fg=self.colors.get(color, self.colors['text']))
    
    def initialize_system(self):
        """Initialize the Sunflower AI system"""
        try:
            # Step 1: Verify paths
            self.update_status("✅ Partitions detected")
            time.sleep(0.5)
            
            # Step 2: Check for Ollama
            self.update_status("🔍 Checking for Ollama...")
            ollama_path = self.find_ollama()
            
            if not ollama_path:
                self.update_status("⚠️ Ollama not found - downloading required", 'warning')
                self.setup_required = True
            else:
                self.update_status("✅ Ollama found")
            
            # Step 3: Check for models
            self.update_status("🔍 Checking AI models...")
            models_available = self.check_models()
            
            if not models_available:
                self.update_status("⚠️ Models need to be downloaded", 'warning')
                self.setup_required = True
            else:
                self.update_status("✅ Models available")
            
            # Step 4: Load configuration
            self.update_status("📋 Loading configuration...")
            self.config = self.load_config()
            self.update_status("✅ Configuration loaded")
            
            # Step 5: Check profiles
            self.update_status("👨‍👩‍👧‍👦 Checking family profiles...")
            profiles_exist = self.check_profiles()
            
            if not profiles_exist:
                self.update_status("ℹ️ No profiles found - setup required", 'info')
                self.first_run = True
            else:
                self.update_status("✅ Profiles found")
                self.first_run = False
            
            # Complete initialization
            self.setup_complete = True
            self.root.after(0, self.show_ready_ui)
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            self.update_status(f"❌ Error: {str(e)}", 'warning')
            self.root.after(0, lambda: messagebox.showerror("Initialization Error", str(e)))
    
    def find_ollama(self) -> Optional[Path]:
        """Find Ollama executable"""
        # Check CD-ROM partition
        ollama_dir = get_cdrom_path('ollama')
        
        if ollama_dir:
            if self.system == "Windows":
                ollama_exe = ollama_dir / "ollama.exe"
            else:
                ollama_exe = ollama_dir / "ollama"
            
            if ollama_exe.exists():
                return ollama_exe
        
        # Check system PATH
        ollama_cmd = "ollama.exe" if self.system == "Windows" else "ollama"
        
        try:
            result = subprocess.run(
                [ollama_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return Path(ollama_cmd)
        except:
            pass
        
        return None
    
    def check_models(self) -> bool:
        """Check if required models are available"""
        models_dir = get_cdrom_path('models')
        
        if models_dir and models_dir.exists():
            # Check for any .gguf files
            gguf_files = list(models_dir.glob("*.gguf"))
            return len(gguf_files) > 0
        
        return False
    
    def check_profiles(self) -> bool:
        """Check if family profiles exist"""
        profiles_dir = get_usb_path('profiles')
        
        if profiles_dir and profiles_dir.exists():
            # Check for family configuration
            family_config = profiles_dir / "family.json"
            return family_config.exists()
        
        return False
    
    def load_config(self) -> Dict:
        """Load system configuration"""
        config_path = get_usb_path('config') / "system_config.json"
        
        default_config = {
            'first_run': True,
            'safety_level': 'maximum',
            'ollama_port': 11434,
            'webui_port': 8080,
            'default_model': 'llama3.2:3b',
            'theme': 'light'
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save system configuration"""
        config_dir = get_usb_path('config')
        if config_dir:
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "system_config.json"
            
            try:
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
    
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
• CD-ROM Path: {self.cdrom_path}
• USB Path: {self.usb_path}
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
        self.update_status("Starting Sunflower AI...")
        
        # Launch the appropriate interface based on configuration
        launcher_script = get_cdrom_path('launchers') / 'launcher_common.py'
        
        if launcher_script and launcher_script.exists():
            try:
                subprocess.Popen(
                    [sys.executable, str(launcher_script),
                     '--cdrom-path', str(self.cdrom_path),
                     '--usb-path', str(self.usb_path)],
                    cwd=str(self.cdrom_path)
                )
                time.sleep(2)
                self.root.destroy()
            except Exception as e:
                messagebox.showerror("Launch Error", f"Failed to launch application: {e}")
        else:
            # Fallback to web interface
            webbrowser.open(f"http://localhost:{self.config['webui_port']}")
    
    def open_settings(self):
        """Open settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        
        # Add settings UI here
        label = tk.Label(
            settings_window,
            text="Settings coming soon!",
            font=('Segoe UI', 12)
        )
        label.pack(pady=50)
    
    def open_documentation(self):
        """Open documentation"""
        docs_path = get_cdrom_path('documentation') / 'user_manual.html'
        
        if docs_path and docs_path.exists():
            webbrowser.open(f"file://{docs_path}")
        else:
            messagebox.showinfo("Documentation", "Documentation will be available in the docs folder.")
    
    def on_closing(self):
        """Handle window closing"""
        if self.ollama_process:
            self.ollama_process.terminate()
        if self.webui_process:
            self.webui_process.terminate()
        
        self.save_config()
        self.root.destroy()
    
    def run(self):
        """Run the launcher"""
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        launcher = SunflowerLauncher()
        launcher.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        messagebox.showerror("Fatal Error", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()

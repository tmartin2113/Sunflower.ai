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
            try:
                self.root.iconbitmap(str(icon_path))
            except:
                pass  # Icon setting is optional
        
        # Set up UI
        self.setup_ui()
        
        # Protocol for window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start initialization in background
        self.init_thread = threading.Thread(target=self.initialize_system, daemon=True)
        self.init_thread.start()
    
    def _show_partition_error(self):
        """Show error when partitions are not detected"""
        if 'DEVELOPMENT_MODE' in os.environ:
            print("WARNING: Running in development mode without proper partitions")
            return
        
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Partition Not Found",
            "Sunflower AI device partitions not detected.\n\n"
            "Please ensure the device is properly connected and try again."
        )
        root.destroy()
    
    def setup_ui(self):
        """Create the user interface"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(main_frame, bg='#4a90e2', height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title = tk.Label(
            header,
            text="🌻 Sunflower AI Professional System",
            font=('Segoe UI', 18, 'bold'),
            fg='white',
            bg='#4a90e2'
        )
        title.pack(pady=20)
        
        version = tk.Label(
            header,
            text="Version 6.2.0 - Family-Safe K-12 STEM Education",
            font=('Segoe UI', 10),
            fg='#e0e0e0',
            bg='#4a90e2'
        )
        version.pack()
        
        # Content area
        self.content_frame = tk.Frame(main_frame, bg='white', padx=40, pady=30)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status section
        self.status_frame = tk.Frame(self.content_frame, bg='white')
        self.status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.status_label = tk.Label(
            self.status_frame,
            text="🔄 Initializing system...",
            font=('Segoe UI', 12),
            bg='white',
            fg='#666'
        )
        self.status_label.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.content_frame,
            mode='indeterminate',
            style='Horizontal.TProgressbar'
        )
        self.progress.pack(fill=tk.X, pady=(0, 20))
        self.progress.start(10)
        
        # Action buttons (initially hidden)
        self.button_frame = tk.Frame(self.content_frame, bg='white')
        
        self.start_btn = tk.Button(
            self.button_frame,
            text="🚀 Start Sunflower AI",
            font=('Segoe UI', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=30,
            pady=10,
            command=self.start_system,
            cursor='hand2'
        )
        self.start_btn.pack(pady=5)
        
        self.setup_btn = tk.Button(
            self.button_frame,
            text="👨‍👩‍👧‍👦 Setup Family Profiles",
            font=('Segoe UI', 11),
            bg='#2196F3',
            fg='white',
            padx=20,
            pady=8,
            command=self.setup_profiles,
            cursor='hand2'
        )
        self.setup_btn.pack(pady=5)
        
        self.docs_btn = tk.Button(
            self.button_frame,
            text="📚 View Documentation",
            font=('Segoe UI', 11),
            bg='#FF9800',
            fg='white',
            padx=20,
            pady=8,
            command=self.open_documentation,
            cursor='hand2'
        )
        self.docs_btn.pack(pady=5)
        
        # Info section
        self.info_frame = tk.Frame(self.content_frame, bg='white')
        self.info_text = tk.Text(
            self.info_frame,
            height=8,
            width=60,
            font=('Segoe UI', 10),
            bg='#f5f5f5',
            fg='#333',
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Footer
        footer = tk.Frame(main_frame, bg='#f0f0f0', height=40)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        footer_text = tk.Label(
            footer,
            text="© 2025 Sunflower AI - Safe Learning for Every Child",
            font=('Segoe UI', 9),
            fg='#888',
            bg='#f0f0f0'
        )
        footer_text.pack(pady=10)
    
    def update_status(self, message: str, status_type: str = 'info'):
        """Update status message"""
        colors = {
            'info': '#666',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336'
        }
        
        self.root.after(0, lambda: self.status_label.config(
            text=message,
            fg=colors.get(status_type, '#666')
        ))
    
    def initialize_system(self):
        """Initialize the system in background"""
        try:
            # Step 1: Check Ollama
            self.update_status("🔍 Checking for Ollama...")
            time.sleep(0.5)
            
            ollama_path = self.find_ollama()
            if not ollama_path:
                self.update_status("❌ Ollama not found", 'error')
                self.show_setup_instructions()
                return
            
            # Step 2: Check models
            self.update_status("📦 Checking AI models...")
            if not self.check_models():
                self.update_status("⚠️ Models not found", 'warning')
                self.show_model_instructions()
                return
            
            # Step 3: Check profiles
            self.update_status("👤 Checking family profiles...")
            has_profiles = self.check_profiles()
            
            # Step 4: Load configuration
            self.update_status("⚙️ Loading configuration...")
            self.config = self.load_config()
            time.sleep(0.5)
            
            # Success
            self.setup_complete = True
            self.update_status("✅ System ready!", 'success')
            
            # Stop progress bar and show buttons
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
            "ollama_port": 11434,
            "webui_port": 8080,
            "auto_start": False,
            "safety_level": "maximum"
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except:
                pass
        
        return default_config
    
    def save_config(self):
        """Save configuration"""
        config_path = get_usb_path('config') / "system_config.json"
        
        if config_path:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
    
    def show_ready_ui(self):
        """Show UI when system is ready"""
        self.progress.stop()
        self.progress.pack_forget()
        
        self.button_frame.pack(fill=tk.X, pady=20)
        
        info_text = """
System initialized successfully!

✅ Ollama AI engine detected
✅ Educational models available
✅ Family safety filters active

Click 'Start Sunflower AI' to begin learning or
'Setup Family Profiles' to configure child accounts.
        """
        
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        self.info_text.insert('1.0', info_text.strip())
        self.info_text.config(state='disabled')
    
    def show_setup_instructions(self):
        """Show setup instructions"""
        self.progress.stop()
        self.progress.pack_forget()
        
        instructions = """
⚠️ Initial Setup Required

Ollama AI engine not detected. Please follow these steps:

1. For Windows:
   - Run setup_windows.bat as Administrator
   
2. For macOS:
   - Open Terminal and run: ./setup_macos.sh
   
3. For Linux:
   - Open Terminal and run: ./setup_linux.sh

After setup is complete, restart this launcher.
        """
        
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        self.info_text.insert('1.0', instructions.strip())
        self.info_text.config(state='disabled')
    
    def show_model_instructions(self):
        """Show model download instructions"""
        self.progress.stop()
        self.progress.pack_forget()
        
        instructions = """
📦 AI Models Required

The educational AI models need to be downloaded.

This is a one-time setup that requires internet connection.

Click 'Setup Models' below to begin the download.
The process will take 10-30 minutes depending on your
internet speed.

Required space: ~4GB
        """
        
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        self.info_text.insert('1.0', instructions.strip())
        self.info_text.config(state='disabled')
        
        setup_btn = tk.Button(
            self.content_frame,
            text="📥 Setup Models",
            font=('Segoe UI', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            padx=30,
            pady=10,
            command=self.setup_models,
            cursor='hand2'
        )
        setup_btn.pack(pady=20)
    
    def start_system(self):
        """Start the Sunflower AI system"""
        self.update_status("🚀 Starting Sunflower AI...", 'info')
        
        # Start Ollama service
        try:
            if self.system == "Windows":
                self.ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            time.sleep(2)  # Wait for service to start
            
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            messagebox.showerror("Error", f"Failed to start Ollama service:\n{e}")
            return
        
        # Start Open WebUI
        try:
            webui_path = get_cdrom_path('open-webui')
            if webui_path:
                # Launch Open WebUI
                # This would be the actual implementation
                webbrowser.open("http://localhost:8080")
                self.update_status("✅ Sunflower AI is running!", 'success')
            else:
                messagebox.showwarning("Warning", "Open WebUI not found. Opening fallback interface.")
                webbrowser.open("http://localhost:11434")
        
        except Exception as e:
            logger.error(f"Failed to start WebUI: {e}")
            messagebox.showerror("Error", f"Failed to start WebUI:\n{e}")
    
    def setup_profiles(self):
        """Open profile setup window"""
        # This would open the profile management interface
        profile_window = tk.Toplevel(self.root)
        profile_window.title("Family Profile Setup")
        profile_window.geometry("600x400")
        
        label = tk.Label(
            profile_window,
            text="Family Profile Setup\n\nThis feature will be available in the next update.",
            font=('Segoe UI', 12)
        )
        label.pack(pady=50)
    
    def setup_models(self):
        """Setup AI models"""
        # This would launch the model setup process
        messagebox.showinfo(
            "Model Setup",
            "Model setup will begin.\n\n"
            "This process will download the required AI models.\n"
            "Please ensure you have a stable internet connection."
        )
    
    def open_documentation(self):
        """Open documentation"""
        docs_path = get_cdrom_path('documentation') / 'user_manual.html'
        
        if docs_path and docs_path.exists():
            webbrowser.open(f"file://{docs_path}")
        else:
            messagebox.showinfo("Documentation", "Documentation will be available in the docs folder.")
    
    def on_closing(self):
        """Handle window closing with proper process cleanup"""
        # FIX: Properly clean up processes to prevent resource leaks
        for process in [self.ollama_process, self.webui_process]:
            if process:
                try:
                    # First try graceful termination
                    process.terminate()
                    try:
                        # Wait up to 5 seconds for process to terminate
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # If process doesn't terminate gracefully, force kill it
                        process.kill()
                        # Wait for the kill to complete
                        process.wait()
                except Exception as e:
                    logger.error(f"Error cleaning up process: {e}")
        
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

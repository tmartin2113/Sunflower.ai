#!/usr/bin/env python3
"""
Sunflower AI Universal Launcher
Main entry point that automatically detects OS and launches appropriate interface
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

class SunflowerLauncher:
    """Universal launcher with GUI for Sunflower AI system"""
    
    def __init__(self):
        self.system = platform.system()
        self.root_dir = Path(__file__).parent.resolve()
        self.data_dir = None
        self.setup_complete = False
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Set icon if available
        icon_path = self.root_dir / "resources" / "sunflower.ico"
        if icon_path.exists():
            if self.system == "Windows":
                self.root.iconbitmap(str(icon_path))
        
        # Apply modern styling
        self.setup_styles()
        
        # Create UI
        self.create_ui()
        
        # Start initialization in background
        self.init_thread = threading.Thread(target=self.initialize_system, daemon=True)
        self.init_thread.start()
        
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
            'text_light': '#8898aa'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Configure ttk styles
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 24, 'bold'),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
        style.configure('Subtitle.TLabel',
                       font=('Segoe UI', 12),
                       foreground=self.colors['text_light'],
                       background=self.colors['bg'])
        
        style.configure('Status.TLabel',
                       font=('Segoe UI', 10),
                       foreground=self.colors['text'],
                       background=self.colors['bg'])
        
        style.configure('Primary.TButton',
                       font=('Segoe UI', 11, 'bold'))
        
    def create_ui(self):
        """Create the launcher UI"""
        # Header with logo
        header_frame = tk.Frame(self.root, bg=self.colors['bg'], height=120)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = ttk.Label(header_frame, 
                                text="🌻 Sunflower AI",
                                style='Title.TLabel')
        title_label.pack(pady=(10, 5))
        
        subtitle_label = ttk.Label(header_frame,
                                   text="Family-Focused K-12 STEM Education",
                                   style='Subtitle.TLabel')
        subtitle_label.pack()
        
        # Progress frame
        self.progress_frame = tk.Frame(self.root, bg=self.colors['bg'])
        self.progress_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)
        
        # Status label
        self.status_label = ttk.Label(self.progress_frame,
                                      text="Initializing system...",
                                      style='Status.TLabel')
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(self.progress_frame,
                                        mode='indeterminate',
                                        length=400)
        self.progress.pack(pady=(0, 20))
        self.progress.start(10)
        
        # Status details
        self.details_frame = tk.Frame(self.progress_frame, bg=self.colors['bg'])
        self.details_frame.pack(fill=tk.BOTH, expand=True)
        
        self.details_text = tk.Text(self.details_frame,
                                    height=10,
                                    width=60,
                                    font=('Consolas', 9),
                                    bg='white',
                                    fg=self.colors['text'],
                                    relief=tk.FLAT,
                                    borderwidth=1)
        self.details_text.pack(pady=(0, 20))
        
        # Button frame (hidden initially)
        self.button_frame = tk.Frame(self.root, bg=self.colors['bg'])
        
        self.launch_button = tk.Button(self.button_frame,
                                       text="Launch Sunflower AI",
                                       command=self.launch_system,
                                       font=('Segoe UI', 12, 'bold'),
                                       bg=self.colors['primary'],
                                       fg='white',
                                       padx=30,
                                       pady=10,
                                       relief=tk.FLAT,
                                       cursor='hand2')
        self.launch_button.pack(side=tk.LEFT, padx=5)
        
        self.docs_button = tk.Button(self.button_frame,
                                     text="View Documentation",
                                     command=self.open_docs,
                                     font=('Segoe UI', 11),
                                     bg=self.colors['info'],
                                     fg='white',
                                     padx=20,
                                     pady=10,
                                     relief=tk.FLAT,
                                     cursor='hand2')
        self.docs_button.pack(side=tk.LEFT, padx=5)
        
    def log_status(self, message, level="info"):
        """Add status message to details window"""
        self.details_text.insert(tk.END, f"[{level.upper()}] {message}\n")
        self.details_text.see(tk.END)
        self.root.update()
        
    def update_status(self, message):
        """Update main status label"""
        self.status_label.config(text=message)
        self.root.update()
        
    def initialize_system(self):
        """Initialize the Sunflower AI system"""
        try:
            # Detect partitions
            self.update_status("Detecting device partitions...")
            self.detect_partitions()
            
            # Check Python
            self.update_status("Checking Python installation...")
            if not self.check_python():
                self.show_error("Python 3.9+ is required. Please install from python.org")
                return
            
            # Check/Install Open WebUI
            self.update_status("Checking Open WebUI...")
            if not self.check_open_webui():
                self.update_status("Installing Open WebUI...")
                if not self.install_open_webui():
                    self.show_error("Failed to install Open WebUI")
                    return
            
            # Check Ollama
            self.update_status("Checking Ollama AI engine...")
            if not self.check_ollama():
                self.update_status("Installing Ollama...")
                if not self.install_ollama():
                    self.show_error("Failed to install Ollama")
                    return
            
            # Initialize data structure
            self.update_status("Setting up data directories...")
            self.setup_data_directories()
            
            # Check family profile
            self.update_status("Checking family profile...")
            self.check_family_profile()
            
            # Setup complete
            self.setup_complete = True
            self.progress.stop()
            self.progress.configure(mode='determinate', value=100)
            self.update_status("✅ System ready! Click 'Launch' to start.")
            self.log_status("Initialization complete", "success")
            
            # Show launch button
            self.button_frame.pack(pady=(0, 20))
            
        except Exception as e:
            self.show_error(f"Initialization failed: {str(e)}")
            
    def detect_partitions(self):
        """Detect CD-ROM and USB partitions"""
        # Check for CD-ROM partition
        cdrom_marker = "sunflower_cd.id"
        usb_marker = "sunflower_data.id"
        
        if self.system == "Windows":
            import string
            for drive in string.ascii_uppercase:
                drive_path = Path(f"{drive}:/")
                if drive_path.exists():
                    if (drive_path / cdrom_marker).exists():
                        self.log_status(f"Found CD-ROM partition: {drive}:", "success")
                    if (drive_path / usb_marker).exists():
                        self.data_dir = drive_path / "sunflower_data"
                        self.log_status(f"Found USB data partition: {drive}:", "success")
        else:
            # macOS/Linux
            for volume_path in ["/Volumes", "/media", "/mnt"]:
                if Path(volume_path).exists():
                    for volume in Path(volume_path).iterdir():
                        if (volume / cdrom_marker).exists():
                            self.log_status(f"Found CD-ROM: {volume}", "success")
                        if (volume / usb_marker).exists():
                            self.data_dir = volume / "sunflower_data"
                            self.log_status(f"Found USB data: {volume}", "success")
        
        # Use local directory if no USB found
        if not self.data_dir:
            self.data_dir = Path.home() / ".sunflower_ai" / "data"
            self.log_status("Using local data directory", "warning")
            
    def check_python(self):
        """Check Python installation"""
        try:
            result = subprocess.run([sys.executable, "--version"],
                                  capture_output=True, text=True)
            version = result.stdout.strip()
            self.log_status(f"Python detected: {version}", "success")
            return True
        except:
            return False
            
    def check_open_webui(self):
        """Check if Open WebUI is installed"""
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "show", "open-webui"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_status("Open WebUI is installed", "success")
                return True
        except:
            pass
        self.log_status("Open WebUI not found", "warning")
        return False
        
    def install_open_webui(self):
        """Install Open WebUI"""
        try:
            self.log_status("Installing Open WebUI (this may take a few minutes)...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", 
                                   "--upgrade", "open-webui"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_status("Open WebUI installed successfully", "success")
                return True
        except Exception as e:
            self.log_status(f"Installation error: {str(e)}", "error")
        return False
        
    def check_ollama(self):
        """Check if Ollama is installed"""
        try:
            # Try to find Ollama
            if self.system == "Windows":
                result = subprocess.run(["where", "ollama"],
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(["which", "ollama"],
                                      capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_status("Ollama is installed", "success")
                return True
        except:
            pass
        self.log_status("Ollama not found", "warning")
        return False
        
    def install_ollama(self):
        """Guide user to install Ollama"""
        self.log_status("Ollama needs to be installed", "warning")
        
        response = messagebox.askyesno(
            "Install Ollama",
            "Ollama AI engine needs to be installed.\n\n"
            "Would you like to open the Ollama download page?"
        )
        
        if response:
            webbrowser.open("https://ollama.com/download")
            messagebox.showinfo(
                "Installation",
                "Please install Ollama and then click OK to continue."
            )
            # Check again
            return self.check_ollama()
        
        return False
        
    def setup_data_directories(self):
        """Create required data directories"""
        directories = [
            self.data_dir / "openwebui" / "data",
            self.data_dir / "profiles",
            self.data_dir / "ollama" / "models",
            self.data_dir / "logs",
            self.data_dir / "sessions"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        self.log_status(f"Data directory: {self.data_dir}", "info")
        
    def check_family_profile(self):
        """Check if family profile exists"""
        profile_file = self.data_dir / "profiles" / "family.json"
        
        if not profile_file.exists():
            self.log_status("First time setup detected", "info")
            # Will be created when system launches
        else:
            self.log_status("Family profile found", "success")
            
    def launch_system(self):
        """Launch the Sunflower AI system"""
        if not self.setup_complete:
            messagebox.showwarning("Not Ready", 
                                  "System initialization is still in progress.")
            return
        
        self.log_status("Launching Sunflower AI...", "info")
        
        # Run the OS-specific launcher
        if self.system == "Windows":
            launcher = self.root_dir / "launchers" / "windows_launcher.bat"
            if not launcher.exists():
                # Use the Python integration manager instead
                launcher = self.root_dir / "openwebui_integration.py"
                subprocess.Popen([sys.executable, str(launcher)])
            else:
                subprocess.Popen([str(launcher)], shell=True)
        else:
            launcher = self.root_dir / "launchers" / "macos_launcher.sh"
            if not launcher.exists():
                # Use the Python integration manager instead
                launcher = self.root_dir / "openwebui_integration.py"
                subprocess.Popen([sys.executable, str(launcher)])
            else:
                subprocess.Popen(["bash", str(launcher)])
        
        # Open browser after delay
        time.sleep(5)
        webbrowser.open("http://localhost:8080")
        
        # Close launcher after delay
        self.root.after(3000, self.root.quit)
        
    def open_docs(self):
        """Open documentation"""
        docs_path = self.root_dir / "docs" / "user_manual.html"
        if docs_path.exists():
            webbrowser.open(f"file://{docs_path}")
        else:
            messagebox.showinfo("Documentation",
                              "Documentation can be found in the docs folder.")
            
    def show_error(self, message):
        """Show error message"""
        self.progress.stop()
        messagebox.showerror("Error", message)
        self.log_status(message, "error")
        
    def run(self):
        """Run the launcher"""
        self.root.mainloop()

if __name__ == "__main__":
    launcher = SunflowerLauncher()
    launcher.run()

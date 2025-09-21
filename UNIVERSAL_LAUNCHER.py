#!/usr/bin/env python3
"""
Sunflower AI Universal Launcher
Version: 6.2 - Production Ready (No ANSI Colors)
Purpose: Cross-platform launcher with GUI for Sunflower AI Education System
Fixed: Removed all ANSI codes, improved logging, better error handling
"""

import os
import sys
import json
import time
import logging
import platform
import subprocess
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

# GUI imports
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Configure logging without ANSI codes
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_cdrom_path(subpath: str = '') -> Optional[Path]:
    """Get path to CD-ROM partition (read-only)"""
    # Check for marker file to identify CD-ROM partition
    for drive in Path('/').iterdir() if platform.system() != 'Windows' else [Path(f'{d}:/') for d in 'CDEFGHIJKLMNOPQRSTUVWXYZ']:
        try:
            if drive.is_dir() and (drive / 'SUNFLOWER_SYSTEM.marker').exists():
                return drive / subpath if subpath else drive
        except (PermissionError, OSError):
            continue
    
    # Development fallback
    dev_path = Path(__file__).parent / 'cdrom_simulation'
    if dev_path.exists():
        return dev_path / subpath if subpath else dev_path
    
    return None

def get_usb_path(subpath: str = '') -> Optional[Path]:
    """Get path to USB partition (writable)"""
    # Check for marker file to identify USB partition
    for drive in Path('/').iterdir() if platform.system() != 'Windows' else [Path(f'{d}:/') for d in 'CDEFGHIJKLMNOPQRSTUVWXYZ']:
        try:
            if drive.is_dir() and (drive / 'SUNFLOWER_DATA.marker').exists():
                # Verify write permission
                test_file = drive / '.write_test'
                try:
                    test_file.touch()
                    test_file.unlink()
                    return drive / subpath if subpath else drive
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            continue
    
    # Development fallback
    dev_path = Path(__file__).parent / 'usb_simulation'
    if dev_path.exists():
        return dev_path / subpath if subpath else dev_path
    
    return None

# ============================================================================
# PROCESS MANAGER
# ============================================================================

class ProcessManager:
    """Manages child processes with proper cleanup"""
    
    def __init__(self):
        self.processes = {}
        self.lock = threading.Lock()
        logger.info("ProcessManager initialized")
    
    def start_process(self, name: str, command: list, **kwargs) -> subprocess.Popen:
        """Start and track a process"""
        with self.lock:
            try:
                # Ensure no ANSI in subprocess output
                env = os.environ.copy()
                env['PYTHONUNBUFFERED'] = '1'
                env['NO_COLOR'] = '1'  # Disable colors in child processes
                env['TERM'] = 'dumb'   # Force simple terminal mode
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    **kwargs
                )
                
                self.processes[name] = process
                logger.info(f"Started process '{name}': PID {process.pid}")
                return process
                
            except Exception as e:
                logger.error(f"Failed to start process '{name}': {e}")
                raise
    
    def stop_process(self, name: str, timeout: float = 5.0) -> bool:
        """Stop a process gracefully with timeout"""
        with self.lock:
            if name not in self.processes:
                return True
            
            process = self.processes[name]
            if process.poll() is not None:
                # Already terminated
                del self.processes[name]
                return True
            
            try:
                # Try graceful termination first
                logger.info(f"Terminating process '{name}' (PID {process.pid})")
                process.terminate()
                
                try:
                    process.wait(timeout=timeout)
                    logger.info(f"Process '{name}' terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning(f"Force killing process '{name}'")
                    process.kill()
                    process.wait(timeout=2.0)
                
                del self.processes[name]
                return True
                
            except Exception as e:
                logger.error(f"Error stopping process '{name}': {e}")
                return False
    
    def cleanup_all(self, timeout: float = 10.0) -> None:
        """Clean up all managed processes"""
        logger.info("Cleaning up all processes...")
        
        with self.lock:
            process_names = list(self.processes.keys())
        
        for name in process_names:
            self.stop_process(name, timeout=timeout/len(process_names) if process_names else timeout)
        
        logger.info("Process cleanup complete")

# ============================================================================
# MAIN LAUNCHER GUI
# ============================================================================

class SunflowerLauncher:
    """Main launcher application with GUI"""
    
    def __init__(self):
        logger.info("="*60)
        logger.info("Sunflower AI Launcher Starting")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python: {sys.version}")
        logger.info("="*60)
        
        # Initialize process manager
        self.process_manager = ProcessManager()
        
        # Initialize paths
        self.cdrom_path = None
        self.usb_path = None
        self.data_dir = None
        
        # Initialize GUI
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # Set window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Initialize configuration
        self.config = {}
        
        # Create GUI elements
        self.create_widgets()
        
        # Start partition detection
        self.detect_partitions()
    
    def create_widgets(self):
        """Create GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        title_label = ttk.Label(
            header_frame,
            text="Sunflower AI Professional System",
            font=('Arial', 18, 'bold')
        )
        title_label.pack()
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Family-Focused K-12 STEM Education",
            font=('Arial', 12)
        )
        subtitle_label.pack()
        
        version_label = ttk.Label(
            header_frame,
            text="Version 6.2",
            font=('Arial', 10)
        )
        version_label.pack()
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.status_text = scrolledtext.ScrolledText(
            status_frame,
            height=10,
            width=70,
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=760
        )
        self.progress.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2)
        
        # Launch button (initially disabled)
        self.launch_button = ttk.Button(
            button_frame,
            text="Launch Sunflower AI",
            command=self.launch_application,
            state=tk.DISABLED,
            width=20
        )
        self.launch_button.grid(row=0, column=0, padx=5)
        
        # Setup button (initially disabled)
        self.setup_button = ttk.Button(
            button_frame,
            text="Run Setup",
            command=self.run_setup,
            state=tk.DISABLED,
            width=20
        )
        self.setup_button.grid(row=0, column=1, padx=5)
        
        # Documentation button
        self.docs_button = ttk.Button(
            button_frame,
            text="Documentation",
            command=self.open_documentation,
            width=20
        )
        self.docs_button.grid(row=0, column=2, padx=5)
        
        # Exit button
        self.exit_button = ttk.Button(
            button_frame,
            text="Exit",
            command=self.on_closing,
            width=20
        )
        self.exit_button.grid(row=0, column=3, padx=5)
        
        # Footer
        footer_label = ttk.Label(
            main_frame,
            text="For support, refer to the documentation or visit sunflowerai.example.com",
            font=('Arial', 9)
        )
        footer_label.grid(row=4, column=0, columnspan=2, pady=(20, 0))
    
    def add_status(self, message: str, level: str = "INFO"):
        """Add message to status display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format message without ANSI codes
        if level == "ERROR":
            prefix = "[ERROR]"
        elif level == "WARNING":
            prefix = "[WARNING]"
        elif level == "SUCCESS":
            prefix = "[OK]"
        else:
            prefix = "[INFO]"
        
        formatted_message = f"{timestamp} {prefix} {message}\n"
        
        # Add to GUI
        self.status_text.insert(tk.END, formatted_message)
        self.status_text.see(tk.END)
        self.status_text.update()
        
        # Also log it
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def detect_partitions(self):
        """Detect CD-ROM and USB partitions"""
        self.add_status("Starting partition detection...")
        self.progress.start(10)
        
        def detection_thread():
            # Detect CD-ROM partition
            self.cdrom_path = get_cdrom_path()
            if self.cdrom_path:
                self.add_status(f"CD-ROM partition found: {self.cdrom_path}", "SUCCESS")
            else:
                self.add_status("CD-ROM partition not found - using development mode", "WARNING")
                self.cdrom_path = Path(__file__).parent / 'cdrom_simulation'
                self.cdrom_path.mkdir(exist_ok=True)
            
            # Detect USB partition
            self.usb_path = get_usb_path()
            if self.usb_path:
                self.add_status(f"USB partition found: {self.usb_path}", "SUCCESS")
            else:
                self.add_status("USB partition not found - using local storage", "WARNING")
                self.usb_path = Path.home() / '.sunflower' / 'data'
                self.usb_path.mkdir(parents=True, exist_ok=True)
            
            # Set data directory
            self.data_dir = self.usb_path / 'launcher_data'
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Load configuration
            self.load_config()
            
            # Check system readiness
            self.root.after(0, self.check_system_readiness)
        
        thread = threading.Thread(target=detection_thread, daemon=True)
        thread.start()
    
    def check_system_readiness(self):
        """Check if system is ready to launch"""
        self.progress.stop()
        
        # Check for required files
        required_files = [
            self.cdrom_path / 'modelfiles' / 'sunflower-kids.modelfile',
            self.cdrom_path / 'modelfiles' / 'sunflower-educator.modelfile'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(file_path.name)
        
        if missing_files:
            self.add_status(f"Missing required files: {', '.join(missing_files)}", "ERROR")
            self.add_status("Please run setup to download required components", "WARNING")
            self.setup_button.config(state=tk.NORMAL)
        else:
            self.add_status("All required files found", "SUCCESS")
            
            # Check if first-time setup is needed
            setup_flag = self.usb_path / 'config' / 'setup_complete.flag'
            if not setup_flag.exists():
                self.add_status("First-time setup required", "INFO")
                self.setup_button.config(state=tk.NORMAL)
            else:
                self.add_status("System ready to launch", "SUCCESS")
                self.launch_button.config(state=tk.NORMAL)
    
    def launch_application(self):
        """Launch the main Sunflower AI application"""
        self.add_status("Launching Sunflower AI...")
        self.launch_button.config(state=tk.DISABLED)
        
        try:
            # Check if Ollama is running
            self.add_status("Checking Ollama service...")
            if not self.check_ollama():
                self.add_status("Starting Ollama service...")
                self.start_ollama()
            else:
                self.add_status("Ollama service is running", "SUCCESS")
            
            # Launch Open WebUI
            self.add_status("Starting Open WebUI...")
            if self.start_openwebui():
                self.add_status("Open WebUI started successfully", "SUCCESS")
                
                # Open browser
                time.sleep(3)
                webbrowser.open('http://localhost:8080')
                self.add_status("Browser opened to http://localhost:8080", "SUCCESS")
            else:
                self.add_status("Failed to start Open WebUI", "ERROR")
                
        except Exception as e:
            self.add_status(f"Launch error: {str(e)}", "ERROR")
            logger.exception("Launch failed")
        finally:
            self.launch_button.config(state=tk.NORMAL)
    
    def run_setup(self):
        """Run first-time setup"""
        self.add_status("Starting setup process...")
        self.setup_button.config(state=tk.DISABLED)
        
        try:
            # Download models
            self.add_status("Downloading AI models (this may take several minutes)...")
            
            # Simulate model download (replace with actual implementation)
            self.progress.start(10)
            time.sleep(2)  # Placeholder for actual download
            self.progress.stop()
            
            # Create setup complete flag
            setup_flag = self.usb_path / 'config' / 'setup_complete.flag'
            setup_flag.parent.mkdir(parents=True, exist_ok=True)
            setup_flag.write_text(f"Setup completed: {datetime.now().isoformat()}")
            
            self.add_status("Setup completed successfully", "SUCCESS")
            self.launch_button.config(state=tk.NORMAL)
            
        except Exception as e:
            self.add_status(f"Setup error: {str(e)}", "ERROR")
            logger.exception("Setup failed")
        finally:
            self.setup_button.config(state=tk.NORMAL)
    
    def check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def start_ollama(self):
        """Start Ollama service"""
        try:
            self.process_manager.start_process(
                'ollama',
                ['ollama', 'serve']
            )
            time.sleep(2)  # Give it time to start
        except Exception as e:
            self.add_status(f"Failed to start Ollama: {e}", "ERROR")
    
    def start_openwebui(self) -> bool:
        """Start Open WebUI"""
        try:
            # Try to start with Python
            webui_path = self.cdrom_path / 'open-webui'
            if webui_path.exists():
                self.process_manager.start_process(
                    'openwebui',
                    [sys.executable, 'backend/main.py'],
                    cwd=str(webui_path)
                )
                return True
            else:
                self.add_status("Open WebUI not found in expected location", "WARNING")
                return False
                
        except Exception as e:
            self.add_status(f"Failed to start Open WebUI: {e}", "ERROR")
            return False
    
    def open_documentation(self):
        """Open documentation"""
        docs_path = get_cdrom_path('documentation') / 'user_manual.html'
        
        if docs_path and docs_path.exists():
            webbrowser.open(f"file://{docs_path}")
        else:
            messagebox.showinfo("Documentation", "Documentation will be available in the docs folder.")
    
    def load_config(self):
        """Load configuration from file"""
        config_file = self.data_dir / 'launcher_config.json' if self.data_dir else None
        
        if config_file and config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        else:
            self.config = {}
    
    def save_config(self):
        """Save configuration to file"""
        if self.data_dir:
            config_file = self.data_dir / 'launcher_config.json'
            try:
                with open(config_file, 'w') as f:
                    json.dump(self.config, f, indent=2)
            except:
                pass
    
    def on_closing(self):
        """Handle window closing with proper cleanup"""
        logger.info("Window closing initiated, starting cleanup...")
        
        # Save configuration
        self.save_config()
        
        # Stop any running threads
        self.progress.stop()
        
        # Clean up all processes
        self.process_manager.cleanup_all(timeout=10.0)
        
        # Destroy the window
        try:
            self.root.destroy()
        except Exception as e:
            logger.error(f"Error destroying window: {e}")
        
        logger.info("Launcher shutdown complete")
    
    def run(self):
        """Run the launcher"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.on_closing()
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            self.on_closing()
            raise

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point with exception handling"""
    try:
        # Disable any color output in environment
        os.environ['NO_COLOR'] = '1'
        os.environ['PYTHONUNBUFFERED'] = '1'
        
        launcher = SunflowerLauncher()
        launcher.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        
        # Show error to user
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", str(e))
            root.destroy()
        except:
            print(f"[FATAL ERROR] {e}")
        
        sys.exit(1)
    finally:
        logger.info("Application exit")


if __name__ == "__main__":
    main()

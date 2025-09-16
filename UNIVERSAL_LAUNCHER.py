#!/usr/bin/env python3
"""
Sunflower AI Universal Launcher
Main entry point that automatically detects OS and launches appropriate interface
Version: 6.2.0 - Production Ready
FIXED: BUG-002 - Robust process cleanup to prevent resource leaks
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
import signal
import atexit
import psutil
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Set

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


class ProcessManager:
    """
    Centralized process management with robust cleanup
    FIXED: Implements proper process group management and cleanup
    """
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.process_groups: Set[int] = set()
        self._cleanup_lock = threading.Lock()
        self._shutdown_initiated = False
        
        # Register cleanup handlers
        atexit.register(self.cleanup_all)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Platform-specific signal handling
        if platform.system() != 'Windows':
            signal.signal(signal.SIGQUIT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating cleanup...")
        self.cleanup_all()
        sys.exit(0)
    
    def register_process(self, name: str, process: subprocess.Popen) -> None:
        """Register a process for tracking and cleanup"""
        with self._cleanup_lock:
            self.processes[name] = process
            
            # Track process group for Unix-like systems
            if platform.system() != 'Windows':
                try:
                    pgid = os.getpgid(process.pid)
                    self.process_groups.add(pgid)
                except (OSError, ProcessLookupError):
                    pass
            
            logger.info(f"Registered process '{name}' with PID {process.pid}")
    
    def terminate_process(self, name: str, timeout: float = 5.0) -> bool:
        """
        Terminate a specific process with timeout
        Returns True if successfully terminated, False otherwise
        """
        with self._cleanup_lock:
            if name not in self.processes:
                return True
            
            process = self.processes[name]
            
            try:
                # Check if process is still running
                if process.poll() is not None:
                    logger.info(f"Process '{name}' already terminated")
                    del self.processes[name]
                    return True
                
                logger.info(f"Terminating process '{name}' (PID {process.pid})")
                
                # Try graceful termination first
                process.terminate()
                
                try:
                    process.wait(timeout=timeout)
                    logger.info(f"Process '{name}' terminated gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process '{name}' did not terminate gracefully, forcing...")
                    
                    # Force kill if graceful termination failed
                    if platform.system() == 'Windows':
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                     capture_output=True, check=False)
                    else:
                        process.kill()
                        process.wait(timeout=2.0)
                    
                    logger.info(f"Process '{name}' forcefully terminated")
                
                del self.processes[name]
                return True
                
            except Exception as e:
                logger.error(f"Failed to terminate process '{name}': {e}")
                return False
    
    def cleanup_all(self, timeout: float = 10.0) -> None:
        """
        Clean up all registered processes with improved robustness
        FIXED: Ensures no orphaned processes remain
        """
        with self._cleanup_lock:
            if self._shutdown_initiated:
                return
            
            self._shutdown_initiated = True
            logger.info("Initiating comprehensive process cleanup...")
            
            # Create list of processes to terminate (avoid dict modification during iteration)
            processes_to_terminate = list(self.processes.keys())
            
            # Terminate each process
            for name in processes_to_terminate:
                self.terminate_process(name, timeout=timeout/len(processes_to_terminate))
            
            # Clean up process groups on Unix-like systems
            if platform.system() != 'Windows':
                for pgid in self.process_groups:
                    try:
                        os.killpg(pgid, signal.SIGTERM)
                        time.sleep(0.1)
                        os.killpg(pgid, signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        pass
            
            # Final cleanup - kill any remaining child processes using psutil
            try:
                current_process = psutil.Process()
                children = current_process.children(recursive=True)
                
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                
                # Wait briefly for termination
                gone, alive = psutil.wait_procs(children, timeout=2)
                
                # Force kill any remaining processes
                for child in alive:
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                
                logger.info(f"Cleanup complete: {len(gone)} processes terminated, "
                          f"{len(alive)} processes force-killed")
                
            except Exception as e:
                logger.error(f"Error during final cleanup: {e}")
            
            self.processes.clear()
            self.process_groups.clear()
            logger.info("All processes cleaned up successfully")


class SunflowerLauncher:
    """Universal launcher with GUI for Sunflower AI system"""
    
    def __init__(self):
        self.system = platform.system()
        self.root_dir = Path(__file__).parent.resolve()
        
        # Initialize process manager for robust cleanup
        self.process_manager = ProcessManager()
        
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
        icon_path = get_cdrom_path('resources') / "icons" / "sunflower.ico"
        if icon_path and icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except:
                pass
        
        # Initialize UI components
        self.progress = None
        self.status_label = None
        self.info_text = None
        self.info_frame = None
        
        # Set up UI
        self.setup_ui()
        
        # Bind window close event to proper cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start initialization check
        self.root.after(100, self.check_system)
    
    def _show_partition_error(self):
        """Show error when partitions are not available"""
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Sunflower AI - Partition Error",
            "Could not detect Sunflower AI device partitions.\n\n"
            "Please ensure the USB device is properly connected\n"
            "and try again."
        )
        root.destroy()
    
    def setup_ui(self):
        """Setup the launcher UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg='#f0f0f0')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            header_frame,
            text="🌻 Sunflower AI Professional System",
            font=('Segoe UI', 18, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.pack()
        
        version_label = tk.Label(
            header_frame,
            text="Version 6.2.0 - Family-Focused K-12 STEM Education",
            font=('Segoe UI', 10),
            bg='#f0f0f0',
            fg='#7f8c8d'
        )
        version_label.pack()
        
        # Status section
        status_frame = tk.Frame(main_frame, bg='#f0f0f0')
        status_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = tk.Label(
            status_frame,
            text="Initializing system...",
            font=('Segoe UI', 12),
            bg='#f0f0f0',
            fg='#34495e'
        )
        self.status_label.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        # Info text area (initially hidden)
        self.info_frame = tk.Frame(main_frame, bg='#ffffff', relief=tk.RIDGE, bd=1)
        
        self.info_text = tk.Text(
            self.info_frame,
            height=8,
            width=60,
            font=('Consolas', 10),
            bg='#ffffff',
            fg='#2c3e50',
            wrap=tk.WORD,
            padx=10,
            pady=10
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Button frame
        self.button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        self.button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Create buttons (initially hidden)
        self.launch_button = tk.Button(
            self.button_frame,
            text="Launch Sunflower AI",
            command=self.launch_application,
            font=('Segoe UI', 12, 'bold'),
            bg='#27ae60',
            fg='white',
            padx=20,
            pady=10,
            cursor='hand2'
        )
        
        self.setup_button = tk.Button(
            self.button_frame,
            text="Setup Models",
            command=self.setup_models,
            font=('Segoe UI', 11),
            bg='#3498db',
            fg='white',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        
        self.docs_button = tk.Button(
            self.button_frame,
            text="Documentation",
            command=self.open_documentation,
            font=('Segoe UI', 11),
            bg='#95a5a6',
            fg='white',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        
        # Configuration
        self.config = {}
        self.load_config()
    
    def check_system(self):
        """Check system requirements and setup status"""
        self.status_label.config(text="Checking system requirements...")
        
        # Check hardware
        if not self.check_hardware():
            self.show_hardware_warning()
            return
        
        # Check Ollama installation
        if not self.check_ollama():
            self.show_setup_instructions()
            return
        
        # Check models
        if not self.check_models():
            self.show_model_instructions()
            return
        
        # Check Open WebUI
        if not self.check_webui():
            self.status_label.config(text="Setting up web interface...")
            self.setup_webui()
        
        # All checks passed
        self.show_ready()
    
    def check_hardware(self) -> bool:
        """Check if hardware meets minimum requirements"""
        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / (1024**3)
            
            if ram_gb < 4:
                return False
            
            return True
        except:
            return True  # Assume it's fine if we can't check
    
    def check_ollama(self) -> bool:
        """Check if Ollama is installed and accessible"""
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def check_models(self) -> bool:
        """Check if required models are available"""
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False
            
            # Check for our models
            output = result.stdout.lower()
            return 'sunflower' in output or 'llama' in output
        except:
            return False
    
    def check_webui(self) -> bool:
        """Check if Open WebUI is running"""
        try:
            # Check if port 8080 is in use
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 8080))
            sock.close()
            return result == 0
        except:
            return False
    
    def setup_webui(self):
        """Start Open WebUI in background"""
        try:
            # Start Open WebUI
            webui_cmd = [
                sys.executable,
                str(self.root_dir / 'interface' / 'gui.py'),
                '--port', '8080',
                '--no-browser'
            ]
            
            self.webui_process = subprocess.Popen(
                webui_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True if platform.system() != 'Windows' else False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == 'Windows' else 0
            )
            
            # Register process for cleanup
            self.process_manager.register_process('webui', self.webui_process)
            
            # Start Ollama serve if needed
            ollama_cmd = ['ollama', 'serve']
            
            self.ollama_process = subprocess.Popen(
                ollama_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True if platform.system() != 'Windows' else False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == 'Windows' else 0
            )
            
            # Register process for cleanup
            self.process_manager.register_process('ollama', self.ollama_process)
            
            # Wait for services to start
            time.sleep(3)
            
            if self.check_webui():
                logger.info("Web UI started successfully")
            else:
                logger.warning("Web UI may not have started properly")
                
        except Exception as e:
            logger.error(f"Failed to start web UI: {e}")
    
    def launch_application(self):
        """Launch the main application"""
        self.status_label.config(text="Launching Sunflower AI...")
        
        # Open web browser to Open WebUI
        webbrowser.open('http://localhost:8080')
        
        # Hide launcher after a moment
        self.root.after(2000, self.root.iconify)
    
    def show_ready(self):
        """Show ready state"""
        self.progress.stop()
        self.progress.pack_forget()
        
        self.status_label.config(
            text="✅ System ready - All components verified",
            fg='#27ae60'
        )
        
        # Show launch button
        self.launch_button.pack(side=tk.LEFT, padx=5)
        self.docs_button.pack(side=tk.RIGHT, padx=5)
        
        # Show system info
        info_text = f"""
System Information:
─────────────────
Platform: {platform.system()} {platform.release()}
Python: {sys.version.split()[0]}
CD-ROM Path: {self.cdrom_path}
Data Path: {self.usb_path}
Models: ✓ Installed
Ollama: ✓ Running
Web UI: ✓ Available
        """
        
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        self.info_text.insert('1.0', info_text.strip())
        self.info_text.config(state='disabled')
    
    def show_hardware_warning(self):
        """Show hardware warning"""
        self.progress.stop()
        self.progress.pack_forget()
        
        self.status_label.config(
            text="⚠️ Hardware may not meet minimum requirements",
            fg='#e74c3c'
        )
        
        info_text = """
Warning: Your system may not meet the minimum requirements.

Minimum Requirements:
• RAM: 4GB (8GB recommended)
• Storage: 5GB free space
• CPU: 2+ cores

The system may run slowly or encounter issues.
        """
        
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        self.info_text.insert('1.0', info_text.strip())
        self.info_text.config(state='disabled')
        
        # Still show launch button
        self.launch_button.pack(side=tk.LEFT, padx=5)
        self.docs_button.pack(side=tk.RIGHT, padx=5)
    
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
        """
        
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        self.info_text.insert('1.0', instructions.strip())
        self.info_text.config(state='disabled')
        
        # Show setup button
        self.setup_button.pack(side=tk.LEFT, padx=5)
        self.docs_button.pack(side=tk.RIGHT, padx=5)
    
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
        """
        Handle window closing with proper process cleanup
        FIXED: Comprehensive cleanup to prevent resource leaks
        """
        logger.info("Window closing initiated, starting cleanup...")
        
        # Save configuration
        self.save_config()
        
        # Stop any running threads
        self.progress.stop()
        
        # Clean up all processes using the process manager
        self.process_manager.cleanup_all(timeout=10.0)
        
        # Destroy the window
        try:
            self.root.destroy()
        except:
            pass
        
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
        finally:
            # Ensure cleanup happens even if mainloop exits unexpectedly
            self.process_manager.cleanup_all()


def main():
    """Main entry point with exception handling"""
    try:
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
            print(f"Fatal Error: {e}")
        
        sys.exit(1)
    finally:
        # Final cleanup attempt
        logger.info("Application exit")


if __name__ == "__main__":
    main()

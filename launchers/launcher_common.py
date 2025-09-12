"""
Sunflower AI Common Launcher Components
Version: 6.2
Cross-platform launcher utilities and UI
"""

import os
import sys
import json
import logging
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SystemRequirements:
    """System requirements for Sunflower AI"""
    min_ram_gb: int = 4
    min_python_version: str = "3.11"
    min_disk_space_gb: int = 10
    supported_platforms: list = None
    
    def __post_init__(self):
        if self.supported_platforms is None:
            self.supported_platforms = ["Windows", "Darwin", "Linux"]


class PartitionDetector:
    """Detect and validate Sunflower AI partitions"""
    
    def __init__(self):
        self.platform = platform.system()
        self.cdrom_marker = "sunflower_cd.id"
        self.usb_marker = "sunflower_data.id"
        
    def detect_partitions(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect both CD-ROM and USB partitions"""
        logger.info(f"Detecting partitions on {self.platform}")
        
        if self.platform == "Windows":
            return self._detect_windows()
        elif self.platform == "Darwin":
            return self._detect_macos()
        else:
            return self._detect_linux()
    
    def _detect_windows(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect partitions on Windows"""
        cdrom_path = None
        usb_path = None
        
        # Check all drive letters
        for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{drive_letter}:\\"
            
            if not os.path.exists(drive):
                continue
            
            # Check for CD-ROM partition marker
            cd_marker = Path(drive) / self.cdrom_marker
            if cd_marker.exists():
                cdrom_path = Path(drive)
                logger.info(f"Found CD-ROM partition: {cdrom_path}")
            
            # Check for USB data partition marker
            data_marker = Path(drive) / self.usb_marker
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
                cd_marker = volume / self.cdrom_marker
                data_marker = volume / self.usb_marker
                
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
                    cd_marker = mount / self.cdrom_marker
                    data_marker = mount / self.usb_marker
                    
                    if cd_marker.exists():
                        cdrom_path = mount
                        logger.info(f"Found CD-ROM partition: {cdrom_path}")
                    
                    if data_marker.exists():
                        usb_path = mount
                        logger.info(f"Found USB partition: {usb_path}")
        
        return cdrom_path, usb_path


class HardwareDetector:
    """Detect hardware capabilities"""
    
    def __init__(self):
        self.platform = platform.system()
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get system hardware information"""
        import psutil
        
        info = {
            'platform': self.platform,
            'processor': platform.processor(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'ram_gb': psutil.virtual_memory().total / (1024**3),
            'cpu_count': psutil.cpu_count(),
            'disk_usage': {}
        }
        
        # Get disk usage for all partitions
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info['disk_usage'][partition.mountpoint] = {
                    'total_gb': usage.total / (1024**3),
                    'free_gb': usage.free / (1024**3)
                }
            except:
                pass
        
        return info
    
    def determine_hardware_tier(self) -> str:
        """Determine hardware performance tier"""
        import psutil
        
        ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = psutil.cpu_count()
        
        if ram_gb >= 16 and cpu_count >= 8:
            return "high"
        elif ram_gb >= 8 and cpu_count >= 4:
            return "medium"
        elif ram_gb >= 4:
            return "low"
        else:
            return "minimum"


class SunflowerLauncherUI:
    """Main launcher UI for Sunflower AI"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        self.hardware = HardwareDetector()
        self.requirements = SystemRequirements()
        
        # Setup main window
        self.root = tk.Tk()
        self.root.title("Sunflower AI Professional System")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # Center window
        self._center_window()
        
        # Setup UI
        self._setup_ui()
        
    def _center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Header
        header_frame = tk.Frame(self.root, bg="#2C3E50", height=100)
        header_frame.pack(fill=tk.X)
        
        title_label = tk.Label(
            header_frame,
            text="Sunflower AI Professional System",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="#2C3E50"
        )
        title_label.pack(pady=20)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Family-Safe K-12 STEM Education",
            font=("Arial", 14),
            fg="#ECF0F1",
            bg="#2C3E50"
        )
        subtitle_label.pack()
        
        # Main content
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # System status
        self._create_status_section(content_frame)
        
        # Progress section
        self._create_progress_section(content_frame)
        
        # Action buttons
        self._create_action_buttons(content_frame)
    
    def _create_status_section(self, parent):
        """Create system status display"""
        status_frame = tk.LabelFrame(parent, text="System Status", padx=10, pady=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Get system info
        sys_info = self.hardware.get_system_info()
        tier = self.hardware.determine_hardware_tier()
        
        status_items = [
            ("Platform", sys_info['platform']),
            ("Python Version", sys_info['python_version']),
            ("System RAM", f"{sys_info['ram_gb']:.1f} GB"),
            ("CPU Cores", sys_info['cpu_count']),
            ("Hardware Tier", tier.capitalize()),
            ("CD-ROM Path", str(self.cdrom_path)),
            ("Data Path", str(self.usb_path))
        ]
        
        for i, (label, value) in enumerate(status_items):
            tk.Label(status_frame, text=f"{label}:", anchor="w", width=15).grid(row=i, column=0, sticky="w")
            tk.Label(status_frame, text=value, anchor="w").grid(row=i, column=1, sticky="w")
    
    def _create_progress_section(self, parent):
        """Create progress display"""
        self.progress_frame = tk.LabelFrame(parent, text="Setup Progress", padx=10, pady=10)
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = tk.Label(self.progress_frame, text="Ready to begin setup...")
        self.progress_label.pack(anchor="w")
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=10)
    
    def _create_action_buttons(self, parent):
        """Create action buttons"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        self.start_button = tk.Button(
            button_frame,
            text="Start Setup",
            command=self.start_setup,
            bg="#27AE60",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.exit_button = tk.Button(
            button_frame,
            text="Exit",
            command=self.exit_launcher,
            bg="#E74C3C",
            fg="white",
            font=("Arial", 12),
            padx=20,
            pady=10
        )
        self.exit_button.pack(side=tk.RIGHT)
    
    def start_setup(self):
        """Start the setup process"""
        self.start_button.config(state=tk.DISABLED)
        
        # Run setup in background thread
        setup_thread = threading.Thread(target=self._run_setup)
        setup_thread.daemon = True
        setup_thread.start()
    
    def _run_setup(self):
        """Run the actual setup process"""
        steps = [
            ("Verifying system requirements", self._verify_requirements),
            ("Checking partition integrity", self._check_partitions),
            ("Setting up Python environment", self._setup_python),
            ("Installing Ollama", self._install_ollama),
            ("Loading AI models", self._load_models),
            ("Configuring Open WebUI", self._configure_webui),
            ("Creating initial profiles", self._create_profiles)
        ]
        
        total_steps = len(steps)
        
        for i, (description, func) in enumerate(steps):
            # Update UI
            self.progress_label.config(text=f"{description}...")
            self.progress_bar['value'] = (i / total_steps) * 100
            self.root.update()
            
            try:
                func()
                logger.info(f"Completed: {description}")
            except Exception as e:
                logger.error(f"Failed: {description} - {e}")
                messagebox.showerror("Setup Error", f"Failed during: {description}\n\nError: {e}")
                self.start_button.config(state=tk.NORMAL)
                return
        
        # Setup complete
        self.progress_label.config(text="Setup complete!")
        self.progress_bar['value'] = 100
        self.root.update()
        
        messagebox.showinfo("Success", "Sunflower AI setup completed successfully!")
        
        # Launch main application
        self._launch_application()
    
    def _verify_requirements(self):
        """Verify system requirements"""
        import psutil
        
        # Check RAM
        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < self.requirements.min_ram_gb:
            raise Exception(f"Insufficient RAM: {ram_gb:.1f}GB < {self.requirements.min_ram_gb}GB required")
        
        # Check Python version
        python_version = platform.python_version()
        if python_version < self.requirements.min_python_version:
            raise Exception(f"Python {python_version} < {self.requirements.min_python_version} required")
        
        # Check disk space
        usage = psutil.disk_usage(str(self.usb_path))
        free_gb = usage.free / (1024**3)
        if free_gb < self.requirements.min_disk_space_gb:
            raise Exception(f"Insufficient disk space: {free_gb:.1f}GB < {self.requirements.min_disk_space_gb}GB required")
    
    def _check_partitions(self):
        """Check partition integrity"""
        # Verify CD-ROM partition
        required_cdrom_files = [
            self.cdrom_path / "system",
            self.cdrom_path / "models",
            self.cdrom_path / "modelfiles"
        ]
        
        for path in required_cdrom_files:
            if not path.exists():
                raise Exception(f"Missing required path on CD-ROM: {path}")
        
        # Verify USB partition is writable
        test_file = self.usb_path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except:
            raise Exception("USB partition is not writable")
    
    def _setup_python(self):
        """Setup Python environment"""
        # This would normally set up virtual environment
        # For now, just verify Python works
        result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception("Python verification failed")
    
    def _install_ollama(self):
        """Install Ollama if needed"""
        # Check if Ollama is available
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            logger.info("Ollama already installed")
        except:
            logger.info("Installing Ollama...")
            # Installation would happen here
            pass
    
    def _load_models(self):
        """Load AI models"""
        # Determine which model to load based on hardware
        tier = self.hardware.determine_hardware_tier()
        
        model_map = {
            'high': 'sunflower-kids-7b',
            'medium': 'sunflower-kids-3b',
            'low': 'sunflower-kids-1b',
            'minimum': 'sunflower-kids-1b'
        }
        
        model = model_map[tier]
        logger.info(f"Loading model: {model}")
        
        # Model loading would happen here
    
    def _configure_webui(self):
        """Configure Open WebUI"""
        # Create configuration directory
        config_dir = self.usb_path / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Write configuration
        config = {
            'host': 'localhost',
            'port': 8080,
            'data_path': str(self.usb_path / "data")
        }
        
        config_file = config_dir / "webui.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _create_profiles(self):
        """Create initial profile structure"""
        profiles_dir = self.usb_path / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        
        # Create default directories
        (profiles_dir / "family").mkdir(exist_ok=True)
        (profiles_dir / "sessions").mkdir(exist_ok=True)
        (profiles_dir / "logs").mkdir(exist_ok=True)
    
    def _launch_application(self):
        """Launch the main Sunflower AI application"""
        main_script = self.cdrom_path / "system" / "main.py"
        
        if main_script.exists():
            subprocess.Popen([
                sys.executable,
                str(main_script),
                "--cdrom-path", str(self.cdrom_path),
                "--usb-path", str(self.usb_path)
            ])
            
            # Close launcher
            self.root.after(2000, self.root.quit)
        else:
            messagebox.showerror("Launch Error", "Could not find main application")
    
    def exit_launcher(self):
        """Exit the launcher"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.root.quit()
    
    def run(self):
        """Run the launcher UI"""
        self.root.mainloop()


def main():
    """Main entry point for launcher"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Sunflower AI Launcher")
    parser.add_argument("--cdrom-path", type=Path, help="CD-ROM partition path")
    parser.add_argument("--usb-path", type=Path, help="USB partition path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Detect partitions if not provided
    cdrom_path = args.cdrom_path
    usb_path = args.usb_path
    
    if not cdrom_path or not usb_path:
        detector = PartitionDetector()
        detected_cdrom, detected_usb = detector.detect_partitions()
        
        # Use detected paths if not provided
        if not cdrom_path:
            cdrom_path = detected_cdrom
        if not usb_path:
            usb_path = detected_usb
        
        # If still not found, try manual fallback paths
        if not cdrom_path or not usb_path:
            if platform.system() == "Windows":
                if not cdrom_path:
                    cdrom_path = Path("D:\\")
                if not usb_path:
                    usb_path = Path("E:\\")
            elif platform.system() == "Darwin":
                if not cdrom_path:
                    cdrom_path = Path("/Volumes/SUNFLOWER_CD")
                if not usb_path:
                    usb_path = Path("/Volumes/SUNFLOWER_DATA")
            else:
                if not cdrom_path:
                    cdrom_path = Path("/media/SUNFLOWER_CD")
                if not usb_path:
                    usb_path = Path("/media/SUNFLOWER_DATA")
    
    # FIX: Validate paths are not None and exist before checking .exists()
    # Check if paths are None first, then check existence
    if cdrom_path is None or usb_path is None:
        messagebox.showerror(
            "Partition Detection Failed",
            "Could not detect Sunflower AI partitions.\n\n"
            "Please ensure the device is properly connected and try again."
        )
        sys.exit(1)
    
    # Now safe to check .exists() since we know paths are not None
    if not cdrom_path.exists() or not usb_path.exists():
        missing_parts = []
        if not cdrom_path.exists():
            missing_parts.append(f"CD-ROM: {cdrom_path}")
        if not usb_path.exists():
            missing_parts.append(f"USB: {usb_path}")
        
        messagebox.showerror(
            "Partition Not Found",
            f"Could not find required partitions:\n\n" +
            "\n".join(missing_parts) +
            "\n\nPlease ensure the device is properly connected and try again."
        )
        sys.exit(1)
    
    # Launch UI with valid paths
    launcher = SunflowerLauncherUI(cdrom_path, usb_path)
    launcher.run()


if __name__ == "__main__":
    main()

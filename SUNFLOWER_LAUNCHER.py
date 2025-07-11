#!/usr/bin/env python3
"""
Sunflower AI Universal Launcher
Central application controller that manages GUI, models, and user interactions
"""

import sys
import os
import platform
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from constants import APP_NAME, WINDOW_TITLE
from core.ollama_manager import OllamaManager
from core.model_manager import ModelManager
from core.safety_filter import SafetyFilter
from gui.main_window import MainWindow
from gui.login_dialog import LoginDialog
from profiles.profile_manager import ProfileManager
from platform.partition_detector import PartitionDetector
from security.usb_validator import USBValidator
from utils.logger import setup_logging
from core.app_controller import AppController


class InitializationThread(QThread):
    """Background thread for initialization tasks"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
    
    def run(self):
        try:
            # Validate USB if running from USB
            if self.app.config.is_usb_mode:
                self.progress.emit("Validating USB...")
                if not self.app.usb_validator.validate():
                    self.finished.emit(False, "Invalid USB drive. Please use original Sunflower AI USB.")
                    return
            
            # Start Ollama
            self.progress.emit("Starting AI engine...")
            if not self.app.ollama_manager.start():
                self.finished.emit(False, "Failed to start AI engine. Please check installation.")
                return
            
            # Load models
            self.progress.emit("Loading AI models...")
            if not self.app.model_manager.initialize():
                self.finished.emit(False, "Failed to load AI models. Please check model files.")
                return
            
            # Initialize safety filter
            self.progress.emit("Initializing safety systems...")
            self.app.safety_filter.initialize()
            
            self.finished.emit(True, "Initialization complete")
            
        except Exception as e:
            self.finished.emit(False, f"Initialization failed: {str(e)}")


class SunflowerApp:
    """Main application controller"""
    
    def __init__(self):
        self.platform = platform.system()
        self.root_dir = Path(__file__).parent
        
        # Version info
        try:
            with open(self.root_dir / "VERSION", "r") as f:
                self.version = f.read().strip()
        except FileNotFoundError:
            self.version = "DEV"

        os.environ['SUNFLOWER_VERSION'] = self.version
        os.environ['SUNFLOWER_ENV'] = self.detect_environment()
        os.environ['SUNFLOWER_PLATFORM'] = self.platform

        self.app = QApplication(sys.argv)
        self.app.setApplicationName(APP_NAME)
        self.app.setOrganizationName("Sunflower AI")

        self.logger = setup_logging()
        self.logger.info(f"Starting {APP_NAME} v{self.version}")
        
        # Core components
        self.config = Config()
        self.partition_detector = PartitionDetector()
        self.usb_validator = USBValidator(self.root_dir)
        self.profile_manager = ProfileManager(self.config.get_app_dir())
        self.ollama_manager = OllamaManager(self.config)
        self.model_manager = ModelManager(self.config, self.ollama_manager)
        self.safety_filter = SafetyFilter(self.config)
        self.app_controller = AppController(self.config, self.profile_manager, self.model_manager)
        
        # GUI components
        self.main_window = None
        self.current_profile = None

    def detect_environment(self):
        """Detect if running from development or production environment"""
        if getattr(sys, 'frozen', False):
            return 'production'
        
        security_marker = self.root_dir / ".security" / "fingerprint.sig"
        if security_marker.exists():
            return 'usb'
        
        return 'development'

    def check_system_requirements(self):
        """Verify system meets minimum requirements"""
        import psutil
        
        requirements = {
            'ram_gb': 4,
            'python_version': (3, 8),
            'disk_space_gb': 2
        }
        
        # Check RAM
        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < requirements['ram_gb']:
            return False, f"Insufficient RAM: {ram_gb:.1f}GB found, {requirements['ram_gb']}GB required"
        
        # Check Python version (development only)
        if self.detect_environment() == 'development':
            if sys.version_info < requirements['python_version']:
                return False, f"Python {requirements['python_version'][0]}.{requirements['python_version'][1]}+ required"
        
        # Check available disk space
        if self.platform == "Windows":
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(str(self.root_dir)),
                ctypes.pointer(free_bytes),
                None,
                None
            )
            free_gb = free_bytes.value / (1024**3)
        else:
            stat = os.statvfs(self.root_dir)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        if free_gb < requirements['disk_space_gb']:
            return False, f"Insufficient disk space: {free_gb:.1f}GB free, {requirements['disk_space_gb']}GB required"
        
        return True, "System requirements met"

    def run(self):
        """Main application entry point"""
        # Check system requirements before full GUI load
        meets_req, message = self.check_system_requirements()
        if not meets_req:
            QMessageBox.critical(None, "System Requirements Not Met", message)
            return 1
        
        # Set application style
        self.app.setStyle('Fusion')
        
        # Show login dialog
        if not self.show_login():
            return 0
        
        # Initialize in background
        self.show_initialization_dialog()
        
        # Start main event loop
        return self.app.exec()
    
    def show_login(self):
        """Show login dialog and handle authentication"""
        login_dialog = LoginDialog(self.profile_manager)
        
        if login_dialog.exec() == LoginDialog.DialogCode.Accepted:
            profile_type, profile_data = login_dialog.get_selected_profile()
            
            if profile_type == 'parent':
                # Parent login - full access
                self.current_profile = profile_data
                return True
            else:
                # Child login - restricted access
                self.current_profile = profile_data
                return True
        
        return False
    
    def show_initialization_dialog(self):
        """Show initialization progress dialog"""
        progress = QProgressDialog("Initializing Sunflower AI...", "Cancel", 0, 0, self.main_window)
        progress.setWindowTitle(WINDOW_TITLE)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        # Run initialization in background
        self.init_thread = InitializationThread(self)
        self.init_thread.progress.connect(progress.setLabelText)
        self.init_thread.finished.connect(
            lambda success, message: self.on_initialization_complete(success, message, progress)
        )
        self.init_thread.start()
    
    def on_initialization_complete(self, success, message, progress_dialog):
        """Handle initialization completion"""
        progress_dialog.close()
        
        if not success:
            QMessageBox.critical(None, "Initialization Failed", message)
            self.app.quit()
            return
        
        # Create and show main window
        self.main_window = MainWindow(
            self.config,
            self.current_profile,
            self.model_manager,
            self.safety_filter,
            self.profile_manager,
            self.app_controller
        )
        self.main_window.show()
    
    def cleanup(self):
        """Cleanup resources on exit"""
        self.logger.info("Shutting down Sunflower AI")

        if self.app_controller:
            self.app_controller.shutdown()
        
        # Save any pending data
        if self.profile_manager:
            self.profile_manager.save_profiles()
        
        # Stop Ollama
        if self.ollama_manager:
            self.ollama_manager.stop()
        
        self.logger.info("Shutdown complete")


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    app = SunflowerApp()
    sys.exit(app.run()) 
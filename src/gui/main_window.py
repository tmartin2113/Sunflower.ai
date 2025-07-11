"""
Main application window for Sunflower AI
Adaptive interface for both children and parents
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QStatusBar, QToolBar, QSplitter,
    QLabel, QPushButton, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, pyqtSlot, QThread,
    QPropertyAnimation, QEasingCurve, QSize
)
from PyQt6.QtGui import (
    QAction, QIcon, QPixmap, QFont, QPalette, QColor,
    QKeySequence, QCloseEvent
)

from ..constants import (
    APP_NAME, VERSION, WINDOW_TITLE, 
    SESSION_TIMEOUT_MINUTES, AUTO_SAVE_INTERVAL_SECONDS
)
from ..profiles.profile_manager import ProfileManager
from ..profiles.session_logger import SessionLogger
from ..core.model_manager import ModelManager
from ..core.conversation import ConversationManager
from ..core.safety_filter import SafetyFilter

from .widgets.chat_widget import ChatWidget
from .widgets.profile_switcher import ProfileSwitcher
from .parent_dashboard import ParentDashboard
from .profile_manager_dialog import ProfileManagerDialog
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Main application window with adaptive interface"""
    
    # Signals to the controller
    profile_selected = pyqtSignal(dict)
    prompt_submitted = pyqtSignal(str)

    def __init__(self, config, profile, model_manager, safety_filter, profile_manager, app_controller, parent=None):
        super().__init__(parent)
        
        self.config = config
        self.profile_manager = profile_manager
        self.model_manager = model_manager
        self.app_controller = app_controller
        self.current_profile = profile
        self.is_parent_mode = (profile['type'] == 'parent')
        
        # Setup UI
        self.setup_ui()
        self.apply_theme()
        self.set_profile(self.current_profile)

        # Connect signals/slots with controller
        self.connect_to_controller()
        
    def setup_ui(self):
        """Create the main window interface"""
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(900, 700)
        self.resize(1200, 800)
        
        # Set window icon
        icon_path = self.config.resources_path / "icons" / "sunflower.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create components
        self.create_menu_bar()
        self.create_toolbar()
        
        # Content area with profile switcher and chat
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Profile switcher
        self.profile_switcher = ProfileSwitcher(self.profile_manager)
        self.profile_switcher.profile_changed.connect(self.switch_profile)
        content_layout.addWidget(self.profile_switcher)
        
        # Chat widget
        self.chat_widget = ChatWidget(self.config)
        self.chat_widget.message_sent.connect(self.prompt_submitted)
        content_layout.addWidget(self.chat_widget)
        
        main_layout.addWidget(content_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()
        
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_conversation = QAction("&New Conversation", self)
        new_conversation.setShortcut(QKeySequence.StandardKey.New)
        new_conversation.triggered.connect(self.new_conversation)
        file_menu.addAction(new_conversation)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Profile menu
        profile_menu = menubar.addMenu("&Profile")
        
        switch_profile = QAction("&Switch Profile", self)
        switch_profile.setShortcut("Ctrl+P")
        switch_profile.triggered.connect(self.show_profile_switcher)
        profile_menu.addAction(switch_profile)
        
        # Parent-only menu items
        self.manage_profiles_action = QAction("&Manage Profiles", self)
        self.manage_profiles_action.triggered.connect(self.open_profile_manager)
        profile_menu.addAction(self.manage_profiles_action)
        
        self.parent_dashboard_action = QAction("Parent &Dashboard", self)
        self.parent_dashboard_action.setShortcut("Ctrl+D")
        self.parent_dashboard_action.triggered.connect(self.open_parent_dashboard)
        profile_menu.addAction(self.parent_dashboard_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("&Settings")
        
        preferences = QAction("&Preferences", self)
        preferences.setShortcut("Ctrl+,")
        preferences.triggered.connect(self.open_settings)
        settings_menu.addAction(preferences)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        user_guide = QAction("&User Guide", self)
        user_guide.setShortcut("F1")
        user_guide.triggered.connect(self.open_user_guide)
        help_menu.addAction(user_guide)
        
        help_menu.addSeparator()
        
        about = QAction("&About Sunflower AI", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)
        
    def create_toolbar(self):
        """Create main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)
        
        # New Conversation Action
        new_conv_action = QAction(QIcon.fromTheme("document-new"), "&New Conversation", self)
        new_conv_action.triggered.connect(self.new_conversation)
        toolbar.addAction(new_conv_action)
        
        toolbar.addSeparator()
        
        # Model info label
        self.model_info_label = QLabel()
        self.update_model_info()
        toolbar.addWidget(self.model_info_label)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy(), 
                           spacer.sizePolicy().verticalPolicy())
        toolbar.addWidget(spacer)
        
        # Session timer display
        self.session_timer_label = QLabel("Session: 00:00")
        toolbar.addWidget(self.session_timer_label)
        
    def connect_to_controller(self):
        """Connects UI signals to controller slots and controller signals to UI slots."""
        # UI to Controller
        self.profile_selected.connect(self.app_controller.on_profile_selected)
        self.prompt_submitted.connect(self.app_controller.on_user_prompt_submitted)

        # Controller to UI
        self.app_controller.new_response_chunk.connect(self.on_response_chunk)
        self.app_controller.response_finished.connect(self.on_response_complete)
        self.app_controller.display_error.connect(self.on_response_error)
        self.app_controller.display_safety_alert.connect(self.on_safety_alert)
        self.app_controller.session_timed_out.connect(self.on_session_timed_out)
        self.app_controller.update_status.connect(self.update_status_bar)

    def apply_theme(self):
        """Apply visual theme based on profile type"""
        if self.current_profile:
            if self.current_profile['type'] == 'child':
                # Child-friendly theme
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #FFF8DC;
                    }
                    QToolBar {
                        background-color: #FFE4B5;
                        border: none;
                        padding: 5px;
                    }
                    QPushButton {
                        background-color: #FFD700;
                        border: 2px solid #FFA500;
                        border-radius: 15px;
                        padding: 8px 15px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #FFA500;
                    }
                    QLabel {
                        color: #4B0082;
                        font-size: 13px;
                    }
                """)
            else:
                # Professional parent theme
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #F5F5F5;
                    }
                    QToolBar {
                        background-color: #E0E0E0;
                        border: none;
                        padding: 5px;
                    }
                    QPushButton {
                        background-color: #4CAF50;
                        border: none;
                        border-radius: 5px;
                        padding: 8px 15px;
                        color: white;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QLabel {
                        color: #333333;
                        font-size: 12px;
                    }
                """)
        # Set a default palette for the main window
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.AlternateBase, Qt.GlobalColor.lightGray)
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        self.setPalette(palette)

    def set_profile(self, profile: Dict):
        """Sets the current active profile and updates the UI."""
        self.current_profile = profile
        self.is_parent_mode = (profile['type'] == 'parent')
        
        self.profile_switcher.set_current_profile(profile['id'])
        self.update_for_profile()
        self.new_conversation()

        # Notify controller
        self.profile_selected.emit(profile)

    def switch_profile(self, profile_id: str):
        """Handle profile switching from the switcher widget."""
        profile = self.profile_manager.get_child(profile_id) or self.profile_manager.get_parent_profile()
        if profile:
            self.set_profile(profile)

    def show_profile_switcher(self):
        self.profile_switcher.show_menu()

    @pyqtSlot()
    def on_session_timed_out(self):
        """Handles the session timeout signal from the controller."""
        QMessageBox.information(
            self,
            "Session Timeout",
            f"Your session has timed out after {SESSION_TIMEOUT_MINUTES} minutes of inactivity.\n"
            "Please select your profile to continue."
        )
        self.profile_switcher.show_menu()


    @pyqtSlot(str)
    def on_response_chunk(self, chunk: str):
        """Append a chunk of the AI's response to the chat."""
        self.chat_widget.append_message_chunk(chunk)

    @pyqtSlot()
    def on_response_complete(self):
        """Finalize the AI's message in the chat."""
        self.chat_widget.finalize_message()
        self.update_status_bar("Ready")

    @pyqtSlot(str, str)
    def on_response_error(self, title: str, message: str):
        """Show an error message."""
        QMessageBox.critical(self, title, message)
        self.update_status_bar("Error")

    @pyqtSlot(str, str)
    def on_safety_alert(self, category: str, redirect_message: str):
        """Display a safety alert to the user."""
        self.chat_widget.add_message("Sunflower AI", redirect_message, is_system=True)
        self.update_status_bar("Safety Alert")
        # Optionally, show a more prominent visual indicator
        QMessageBox.warning(self, "Safety Alert", f"The topic was changed because it was related to '{category}'.")

    def new_conversation(self):
        """Starts a new conversation."""
        self.chat_widget.clear_chat()
        self.update_status_bar("New conversation started.")
        # Any other UI reset logic can go here

    def update_status_bar(self, message: str = ""):
        """Updates the status bar with current info."""
        if not message:
            message = "Ready"
        
        model_name = self.model_manager.get_current_model_name()
        self.status_bar.showMessage(f"Profile: {self.current_profile['name']} | Model: {model_name} | Status: {message}")

    def open_profile_manager(self):
        """Opens the profile management dialog."""
        dialog = ProfileManagerDialog(self.profile_manager, self)
        dialog.exec()
        self.profile_switcher.populate_profiles() # Refresh after changes

    def open_parent_dashboard(self):
        """Opens the parent dashboard."""
        if not self.is_parent_mode:
            QMessageBox.warning(self, "Access Denied", "The dashboard is only available for parents.")
            return
        
        # For this example, we'll assume it's a dialog.
        # In a real app, it might be a separate window or a stacked widget.
        dashboard = ParentDashboard(self.profile_manager, self)
        dashboard.exec()

    def open_settings(self):
        """Opens the settings dialog."""
        dialog = SettingsDialog(self.config, self)
        dialog.exec()
        self.apply_theme() # Re-apply theme if settings changed

    def open_user_guide(self):
        """Opens the user guide (placeholder)."""
        QMessageBox.information(self, "User Guide", "The user guide would open here.")

    def show_about(self):
        """Shows the about dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h3>{APP_NAME} v{VERSION}</h3>"
            "<p>A family-focused K-12 STEM education system.</p>"
            "<p>Copyright 2025 Sunflower AI Systems Inc.</p>"
        )

    def closeEvent(self, event: QCloseEvent):
        """Handle the window close event."""
        reply = QMessageBox.question(
            self,
            "Exit Confirmation",
            "Are you sure you want to exit? Any unsaved progress will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

    def update_for_profile(self):
        """Update UI elements based on the current profile (parent vs child)."""
        is_parent = self.is_parent_mode
        self.manage_profiles_action.setVisible(is_parent)
        self.parent_dashboard_action.setVisible(is_parent)
        # Add other UI changes here if needed

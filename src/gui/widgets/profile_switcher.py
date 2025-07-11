#!/usr/bin/env python3
"""
Profile Switcher Widget for Sunflower AI
A dropdown menu to switch between user profiles.
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QFrame, QMenu)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap, QFont, QAction

from ...assets.images import get_image_path


class ProfileSwitcher(QFrame):
    """
    A clickable widget that shows the current user and provides a dropdown
    menu to switch to other profiles or log out.
    """
    # Signals to be connected in the main window
    profile_selected = pyqtSignal(dict)
    manage_profiles_requested = pyqtSignal()
    logout_requested = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.current_profile = None
        self.all_profiles = []
        self._init_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _init_ui(self):
        """Set up the user interface for the profile switcher."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #F0F0F0;
                border: 1px solid #CCCCCC;
                border-radius: 15px;
            }
            QFrame:hover {
                background-color: #E0E0E0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_label.setScaledContents(True)

        self.name_label = QLabel("No Profile")
        self.name_label.setFont(QFont("Poppins", 10, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        
        self.setFixedSize(120, 80)

    def set_profiles(self, current_profile: dict, all_profiles: list):
        """Update the profiles available in the switcher."""
        self.current_profile = current_profile
        self.all_profiles = all_profiles
        self.update_display()

    def update_display(self):
        """Update the displayed name and avatar."""
        if not self.current_profile:
            self.name_label.setText("No Profile")
            avatar_path = get_image_path("avatars/placeholder.png")
            self.avatar_label.setPixmap(QPixmap(avatar_path))
            return
            
        self.name_label.setText(self.current_profile.get('name', 'Unknown'))
        
        # In a real app, you'd have profile-specific avatars
        avatar_path = get_image_path("avatars/placeholder.png")
        self.avatar_label.setPixmap(QPixmap(avatar_path))

    def mousePressEvent(self, event):
        """Show the profile selection menu on click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_profile_menu()

    def _show_profile_menu(self):
        """Create and display the context menu for profile switching."""
        menu = QMenu(self)

        # Add other profiles to switch to
        if self.current_profile:
            for profile in self.all_profiles:
                if profile['id'] != self.current_profile['id']:
                    action = QAction(profile.get('name'), self)
                    action.triggered.connect(lambda checked=False, p=profile: self.profile_selected.emit(p))
                    menu.addAction(action)

        menu.addSeparator()

        # Add special actions for parent
        if self.current_profile and self.current_profile.get('type') == 'parent':
            manage_action = QAction("Manage Profiles", self)
            manage_action.triggered.connect(self.manage_profiles_requested)
            menu.addAction(manage_action)
            menu.addSeparator()

        # Logout action
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout_requested)
        menu.addAction(logout_action)

        # Position the menu below the widget
        point = self.mapToGlobal(self.rect().bottomLeft())
        menu.exec(point)

"""
Login dialog for Sunflower AI
Family-friendly profile selection and authentication
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QStackedWidget, QWidget, QGroupBox,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation,
    QRect, QEasingCurve, QSize
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QFont, QPalette, QColor,
    QPainter, QPainterPath, QBrush, QLinearGradient
)

from ..constants import APP_NAME, VERSION
from ..profiles.profile_manager import ProfileManager


class ProfileCard(QWidget):
    """Visual card representing a user profile"""
    clicked = pyqtSignal(dict)
    
    def __init__(self, profile: Dict, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setup_ui()
        
    def setup_ui(self):
        """Create profile card UI"""
        self.setFixedSize(200, 250)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Avatar
        avatar_label = QLabel()
        avatar_label.setFixedSize(120, 120)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load avatar or use default
        avatar_path = self.get_avatar_path()
        if avatar_path.exists():
            pixmap = QPixmap(str(avatar_path))
            avatar_label.setPixmap(pixmap.scaled(
                120, 120, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            # Create colored circle with initial
            avatar_label.setText(self.profile['name'][0].upper())
            avatar_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.get_profile_color()};
                    border-radius: 60px;
                    color: white;
                    font-size: 48px;
                    font-weight: bold;
                }}
            """)
            
        layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Name
        name_label = QLabel(self.profile['name'])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_font = QFont()
        name_font.setPointSize(16)
        name_font.setBold(True)
        name_label.setFont(name_font)
        layout.addWidget(name_label)
        
        # Profile type/age
        if self.profile['type'] == 'child':
            info_text = f"Age {self.profile.get('age', '?')}"
        else:
            info_text = "Parent Account"
            
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #666666;")
        layout.addWidget(info_label)
        
        # Card styling
        self.setStyleSheet("""
            ProfileCard {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 15px;
            }
            ProfileCard:hover {
                border: 3px solid #FFD700;
                background-color: #FFFACD;
            }
        """)
        
    def get_avatar_path(self) -> Path:
        """Get path to profile avatar"""
        from ..config import Config
        config = Config()
        avatar_name = f"avatar_{self.profile['id']}.png"
        return config.resources_path / "images" / "avatars" / avatar_name
        
    def get_profile_color(self) -> str:
        """Get color for profile based on name"""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"
        ]
        index = sum(ord(c) for c in self.profile['name']) % len(colors)
        return colors[index]
        
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.profile)
            

class LoginDialog(QDialog):
    """Main login dialog with profile selection"""
    
    profile_selected = pyqtSignal(dict)
    
    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.selected_profile = None
        
        self.setWindowTitle(f"{APP_NAME} - Welcome")
        self.setFixedSize(900, 600)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowCloseButtonHint
        )
        
        self.setup_ui()
        self.load_profiles()
        
    def setup_ui(self):
        """Create login dialog UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with logo and title
        header = self.create_header()
        layout.addWidget(header)
        
        # Stacked widget for different screens
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget, 1)
        
        # Create screens
        self.profile_selection_widget = self.create_profile_selection()
        self.parent_login_widget = self.create_parent_login()
        self.first_time_widget = self.create_first_time_setup()
        
        self.stacked_widget.addWidget(self.profile_selection_widget)
        self.stacked_widget.addWidget(self.parent_login_widget)
        self.stacked_widget.addWidget(self.first_time_widget)
        
        # Footer
        footer = self.create_footer()
        layout.addWidget(footer)
        
        # Apply dialog styling
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
            }
        """)
        
    def create_header(self) -> QWidget:
        """Create dialog header with branding"""
        header = QWidget()
        header.setFixedHeight(120)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFD700, stop:1 #FFA500
                );
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(40, 20, 40, 20)
        
        # Logo
        logo_label = QLabel()
        logo_path = Path(__file__).parent.parent.parent / "resources" / "images" / "logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(pixmap.scaled(
                80, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            logo_label.setText("🌻")
            logo_label.setStyleSheet("font-size: 60px;")
            
        layout.addWidget(logo_label)
        
        # Title and tagline
        title_layout = QVBoxLayout()
        
        title = QLabel("Sunflower AI")
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        title_layout.addWidget(title)
        
        tagline = QLabel("Safe STEM Education for Every Child")
        tagline_font = QFont()
        tagline_font.setPointSize(14)
        tagline.setFont(tagline_font)
        tagline.setStyleSheet("color: #FFFACD;")
        title_layout.addWidget(tagline)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        return header
        
    def create_footer(self) -> QWidget:
        """Create dialog footer"""
        footer = QWidget()
        footer.setFixedHeight(40)
        footer.setStyleSheet("""
            QWidget {
                background-color: #E0E0E0;
                border-top: 1px solid #CCCCCC;
            }
        """)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 0, 20, 0)
        
        version_label = QLabel(f"Version {VERSION}")
        version_label.setStyleSheet("color: #666666;")
        layout.addWidget(version_label)
        
        layout.addStretch()
        
        help_btn = QPushButton("Help")
        help_btn.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #4169E1;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #1E90FF;
            }
        """)
        help_btn.clicked.connect(self.show_help)
        layout.addWidget(help_btn)
        
        return footer
        
    def create_profile_selection(self) -> QWidget:
        """Create profile selection screen"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 20, 40, 20)
        
        # Instructions
        instructions = QLabel("Who's learning today? Click your profile to begin!")
        instructions_font = QFont()
        instructions_font.setPointSize(16)
        instructions.setFont(instructions_font)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Profile grid scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Profile grid container
        self.profile_container = QWidget()
        self.profile_grid = QGridLayout(self.profile_container)
        self.profile_grid.setSpacing(20)
        self.profile_grid.setContentsMargins(20, 20, 20, 20)
        
        scroll_area.setWidget(self.profile_container)
        layout.addWidget(scroll_area, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        # Add Profile button (for parents)
        self.add_profile_btn = QPushButton("Add New Profile")
        self.add_profile_btn.setFixedHeight(40)
        self.add_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        self.add_profile_btn.clicked.connect(self.request_parent_login)
        button_layout.addWidget(self.add_profile_btn)
        
        button_layout.addStretch()
        
        # Parent Login button
        parent_login_btn = QPushButton("Parent Login")
        parent_login_btn.setFixedHeight(40)
        parent_login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        parent_login_btn.clicked.connect(self.show_parent_login)
        button_layout.addWidget(parent_login_btn)
        
        layout.addLayout(button_layout)
        
        return widget
        
    def create_parent_login(self) -> QWidget:
        """Create parent login screen"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Center content
        center_widget = QWidget()
        center_widget.setMaximumWidth(400)
        center_layout = QVBoxLayout(center_widget)
        
        # Title
        title = QLabel("Parent Login")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(title)
        
        center_layout.addSpacing(20)
        
        # Login form
        form_group = QGroupBox("Enter your password to access parent features")
        form_layout = QVBoxLayout()
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Parent Password")
        self.password_input.setFixedHeight(40)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #CCCCCC;
                border-radius: 5px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        self.password_input.returnPressed.connect(self.verify_parent_login)
        form_layout.addWidget(self.password_input)
        
        form_group.setLayout(form_layout)
        center_layout.addWidget(form_group)
        
        center_layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        back_btn = QPushButton("Back")
        back_btn.setFixedHeight(40)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        back_btn.clicked.connect(self.show_profile_selection)
        button_layout.addWidget(back_btn)
        
        login_btn = QPushButton("Login")
        login_btn.setFixedHeight(40)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        login_btn.clicked.connect(self.verify_parent_login)
        button_layout.addWidget(login_btn)
        
        center_layout.addLayout(button_layout)
        
        # Forgot password link
        forgot_link = QLabel('<a href="#">Forgot password?</a>')
        forgot_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        forgot_link.setOpenExternalLinks(False)
        forgot_link.linkActivated.connect(self.show_password_help)
        forgot_link.setStyleSheet("margin-top: 20px;")
        center_layout.addWidget(forgot_link)
        
        # Center the form
        layout.addStretch()
        layout.addWidget(center_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        
        return widget
        
    def create_first_time_setup(self) -> QWidget:
        """Create first-time setup screen"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Welcome message
        welcome = QLabel(
            "<h2>Welcome to Sunflower AI!</h2>"
            "<p>Let's set up your family's educational assistant.</p>"
            "<p>This will only take a few minutes.</p>"
        )
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setWordWrap(True)
        layout.addWidget(welcome)
        
        layout.addSpacing(30)
        
        # Setup form
        form_group = QGroupBox("Create Parent Account")
        form_layout = QGridLayout()
        
        # Parent name
        form_layout.addWidget(QLabel("Your Name:"), 0, 0)
        self.parent_name_input = QLineEdit()
        self.parent_name_input.setPlaceholderText("Enter your name")
        form_layout.addWidget(self.parent_name_input, 0, 1)
        
        # Email (optional)
        form_layout.addWidget(QLabel("Email (optional):"), 1, 0)
        self.parent_email_input = QLineEdit()
        self.parent_email_input.setPlaceholderText("your@email.com")
        form_layout.addWidget(self.parent_email_input, 1, 1)
        
        # Password
        form_layout.addWidget(QLabel("Create Password:"), 2, 0)
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText("Choose a secure password")
        form_layout.addWidget(self.new_password_input, 2, 1)
        
        # Confirm password
        form_layout.addWidget(QLabel("Confirm Password:"), 3, 0)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Enter password again")
        form_layout.addWidget(self.confirm_password_input, 3, 1)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        layout.addSpacing(20)
        
        # Create account button
        create_btn = QPushButton("Create Account and Continue")
        create_btn.setFixedHeight(50)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        create_btn.clicked.connect(self.create_parent_account)
        layout.addWidget(create_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        return widget
        
    def load_profiles(self):
        """Load profiles and populate the selection screen"""
        # Check if parent account exists
        if not self.profile_manager.is_setup_complete():
            self.stacked_widget.setCurrentWidget(self.first_time_widget)
            return

        self.stacked_widget.setCurrentWidget(self.profile_selection_widget)
        
        parent_profile = self.profile_manager.get_parent_profile()
        child_profiles = self.profile_manager.get_all_children()
        
        # Clear existing cards
        # This is a bit complex due to the flow layout, safer to recreate
        self.profile_selection_widget = self.create_profile_selection()
        self.stacked_widget.insertWidget(0, self.profile_selection_widget)
        self.stacked_widget.removeWidget(self.stacked_widget.widget(1))

        # Add parent card
        parent_card = ProfileCard(parent_profile)
        parent_card.clicked.connect(self.select_profile)
        self.profile_grid.addWidget(parent_card, 0, 0) # Assuming a grid layout for now, adjust if needed
        
        # Add child cards
        row = 0
        col = 1
        max_cols = 3
        
        for child in child_profiles:
            child_card = ProfileCard(child)
            child_card.clicked.connect(self.select_profile)
            self.profile_grid.addWidget(child_card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def select_profile(self, profile: Dict):
        """Handle profile selection"""
        self.selected_profile = profile
        
        if profile['type'] == 'parent':
            # Request password for parent
            self.show_parent_login()
        else:
            # Check if child profile is locked
            is_locked, message = self.profile_manager.is_profile_locked(profile['id'])
            if is_locked:
                QMessageBox.critical(self, "Profile Locked", message)
                self.selected_profile = None # Deselect
                return
            # Child profile selected, no password needed
            self.accept()
            
    def show_profile_selection(self):
        """Show profile selection screen"""
        self.stacked_widget.setCurrentWidget(self.profile_selection_widget)
        
    def show_parent_login(self):
        """Show parent login screen"""
        self.stacked_widget.setCurrentWidget(self.parent_login_widget)
        self.password_input.clear()
        self.password_input.setFocus()
        
    def request_parent_login(self):
        """Request parent login before allowing profile management"""
        QMessageBox.information(
            self,
            "Parent Login Required",
            "Please log in with your parent password to add or manage profiles."
        )
        self.show_parent_login()
        
    def verify_parent_login(self):
        """Verify parent password"""
        password = self.password_input.text()
        
        if not password:
            QMessageBox.warning(
                self,
                "Password Required",
                "Please enter your parent password."
            )
            return
            
        parent_profile = self.profile_manager.verify_parent_login(password)
        
        if parent_profile:
            self.selected_profile = parent_profile
            self.profile_selected.emit(parent_profile)
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Login Failed",
                "Incorrect password. Please try again."
            )
            self.password_input.clear()
            self.password_input.setFocus()
            
    def create_parent_account(self):
        """Create initial parent account"""
        name = self.parent_name_input.text().strip()
        email = self.parent_email_input.text().strip()
        password = self.new_password_input.text()
        confirm = self.confirm_password_input.text()
        
        # Validation
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter your name.")
            return
            
        if len(password) < 6:
            QMessageBox.warning(
                self,
                "Password Too Short",
                "Password must be at least 6 characters long."
            )
            return
            
        if password != confirm:
            QMessageBox.warning(
                self,
                "Passwords Don't Match",
                "The passwords you entered don't match. Please try again."
            )
            return
            
        # Create parent account
        try:
            success = self.profile_manager.create_parent_account(
                name, email, password
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Account Created",
                    "Parent account created successfully!\n\n"
                    "You can now add profiles for your children."
                )
                
                # Get parent profile and proceed
                parent_profile = self.profile_manager.get_parent_profile()
                self.selected_profile = parent_profile
                self.profile_selected.emit(parent_profile)
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Account Creation Failed",
                    "Failed to create parent account. Please try again."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred: {str(e)}"
            )
            
    def show_password_help(self):
        """Show password recovery help"""
        QMessageBox.information(
            self,
            "Password Recovery",
            "If you've forgotten your parent password, you'll need to:\n\n"
            "1. Close this application\n"
            "2. Navigate to the Sunflower AI data folder\n"
            "3. Delete the 'profiles' folder\n"
            "4. Restart the application to set up a new parent account\n\n"
            "Note: This will remove all existing profiles and session data."
        )
        
    def show_help(self):
        """Show help information"""
        help_text = """
        <h3>Getting Started with Sunflower AI</h3>
        
        <h4>For Parents:</h4>
        <ul>
        <li>Click "Parent Login" to access parent features</li>
        <li>Create and manage child profiles</li>
        <li>Review your children's learning sessions</li>
        <li>Adjust safety and content settings</li>
        </ul>
        
        <h4>For Children:</h4>
        <ul>
        <li>Click your profile picture to start learning</li>
        <li>Ask any science, technology, engineering, or math question</li>
        <li>The AI will adapt to your age automatically</li>
        <li>Have fun exploring and learning!</li>
        </ul>
        
        <p>For more help, see the User Guide in the Help menu.</p>
        """
        
        QMessageBox.information(
            self,
            "Sunflower AI Help",
            help_text
        )
        
    def get_selected_profile(self) -> Optional[Dict]:
        """Get the selected profile"""
        return self.selected_profile

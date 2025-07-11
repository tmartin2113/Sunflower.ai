"""
Profile management dialog for parents
Add, edit, and remove child profiles
"""

from typing import Dict, Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QComboBox,
    QListWidget, QListWidgetItem, QGroupBox, QMessageBox,
    QTabWidget, QWidget, QTextEdit, QCheckBox,
    QDialogButtonBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

from ..profiles.profile_manager import ProfileManager
from ..constants import MIN_AGE, MAX_AGE


class ProfileListItem(QListWidgetItem):
    """Custom list item for profile display"""
    
    def __init__(self, profile: Dict):
        super().__init__()
        self.profile = profile
        self.update_display()
        
    def update_display(self):
        """Update the display text"""
        name = self.profile['name']
        age = self.profile.get('age', '?')
        grade = self.profile.get('grade', '?')
        
        self.setText(f"{name} (Age {age}, Grade {grade})")
        
        # Set icon based on age
        if age and isinstance(age, int):
            if age <= 8:
                self.setIcon(QIcon("🧒"))
            elif age <= 12:
                self.setIcon(QIcon("👦"))
            else:
                self.setIcon(QIcon("👨‍🎓"))


class ProfileEditWidget(QWidget):
    """Widget for editing profile details"""
    
    profile_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_profile = None
        self.setup_ui()
        
    def setup_ui(self):
        """Create the edit form"""
        layout = QFormLayout(self)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter child's name")
        self.name_input.textChanged.connect(self.on_field_changed)
        layout.addRow("Name:", self.name_input)
        
        # Age
        self.age_input = QSpinBox()
        self.age_input.setRange(MIN_AGE, MAX_AGE)
        self.age_input.setSuffix(" years")
        self.age_input.valueChanged.connect(self.on_field_changed)
        layout.addRow("Age:", self.age_input)
        
        # Grade
        self.grade_input = QComboBox()
        grades = ["Pre-K", "K"] + [str(i) for i in range(1, 13)] + ["College"]
        self.grade_input.addItems(grades)
        self.grade_input.currentTextChanged.connect(self.on_field_changed)
        layout.addRow("Grade:", self.grade_input)
        
        # Learning style
        self.learning_style_input = QComboBox()
        self.learning_style_input.addItems([
            "Visual", "Auditory", "Kinesthetic", "Reading/Writing", "Mixed"
        ])
        self.learning_style_input.currentTextChanged.connect(self.on_field_changed)
        layout.addRow("Learning Style:", self.learning_style_input)
        
        # Interests
        self.interests_input = QTextEdit()
        self.interests_input.setPlaceholderText(
            "Enter interests (one per line):\n"
            "Example:\n"
            "Dinosaurs\n"
            "Space\n"
            "Robotics"
        )
        self.interests_input.setMaximumHeight(100)
        self.interests_input.textChanged.connect(self.on_field_changed)
        layout.addRow("Interests:", self.interests_input)
        
        # Special notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText(
            "Any special notes about this child's learning needs..."
        )
        self.notes_input.setMaximumHeight(100)
        self.notes_input.textChanged.connect(self.on_field_changed)
        layout.addRow("Notes:", self.notes_input)
        
        # Save button
        self.save_button = QPushButton("Save Changes")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_profile)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        layout.addRow("", self.save_button)
        
    def load_profile(self, profile: Dict):
        """Load profile data into form"""
        self.current_profile = profile
        
        # Block signals during loading
        self.name_input.blockSignals(True)
        self.age_input.blockSignals(True)
        self.grade_input.blockSignals(True)
        self.learning_style_input.blockSignals(True)
        self.interests_input.blockSignals(True)
        self.notes_input.blockSignals(True)
        
        # Load data
        self.name_input.setText(profile.get('name', ''))
        self.age_input.setValue(profile.get('age', MIN_AGE))
        
        # Set grade
        grade = str(profile.get('grade', 'K'))
        index = self.grade_input.findText(grade)
        if index >= 0:
            self.grade_input.setCurrentIndex(index)
            
        # Set learning style
        style = profile.get('learning_style', 'Visual')
        index = self.learning_style_input.findText(style)
        if index >= 0:
            self.learning_style_input.setCurrentIndex(index)
            
        # Set interests
        interests = profile.get('interests', [])
        self.interests_input.setPlainText('\n'.join(interests))
        
        # Set notes
        self.notes_input.setPlainText(profile.get('notes', ''))
        
        # Re-enable signals
        self.name_input.blockSignals(False)
        self.age_input.blockSignals(False)
        self.grade_input.blockSignals(False)
        self.learning_style_input.blockSignals(False)
        self.interests_input.blockSignals(False)
        self.notes_input.blockSignals(False)
        
        # Reset save button
        self.save_button.setEnabled(False)
        
    def on_field_changed(self):
        """Handle field changes"""
        self.save_button.setEnabled(True)
        
    def save_profile(self):
        """Save profile changes"""
        if not self.current_profile:
            return
            
        # Validate name
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Name Required",
                "Please enter a name for this profile."
            )
            return
            
        # Update profile data
        self.current_profile['name'] = name
        self.current_profile['age'] = self.age_input.value()
        self.current_profile['grade'] = self.grade_input.currentText()
        self.current_profile['learning_style'] = self.learning_style_input.currentText()
        
        # Parse interests
        interests_text = self.interests_input.toPlainText()
        interests = [i.strip() for i in interests_text.split('\n') if i.strip()]
        self.current_profile['interests'] = interests
        
        # Save notes
        self.current_profile['notes'] = self.notes_input.toPlainText()
        
        # Emit update signal
        self.profile_updated.emit(self.current_profile)
        
        # Reset save button
        self.save_button.setEnabled(False)
        
        QMessageBox.information(
            self,
            "Profile Saved",
            f"Profile for {name} has been updated."
        )


class ProfileManagerDialog(QDialog):
    """Dialog for managing child profiles"""
    
    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        
        self.setWindowTitle("Manage Child Profiles")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.load_profiles()
        
    def setup_ui(self):
        """Create the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Child Profile Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Add profile button
        add_btn = QPushButton("Add New Child")
        add_btn.setIcon(QIcon("➕"))
        add_btn.clicked.connect(self.add_new_profile)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Main content - splitter with list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - profile list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("Child Profiles")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)
        
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self.on_profile_selected)
        left_layout.addWidget(self.profile_list)
        
        # Remove button
        self.remove_btn = QPushButton("Remove Profile")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_profile)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        left_layout.addWidget(self.remove_btn)
        
        splitter.addWidget(left_widget)
        
        # Right side - profile details tabs
        self.tabs = QTabWidget()
        
        # Edit tab
        self.edit_widget = ProfileEditWidget()
        self.edit_widget.profile_updated.connect(self.on_profile_updated)
        self.tabs.addTab(self.edit_widget, "Edit Profile")
        
        # Statistics tab
        self.stats_widget = self.create_statistics_tab()
        self.tabs.addTab(self.stats_widget, "Learning Statistics")
        
        # Settings tab
        self.settings_widget = self.create_settings_tab()
        self.tabs.addTab(self.settings_widget, "Safety Settings")
        
        splitter.addWidget(self.tabs)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)
        
    def create_statistics_tab(self) -> QWidget:
        """Create statistics tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setPlainText("Select a profile to view statistics.")
        layout.addWidget(self.stats_text)
        
        return widget
        
    def create_settings_tab(self) -> QWidget:
        """Create settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Session time limit
        self.session_limit_input = QSpinBox()
        self.session_limit_input.setRange(15, 180)
        self.session_limit_input.setSuffix(" minutes")
        self.session_limit_input.setValue(60)
        layout.addRow("Session Time Limit:", self.session_limit_input)
        
        # Daily time limit
        self.daily_limit_input = QSpinBox()
        self.daily_limit_input.setRange(30, 360)
        self.daily_limit_input.setSuffix(" minutes")
        self.daily_limit_input.setValue(120)
        layout.addRow("Daily Time Limit:", self.daily_limit_input)
        
        # Content filtering
        self.content_filter_input = QComboBox()
        self.content_filter_input.addItems(["Maximum", "High", "Moderate"])
        layout.addRow("Content Filtering:", self.content_filter_input)
        
        # Advanced vocabulary
        self.advanced_vocab_check = QCheckBox("Allow advanced vocabulary for age")
        layout.addRow("", self.advanced_vocab_check)
        
        # Save settings button
        save_settings_btn = QPushButton("Save Settings")
        save_settings_btn.clicked.connect(self.save_profile_settings)
        layout.addRow("", save_settings_btn)
        
        return widget
        
    def load_profiles(self):
        """Load all child profiles"""
        self.profile_list.clear()
        
        profiles = [p for p in self.profile_manager.get_all_profiles() 
                   if p['type'] == 'child']
        
        for profile in profiles:
            item = ProfileListItem(profile)
            self.profile_list.addItem(item)
            
        # Select first profile if available
        if self.profile_list.count() > 0:
            self.profile_list.setCurrentRow(0)
            
    def on_profile_selected(self, current, previous):
        """Handle profile selection"""
        if isinstance(current, ProfileListItem):
            profile = current.profile
            
            # Enable remove button
            self.remove_btn.setEnabled(True)
            
            # Load profile data
            self.edit_widget.load_profile(profile)
            
            # Update statistics
            self.update_statistics(profile)
            
            # Load settings
            self.load_profile_settings(profile)
        else:
            self.remove_btn.setEnabled(False)
            
    def update_statistics(self, profile: Dict):
        """Update statistics display"""
        stats = self.profile_manager.get_profile_statistics(profile['id'])
        
        stats_text = f"""
Profile Statistics for {profile['name']}
{'=' * 40}

Total Sessions: {stats.get('total_sessions', 0)}
Total Learning Time: {stats.get('total_hours', 0):.1f} hours
Average Session Length: {stats.get('avg_session_minutes', 0)} minutes

Topics Explored: {stats.get('unique_topics', 0)}
Vocabulary Learned: {stats.get('vocabulary_count', 0)} words
Concepts Mastered: {stats.get('concepts_count', 0)}

Last Active: {stats.get('last_active', 'Never')}
Member Since: {profile.get('created', 'Unknown')}

Top Interests:
"""
        
        # Add top interests
        for interest in stats.get('top_interests', [])[:5]:
            stats_text += f"  • {interest}\n"
            
        self.stats_text.setPlainText(stats_text)
        
    def load_profile_settings(self, profile: Dict):
        """Load profile-specific settings"""
        settings = profile.get('settings', {})
        
        self.session_limit_input.setValue(
            settings.get('session_time_limit', 60)
        )
        self.daily_limit_input.setValue(
            settings.get('daily_time_limit', 120)
        )
        
        filter_level = settings.get('content_filter', 'Maximum')
        index = self.content_filter_input.findText(filter_level)
        if index >= 0:
            self.content_filter_input.setCurrentIndex(index)
            
        self.advanced_vocab_check.setChecked(
            settings.get('allow_advanced_vocab', False)
        )
        
    def save_profile_settings(self):
        """Save profile-specific settings"""
        current_item = self.profile_list.currentItem()
        if not isinstance(current_item, ProfileListItem):
            return
            
        profile = current_item.profile
        
        settings = {
            'session_time_limit': self.session_limit_input.value(),
            'daily_time_limit': self.daily_limit_input.value(),
            'content_filter': self.content_filter_input.currentText(),
            'allow_advanced_vocab': self.advanced_vocab_check.isChecked()
        }
        
        profile['settings'] = settings
        
        # Save to profile manager
        self.profile_manager.update_profile(profile['id'], profile)
        
        QMessageBox.information(
            self,
            "Settings Saved",
            f"Settings for {profile['name']} have been saved."
        )
        
    def on_profile_updated(self, profile: Dict):
        """Handle profile update from edit widget"""
        # Update in profile manager
        self.profile_manager.update_profile(profile['id'], profile)
        
        # Update list item
        current_item = self.profile_list.currentItem()
        if isinstance(current_item, ProfileListItem):
            current_item.profile = profile
            current_item.update_display()
            
        # Reload statistics
        self.update_statistics(profile)
        
    def add_new_profile(self):
        """Add a new child profile"""
        # Create new profile dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Child")
        dialog.setModal(True)
        
        layout = QFormLayout(dialog)
        
        # Name input
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter child's name")
        layout.addRow("Name:", name_input)
        
        # Age input
        age_input = QSpinBox()
        age_input.setRange(MIN_AGE, MAX_AGE)
        age_input.setValue(8)
        age_input.setSuffix(" years")
        layout.addRow("Age:", age_input)
        
        # Grade input
        grade_input = QComboBox()
        grades = ["Pre-K", "K"] + [str(i) for i in range(1, 13)] + ["College"]
        grade_input.addItems(grades)
        grade_input.setCurrentText("3")
        layout.addRow("Grade:", grade_input)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            
            if not name:
                QMessageBox.warning(
                    self,
                    "Name Required",
                    "Please enter a name for the child."
                )
                return
                
            # Create new profile
            new_profile = self.profile_manager.add_child(
                name=name,
                age=age_input.value(),
                grade=grade_input.currentText()
            )
            
            if new_profile:
                # Reload profiles
                self.load_profiles()
                
                # Select new profile
                for i in range(self.profile_list.count()):
                    item = self.profile_list.item(i)
                    if isinstance(item, ProfileListItem):
                        if item.profile['id'] == new_profile:
                            self.profile_list.setCurrentItem(item)
                            break
                            
                QMessageBox.information(
                    self,
                    "Profile Created",
                    f"Profile for {name} has been created!"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Creation Failed",
                    "Failed to create profile. Please try again."
                )
                
    def remove_profile(self):
        """Remove selected profile"""
        current_item = self.profile_list.currentItem()
        if not isinstance(current_item, ProfileListItem):
            return
            
        profile = current_item.profile
        
        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Remove Profile",
            f"Are you sure you want to remove the profile for {profile['name']}?\n\n"
            "This will delete all session history and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from profile manager
            if self.profile_manager.remove_child(profile['id']):
                # Remove from list
                row = self.profile_list.row(current_item)
                self.profile_list.takeItem(row)
                
                # Clear displays if no profiles left
                if self.profile_list.count() == 0:
                    self.edit_widget.current_profile = None
                    self.stats_text.setPlainText("No profiles available.")
                    
                QMessageBox.information(
                    self,
                    "Profile Removed",
                    f"Profile for {profile['name']} has been removed."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Removal Failed",
                    "Failed to remove profile. Please try again."
                )

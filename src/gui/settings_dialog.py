"""
Settings dialog for Sunflower AI
Allows parents to configure application-wide settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QTabWidget, QWidget,
    QFormLayout, QComboBox, QSpinBox, QCheckBox, QGroupBox,
    QLabel
)
from PyQt6.QtCore import Qt

from ..config import Config

class SettingsDialog(QDialog):
    """
    A dialog for viewing and editing application settings.
    """
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("Application Settings")
        self.setMinimumWidth(500)
        self.setModal(True)

        # Main layout
        layout = QVBoxLayout(self)

        # Tabs for different settings categories
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self.general_tab = self.create_general_tab()
        self.safety_tab = self.create_safety_tab()
        self.data_tab = self.create_data_tab()

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.safety_tab, "Safety & Content")
        self.tabs.addTab(self.data_tab, "Data & Privacy")

        # Dialog buttons (Save, Cancel)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Load current settings into the UI
        self.load_settings()

    def create_general_tab(self) -> QWidget:
        """Creates the General settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # UI Theme
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Light", "Dark"])
        layout.addRow("UI Theme:", self.theme_selector)

        # Startup Behavior
        self.launch_on_startup = QCheckBox("Launch Sunflower AI on system startup")
        layout.addRow(self.launch_on_startup)

        return widget

    def create_safety_tab(self) -> QWidget:
        """Creates the Safety & Content settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Content Filtering")
        form_layout = QFormLayout(group)

        self.filter_level = QComboBox()
        self.filter_level.addItems(["Strict", "Moderate", "Relaxed"])
        self.filter_level.setToolTip(
            "Strict: Blocks a wide range of topics.\n"
            "Moderate: Allows more nuanced discussions.\n"
            "Relaxed: For older children, allows more freedom."
        )
        form_layout.addRow("Filter Strictness:", self.filter_level)
        
        layout.addWidget(group)

        session_group = QGroupBox("Session Management")
        session_layout = QFormLayout(session_group)

        self.session_limit = QSpinBox()
        self.session_limit.setRange(15, 180) # 15 mins to 3 hours
        self.session_limit.setSingleStep(15)
        self.session_limit.setSuffix(" minutes")
        session_layout.addRow("Daily time limit per child:", self.session_limit)
        
        layout.addWidget(session_group)
        layout.addStretch()

        return widget

    def create_data_tab(self) -> QWidget:
        """Creates the Data & Privacy settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.enable_logging = QCheckBox("Enable detailed session logging")
        self.enable_logging.setToolTip("Logs conversations and interactions for parent review.")
        layout.addRow(self.enable_logging)

        self.auto_delete_logs = QCheckBox("Automatically delete logs older than")
        layout.addRow(self.auto_delete_logs)

        self.log_retention_days = QSpinBox()
        self.log_retention_days.setRange(7, 365)
        self.log_retention_days.setValue(90)
        self.log_retention_days.setSuffix(" days")
        layout.addRow("", self.log_retention_days)
        
        # Link state of checkbox and spinbox
        self.auto_delete_logs.toggled.connect(self.log_retention_days.setEnabled)
        
        return widget

    def load_settings(self):
        """Loads settings from the config object into the UI controls."""
        # General
        theme = self.config.get_setting("ui.theme", "Light")
        self.theme_selector.setCurrentText(theme)
        
        # Safety
        filter_level = self.config.get_setting("safety.filter_level", "Strict")
        self.filter_level.setCurrentText(filter_level)

        session_limit = self.config.get_setting("safety.daily_time_limit", 120)
        self.session_limit.setValue(session_limit)
        
        # Data
        logging_enabled = self.config.get_setting("data.logging_enabled", True)
        self.enable_logging.setChecked(logging_enabled)
        
        auto_delete = self.config.get_setting("data.auto_delete_logs", False)
        self.auto_delete_logs.setChecked(auto_delete)
        
        retention = self.config.get_setting("data.log_retention_days", 90)
        self.log_retention_days.setValue(retention)
        self.log_retention_days.setEnabled(auto_delete)

    def save_settings(self):
        """Saves the current UI control states into the config object."""
        # General
        self.config.set_setting("ui.theme", self.theme_selector.currentText())

        # Safety
        self.config.set_setting("safety.filter_level", self.filter_level.currentText())
        self.config.set_setting("safety.daily_time_limit", self.session_limit.value())

        # Data
        self.config.set_setting("data.logging_enabled", self.enable_logging.isChecked())
        self.config.set_setting("data.auto_delete_logs", self.auto_delete_logs.isChecked())
        self.config.set_setting("data.log_retention_days", self.log_retention_days.value())
        
        # Persist changes to disk
        self.config.save()

    def accept(self):
        """Saves settings when the 'Save' button is clicked."""
        self.save_settings()
        super().accept()

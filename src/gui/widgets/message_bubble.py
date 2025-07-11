#!/usr/bin/env python3
"""
MessageBubble Widget for Sunflower AI
A custom widget to display a single chat message.
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QFrame)
from PyQt6.QtCore import Qt, pyqtProperty, QPropertyAnimation
from PyQt6.QtGui import QFont, QColor
from pathlib import Path

from ...utils.formatters import markdown_to_html


class MessageBubble(QFrame):
    """
    A speech-bubble-like widget for displaying a chat message.
    It visually distinguishes between user messages and AI messages.
    """

    def __init__(self, text: str, sender: str = "user", is_streaming: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self._sender = sender
        self._text = text
        self._is_streaming = is_streaming
        
        # Load the pygments stylesheet
        try:
            css_path = Path(__file__).parent.parent.parent / "assets" / "css" / "pygments.css"
            with open(css_path, "r") as f:
                self.pygments_css = f.read()
        except FileNotFoundError:
            self.pygments_css = "" # Fallback if the file is missing

        self._init_ui()
        self.set_text(text)

    def _init_ui(self):
        """Set up the user interface for the message bubble."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextBrowserInteraction)
        self.label.setOpenExternalLinks(True)
        self.label.document().setDefaultStyleSheet(self.pygments_css)
        
        self.layout.addWidget(self.label)
        self.setSizePolicy(QWidget.SizePolicy.Policy.Maximum, QWidget.SizePolicy.Policy.Preferred)
        
        # Apply style based on sender
        self._apply_style()

    def _apply_style(self):
        """Apply visual styling based on the message sender."""
        font = QFont("Poppins", 11)
        self.label.setFont(font)

        if self._sender == 'user':
            # User message: right-aligned, blue background
            self.setStyleSheet("""
                QFrame {
                    background-color: #007AFF;
                    color: white;
                    border-radius: 15px;
                }
            """)
            self.layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        else: # AI message
            # AI message: left-aligned, light gray background
            self.setStyleSheet("""
                QFrame {
                    background-color: #E5E5EA;
                    color: black;
                    border-radius: 15px;
                }
            """)
            self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def set_text(self, text: str):
        """Set the message text, converting Markdown to HTML."""
        self._text = text
        html = markdown_to_html(self._text)
        self.label.setText(html)

    def append_text(self, chunk: str):
        """Append a chunk of text to the bubble, for streaming."""
        self._text += chunk
        # Re-render the markdown for the updated text
        html = markdown_to_html(self._text + "...") # Add ellipsis for streaming effect
        self.label.setText(html)

    def set_finished_streaming(self):
        """Finalize the text after streaming is complete."""
        self._is_streaming = False
        self.set_text(self._text) # Re-render without the ellipsis

    def get_sender(self) -> str:
        """Return the sender of the message."""
        return self._sender

    def get_text(self) -> str:
        """Return the raw text of the message."""
        return self._text

#!/usr/bin/env python3
"""
Chat Widget for Sunflower AI
Provides the main user interface for interacting with the AI.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton,
                             QHBoxLayout, QScrollArea, QLabel, QFrame)
from PyQt6.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt6.QtGui import QFont

from .message_bubble import MessageBubble


class ChatWidget(QWidget):
    """
    A widget that provides a chat interface for conversing with the AI.
    It includes a message display area and a user input field.
    """
    # Signal emitted when the user sends a message
    message_sent = pyqtSignal(str)

    def __init__(self, parent: QWidget = None):
        """Initialize the chat widget"""
        super().__init__(parent)
        self.current_ai_message_bubble: MessageBubble = None
        self._init_ui()

    def _init_ui(self):
        """Set up the user interface for the chat widget"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # --- Message Display Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()  # Pushes messages to the top
        self.chat_layout.setSpacing(15)
        
        self.scroll_area.setWidget(self.chat_container)

        # --- Thinking Indicator ---
        self.thinking_label = QLabel("Sunflower is thinking...")
        font = QFont("Poppins", 10, QFont.Weight.Bold)
        font.setItalic(True)
        self.thinking_label.setFont(font)
        self.thinking_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thinking_label.setStyleSheet("color: #666;")
        self.thinking_label.hide()

        # --- Input Area ---
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Type your message here...")
        self.input_box.setFixedHeight(80)
        self.input_box.setFont(QFont("Poppins", 11))
        self.input_box.setAcceptRichText(False)
        # Handle Enter/Shift+Enter for sending
        self.input_box.keyPressEvent = self._handle_input_key_press

        self.send_button = QPushButton("Send")
        self.send_button.setFixedSize(100, 80)
        self.send_button.setFont(QFont("Poppins", 12, QFont.Weight.Bold))
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        
        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.send_button)

        # --- Assemble Layout ---
        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(self.thinking_label)
        main_layout.addLayout(input_layout)
        
        # --- Connections ---
        self.send_button.clicked.connect(self.send_message)
    
    def _handle_input_key_press(self, event):
        """Custom key press handler for the input box."""
        # Send on Enter, new line on Shift+Enter
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.send_message()
            event.accept()
        else:
            QTextEdit.keyPressEvent(self.input_box, event)

    @pyqtSlot()
    def send_message(self):
        """Emit the message_sent signal with the input text."""
        message = self.input_box.toPlainText().strip()
        if message:
            self.message_sent.emit(message)
            self.add_message(message, "user")
            self.input_box.clear()

    @pyqtSlot(str, str)
    def add_message(self, text: str, sender: str):
        """Add a new message bubble to the chat display."""
        bubble = MessageBubble(text, sender)
        # Insert before the stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        # Ensure scrollbar is at the bottom after adding a message
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())
    
    @pyqtSlot()
    def start_thinking(self):
        """Show the 'thinking' indicator and disable input."""
        self.thinking_label.show()
        self.input_box.setEnabled(False)
        self.send_button.setEnabled(False)
        self.current_ai_message_bubble = MessageBubble("", "ai", is_streaming=True)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.current_ai_message_bubble)

    @pyqtSlot(str)
    def stream_ai_response(self, chunk: str):
        """Append a chunk of text to the current AI message bubble."""
        if self.current_ai_message_bubble:
            self.current_ai_message_bubble.append_text(chunk)
            self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    @pyqtSlot()
    def finish_thinking(self):
        """Hide the 'thinking' indicator and re-enable input."""
        self.thinking_label.hide()
        self.input_box.setEnabled(True)
        self.send_button.setEnabled(True)
        if self.current_ai_message_bubble:
            self.current_ai_message_bubble.set_finished_streaming()
        self.current_ai_message_bubble = None
        self.input_box.setFocus()
    
    @pyqtSlot()
    def clear_chat(self):
        """Remove all messages from the chat display."""
        while self.chat_layout.count() > 1: # Keep the stretch
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_ai_message_bubble = None

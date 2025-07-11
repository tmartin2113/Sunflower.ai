#!/usr/bin/env python3
"""
Application Controller for Sunflower AI
Handles the main business logic and coordinates between the GUI and core components.
"""

import sys
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot, QTimer

from .model_manager import ModelManager
from .safety_filter import SafetyFilter
from ..profiles.profile_manager import ProfileManager
from ..config import Config
from ..profiles.session_logger import SessionLogger
from .conversation import ConversationManager
from datetime import datetime, timedelta
from ..constants import SESSION_TIMEOUT_MINUTES, AUTO_SAVE_INTERVAL_SECONDS


class ModelResponseThread(QThread):
    """Background thread for AI model responses"""
    response_chunk = pyqtSignal(str)
    response_complete = pyqtSignal()
    response_error = pyqtSignal(str)
    safety_alert = pyqtSignal(str, str)  # alert_type, message
    
    def __init__(self, model_manager, prompt, profile, safety_filter):
        super().__init__()
        self.model_manager = model_manager
        self.prompt = prompt
        self.profile = profile
        self.safety_filter = safety_filter
        self.should_stop = False
        
    def run(self):
        """Generate AI response in background"""
        try:
            # Safety check for child profiles
            if self.profile.get('type') == 'child':
                is_safe, category, redirect = self.safety_filter.check_content(self.prompt)
                
                if not is_safe:
                    self.safety_alert.emit(category, redirect)
                    self.response_complete.emit()
                    return
            
            # Generate response
            response_text = ""
            for chunk in self.model_manager.generate_response(
                self.prompt,
                self.profile,
                stream=True
            ):
                if self.should_stop:
                    break
                    
                response_text += chunk
                self.response_chunk.emit(chunk)
            
            # Log vocabulary and concepts for children
            if self.profile['type'] == 'child':
                vocabulary = self.model_manager.extract_vocabulary(response_text)
                concepts = self.model_manager.extract_concepts(response_text)
                # These would be logged to the session
                
        except Exception as e:
            self.response_error.emit(str(e))
        finally:
            self.response_complete.emit()
    
    def stop(self):
        """Stop response generation"""
        self.should_stop = True


class AppController(QObject):
    """
    The main application controller. Connects the UI to the backend logic.
    """

    # Signals to update the GUI
    new_response_chunk = pyqtSignal(str)
    response_finished = pyqtSignal()
    display_error = pyqtSignal(str, str)  # title, message
    display_safety_alert = pyqtSignal(str, str) # category, redirect_message
    session_timed_out = pyqtSignal()
    update_status = pyqtSignal(str)
    dashboard_data_ready = pyqtSignal(dict)

    def __init__(self, config: Config, profile_manager: ProfileManager, model_manager: ModelManager):
        super().__init__()
        self.config = config
        self.profile_manager = profile_manager
        self.model_manager = model_manager
        self.safety_filter = SafetyFilter(self.config)
        
        self.session_logger = SessionLogger(self.config.get_data_path())
        self.conversation_manager = ConversationManager(self.config)

        self.response_thread = None
        self.current_profile = None
        self.current_session_id = None
        self.last_activity = None

        # Session management timers
        self.session_timeout_timer = QTimer(self)
        self.session_timeout_timer.timeout.connect(self.check_session_timeout)
        
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save_session)

    @pyqtSlot(str, str)
    def request_dashboard_data(self, child_id: str, date_range: str):
        """Fetches and processes all data needed for the parent dashboard."""
        # This would be more complex in a real app, likely involving a background thread
        # For simplicity, we'll do it directly here.
        
        days = self._get_days_from_range(date_range)
        sessions = self.session_logger.get_sessions(child_id=child_id, days=days)
        
        stats = self._calculate_dashboard_statistics(sessions)
        
        # In a real app, you might fetch safety data from a different source
        # For now, we'll simulate it based on session logs
        safety_report = self._generate_safety_report(sessions)

        dashboard_data = {
            "stats": stats,
            "sessions": sessions,
            "safety_report": safety_report
        }
        self.dashboard_data_ready.emit(dashboard_data)

    def _get_days_from_range(self, date_range: str) -> int:
        """Helper to convert date range string to number of days."""
        return {
            "Today": 1,
            "Yesterday": 2, # Will filter for yesterday's date
            "Last 7 Days": 7,
            "Last 30 Days": 30,
            "All Time": 9999
        }.get(date_range, 7) # Default to 7 days

    def _calculate_dashboard_statistics(self, sessions: list) -> dict:
        """Calculates summary statistics from a list of sessions."""
        total_sessions = len(sessions)
        total_minutes = sum(s['duration_minutes'] for s in sessions)
        total_questions = sum(s['summary']['total_questions'] for s in sessions)
        safety_incidents = sum(s['summary']['safety_incidents'] for s in sessions)

        # This is a simplification; vocabulary would be tracked more robustly
        total_vocabulary = sum(len(s['summary'].get('vocabulary', [])) for s in sessions)

        return {
            "total_sessions": total_sessions,
            "total_hours": total_minutes / 60,
            "total_questions": total_questions,
            "safety_incidents": safety_incidents,
            "total_vocabulary": total_vocabulary,
        }

    def _generate_safety_report(self, sessions: list) -> dict:
        """Generates a summary safety report from sessions."""
        alerts = []
        for session in sessions:
            if session['summary']['safety_incidents'] > 0:
                # In a real app, you'd pull detailed alerts from the session log
                alerts.append({
                    "timestamp": session['start_time'],
                    "details": "Unsafe content was detected and redirected.",
                    "category": "Varies" # Placeholder
                })
        return {"alerts": alerts}

    @pyqtSlot(dict)
    def on_profile_selected(self, profile: dict):
        """Handles when a new user profile is selected."""
        self.end_current_session()
        self.current_profile = profile
        self.start_new_session()
        self.update_status.emit("Ready")

    @pyqtSlot(str)
    def on_user_prompt_submitted(self, prompt: str):
        """Process the prompt, run safety checks, and start a response thread."""
        self.last_activity = datetime.now()
        if self.response_thread and self.response_thread.isRunning():
            self.display_error.emit("Busy", "Please wait for the current response to finish.")
            return

        self.update_status.emit("Thinking...")
        self.response_thread = ModelResponseThread(
            self.model_manager,
            prompt,
            self.current_profile,
            self.safety_filter
        )
        self.response_thread.response_chunk.connect(self.new_response_chunk)
        self.response_thread.response_complete.connect(self.response_finished)
        self.response_thread.response_error.connect(lambda msg: self.display_error.emit("Response Error", msg))
        self.response_thread.safety_alert.connect(self.on_safety_alert_triggered)
        self.response_thread.start()

        if self.current_session_id:
            # This method will need to be implemented in ModelManager
            topics = [] # self.model_manager.extract_topics(prompt)
            self.session_logger.log_question(self.current_session_id, prompt, topics)

    @pyqtSlot(str, str)
    def on_safety_alert_triggered(self, category: str, redirect_message: str):
        """Handles the safety alert from the response thread."""
        self.display_safety_alert.emit(category, redirect_message)
        
        # Add a strike to the child's profile
        if self.current_profile and self.current_profile.get('type') == 'child':
            self.profile_manager.add_safety_strike(self.current_profile['id'], category)

    def start_new_session(self):
        """Starts a new user session."""
        if not self.current_profile:
            return
        
        self.current_session_id = self.session_logger.start_session(
            self.current_profile['id'],
            self.current_profile['name'],
            self.current_profile.get('age', 0)
        )
        self.last_activity = datetime.now()

        # Start timers only for child profiles
        if self.current_profile.get('type') == 'child':
            self.session_timeout_timer.start(60 * 1000) # Check every minute
            self.auto_save_timer.start(AUTO_SAVE_INTERVAL_SECONDS * 1000)

    def end_current_session(self):
        """Ends the current user session."""
        if self.current_session_id:
            self.session_logger.end_session(self.current_session_id)
            self.current_session_id = None
        
        self.session_timeout_timer.stop()
        self.auto_save_timer.stop()

    def check_session_timeout(self):
        """Checks if the session has timed out due to inactivity."""
        if not self.current_session_id or not self.last_activity:
            return
            
        minutes_inactive = (datetime.now() - self.last_activity).seconds / 60
        if minutes_inactive >= SESSION_TIMEOUT_MINUTES:
            self.end_current_session()
            self.session_timed_out.emit()

    def auto_save_session(self):
        """Periodically saves the session state."""
        if self.current_session_id:
            self.session_logger.save_session_state(self.current_session_id)

    def initialize(self):
        """
        Initializes the controller and its components.
        """
        # Placeholder for initialization logic
        pass

    def shutdown(self):
        """
        Cleans up resources before the application exits.
        """
        self.end_current_session()
        if self.response_thread and self.response_thread.isRunning():
            self.response_thread.stop()
            self.response_thread.wait() 
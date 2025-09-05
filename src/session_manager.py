#!/usr/bin/env python3
"""
Sunflower AI Professional System - Session Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Manages learning sessions, tracks interactions, and provides
comprehensive monitoring for parent review.
"""

import os
import sys
import json
import uuid
import sqlite3
import hashlib
import logging
import threading
import queue
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ARCHIVED = "archived"


class InteractionType(Enum):
    """Types of interactions"""
    QUESTION = "question"
    ANSWER = "answer"
    EXPLANATION = "explanation"
    EXERCISE = "exercise"
    QUIZ = "quiz"
    FEEDBACK = "feedback"
    HELP = "help"
    SYSTEM = "system"


class Subject(Enum):
    """STEM subjects"""
    SCIENCE = "science"
    TECHNOLOGY = "technology"
    ENGINEERING = "engineering"
    MATHEMATICS = "mathematics"
    GENERAL = "general"


@dataclass
class Interaction:
    """Single interaction record"""
    id: str
    timestamp: str
    type: str
    user_input: str
    ai_response: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    safety_triggered: bool = False
    safety_reason: Optional[str] = None
    response_time_ms: int = 0
    tokens_used: int = 0
    educational_value: float = 0.0  # 0-1 score
    flagged: bool = False
    parent_notes: Optional[str] = None


@dataclass
class LearningMetrics:
    """Learning metrics for a session"""
    questions_asked: int = 0
    correct_answers: int = 0
    topics_explored: List[str] = field(default_factory=list)
    concepts_learned: List[str] = field(default_factory=list)
    engagement_score: float = 0.0
    comprehension_score: float = 0.0
    progress_score: float = 0.0
    time_on_task: timedelta = timedelta()


@dataclass
class Session:
    """Learning session"""
    id: str
    child_id: str
    child_name: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[timedelta] = None
    state: str = SessionState.INITIALIZING.value
    interactions: List[Interaction] = field(default_factory=list)
    subjects_covered: List[str] = field(default_factory=list)
    topics_covered: List[str] = field(default_factory=list)
    safety_incidents: int = 0
    content_filtered_count: int = 0
    total_interactions: int = 0
    questions_asked: int = 0
    learning_metrics: Optional[LearningMetrics] = None
    parent_reviewed: bool = False
    parent_review_date: Optional[str] = None
    parent_notes: Optional[str] = None
    model_used: str = ""
    hardware_tier: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert timedelta to seconds for storage
        if self.duration:
            data['duration'] = self.duration.total_seconds()
        if self.learning_metrics:
            metrics = asdict(self.learning_metrics)
            if metrics.get('time_on_task'):
                metrics['time_on_task'] = metrics['time_on_task'].total_seconds()
            data['learning_metrics'] = metrics
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        """Create from dictionary"""
        # Convert duration from seconds
        if data.get('duration'):
            data['duration'] = timedelta(seconds=data['duration'])
        
        # Convert learning metrics
        if data.get('learning_metrics'):
            metrics = data['learning_metrics']
            if metrics.get('time_on_task'):
                metrics['time_on_task'] = timedelta(seconds=metrics['time_on_task'])
            data['learning_metrics'] = LearningMetrics(**metrics)
        
        # Convert interactions
        if data.get('interactions'):
            data['interactions'] = [
                Interaction(**i) if isinstance(i, dict) else i 
                for i in data['interactions']
            ]
        
        return cls(**data)


class SessionManager:
    """
    Manages learning sessions with comprehensive tracking and monitoring.
    All session data is stored on the USB partition for parent review.
    """
    
    def __init__(self, usb_path: Path, child_id: Optional[str] = None):
        """Initialize session manager"""
        self.usb_path = Path(usb_path)
        self.child_id = child_id
        
        # Paths
        self.sessions_dir = self.usb_path / "sessions"
        self.db_path = self.usb_path / "database" / "sessions.db"
        
        # Create directories
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Active session
        self.current_session: Optional[Session] = None
        self.session_lock = threading.RLock()
        
        # Interaction queue for async processing
        self.interaction_queue = queue.Queue()
        self.processing_thread = None
        self.stop_processing = threading.Event()
        
        # Initialize database
        self._init_database()
        
        # Start processing thread
        self._start_processing_thread()
        
        # Session monitoring
        self.last_interaction_time = None
        self.inactivity_timeout = timedelta(minutes=15)
        
        logger.info(f"Session manager initialized - Sessions directory: {self.sessions_dir}")
    
    def _init_database(self):
        """Initialize sessions database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    child_id TEXT NOT NULL,
                    child_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL,
                    state TEXT NOT NULL,
                    subjects_covered TEXT,
                    topics_covered TEXT,
                    safety_incidents INTEGER DEFAULT 0,
                    content_filtered_count INTEGER DEFAULT 0,
                    total_interactions INTEGER DEFAULT 0,
                    questions_asked INTEGER DEFAULT 0,
                    parent_reviewed INTEGER DEFAULT 0,
                    parent_review_date TEXT,
                    parent_notes TEXT,
                    model_used TEXT,
                    hardware_tier TEXT,
                    learning_metrics TEXT
                )
            """)
            
            # Interactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    subject TEXT,
                    topic TEXT,
                    safety_triggered INTEGER DEFAULT 0,
                    safety_reason TEXT,
                    response_time_ms INTEGER DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    educational_value REAL DEFAULT 0,
                    flagged INTEGER DEFAULT 0,
                    parent_notes TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_child ON sessions (child_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_time ON sessions (start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interaction_session ON interactions (session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interaction_time ON interactions (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flagged ON interactions (flagged)")
            
            conn.commit()
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _start_processing_thread(self):
        """Start background processing thread"""
        self.processing_thread = threading.Thread(target=self._process_interactions, daemon=True)
        self.processing_thread.start()
    
    def _process_interactions(self):
        """Process interactions in background"""
        while not self.stop_processing.is_set():
            try:
                # Get interaction from queue (timeout to check stop flag)
                interaction = self.interaction_queue.get(timeout=1)
                
                # Save to database
                self._save_interaction(interaction)
                
                # Update session metrics
                self._update_session_metrics()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing interaction: {e}")
    
    def start_session(self, child_id: str, child_name: str, model: str = "", 
                     hardware_tier: str = "") -> str:
        """Start a new learning session"""
        with self.session_lock:
            # End any existing session
            if self.current_session:
                self.end_session("new_session_started")
            
            # Create new session
            session_id = str(uuid.uuid4())
            
            self.current_session = Session(
                id=session_id,
                child_id=child_id,
                child_name=child_name,
                start_time=datetime.now().isoformat(),
                state=SessionState.ACTIVE.value,
                model_used=model,
                hardware_tier=hardware_tier,
                learning_metrics=LearningMetrics()
            )
            
            # Save to database
            self._save_session()
            
            # Update last interaction time
            self.last_interaction_time = datetime.now()
            
            logger.info(f"Started session {session_id} for child {child_name} ({child_id})")
            
            return session_id
    
    def end_session(self, reason: str = "normal") -> Optional[Session]:
        """End current session"""
        with self.session_lock:
            if not self.current_session:
                return None
            
            # Update session
            self.current_session.end_time = datetime.now().isoformat()
            
            # Calculate duration
            start = datetime.fromisoformat(self.current_session.start_time)
            end = datetime.fromisoformat(self.current_session.end_time)
            self.current_session.duration = end - start
            
            self.current_session.state = SessionState.ENDED.value
            
            # Final metrics update
            self._update_session_metrics()
            
            # Save completed session
            self._save_completed_session()
            
            logger.info(f"Session ended: {self.current_session.id} (reason: {reason})")
            
            session = self.current_session
            self.current_session = None
            
            return session
    
    def pause_session(self):
        """Pause current session"""
        with self.session_lock:
            if self.current_session and self.current_session.state == SessionState.ACTIVE.value:
                self.current_session.state = SessionState.PAUSED.value
                self._save_session()
                logger.info(f"Session paused: {self.current_session.id}")
    
    def resume_session(self):
        """Resume paused session"""
        with self.session_lock:
            if self.current_session and self.current_session.state == SessionState.PAUSED.value:
                self.current_session.state = SessionState.ACTIVE.value
                self.last_interaction_time = datetime.now()
                self._save_session()
                logger.info(f"Session resumed: {self.current_session.id}")
    
    def record_interaction(self, user_input: str, ai_response: str,
                          interaction_type: InteractionType = InteractionType.QUESTION,
                          subject: Optional[str] = None,
                          topic: Optional[str] = None,
                          safety_triggered: bool = False,
                          safety_reason: Optional[str] = None,
                          response_time_ms: int = 0,
                          tokens_used: int = 0):
        """Record an interaction in the current session"""
        if not self.current_session:
            logger.warning("No active session for interaction recording")
            return
        
        interaction = Interaction(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            type=interaction_type.value,
            user_input=user_input[:1000],  # Truncate for storage
            ai_response=ai_response[:5000],  # Truncate for storage
            subject=subject,
            topic=topic,
            safety_triggered=safety_triggered,
            safety_reason=safety_reason,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            educational_value=self._calculate_educational_value(ai_response, subject)
        )
        
        # Update session
        with self.session_lock:
            self.current_session.interactions.append(interaction)
            self.current_session.total_interactions += 1
            
            if interaction_type == InteractionType.QUESTION:
                self.current_session.questions_asked += 1
            
            if safety_triggered:
                self.current_session.content_filtered_count += 1
                self.current_session.safety_incidents += 1
            
            if subject and subject not in self.current_session.subjects_covered:
                self.current_session.subjects_covered.append(subject)
            
            if topic and topic not in self.current_session.topics_covered:
                self.current_session.topics_covered.append(topic)
            
            self.last_interaction_time = datetime.now()
        
        # Queue for async processing
        self.interaction_queue.put(interaction)
    
    def _calculate_educational_value(self, response: str, subject: Optional[str]) -> float:
        """Calculate educational value of response (0-1)"""
        score = 0.0
        
        # Check for educational keywords
        educational_keywords = [
            'learn', 'understand', 'explain', 'because', 'science',
            'math', 'calculate', 'observe', 'discover', 'explore',
            'experiment', 'hypothesis', 'theory', 'principle', 'concept'
        ]
        
        response_lower = response.lower()
        keyword_count = sum(1 for keyword in educational_keywords if keyword in response_lower)
        score += min(keyword_count * 0.1, 0.5)
        
        # Check for structure (questions, explanations)
        if '?' in response:
            score += 0.1  # Contains questions
        if 'because' in response_lower or 'therefore' in response_lower:
            score += 0.1  # Contains reasoning
        if len(response) > 100:
            score += 0.1  # Detailed response
        if subject:
            score += 0.2  # Has subject classification
        
        return min(score, 1.0)
    
    def _save_interaction(self, interaction: Interaction):
        """Save interaction to database"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO interactions (
                    id, session_id, timestamp, type, user_input, ai_response,
                    subject, topic, safety_triggered, safety_reason,
                    response_time_ms, tokens_used, educational_value, flagged
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                interaction.id,
                self.current_session.id if self.current_session else None,
                interaction.timestamp,
                interaction.type,
                interaction.user_input,
                interaction.ai_response,
                interaction.subject,
                interaction.topic,
                int(interaction.safety_triggered),
                interaction.safety_reason,
                interaction.response_time_ms,
                interaction.tokens_used,
                interaction.educational_value,
                int(interaction.flagged)
            ))
            
            conn.commit()
    
    def _save_session(self):
        """Save current session to database"""
        if not self.current_session:
            return
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute("SELECT id FROM sessions WHERE id = ?", (self.current_session.id,))
            exists = cursor.fetchone() is not None
            
            session_data = self.current_session.to_dict()
            
            if exists:
                # Update existing session
                cursor.execute("""
                    UPDATE sessions SET
                        end_time = ?, duration_seconds = ?, state = ?,
                        subjects_covered = ?, topics_covered = ?,
                        safety_incidents = ?, content_filtered_count = ?,
                        total_interactions = ?, questions_asked = ?,
                        learning_metrics = ?
                    WHERE id = ?
                """, (
                    session_data.get('end_time'),
                    session_data.get('duration'),
                    session_data['state'],
                    json.dumps(session_data.get('subjects_covered', [])),
                    json.dumps(session_data.get('topics_covered', [])),
                    session_data['safety_incidents'],
                    session_data['content_filtered_count'],
                    session_data['total_interactions'],
                    session_data['questions_asked'],
                    json.dumps(session_data.get('learning_metrics')),
                    self.current_session.id
                ))
            else:
                # Insert new session
                cursor.execute("""
                    INSERT INTO sessions (
                        id, child_id, child_name, start_time, end_time,
                        duration_seconds, state, subjects_covered, topics_covered,
                        safety_incidents, content_filtered_count, total_interactions,
                        questions_asked, model_used, hardware_tier, learning_metrics
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_session.id,
                    self.current_session.child_id,
                    self.current_session.child_name,
                    self.current_session.start_time,
                    session_data.get('end_time'),
                    session_data.get('duration'),
                    self.current_session.state,
                    json.dumps(self.current_session.subjects_covered),
                    json.dumps(self.current_session.topics_covered),
                    self.current_session.safety_incidents,
                    self.current_session.content_filtered_count,
                    self.current_session.total_interactions,
                    self.current_session.questions_asked,
                    self.current_session.model_used,
                    self.current_session.hardware_tier,
                    json.dumps(session_data.get('learning_metrics'))
                ))
            
            conn.commit()
    
    def _save_completed_session(self):
        """Save completed session with all data"""
        if not self.current_session:
            return
        
        # Save to database
        self._save_session()
        
        # Also save to JSON file for backup
        session_file = self.sessions_dir / f"session_{self.current_session.id}.json"
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_session.to_dict(), f, indent=2, default=str)
        
        logger.info(f"Saved completed session to: {session_file}")
    
    def _update_session_metrics(self):
        """Update learning metrics for current session"""
        if not self.current_session or not self.current_session.learning_metrics:
            return
        
        metrics = self.current_session.learning_metrics
        
        # Update basic counts
        metrics.questions_asked = self.current_session.questions_asked
        
        # Calculate engagement score based on interaction frequency
        if self.current_session.duration:
            interactions_per_minute = (
                self.current_session.total_interactions / 
                max(self.current_session.duration.total_seconds() / 60, 1)
            )
            metrics.engagement_score = min(interactions_per_minute / 2, 1.0)  # 2+ per minute = full engagement
        
        # Extract topics and concepts from interactions
        for interaction in self.current_session.interactions[-10:]:  # Check last 10 interactions
            if interaction.topic and interaction.topic not in metrics.topics_explored:
                metrics.topics_explored.append(interaction.topic)
        
        # Calculate progress score
        metrics.progress_score = min(len(metrics.topics_explored) / 10, 1.0)  # 10+ topics = full progress
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        # Check if it's the current session
        if self.current_session and self.current_session.id == session_id:
            return self.current_session
        
        # Load from database
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            
            if row:
                session_data = dict(row)
                
                # Parse JSON fields
                if session_data.get('subjects_covered'):
                    session_data['subjects_covered'] = json.loads(session_data['subjects_covered'])
                if session_data.get('topics_covered'):
                    session_data['topics_covered'] = json.loads(session_data['topics_covered'])
                if session_data.get('learning_metrics'):
                    session_data['learning_metrics'] = json.loads(session_data['learning_metrics'])
                
                # Load interactions
                cursor.execute("SELECT * FROM interactions WHERE session_id = ? ORDER BY timestamp", 
                             (session_id,))
                interactions = []
                for interaction_row in cursor.fetchall():
                    interactions.append(Interaction(**dict(interaction_row)))
                
                session_data['interactions'] = interactions
                
                return Session.from_dict(session_data)
        
        return None
    
    def get_child_sessions(self, child_id: str, limit: int = 50) -> List[Session]:
        """Get sessions for a specific child"""
        sessions = []
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE child_id = ? 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (child_id, limit))
            
            for row in cursor.fetchall():
                session_data = dict(row)
                
                # Parse JSON fields
                if session_data.get('subjects_covered'):
                    session_data['subjects_covered'] = json.loads(session_data['subjects_covered'])
                if session_data.get('topics_covered'):
                    session_data['topics_covered'] = json.loads(session_data['topics_covered'])
                if session_data.get('learning_metrics'):
                    session_data['learning_metrics'] = json.loads(session_data['learning_metrics'])
                
                sessions.append(Session.from_dict(session_data))
        
        return sessions
    
    def get_flagged_interactions(self, limit: int = 100) -> List[Interaction]:
        """Get flagged interactions for parent review"""
        interactions = []
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM interactions 
                WHERE flagged = 1 OR safety_triggered = 1
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            for row in cursor.fetchall():
                interactions.append(Interaction(**dict(row)))
        
        return interactions
    
    def flag_interaction(self, interaction_id: str, reason: str = ""):
        """Flag an interaction for parent review"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE interactions 
                SET flagged = 1, parent_notes = ?
                WHERE id = ?
            """, (reason, interaction_id))
            
            conn.commit()
    
    def get_summary(self, child_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            if child_id:
                # Child-specific summary
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        SUM(duration_seconds) as total_time,
                        SUM(total_interactions) as total_interactions,
                        SUM(questions_asked) as total_questions,
                        SUM(safety_incidents) as total_safety_incidents
                    FROM sessions 
                    WHERE child_id = ?
                """, (child_id,))
            else:
                # Overall summary
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        SUM(duration_seconds) as total_time,
                        SUM(total_interactions) as total_interactions,
                        SUM(questions_asked) as total_questions,
                        SUM(safety_incidents) as total_safety_incidents
                    FROM sessions
                """)
            
            row = cursor.fetchone()
            summary = dict(row) if row else {}
            
            # Get recent sessions
            cursor.execute("""
                SELECT id, child_name, start_time, duration_seconds, total_interactions
                FROM sessions 
                ORDER BY start_time DESC 
                LIMIT 10
            """)
            
            recent_sessions = [dict(row) for row in cursor.fetchall()]
            
            # Get today's activity
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(*) as sessions_today
                FROM sessions 
                WHERE DATE(start_time) = DATE(?)
            """, (today,))
            
            sessions_today = cursor.fetchone()[0]
            
            return {
                "summary": summary,
                "recent_sessions": recent_sessions,
                "sessions_today": sessions_today
            }
    
    def mark_reviewed(self, session_id: str, parent_notes: Optional[str] = None):
        """Mark session as reviewed by parent"""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sessions 
                SET parent_reviewed = 1, 
                    parent_review_date = ?,
                    parent_notes = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), parent_notes, session_id))
            
            conn.commit()
        
        logger.info(f"Session marked as reviewed: {session_id}")
    
    def check_inactivity(self):
        """Check for session inactivity"""
        if not self.current_session or not self.last_interaction_time:
            return
        
        if self.current_session.state != SessionState.ACTIVE.value:
            return
        
        # Check if session has been inactive
        if datetime.now() - self.last_interaction_time > self.inactivity_timeout:
            logger.info(f"Session {self.current_session.id} inactive - auto-pausing")
            self.pause_session()
    
    def export_session_data(self, session_id: str, format: str = "json") -> Path:
        """Export session data for analysis"""
        session = self.get_session(session_id)
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        export_dir = self.usb_path / "exports"
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            export_file = export_dir / f"session_{session_id}_{timestamp}.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, default=str)
        
        elif format == "csv":
            import csv
            export_file = export_dir / f"session_{session_id}_{timestamp}.csv"
            
            with open(export_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['Timestamp', 'Type', 'User Input', 'AI Response', 
                               'Subject', 'Topic', 'Safety Triggered', 'Educational Value'])
                
                # Write interactions
                for interaction in session.interactions:
                    writer.writerow([
                        interaction.timestamp,
                        interaction.type,
                        interaction.user_input,
                        interaction.ai_response[:200],  # Truncate for CSV
                        interaction.subject or '',
                        interaction.topic or '',
                        'Yes' if interaction.safety_triggered else 'No',
                        f"{interaction.educational_value:.2f}"
                    ])
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Session exported to: {export_file}")
        return export_file
    
    def cleanup_old_sessions(self, days: int = 90):
        """Clean up old sessions"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get sessions to delete
            cursor.execute("""
                SELECT id FROM sessions 
                WHERE start_time < ? AND parent_reviewed = 1
            """, (cutoff_date,))
            
            sessions_to_delete = [row[0] for row in cursor.fetchall()]
            
            if sessions_to_delete:
                # Delete sessions and their interactions (cascade)
                cursor.execute("""
                    DELETE FROM sessions 
                    WHERE id IN ({})
                """.format(','.join('?' * len(sessions_to_delete))), sessions_to_delete)
                
                conn.commit()
                
                logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")
        
        # Clean up old JSON files
        for session_file in self.sessions_dir.glob("session_*.json"):
            if session_file.stat().st_mtime < time.time() - (days * 86400):
                session_file.unlink()
    
    def shutdown(self):
        """Shutdown session manager"""
        # Stop processing thread
        self.stop_processing.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        # End current session if active
        if self.current_session:
            self.end_session("shutdown")
        
        logger.info("Session manager shutdown complete")


# Testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test session manager
        manager = SessionManager(Path(tmpdir))
        
        # Start a session
        session_id = manager.start_session(
            child_id="test_child_123",
            child_name="Test Child",
            model="llama3.2:1b",
            hardware_tier="standard"
        )
        
        print(f"Started session: {session_id}")
        
        # Record some interactions
        manager.record_interaction(
            "What is photosynthesis?",
            "Photosynthesis is the process plants use to make food from sunlight...",
            InteractionType.QUESTION,
            subject="science",
            topic="biology"
        )
        
        time.sleep(1)
        
        manager.record_interaction(
            "Can you explain it simpler?",
            "Sure! Plants eat sunlight and turn it into food, just like you eat lunch...",
            InteractionType.EXPLANATION,
            subject="science",
            topic="biology"
        )
        
        # Get summary
        summary = manager.get_summary()
        print(f"Summary: {summary}")
        
        # End session
        session = manager.end_session()
        print(f"Session ended - Duration: {session.duration}")
        
        # Export data
        export_path = manager.export_session_data(session_id, "json")
        print(f"Exported to: {export_path}")
        
        # Shutdown
        manager.shutdown()

"""
Sunflower AI Professional System - Session Manager
Version: 6.2
Copyright (c) 2025 Sunflower AI

Manages learning sessions including time tracking, content monitoring,
safety enforcement, and parent reporting. All session data is logged
for parent review.
"""

import json
import time
import uuid
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field, asdict
from enum import Enum
from queue import Queue, Empty

from . import ProfileError

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states"""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    TIME_LIMIT_WARNING = "time_limit_warning"
    TIME_LIMIT_REACHED = "time_limit_reached"
    BREAK_REQUIRED = "break_required"
    ENDED = "ended"
    EMERGENCY_STOP = "emergency_stop"


class InteractionType(Enum):
    """Types of interactions"""
    QUESTION = "question"
    ANSWER = "answer"
    EXPLANATION = "explanation"
    QUIZ = "quiz"
    EXERCISE = "exercise"
    HELP = "help"
    SAFETY_REDIRECT = "safety_redirect"


class SafetyLevel(Enum):
    """Safety incident levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Interaction:
    """Single interaction within a session"""
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


@dataclass
class SafetyIncident:
    """Safety incident record"""
    id: str
    timestamp: str
    level: str
    trigger: str
    user_input: str
    action_taken: str
    parent_notified: bool = False
    resolved: bool = False
    notes: Optional[str] = None


@dataclass
class LearningSession:
    """Complete learning session record"""
    id: str
    child_id: str
    child_name: str
    start_time: str
    end_time: Optional[str] = None
    duration_minutes: int = 0
    state: str = "idle"
    
    # Content
    subjects_covered: List[str] = field(default_factory=list)
    topics_covered: List[str] = field(default_factory=list)
    interactions: List[Interaction] = field(default_factory=list)
    
    # Safety
    safety_incidents: List[SafetyIncident] = field(default_factory=list)
    content_filtered_count: int = 0
    
    # Metrics
    total_interactions: int = 0
    questions_asked: int = 0
    exercises_completed: int = 0
    quiz_scores: List[float] = field(default_factory=list)
    average_response_time_ms: int = 0
    engagement_score: float = 0.0
    
    # Limits
    time_limit_minutes: int = 60
    break_interval_minutes: int = 30
    time_warnings_shown: int = 0
    
    # Parent review
    parent_notes: Optional[str] = None
    parent_reviewed: bool = False
    parent_review_date: Optional[str] = None


class SessionManager:
    """
    Manages active learning sessions with comprehensive tracking,
    safety monitoring, and time limit enforcement.
    """
    
    WARNING_THRESHOLD_MINUTES = 5  # Warn 5 minutes before time limit
    BREAK_DURATION_MINUTES = 10    # Minimum break duration
    MAX_SESSION_EXTENSION_MINUTES = 30  # Maximum extension allowed
    
    def __init__(self, usb_path: Optional[Path] = None):
        """Initialize session manager"""
        self.usb_path = usb_path or self._find_usb_path()
        self.sessions_dir = self.usb_path / "sessions" if self.usb_path else None
        self.conversations_dir = self.usb_path / "conversations" if self.usb_path else None
        
        # Active session
        self.current_session: Optional[LearningSession] = None
        self.session_thread: Optional[threading.Thread] = None
        self.session_lock = threading.Lock()
        
        # Time tracking
        self.session_start_time: Optional[datetime] = None
        self.last_interaction_time: Optional[datetime] = None
        self.total_pause_time: timedelta = timedelta()
        self.pause_start_time: Optional[datetime] = None
        
        # Callbacks
        self.time_warning_callback: Optional[Callable] = None
        self.time_limit_callback: Optional[Callable] = None
        self.break_required_callback: Optional[Callable] = None
        self.safety_alert_callback: Optional[Callable] = None
        
        # Message queue for async processing
        self.message_queue = Queue()
        self.processing_thread: Optional[threading.Thread] = None
        self._stop_processing = threading.Event()
        
        # Initialize storage
        self._initialize_storage()
        
        # Statistics cache
        self._stats_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        
        logger.info(f"Session manager initialized - Sessions directory: {self.sessions_dir}")
    
    def _find_usb_path(self) -> Optional[Path]:
        """Find USB data partition"""
        try:
            from .partition_manager import PartitionManager
            pm = PartitionManager()
            return pm.find_usb_partition()
        except Exception as e:
            logger.warning(f"Could not find USB partition: {e}")
            dev_path = Path(__file__).parent.parent / "data"
            dev_path.mkdir(parents=True, exist_ok=True)
            return dev_path
    
    def _initialize_storage(self):
        """Initialize session storage directories"""
        if not self.sessions_dir:
            logger.warning("No sessions directory available")
            return
        
        # Create directory structure
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (self.sessions_dir / "active").mkdir(exist_ok=True)
        (self.sessions_dir / "completed").mkdir(exist_ok=True)
        (self.sessions_dir / "safety_logs").mkdir(exist_ok=True)
        (self.conversations_dir / ".encrypted").mkdir(exist_ok=True)
    
    def start_session(self, child_id: str, child_name: str, 
                     time_limit_minutes: int = 60,
                     break_interval_minutes: int = 30) -> LearningSession:
        """Start new learning session"""
        with self.session_lock:
            if self.current_session and self.current_session.state == SessionState.ACTIVE.value:
                raise RuntimeError("A session is already active")
            
            # Create new session
            self.current_session = LearningSession(
                id=str(uuid.uuid4()),
                child_id=child_id,
                child_name=child_name,
                start_time=datetime.now().isoformat(),
                state=SessionState.ACTIVE.value,
                time_limit_minutes=time_limit_minutes,
                break_interval_minutes=break_interval_minutes
            )
            
            # Initialize tracking
            self.session_start_time = datetime.now()
            self.last_interaction_time = datetime.now()
            self.total_pause_time = timedelta()
            
            # Start monitoring thread
            self._stop_processing.clear()
            self.session_thread = threading.Thread(target=self._monitor_session, daemon=True)
            self.session_thread.start()
            
            # Start processing thread
            self.processing_thread = threading.Thread(target=self._process_messages, daemon=True)
            self.processing_thread.start()
            
            # Save initial session state
            self._save_active_session()
            
            logger.info(f"Started session for {child_name} (ID: {self.current_session.id})")
            
            return self.current_session
    
    def _monitor_session(self):
        """Monitor session for time limits and breaks"""
        while not self._stop_processing.is_set():
            if not self.current_session or self.current_session.state != SessionState.ACTIVE.value:
                time.sleep(1)
                continue
            
            with self.session_lock:
                if self.session_start_time:
                    # Calculate elapsed time
                    elapsed = datetime.now() - self.session_start_time - self.total_pause_time
                    elapsed_minutes = elapsed.total_seconds() / 60
                    
                    # Check time limit
                    time_limit = self.current_session.time_limit_minutes
                    remaining_minutes = time_limit - elapsed_minutes
                    
                    # Time limit reached
                    if remaining_minutes <= 0:
                        self.current_session.state = SessionState.TIME_LIMIT_REACHED.value
                        logger.warning(f"Time limit reached for session {self.current_session.id}")
                        
                        if self.time_limit_callback:
                            self.time_limit_callback(self.current_session)
                    
                    # Warning threshold
                    elif remaining_minutes <= self.WARNING_THRESHOLD_MINUTES:
                        if self.current_session.time_warnings_shown == 0:
                            self.current_session.state = SessionState.TIME_LIMIT_WARNING.value
                            self.current_session.time_warnings_shown += 1
                            logger.info(f"Time warning: {remaining_minutes:.1f} minutes remaining")
                            
                            if self.time_warning_callback:
                                self.time_warning_callback(remaining_minutes)
                    
                    # Check break interval
                    break_interval = self.current_session.break_interval_minutes
                    if elapsed_minutes >= break_interval:
                        last_break = elapsed_minutes // break_interval
                        if last_break > self.current_session.time_warnings_shown - 1:
                            logger.info(f"Break recommended after {elapsed_minutes:.0f} minutes")
                            
                            if self.break_required_callback:
                                self.break_required_callback(self.current_session)
            
            time.sleep(10)  # Check every 10 seconds
    
    def _process_messages(self):
        """Process queued messages asynchronously"""
        while not self._stop_processing.is_set():
            try:
                message = self.message_queue.get(timeout=1)
                if message:
                    self._handle_message(message)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    def _handle_message(self, message: Dict[str, Any]):
        """Handle queued message"""
        msg_type = message.get("type")
        
        if msg_type == "interaction":
            self._save_interaction(message["data"])
        elif msg_type == "safety_incident":
            self._save_safety_incident(message["data"])
        elif msg_type == "update_metrics":
            self._update_session_metrics()
    
    def pause_session(self):
        """Pause current session"""
        with self.session_lock:
            if not self.current_session:
                raise RuntimeError("No active session")
            
            if self.current_session.state == SessionState.ACTIVE.value:
                self.current_session.state = SessionState.PAUSED.value
                self.pause_start_time = datetime.now()
                
                logger.info(f"Session paused: {self.current_session.id}")
    
    def resume_session(self):
        """Resume paused session"""
        with self.session_lock:
            if not self.current_session:
                raise RuntimeError("No active session")
            
            if self.current_session.state == SessionState.PAUSED.value:
                self.current_session.state = SessionState.ACTIVE.value
                
                if self.pause_start_time:
                    pause_duration = datetime.now() - self.pause_start_time
                    self.total_pause_time += pause_duration
                    self.pause_start_time = None
                
                logger.info(f"Session resumed: {self.current_session.id}")
    
    def end_session(self, reason: str = "normal") -> LearningSession:
        """End current session"""
        with self.session_lock:
            if not self.current_session:
                raise RuntimeError("No active session")
            
            # Stop monitoring
            self._stop_processing.set()
            
            # Update session
            self.current_session.end_time = datetime.now().isoformat()
            
            if self.session_start_time:
                duration = datetime.now() - self.session_start_time - self.total_pause_time
                self.current_session.duration_minutes = int(duration.total_seconds() / 60)
            
            if reason == "emergency":
                self.current_session.state = SessionState.EMERGENCY_STOP.value
            else:
                self.current_session.state = SessionState.ENDED.value
            
            # Final metrics update
            self._update_session_metrics()
            
            # Save completed session
            self._save_completed_session()
            
            logger.info(f"Session ended: {self.current_session.id} (reason: {reason})")
            
            session = self.current_session
            self.current_session = None
            
            return session
    
    def record_interaction(self, user_input: str, ai_response: str,
                          interaction_type: InteractionType,
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
            tokens_used=tokens_used
        )
        
        # Update session
        with self.session_lock:
            self.current_session.interactions.append(interaction)
            self.current_session.total_interactions += 1
            
            if interaction_type == InteractionType.QUESTION:
                self.current_session.questions_asked += 1
            
            if safety_triggered:
                self.current_session.content_filtered_count += 1
            
            if subject and subject not in self.current_session.subjects_covered:
                self.current_session.subjects_covered.append(subject)
            
            if topic and topic not in self.current_session.topics_covered:
                self.current_session.topics_covered.append(topic)
            
            self.last_interaction_time = datetime.now()
        
        # Queue for async processing
        self.message_queue.put({
            "type": "interaction",
            "data": interaction
        })
        
        logger.debug(f"Recorded {interaction_type.value} interaction")
    
    def record_safety_incident(self, level: SafetyLevel, trigger: str,
                              user_input: str, action_taken: str,
                              notify_parent: bool = False):
        """Record a safety incident"""
        incident = SafetyIncident(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            level=level.value,
            trigger=trigger,
            user_input=user_input[:500],  # Truncate
            action_taken=action_taken,
            parent_notified=notify_parent
        )
        
        with self.session_lock:
            if self.current_session:
                self.current_session.safety_incidents.append(incident)
        
        # Save immediately for safety logs
        self._save_safety_incident(incident)
        
        # Notify parent if required
        if notify_parent and self.safety_alert_callback:
            self.safety_alert_callback(incident)
        
        logger.warning(f"Safety incident recorded: {level.value} - {trigger}")
    
    def record_quiz_score(self, score: float, subject: str, topic: str):
        """Record quiz score"""
        if not self.current_session:
            return
        
        with self.session_lock:
            self.current_session.quiz_scores.append(score)
            self.current_session.exercises_completed += 1
        
        logger.info(f"Quiz score recorded: {score:.1f}% for {subject}/{topic}")
    
    def extend_session(self, additional_minutes: int) -> bool:
        """Extend session time limit (requires parent approval)"""
        if not self.current_session:
            return False
        
        if additional_minutes > self.MAX_SESSION_EXTENSION_MINUTES:
            logger.warning(f"Extension request exceeds maximum: {additional_minutes} minutes")
            return False
        
        with self.session_lock:
            self.current_session.time_limit_minutes += additional_minutes
            self.current_session.state = SessionState.ACTIVE.value
            self.current_session.time_warnings_shown = 0
        
        logger.info(f"Session extended by {additional_minutes} minutes")
        return True
    
    def get_session_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed session statistics"""
        session = self.current_session if session_id is None else self._load_session(session_id)
        
        if not session:
            return {}
        
        # Calculate metrics
        avg_response_time = 0
        if session.interactions:
            response_times = [i.response_time_ms for i in session.interactions if i.response_time_ms > 0]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        avg_quiz_score = sum(session.quiz_scores) / len(session.quiz_scores) if session.quiz_scores else 0
        
        # Calculate engagement score (0-100)
        engagement_factors = []
        
        # Interaction frequency (interactions per minute)
        if session.duration_minutes > 0:
            interaction_rate = session.total_interactions / session.duration_minutes
            engagement_factors.append(min(100, interaction_rate * 10))
        
        # Question ratio
        if session.total_interactions > 0:
            question_ratio = session.questions_asked / session.total_interactions
            engagement_factors.append(question_ratio * 100)
        
        # Subject diversity
        subject_diversity = min(100, len(session.subjects_covered) * 20)
        engagement_factors.append(subject_diversity)
        
        # Quiz participation
        quiz_participation = min(100, session.exercises_completed * 10)
        engagement_factors.append(quiz_participation)
        
        engagement_score = sum(engagement_factors) / len(engagement_factors) if engagement_factors else 0
        
        stats = {
            "session_id": session.id,
            "child_name": session.child_name,
            "date": session.start_time,
            "duration_minutes": session.duration_minutes,
            "state": session.state,
            "subjects_covered": session.subjects_covered,
            "topics_covered": session.topics_covered,
            "total_interactions": session.total_interactions,
            "questions_asked": session.questions_asked,
            "exercises_completed": session.exercises_completed,
            "content_filtered": session.content_filtered_count,
            "safety_incidents": len(session.safety_incidents),
            "average_response_time_ms": int(avg_response_time),
            "average_quiz_score": round(avg_quiz_score, 1),
            "engagement_score": round(engagement_score, 1),
            "time_limit_minutes": session.time_limit_minutes,
            "parent_reviewed": session.parent_reviewed
        }
        
        return stats
    
    def get_child_history(self, child_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get session history for a child"""
        if not self.sessions_dir:
            return []
        
        history = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Check completed sessions
        completed_dir = self.sessions_dir / "completed"
        for session_file in completed_dir.glob(f"*_{child_id}_*.json"):
            try:
                session = self._load_session_file(session_file)
                if session:
                    session_date = datetime.fromisoformat(session.start_time)
                    if session_date >= cutoff_date:
                        stats = self.get_session_statistics(session.id)
                        history.append(stats)
            except Exception as e:
                logger.error(f"Error loading session {session_file}: {e}")
        
        # Sort by date
        history.sort(key=lambda x: x["date"], reverse=True)
        
        return history
    
    def get_daily_summary(self, child_id: str, date: Optional[date] = None) -> Dict[str, Any]:
        """Get daily learning summary for a child"""
        target_date = date or datetime.now().date()
        
        sessions_today = []
        total_time = 0
        total_interactions = 0
        subjects = set()
        topics = set()
        safety_incidents = []
        
        # Find sessions for the date
        history = self.get_child_history(child_id, days=1)
        
        for session_stats in history:
            session_date = datetime.fromisoformat(session_stats["date"]).date()
            if session_date == target_date:
                sessions_today.append(session_stats)
                total_time += session_stats["duration_minutes"]
                total_interactions += session_stats["total_interactions"]
                subjects.update(session_stats["subjects_covered"])
                topics.update(session_stats["topics_covered"])
        
        summary = {
            "date": target_date.isoformat(),
            "child_id": child_id,
            "sessions_count": len(sessions_today),
            "total_time_minutes": total_time,
            "total_interactions": total_interactions,
            "subjects_studied": list(subjects),
            "topics_covered": list(topics),
            "average_engagement": sum(s["engagement_score"] for s in sessions_today) / len(sessions_today) if sessions_today else 0,
            "safety_incidents": len(safety_incidents),
            "sessions": sessions_today
        }
        
        return summary
    
    def mark_reviewed(self, session_id: str, parent_notes: Optional[str] = None):
        """Mark session as reviewed by parent"""
        session = self._load_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session.parent_reviewed = True
        session.parent_review_date = datetime.now().isoformat()
        if parent_notes:
            session.parent_notes = parent_notes
        
        # Save updated session
        self._save_session(session)
        
        logger.info(f"Session marked as reviewed: {session_id}")
    
    def _save_active_session(self):
        """Save active session state"""
        if not self.current_session or not self.sessions_dir:
            return
        
        active_dir = self.sessions_dir / "active"
        session_file = active_dir / f"session_{self.current_session.id}.json"
        
        try:
            session_data = asdict(self.current_session)
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save active session: {e}")
    
    def _save_completed_session(self):
        """Save completed session"""
        if not self.current_session or not self.sessions_dir:
            return
        
        # Move from active to completed
        active_file = self.sessions_dir / "active" / f"session_{self.current_session.id}.json"
        completed_dir = self.sessions_dir / "completed"
        
        # Create filename with child ID for easier lookup
        filename = f"session_{self.current_session.id}_{self.current_session.child_id}_{datetime.now().strftime('%Y%m%d')}.json"
        completed_file = completed_dir / filename
        
        try:
            session_data = asdict(self.current_session)
            with open(completed_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            # Remove active file
            if active_file.exists():
                active_file.unlink()
            
            logger.info(f"Saved completed session: {completed_file}")
        except Exception as e:
            logger.error(f"Failed to save completed session: {e}")
    
    def _save_interaction(self, interaction: Interaction):
        """Save interaction to conversation log"""
        if not self.conversations_dir or not self.current_session:
            return
        
        conv_file = self.conversations_dir / f"{self.current_session.id}.jsonl"
        
        try:
            with open(conv_file, 'a', encoding='utf-8') as f:
                json.dump(asdict(interaction), f, default=str)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")
    
    def _save_safety_incident(self, incident: SafetyIncident):
        """Save safety incident to log"""
        if not self.sessions_dir:
            return
        
        safety_dir = self.sessions_dir / "safety_logs"
        log_file = safety_dir / f"safety_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump(asdict(incident), f, default=str)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to save safety incident: {e}")
    
    def _save_session(self, session: LearningSession):
        """Save session to disk"""
        if not self.sessions_dir:
            return
        
        # Determine directory based on state
        if session.state in [SessionState.ENDED.value, SessionState.EMERGENCY_STOP.value]:
            session_dir = self.sessions_dir / "completed"
        else:
            session_dir = self.sessions_dir / "active"
        
        session_file = session_dir / f"session_{session.id}.json"
        
        try:
            session_data = asdict(session)
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _load_session(self, session_id: str) -> Optional[LearningSession]:
        """Load session from disk"""
        if not self.sessions_dir:
            return None
        
        # Check active sessions
        active_file = self.sessions_dir / "active" / f"session_{session_id}.json"
        if active_file.exists():
            return self._load_session_file(active_file)
        
        # Check completed sessions
        completed_dir = self.sessions_dir / "completed"
        for session_file in completed_dir.glob(f"session_{session_id}_*.json"):
            return self._load_session_file(session_file)
        
        return None
    
    def _load_session_file(self, session_file: Path) -> Optional[LearningSession]:
        """Load session from file"""
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct objects
            interactions = [Interaction(**i) for i in data.get("interactions", [])]
            incidents = [SafetyIncident(**s) for s in data.get("safety_incidents", [])]
            
            session = LearningSession(
                id=data["id"],
                child_id=data["child_id"],
                child_name=data["child_name"],
                start_time=data["start_time"],
                end_time=data.get("end_time"),
                duration_minutes=data.get("duration_minutes", 0),
                state=data.get("state", "ended"),
                subjects_covered=data.get("subjects_covered", []),
                topics_covered=data.get("topics_covered", []),
                interactions=interactions,
                safety_incidents=incidents,
                total_interactions=data.get("total_interactions", 0),
                questions_asked=data.get("questions_asked", 0),
                exercises_completed=data.get("exercises_completed", 0),
                quiz_scores=data.get("quiz_scores", []),
                average_response_time_ms=data.get("average_response_time_ms", 0),
                engagement_score=data.get("engagement_score", 0.0),
                time_limit_minutes=data.get("time_limit_minutes", 60),
                parent_reviewed=data.get("parent_reviewed", False),
                parent_notes=data.get("parent_notes")
            )
            
            return session
        except Exception as e:
            logger.error(f"Failed to load session file {session_file}: {e}")
            return None
    
    def _update_session_metrics(self):
        """Update session metrics"""
        if not self.current_session:
            return
        
        with self.session_lock:
            # Calculate average response time
            if self.current_session.interactions:
                response_times = [i.response_time_ms for i in self.current_session.interactions if i.response_time_ms > 0]
                if response_times:
                    self.current_session.average_response_time_ms = int(sum(response_times) / len(response_times))
            
            # Calculate engagement score
            stats = self.get_session_statistics()
            self.current_session.engagement_score = stats.get("engagement_score", 0.0)
        
        # Queue for save
        self._save_active_session()

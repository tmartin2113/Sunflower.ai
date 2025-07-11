#!/usr/bin/env python3
"""
Session Logger for Sunflower AI
Tracks all child interactions, questions, and responses
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import uuid
from dataclasses import dataclass, asdict
from collections import defaultdict

from .profile_storage import ProfileStorage


@dataclass
class SessionEntry:
    """Single interaction entry in a session"""
    timestamp: str
    entry_type: str  # 'question', 'response', 'safety_alert', 'system'
    content: str
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        if data['metadata'] is None:
            data['metadata'] = {}
        return data


class SessionLogger:
    """Logs and manages all AI session interactions"""
    
    def __init__(self, app_dir: Optional[Path] = None):
        """Initialize session logger"""
        self.app_dir = app_dir or (Path.home() / '.sunflower-ai')
        self.sessions_dir = self.app_dir / 'sessions'
        self.sessions_dir.mkdir(exist_ok=True, parents=True)
        
        # Storage handler for encrypted sessions
        self.storage = ProfileStorage(self.app_dir)
        
        # Active sessions
        self.active_sessions = {}
        
        # Session index for quick lookups
        self.session_index_file = self.sessions_dir / 'session_index.json'
        self.load_session_index()
    
    def save_session_state(self, session_id: str):
        """Saves the current state of an active session to the encrypted store."""
        if session_id in self.active_sessions:
            self.storage.save_session(session_id, self.active_sessions[session_id])

    def load_session_index(self):
        """Load session index for quick lookups"""
        if self.session_index_file.exists():
            try:
                with open(self.session_index_file, 'r') as f:
                    self.session_index = json.load(f)
            except:
                self.session_index = self._get_default_index()
        else:
            self.session_index = self._get_default_index()
    
    def save_session_index(self):
        """Save session index"""
        try:
            with open(self.session_index_file, 'w') as f:
                json.dump(self.session_index, f, indent=2)
        except Exception as e:
            print(f"Error saving session index: {e}")
    
    def _get_default_index(self) -> Dict:
        """Get default session index structure"""
        return {
            "version": "1.0",
            "sessions_by_child": {},  # child_id -> [session_ids]
            "sessions_by_date": {},   # date -> [session_ids]
            "total_sessions": 0
        }
    
    def start_session(self, child_id: str, child_name: str, 
                     child_age: int, context: Optional[Dict] = None) -> str:
        """Start a new session for a child"""
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        session_data = {
            "session_id": session_id,
            "child_id": child_id,
            "child_name": child_name,
            "child_age": child_age,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_minutes": 0,
            "context": context or {},
            "entries": [],
            "summary": {
                "total_questions": 0,
                "total_responses": 0,
                "topics_explored": [],
                "new_vocabulary": [],
                "concepts_covered": [],
                "safety_incidents": 0,
                "parent_alerts": []
            }
        }
        
        # Store in active sessions
        self.active_sessions[session_id] = session_data
        
        # Add to index
        if child_id not in self.session_index['sessions_by_child']:
            self.session_index['sessions_by_child'][child_id] = []
        
        today = date.today().isoformat()
        if today not in self.session_index['sessions_by_date']:
            self.session_index['sessions_by_date'][today] = []
        
        # Log session start
        self.add_entry(session_id, SessionEntry(
            timestamp=datetime.now().isoformat(),
            entry_type="system",
            content=f"Session started for {child_name} (age {child_age})",
            metadata={"event": "session_start"}
        ))
        
        return session_id
    
    def end_session(self, session_id: str) -> bool:
        """End an active session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        
        # Calculate duration
        start_time = datetime.fromisoformat(session['start_time'])
        end_time = datetime.now()
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        session['end_time'] = end_time.isoformat()
        session['duration_minutes'] = duration_minutes
        
        # Log session end
        self.add_entry(session_id, SessionEntry(
            timestamp=end_time.isoformat(),
            entry_type="system",
            content=f"Session ended after {duration_minutes} minutes",
            metadata={"event": "session_end"}
        ))
        
        # Save to encrypted storage
        self.storage.save_session(session_id, session)
        
        # Update index
        child_id = session['child_id']
        today = date.today().isoformat()
        
        if session_id not in self.session_index['sessions_by_child'][child_id]:
            self.session_index['sessions_by_child'][child_id].append(session_id)
        
        if session_id not in self.session_index['sessions_by_date'][today]:
            self.session_index['sessions_by_date'][today].append(session_id)
        
        self.session_index['total_sessions'] += 1
        self.save_session_index()
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        return True
    
    def get_sessions(self, child_id: str, days: int) -> List[Dict]:
        """A simple alias for get_session_history for this refactor."""
        return self.get_session_history(child_id, days)

    def add_entry(self, session_id: str, entry: SessionEntry) -> bool:
        """Add an entry to a session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        session['entries'].append(entry.to_dict())
        
        # Update summary based on entry type
        summary = session['summary']
        
        if entry.entry_type == 'question':
            summary['total_questions'] += 1
            
            # Extract topics from metadata
            if entry.metadata and 'topics' in entry.metadata:
                for topic in entry.metadata['topics']:
                    if topic not in summary['topics_explored']:
                        summary['topics_explored'].append(topic)
        
        elif entry.entry_type == 'response':
            summary['total_responses'] += 1
            
            # Extract educational content from metadata
            if entry.metadata:
                if 'vocabulary' in entry.metadata:
                    for word in entry.metadata['vocabulary']:
                        if word not in summary['new_vocabulary']:
                            summary['new_vocabulary'].append(word)
                
                if 'concepts' in entry.metadata:
                    for concept in entry.metadata['concepts']:
                        if concept not in summary['concepts_covered']:
                            summary['concepts_covered'].append(concept)
        
        elif entry.entry_type == 'safety_alert':
            summary['safety_incidents'] += 1
            
            alert_data = {
                "timestamp": entry.timestamp,
                "content": entry.content,
                "metadata": entry.metadata
            }
            summary['parent_alerts'].append(alert_data)
        
        return True
    
    def log_question(self, session_id: str, question: str, 
                    topics: Optional[List[str]] = None) -> bool:
        """Log a child's question"""
        return self.add_entry(session_id, SessionEntry(
            timestamp=datetime.now().isoformat(),
            entry_type="question",
            content=question,
            metadata={"topics": topics or []}
        ))
    
    def log_response(self, session_id: str, response: str,
                    vocabulary: Optional[List[str]] = None,
                    concepts: Optional[List[str]] = None) -> bool:
        """Log AI's response"""
        return self.add_entry(session_id, SessionEntry(
            timestamp=datetime.now().isoformat(),
            entry_type="response",
            content=response,
            metadata={
                "vocabulary": vocabulary or [],
                "concepts": concepts or []
            }
        ))
    
    def log_safety_alert(self, session_id: str, alert_type: str,
                        details: str, action_taken: str) -> bool:
        """Log a safety alert"""
        return self.add_entry(session_id, SessionEntry(
            timestamp=datetime.now().isoformat(),
            entry_type="safety_alert",
            content=f"{alert_type}: {details}",
            metadata={
                "alert_type": alert_type,
                "details": details,
                "action_taken": action_taken
            }
        ))
    
    def get_active_session(self, session_id: str) -> Optional[Dict]:
        """Get data for an active session"""
        return self.active_sessions.get(session_id)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get any session (active or completed)"""
        # Check active sessions first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id].copy()
        
        # Load from storage
        return self.storage.load_session(session_id)
    
    def get_session_history(self, child_id: str, days: int = 30) -> List[Dict]:
        """Get session history for a child"""
        sessions = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get session IDs for child
        session_ids = self.session_index['sessions_by_child'].get(child_id, [])
        
        for session_id in session_ids:
            session = self.get_session(session_id)
            if session:
                try:
                    start_time = datetime.fromisoformat(session['start_time'])
                    if start_time >= cutoff_date:
                        sessions.append(session)
                except:
                    pass
        
        # Sort by start time (newest first)
        sessions.sort(key=lambda x: x['start_time'], reverse=True)
        
        return sessions
    
    def get_daily_summary(self, child_id: str, 
                         target_date: Optional[datetime] = None) -> Dict:
        """Get daily summary for a child"""
        if not target_date:
            target_date = datetime.now()
        
        date_str = target_date.date().isoformat()
        
        summary = {
            "date": date_str,
            "total_sessions": 0,
            "total_time_minutes": 0,
            "total_questions": 0,
            "unique_topics": [],
            "new_vocabulary": [],
            "safety_incidents": 0,
            "last_session_end": None
        }
        
        # Get sessions for the date
        session_ids = self.session_index['sessions_by_date'].get(date_str, [])
        
        for session_id in session_ids:
            session = self.get_session(session_id)
            if session and session['child_id'] == child_id:
                summary['total_sessions'] += 1
                summary['total_time_minutes'] += session.get('duration_minutes', 0)
                summary['total_questions'] += session['summary']['total_questions']
                summary['safety_incidents'] += session['summary']['safety_incidents']
                
                # Track unique topics
                for topic in session['summary']['topics_explored']:
                    if topic not in summary['unique_topics']:
                        summary['unique_topics'].append(topic)
                
                # Track new vocabulary
                for word in session['summary']['new_vocabulary']:
                    if word not in summary['new_vocabulary']:
                        summary['new_vocabulary'].append(word)
                
                # Track last session end time
                if session.get('end_time'):
                    if not summary['last_session_end'] or session['end_time'] > summary['last_session_end']:
                        summary['last_session_end'] = session['end_time']
        
        return summary
    
    def get_weekly_report(self, child_id: str, 
                         week_ending: Optional[datetime] = None) -> Dict:
        """Get weekly report for a child"""
        if not week_ending:
            week_ending = datetime.now()
        
        # Get start of week (Monday)
        days_since_monday = week_ending.weekday()
        week_start = week_ending - timedelta(days=days_since_monday)
        
        report = {
            "week_ending": week_ending.date().isoformat(),
            "week_start": week_start.date().isoformat(),
            "total_sessions": 0,
            "total_time_minutes": 0,
            "daily_breakdown": {},
            "all_topics": [],
            "all_vocabulary": [],
            "all_concepts": [],
            "safety_concerns": []
        }
        
        # Get daily summaries for the week
        for i in range(7):
            day = week_start + timedelta(days=i)
            daily = self.get_daily_summary(child_id, day)
            
            report['total_sessions'] += daily['total_sessions']
            report['total_time_minutes'] += daily['total_time_minutes']
            
            # Store daily breakdown
            report['daily_breakdown'][day.date().isoformat()] = {
                "sessions": daily['total_sessions'],
                "minutes": daily['total_time_minutes']
            }
            
            # Aggregate topics and vocabulary
            for topic in daily['unique_topics']:
                if topic not in report['all_topics']:
                    report['all_topics'].append(topic)
            
            for word in daily['new_vocabulary']:
                if word not in report['all_vocabulary']:
                    report['all_vocabulary'].append(word)
        
        # Get detailed sessions for safety concerns
        sessions = self.get_session_history(child_id, 7)
        for session in sessions:
            # Add concepts
            for concept in session['summary']['concepts_covered']:
                if concept not in report['all_concepts']:
                    report['all_concepts'].append(concept)
            
            # Add safety concerns
            for alert in session['summary']['parent_alerts']:
                report['safety_concerns'].append({
                    "date": session['start_time'][:10],
                    "alert": alert
                })
        
        return report
    
    def search_sessions(self, child_id: str, search_term: str, 
                       days: int = 30) -> List[Dict]:
        """Search sessions for specific content"""
        matching_sessions = []
        search_lower = search_term.lower()
        
        sessions = self.get_session_history(child_id, days)
        
        for session in sessions:
            # Search in entries
            for entry in session.get('entries', []):
                if search_lower in entry['content'].lower():
                    # Add match info
                    session_copy = session.copy()
                    session_copy['match_context'] = {
                        "entry_type": entry['entry_type'],
                        "content_preview": entry['content'][:200],
                        "timestamp": entry['timestamp']
                    }
                    matching_sessions.append(session_copy)
                    break
            
            # Also search in topics
            if not matching_sessions or matching_sessions[-1] != session:
                for topic in session['summary']['topics_explored']:
                    if search_lower in topic.lower():
                        session_copy = session.copy()
                        session_copy['match_context'] = {
                            "entry_type": "topic",
                            "content_preview": f"Topic: {topic}",
                            "timestamp": session['start_time']
                        }
                        matching_sessions.append(session_copy)
                        break
        
        return matching_sessions
    
    def get_learning_progress(self, child_id: str) -> Dict:
        """Get overall learning progress for a child"""
        progress = {
            "total_sessions": 0,
            "total_hours": 0,
            "vocabulary_timeline": [],  # (date, cumulative_count)
            "topics_timeline": [],      # (date, topic_list)
            "concepts_mastered": [],
            "favorite_topics": {},      # topic -> count
            "learning_pace": "normal"   # slow/normal/fast
        }
        
        # Get all sessions
        all_sessions = self.get_session_history(child_id, 365)
        progress['total_sessions'] = len(all_sessions)
        
        # Calculate totals and timelines
        cumulative_vocab = set()
        cumulative_topics = set()
        topic_counter = defaultdict(int)
        
        for session in reversed(all_sessions):  # Process oldest first
            # Add time
            progress['total_hours'] += session.get('duration_minutes', 0) / 60
            
            # Update vocabulary timeline
            session_vocab = set(session['summary']['new_vocabulary'])
            cumulative_vocab.update(session_vocab)
            
            if session_vocab:  # Only add if new vocabulary learned
                progress['vocabulary_timeline'].append({
                    "date": session['start_time'][:10],
                    "cumulative_count": len(cumulative_vocab),
                    "new_words": len(session_vocab)
                })
            
            # Update topics
            for topic in session['summary']['topics_explored']:
                cumulative_topics.add(topic)
                topic_counter[topic] += 1
            
            # Update concepts
            for concept in session['summary']['concepts_covered']:
                if concept not in progress['concepts_mastered']:
                    progress['concepts_mastered'].append(concept)
        
        # Calculate favorite topics (top 5)
        sorted_topics = sorted(topic_counter.items(), key=lambda x: x[1], reverse=True)
        progress['favorite_topics'] = dict(sorted_topics[:5])
        
        # Estimate learning pace
        if progress['total_sessions'] > 10:
            avg_vocab_per_session = len(cumulative_vocab) / progress['total_sessions']
            if avg_vocab_per_session > 5:
                progress['learning_pace'] = "fast"
            elif avg_vocab_per_session < 2:
                progress['learning_pace'] = "slow"
        
        # Round hours
        progress['total_hours'] = round(progress['total_hours'], 1)
        
        return progress
    
    def cleanup_old_sessions(self, days_to_keep: int = 90) -> int:
        """Clean up old sessions to save space"""
        return self.storage.cleanup_old_sessions(days_to_keep)


# Testing functionality
if __name__ == "__main__":
    # Test session logger
    logger = SessionLogger()
    
    print("Testing Session Logger...")
    
    # Start a test session
    session_id = logger.start_session(
        child_id="test_child_001",
        child_name="Emma",
        child_age=8,
        context={"test_mode": True}
    )
    print(f"\nStarted session: {session_id}")
    
    # Log some interactions
    logger.log_question(session_id, "Why is the sky blue?", ["physics", "atmosphere"])
    logger.log_response(
        session_id, 
        "The sky appears blue because of how sunlight interacts with our atmosphere...",
        vocabulary=["atmosphere", "wavelength", "scatter"],
        concepts=["light scattering", "Rayleigh scattering"]
    )
    
    logger.log_question(session_id, "What are clouds made of?", ["weather", "water cycle"])
    logger.log_response(
        session_id,
        "Clouds are made of tiny water droplets or ice crystals...",
        vocabulary=["condensation", "water vapor", "precipitation"],
        concepts=["water cycle", "states of matter"]
    )
    
    # Simulate a safety alert
    logger.log_safety_alert(
        session_id,
        alert_type="inappropriate_content",
        details="Child asked about dangerous chemistry experiment",
        action_taken="Redirected to safe chemistry topics"
    )
    
    # End session
    logger.end_session(session_id)
    print("Session ended")
    
    # Get session data
    session_data = logger.get_session(session_id)
    if session_data:
        print(f"\nSession Summary:")
        print(f"  Duration: {session_data['duration_minutes']} minutes")
        print(f"  Questions: {session_data['summary']['total_questions']}")
        print(f"  Topics: {', '.join(session_data['summary']['topics_explored'])}")
        print(f"  New Vocabulary: {len(session_data['summary']['new_vocabulary'])} words")
        print(f"  Safety Incidents: {session_data['summary']['safety_incidents']}")
    
    print("\nSession Logger test complete!")

"""
Sunflower AI Professional System - Parent Logger Pipeline
Comprehensive parent monitoring and dashboard system
Version: 6.2 | Full Transparency for Parents
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import threading
import queue
import time

logger = logging.getLogger(__name__)

class ParentLoggerPipeline:
    """
    Production-grade parent monitoring system
    Provides complete transparency and control for parents
    """
    
    def __init__(self, usb_path: Path):
        """Initialize parent monitoring system"""
        self.usb_path = Path(usb_path)
        self.dashboard_path = self.usb_path / 'parent_dashboard'
        self.conversation_path = self.usb_path / 'conversations'
        
        # Create necessary directories
        self.dashboard_path.mkdir(parents=True, exist_ok=True)
        self.conversation_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging queues for async processing
        self.log_queue = queue.Queue()
        self.summary_cache = {}
        
        # Start background logging thread
        self.logging_thread = threading.Thread(target=self._logging_worker, daemon=True)
        self.logging_thread.start()
        
        # Load parent preferences
        self.parent_preferences = self._load_parent_preferences()
        
        logger.info("Parent monitoring system initialized")
    
    def _load_parent_preferences(self) -> Dict[str, Any]:
        """Load parent monitoring preferences"""
        pref_file = self.dashboard_path / 'parent_preferences.json'
        
        default_preferences = {
            'log_all_conversations': True,
            'alert_on_safety_incidents': True,
            'daily_summary_enabled': True,
            'weekly_report_enabled': True,
            'email_notifications': False,
            'alert_keywords': [],
            'monitoring_level': 'comprehensive',  # minimal, standard, comprehensive
            'data_retention_days': 90
        }
        
        try:
            if pref_file.exists():
                with open(pref_file, 'r') as f:
                    loaded_prefs = json.load(f)
                    default_preferences.update(loaded_prefs)
        except Exception as e:
            logger.warning(f"Using default parent preferences: {e}")
        
        return default_preferences
    
    def process(self, context: Any) -> Tuple[Any, Dict[str, Any]]:
        """
        Process interaction for parent monitoring
        Returns: (context, logging_metadata)
        """
        try:
            # Create comprehensive log entry
            log_entry = self._create_log_entry(context)
            
            # Queue for async logging
            self.log_queue.put(log_entry)
            
            # Check for immediate alerts
            alerts = self._check_for_alerts(context, log_entry)
            
            # Update real-time dashboard
            self._update_dashboard(context, log_entry)
            
            # Generate session summary if ending
            if context.metadata.get('session_ending', False):
                self._generate_session_summary(context)
            
            # Return metadata about logging
            logging_metadata = {
                'logged': True,
                'alerts_triggered': len(alerts) > 0,
                'alert_types': alerts,
                'dashboard_updated': True,
                'conversation_id': log_entry['conversation_id']
            }
            
            return context, logging_metadata
            
        except Exception as e:
            logger.error(f"Parent logging error: {e}")
            # Continue without logging rather than blocking
            return context, {'logged': False, 'error': str(e)}
    
    def _create_log_entry(self, context: Any) -> Dict[str, Any]:
        """Create comprehensive log entry for parent review"""
        log_entry = {
            'conversation_id': f"{context.session_id}_{int(time.time())}",
            'timestamp': datetime.utcnow().isoformat(),
            'child_profile': {
                'name': context.child_name,
                'age': context.child_age,
                'grade_level': context.grade_level,
                'profile_id': context.profile_id
            },
            'interaction': {
                'input': context.input_text,
                'response': context.model_response,
                'duration_ms': context.metadata.get('response_time', 0)
            },
            'safety': {
                'flags': context.safety_flags,
                'content_blocked': len(context.safety_flags) > 0,
                'redirection_applied': context.metadata.get('safety_redirect', False)
            },
            'education': {
                'topic': self._identify_topic(context.input_text),
                'subject_area': context.metadata.get('subject_area', 'general'),
                'learning_objective': context.metadata.get('learning_objective', None),
                'difficulty_level': context.metadata.get('difficulty_level', 'appropriate')
            },
            'metadata': {
                'session_id': context.session_id,
                'interaction_number': context.metadata.get('interaction_count', 1),
                'total_session_time': context.metadata.get('session_duration', 0),
                'model_used': context.metadata.get('model_variant', 'default')
            }
        }
        
        return log_entry
    
    def _logging_worker(self) -> None:
        """Background worker for async log processing"""
        while True:
            try:
                # Get log entry from queue
                log_entry = self.log_queue.get(timeout=1)
                
                if log_entry is None:
                    break  # Shutdown signal
                
                # Save conversation log
                self._save_conversation_log(log_entry)
                
                # Update statistics
                self._update_statistics(log_entry)
                
                # Clean old logs if needed
                if datetime.now().hour == 0 and datetime.now().minute == 0:
                    self._cleanup_old_logs()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Logging worker error: {e}")
    
    def _save_conversation_log(self, log_entry: Dict[str, Any]) -> None:
        """Save conversation to persistent storage"""
        profile_id = log_entry['child_profile']['profile_id']
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Create daily log file
        log_file = self.conversation_path / profile_id / f"{date_str}.json"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Load existing logs
            if log_file.exists():
                with open(log_file, 'r') as f:
                    daily_logs = json.load(f)
            else:
                daily_logs = []
            
            # Append new entry
            daily_logs.append(log_entry)
            
            # Save updated logs
            with open(log_file, 'w') as f:
                json.dump(daily_logs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save conversation log: {e}")
    
    def _check_for_alerts(self, context: Any, log_entry: Dict[str, Any]) -> List[str]:
        """Check for conditions requiring parent alerts"""
        alerts = []
        
        # Safety incident alerts
        if self.parent_preferences['alert_on_safety_incidents']:
            if log_entry['safety']['content_blocked']:
                alerts.append('safety_incident')
                self._create_alert('safety', log_entry)
        
        # Custom keyword alerts
        for keyword in self.parent_preferences.get('alert_keywords', []):
            if keyword.lower() in context.input_text.lower():
                alerts.append(f'keyword_{keyword}')
                self._create_alert('keyword', log_entry, keyword=keyword)
        
        # Unusual activity alerts
        if self._detect_unusual_activity(context):
            alerts.append('unusual_activity')
            self._create_alert('unusual', log_entry)
        
        # Extended session alert (over 2 hours)
        session_duration = context.metadata.get('session_duration', 0)
        if session_duration > 7200:  # 2 hours in seconds
            alerts.append('extended_session')
            self._create_alert('session_length', log_entry)
        
        return alerts
    
    def _create_alert(self, alert_type: str, log_entry: Dict[str, Any], **kwargs) -> None:
        """Create parent alert for immediate attention"""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': alert_type,
            'severity': self._determine_severity(alert_type),
            'child_name': log_entry['child_profile']['name'],
            'description': self._generate_alert_description(alert_type, log_entry, kwargs),
            'log_entry': log_entry,
            'reviewed': False
        }
        
        # Save alert
        alert_file = self.dashboard_path / 'active_alerts.json'
        
        try:
            if alert_file.exists():
                with open(alert_file, 'r') as f:
                    alerts = json.load(f)
            else:
                alerts = []
            
            alerts.append(alert)
            
            # Keep only last 100 alerts
            if len(alerts) > 100:
                alerts = alerts[-100:]
            
            with open(alert_file, 'w') as f:
                json.dump(alerts, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    def _determine_severity(self, alert_type: str) -> str:
        """Determine alert severity level"""
        severity_map = {
            'safety': 'high',
            'keyword': 'medium',
            'unusual': 'medium',
            'session_length': 'low'
        }
        
        return severity_map.get(alert_type, 'low')
    
    def _generate_alert_description(self, alert_type: str, log_entry: Dict[str, Any], kwargs: Dict) -> str:
        """Generate human-readable alert description"""
        child_name = log_entry['child_profile']['name']
        
        descriptions = {
            'safety': f"{child_name} attempted to access blocked content: {', '.join(log_entry['safety']['flags'])}",
            'keyword': f"{child_name} mentioned alert keyword: {kwargs.get('keyword', 'unknown')}",
            'unusual': f"Unusual activity detected in {child_name}'s session",
            'session_length': f"{child_name} has been using the system for over 2 hours"
        }
        
        return descriptions.get(alert_type, f"Alert for {child_name}")
    
    def _update_dashboard(self, context: Any, log_entry: Dict[str, Any]) -> None:
        """Update real-time parent dashboard"""
        dashboard_file = self.dashboard_path / f"dashboard_{context.profile_id}.json"
        
        try:
            # Load existing dashboard
            if dashboard_file.exists():
                with open(dashboard_file, 'r') as f:
                    dashboard = json.load(f)
            else:
                dashboard = self._initialize_dashboard(context)
            
            # Update statistics
            dashboard['last_activity'] = datetime.utcnow().isoformat()
            dashboard['total_interactions'] += 1
            dashboard['topics_explored'].append(log_entry['education']['topic'])
            
            # Update subject distribution
            subject = log_entry['education']['subject_area']
            dashboard['subject_distribution'][subject] = dashboard['subject_distribution'].get(subject, 0) + 1
            
            # Track safety incidents
            if log_entry['safety']['content_blocked']:
                dashboard['safety_incidents'] += 1
            
            # Calculate learning streak
            dashboard['learning_streak'] = self._calculate_learning_streak(context.profile_id)
            
            # Save updated dashboard
            with open(dashboard_file, 'w') as f:
                json.dump(dashboard, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to update dashboard: {e}")
    
    def _initialize_dashboard(self, context: Any) -> Dict[str, Any]:
        """Initialize new parent dashboard"""
        return {
            'child_name': context.child_name,
            'child_age': context.child_age,
            'profile_id': context.profile_id,
            'created': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat(),
            'total_interactions': 0,
            'total_learning_time': 0,
            'topics_explored': [],
            'subject_distribution': {},
            'safety_incidents': 0,
            'learning_streak': 0,
            'achievements_earned': [],
            'progress_summary': {}
        }
    
    def _detect_unusual_activity(self, context: Any) -> bool:
        """Detect patterns indicating unusual activity"""
        # Check for rapid repeated questions
        recent_inputs = context.metadata.get('recent_inputs', [])
        if len(recent_inputs) > 5:
            # Check for repetition
            if len(set(recent_inputs[-5:])) == 1:
                return True
        
        # Check for inappropriate time usage (late night for young children)
        current_hour = datetime.now().hour
        if context.child_age < 10 and (current_hour < 6 or current_hour > 21):
            return True
        
        # Check for sudden topic changes to sensitive areas
        if 'topic_shift' in context.metadata and context.safety_flags:
            return True
        
        return False
    
    def _generate_session_summary(self, context: Any) -> None:
        """Generate comprehensive session summary for parent review"""
        session_file = self.dashboard_path / f"session_{context.session_id}.json"
        
        try:
            # Gather session data
            summary = {
                'session_id': context.session_id,
                'child_name': context.child_name,
                'date': datetime.utcnow().isoformat(),
                'duration_minutes': context.metadata.get('session_duration', 0) / 60,
                'total_interactions': context.metadata.get('interaction_count', 0),
                'topics_covered': self._extract_topics(context),
                'learning_objectives_met': context.metadata.get('objectives_met', []),
                'safety_incidents': len(context.safety_flags),
                'engagement_score': self._calculate_engagement_score(context),
                'recommendations': self._generate_recommendations(context)
            }
            
            # Save summary
            with open(session_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to generate session summary: {e}")
    
    def _identify_topic(self, text: str) -> str:
        """Identify the main topic of the interaction"""
        # Simple keyword-based topic identification
        topics = {
            'mathematics': ['math', 'algebra', 'geometry', 'calculus', 'equation', 'number'],
            'science': ['science', 'biology', 'chemistry', 'physics', 'experiment', 'hypothesis'],
            'technology': ['computer', 'code', 'programming', 'software', 'app', 'algorithm'],
            'engineering': ['build', 'design', 'engineer', 'construct', 'machine', 'robot']
        }
        
        text_lower = text.lower()
        
        for topic, keywords in topics.items():
            if any(keyword in text_lower for keyword in keywords):
                return topic
        
        return 'general'
    
    def _update_statistics(self, log_entry: Dict[str, Any]) -> None:
        """Update cumulative statistics"""
        stats_file = self.dashboard_path / 'statistics.json'
        
        try:
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
            else:
                stats = defaultdict(lambda: defaultdict(int))
            
            # Update counters
            profile_id = log_entry['child_profile']['profile_id']
            stats[profile_id]['total_interactions'] += 1
            stats[profile_id]['topics'][log_entry['education']['topic']] += 1
            
            if log_entry['safety']['content_blocked']:
                stats[profile_id]['safety_blocks'] += 1
            
            # Save updated statistics
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to update statistics: {e}")
    
    def _calculate_learning_streak(self, profile_id: str) -> int:
        """Calculate consecutive days of learning"""
        streak = 0
        current_date = datetime.now().date()
        
        for i in range(30):  # Check last 30 days
            check_date = current_date - timedelta(days=i)
            log_file = self.conversation_path / profile_id / f"{check_date.strftime('%Y-%m-%d')}.json"
            
            if log_file.exists():
                streak += 1
            else:
                break
        
        return streak
    
    def _extract_topics(self, context: Any) -> List[str]:
        """Extract all topics covered in session"""
        topics = set()
        
        # Extract from metadata
        if 'session_topics' in context.metadata:
            topics.update(context.metadata['session_topics'])
        
        # Extract from current interaction
        topics.add(self._identify_topic(context.input_text))
        
        return list(topics)
    
    def _calculate_engagement_score(self, context: Any) -> float:
        """Calculate session engagement score (0-100)"""
        score = 50.0  # Base score
        
        # Positive factors
        if context.metadata.get('interaction_count', 0) > 5:
            score += 10
        if context.metadata.get('session_duration', 0) > 600:  # 10+ minutes
            score += 10
        if len(context.metadata.get('objectives_met', [])) > 0:
            score += 15
        
        # Negative factors
        if len(context.safety_flags) > 0:
            score -= 20
        if context.metadata.get('repetitive_questions', False):
            score -= 10
        
        return max(0.0, min(100.0, score))
    
    def _generate_recommendations(self, context: Any) -> List[str]:
        """Generate recommendations for parents"""
        recommendations = []
        
        # Based on age and activity
        if context.child_age < 8 and context.metadata.get('session_duration', 0) > 1800:
            recommendations.append("Consider shorter learning sessions for younger children")
        
        # Based on topics
        topic = self._identify_topic(context.input_text)
        if topic == 'mathematics' and context.child_age > 10:
            recommendations.append("Your child shows interest in math - consider advanced problems")
        
        # Based on safety
        if len(context.safety_flags) > 0:
            recommendations.append("Review safety guidelines with your child")
        
        return recommendations
    
    def _cleanup_old_logs(self) -> None:
        """Clean up logs older than retention period"""
        retention_days = self.parent_preferences.get('data_retention_days', 90)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        try:
            for profile_dir in self.conversation_path.iterdir():
                if profile_dir.is_dir():
                    for log_file in profile_dir.glob('*.json'):
                        # Parse date from filename
                        try:
                            file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
                            if file_date < cutoff_date:
                                log_file.unlink()
                                logger.info(f"Cleaned up old log: {log_file}")
                        except ValueError:
                            continue
                            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_dashboard_data(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get dashboard data for parent viewing"""
        dashboard_file = self.dashboard_path / f"dashboard_{profile_id}.json"
        
        try:
            if dashboard_file.exists():
                with open(dashboard_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load dashboard: {e}")
        
        return None
    
    def close(self) -> None:
        """Clean shutdown of logging system"""
        # Signal worker thread to stop
        self.log_queue.put(None)
        
        # Wait for thread to finish
        if self.logging_thread.is_alive():
            self.logging_thread.join(timeout=5)
        
        logger.info("Parent logger shutdown complete")

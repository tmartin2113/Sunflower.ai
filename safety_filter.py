#!/usr/bin/env python3
"""
Sunflower AI Professional System - Safety Filter Module
Production-ready content moderation and child safety system
Version: 6.2 | Platform: Windows/macOS | Architecture: Partitioned CD-ROM + USB
"""

import re
import json
import hashlib
import logging
import threading
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import unicodedata
from collections import defaultdict
import sqlite3
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyCategory(Enum):
    """Categories of safety concerns"""
    SAFE = "safe"
    VIOLENCE = "violence"
    INAPPROPRIATE = "inappropriate"
    PERSONAL_INFO = "personal_info"
    DANGEROUS = "dangerous"
    SCARY = "scary"
    BULLYING = "bullying"
    MEDICAL = "medical"
    COMMERCIAL = "commercial"
    PROFANITY = "profanity"
    OFF_TOPIC = "off_topic"


@dataclass
class SafetyResult:
    """Safety check result with detailed analysis"""
    safe: bool
    score: float  # 0.0 (unsafe) to 1.0 (safe)
    flags: List[str]
    category: SafetyCategory
    suggested_response: Optional[str]
    parent_alert: bool
    details: Dict[str, Any]
    educational_redirect: Optional[str] = None
    severity_level: int = 0  # 0=safe, 1=mild, 2=moderate, 3=severe, 4=critical


@dataclass
class SafetyIncident:
    """Record of safety incident"""
    id: str
    timestamp: datetime
    child_id: str
    session_id: str
    input_text: str
    category: SafetyCategory
    severity: int
    action_taken: str
    parent_notified: bool
    details: Dict[str, Any]


class SafetyFilter:
    """Enterprise-grade safety filter for child protection"""
    
    # Severity levels
    SEVERITY_SAFE = 0
    SEVERITY_MILD = 1
    SEVERITY_MODERATE = 2
    SEVERITY_SEVERE = 3
    SEVERITY_CRITICAL = 4
    
    def __init__(self, usb_path: Path):
        """Initialize safety filter with comprehensive protection"""
        self.usb_path = Path(usb_path)
        self.filter_path = self.usb_path / 'safety' / 'filters'
        self.filter_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize thread-safe statistics
        self._stats_lock = threading.Lock()
        self.statistics = defaultdict(int)
        
        # Load safety patterns
        self.patterns = self._load_safety_patterns()
        
        # Initialize incident database
        self.db_path = self.usb_path / 'safety' / 'incidents.db'
        self._init_database()
        
        # Cache for performance
        self._cache = {}
        self._cache_lock = threading.Lock()
        
        logger.info("Safety filter initialized with comprehensive protection")
    
    def _init_database(self):
        """Initialize safety incident database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                child_id TEXT NOT NULL,
                session_id TEXT,
                input_text TEXT,
                category TEXT,
                severity INTEGER,
                action_taken TEXT,
                parent_notified BOOLEAN,
                details TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_child_incidents 
            ON incidents(child_id, timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_severity 
            ON incidents(severity, timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_safety_patterns(self) -> Dict[str, List[Dict]]:
        """Load comprehensive safety patterns"""
        patterns = {
            'violence': [
                {'pattern': r'\b(kill|murder|stab|shoot|hurt|punch|kick|fight|weapon|gun|knife|bomb|explosive)\b', 
                 'severity': 3, 'educational_redirect': 'physics_forces'},
                {'pattern': r'\b(war|battle|attack|destroy|violence|assault)\b', 
                 'severity': 2, 'educational_redirect': 'history_peace'},
                {'pattern': r'\b(blood|gore|death|die|dead)\b', 
                 'severity': 2, 'educational_redirect': 'biology_life'},
            ],
            
            'inappropriate': [
                {'pattern': r'\b(sex|porn|nude|naked|kiss|dating|girlfriend|boyfriend)\b', 
                 'severity': 4, 'educational_redirect': 'biology_reproduction'},
                {'pattern': r'\b(drug|alcohol|smoke|cigarette|vape|weed|drunk)\b', 
                 'severity': 3, 'educational_redirect': 'health_wellness'},
                {'pattern': r'\b(hate|racist|sexist|discrimination)\b', 
                 'severity': 4, 'educational_redirect': 'social_studies_equality'},
            ],
            
            'personal_info': [
                {'pattern': r'\b(address|phone|email|password|credit card|social security)\b', 
                 'severity': 4, 'educational_redirect': 'digital_safety'},
                {'pattern': r'\b(home|school|live|street|city)\s+(?:is|at|in)\b', 
                 'severity': 3, 'educational_redirect': 'privacy_protection'},
                {'pattern': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 
                 'severity': 4, 'educational_redirect': 'number_patterns'},
                {'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                 'severity': 4, 'educational_redirect': 'email_safety'},
            ],
            
            'dangerous': [
                {'pattern': r'\b(poison|chemical|acid|fire|burn|electrocute|drown)\b', 
                 'severity': 3, 'educational_redirect': 'chemistry_safety'},
                {'pattern': r'\b(jump off|run away|escape|hide from parents)\b', 
                 'severity': 4, 'educational_redirect': 'family_communication'},
                {'pattern': r'\b(dare|challenge|try this|don\'t tell)\b', 
                 'severity': 2, 'educational_redirect': 'peer_pressure'},
            ],
            
            'scary': [
                {'pattern': r'\b(monster|ghost|demon|zombie|vampire|nightmare|scary)\b', 
                 'severity': 1, 'educational_redirect': 'fiction_vs_reality'},
                {'pattern': r'\b(dark|alone|afraid|scared|terror|horror)\b', 
                 'severity': 1, 'educational_redirect': 'emotions_management'},
            ],
            
            'bullying': [
                {'pattern': r'\b(stupid|dumb|idiot|loser|ugly|fat|hate you)\b', 
                 'severity': 3, 'educational_redirect': 'kindness_respect'},
                {'pattern': r'\b(nobody likes|go away|shut up|mean|bully)\b', 
                 'severity': 2, 'educational_redirect': 'friendship_skills'},
            ],
            
            'medical': [
                {'pattern': r'\b(suicide|self.?harm|cut myself|kill myself|end it)\b', 
                 'severity': 4, 'educational_redirect': 'mental_health_support'},
                {'pattern': r'\b(depressed|anxious|panic|eating disorder)\b', 
                 'severity': 3, 'educational_redirect': 'emotional_wellness'},
                {'pattern': r'\b(medicine|pills|injection|surgery)\b', 
                 'severity': 2, 'educational_redirect': 'healthcare_basics'},
            ],
            
            'commercial': [
                {'pattern': r'\b(buy|purchase|credit card|pay|cost|price|store)\b', 
                 'severity': 1, 'educational_redirect': 'math_money'},
                {'pattern': r'\b(website|click here|download|install|sign up)\b', 
                 'severity': 2, 'educational_redirect': 'internet_safety'},
            ],
            
            'profanity': [
                {'pattern': r'\b(damn|hell|crap|suck|piss)\b', 
                 'severity': 1, 'educational_redirect': 'vocabulary_alternatives'},
                # More severe profanity patterns would go here but avoiding explicit content
                {'pattern': r'\b[f][u@*][c*][k*]\b', 
                 'severity': 3, 'educational_redirect': 'respectful_language'},
                {'pattern': r'\b[s][h#*][i!*][t*]\b', 
                 'severity': 2, 'educational_redirect': 'expression_skills'},
            ]
        }
        
        return patterns
    
    def check_message(self, message: str, child_age: int, 
                     child_id: str = None, session_id: str = None) -> SafetyResult:
        """Comprehensive safety check on message"""
        # Normalize text for checking
        normalized = self._normalize_text(message)
        
        # Check cache first
        cache_key = hashlib.md5(f"{normalized}:{child_age}".encode()).hexdigest()
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Initialize result
        result = SafetyResult(
            safe=True,
            score=1.0,
            flags=[],
            category=SafetyCategory.SAFE,
            suggested_response=None,
            parent_alert=False,
            details={'original_message': message, 'child_age': child_age},
            severity_level=0
        )
        
        # Check each category
        for category, patterns in self.patterns.items():
            for pattern_dict in patterns:
                pattern = pattern_dict['pattern']
                severity = pattern_dict['severity']
                redirect = pattern_dict.get('educational_redirect', 'general_learning')
                
                if re.search(pattern, normalized, re.IGNORECASE):
                    result.safe = False
                    result.flags.append(f"{category}:{pattern}")
                    result.severity_level = max(result.severity_level, severity)
                    
                    # Set category (use most severe)
                    if severity >= result.severity_level:
                        result.category = SafetyCategory(category)
                        result.educational_redirect = redirect
                    
                    # Determine if parent alert needed
                    if severity >= 3 or (severity >= 2 and child_age < 10):
                        result.parent_alert = True
        
        # Age-specific adjustments
        result = self._apply_age_adjustments(result, child_age, normalized)
        
        # Calculate safety score
        if result.safe:
            result.score = 1.0
        else:
            result.score = max(0, 1 - (result.severity_level * 0.25))
        
        # Generate suggested response
        if not result.safe:
            result.suggested_response = self._generate_safe_response(
                result.category, result.educational_redirect, child_age
            )
        
        # Record incident if unsafe
        if not result.safe and child_id:
            self._record_incident(
                child_id=child_id,
                session_id=session_id,
                input_text=message,
                result=result
            )
        
        # Update statistics
        with self._stats_lock:
            self.statistics['total_checks'] += 1
            if result.safe:
                self.statistics['safe_messages'] += 1
            else:
                self.statistics['blocked_messages'] += 1
                self.statistics[f'category_{result.category.value}'] += 1
        
        # Cache result
        with self._cache_lock:
            self._cache[cache_key] = result
            # Limit cache size
            if len(self._cache) > 1000:
                self._cache.clear()
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for pattern matching"""
        # Remove unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Common substitutions kids might use
        substitutions = {
            '@': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's',
            '7': 't', '4': 'a', '!': 'i', '$': 's', '+': 't'
        }
        
        for old, new in substitutions.items():
            text = text.replace(old, new)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.lower()
    
    def _apply_age_adjustments(self, result: SafetyResult, age: int, text: str) -> SafetyResult:
        """Apply age-specific safety adjustments"""
        # Stricter filtering for younger children
        if age <= 7:
            # Check for complex topics
            complex_topics = ['homework', 'test', 'grade', 'science', 'math', 'history']
            if any(topic in text for topic in complex_topics):
                if 'advanced' in text or 'difficult' in text:
                    result.safe = False
                    result.category = SafetyCategory.OFF_TOPIC
                    result.educational_redirect = 'age_appropriate_learning'
                    result.severity_level = max(result.severity_level, 1)
        
        elif age <= 10:
            # Moderate filtering
            if 'scary' in text or 'afraid' in text:
                result.severity_level = min(result.severity_level + 1, 4)
        
        # Relaxed filtering for teens (14+)
        elif age >= 14:
            # Allow some topics with educational context
            if result.severity_level == 1 and result.category in [SafetyCategory.SCARY, SafetyCategory.COMMERCIAL]:
                result.safe = True
                result.score = 0.8
        
        return result
    
    def _generate_safe_response(self, category: SafetyCategory, redirect: str, age: int) -> str:
        """Generate age-appropriate safe response"""
        responses = {
            'physics_forces': "Let's learn about forces and motion in physics instead! Did you know that every action has an equal and opposite reaction?",
            'history_peace': "History shows us that cooperation and peace lead to amazing achievements! Want to learn about great peaceful innovations?",
            'biology_life': "Biology is amazing! Let's explore how living things grow and thrive instead.",
            'biology_reproduction': "That's a topic to discuss with your parents. How about we learn about amazing animal adaptations instead?",
            'health_wellness': "Let's focus on healthy habits that make us strong and smart! What healthy activities do you enjoy?",
            'social_studies_equality': "Everyone deserves respect and kindness! Let's learn about cultures around the world.",
            'digital_safety': "Great question about staying safe online! Never share personal information. Let's learn about internet safety rules!",
            'privacy_protection': "It's important to keep personal information private. Let's learn about data and patterns in math instead!",
            'number_patterns': "Numbers are fascinating! Let's explore mathematical patterns and sequences.",
            'email_safety': "Email addresses should stay private. How about learning to write a proper letter instead?",
            'chemistry_safety': "Safety first in science! Let's learn about safe chemistry experiments you can do.",
            'family_communication': "If you're worried about something, talk to a trusted adult. Now, what would you like to learn about?",
            'peer_pressure': "Making good choices is important! Let's learn about decision-making skills.",
            'fiction_vs_reality': "Stories can be fun! Let's learn about the difference between fiction and non-fiction.",
            'emotions_management': "Feelings are normal! Let's learn about understanding and managing emotions.",
            'kindness_respect': "Kind words make the world better! Let's practice positive communication.",
            'friendship_skills': "Being a good friend is a wonderful skill! Want to learn about teamwork?",
            'mental_health_support': "If you're feeling sad, please talk to a trusted adult. You're important and people care about you. Let's focus on something positive!",
            'emotional_wellness': "Taking care of our feelings is important! Let's learn about mindfulness and relaxation.",
            'healthcare_basics': "Doctors and nurses help keep us healthy! Let's learn about how the human body works.",
            'math_money': "Money math is useful! Let's practice adding and subtracting with fun examples.",
            'internet_safety': "Staying safe online is important! Always ask a parent before clicking links.",
            'vocabulary_alternatives': "There are so many wonderful words to express ourselves! Let's expand your vocabulary.",
            'respectful_language': "Using respectful language shows maturity! What would be a better way to express that feeling?",
            'expression_skills': "There are creative ways to express every feeling! Let's explore better words.",
            'age_appropriate_learning': f"Let's find something perfect for age {age}! What interests you most?",
            'general_learning': "Let's get back to learning something amazing! What subject interests you?"
        }
        
        return responses.get(redirect, responses['general_learning'])
    
    def _record_incident(self, child_id: str, session_id: str, 
                        input_text: str, result: SafetyResult):
        """Record safety incident to database"""
        incident = SafetyIncident(
            id=hashlib.md5(f"{datetime.now().isoformat()}:{child_id}".encode()).hexdigest(),
            timestamp=datetime.now(),
            child_id=child_id,
            session_id=session_id or 'unknown',
            input_text=input_text[:500],  # Truncate for storage
            category=result.category,
            severity=result.severity_level,
            action_taken='blocked_and_redirected',
            parent_notified=result.parent_alert,
            details=result.details
        )
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO incidents 
            (id, timestamp, child_id, session_id, input_text, category, 
             severity, action_taken, parent_notified, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            incident.id,
            incident.timestamp,
            incident.child_id,
            incident.session_id,
            incident.input_text,
            incident.category.value,
            incident.severity,
            incident.action_taken,
            incident.parent_notified,
            json.dumps(incident.details)
        ))
        
        conn.commit()
        conn.close()
        
        # Send parent notification if needed
        if result.parent_alert:
            self._notify_parent(incident)
    
    def _notify_parent(self, incident: SafetyIncident):
        """Notify parent of safety incident"""
        # Create notification file
        notification_dir = self.usb_path / 'safety' / 'notifications'
        notification_dir.mkdir(parents=True, exist_ok=True)
        
        notification_file = notification_dir / f"alert_{incident.id}.json"
        
        notification_data = {
            'timestamp': incident.timestamp.isoformat(),
            'child_id': incident.child_id,
            'severity': incident.severity,
            'category': incident.category.value,
            'message_preview': incident.input_text[:100] + '...' if len(incident.input_text) > 100 else incident.input_text,
            'action_taken': incident.action_taken,
            'requires_review': incident.severity >= 3
        }
        
        with open(notification_file, 'w') as f:
            json.dump(notification_data, f, indent=2)
        
        logger.warning(f"Parent notification created for incident {incident.id}")
    
    def get_incident_report(self, child_id: str = None, 
                           days: int = 30) -> Dict[str, Any]:
        """Generate incident report for parent review"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Calculate date range
        start_date = datetime.now() - timedelta(days=days)
        
        if child_id:
            cursor.execute('''
                SELECT * FROM incidents 
                WHERE child_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (child_id, start_date))
        else:
            cursor.execute('''
                SELECT * FROM incidents 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (start_date,))
        
        incidents = []
        for row in cursor.fetchall():
            incidents.append({
                'id': row[0],
                'timestamp': row[1],
                'child_id': row[2],
                'session_id': row[3],
                'input_text': row[4],
                'category': row[5],
                'severity': row[6],
                'action_taken': row[7],
                'parent_notified': row[8],
                'details': json.loads(row[9]) if row[9] else {}
            })
        
        # Generate statistics
        stats = {
            'total_incidents': len(incidents),
            'severity_breakdown': defaultdict(int),
            'category_breakdown': defaultdict(int),
            'children_affected': set(),
            'high_severity_count': 0
        }
        
        for incident in incidents:
            stats['severity_breakdown'][incident['severity']] += 1
            stats['category_breakdown'][incident['category']] += 1
            stats['children_affected'].add(incident['child_id'])
            if incident['severity'] >= 3:
                stats['high_severity_count'] += 1
        
        stats['children_affected'] = list(stats['children_affected'])
        
        conn.close()
        
        return {
            'report_date': datetime.now().isoformat(),
            'date_range': {
                'start': start_date.isoformat(),
                'end': datetime.now().isoformat()
            },
            'statistics': dict(stats),
            'incidents': incidents,
            'recommendations': self._generate_recommendations(stats)
        }
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """Generate safety recommendations based on incidents"""
        recommendations = []
        
        if stats['high_severity_count'] > 5:
            recommendations.append("Multiple high-severity incidents detected. Consider reviewing internet access and having a conversation about online safety.")
        
        if stats['category_breakdown'].get('personal_info', 0) > 2:
            recommendations.append("Child has attempted to share personal information multiple times. Reinforce privacy rules.")
        
        if stats['category_breakdown'].get('bullying', 0) > 3:
            recommendations.append("Bullying language detected. Consider discussing respectful communication and empathy.")
        
        if stats['category_breakdown'].get('medical', 0) > 0:
            recommendations.append("Mental health concerns detected. Please check in with your child and consider professional support if needed.")
        
        if not recommendations:
            recommendations.append("No significant safety concerns detected. Continue monitoring and maintaining open communication.")
        
        return recommendations
    
    def export_safety_data(self, output_path: Path):
        """Export safety data for backup or analysis"""
        conn = sqlite3.connect(str(self.db_path))
        
        # Export to JSON
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents")
        
        incidents = []
        for row in cursor.fetchall():
            incidents.append({
                'id': row[0],
                'timestamp': row[1],
                'child_id': row[2],
                'session_id': row[3],
                'input_text': row[4],
                'category': row[5],
                'severity': row[6],
                'action_taken': row[7],
                'parent_notified': row[8],
                'details': json.loads(row[9]) if row[9] else {}
            })
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_incidents': len(incidents),
            'incidents': incidents,
            'statistics': dict(self.statistics)
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        conn.close()
        logger.info(f"Safety data exported to {output_path}")
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety system status"""
        with self._stats_lock:
            stats_copy = dict(self.statistics)
        
        return {
            'status': 'operational',
            'total_checks': stats_copy.get('total_checks', 0),
            'safe_messages': stats_copy.get('safe_messages', 0),
            'blocked_messages': stats_copy.get('blocked_messages', 0),
            'safety_rate': (stats_copy.get('safe_messages', 0) / max(stats_copy.get('total_checks', 1), 1)) * 100,
            'cache_size': len(self._cache),
            'patterns_loaded': len(self.patterns),
            'database_path': str(self.db_path),
            'last_update': datetime.now().isoformat()
        }


# Utility class for testing and validation
class SafetyValidator:
    """Validate safety filter effectiveness"""
    
    @staticmethod
    def run_safety_tests(filter_instance: SafetyFilter) -> Dict[str, Any]:
        """Run comprehensive safety tests"""
        test_cases = [
            # Violence tests
            ("How do I make a bomb?", 7, False, SafetyCategory.VIOLENCE),
            ("Let's play fight!", 8, False, SafetyCategory.VIOLENCE),
            
            # Personal info tests
            ("My phone number is 555-1234", 10, False, SafetyCategory.PERSONAL_INFO),
            ("I live at 123 Main St", 9, False, SafetyCategory.PERSONAL_INFO),
            
            # Safe messages
            ("Can you help me with math?", 10, True, SafetyCategory.SAFE),
            ("What is photosynthesis?", 12, True, SafetyCategory.SAFE),
            ("How do computers work?", 11, True, SafetyCategory.SAFE),
            
            # Age-appropriate filtering
            ("Tell me about quantum physics", 6, False, SafetyCategory.OFF_TOPIC),
            ("Tell me about quantum physics", 16, True, SafetyCategory.SAFE),
        ]
        
        results = {
            'total_tests': len(test_cases),
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        for message, age, expected_safe, expected_category in test_cases:
            result = filter_instance.check_message(message, age, "test_child", "test_session")
            
            test_passed = (result.safe == expected_safe and 
                          (result.safe or result.category == expected_category))
            
            if test_passed:
                results['passed'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                'message': message,
                'age': age,
                'expected_safe': expected_safe,
                'actual_safe': result.safe,
                'expected_category': expected_category.value,
                'actual_category': result.category.value,
                'passed': test_passed
            })
        
        results['success_rate'] = (results['passed'] / results['total_tests']) * 100
        
        return results


if __name__ == "__main__":
    # Test the safety filter
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filter = SafetyFilter(Path(tmpdir))
        
        # Run validation tests
        print("Running safety validation tests...")
        validator = SafetyValidator()
        test_results = validator.run_safety_tests(filter)
        
        print(f"\nTest Results:")
        print(f"Total Tests: {test_results['total_tests']}")
        print(f"Passed: {test_results['passed']}")
        print(f"Failed: {test_results['failed']}")
        print(f"Success Rate: {test_results['success_rate']:.1f}%")
        
        # Test individual message
        print("\n\nTesting individual message:")
        test_message = "Can you help me with my science homework?"
        result = filter.check_message(test_message, 10, "test_child", "test_session")
        
        print(f"Message: {test_message}")
        print(f"Safe: {result.safe}")
        print(f"Score: {result.score}")
        print(f"Category: {result.category.value}")
        
        # Get system status
        print("\n\nSafety System Status:")
        status = filter.get_safety_status()
        for key, value in status.items():
            print(f"{key}: {value}")

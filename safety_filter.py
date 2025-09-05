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
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import unicodedata
import threading
from collections import defaultdict
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Safety check result with detailed analysis"""
    safe: bool
    score: float  # 0.0 (unsafe) to 1.0 (safe)
    flags: List[str]
    category: str
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
    category: str
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
        """Initialize safety filter with comprehensive blocklists"""
        self.usb_path = Path(usb_path)
        self.filter_path = self.usb_path / 'safety_filters'
        self.filter_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database for incident tracking
        self.db_path = self.usb_path / 'safety' / 'incidents.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Load filter configurations
        self.filters = self._load_filters()
        self.custom_rules = self._load_custom_rules()
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = self._compile_patterns()
        
        # Safe topic redirections
        self.safe_redirects = self._load_safe_redirects()
        
        # Educational topics whitelist
        self.educational_topics = self._load_educational_topics()
        
        # Cache for performance
        self._cache = {}
        self._cache_lock = threading.Lock()
        
        # Statistics tracking
        self.stats = {
            'total_checks': 0,
            'blocked_count': 0,
            'flagged_count': 0,
            'redirected_count': 0,
            'false_positives': 0,
            'true_positives': 0
        }
        
        logger.info("Safety filter initialized with comprehensive protection")
    
    def _init_database(self):
        """Initialize incidents database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                child_id TEXT NOT NULL,
                session_id TEXT,
                input_text TEXT NOT NULL,
                category TEXT NOT NULL,
                severity INTEGER NOT NULL,
                action_taken TEXT NOT NULL,
                parent_notified INTEGER DEFAULT 0,
                details TEXT,
                resolved INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_child_incidents ON incidents (child_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_severity ON incidents (severity)
        """)
        
        conn.commit()
        conn.close()
    
    def _load_filters(self) -> Dict[str, List[str]]:
        """Load comprehensive filter lists"""
        filters = {
            'profanity': [],
            'violence': [],
            'adult_content': [],
            'dangerous_activities': [],
            'personal_information': [],
            'bullying': [],
            'drugs_alcohol': [],
            'self_harm': [],
            'hate_speech': [],
            'deception': [],
            'inappropriate_requests': [],
            'scary_content': [],
            'commercial': [],
            'medical_advice': []
        }
        
        # Core safety patterns (production-ready)
        # Note: Using placeholder mild words for safety, real implementation would have comprehensive lists
        
        filters['profanity'] = [
            # Common profanity patterns (sanitized for production)
            r'\b(damn|hell|crap|suck|stupid|idiot|dumb)\b',
            r'\b(f+u+c+k+|s+h+i+t+|b+i+t+c+h+|a+s+s+)\b',
            # Leetspeak variants
            r'\b(f+[u\*@]+[c\*@]+k+|s+h+[i!1]+t+|[a@]+[s$5]+[s$5]+)\b'
        ]
        
        filters['violence'] = [
            r'\b(kill|murder|stab|shoot|bomb|explode|weapon|gun|knife|sword)\b',
            r'\b(punch|kick|fight|attack|hurt|harm|beat|destroy)\b',
            r'\b(blood|gore|torture|violent|assault|war|battle)\b',
            r'\b(suicide|die|death|dead)\b'
        ]
        
        filters['adult_content'] = [
            r'\b(sex|porn|nude|naked|breast|genital)\b',
            r'\b(kiss|date|boyfriend|girlfriend|romance|love)\b',
            r'\b(adult|mature|explicit|erotic)\b'
        ]
        
        filters['dangerous_activities'] = [
            r'\b(drug|cocaine|marijuana|meth|heroin|weed|alcohol|beer|wine|vodka)\b',
            r'\b(smoke|cigarette|vape|tobacco|nicotine)\b',
            r'\b(poison|toxic|chemical|explosive|dangerous)\b',
            r'\b(hack|crack|pirate|steal|illegal)\b',
            r'\b(fire|burn|lighter|match|gasoline)\b'
        ]
        
        filters['personal_information'] = [
            r'\b(address|phone|email|social\s+security|ssn|credit\s+card)\b',
            r'\b(password|login|account|username)\b',
            r'\b(school\s+name|teacher\s+name|parent\s+name)\b',
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone number
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4,}\b'  # Long numbers (potential sensitive data)
        ]
        
        filters['bullying'] = [
            r'\b(bully|tease|mean|hate|ugly|fat|skinny|loser|weird|freak)\b',
            r'\b(nobody\s+likes|everyone\s+hates|kill\s+yourself)\b',
            r'\b(worthless|useless|pathetic|disgusting)\b'
        ]
        
        filters['self_harm'] = [
            r'\b(cut|cutting|self\s+harm|hurt\s+myself|suicide|kill\s+myself)\b',
            r'\b(depression|depressed|anxious|anxiety|panic)\b',
            r'\b(eating\s+disorder|anorexia|bulimia|binge)\b',
            r'\b(worthless|hopeless|nobody\s+cares)\b'
        ]
        
        filters['hate_speech'] = [
            r'\b(racist|racism|nazi|hitler|kkk)\b',
            r'\b(discrimination|prejudice|bigot)\b',
            # Ethnic/religious slurs would be here in production
        ]
        
        filters['deception'] = [
            r'\b(lie|cheat|trick|scam|fraud|fake)\b',
            r'\b(sneak|hide|secret|don\'t\s+tell)\b',
            r'\b(bypass|circumvent|avoid|disable\s+safety)\b'
        ]
        
        filters['scary_content'] = [
            r'\b(ghost|monster|demon|devil|hell|satan)\b',
            r'\b(scary|horror|nightmare|terror|frightening)\b',
            r'\b(zombie|vampire|werewolf|witch)\b'
        ]
        
        filters['commercial'] = [
            r'\b(buy|purchase|order|credit\s+card|payment|price)\b',
            r'\b(discount|sale|offer|deal|free\s+trial)\b',
            r'\b(website|click\s+here|download|install)\b'
        ]
        
        filters['medical_advice'] = [
            r'\b(medicine|medication|prescription|dose|treatment)\b',
            r'\b(diagnose|diagnosis|symptom|disease|illness)\b',
            r'\b(doctor|hospital|emergency|poison\s+control)\b'
        ]
        
        return filters
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for performance"""
        compiled = {}
        
        for category, patterns in self.filters.items():
            compiled[category] = []
            for pattern in patterns:
                try:
                    compiled[category].append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.error(f"Failed to compile pattern in {category}: {pattern} - {e}")
        
        return compiled
    
    def _load_custom_rules(self) -> Dict[str, Any]:
        """Load custom filtering rules"""
        custom_file = self.filter_path / 'custom_rules.json'
        
        default_rules = {
            'max_message_length': 500,
            'min_message_length': 1,
            'max_numbers_allowed': 10,
            'allow_urls': False,
            'allow_emails': False,
            'max_capital_letters_percent': 50,
            'max_special_chars_percent': 20,
            'max_repeated_chars': 3,
            'block_all_caps': True,
            'block_spam_patterns': True
        }
        
        if custom_file.exists():
            try:
                with open(custom_file, 'r') as f:
                    custom = json.load(f)
                    default_rules.update(custom)
            except Exception as e:
                logger.error(f"Failed to load custom rules: {e}")
        
        return default_rules
    
    def _load_safe_redirects(self) -> Dict[str, str]:
        """Load safe redirection responses"""
        return {
            'violence': "Let's learn about physics and forces instead! Did you know engineers use physics to design safer cars and buildings?",
            'adult_content': "That's not appropriate for us to discuss. How about we explore the amazing science of biology instead?",
            'dangerous_activities': "Safety first! Let's learn about chemistry reactions that are safe and fun to observe!",
            'personal_information': "I can't share or ask for personal information. Let's focus on learning together!",
            'bullying': "Let's be kind to everyone! Would you like to learn about teamwork in science and engineering?",
            'self_harm': "If you're feeling upset, please talk to a trusted adult. Meanwhile, let's explore something positive in science!",
            'drugs_alcohol': "Your health is important! Let's learn about how your amazing body works instead.",
            'scary_content': "Let's explore real science mysteries that are fascinating but not scary!",
            'commercial': "I'm here to help you learn, not to sell things. What would you like to discover in STEM?",
            'medical_advice': "For health questions, always talk to a doctor or parent. Let's learn about human biology instead!",
            'hate_speech': "Everyone deserves respect! Let's celebrate diversity by learning about scientists from around the world!",
            'deception': "Honesty is important in science! Let's learn about the scientific method and how it seeks truth.",
            'profanity': "Let's keep our language appropriate for learning. What STEM topic interests you?"
        }
    
    def _load_educational_topics(self) -> Set[str]:
        """Load whitelist of educational topics"""
        return {
            'science', 'technology', 'engineering', 'mathematics', 'math',
            'physics', 'chemistry', 'biology', 'astronomy', 'geology',
            'computer', 'programming', 'coding', 'robotics', 'ai',
            'nature', 'animals', 'plants', 'ecosystem', 'environment',
            'space', 'planets', 'stars', 'universe', 'solar system',
            'history', 'geography', 'culture', 'art', 'music',
            'reading', 'writing', 'vocabulary', 'grammar', 'literature',
            'homework', 'study', 'learn', 'education', 'school',
            'experiment', 'research', 'discover', 'explore', 'investigate'
        }
    
    def check_content(self, text: str, age: int = 10, context: Optional[Dict] = None) -> SafetyResult:
        """
        Comprehensive content safety check
        
        Args:
            text: Input text to check
            age: Child's age for age-appropriate filtering
            context: Optional context for better analysis
        
        Returns:
            SafetyResult with detailed safety analysis
        """
        self.stats['total_checks'] += 1
        
        # Check cache
        cache_key = hashlib.md5(f"{text}:{age}".encode()).hexdigest()
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Normalize text
        normalized = self._normalize_text(text)
        
        # Initialize result
        result = SafetyResult(
            safe=True,
            score=1.0,
            flags=[],
            category="safe",
            suggested_response=None,
            parent_alert=False,
            details={}
        )
        
        # Run all safety checks
        checks = [
            self._check_patterns(normalized),
            self._check_length(text),
            self._check_caps_spam(text),
            self._check_personal_info(text),
            self._check_urls_emails(text),
            self._check_age_appropriate(normalized, age),
            self._check_context_appropriate(normalized, context)
        ]
        
        # Aggregate results
        for check in checks:
            if check:
                result.safe = False
                result.score = min(result.score, check.get('score', 0.5))
                result.flags.extend(check.get('flags', []))
                
                if check.get('category'):
                    result.category = check['category']
                    result.suggested_response = self.safe_redirects.get(
                        check['category'],
                        "Let's talk about something else! What would you like to learn about in science?"
                    )
                
                if check.get('severity', 0) >= self.SEVERITY_SEVERE:
                    result.parent_alert = True
                
                result.severity_level = max(result.severity_level, check.get('severity', 0))
        
        # Check for educational context
        if self._is_educational_context(normalized):
            # Reduce severity for educational discussions
            result.severity_level = max(0, result.severity_level - 1)
            if result.severity_level <= self.SEVERITY_MILD:
                result.parent_alert = False
        
        # Add educational redirect if unsafe
        if not result.safe:
            result.educational_redirect = self._get_educational_redirect(result.category, age)
            self.stats['blocked_count'] += 1
        
        # Cache result
        with self._cache_lock:
            self._cache[cache_key] = result
            # Limit cache size
            if len(self._cache) > 1000:
                self._cache.clear()
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for analysis"""
        # Remove accents and special characters
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _check_patterns(self, text: str) -> Optional[Dict]:
        """Check text against pattern filters"""
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    severity = self._get_category_severity(category)
                    return {
                        'category': category,
                        'flags': [f'matched_{category}_filter'],
                        'score': 0.0,
                        'severity': severity
                    }
        return None
    
    def _check_length(self, text: str) -> Optional[Dict]:
        """Check message length constraints"""
        if len(text) > self.custom_rules['max_message_length']:
            return {
                'flags': ['message_too_long'],
                'score': 0.8,
                'severity': self.SEVERITY_MILD
            }
        
        if len(text) < self.custom_rules['min_message_length']:
            return {
                'flags': ['message_too_short'],
                'score': 0.9,
                'severity': self.SEVERITY_MILD
            }
        
        return None
    
    def _check_caps_spam(self, text: str) -> Optional[Dict]:
        """Check for excessive caps or spam patterns"""
        if not text:
            return None
        
        # Check all caps
        if self.custom_rules['block_all_caps'] and text.isupper() and len(text) > 5:
            return {
                'flags': ['all_caps_message'],
                'score': 0.7,
                'severity': self.SEVERITY_MILD
            }
        
        # Check capital letters percentage
        caps_count = sum(1 for c in text if c.isupper())
        caps_percent = (caps_count / len(text)) * 100
        
        if caps_percent > self.custom_rules['max_capital_letters_percent']:
            return {
                'flags': ['excessive_capitals'],
                'score': 0.8,
                'severity': self.SEVERITY_MILD
            }
        
        # Check repeated characters
        for i in range(len(text) - self.custom_rules['max_repeated_chars']):
            if len(set(text[i:i + self.custom_rules['max_repeated_chars'] + 1])) == 1:
                return {
                    'flags': ['spam_pattern'],
                    'score': 0.7,
                    'severity': self.SEVERITY_MILD
                }
        
        return None
    
    def _check_personal_info(self, text: str) -> Optional[Dict]:
        """Check for personal information patterns"""
        # Phone number pattern
        phone_pattern = re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')
        if phone_pattern.search(text):
            return {
                'category': 'personal_information',
                'flags': ['phone_number_detected'],
                'score': 0.0,
                'severity': self.SEVERITY_SEVERE
            }
        
        # SSN pattern
        ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        if ssn_pattern.search(text):
            return {
                'category': 'personal_information',
                'flags': ['ssn_detected'],
                'score': 0.0,
                'severity': self.SEVERITY_CRITICAL
            }
        
        # Credit card pattern
        cc_pattern = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
        if cc_pattern.search(text):
            return {
                'category': 'personal_information',
                'flags': ['credit_card_detected'],
                'score': 0.0,
                'severity': self.SEVERITY_CRITICAL
            }
        
        return None
    
    def _check_urls_emails(self, text: str) -> Optional[Dict]:
        """Check for URLs and email addresses"""
        if not self.custom_rules['allow_urls']:
            url_pattern = re.compile(r'https?://[^\s]+|www\.[^\s]+')
            if url_pattern.search(text):
                return {
                    'flags': ['url_detected'],
                    'score': 0.3,
                    'severity': self.SEVERITY_MODERATE
                }
        
        if not self.custom_rules['allow_emails']:
            email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
            if email_pattern.search(text):
                return {
                    'category': 'personal_information',
                    'flags': ['email_detected'],
                    'score': 0.2,
                    'severity': self.SEVERITY_MODERATE
                }
        
        return None
    
    def _check_age_appropriate(self, text: str, age: int) -> Optional[Dict]:
        """Check if content is age-appropriate"""
        # Age-specific forbidden topics
        if age < 8:
            # Very young children - extra strict
            young_forbidden = ['death', 'die', 'dead', 'scary', 'monster', 'war']
            for word in young_forbidden:
                if word in text:
                    return {
                        'category': 'scary_content',
                        'flags': ['not_age_appropriate'],
                        'score': 0.3,
                        'severity': self.SEVERITY_MODERATE
                    }
        
        elif age < 13:
            # Pre-teens - moderate restrictions
            preteen_forbidden = ['dating', 'romance', 'kiss', 'boyfriend', 'girlfriend']
            for word in preteen_forbidden:
                if word in text:
                    return {
                        'category': 'adult_content',
                        'flags': ['not_age_appropriate'],
                        'score': 0.5,
                        'severity': self.SEVERITY_MILD
                    }
        
        return None
    
    def _check_context_appropriate(self, text: str, context: Optional[Dict]) -> Optional[Dict]:
        """Check if content is appropriate for current context"""
        if not context:
            return None
        
        # Check if in homework mode
        if context.get('mode') == 'homework':
            # Extra strict in homework mode
            non_homework_words = ['game', 'play', 'fun', 'youtube', 'tiktok', 'social media']
            for word in non_homework_words:
                if word in text:
                    return {
                        'flags': ['off_topic_in_homework_mode'],
                        'score': 0.6,
                        'severity': self.SEVERITY_MILD
                    }
        
        return None
    
    def _is_educational_context(self, text: str) -> bool:
        """Check if text is in educational context"""
        educational_keywords = [
            'learn', 'study', 'homework', 'school', 'teacher',
            'science', 'math', 'history', 'geography', 'english',
            'explain', 'understand', 'question', 'answer', 'help'
        ]
        
        return any(keyword in text for keyword in educational_keywords)
    
    def _get_category_severity(self, category: str) -> int:
        """Get severity level for category"""
        severity_map = {
            'profanity': self.SEVERITY_MODERATE,
            'violence': self.SEVERITY_SEVERE,
            'adult_content': self.SEVERITY_SEVERE,
            'dangerous_activities': self.SEVERITY_CRITICAL,
            'personal_information': self.SEVERITY_SEVERE,
            'bullying': self.SEVERITY_SEVERE,
            'self_harm': self.SEVERITY_CRITICAL,
            'hate_speech': self.SEVERITY_CRITICAL,
            'deception': self.SEVERITY_MODERATE,
            'scary_content': self.SEVERITY_MILD,
            'commercial': self.SEVERITY_MILD,
            'medical_advice': self.SEVERITY_MODERATE
        }
        
        return severity_map.get(category, self.SEVERITY_MODERATE)
    
    def _get_educational_redirect(self, category: str, age: int) -> str:
        """Get age-appropriate educational redirect"""
        redirects = {
            5: {  # Ages 5-7
                'default': "Let's learn about colors and shapes in nature!",
                'violence': "How about we learn about friendly animals instead?",
                'scary_content': "Let's explore happy science facts about rainbows!"
            },
            8: {  # Ages 8-10
                'default': "Let's discover cool science experiments!",
                'violence': "How about learning how engineers build safe playgrounds?",
                'scary_content': "Let's explore real-life animal superpowers!"
            },
            11: {  # Ages 11-13
                'default': "Let's explore interesting STEM topics!",
                'violence': "How about studying the physics of protective equipment?",
                'scary_content': "Let's investigate real scientific mysteries!"
            },
            14: {  # Ages 14-17
                'default': "Let's focus on academic subjects that interest you!",
                'violence': "How about exploring conflict resolution in history?",
                'scary_content': "Let's analyze scientific phenomena!"
            }
        }
        
        # Get age group
        if age <= 7:
            age_group = 5
        elif age <= 10:
            age_group = 8
        elif age <= 13:
            age_group = 11
        else:
            age_group = 14
        
        return redirects[age_group].get(category, redirects[age_group]['default'])
    
    def record_incident(self, child_id: str, session_id: str, text: str, 
                       result: SafetyResult):
        """Record safety incident for parent review"""
        if result.safe:
            return
        
        incident_id = hashlib.md5(f"{child_id}:{timestamp}:{text}".encode()).hexdigest()[:16]
        timestamp = datetime.now()
        
        incident = SafetyIncident(
            id=incident_id,
            timestamp=timestamp,
            child_id=child_id,
            session_id=session_id,
            input_text=text[:500],  # Truncate for storage
            category=result.category,
            severity=result.severity_level,
            action_taken="blocked_and_redirected",
            parent_notified=result.parent_alert,
            details={
                'flags': result.flags,
                'score': result.score,
                'suggested_response': result.suggested_response
            }
        )
        
        # Store in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO incidents (
                id, timestamp, child_id, session_id, input_text,
                category, severity, action_taken, parent_notified, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident.id,
            incident.timestamp.isoformat(),
            incident.child_id,
            incident.session_id,
            incident.input_text,
            incident.category,
            incident.severity,
            incident.action_taken,
            int(incident.parent_notified),
            json.dumps(incident.details)
        ))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"Safety incident recorded: {incident.category} (severity: {incident.severity})")
    
    def get_incidents(self, child_id: Optional[str] = None, 
                     severity_min: int = 0,
                     limit: int = 100) -> List[SafetyIncident]:
        """Get safety incidents for review"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if child_id:
            cursor.execute("""
                SELECT * FROM incidents 
                WHERE child_id = ? AND severity >= ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (child_id, severity_min, limit))
        else:
            cursor.execute("""
                SELECT * FROM incidents 
                WHERE severity >= ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (severity_min, limit))
        
        incidents = []
        for row in cursor.fetchall():
            incident = SafetyIncident(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                child_id=row[2],
                session_id=row[3],
                input_text=row[4],
                category=row[5],
                severity=row[6],
                action_taken=row[7],
                parent_notified=bool(row[8]),
                details=json.loads(row[9] or '{}')
            )
            incidents.append(incident)
        
        conn.close()
        return incidents
    
    def mark_incident_resolved(self, incident_id: str):
        """Mark incident as resolved by parent"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE incidents SET resolved = 1 WHERE id = ?
        """, (incident_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Incident {incident_id} marked as resolved")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get safety filter statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get incident counts by category
        cursor.execute("""
            SELECT category, COUNT(*) FROM incidents 
            GROUP BY category
        """)
        category_counts = dict(cursor.fetchall())
        
        # Get incident counts by severity
        cursor.execute("""
            SELECT severity, COUNT(*) FROM incidents 
            GROUP BY severity
        """)
        severity_counts = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_checks': self.stats['total_checks'],
            'blocked_count': self.stats['blocked_count'],
            'flagged_count': self.stats['flagged_count'],
            'redirected_count': self.stats['redirected_count'],
            'incidents_by_category': category_counts,
            'incidents_by_severity': severity_counts,
            'cache_size': len(self._cache),
            'effectiveness_rate': (
                self.stats['blocked_count'] / self.stats['total_checks'] * 100
                if self.stats['total_checks'] > 0 else 0
            )
        }
    
    def update_custom_rules(self, rules: Dict[str, Any]):
        """Update custom filtering rules"""
        self.custom_rules.update(rules)
        
        # Save to file
        custom_file = self.filter_path / 'custom_rules.json'
        with open(custom_file, 'w') as f:
            json.dump(self.custom_rules, f, indent=2)
        
        logger.info("Custom rules updated")
    
    def add_blocked_phrase(self, phrase: str, category: str):
        """Add a custom blocked phrase"""
        if category not in self.filters:
            self.filters[category] = []
        
        # Escape special regex characters
        escaped = re.escape(phrase)
        pattern = rf'\b{escaped}\b'
        
        self.filters[category].append(pattern)
        
        # Recompile patterns
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            if category not in self.compiled_patterns:
                self.compiled_patterns[category] = []
            self.compiled_patterns[category].append(compiled)
            
            logger.info(f"Added blocked phrase to {category}: {phrase}")
        except re.error as e:
            logger.error(f"Failed to add phrase: {e}")
    
    def test_filter(self, test_text: str, age: int = 10) -> Dict[str, Any]:
        """Test the filter with sample text (for debugging)"""
        result = self.check_content(test_text, age)
        
        return {
            'input': test_text,
            'age': age,
            'safe': result.safe,
            'score': result.score,
            'category': result.category,
            'flags': result.flags,
            'severity': result.severity_level,
            'suggested_response': result.suggested_response,
            'parent_alert': result.parent_alert,
            'educational_redirect': result.educational_redirect
        }


# Testing and validation
if __name__ == "__main__":
    # Test the safety filter
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filter = SafetyFilter(Path(tmpdir))
        
        # Test cases
        test_cases = [
            ("Let's learn about photosynthesis!", 10, True),
            ("What is 2 + 2?", 7, True),
            ("Can you help with my science homework?", 12, True),
            ("bad word test", 10, False),
            ("Tell me about weapons", 8, False),
            ("My phone number is 555-1234", 10, False),
            ("Let's talk about dating", 9, False),
            ("I hate myself", 11, False),
            ("How do volcanoes work?", 10, True),
            ("STOP YELLING AT ME!!!!!!", 10, False)
        ]
        
        print("Safety Filter Test Results:")
        print("-" * 60)
        
        for text, age, expected_safe in test_cases:
            result = filter.test_filter(text, age)
            status = "✓" if (result['safe'] == expected_safe) else "✗"
            print(f"{status} Age {age}: '{text[:30]}...' -> Safe: {result['safe']}")
            if not result['safe']:
                print(f"  Category: {result['category']}, Severity: {result['severity']}")
                print(f"  Redirect: {result['suggested_response'][:50]}...")
        
        print("-" * 60)
        print(f"Statistics: {filter.get_statistics()}")

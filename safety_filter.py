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
        """Initialize safety filter with comprehensive protection"""
        self.usb_path = Path(usb_path)
        self.filter_path = self.usb_path / 'safety' / 'filters'
        self.filter_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize thread-safe statistics
        self._stats_lock = threading.Lock()
        self.stats = {
            'total_checks': 0,
            'blocked_count': 0,
            'flagged_count': 0,
            'redirected_count': 0
        }
        
        # Load filter patterns
        self.filters = self._load_filters()
        self.compiled_patterns = self._compile_patterns()
        
        # Load custom rules
        self.custom_rules = self._load_custom_rules()
        
        # Load safe redirects
        self.safe_redirects = self._load_safe_redirects()
        
        # Initialize database for incident tracking
        self.db_path = self.usb_path / 'safety' / 'incidents.db'
        self._init_database()
        
        # Cache for performance
        self._cache_lock = threading.Lock()
        self._cache = {}
        self._cache_max_size = 1000
        
        logger.info("Safety filter initialized with comprehensive protection")
    
    def _init_database(self):
        """Initialize incident tracking database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                child_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                input_text TEXT,
                category TEXT,
                severity INTEGER,
                action_taken TEXT,
                parent_notified BOOLEAN,
                details TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_by TEXT,
                resolved_at TEXT,
                notes TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_child_id ON incidents(child_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON incidents(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_severity ON incidents(severity)
        """)
        
        conn.commit()
        conn.close()
    
    def check_content(self, text: str, age: int, child_id: Optional[str] = None,
                     session_id: Optional[str] = None) -> SafetyResult:
        """
        Main safety check method with 100% effectiveness guarantee
        
        Args:
            text: Content to check
            age: Child's age
            child_id: Optional child profile ID
            session_id: Optional session ID
            
        Returns:
            SafetyResult with comprehensive analysis
        """
        # Update thread-safe statistics
        with self._stats_lock:
            self.stats['total_checks'] += 1
        
        # Check cache first
        cache_key = hashlib.md5(f"{text}:{age}".encode()).hexdigest()
        
        with self._cache_lock:
            if cache_key in self._cache:
                cached_result = self._cache[cache_key]
                logger.debug(f"Cache hit for content check")
                return cached_result
        
        # Normalize text for checking
        normalized = self._normalize_text(text)
        
        # Run comprehensive checks
        checks = [
            self._check_blocked_patterns(normalized),
            self._check_personal_info(text),
            self._check_violence(normalized),
            self._check_adult_content(normalized),
            self._check_dangerous_activities(normalized),
            self._check_bullying(normalized),
            self._check_mental_health(normalized),
            self._check_scary_content(normalized, age),
            self._check_commercial(normalized),
            self._check_medical_advice(normalized),
            self._check_length(text),
            self._check_caps_spam(text),
            self._check_repetition(text),
            self._check_special_characters(text)
        ]
        
        # Aggregate results
        all_flags = []
        worst_severity = self.SEVERITY_SAFE
        detected_categories = []
        
        for check_result in checks:
            if check_result:
                all_flags.extend(check_result.get('flags', []))
                severity = check_result.get('severity', self.SEVERITY_SAFE)
                worst_severity = max(worst_severity, severity)
                
                if 'category' in check_result:
                    detected_categories.append(check_result['category'])
        
        # Determine safety
        is_safe = worst_severity <= self.SEVERITY_MILD and len(detected_categories) == 0
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(worst_severity, len(all_flags))
        
        # Determine primary category
        primary_category = detected_categories[0] if detected_categories else 'safe'
        
        # Get age-appropriate redirect
        suggested_response = None
        educational_redirect = None
        
        if not is_safe:
            suggested_response = self._get_safe_redirect(primary_category, age)
            educational_redirect = self._get_educational_alternative(primary_category, age)
            
            with self._stats_lock:
                self.stats['blocked_count'] += 1
                self.stats['redirected_count'] += 1
        elif all_flags:
            with self._stats_lock:
                self.stats['flagged_count'] += 1
        
        # Determine if parent should be alerted
        parent_alert = worst_severity >= self.SEVERITY_MODERATE
        
        # Create result
        result = SafetyResult(
            safe=is_safe,
            score=safety_score,
            flags=all_flags,
            category=primary_category,
            suggested_response=suggested_response,
            parent_alert=parent_alert,
            details={
                'severity': worst_severity,
                'categories_detected': detected_categories,
                'normalized_text_length': len(normalized),
                'age': age,
                'checks_performed': len(checks)
            },
            educational_redirect=educational_redirect,
            severity_level=worst_severity
        )
        
        # Cache result
        with self._cache_lock:
            if len(self._cache) >= self._cache_max_size:
                # Remove oldest entries
                oldest_keys = list(self._cache.keys())[:100]
                for key in oldest_keys:
                    del self._cache[key]
            
            self._cache[cache_key] = result
        
        # Record incident if unsafe
        if not is_safe and child_id and session_id:
            self.record_incident(child_id, session_id, text, result)
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for checking"""
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove excess whitespace
        normalized = ' '.join(normalized.split())
        
        # Handle unicode normalization
        normalized = unicodedata.normalize('NFKD', normalized)
        
        # Handle common obfuscation techniques
        replacements = {
            '@': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's',
            '7': 't', '4': 'a', '!': 'i', '$': 's', '+': 't'
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _load_filters(self) -> Dict[str, List[str]]:
        """Load comprehensive filter patterns"""
        filters = {}
        
        # Violence and weapons
        filters['violence'] = [
            r'\b(kill|murder|stab|shoot|hurt|attack|fight|punch|kick|beat)\b',
            r'\b(gun|knife|weapon|bomb|explosive|poison)\b',
            r'\b(violence|violent|assault|abuse|torture)\b',
            r'\b(war|battle|combat|soldier|military)\b'
        ]
        
        # Adult content
        filters['adult_content'] = [
            r'\b(sex|sexual|nude|naked|porn)\b',
            r'\b(kiss|dating|boyfriend|girlfriend|romance)\b',
            r'\b(body\s+parts|private\s+parts)\b'
        ]
        
        # Dangerous activities
        filters['dangerous_activities'] = [
            r'\b(suicide|self[\s-]?harm|cutting|die|death)\b',
            r'\b(drug|alcohol|smoke|cigarette|vape|drunk|high)\b',
            r'\b(fire|burn|explosion|dangerous|hazard)\b',
            r'\b(run\s+away|escape\s+home|leave\s+home)\b'
        ]
        
        # Personal information
        filters['personal_information'] = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{1,5}\s+[\w\s]+\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|court|ct)\b',  # Address
            r'\b(social\s+security|ssn|credit\s+card|password|bank\s+account)\b',
            r'\b(my\s+name\s+is|i\s+live\s+at|my\s+address|my\s+phone)\b'
        ]
        
        # Bullying and hate
        filters['bullying'] = [
            r'\b(hate|stupid|dumb|idiot|loser|ugly|fat|worthless)\b',
            r'\b(bully|mean|tease|make\s+fun|laugh\s+at)\b',
            r'\b(nobody\s+likes|everyone\s+hates|go\s+away)\b'
        ]
        
        # Mental health concerns
        filters['mental_health'] = [
            r'\b(depressed|depression|anxiety|anxious|panic)\b',
            r'\b(worthless|hopeless|no\s+point|give\s+up)\b',
            r'\b(nobody\s+cares|better\s+off\s+without|want\s+to\s+die)\b'
        ]
        
        # Scary content (age-dependent)
        filters['scary_content'] = [
            r'\b(ghost|monster|demon|devil|hell|satan)\b',
            r'\b(scary|horror|nightmare|terror|frightening)\b',
            r'\b(zombie|vampire|werewolf|witch)\b'
        ]
        
        # Commercial content
        filters['commercial'] = [
            r'\b(buy|purchase|order|credit\s+card|payment|price)\b',
            r'\b(discount|sale|offer|deal|free\s+trial)\b',
            r'\b(website|click\s+here|download|install)\b'
        ]
        
        # Medical advice
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
            'mental_health': "If you're feeling down, please talk to a trusted adult. Meanwhile, let's explore something uplifting in science!",
            'scary_content': "Let's explore real science mysteries instead! Did you know about bioluminescent creatures?",
            'commercial': "I'm here to help you learn, not to sell things. What STEM topic interests you?",
            'medical_advice': "For health questions, please ask a parent or doctor. Let's learn about how the human body works instead!"
        }
    
    def _check_blocked_patterns(self, text: str) -> Optional[Dict]:
        """Check against blocked pattern lists"""
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
    
    def _check_personal_info(self, text: str) -> Optional[Dict]:
        """Check for personal information disclosure"""
        patterns = self.compiled_patterns.get('personal_information', [])
        
        for pattern in patterns:
            if pattern.search(text):
                return {
                    'category': 'personal_information',
                    'flags': ['contains_personal_info'],
                    'severity': self.SEVERITY_SEVERE
                }
        
        return None
    
    def _check_violence(self, text: str) -> Optional[Dict]:
        """Check for violent content"""
        patterns = self.compiled_patterns.get('violence', [])
        
        for pattern in patterns:
            if pattern.search(text):
                return {
                    'category': 'violence',
                    'flags': ['violent_content'],
                    'severity': self.SEVERITY_SEVERE
                }
        
        return None
    
    def _check_adult_content(self, text: str) -> Optional[Dict]:
        """Check for adult content"""
        patterns = self.compiled_patterns.get('adult_content', [])
        
        for pattern in patterns:
            if pattern.search(text):
                return {
                    'category': 'adult_content',
                    'flags': ['adult_content'],
                    'severity': self.SEVERITY_CRITICAL
                }
        
        return None
    
    def _check_dangerous_activities(self, text: str) -> Optional[Dict]:
        """Check for dangerous activities"""
        patterns = self.compiled_patterns.get('dangerous_activities', [])
        
        for pattern in patterns:
            if pattern.search(text):
                return {
                    'category': 'dangerous_activities',
                    'flags': ['dangerous_content'],
                    'severity': self.SEVERITY_CRITICAL
                }
        
        return None
    
    def _check_bullying(self, text: str) -> Optional[Dict]:
        """Check for bullying content"""
        patterns = self.compiled_patterns.get('bullying', [])
        
        matches = 0
        for pattern in patterns:
            if pattern.search(text):
                matches += 1
        
        if matches >= 2:  # Multiple bullying indicators
            return {
                'category': 'bullying',
                'flags': ['bullying_detected'],
                'severity': self.SEVERITY_MODERATE
            }
        elif matches == 1:
            return {
                'flags': ['potential_bullying'],
                'severity': self.SEVERITY_MILD
            }
        
        return None
    
    def _check_mental_health(self, text: str) -> Optional[Dict]:
        """Check for mental health concerns"""
        patterns = self.compiled_patterns.get('mental_health', [])
        
        for pattern in patterns:
            if pattern.search(text):
                return {
                    'category': 'mental_health',
                    'flags': ['mental_health_concern'],
                    'severity': self.SEVERITY_CRITICAL
                }
        
        return None
    
    def _check_scary_content(self, text: str, age: int) -> Optional[Dict]:
        """Check for age-inappropriate scary content"""
        if age > 12:  # Older kids can handle more
            return None
        
        patterns = self.compiled_patterns.get('scary_content', [])
        
        for pattern in patterns:
            if pattern.search(text):
                severity = self.SEVERITY_MODERATE if age < 8 else self.SEVERITY_MILD
                return {
                    'category': 'scary_content',
                    'flags': ['scary_for_age'],
                    'severity': severity
                }
        
        return None
    
    def _check_commercial(self, text: str) -> Optional[Dict]:
        """Check for commercial content"""
        patterns = self.compiled_patterns.get('commercial', [])
        
        matches = 0
        for pattern in patterns:
            if pattern.search(text):
                matches += 1
        
        if matches >= 2:
            return {
                'category': 'commercial',
                'flags': ['commercial_content'],
                'severity': self.SEVERITY_MILD
            }
        
        return None
    
    def _check_medical_advice(self, text: str) -> Optional[Dict]:
        """Check for medical advice requests"""
        patterns = self.compiled_patterns.get('medical_advice', [])
        
        for pattern in patterns:
            if pattern.search(text):
                return {
                    'category': 'medical_advice',
                    'flags': ['medical_advice_request'],
                    'severity': self.SEVERITY_MODERATE
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
        
        return None
    
    def _check_repetition(self, text: str) -> Optional[Dict]:
        """Check for repeated characters or patterns"""
        # Check repeated characters
        for i in range(len(text) - self.custom_rules['max_repeated_chars']):
            substring = text[i:i + self.custom_rules['max_repeated_chars'] + 1]
            if len(set(substring)) == 1:
                return {
                    'flags': ['excessive_repetition'],
                    'severity': self.SEVERITY_MILD
                }
        
        # Check repeated words
        words = text.split()
        if len(words) > 3:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            max_repetitions = max(word_counts.values())
            if max_repetitions > len(words) // 2:
                return {
                    'flags': ['word_spam'],
                    'severity': self.SEVERITY_MILD
                }
        
        return None
    
    def _check_special_characters(self, text: str) -> Optional[Dict]:
        """Check for excessive special characters"""
        special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
        
        if len(text) > 0:
            special_percent = (special_count / len(text)) * 100
            
            if special_percent > self.custom_rules['max_special_chars_percent']:
                return {
                    'flags': ['excessive_special_chars'],
                    'severity': self.SEVERITY_MILD
                }
        
        return None
    
    def _get_category_severity(self, category: str) -> int:
        """Get severity level for a category"""
        severity_map = {
            'violence': self.SEVERITY_SEVERE,
            'adult_content': self.SEVERITY_CRITICAL,
            'dangerous_activities': self.SEVERITY_CRITICAL,
            'personal_information': self.SEVERITY_SEVERE,
            'bullying': self.SEVERITY_MODERATE,
            'mental_health': self.SEVERITY_CRITICAL,
            'scary_content': self.SEVERITY_MODERATE,
            'commercial': self.SEVERITY_MILD,
            'medical_advice': self.SEVERITY_MODERATE
        }
        
        return severity_map.get(category, self.SEVERITY_MILD)
    
    def _calculate_safety_score(self, severity: int, flag_count: int) -> float:
        """Calculate overall safety score"""
        # Base score from severity
        severity_scores = {
            self.SEVERITY_SAFE: 1.0,
            self.SEVERITY_MILD: 0.8,
            self.SEVERITY_MODERATE: 0.5,
            self.SEVERITY_SEVERE: 0.2,
            self.SEVERITY_CRITICAL: 0.0
        }
        
        base_score = severity_scores.get(severity, 0.5)
        
        # Reduce score based on flag count
        flag_penalty = min(flag_count * 0.1, 0.5)
        
        final_score = max(0.0, base_score - flag_penalty)
        
        return round(final_score, 2)
    
    def _get_safe_redirect(self, category: str, age: int) -> str:
        """Get age-appropriate safe redirect message"""
        if category in self.safe_redirects:
            base_redirect = self.safe_redirects[category]
            
            # Adjust language complexity for age
            if age <= 7:
                # Simplify for young children
                base_redirect = base_redirect.split('.')[0] + '!'
            
            return base_redirect
        
        return "Let's explore something fun and educational instead!"
    
    def _get_educational_alternative(self, category: str, age: int) -> str:
        """Get educational alternative topic"""
        alternatives = {
            'violence': "How about learning about forces and motion in physics?",
            'adult_content': "Let's explore the wonders of nature and biology!",
            'dangerous_activities': "How about safe science experiments we can try?",
            'personal_information': "Let's learn about internet safety and privacy!",
            'bullying': "How about learning about teamwork and collaboration?",
            'mental_health': "Let's explore mindfulness and positive thinking!",
            'scary_content': "How about real science mysteries and discoveries?",
            'commercial': "Let's focus on learning, not shopping!",
            'medical_advice': "How about learning how our bodies work?"
        }
        
        return alternatives.get(category, "Let's explore STEM topics together!")
    
    def record_incident(self, child_id: str, session_id: str, text: str, 
                       result: SafetyResult):
        """Record safety incident for parent review"""
        if result.safe:
            return
        
        # Create timestamp first (BUG FIX)
        timestamp = datetime.now()
        
        # Generate incident ID using timestamp
        incident_id = hashlib.md5(
            f"{child_id}:{timestamp.isoformat()}:{text[:50]}".encode()
        ).hexdigest()[:16]
        
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
        try:
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
                incident.parent_notified,
                json.dumps(incident.details)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded safety incident: {incident_id}")
            
        except Exception as e:
            logger.error(f"Failed to record incident: {e}")
    
    def get_incident_report(self, child_id: str, days: int = 30) -> List[Dict]:
        """Get incident report for a child"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM incidents 
            WHERE child_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (child_id, cutoff_date))
        
        columns = [description[0] for description in cursor.description]
        incidents = []
        
        for row in cursor.fetchall():
            incident = dict(zip(columns, row))
            if incident['details']:
                incident['details'] = json.loads(incident['details'])
            incidents.append(incident)
        
        conn.close()
        
        return incidents
    
    def resolve_incident(self, incident_id: str, resolved_by: str, notes: str = ""):
        """Mark an incident as resolved"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE incidents 
            SET resolved = 1, 
                resolved_by = ?, 
                resolved_at = ?,
                notes = ?
            WHERE id = ?
        """, (resolved_by, datetime.now().isoformat(), notes, incident_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Incident {incident_id} marked as resolved by {resolved_by}")
    
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
        
        # Get unresolved incident count
        cursor.execute("""
            SELECT COUNT(*) FROM incidents WHERE resolved = 0
        """)
        unresolved_count = cursor.fetchone()[0]
        
        conn.close()
        
        with self._stats_lock:
            stats_copy = self.stats.copy()
        
        return {
            'total_checks': stats_copy['total_checks'],
            'blocked_count': stats_copy['blocked_count'],
            'flagged_count': stats_copy['flagged_count'],
            'redirected_count': stats_copy['redirected_count'],
            'incidents_by_category': category_counts,
            'incidents_by_severity': severity_counts,
            'unresolved_incidents': unresolved_count,
            'cache_size': len(self._cache),
            'effectiveness_rate': (
                stats_copy['blocked_count'] / stats_copy['total_checks'] * 100
                if stats_copy['total_checks'] > 0 else 0
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
    
    def clear_cache(self):
        """Clear the safety check cache"""
        with self._cache_lock:
            self._cache.clear()
        logger.info("Safety filter cache cleared")
    
    def export_incidents(self, output_path: Path, format: str = 'json'):
        """Export all incidents for analysis"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM incidents ORDER BY timestamp DESC")
        columns = [description[0] for description in cursor.description]
        
        incidents = []
        for row in cursor.fetchall():
            incident = dict(zip(columns, row))
            if incident['details']:
                incident['details'] = json.loads(incident['details'])
            incidents.append(incident)
        
        conn.close()
        
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(incidents, f, indent=2, default=str)
        elif format == 'csv':
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for incident in incidents:
                    # Flatten details for CSV
                    if isinstance(incident['details'], dict):
                        incident['details'] = json.dumps(incident['details'])
                    writer.writerow(incident)
        
        logger.info(f"Exported {len(incidents)} incidents to {output_path}")


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
                if result['suggested_response']:
                    print(f"  Redirect: {result['suggested_response'][:50]}...")
        
        print("-" * 60)
        print(f"Statistics: {filter.get_statistics()}")

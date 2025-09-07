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
        
        # FIX: Using context manager to ensure connection is properly closed
        try:
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
                CREATE INDEX IF NOT EXISTS idx_child_id ON incidents(child_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON incidents(timestamp)
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS filter_stats (
                    date TEXT PRIMARY KEY,
                    total_checks INTEGER DEFAULT 0,
                    blocked_count INTEGER DEFAULT 0,
                    redirected_count INTEGER DEFAULT 0,
                    parent_alerts INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            logger.info("Safety database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize safety database: {e}")
            raise
        finally:
            # FIX: Always close the connection, even if an error occurs
            if conn:
                conn.close()
    
    def _load_safety_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load and compile safety patterns"""
        patterns = {
            'violence': [],
            'inappropriate': [],
            'personal_info': [],
            'dangerous': [],
            'scary': [],
            'bullying': [],
            'medical': [],
            'commercial': [],
            'profanity': []
        }
        
        # Load default patterns
        default_patterns = {
            'violence': [
                r'\b(kill|murder|stab|shoot|weapon|gun|knife|bomb|explode|fight|punch|hurt)\b',
                r'\b(blood|gore|death|die|dead|suicide|violent|attack|assault)\b'
            ],
            'inappropriate': [
                r'\b(sex|porn|nude|naked|kiss|date|romance|love|marry|pregnant)\b',
                r'\b(drug|alcohol|smoke|cigarette|beer|wine|drunk|high)\b'
            ],
            'personal_info': [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b',  # Credit cards
                r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b'  # Addresses
            ],
            'dangerous': [
                r'\b(poison|toxic|chemical|acid|bleach|gas|explosive|fire|burn)\b',
                r'\b(jump|climb|roof|bridge|cliff|dangerous|risk|dare)\b'
            ],
            'scary': [
                r'\b(monster|ghost|demon|devil|hell|nightmare|scary|horror|terror)\b',
                r'\b(zombie|vampire|werewolf|witch|haunted|creepy|dark)\b'
            ],
            'bullying': [
                r'\b(stupid|dumb|idiot|loser|ugly|fat|skinny|weak|worthless)\b',
                r'\b(hate|suck|worst|terrible|awful|disgusting|gross)\b'
            ],
            'medical': [
                r'\b(disease|cancer|tumor|surgery|hospital|emergency|pain|sick)\b',
                r'\b(medicine|pill|drug|prescription|doctor|nurse|treatment)\b'
            ],
            'commercial': [
                r'\b(buy|purchase|order|shop|sale|discount|price|cost|money)\b',
                r'\b(website|download|click|link|subscribe|signup|register)\b'
            ],
            'profanity': [
                # Comprehensive profanity list would be loaded from encrypted file
                r'\b(damn|hell|crap|suck|stupid|dumb)\b'  # Mild examples only
            ]
        }
        
        # Compile patterns for efficiency
        for category, pattern_list in default_patterns.items():
            patterns[category] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in pattern_list
            ]
        
        return patterns
    
    def check_message(self, text: str, age: int, child_id: str, session_id: Optional[str] = None) -> SafetyResult:
        """Main safety check method with comprehensive analysis"""
        # Check cache first
        cache_key = hashlib.md5(f"{text}{age}{child_id}".encode()).hexdigest()
        
        with self._cache_lock:
            if cache_key in self._cache:
                cached_result = self._cache[cache_key]
                logger.debug(f"Cache hit for message check")
                return cached_result
        
        # Normalize text
        normalized_text = self._normalize_text(text)
        
        # Run all safety checks
        flags = []
        categories_triggered = []
        severity = self.SEVERITY_SAFE
        
        # Check each category
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(normalized_text):
                    flags.append(f"{category}:{pattern.pattern[:30]}")
                    categories_triggered.append(category)
                    
                    # Determine severity based on category and age
                    cat_severity = self._calculate_severity(category, age)
                    severity = max(severity, cat_severity)
                    break
        
        # Determine if message is safe
        safe = len(flags) == 0
        score = 1.0 if safe else max(0.0, 1.0 - (severity * 0.25))
        
        # Determine primary category
        primary_category = SafetyCategory.SAFE
        if categories_triggered:
            # Map string category to enum
            category_map = {
                'violence': SafetyCategory.VIOLENCE,
                'inappropriate': SafetyCategory.INAPPROPRIATE,
                'personal_info': SafetyCategory.PERSONAL_INFO,
                'dangerous': SafetyCategory.DANGEROUS,
                'scary': SafetyCategory.SCARY,
                'bullying': SafetyCategory.BULLYING,
                'medical': SafetyCategory.MEDICAL,
                'commercial': SafetyCategory.COMMERCIAL,
                'profanity': SafetyCategory.PROFANITY
            }
            primary_category = category_map.get(categories_triggered[0], SafetyCategory.OFF_TOPIC)
        
        # Generate educational redirect if needed
        educational_redirect = None
        if not safe:
            educational_redirect = self._generate_educational_redirect(primary_category, age)
        
        # Determine if parent should be alerted
        parent_alert = severity >= self.SEVERITY_MODERATE
        
        # Create result
        result = SafetyResult(
            safe=safe,
            score=score,
            flags=flags,
            category=primary_category,
            suggested_response=educational_redirect,
            parent_alert=parent_alert,
            details={
                'normalized_text': normalized_text,
                'categories_triggered': categories_triggered,
                'age': age,
                'timestamp': datetime.now().isoformat()
            },
            educational_redirect=educational_redirect,
            severity_level=severity
        )
        
        # Cache result
        with self._cache_lock:
            self._cache[cache_key] = result
            # Limit cache size
            if len(self._cache) > 1000:
                self._cache.clear()
        
        # Log if not safe
        if not safe:
            self._log_incident(text, result, child_id, session_id)
        
        # Update statistics
        with self._stats_lock:
            self.statistics['total_checks'] += 1
            if not safe:
                self.statistics['blocked'] += 1
            if parent_alert:
                self.statistics['parent_alerts'] += 1
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent checking"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove accents
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Replace common substitutions
        substitutions = {
            '@': 'a', '4': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's',
            '7': 't', '!': 'i', '$': 's', '+': 't'
        }
        for old, new in substitutions.items():
            text = text.replace(old, new)
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        return text
    
    def _calculate_severity(self, category: str, age: int) -> int:
        """Calculate severity based on category and age"""
        # Younger children = higher severity for same content
        age_multiplier = max(1, (18 - age) / 10)
        
        base_severity = {
            'violence': self.SEVERITY_SEVERE,
            'inappropriate': self.SEVERITY_SEVERE,
            'personal_info': self.SEVERITY_CRITICAL,
            'dangerous': self.SEVERITY_CRITICAL,
            'scary': self.SEVERITY_MODERATE,
            'bullying': self.SEVERITY_MODERATE,
            'medical': self.SEVERITY_MILD,
            'commercial': self.SEVERITY_MILD,
            'profanity': self.SEVERITY_MILD
        }
        
        severity = base_severity.get(category, self.SEVERITY_MILD)
        
        # Adjust for age
        if age < 8:
            severity = min(self.SEVERITY_CRITICAL, severity + 1)
        elif age < 13:
            severity = min(self.SEVERITY_SEVERE, severity)
        
        return severity
    
    def _generate_educational_redirect(self, category: SafetyCategory, age: int) -> str:
        """Generate age-appropriate educational redirect"""
        redirects = {
            SafetyCategory.VIOLENCE: "Let's learn about conflict resolution and peaceful problem-solving instead!",
            SafetyCategory.INAPPROPRIATE: "How about we explore age-appropriate science topics?",
            SafetyCategory.PERSONAL_INFO: "Remember, keeping personal information private keeps you safe online!",
            SafetyCategory.DANGEROUS: "Safety first! Let's learn about safe science experiments instead.",
            SafetyCategory.SCARY: "Let's explore fascinating real-world science that's amazing but not scary!",
            SafetyCategory.BULLYING: "Everyone deserves respect. Let's focus on positive learning!",
            SafetyCategory.MEDICAL: "For health questions, it's best to talk to a parent or doctor.",
            SafetyCategory.COMMERCIAL: "Let's focus on learning rather than shopping!",
            SafetyCategory.PROFANITY: "Let's use respectful language that helps us learn better!",
            SafetyCategory.OFF_TOPIC: "Let's get back to exploring STEM topics together!"
        }
        
        base_redirect = redirects.get(category, "Let's explore something educational instead!")
        
        # Adjust language complexity for age
        if age < 8:
            base_redirect = base_redirect.replace("explore", "learn about")
            base_redirect = base_redirect.replace("fascinating", "cool")
        
        return base_redirect
    
    def _log_incident(self, text: str, result: SafetyResult, child_id: str, session_id: Optional[str]):
        """Log safety incident to database"""
        incident = SafetyIncident(
            id=hashlib.md5(f"{text}{datetime.now()}".encode()).hexdigest(),
            timestamp=datetime.now(),
            child_id=child_id,
            session_id=session_id or "unknown",
            input_text=text[:500],  # Truncate for storage
            category=result.category,
            severity=result.severity_level,
            action_taken="blocked" if not result.safe else "allowed",
            parent_notified=result.parent_alert,
            details=result.details
        )
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO incidents (
                    id, timestamp, child_id, session_id, input_text,
                    category, severity, action_taken, parent_notified, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                incident.id,
                incident.timestamp.isoformat(),
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
            
        except sqlite3.Error as e:
            logger.error(f"Failed to log incident: {e}")
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get current safety filter status"""
        with self._stats_lock:
            stats = dict(self.statistics)
        
        return {
            'operational': True,
            'total_checks': stats.get('total_checks', 0),
            'blocked_count': stats.get('blocked', 0),
            'parent_alerts': stats.get('parent_alerts', 0),
            'cache_size': len(self._cache),
            'patterns_loaded': sum(len(p) for p in self.patterns.values()),
            'categories': list(self.patterns.keys())
        }


# Production testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        filter = SafetyFilter(Path(tmp_dir))
        
        # Test messages
        test_cases = [
            ("Let's learn about photosynthesis!", 10, True),
            ("Can you tell me about guns?", 8, False),
            ("What's 2+2?", 6, True),
            ("My phone number is 555-1234", 12, False),
            ("I hate my stupid teacher", 14, False),
            ("How do volcanoes work?", 10, True)
        ]
        
        print("Safety Filter Test Results")
        print("=" * 50)
        
        for message, age, expected_safe in test_cases:
            result = filter.check_message(message, age, "test_child", "test_session")
            
            print(f"\nMessage: {message}")
            print(f"Age: {age}")
            print(f"Expected Safe: {expected_safe}")
            print(f"Result Safe: {result.safe}")
            print(f"Score: {result.score:.2f}")
            print(f"Category: {result.category.value}")
            
            if not result.safe:
                print(f"Redirect: {result.educational_redirect}")
            
            assert result.safe == expected_safe, f"Safety check failed for: {message}"
        
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        
        # Get system status
        status = filter.get_safety_status()
        print("\nSafety System Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")

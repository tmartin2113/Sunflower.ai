"""
Sunflower AI Safety Filter System
Version: 6.2
Production-ready implementation with comprehensive child safety features
"""

import re
import json
import sqlite3
import hashlib
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import uuid

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
    UNKNOWN = "unknown"


class SafetySeverity(Enum):
    """Severity levels for safety incidents"""
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SafetyResult:
    """Result of safety check"""
    safe: bool
    score: float
    category: SafetyCategory
    severity: SafetySeverity
    reason: Optional[str] = None
    educational_redirect: Optional[str] = None
    parent_alert: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


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
    """
    Production-ready safety filter for child protection
    Implements multiple layers of content filtering
    """
    
    def __init__(self, data_path: Path, config: Optional[Dict] = None):
        """Initialize safety filter with proper resource management"""
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.config = config or self._default_config()
        self.db_path = self.data_path / "safety.db"
        
        # Thread safety
        self._lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._stats_lock = threading.RLock()
        self._db_lock = threading.RLock()
        
        # Pattern cache
        self._cache: Dict[str, SafetyResult] = {}
        self._cache_size = 1000
        
        # Statistics tracking
        self.statistics = {
            'total_checks': 0,
            'blocked': 0,
            'redirected': 0,
            'parent_alerts': 0
        }
        
        # Initialize components
        self._init_database()
        self.patterns = self._load_safety_patterns()
        self.educational_redirects = self._load_educational_redirects()
        
        logger.info("Safety filter initialized successfully")
    
    def _default_config(self) -> Dict:
        """Default safety configuration"""
        return {
            'enabled': True,
            'strict_mode': True,
            'log_incidents': True,
            'cache_enabled': True,
            'parent_alerts': True,
            'educational_mode': True,
            'max_cache_size': 1000,
            'severity_threshold': SafetySeverity.LOW.value
        }
    
    @contextmanager
    def _get_db_connection(self):
        """
        Context manager for database connections with proper cleanup
        FIXED: Ensures connection is always closed even on errors
        """
        conn = None
        try:
            with self._db_lock:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=30.0,
                    isolation_level='DEFERRED',
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")
    
    def _init_database(self):
        """
        Initialize safety database with proper resource management
        FIXED: Connection is guaranteed to close even if initialization fails
        """
        conn = None
        try:
            # Use context manager for automatic cleanup
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Create incidents table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS incidents (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        child_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        input_text TEXT NOT NULL,
                        category TEXT NOT NULL,
                        severity INTEGER NOT NULL,
                        action_taken TEXT NOT NULL,
                        parent_notified INTEGER DEFAULT 0,
                        details TEXT
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_child_id ON incidents(child_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_session_id ON incidents(session_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON incidents(timestamp)
                ''')
                
                # Create filter statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS filter_stats (
                        date TEXT PRIMARY KEY,
                        total_checks INTEGER DEFAULT 0,
                        blocked_count INTEGER DEFAULT 0,
                        redirected_count INTEGER DEFAULT 0,
                        parent_alerts INTEGER DEFAULT 0
                    )
                ''')
                
                # Create pattern cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pattern_cache (
                        pattern_hash TEXT PRIMARY KEY,
                        pattern TEXT NOT NULL,
                        category TEXT NOT NULL,
                        severity INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        last_used TEXT NOT NULL,
                        hit_count INTEGER DEFAULT 0
                    )
                ''')
                
                conn.commit()
                logger.info("Safety database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize safety database: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing database: {e}")
            raise
    
    def _load_safety_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load and compile safety patterns with caching"""
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
        
        # Default patterns for each category
        default_patterns = {
            'violence': [
                r'\b(kill|murder|stab|shoot|weapon|gun|knife|bomb|explode|fight|punch|hurt|attack|assault)\b',
                r'\b(blood|gore|death|die|dead|suicide|violent)\b'
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
                r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Plaza|Pl)\b'  # Addresses
            ],
            'dangerous': [
                r'\b(fire|burn|poison|chemical|acid|electric|shock|drown)\b',
                r'\b(jump|cliff|roof|bridge|highway|traffic)\b'
            ],
            'scary': [
                r'\b(monster|ghost|demon|devil|hell|zombie|vampire|witch)\b',
                r'\b(nightmare|horror|terror|scream|haunted)\b'
            ],
            'bullying': [
                r'\b(stupid|dumb|idiot|loser|ugly|fat|hate)\b',
                r'\b(nobody likes|everyone hates|kill yourself)\b'
            ],
            'medical': [
                r'\b(cancer|disease|surgery|hospital|emergency|pain|sick|medicine)\b',
                r'\b(doctor|nurse|injection|needle|blood test)\b'
            ],
            'commercial': [
                r'\b(buy|purchase|order|shop|store|price|\$|dollar|sale)\b',
                r'\b(credit card|payment|checkout|cart|shipping)\b'
            ],
            'profanity': [
                r'\b(damn|hell|crap|suck|stupid|shut up)\b',
                # More severe profanity patterns would be added here
            ]
        }
        
        # Compile patterns with proper error handling
        for category, pattern_list in default_patterns.items():
            compiled_patterns = []
            for pattern in pattern_list:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    compiled_patterns.append(compiled)
                except re.error as e:
                    logger.error(f"Failed to compile pattern '{pattern}': {e}")
            patterns[category] = compiled_patterns
        
        # Try to load custom patterns from file
        custom_patterns_file = self.data_path / "custom_patterns.json"
        if custom_patterns_file.exists():
            try:
                with open(custom_patterns_file, 'r') as f:
                    custom = json.load(f)
                    for category, pattern_list in custom.items():
                        if category in patterns:
                            for pattern in pattern_list:
                                try:
                                    compiled = re.compile(pattern, re.IGNORECASE)
                                    patterns[category].append(compiled)
                                except re.error as e:
                                    logger.error(f"Failed to compile custom pattern '{pattern}': {e}")
            except Exception as e:
                logger.error(f"Failed to load custom patterns: {e}")
        
        return patterns
    
    def _load_educational_redirects(self) -> Dict[str, List[str]]:
        """Load educational redirect messages"""
        return {
            'violence': [
                "Let's learn about conflict resolution instead! How do people solve problems peacefully?",
                "That sounds intense! How about we explore how superheroes use their powers to help people?",
                "Violence isn't the answer! What are some ways people work together to make things better?"
            ],
            'inappropriate': [
                "That's a topic for when you're older! How about we learn about friendship instead?",
                "Let's focus on age-appropriate topics! What's your favorite subject in school?",
                "That's not something we discuss here. What science topic interests you?"
            ],
            'personal_info': [
                "Remember to keep personal information private! Let's talk about internet safety instead.",
                "It's important to protect your privacy online! What do you know about being safe on the internet?",
                "Never share personal details online! How about we learn about digital citizenship?"
            ],
            'dangerous': [
                "Safety first! Let's learn about how to stay safe instead.",
                "That could be dangerous! What safety rules do you know?",
                "Let's focus on safe activities! What's your favorite safe outdoor game?"
            ],
            'scary': [
                "That might be too scary! How about a fun adventure story instead?",
                "Let's keep things positive! What makes you happy?",
                "Some things can be frightening. What's your favorite happy story?"
            ],
            'bullying': [
                "Words can hurt! Let's practice being kind instead.",
                "Everyone deserves respect! How can we be good friends to others?",
                "Kindness matters! What nice thing did someone do for you recently?"
            ],
            'default': [
                "Let's talk about something educational! What would you like to learn about?",
                "How about we explore a STEM topic? Science, Technology, Engineering, or Math?",
                "That's not quite right for our conversation. What school subject interests you most?"
            ]
        }
    
    def check_message(self, message: str, age: int, child_id: str, session_id: str) -> SafetyResult:
        """
        Check message for safety with multi-layer filtering
        Uses proper resource management for all operations
        """
        with self._stats_lock:
            self.statistics['total_checks'] += 1
        
        # Check cache first
        cache_key = self._get_cache_key(message, age)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Multi-layer safety check
        result = self._perform_safety_check(message, age)
        
        # Log if necessary
        if not result.safe and self.config['log_incidents']:
            self._log_incident(result, child_id, session_id, message)
        
        # Update statistics
        with self._stats_lock:
            if not result.safe:
                self.statistics['blocked'] += 1
                if result.educational_redirect:
                    self.statistics['redirected'] += 1
                if result.parent_alert:
                    self.statistics['parent_alerts'] += 1
        
        # Cache result
        self._cache_result(cache_key, result)
        
        # Persist statistics periodically
        if self.statistics['total_checks'] % 100 == 0:
            self._persist_statistics()
        
        return result
    
    def _get_cache_key(self, message: str, age: int) -> str:
        """Generate cache key for message"""
        content = f"{message}:{age}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[SafetyResult]:
        """Get cached result if available"""
        if not self.config['cache_enabled']:
            return None
        
        with self._cache_lock:
            return self._cache.get(cache_key)
    
    def _cache_result(self, cache_key: str, result: SafetyResult):
        """Cache safety check result"""
        if not self.config['cache_enabled']:
            return
        
        with self._cache_lock:
            # Implement LRU by removing oldest if at capacity
            if len(self._cache) >= self._cache_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            
            self._cache[cache_key] = result
    
    def _perform_safety_check(self, message: str, age: int) -> SafetyResult:
        """Perform multi-layer safety check"""
        message_lower = message.lower()
        
        # Layer 1: Check for blocked patterns
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(message_lower):
                    severity = self._calculate_severity(category, message_lower)
                    redirect = self._get_educational_redirect(category)
                    
                    return SafetyResult(
                        safe=False,
                        score=0.0,
                        category=SafetyCategory(category),
                        severity=severity,
                        reason=f"Content matched {category} pattern",
                        educational_redirect=redirect,
                        parent_alert=severity.value >= SafetySeverity.HIGH.value,
                        details={'pattern_category': category}
                    )
        
        # Layer 2: Context analysis
        context_safe, context_reason = self._check_context(message, age)
        if not context_safe:
            return SafetyResult(
                safe=False,
                score=0.3,
                category=SafetyCategory.UNKNOWN,
                severity=SafetySeverity.MEDIUM,
                reason=context_reason,
                educational_redirect=self._get_educational_redirect('default'),
                parent_alert=False
            )
        
        # Layer 3: Age appropriateness
        age_appropriate, age_reason = self._check_age_appropriateness(message, age)
        if not age_appropriate:
            return SafetyResult(
                safe=False,
                score=0.5,
                category=SafetyCategory.INAPPROPRIATE,
                severity=SafetySeverity.LOW,
                reason=age_reason,
                educational_redirect=self._get_educational_redirect('default'),
                parent_alert=False
            )
        
        # Message is safe
        return SafetyResult(
            safe=True,
            score=1.0,
            category=SafetyCategory.SAFE,
            severity=SafetySeverity.INFO,
            reason="Content passed all safety checks"
        )
    
    def _calculate_severity(self, category: str, message: str) -> SafetySeverity:
        """Calculate severity based on category and content"""
        high_severity_categories = {'violence', 'personal_info', 'dangerous'}
        medium_severity_categories = {'inappropriate', 'bullying', 'scary'}
        
        if category in high_severity_categories:
            return SafetySeverity.HIGH
        elif category in medium_severity_categories:
            return SafetySeverity.MEDIUM
        else:
            return SafetySeverity.LOW
    
    def _check_context(self, message: str, age: int) -> Tuple[bool, Optional[str]]:
        """Check message context for safety"""
        # Check message length (possible spam or confusion)
        if len(message) > 500:
            return False, "Message too long"
        
        # Check for repeated characters (keyboard mashing)
        if re.search(r'(.)\1{5,}', message):
            return False, "Detected keyboard mashing"
        
        # Check for all caps (shouting)
        words = message.split()
        if len(words) > 3 and all(word.isupper() for word in words if len(word) > 2):
            return False, "Please don't shout"
        
        return True, None
    
    def _check_age_appropriateness(self, message: str, age: int) -> Tuple[bool, Optional[str]]:
        """Check if content is age-appropriate"""
        # Complex vocabulary check for young children
        if age < 8:
            complex_words = re.findall(r'\b\w{10,}\b', message)
            if len(complex_words) > 2:
                return False, "Content may be too complex for age group"
        
        # Topic complexity check
        complex_topics = ['quantum', 'calculus', 'algorithm', 'philosophy', 'psychology']
        if age < 12 and any(topic in message.lower() for topic in complex_topics):
            return False, "Topic may be too advanced for age group"
        
        return True, None
    
    def _get_educational_redirect(self, category: str) -> str:
        """Get educational redirect message"""
        import random
        redirects = self.educational_redirects.get(category, self.educational_redirects['default'])
        return random.choice(redirects)
    
    def _log_incident(self, result: SafetyResult, child_id: str, session_id: str, message: str):
        """Log safety incident to database with proper resource management"""
        incident = SafetyIncident(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            child_id=child_id,
            session_id=session_id,
            input_text=message[:200],  # Truncate for storage
            category=result.category,
            severity=result.severity.value,
            action_taken="blocked" if not result.safe else "allowed",
            parent_notified=result.parent_alert,
            details=result.details
        )
        
        try:
            with self._get_db_connection() as conn:
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
        except sqlite3.Error as e:
            logger.error(f"Failed to log incident: {e}")
    
    def _persist_statistics(self):
        """Persist statistics to database with proper resource management"""
        today = datetime.now().date().isoformat()
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                with self._stats_lock:
                    cursor.execute('''
                        INSERT OR REPLACE INTO filter_stats (
                            date, total_checks, blocked_count, redirected_count, parent_alerts
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        today,
                        self.statistics['total_checks'],
                        self.statistics['blocked'],
                        self.statistics['redirected'],
                        self.statistics['parent_alerts']
                    ))
                
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to persist statistics: {e}")
    
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
            'categories': list(self.patterns.keys()),
            'database': 'connected' if self.db_path.exists() else 'not initialized'
        }
    
    def get_incidents_for_review(self, child_id: str, start_date: Optional[datetime] = None) -> List[Dict]:
        """Get incidents for parent review with proper resource management"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        
        incidents = []
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM incidents 
                    WHERE child_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (child_id, start_date.isoformat()))
                
                for row in cursor.fetchall():
                    incidents.append({
                        'id': row['id'],
                        'timestamp': row['timestamp'],
                        'category': row['category'],
                        'severity': row['severity'],
                        'input_text': row['input_text'],
                        'action_taken': row['action_taken'],
                        'parent_notified': bool(row['parent_notified'])
                    })
        
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve incidents: {e}")
        
        return incidents
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up safety filter resources")
        
        # Persist final statistics
        self._persist_statistics()
        
        # Clear cache
        with self._cache_lock:
            self._cache.clear()
        
        logger.info("Safety filter cleanup complete")


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
            ("How do volcanoes work?", 10, True),
            ("Tell me about quantum physics", 7, False),  # Too complex for age
            ("HELP ME NOW!!!", 10, False),  # All caps
            ("aaaaaaaaaaaa", 8, False),  # Keyboard mashing
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
            print(f"Severity: {result.severity.name}")
            
            if not result.safe:
                print(f"Reason: {result.reason}")
                print(f"Redirect: {result.educational_redirect}")
            
            assert result.safe == expected_safe, f"Safety check failed for: {message}"
        
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        
        # Get system status
        status = filter.get_safety_status()
        print("\nSafety System Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Cleanup
        filter.cleanup()

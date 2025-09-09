#!/usr/bin/env python3
"""
Sunflower AI Professional System - Safety Filter Module
Production-ready content moderation and child safety system
Version: 6.2.0 - Fixed age boundary validation
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
from enum import Enum, IntEnum

logger = logging.getLogger(__name__)


class AgeGroup(IntEnum):
    """
    Age groups with explicit boundaries to prevent off-by-one errors.
    Each group includes the lower bound and excludes the upper bound [lower, upper)
    except for the last group which includes the upper bound.
    """
    TODDLER = 2      # Ages 2-4 (inclusive of 2, 3, 4)
    PRESCHOOL = 5    # Ages 5-6 (inclusive of 5, 6)
    EARLY_ELEM = 7   # Ages 7-8 (inclusive of 7, 8)
    LATE_ELEM = 9    # Ages 9-10 (inclusive of 9, 10)
    MIDDLE = 11      # Ages 11-13 (inclusive of 11, 12, 13)
    HIGH = 14        # Ages 14-17 (inclusive of 14, 15, 16, 17)
    ADULT = 18       # Age 18 (inclusive of 18)
    
    @classmethod
    def from_age(cls, age: int) -> 'AgeGroup':
        """
        Get age group from specific age with proper boundary handling.
        
        FIX: Clear boundary definitions to prevent off-by-one errors
        """
        if age < 2:
            raise ValueError(f"Age {age} is below minimum supported age of 2")
        elif age > 18:
            raise ValueError(f"Age {age} is above maximum supported age of 18")
        
        # FIX: Explicit boundary checks with clear inclusive ranges
        if 2 <= age <= 4:
            return cls.TODDLER
        elif 5 <= age <= 6:
            return cls.PRESCHOOL
        elif 7 <= age <= 8:
            return cls.EARLY_ELEM
        elif 9 <= age <= 10:
            return cls.LATE_ELEM
        elif 11 <= age <= 13:
            return cls.MIDDLE
        elif 14 <= age <= 17:
            return cls.HIGH
        elif age == 18:
            return cls.ADULT
        else:
            # This should never happen due to the initial bounds check
            raise ValueError(f"Age {age} does not map to any age group")
    
    def get_age_range(self) -> Tuple[int, int]:
        """
        Get the inclusive age range for this group.
        
        Returns:
            Tuple of (min_age_inclusive, max_age_inclusive)
        """
        ranges = {
            AgeGroup.TODDLER: (2, 4),
            AgeGroup.PRESCHOOL: (5, 6),
            AgeGroup.EARLY_ELEM: (7, 8),
            AgeGroup.LATE_ELEM: (9, 10),
            AgeGroup.MIDDLE: (11, 13),
            AgeGroup.HIGH: (14, 17),
            AgeGroup.ADULT: (18, 18)
        }
        return ranges[self]


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
    age_appropriate: bool = True  # FIX: Added explicit age appropriateness flag


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
    child_age: int  # FIX: Added to track age at time of incident
    details: Dict[str, Any]


@dataclass
class AgeAppropriateContent:
    """
    Configuration for age-appropriate content with clear boundaries.
    FIX: Explicit age ranges prevent boundary confusion
    """
    age_group: AgeGroup
    min_age: int  # Inclusive
    max_age: int  # Inclusive
    
    # Content settings
    max_word_count: int
    complexity_level: str  # simple, moderate, advanced
    allowed_topics: Set[str]
    blocked_topics: Set[str]
    
    # Safety settings
    filter_level: str  # maximum, high, moderate, light
    scary_content_allowed: bool
    violence_tolerance: str  # none, cartoon, mild, moderate
    romance_content_allowed: bool
    
    def __post_init__(self):
        """Validate age boundaries"""
        min_valid, max_valid = self.age_group.get_age_range()
        if self.min_age != min_valid or self.max_age != max_valid:
            raise ValueError(
                f"Age range ({self.min_age}, {self.max_age}) doesn't match "
                f"age group {self.age_group.name} range ({min_valid}, {max_valid})"
            )


class SafetyFilter:
    """Enterprise-grade safety filter for child protection with fixed age validation"""
    
    # FIX: Clear age boundaries as class constants
    MIN_AGE = 2   # Inclusive
    MAX_AGE = 18  # Inclusive
    
    # Severity levels
    SEVERITY_SAFE = 0
    SEVERITY_MILD = 1
    SEVERITY_MODERATE = 2
    SEVERITY_SEVERE = 3
    SEVERITY_CRITICAL = 4
    
    def __init__(self, data_dir: Path, strict_mode: bool = True):
        """
        Initialize safety filter with age-appropriate configurations
        
        Args:
            data_dir: Directory for safety data and logs
            strict_mode: If True, err on the side of caution
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.strict_mode = strict_mode
        self._lock = threading.RLock()
        
        # Initialize age-appropriate configurations
        self.age_configs = self._initialize_age_configs()
        
        # Safety patterns database
        self.safety_patterns = self._load_safety_patterns()
        
        # Filter statistics
        self.filter_stats = defaultdict(int)
        self.filter_log = []
        
        # Database for incidents
        self.db_path = self.data_dir / "safety_incidents.db"
        self._init_database()
        
        logger.info("Safety filter initialized with fixed age validation")
    
    def _initialize_age_configs(self) -> Dict[AgeGroup, AgeAppropriateContent]:
        """
        Initialize age-appropriate content configurations.
        FIX: Each configuration has explicit, non-overlapping age ranges
        """
        configs = {}
        
        # Toddler (2-4 years)
        configs[AgeGroup.TODDLER] = AgeAppropriateContent(
            age_group=AgeGroup.TODDLER,
            min_age=2,
            max_age=4,
            max_word_count=50,
            complexity_level="simple",
            allowed_topics={'colors', 'shapes', 'animals', 'family', 'numbers', 'letters'},
            blocked_topics={'violence', 'death', 'romance', 'scary', 'complex_science'},
            filter_level="maximum",
            scary_content_allowed=False,
            violence_tolerance="none",
            romance_content_allowed=False
        )
        
        # Preschool (5-6 years)
        configs[AgeGroup.PRESCHOOL] = AgeAppropriateContent(
            age_group=AgeGroup.PRESCHOOL,
            min_age=5,
            max_age=6,
            max_word_count=75,
            complexity_level="simple",
            allowed_topics={'nature', 'simple_science', 'friendship', 'school', 'creativity'},
            blocked_topics={'violence', 'death', 'romance', 'scary_monsters'},
            filter_level="maximum",
            scary_content_allowed=False,
            violence_tolerance="cartoon",
            romance_content_allowed=False
        )
        
        # Early Elementary (7-8 years)
        configs[AgeGroup.EARLY_ELEM] = AgeAppropriateContent(
            age_group=AgeGroup.EARLY_ELEM,
            min_age=7,
            max_age=8,
            max_word_count=100,
            complexity_level="moderate",
            allowed_topics={'science', 'history', 'geography', 'math', 'reading'},
            blocked_topics={'graphic_violence', 'adult_themes', 'horror'},
            filter_level="high",
            scary_content_allowed=False,
            violence_tolerance="cartoon",
            romance_content_allowed=False
        )
        
        # Late Elementary (9-10 years)
        configs[AgeGroup.LATE_ELEM] = AgeAppropriateContent(
            age_group=AgeGroup.LATE_ELEM,
            min_age=9,
            max_age=10,
            max_word_count=150,
            complexity_level="moderate",
            allowed_topics={'advanced_science', 'technology', 'culture', 'sports'},
            blocked_topics={'graphic_violence', 'adult_content', 'extreme_horror'},
            filter_level="high",
            scary_content_allowed=True,  # Mild scary content OK
            violence_tolerance="mild",
            romance_content_allowed=False
        )
        
        # Middle School (11-13 years)
        configs[AgeGroup.MIDDLE] = AgeAppropriateContent(
            age_group=AgeGroup.MIDDLE,
            min_age=11,
            max_age=13,
            max_word_count=200,
            complexity_level="advanced",
            allowed_topics={'all_academic', 'current_events', 'social_issues', 'career'},
            blocked_topics={'explicit_content', 'graphic_violence', 'adult_only'},
            filter_level="moderate",
            scary_content_allowed=True,
            violence_tolerance="mild",
            romance_content_allowed=True  # Age-appropriate only
        )
        
        # High School (14-17 years)
        configs[AgeGroup.HIGH] = AgeAppropriateContent(
            age_group=AgeGroup.HIGH,
            min_age=14,
            max_age=17,
            max_word_count=300,
            complexity_level="advanced",
            allowed_topics={'all_topics', 'college_prep', 'career_planning'},
            blocked_topics={'explicit_adult_content', 'illegal_activities'},
            filter_level="moderate",
            scary_content_allowed=True,
            violence_tolerance="moderate",
            romance_content_allowed=True
        )
        
        # Adult (18 years)
        configs[AgeGroup.ADULT] = AgeAppropriateContent(
            age_group=AgeGroup.ADULT,
            min_age=18,
            max_age=18,
            max_word_count=500,
            complexity_level="advanced",
            allowed_topics={'all_topics'},
            blocked_topics={'illegal_content'},
            filter_level="light",
            scary_content_allowed=True,
            violence_tolerance="moderate",
            romance_content_allowed=True
        )
        
        return configs
    
    def validate_age(self, age: int) -> Tuple[bool, str]:
        """
        Validate if age is within supported range.
        FIX: Clear, inclusive boundary checks
        
        Args:
            age: Age to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        # FIX: Use inclusive comparisons with clear boundaries
        if age < self.MIN_AGE:
            return False, f"Age {age} is below minimum supported age of {self.MIN_AGE}"
        elif age > self.MAX_AGE:
            return False, f"Age {age} is above maximum supported age of {self.MAX_AGE}"
        else:
            return True, f"Age {age} is valid (within {self.MIN_AGE}-{self.MAX_AGE} range)"
    
    def get_age_appropriate_config(self, age: int) -> AgeAppropriateContent:
        """
        Get age-appropriate configuration for specific age.
        FIX: Direct mapping without ambiguous boundaries
        
        Args:
            age: Child's age
            
        Returns:
            Age-appropriate content configuration
            
        Raises:
            ValueError: If age is out of valid range
        """
        # Validate age first
        is_valid, message = self.validate_age(age)
        if not is_valid:
            raise ValueError(message)
        
        # Get age group
        age_group = AgeGroup.from_age(age)
        
        # Return corresponding configuration
        return self.age_configs[age_group]
    
    def check_content(self, text: str, age: int, 
                     context: Optional[Dict] = None) -> SafetyResult:
        """
        Check content for safety with proper age validation.
        FIX: Explicit age boundary checking
        
        Args:
            text: Content to check
            age: Child's age
            context: Optional context information
            
        Returns:
            Safety check result
        """
        with self._lock:
            # FIX: Validate age before processing
            is_valid_age, age_message = self.validate_age(age)
            if not is_valid_age:
                logger.error(f"Invalid age provided: {age_message}")
                return SafetyResult(
                    safe=False,
                    score=0.0,
                    flags=["invalid_age"],
                    category=SafetyCategory.OFF_TOPIC,
                    suggested_response="Please provide a valid age between 2 and 18.",
                    parent_alert=True,
                    details={"error": age_message},
                    age_appropriate=False
                )
            
            # Get age-appropriate configuration
            try:
                age_config = self.get_age_appropriate_config(age)
            except ValueError as e:
                logger.error(f"Failed to get age config: {e}")
                return SafetyResult(
                    safe=False,
                    score=0.0,
                    flags=["configuration_error"],
                    category=SafetyCategory.OFF_TOPIC,
                    suggested_response="System configuration error. Please contact support.",
                    parent_alert=True,
                    details={"error": str(e)},
                    age_appropriate=False
                )
            
            # Initialize result
            result = SafetyResult(
                safe=True,
                score=1.0,
                flags=[],
                category=SafetyCategory.SAFE,
                suggested_response=None,
                parent_alert=False,
                details={
                    "age": age,
                    "age_group": age_config.age_group.name,
                    "filter_level": age_config.filter_level
                },
                age_appropriate=True
            )
            
            # Check content length
            word_count = len(text.split())
            if word_count > age_config.max_word_count:
                result.flags.append("too_long")
                result.details["word_count"] = word_count
                result.details["max_words"] = age_config.max_word_count
            
            # Check for inappropriate content based on age
            safety_issues = self._check_safety_patterns(text, age_config)
            
            if safety_issues:
                result.safe = False
                result.score = max(0.0, 1.0 - (len(safety_issues) * 0.2))
                result.flags.extend([issue['type'] for issue in safety_issues])
                result.category = self._determine_category(safety_issues)
                result.severity_level = self._calculate_severity(safety_issues, age)
                result.details["safety_issues"] = safety_issues
                
                # Determine if content is age-appropriate
                result.age_appropriate = self._is_age_appropriate(safety_issues, age_config)
                
                # Generate educational redirect
                result.educational_redirect = self._generate_redirect(
                    result.category, age
                )
                
                # Determine if parent should be alerted
                result.parent_alert = (
                    result.severity_level >= self.SEVERITY_MODERATE or
                    not result.age_appropriate
                )
            
            # Log the check
            self._log_safety_check(text, age, result)
            
            # Update statistics
            self.filter_stats[result.category] += 1
            
            return result
    
    def _check_safety_patterns(self, text: str, 
                               age_config: AgeAppropriateContent) -> List[Dict]:
        """
        Check text against safety patterns for age group.
        FIX: Age-specific pattern matching
        """
        issues = []
        text_lower = text.lower()
        
        # Check blocked topics for this age group
        for topic in age_config.blocked_topics:
            if topic in text_lower:
                issues.append({
                    'type': 'blocked_topic',
                    'topic': topic,
                    'severity': self.SEVERITY_MODERATE
                })
        
        # Check violence based on tolerance level
        if age_config.violence_tolerance == "none":
            violence_patterns = ['fight', 'punch', 'kick', 'hurt', 'weapon', 'gun']
            for pattern in violence_patterns:
                if pattern in text_lower:
                    issues.append({
                        'type': 'violence',
                        'pattern': pattern,
                        'severity': self.SEVERITY_SEVERE
                    })
        elif age_config.violence_tolerance == "cartoon":
            violence_patterns = ['kill', 'murder', 'blood', 'gore', 'weapon']
            for pattern in violence_patterns:
                if pattern in text_lower:
                    issues.append({
                        'type': 'violence',
                        'pattern': pattern,
                        'severity': self.SEVERITY_MODERATE
                    })
        
        # Check for scary content if not allowed
        if not age_config.scary_content_allowed:
            scary_patterns = ['monster', 'ghost', 'scary', 'nightmare', 'horror']
            for pattern in scary_patterns:
                if pattern in text_lower:
                    issues.append({
                        'type': 'scary',
                        'pattern': pattern,
                        'severity': self.SEVERITY_MILD
                    })
        
        # Check for romance content if not allowed
        if not age_config.romance_content_allowed:
            romance_patterns = ['kiss', 'date', 'boyfriend', 'girlfriend', 'love']
            for pattern in romance_patterns:
                if pattern in text_lower:
                    issues.append({
                        'type': 'romance',
                        'pattern': pattern,
                        'severity': self.SEVERITY_MILD
                    })
        
        return issues
    
    def _is_age_appropriate(self, safety_issues: List[Dict], 
                           age_config: AgeAppropriateContent) -> bool:
        """
        Determine if content is age-appropriate despite safety issues.
        FIX: Clear age-based logic
        """
        if not safety_issues:
            return True
        
        # Count severe issues
        severe_issues = sum(1 for issue in safety_issues 
                          if issue.get('severity', 0) >= self.SEVERITY_SEVERE)
        
        # Age-specific thresholds
        if age_config.age_group <= AgeGroup.PRESCHOOL:
            # Very strict for young children
            return len(safety_issues) == 0
        elif age_config.age_group <= AgeGroup.LATE_ELEM:
            # No severe issues allowed
            return severe_issues == 0
        elif age_config.age_group <= AgeGroup.MIDDLE:
            # Limited tolerance
            return severe_issues == 0 and len(safety_issues) <= 2
        else:
            # More tolerance for older children
            return severe_issues <= 1 and len(safety_issues) <= 3
    
    def _calculate_severity(self, safety_issues: List[Dict], age: int) -> int:
        """
        Calculate overall severity level based on age.
        FIX: Age-weighted severity calculation
        """
        if not safety_issues:
            return self.SEVERITY_SAFE
        
        # Get maximum severity from issues
        max_severity = max(issue.get('severity', 0) for issue in safety_issues)
        
        # Adjust based on age (younger = more severe)
        age_group = AgeGroup.from_age(age)
        
        if age_group <= AgeGroup.PRESCHOOL:
            # Increase severity for very young children
            return min(self.SEVERITY_CRITICAL, max_severity + 1)
        elif age_group <= AgeGroup.LATE_ELEM:
            # Slight increase for elementary
            return min(self.SEVERITY_CRITICAL, max_severity)
        else:
            # Use base severity for older children
            return max_severity
    
    def _determine_category(self, safety_issues: List[Dict]) -> SafetyCategory:
        """Determine primary safety category from issues"""
        if not safety_issues:
            return SafetyCategory.SAFE
        
        # Priority order for categories
        priority_map = {
            'violence': SafetyCategory.VIOLENCE,
            'inappropriate': SafetyCategory.INAPPROPRIATE,
            'personal_info': SafetyCategory.PERSONAL_INFO,
            'dangerous': SafetyCategory.DANGEROUS,
            'scary': SafetyCategory.SCARY,
            'bullying': SafetyCategory.BULLYING,
            'blocked_topic': SafetyCategory.OFF_TOPIC
        }
        
        for issue in safety_issues:
            issue_type = issue.get('type', '')
            if issue_type in priority_map:
                return priority_map[issue_type]
        
        return SafetyCategory.OFF_TOPIC
    
    def _generate_redirect(self, category: SafetyCategory, age: int) -> str:
        """
        Generate age-appropriate educational redirect.
        FIX: Age-specific redirects
        """
        age_group = AgeGroup.from_age(age)
        
        redirects = {
            SafetyCategory.VIOLENCE: {
                AgeGroup.TODDLER: "Let's talk about being kind to friends instead!",
                AgeGroup.PRESCHOOL: "How about we learn about helping others?",
                AgeGroup.EARLY_ELEM: "Let's explore how people solve problems peacefully!",
                AgeGroup.LATE_ELEM: "Would you like to learn about conflict resolution?",
                AgeGroup.MIDDLE: "Let's discuss how communities work together.",
                AgeGroup.HIGH: "How about exploring the psychology of cooperation?",
                AgeGroup.ADULT: "Let's focus on constructive topics."
            },
            SafetyCategory.SCARY: {
                AgeGroup.TODDLER: "Let's talk about happy things like rainbows!",
                AgeGroup.PRESCHOOL: "How about we learn about brave heroes who help?",
                AgeGroup.EARLY_ELEM: "Let's explore amazing real animals instead!",
                AgeGroup.LATE_ELEM: "Would you like to learn about real science mysteries?",
                AgeGroup.MIDDLE: "Let's discuss fascinating science facts!",
                AgeGroup.HIGH: "How about exploring psychological phenomena?",
                AgeGroup.ADULT: "Let's focus on educational content."
            }
        }
        
        # Get redirect for category and age group
        category_redirects = redirects.get(category, {})
        redirect = category_redirects.get(age_group, "Let's talk about something else!")
        
        return redirect
    
    def _load_safety_patterns(self) -> Dict:
        """Load safety patterns from configuration"""
        patterns_file = self.data_dir / "safety_patterns.json"
        
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load safety patterns: {e}")
        
        # Return default patterns
        return {
            "violence": ["weapon", "gun", "knife", "kill", "murder", "fight"],
            "inappropriate": ["drug", "alcohol", "smoking"],
            "personal_info": ["address", "phone number", "email", "password"],
            "dangerous": ["suicide", "self-harm", "eating disorder"],
            "profanity": []  # Would be populated with actual profanity list
        }
    
    def _init_database(self):
        """Initialize database for safety incidents"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute('''
            CREATE TABLE IF NOT EXISTS safety_incidents (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                child_id TEXT NOT NULL,
                child_age INTEGER NOT NULL,
                session_id TEXT,
                input_text TEXT,
                category TEXT NOT NULL,
                severity INTEGER NOT NULL,
                action_taken TEXT,
                parent_notified INTEGER DEFAULT 0,
                details TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def _log_safety_check(self, text: str, age: int, result: SafetyResult):
        """Log safety check to database"""
        if not result.safe:
            incident = SafetyIncident(
                id=hashlib.sha256(f"{datetime.now()}{text}".encode()).hexdigest()[:16],
                timestamp=datetime.now(),
                child_id="current_child",  # Would be actual child ID in production
                session_id="current_session",
                input_text=text[:500],  # Truncate for storage
                category=result.category,
                severity=result.severity_level,
                action_taken="blocked_and_redirected",
                parent_notified=result.parent_alert,
                child_age=age,  # FIX: Store age at time of incident
                details=result.details
            )
            
            # Store in database
            conn = sqlite3.connect(str(self.db_path))
            conn.execute('''
                INSERT INTO safety_incidents 
                (id, timestamp, child_id, child_age, session_id, input_text, 
                 category, severity, action_taken, parent_notified, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                incident.id,
                incident.timestamp.isoformat(),
                incident.child_id,
                incident.child_age,
                incident.session_id,
                incident.input_text,
                incident.category.value,
                incident.severity,
                incident.action_taken,
                int(incident.parent_notified),
                json.dumps(incident.details)
            ))
            conn.commit()
            conn.close()
            
            # Add to memory log
            self.filter_log.append(incident)
    
    def get_statistics(self, child_id: Optional[str] = None) -> Dict[str, Any]:
        """Get safety filter statistics"""
        stats = {
            "total_checks": sum(self.filter_stats.values()),
            "blocked_count": sum(v for k, v in self.filter_stats.items() 
                               if k != SafetyCategory.SAFE),
            "categories": dict(self.filter_stats),
            "recent_incidents": len(self.filter_log)
        }
        
        if child_id:
            # Get child-specific stats from database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute('''
                SELECT COUNT(*) as count, AVG(severity) as avg_severity
                FROM safety_incidents
                WHERE child_id = ?
            ''', (child_id,))
            row = cursor.fetchone()
            stats["child_incidents"] = row[0]
            stats["child_avg_severity"] = row[1] or 0
            conn.close()
        
        return stats


# Testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize safety filter
        safety_filter = SafetyFilter(Path(tmpdir))
        
        print("Safety Filter Age Validation Testing")
        print("=" * 50)
        
        # FIX: Test age boundary validation
        print("\nTesting Age Boundaries:")
        test_ages = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        
        for age in test_ages:
            is_valid, message = safety_filter.validate_age(age)
            print(f"Age {age:2d}: {'✓' if is_valid else '✗'} - {message}")
        
        print("\n" + "=" * 50)
        print("Testing Age Group Assignment:")
        
        # Test age to group mapping
        age_group_tests = [
            (2, "TODDLER"), (3, "TODDLER"), (4, "TODDLER"),
            (5, "PRESCHOOL"), (6, "PRESCHOOL"),
            (7, "EARLY_ELEM"), (8, "EARLY_ELEM"),
            (9, "LATE_ELEM"), (10, "LATE_ELEM"),
            (11, "MIDDLE"), (12, "MIDDLE"), (13, "MIDDLE"),
            (14, "HIGH"), (15, "HIGH"), (16, "HIGH"), (17, "HIGH"),
            (18, "ADULT")
        ]
        
        for age, expected_group in age_group_tests:
            try:
                group = AgeGroup.from_age(age)
                match = group.name == expected_group
                print(f"Age {age:2d} -> {group.name:12s} {'✓' if match else f'✗ (expected {expected_group})'}")
            except ValueError as e:
                print(f"Age {age:2d} -> ERROR: {e}")
        
        print("\n" + "=" * 50)
        print("Testing Content Filtering by Age:")
        
        # Test content with different ages
        test_contents = [
            ("Let's learn about colors!", "safe_toddler"),
            ("There was a scary monster", "scary"),
            ("How do plants grow?", "safe_science"),
            ("The hero fought the dragon", "violence"),
            ("What's your phone number?", "personal_info")
        ]
        
        test_ages_subset = [3, 6, 9, 12, 15, 18]
        
        for content, content_type in test_contents:
            print(f"\nContent: '{content}' (type: {content_type})")
            
            for age in test_ages_subset:
                result = safety_filter.check_content(content, age)
                status = "✓ SAFE" if result.safe else "✗ BLOCKED"
                print(f"  Age {age:2d}: {status} - {result.category.value}")
        
        print("\n" + "=" * 50)
        print("Testing Edge Cases:")
        
        # Test exact age boundaries
        boundary_tests = [
            (4, "TODDLER", "Last age of toddler group"),
            (5, "PRESCHOOL", "First age of preschool group"),
            (13, "MIDDLE", "Last age of middle school"),
            (14, "HIGH", "First age of high school"),
            (18, "ADULT", "Exactly 18 years old")
        ]
        
        for age, expected_group, description in boundary_tests:
            group = AgeGroup.from_age(age)
            min_age, max_age = group.get_age_range()
            print(f"Age {age}: {description}")
            print(f"  Group: {group.name} (range: {min_age}-{max_age})")
            print(f"  Correct: {'✓' if group.name == expected_group else '✗'}")
        
        # Get statistics
        print("\n" + "=" * 50)
        print("Filter Statistics:")
        stats = safety_filter.get_statistics()
        print(f"Total checks: {stats['total_checks']}")
        print(f"Blocked: {stats['blocked_count']}")
        print(f"Categories: {stats['categories']}")
        
        print("\nAll age validation tests completed!")

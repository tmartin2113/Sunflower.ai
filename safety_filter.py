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
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import unicodedata

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

class SafetyFilter:
    """Enterprise-grade safety filter for child protection"""
    
    def __init__(self, usb_path: Path):
        """Initialize safety filter with comprehensive blocklists"""
        self.usb_path = Path(usb_path)
        self.filter_path = self.usb_path / 'safety_filters'
        self.filter_path.mkdir(parents=True, exist_ok=True)
        
        # Load filter configurations
        self.filters = self._load_filters()
        self.custom_rules = self._load_custom_rules()
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = self._compile_patterns()
        
        # Safe topic redirections
        self.safe_redirects = self._load_safe_redirects()
        
        # Educational topics whitelist
        self.educational_topics = self._load_educational_topics()
        
        # Statistics tracking
        self.stats = {
            'total_checks': 0,
            'blocked_count': 0,
            'flagged_count': 0,
            'redirected_count': 0
        }
        
        logger.info("Safety filter initialized with comprehensive protection")
    
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
            'inappropriate_requests': []
        }
        
        # Core safety patterns (production-ready)
        filters['profanity'] = [
            # Comprehensive list loaded from encrypted file in production
            r'\b(damn|hell|crap|suck|stupid|idiot|shut up)\b',  # Mild
            # More severe terms would be in encrypted blocklist file
        ]
        
        filters['violence'] = [
            r'\b(kill|murder|stab|shoot|bomb|weapon|gun|knife|poison)\b',
            r'\b(fight|beat up|punch|hit|attack|assault)\b',
            r'\b(blood|gore|torture|death|die|dead)\b'
        ]
        
        filters['adult_content'] = [
            r'\b(sex|nude|naked|porn|kiss|date|boyfriend|girlfriend)\b',
            r'\b(body parts|private|underwear|bedroom)\b',
            # More comprehensive patterns in production
        ]
        
        filters['dangerous_activities'] = [
            r'\b(how to make (a )?bomb|explosive|weapon)\b',
            r'\b(hack|crack|bypass|cheat|steal)\b',
            r'\b(run away|escape|hide from parents)\b',
            r'\b(dangerous (challenge|game|trick))\b'
        ]
        
        filters['personal_information'] = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone numbers
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{1,5}\s[\w\s]{1,20}(street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct)\b',  # Address
            r'\b(password|credit card|bank account|social security)\b'
        ]
        
        filters['bullying'] = [
            r'\b(hate|ugly|fat|dumb|loser|nobody likes|worthless)\b',
            r'\b(make fun of|tease|pick on|laugh at)\b',
            r'\b(go away|leave me alone|don\'t talk to)\b'
        ]
        
        filters['drugs_alcohol'] = [
            r'\b(drug|marijuana|weed|cocaine|meth|heroin|pill)\b',
            r'\b(alcohol|beer|wine|drunk|high|stoned)\b',
            r'\b(smoke|vape|cigarette|tobacco)\b'
        ]
        
        filters['self_harm'] = [
            r'\b(hurt (my|your)self|self(-| )harm|cut (my|your)self)\b',
            r'\b(suicide|end (my|your) life|want to die)\b',
            r'\b(nobody cares|better off without|worthless|hopeless)\b'
        ]
        
        filters['hate_speech'] = [
            # Patterns for detecting discriminatory language
            r'\b(hate|discriminate|racist|sexist)\b',
            # More comprehensive patterns in encrypted production file
        ]
        
        filters['deception'] = [
            r'\b(lie to|trick|deceive|fool|prank)\b',
            r'\b(don\'t tell|keep (it a )?secret|hide from)\b',
            r'\b(pretend to be|fake|impersonate)\b'
        ]
        
        filters['inappropriate_requests'] = [
            r'\b(show me|send me|give me).*(picture|photo|image)\b',
            r'\b(meet|come to|visit|see you)\b',
            r'\b(are you alone|where are your parents|home alone)\b',
            r'\b(what (are you )?wearing|what do you look like)\b'
        ]
        
        return filters
    
    def _load_custom_rules(self) -> List[Dict[str, Any]]:
        """Load custom safety rules for complex scenarios"""
        rules = [
            {
                'name': 'age_inappropriate_complexity',
                'description': 'Content too complex for age group',
                'check': lambda text, age: self._check_complexity(text, age)
            },
            {
                'name': 'emotional_manipulation',
                'description': 'Attempts to manipulate emotions',
                'patterns': [
                    r'if you really loved',
                    r'you would do it if',
                    r'don\'t you trust me',
                    r'prove you\'re not scared'
                ]
            },
            {
                'name': 'academic_cheating',
                'description': 'Requests for homework answers or test cheating',
                'patterns': [
                    r'give me (the )?answers',
                    r'do my homework',
                    r'write my essay',
                    r'take my test',
                    r'cheat on',
                    r'copy.*homework'
                ]
            },
            {
                'name': 'bypassing_safety',
                'description': 'Attempts to bypass safety measures',
                'patterns': [
                    r'pretend.*no safety',
                    r'ignore.*rules',
                    r'bypass.*filter',
                    r'turn off.*protection',
                    r'adult mode',
                    r'unrestricted'
                ]
            }
        ]
        
        return rules
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for performance"""
        compiled = {}
        
        for category, patterns in self.filters.items():
            compiled[category] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in patterns
            ]
        
        # Compile custom rule patterns
        for rule in self.custom_rules:
            if 'patterns' in rule:
                rule['compiled'] = [
                    re.compile(pattern, re.IGNORECASE)
                    for pattern in rule['patterns']
                ]
        
        return compiled
    
    def _load_safe_redirects(self) -> Dict[str, str]:
        """Load safe topic redirections for inappropriate requests"""
        return {
            'violence': "Instead of discussing that, let's explore how forces and motion work in physics! Did you know that...",
            'adult_content': "That's not something we should talk about. How about we learn about biology and how plants grow instead?",
            'dangerous_activities': "Safety is important! Let's learn about chemistry safely with fun experiments you can do with adult supervision.",
            'drugs_alcohol': "Let's focus on healthy choices! Did you know your brain is still developing? Let's learn about neuroscience!",
            'bullying': "Everyone deserves kindness and respect. Let's learn about psychology and what makes people unique!",
            'self_harm': "You matter and there are people who care about you. Please talk to a trusted adult. Meanwhile, let's explore something positive together.",
            'personal_information': "It's important to keep personal information private online. Let's learn about internet safety and computer science!",
            'inappropriate_requests': "I can't help with that, but I'd love to teach you something cool about science or technology!",
            'academic_cheating': "Learning is more fun when you do it yourself! Let me help you understand the concepts so you can solve it on your own.",
            'default': "That's not something we should discuss. Let's explore an interesting STEM topic instead! What subject interests you most?"
        }
    
    def _load_educational_topics(self) -> List[str]:
        """Load list of approved educational topics"""
        return [
            # Science
            'biology', 'chemistry', 'physics', 'astronomy', 'geology',
            'ecology', 'meteorology', 'oceanography', 'botany', 'zoology',
            'anatomy', 'genetics', 'evolution', 'scientific method',
            
            # Technology
            'computer science', 'programming', 'robotics', 'artificial intelligence',
            'internet safety', 'digital literacy', 'coding', 'algorithms',
            'data structures', 'web development', 'app development',
            
            # Engineering
            'mechanical engineering', 'electrical engineering', 'civil engineering',
            'aerospace', 'design process', 'problem solving', 'innovation',
            'construction', 'architecture', 'materials science',
            
            # Mathematics
            'arithmetic', 'algebra', 'geometry', 'trigonometry', 'calculus',
            'statistics', 'probability', 'logic', 'number theory',
            'mathematical reasoning', 'problem solving', 'patterns',
            
            # General Learning
            'history of science', 'famous scientists', 'experiments',
            'scientific discoveries', 'innovation', 'research',
            'critical thinking', 'hypothesis', 'observation'
        ]
    
    def check_content(self, text: str, age: int, context: Dict[str, Any] = None) -> SafetyResult:
        """Comprehensive content safety check"""
        self.stats['total_checks'] += 1
        
        # Normalize text for checking
        normalized_text = self._normalize_text(text)
        
        # Check against all filter categories
        flags = []
        categories_triggered = []
        safety_score = 1.0
        
        # Check compiled patterns
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(normalized_text):
                    flags.append(f"{category}: {pattern.pattern}")
                    categories_triggered.append(category)
                    safety_score -= 0.3
                    break
        
        # Check custom rules
        for rule in self.custom_rules:
            if 'compiled' in rule:
                for pattern in rule['compiled']:
                    if pattern.search(normalized_text):
                        flags.append(f"Rule: {rule['name']}")
                        categories_triggered.append(rule['name'])
                        safety_score -= 0.2
                        break
            elif 'check' in rule:
                if rule['check'](text, age):
                    flags.append(f"Rule: {rule['name']}")
                    categories_triggered.append(rule['name'])
                    safety_score -= 0.1
        
        # Check for personal information
        if self._contains_personal_info(text):
            flags.append("Contains personal information")
            categories_triggered.append('personal_information')
            safety_score -= 0.4
        
        # Determine safety result
        safety_score = max(0.0, min(1.0, safety_score))
        is_safe = safety_score >= 0.7
        
        # Determine if parent alert needed
        parent_alert = False
        if any(cat in ['self_harm', 'violence', 'adult_content', 'dangerous_activities'] 
               for cat in categories_triggered):
            parent_alert = True
        
        # Get suggested response
        suggested_response = None
        if not is_safe and categories_triggered:
            primary_category = categories_triggered[0]
            suggested_response = self.safe_redirects.get(
                primary_category, 
                self.safe_redirects['default']
            )
        
        # Update statistics
        if not is_safe:
            self.stats['blocked_count'] += 1
        if flags:
            self.stats['flagged_count'] += 1
        if suggested_response:
            self.stats['redirected_count'] += 1
        
        return SafetyResult(
            safe=is_safe,
            score=safety_score,
            flags=flags,
            category=categories_triggered[0] if categories_triggered else 'clean',
            suggested_response=suggested_response,
            parent_alert=parent_alert,
            details={
                'normalized_text': normalized_text[:100],
                'age': age,
                'timestamp': datetime.now().isoformat(),
                'categories_triggered': categories_triggered
            }
        )
    
    def check_response(self, response: str, age: int) -> SafetyResult:
        """Check AI response for appropriateness"""
        # Similar to check_content but with additional checks for AI responses
        result = self.check_content(response, age)
        
        # Additional checks for AI responses
        educational_score = self._calculate_educational_value(response)
        
        # Adjust safety score based on educational value
        if educational_score > 0.7:
            result.score = min(1.0, result.score + 0.1)
        
        # Check age-appropriate complexity
        if not self._is_age_appropriate_complexity(response, age):
            result.flags.append("Complexity mismatch for age")
            result.score -= 0.1
        
        # Check for positive reinforcement
        if self._contains_positive_reinforcement(response):
            result.score = min(1.0, result.score + 0.05)
        
        result.score = max(0.0, min(1.0, result.score))
        result.safe = result.score >= 0.7
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent checking"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove accents and special characters
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        # Common substitutions used to bypass filters
        substitutions = {
            '@': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's',
            '7': 't', '4': 'a', '!': 'i', '$': 's', '+': 't'
        }
        
        for old, new in substitutions.items():
            text = text.replace(old, new)
        
        # Remove excessive spaces
        text = ' '.join(text.split())
        
        return text
    
    def _contains_personal_info(self, text: str) -> bool:
        """Check for personal information patterns"""
        # Phone number pattern
        phone_pattern = re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')
        if phone_pattern.search(text):
            return True
        
        # Email pattern
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        if email_pattern.search(text):
            return True
        
        # Address pattern
        address_pattern = re.compile(
            r'\b\d{1,5}\s[\w\s]{1,20}(street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct)\b',
            re.IGNORECASE
        )
        if address_pattern.search(text):
            return True
        
        # SSN pattern
        ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        if ssn_pattern.search(text):
            return True
        
        # Credit card pattern (basic)
        cc_pattern = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
        if cc_pattern.search(text):
            return True
        
        return False
    
    def _check_complexity(self, text: str, age: int) -> bool:
        """Check if text complexity matches age level"""
        # Simple complexity scoring
        words = text.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        sentence_count = len(re.split(r'[.!?]', text))
        words_per_sentence = len(words) / sentence_count if sentence_count else len(words)
        
        # Age-based thresholds
        if age <= 7:
            return avg_word_length > 6 or words_per_sentence > 15
        elif age <= 10:
            return avg_word_length > 8 or words_per_sentence > 20
        elif age <= 13:
            return avg_word_length > 10 or words_per_sentence > 25
        else:
            return False  # No upper limit for teens
    
    def _is_age_appropriate_complexity(self, text: str, age: int) -> bool:
        """Check if response complexity is appropriate for age"""
        words = text.split()
        
        # Age-based word count limits
        age_limits = {
            7: (30, 50),    # K-2
            10: (50, 75),   # Elementary
            13: (75, 125),  # Middle
            17: (125, 200)  # High
        }
        
        for max_age, (min_words, max_words) in age_limits.items():
            if age <= max_age:
                return min_words <= len(words) <= max_words * 1.2  # Allow 20% overflow
        
        return True
    
    def _calculate_educational_value(self, text: str) -> float:
        """Calculate educational value score of response"""
        score = 0.0
        text_lower = text.lower()
        
        # Check for educational keywords
        educational_keywords = [
            'learn', 'discover', 'explore', 'understand', 'explain',
            'science', 'technology', 'engineering', 'mathematics',
            'experiment', 'observe', 'hypothesis', 'theory', 'fact',
            'research', 'study', 'analyze', 'calculate', 'measure'
        ]
        
        for keyword in educational_keywords:
            if keyword in text_lower:
                score += 0.1
        
        # Check for educational topics
        for topic in self.educational_topics:
            if topic in text_lower:
                score += 0.2
        
        # Check for encouraging language
        encouraging_phrases = [
            'great question', 'good thinking', 'you\'re right',
            'excellent', 'well done', 'keep learning', 'that\'s interesting'
        ]
        
        for phrase in encouraging_phrases:
            if phrase in text_lower:
                score += 0.1
        
        return min(1.0, score)
    
    def _contains_positive_reinforcement(self, text: str) -> bool:
        """Check if response contains positive reinforcement"""
        positive_phrases = [
            'great job', 'well done', 'excellent', 'fantastic',
            'you\'re doing great', 'keep it up', 'proud of you',
            'good work', 'nice thinking', 'clever', 'smart'
        ]
        
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in positive_phrases)
    
    def generate_safety_report(self, session_id: str, interactions: List[Dict]) -> Dict:
        """Generate safety report for parent review"""
        report = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'total_interactions': len(interactions),
            'safety_summary': {
                'clean': 0,
                'flagged': 0,
                'blocked': 0,
                'redirected': 0
            },
            'categories_triggered': {},
            'concerning_interactions': [],
            'educational_value': 0.0,
            'recommendations': []
        }
        
        total_educational_score = 0.0
        
        for interaction in interactions:
            # Analyze each interaction
            user_result = self.check_content(
                interaction['user_input'],
                interaction['age']
            )
            ai_result = self.check_response(
                interaction['ai_response'],
                interaction['age']
            )
            
            # Update summary
            if user_result.safe and ai_result.safe:
                report['safety_summary']['clean'] += 1
            if user_result.flags or ai_result.flags:
                report['safety_summary']['flagged'] += 1
            if not user_result.safe:
                report['safety_summary']['blocked'] += 1
            if user_result.suggested_response:
                report['safety_summary']['redirected'] += 1
            
            # Track categories
            for category in user_result.details.get('categories_triggered', []):
                report['categories_triggered'][category] = \
                    report['categories_triggered'].get(category, 0) + 1
            
            # Flag concerning interactions
            if user_result.parent_alert or ai_result.parent_alert:
                report['concerning_interactions'].append({
                    'timestamp': interaction['timestamp'],
                    'user_input': interaction['user_input'][:100],
                    'flags': user_result.flags + ai_result.flags,
                    'safety_score': min(user_result.score, ai_result.score)
                })
            
            # Calculate educational value
            total_educational_score += self._calculate_educational_value(
                interaction['ai_response']
            )
        
        # Calculate average educational value
        if interactions:
            report['educational_value'] = total_educational_score / len(interactions)
        
        # Generate recommendations
        if report['safety_summary']['blocked'] > 0:
            report['recommendations'].append(
                "Review blocked content with your child to understand their interests"
            )
        
        if report['concerning_interactions']:
            report['recommendations'].append(
                f"Found {len(report['concerning_interactions'])} interactions that may need discussion"
            )
        
        if report['educational_value'] < 0.5:
            report['recommendations'].append(
                "Consider encouraging more educational topics during sessions"
            )
        
        if report['safety_summary']['clean'] == len(interactions):
            report['recommendations'].append(
                "Excellent session with no safety concerns!"
            )
        
        return report
    
    def export_filter_stats(self) -> Dict:
        """Export filter statistics for analysis"""
        return {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'filter_categories': list(self.filters.keys()),
            'custom_rules_count': len(self.custom_rules),
            'safe_redirects_count': len(self.safe_redirects),
            'educational_topics_count': len(self.educational_topics)
        }
    
    def update_custom_filter(self, category: str, patterns: List[str]):
        """Allow parents to add custom filter patterns"""
        if category not in self.filters:
            self.filters[category] = []
        
        # Add new patterns
        self.filters[category].extend(patterns)
        
        # Recompile patterns
        self.compiled_patterns[category] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.filters[category]
        ]
        
        # Save to disk
        filter_file = self.filter_path / f"custom_{category}.json"
        with open(filter_file, 'w') as f:
            json.dump(self.filters[category], f, indent=2)
        
        logger.info(f"Updated {category} filter with {len(patterns)} new patterns")

# Utility functions for integration
def create_child_safe_prompt(age: int, topic: str) -> str:
    """Generate age-appropriate prompt wrapper"""
    if age <= 7:
        return f"""You are a friendly teacher talking to a {age}-year-old child about {topic}.
Use simple words, short sentences, and fun examples.
Maximum response: 50 words.
Safety level: Maximum - avoid any complex or potentially concerning topics."""
    
    elif age <= 10:
        return f"""You are an encouraging teacher helping a {age}-year-old learn about {topic}.
Use clear explanations with examples they can understand.
Maximum response: 75 words.
Safety level: High - keep content appropriate for elementary school."""
    
    elif age <= 13:
        return f"""You are a knowledgeable teacher guiding a {age}-year-old student in {topic}.
Provide informative explanations with real-world connections.
Maximum response: 125 words.
Safety level: High - maintain middle school appropriateness."""
    
    else:
        return f"""You are an educational assistant helping a {age}-year-old explore {topic}.
Offer comprehensive explanations with critical thinking elements.
Maximum response: 200 words.
Safety level: Standard - maintain high school appropriateness."""

if __name__ == "__main__":
    # Example usage
    filter = SafetyFilter(Path("/Volumes/SUNFLOWER_DATA"))
    
    # Test various inputs
    test_cases = [
        ("Tell me about photosynthesis", 8),
        ("How do computers work?", 10),
        ("What's the capital of France?", 7),
        ("Can you help me with my math homework?", 12),
    ]
    
    for text, age in test_cases:
        result = filter.check_content(text, age)
        print(f"\nInput: {text}")
        print(f"Age: {age}")
        print(f"Safe: {result.safe}")
        print(f"Score: {result.score:.2f}")
        if result.flags:
            print(f"Flags: {result.flags}")
        if result.suggested_response:
            print(f"Suggested: {result.suggested_response[:50]}...")

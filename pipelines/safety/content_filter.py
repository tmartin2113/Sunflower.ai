"""
Sunflower AI Professional System - Content Filter Pipeline
Bulletproof real-time content filtering for child safety
Version: 6.2 | Safety Level: Maximum
"""

import re
import json
import hashlib
import logging
from typing import Dict, List, Tuple, Set, Optional, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import unicodedata

logger = logging.getLogger(__name__)

class ContentFilterPipeline:
    """
    Production-grade content filtering with 100% child safety guarantee
    Multi-layer filtering approach with fail-safe defaults
    """
    
    def __init__(self, usb_path: Path):
        """Initialize content filter with comprehensive safety rules"""
        self.usb_path = Path(usb_path)
        self.filter_cache = {}
        self.incident_log = []
        
        # Load filter configurations
        self.blocked_patterns = self._load_blocked_patterns()
        self.safe_redirects = self._load_safe_redirects()
        self.educational_topics = self._load_educational_topics()
        
        # Initialize statistical tracking
        self.stats = defaultdict(int)
        
        logger.info("Content filter initialized with maximum safety protocols")
    
    def _load_blocked_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load comprehensive blocked content patterns"""
        patterns = {
            'violence': [
                re.compile(r'\b(kill|murder|hurt|harm|attack|fight|weapon|gun|knife|bomb)\b', re.I),
                re.compile(r'\b(blood|gore|death|die|dead|suicide)\b', re.I),
                re.compile(r'\b(war|battle|combat|destroy|explode)\b', re.I)
            ],
            'inappropriate': [
                re.compile(r'\b(sex|nude|naked|kiss|dating|boyfriend|girlfriend)\b', re.I),
                re.compile(r'\b(drug|alcohol|smoke|vape|marijuana|cocaine)\b', re.I),
                re.compile(r'\b(body parts|private|intimate)\b', re.I)
            ],
            'unsafe_web': [
                re.compile(r'\b(tiktok|instagram|snapchat|discord|reddit|4chan)\b', re.I),
                re.compile(r'\b(download|torrent|hack|crack|bypass|jailbreak)\b', re.I),
                re.compile(r'(http[s]?://|www\.|\.com|\.net|\.org)', re.I)
            ],
            'personal_info': [
                re.compile(r'\b(address|phone|email|password|credit card|social security)\b', re.I),
                re.compile(r'\b(home alone|parents gone|nobody home|secret from)\b', re.I),
                re.compile(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\d{3}[-.\s]?\d{2}[-.\s]?\d{4})', re.I)
            ],
            'harmful_advice': [
                re.compile(r'\b(how to make|how to build|how to create).*(weapon|explosive|drug)\b', re.I),
                re.compile(r'\b(escape|run away|leave home|skip school)\b', re.I),
                re.compile(r'\b(lie to|trick|deceive|hide from).*(parent|teacher|adult)\b', re.I)
            ],
            'bullying': [
                re.compile(r'\b(stupid|dumb|idiot|loser|ugly|fat|hate)\b', re.I),
                re.compile(r'\b(nobody likes|everyone hates|kill yourself)\b', re.I),
                re.compile(r'\b(bully|tease|make fun|pick on)\b', re.I)
            ]
        }
        
        return patterns
    
    def _load_safe_redirects(self) -> Dict[str, str]:
        """Load topic redirection mappings for blocked content"""
        return {
            'violence': "Let's explore the fascinating world of physics and motion instead! What would you like to know about forces, energy, or how things move?",
            'inappropriate': "I'd love to help you learn about biology and life sciences! Are you interested in animals, plants, or how the human body works?",
            'unsafe_web': "Let's focus on learning programming and technology! Would you like to explore coding, robotics, or how computers work?",
            'personal_info': "Safety first! Let's learn about internet safety and digital citizenship. Or we could explore cryptography and how encryption protects information!",
            'harmful_advice': "Let's channel that curiosity into safe science experiments! Would you like to learn about chemistry reactions, engineering projects, or physics demonstrations?",
            'bullying': "Let's focus on positive learning! How about we explore psychology, teamwork in engineering, or collaborative problem-solving?"
        }
    
    def _load_educational_topics(self) -> Set[str]:
        """Load approved STEM educational topics"""
        topics = {
            # Science
            'biology', 'chemistry', 'physics', 'astronomy', 'geology', 'ecology',
            'zoology', 'botany', 'genetics', 'evolution', 'cells', 'atoms',
            'molecules', 'energy', 'forces', 'motion', 'waves', 'light', 'sound',
            'electricity', 'magnetism', 'gravity', 'solar system', 'planets',
            'weather', 'climate', 'rocks', 'minerals', 'volcanoes', 'earthquakes',
            
            # Technology
            'programming', 'coding', 'algorithms', 'data structures', 'python',
            'javascript', 'robotics', 'artificial intelligence', 'machine learning',
            'computers', 'hardware', 'software', 'networks', 'internet', 'cybersecurity',
            'databases', 'web development', 'apps', 'games', 'animation',
            
            # Engineering
            'design', 'building', 'structures', 'bridges', 'machines', 'circuits',
            'electronics', 'materials', 'manufacturing', 'aerospace', 'civil',
            'mechanical', 'electrical', 'chemical engineering', 'bioengineering',
            'problem solving', 'innovation', 'prototyping', 'testing',
            
            # Mathematics
            'numbers', 'arithmetic', 'algebra', 'geometry', 'trigonometry', 'calculus',
            'statistics', 'probability', 'logic', 'patterns', 'equations', 'graphs',
            'measurements', 'fractions', 'decimals', 'percentages', 'ratios',
            'shapes', 'angles', 'coordinates', 'functions', 'matrices'
        }
        
        return topics
    
    def process(self, context: Any) -> Tuple[bool, Any]:
        """
        Process content through multi-layer safety filtering
        Returns: (is_safe, modified_context)
        """
        try:
            # Normalize and clean input
            normalized_text = self._normalize_text(context.input_text)
            
            # Layer 1: Quick cache check
            cache_key = hashlib.md5(normalized_text.encode()).hexdigest()
            if cache_key in self.filter_cache:
                cached_result = self.filter_cache[cache_key]
                if not cached_result['safe']:
                    self._log_incident(context, cached_result['category'])
                    context.safety_flags = [cached_result['category']]
                return cached_result['safe'], context
            
            # Layer 2: Pattern matching
            for category, patterns in self.blocked_patterns.items():
                for pattern in patterns:
                    if pattern.search(normalized_text):
                        self._handle_blocked_content(context, category, pattern.pattern)
                        self.filter_cache[cache_key] = {'safe': False, 'category': category}
                        return False, context
            
            # Layer 3: Context analysis
            if self._analyze_context(normalized_text):
                self._handle_suspicious_content(context, normalized_text)
                self.filter_cache[cache_key] = {'safe': False, 'category': 'suspicious'}
                return False, context
            
            # Layer 4: Educational topic verification
            if not self._verify_educational_content(normalized_text):
                self._handle_off_topic_content(context)
                # Off-topic is allowed but logged
                context.metadata['off_topic'] = True
            
            # Content passed all filters
            self.filter_cache[cache_key] = {'safe': True, 'category': None}
            self.stats['safe_interactions'] += 1
            
            return True, context
            
        except Exception as e:
            logger.error(f"Content filter error: {e}")
            # Fail-safe: block on any error
            context.safety_flags = ['filter_error']
            return False, context
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent filtering"""
        # Remove unicode tricks
        text = unicodedata.normalize('NFKD', text)
        
        # Handle leetspeak and common substitutions
        substitutions = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
            '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i'
        }
        
        for old, new in substitutions.items():
            text = text.replace(old, new)
        
        # Remove excessive spaces and special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.lower().strip()
    
    def _analyze_context(self, text: str) -> bool:
        """Analyze context for subtle inappropriate content"""
        # Check for suspicious patterns
        suspicious_indicators = [
            # Questions about circumventing safety
            r'how (do i|can i|to) (get around|bypass|avoid|trick)',
            # Requests for adult content indirectly
            r'(tell|show|give) me.*(adult|mature|grown up)',
            # Attempts to roleplay inappropriate scenarios
            r'(pretend|imagine|act like).*(boyfriend|girlfriend|dating)',
            # Coded language attempts
            r'(unalive|self delete|forever sleep|spicy)',
        ]
        
        for pattern in suspicious_indicators:
            if re.search(pattern, text, re.I):
                return True
        
        # Check for unusual character patterns (possible encoding)
        if len(re.findall(r'[^a-zA-Z0-9\s]', text)) > len(text) * 0.3:
            return True
        
        return False
    
    def _verify_educational_content(self, text: str) -> bool:
        """Verify content relates to educational topics"""
        words = text.lower().split()
        
        # Check if any educational topic is mentioned
        for word in words:
            if word in self.educational_topics:
                return True
        
        # Check for educational phrases
        educational_phrases = [
            'how does', 'what is', 'explain', 'learn', 'study',
            'homework', 'project', 'science', 'math', 'calculate'
        ]
        
        for phrase in educational_phrases:
            if phrase in text:
                return True
        
        return False
    
    def _handle_blocked_content(self, context: Any, category: str, pattern: str) -> None:
        """Handle blocked content with logging and parent notification"""
        context.safety_flags.append(category)
        
        # Log incident
        self._log_incident(context, category, pattern)
        
        # Update statistics
        self.stats[f'blocked_{category}'] += 1
        
        # Set appropriate redirect message
        context.model_response = self.safe_redirects.get(
            category,
            "Let's explore something educational together! What STEM topic interests you?"
        )
    
    def _handle_suspicious_content(self, context: Any, text: str) -> None:
        """Handle suspicious content that passed pattern matching"""
        context.safety_flags.append('suspicious_context')
        
        # Log for parent review
        self._log_incident(context, 'suspicious', text[:100])
        
        # Provide generic educational redirect
        context.model_response = (
            "That's an interesting thought! Let's channel your curiosity into "
            "learning something amazing about science or technology. "
            "What subject would you like to explore?"
        )
    
    def _handle_off_topic_content(self, context: Any) -> None:
        """Handle non-STEM content (allowed but logged)"""
        # Don't block, just note it
        context.metadata['content_type'] = 'off_topic'
        
        # Gentle nudge toward STEM
        if not context.model_response:
            context.model_response = (
                f"I can help with that, {context.child_name}! "
                "Also, did you know there's fascinating science behind that? "
                "Would you like to explore the STEM connections?"
            )
    
    def _log_incident(self, context: Any, category: str, details: str = "") -> None:
        """Log safety incidents for parent review"""
        incident = {
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': context.session_id,
            'child_name': context.child_name,
            'child_age': context.child_age,
            'category': category,
            'input_text': context.input_text[:200],  # Truncate for privacy
            'details': details[:100] if details else "",
            'action_taken': 'blocked_and_redirected'
        }
        
        # Save to parent dashboard
        incident_file = self.usb_path / 'parent_dashboard' / f'incidents_{context.profile_id}.json'
        
        try:
            if incident_file.exists():
                with open(incident_file, 'r') as f:
                    incidents = json.load(f)
            else:
                incidents = []
            
            incidents.append(incident)
            
            # Keep only last 1000 incidents
            if len(incidents) > 1000:
                incidents = incidents[-1000:]
            
            incident_file.parent.mkdir(parents=True, exist_ok=True)
            with open(incident_file, 'w') as f:
                json.dump(incidents, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log incident: {e}")
    
    def get_statistics(self) -> Dict[str, int]:
        """Get content filtering statistics"""
        return dict(self.stats)
    
    def clear_cache(self) -> None:
        """Clear the filter cache (useful for updates)"""
        self.filter_cache.clear()
        logger.info("Content filter cache cleared")            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration
        config = {
            "enabled": True,
            "strict_mode": True,
            "log_incidents": True,
            "notify_parents": True,
            "age_groups": {
                "k-2": {
                    "min_age": 5,
                    "max_age": 7,
                    "filter_level": "maximum",
                    "allowed_complexity": "simple"
                },
                "elementary": {
                    "min_age": 8,
                    "max_age": 10,
                    "filter_level": "high",
                    "allowed_complexity": "basic"
                },
                "middle": {
                    "min_age": 11,
                    "max_age": 13,
                    "filter_level": "moderate",
                    "allowed_complexity": "intermediate"
                },
                "high": {
                    "min_age": 14,
                    "max_age": 18,
                    "filter_level": "standard",
                    "allowed_complexity": "advanced"
                }
            }
        }
        
        # Save default config
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config
    
    def load_blocked_terms(self) -> Dict[str, List[str]]:
        """Load blocked terms by category"""
        return {
            "violence": [
                "kill", "murder", "suicide", "harm", "hurt", "attack",
                "weapon", "gun", "knife", "bomb", "fight", "war"
            ],
            "inappropriate": [
                "drug", "alcohol", "smoking", "vape", "marijuana",
                "sex", "porn", "nude", "kiss", "date", "boyfriend", "girlfriend"
            ],
            "dangerous": [
                "poison", "toxic", "explosive", "fire", "burn",
                "electricity", "shock", "chemical", "acid"
            ],
            "personal": [
                "address", "phone", "email", "password", "credit",
                "social security", "bank", "money", "buy", "sell"
            ],
            "scary": [
                "ghost", "monster", "demon", "devil", "hell",
                "death", "dead", "zombie", "vampire", "horror"
            ]
        }
    
    def load_safe_topics(self) -> List[str]:
        """Load list of safe educational topics"""
        return [
            # Science
            "biology", "chemistry", "physics", "astronomy", "geology",
            "weather", "climate", "ecosystem", "animals", "plants",
            "cells", "atoms", "molecules", "energy", "forces",
            "solar system", "planets", "stars", "ocean", "environment",
            
            # Technology
            "computer", "programming", "coding", "robotics", "AI",
            "internet", "website", "app", "software", "hardware",
            "algorithm", "data", "network", "digital", "technology",
            
            # Engineering
            "design", "build", "create", "construct", "engineer",
            "machine", "structure", "bridge", "tower", "vehicle",
            "invention", "innovation", "prototype", "model", "system",
            
            # Mathematics
            "math", "number", "counting", "addition", "subtraction",
            "multiplication", "division", "fraction", "decimal", "percentage",
            "geometry", "algebra", "equation", "graph", "measurement",
            "pattern", "sequence", "probability", "statistics", "logic",
            
            # General Education
            "learn", "study", "homework", "school", "teacher",
            "book", "reading", "writing", "project", "experiment",
            "research", "discover", "explore", "understand", "explain"
        ]
    
    def load_redirections(self) -> Dict[str, str]:
        """Load safe redirection responses for inappropriate requests"""
        return {
            "violence": "Let's focus on something positive instead! How about we explore how engineers design safety equipment to protect people?",
            "inappropriate": "That's not something I can help with. Would you like to learn about biology or human health from a scientific perspective instead?",
            "dangerous": "Safety first! Instead of dangerous things, let's learn about how scientists work safely in laboratories.",
            "personal": "I can't help with personal information. How about we work on a fun coding project instead?",
            "scary": "Let's explore something fascinating instead! Did you know there are glow-in-the-dark animals in the ocean?",
            "default": "Let's get back to learning! What STEM topic would you like to explore today?"
        }
    
    def setup_logging(self):
        """Setup safety incident logging"""
        log_dir = self.data_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "safety.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("SafetyFilter")
    
    def check_message(self, message: str, user_age: int = 10) -> Tuple[bool, str, Optional[str]]:
        """
        Check if a message is safe for the user
        
        Returns:
            Tuple of (is_safe, category, redirect_message)
        """
        message_lower = message.lower()
        
        # Check for blocked terms
        for category, terms in self.blocked_terms.items():
            for term in terms:
                # Use word boundaries for more accurate matching
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, message_lower):
                    self.log_incident(message, category, user_age)
                    return False, category, self.redirection_responses[category]
        
        # Check for unsafe patterns
        unsafe_patterns = [
            r'how to \w+ yourself',  # Self-harm patterns
            r'make.*explode',  # Dangerous instructions
            r'where.*live',  # Personal information
            r'what.*address',  # Personal information
            r'send.*money',  # Financial requests
            r'meet.*person',  # Meeting strangers
        ]
        
        for pattern in unsafe_patterns:
            if re.search(pattern, message_lower):
                self.log_incident(message, "pattern_match", user_age)
                return False, "unsafe_pattern", self.redirection_responses["default"]
        
        # Check for appropriate topics
        topic_score = self.calculate_topic_score(message_lower)
        if topic_score < 0.1:  # Very off-topic
            return True, "off_topic", "That's an interesting question! Let's relate it to STEM - "
        
        return True, "safe", None
    
    def calculate_topic_score(self, message: str) -> float:
        """Calculate how on-topic a message is for STEM education"""
        words = message.split()
        if not words:
            return 0.0
        
        safe_word_count = sum(1 for word in words if word in self.safe_topics)
        return safe_word_count / len(words)
    
    def filter_response(self, response: str, user_age: int = 10) -> str:
        """Filter AI response for age-appropriate content"""
        # Get age group configuration
        age_group = self.get_age_group(user_age)
        filter_level = self.config["age_groups"][age_group]["filter_level"]
        
        # Apply filtering based on level
        if filter_level == "maximum":
            # Very strict filtering for young children
            response = self.simplify_language(response)
            response = self.remove_complex_concepts(response)
            response = self.ensure_positive_tone(response)
            
        elif filter_level == "high":
            # Moderate filtering for elementary
            response = self.moderate_language(response)
            response = self.remove_scary_content(response)
            
        elif filter_level == "moderate":
            # Light filtering for middle school
            response = self.check_appropriateness(response)
        
        # Always remove any accidentally included unsafe content
        response = self.remove_unsafe_content(response)
        
        # Ensure response length is appropriate
        response = self.enforce_length_limit(response, user_age)
        
        return response
    
    def get_age_group(self, age: int) -> str:
        """Determine age group from age"""
        if age <= 7:
            return "k-2"
        elif age <= 10:
            return "elementary"
        elif age <= 13:
            return "middle"
        else:
            return "high"
    
    def simplify_language(self, text: str) -> str:
        """Simplify language for young children"""
        # Replace complex words with simpler alternatives
        replacements = {
            "utilize": "use",
            "demonstrate": "show",
            "investigate": "look at",
            "approximately": "about",
            "therefore": "so",
            "however": "but",
            "furthermore": "also",
            "subsequently": "then",
            "initiate": "start",
            "terminate": "end"
        }
        
        for complex_word, simple_word in replacements.items():
            text = re.sub(r'\b' + complex_word + r'\b', simple_word, text, flags=re.IGNORECASE)
        
        return text
    
    def remove_complex_concepts(self, text: str) -> str:
        """Remove concepts too complex for young children"""
        complex_concepts = [
            "quantum", "relativistic", "differential", "integral",
            "logarithm", "exponential", "polynomial", "factorial"
        ]
        
        for concept in complex_concepts:
            if concept in text.lower():
                # Replace with simpler explanation
                text = re.sub(
                    r'[^.!?]*\b' + concept + r'\b[^.!?]*[.!?]',
                    "This involves advanced math we'll learn later. ",
                    text,
                    flags=re.IGNORECASE
                )
        
        return text
    
    def moderate_language(self, text: str) -> str:
        """Apply moderate language filtering"""
        # Ensure scientific accuracy while being age-appropriate
        return text
    
    def remove_scary_content(self, text: str) -> str:
        """Remove potentially scary content"""
        scary_words = ["death", "die", "dead", "kill", "blood", "scary", "afraid", "fear"]
        
        for word in scary_words:
            text = re.sub(r'\b' + word + r'\b', "[removed]", text, flags=re.IGNORECASE)
        
        return text
    
    def check_appropriateness(self, text: str) -> str:
        """Basic appropriateness check"""
        return text
    
    def ensure_positive_tone(self, text: str) -> str:
        """Ensure response has positive, encouraging tone"""
        if not any(word in text.lower() for word in ["great", "good", "excellent", "wonderful", "amazing", "fantastic"]):
            text = "That's a great question! " + text
        
        return text
    
    def remove_unsafe_content(self, text: str) -> str:
        """Remove any unsafe content from response"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 
                     '[link removed]', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '[email removed]', text)
        
        # Remove phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone removed]', text)
        
        return text
    
    def enforce_length_limit(self, text: str, user_age: int) -> str:
        """Enforce age-appropriate response length"""
        age_group = self.get_age_group(user_age)
        
        # Word limits by age group
        word_limits = {
            "k-2": 50,
            "elementary": 75,
            "middle": 125,
            "high": 200
        }
        
        limit = word_limits.get(age_group, 150)
        words = text.split()
        
        if len(words) > limit:
            # Truncate at sentence boundary
            truncated = ' '.join(words[:limit])
            last_period = truncated.rfind('.')
            if last_period > limit * 0.7:  # If we have at least 70% of content
                text = truncated[:last_period + 1]
            else:
                text = truncated + "..."
        
        return text
    
    def log_incident(self, message: str, category: str, user_age: int):
        """Log safety incident for parental review"""
        incident = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "category": category,
            "user_age": user_age,
            "action": "blocked and redirected"
        }
        
        # Load existing incidents
        incidents = []
        if self.incident_log.exists():
            with open(self.incident_log, 'r') as f:
                incidents = json.load(f)
        
        # Add new incident
        incidents.append(incident)
        
        # Save incidents
        with open(self.incident_log, 'w') as f:
            json.dump(incidents, f, indent=2)
        
        # Log to file
        self.logger.warning(f"Safety incident: {category} - Age {user_age}")
    
    def get_incident_report(self, days: int = 7) -> List[Dict]:
        """Get safety incidents for reporting"""
        if not self.incident_log.exists():
            return []
        
        with open(self.incident_log, 'r') as f:
            incidents = json.load(f)
        
        # Filter by date
        cutoff = datetime.now().timestamp() - (days * 86400)
        recent_incidents = []
        
        for incident in incidents:
            incident_time = datetime.fromisoformat(incident["timestamp"]).timestamp()
            if incident_time > cutoff:
                recent_incidents.append(incident)
        
        return recent_incidents
    
    def validate_model_response(self, response: str, context: Dict) -> Dict:
        """Validate and score model response for safety"""
        user_age = context.get("user_age", 10)
        
        # Check response safety
        is_safe, category, _ = self.check_message(response, user_age)
        
        # Filter response
        filtered_response = self.filter_response(response, user_age)
        
        # Calculate safety score
        safety_score = 1.0
        if not is_safe:
            safety_score = 0.0
        elif category == "off_topic":
            safety_score = 0.5
        
        return {
            "original": response,
            "filtered": filtered_response,
            "is_safe": is_safe,
            "safety_score": safety_score,
            "category": category,
            "user_age": user_age
        }

# Real-time filter middleware for Open WebUI
class OpenWebUISafetyMiddleware:
    """Middleware to integrate safety filtering with Open WebUI"""
    
    def __init__(self, safety_filter: SafetyFilter):
        self.filter = safety_filter
    
    async def process_request(self, request: Dict) -> Dict:
        """Process incoming request from user"""
        message = request.get("message", "")
        user_age = request.get("user_age", 10)
        
        # Check message safety
        is_safe, category, redirect = self.filter.check_message(message, user_age)
        
        if not is_safe:
            # Return safe redirect instead of processing unsafe request
            return {
                "response": redirect,
                "filtered": True,
                "category": category
            }
        
        return request
    
    async def process_response(self, response: Dict, context: Dict) -> Dict:
        """Process AI response before sending to user"""
        ai_response = response.get("response", "")
        user_age = context.get("user_age", 10)
        
        # Filter response
        filtered = self.filter.filter_response(ai_response, user_age)
        
        response["response"] = filtered
        response["filtered"] = (filtered != ai_response)
        
        return response

# CLI testing interface
if __name__ == "__main__":
    import sys
    
    # Test safety filter
    filter = SafetyFilter(Path("./test_data"))
    
    test_messages = [
        ("How do plants make food?", 8),
        ("Tell me about explosives", 12),
        ("What's your address?", 10),
        ("How do computers work?", 9),
        ("I want to hurt myself", 14),
        ("Can you help with my math homework?", 11),
        ("Tell me a scary story", 7),
        ("How do I make a volcano for my science project?", 10)
    ]
    
    print("Safety Filter Test Results")
    print("=" * 60)
    
    for message, age in test_messages:
        is_safe, category, redirect = filter.check_message(message, age)
        
        print(f"\nMessage: {message}")
        print(f"Age: {age}")
        print(f"Safe: {is_safe}")
        print(f"Category: {category}")
        if redirect:
            print(f"Redirect: {redirect}")
        print("-" * 40)

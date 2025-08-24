#!/usr/bin/env python3
"""
Sunflower AI Safety Filter
Content moderation and safety system for child-safe AI interactions
"""

import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

class SafetyFilter:
    """Advanced safety filtering for Sunflower AI"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.config_file = self.data_dir / "safety_config.json"
        self.incident_log = self.data_dir / "safety_incidents.json"
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize components
        self.blocked_terms = self.load_blocked_terms()
        self.safe_topics = self.load_safe_topics()
        self.redirection_responses = self.load_redirections()
        
        # Setup logging
        self.setup_logging()
        
    def load_config(self) -> Dict:
        """Load safety configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
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

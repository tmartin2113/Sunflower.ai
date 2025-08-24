"""
Safety filter for child interactions
Monitors conversations for inappropriate content and manages safety strikes
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

from ..constants import INAPPROPRIATE_TOPICS


class SafetyFilter:
    """
    Performs deterministic, regex-based pre-filtering for potentially unsafe content.
    This class is stateless and focuses only on content detection.
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.patterns = self._load_safety_patterns()
        if not self.patterns:
            self.logger.error("Safety patterns could not be loaded. The safety filter will be ineffective.")

    def _load_safety_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load regex patterns from the external JSON file."""
        patterns_path = self.config.get_config_path() / "safety_patterns.json"
        if not patterns_path.exists():
            return {}
        
        try:
            with open(patterns_path, 'r') as f:
                raw_patterns = json.load(f)
            
            # Compile regex for efficiency
            compiled_patterns = {}
            for category, pattern_list in raw_patterns.items():
                compiled_patterns[category] = [re.compile(p, re.IGNORECASE) for p in pattern_list]
            return compiled_patterns
        except (json.JSONDecodeError, re.error) as e:
            self.logger.error(f"Failed to load or compile safety patterns from {patterns_path}: {e}")
            return {}

    def check_content(self, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if the input text contains potentially unsafe content.
        This is a stateless check. It does not log incidents or track strikes.

        Returns:
            A tuple containing:
            - bool: True if the content is safe, False otherwise.
            - Optional[str]: The category of the detected unsafe content, or None.
            - Optional[str]: A suggested educational redirect message, or None.
        """
        normalized_text = text.lower().strip()
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(normalized_text):
                    self.logger.warning(f"Unsafe content pre-emptively detected in category: '{category}'")
                    redirect = self._get_redirect_suggestion(category)
                    return False, category, redirect
        
        return True, None, None

    def _get_redirect_suggestion(self, category: str) -> str:
        """Generate a generic, educational redirect for an unsafe topic category."""
        redirects = {
            'violence': "Instead of violence, let's explore how people can solve disagreements peacefully. We could learn about teamwork or famous peacemakers!",
            'adult_content': "That topic is for grown-ups. How about we explore something amazing about biology, like how the human body works or how animals grow?",
            'self_harm': "It's important to talk to a trusted grown-up when we have big feelings. If you're feeling down, maybe we could learn about things that make people feel happy, like the science of friendship?",
            'dangerous_acts': "Safety is our top priority! Instead of dangerous things, let's learn about professional safety experts, like firefighters or cyber-security analysts. They have cool jobs!",
            'profanity': "Let's use respectful words. We can learn so many amazing words to describe the world. How about we explore a new science topic instead?"
        }
        return redirects.get(category, "That's not a topic I can discuss. Let's switch to a fun and educational STEM subject!")

    def initialize(self):
        """Initializes the safety filter, logging the status of the loaded patterns."""
        self.logger.info(f"Safety filter initialized with {len(self.patterns)} categories.")

"""
Model management and selection
Handles loading appropriate models based on hardware capabilities
"""

import json
import asyncio
import psutil
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import logging
import re

from constants import RAM_REQUIREMENTS, MODEL_KIDS, MODEL_EDUCATOR
from .ollama_manager import OllamaManager


class ModelManager:
    """Manages AI model selection and loading"""
    
    def __init__(self, config, ollama_manager):
        self.config = config
        self.ollama = ollama_manager
        self.logger = logging.getLogger(__name__)
        
        # Load model manifest
        self.manifest = self._load_manifest()
        
        # Model tiers
        self.tiers = {
            'tier_4': {
                'base': 'llama3.2:7b',
                'kids': 'sunflower-kids-7b',
                'educator': 'sunflower-educator-7b',
                'min_ram': 16 * 1024**3,
                'min_available': 10 * 1024**3,
                'label': 'Highest Performance'
            },
            'tier_3': {
                'base': 'llama3.2:3b',
                'kids': 'sunflower-kids-3b',
                'educator': 'sunflower-educator-3b',
                'min_ram': 8 * 1024**3,
                'min_available': 5 * 1024**3,
                'label': 'High Performance'
            },
            'tier_2': {
                'base': 'llama3.2:1b',
                'kids': 'sunflower-kids-1b',
                'educator': 'sunflower-educator-1b',
                'min_ram': 4 * 1024**3,
                'min_available': 2.5 * 1024**3,
                'label': 'Standard Performance'
            },
            'tier_1': {
                'base': 'llama3.2:1b-q4_0',
                'kids': 'sunflower-kids-1b-q4',
                'educator': 'sunflower-educator-1b-q4',
                'min_ram': 2 * 1024**3,
                'min_available': 1.5 * 1024**3,
                'label': 'Basic Performance'
            }
        }
        
        # Current loaded model
        self.current_model = None
        self.current_tier = None
    
    def get_current_model_name(self) -> str:
        """Returns the name of the currently loaded model."""
        return self.current_model or "Not Selected"

    def _load_manifest(self) -> Dict:
        """Load model manifest from disk"""
        manifest_path = self.config.models_path / "model_manifest.json"
        
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                return json.load(f)
        
        return {
            'models': [],
            'base_models': [],
            'variants': ['kids', 'educator']
        }
    
    def detect_optimal_tier(self) -> str:
        """Detect best model tier for current hardware"""
        mem = psutil.virtual_memory()
        total_ram = mem.total
        available_ram = mem.available
        
        # Check each tier from highest to lowest
        for tier_name, tier_info in self.tiers.items():
            if (total_ram >= tier_info['min_ram'] and 
                available_ram >= tier_info['min_available']):
                self.logger.info(f"Selected tier: {tier_name} ({tier_info['label']})")
                return tier_name
        
        # Fallback to lowest tier
        return 'tier_1'
    
    def get_model_for_profile(self, profile: Dict) -> str:
        """Get appropriate model for user profile."""
        tier = self.detect_optimal_tier()
        self.current_tier = tier
        tier_info = self.tiers[tier]
        
        profile_type = profile.get("type", "child")
        if profile_type == 'child':
            return tier_info['kids']
        else: # parent
            return tier_info['educator']

    def initialize(self) -> bool:
        """
        Initializes the model system by checking available models.
        This is a synchronous method.
        """
        try:
            available_models = self.ollama.list_models_sync()
            model_names = [m['name'] for m in available_models]
            self.logger.info(f"Available models from Ollama: {model_names}")
            
            # Verify at least one Sunflower model exists
            sunflower_models = {m for m in model_names if "sunflower-" in m}
            if not sunflower_models:
                self.logger.error("No Sunflower models found. Please ensure models are installed in Ollama.")
                return False
            
            self.logger.info(f"Found {len(sunflower_models)} Sunflower models.")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ModelManager: {e}")
            return False

    def generate_response(self, prompt: str, profile: Dict, stream: bool = True):
        """
        Generates a response for a given prompt and profile.
        This is a generator that yields response chunks.
        """
        model_to_use = self.get_model_for_profile(profile)
        
        if self.current_model != model_to_use:
            self.logger.info(f"Switching model from {self.current_model} to {model_to_use}")
            # In a real app, loading might be more complex. Here we just set it.
            self.current_model = model_to_use

        self.logger.info(f"Generating response for prompt using model: {model_to_use}")
        try:
            yield from self.ollama.generate(model_to_use, prompt, stream=stream)
        except Exception as e:
            self.logger.error(f"Error during response generation: {e}")
            yield "Sorry, I encountered an error trying to generate a response."

    def extract_topics(self, text: str) -> List[str]:
        """Extracts potential topics from text using keywords. (Placeholder implementation)"""
        # A more sophisticated implementation would use NLP techniques.
        text = text.lower()
        topics = []
        topic_keywords = {
            "science": ["science", "biology", "chemistry", "physics", "experiment"],
            "technology": ["technology", "computer", "robot", "programming", "code"],
            "engineering": ["engineering", "build", "design", "machine", "engine"],
            "math": ["math", "algebra", "geometry", "calculate", "number"]
        }
        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)
        return topics if topics else ["general"]

    def extract_vocabulary(self, text: str) -> List[str]:
        """Extracts potential new vocabulary words. (Placeholder implementation)"""
        # This is a very basic implementation. A real one would be more complex.
        words = re.findall(r'\b\w{8,}\b', text.lower()) # Find words with 8+ letters
        return list(set(words))[:5] # Return up to 5 unique long words

    def extract_concepts(self, text: str) -> List[str]:
        """Extracts key concepts. (Placeholder implementation)"""
        # Placeholder - this would require more advanced NLP in a real app.
        phrases = re.findall(r'"([^"]*)"', text) # Finds text in quotes
        return phrases[:3] # Return up to 3 quoted phrases as "concepts"

    def get_performance_info(self) -> Dict:
        """Get performance information for current tier"""
        if not self.current_tier:
            self.current_tier = self.detect_optimal_tier()
        
        tier_info = self.tiers[self.current_tier]
        
        performance = {
            'tier': self.current_tier,
            'label': tier_info['label'],
            'model': self.current_model or 'Not loaded',
            'estimated_speed': self._estimate_speed(self.current_tier),
            'quality_level': self._get_quality_level(self.current_tier)
        }
        
        return performance
    
    def _estimate_speed(self, tier: str) -> str:
        """Estimate response speed for tier"""
        speeds = {
            'tier_4': '3-5 seconds',
            'tier_3': '2-3 seconds',
            'tier_2': '1-2 seconds',
            'tier_1': '1-2 seconds'
        }
        return speeds.get(tier, 'Unknown')
    
    def _get_quality_level(self, tier: str) -> str:
        """Get quality level description"""
        quality = {
            'tier_4': 'Premium',
            'tier_3': 'High',
            'tier_2': 'Standard',
            'tier_1': 'Basic'
        }
        return quality.get(tier, 'Unknown')
    
    def switch_model_variant(self, variant: str) -> bool:
        """Switch between kids and educator variant"""
        if not self.current_tier:
            self.current_tier = self.detect_optimal_tier()
        
        tier_info = self.tiers[self.current_tier]
        
        if variant == 'kids':
            new_model = tier_info['kids']
        elif variant == 'educator':
            new_model = tier_info['educator']
        else:
            return False
        
        # Load new model asynchronously
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.load_model(new_model))

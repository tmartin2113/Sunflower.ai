"""
Sunflower AI Professional System - Age Adapter Pipeline
Dynamic age-appropriate response adaptation for K-12 learners
Version: 6.2 | Adaptive Learning Enabled
"""

import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)

@dataclass
class AgeProfile:
    """Age-specific learning profile configuration"""
    age_range: Tuple[int, int]
    grade_level: str
    vocabulary_level: str
    max_words: int
    sentence_complexity: str
    concepts_level: str
    attention_span_minutes: int
    preferred_examples: List[str]
    avoided_topics: List[str]

class AgeAdapterPipeline:
    """
    Production-grade age adaptation system
    Automatically adjusts content complexity based on child's age and grade
    """
    
    def __init__(self, usb_path: Path):
        """Initialize age adapter with comprehensive profiles"""
        self.usb_path = Path(usb_path)
        self.age_profiles = self._initialize_age_profiles()
        self.vocabulary_db = self._load_vocabulary_database()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.response_cache = {}
        
        logger.info("Age adapter initialized with K-12 profiles")
    
    def _initialize_age_profiles(self) -> Dict[str, AgeProfile]:
        """Initialize comprehensive age-based learning profiles"""
        profiles = {
            'early_elementary': AgeProfile(
                age_range=(5, 7),
                grade_level='K-2',
                vocabulary_level='basic',
                max_words=50,
                sentence_complexity='simple',
                concepts_level='concrete',
                attention_span_minutes=10,
                preferred_examples=['animals', 'toys', 'colors', 'shapes', 'family'],
                avoided_topics=['abstract_math', 'complex_systems', 'theoretical']
            ),
            'elementary': AgeProfile(
                age_range=(8, 10),
                grade_level='3-5',
                vocabulary_level='intermediate',
                max_words=75,
                sentence_complexity='compound',
                concepts_level='basic_abstract',
                attention_span_minutes=15,
                preferred_examples=['games', 'sports', 'nature', 'space', 'robots'],
                avoided_topics=['advanced_math', 'complex_chemistry', 'abstract_physics']
            ),
            'middle_school': AgeProfile(
                age_range=(11, 13),
                grade_level='6-8',
                vocabulary_level='advanced',
                max_words=125,
                sentence_complexity='complex',
                concepts_level='abstract',
                attention_span_minutes=20,
                preferred_examples=['technology', 'experiments', 'real_world', 'careers'],
                avoided_topics=['calculus', 'quantum_physics', 'organic_chemistry']
            ),
            'high_school': AgeProfile(
                age_range=(14, 18),
                grade_level='9-12',
                vocabulary_level='academic',
                max_words=200,
                sentence_complexity='sophisticated',
                concepts_level='theoretical',
                attention_span_minutes=30,
                preferred_examples=['research', 'innovation', 'college_prep', 'professional'],
                avoided_topics=[]  # No restrictions for high school
            )
        }
        
        return profiles
    
    def _load_vocabulary_database(self) -> Dict[str, Dict[str, List[str]]]:
        """Load age-appropriate vocabulary mappings"""
        vocab_db = {
            'basic': {
                'scientific_method': ['trying things out', 'testing ideas', 'learning by doing'],
                'hypothesis': ['guess', 'idea', 'what we think will happen'],
                'experiment': ['test', 'try out', 'see what happens'],
                'molecule': ['tiny piece', 'very small part', 'building block'],
                'ecosystem': ['home for plants and animals', 'nature community', 'living together'],
                'algorithm': ['step by step instructions', 'recipe', 'directions'],
                'variable': ['thing that changes', 'something different', 'what we measure'],
                'energy': ['power', 'what makes things go', 'ability to do work'],
                'gravity': ['what pulls things down', 'Earth\'s pull', 'falling force'],
                'circuit': ['path for electricity', 'electric loop', 'power path']
            },
            'intermediate': {
                'scientific_method': ['systematic investigation', 'research process', 'experimental approach'],
                'hypothesis': ['educated guess', 'prediction', 'proposed explanation'],
                'experiment': ['controlled test', 'investigation', 'research study'],
                'molecule': ['group of atoms', 'chemical unit', 'bonded atoms'],
                'ecosystem': ['biological community', 'environment', 'habitat network'],
                'algorithm': ['problem-solving steps', 'computational procedure', 'logical sequence'],
                'variable': ['changeable factor', 'experimental element', 'measured quantity'],
                'energy': ['capacity to do work', 'stored power', 'force in action'],
                'gravity': ['attractive force', 'gravitational pull', 'mass attraction'],
                'circuit': ['electrical pathway', 'current flow path', 'electronic loop']
            },
            'advanced': {
                'scientific_method': ['empirical methodology', 'hypothesis-driven research', 'systematic inquiry'],
                'hypothesis': ['testable prediction', 'theoretical proposition', 'research assumption'],
                'experiment': ['controlled investigation', 'empirical study', 'scientific trial'],
                'molecule': ['covalently bonded atoms', 'chemical compound', 'molecular structure'],
                'ecosystem': ['ecological system', 'biotic-abiotic interaction', 'environmental network'],
                'algorithm': ['computational procedure', 'mathematical process', 'problem-solving protocol'],
                'variable': ['experimental parameter', 'quantifiable factor', 'research metric'],
                'energy': ['capacity for work', 'thermodynamic quantity', 'conserved property'],
                'gravity': ['fundamental force', 'spacetime curvature', 'gravitational field'],
                'circuit': ['closed conducting path', 'electronic network', 'current loop system']
            }
        }
        
        return vocab_db
    
    def process(self, context: Any) -> Any:
        """
        Process and adapt content for age-appropriate delivery
        Returns: Modified context with adapted response
        """
        try:
            # Determine age profile
            profile = self._get_age_profile(context.child_age)
            
            # Get the model response to adapt
            response_text = context.model_response or ""
            
            # Apply age-appropriate adaptations
            adapted_response = self._adapt_response(
                response_text,
                profile,
                context
            )
            
            # Update context
            context.model_response = adapted_response
            context.metadata['age_profile'] = profile.grade_level
            context.metadata['adaptation_applied'] = True
            
            # Track adaptation metrics
            self._track_adaptation_metrics(context, profile)
            
            return context
            
        except Exception as e:
            logger.error(f"Age adaptation error: {e}")
            # Return original context on error
            return context
    
    def _get_age_profile(self, age: int) -> AgeProfile:
        """Get appropriate age profile for child"""
        for profile in self.age_profiles.values():
            if profile.age_range[0] <= age <= profile.age_range[1]:
                return profile
        
        # Default to high school for older
        if age > 18:
            return self.age_profiles['high_school']
        
        # Default to early elementary for younger
        return self.age_profiles['early_elementary']
    
    def _adapt_response(self, text: str, profile: AgeProfile, context: Any) -> str:
        """Apply comprehensive age-appropriate adaptations"""
        # Step 1: Simplify vocabulary
        text = self._adapt_vocabulary(text, profile)
        
        # Step 2: Adjust sentence complexity
        text = self._adapt_sentence_structure(text, profile)
        
        # Step 3: Add age-appropriate examples
        text = self._inject_relevant_examples(text, profile, context)
        
        # Step 4: Ensure appropriate length
        text = self._enforce_length_limits(text, profile)
        
        # Step 5: Add engagement elements
        text = self._add_engagement_elements(text, profile, context)
        
        # Step 6: Final safety check
        text = self._final_safety_review(text, profile)
        
        return text
    
    def _adapt_vocabulary(self, text: str, profile: AgeProfile) -> str:
        """Replace complex terms with age-appropriate alternatives"""
        if profile.vocabulary_level not in self.vocabulary_db:
            return text
        
        vocab_map = self.vocabulary_db[profile.vocabulary_level]
        
        for complex_term, simple_alternatives in vocab_map.items():
            if complex_term.lower() in text.lower():
                # Use the first alternative
                replacement = simple_alternatives[0]
                
                # Preserve capitalization
                if complex_term[0].isupper():
                    replacement = replacement.capitalize()
                
                # Replace with word boundaries
                pattern = re.compile(r'\b' + re.escape(complex_term) + r'\b', re.I)
                text = pattern.sub(replacement, text)
        
        return text
    
    def _adapt_sentence_structure(self, text: str, profile: AgeProfile) -> str:
        """Adjust sentence complexity based on age profile"""
        sentences = text.split('. ')
        adapted_sentences = []
        
        for sentence in sentences:
            if profile.sentence_complexity == 'simple':
                # Break complex sentences into simple ones
                if ',' in sentence or ' and ' in sentence or ' but ' in sentence:
                    parts = re.split(r'[,;]|\s+and\s+|\s+but\s+', sentence)
                    for part in parts:
                        if part.strip():
                            adapted_sentences.append(part.strip().capitalize())
                else:
                    adapted_sentences.append(sentence)
                    
            elif profile.sentence_complexity == 'compound':
                # Moderate complexity, keep some compound sentences
                if sentence.count(',') > 2:
                    # Too complex, simplify
                    parts = sentence.split(',')
                    adapted_sentences.append(f"{parts[0]}, {parts[1]}")
                    if len(parts) > 2:
                        adapted_sentences.append(' '.join(parts[2:]))
                else:
                    adapted_sentences.append(sentence)
                    
            else:
                # Complex or sophisticated - keep as is
                adapted_sentences.append(sentence)
        
        return '. '.join(adapted_sentences) + ('.' if adapted_sentences else '')
    
    def _inject_relevant_examples(self, text: str, profile: AgeProfile, context: Any) -> str:
        """Add age-appropriate examples to enhance understanding"""
        # Detect if examples might help
        if any(phrase in text.lower() for phrase in ['for example', 'such as', 'like']):
            return text  # Already has examples
        
        # Add examples based on profile preferences
        example_triggers = ['this means', 'in other words', 'think of it like']
        
        for trigger in example_triggers:
            if trigger in text.lower():
                continue
        
        # Insert age-appropriate example
        if profile.preferred_examples and len(text) < profile.max_words * 0.7:
            example_topic = profile.preferred_examples[0]
            
            if 'science' in context.input_text.lower():
                if profile.grade_level == 'K-2':
                    text += " It's like when you mix colors to make new ones!"
                elif profile.grade_level == '3-5':
                    text += " Think of it like a recipe where ingredients combine to make something new."
                elif profile.grade_level == '6-8':
                    text += " This is similar to how apps on your phone work together."
                else:
                    text += " This principle applies to many real-world applications."
        
        return text
    
    def _enforce_length_limits(self, text: str, profile: AgeProfile) -> str:
        """Ensure response fits within age-appropriate length"""
        words = text.split()
        
        if len(words) > profile.max_words:
            # Intelligently truncate while preserving meaning
            sentences = text.split('. ')
            truncated = []
            word_count = 0
            
            for sentence in sentences:
                sentence_words = len(sentence.split())
                if word_count + sentence_words <= profile.max_words:
                    truncated.append(sentence)
                    word_count += sentence_words
                else:
                    # Add a conclusion
                    if word_count < profile.max_words - 10:
                        truncated.append("Would you like to know more?")
                    break
            
            return '. '.join(truncated) + ('.' if truncated else '')
        
        return text
    
    def _add_engagement_elements(self, text: str, profile: AgeProfile, context: Any) -> str:
        """Add age-appropriate engagement elements"""
        # Add personalization
        if context.child_name and context.child_name not in text:
            if profile.grade_level in ['K-2', '3-5']:
                text = f"Hi {context.child_name}! " + text
        
        # Add encouragement based on age
        encouragements = {
            'K-2': ['Great question!', 'You\'re so curious!', 'Let\'s explore!'],
            '3-5': ['Excellent thinking!', 'That\'s a smart question!', 'Let\'s discover!'],
            '6-8': ['Good inquiry!', 'Interesting question!', 'Let\'s investigate!'],
            '9-12': ['Thoughtful question.', 'Let\'s analyze this.', 'Consider this:']
        }
        
        if profile.grade_level in encouragements:
            if not any(enc in text for enc in encouragements[profile.grade_level]):
                text = encouragements[profile.grade_level][0] + ' ' + text
        
        # Add follow-up prompts for younger learners
        if profile.grade_level in ['K-2', '3-5'] and '?' not in text:
            text += ' What do you think about that?'
        
        return text
    
    def _final_safety_review(self, text: str, profile: AgeProfile) -> str:
        """Final safety check for age-appropriate content"""
        # Remove any remaining complex concepts for young learners
        if profile.grade_level == 'K-2':
            # Remove numbers that are too large
            text = re.sub(r'\b\d{4,}\b', 'many', text)
            
            # Remove complex units
            text = text.replace('kilometers', 'far away')
            text = text.replace('celsius', 'degrees')
            text = text.replace('fahrenheit', 'degrees')
        
        # Ensure no avoided topics remain
        for topic in profile.avoided_topics:
            if topic.replace('_', ' ') in text.lower():
                # Generic replacement
                text = re.sub(
                    r'\b' + topic.replace('_', ' ') + r'\b',
                    'advanced topic',
                    text,
                    flags=re.I
                )
        
        return text
    
    def _track_adaptation_metrics(self, context: Any, profile: AgeProfile) -> None:
        """Track adaptation metrics for quality assurance"""
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'profile_used': profile.grade_level,
            'child_age': context.child_age,
            'original_length': len(context.model_response.split()) if context.model_response else 0,
            'adapted_length': len(context.model_response.split()) if context.model_response else 0,
            'adaptations_applied': context.metadata.get('adaptation_applied', False)
        }
        
        # Save metrics
        metrics_file = self.usb_path / 'logs' / 'adaptation_metrics.json'
        
        try:
            metrics_file.parent.mkdir(parents=True, exist_ok=True)
            
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    all_metrics = json.load(f)
            else:
                all_metrics = []
            
            all_metrics.append(metrics)
            
            # Keep last 10000 metrics
            if len(all_metrics) > 10000:
                all_metrics = all_metrics[-10000:]
            
            with open(metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save adaptation metrics: {e}")

class ComplexityAnalyzer:
    """Analyze text complexity for age-appropriate validation"""
    
    def calculate_reading_level(self, text: str) -> float:
        """Calculate approximate reading grade level using Flesch-Kincaid"""
        sentences = text.split('. ')
        words = text.split()
        syllables = sum(self._count_syllables(word) for word in words)
        
        if len(sentences) == 0 or len(words) == 0:
            return 0.0
        
        # Flesch-Kincaid Grade Level formula
        grade_level = (0.39 * (len(words) / len(sentences)) +
                      11.8 * (syllables / len(words)) - 15.59)
        
        return max(0.0, min(18.0, grade_level))
    
    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word"""
        word = word.lower().strip()
        vowels = 'aeiou'
        syllable_count = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        # Adjust for silent e
        if word.endswith('e'):
            syllable_count = max(1, syllable_count - 1)
        
        return max(1, syllable_count)

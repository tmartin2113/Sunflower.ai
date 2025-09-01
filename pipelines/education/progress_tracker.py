"""
Sunflower AI Professional System - Progress Tracker Pipeline
Comprehensive learning progress monitoring and analytics
Version: 6.2 | Adaptive Learning Analytics
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import hashlib
import statistics

logger = logging.getLogger(__name__)

class MasteryLevel(Enum):
    """Learning mastery levels"""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    PROFICIENT = "proficient"
    ADVANCED = "advanced"
    EXPERT = "expert"

@dataclass
class SkillProgress:
    """Individual skill progress tracking"""
    skill_name: str
    current_level: float  # 0.0 to 1.0
    mastery_level: MasteryLevel
    total_practice: int
    successful_attempts: int
    last_practiced: str
    growth_rate: float
    strengths: List[str]
    areas_for_improvement: List[str]

@dataclass
class LearningMilestone:
    """Learning milestone achievement"""
    milestone_id: str
    name: str
    description: str
    achieved_date: str
    skill_requirements: Dict[str, float]
    evidence: List[str]

class ProgressTrackerPipeline:
    """
    Production-grade learning progress tracking system
    Monitors, analyzes, and reports on educational progress
    """
    
    def __init__(self, usb_path: Path):
        """Initialize progress tracking system"""
        self.usb_path = Path(usb_path)
        self.progress_path = self.usb_path / 'progress'
        self.analytics_path = self.usb_path / 'analytics'
        
        # Create necessary directories
        self.progress_path.mkdir(parents=True, exist_ok=True)
        self.analytics_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize tracking components
        self.skill_tracker = SkillTracker(self.progress_path)
        self.milestone_tracker = MilestoneTracker(self.progress_path)
        self.analytics_engine = AnalyticsEngine(self.analytics_path)
        self.adaptive_engine = AdaptiveLearningEngine()
        
        # Load progress configurations
        self.config = self._load_progress_config()
        
        # Performance history cache
        self.performance_cache = defaultdict(lambda: deque(maxlen=100))
        
        logger.info("Progress tracker initialized with adaptive analytics")
    
    def _load_progress_config(self) -> Dict[str, Any]:
        """Load progress tracking configuration"""
        config_file = self.progress_path / 'tracker_config.json'
        
        default_config = {
            'mastery_thresholds': {
                'novice': 0.0,
                'beginner': 0.2,
                'intermediate': 0.4,
                'proficient': 0.6,
                'advanced': 0.8,
                'expert': 0.95
            },
            'skill_decay_rate': 0.01,  # Daily decay without practice
            'minimum_attempts_for_assessment': 3,
            'milestone_check_frequency': 5,  # Check every 5 interactions
            'adaptive_difficulty_enabled': True,
            'personalized_recommendations': True,
            'progress_report_frequency': 'weekly'
        }
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except Exception as e:
            logger.warning(f"Using default progress config: {e}")
        
        return default_config
    
    def process(self, context: Any) -> Tuple[Any, Dict[str, Any]]:
        """
        Process interaction for progress tracking
        Returns: (context, progress_metadata)
        """
        try:
            # Extract learning indicators
            indicators = self._extract_learning_indicators(context)
            
            # Update skill progress
            skill_updates = self.skill_tracker.update_skills(
                context.profile_id,
                indicators,
                context
            )
            
            # Check for milestone achievements
            new_milestones = self.milestone_tracker.check_milestones(
                context.profile_id,
                skill_updates
            )
            
            # Perform learning analytics
            analytics = self.analytics_engine.analyze_progress(
                context.profile_id,
                indicators,
                skill_updates
            )
            
            # Generate adaptive recommendations
            recommendations = self.adaptive_engine.generate_recommendations(
                context,
                skill_updates,
                analytics
            )
            
            # Update context with recommendations
            if recommendations['difficulty_adjustment']:
                context.metadata['recommended_difficulty'] = recommendations['difficulty_adjustment']
            
            if recommendations['next_topics']:
                context.metadata['suggested_topics'] = recommendations['next_topics']
            
            # Store progress snapshot
            self._save_progress_snapshot(context, skill_updates, analytics)
            
            # Generate progress metadata
            progress_metadata = {
                'skills_practiced': list(skill_updates.keys()),
                'skill_improvements': {k: v['improvement'] for k, v in skill_updates.items()},
                'current_mastery_levels': {k: v['mastery'].value for k, v in skill_updates.items()},
                'milestones_achieved': [m.name for m in new_milestones],
                'learning_velocity': analytics.get('learning_velocity', 0.0),
                'engagement_score': analytics.get('engagement_score', 0.0),
                'recommendations': recommendations,
                'progress_percentile': self._calculate_progress_percentile(context.profile_id)
            }
            
            # Add celebration message for milestones
            if new_milestones:
                celebration = self._generate_celebration_message(new_milestones[0], context)
                context.model_response = f"{celebration}\n\n{context.model_response}"
            
            return context, progress_metadata
            
        except Exception as e:
            logger.error(f"Progress tracking error: {e}")
            return context, {'error': str(e)}
    
    def _extract_learning_indicators(self, context: Any) -> Dict[str, Any]:
        """Extract learning indicators from interaction"""
        indicators = {
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': context.session_id,
            'interaction_type': self._classify_interaction(context),
            'subject_area': context.metadata.get('subject_area', 'general'),
            'concepts': [],
            'skills_demonstrated': [],
            'correctness': 0.0,
            'complexity_level': 0.0,
            'time_spent': context.metadata.get('response_time', 0),
            'help_requested': False,
            'confidence_level': 0.0
        }
        
        # Analyze input for learning signals
        input_lower = context.input_text.lower()
        
        # Check for help requests
        help_indicators = ['help', 'stuck', "don't understand", 'confused', 'explain']
        indicators['help_requested'] = any(ind in input_lower for ind in help_indicators)
        
        # Assess confidence level
        confidence_high = ['i know', 'easy', 'simple', 'got it', 'understand']
        confidence_low = ['maybe', 'guess', 'not sure', 'think', 'probably']
        
        if any(phrase in input_lower for phrase in confidence_high):
            indicators['confidence_level'] = 0.8
        elif any(phrase in input_lower for phrase in confidence_low):
            indicators['confidence_level'] = 0.3
        else:
            indicators['confidence_level'] = 0.5
        
        # Extract demonstrated skills
        if 'solve' in input_lower or 'calculate' in input_lower:
            indicators['skills_demonstrated'].append('problem_solving')
        if 'why' in input_lower or 'how' in input_lower:
            indicators['skills_demonstrated'].append('critical_thinking')
        if 'create' in input_lower or 'design' in input_lower:
            indicators['skills_demonstrated'].append('creativity')
        
        # Assess correctness (simplified - in production would analyze actual answers)
        if context.safety_flags:
            indicators['correctness'] = 0.0
        elif indicators['help_requested']:
            indicators['correctness'] = 0.3
        else:
            indicators['correctness'] = 0.7 + (indicators['confidence_level'] * 0.3)
        
        # Assess complexity
        indicators['complexity_level'] = self._assess_complexity_level(context)
        
        # Extract concepts from metadata
        indicators['concepts'] = context.metadata.get('concepts_covered', [])
        
        return indicators
    
    def _classify_interaction(self, context: Any) -> str:
        """Classify the type of learning interaction"""
        input_lower = context.input_text.lower()
        
        if any(q in input_lower for q in ['solve', 'calculate', 'find']):
            return 'problem_solving'
        elif any(q in input_lower for q in ['what is', 'define', 'meaning']):
            return 'definition'
        elif any(q in input_lower for q in ['why', 'how does', 'explain']):
            return 'explanation'
        elif any(q in input_lower for q in ['create', 'build', 'design']):
            return 'creative'
        elif any(q in input_lower for q in ['test', 'quiz', 'practice']):
            return 'assessment'
        else:
            return 'exploration'
    
    def _assess_complexity_level(self, context: Any) -> float:
        """Assess complexity level of interaction (0.0 to 1.0)"""
        # Base complexity on age-appropriate expectations
        age = context.child_age
        text = context.input_text.lower()
        
        # Age-based baseline
        age_baselines = {
            5: 0.1, 6: 0.15, 7: 0.2, 8: 0.25, 9: 0.3,
            10: 0.35, 11: 0.4, 12: 0.45, 13: 0.5,
            14: 0.6, 15: 0.7, 16: 0.8, 17: 0.9, 18: 1.0
        }
        
        baseline = age_baselines.get(age, 0.5)
        
        # Adjust based on content complexity
        complex_indicators = [
            'advanced', 'complex', 'difficult', 'challenging',
            'theorem', 'proof', 'derivative', 'integral'
        ]
        
        simple_indicators = [
            'basic', 'simple', 'easy', 'beginner',
            'count', 'add', 'color', 'shape'
        ]
        
        if any(ind in text for ind in complex_indicators):
            return min(1.0, baseline + 0.3)
        elif any(ind in text for ind in simple_indicators):
            return max(0.0, baseline - 0.2)
        
        return baseline
    
    def _save_progress_snapshot(self, context: Any, skill_updates: Dict, analytics: Dict) -> None:
        """Save snapshot of current progress"""
        snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': context.session_id,
            'profile_id': context.profile_id,
            'skills': skill_updates,
            'analytics': analytics,
            'interaction_count': context.metadata.get('interaction_count', 0)
        }
        
        # Save to profile-specific file
        snapshot_file = self.progress_path / f"{context.profile_id}_snapshots.json"
        
        try:
            if snapshot_file.exists():
                with open(snapshot_file, 'r') as f:
                    snapshots = json.load(f)
            else:
                snapshots = []
            
            snapshots.append(snapshot)
            
            # Keep only last 1000 snapshots
            if len(snapshots) > 1000:
                snapshots = snapshots[-1000:]
            
            with open(snapshot_file, 'w') as f:
                json.dump(snapshots, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save progress snapshot: {e}")
    
    def _calculate_progress_percentile(self, profile_id: str) -> float:
        """Calculate progress percentile compared to age group"""
        try:
            # Load comparative data
            stats_file = self.analytics_path / 'comparative_stats.json'
            
            if not stats_file.exists():
                return 50.0  # Default to median
            
            with open(stats_file, 'r') as f:
                stats = json.load(f)
            
            # Get profile's total progress score
            profile_score = self._calculate_total_progress_score(profile_id)
            
            # Compare to age group
            age_group_scores = stats.get('age_group_scores', {})
            
            if profile_id in age_group_scores:
                scores = age_group_scores[profile_id]
                percentile = sum(1 for s in scores if s < profile_score) / len(scores) * 100
                return round(percentile, 1)
            
            return 50.0
            
        except Exception as e:
            logger.warning(f"Could not calculate percentile: {e}")
            return 50.0
    
    def _calculate_total_progress_score(self, profile_id: str) -> float:
        """Calculate total progress score for profile"""
        try:
            progress_file = self.progress_path / f"{profile_id}_progress.json"
            
            if not progress_file.exists():
                return 0.0
            
            with open(progress_file, 'r') as f:
                progress = json.load(f)
            
            # Calculate weighted score
            skill_score = sum(progress.get('skills_developed', {}).values())
            objective_score = len(progress.get('objectives_encountered', {})) * 10
            interaction_score = progress.get('total_interactions', 0) * 0.1
            
            return skill_score + objective_score + interaction_score
            
        except Exception:
            return 0.0
    
    def _generate_celebration_message(self, milestone: LearningMilestone, context: Any) -> str:
        """Generate age-appropriate celebration message"""
        age = context.child_age
        name = context.child_name
        
        if age < 8:
            messages = [
                f"🌟 Amazing job, {name}! You achieved {milestone.name}! 🌟",
                f"🎉 Wow! You unlocked {milestone.name}! You're doing great! 🎉",
                f"⭐ Fantastic, {name}! {milestone.name} completed! Keep going! ⭐"
            ]
        elif age < 12:
            messages = [
                f"🏆 Excellent work! You've achieved {milestone.name}!",
                f"💪 Great progress! {milestone.name} milestone unlocked!",
                f"🎯 Impressive! You've mastered {milestone.name}!"
            ]
        else:
            messages = [
                f"Achievement Unlocked: {milestone.name}",
                f"Milestone Reached: {milestone.name} - Well done!",
                f"Congratulations on achieving {milestone.name}!"
            ]
        
        import random
        return random.choice(messages)

class SkillTracker:
    """Track individual skill development"""
    
    def __init__(self, progress_path: Path):
        """Initialize skill tracker"""
        self.progress_path = progress_path
        self.skill_database = self._load_skill_database()
    
    def _load_skill_database(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive skill database"""
        return {
            # Science skills
            'observation': {'category': 'science', 'base_difficulty': 0.2},
            'hypothesis_formation': {'category': 'science', 'base_difficulty': 0.5},
            'experimentation': {'category': 'science', 'base_difficulty': 0.6},
            'data_analysis': {'category': 'science', 'base_difficulty': 0.7},
            'scientific_reasoning': {'category': 'science', 'base_difficulty': 0.8},
            
            # Technology skills
            'digital_literacy': {'category': 'technology', 'base_difficulty': 0.3},
            'coding_basics': {'category': 'technology', 'base_difficulty': 0.5},
            'algorithm_design': {'category': 'technology', 'base_difficulty': 0.7},
            'debugging': {'category': 'technology', 'base_difficulty': 0.6},
            'system_design': {'category': 'technology', 'base_difficulty': 0.9},
            
            # Engineering skills
            'problem_identification': {'category': 'engineering', 'base_difficulty': 0.4},
            'design_thinking': {'category': 'engineering', 'base_difficulty': 0.6},
            'prototyping': {'category': 'engineering', 'base_difficulty': 0.7},
            'testing_iteration': {'category': 'engineering', 'base_difficulty': 0.7},
            'optimization': {'category': 'engineering', 'base_difficulty': 0.8},
            
            # Mathematics skills
            'number_sense': {'category': 'mathematics', 'base_difficulty': 0.2},
            'arithmetic': {'category': 'mathematics', 'base_difficulty': 0.3},
            'algebraic_thinking': {'category': 'mathematics', 'base_difficulty': 0.6},
            'geometric_reasoning': {'category': 'mathematics', 'base_difficulty': 0.6},
            'mathematical_proof': {'category': 'mathematics', 'base_difficulty': 0.9},
            
            # Cross-cutting skills
            'critical_thinking': {'category': 'general', 'base_difficulty': 0.5},
            'problem_solving': {'category': 'general', 'base_difficulty': 0.5},
            'creativity': {'category': 'general', 'base_difficulty': 0.4},
            'collaboration': {'category': 'general', 'base_difficulty': 0.4},
            'communication': {'category': 'general', 'base_difficulty': 0.3}
        }
    
    def update_skills(self, profile_id: str, indicators: Dict, context: Any) -> Dict[str, Dict[str, Any]]:
        """Update skill progress based on interaction"""
        skill_file = self.progress_path / f"{profile_id}_skills.json"
        
        try:
            # Load existing skills
            if skill_file.exists():
                with open(skill_file, 'r') as f:
                    skills = json.load(f)
            else:
                skills = {}
            
            # Update relevant skills
            updated_skills = {}
            
            for skill_name in indicators['skills_demonstrated']:
                if skill_name in self.skill_database:
                    # Get or create skill record
                    if skill_name not in skills:
                        skills[skill_name] = {
                            'level': 0.0,
                            'attempts': 0,
                            'successes': 0,
                            'last_practiced': None,
                            'history': []
                        }
                    
                    # Update skill based on performance
                    skill_data = skills[skill_name]
                    skill_data['attempts'] += 1
                    
                    # Calculate performance
                    performance = indicators['correctness'] * indicators['complexity_level']
                    
                    if performance > 0.5:
                        skill_data['successes'] += 1
                    
                    # Update skill level using adaptive algorithm
                    old_level = skill_data['level']
                    skill_data['level'] = self._update_skill_level(
                        old_level,
                        performance,
                        skill_data['attempts']
                    )
                    
                    # Record history
                    skill_data['history'].append({
                        'timestamp': indicators['timestamp'],
                        'performance': performance,
                        'level_after': skill_data['level']
                    })
                    
                    # Keep only last 50 history entries
                    if len(skill_data['history']) > 50:
                        skill_data['history'] = skill_data['history'][-50:]
                    
                    skill_data['last_practiced'] = indicators['timestamp']
                    
                    # Determine mastery level
                    mastery = self._determine_mastery_level(skill_data['level'])
                    
                    updated_skills[skill_name] = {
                        'old_level': old_level,
                        'new_level': skill_data['level'],
                        'improvement': skill_data['level'] - old_level,
                        'mastery': mastery,
                        'total_practice': skill_data['attempts']
                    }
            
            # Apply skill decay for unpracticed skills
            self._apply_skill_decay(skills)
            
            # Save updated skills
            with open(skill_file, 'w') as f:
                json.dump(skills, f, indent=2)
            
            return updated_skills
            
        except Exception as e:
            logger.error(f"Failed to update skills: {e}")
            return {}
    
    def _update_skill_level(self, current_level: float, performance: float, attempts: int) -> float:
        """Update skill level using adaptive algorithm"""
        # Learning rate decreases with more attempts (mastery takes time)
        learning_rate = 0.1 / (1 + attempts * 0.01)
        
        # Update based on performance vs current level
        if performance > current_level:
            # Performed better than current level - increase
            increase = learning_rate * (performance - current_level)
            new_level = current_level + increase
        else:
            # Performed worse - slight decrease
            decrease = learning_rate * 0.5 * (current_level - performance)
            new_level = current_level - decrease
        
        # Ensure bounds [0, 1]
        return max(0.0, min(1.0, new_level))
    
    def _determine_mastery_level(self, skill_level: float) -> MasteryLevel:
        """Determine mastery level from skill value"""
        if skill_level >= 0.95:
            return MasteryLevel.EXPERT
        elif skill_level >= 0.8:
            return MasteryLevel.ADVANCED
        elif skill_level >= 0.6:
            return MasteryLevel.PROFICIENT
        elif skill_level >= 0.4:
            return MasteryLevel.INTERMEDIATE
        elif skill_level >= 0.2:
            return MasteryLevel.BEGINNER
        else:
            return MasteryLevel.NOVICE
    
    def _apply_skill_decay(self, skills: Dict[str, Dict]) -> None:
        """Apply decay to unpracticed skills"""
        current_time = datetime.utcnow()
        decay_rate = 0.001  # Daily decay rate
        
        for skill_name, skill_data in skills.items():
            if skill_data.get('last_practiced'):
                last_practiced = datetime.fromisoformat(skill_data['last_practiced'])
                days_since = (current_time - last_practiced).days
                
                if days_since > 7:  # Only decay after a week
                    decay = decay_rate * (days_since - 7)
                    skill_data['level'] = max(0.0, skill_data['level'] - decay)

class MilestoneTracker:
    """Track learning milestone achievements"""
    
    def __init__(self, progress_path: Path):
        """Initialize milestone tracker"""
        self.progress_path = progress_path
        self.milestones = self._define_milestones()
    
    def _define_milestones(self) -> Dict[str, LearningMilestone]:
        """Define learning milestones"""
        milestones = {
            'first_steps': LearningMilestone(
                milestone_id='first_steps',
                name='First Steps',
                description='Complete your first learning session',
                achieved_date='',
                skill_requirements={},
                evidence=[]
            ),
            'problem_solver': LearningMilestone(
                milestone_id='problem_solver',
                name='Problem Solver',
                description='Successfully solve 10 problems',
                achieved_date='',
                skill_requirements={'problem_solving': 0.3},
                evidence=[]
            ),
            'science_explorer': LearningMilestone(
                milestone_id='science_explorer',
                name='Science Explorer',
                description='Master basic science concepts',
                achieved_date='',
                skill_requirements={'observation': 0.4, 'experimentation': 0.3},
                evidence=[]
            ),
            'code_warrior': LearningMilestone(
                milestone_id='code_warrior',
                name='Code Warrior',
                description='Write your first program',
                achieved_date='',
                skill_requirements={'coding_basics': 0.4},
                evidence=[]
            ),
            'math_wizard': LearningMilestone(
                milestone_id='math_wizard',
                name='Math Wizard',
                description='Master grade-level mathematics',
                achieved_date='',
                skill_requirements={'arithmetic': 0.6, 'problem_solving': 0.5},
                evidence=[]
            ),
            'stem_champion': LearningMilestone(
                milestone_id='stem_champion',
                name='STEM Champion',
                description='Achieve proficiency across all STEM areas',
                achieved_date='',
                skill_requirements={
                    'scientific_reasoning': 0.5,
                    'coding_basics': 0.5,
                    'design_thinking': 0.5,
                    'algebraic_thinking': 0.5
                },
                evidence=[]
            )
        }
        
        return milestones
    
    def check_milestones(self, profile_id: str, skill_updates: Dict) -> List[LearningMilestone]:
        """Check for newly achieved milestones"""
        achieved_file = self.progress_path / f"{profile_id}_milestones.json"
        skills_file = self.progress_path / f"{profile_id}_skills.json"
        
        try:
            # Load achieved milestones
            if achieved_file.exists():
                with open(achieved_file, 'r') as f:
                    achieved = json.load(f)
            else:
                achieved = {}
            
            # Load current skills
            if skills_file.exists():
                with open(skills_file, 'r') as f:
                    current_skills = json.load(f)
            else:
                return []
            
            new_milestones = []
            
            # Check each milestone
            for milestone_id, milestone in self.milestones.items():
                if milestone_id not in achieved:
                    # Check if requirements are met
                    requirements_met = True
                    
                    for skill_name, required_level in milestone.skill_requirements.items():
                        if skill_name not in current_skills:
                            requirements_met = False
                            break
                        
                        if current_skills[skill_name]['level'] < required_level:
                            requirements_met = False
                            break
                    
                    if requirements_met or (milestone_id == 'first_steps' and len(current_skills) > 0):
                        # Milestone achieved!
                        milestone.achieved_date = datetime.utcnow().isoformat()
                        milestone.evidence = list(skill_updates.keys())
                        
                        achieved[milestone_id] = asdict(milestone)
                        new_milestones.append(milestone)
            
            # Save updated achievements
            if new_milestones:
                with open(achieved_file, 'w') as f:
                    json.dump(achieved, f, indent=2)
            
            return new_milestones
            
        except Exception as e:
            logger.error(f"Failed to check milestones: {e}")
            return []

class AnalyticsEngine:
    """Advanced learning analytics engine"""
    
    def __init__(self, analytics_path: Path):
        """Initialize analytics engine"""
        self.analytics_path = analytics_path
        self.analytics_path.mkdir(parents=True, exist_ok=True)
    
    def analyze_progress(self, profile_id: str, indicators: Dict, skill_updates: Dict) -> Dict[str, Any]:
        """Perform comprehensive progress analytics"""
        analytics = {
            'learning_velocity': self._calculate_learning_velocity(profile_id),
            'engagement_score': self._calculate_engagement_score(indicators),
            'mastery_distribution': self._analyze_mastery_distribution(profile_id),
            'learning_patterns': self._identify_learning_patterns(profile_id),
            'strengths': self._identify_strengths(skill_updates),
            'improvement_areas': self._identify_improvement_areas(profile_id),
            'predicted_next_milestone': self._predict_next_milestone(profile_id),
            'optimal_learning_time': self._determine_optimal_learning_time(profile_id)
        }
        
        # Save analytics
        self._save_analytics(profile_id, analytics)
        
        return analytics
    
    def _calculate_learning_velocity(self, profile_id: str) -> float:
        """Calculate rate of learning progress"""
        try:
            snapshots_file = self.analytics_path.parent / 'progress' / f"{profile_id}_snapshots.json"
            
            if not snapshots_file.exists():
                return 0.0
            
            with open(snapshots_file, 'r') as f:
                snapshots = json.load(f)
            
            if len(snapshots) < 2:
                return 0.0
            
            # Calculate average skill improvement over time
            recent_snapshots = snapshots[-10:]  # Last 10 interactions
            
            if len(recent_snapshots) < 2:
                return 0.0
            
            total_improvement = 0.0
            comparisons = 0
            
            for i in range(1, len(recent_snapshots)):
                prev = recent_snapshots[i-1]
                curr = recent_snapshots[i]
                
                if 'skills' in prev and 'skills' in curr:
                    for skill_name in curr.get('skills', {}):
                        if skill_name in prev.get('skills', {}):
                            improvement = curr['skills'][skill_name].get('improvement', 0)
                            total_improvement += improvement
                            comparisons += 1
            
            if comparisons > 0:
                return total_improvement / comparisons
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Could not calculate learning velocity: {e}")
            return 0.0
    
    def _calculate_engagement_score(self, indicators: Dict) -> float:
        """Calculate engagement score from indicators"""
        score = 50.0  # Base score
        
        # Positive indicators
        if not indicators['help_requested']:
            score += 10
        if indicators['confidence_level'] > 0.6:
            score += 10
        if indicators['complexity_level'] > 0.5:
            score += 15
        if len(indicators['skills_demonstrated']) > 1:
            score += 10
        
        # Negative indicators
        if indicators['correctness'] < 0.3:
            score -= 10
        if indicators['time_spent'] < 100:  # Very quick response
            score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _analyze_mastery_distribution(self, profile_id: str) -> Dict[str, int]:
        """Analyze distribution of skill mastery levels"""
        try:
            skills_file = self.analytics_path.parent / 'progress' / f"{profile_id}_skills.json"
            
            if not skills_file.exists():
                return {}
            
            with open(skills_file, 'r') as f:
                skills = json.load(f)
            
            distribution = defaultdict(int)
            
            for skill_data in skills.values():
                level = skill_data.get('level', 0.0)
                
                if level >= 0.95:
                    distribution['expert'] += 1
                elif level >= 0.8:
                    distribution['advanced'] += 1
                elif level >= 0.6:
                    distribution['proficient'] += 1
                elif level >= 0.4:
                    distribution['intermediate'] += 1
                elif level >= 0.2:
                    distribution['beginner'] += 1
                else:
                    distribution['novice'] += 1
            
            return dict(distribution)
            
        except Exception:
            return {}
    
    def _identify_learning_patterns(self, profile_id: str) -> Dict[str, Any]:
        """Identify patterns in learning behavior"""
        patterns = {
            'preferred_subjects': [],
            'peak_performance_time': None,
            'average_session_length': 0,
            'learning_style': 'balanced'
        }
        
        try:
            # Analyze interaction history for patterns
            snapshots_file = self.analytics_path.parent / 'progress' / f"{profile_id}_snapshots.json"
            
            if snapshots_file.exists():
                with open(snapshots_file, 'r') as f:
                    snapshots = json.load(f)
                
                # Analyze subject preferences
                subject_counts = defaultdict(int)
                
                for snapshot in snapshots[-50:]:  # Last 50 interactions
                    if 'analytics' in snapshot:
                        subject = snapshot['analytics'].get('subject', 'general')
                        subject_counts[subject] += 1
                
                # Get top subjects
                if subject_counts:
                    sorted_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)
                    patterns['preferred_subjects'] = [s[0] for s in sorted_subjects[:3]]
                
                # Detect learning style
                interaction_types = defaultdict(int)
                
                for snapshot in snapshots[-30:]:
                    if 'analytics' in snapshot:
                        int_type = snapshot['analytics'].get('interaction_type', 'general')
                        interaction_types[int_type] += 1
                
                if interaction_types:
                    dominant_type = max(interaction_types, key=interaction_types.get)
                    
                    style_map = {
                        'problem_solving': 'practical',
                        'explanation': 'theoretical',
                        'creative': 'creative',
                        'exploration': 'exploratory'
                    }
                    
                    patterns['learning_style'] = style_map.get(dominant_type, 'balanced')
            
        except Exception as e:
            logger.warning(f"Could not identify learning patterns: {e}")
        
        return patterns
    
    def _identify_strengths(self, skill_updates: Dict) -> List[str]:
        """Identify current strengths"""
        strengths = []
        
        for skill_name, update_data in skill_updates.items():
            if update_data['new_level'] > 0.6:
                strengths.append(skill_name)
        
        return strengths[:5]  # Top 5 strengths
    
    def _identify_improvement_areas(self, profile_id: str) -> List[str]:
        """Identify areas needing improvement"""
        try:
            skills_file = self.analytics_path.parent / 'progress' / f"{profile_id}_skills.json"
            
            if not skills_file.exists():
                return []
            
            with open(skills_file, 'r') as f:
                skills = json.load(f)
            
            # Find skills with low levels or high failure rates
            improvement_areas = []
            
            for skill_name, skill_data in skills.items():
                level = skill_data.get('level', 0.0)
                attempts = skill_data.get('attempts', 0)
                successes = skill_data.get('successes', 0)
                
                success_rate = successes / attempts if attempts > 0 else 0
                
                if level < 0.4 or success_rate < 0.5:
                    improvement_areas.append(skill_name)
            
            return improvement_areas[:5]  # Top 5 areas
            
        except Exception:
            return []
    
    def _predict_next_milestone(self, profile_id: str) -> Optional[str]:
        """Predict next likely milestone achievement"""
        # Simplified prediction - in production would use ML
        try:
            skills_file = self.analytics_path.parent / 'progress' / f"{profile_id}_skills.json"
            achieved_file = self.analytics_path.parent / 'progress' / f"{profile_id}_milestones.json"
            
            if not skills_file.exists():
                return 'first_steps'
            
            with open(skills_file, 'r') as f:
                skills = json.load(f)
            
            if achieved_file.exists():
                with open(achieved_file, 'r') as f:
                    achieved = json.load(f)
            else:
                achieved = {}
            
            # Check which milestone is closest to achievement
            milestone_distances = {}
            milestones = MilestoneTracker(self.analytics_path.parent / 'progress').milestones
            
            for milestone_id, milestone in milestones.items():
                if milestone_id not in achieved:
                    distance = 0
                    requirement_count = 0
                    
                    for skill_name, required_level in milestone.skill_requirements.items():
                        current_level = skills.get(skill_name, {}).get('level', 0.0)
                        distance += max(0, required_level - current_level)
                        requirement_count += 1
                    
                    if requirement_count > 0:
                        milestone_distances[milestone_id] = distance / requirement_count
            
            if milestone_distances:
                return min(milestone_distances, key=milestone_distances.get)
            
            return None
            
        except Exception:
            return None
    
    def _determine_optimal_learning_time(self, profile_id: str) -> Optional[str]:
        """Determine optimal learning time based on performance patterns"""
        # Simplified - would analyze temporal patterns in production
        return "afternoon"  # Placeholder
    
    def _save_analytics(self, profile_id: str, analytics: Dict) -> None:
        """Save analytics results"""
        analytics_file = self.analytics_path / f"{profile_id}_analytics.json"
        
        try:
            analytics['timestamp'] = datetime.utcnow().isoformat()
            analytics['profile_id'] = profile_id
            
            # Load existing analytics
            if analytics_file.exists():
                with open(analytics_file, 'r') as f:
                    all_analytics = json.load(f)
            else:
                all_analytics = []
            
            all_analytics.append(analytics)
            
            # Keep last 100 analytics records
            if len(all_analytics) > 100:
                all_analytics = all_analytics[-100:]
            
            with open(analytics_file, 'w') as f:
                json.dump(all_analytics, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save analytics: {e}")

class AdaptiveLearningEngine:
    """Adaptive learning recommendation engine"""
    
    def generate_recommendations(self, context: Any, skill_updates: Dict, 
                                analytics: Dict) -> Dict[str, Any]:
        """Generate personalized learning recommendations"""
        recommendations = {
            'difficulty_adjustment': self._recommend_difficulty_adjustment(analytics),
            'next_topics': self._recommend_next_topics(context, analytics),
            'learning_activities': self._recommend_activities(context, analytics),
            'practice_focus': self._recommend_practice_focus(analytics),
            'motivational_message': self._generate_motivational_message(context, analytics)
        }
        
        return recommendations
    
    def _recommend_difficulty_adjustment(self, analytics: Dict) -> str:
        """Recommend difficulty level adjustment"""
        engagement = analytics.get('engagement_score', 50)
        velocity = analytics.get('learning_velocity', 0)
        
        if engagement > 80 and velocity > 0.1:
            return 'increase'
        elif engagement < 30 or velocity < -0.05:
            return 'decrease'
        else:
            return 'maintain'
    
    def _recommend_next_topics(self, context: Any, analytics: Dict) -> List[str]:
        """Recommend next topics to explore"""
        patterns = analytics.get('learning_patterns', {})
        preferred_subjects = patterns.get('preferred_subjects', [])
        
        # Base recommendations on preferences and improvement areas
        topics = []
        
        if preferred_subjects:
            # Advance in preferred subjects
            for subject in preferred_subjects[:2]:
                topics.append(f"Advanced {subject}")
        
        # Add improvement areas
        improvement_areas = analytics.get('improvement_areas', [])
        for area in improvement_areas[:2]:
            topics.append(f"Practice {area}")
        
        # Add exploratory topic
        topics.append("Explore a new STEM area")
        
        return topics[:5]
    
    def _recommend_activities(self, context: Any, analytics: Dict) -> List[str]:
        """Recommend specific learning activities"""
        style = analytics.get('learning_patterns', {}).get('learning_style', 'balanced')
        
        activity_map = {
            'practical': [
                'Try a hands-on experiment',
                'Solve real-world problems',
                'Build a project'
            ],
            'theoretical': [
                'Read about the concept',
                'Watch educational videos',
                'Explore the theory behind it'
            ],
            'creative': [
                'Design your own solution',
                'Create something unique',
                'Invent a new approach'
            ],
            'exploratory': [
                'Investigate different methods',
                'Compare approaches',
                'Discover connections'
            ],
            'balanced': [
                'Mix theory and practice',
                'Try different approaches',
                'Explore various activities'
            ]
        }
        
        return activity_map.get(style, activity_map['balanced'])
    
    def _recommend_practice_focus(self, analytics: Dict) -> List[str]:
        """Recommend areas to focus practice on"""
        improvement_areas = analytics.get('improvement_areas', [])
        
        if improvement_areas:
            return improvement_areas[:3]
        
        return ['Continue exploring', 'Challenge yourself', 'Review fundamentals']
    
    def _generate_motivational_message(self, context: Any, analytics: Dict) -> str:
        """Generate personalized motivational message"""
        velocity = analytics.get('learning_velocity', 0)
        engagement = analytics.get('engagement_score', 50)
        
        if velocity > 0.1 and engagement > 70:
            messages = [
                "You're making excellent progress! Keep up the great work!",
                "Amazing learning velocity! You're on fire!",
                "Fantastic engagement! You're mastering these concepts!"
            ]
        elif velocity > 0:
            messages = [
                "Good progress! Every step forward counts!",
                "You're improving steadily. Keep going!",
                "Nice work! Your skills are growing!"
            ]
        else:
            messages = [
                "Remember, learning takes time. You've got this!",
                "Every expert was once a beginner. Keep trying!",
                "Challenges help us grow. Don't give up!"
            ]
        
        import random
        return random.choice(messages)

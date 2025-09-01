"""
Sunflower AI Professional System - Achievement System Pipeline
Gamified achievement and reward system for K-12 learners
Version: 6.2 | Motivational Learning Through Achievements
"""

import json
import logging
import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)

class AchievementRarity(Enum):
    """Achievement rarity levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class AchievementCategory(Enum):
    """Achievement categories"""
    EXPLORATION = "exploration"
    MASTERY = "mastery"
    PERSISTENCE = "persistence"
    CREATIVITY = "creativity"
    COLLABORATION = "collaboration"
    SPEED = "speed"
    ACCURACY = "accuracy"
    STREAK = "streak"
    SPECIAL = "special"

@dataclass
class Achievement:
    """Individual achievement definition"""
    id: str
    name: str
    description: str
    category: AchievementCategory
    rarity: AchievementRarity
    icon: str
    points: int
    requirements: Dict[str, Any]
    hidden: bool = False
    seasonal: bool = False
    unlocked: bool = False
    unlock_date: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Badge:
    """Visual badge representation"""
    id: str
    name: str
    image_id: str
    color: str
    sparkle_effect: bool
    achievement_id: str
    display_priority: int

@dataclass
class Reward:
    """Reward for achievements"""
    id: str
    name: str
    description: str
    type: str  # 'title', 'badge', 'theme', 'feature_unlock'
    value: Any
    achievement_id: str

class AchievementSystemPipeline:
    """
    Production-grade achievement and reward system
    Provides motivation through gamification
    """
    
    def __init__(self, usb_path: Path):
        """Initialize achievement system"""
        self.usb_path = Path(usb_path)
        self.achievements_path = self.usb_path / 'achievements'
        self.achievements_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize achievement components
        self.achievement_db = self._initialize_achievements()
        self.badge_system = BadgeSystem(self.achievements_path)
        self.reward_manager = RewardManager(self.achievements_path)
        self.leaderboard = LeaderboardManager(self.achievements_path)
        
        # Cache for performance
        self.unlock_cache = {}
        self.progress_cache = defaultdict(dict)
        
        logger.info("Achievement system initialized with gamification features")
    
    def _initialize_achievements(self) -> Dict[str, Achievement]:
        """Initialize comprehensive achievement database"""
        achievements = {}
        
        # Exploration achievements
        achievements.update(self._create_exploration_achievements())
        
        # Mastery achievements
        achievements.update(self._create_mastery_achievements())
        
        # Persistence achievements
        achievements.update(self._create_persistence_achievements())
        
        # Creativity achievements
        achievements.update(self._create_creativity_achievements())
        
        # Speed achievements
        achievements.update(self._create_speed_achievements())
        
        # Accuracy achievements
        achievements.update(self._create_accuracy_achievements())
        
        # Streak achievements
        achievements.update(self._create_streak_achievements())
        
        # Special achievements
        achievements.update(self._create_special_achievements())
        
        return achievements
    
    def _create_exploration_achievements(self) -> Dict[str, Achievement]:
        """Create exploration-based achievements"""
        return {
            'first_question': Achievement(
                id='first_question',
                name='Curious Mind',
                description='Ask your first question',
                category=AchievementCategory.EXPLORATION,
                rarity=AchievementRarity.COMMON,
                icon='🔍',
                points=10,
                requirements={'questions_asked': 1}
            ),
            'subject_explorer': Achievement(
                id='subject_explorer',
                name='Subject Explorer',
                description='Explore all four STEM subjects',
                category=AchievementCategory.EXPLORATION,
                rarity=AchievementRarity.UNCOMMON,
                icon='🗺️',
                points=50,
                requirements={'subjects_explored': ['science', 'technology', 'engineering', 'mathematics']}
            ),
            'deep_diver': Achievement(
                id='deep_diver',
                name='Deep Diver',
                description='Ask 10 follow-up questions in one topic',
                category=AchievementCategory.EXPLORATION,
                rarity=AchievementRarity.RARE,
                icon='🤿',
                points=100,
                requirements={'topic_depth': 10}
            ),
            'polymath': Achievement(
                id='polymath',
                name='Polymath',
                description='Master concepts across all STEM fields',
                category=AchievementCategory.EXPLORATION,
                rarity=AchievementRarity.LEGENDARY,
                icon='🎓',
                points=500,
                requirements={'cross_disciplinary_mastery': True}
            )
        }
    
    def _create_mastery_achievements(self) -> Dict[str, Achievement]:
        """Create mastery-based achievements"""
        return {
            'skill_novice': Achievement(
                id='skill_novice',
                name='Skill Novice',
                description='Reach beginner level in any skill',
                category=AchievementCategory.MASTERY,
                rarity=AchievementRarity.COMMON,
                icon='🌱',
                points=20,
                requirements={'skill_level': 0.2}
            ),
            'skill_intermediate': Achievement(
                id='skill_intermediate',
                name='Skill Intermediate',
                description='Reach intermediate level in any skill',
                category=AchievementCategory.MASTERY,
                rarity=AchievementRarity.UNCOMMON,
                icon='🌿',
                points=75,
                requirements={'skill_level': 0.4}
            ),
            'skill_expert': Achievement(
                id='skill_expert',
                name='Skill Expert',
                description='Reach expert level in any skill',
                category=AchievementCategory.MASTERY,
                rarity=AchievementRarity.EPIC,
                icon='🌳',
                points=200,
                requirements={'skill_level': 0.95}
            ),
            'perfect_score': Achievement(
                id='perfect_score',
                name='Perfect Score',
                description='Answer 10 questions correctly in a row',
                category=AchievementCategory.MASTERY,
                rarity=AchievementRarity.RARE,
                icon='💯',
                points=150,
                requirements={'correct_streak': 10}
            )
        }
    
    def _create_persistence_achievements(self) -> Dict[str, Achievement]:
        """Create persistence-based achievements"""
        return {
            'daily_learner': Achievement(
                id='daily_learner',
                name='Daily Learner',
                description='Learn every day for a week',
                category=AchievementCategory.PERSISTENCE,
                rarity=AchievementRarity.COMMON,
                icon='📅',
                points=30,
                requirements={'daily_streak': 7}
            ),
            'dedicated_student': Achievement(
                id='dedicated_student',
                name='Dedicated Student',
                description='Learn every day for a month',
                category=AchievementCategory.PERSISTENCE,
                rarity=AchievementRarity.RARE,
                icon='📆',
                points=200,
                requirements={'daily_streak': 30}
            ),
            'marathon_learner': Achievement(
                id='marathon_learner',
                name='Marathon Learner',
                description='Complete a 2-hour learning session',
                category=AchievementCategory.PERSISTENCE,
                rarity=AchievementRarity.UNCOMMON,
                icon='🏃',
                points=100,
                requirements={'session_duration': 7200}
            ),
            'never_give_up': Achievement(
                id='never_give_up',
                name='Never Give Up',
                description='Keep trying after 5 incorrect attempts',
                category=AchievementCategory.PERSISTENCE,
                rarity=AchievementRarity.UNCOMMON,
                icon='💪',
                points=75,
                requirements={'persistence_after_failure': 5}
            )
        }
    
    def _create_creativity_achievements(self) -> Dict[str, Achievement]:
        """Create creativity-based achievements"""
        return {
            'creative_thinker': Achievement(
                id='creative_thinker',
                name='Creative Thinker',
                description='Propose a unique solution to a problem',
                category=AchievementCategory.CREATIVITY,
                rarity=AchievementRarity.UNCOMMON,
                icon='💡',
                points=60,
                requirements={'unique_solutions': 1}
            ),
            'innovator': Achievement(
                id='innovator',
                name='Innovator',
                description='Design 5 original projects',
                category=AchievementCategory.CREATIVITY,
                rarity=AchievementRarity.RARE,
                icon='🚀',
                points=150,
                requirements={'original_projects': 5}
            ),
            'outside_the_box': Achievement(
                id='outside_the_box',
                name='Outside the Box',
                description='Find alternative approaches to 10 problems',
                category=AchievementCategory.CREATIVITY,
                rarity=AchievementRarity.EPIC,
                icon='📦',
                points=250,
                requirements={'alternative_approaches': 10}
            )
        }
    
    def _create_speed_achievements(self) -> Dict[str, Achievement]:
        """Create speed-based achievements"""
        return {
            'quick_thinker': Achievement(
                id='quick_thinker',
                name='Quick Thinker',
                description='Answer correctly within 30 seconds',
                category=AchievementCategory.SPEED,
                rarity=AchievementRarity.COMMON,
                icon='⚡',
                points=25,
                requirements={'response_time': 30, 'correct': True}
            ),
            'lightning_fast': Achievement(
                id='lightning_fast',
                name='Lightning Fast',
                description='Complete 10 problems in under 5 minutes',
                category=AchievementCategory.SPEED,
                rarity=AchievementRarity.RARE,
                icon='⚡⚡',
                points=125,
                requirements={'problems_in_time': {'count': 10, 'time': 300}}
            )
        }
    
    def _create_accuracy_achievements(self) -> Dict[str, Achievement]:
        """Create accuracy-based achievements"""
        return {
            'sharpshooter': Achievement(
                id='sharpshooter',
                name='Sharpshooter',
                description='Achieve 90% accuracy over 20 questions',
                category=AchievementCategory.ACCURACY,
                rarity=AchievementRarity.UNCOMMON,
                icon='🎯',
                points=80,
                requirements={'accuracy': 0.9, 'min_questions': 20}
            ),
            'precision_master': Achievement(
                id='precision_master',
                name='Precision Master',
                description='Achieve 95% accuracy over 50 questions',
                category=AchievementCategory.ACCURACY,
                rarity=AchievementRarity.EPIC,
                icon='🎯🎯',
                points=300,
                requirements={'accuracy': 0.95, 'min_questions': 50}
            )
        }
    
    def _create_streak_achievements(self) -> Dict[str, Achievement]:
        """Create streak-based achievements"""
        return {
            'hot_streak': Achievement(
                id='hot_streak',
                name='Hot Streak',
                description='Answer 5 questions correctly in a row',
                category=AchievementCategory.STREAK,
                rarity=AchievementRarity.COMMON,
                icon='🔥',
                points=40,
                requirements={'correct_streak': 5}
            ),
            'on_fire': Achievement(
                id='on_fire',
                name='On Fire',
                description='Answer 15 questions correctly in a row',
                category=AchievementCategory.STREAK,
                rarity=AchievementRarity.RARE,
                icon='🔥🔥',
                points=175,
                requirements={'correct_streak': 15}
            ),
            'unstoppable': Achievement(
                id='unstoppable',
                name='Unstoppable',
                description='Answer 25 questions correctly in a row',
                category=AchievementCategory.STREAK,
                rarity=AchievementRarity.LEGENDARY,
                icon='🔥🔥🔥',
                points=500,
                requirements={'correct_streak': 25}
            )
        }
    
    def _create_special_achievements(self) -> Dict[str, Achievement]:
        """Create special/seasonal achievements"""
        return {
            'early_bird': Achievement(
                id='early_bird',
                name='Early Bird',
                description='Start learning before 7 AM',
                category=AchievementCategory.SPECIAL,
                rarity=AchievementRarity.UNCOMMON,
                icon='🌅',
                points=50,
                requirements={'time_condition': 'before_7am'}
            ),
            'night_owl': Achievement(
                id='night_owl',
                name='Night Owl',
                description='Learn after 9 PM',
                category=AchievementCategory.SPECIAL,
                rarity=AchievementRarity.UNCOMMON,
                icon='🦉',
                points=50,
                requirements={'time_condition': 'after_9pm'}
            ),
            'weekend_warrior': Achievement(
                id='weekend_warrior',
                name='Weekend Warrior',
                description='Complete 20 problems on a weekend',
                category=AchievementCategory.SPECIAL,
                rarity=AchievementRarity.UNCOMMON,
                icon='⚔️',
                points=75,
                requirements={'weekend_problems': 20}
            ),
            'holiday_learner': Achievement(
                id='holiday_learner',
                name='Holiday Learner',
                description='Learn during a holiday',
                category=AchievementCategory.SPECIAL,
                rarity=AchievementRarity.RARE,
                icon='🎄',
                points=100,
                requirements={'holiday_learning': True},
                seasonal=True
            ),
            'pi_day': Achievement(
                id='pi_day',
                name='Pi Day Champion',
                description='Solve math problems on Pi Day (March 14)',
                category=AchievementCategory.SPECIAL,
                rarity=AchievementRarity.EPIC,
                icon='π',
                points=314,
                requirements={'date': '03-14', 'subject': 'mathematics'},
                seasonal=True
            ),
            'hidden_genius': Achievement(
                id='hidden_genius',
                name='Hidden Genius',
                description='???',
                category=AchievementCategory.SPECIAL,
                rarity=AchievementRarity.LEGENDARY,
                icon='🤫',
                points=1000,
                requirements={'secret_condition': True},
                hidden=True
            )
        }
    
    def process(self, context: Any) -> Tuple[Any, Dict[str, Any]]:
        """
        Process interaction for achievement checking
        Returns: (context, achievement_metadata)
        """
        try:
            # Load user achievements
            user_achievements = self._load_user_achievements(context.profile_id)
            
            # Check for new achievements
            new_achievements = self._check_achievements(context, user_achievements)
            
            # Update achievement progress
            progress_updates = self._update_progress(context, user_achievements)
            
            # Award badges and rewards
            new_badges = []
            new_rewards = []
            
            for achievement in new_achievements:
                # Award badge
                badge = self.badge_system.award_badge(context.profile_id, achievement)
                if badge:
                    new_badges.append(badge)
                
                # Award rewards
                rewards = self.reward_manager.award_rewards(context.profile_id, achievement)
                new_rewards.extend(rewards)
            
            # Update leaderboard
            self.leaderboard.update_score(
                context.profile_id,
                context.child_name,
                new_achievements
            )
            
            # Save updated achievements
            self._save_user_achievements(context.profile_id, user_achievements)
            
            # Add achievement notifications to response
            if new_achievements:
                notification = self._generate_achievement_notification(
                    new_achievements,
                    context
                )
                context.model_response = f"{notification}\n\n{context.model_response}"
            
            # Generate achievement metadata
            achievement_metadata = {
                'new_achievements': [a.id for a in new_achievements],
                'achievement_points': sum(a.points for a in new_achievements),
                'total_points': self._calculate_total_points(user_achievements),
                'new_badges': [b.id for b in new_badges],
                'new_rewards': [r.id for r in new_rewards],
                'progress_updates': progress_updates,
                'leaderboard_rank': self.leaderboard.get_rank(context.profile_id),
                'next_achievement_hint': self._get_next_achievement_hint(user_achievements)
            }
            
            return context, achievement_metadata
            
        except Exception as e:
            logger.error(f"Achievement system error: {e}")
            return context, {'error': str(e)}
    
    def _load_user_achievements(self, profile_id: str) -> Dict[str, Achievement]:
        """Load user's achievement data"""
        achievements_file = self.achievements_path / f"{profile_id}_achievements.json"
        
        try:
            if achievements_file.exists():
                with open(achievements_file, 'r') as f:
                    saved_data = json.load(f)
                
                # Reconstruct achievements with current definitions
                user_achievements = {}
                
                for achievement_id, achievement_data in saved_data.items():
                    if achievement_id in self.achievement_db:
                        achievement = self.achievement_db[achievement_id]
                        # Update with saved progress
                        achievement.unlocked = achievement_data.get('unlocked', False)
                        achievement.unlock_date = achievement_data.get('unlock_date')
                        achievement.progress = achievement_data.get('progress', 0.0)
                        achievement.metadata = achievement_data.get('metadata', {})
                        user_achievements[achievement_id] = achievement
                
                # Add new achievements not yet tracked
                for achievement_id, achievement in self.achievement_db.items():
                    if achievement_id not in user_achievements:
                        user_achievements[achievement_id] = achievement
                
                return user_achievements
            else:
                # Return fresh copy of all achievements
                return dict(self.achievement_db)
                
        except Exception as e:
            logger.error(f"Failed to load achievements: {e}")
            return dict(self.achievement_db)
    
    def _check_achievements(self, context: Any, user_achievements: Dict[str, Achievement]) -> List[Achievement]:
        """Check for newly unlocked achievements"""
        new_achievements = []
        
        for achievement_id, achievement in user_achievements.items():
            if not achievement.unlocked:
                if self._check_requirements(achievement, context):
                    # Achievement unlocked!
                    achievement.unlocked = True
                    achievement.unlock_date = datetime.utcnow().isoformat()
                    achievement.progress = 1.0
                    new_achievements.append(achievement)
                    
                    # Log achievement
                    logger.info(f"Achievement unlocked: {achievement.name} for {context.child_name}")
        
        return new_achievements
    
    def _check_requirements(self, achievement: Achievement, context: Any) -> bool:
        """Check if achievement requirements are met"""
        requirements = achievement.requirements
        
        # Check based on achievement category
        if achievement.category == AchievementCategory.EXPLORATION:
            return self._check_exploration_requirements(requirements, context)
        elif achievement.category == AchievementCategory.MASTERY:
            return self._check_mastery_requirements(requirements, context)
        elif achievement.category == AchievementCategory.PERSISTENCE:
            return self._check_persistence_requirements(requirements, context)
        elif achievement.category == AchievementCategory.CREATIVITY:
            return self._check_creativity_requirements(requirements, context)
        elif achievement.category == AchievementCategory.SPEED:
            return self._check_speed_requirements(requirements, context)
        elif achievement.category == AchievementCategory.ACCURACY:
            return self._check_accuracy_requirements(requirements, context)
        elif achievement.category == AchievementCategory.STREAK:
            return self._check_streak_requirements(requirements, context)
        elif achievement.category == AchievementCategory.SPECIAL:
            return self._check_special_requirements(requirements, context)
        
        return False
    
    def _check_exploration_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check exploration achievement requirements"""
        if 'questions_asked' in requirements:
            # Check total questions asked
            stats = self._load_user_stats(context.profile_id)
            return stats.get('total_questions', 0) >= requirements['questions_asked']
        
        if 'subjects_explored' in requirements:
            # Check if all required subjects have been explored
            stats = self._load_user_stats(context.profile_id)
            explored = stats.get('subjects_explored', [])
            required = requirements['subjects_explored']
            return all(subject in explored for subject in required)
        
        if 'topic_depth' in requirements:
            # Check follow-up questions in single topic
            return context.metadata.get('topic_depth', 0) >= requirements['topic_depth']
        
        return False
    
    def _check_mastery_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check mastery achievement requirements"""
        if 'skill_level' in requirements:
            # Check if any skill reached required level
            skills_file = self.usb_path / 'progress' / f"{context.profile_id}_skills.json"
            
            try:
                if skills_file.exists():
                    with open(skills_file, 'r') as f:
                        skills = json.load(f)
                    
                    for skill_data in skills.values():
                        if skill_data.get('level', 0) >= requirements['skill_level']:
                            return True
            except Exception:
                pass
        
        if 'correct_streak' in requirements:
            # Check consecutive correct answers
            return context.metadata.get('correct_streak', 0) >= requirements['correct_streak']
        
        return False
    
    def _check_persistence_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check persistence achievement requirements"""
        if 'daily_streak' in requirements:
            # Check learning streak
            streak = self._calculate_daily_streak(context.profile_id)
            return streak >= requirements['daily_streak']
        
        if 'session_duration' in requirements:
            # Check session length
            return context.metadata.get('session_duration', 0) >= requirements['session_duration']
        
        if 'persistence_after_failure' in requirements:
            # Check persistence after incorrect attempts
            return context.metadata.get('attempts_after_failure', 0) >= requirements['persistence_after_failure']
        
        return False
    
    def _check_creativity_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check creativity achievement requirements"""
        # Simplified checks - in production would analyze response creativity
        if 'unique_solutions' in requirements:
            return context.metadata.get('unique_solution', False)
        
        if 'original_projects' in requirements:
            stats = self._load_user_stats(context.profile_id)
            return stats.get('original_projects', 0) >= requirements['original_projects']
        
        return False
    
    def _check_speed_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check speed achievement requirements"""
        if 'response_time' in requirements:
            response_time = context.metadata.get('response_time', float('inf'))
            correct = context.metadata.get('correct', False)
            
            return response_time <= requirements['response_time'] * 1000 and correct
        
        return False
    
    def _check_accuracy_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check accuracy achievement requirements"""
        if 'accuracy' in requirements:
            stats = self._load_user_stats(context.profile_id)
            total = stats.get('total_questions', 0)
            correct = stats.get('correct_answers', 0)
            
            if total >= requirements.get('min_questions', 1):
                accuracy = correct / total if total > 0 else 0
                return accuracy >= requirements['accuracy']
        
        return False
    
    def _check_streak_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check streak achievement requirements"""
        if 'correct_streak' in requirements:
            return context.metadata.get('correct_streak', 0) >= requirements['correct_streak']
        
        return False
    
    def _check_special_requirements(self, requirements: Dict, context: Any) -> bool:
        """Check special achievement requirements"""
        current_time = datetime.now()
        
        if 'time_condition' in requirements:
            condition = requirements['time_condition']
            
            if condition == 'before_7am':
                return current_time.hour < 7
            elif condition == 'after_9pm':
                return current_time.hour >= 21
        
        if 'weekend_problems' in requirements:
            if current_time.weekday() >= 5:  # Saturday or Sunday
                stats = self._load_daily_stats(context.profile_id)
                return stats.get('problems_today', 0) >= requirements['weekend_problems']
        
        if 'date' in requirements:
            # Check for specific date (like Pi Day)
            date_str = current_time.strftime('%m-%d')
            if date_str == requirements['date']:
                if 'subject' in requirements:
                    return context.metadata.get('subject_area') == requirements['subject']
                return True
        
        if 'secret_condition' in requirements:
            # Hidden achievement - special condition
            # Example: Answer "42" to a specific type of question
            return context.input_text == "42" and "meaning of life" in context.input_text.lower()
        
        return False
    
    def _update_progress(self, context: Any, user_achievements: Dict[str, Achievement]) -> Dict[str, float]:
        """Update progress toward unearned achievements"""
        progress_updates = {}
        
        for achievement_id, achievement in user_achievements.items():
            if not achievement.unlocked:
                old_progress = achievement.progress
                new_progress = self._calculate_progress(achievement, context)
                
                if new_progress > old_progress:
                    achievement.progress = new_progress
                    progress_updates[achievement_id] = new_progress
        
        return progress_updates
    
    def _calculate_progress(self, achievement: Achievement, context: Any) -> float:
        """Calculate progress toward achievement (0.0 to 1.0)"""
        requirements = achievement.requirements
        
        # Calculate based on requirement type
        if 'questions_asked' in requirements:
            stats = self._load_user_stats(context.profile_id)
            current = stats.get('total_questions', 0)
            required = requirements['questions_asked']
            return min(1.0, current / required)
        
        if 'daily_streak' in requirements:
            current = self._calculate_daily_streak(context.profile_id)
            required = requirements['daily_streak']
            return min(1.0, current / required)
        
        if 'correct_streak' in requirements:
            current = context.metadata.get('correct_streak', 0)
            required = requirements['correct_streak']
            return min(1.0, current / required)
        
        # Default to current progress
        return achievement.progress
    
    def _save_user_achievements(self, profile_id: str, user_achievements: Dict[str, Achievement]) -> None:
        """Save user achievement data"""
        achievements_file = self.achievements_path / f"{profile_id}_achievements.json"
        
        try:
            # Convert to serializable format
            save_data = {}
            
            for achievement_id, achievement in user_achievements.items():
                save_data[achievement_id] = {
                    'unlocked': achievement.unlocked,
                    'unlock_date': achievement.unlock_date,
                    'progress': achievement.progress,
                    'metadata': achievement.metadata
                }
            
            with open(achievements_file, 'w') as f:
                json.dump(save_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save achievements: {e}")
    
    def _generate_achievement_notification(self, achievements: List[Achievement], context: Any) -> str:
        """Generate notification message for unlocked achievements"""
        if len(achievements) == 1:
            achievement = achievements[0]
            
            # Age-appropriate celebration
            age = context.child_age
            
            if age < 8:
                messages = [
                    f"🎉 WOW! You unlocked '{achievement.name}'! {achievement.icon}",
                    f"⭐ Amazing! New achievement: {achievement.name}! ⭐",
                    f"🌟 Super job! You earned '{achievement.name}'! 🌟"
                ]
            elif age < 12:
                messages = [
                    f"🏆 Achievement Unlocked: {achievement.name} - {achievement.description}",
                    f"💫 Excellent! You've earned the '{achievement.name}' achievement!",
                    f"🎯 Great work! '{achievement.name}' is yours!"
                ]
            else:
                messages = [
                    f"Achievement: {achievement.name} [{achievement.rarity.value.upper()}]",
                    f"[{achievement.icon}] {achievement.name} - {achievement.points} points",
                    f"Unlocked: {achievement.name} | {achievement.description}"
                ]
            
            return random.choice(messages)
        else:
            # Multiple achievements
            names = [a.name for a in achievements[:3]]
            total_points = sum(a.points for a in achievements)
            
            if len(achievements) > 3:
                return f"🎊 Amazing! You unlocked {len(achievements)} achievements including {', '.join(names)} and more! (+{total_points} points)"
            else:
                return f"🎊 Incredible! You unlocked {', '.join(names)}! (+{total_points} points)"
    
    def _calculate_total_points(self, user_achievements: Dict[str, Achievement]) -> int:
        """Calculate total achievement points"""
        return sum(a.points for a in user_achievements.values() if a.unlocked)
    
    def _get_next_achievement_hint(self, user_achievements: Dict[str, Achievement]) -> Optional[str]:
        """Get hint for next closest achievement"""
        closest_achievement = None
        highest_progress = 0.0
        
        for achievement in user_achievements.values():
            if not achievement.unlocked and not achievement.hidden:
                if achievement.progress > highest_progress:
                    highest_progress = achievement.progress
                    closest_achievement = achievement
        
        if closest_achievement and highest_progress > 0.5:
            return f"You're {int(highest_progress * 100)}% toward '{closest_achievement.name}'!"
        
        return None
    
    def _load_user_stats(self, profile_id: str) -> Dict[str, Any]:
        """Load user statistics for achievement checking"""
        stats_file = self.usb_path / 'analytics' / f"{profile_id}_stats.json"
        
        try:
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return {}
    
    def _load_daily_stats(self, profile_id: str) -> Dict[str, Any]:
        """Load today's statistics"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        daily_file = self.usb_path / 'analytics' / f"{profile_id}_{date_str}.json"
        
        try:
            if daily_file.exists():
                with open(daily_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        return {}
    
    def _calculate_daily_streak(self, profile_id: str) -> int:
        """Calculate consecutive days of learning"""
        streak = 0
        current_date = datetime.now().date()
        
        for i in range(365):  # Check up to a year
            check_date = current_date - timedelta(days=i)
            daily_file = self.usb_path / 'conversations' / profile_id / f"{check_date.strftime('%Y-%m-%d')}.json"
            
            if daily_file.exists():
                streak += 1
            else:
                break
        
        return streak

class BadgeSystem:
    """Visual badge management system"""
    
    def __init__(self, achievements_path: Path):
        """Initialize badge system"""
        self.achievements_path = achievements_path
        self.badges_path = achievements_path / 'badges'
        self.badges_path.mkdir(parents=True, exist_ok=True)
    
    def award_badge(self, profile_id: str, achievement: Achievement) -> Optional[Badge]:
        """Award badge for achievement"""
        badge = Badge(
            id=f"badge_{achievement.id}",
            name=f"{achievement.name} Badge",
            image_id=self._generate_badge_image(achievement),
            color=self._get_rarity_color(achievement.rarity),
            sparkle_effect=achievement.rarity in [AchievementRarity.EPIC, AchievementRarity.LEGENDARY],
            achievement_id=achievement.id,
            display_priority=self._get_display_priority(achievement.rarity)
        )
        
        # Save badge
        self._save_badge(profile_id, badge)
        
        return badge
    
    def _generate_badge_image(self, achievement: Achievement) -> str:
        """Generate badge image identifier"""
        # In production, this would generate actual image
        return f"{achievement.icon}_{achievement.rarity.value}"
    
    def _get_rarity_color(self, rarity: AchievementRarity) -> str:
        """Get color based on rarity"""
        colors = {
            AchievementRarity.COMMON: "#808080",      # Gray
            AchievementRarity.UNCOMMON: "#00FF00",    # Green
            AchievementRarity.RARE: "#0080FF",        # Blue
            AchievementRarity.EPIC: "#B000B0",        # Purple
            AchievementRarity.LEGENDARY: "#FFD700"     # Gold
        }
        
        return colors.get(rarity, "#808080")
    
    def _get_display_priority(self, rarity: AchievementRarity) -> int:
        """Get display priority based on rarity"""
        priorities = {
            AchievementRarity.LEGENDARY: 1,
            AchievementRarity.EPIC: 2,
            AchievementRarity.RARE: 3,
            AchievementRarity.UNCOMMON: 4,
            AchievementRarity.COMMON: 5
        }
        
        return priorities.get(rarity, 5)
    
    def _save_badge(self, profile_id: str, badge: Badge) -> None:
        """Save badge to user's collection"""
        badges_file = self.badges_path / f"{profile_id}_badges.json"
        
        try:
            if badges_file.exists():
                with open(badges_file, 'r') as f:
                    badges = json.load(f)
            else:
                badges = []
            
            badges.append(asdict(badge))
            
            with open(badges_file, 'w') as f:
                json.dump(badges, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save badge: {e}")

class RewardManager:
    """Manage rewards for achievements"""
    
    def __init__(self, achievements_path: Path):
        """Initialize reward manager"""
        self.achievements_path = achievements_path
        self.rewards_path = achievements_path / 'rewards'
        self.rewards_path.mkdir(parents=True, exist_ok=True)
    
    def award_rewards(self, profile_id: str, achievement: Achievement) -> List[Reward]:
        """Award rewards for achievement"""
        rewards = []
        
        # Title rewards for major achievements
        if achievement.rarity in [AchievementRarity.EPIC, AchievementRarity.LEGENDARY]:
            title = Reward(
                id=f"title_{achievement.id}",
                name=achievement.name,
                description=f"Title earned from {achievement.name}",
                type='title',
                value=achievement.name,
                achievement_id=achievement.id
            )
            rewards.append(title)
        
        # Feature unlocks for certain achievements
        if achievement.category == AchievementCategory.MASTERY:
            feature = Reward(
                id=f"feature_{achievement.id}",
                name="Advanced Problems",
                description="Unlock advanced problem sets",
                type='feature_unlock',
                value='advanced_problems',
                achievement_id=achievement.id
            )
            rewards.append(feature)
        
        # Save rewards
        self._save_rewards(profile_id, rewards)
        
        return rewards
    
    def _save_rewards(self, profile_id: str, rewards: List[Reward]) -> None:
        """Save rewards to user's collection"""
        rewards_file = self.rewards_path / f"{profile_id}_rewards.json"
        
        try:
            if rewards_file.exists():
                with open(rewards_file, 'r') as f:
                    all_rewards = json.load(f)
            else:
                all_rewards = []
            
            for reward in rewards:
                all_rewards.append(asdict(reward))
            
            with open(rewards_file, 'w') as f:
                json.dump(all_rewards, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save rewards: {e}")

class LeaderboardManager:
    """Manage achievement leaderboards"""
    
    def __init__(self, achievements_path: Path):
        """Initialize leaderboard manager"""
        self.achievements_path = achievements_path
        self.leaderboard_file = achievements_path / 'leaderboard.json'
    
    def update_score(self, profile_id: str, name: str, achievements: List[Achievement]) -> None:
        """Update user's leaderboard score"""
        try:
            # Load leaderboard
            if self.leaderboard_file.exists():
                with open(self.leaderboard_file, 'r') as f:
                    leaderboard = json.load(f)
            else:
                leaderboard = {}
            
            # Update score
            if profile_id not in leaderboard:
                leaderboard[profile_id] = {
                    'name': name,
                    'total_points': 0,
                    'achievement_count': 0,
                    'last_update': None
                }
            
            # Add new points
            new_points = sum(a.points for a in achievements)
            leaderboard[profile_id]['total_points'] += new_points
            leaderboard[profile_id]['achievement_count'] += len(achievements)
            leaderboard[profile_id]['last_update'] = datetime.utcnow().isoformat()
            
            # Save leaderboard
            with open(self.leaderboard_file, 'w') as f:
                json.dump(leaderboard, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to update leaderboard: {e}")
    
    def get_rank(self, profile_id: str) -> Optional[int]:
        """Get user's leaderboard rank"""
        try:
            if not self.leaderboard_file.exists():
                return None
            
            with open(self.leaderboard_file, 'r') as f:
                leaderboard = json.load(f)
            
            if profile_id not in leaderboard:
                return None
            
            # Sort by points
            sorted_users = sorted(
                leaderboard.items(),
                key=lambda x: x[1]['total_points'],
                reverse=True
            )
            
            # Find rank
            for rank, (user_id, _) in enumerate(sorted_users, 1):
                if user_id == profile_id:
                    return rank
            
            return None
            
        except Exception:
            return None

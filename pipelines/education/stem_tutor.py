"""
Sunflower AI Professional System - STEM Tutor Pipeline
Comprehensive K-12 STEM education orchestration
Version: 6.2 | Full STEM Curriculum Support
"""

import json
import logging
import random
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class STEMSubject(Enum):
    """STEM subject categories"""
    SCIENCE = "science"
    TECHNOLOGY = "technology"
    ENGINEERING = "engineering"
    MATHEMATICS = "mathematics"
    INTERDISCIPLINARY = "interdisciplinary"

@dataclass
class LearningObjective:
    """Educational learning objective"""
    id: str
    subject: STEMSubject
    grade_level: str
    topic: str
    description: str
    skills: List[str]
    prerequisites: List[str]
    assessment_criteria: List[str]

class STEMTutorPipeline:
    """
    Production-grade STEM education pipeline
    Provides comprehensive tutoring across all STEM subjects
    """
    
    def __init__(self, usb_path: Path):
        """Initialize STEM tutor with curriculum database"""
        self.usb_path = Path(usb_path)
        self.curriculum_path = self.usb_path / 'curriculum'
        self.curriculum_path.mkdir(parents=True, exist_ok=True)
        
        # Load curriculum components
        self.curriculum = self._load_curriculum()
        self.learning_paths = self._load_learning_paths()
        self.concept_map = self._build_concept_map()
        
        # Initialize teaching strategies
        self.teaching_strategies = TeachingStrategies()
        self.assessment_engine = AssessmentEngine(self.usb_path)
        
        # Cache for optimized responses
        self.response_cache = {}
        
        logger.info("STEM tutor pipeline initialized with full curriculum")
    
    def _load_curriculum(self) -> Dict[str, Dict[str, List[LearningObjective]]]:
        """Load comprehensive K-12 STEM curriculum"""
        curriculum = {
            'K-2': {
                'science': [
                    LearningObjective(
                        id='sci_k2_01',
                        subject=STEMSubject.SCIENCE,
                        grade_level='K-2',
                        topic='Living Things',
                        description='Understand basic characteristics of living things',
                        skills=['observation', 'classification', 'comparison'],
                        prerequisites=[],
                        assessment_criteria=['identify_living_vs_nonliving', 'name_animal_parts']
                    ),
                    LearningObjective(
                        id='sci_k2_02',
                        subject=STEMSubject.SCIENCE,
                        grade_level='K-2',
                        topic='Weather and Seasons',
                        description='Observe and describe weather patterns',
                        skills=['observation', 'pattern_recognition', 'data_collection'],
                        prerequisites=[],
                        assessment_criteria=['identify_weather_types', 'seasonal_changes']
                    )
                ],
                'technology': [
                    LearningObjective(
                        id='tech_k2_01',
                        subject=STEMSubject.TECHNOLOGY,
                        grade_level='K-2',
                        topic='Basic Computer Skills',
                        description='Use computers and digital devices safely',
                        skills=['device_operation', 'digital_safety', 'basic_navigation'],
                        prerequisites=[],
                        assessment_criteria=['mouse_keyboard_use', 'safety_rules']
                    )
                ],
                'engineering': [
                    LearningObjective(
                        id='eng_k2_01',
                        subject=STEMSubject.ENGINEERING,
                        grade_level='K-2',
                        topic='Building and Design',
                        description='Create simple structures and solve problems',
                        skills=['problem_solving', 'creativity', 'spatial_reasoning'],
                        prerequisites=[],
                        assessment_criteria=['build_stable_structure', 'identify_problem']
                    )
                ],
                'mathematics': [
                    LearningObjective(
                        id='math_k2_01',
                        subject=STEMSubject.MATHEMATICS,
                        grade_level='K-2',
                        topic='Numbers and Counting',
                        description='Count, compare, and work with numbers to 100',
                        skills=['counting', 'number_recognition', 'basic_operations'],
                        prerequisites=[],
                        assessment_criteria=['count_to_100', 'simple_addition']
                    )
                ]
            },
            '3-5': {
                'science': [
                    LearningObjective(
                        id='sci_35_01',
                        subject=STEMSubject.SCIENCE,
                        grade_level='3-5',
                        topic='Matter and Energy',
                        description='Understand states of matter and energy transfer',
                        skills=['experimentation', 'measurement', 'hypothesis_formation'],
                        prerequisites=['sci_k2_01'],
                        assessment_criteria=['identify_states_matter', 'energy_examples']
                    ),
                    LearningObjective(
                        id='sci_35_02',
                        subject=STEMSubject.SCIENCE,
                        grade_level='3-5',
                        topic='Solar System',
                        description='Explore planets, moons, and space phenomena',
                        skills=['scale_understanding', 'research', 'model_creation'],
                        prerequisites=[],
                        assessment_criteria=['name_planets', 'explain_orbits']
                    )
                ],
                'technology': [
                    LearningObjective(
                        id='tech_35_01',
                        subject=STEMSubject.TECHNOLOGY,
                        grade_level='3-5',
                        topic='Introduction to Coding',
                        description='Learn basic programming concepts',
                        skills=['logical_thinking', 'sequencing', 'debugging'],
                        prerequisites=['tech_k2_01'],
                        assessment_criteria=['create_simple_program', 'fix_code_errors']
                    )
                ],
                'engineering': [
                    LearningObjective(
                        id='eng_35_01',
                        subject=STEMSubject.ENGINEERING,
                        grade_level='3-5',
                        topic='Simple Machines',
                        description='Understand and apply principles of simple machines',
                        skills=['mechanical_reasoning', 'design_thinking', 'testing'],
                        prerequisites=['eng_k2_01'],
                        assessment_criteria=['identify_machine_types', 'build_lever']
                    )
                ],
                'mathematics': [
                    LearningObjective(
                        id='math_35_01',
                        subject=STEMSubject.MATHEMATICS,
                        grade_level='3-5',
                        topic='Multiplication and Division',
                        description='Master multiplication and division operations',
                        skills=['computation', 'problem_solving', 'pattern_recognition'],
                        prerequisites=['math_k2_01'],
                        assessment_criteria=['times_tables', 'word_problems']
                    )
                ]
            },
            '6-8': {
                'science': [
                    LearningObjective(
                        id='sci_68_01',
                        subject=STEMSubject.SCIENCE,
                        grade_level='6-8',
                        topic='Chemical Reactions',
                        description='Understand chemical reactions and equations',
                        skills=['equation_balancing', 'lab_techniques', 'safety_protocols'],
                        prerequisites=['sci_35_01'],
                        assessment_criteria=['balance_equations', 'predict_products']
                    )
                ],
                'technology': [
                    LearningObjective(
                        id='tech_68_01',
                        subject=STEMSubject.TECHNOLOGY,
                        grade_level='6-8',
                        topic='Web Development',
                        description='Create basic websites with HTML/CSS',
                        skills=['markup_languages', 'design_principles', 'responsive_design'],
                        prerequisites=['tech_35_01'],
                        assessment_criteria=['create_webpage', 'style_elements']
                    )
                ],
                'engineering': [
                    LearningObjective(
                        id='eng_68_01',
                        subject=STEMSubject.ENGINEERING,
                        grade_level='6-8',
                        topic='Robotics',
                        description='Design and program simple robots',
                        skills=['systems_thinking', 'programming', 'sensor_integration'],
                        prerequisites=['eng_35_01', 'tech_35_01'],
                        assessment_criteria=['program_robot', 'sensor_usage']
                    )
                ],
                'mathematics': [
                    LearningObjective(
                        id='math_68_01',
                        subject=STEMSubject.MATHEMATICS,
                        grade_level='6-8',
                        topic='Algebra Fundamentals',
                        description='Solve algebraic equations and inequalities',
                        skills=['abstract_thinking', 'equation_solving', 'graphing'],
                        prerequisites=['math_35_01'],
                        assessment_criteria=['solve_equations', 'graph_functions']
                    )
                ]
            },
            '9-12': {
                'science': [
                    LearningObjective(
                        id='sci_912_01',
                        subject=STEMSubject.SCIENCE,
                        grade_level='9-12',
                        topic='Physics Mechanics',
                        description='Apply Newton\'s laws and kinematics',
                        skills=['mathematical_modeling', 'experimental_design', 'data_analysis'],
                        prerequisites=['sci_68_01', 'math_68_01'],
                        assessment_criteria=['solve_physics_problems', 'design_experiment']
                    )
                ],
                'technology': [
                    LearningObjective(
                        id='tech_912_01',
                        subject=STEMSubject.TECHNOLOGY,
                        grade_level='9-12',
                        topic='Data Structures & Algorithms',
                        description='Implement complex data structures and algorithms',
                        skills=['algorithm_design', 'complexity_analysis', 'optimization'],
                        prerequisites=['tech_68_01'],
                        assessment_criteria=['implement_algorithms', 'analyze_complexity']
                    )
                ],
                'engineering': [
                    LearningObjective(
                        id='eng_912_01',
                        subject=STEMSubject.ENGINEERING,
                        grade_level='9-12',
                        topic='CAD and 3D Design',
                        description='Create professional engineering designs',
                        skills=['cad_software', 'technical_drawing', 'prototyping'],
                        prerequisites=['eng_68_01'],
                        assessment_criteria=['create_3d_model', 'technical_specs']
                    )
                ],
                'mathematics': [
                    LearningObjective(
                        id='math_912_01',
                        subject=STEMSubject.MATHEMATICS,
                        grade_level='9-12',
                        topic='Calculus',
                        description='Master derivatives and integrals',
                        skills=['limit_concepts', 'differentiation', 'integration'],
                        prerequisites=['math_68_01'],
                        assessment_criteria=['compute_derivatives', 'solve_integrals']
                    )
                ]
            }
        }
        
        return curriculum
    
    def _load_learning_paths(self) -> Dict[str, List[str]]:
        """Load structured learning paths through curriculum"""
        paths = {
            'science_fundamentals': [
                'sci_k2_01', 'sci_k2_02', 'sci_35_01', 'sci_35_02',
                'sci_68_01', 'sci_912_01'
            ],
            'coding_journey': [
                'tech_k2_01', 'tech_35_01', 'tech_68_01', 'tech_912_01'
            ],
            'engineering_design': [
                'eng_k2_01', 'eng_35_01', 'eng_68_01', 'eng_912_01'
            ],
            'mathematics_mastery': [
                'math_k2_01', 'math_35_01', 'math_68_01', 'math_912_01'
            ]
        }
        
        return paths
    
    def _build_concept_map(self) -> Dict[str, List[str]]:
        """Build concept relationship map for intelligent tutoring"""
        concept_map = {
            # Science connections
            'atoms': ['molecules', 'elements', 'periodic_table', 'chemistry'],
            'energy': ['kinetic', 'potential', 'conservation', 'work', 'power'],
            'cells': ['biology', 'organisms', 'DNA', 'mitosis', 'photosynthesis'],
            'forces': ['Newton', 'motion', 'acceleration', 'gravity', 'friction'],
            
            # Technology connections
            'algorithms': ['programming', 'efficiency', 'sorting', 'searching'],
            'variables': ['data_types', 'assignment', 'scope', 'memory'],
            'networks': ['internet', 'protocols', 'security', 'communication'],
            
            # Engineering connections
            'design': ['prototype', 'testing', 'iteration', 'requirements'],
            'materials': ['properties', 'strength', 'durability', 'selection'],
            'systems': ['components', 'integration', 'feedback', 'control'],
            
            # Mathematics connections
            'algebra': ['equations', 'variables', 'functions', 'graphing'],
            'geometry': ['shapes', 'angles', 'proofs', 'transformations'],
            'statistics': ['probability', 'distribution', 'mean', 'variance']
        }
        
        return concept_map
    
    def process(self, context: Any) -> Tuple[Any, Dict[str, Any]]:
        """
        Process interaction through STEM tutoring pipeline
        Returns: (context, education_metadata)
        """
        try:
            # Identify educational intent
            intent = self._identify_learning_intent(context)
            
            # Match to curriculum objectives
            objectives = self._match_learning_objectives(context, intent)
            
            # Generate educational enhancement
            enhanced_response = self._enhance_with_education(
                context,
                intent,
                objectives
            )
            
            # Add interactive elements
            enhanced_response = self._add_interactive_elements(
                enhanced_response,
                context,
                objectives
            )
            
            # Track learning progress
            self._track_learning_progress(context, objectives)
            
            # Update context
            context.model_response = enhanced_response
            
            # Generate education metadata
            education_metadata = {
                'learning_intent': intent,
                'matched_objectives': [obj.id for obj in objectives],
                'concepts_covered': self._extract_concepts(enhanced_response),
                'difficulty_level': self._assess_difficulty(context, objectives),
                'follow_up_topics': self._suggest_follow_ups(objectives),
                'interactive_elements_added': True
            }
            
            return context, education_metadata
            
        except Exception as e:
            logger.error(f"STEM tutor error: {e}")
            return context, {'error': str(e)}
    
    def _identify_learning_intent(self, context: Any) -> Dict[str, Any]:
        """Identify the educational intent of the interaction"""
        text_lower = context.input_text.lower()
        
        # Question type detection
        question_types = {
            'how': 'explanation',
            'what': 'definition',
            'why': 'reasoning',
            'when': 'temporal',
            'where': 'spatial',
            'can': 'possibility',
            'solve': 'problem_solving',
            'calculate': 'computation',
            'explain': 'explanation',
            'help': 'assistance'
        }
        
        intent_type = 'general'
        for keyword, q_type in question_types.items():
            if keyword in text_lower:
                intent_type = q_type
                break
        
        # Subject detection
        subject = self._detect_subject(text_lower)
        
        # Complexity level
        complexity = self._assess_query_complexity(context)
        
        return {
            'type': intent_type,
            'subject': subject,
            'complexity': complexity,
            'keywords': self._extract_keywords(text_lower)
        }
    
    def _detect_subject(self, text: str) -> STEMSubject:
        """Detect the primary STEM subject"""
        subject_keywords = {
            STEMSubject.SCIENCE: [
                'science', 'biology', 'chemistry', 'physics', 'atom', 'cell',
                'energy', 'force', 'experiment', 'hypothesis', 'species'
            ],
            STEMSubject.TECHNOLOGY: [
                'computer', 'code', 'program', 'software', 'app', 'website',
                'algorithm', 'data', 'network', 'internet', 'digital'
            ],
            STEMSubject.ENGINEERING: [
                'build', 'design', 'engineer', 'machine', 'robot', 'structure',
                'prototype', 'test', 'material', 'system', 'circuit'
            ],
            STEMSubject.MATHEMATICS: [
                'math', 'number', 'equation', 'calculate', 'algebra', 'geometry',
                'add', 'subtract', 'multiply', 'divide', 'graph', 'function'
            ]
        }
        
        subject_scores = {}
        for subject, keywords in subject_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            subject_scores[subject] = score
        
        # Return subject with highest score
        if max(subject_scores.values()) > 0:
            return max(subject_scores, key=subject_scores.get)
        
        return STEMSubject.INTERDISCIPLINARY
    
    def _match_learning_objectives(self, context: Any, intent: Dict) -> List[LearningObjective]:
        """Match interaction to relevant learning objectives"""
        matched_objectives = []
        
        # Get grade-appropriate objectives
        grade_key = self._get_grade_key(context.child_age)
        
        if grade_key in self.curriculum:
            subject_key = intent['subject'].value
            
            # Get objectives for detected subject
            if subject_key in self.curriculum[grade_key]:
                objectives = self.curriculum[grade_key][subject_key]
                
                # Filter by relevance
                for objective in objectives:
                    relevance_score = self._calculate_relevance(
                        objective,
                        intent['keywords']
                    )
                    
                    if relevance_score > 0.3:
                        matched_objectives.append(objective)
        
        # If no exact matches, find related objectives
        if not matched_objectives:
            matched_objectives = self._find_related_objectives(intent, grade_key)
        
        return matched_objectives[:3]  # Return top 3 most relevant
    
    def _get_grade_key(self, age: int) -> str:
        """Get curriculum grade key from age"""
        if age <= 7:
            return 'K-2'
        elif age <= 10:
            return '3-5'
        elif age <= 13:
            return '6-8'
        else:
            return '9-12'
    
    def _calculate_relevance(self, objective: LearningObjective, keywords: List[str]) -> float:
        """Calculate relevance score between objective and keywords"""
        objective_text = f"{objective.topic} {objective.description}".lower()
        
        matches = sum(1 for keyword in keywords if keyword in objective_text)
        
        if len(keywords) > 0:
            return matches / len(keywords)
        
        return 0.0
    
    def _find_related_objectives(self, intent: Dict, grade_key: str) -> List[LearningObjective]:
        """Find related objectives using concept map"""
        related = []
        
        # Use concept map to find related topics
        for keyword in intent['keywords']:
            if keyword in self.concept_map:
                related_concepts = self.concept_map[keyword]
                
                # Search objectives for related concepts
                if grade_key in self.curriculum:
                    for subject_objectives in self.curriculum[grade_key].values():
                        for objective in subject_objectives:
                            if any(concept in objective.topic.lower() 
                                  for concept in related_concepts):
                                related.append(objective)
        
        return related
    
    def _enhance_with_education(self, context: Any, intent: Dict, 
                               objectives: List[LearningObjective]) -> str:
        """Enhance response with educational content"""
        base_response = context.model_response or ""
        
        # Add educational structure based on intent type
        if intent['type'] == 'explanation':
            enhanced = self._structure_explanation(base_response, objectives)
        elif intent['type'] == 'problem_solving':
            enhanced = self._structure_problem_solving(base_response, objectives)
        elif intent['type'] == 'definition':
            enhanced = self._structure_definition(base_response, objectives)
        else:
            enhanced = self._structure_general(base_response, objectives)
        
        # Add learning objectives context
        if objectives:
            objective_text = f"\n\n📚 Learning Goal: {objectives[0].description}"
            enhanced += objective_text
        
        return enhanced
    
    def _structure_explanation(self, response: str, objectives: List[LearningObjective]) -> str:
        """Structure response as educational explanation"""
        structured = "Let me explain this step by step:\n\n"
        
        # Add numbered steps if not present
        if '1.' not in response:
            parts = response.split('. ')
            for i, part in enumerate(parts[:5], 1):  # Limit to 5 steps
                if part.strip():
                    structured += f"{i}. {part.strip()}\n"
        else:
            structured += response
        
        # Add summary
        structured += "\n💡 Remember: The key concept here is understanding "
        
        if objectives:
            structured += objectives[0].topic.lower()
        
        return structured
    
    def _structure_problem_solving(self, response: str, objectives: List[LearningObjective]) -> str:
        """Structure response for problem-solving"""
        structured = "Let's solve this together!\n\n"
        
        # Problem-solving framework
        structured += "**Step 1: Understand the Problem**\n"
        structured += "What do we need to find?\n\n"
        
        structured += "**Step 2: Plan Our Approach**\n"
        structured += "What method should we use?\n\n"
        
        structured += "**Step 3: Execute the Solution**\n"
        structured += response + "\n\n"
        
        structured += "**Step 4: Check Our Answer**\n"
        structured += "Does this make sense?\n"
        
        return structured
    
    def _structure_definition(self, response: str, objectives: List[LearningObjective]) -> str:
        """Structure response as educational definition"""
        structured = response
        
        # Add examples if not present
        if 'example' not in response.lower() and 'for instance' not in response.lower():
            structured += "\n\n**Example**: "
            
            if objectives and objectives[0].subject == STEMSubject.SCIENCE:
                structured += "Think about how this works in nature..."
            elif objectives and objectives[0].subject == STEMSubject.MATHEMATICS:
                structured += "Here's how we use this in math..."
            else:
                structured += "Here's how this applies in real life..."
        
        return structured
    
    def _structure_general(self, response: str, objectives: List[LearningObjective]) -> str:
        """Structure general educational response"""
        return response
    
    def _add_interactive_elements(self, response: str, context: Any, 
                                 objectives: List[LearningObjective]) -> str:
        """Add interactive educational elements"""
        interactive = response
        
        # Add follow-up questions for engagement
        if '?' not in response[-20:]:  # No question at end
            age = context.child_age
            
            if age < 8:
                questions = [
                    "Can you think of another example?",
                    "What do you think happens next?",
                    "Would you like to try a fun activity?"
                ]
            elif age < 12:
                questions = [
                    "Can you apply this to solve a problem?",
                    "What would happen if we changed one thing?",
                    "Ready for a challenge question?"
                ]
            else:
                questions = [
                    "How might this concept apply elsewhere?",
                    "Can you think of a real-world application?",
                    "Would you like to explore this deeper?"
                ]
            
            interactive += f"\n\n🤔 {random.choice(questions)}"
        
        # Add mini-challenge if appropriate
        if objectives and context.metadata.get('add_challenge', True):
            challenge = self._generate_mini_challenge(objectives[0], context.child_age)
            if challenge:
                interactive += f"\n\n🎯 **Mini Challenge**: {challenge}"
        
        return interactive
    
    def _generate_mini_challenge(self, objective: LearningObjective, age: int) -> Optional[str]:
        """Generate age-appropriate mini challenge"""
        challenges = {
            'Living Things': {
                5: "Can you name 3 animals that live in water?",
                8: "What's the difference between a plant and an animal?",
                11: "How do plants make their own food?",
                14: "Explain the role of producers in an ecosystem."
            },
            'Numbers and Counting': {
                5: "Can you count backwards from 10?",
                8: "What's 7 + 8?",
                11: "If you have 24 cookies and share equally with 3 friends, how many does each get?",
                14: "Solve for x: 3x + 7 = 22"
            },
            'Basic Computer Skills': {
                5: "Can you name 3 parts of a computer?",
                8: "What does 'save' mean when using a computer?",
                11: "Why is it important to have strong passwords?",
                14: "What's the difference between hardware and software?"
            }
        }
        
        if objective.topic in challenges:
            age_challenges = challenges[objective.topic]
            
            # Find closest age match
            closest_age = min(age_challenges.keys(), key=lambda x: abs(x - age))
            return age_challenges[closest_age]
        
        return None
    
    def _track_learning_progress(self, context: Any, objectives: List[LearningObjective]) -> None:
        """Track learning progress for each child"""
        if not objectives:
            return
        
        progress_file = self.usb_path / 'progress' / f"{context.profile_id}_progress.json"
        
        try:
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing progress
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
            else:
                progress = {
                    'objectives_encountered': {},
                    'skills_developed': {},
                    'topics_explored': [],
                    'total_interactions': 0
                }
            
            # Update progress
            for objective in objectives:
                obj_id = objective.id
                
                if obj_id not in progress['objectives_encountered']:
                    progress['objectives_encountered'][obj_id] = {
                        'first_encounter': datetime.utcnow().isoformat(),
                        'encounter_count': 0,
                        'mastery_level': 0.0
                    }
                
                progress['objectives_encountered'][obj_id]['encounter_count'] += 1
                
                # Update skills
                for skill in objective.skills:
                    if skill not in progress['skills_developed']:
                        progress['skills_developed'][skill] = 0
                    progress['skills_developed'][skill] += 1
                
                # Track topics
                if objective.topic not in progress['topics_explored']:
                    progress['topics_explored'].append(objective.topic)
            
            progress['total_interactions'] += 1
            
            # Save updated progress
            with open(progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to track progress: {e}")
    
    def _extract_concepts(self, response: str) -> List[str]:
        """Extract educational concepts from response"""
        concepts = []
        
        # Check for known concepts in response
        for concept in self.concept_map.keys():
            if concept in response.lower():
                concepts.append(concept)
        
        return concepts
    
    def _assess_difficulty(self, context: Any, objectives: List[LearningObjective]) -> str:
        """Assess difficulty level of content"""
        if not objectives:
            return 'appropriate'
        
        # Compare objective grade level with child's grade
        child_grade = self._get_grade_key(context.child_age)
        objective_grade = objectives[0].grade_level if objectives else child_grade
        
        grade_order = ['K-2', '3-5', '6-8', '9-12']
        
        child_index = grade_order.index(child_grade)
        obj_index = grade_order.index(objective_grade)
        
        if obj_index < child_index:
            return 'below_level'
        elif obj_index > child_index:
            return 'above_level'
        else:
            return 'appropriate'
    
    def _suggest_follow_ups(self, objectives: List[LearningObjective]) -> List[str]:
        """Suggest follow-up topics based on current learning"""
        follow_ups = []
        
        if not objectives:
            return ["Explore more STEM topics!", "Try a hands-on experiment", "Solve practice problems"]
        
        # Get prerequisites and next steps
        for objective in objectives:
            # Find objectives that have this as prerequisite
            for grade_objs in self.curriculum.values():
                for subject_objs in grade_objs.values():
                    for obj in subject_objs:
                        if objective.id in obj.prerequisites:
                            follow_ups.append(obj.topic)
        
        # Add related concepts
        for objective in objectives:
            topic_words = objective.topic.lower().split()
            for word in topic_words:
                if word in self.concept_map:
                    follow_ups.extend(self.concept_map[word][:2])
        
        return list(set(follow_ups))[:5]  # Return up to 5 unique suggestions
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract educational keywords from text"""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'about', 'as', 'is', 'was', 'are', 'were',
                     'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                     'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what',
                     'how', 'why', 'when', 'where', 'who', 'which', 'this', 'that', 'these',
                     'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her'}
        
        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _assess_query_complexity(self, context: Any) -> str:
        """Assess complexity level of the query"""
        text = context.input_text.lower()
        
        # Simple indicators
        simple_indicators = ['what is', 'how many', 'name', 'list', 'tell me']
        complex_indicators = ['explain why', 'compare', 'analyze', 'evaluate', 'prove']
        
        for indicator in complex_indicators:
            if indicator in text:
                return 'complex'
        
        for indicator in simple_indicators:
            if indicator in text:
                return 'simple'
        
        return 'moderate'

class TeachingStrategies:
    """Educational teaching strategies"""
    
    def get_strategy(self, learning_style: str, subject: STEMSubject) -> Dict[str, Any]:
        """Get appropriate teaching strategy"""
        strategies = {
            'visual': {
                'approach': 'Use diagrams and visual representations',
                'techniques': ['mind_maps', 'charts', 'illustrations']
            },
            'kinesthetic': {
                'approach': 'Hands-on activities and experiments',
                'techniques': ['experiments', 'building', 'simulations']
            },
            'auditory': {
                'approach': 'Verbal explanations and discussions',
                'techniques': ['storytelling', 'mnemonics', 'repetition']
            },
            'logical': {
                'approach': 'Step-by-step reasoning and analysis',
                'techniques': ['problem_solving', 'patterns', 'sequences']
            }
        }
        
        return strategies.get(learning_style, strategies['logical'])

class AssessmentEngine:
    """Learning assessment engine"""
    
    def __init__(self, usb_path: Path):
        """Initialize assessment engine"""
        self.usb_path = Path(usb_path)
        self.assessment_path = self.usb_path / 'assessments'
        self.assessment_path.mkdir(parents=True, exist_ok=True)
    
    def assess_understanding(self, context: Any, objective: LearningObjective) -> float:
        """Assess understanding level for objective"""
        # Simplified assessment logic
        # In production, this would analyze response quality, correctness, etc.
        return 0.75  # Placeholder
    
    def generate_assessment(self, objective: LearningObjective, difficulty: str) -> Dict[str, Any]:
        """Generate assessment questions"""
        assessment = {
            'objective_id': objective.id,
            'questions': [],
            'difficulty': difficulty
        }
        
        # Generate questions based on assessment criteria
        for criterion in objective.assessment_criteria[:3]:
            assessment['questions'].append({
                'criterion': criterion,
                'question': f"Can you demonstrate {criterion}?",
                'type': 'open_ended'
            })
        
        return assessment

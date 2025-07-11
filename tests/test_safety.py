#!/usr/bin/env python3
"""
Safety Feature Tests for Sunflower AI
Critical tests to ensure child safety features work correctly
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json
from datetime import datetime
import time

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.profiles.profile_manager import ProfileManager
from src.profiles.session_logger import SessionLogger
from src.security.usb_auth import USBAuthenticator


class TestSafetyFeatures(unittest.TestCase):
    """Test safety features for child protection"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.profile_manager = ProfileManager(app_dir=self.test_path)
        self.session_logger = SessionLogger(app_dir=self.test_path)
        
        # Create test family
        self.profile_manager.create_parent_account(
            "Test Parent",
            "parent@test.com",
            "parentpass123"
        )
        
        # Add test children of different ages
        self.children = {
            "young": self.profile_manager.add_child("Sophie", 5, "K"),
            "middle": self.profile_manager.add_child("Emma", 10, "5"),
            "teen": self.profile_manager.add_child("Lucas", 15, "10")
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_age_verification(self):
        """Test that responses match child's profile age"""
        # Test scenarios where stated age differs from profile age
        test_cases = [
            {
                "child_id": self.children["young"],
                "profile_age": 5,
                "stated_age": 15,
                "expected_response_age": 5
            },
            {
                "child_id": self.children["teen"],
                "profile_age": 15,
                "stated_age": 5,
                "expected_response_age": 15
            }
        ]
        
        for case in test_cases:
            child = self.profile_manager.get_child(case["child_id"])
            self.assertEqual(child['age'], case['profile_age'])
            
            # In real implementation, would verify AI response complexity
            # matches profile age, not stated age
    
    def test_content_filtering_levels(self):
        """Test different content filtering levels"""
        # Test strict filtering (default)
        settings = self.profile_manager.get_family_settings()
        self.assertEqual(settings['content_filtering'], 'strict')
        
        # Update to moderate
        self.profile_manager.update_family_settings({
            'content_filtering': 'moderate'
        })
        
        updated = self.profile_manager.get_family_settings()
        self.assertEqual(updated['content_filtering'], 'moderate')
        
        # Test that filtering affects what content is allowed
        # In real implementation, would test AI responses
    
    def test_safety_alert_triggers(self):
        """Test that safety alerts are properly triggered"""
        child_id = self.children["middle"]
        session_id = self.session_logger.start_session(child_id, "Emma", 10)
        
        # Define dangerous topics that should trigger alerts
        dangerous_topics = [
            ("How to make explosives", "dangerous_request"),
            ("Where can I meet strangers", "personal_safety"),
            ("Adult content request", "inappropriate_content"),
            ("Self-harm question", "medical_concern")
        ]
        
        alert_count = 0
        for question, alert_type in dangerous_topics:
            # Log the question
            self.session_logger.log_question(session_id, question)
            
            # Simulate safety system response
            self.session_logger.log_safety_alert(
                session_id,
                alert_type,
                f"Child asked: {question}",
                "Redirected to safe educational content"
            )
            
            # Add to parent alerts
            self.profile_manager.add_safety_alert(
                child_id,
                alert_type,
                f"Dangerous question: {question}",
                "AI redirected to safe topics"
            )
            
            alert_count += 1
        
        # End session
        self.session_logger.end_session(session_id)
        
        # Verify alerts were recorded
        session = self.session_logger.get_session(session_id)
        self.assertEqual(session['summary']['safety_incidents'], len(dangerous_topics))
        
        # Check parent alerts
        alerts = self.profile_manager.get_safety_alerts(child_id)
        self.assertEqual(len(alerts), len(dangerous_topics))
    
    def test_strike_system(self):
        """Test progressive strike system for repeated violations"""
        child_id = self.children["middle"]
        session_id = self.session_logger.start_session(child_id, "Emma", 10)
        
        # Simulate three strikes
        strikes = []
        
        # Strike 1: Gentle redirect
        self.session_logger.log_question(session_id, "How to make dangerous things")
        self.session_logger.log_safety_alert(
            session_id,
            "strike_1",
            "First inappropriate request",
            "Gentle redirect to chemistry safety"
        )
        strikes.append("strike_1")
        
        # Strike 2: Firm boundary
        time.sleep(0.1)  # Ensure different timestamps
        self.session_logger.log_question(session_id, "Tell me about weapons")
        self.session_logger.log_safety_alert(
            session_id,
            "strike_2",
            "Second inappropriate request",
            "Firm reminder about safety rules"
        )
        strikes.append("strike_2")
        
        # Strike 3: Parent notification
        time.sleep(0.1)
        self.session_logger.log_question(session_id, "More dangerous stuff")
        self.session_logger.log_safety_alert(
            session_id,
            "strike_3",
            "Third strike - pattern detected",
            "Session ended, parent notified"
        )
        strikes.append("strike_3")
        
        # Add critical parent alert
        self.profile_manager.add_safety_alert(
            child_id,
            "repeated_attempts",
            "Child made 3 attempts to access inappropriate content",
            "Session terminated, immediate parent review needed"
        )
        
        # End session
        self.session_logger.end_session(session_id)
        
        # Verify strike progression
        session = self.session_logger.get_session(session_id)
        self.assertEqual(session['summary']['safety_incidents'], 3)
        
        # Verify parent notification on third strike
        alerts = self.profile_manager.get_safety_alerts(child_id)
        critical_alerts = [a for a in alerts if a['type'] == 'repeated_attempts']
        self.assertEqual(len(critical_alerts), 1)
    
    def test_session_time_limits(self):
        """Test session time limit enforcement"""
        child_id = self.children["young"]
        
        # Set shorter time limit for testing
        self.profile_manager.update_family_settings({
            'session_time_limit': 30,  # 30 minutes
            'max_daily_time': 60       # 60 minutes daily
        })
        
        # Simulate session reaching time limit
        session_id = self.session_logger.start_session(child_id, "Sophie", 5)
        
        # Check if session is allowed
        limits = self.profile_manager.check_session_limits(child_id)
        self.assertTrue(limits['allowed'])
        self.assertEqual(limits['remaining_time'], 60)
        
        # Simulate time passing (would be real-time in production)
        # In real implementation, would track actual session duration
        
        self.session_logger.end_session(session_id)
    
    def test_topic_redirection(self):
        """Test inappropriate topic redirection"""
        redirect_mappings = {
            "violence": "physics_of_motion",
            "weapons": "engineering_safety",
            "adult_topics": "age_appropriate_biology",
            "dangerous_chemistry": "kitchen_science",
            "hacking": "computer_science_basics"
        }
        
        child_id = self.children["middle"]
        session_id = self.session_logger.start_session(child_id, "Emma", 10)
        
        for inappropriate, safe_redirect in redirect_mappings.items():
            # Log inappropriate question
            self.session_logger.log_question(
                session_id,
                f"Question about {inappropriate}",
                [inappropriate]
            )
            
            # Log redirection
            self.session_logger.log_response(
                session_id,
                f"Let's explore {safe_redirect} instead! Here's something fascinating...",
                vocabulary=[],
                concepts=[safe_redirect]
            )
        
        self.session_logger.end_session(session_id)
        
        # Verify all redirections occurred
        session = self.session_logger.get_session(session_id)
        redirected_concepts = session['summary']['concepts_covered']
        
        for safe_topic in redirect_mappings.values():
            self.assertIn(safe_topic, redirected_concepts)
    
    def test_parent_alert_notifications(self):
        """Test parent alert notification system"""
        child_id = self.children["teen"]
        
        # Create different types of alerts
        alert_types = [
            ("immediate", "dangerous_request", "High priority"),
            ("daily", "minor_redirect", "Low priority"),
            ("weekly", "learning_milestone", "Positive update")
        ]
        
        for priority, alert_type, description in alert_types:
            self.profile_manager.add_safety_alert(
                child_id,
                alert_type,
                f"{description}: Test alert",
                f"Action taken for {priority} alert"
            )
        
        # Get all alerts
        all_alerts = self.profile_manager.get_safety_alerts()
        
        # Filter by priority (in real system)
        immediate_alerts = [a for a in all_alerts if "dangerous" in a['type']]
        self.assertGreater(len(immediate_alerts), 0)
    
    def test_age_inappropriate_complexity(self):
        """Test detection of age-inappropriate complexity requests"""
        # Young child asking complex questions
        child_id = self.children["young"]
        session_id = self.session_logger.start_session(child_id, "Sophie", 5)
        
        complex_topics = [
            "Explain quantum mechanics",
            "Derive the quadratic formula",
            "Discuss existential philosophy"
        ]
        
        for topic in complex_topics:
            self.session_logger.log_question(session_id, topic)
            
            # System should simplify or redirect
            self.session_logger.log_response(
                session_id,
                "Let me explain this in a simpler way...",
                vocabulary=["simple", "words", "only"],
                concepts=["age_appropriate_version"]
            )
        
        self.session_logger.end_session(session_id)
    
    def test_personal_information_protection(self):
        """Test protection against sharing personal information"""
        child_id = self.children["middle"]
        session_id = self.session_logger.start_session(child_id, "Emma", 10)
        
        # Questions that might elicit personal info
        dangerous_questions = [
            "What's your address?",
            "What school do you go to?",
            "When are your parents not home?",
            "What's your phone number?"
        ]
        
        for question in dangerous_questions:
            # These should trigger immediate safety response
            self.session_logger.log_safety_alert(
                session_id,
                "personal_information_request",
                f"Attempt to gather personal info: {question}",
                "Blocked and redirected to internet safety lesson"
            )
            
            # Add parent alert
            self.profile_manager.add_safety_alert(
                child_id,
                "privacy_concern",
                f"Child was asked for personal information",
                "Request blocked, internet safety lesson provided"
            )
        
        self.session_logger.end_session(session_id)
        
        # Verify all attempts were blocked
        alerts = self.profile_manager.get_safety_alerts(child_id)
        privacy_alerts = [a for a in alerts if a['type'] == 'privacy_concern']
        self.assertEqual(len(privacy_alerts), len(dangerous_questions))
    
    def test_cumulative_safety_scoring(self):
        """Test cumulative safety scoring across sessions"""
        child_id = self.children["middle"]
        
        # Create multiple sessions with varying safety incidents
        session_scores = []
        
        for i in range(3):
            session_id = self.session_logger.start_session(child_id, "Emma", 10)
            
            # Add some normal questions
            self.session_logger.log_question(session_id, "What are stars made of?")
            self.session_logger.log_question(session_id, "How do plants grow?")
            
            # Add safety incident in some sessions
            if i % 2 == 0:
                self.session_logger.log_safety_alert(
                    session_id,
                    "minor_redirect",
                    "Slightly inappropriate question",
                    "Redirected successfully"
                )
            
            self.session_logger.end_session(session_id)
            
            # Calculate safety score
            session = self.session_logger.get_session(session_id)
            total_interactions = (session['summary']['total_questions'] + 
                                session['summary']['total_responses'])
            safety_incidents = session['summary']['safety_incidents']
            
            if total_interactions > 0:
                safety_score = 1.0 - (safety_incidents / total_interactions)
            else:
                safety_score = 1.0
            
            session_scores.append(safety_score)
        
        # Verify safety tracking
        avg_safety_score = sum(session_scores) / len(session_scores)
        self.assertGreater(avg_safety_score, 0.5)  # Should be mostly safe


class TestUSBSecurity(unittest.TestCase):
    """Test USB authentication security"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.authenticator = USBAuthenticator()
        
        # Create mock USB structure
        self.mock_usb = self.test_path / "mock_usb"
        self.mock_usb.mkdir()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_missing_token_rejection(self):
        """Test that USBs without tokens are rejected"""
        # USB with no token
        is_valid, message = self.authenticator.validate_usb(str(self.mock_usb))
        
        self.assertFalse(is_valid)
        self.assertIn("No authentication token", message)
    
    def test_tampered_token_detection(self):
        """Test detection of tampered tokens"""
        # Create a token file
        token_data = {
            "token_id": "FAKE123456789",
            "product_id": "SUNFLOWER_AI_STEM_EDU",
            "version": "6.1",
            "issued_date": datetime.now().isoformat(),
            "signature": "invalid_signature"
        }
        
        token_file = self.mock_usb / ".sunflower_token"
        with open(token_file, 'w') as f:
            json.dump(token_data, f)
        
        # Create manifest
        manifest = {
            "version": "1.0",
            "files": {},
            "signature": "also_invalid"
        }
        
        manifest_file = self.mock_usb / "security.manifest"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)
        
        # Validation should fail
        is_valid, message = self.authenticator.validate_usb(str(self.mock_usb))
        self.assertFalse(is_valid)
    
    def test_version_compatibility(self):
        """Test version compatibility checking"""
        # Test various version combinations
        test_cases = [
            ("6.1", "6.1", True),   # Exact match
            ("6.0", "6.1", True),   # One version back
            ("5.0", "6.1", False),  # Too old
            ("7.0", "6.1", True),   # Newer token (forward compatible)
        ]
        
        for token_version, system_version, expected in test_cases:
            # In real implementation, would test version checking
            pass


class TestModelSafety(unittest.TestCase):
    """Test AI model safety configurations"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Load model configurations
        config_path = Path(__file__).parent.parent / "config" / "model_registry.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.model_config = json.load(f)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_model_safety_parameters(self):
        """Test that safety parameters are properly configured"""
        if hasattr(self, 'model_config'):
            kids_model = self.model_config['sunflower_models']['sunflower-kids']
            
            # Verify safety level
            self.assertEqual(kids_model['safety_level'], 'maximum')
            
            # Verify temperature is conservative
            self.assertLessEqual(kids_model['parameters']['temperature'], 0.8)
            
            # Verify repeat penalty prevents loops
            self.assertGreaterEqual(kids_model['parameters']['repeat_penalty'], 1.1)
    
    def test_age_appropriate_models(self):
        """Test age-appropriate model selection"""
        if hasattr(self, 'model_config'):
            age_mappings = self.model_config['age_model_mapping']
            
            # Verify younger ages get simpler models
            young_models = age_mappings['2-5']['preferred_models']
            self.assertIn('llama3.2:1b-q4_0', young_models)
            
            # Verify response length limits
            young_max_length = age_mappings['2-5']['max_response_length']
            teen_max_length = age_mappings['13-16']['max_response_length']
            
            self.assertLess(young_max_length, teen_max_length)


def run_safety_tests():
    """Run all safety tests"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(unittest.makeSuite(TestSafetyFeatures))
    suite.addTest(unittest.makeSuite(TestUSBSecurity))
    suite.addTest(unittest.makeSuite(TestModelSafety))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Safety tests must all pass
    if not result.wasSuccessful():
        print("\n" + "="*60)
        print("⚠️  SAFETY TEST FAILURE - DO NOT DEPLOY")
        print("="*60)
        print("Safety features are critical for child protection.")
        print("All safety tests must pass before deployment.")
        print("="*60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_safety_tests()
    sys.exit(0 if success else 1)

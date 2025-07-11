#!/usr/bin/env python3
"""
Profile System Tests for Sunflower AI
Tests family profile management, child profiles, and session logging
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.profiles.profile_manager import ProfileManager
from src.profiles.session_logger import SessionLogger, SessionEntry
from src.profiles.profile_storage import ProfileStorage


class TestProfileManager(unittest.TestCase):
    """Test ProfileManager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.manager = ProfileManager(app_dir=self.test_path)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_parent_account_creation(self):
        """Test parent account creation"""
        # Create parent account
        success = self.manager.create_parent_account(
            "Test Parent",
            "test@example.com",
            "password123"
        )
        
        self.assertTrue(success)
        self.assertTrue(self.manager.family_data['parent']['setup_complete'])
        self.assertEqual(self.manager.family_data['parent']['name'], "Test Parent")
        self.assertEqual(self.manager.family_data['parent']['email'], "test@example.com")
    
    def test_password_verification(self):
        """Test parent password verification"""
        # Create account
        self.manager.create_parent_account(
            "Test Parent",
            "test@example.com",
            "correctpassword"
        )
        
        # Test correct password
        self.assertTrue(self.manager.verify_parent_password("correctpassword"))
        
        # Test incorrect password
        self.assertFalse(self.manager.verify_parent_password("wrongpassword"))
    
    def test_add_child(self):
        """Test adding child profiles"""
        # Add first child
        child1_id = self.manager.add_child(
            "Emma",
            8,
            "3",
            ["butterflies", "space"]
        )
        
        self.assertIsNotNone(child1_id)
        self.assertEqual(len(self.manager.get_all_children()), 1)
        
        # Add second child
        child2_id = self.manager.add_child(
            "Lucas",
            12,
            "7",
            ["robots", "chemistry"]
        )
        
        self.assertIsNotNone(child2_id)
        self.assertEqual(len(self.manager.get_all_children()), 2)
        
        # Test invalid age
        invalid_id = self.manager.add_child("Baby", 1, "Pre-K")
        self.assertIsNone(invalid_id)
    
    def test_get_child(self):
        """Test retrieving child profiles"""
        # Add child
        child_id = self.manager.add_child(
            "Sophia",
            10,
            "5",
            ["art", "music"]
        )
        
        # Get by ID
        child = self.manager.get_child(child_id)
        self.assertIsNotNone(child)
        self.assertEqual(child['name'], "Sophia")
        self.assertEqual(child['age'], 10)
        
        # Get by name
        child_by_name = self.manager.get_child_by_name("Sophia")
        self.assertIsNotNone(child_by_name)
        self.assertEqual(child_by_name['id'], child_id)
        
        # Test non-existent child
        self.assertIsNone(self.manager.get_child("invalid_id"))
        self.assertIsNone(self.manager.get_child_by_name("NonExistent"))
    
    def test_update_child_profile(self):
        """Test updating child profiles"""
        # Add child
        child_id = self.manager.add_child("Test Child", 8, "3")
        
        # Update profile
        success = self.manager.update_child_profile(child_id, {
            "age": 9,
            "grade": "4",
            "interests": ["science", "math"]
        })
        
        self.assertTrue(success)
        
        # Verify updates
        child = self.manager.get_child(child_id)
        self.assertEqual(child['age'], 9)
        self.assertEqual(child['grade'], "4")
        self.assertEqual(child['interests'], ["science", "math"])
    
    def test_remove_child(self):
        """Test removing child profiles"""
        # Add children
        child1_id = self.manager.add_child("Child1", 8, "3")
        child2_id = self.manager.add_child("Child2", 10, "5")
        
        self.assertEqual(len(self.manager.get_all_children()), 2)
        
        # Remove one child
        success = self.manager.remove_child(child1_id)
        self.assertTrue(success)
        self.assertEqual(len(self.manager.get_all_children()), 1)
        
        # Verify correct child was removed
        self.assertIsNone(self.manager.get_child(child1_id))
        self.assertIsNotNone(self.manager.get_child(child2_id))
    
    def test_safety_alerts(self):
        """Test safety alert system"""
        # Add child
        child_id = self.manager.add_child("Test Child", 10, "5")
        
        # Add safety alert
        success = self.manager.add_safety_alert(
            child_id,
            "inappropriate_content",
            "Child asked about dangerous topics",
            "Redirected to safe content"
        )
        
        self.assertTrue(success)
        
        # Get alerts
        alerts = self.manager.get_safety_alerts(child_id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], "inappropriate_content")
    
    def test_session_limits(self):
        """Test session time limit checking"""
        # Add child
        child_id = self.manager.add_child("Test Child", 8, "3")
        
        # Check limits (should be allowed initially)
        result = self.manager.check_session_limits(child_id)
        self.assertTrue(result['allowed'])
        self.assertIn('remaining_time', result)
    
    def test_family_settings(self):
        """Test family settings management"""
        # Get default settings
        settings = self.manager.get_family_settings()
        self.assertEqual(settings['content_filtering'], 'strict')
        self.assertTrue(settings['session_recording'])
        
        # Update settings
        success = self.manager.update_family_settings({
            'content_filtering': 'moderate',
            'session_time_limit': 45
        })
        
        self.assertTrue(success)
        
        # Verify updates
        updated = self.manager.get_family_settings()
        self.assertEqual(updated['content_filtering'], 'moderate')
        self.assertEqual(updated['session_time_limit'], 45)
    
    def test_progress_tracking(self):
        """Test child progress tracking"""
        # Add child
        child_id = self.manager.add_child("Test Child", 10, "5")
        
        # Update progress
        session_data = {
            'duration_minutes': 30,
            'new_vocabulary': ['photosynthesis', 'chlorophyll'],
            'concepts_covered': ['plant biology', 'energy conversion'],
            'topics': ['science', 'biology']
        }
        
        success = self.manager.update_child_progress(child_id, session_data)
        self.assertTrue(success)
        
        # Get statistics
        stats = self.manager.get_session_statistics(child_id)
        self.assertEqual(stats['total_sessions'], 1)
        self.assertEqual(stats['total_time_minutes'], 30)
        self.assertEqual(stats['total_vocabulary'], 2)
        self.assertEqual(stats['total_concepts'], 2)
    
    def test_data_export_import(self):
        """Test profile data export and import"""
        # Create test data
        self.manager.create_parent_account("Test Parent", "test@example.com", "password")
        child_id = self.manager.add_child("Test Child", 8, "3", ["science"])
        
        # Export data
        export_path = self.manager.export_profile_data()
        self.assertIsNotNone(export_path)
        self.assertTrue(export_path.exists())
        
        # Create new manager and import
        new_manager = ProfileManager(app_dir=self.test_path)
        success = new_manager.import_profile_data(export_path)
        
        self.assertTrue(success)
        self.assertEqual(len(new_manager.get_all_children()), 1)
        self.assertEqual(new_manager.family_data['parent']['name'], "Test Parent")


class TestSessionLogger(unittest.TestCase):
    """Test SessionLogger functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.logger = SessionLogger(app_dir=self.test_path)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_session_lifecycle(self):
        """Test complete session lifecycle"""
        # Start session
        session_id = self.logger.start_session(
            "child_001",
            "Emma",
            8,
            {"test": True}
        )
        
        self.assertIsNotNone(session_id)
        self.assertIn(session_id, self.logger.active_sessions)
        
        # Add entries
        self.assertTrue(self.logger.log_question(
            session_id,
            "Why is the sky blue?",
            ["physics", "atmosphere"]
        ))
        
        self.assertTrue(self.logger.log_response(
            session_id,
            "The sky appears blue because...",
            vocabulary=["atmosphere", "wavelength"],
            concepts=["light scattering"]
        ))
        
        # End session
        self.assertTrue(self.logger.end_session(session_id))
        self.assertNotIn(session_id, self.logger.active_sessions)
        
        # Verify session was saved
        saved_session = self.logger.get_session(session_id)
        self.assertIsNotNone(saved_session)
        self.assertEqual(saved_session['child_name'], "Emma")
        self.assertEqual(saved_session['summary']['total_questions'], 1)
        self.assertEqual(saved_session['summary']['total_responses'], 1)
    
    def test_safety_logging(self):
        """Test safety alert logging"""
        # Start session
        session_id = self.logger.start_session("child_001", "Test", 10)
        
        # Log safety alert
        success = self.logger.log_safety_alert(
            session_id,
            "inappropriate_content",
            "Child asked about weapons",
            "Redirected to physics of motion"
        )
        
        self.assertTrue(success)
        
        # Check summary
        session = self.logger.get_active_session(session_id)
        self.assertEqual(session['summary']['safety_incidents'], 1)
        self.assertEqual(len(session['summary']['parent_alerts']), 1)
    
    def test_session_history(self):
        """Test retrieving session history"""
        child_id = "test_child_001"
        
        # Create multiple sessions
        for i in range(3):
            session_id = self.logger.start_session(
                child_id,
                "Test Child",
                10
            )
            self.logger.log_question(session_id, f"Question {i}")
            self.logger.end_session(session_id)
        
        # Get history
        history = self.logger.get_session_history(child_id, days=30)
        self.assertEqual(len(history), 3)
        
        # Verify order (newest first)
        self.assertIn("Question 2", history[0]['entries'][1]['content'])
    
    def test_daily_summary(self):
        """Test daily summary generation"""
        child_id = "test_child_001"
        
        # Create session
        session_id = self.logger.start_session(child_id, "Test", 10)
        self.logger.log_question(session_id, "What is photosynthesis?", ["biology"])
        self.logger.log_response(
            session_id,
            "Photosynthesis is...",
            vocabulary=["chlorophyll", "glucose"],
            concepts=["energy conversion"]
        )
        self.logger.end_session(session_id)
        
        # Get daily summary
        summary = self.logger.get_daily_summary(child_id)
        
        self.assertEqual(summary['total_sessions'], 1)
        self.assertGreater(summary['total_time_minutes'], 0)
        self.assertEqual(summary['total_questions'], 1)
        self.assertIn("biology", summary['unique_topics'])
        self.assertEqual(len(summary['new_vocabulary']), 2)
    
    def test_weekly_report(self):
        """Test weekly report generation"""
        child_id = "test_child_001"
        
        # Create sessions across multiple days
        for i in range(3):
            session_id = self.logger.start_session(child_id, "Test", 10)
            self.logger.log_question(
                session_id,
                f"Question about topic {i}",
                [f"topic_{i}"]
            )
            self.logger.end_session(session_id)
        
        # Get weekly report
        report = self.logger.get_weekly_report(child_id)
        
        self.assertEqual(report['total_sessions'], 3)
        self.assertEqual(len(report['all_topics']), 3)
        self.assertIn('daily_breakdown', report)
    
    def test_session_search(self):
        """Test searching sessions"""
        child_id = "test_child_001"
        
        # Create sessions with different content
        session1 = self.logger.start_session(child_id, "Test", 10)
        self.logger.log_question(session1, "What are butterflies?")
        self.logger.log_response(session1, "Butterflies are insects...")
        self.logger.end_session(session1)
        
        session2 = self.logger.start_session(child_id, "Test", 10)
        self.logger.log_question(session2, "How do rockets work?")
        self.logger.log_response(session2, "Rockets use propulsion...")
        self.logger.end_session(session2)
        
        # Search for butterflies
        results = self.logger.search_sessions(child_id, "butterflies")
        self.assertEqual(len(results), 1)
        self.assertIn("butterflies", results[0]['match_context']['content_preview'])
        
        # Search for rockets
        results = self.logger.search_sessions(child_id, "rockets")
        self.assertEqual(len(results), 1)
    
    def test_learning_progress(self):
        """Test learning progress tracking"""
        child_id = "test_child_001"
        
        # Create sessions with vocabulary and concepts
        for i in range(3):
            session_id = self.logger.start_session(child_id, "Test", 10)
            self.logger.log_response(
                session_id,
                f"Response {i}",
                vocabulary=[f"word_{i}", f"term_{i}"],
                concepts=[f"concept_{i}"]
            )
            self.logger.end_session(session_id)
        
        # Get progress
        progress = self.logger.get_learning_progress(child_id)
        
        self.assertEqual(progress['total_sessions'], 3)
        self.assertGreater(progress['total_hours'], 0)
        self.assertGreater(len(progress['vocabulary_timeline']), 0)
        self.assertEqual(len(progress['concepts_mastered']), 3)


class TestProfileStorage(unittest.TestCase):
    """Test ProfileStorage encryption functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        self.storage = ProfileStorage(app_dir=self.test_path)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_profile_encryption(self):
        """Test profile encryption and decryption"""
        # Create test profile
        profile_data = {
            'id': 'test_001',
            'name': 'Test Child',
            'age': 10,
            'safety': {
                'parent_alerts': [
                    {'timestamp': '2024-01-01', 'type': 'test'}
                ]
            }
        }
        
        # Save encrypted
        success = self.storage.save_profile('test_001', profile_data)
        self.assertTrue(success)
        
        # Load and verify
        loaded = self.storage.load_profile('test_001')
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['name'], 'Test Child')
        self.assertEqual(loaded['age'], 10)
    
    def test_session_encryption(self):
        """Test session encryption and decryption"""
        # Create test session
        session_data = {
            'session_id': 'sess_001',
            'child_id': 'child_001',
            'entries': [
                {'type': 'question', 'content': 'Test question'}
            ]
        }
        
        # Save encrypted
        success = self.storage.save_session('sess_001', session_data)
        self.assertTrue(success)
        
        # Load and verify
        loaded = self.storage.load_session('sess_001')
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['session_id'], 'sess_001')
        self.assertEqual(len(loaded['entries']), 1)
    
    def test_secure_deletion(self):
        """Test secure file deletion"""
        # Save data
        self.storage.save_profile('delete_test', {'name': 'Test'})
        
        # Verify it exists
        self.assertIsNotNone(self.storage.load_profile('delete_test'))
        
        # Delete securely
        success = self.storage.delete_secure_data('profile_delete_test')
        self.assertTrue(success)
        
        # Verify deletion
        self.assertIsNone(self.storage.load_profile('delete_test'))
    
    def test_export_import(self):
        """Test export/import with password"""
        # Create test data
        self.storage.save_profile('child_001', {'name': 'Child 1'})
        self.storage.save_session('sess_001', {'data': 'test'})
        
        # Export with password
        export_password = "test_password_123"
        export_data = self.storage.export_all_data(export_password)
        self.assertIsNotNone(export_data)
        
        # Create new storage instance
        new_storage = ProfileStorage(app_dir=self.test_path / 'new')
        
        # Import with correct password
        success = new_storage.import_all_data(export_data, export_password)
        self.assertTrue(success)
        
        # Verify imported data
        profile = new_storage.load_profile('child_001')
        self.assertIsNotNone(profile)
        self.assertEqual(profile['name'], 'Child 1')
        
        # Test wrong password
        another_storage = ProfileStorage(app_dir=self.test_path / 'another')
        success = another_storage.import_all_data(export_data, "wrong_password")
        self.assertFalse(success)


def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(unittest.makeSuite(TestProfileManager))
    suite.addTest(unittest.makeSuite(TestSessionLogger))
    suite.addTest(unittest.makeSuite(TestProfileStorage))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test Open WebUI Integration with Sunflower AI
Comprehensive testing of Open WebUI integration with safety and profile systems
"""

import os
import sys
import json
import time
import unittest
import tempfile
import sqlite3
import hashlib
import psutil
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock
from cryptography.fernet import Fernet

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import standardized path configuration
from config.path_config import PathConfiguration, get_usb_path, get_cdrom_path

# Import components to test
from safety_filter import SafetyFilter
from pipelines import PipelineOrchestrator, PipelineContext


class TestOpenWebUIIntegration(unittest.TestCase):
    """Test suite for Open WebUI integration"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory structure mimicking real partitions
        self.temp_dir = tempfile.mkdtemp(prefix="sunflower_test_")
        
        # Create mock partition structure
        self.mock_cdrom = Path(self.temp_dir) / "SUNFLOWER_CD"
        self.mock_usb = Path(self.temp_dir) / "SUNFLOWER_DATA"
        
        self.mock_cdrom.mkdir()
        self.mock_usb.mkdir()
        
        # Create marker files
        (self.mock_cdrom / "sunflower_cd.id").write_text("SUNFLOWER_AI_SYSTEM_v6.2.0")
        (self.mock_usb / "sunflower_data.id").write_text("SUNFLOWER_AI_DATA_v6.2.0")
        
        # Create standardized directory structure
        path_config = PathConfiguration(auto_detect=False)
        
        # Create CD-ROM directories
        for dir_name in path_config.CDROM_STRUCTURE.values():
            (self.mock_cdrom / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create USB directories
        for dir_name in path_config.USB_STRUCTURE.values():
            (self.mock_usb / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Patch the path configuration to use our mock directories
        self.path_patch = patch('config.path_config.get_path_config')
        mock_config = self.path_patch.start()
        mock_config.return_value.cdrom_path = self.mock_cdrom
        mock_config.return_value.usb_path = self.mock_usb
        
        # Initialize components with mock paths
        self.safety_filter = SafetyFilter(self.mock_usb)
        
    def tearDown(self):
        """Clean up test environment"""
        self.path_patch.stop()
        
        # Clean up temporary directory
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_path_detection(self):
        """Test that paths are correctly detected"""
        from config.path_config import get_usb_path, get_cdrom_path
        
        # These should return our mock paths
        usb_path = get_usb_path()
        cdrom_path = get_cdrom_path()
        
        self.assertEqual(usb_path, self.mock_usb)
        self.assertEqual(cdrom_path, self.mock_cdrom)
    
    def test_safety_filter_initialization(self):
        """Test safety filter initializes with correct paths"""
        self.assertIsNotNone(self.safety_filter)
        self.assertEqual(self.safety_filter.usb_path, self.mock_usb)
        
        # Check that safety directories were created
        safety_dir = self.mock_usb / 'safety'
        self.assertTrue(safety_dir.exists())
        
        # Check that database was initialized
        db_path = safety_dir / 'incidents.db'
        self.assertTrue(db_path.exists())
    
    def test_profile_system_with_paths(self):
        """Test profile system uses correct paths"""
        profiles_dir = self.mock_usb / 'profiles'
        self.assertTrue(profiles_dir.exists())
        
        # Create a test family profile
        family_data = {
            "family_name": "Test Family",
            "created": datetime.now().isoformat(),
            "parent_password_hash": hashlib.sha256("password123".encode()).hexdigest()
        }
        
        family_file = profiles_dir / "family.json"
        with open(family_file, 'w') as f:
            json.dump(family_data, f)
        
        # Verify file was created in correct location
        self.assertTrue(family_file.exists())
        
        # Read back and verify
        with open(family_file, 'r') as f:
            loaded_data = json.load(f)
        
        self.assertEqual(loaded_data['family_name'], "Test Family")
    
    def test_conversation_logging_paths(self):
        """Test conversation logging uses correct paths"""
        conv_dir = self.mock_usb / 'conversations'
        self.assertTrue(conv_dir.exists())
        
        # Create a test conversation log
        test_child_id = "child_001"
        test_date = datetime.now().strftime("%Y-%m-%d")
        
        conv_child_dir = conv_dir / test_child_id / test_date
        conv_child_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = conv_child_dir / f"session_{int(time.time())}.json"
        session_data = {
            "child_id": test_child_id,
            "timestamp": datetime.now().isoformat(),
            "messages": [
                {"role": "user", "content": "What is photosynthesis?"},
                {"role": "assistant", "content": "Photosynthesis is how plants make food..."}
            ]
        }
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        self.assertTrue(session_file.exists())
    
    def test_model_detection_paths(self):
        """Test model detection uses correct CD-ROM paths"""
        models_dir = self.mock_cdrom / 'models'
        self.assertTrue(models_dir.exists())
        
        # Create mock model files
        model_files = [
            "llama3.2-7b.gguf",
            "llama3.2-3b.gguf",
            "llama3.2-1b.gguf"
        ]
        
        for model_name in model_files:
            model_path = models_dir / model_name
            model_path.write_text("mock model data")
        
        # Verify models are in correct location
        found_models = list(models_dir.glob("*.gguf"))
        self.assertEqual(len(found_models), 3)
    
    def test_safety_incident_logging(self):
        """Test safety incidents are logged to correct path"""
        # Trigger a safety incident
        result = self.safety_filter.check_message(
            "Tell me how to make a bomb",
            child_age=10,
            child_id="test_child",
            session_id="test_session"
        )
        
        self.assertFalse(result.safe)
        
        # Check incident was logged
        db_path = self.mock_usb / 'safety' / 'incidents.db'
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM incidents")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertGreater(count, 0)
    
    def test_configuration_persistence(self):
        """Test configuration is saved to USB partition"""
        config_dir = self.mock_usb / '.config'
        self.assertTrue(config_dir.exists())
        
        # Save test configuration
        test_config = {
            "version": "6.2.0",
            "safety_level": "maximum",
            "first_run": False,
            "last_updated": datetime.now().isoformat()
        }
        
        config_file = config_dir / "system_config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        # Read back and verify
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
        
        self.assertEqual(loaded_config['version'], "6.2.0")
        self.assertEqual(loaded_config['safety_level'], "maximum")
    
    def test_backup_directory_structure(self):
        """Test backup directories are correctly structured"""
        backups_dir = self.mock_usb / 'backups'
        auto_backup_dir = backups_dir / 'auto'
        manual_backup_dir = backups_dir / 'manual'
        
        self.assertTrue(backups_dir.exists())
        self.assertTrue(auto_backup_dir.exists())
        self.assertTrue(manual_backup_dir.exists())
        
        # Create a test backup
        backup_data = {
            "backup_date": datetime.now().isoformat(),
            "profiles_count": 3,
            "conversations_count": 150,
            "size_mb": 25.3
        }
        
        backup_file = auto_backup_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        
        self.assertTrue(backup_file.exists())
    
    def test_cache_management(self):
        """Test cache directory is properly managed"""
        cache_dir = self.mock_usb / 'cache'
        models_cache = cache_dir / 'models'
        temp_cache = cache_dir / 'temp'
        
        self.assertTrue(cache_dir.exists())
        self.assertTrue(models_cache.exists())
        self.assertTrue(temp_cache.exists())
        
        # Create temp file
        temp_file = temp_cache / "temp_processing.tmp"
        temp_file.write_text("temporary data")
        
        self.assertTrue(temp_file.exists())
        
        # Simulate cache cleanup
        for temp_file in temp_cache.glob("*.tmp"):
            temp_file.unlink()
        
        self.assertEqual(len(list(temp_cache.glob("*.tmp"))), 0)
    
    def test_ollama_integration_paths(self):
        """Test Ollama binary detection on CD-ROM"""
        ollama_dir = self.mock_cdrom / 'ollama'
        self.assertTrue(ollama_dir.exists())
        
        # Create mock Ollama executable
        if platform.system() == "Windows":
            ollama_exe = ollama_dir / "ollama.exe"
        else:
            ollama_exe = ollama_dir / "ollama"
        
        ollama_exe.write_text("mock ollama binary")
        
        self.assertTrue(ollama_exe.exists())
    
    def test_documentation_paths(self):
        """Test documentation is accessible from CD-ROM"""
        docs_dir = self.mock_cdrom / 'docs'
        self.assertTrue(docs_dir.exists())
        
        # Create mock documentation
        user_manual = docs_dir / "user_manual.html"
        user_manual.write_text("<html><body>User Manual</body></html>")
        
        self.assertTrue(user_manual.exists())
    
    def test_security_token_storage(self):
        """Test security tokens are stored in correct location"""
        security_dir = self.mock_usb / '.security'
        self.assertTrue(security_dir.exists())
        
        # Create mock security token
        token_data = {
            "device_id": "SAI-TEST-001",
            "token": hashlib.sha256("test_token".encode()).hexdigest(),
            "created": datetime.now().isoformat()
        }
        
        token_file = security_dir / "device_token.json"
        with open(token_file, 'w') as f:
            json.dump(token_data, f)
        
        self.assertTrue(token_file.exists())
    
    def test_cross_partition_communication(self):
        """Test that system can read from CD-ROM and write to USB"""
        # Read model list from CD-ROM
        models_dir = self.mock_cdrom / 'models'
        model_files = list(models_dir.glob("*.gguf"))
        
        # Write selected model to USB config
        config_dir = self.mock_usb / '.config'
        selected_model_file = config_dir / "selected_model.json"
        
        selected_data = {
            "selected_model": model_files[0].name if model_files else "default",
            "selection_date": datetime.now().isoformat()
        }
        
        with open(selected_model_file, 'w') as f:
            json.dump(selected_data, f)
        
        self.assertTrue(selected_model_file.exists())
    
    def test_hardware_detection_logging(self):
        """Test hardware detection results are logged to USB"""
        logs_dir = self.mock_usb / 'logs' / 'system'
        self.assertTrue(logs_dir.exists())
        
        # Log hardware info
        hardware_info = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.system(),
            "ram_gb": psutil.virtual_memory().total / (1024**3),
            "cpu_cores": psutil.cpu_count(),
            "detected_model": "llama3.2:3b"
        }
        
        hw_log_file = logs_dir / f"hardware_{datetime.now().strftime('%Y%m%d')}.json"
        with open(hw_log_file, 'w') as f:
            json.dump(hardware_info, f)
        
        self.assertTrue(hw_log_file.exists())
    
    def test_session_management_paths(self):
        """Test session data is stored in correct location"""
        sessions_dir = self.mock_usb / 'sessions'
        self.assertTrue(sessions_dir.exists())
        
        # Create session directory structure
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")
        day = datetime.now().strftime("%d")
        
        session_day_dir = sessions_dir / year / month / day
        session_day_dir.mkdir(parents=True, exist_ok=True)
        
        # Create session file
        session_data = {
            "session_id": "session_001",
            "child_id": "child_001",
            "start_time": datetime.now().isoformat(),
            "interactions": 15,
            "topics": ["photosynthesis", "water cycle", "gravity"]
        }
        
        session_file = session_day_dir / f"session_{int(time.time())}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        self.assertTrue(session_file.exists())
    
    def test_progress_tracking_paths(self):
        """Test learning progress is tracked in correct location"""
        progress_dir = self.mock_usb / 'progress'
        self.assertTrue(progress_dir.exists())
        
        # Create progress file for a child
        child_progress = {
            "child_id": "child_001",
            "last_updated": datetime.now().isoformat(),
            "skills": {
                "mathematics": {"level": 3, "xp": 450},
                "science": {"level": 4, "xp": 680},
                "technology": {"level": 2, "xp": 230}
            },
            "achievements": ["First Question", "Science Explorer", "Math Wizard"]
        }
        
        progress_file = progress_dir / "child_001_progress.json"
        with open(progress_file, 'w') as f:
            json.dump(child_progress, f)
        
        self.assertTrue(progress_file.exists())


class TestPathMigration(unittest.TestCase):
    """Test path migration from old to new structure"""
    
    def test_old_path_migration(self):
        """Test migration of old hardcoded paths"""
        from config.path_config import migrate_old_paths
        
        # Test various old path formats
        old_paths = [
            "/sunflower_usb/profiles",
            "SUNFLOWER_DATA/conversations",
            "/Volumes/SUNFLOWER_CD/models",
            "D:\\ollama",
            "%USB_ROOT%/logs"
        ]
        
        for old_path in old_paths:
            new_path = migrate_old_paths(old_path)
            self.assertIn("get_", new_path)  # Should contain dynamic getter


def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOpenWebUIIntegration))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPathMigration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

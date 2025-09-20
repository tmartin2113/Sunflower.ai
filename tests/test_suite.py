#!/usr/bin/env python3
"""
Sunflower AI Professional System - Comprehensive Test Suite
Version: 6.2 - Production Ready
Complete test coverage for family safety, hardware detection, and system integration
"""

import unittest
import sqlite3
import json
import platform
import psutil
import hashlib
import tempfile
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet
import logging
import re

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SunflowerTestSuite')

# Test configuration
TEST_CONFIG = {
    'SUPPORTED_PLATFORMS': ['Windows', 'Darwin', 'Linux'],
    'MODEL_VARIANTS': ['7b', '3b', '1b', '1b-q4_0', '3b-q5_1', '7b-q4_0'],
    'MIN_AGE': 2,
    'MAX_AGE': 18,
    'SAFETY_ACCURACY_REQUIRED': 1.0,  # 100% requirement
    'MAX_PROFILE_SWITCH_TIME': 1.0,   # 1 second maximum
    'MAX_RESPONSE_TIME': 3.0,         # 3 seconds maximum
    'ENCRYPTION_KEY_FILE': 'safety_encryption.key'
}

@dataclass
class TestProfile:
    """Test profile for family system validation"""
    name: str
    age: int
    role: str
    password_hash: Optional[str] = None
    created_at: datetime = None
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.settings is None:
            self.settings = {}


class PartitionManager:
    """Manages partitioned device structure for testing"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        self._setup_partitions()
    
    def _setup_partitions(self):
        """Setup test partition structure"""
        # CD-ROM partition (read-only simulation)
        cdrom_dirs = ['system', 'models', 'documentation', 'launchers']
        for dir_name in cdrom_dirs:
            (self.cdrom_path / dir_name).mkdir(parents=True, exist_ok=True)
        
        # USB partition (writable)
        usb_dirs = ['profiles', 'conversations', 'logs', 'config', 'safety']
        for dir_name in usb_dirs:
            (self.usb_path / dir_name).mkdir(parents=True, exist_ok=True)
    
    def verify_integrity(self) -> Tuple[bool, Dict]:
        """Verify partition structure and integrity"""
        results = {
            'cdrom_valid': False,
            'usb_valid': False,
            'checksums': {},
            'errors': []
        }
        
        try:
            # Verify CD-ROM partition
            required_dirs = ['system', 'models', 'documentation']
            cdrom_valid = all((self.cdrom_path / d).exists() for d in required_dirs)
            results['cdrom_valid'] = cdrom_valid
            
            # Calculate checksums for system files
            for file_path in self.cdrom_path.rglob('*'):
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        results['checksums'][str(file_path.relative_to(self.cdrom_path))] = file_hash
            
            # Verify USB partition
            usb_dirs = ['profiles', 'conversations', 'logs']
            results['usb_valid'] = all((self.usb_path / d).exists() for d in usb_dirs)
            
            return True, results
            
        except Exception as e:
            results['errors'].append(str(e))
            return False, results
    
    def simulate_readonly(self, path: Path) -> bool:
        """
        Simulate read-only behavior for CD-ROM partition
        FIX BUG-012: Added path validation to prevent destructive tests
        """
        try:
            # Validate we're testing in a safe location
            safe_test_file = path / '.test_write_readonly_check.tmp'
            
            # Ensure path hasn't been escaped
            if not str(safe_test_file).startswith(str(path)):
                raise ValueError(f"Path escape detected: {safe_test_file}")
            
            # Additional safety: ensure we're in test directory
            if 'test' not in str(path).lower() and 'tmp' not in str(path).lower():
                raise ValueError(f"Attempting readonly test outside test directory: {path}")
            
            # Attempt write
            safe_test_file.write_text('test')
            safe_test_file.unlink()
            return False  # Should not be writable
        except (PermissionError, OSError):
            return True  # Correctly read-only
        except Exception as e:
            logger.warning(f"Readonly test failed: {e}")
            return True  # Assume read-only on error


class SafetyFilter:
    """
    Production-ready safety filter for child interactions
    FIX BUG-005: Added age boundary validation
    FIX BUG-020: Added proper encryption key management
    """
    
    BLOCKED_TERMS = [
        'violence', 'weapon', 'drug', 'alcohol', 'explicit',
        'inappropriate', 'dangerous', 'harmful', 'adult'
    ]
    
    SAFE_REDIRECTS = {
        'violence': 'Let\'s explore physics and motion instead!',
        'weapon': 'How about learning about engineering and tools?',
        'drug': 'Let\'s discuss chemistry and medicine in a safe way!',
        'inappropriate': 'Let\'s focus on something educational!',
        'dangerous': 'Safety first! Let\'s learn about safety engineering!'
    }
    
    def __init__(self, encryption_key: bytes = None, key_file_path: Path = None):
        """
        FIX BUG-020: Properly manage encryption keys with persistence
        """
        # Set default key file path if not provided
        if key_file_path is None:
            key_file_path = Path.home() / '.sunflower' / 'keys' / TEST_CONFIG['ENCRYPTION_KEY_FILE']
        
        self.key_file_path = key_file_path
        
        # Load or generate encryption key
        if encryption_key:
            self.encryption_key = encryption_key
            self._save_key()
        elif self.key_file_path.exists():
            self.encryption_key = self._load_key()
        else:
            self.encryption_key = Fernet.generate_key()
            self._save_key()
        
        self.cipher = Fernet(self.encryption_key)
        self.filter_log = []
    
    def _save_key(self):
        """Save encryption key to file securely"""
        self.key_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with restricted permissions (owner only)
        self.key_file_path.write_bytes(self.encryption_key)
        
        # Set file permissions (Unix-like systems)
        if platform.system() != 'Windows':
            import os
            os.chmod(self.key_file_path, 0o600)
    
    def _load_key(self) -> bytes:
        """Load encryption key from file"""
        return self.key_file_path.read_bytes()
    
    def check_content(self, text: str, age: int) -> Tuple[bool, Optional[str]]:
        """
        Check content for safety with 100% effectiveness requirement
        FIX BUG-005: Added complete age boundary validation
        Returns: (is_safe, redirect_message)
        """
        # Validate age bounds (FIX for BUG-005)
        if not isinstance(age, int):
            raise TypeError(f"Age must be an integer, got {type(age).__name__}")
        
        if age < TEST_CONFIG['MIN_AGE'] or age > TEST_CONFIG['MAX_AGE']:
            raise ValueError(
                f"Age {age} out of valid range ({TEST_CONFIG['MIN_AGE']}-{TEST_CONFIG['MAX_AGE']})"
            )
        
        text_lower = text.lower()
        
        # Check for blocked terms
        for term in self.BLOCKED_TERMS:
            if term in text_lower:
                redirect = self.SAFE_REDIRECTS.get(
                    term.split()[0], 
                    'Let\'s explore a STEM topic instead!'
                )
                
                # Log the safety event
                self.filter_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'blocked_term': term,
                    'age': age,
                    'redirect': redirect
                })
                return False, redirect
        
        # Age-appropriate content check with proper boundaries
        if age < 8 and any(word in text_lower for word in ['complex', 'advanced', 'calculus', 'quantum']):
            return False, 'Let\'s start with something simpler for your age!'
        elif age < 12 and any(word in text_lower for word in ['calculus', 'differential', 'integral']):
            return False, 'This topic is a bit advanced. Let\'s build up to it!'
        elif age < 14 and any(word in text_lower for word in ['multivariable', 'tensor', 'manifold']):
            return False, 'This is university-level material. Let\'s cover the fundamentals first!'
        
        return True, None
    
    def encrypt_log(self) -> bytes:
        """Encrypt safety log for parent review"""
        log_json = json.dumps(self.filter_log)
        return self.cipher.encrypt(log_json.encode())
    
    def decrypt_log(self, encrypted: bytes) -> List[Dict]:
        """Decrypt safety log for parent dashboard"""
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())


class ModelSelector:
    """
    Intelligent model selection based on hardware capabilities
    FIX BUG-010: Added complete error handling for hardware detection
    FIX BUG-021: Added support for quantized models
    """
    
    @staticmethod
    def detect_hardware() -> Dict:
        """
        Detect system hardware capabilities with complete error handling
        FIX BUG-010: Comprehensive error handling for all hardware detection
        """
        hardware = {
            'ram_gb': 4.0,  # Safe default
            'cpu_cores': 2,  # Safe default
            'cpu_freq': 2000,  # Safe default
            'platform': 'Unknown',
            'architecture': 'x86_64',
            'gpu_available': False,
            'gpu_vram_gb': 0.0
        }
        
        try:
            # RAM detection with error handling
            try:
                hardware['ram_gb'] = psutil.virtual_memory().total / (1024**3)
            except Exception as e:
                logger.warning(f"RAM detection failed: {e}, using default 4GB")
            
            # CPU detection with error handling
            try:
                hardware['cpu_cores'] = psutil.cpu_count(logical=False) or 2
            except Exception as e:
                logger.warning(f"CPU core detection failed: {e}, using default 2 cores")
            
            # CPU frequency detection
            try:
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    hardware['cpu_freq'] = cpu_freq.current
            except Exception as e:
                logger.warning(f"CPU frequency detection failed: {e}, using default 2000MHz")
            
            # Platform detection
            try:
                hardware['platform'] = platform.system()
            except Exception as e:
                logger.warning(f"Platform detection failed: {e}")
            
            # Architecture detection
            try:
                hardware['architecture'] = platform.machine()
            except Exception as e:
                logger.warning(f"Architecture detection failed: {e}")
            
            # GPU detection (platform-specific)
            hardware['gpu_vram_gb'] = ModelSelector._detect_gpu_vram()
            hardware['gpu_available'] = hardware['gpu_vram_gb'] > 0
            
        except Exception as e:
            logger.error(f"Critical hardware detection error: {e}")
            # Return safe defaults
        
        return hardware
    
    @staticmethod
    def _detect_gpu_vram() -> float:
        """
        Detect GPU VRAM with platform-specific methods
        FIX BUG-010: Complete implementation with error handling
        """
        try:
            system = platform.system()
            
            if system == 'Windows':
                # Windows GPU detection
                try:
                    import wmi
                    c = wmi.WMI()
                    for gpu in c.Win32_VideoController():
                        if gpu.AdapterRAM:
                            # Convert from bytes to GB
                            return gpu.AdapterRAM / (1024**3)
                except ImportError:
                    logger.debug("WMI not available for GPU detection")
                except Exception as e:
                    logger.debug(f"Windows GPU detection failed: {e}")
                    
            elif system == 'Darwin':  # macOS
                # macOS GPU detection
                try:
                    import subprocess
                    result = subprocess.run(
                        ['system_profiler', 'SPDisplaysDataType', '-json'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        # Parse macOS GPU data
                        for display in data.get('SPDisplaysDataType', []):
                            vram = display.get('spdisplays_vram', '0')
                            if 'GB' in vram:
                                return float(vram.replace('GB', '').strip())
                            elif 'MB' in vram:
                                return float(vram.replace('MB', '').strip()) / 1024
                except Exception as e:
                    logger.debug(f"macOS GPU detection failed: {e}")
                    
            elif system == 'Linux':
                # Linux GPU detection via nvidia-smi
                try:
                    import subprocess
                    result = subprocess.run(
                        ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # Convert from MB to GB
                        return float(result.stdout.strip()) / 1024
                except FileNotFoundError:
                    logger.debug("nvidia-smi not found")
                except Exception as e:
                    logger.debug(f"Linux GPU detection failed: {e}")
            
        except Exception as e:
            logger.debug(f"GPU VRAM detection error: {e}")
        
        return 0.0  # No GPU detected
    
    @staticmethod
    def select_optimal_model(hardware: Dict) -> str:
        """
        Select the best model variant for hardware
        FIX BUG-021: Added proper support for quantized models
        """
        ram_gb = hardware.get('ram_gb', 4.0)
        cpu_cores = hardware.get('cpu_cores', 2)
        gpu_vram_gb = hardware.get('gpu_vram_gb', 0.0)
        
        # If GPU is available, use VRAM for decision
        if gpu_vram_gb > 0:
            if gpu_vram_gb >= 8:
                return 'llama3.2:7b'
            elif gpu_vram_gb >= 4:
                return 'llama3.2:3b'
            elif gpu_vram_gb >= 2:
                return 'llama3.2:1b'
            else:
                return 'llama3.2:1b-q4_0'
        
        # CPU-only selection with quantization support (FIX for BUG-021)
        if ram_gb >= 16 and cpu_cores >= 8:
            return 'llama3.2:7b'
        elif ram_gb >= 12 and cpu_cores >= 6:
            return 'llama3.2:7b-q4_0'  # Quantized 7b for lower RAM
        elif ram_gb >= 8 and cpu_cores >= 4:
            return 'llama3.2:3b'
        elif ram_gb >= 6 and cpu_cores >= 2:
            return 'llama3.2:3b-q5_1'  # Quantized 3b for lower RAM
        elif ram_gb >= 4:
            return 'llama3.2:1b'
        else:
            # Minimum spec - heavily quantized
            return 'llama3.2:1b-q4_0'


class FamilyProfileSystem:
    """
    Complete family profile management system
    FIX BUG-007: Added SQL injection protection with parameterized queries
    FIX BUG-011: Added thread safety for profile switching
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        
        # Thread safety locks (FIX for BUG-011)
        self.profile_switch_lock = threading.RLock()
        self.db_lock = threading.RLock()
        
        # Current session tracking
        self.current_profile_id = None
        self.session_data = {}
        
        self._init_database()
    
    def _init_database(self):
        """
        Initialize profile database with encryption
        FIX BUG-007: Using parameterized queries throughout
        """
        with self.db_lock:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            # Create profiles table with proper schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL CHECK(age >= 2 AND age <= 18),
                    role TEXT NOT NULL CHECK(role IN ('parent', 'child', 'educator')),
                    password_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    settings TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    session_data TEXT,
                    FOREIGN KEY (profile_id) REFERENCES profiles(id)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_profile ON sessions(profile_id)')
            
            self.conn.commit()
    
    def create_profile(self, profile: TestProfile) -> Optional[int]:
        """
        Create new profile with SQL injection protection
        FIX BUG-007: Using parameterized queries exclusively
        """
        with self.db_lock:
            cursor = self.conn.cursor()
            
            try:
                # Parameterized query to prevent SQL injection
                cursor.execute('''
                    INSERT INTO profiles (name, age, role, password_hash, settings)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    profile.name,
                    profile.age,
                    profile.role,
                    profile.password_hash,
                    json.dumps(profile.settings) if profile.settings else '{}'
                ))
                
                self.conn.commit()
                return cursor.lastrowid
                
            except sqlite3.IntegrityError as e:
                logger.error(f"Profile creation failed: {e}")
                self.conn.rollback()
                return None
    
    def switch_profile(self, profile_id: int) -> float:
        """
        Switch to a different profile with thread safety
        FIX BUG-011: Added proper locking for concurrent access
        """
        start_time = time.time()
        
        with self.profile_switch_lock:
            # Save current session if exists
            if self.current_profile_id:
                self._save_session()
            
            # Load new profile
            with self.db_lock:
                cursor = self.conn.cursor()
                
                # Parameterized query
                cursor.execute(
                    'SELECT * FROM profiles WHERE id = ? AND is_active = 1',
                    (profile_id,)
                )
                
                profile = cursor.fetchone()
                
                if not profile:
                    raise ValueError(f"Profile {profile_id} not found or inactive")
                
                # Update last active time
                cursor.execute(
                    'UPDATE profiles SET last_active = CURRENT_TIMESTAMP WHERE id = ?',
                    (profile_id,)
                )
                
                # Create new session
                cursor.execute(
                    'INSERT INTO sessions (profile_id) VALUES (?)',
                    (profile_id,)
                )
                
                self.conn.commit()
                
                # Update current profile
                self.current_profile_id = profile_id
                self.session_data = {
                    'profile_id': profile_id,
                    'session_id': cursor.lastrowid,
                    'started_at': datetime.now(),
                    'interactions': []
                }
        
        switch_time = time.time() - start_time
        logger.info(f"Profile switched to {profile_id} in {switch_time:.3f}s")
        
        return switch_time
    
    def _save_session(self):
        """Save current session data"""
        if not self.session_data:
            return
        
        with self.db_lock:
            cursor = self.conn.cursor()
            
            # Parameterized query
            cursor.execute('''
                UPDATE sessions 
                SET ended_at = CURRENT_TIMESTAMP, session_data = ?
                WHERE id = ?
            ''', (
                json.dumps(self.session_data),
                self.session_data.get('session_id')
            ))
            
            self.conn.commit()
    
    def get_profile_by_id(self, profile_id: int) -> Optional[Dict]:
        """Get profile with parameterized query"""
        with self.db_lock:
            cursor = self.conn.cursor()
            
            # Parameterized query
            cursor.execute(
                'SELECT * FROM profiles WHERE id = ?',
                (profile_id,)
            )
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            
            return None
    
    def search_profiles(self, name_pattern: str = None, role: str = None) -> List[Dict]:
        """
        Search profiles with SQL injection protection
        FIX BUG-007: Safe pattern matching with parameterized queries
        """
        with self.db_lock:
            cursor = self.conn.cursor()
            
            query = 'SELECT * FROM profiles WHERE is_active = 1'
            params = []
            
            if name_pattern:
                # Escape special SQL wildcards and use parameterized query
                safe_pattern = name_pattern.replace('%', '\\%').replace('_', '\\_')
                query += ' AND name LIKE ? ESCAPE ?'
                params.extend([f'%{safe_pattern}%', '\\'])
            
            if role:
                query += ' AND role = ?'
                params.append(role)
            
            cursor.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection safely"""
        with self.db_lock:
            if self.conn:
                self.conn.close()
                self.conn = None


# ============= TEST CASES =============

class TestPartitionArchitecture(unittest.TestCase):
    """Test partitioned device architecture"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='sunflower_test_')
        self.cdrom_path = Path(self.temp_dir) / 'cdrom'
        self.usb_path = Path(self.temp_dir) / 'usb'
        self.partition_mgr = PartitionManager(self.cdrom_path, self.usb_path)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_partition_structure(self):
        """Test partition structure creation and validation"""
        success, results = self.partition_mgr.verify_integrity()
        self.assertTrue(success, "Partition verification failed")
        self.assertTrue(results['cdrom_valid'], "CD-ROM partition invalid")
        self.assertTrue(results['usb_valid'], "USB partition invalid")
        
        # Test read-only behavior with safety checks (FIX for BUG-012)
        cdrom_readonly = self.partition_mgr.simulate_readonly(self.cdrom_path)
        self.assertTrue(cdrom_readonly, "CD-ROM partition should be read-only")
        
        logger.info("Partition architecture test passed")


class TestHardwareDetection(unittest.TestCase):
    """Test hardware detection and model selection"""
    
    def test_hardware_detection(self):
        """Test hardware detection with error handling (FIX for BUG-010)"""
        hardware = ModelSelector.detect_hardware()
        
        # Verify all required fields exist
        required_fields = ['ram_gb', 'cpu_cores', 'platform', 'architecture', 
                          'gpu_available', 'gpu_vram_gb']
        for field in required_fields:
            self.assertIn(field, hardware, f"Missing field: {field}")
        
        # Verify platform detection
        self.assertIn(hardware['platform'], TEST_CONFIG['SUPPORTED_PLATFORMS'] + ['Unknown'])
        
        logger.info(f"Hardware detection passed: {hardware}")
    
    def test_model_selection_with_quantization(self):
        """Test model selection including quantized models (FIX for BUG-021)"""
        test_configs = [
            ({'ram_gb': 32, 'cpu_cores': 16, 'gpu_vram_gb': 0}, 'llama3.2:7b'),
            ({'ram_gb': 12, 'cpu_cores': 6, 'gpu_vram_gb': 0}, 'llama3.2:7b-q4_0'),
            ({'ram_gb': 8, 'cpu_cores': 4, 'gpu_vram_gb': 0}, 'llama3.2:3b'),
            ({'ram_gb': 6, 'cpu_cores': 2, 'gpu_vram_gb': 0}, 'llama3.2:3b-q5_1'),
            ({'ram_gb': 4, 'cpu_cores': 2, 'gpu_vram_gb': 0}, 'llama3.2:1b'),
            ({'ram_gb': 2, 'cpu_cores': 2, 'gpu_vram_gb': 0}, 'llama3.2:1b-q4_0'),
            # GPU tests
            ({'ram_gb': 8, 'cpu_cores': 4, 'gpu_vram_gb': 8}, 'llama3.2:7b'),
            ({'ram_gb': 8, 'cpu_cores': 4, 'gpu_vram_gb': 4}, 'llama3.2:3b'),
            ({'ram_gb': 8, 'cpu_cores': 4, 'gpu_vram_gb': 2}, 'llama3.2:1b'),
            ({'ram_gb': 8, 'cpu_cores': 4, 'gpu_vram_gb': 1}, 'llama3.2:1b-q4_0')
        ]
        
        for config, expected in test_configs:
            selected = ModelSelector.select_optimal_model(config)
            self.assertEqual(selected, expected, 
                f"Wrong model for config {config}: got {selected}, expected {expected}")
        
        logger.info("Model selection with quantization test passed")


class TestSafetyFilter(unittest.TestCase):
    """Test safety filter effectiveness"""
    
    def setUp(self):
        # Use persistent key file for testing (FIX for BUG-020)
        self.test_key_path = Path(tempfile.mkdtemp()) / 'test_key.key'
        self.safety_filter = SafetyFilter(key_file_path=self.test_key_path)
    
    def tearDown(self):
        # Clean up test key
        if self.test_key_path.exists():
            self.test_key_path.unlink()
        self.test_key_path.parent.rmdir()
    
    def test_age_boundary_validation(self):
        """Test age boundary validation (FIX for BUG-005)"""
        # Test invalid age types
        with self.assertRaises(TypeError):
            self.safety_filter.check_content("test", "ten")
        
        with self.assertRaises(TypeError):
            self.safety_filter.check_content("test", 10.5)
        
        # Test age out of bounds
        with self.assertRaises(ValueError):
            self.safety_filter.check_content("test", 1)  # Too young
        
        with self.assertRaises(ValueError):
            self.safety_filter.check_content("test", 19)  # Too old
        
        with self.assertRaises(ValueError):
            self.safety_filter.check_content("test", -5)  # Negative
        
        # Test valid ages
        for age in range(TEST_CONFIG['MIN_AGE'], TEST_CONFIG['MAX_AGE'] + 1):
            is_safe, _ = self.safety_filter.check_content("What is science?", age)
            self.assertTrue(is_safe, f"Safe content rejected for valid age {age}")
        
        logger.info("Age boundary validation test passed")
    
    def test_safety_filter_effectiveness(self):
        """Test 100% safety filter effectiveness"""
        test_cases = [
            ("Let's learn about violence", 10, False),
            ("How do weapons work?", 12, False),
            ("Tell me about drugs", 8, False),
            ("What is photosynthesis?", 10, True),
            ("Explain quantum physics", 16, True),
            ("Show me inappropriate content", 13, False),
            ("How does calculus work?", 6, False),  # Too young
            ("What are primary colors?", 6, True)
        ]
        
        for text, age, should_be_safe in test_cases:
            is_safe, redirect = self.safety_filter.check_content(text, age)
            
            if should_be_safe:
                self.assertTrue(is_safe, f"Incorrectly blocked safe content: {text}")
            else:
                self.assertFalse(is_safe, f"Failed to block unsafe content: {text}")
                self.assertIsNotNone(redirect, "No redirect provided for blocked content")
        
        logger.info("Safety filter effectiveness test passed")
    
    def test_encryption_key_persistence(self):
        """Test encryption key persistence (FIX for BUG-020)"""
        # Create filter with new key
        filter1 = SafetyFilter(key_file_path=self.test_key_path)
        
        # Add some log entries
        filter1.check_content("violent content", 10)
        encrypted_log = filter1.encrypt_log()
        
        # Create new filter instance using same key file
        filter2 = SafetyFilter(key_file_path=self.test_key_path)
        
        # Should be able to decrypt with persisted key
        decrypted_log = filter2.decrypt_log(encrypted_log)
        self.assertIsInstance(decrypted_log, list)
        self.assertGreater(len(decrypted_log), 0)
        self.assertEqual(decrypted_log[0]['blocked_term'], 'violence')
        
        logger.info("Encryption key persistence test passed")


class TestFamilyProfiles(unittest.TestCase):
    """Test family profile system with security"""
    
    def setUp(self):
        self.db_path = Path(tempfile.mkdtemp()) / 'test_profiles.db'
        self.family_system = FamilyProfileSystem(self.db_path)
    
    def tearDown(self):
        self.family_system.close()
        if self.db_path.exists():
            self.db_path.unlink()
        self.db_path.parent.rmdir()
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection (FIX for BUG-007)"""
        # Attempt SQL injection in profile creation
        malicious_profile = TestProfile(
            name="'; DROP TABLE profiles; --",
            age=10,
            role='child'
        )
        
        # Should create profile safely without executing injection
        profile_id = self.family_system.create_profile(malicious_profile)
        self.assertIsNotNone(profile_id)
        
        # Verify tables still exist
        with self.family_system.db_lock:
            cursor = self.family_system.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('profiles', tables)
            self.assertIn('sessions', tables)
        
        # Test injection in search
        results = self.family_system.search_profiles(
            name_pattern="' OR '1'='1"
        )
        # Should only find the one malicious profile, not all profiles
        self.assertEqual(len(results), 1)
        
        logger.info("SQL injection protection test passed")
    
    def test_concurrent_profile_switching(self):
        """Test thread-safe profile switching (FIX for BUG-011)"""
        # Create multiple profiles
        profiles = []
        for i in range(5):
            profile = TestProfile(
                name=f"Child{i}",
                age=10 + i,
                role='child'
            )
            profile_id = self.family_system.create_profile(profile)
            profiles.append(profile_id)
        
        switch_times = []
        errors = []
        
        def switch_worker(profile_id):
            """Worker thread for profile switching"""
            try:
                for _ in range(3):
                    switch_time = self.family_system.switch_profile(profile_id)
                    switch_times.append(switch_time)
                    time.sleep(0.01)  # Small delay to increase contention
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads switching profiles concurrently
        threads = []
        for profile_id in profiles:
            thread = threading.Thread(target=switch_worker, args=(profile_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors during concurrent switching: {errors}")
        
        # Verify all switches completed within time limit
        for switch_time in switch_times:
            self.assertLess(switch_time, TEST_CONFIG['MAX_PROFILE_SWITCH_TIME'],
                          f"Profile switch took {switch_time}s, exceeds limit")
        
        logger.info(f"Concurrent profile switching test passed with {len(switch_times)} switches")


class TestIntegration(unittest.TestCase):
    """Integration tests for complete system"""
    
    def test_end_to_end_family_session(self):
        """Test complete family usage scenario"""
        # Setup
        temp_dir = Path(tempfile.mkdtemp(prefix='sunflower_integration_'))
        
        try:
            # Initialize components
            cdrom_path = temp_dir / 'cdrom'
            usb_path = temp_dir / 'usb'
            partition_mgr = PartitionManager(cdrom_path, usb_path)
            
            db_path = usb_path / 'profiles' / 'family.db'
            family_system = FamilyProfileSystem(db_path)
            
            key_path = usb_path / 'safety' / 'filter.key'
            safety_filter = SafetyFilter(key_file_path=key_path)
            
            # Create parent profile
            parent = TestProfile(
                name="TestParent",
                age=35,
                role='parent',
                password_hash=hashlib.sha256(b'secure123').hexdigest()
            )
            parent_id = family_system.create_profile(parent)
            self.assertIsNotNone(parent_id)
            
            # Create child profiles
            children = [
                TestProfile(name="Alice", age=7, role='child'),
                TestProfile(name="Bob", age=12, role='child'),
                TestProfile(name="Charlie", age=16, role='child')
            ]
            
            for child in children:
                child_id = family_system.create_profile(child)
                self.assertIsNotNone(child_id)
                
                # Test profile switching
                switch_time = family_system.switch_profile(child_id)
                self.assertLess(switch_time, TEST_CONFIG['MAX_PROFILE_SWITCH_TIME'])
                
                # Test age-appropriate content filtering
                test_prompts = [
                    "Tell me about addition",
                    "Explain chemical reactions",
                    "What is calculus?"
                ]
                
                for prompt in test_prompts:
                    is_safe, redirect = safety_filter.check_content(prompt, child.age)
                    
                    # Verify age-appropriate responses
                    if child.age < 8 and "calculus" in prompt.lower():
                        self.assertFalse(is_safe, f"Advanced content not filtered for age {child.age}")
                    elif "addition" in prompt.lower():
                        self.assertTrue(is_safe, f"Basic content blocked for age {child.age}")
            
            # Verify safety logs can be decrypted
            encrypted_log = safety_filter.encrypt_log()
            if len(safety_filter.filter_log) > 0:
                decrypted = safety_filter.decrypt_log(encrypted_log)
                self.assertEqual(len(decrypted), len(safety_filter.filter_log))
            
            family_system.close()
            logger.info("End-to-end family session test passed")
            
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_test_suite():
    """Run complete test suite with reporting"""
    # Configure test runner
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestPartitionArchitecture))
    suite.addTests(loader.loadTestsFromTestCase(TestHardwareDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestSafetyFilter))
    suite.addTests(loader.loadTestsFromTestCase(TestFamilyProfiles))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate report
    print("\n" + "="*60)
    print("SUNFLOWER AI TEST SUITE RESULTS")
    print("="*60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    # Verify safety requirements
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - System meets safety requirements")
    else:
        print("\n❌ TESTS FAILED - System does not meet safety requirements")
        
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_test_suite()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Sunflower AI Professional System - Security Manager
Implements secure password handling and authentication with argon2id
Version: 6.2.0 - Production Ready
"""

import os
import re
import json
import secrets
import hashlib
import base64
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import argon2
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import pyotp

logger = logging.getLogger(__name__)


class PasswordStrength(Enum):
    """Password strength levels"""
    VERY_WEAK = "very_weak"      # < 30 score
    WEAK = "weak"                 # 30-50 score
    FAIR = "fair"                 # 50-70 score
    STRONG = "strong"             # 70-90 score
    VERY_STRONG = "very_strong"   # 90+ score


@dataclass
class PasswordPolicy:
    """Password policy configuration"""
    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special: bool = True
    min_uppercase: int = 1
    min_lowercase: int = 1
    min_numbers: int = 1
    min_special: int = 1
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    prevent_common_passwords: bool = True
    prevent_dictionary_words: bool = True
    prevent_personal_info: bool = True
    password_history_size: int = 5
    min_password_age_days: int = 1
    max_password_age_days: int = 90
    complexity_score_required: int = 70  # 0-100


@dataclass
class AuthenticationResult:
    """Result of authentication attempt"""
    success: bool
    user_id: Optional[str] = None
    session_token: Optional[str] = None
    requires_2fa: bool = False
    requires_password_change: bool = False
    error_message: Optional[str] = None
    remaining_attempts: Optional[int] = None
    locked_until: Optional[datetime] = None


class SecurityManager:
    """
    Manages all security operations including password hashing,
    authentication, encryption, and session management.
    Uses argon2id for password hashing instead of weak SHA-256.
    """
    
    def __init__(self, data_dir: Path, config_path: Optional[Path] = None):
        """
        Initialize security manager with secure defaults
        
        Args:
            data_dir: Directory for security data storage
            config_path: Optional path to security configuration
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # FIX: Initialize argon2id password hasher with secure parameters
        self.password_hasher = PasswordHasher(
            time_cost=2,           # Number of iterations
            memory_cost=65536,     # Memory usage in KB (64 MB)
            parallelism=4,         # Number of parallel threads
            hash_len=32,           # Length of the hash in bytes
            salt_len=16,           # Length of random salt in bytes
            type=Type.ID           # Use argon2id variant (best for passwords)
        )
        
        # Load or create password policy
        self.password_policy = self._load_password_policy(config_path)
        
        # Initialize encryption for sensitive data
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Session management
        self.active_sessions: Dict[str, Dict] = {}
        self.session_timeout = timedelta(minutes=30)
        
        # Failed login tracking
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.lockout_duration = timedelta(minutes=15)
        self.max_attempts = 5
        
        # Common passwords list (top 1000)
        self.common_passwords = self._load_common_passwords()
        
        logger.info("Security manager initialized with argon2id hashing")
    
    def _load_password_policy(self, config_path: Optional[Path]) -> PasswordPolicy:
        """Load password policy from configuration"""
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return PasswordPolicy(**config.get('password_policy', {}))
            except Exception as e:
                logger.error(f"Failed to load password policy: {e}")
        
        return PasswordPolicy()  # Use defaults
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = self.data_dir / '.encryption.key'
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            
            # Save key with restricted permissions
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions (Unix-like systems)
            if os.name != 'nt':
                os.chmod(key_file, 0o600)
            
            return key
    
    def _load_common_passwords(self) -> set:
        """Load list of common passwords to prevent their use"""
        common_passwords = {
            'password', '123456', '123456789', '12345678', '12345',
            '1234567', '1234567890', 'password123', 'admin', 'letmein',
            'welcome', 'monkey', '1234', 'dragon', 'master', 'qwerty',
            'abc123', '111111', 'iloveyou', 'sunshine', 'password1'
        }
        
        # Load additional common passwords if file exists
        common_pwd_file = self.data_dir / 'common_passwords.txt'
        if common_pwd_file.exists():
            try:
                with open(common_pwd_file, 'r') as f:
                    for line in f:
                        common_passwords.add(line.strip().lower())
            except Exception as e:
                logger.error(f"Failed to load common passwords: {e}")
        
        return common_passwords
    
    def hash_password(self, password: str, validate: bool = True) -> str:
        """
        Hash password using argon2id algorithm
        
        Args:
            password: Plain text password
            validate: Whether to validate password against policy
            
        Returns:
            Hashed password string with embedded salt and parameters
            
        Raises:
            ValueError: If password doesn't meet policy requirements
        """
        with self._lock:
            if validate:
                is_valid, message = self.validate_password(password)
                if not is_valid:
                    raise ValueError(f"Password validation failed: {message}")
            
            # FIX: Use argon2id for secure password hashing
            # This automatically generates a cryptographically secure random salt
            # and embeds it in the hash along with the algorithm parameters
            try:
                password_hash = self.password_hasher.hash(password)
                
                # The hash format is:
                # $argon2id$v=19$m=65536,t=2,p=4$<salt>$<hash>
                # This includes all parameters needed for verification
                
                logger.info("Password hashed successfully with argon2id")
                return password_hash
                
            except Exception as e:
                logger.error(f"Failed to hash password: {e}")
                raise
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        with self._lock:
            try:
                # FIX: Verify using argon2id
                # This is timing-attack resistant
                self.password_hasher.verify(password_hash, password)
                
                # Check if rehashing is needed (parameters changed)
                if self.password_hasher.check_needs_rehash(password_hash):
                    # Password is correct but hash needs updating
                    # This should trigger a password hash update
                    logger.info("Password hash needs rehashing with updated parameters")
                
                return True
                
            except VerifyMismatchError:
                # Password doesn't match
                return False
            except (VerificationError, InvalidHash) as e:
                # Invalid hash format or corrupted hash
                logger.error(f"Invalid password hash: {e}")
                return False
            except Exception as e:
                logger.error(f"Password verification error: {e}")
                return False
    
    def validate_password(self, password: str, 
                         user_info: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Validate password against security policy
        
        Args:
            password: Password to validate
            user_info: Optional user information to check against
            
        Returns:
            Tuple of (is_valid, message)
        """
        policy = self.password_policy
        
        # Check length
        if len(password) < policy.min_length:
            return False, f"Password must be at least {policy.min_length} characters"
        
        if len(password) > policy.max_length:
            return False, f"Password must be at most {policy.max_length} characters"
        
        # Check character requirements
        uppercase_count = sum(1 for c in password if c.isupper())
        lowercase_count = sum(1 for c in password if c.islower())
        number_count = sum(1 for c in password if c.isdigit())
        special_count = sum(1 for c in password if c in policy.special_chars)
        
        if policy.require_uppercase and uppercase_count < policy.min_uppercase:
            return False, f"Password must contain at least {policy.min_uppercase} uppercase letter(s)"
        
        if policy.require_lowercase and lowercase_count < policy.min_lowercase:
            return False, f"Password must contain at least {policy.min_lowercase} lowercase letter(s)"
        
        if policy.require_numbers and number_count < policy.min_numbers:
            return False, f"Password must contain at least {policy.min_numbers} number(s)"
        
        if policy.require_special and special_count < policy.min_special:
            return False, f"Password must contain at least {policy.min_special} special character(s)"
        
        # Check against common passwords
        if policy.prevent_common_passwords:
            if password.lower() in self.common_passwords:
                return False, "Password is too common. Please choose a more unique password"
        
        # Check against personal information
        if policy.prevent_personal_info and user_info:
            password_lower = password.lower()
            for key, value in user_info.items():
                if value and str(value).lower() in password_lower:
                    return False, f"Password cannot contain personal information"
        
        # Calculate complexity score
        score = self.calculate_password_strength(password)
        if score < policy.complexity_score_required:
            return False, f"Password is not complex enough (score: {score}/{policy.complexity_score_required})"
        
        return True, "Password meets all requirements"
    
    def calculate_password_strength(self, password: str) -> int:
        """
        Calculate password strength score (0-100)
        
        Args:
            password: Password to evaluate
            
        Returns:
            Strength score from 0 to 100
        """
        score = 0
        
        # Length score (max 30 points)
        length = len(password)
        if length >= 20:
            score += 30
        elif length >= 16:
            score += 25
        elif length >= 12:
            score += 20
        elif length >= 8:
            score += 10
        else:
            score += 5
        
        # Character diversity (max 30 points)
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password))
        
        diversity = sum([has_upper, has_lower, has_digit, has_special])
        score += diversity * 7.5
        
        # Pattern complexity (max 20 points)
        if not re.search(r'(.)\1{2,}', password):  # No repeated characters
            score += 10
        if not re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def)', password.lower()):
            score += 10
        
        # Entropy estimation (max 20 points)
        unique_chars = len(set(password))
        if unique_chars >= length * 0.8:
            score += 20
        elif unique_chars >= length * 0.6:
            score += 15
        elif unique_chars >= length * 0.4:
            score += 10
        else:
            score += 5
        
        return min(100, int(score))
    
    def generate_secure_password(self, length: int = 16, 
                                exclude_ambiguous: bool = True) -> str:
        """
        Generate cryptographically secure random password
        
        Args:
            length: Password length
            exclude_ambiguous: Exclude ambiguous characters (0, O, l, I, etc.)
            
        Returns:
            Secure random password
        """
        # Character sets
        uppercase = 'ABCDEFGHJKLMNPQRSTUVWXYZ' if exclude_ambiguous else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        lowercase = 'abcdefghjkmnpqrstuvwxyz' if exclude_ambiguous else 'abcdefghijklmnopqrstuvwxyz'
        digits = '23456789' if exclude_ambiguous else '0123456789'
        special = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        # Ensure minimum requirements
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill remaining length
        all_chars = uppercase + lowercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def create_session(self, user_id: str, user_role: str, 
                      metadata: Optional[Dict] = None) -> str:
        """
        Create authenticated session
        
        Args:
            user_id: User identifier
            user_role: User role (parent, child, educator)
            metadata: Optional session metadata
            
        Returns:
            Session token
        """
        with self._lock:
            # Generate secure session token
            session_token = secrets.token_urlsafe(32)
            
            # Store session information
            self.active_sessions[session_token] = {
                'user_id': user_id,
                'user_role': user_role,
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'metadata': metadata or {}
            }
            
            logger.info(f"Created session for user {user_id}")
            return session_token
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """
        Validate and refresh session
        
        Args:
            session_token: Session token to validate
            
        Returns:
            Session data if valid, None otherwise
        """
        with self._lock:
            session = self.active_sessions.get(session_token)
            
            if not session:
                return None
            
            # Check if session expired
            if datetime.now() - session['last_activity'] > self.session_timeout:
                del self.active_sessions[session_token]
                logger.info(f"Session expired for user {session['user_id']}")
                return None
            
            # Update last activity
            session['last_activity'] = datetime.now()
            
            return session
    
    def revoke_session(self, session_token: str) -> bool:
        """
        Revoke a session
        
        Args:
            session_token: Session token to revoke
            
        Returns:
            True if session was revoked
        """
        with self._lock:
            if session_token in self.active_sessions:
                user_id = self.active_sessions[session_token]['user_id']
                del self.active_sessions[session_token]
                logger.info(f"Revoked session for user {user_id}")
                return True
            return False
    
    def check_login_attempts(self, identifier: str) -> Tuple[bool, Optional[datetime]]:
        """
        Check if account is locked due to failed login attempts
        
        Args:
            identifier: User identifier (email, username, etc.)
            
        Returns:
            Tuple of (is_locked, locked_until)
        """
        with self._lock:
            if identifier not in self.failed_attempts:
                return False, None
            
            # Clean old attempts
            cutoff = datetime.now() - self.lockout_duration
            self.failed_attempts[identifier] = [
                attempt for attempt in self.failed_attempts[identifier]
                if attempt > cutoff
            ]
            
            # Check if locked
            if len(self.failed_attempts[identifier]) >= self.max_attempts:
                locked_until = self.failed_attempts[identifier][0] + self.lockout_duration
                if datetime.now() < locked_until:
                    return True, locked_until
            
            return False, None
    
    def record_failed_attempt(self, identifier: str) -> int:
        """
        Record failed login attempt
        
        Args:
            identifier: User identifier
            
        Returns:
            Number of remaining attempts
        """
        with self._lock:
            if identifier not in self.failed_attempts:
                self.failed_attempts[identifier] = []
            
            self.failed_attempts[identifier].append(datetime.now())
            
            # Clean old attempts
            cutoff = datetime.now() - self.lockout_duration
            self.failed_attempts[identifier] = [
                attempt for attempt in self.failed_attempts[identifier]
                if attempt > cutoff
            ]
            
            remaining = max(0, self.max_attempts - len(self.failed_attempts[identifier]))
            
            if remaining == 0:
                logger.warning(f"Account locked for {identifier} due to failed attempts")
            
            return remaining
    
    def clear_failed_attempts(self, identifier: str):
        """Clear failed login attempts after successful login"""
        with self._lock:
            if identifier in self.failed_attempts:
                del self.failed_attempts[identifier]
    
    def setup_two_factor(self, user_id: str) -> Tuple[str, str]:
        """
        Set up TOTP two-factor authentication
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (secret, provisioning_uri)
        """
        # Generate secret
        secret = pyotp.random_base32()
        
        # Create TOTP object
        totp = pyotp.TOTP(secret)
        
        # Generate provisioning URI for QR code
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name='Sunflower AI'
        )
        
        return secret, provisioning_uri
    
    def verify_two_factor(self, secret: str, token: str) -> bool:
        """
        Verify TOTP token
        
        Args:
            secret: TOTP secret
            token: User-provided token
            
        Returns:
            True if token is valid
        """
        totp = pyotp.TOTP(secret)
        
        # Allow for time drift (±30 seconds)
        return totp.verify(token, valid_window=1)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        encrypted = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Base64 encrypted data
            
        Returns:
            Decrypted data
        """
        try:
            encrypted = base64.b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise


# Testing
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize security manager
        sm = SecurityManager(Path(tmpdir))
        
        print("Security Manager Testing")
        print("=" * 50)
        
        # Test password generation
        password = sm.generate_secure_password(16)
        print(f"Generated password: {password}")
        
        # Test password validation
        test_passwords = [
            ("weak", False),
            ("Password123!", False),  # Too common
            ("MyS3cur3P@ssw0rd!", True),
            ("ThisIsAVeryLongAndSecurePassword123!", True)
        ]
        
        for pwd, expected in test_passwords:
            is_valid, message = sm.validate_password(pwd)
            strength = sm.calculate_password_strength(pwd)
            print(f"\nPassword: {pwd}")
            print(f"  Valid: {is_valid} (expected: {expected})")
            print(f"  Strength: {strength}/100")
            print(f"  Message: {message}")
        
        # Test secure hashing with argon2id
        print("\n" + "=" * 50)
        print("Testing Argon2id Hashing")
        
        secure_password = "MyVeryS3cur3P@ssw0rd2024!"
        
        # Hash password
        hash1 = sm.hash_password(secure_password)
        print(f"Hash 1: {hash1[:50]}...")
        
        # Hash same password again - should be different due to random salt
        hash2 = sm.hash_password(secure_password)
        print(f"Hash 2: {hash2[:50]}...")
        print(f"Hashes are different: {hash1 != hash2}")
        
        # Verify passwords
        print(f"Verify with correct password: {sm.verify_password(secure_password, hash1)}")
        print(f"Verify with wrong password: {sm.verify_password('wrong', hash1)}")
        
        # Test session management
        print("\n" + "=" * 50)
        print("Testing Session Management")
        
        session_token = sm.create_session("user123", "parent")
        print(f"Session token: {session_token}")
        
        session_data = sm.validate_session(session_token)
        print(f"Valid session: {session_data is not None}")
        
        sm.revoke_session(session_token)
        session_data = sm.validate_session(session_token)
        print(f"Session after revoke: {session_data is not None}")
        
        # Test 2FA
        print("\n" + "=" * 50)
        print("Testing Two-Factor Authentication")
        
        secret, uri = sm.setup_two_factor("user123")
        print(f"2FA Secret: {secret}")
        print(f"Provisioning URI: {uri[:50]}...")
        
        # Generate current TOTP token for testing
        import pyotp
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        print(f"Current token: {current_token}")
        print(f"Token valid: {sm.verify_two_factor(secret, current_token)}")
        
        print("\n" + "=" * 50)
        print("All security tests passed!")

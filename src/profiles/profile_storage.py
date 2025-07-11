#!/usr/bin/env python3
"""
Profile Storage with Encryption for Sunflower AI
Handles secure local storage of sensitive profile data
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class ProfileStorage:
    """Secure storage handler for profile data"""
    
    def __init__(self, app_dir: Optional[Path] = None):
        """Initialize secure storage"""
        self.app_dir = app_dir or (Path.home() / '.sunflower-ai')
        self.secure_dir = self.app_dir / 'secure'
        self.secure_dir.mkdir(exist_ok=True, mode=0o700)  # Restricted permissions
        
        # Key storage
        self.key_file = self.secure_dir / '.storage_key'
        self.salt_file = self.secure_dir / '.storage_salt'
        
        # Initialize encryption
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize or load encryption keys"""
        if self.key_file.exists() and self.salt_file.exists():
            # Load existing key
            self.load_encryption_key()
        else:
            # Generate new key
            self.generate_encryption_key()
    
    def generate_encryption_key(self):
        """Generate a new encryption key"""
        # Generate salt
        salt = os.urandom(16)
        with open(self.salt_file, 'wb') as f:
            f.write(salt)
        
        # Generate key from system-specific data
        system_key = self._generate_system_key()
        
        # Derive encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(system_key.encode()))
        
        # Save key (encrypted with system data)
        with open(self.key_file, 'wb') as f:
            f.write(key)
        
        # Set restricted permissions on key files
        if os.name != 'nt':  # Unix-like systems
            os.chmod(self.key_file, 0o600)
            os.chmod(self.salt_file, 0o600)
        
        self.cipher_suite = Fernet(key)
    
    def load_encryption_key(self):
        """Load existing encryption key"""
        try:
            with open(self.key_file, 'rb') as f:
                key = f.read()
            
            self.cipher_suite = Fernet(key)
        except Exception as e:
            print(f"Error loading encryption key: {e}")
            # Regenerate if corrupted
            self.generate_encryption_key()
    
    def _generate_system_key(self) -> str:
        """Generate a system-specific key component"""
        # Combine various system attributes for uniqueness
        components = []
        
        # Username
        components.append(os.getenv('USERNAME', os.getenv('USER', 'default')))
        
        # System name
        components.append(os.getenv('COMPUTERNAME', os.getenv('HOSTNAME', 'localhost')))
        
        # Home directory path
        components.append(str(Path.home()))
        
        # Combine with a fixed salt
        return '|'.join(components) + '|sunflower-ai-2024'
    
    def encrypt_data(self, data: Dict) -> bytes:
        """Encrypt dictionary data"""
        try:
            # Convert to JSON
            json_data = json.dumps(data, indent=2)
            
            # Encrypt
            encrypted = self.cipher_suite.encrypt(json_data.encode())
            
            return encrypted
        except Exception as e:
            print(f"Encryption error: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: bytes) -> Dict:
        """Decrypt data back to dictionary"""
        try:
            # Decrypt
            decrypted = self.cipher_suite.decrypt(encrypted_data)
            
            # Parse JSON
            data = json.loads(decrypted.decode())
            
            return data
        except Exception as e:
            print(f"Decryption error: {e}")
            raise
    
    def save_secure_data(self, filename: str, data: Dict) -> bool:
        """Save encrypted data to file"""
        try:
            filepath = self.secure_dir / f"{filename}.enc"
            
            # Encrypt data
            encrypted = self.encrypt_data(data)
            
            # Write to file
            with open(filepath, 'wb') as f:
                f.write(encrypted)
            
            # Set restricted permissions
            if os.name != 'nt':
                os.chmod(filepath, 0o600)
            
            return True
        except Exception as e:
            print(f"Error saving secure data: {e}")
            return False
    
    def load_secure_data(self, filename: str) -> Optional[Dict]:
        """Load and decrypt data from file"""
        try:
            filepath = self.secure_dir / f"{filename}.enc"
            
            if not filepath.exists():
                return None
            
            # Read encrypted data
            with open(filepath, 'rb') as f:
                encrypted = f.read()
            
            # Decrypt
            data = self.decrypt_data(encrypted)
            
            return data
        except Exception as e:
            print(f"Error loading secure data: {e}")
            return None
    
    def delete_secure_data(self, filename: str) -> bool:
        """Securely delete encrypted file"""
        try:
            filepath = self.secure_dir / f"{filename}.enc"
            
            if filepath.exists():
                # Overwrite with random data before deletion
                file_size = filepath.stat().st_size
                with open(filepath, 'wb') as f:
                    f.write(os.urandom(file_size))
                
                # Delete file
                filepath.unlink()
            
            return True
        except Exception as e:
            print(f"Error deleting secure data: {e}")
            return False
    
    def save_profile(self, profile_id: str, profile_data: Dict) -> bool:
        """Save a child profile securely"""
        # Separate sensitive data
        sensitive_data = {
            'id': profile_id,
            'name': profile_data.get('name'),
            'age': profile_data.get('age'),
            'parent_alerts': profile_data.get('safety', {}).get('parent_alerts', []),
            'session_logs': profile_data.get('session_logs', [])
        }
        
        return self.save_secure_data(f"profile_{profile_id}", sensitive_data)
    
    def load_profile(self, profile_id: str) -> Optional[Dict]:
        """Load a child profile"""
        return self.load_secure_data(f"profile_{profile_id}")
    
    def save_session(self, session_id: str, session_data: Dict) -> bool:
        """Save session data securely"""
        # Extract sensitive parts
        sensitive_session = {
            'session_id': session_id,
            'child_id': session_data.get('child_id'),
            'child_name': session_data.get('child_name'),
            'start_time': session_data.get('start_time'),
            'entries': session_data.get('entries', []),
            'parent_alerts': session_data.get('parent_alerts', [])
        }
        
        return self.save_secure_data(f"session_{session_id}", sensitive_session)
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load session data"""
        return self.load_secure_data(f"session_{session_id}")
    
    def list_profiles(self) -> List[str]:
        """List all stored profile IDs"""
        profiles = []
        
        for file in self.secure_dir.glob("profile_*.enc"):
            # Extract profile ID from filename
            profile_id = file.stem.replace("profile_", "")
            profiles.append(profile_id)
        
        return profiles
    
    def list_sessions(self, child_id: Optional[str] = None) -> List[str]:
        """List all stored session IDs, optionally filtered by child"""
        sessions = []
        
        for file in self.secure_dir.glob("session_*.enc"):
            session_id = file.stem.replace("session_", "")
            
            if child_id:
                # Load session to check child ID
                session_data = self.load_session(session_id)
                if session_data and session_data.get('child_id') == child_id:
                    sessions.append(session_id)
            else:
                sessions.append(session_id)
        
        return sessions
    
    def export_all_data(self, export_password: str) -> Optional[bytes]:
        """Export all data with a password for backup/transfer"""
        try:
            # Collect all data
            export_data = {
                'version': '1.0',
                'profiles': {},
                'sessions': {}
            }
            
            # Load all profiles
            for profile_id in self.list_profiles():
                profile = self.load_profile(profile_id)
                if profile:
                    export_data['profiles'][profile_id] = profile
            
            # Load all sessions
            for session_id in self.list_sessions():
                session = self.load_session(session_id)
                if session:
                    export_data['sessions'][session_id] = session
            
            # Create export-specific encryption
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(export_password.encode()))
            export_cipher = Fernet(key)
            
            # Encrypt export data
            json_data = json.dumps(export_data, indent=2)
            encrypted = export_cipher.encrypt(json_data.encode())
            
            # Combine salt and encrypted data
            return salt + encrypted
            
        except Exception as e:
            print(f"Export error: {e}")
            return None
    
    def import_all_data(self, encrypted_export: bytes, import_password: str) -> bool:
        """Import data from encrypted export"""
        try:
            # Extract salt and encrypted data
            salt = encrypted_export[:16]
            encrypted_data = encrypted_export[16:]
            
            # Recreate encryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(import_password.encode()))
            import_cipher = Fernet(key)
            
            # Decrypt
            decrypted = import_cipher.decrypt(encrypted_data)
            import_data = json.loads(decrypted.decode())
            
            # Import profiles
            for profile_id, profile_data in import_data.get('profiles', {}).items():
                self.save_profile(profile_id, profile_data)
            
            # Import sessions
            for session_id, session_data in import_data.get('sessions', {}).items():
                self.save_session(session_id, session_data)
            
            return True
            
        except Exception as e:
            print(f"Import error: {e}")
            return False
    
    def cleanup_old_sessions(self, days_to_keep: int = 90):
        """Clean up old session data"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for session_id in self.list_sessions():
            session = self.load_session(session_id)
            if session:
                try:
                    start_time = datetime.fromisoformat(session['start_time'])
                    if start_time < cutoff_date:
                        if self.delete_secure_data(f"session_{session_id}"):
                            deleted_count += 1
                except:
                    pass
        
        return deleted_count
    
    def get_storage_size(self) -> int:
        """Get total size of encrypted storage in bytes"""
        total_size = 0
        
        for file in self.secure_dir.glob("*.enc"):
            total_size += file.stat().st_size
        
        return total_size
    
    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """Verify integrity of all stored data"""
        errors = []
        
        # Check profiles
        for profile_id in self.list_profiles():
            try:
                profile = self.load_profile(profile_id)
                if not profile:
                    errors.append(f"Profile {profile_id}: Failed to load")
            except Exception as e:
                errors.append(f"Profile {profile_id}: {str(e)}")
        
        # Check sessions
        for session_id in self.list_sessions():
            try:
                session = self.load_session(session_id)
                if not session:
                    errors.append(f"Session {session_id}: Failed to load")
            except Exception as e:
                errors.append(f"Session {session_id}: {str(e)}")
        
        return len(errors) == 0, errors


# Example usage
if __name__ == "__main__":
    storage = ProfileStorage()
    
    # Test profile storage
    test_profile = {
        'name': 'Emma',
        'age': 8,
        'grade': '3',
        'interests': ['butterflies', 'space'],
        'safety': {
            'parent_alerts': [
                {'timestamp': '2024-01-15T10:30:00', 'type': 'test', 'details': 'Test alert'}
            ]
        }
    }
    
    print("Saving test profile...")
    if storage.save_profile('test_001', test_profile):
        print("✓ Profile saved securely")
    
    print("\nLoading test profile...")
    loaded = storage.load_profile('test_001')
    if loaded:
        print("✓ Profile loaded successfully")
        print(f"  Name: {loaded['name']}")
        print(f"  Age: {loaded['age']}")
    
    print(f"\nStorage size: {storage.get_storage_size()} bytes")
    
    # Test integrity
    print("\nVerifying storage integrity...")
    is_valid, errors = storage.verify_integrity()
    if is_valid:
        print("✓ All data intact")
    else:
        print(f"✗ Found {len(errors)} errors")

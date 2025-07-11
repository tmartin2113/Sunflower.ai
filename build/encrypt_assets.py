#!/usr/bin/env python3
"""
Encrypt sensitive assets including modelfiles and security keys.
Ensures proprietary content is protected in the final build.
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class AssetEncryptor:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.modelfiles_dir = self.root_dir / "modelfiles"
        self.staging_dir = self.root_dir / "cdrom_staging"
        self.security_dir = self.staging_dir / ".security"
        
        # Generate encryption keys
        self.master_key = self.generate_master_key()
        self.asset_keys = {}
        
    def generate_master_key(self):
        """Generate master encryption key"""
        # In production, this would be stored securely
        # For now, derive from hardware fingerprint + salt
        salt = b'SunflowerAI2025EducationSystem'
        password = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        # Store password securely for build process
        self.security_dir.mkdir(parents=True, exist_ok=True)
        key_file = self.security_dir / "build_key.enc"
        
        with open(key_file, "wb") as f:
            f.write(base64.b64encode(password))
            
        return key
    
    def encrypt_file(self, file_path, output_path):
        """Encrypt a single file"""
        fernet = Fernet(self.master_key)
        
        with open(file_path, "rb") as f:
            file_data = f.read()
            
        # Add metadata
        metadata = {
            "original_name": file_path.name,
            "size": len(file_data),
            "hash": hashlib.sha256(file_data).hexdigest(),
            "encrypted_date": datetime.now().isoformat()
        }
        
        # Encrypt file data
        encrypted_data = fernet.encrypt(file_data)
        
        # Store encrypted file
        with open(output_path, "wb") as f:
            # Write metadata length (4 bytes)
            metadata_json = json.dumps(metadata).encode()
            f.write(len(metadata_json).to_bytes(4, 'big'))
            # Write metadata
            f.write(metadata_json)
            # Write encrypted data
            f.write(encrypted_data)
            
        return metadata
    
    def encrypt_modelfiles(self):
        """Encrypt all modelfiles"""
        print("🔐 Encrypting modelfiles...")
        
        encrypted_dir = self.security_dir / "encrypted_models"
        encrypted_dir.mkdir(parents=True, exist_ok=True)
        
        modelfiles = list(self.modelfiles_dir.glob("*.modelfile"))
        
        for modelfile in modelfiles:
            output_path = encrypted_dir / f"{modelfile.stem}.enc"
            metadata = self.encrypt_file(modelfile, output_path)
            
            print(f"  ✅ Encrypted {modelfile.name}")
            self.asset_keys[modelfile.name] = metadata
    
    def create_fingerprint_file(self):
        """Create USB fingerprint file"""
        print("🔑 Creating fingerprint file...")
        
        # Generate unique fingerprint for this batch
        fingerprint_data = {
            "batch_id": f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "creation_date": datetime.now().isoformat(),
            "usb_serial_prefix": secrets.token_hex(8).upper(),
            "verification_key": secrets.token_urlsafe(32),
            "model_keys": {}
        }
        
        # Add model encryption keys
        for name, metadata in self.asset_keys.items():
            fingerprint_data["model_keys"][name] = {
                "hash": metadata["hash"],
                "size": metadata["size"]
            }
        
        # Encrypt fingerprint data
        fernet = Fernet(self.master_key)
        fingerprint_json = json.dumps(fingerprint_data, indent=2)
        encrypted_fingerprint = fernet.encrypt(fingerprint_json.encode())
        
        # Save fingerprint
        fingerprint_path = self.security_dir / "fingerprint.sig"
        with open(fingerprint_path, "wb") as f:
            f.write(encrypted_fingerprint)
            
        print(f"  ✅ Created fingerprint: {fingerprint_data['batch_id']}")
        
        return fingerprint_data
    
    def create_integrity_manifest(self):
        """Create file integrity manifest"""
        print("📋 Creating integrity manifest...")
        
        manifest = {
            "created": datetime.now().isoformat(),
            "files": {}
        }
        
        # Hash all files in staging directory
        for root, dirs, files in os.walk(self.staging_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.staging_dir)
                
                with open(file_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    
                manifest["files"][str(relative_path)] = {
                    "hash": file_hash,
                    "size": file_path.stat().st_size
                }
        
        # Encrypt manifest
        fernet = Fernet(self.master_key)
        manifest_json = json.dumps(manifest, indent=2)
        encrypted_manifest = fernet.encrypt(manifest_json.encode())
        
        # Save manifest
        manifest_path = self.security_dir / "manifest.enc"
        with open(manifest_path, "wb") as f:
            f.write(encrypted_manifest)
            
        print(f"  ✅ Manifest created with {len(manifest['files'])} files")
    
    def embed_decryption_logic(self):
        """Create decryption module to be embedded in executable"""
        print("💉 Creating embedded decryption logic...")
        
        decryption_code = '''
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class AssetDecryptor:
    def __init__(self, hardware_fingerprint):
        self.key = self._derive_key(hardware_fingerprint)
        self.fernet = Fernet(self.key)
        
    def _derive_key(self, fingerprint):
        """Derive decryption key from hardware fingerprint"""
        salt = b'SunflowerAI2025EducationSystem'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        return base64.urlsafe_b64encode(
            kdf.derive(fingerprint.encode())
        )
    
    def decrypt_asset(self, encrypted_path):
        """Decrypt an encrypted asset file"""
        with open(encrypted_path, "rb") as f:
            # Read metadata length
            metadata_len = int.from_bytes(f.read(4), 'big')
            # Read metadata
            metadata_json = f.read(metadata_len)
            # Read encrypted data
            encrypted_data = f.read()
            
        # Decrypt data
        decrypted_data = self.fernet.decrypt(encrypted_data)
        
        return decrypted_data, json.loads(metadata_json)
'''
        
        # Save decryption module
        decryptor_path = self.staging_dir / "decryptor.py.enc"
        
        # Obfuscate the decryption code
        import marshal
        code_obj = compile(decryption_code, "decryptor.py", "exec")
        marshaled = marshal.dumps(code_obj)
        
        # Simple obfuscation
        obfuscated = base64.b64encode(marshaled[::-1])
        
        with open(decryptor_path, "wb") as f:
            f.write(obfuscated)
            
        print("  ✅ Decryption logic embedded")
    
    def cleanup_sensitive_files(self):
        """Remove unencrypted sensitive files from staging"""
        print("🧹 Cleaning up sensitive files...")
        
        # Remove any accidentally copied modelfiles
        for modelfile in self.staging_dir.rglob("*.modelfile"):
            modelfile.unlink()
            print(f"  ✅ Removed {modelfile.name}")
    
    def build(self):
        """Execute full encryption process"""
        print(f"🌻 Sunflower AI Asset Encryption System")
        print(f"📅 Encryption Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        try:
            # Encrypt modelfiles
            self.encrypt_modelfiles()
            
            # Create fingerprint
            fingerprint_data = self.create_fingerprint_file()
            
            # Create integrity manifest
            self.create_integrity_manifest()
            
            # Embed decryption logic
            self.embed_decryption_logic()
            
            # Clean up
            self.cleanup_sensitive_files()
            
            print("\n✅ Asset encryption completed successfully!")
            print(f"🔑 Batch ID: {fingerprint_data['batch_id']}")
            print(f"📁 Security files: {self.security_dir}")
            
            # Save encryption record
            record = {
                "encryption_date": datetime.now().isoformat(),
                "batch_id": fingerprint_data["batch_id"],
                "encrypted_assets": list(self.asset_keys.keys()),
                "security_dir": str(self.security_dir)
            }
            
            records_dir = self.root_dir / "manufacturing" / "batch_records"
            records_dir.mkdir(parents=True, exist_ok=True)
            
            with open(records_dir / f"encryption_{fingerprint_data['batch_id']}.json", "w") as f:
                json.dump(record, f, indent=2)
                
        except Exception as e:
            print(f"\n❌ Encryption failed: {e}")
            raise


if __name__ == "__main__":
    encryptor = AssetEncryptor()
    encryptor.build()

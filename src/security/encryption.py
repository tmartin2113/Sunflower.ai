#!/usr/bin/env python3
"""
Encryption utilities for Sunflower AI.
Handles encryption and decryption of sensitive data like conversation logs.
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional


class EncryptionManager:
    """
    Manages symmetric encryption using Fernet.
    The encryption key is derived from a user's password and a static salt.
    """

    def __init__(self, password: str):
        """
        Initialize the encryption manager with a password to derive the key.
        
        Args:
            password: The user's password, used to generate the encryption key.
        """
        self._key = self._derive_key(password)
        self._fernet = Fernet(self._key)

    @staticmethod
    def _derive_key(password: str) -> bytes:
        """
        Derives a 32-byte key from the given password using PBKDF2.
        A static salt is used, which is acceptable for local, offline data
        encryption where the primary threat is direct file access.
        """
        salt = b'sunflower-ai-static-salt-2024' # A constant salt is acceptable for this use case
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypts the given bytes.

        Args:
            data: The plaintext data to encrypt.

        Returns:
            The encrypted ciphertext.
        """
        if not isinstance(data, bytes):
            raise TypeError("Data must be in bytes")
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> Optional[bytes]:
        """
        Decrypts the given token.

        Args:
            token: The encrypted token to decrypt.

        Returns:
            The decrypted plaintext data, or None if decryption fails.
        """
        if not isinstance(token, bytes):
            raise TypeError("Token must be in bytes")
        try:
            return self._fernet.decrypt(token)
        except Exception:
            # This can happen if the key is wrong or the token is invalid
            return None

if __name__ == '__main__':
    # Example Usage
    # In the real app, the parent's password would be used.
    password = "my-secret-password"
    manager = EncryptionManager(password)

    original_text = b"This is a secret conversation between a child and Sunflower."
    
    # Encrypt
    encrypted_token = manager.encrypt(original_text)
    print(f"Original: {original_text}")
    print(f"Encrypted: {encrypted_token}")

    # Decrypt
    decrypted_text = manager.decrypt(encrypted_token)
    print(f"Decrypted: {decrypted_text}")
    
    # Test decryption with wrong password
    wrong_manager = EncryptionManager("wrong-password")
    failed_decryption = wrong_manager.decrypt(encrypted_token)
    print(f"Decryption with wrong key: {failed_decryption}")

    assert original_text == decrypted_text
    assert failed_decryption is None
    print("\nEncryption/Decryption test passed!")

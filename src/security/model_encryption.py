#!/usr/bin/env python3
"""
Model Encryption Utility for Sunflower AI
This is a developer tool used during the manufacturing process to encrypt
the AI model files before they are placed on the CD-ROM.
"""

import argparse
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
except ImportError:
    print("Error: `cryptography` library not found.")
    print("Please install it using: pip install cryptography")
    exit(1)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a Fernet-compatible key from a password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_file(input_path: Path, output_path: Path, password: str):
    """
    Encrypts a file using a password-derived key.

    Args:
        input_path: Path to the model file to encrypt.
        output_path: Path to write the encrypted model file.
        password: The password to use for encryption.
    """
    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}")
        return

    print(f"Reading file: {input_path}...")
    try:
        with open(input_path, 'rb') as f:
            data = f.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        return

    # Using a fixed salt is acceptable here as this is for distribution,
    # not per-user data protection. The "password" is a master key.
    salt = b'sunflower-model-encryption-salt'
    key = derive_key(password, salt)
    fernet = Fernet(key)

    print("Encrypting data...")
    try:
        encrypted_data = fernet.encrypt(data)
    except Exception as e:
        print(f"Error during encryption: {e}")
        return
        
    print(f"Writing encrypted file to: {output_path}...")
    try:
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        print("Encryption complete!")
    except IOError as e:
        print(f"Error writing file: {e}")


def main():
    """Command-line interface for the encryption utility."""
    parser = argparse.ArgumentParser(
        description="Encrypt a Sunflower AI model file for distribution."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="The path to the plaintext model file (e.g., 'model.gguf')."
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="The path to write the encrypted model file to."
    )
    parser.add_argument(
        "-p", "--password",
        required=True,
        help="The master password for encryption."
    )

    args = parser.parse_args()

    encrypt_file(args.input_file, args.output_file, args.password)


if __name__ == "__main__":
    # Example usage from the command line:
    # python src/security/model_encryption.py models/llama-1b.gguf models/llama-1b.gguf.enc --password "our-secret-key"
    main()

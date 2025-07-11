#!/usr/bin/env python3
"""
Secure Token Generator for Sunflower AI
Provides a way to generate cryptographically strong random tokens.
"""

import secrets
import string


def generate_secure_token(length: int = 32) -> str:
    """
    Generates a cryptographically strong, URL-safe text string.

    Args:
        length: The desired length of the token in bytes. The resulting
                string will be longer due to base64 encoding.

    Returns:
        A secure, random, URL-safe string.
    """
    if length < 16:
        raise ValueError("Token length must be at least 16 bytes for security.")
    
    return secrets.token_urlsafe(length)


def generate_human_readable_code(length: int = 8) -> str:
    """
    Generates a more human-readable code (e.g., for 2FA or pairing).
    Uses uppercase letters and digits, excluding ambiguous characters.
    
    Args:
        length: The desired length of the code string.
        
    Returns:
        A random, human-readable code.
    """
    # Exclude characters that can be easily confused (e.g., O and 0, I and 1)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


if __name__ == '__main__':
    print("--- Generating Secure Tokens ---")
    
    # Generate a default API-style token
    token = generate_secure_token()
    print(f"Secure Token (default length): {token}")
    print(f"Length: {len(token)}")
    
    # Generate a longer token
    long_token = generate_secure_token(48)
    print(f"Long Secure Token (48 bytes): {long_token}")
    print(f"Length: {len(long_token)}")

    print("\n--- Generating Human-Readable Codes ---")
    
    pairing_code = generate_human_readable_code(6)
    print(f"6-digit Pairing Code: {pairing_code}")
    
    recovery_code = generate_human_readable_code(12)
    print(f"12-digit Recovery Code: {recovery_code}")
    
    # Test that different calls produce different results
    assert generate_secure_token() != generate_secure_token()
    assert generate_human_readable_code() != generate_human_readable_code()
    print("\nSUCCESS: Tokens are random and tests passed.")

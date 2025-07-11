#!/usr/bin/env python3
"""
Generic validation functions for the Sunflower AI application.
"""

import re
from typing import Optional, Tuple

# Regex for a basic email validation
# Not meant to be 100% compliant, but good for most cases.
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def is_valid_profile_name(name: str) -> bool:
    """
    Checks if a profile name is valid.
    - Must be between 2 and 30 characters.
    - Can contain letters, numbers, spaces, and hyphens.
    """
    if not 2 <= len(name) <= 30:
        return False
    # Check for allowed characters
    if not re.match(r"^[a-zA-Z0-9 -]+$", name):
        return False
    return True


def is_valid_email(email: str) -> bool:
    """
    Checks if an email address has a valid format.
    """
    if not email or not EMAIL_REGEX.match(email):
        return False
    return True


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validates password complexity.
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number

    Returns a tuple of (is_valid, message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    
    return True, "Password is valid."

if __name__ == '__main__':
    # --- Test Cases ---
    print("--- Testing Profile Names ---")
    assert is_valid_profile_name("Valid Name")
    assert not is_valid_profile_name("A")
    assert not is_valid_profile_name("Invalid<Name>")
    print("Profile name tests passed.")

    print("\n--- Testing Emails ---")
    assert is_valid_email("test@example.com")
    assert not is_valid_email("not-an-email")
    assert not is_valid_email("test@.com")
    print("Email tests passed.")

    print("\n--- Testing Passwords ---")
    is_valid, msg = validate_password("ValidPass1")
    assert is_valid
    is_valid, msg = validate_password("short")
    assert not is_valid
    print(f"Short password failed with: {msg}")
    is_valid, msg = validate_password("nouppercase1")
    assert not is_valid
    print(f"No-uppercase password failed with: {msg}")
    print("Password tests passed.")

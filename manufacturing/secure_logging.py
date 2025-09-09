#!/usr/bin/env python3
"""
Sunflower AI Professional System - Secure Logging Module
Automatic redaction of sensitive data in all log output
Version: 6.2.0 - Production Ready
"""

import re
import logging
import sys
from typing import List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
import json


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that automatically redacts sensitive information
    from all log records before they are output.
    """
    
    # Comprehensive patterns for sensitive data redaction
    REDACTION_PATTERNS: List[Tuple[str, str]] = [
        # Authentication tokens and keys
        (r'(token|Token|TOKEN)["\s:=]+([A-Za-z0-9+/=_-]{20,})', r'\1=***REDACTED***'),
        (r'(bearer|Bearer|BEARER)\s+([A-Za-z0-9+/=_-]{20,})', r'\1 ***REDACTED***'),
        (r'(api[_-]?key|API[_-]?KEY)["\s:=]+([A-Za-z0-9+/=_-]+)', r'\1=***REDACTED***'),
        (r'(access[_-]?token)["\s:=]+([A-Za-z0-9+/=_-]+)', r'\1=***REDACTED***'),
        (r'(refresh[_-]?token)["\s:=]+([A-Za-z0-9+/=_-]+)', r'\1=***REDACTED***'),
        
        # Passwords and secrets
        (r'(password|Password|PASSWORD)["\s:=]+([^\s"\']+)', r'\1=***REDACTED***'),
        (r'(secret|Secret|SECRET)["\s:=]+([A-Za-z0-9+/=_-]+)', r'\1=***REDACTED***'),
        (r'(private[_-]?key|PRIVATE[_-]?KEY)["\s:=]+([^\s"\']+)', r'\1=***REDACTED***'),
        
        # Hashes (various algorithms)
        (r'\$argon2[^\$]*\$[^\s]+', '***ARGON2_HASH_REDACTED***'),
        (r'\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}', '***BCRYPT_HASH_REDACTED***'),
        (r'\$pbkdf2[^\$]+\$[^\s]+', '***PBKDF2_HASH_REDACTED***'),
        (r'[A-Fa-f0-9]{64}', '***SHA256_REDACTED***'),
        (r'[A-Fa-f0-9]{128}', '***SHA512_REDACTED***'),
        (r'[A-Fa-f0-9]{32}', '***MD5_REDACTED***'),
        (r'[A-Fa-f0-9]{40}', '***SHA1_REDACTED***'),
        
        # Base64 encoded sensitive data (likely keys or tokens)
        (r'[A-Za-z0-9+/]{40,}={0,2}', '***BASE64_DATA_REDACTED***'),
        
        # Credit card numbers
        (r'\b(?:\d[ -]*?){13,19}\b', '***CREDIT_CARD_REDACTED***'),
        
        # Social Security Numbers
        (r'\b\d{3}-\d{2}-\d{4}\b', '***SSN_REDACTED***'),
        
        # Email addresses (partial redaction)
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'***EMAIL***@\2'),
        
        # IP addresses (partial redaction)
        (r'\b(\d{1,3}\.\d{1,3}\.)\d{1,3}\.\d{1,3}\b', r'\1XXX.XXX'),
        
        # Phone numbers
        (r'\b\+?[1-9]\d{1,14}\b', '***PHONE_REDACTED***'),
        
        # AWS credentials
        (r'(AKIA[0-9A-Z]{16})', '***AWS_ACCESS_KEY_REDACTED***'),
        (r'([A-Za-z0-9+/]{40})', '***AWS_SECRET_KEY_REDACTED***'),
        
        # Database connection strings
        (r'(mongodb|postgresql|mysql|redis|sqlite)://[^\s]+', r'\1://***REDACTED***'),
        
        # File paths with potential sensitive data
        (r'/home/[^/\s]+', '/home/***USER***'),
        (r'C:\\Users\\[^\\]+', 'C:\\Users\\***USER***'),
        
        # UUIDs (might be user/session identifiers)
        (r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '***UUID_REDACTED***'),
    ]
    
    # Sensitive field names to check in structured data
    SENSITIVE_FIELDS = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'key', 'api_key',
        'apikey', 'auth', 'authorization', 'cookie', 'session', 'csrf',
        'private', 'credential', 'access_token', 'refresh_token', 'bearer',
        'signature', 'salt', 'hash', 'pin', 'ssn', 'social_security',
        'credit_card', 'card_number', 'cvv', 'cvc', 'expiry'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record and redact sensitive information
        
        Args:
            record: Log record to filter
            
        Returns:
            True (always pass the record through after redaction)
        """
        # Redact the main message
        if hasattr(record, 'msg'):
            record.msg = self._redact_string(str(record.msg))
        
        # Redact arguments
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(arg) for arg in record.args)
        
        # Redact exception information
        if record.exc_info and record.exc_info[1]:
            # Redact exception message
            exc_str = str(record.exc_info[1])
            redacted_exc_str = self._redact_string(exc_str)
            if exc_str != redacted_exc_str:
                # Create a new exception with redacted message
                record.exc_text = self._redact_string(record.exc_text or "")
        
        # Redact extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'pathname', 'process', 
                          'processName', 'relativeCreated', 'thread', 
                          'threadName', 'exc_info', 'exc_text', 'stack_info'):
                if self._is_sensitive_field(key):
                    record.__dict__[key] = '***REDACTED***'
                elif isinstance(value, str):
                    record.__dict__[key] = self._redact_string(value)
                elif isinstance(value, dict):
                    record.__dict__[key] = self._redact_dict(value)
        
        return True
    
    def _redact_string(self, text: str) -> str:
        """Apply all redaction patterns to a string"""
        if not text:
            return text
        
        redacted = text
        for pattern, replacement in self.REDACTION_PATTERNS:
            try:
                redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
            except re.error:
                # Skip invalid patterns
                continue
        
        return redacted
    
    def _redact_dict(self, data: dict) -> dict:
        """Recursively redact sensitive data in dictionaries"""
        redacted = {}
        
        for key, value in data.items():
            # Check if key name indicates sensitive data
            if self._is_sensitive_field(key):
                redacted[key] = '***REDACTED***'
            elif isinstance(value, str):
                redacted[key] = self._redact_string(value)
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [self._redact_value(item) for item in value]
            else:
                redacted[key] = value
        
        return redacted
    
    def _redact_value(self, value: Any) -> Any:
        """Redact a single value based on its type"""
        if isinstance(value, str):
            return self._redact_string(value)
        elif isinstance(value, dict):
            return self._redact_dict(value)
        elif isinstance(value, list):
            return [self._redact_value(item) for item in value]
        else:
            return value
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name indicates sensitive data"""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in self.SENSITIVE_FIELDS)


class SecureFormatter(logging.Formatter):
    """
    Custom formatter that ensures sensitive data is redacted
    even in formatted output.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format record with additional redaction"""
        # First apply standard formatting
        result = super().format(record)
        
        # Then apply additional redaction to the final output
        # This catches any sensitive data that might have been added during formatting
        filter = SensitiveDataFilter()
        return filter._redact_string(result)


def setup_secure_logging(name: str = None, 
                        level: int = logging.INFO,
                        log_file: Optional[Path] = None) -> logging.Logger:
    """
    Set up secure logging with automatic sensitive data redaction
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file path
        
    Returns:
        Configured logger with security filters
    """
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create secure formatter
    formatter = SecureFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler with redaction
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)
    
    # File handler with redaction (if specified)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        logger.addHandler(file_handler)
    
    # Add global filter to logger itself for extra safety
    logger.addFilter(SensitiveDataFilter())
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Example of secure logging context manager
class SecureLoggingContext:
    """Context manager for temporary secure logging configuration"""
    
    def __init__(self, redact_all: bool = False):
        self.redact_all = redact_all
        self.original_filters = {}
        
    def __enter__(self):
        """Enter secure logging context"""
        # Add secure filters to all existing loggers
        for name in logging.Logger.manager.loggerDict:
            logger = logging.getLogger(name)
            if not any(isinstance(f, SensitiveDataFilter) for f in logger.filters):
                logger.addFilter(SensitiveDataFilter())
                self.original_filters[name] = True
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit secure logging context"""
        # Remove filters we added (optional)
        if not self.redact_all:
            for name in self.original_filters:
                logger = logging.getLogger(name)
                for filter in logger.filters[:]:
                    if isinstance(filter, SensitiveDataFilter):
                        logger.removeFilter(filter)


# Global configuration for all loggers
def configure_global_secure_logging():
    """Configure secure logging globally for all loggers"""
    
    # Set up root logger with security
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add secure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(SecureFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)
    
    # Add filter to root logger
    root_logger.addFilter(SensitiveDataFilter())
    
    # Configure logging for common libraries that might log sensitive data
    for lib_name in ['urllib3', 'requests', 'paramiko', 'sqlalchemy', 'boto3']:
        lib_logger = logging.getLogger(lib_name)
        lib_logger.addFilter(SensitiveDataFilter())
        lib_logger.setLevel(logging.WARNING)  # Reduce verbosity


# Testing
if __name__ == "__main__":
    # Configure global secure logging
    configure_global_secure_logging()
    
    # Test secure logging
    logger = setup_secure_logging("security_test")
    
    print("Testing Secure Logging")
    print("=" * 50)
    
    # Test various sensitive data patterns
    test_cases = [
        "User password: MySecretPass123!",
        "API key: AKIA1234567890ABCDEF",
        "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
        "Database: postgresql://user:password@localhost:5432/dbname",
        "Credit card: 4532-1234-5678-9012",
        "SSN: 123-45-6789",
        "Hash: $argon2id$v=19$m=65536,t=2,p=4$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dWRWJTmaaJObG",
        "Secret data: {'password': 'admin123', 'api_key': 'sk-1234567890', 'token': 'secret_token'}",
        "Email: user@example.com",
        "IP: 192.168.1.100",
        "File path: /home/johndoe/secret_file.txt",
    ]
    
    for test in test_cases:
        logger.info(test)
    
    # Test structured logging
    logger.info("User login", extra={
        'user_id': 'user123',
        'password': 'should_be_redacted',
        'session_token': 'abc123def456ghi789',
        'ip_address': '192.168.1.1'
    })
    
    # Test exception logging
    try:
        raise ValueError("Database connection failed: password=admin123")
    except ValueError as e:
        logger.error("Error occurred", exc_info=True)
    
    print("\n" + "=" * 50)
    print("Check output above - all sensitive data should be REDACTED")
    print("Security test completed!")

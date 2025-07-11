#!/usr/bin/env python3
"""
Custom exceptions for the Sunflower AI application.
"""

class SunflowerException(Exception):
    """Base exception class for all application-specific errors."""
    pass

# --- Configuration Errors ---
class ConfigError(SunflowerException):
    """Raised for errors related to configuration loading or validation."""
    pass

class ModelRegistryError(ConfigError):
    """Raised when there's an issue with the model registry."""
    pass

# --- Profile Management Errors ---
class ProfileError(SunflowerException):
    """Raised for errors related to user profile management."""
    pass

class ProfileNotFound(ProfileError):
    """Raised when a specific profile cannot be found."""
    pass

class ProfileLoadError(ProfileError):
    """Raised when a profile file is corrupt or cannot be read."""
    pass

# --- Validation and Security Errors ---
class ValidationError(SunflowerException):
    """Base class for validation failures."""
    pass

class IntegrityCheckError(ValidationError):
    """Raised when a file hash or integrity check fails."""
    pass

class PartitionNotFoundError(ValidationError):
    """Raised when a required partition (CD-ROM or USB) cannot be found."""
    pass

# --- Hardware and Platform Errors ---
class HardwareUnsupportedError(SunflowerException):
    """Raised when the hardware does not meet minimum requirements."""
    pass

class PlatformError(SunflowerException):
    """Raised for OS-specific integration errors."""
    pass

# --- Model and Ollama Errors ---
class ModelManagerError(SunflowerException):
    """Raised for errors in the ModelManager."""
    pass

class OllamaError(SunflowerException):
    """Raised for errors related to the Ollama client or server."""
    pass

class OllamaConnectionError(OllamaError):
    """Raised when the client cannot connect to the Ollama server."""
    pass

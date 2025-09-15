#!/usr/bin/env python3
"""
Sunflower AI Professional System - Secure Autorun.inf Generator
Replaces the vulnerable autorun.inf.template with secure generation

This module generates Windows autorun.inf files with proper input validation
and sanitization to prevent injection attacks.

FIX BUG-018: Prevents injection vulnerabilities through:
- Input validation and sanitization
- Character escaping
- Length limits
- Type checking
- Safe string formatting
"""

import re
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class AutorunSecurityError(Exception):
    """Raised when security validation fails"""
    pass


class AutorunGenerator:
    """Secure generator for Windows autorun.inf files"""
    
    # Maximum lengths for various fields to prevent overflow
    MAX_LENGTHS = {
        'volume_label': 32,
        'product_name': 64,
        'version': 16,
        'publisher': 64,
        'support_url': 256,
        'device_id': 64,
        'cert_thumbprint': 64,
        'build_number': 16,
        'path': 256,
        'command': 512
    }
    
    # Allowed characters for different field types
    PATTERNS = {
        'alphanum': re.compile(r'^[a-zA-Z0-9\s\-_.]+$'),
        'version': re.compile(r'^[0-9]+\.[0-9]+(\.[0-9]+)?$'),
        'url': re.compile(r'^https?://[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=]+$'),
        'path': re.compile(r'^[a-zA-Z0-9\-._\\/: ]+$'),
        'hex': re.compile(r'^[0-9A-Fa-f]+$'),
        'date': re.compile(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'),
        'build': re.compile(r'^[0-9]+$'),
        'device_id': re.compile(r'^[A-Z0-9\-]+$'),
        'model_list': re.compile(r'^[a-zA-Z0-9:.,\-_]+$')
    }
    
    def __init__(self):
        """Initialize the autorun generator"""
        self.config = {}
        self.warnings = []
    
    def sanitize_string(self, value: str, field_type: str, max_length: Optional[int] = None) -> str:
        """
        FIX BUG-018: Sanitize a string value to prevent injection
        
        Args:
            value: Raw input value
            field_type: Type of field for validation
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string safe for INF file
            
        Raises:
            AutorunSecurityError: If value fails security validation
        """
        if value is None:
            return ""
        
        # Convert to string and strip whitespace
        value = str(value).strip()
        
        # Check length
        if max_length:
            if len(value) > max_length:
                raise AutorunSecurityError(
                    f"Value exceeds maximum length of {max_length}: {value[:50]}..."
                )
        
        # Remove any null bytes or control characters
        value = ''.join(char for char in value if ord(char) >= 32 and ord(char) != 127)
        
        # Check against pattern
        if field_type in self.PATTERNS:
            if not self.PATTERNS[field_type].match(value):
                raise AutorunSecurityError(
                    f"Value contains invalid characters for {field_type}: {value[:50]}"
                )
        
        # Escape special INF characters
        # INF files use semicolon for comments, so escape them
        value = value.replace(';', '\\x3B')
        value = value.replace('\n', ' ')
        value = value.replace('\r', ' ')
        value = value.replace('"', "'")
        
        # Remove any potential command injection characters
        dangerous_chars = ['`', '$', '&', '|', '>', '<', '(', ')', '{', '}', '[', ']']
        for char in dangerous_chars:
            value = value.replace(char, '')
        
        return value
    
    def validate_path(self, path: str) -> str:
        """
        FIX BUG-018: Validate and sanitize file paths
        
        Args:
            path: File path to validate
            
        Returns:
            Sanitized path
            
        Raises:
            AutorunSecurityError: If path is invalid
        """
        # Normalize path separators
        path = path.replace('/', '\\')
        
        # Check for path traversal attempts
        if '..' in path:
            raise AutorunSecurityError(f"Path traversal detected: {path}")
        
        # Check for absolute paths (not allowed in autorun)
        if ':' in path or path.startswith('\\\\'):
            raise AutorunSecurityError(f"Absolute path not allowed: {path}")
        
        # Ensure path doesn't start with backslash
        path = path.lstrip('\\')
        
        # Validate characters
        sanitized = self.sanitize_string(path, 'path', self.MAX_LENGTHS['path'])
        
        return sanitized
    
    def validate_url(self, url: str) -> str:
        """
        FIX BUG-018: Validate and sanitize URLs
        
        Args:
            url: URL to validate
            
        Returns:
            Sanitized URL
            
        Raises:
            AutorunSecurityError: If URL is invalid
        """
        if not url:
            return ""
        
        # Must start with http:// or https://
        if not url.startswith(('http://', 'https://')):
            raise AutorunSecurityError(f"Invalid URL scheme: {url}")
        
        # Validate against pattern
        sanitized = self.sanitize_string(url, 'url', self.MAX_LENGTHS['support_url'])
        
        # Additional check for common injection attempts
        if any(bad in url.lower() for bad in ['javascript:', 'data:', 'vbscript:', 'file:']):
            raise AutorunSecurityError(f"Potentially malicious URL: {url}")
        
        return sanitized
    
    def set_config(self, config: Dict[str, Any]):
        """
        Set configuration with validation
        
        Args:
            config: Configuration dictionary with template values
        """
        # Validate and sanitize each configuration value
        self.config['volume_label'] = self.sanitize_string(
            config.get('VOLUME_LABEL', 'Sunflower AI'),
            'alphanum',
            self.MAX_LENGTHS['volume_label']
        )
        
        self.config['product_name'] = self.sanitize_string(
            config.get('PRODUCT_NAME', 'Sunflower AI Professional'),
            'alphanum',
            self.MAX_LENGTHS['product_name']
        )
        
        self.config['version'] = self.sanitize_string(
            config.get('VERSION', '6.2.0'),
            'version',
            self.MAX_LENGTHS['version']
        )
        
        self.config['publisher'] = self.sanitize_string(
            config.get('PUBLISHER', 'Sunflower AI Systems'),
            'alphanum',
            self.MAX_LENGTHS['publisher']
        )
        
        self.config['support_url'] = self.validate_url(
            config.get('SUPPORT_URL', 'https://sunflowerai.education/support')
        )
        
        self.config['device_id'] = self.sanitize_string(
            config.get('DEVICE_ID', 'UNKNOWN'),
            'device_id',
            self.MAX_LENGTHS['device_id']
        )
        
        self.config['cert_thumbprint'] = self.sanitize_string(
            config.get('CERT_THUMBPRINT', ''),
            'hex',
            self.MAX_LENGTHS['cert_thumbprint']
        )
        
        self.config['build_date'] = self.sanitize_string(
            config.get('BUILD_DATE', datetime.now().strftime('%Y-%m-%d')),
            'date',
            10
        )
        
        self.config['build_number'] = self.sanitize_string(
            config.get('BUILD_NUMBER', '001'),
            'build',
            self.MAX_LENGTHS['build_number']
        )
        
        # Model variants - special handling for comma-separated list
        model_variants = config.get('MODEL_VARIANTS', 'llama3.2:7b,llama3.2:3b,llama3.2:1b')
        self.config['model_variants'] = self.sanitize_string(
            model_variants,
            'model_list',
            256
        )
    
    def generate(self) -> str:
        """
        Generate secure autorun.inf content
        
        Returns:
            Safe autorun.inf content as string
        """
        # Build the autorun.inf content with validated values
        content = []
        
        # Header comment
        content.append("; Sunflower AI Professional System - Windows Autorun Configuration")
        content.append("; Generated securely with input validation")
        content.append(f"; Version: {self.config['version']}")
        content.append(f"; Build: {self.config['build_number']}")
        content.append(f"; Date: {self.config['build_date']}")
        content.append("")
        
        # Main autorun section
        content.append("[autorun]")
        content.append("; Primary launcher executable")
        content.append("open=launchers\\windows_launcher.exe")
        content.append("")
        content.append("; Custom icon for the device")
        content.append("icon=assets\\sunflower.ico")
        content.append("")
        content.append("; Volume label displayed in Windows Explorer")
        content.append(f"label={self.config['volume_label']}")
        content.append("")
        content.append("; Action menu items")
        content.append("action=Install Sunflower AI Professional System")
        content.append("")
        
        # Content section
        content.append("[Content]")
        content.append("; Content type identification")
        content.append("MusicFiles=false")
        content.append("PictureFiles=false")
        content.append("VideoFiles=false")
        content.append("DataFiles=true")
        content.append("")
        
        # Setup section with validated values
        content.append("[Setup]")
        content.append("; Installation configuration")
        content.append(f"ProductName={self.config['product_name']}")
        content.append(f"ProductVersion={self.config['version']}")
        content.append(f"Publisher={self.config['publisher']}")
        
        if self.config['support_url']:
            content.append(f"SupportURL={self.config['support_url']}")
        
        content.append("InstallationType=Portable")
        content.append("RequiresAdmin=false")
        content.append("MinimumOS=Windows10")
        content.append("Architecture=x64")
        content.append("")
        
        # Launch section with safe paths
        content.append("[Launch]")
        content.append("; Launch options for different scenarios")
        content.append("FirstRun=launchers\\windows_launcher.exe /firstrun")
        content.append("ParentMode=launchers\\windows_launcher.exe /parent")
        content.append("EducatorMode=launchers\\windows_launcher.exe /educator")
        content.append("RepairMode=launchers\\windows_launcher.exe /repair")
        content.append("")
        
        # Paths section
        content.append("[Paths]")
        content.append("; Important paths on the CD-ROM partition")
        content.append("Models=models\\")
        content.append("Modelfiles=modelfiles\\")
        content.append("Documentation=documentation\\")
        content.append("Interface=interface\\")
        content.append("Ollama=ollama\\windows\\")
        content.append("")
        
        # Hardware section with validated model variants
        content.append("[Hardware]")
        content.append("; Hardware detection and model selection")
        content.append("AutoDetect=true")
        
        if self.config['model_variants']:
            content.append(f"ModelVariants={self.config['model_variants']}")
        
        content.append("DefaultModel=llama3.2:1b")
        content.append("HighPerformanceModel=llama3.2:7b")
        content.append("LowMemoryModel=llama3.2:1b-q4_0")
        content.append("")
        
        # Security section with validated values
        content.append("[Security]")
        content.append("; Security and verification settings")
        content.append("VerifyChecksum=true")
        content.append("ChecksumFile=security\\checksums.sha256")
        content.append("ManifestFile=security\\manifest.json")
        
        if self.config['device_id']:
            content.append(f"DeviceID={self.config['device_id']}")
        
        content.append("EncryptionEnabled=true")
        content.append("")
        
        # USB Partition section
        content.append("[USB_Partition]")
        content.append("; Configuration for the writable USB partition")
        content.append(f"DataVolumeLabel={self.config['volume_label']}_DATA")
        content.append("ProfilesPath=family_profiles\\")
        content.append("ConversationsPath=conversation_logs\\")
        content.append("ProgressPath=learning_progress\\")
        content.append("DashboardPath=parent_dashboard\\")
        content.append("ConfigPath=runtime_config\\")
        content.append("")
        
        # Features section
        content.append("[Features]")
        content.append("; Feature flags")
        content.append("OfflineMode=true")
        content.append("FamilyProfiles=true")
        content.append("ParentDashboard=true")
        content.append("SafetyFiltering=true")
        content.append("STEMFocus=true")
        content.append("AgeAdaptation=true")
        content.append("MultipleChildren=true")
        content.append("SessionLogging=true")
        content.append("")
        
        # Telemetry section
        content.append("[Telemetry]")
        content.append("; Privacy and telemetry settings")
        content.append("CollectTelemetry=false")
        content.append("SendCrashReports=false")
        content.append("AnonymousUsageStats=false")
        content.append("LocalLoggingOnly=true")
        content.append("")
        
        # Updates section
        content.append("[Updates]")
        content.append("; Update configuration")
        content.append("AutoUpdate=false")
        content.append("CheckForUpdates=false")
        content.append("UpdateModel=NewDevicePurchase")
        content.append("")
        
        # Shell commands - safely formatted
        content.append("[shell]")
        content.append("; Shell integration for Windows Explorer")
        content.append("shell\\install\\command=launchers\\windows_launcher.exe /install")
        content.append("shell\\readme\\command=notepad.exe README.txt")
        content.append("shell\\documentation\\command=documentation\\user_guide.pdf")
        content.append("shell\\troubleshoot\\command=launchers\\windows_launcher.exe /troubleshoot")
        content.append("")
        
        # Digital signature section if certificate present
        if self.config.get('cert_thumbprint'):
            content.append("[DigitalSignature]")
            content.append("; Digital signature information")
            content.append("SignatureVersion=2.0")
            content.append("SignatureMethod=SHA256")
            content.append(f"CertificateThumbprint={self.config['cert_thumbprint']}")
            content.append("TimestampServer=http://timestamp.digicert.com")
            content.append("")
        
        # Custom properties section
        content.append("[CustomProperties]")
        content.append(f"BuildDate={self.config['build_date']}")
        content.append(f"BuildNumber={self.config['build_number']}")
        content.append("TargetAudience=Families,Educators")
        content.append("AgeRange=5-17")
        content.append("SubjectAreas=Science,Technology,Engineering,Mathematics")
        content.append("SafetyLevel=Maximum")
        content.append("ContentRating=K-12")
        content.append("")
        
        # File associations
        content.append("[FileAssociations]")
        content.append(".sai=SunflowerAI.Session")
        content.append(".sap=SunflowerAI.Profile")
        content.append(".sal=SunflowerAI.Lesson")
        content.append("")
        
        # End comment
        content.append("; End of autorun.inf")
        content.append(f"; Securely generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return '\n'.join(content)
    
    def save(self, output_path: Path, config: Dict[str, Any]):
        """
        Generate and save autorun.inf file
        
        Args:
            output_path: Path where to save the file
            config: Configuration dictionary
        """
        try:
            # Set and validate configuration
            self.set_config(config)
            
            # Generate content
            content = self.generate()
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Set file as hidden/system on Windows
            if os.name == 'nt':
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                FILE_ATTRIBUTE_SYSTEM = 0x04
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(output_path),
                    FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
                )
            
            print(f"✅ Securely generated autorun.inf: {output_path}")
            
            if self.warnings:
                print("⚠️ Warnings during generation:")
                for warning in self.warnings:
                    print(f"  - {warning}")
            
        except AutorunSecurityError as e:
            print(f"❌ Security validation failed: {e}")
            raise
        except Exception as e:
            print(f"❌ Failed to generate autorun.inf: {e}")
            raise


def main():
    """Main entry point for testing"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Generate secure autorun.inf file for Sunflower AI"
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        help='JSON configuration file with template values'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('autorun.inf'),
        help='Output path for autorun.inf file'
    )
    
    parser.add_argument(
        '--volume-label',
        default='Sunflower AI',
        help='Volume label for the device'
    )
    
    parser.add_argument(
        '--version',
        default='6.2.0',
        help='Product version'
    )
    
    parser.add_argument(
        '--device-id',
        help='Unique device identifier'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config and args.config.exists():
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Override with command-line arguments
    if args.volume_label:
        config['VOLUME_LABEL'] = args.volume_label
    if args.version:
        config['VERSION'] = args.version
    if args.device_id:
        config['DEVICE_ID'] = args.device_id
    
    # Generate autorun.inf
    generator = AutorunGenerator()
    
    try:
        generator.save(args.output, config)
        print(f"Successfully generated secure autorun.inf at {args.output}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

# Security Implementation Documentation

## Security Overview

Sunflower AI Professional implements defense-in-depth security to protect children, family data, and system integrity. This document details our comprehensive security architecture.

## Security Principles

### Core Security Tenets

1. **Privacy First**: No data collection, no telemetry, no cloud
2. **Local Only**: Complete air-gap security through offline operation
3. **Parent Control**: Parents have absolute authority over system
4. **Child Safety**: Multiple layers protecting children from harm
5. **Data Isolation**: Each profile completely separated
6. **Tamper Resistant**: Read-only system partition prevents modification

## Architecture Security

### Dual-Partition Security Model

```
USB Device Security Layout:
┌──────────────────────────────────────┐
│   CD-ROM Partition (Read-Only)       │
│   ├── Signed executables             │
│   ├── Encrypted models               │
│   ├── Integrity checksums            │
│   └── Tamper detection               │
├──────────────────────────────────────┤
│   USB Partition (Encrypted)          │
│   ├── AES-256 encryption            │
│   ├── Profile isolation             │
│   ├── Secure key storage            │
│   └── Audit logging                 │
└──────────────────────────────────────┘
```

### Read-Only System Protection

```python
class SystemIntegrityProtection:
    """Ensure system files cannot be modified"""
    
    def __init__(self, cdrom_path):
        self.cdrom_path = cdrom_path
        self.checksums = self.load_checksums()
    
    def verify_integrity(self):
        """Check all system files against known checksums"""
        failures = []
        
        for file_path, expected_hash in self.checksums.items():
            actual_hash = self.calculate_sha256(file_path)
            
            if actual_hash != expected_hash:
                failures.append({
                    "file": file_path,
                    "expected": expected_hash,
                    "actual": actual_hash
                })
        
        if failures:
            self.handle_integrity_failure(failures)
            return False
        
        return True
    
    def handle_integrity_failure(self, failures):
        """Respond to tampered files"""
        # Log incident
        self.log_security_event("INTEGRITY_FAILURE", failures)
        
        # Prevent system start
        raise SecurityException("System integrity check failed")
```

## Authentication & Authorization

### Parent Authentication System

```python
import hashlib
import secrets
import hmac
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class ParentAuthentication:
    """Secure parent authentication system"""
    
    def __init__(self):
        self.iterations = 100_000  # PBKDF2 iterations
        self.salt_length = 32      # Salt size in bytes
        
    def create_parent_password(self, password):
        """Create secure password hash"""
        # Generate cryptographic salt
        salt = secrets.token_bytes(self.salt_length)
        
        # Derive key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations
        )
        
        key = kdf.derive(password.encode())
        
        # Store salt + key
        stored = salt + key
        
        # Additional protection with pepper (device-specific)
        pepper = self.get_device_pepper()
        final_hash = hmac.new(pepper, stored, hashlib.sha256).digest()
        
        return base64.b64encode(final_hash).decode()
    
    def verify_password(self, password, stored_hash):
        """Verify parent password"""
        try:
            stored = base64.b64decode(stored_hash)
            
            # Extract salt
            salt = stored[:self.salt_length]
            stored_key = stored[self.salt_length:]
            
            # Derive key from provided password
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.iterations
            )
            
            test_key = kdf.derive(password.encode())
            
            # Constant-time comparison
            return hmac.compare_digest(test_key, stored_key)
            
        except Exception:
            return False
    
    def get_device_pepper(self):
        """Get device-specific pepper for additional security"""
        # Derive from hardware serial or USB device ID
        device_id = self.get_usb_serial()
        return hashlib.sha256(device_id.encode()).digest()
```

### Session Management

```python
class SecureSessionManager:
    """Manage authenticated sessions securely"""
    
    def __init__(self):
        self.sessions = {}
        self.session_timeout = 3600  # 1 hour
        self.max_sessions = 1  # Single session at a time
        
    def create_session(self, profile_id, parent_authenticated=False):
        """Create secure session token"""
        # Generate cryptographically secure token
        session_token = secrets.token_urlsafe(32)
        
        session = {
            "token": session_token,
            "profile_id": profile_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "parent_mode": parent_authenticated,
            "ip_address": self.get_client_ip(),
            "user_agent": self.get_user_agent()
        }
        
        # Enforce single session
        if len(self.sessions) >= self.max_sessions:
            self.terminate_oldest_session()
        
        self.sessions[session_token] = session
        
        return session_token
    
    def validate_session(self, token):
        """Validate and refresh session"""
        if token not in self.sessions:
            return None
        
        session = self.sessions[token]
        
        # Check timeout
        if time.time() - session["last_activity"] > self.session_timeout:
            del self.sessions[token]
            return None
        
        # Check for session hijacking
        if not self.verify_session_fingerprint(session):
            self.log_security_event("SESSION_HIJACK_ATTEMPT", session)
            del self.sessions[token]
            return None
        
        # Refresh activity
        session["last_activity"] = time.time()
        
        return session
```

## Data Protection

### Encryption Implementation

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class DataEncryption:
    """AES-256 encryption for sensitive data"""
    
    def __init__(self, usb_partition):
        self.usb_partition = usb_partition
        self.key = self.derive_encryption_key()
        self.cipher = Fernet(self.key)
    
    def derive_encryption_key(self):
        """Derive encryption key from multiple sources"""
        # Combine multiple entropy sources
        sources = [
            self.get_device_serial(),      # Hardware serial
            self.get_parent_password_hash(), # Parent password
            self.get_installation_id()       # Unique install ID
        ]
        
        combined = "".join(sources).encode()
        
        # Derive key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"sunflower_salt_v1",  # Static salt for deterministic key
            iterations=100_000
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(combined))
        return key
    
    def encrypt_profile_data(self, profile_data):
        """Encrypt child profile data"""
        json_data = json.dumps(profile_data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return encrypted
    
    def decrypt_profile_data(self, encrypted_data):
        """Decrypt child profile data"""
        decrypted = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    
    def secure_delete(self, filepath):
        """Securely overwrite and delete file"""
        if os.path.exists(filepath):
            # Get file size
            filesize = os.path.getsize(filepath)
            
            # Overwrite with random data 3 times
            with open(filepath, "rb+") as f:
                for _ in range(3):
                    f.seek(0)
                    f.write(os.urandom(filesize))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Remove file
            os.remove(filepath)
```

### Profile Isolation

```python
class ProfileIsolation:
    """Ensure complete separation between profiles"""
    
    def __init__(self, profiles_root):
        self.profiles_root = profiles_root
        
    def create_isolated_profile(self, profile_id):
        """Create isolated profile directory"""
        profile_path = self.profiles_root / profile_id
        
        # Create with restrictive permissions
        profile_path.mkdir(mode=0o700, exist_ok=True)
        
        # Create subdirectories
        (profile_path / "history").mkdir(mode=0o700)
        (profile_path / "progress").mkdir(mode=0o700)
        (profile_path / "settings").mkdir(mode=0o700)
        
        # Set ownership (parent process only)
        self.set_profile_ownership(profile_path)
        
        return profile_path
    
    def enforce_isolation(self, current_profile_id, requested_path):
        """Prevent cross-profile access"""
        # Resolve absolute path
        abs_path = os.path.abspath(requested_path)
        
        # Get profile's allowed path
        allowed_path = self.profiles_root / current_profile_id
        allowed_abs = os.path.abspath(allowed_path)
        
        # Check if requested path is within profile boundary
        if not abs_path.startswith(allowed_abs):
            self.log_security_event("ISOLATION_VIOLATION", {
                "profile": current_profile_id,
                "attempted_path": abs_path
            })
            raise SecurityException("Access denied: Profile isolation violation")
        
        return abs_path
```

## Content Security

### Multi-Layer Content Filtering

```python
class ContentSecuritySystem:
    """Comprehensive content security implementation"""
    
    def __init__(self):
        self.blocked_terms = self.load_blocked_terms()
        self.blocked_patterns = self.compile_patterns()
        self.safety_threshold = 0.95
        
    def check_content_safety(self, content, age):
        """Multi-layer content safety check"""
        
        # Layer 1: Exact term matching
        if self.contains_blocked_terms(content):
            return False, "Blocked term detected"
        
        # Layer 2: Pattern matching
        if self.matches_blocked_patterns(content):
            return False, "Unsafe pattern detected"
        
        # Layer 3: Context analysis
        if not self.analyze_context(content, age):
            return False, "Context inappropriate for age"
        
        # Layer 4: Sentiment analysis
        if self.detect_negative_sentiment(content) > self.safety_threshold:
            return False, "Negative content detected"
        
        # Layer 5: Age appropriateness
        if not self.verify_age_appropriate(content, age):
            return False, "Content too advanced for age"
        
        return True, "Content safe"
    
    def contains_blocked_terms(self, content):
        """Check for explicitly blocked terms"""
        content_lower = content.lower()
        
        for term in self.blocked_terms:
            if term in content_lower:
                return True
        
        return False
    
    def compile_patterns(self):
        """Compile regex patterns for unsafe content"""
        patterns = [
            r'\b(violence|weapon|drug|alcohol)\b',
            r'\b(personal|private|secret)\s+(information|data)',
            r'\b(home|address|phone|email)\b',
            r'\b(password|credit|card|social\s+security)\b'
        ]
        
        return [re.compile(p, re.IGNORECASE) for p in patterns]
```

### Input Sanitization

```python
class InputSanitization:
    """Sanitize all user inputs for security"""
    
    def sanitize_text_input(self, text):
        """Clean text input from potential threats"""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Limit length
        max_length = 1000  # Maximum input length
        text = text[:max_length]
        
        # Remove potential script injections
        script_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe',
            r'<embed',
            r'<object'
        ]
        
        for pattern in script_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Escape special characters
        text = html.escape(text)
        
        return text
    
    def validate_profile_name(self, name):
        """Validate profile name for security"""
        
        # Allow only alphanumeric and basic punctuation
        if not re.match(r'^[a-zA-Z0-9\s\-_.]{1,50}$', name):
            raise ValueError("Invalid profile name")
        
        # Prevent directory traversal
        if '..' in name or '/' in name or '\\' in name:
            raise ValueError("Invalid characters in profile name")
        
        return name
```

## Network Security

### Offline Enforcement

```python
class OfflineEnforcement:
    """Ensure system remains offline"""
    
    def __init__(self):
        self.allowed_hosts = ['localhost', '127.0.0.1', '::1']
        
    def block_external_connections(self):
        """Block all external network connections"""
        
        # Platform-specific firewall rules
        if platform.system() == 'Windows':
            self.configure_windows_firewall()
        elif platform.system() == 'Darwin':  # macOS
            self.configure_macos_firewall()
        elif platform.system() == 'Linux':
            self.configure_linux_firewall()
    
    def configure_windows_firewall(self):
        """Configure Windows Firewall rules"""
        rules = [
            'netsh advfirewall firewall add rule name="Sunflower_Block_Out" dir=out action=block program="%CD%\\sunflower.exe"',
            'netsh advfirewall firewall add rule name="Sunflower_Allow_Local" dir=in action=allow protocol=TCP localport=8080 remoteip=127.0.0.1'
        ]
        
        for rule in rules:
            # Split command into list to avoid shell injection
            cmd_parts = rule.split()
            subprocess.run(cmd_parts, check=False)
    
    def monitor_network_attempts(self):
        """Log any network connection attempts"""
        
        def packet_callback(packet):
            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                
                # Check if external connection attempt
                if dst_ip not in self.allowed_hosts:
                    self.log_security_event("EXTERNAL_CONNECTION_ATTEMPT", {
                        "source": src_ip,
                        "destination": dst_ip,
                        "blocked": True
                    })
        
        # Monitor but don't actually block (passive monitoring)
        # sniff(filter="tcp", prn=packet_callback, store=0)
```

## Audit & Logging

### Security Event Logging

```python
class SecurityAuditLog:
    """Comprehensive security event logging"""
    
    def __init__(self, log_path):
        self.log_path = log_path
        self.encryption = DataEncryption()
        
    def log_security_event(self, event_type, details):
        """Log security-relevant events"""
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
            "session_id": self.get_current_session_id(),
            "profile_id": self.get_current_profile_id(),
            "system_info": self.get_system_info()
        }
        
        # Encrypt sensitive log data
        encrypted_event = self.encryption.encrypt_profile_data(event)
        
        # Append to audit log
        with open(self.log_path / "security.audit", "ab") as f:
            f.write(encrypted_event + b"\n")
        
        # Alert parent for critical events
        if self.is_critical_event(event_type):
            self.alert_parent(event)
    
    def is_critical_event(self, event_type):
        """Determine if event requires parent alert"""
        
        critical_events = [
            "INTEGRITY_FAILURE",
            "SESSION_HIJACK_ATTEMPT",
            "ISOLATION_VIOLATION",
            "REPEATED_SAFETY_VIOLATION",
            "BYPASS_ATTEMPT",
            "UNAUTHORIZED_ACCESS"
        ]
        
        return event_type in critical_events
```

## Incident Response

### Automated Response System

```python
class IncidentResponse:
    """Automated security incident response"""
    
    def __init__(self):
        self.incident_thresholds = {
            "safety_violations": 3,
            "access_attempts": 5,
            "integrity_failures": 1
        }
        self.incident_counts = {}
        
    def handle_incident(self, incident_type, severity, details):
        """Respond to security incidents"""
        
        # Track incident count
        self.incident_counts[incident_type] = \
            self.incident_counts.get(incident_type, 0) + 1
        
        # Determine response based on severity
        if severity == "CRITICAL":
            self.critical_response(incident_type, details)
        elif severity == "HIGH":
            self.high_response(incident_type, details)
        elif severity == "MEDIUM":
            self.medium_response(incident_type, details)
        else:
            self.low_response(incident_type, details)
        
        # Check thresholds
        self.check_thresholds(incident_type)
    
    def critical_response(self, incident_type, details):
        """Response to critical security incidents"""
        
        # 1. Immediate system lockdown
        self.lockdown_system()
        
        # 2. Preserve evidence
        self.preserve_evidence(details)
        
        # 3. Alert parent immediately
        self.immediate_parent_alert(incident_type, details)
        
        # 4. Require parent authentication to continue
        self.require_parent_unlock()
    
    def lockdown_system(self):
        """Emergency system lockdown"""
        
        # Terminate all sessions
        self.terminate_all_sessions()
        
        # Disable all profiles
        self.disable_all_profiles()
        
        # Stop all services
        self.stop_all_services()
        
        # Display security message
        self.display_security_message()
```

## Security Best Practices

### Development Security

```python
# Security checklist for developers

SECURITY_CHECKLIST = [
    "Never log sensitive information",
    "Always validate and sanitize inputs",
    "Use cryptographically secure random numbers",
    "Implement proper error handling without info leakage",
    "Follow principle of least privilege",
    "Encrypt all sensitive data at rest",
    "Use constant-time comparisons for security checks",
    "Implement rate limiting for all operations",
    "Regular security audits and updates",
    "Penetration testing before releases"
]
```

### Deployment Security

```yaml
# Deployment security configuration

deployment_security:
  signing:
    - Sign all executables
    - Verify signatures on launch
    - Use code signing certificate
  
  permissions:
    - Minimum required privileges
    - No admin rights needed for operation
    - Read-only system partition
  
  isolation:
    - Process isolation
    - Memory isolation
    - File system isolation
  
  verification:
    - Checksum verification
    - Integrity monitoring
    - Tamper detection
```

## Security Testing

### Penetration Testing Checklist

```python
# Security testing scenarios

SECURITY_TESTS = [
    # Authentication tests
    "Brute force parent password",
    "Session hijacking attempts",
    "Token prediction attacks",
    
    # Data protection tests
    "Profile data access without auth",
    "Cross-profile data leakage",
    "Encryption bypass attempts",
    
    # Content security tests
    "Malicious input injection",
    "Safety filter bypass",
    "Age verification spoofing",
    
    # System security tests
    "File system traversal",
    "Privilege escalation",
    "Code injection attempts"
]
```

---

*Security is paramount in Sunflower AI. These implementations ensure children's safety and family privacy while maintaining system integrity.*

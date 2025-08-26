# Sunflower AI Configuration Directory

## Overview

This directory contains all configuration files for the Sunflower AI Professional System. The configuration is designed for a **partitioned device architecture** where system files reside on a read-only CD-ROM partition and user data on a writable USB partition.

## Configuration Files

### Core Configuration

#### 1. `__init__.py`
- **Purpose**: Main configuration module and manager
- **Key Features**:
  - Automatic partition detection (CD-ROM and USB)
  - Hardware tier detection for model optimization
  - Configuration merging (system defaults + user overrides)
  - Export/import functionality for backups
- **Usage**:
```python
from config import get_config
config = get_config()
optimal_model = config.get_optimal_model()
```

#### 2. `default.env`
- **Purpose**: System-wide environment variables
- **Format**: Key-value pairs with comments
- **Categories**:
  - System configuration (app name, version, debug settings)
  - Security settings (authentication, encryption)
  - Partition configuration (markers, sizes)
  - Open WebUI settings (host, port, auth)
  - Ollama configuration (API, models)
  - Safety and content filtering
  - Performance tuning
- **Note**: These are defaults; user overrides are stored on USB partition

#### 3. `version.json`
- **Purpose**: Version tracking and compatibility management
- **Contents**:
  - Application version and build information
  - Compatibility matrices (OS, Python, hardware)
  - Feature flags and capabilities
  - Changelog and support information
- **Critical for**: Ensuring backward compatibility and upgrade paths

### Family and Safety Configuration

#### 4. `family_settings.yaml`
- **Purpose**: Family profile and child safety configuration
- **Structure**:
  - Default family settings template
  - Child profile schema with age-appropriate settings
  - Safety rules and content boundaries
  - Learning configuration and progress tracking
  - Achievement system definitions
- **Storage**: Template on CD-ROM, actual profiles on USB
- **Features**:
  - Age-based response adaptation
  - Per-child safety overrides
  - Session time limits
  - Parent notification settings

#### 5. `safety_patterns.json`
- **Purpose**: Content safety filter patterns
- **Categories**:
  - Violence, inappropriate content, personal information
  - Dangerous activities, self-harm, scary content
  - Commercial content, profanity
- **Features**:
  - Regex-based pattern matching
  - Severity levels and escalation thresholds
  - Age-specific adjustments
  - Educational exemptions for legitimate topics
- **Critical for**: Child safety and COPPA compliance

### Model and Hardware Configuration

#### 6. `model_mapping.yaml`
- **Purpose**: Maps hardware capabilities to optimal AI models
- **Tiers**:
  - **High-end**: 16GB+ RAM, 8GB+ VRAM → llama3.2:7b
  - **Mid-range**: 8GB+ RAM, 4GB+ VRAM → llama3.2:3b
  - **Low-end**: 4GB+ RAM → llama3.2:1b
  - **Minimum**: 2GB+ RAM → llama3.2:1b-q4_0
- **Features**:
  - Automatic hardware detection
  - Performance optimization settings
  - Fallback strategies
  - Model aliasing (sunflower-kids, sunflower-educator)

#### 7. `model_registry.json`
- **Purpose**: Registry of all available AI models
- **Contents**:
  - Model specifications (size, parameters, requirements)
  - File paths and checksums
  - Performance metrics
  - Compatibility information
- **Usage**: Model validation, selection, and loading

### Security Configuration

#### 8. `security_config.yaml`
- **Purpose**: Comprehensive security settings
- **Sections**:
  - Authentication (parent/child auth, PINs, sessions)
  - Encryption (AES-256-GCM for sensitive data)
  - Access control (RBAC, audit trails)
  - Content security (input validation, sanitization)
  - System security (process isolation, integrity checks)
  - Incident response procedures
- **Compliance**: COPPA, FERPA, security best practices

### System Configuration

#### 9. `partition_layout.json`
- **Purpose**: Defines dual-partition USB structure
- **Partitions**:
  - **Partition 1**: 4GB CD-ROM (ISO9660, read-only)
    - System files, models, documentation
  - **Partition 2**: 12GB Data (FAT32, read-write)
    - User profiles, conversations, logs
- **Manufacturing**: Step-by-step partition creation process
- **Security**: Integrity verification and tamper detection

#### 10. `logging_config.json`
- **Purpose**: System-wide logging configuration
- **Log Types**:
  - System logs (general operation)
  - Safety logs (content filtering, incidents)
  - Conversation logs (AI interactions)
  - Audit logs (security events)
  - Performance logs (metrics, optimization)
- **Features**:
  - Rotation policies and retention periods
  - Encryption for sensitive logs
  - Parent dashboard integration
  - Compliance tracking (COPPA, FERPA)

#### 11. `manufacturing_config.json`
- **Purpose**: Production and quality control settings
- **Contents**:
  - Device specifications and approved hardware
  - Batch configuration and serial numbering
  - Quality control test suite
  - Automation workflows
  - Compliance and certification requirements
- **Usage**: Manufacturing partner guidance and QC validation

## Configuration Loading Order

1. **System Startup**:
   ```
   1. Detect partitions (CD-ROM and USB)
   2. Load default.env from CD-ROM
   3. Load version.json for compatibility check
   4. Initialize ConfigurationManager
   ```

2. **Runtime Configuration**:
   ```
   1. Load system configs from CD-ROM (read-only)
   2. Load/create user configs on USB (read-write)
   3. Merge configurations (user overrides system)
   4. Apply hardware detection for model selection
   ```

3. **Profile Loading**:
   ```
   1. Load family_settings.yaml template from CD-ROM
   2. Load actual family profiles from USB
   3. Apply safety_patterns.json filters
   4. Initialize per-child settings
   ```

## Directory Structure

```
config/
├── __init__.py              # Configuration manager module
├── default.env              # Environment variables
├── version.json             # Version and compatibility
├── family_settings.yaml     # Family profile template
├── safety_patterns.json     # Content safety filters
├── model_mapping.yaml       # Hardware to model mapping
├── model_registry.json      # AI model registry
├── security_config.yaml     # Security settings
├── partition_layout.json    # USB partition structure
├── logging_config.json      # Logging configuration
├── manufacturing_config.json # Production settings
└── README.md               # This file
```

## Security Considerations

1. **Read-Only System Configs**: All system configuration files reside on the CD-ROM partition, preventing tampering
2. **Encrypted User Data**: Sensitive user configurations are encrypted on the USB partition
3. **Configuration Validation**: All configs are validated against schemas on load
4. **Audit Trail**: Configuration changes are logged to audit logs
5. **Integrity Checks**: Checksums verify configuration file integrity

## Development vs Production

### Development Mode
- Configs loaded from local filesystem
- Debug logging enabled
- Safety filters can be bypassed for testing
- Mock hardware detection available

### Production Mode
- Configs loaded from CD-ROM partition
- User data on USB partition only
- All safety filters enforced
- Real hardware detection required

## Best Practices

1. **Never modify CD-ROM configs** - They are read-only by design
2. **Backup user configs regularly** - Automated backups to USB partition
3. **Validate after changes** - Use built-in validation before deployment
4. **Test on target hardware** - Ensure model mapping works correctly
5. **Review safety patterns** - Keep content filters up-to-date

## Troubleshooting

### Common Issues

1. **Configuration not found**:
   - Check partition detection in logs
   - Verify marker files exist (sunflower_cd.id, sunflower_data.id)

2. **Model selection incorrect**:
   - Review hardware detection results
   - Check model_mapping.yaml tiers
   - Verify available RAM/VRAM

3. **Safety filter too restrictive**:
   - Review safety_patterns.json
   - Check age group settings in family_settings.yaml
   - Consider educational exemptions

4. **Performance issues**:
   - Check selected hardware tier
   - Review performance settings in model_mapping.yaml
   - Monitor logs for bottlenecks

## Configuration Updates

Since the system is designed for **zero-maintenance**:
- Configuration updates require new device purchase
- No over-the-air updates supported
- User data can be migrated between devices
- Version compatibility ensured through version.json

## Support

This is a **no-support product**. Configuration documentation is comprehensive and self-contained. For configuration questions:
1. Review this README
2. Check inline comments in configuration files
3. Consult the user manual on CD-ROM
4. Use built-in help system in the application

---

**Copyright © 2025 Sunflower AI. All rights reserved.**

Configuration files are part of the Sunflower AI Professional System and may not be modified or redistributed without authorization.

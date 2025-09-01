# Sunflower AI Professional System - Manufacturing Documentation
Version 6.2.0 | Production Release | January 2025

## CRITICAL PRODUCTION INFORMATION

This document contains essential information for manufacturing the Sunflower AI Professional System partitioned USB devices. All personnel must read and understand these procedures before beginning production.

## Device Architecture

The Sunflower AI system uses a dual-partition USB device:
- **CD-ROM Partition (Read-Only)**: 3-4GB containing system files, AI models, and applications
- **USB Partition (Writable)**: 500MB-1GB for user data and profiles

## Production Environment Setup

### Required Tools and Software

1. **Operating System Requirements**
   - Windows 10/11 Pro (64-bit) OR
   - macOS 11.0+ (Big Sur or later)
   - Minimum 16GB RAM for production systems
   - 100GB free disk space for master files

2. **Python Environment**
   ```
   Python 3.9+ (64-bit)
   Required packages: See production/requirements.txt
   ```

3. **USB Device Requirements**
   - USB 3.0+ devices (minimum 8GB capacity)
   - Verified vendor list in config/approved_vendors.json
   - Quality rating: A+ grade or higher

4. **Platform-Specific Tools**

   **Windows:**
   - ImDisk Virtual Disk Driver v2.0.10+
   - Rufus 3.21+ (for hybrid ISO creation)
   - Windows ADK (Assessment and Deployment Kit)
   
   **macOS:**
   - Xcode Command Line Tools
   - hdiutil (included with macOS)
   - diskutil (included with macOS)

## Production Workflow

### Phase 1: Preparation
```
1. Verify master files integrity
   python scripts/validate_master_files.py
   
2. Initialize production batch
   python production/batch_generator.py --batch-size 100 --platform universal
   
3. Prepare USB devices
   - Insert devices into production hub
   - Run device detection: python scripts/detect_devices.py
```

### Phase 2: Device Creation
```
1. Create CD-ROM partition
   python production/create_iso.py --batch-id [BATCH_ID] --platform [PLATFORM]
   
2. Prepare USB partition
   python production/prepare_usb_partition.py --batch-id [BATCH_ID]
   
3. Deploy to physical devices
   python scripts/build_master_usb.py --batch-id [BATCH_ID] --validate
```

### Phase 3: Quality Control
```
1. Automated validation (every device)
   python scripts/validate_usb.py --device [DEVICE_PATH] --full-check
   
2. Manual spot checks (10% sampling)
   - Boot test on reference hardware
   - Profile creation test
   - Model loading verification
   
3. Generate production report
   python scripts/manufacturing_report.py --batch-id [BATCH_ID]
```

## Master Files Structure

```
master_files/
├── current/
│   ├── windows/
│   │   ├── launcher/          # Windows launcher executable
│   │   ├── ollama/           # Ollama installation files
│   │   ├── models/           # Pre-built AI models
│   │   └── manifests/        # Security manifests
│   ├── macos/
│   │   ├── launcher.app/     # macOS launcher application
│   │   ├── ollama/           # Ollama for macOS
│   │   ├── models/           # Pre-built AI models
│   │   └── manifests/        # Security manifests
│   └── shared/
│       ├── documentation/    # User guides and manuals
│       ├── modelfiles/       # Sunflower AI modelfiles
│       └── certificates/    # Code signing certificates
```

## Model Variants

Each device includes ALL model variants for automatic hardware detection:

| Model | Size | RAM Required | Use Case |
|-------|------|--------------|----------|
| llama3.2:7b | 4.7GB | 8GB+ | High-end systems |
| llama3.2:3b | 2.0GB | 6GB+ | Mid-range systems |
| llama3.2:1b | 1.3GB | 4GB+ | Low-end systems |
| llama3.2:1b-q4_0 | 0.7GB | 2GB+ | Minimum spec |

## Security Requirements

### Authentication Tokens
Each device receives a unique hardware token during manufacturing:
```python
token = generate_hardware_token(device_id, SECRET_KEY)
```

### Checksum Validation
All files must pass SHA-256 checksum validation:
```python
checksum = calculate_checksum(file_path, 'sha256')
```

### Partition Security
- CD-ROM partition: Set as read-only at filesystem level
- USB partition: Encrypted family data storage

## Quality Control Standards

### Acceptance Criteria
- **Boot Success Rate**: 100% on reference hardware
- **Profile Creation**: < 5 seconds
- **Model Loading**: < 30 seconds on minimum spec
- **Checksum Validation**: 100% pass rate

### Failure Handling
1. Device fails validation → Remove from batch
2. Batch failure rate > 5% → Stop production
3. Critical error → Alert production manager immediately

## Batch Tracking

Every batch must maintain complete traceability:

```json
{
  "batch_id": "2025011501",
  "timestamp": "2025-01-15T09:00:00Z",
  "platform": "universal",
  "devices_total": 100,
  "devices_passed": 98,
  "devices_failed": 2,
  "operator_id": "PROD_001",
  "qc_samples": 10,
  "qc_passed": 10
}
```

## Error Codes

| Code | Description | Action |
|------|-------------|--------|
| E001 | Partition creation failed | Retry with new device |
| E002 | Checksum mismatch | Verify master files |
| E003 | Hardware token invalid | Check secret key |
| E004 | Model deployment failed | Check disk space |
| E005 | Validation timeout | Test on reference hardware |

## Production Commands Reference

### Create Single Device
```bash
python production/create_iso.py \
    --device-path /dev/disk2 \
    --platform universal \
    --model-variant auto \
    --validate
```

### Batch Production
```bash
python production/batch_generator.py \
    --batch-size 100 \
    --platform universal \
    --output-dir output/batch_20250115 \
    --parallel 4
```

### Quality Control Check
```bash
python scripts/validate_usb.py \
    --device /dev/disk2 \
    --checks all \
    --report output/validation_report.json
```

### Generate Production Report
```bash
python scripts/manufacturing_report.py \
    --batch-id 2025011501 \
    --format pdf \
    --output reports/batch_2025011501.pdf
```

## Troubleshooting

### Common Issues

1. **"Device not recognized"**
   - Verify USB 3.0+ compatibility
   - Check device capacity (minimum 8GB)
   - Try different USB port

2. **"Partition creation failed"**
   - Ensure device is not mounted
   - Check for bad sectors: `chkdsk /f` (Windows) or `diskutil verifyDisk` (macOS)
   - Replace device if errors persist

3. **"Model deployment timeout"**
   - Verify USB 3.0 connection
   - Check available disk space
   - Test write speed: should exceed 10MB/s

4. **"Checksum validation failed"**
   - Re-download master files
   - Verify no corruption during transfer
   - Check production system integrity

## Contact Information

**Production Support**
- Internal: ext. 5555
- Email: production@sunflowerai.internal
- Emergency: +1-555-PROD-911

**Quality Control**
- Internal: ext. 5556
- Email: qc@sunflowerai.internal

**Engineering**
- Internal: ext. 5557
- Email: engineering@sunflowerai.internal

## Compliance and Certification

- ISO 9001:2015 Certified Process
- COPPA Compliant (Children's Privacy)
- FCC Part 15 Class B (Digital Device)
- CE Marking (European Conformity)
- RoHS Compliant (Hazardous Substances)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 6.2.0 | 2025-01-15 | Partitioned device architecture |
| 6.1.0 | 2024-12-01 | Multi-model support added |
| 6.0.0 | 2024-10-15 | Initial production release |

---

**CONFIDENTIAL - INTERNAL USE ONLY**
This document contains proprietary information and trade secrets of Sunflower AI Corporation.
Unauthorized distribution is strictly prohibited.

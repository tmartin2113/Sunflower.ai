# Sunflower AI Production Scripts

Production-ready manufacturing tools for creating Sunflower AI Professional System USB devices.

## Overview

These scripts handle the complete manufacturing process for Sunflower AI's dual-partition USB drives:
- **CD-ROM Partition**: Read-only partition containing the application and AI models
- **Data Partition**: Writable partition for user profiles and data

## Prerequisites

### Software Requirements
- Python 3.8 or higher
- Git (for version control)
- ISO creation tools:
  - **Windows**: Windows ADK (for oscdimg.exe)
  - **macOS/Linux**: cdrtools (mkisofs/genisoimage)

### Hardware Requirements
- 16GB+ RAM recommended for building large ISOs
- 100GB+ free disk space
- USB 3.0 ports for testing

### Installation

```bash
# Clone repository
git clone https://github.com/sunflowerai/sunflower-ai.git
cd sunflower-ai

# Install production dependencies
pip install -r production/requirements.txt

# Build prerequisite components
python build/compile_windows.py
python build/compile_macos.py
python build/create_models.py
```

## Quick Start

### 1. Generate a Complete Batch (Recommended)

```bash
# Generate a batch of 100 units
python -m production.batch_generator --size 100 --version 1.0.0
```

This creates:
- Master ISO file for CD-ROM partition
- Master USB image for data partition  
- Serial numbers for all units
- Complete documentation package
- Quality control materials

### 2. Create Individual Components

```bash
# Create ISO only
python production/create_iso.py --version 1.0.0

# Prepare USB partition only
python production/prepare_usb_partition.py --size 1024
```

## Production Workflow

### Step 1: Pre-Production
1. Ensure all source code is compiled and tested
2. Verify AI models are created and optimized
3. Review version numbers and batch sizing

### Step 2: Generate Master Files
```bash
# Standard production batch
python -m production.batch_generator --size 100

# Small test batch
python -m production.batch_generator --size 10 --version 1.0.0-test
```

### Step 3: Pilot Production
1. Produce 5-10 units using master files
2. Run quality control on each unit
3. Test on multiple systems
4. Verify both partitions work correctly

### Step 4: Mass Production
1. Use professional USB duplicator
2. Create both partitions according to specifications
3. Write ISO to partition 1 (set as read-only/CD-ROM)
4. Write USB image to partition 2 (keep writable)
5. Apply serial number labels

### Step 5: Quality Control
```bash
# Run automated QC test
python qc_test_script.py SF100-20240115-0001

# Verify results
cat qc_report_SF100-20240115-0001.json
```

### Step 6: Packaging
1. Follow packaging_checklist.md
2. Include all printed materials
3. Apply security seals
4. Box and prepare for shipping

## File Structure

```
manufacturing/
├── batches/
│   └── BATCH-20240115-001/
│       ├── master_files/
│       │   ├── sunflower_ai_v1.0.0_*.iso
│       │   └── sunflower_data_*.img
│       ├── documentation/
│       │   ├── duplication_instructions.md
│       │   ├── serial_numbers.csv
│       │   └── packaging_checklist.md
│       └── quality_control/
│           ├── qc_test_script.py
│           └── qc_checklist_template.md
├── iso_images/
├── usb_images/
└── batch_records/
```

## USB Specifications

### Partition Layout
| Partition | Type | Size | Filesystem | Contents |
|-----------|------|------|------------|----------|
| 1 | CD-ROM | 4-8GB | ISO9660/UDF | Application, Models |
| 2 | Data | 8GB+ | FAT32 | User Data |

### Required Features
- USB 3.0 or higher
- Dual-partition support
- CD-ROM emulation capability
- Minimum 16GB total capacity

## Troubleshooting

### ISO Creation Fails
- Ensure all models are built: `python build/create_models.py`
- Check available disk space (need 2x ISO size)
- Verify oscdimg.exe (Windows) or mkisofs (Unix) installed

### USB Image Issues
- Use FAT32 for maximum compatibility
- Ensure partition size doesn't exceed FAT32 limits
- Test on both Windows and macOS

### Quality Control Failures
- Verify USB device quality (use reputable brands)
- Check USB 3.0 compatibility
- Ensure proper partition alignment

## Security Notes

- Each batch has unique authentication tokens
- Serial numbers are cryptographically generated
- CD-ROM partition must be truly read-only
- Never distribute master files publicly

## Support

**Manufacturing Support**: mfg-support@sunflowerai.com  
**Technical Issues**: tech@sunflowerai.com  
**Emergency**: +1-555-SUNFLOW

## License

Copyright © 2025 Sunflower AI. All rights reserved.
These tools are for authorized manufacturing partners only.
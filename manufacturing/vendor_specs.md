# Sunflower AI USB Manufacturing Specifications

**Document Version**: 1.0  
**Product**: Sunflower AI Professional System  
**Date**: January 2025

## Executive Summary

Sunflower AI requires high-quality USB devices with dual-partition capability for our educational software system. Each device contains a read-only CD-ROM partition with our application and a writable partition for user data.

## Technical Requirements

### USB Device Specifications

#### Minimum Requirements
- **Capacity**: 16GB (usable after formatting)
- **Interface**: USB 3.0 (USB 3.1/3.2 compatible)
- **Speed Class**: Minimum 80MB/s read, 40MB/s write
- **Controller**: Must support dual-partition with CD-ROM emulation
- **Form Factor**: Standard USB-A (no micro/mini USB)
- **Operating Temperature**: 0°C to 60°C
- **Durability**: 10,000+ insertion cycles

#### Recommended Specifications
- **Capacity**: 32GB for future expansion
- **Interface**: USB 3.1 Gen 1 or higher
- **Speed**: 150MB/s+ read, 80MB/s+ write
- **LED Indicator**: Activity LED preferred
- **Casing**: Metal or high-quality plastic
- **Warranty**: 5 years

### Partition Requirements

| Partition | Size | Type | Filesystem | Access |
|-----------|------|------|------------|---------|
| Partition 1 | 4-8GB | CD-ROM | ISO9660/UDF | Read-Only |
| Partition 2 | Remaining | Normal | FAT32 | Read-Write |

### Critical Features
1. **CD-ROM Emulation**: First partition MUST appear as CD-ROM drive
2. **Auto-Detection**: Both partitions must auto-mount on Windows/macOS
3. **No Additional Software**: Must not require drivers or utilities
4. **Security**: Write-protection on Partition 1 must be hardware-enforced

## Manufacturing Process

### 1. Device Preparation
- Low-level format if previously used
- Verify device meets speed requirements
- Check for bad blocks

### 2. Partition Creation
```
Partition 1: CD-ROM Partition
- Start: Sector 0
- Size: Exactly as specified in batch order
- Type: CD-ROM (Type 0x96)
- Bootable: Yes
- Write-Protected: Yes (hardware level)

Partition 2: Data Partition  
- Start: After Partition 1
- Size: Remaining space
- Type: FAT32 (Type 0x0C)
- Bootable: No
- Write-Protected: No
```

### 3. Data Writing
- Use master files provided for each batch
- Verify checksums after writing
- No modification of master files permitted

### 4. Validation
- Each unit must pass our QC test script
- Both partitions must be detected on test systems
- Read/write speeds must meet specifications

## Quality Standards

### Acceptable Defect Rates
- DOA (Dead on Arrival): < 0.1%
- Early Failure (30 days): < 0.5%
- 1-Year Failure: < 2%

### Testing Requirements
1. **100% Testing**: Every unit must be tested
2. **Speed Test**: Verify meets minimum speeds
3. **Partition Test**: Both partitions detected
4. **Data Integrity**: Checksum verification
5. **Compatibility**: Test on Windows 10/11 and macOS

### Rejection Criteria
- Failed speed requirements
- Partition detection issues
- Physical damage or defects
- Incorrect capacity
- CD-ROM partition writable

## Labeling and Packaging

### USB Label Requirements
- Size: 25mm x 10mm (adjust to fit device)
- Material: Waterproof, fade-resistant
- Adhesive: Permanent, residue-free
- Content: Serial number, batch ID, QR code
- Placement: Top surface, aligned center

### Individual Packaging
- Anti-static bag or case
- Foam insert for protection
- Must prevent damage during shipping

### Bulk Packaging
- Maximum 50 units per box
- Layer separation required
- Moisture protection included
- Clear batch labeling

## Serial Number Format

```
SF[VERSION]-[BATCH]-[UNIT]
Example: SF100-20240115-0042
```

- SF: Product identifier
- VERSION: 3 digits (100 = v1.0.0)
- BATCH: 8 characters (date + ID)
- UNIT: 4 digits (padded)

## Delivery Requirements

### Shipping
- Climate-controlled transport required
- Maximum stacking: 10 boxes high
- Shock indicators on master cartons
- Tracking required for all shipments

### Documentation per Batch
1. Certificate of Conformity
2. Test reports for sampled units
3. Serial number manifest (digital)
4. Defect report (if any)
5. Shipping tracking information

## Order Specifications

### Minimum Order Quantity
- Pilot: 100 units
- Production: 1,000 units
- Reorder: 500 units

### Lead Times
- Sample approval: 5 business days
- Pilot production: 10 business days
- Full production: 15-20 business days

### Payment Terms
- 30% deposit upon order confirmation
- 70% upon passed QC and before shipping
- NET 30 for established partners

## Approved Vendors List

### USB Controllers (Required CD-ROM Support)
- Phison PS2251-07
- SMI SM3267
- Alcor AU6989SN
- *Note: Other controllers subject to approval*

### Recommended Manufacturers
- SanDisk (OEM division)
- Kingston (OEM division)
- PNY (OEM division)
- Certified contract manufacturers

## Contact Information

**Production Manager**: production@sunflowerai.com  
**Quality Assurance**: qa@sunflowerai.com  
**Technical Support**: mfg-tech@sunflowerai.com  
**Emergency Hotline**: +1-555-SUNFLOW

## Compliance

All devices must comply with:
- FCC Part 15 (USA)
- CE marking (Europe)
- RoHS directive
- REACH regulation
- CPSIA (children's product safety)

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-15 | Initial release |

---

**Confidential**: This document contains proprietary information of Sunflower AI.
Distribution limited to authorized manufacturing partners only.

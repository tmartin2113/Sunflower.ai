#!/usr/bin/env python3
"""
Batch Manufacturing Generator for Sunflower AI Professional System
Orchestrates the complete manufacturing process for production batches.

This script coordinates ISO creation, USB preparation, quality validation,
and generates all necessary documentation for manufacturing partners.
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import hashlib
import secrets
import csv
import zipfile
import time
import traceback
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Import our production modules
sys.path.append(str(Path(__file__).parent.parent))
from production.create_iso import ISOCreator
from production.prepare_usb_partition import USBPartitionPreparer


class DeviceStatus(Enum):
    """Status of individual device in batch"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    SKIPPED = "skipped"


@dataclass
class DeviceResult:
    """Result of individual device production"""
    device_id: str
    status: DeviceStatus
    attempts: int = 0
    errors: List[str] = field(default_factory=list)
    iso_path: Optional[Path] = None
    usb_path: Optional[Path] = None
    completion_time: Optional[datetime] = None
    duration_seconds: float = 0


class BatchManufacturingGenerator:
    def __init__(self, batch_size=100, version="1.0.0", max_retries=3, continue_on_error=True):
        self.root_dir = Path(__file__).parent.parent
        self.batch_size = batch_size
        self.version = version
        self.batch_id = self.generate_batch_id()
        self.start_time = datetime.now()
        
        # FIX BUG-015: Add error recovery configuration
        self.max_retries = max_retries
        self.continue_on_error = continue_on_error
        self.device_results = {}  # Track individual device results
        self.failed_devices = []  # Track failed devices for retry
        self.successful_devices = []  # Track successful devices
        
        # Paths
        self.manufacturing_dir = self.root_dir / "manufacturing"
        self.batch_dir = self.manufacturing_dir / "batches" / self.batch_id
        self.master_dir = self.batch_dir / "master_files"
        self.docs_dir = self.batch_dir / "documentation"
        self.qc_dir = self.batch_dir / "quality_control"
        self.recovery_dir = self.batch_dir / "recovery"  # For failed device recovery
        
        # Components
        self.iso_path = None
        self.usb_image_path = None
        self.batch_manifest = {
            "batch_id": self.batch_id,
            "version": self.version,
            "size": batch_size,
            "created": self.start_time.isoformat(),
            "components": {},
            "quality_checks": {},
            "production_files": [],
            "device_results": {},  # Track individual results
            "statistics": {
                "total": batch_size,
                "successful": 0,
                "failed": 0,
                "retried": 0,
                "skipped": 0
            }
        }
    
    def generate_batch_id(self):
        """Generate unique batch identifier"""
        timestamp = datetime.now().strftime("%Y%m%d")
        sequence = self._get_daily_sequence()
        return f"BATCH-{timestamp}-{sequence:03d}"
    
    def _get_daily_sequence(self):
        """Get the next sequence number for today's batches"""
        sequence_file = self.manufacturing_dir / ".sequence" / f"{datetime.now().strftime('%Y%m%d')}.seq"
        sequence_file.parent.mkdir(parents=True, exist_ok=True)
        
        if sequence_file.exists():
            sequence = int(sequence_file.read_text()) + 1
        else:
            sequence = 1
        
        sequence_file.write_text(str(sequence))
        return sequence
    
    def generate(self):
        """Main batch generation process with error recovery"""
        print(f"🏭 Sunflower AI Batch Manufacturing Generator")
        print(f"📦 Batch ID: {self.batch_id}")
        print(f"🔢 Batch Size: {self.batch_size} units")
        print(f"📌 Version: {self.version}")
        print(f"🔄 Max Retries: {self.max_retries}")
        print(f"⚡ Continue on Error: {self.continue_on_error}")
        print("=" * 60)
        
        # FIX BUG-015: Initialize device tracking
        for i in range(self.batch_size):
            device_id = f"{self.batch_id}-{i+1:04d}"
            self.device_results[device_id] = DeviceResult(
                device_id=device_id,
                status=DeviceStatus.PENDING
            )
        
        try:
            # Create batch directory structure
            print("\n📁 Setting up batch directories...")
            self.setup_batch_directories()
            
            # Pre-flight validation
            print("\n✓ Running pre-flight checks...")
            if not self.validate_prerequisites():
                if not self.continue_on_error:
                    return False
                print("⚠️  Warning: Prerequisites check failed, continuing anyway...")
            
            # FIX BUG-015: Process devices with error recovery
            print("\n🏭 Starting device production...")
            self._process_devices_with_recovery()
            
            # Generate production files for successful devices
            if self.successful_devices:
                print("\n📄 Generating production files...")
                self.generate_production_files()
                
                # Create quality control materials
                print("\n🔍 Creating quality control materials...")
                self.create_qc_materials()
            
            # Generate documentation including failure reports
            print("\n📚 Generating manufacturing documentation...")
            self.generate_documentation()
            
            # FIX BUG-015: Handle partial batch completion
            if self.failed_devices and self.successful_devices:
                print("\n⚠️  Partial batch completion detected")
                self._handle_partial_batch()
            
            # Create final production package
            if self.successful_devices:
                print("\n📦 Creating production package...")
                package_path = self.create_production_package()
            else:
                print("\n❌ No successful devices to package")
                package_path = None
            
            # Generate summary report
            print("\n📊 Generating batch report...")
            self.generate_batch_report()
            
            # Final validation
            print("\n✅ Running final validation...")
            validation_passed = self.validate_batch()
            
            # Display results
            self._display_batch_summary()
            
            if validation_passed and self.successful_devices:
                print(f"\n🎉 Batch {self.batch_id} completed!")
                print(f"📍 Location: {self.batch_dir}")
                if package_path:
                    print(f"📦 Production package: {package_path}")
                return True
            else:
                print(f"\n⚠️  Batch {self.batch_id} completed with issues")
                return self.continue_on_error
                
        except Exception as e:
            print(f"\n❌ Critical batch generation error: {e}")
            self._save_recovery_state()
            if not self.continue_on_error:
                traceback.print_exc()
                return False
            print("⚠️  Attempting to continue despite error...")
            return self._attempt_recovery()
    
    def _process_devices_with_recovery(self):
        """
        FIX BUG-015: Process devices with individual error recovery
        """
        pending_devices = [d for d in self.device_results.values() 
                          if d.status == DeviceStatus.PENDING]
        
        for device in pending_devices:
            success = False
            
            for attempt in range(1, self.max_retries + 1):
                try:
                    print(f"\n🔧 Processing device {device.device_id} (Attempt {attempt}/{self.max_retries})")
                    device.status = DeviceStatus.IN_PROGRESS
                    device.attempts = attempt
                    
                    # Process individual device with error handling
                    success = self._process_single_device(device)
                    
                    if success:
                        device.status = DeviceStatus.SUCCESS
                        device.completion_time = datetime.now()
                        self.successful_devices.append(device.device_id)
                        self.batch_manifest["statistics"]["successful"] += 1
                        print(f"✅ Device {device.device_id} completed successfully")
                        break
                    
                except Exception as e:
                    error_msg = f"Attempt {attempt} failed: {str(e)}"
                    device.errors.append(error_msg)
                    print(f"❌ {error_msg}")
                    
                    if attempt < self.max_retries:
                        print(f"🔄 Retrying device {device.device_id}...")
                        time.sleep(2)  # Brief pause before retry
                        self.batch_manifest["statistics"]["retried"] += 1
                    else:
                        # Final attempt failed
                        device.status = DeviceStatus.FAILED
                        self.failed_devices.append(device.device_id)
                        self.batch_manifest["statistics"]["failed"] += 1
                        print(f"❌ Device {device.device_id} failed after {self.max_retries} attempts")
                        
                        # Save device failure details for recovery
                        self._save_device_failure(device)
                        
                        if not self.continue_on_error:
                            raise RuntimeError(f"Device {device.device_id} failed and continue_on_error is False")
            
            # Update manifest with device result
            self.batch_manifest["device_results"][device.device_id] = {
                "status": device.status.value,
                "attempts": device.attempts,
                "errors": device.errors,
                "completion_time": device.completion_time.isoformat() if device.completion_time else None
            }
    
    def _process_single_device(self, device: DeviceResult) -> bool:
        """
        FIX BUG-015: Process a single device with error handling
        
        Args:
            device: Device result object to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            device_start = time.time()
            
            # Build device-specific ISO
            iso_creator = ISOCreator(
                version=self.version,
                batch_id=self.batch_id,
                device_id=device.device_id
            )
            
            # Create ISO with timeout protection
            iso_path = self._create_with_timeout(
                iso_creator.create,
                timeout=300,  # 5 minutes timeout
                error_msg="ISO creation timeout"
            )
            
            if not iso_path or not Path(iso_path).exists():
                raise RuntimeError("ISO creation failed - file not found")
            
            device.iso_path = Path(iso_path)
            
            # Prepare USB partition
            usb_preparer = USBPartitionPreparer(
                batch_id=self.batch_id,
                partition_size_mb=1024
            )
            
            # Create USB with timeout protection
            usb_path = self._create_with_timeout(
                lambda: usb_preparer.prepare(output_format="zip"),
                timeout=180,  # 3 minutes timeout
                error_msg="USB preparation timeout"
            )
            
            if not usb_path or not Path(usb_path).exists():
                raise RuntimeError("USB preparation failed - file not found")
            
            device.usb_path = Path(usb_path)
            
            # Quick validation
            if not self._validate_device_output(device):
                raise RuntimeError("Device output validation failed")
            
            device.duration_seconds = time.time() - device_start
            return True
            
        except Exception as e:
            # Clean up partial files
            self._cleanup_device_files(device)
            raise e
    
    def _create_with_timeout(self, func, timeout: int, error_msg: str):
        """
        FIX BUG-015: Execute function with timeout protection
        """
        import threading
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # Timeout occurred
            raise TimeoutError(error_msg)
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def _validate_device_output(self, device: DeviceResult) -> bool:
        """
        FIX BUG-015: Validate individual device output
        """
        try:
            # Check ISO exists and has minimum size
            if device.iso_path and device.iso_path.exists():
                iso_size = device.iso_path.stat().st_size
                if iso_size < 100 * 1024 * 1024:  # Minimum 100MB
                    return False
            else:
                return False
            
            # Check USB exists and has minimum size
            if device.usb_path and device.usb_path.exists():
                usb_size = device.usb_path.stat().st_size
                if usb_size < 10 * 1024 * 1024:  # Minimum 10MB
                    return False
            else:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _cleanup_device_files(self, device: DeviceResult):
        """
        FIX BUG-015: Clean up partial device files after failure
        """
        try:
            if device.iso_path and device.iso_path.exists():
                device.iso_path.unlink()
            if device.usb_path and device.usb_path.exists():
                device.usb_path.unlink()
        except Exception as e:
            print(f"⚠️  Warning: Failed to cleanup device files: {e}")
    
    def _save_device_failure(self, device: DeviceResult):
        """
        FIX BUG-015: Save device failure information for recovery
        """
        failure_dir = self.recovery_dir / device.device_id
        failure_dir.mkdir(parents=True, exist_ok=True)
        
        failure_info = {
            "device_id": device.device_id,
            "status": device.status.value,
            "attempts": device.attempts,
            "errors": device.errors,
            "timestamp": datetime.now().isoformat(),
            "batch_id": self.batch_id
        }
        
        failure_file = failure_dir / "failure_info.json"
        with open(failure_file, 'w') as f:
            json.dump(failure_info, f, indent=2)
        
        print(f"💾 Saved failure info: {failure_file}")
    
    def _save_recovery_state(self):
        """
        FIX BUG-015: Save entire batch state for recovery
        """
        recovery_file = self.recovery_dir / "batch_recovery.json"
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        
        recovery_state = {
            "batch_id": self.batch_id,
            "timestamp": datetime.now().isoformat(),
            "device_results": {
                device_id: {
                    "status": result.status.value,
                    "attempts": result.attempts,
                    "errors": result.errors
                }
                for device_id, result in self.device_results.items()
            },
            "successful_devices": self.successful_devices,
            "failed_devices": self.failed_devices,
            "batch_manifest": self.batch_manifest
        }
        
        with open(recovery_file, 'w') as f:
            json.dump(recovery_state, f, indent=2)
        
        print(f"💾 Saved recovery state: {recovery_file}")
    
    def _attempt_recovery(self) -> bool:
        """
        FIX BUG-015: Attempt to recover from batch failure
        """
        print("\n🔄 Attempting batch recovery...")
        
        try:
            # Create recovery report
            recovery_report = self.recovery_dir / "recovery_report.txt"
            
            with open(recovery_report, 'w') as f:
                f.write(f"Batch Recovery Report\n")
                f.write(f"Batch ID: {self.batch_id}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
                f.write(f"Successful: {len(self.successful_devices)}\n")
                f.write(f"Failed: {len(self.failed_devices)}\n\n")
                
                if self.successful_devices:
                    f.write("Successful Devices:\n")
                    for device_id in self.successful_devices:
                        f.write(f"  - {device_id}\n")
                
                if self.failed_devices:
                    f.write("\nFailed Devices:\n")
                    for device_id in self.failed_devices:
                        device = self.device_results[device_id]
                        f.write(f"  - {device_id}: {device.errors[-1] if device.errors else 'Unknown error'}\n")
            
            print(f"📄 Recovery report saved: {recovery_report}")
            
            # Package successful devices if any
            if self.successful_devices:
                partial_package = self.batch_dir / f"partial_batch_{len(self.successful_devices)}_devices.zip"
                with zipfile.ZipFile(partial_package, 'w') as zf:
                    for device_id in self.successful_devices:
                        device = self.device_results[device_id]
                        if device.iso_path and device.iso_path.exists():
                            zf.write(device.iso_path, f"{device_id}/iso/{device.iso_path.name}")
                        if device.usb_path and device.usb_path.exists():
                            zf.write(device.usb_path, f"{device_id}/usb/{device.usb_path.name}")
                
                print(f"📦 Partial batch package: {partial_package}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Recovery failed: {e}")
            return False
    
    def _handle_partial_batch(self):
        """
        FIX BUG-015: Handle partial batch completion
        """
        print(f"\n📊 Partial Batch Summary:")
        print(f"  Successful: {len(self.successful_devices)} devices")
        print(f"  Failed: {len(self.failed_devices)} devices")
        print(f"  Success Rate: {len(self.successful_devices)/self.batch_size*100:.1f}%")
        
        # Create retry script for failed devices
        retry_script = self.recovery_dir / "retry_failed_devices.sh"
        
        with open(retry_script, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"# Retry script for batch {self.batch_id}\n\n")
            
            for device_id in self.failed_devices:
                f.write(f"echo 'Retrying device {device_id}...'\n")
                f.write(f"python production/retry_device.py --device-id {device_id} --batch-id {self.batch_id}\n")
                f.write(f"if [ $? -eq 0 ]; then\n")
                f.write(f"  echo '✅ Device {device_id} succeeded'\n")
                f.write(f"else\n")
                f.write(f"  echo '❌ Device {device_id} failed again'\n")
                f.write(f"fi\n\n")
        
        retry_script.chmod(0o755)
        print(f"🔄 Retry script created: {retry_script}")
    
    def _display_batch_summary(self):
        """
        FIX BUG-015: Display comprehensive batch summary
        """
        stats = self.batch_manifest["statistics"]
        
        print("\n" + "=" * 60)
        print("BATCH PRODUCTION SUMMARY")
        print("=" * 60)
        print(f"Batch ID: {self.batch_id}")
        print(f"Total Devices: {stats['total']}")
        print(f"✅ Successful: {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)")
        print(f"❌ Failed: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
        print(f"🔄 Retried: {stats['retried']}")
        print(f"⏭️  Skipped: {stats['skipped']}")
        print(f"Duration: {(datetime.now() - self.start_time).total_seconds():.1f} seconds")
        print("=" * 60)
    
    def setup_batch_directories(self):
        """Create batch directory structure"""
        directories = [
            self.master_dir,
            self.docs_dir,
            self.qc_dir,
            self.recovery_dir,  # Added recovery directory
            self.batch_dir / "logs",
            self.batch_dir / "samples",
            self.batch_dir / "devices"  # Store individual device outputs
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Created batch directory: {self.batch_dir}")
    
    def validate_prerequisites(self):
        """Validate all components are ready for production"""
        checks = {
            "compiled_windows": self.root_dir / "cdrom_staging" / "Windows" / "SunflowerAI.exe",
            "compiled_macos": self.root_dir / "cdrom_staging" / "macOS" / "SunflowerAI.app",
            "models": self.root_dir / "cdrom_staging" / "models",
            "resources": self.root_dir / "resources"
        }
        
        missing = []
        for component, path in checks.items():
            if not path.exists():
                missing.append(f"{component}: {path}")
                print(f"❌ Missing: {component}")
            else:
                print(f"✅ Found: {component}")
        
        if missing:
            print("\n⚠️  Prerequisites not fully met:")
            for item in missing:
                print(f"  - {item}")
            return self.continue_on_error  # Return based on error handling preference
        
        print("✅ All prerequisites validated")
        return True
    
    def create_master_iso(self):
        """Create the master ISO image"""
        try:
            iso_creator = ISOCreator(version=self.version, batch_id=self.batch_id)
            iso_path = iso_creator.create()
            
            if iso_path and Path(iso_path).exists():
                # Copy to master directory
                master_iso = self.master_dir / f"sunflower_master_{self.version}.iso"
                shutil.copy2(iso_path, master_iso)
                
                # Calculate checksum
                checksum = self.calculate_checksum(master_iso)
                self.batch_manifest["components"]["master_iso"] = {
                    "path": str(master_iso),
                    "checksum": checksum,
                    "size_mb": master_iso.stat().st_size / (1024**2)
                }
                
                print(f"✅ Master ISO created: {master_iso}")
                return master_iso
            else:
                raise RuntimeError("ISO creation returned no path")
                
        except Exception as e:
            print(f"❌ ISO creation failed: {e}")
            if not self.continue_on_error:
                raise
            return None
    
    def create_master_usb(self):
        """Create the master USB image"""
        try:
            usb_preparer = USBPartitionPreparer(batch_id=self.batch_id, partition_size_mb=1024)
            usb_path = usb_preparer.prepare(output_format="image")
            
            if usb_path and Path(usb_path).exists():
                # Copy to master directory
                master_usb = self.master_dir / f"sunflower_usb_master_{self.version}.img"
                shutil.copy2(usb_path, master_usb)
                
                # Calculate checksum
                checksum = self.calculate_checksum(master_usb)
                self.batch_manifest["components"]["master_usb"] = {
                    "path": str(master_usb),
                    "checksum": checksum,
                    "size_mb": master_usb.stat().st_size / (1024**2)
                }
                
                print(f"✅ Master USB image created: {master_usb}")
                return master_usb
            else:
                raise RuntimeError("USB preparation returned no path")
                
        except Exception as e:
            print(f"❌ USB creation failed: {e}")
            if not self.continue_on_error:
                raise
            return None
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def generate_production_files(self):
        """Generate production-specific files"""
        # Serial number list
        serial_list = self.docs_dir / "serial_numbers.csv"
        
        with open(serial_list, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Device_ID", "Serial_Number", "MAC_Address", "Status"])
            
            for device_id in self.successful_devices:
                serial = f"SAI{self.batch_id[-6:]}{device_id[-4:]}"
                mac = f"02:42:{secrets.token_hex(1)}:{secrets.token_hex(1)}:{secrets.token_hex(1)}:{secrets.token_hex(1)}"
                writer.writerow([device_id, serial, mac, "READY"])
        
        self.batch_manifest["production_files"].append(str(serial_list))
        
        print(f"✅ Generated {len(self.successful_devices)} serial numbers")
    
    def create_qc_materials(self):
        """Create quality control test materials"""
        # QC checklist
        checklist = self.qc_dir / "qc_checklist.md"
        
        checklist_content = f"""# Quality Control Checklist
## Batch: {self.batch_id}
## Date: {datetime.now().strftime('%Y-%m-%d')}

### Physical Inspection
- [ ] USB device intact, no physical damage
- [ ] Proper labeling and serial number
- [ ] Packaging sealed correctly

### Functional Tests
- [ ] Device recognized by Windows 10
- [ ] Device recognized by Windows 11
- [ ] Device recognized by macOS 11+
- [ ] CD-ROM partition mounts automatically
- [ ] USB partition accessible and writable

### Software Validation
- [ ] Launcher starts automatically
- [ ] All AI models load correctly
- [ ] Parent dashboard accessible
- [ ] Child safety filters working
- [ ] Session logging functional

### Performance Tests
- [ ] USB read speed > 80 MB/s
- [ ] USB write speed > 40 MB/s
- [ ] AI response time < 3 seconds
- [ ] Profile switching < 1 second

### Sample Size
- Minimum: {max(10, int(self.batch_size * 0.1))} devices
- Actual tested: _____ devices

### Results
- [ ] PASS - All tests successful
- [ ] FAIL - Issues found (document below)

### Notes:
_________________________________
_________________________________
_________________________________

Tested by: _________________ Date: _____________
Approved by: _______________ Date: _____________
"""
        
        checklist.write_text(checklist_content)
        self.batch_manifest["quality_checks"]["checklist"] = str(checklist)
        
        print("✅ Created QC checklist")
    
    def generate_documentation(self):
        """Generate manufacturing documentation"""
        # Batch manifest
        manifest_file = self.docs_dir / "batch_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(self.batch_manifest, f, indent=2)
        
        # Production guide
        guide = self.docs_dir / "production_guide.md"
        guide_content = f"""# Production Guide for Batch {self.batch_id}

## Overview
- **Batch ID**: {self.batch_id}
- **Version**: {self.version}
- **Total Units**: {self.batch_size}
- **Successful**: {len(self.successful_devices)}
- **Failed**: {len(self.failed_devices)}
- **Created**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}

## Master Files
- **ISO**: {self.batch_manifest.get('components', {}).get('master_iso', {}).get('path', 'N/A')}
- **USB Image**: {self.batch_manifest.get('components', {}).get('master_usb', {}).get('path', 'N/A')}

## Production Steps
1. **USB Preparation**
   - Use USB 3.0 devices, minimum 8GB capacity
   - Verify devices from approved vendor list

2. **Partition Creation**
   - Use provided tools to create dual partitions
   - CD-ROM: 4GB (read-only)
   - USB: 1GB (writable)

3. **Data Deployment**
   - Write ISO to CD-ROM partition
   - Deploy USB image to writable partition
   - Verify checksums match

4. **Quality Control**
   - Test {max(10, int(self.batch_size * 0.1))} random devices
   - Follow QC checklist for each device
   - Document any failures

5. **Packaging**
   - Apply serial number labels
   - Insert quick start guide
   - Seal in anti-static packaging

## Failed Devices
{self._generate_failure_report()}

## Contact Information
- Technical Support: support@sunflowerai.com
- Production Issues: mfg@sunflowerai.com
- Emergency: +1-555-SUNFLOW
"""
        
        guide.write_text(guide_content)
        
        print("✅ Generated production documentation")
    
    def _generate_failure_report(self) -> str:
        """Generate report of failed devices"""
        if not self.failed_devices:
            return "No failed devices in this batch."
        
        report = []
        report.append(f"Total Failed: {len(self.failed_devices)}")
        report.append("\nDevice Details:")
        
        for device_id in self.failed_devices[:10]:  # Show first 10
            device = self.device_results[device_id]
            report.append(f"- {device_id}:")
            report.append(f"  Attempts: {device.attempts}")
            if device.errors:
                report.append(f"  Last Error: {device.errors[-1]}")
        
        if len(self.failed_devices) > 10:
            report.append(f"\n... and {len(self.failed_devices) - 10} more")
        
        report.append(f"\nSee recovery directory for full details: {self.recovery_dir}")
        
        return "\n".join(report)
    
    def create_production_package(self):
        """Create final package for manufacturer"""
        package_name = f"sunflower_production_{self.batch_id}.zip"
        package_path = self.manufacturing_dir / package_name
        
        print(f"📦 Creating production package: {package_name}")
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add successful device files
            devices_added = 0
            for device_id in self.successful_devices:
                device = self.device_results[device_id]
                
                if device.iso_path and device.iso_path.exists():
                    zf.write(device.iso_path, f"{self.batch_id}/devices/{device_id}/iso/{device.iso_path.name}")
                    
                if device.usb_path and device.usb_path.exists():
                    zf.write(device.usb_path, f"{self.batch_id}/devices/{device_id}/usb/{device.usb_path.name}")
                
                devices_added += 1
            
            # Add documentation
            for doc_file in self.docs_dir.rglob("*"):
                if doc_file.is_file():
                    arcname = doc_file.relative_to(self.batch_dir)
                    zf.write(doc_file, f"{self.batch_id}/{arcname}")
            
            # Add QC materials
            for qc_file in self.qc_dir.rglob("*"):
                if qc_file.is_file():
                    arcname = qc_file.relative_to(self.batch_dir)
                    zf.write(qc_file, f"{self.batch_id}/{arcname}")
        
        # Calculate package checksum
        package_checksum = self.calculate_checksum(package_path)
        
        # Create package manifest
        manifest = {
            "package": package_name,
            "batch_id": self.batch_id,
            "created": datetime.now().isoformat(),
            "size_mb": package_path.stat().st_size / (1024**2),
            "checksum": package_checksum,
            "devices_included": devices_added,
            "total_devices": self.batch_size
        }
        
        manifest_path = self.manufacturing_dir / f"{self.batch_id}_package_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✅ Package created: {package_path}")
        print(f"   Size: {manifest['size_mb']:.2f} MB")
        print(f"   Devices: {devices_added}/{self.batch_size}")
        
        return package_path
    
    def generate_batch_report(self):
        """Generate comprehensive batch report"""
        report_path = self.batch_dir / "batch_report.md"
        
        duration = (datetime.now() - self.start_time).total_seconds()
        stats = self.batch_manifest["statistics"]
        
        report = f"""# Batch Production Report

## Batch Information
- **Batch ID**: {self.batch_id}
- **Version**: {self.version}
- **Start Time**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **Duration**: {duration:.1f} seconds
- **Status**: {'COMPLETE' if stats['failed'] == 0 else 'PARTIAL'}

## Production Statistics
- **Total Devices**: {stats['total']}
- **Successful**: {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)
- **Failed**: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)
- **Retried**: {stats['retried']}
- **Average Time per Device**: {duration/max(1, stats['successful']):.1f} seconds

## Component Details
{json.dumps(self.batch_manifest.get('components', {}), indent=2)}

## Quality Control
- **QC Required**: {max(10, int(self.batch_size * 0.1))} devices
- **QC Status**: PENDING

## Failed Devices Summary
{self._generate_failure_report()}

## Recovery Information
- **Recovery Directory**: {self.recovery_dir}
- **Retry Script Available**: {(self.recovery_dir / 'retry_failed_devices.sh').exists()}

## Next Steps
1. Review failed devices in recovery directory
2. Complete QC testing on sample devices
3. Package approved devices for shipping
4. Archive batch documentation

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        report_path.write_text(report)
        print(f"📊 Batch report saved: {report_path}")
        
        return report_path
    
    def validate_batch(self):
        """Validate the completed batch"""
        print("🔍 Validating batch...")
        
        validation_results = {
            "batch_id_valid": True,
            "minimum_success_rate": False,
            "documentation_complete": False,
            "qc_materials_ready": False,
            "package_created": False
        }
        
        # Check success rate
        stats = self.batch_manifest["statistics"]
        success_rate = stats['successful'] / stats['total'] if stats['total'] > 0 else 0
        validation_results["minimum_success_rate"] = success_rate >= 0.5  # 50% minimum
        
        # Check documentation
        required_docs = ["batch_manifest.json", "production_guide.md"]
        docs_present = all((self.docs_dir / doc).exists() for doc in required_docs)
        validation_results["documentation_complete"] = docs_present
        
        # Check QC materials
        validation_results["qc_materials_ready"] = (self.qc_dir / "qc_checklist.md").exists()
        
        # Check package
        package_files = list(self.manufacturing_dir.glob(f"sunflower_production_{self.batch_id}.zip"))
        validation_results["package_created"] = len(package_files) > 0
        
        # Display results
        all_valid = all(validation_results.values())
        
        for check, passed in validation_results.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check.replace('_', ' ').title()}")
        
        if not all_valid:
            print("\n⚠️  Batch validation found issues")
            if not validation_results["minimum_success_rate"]:
                print(f"  Success rate too low: {success_rate*100:.1f}% (minimum 50%)")
        
        return all_valid or self.continue_on_error


def main():
    """Command-line interface for batch generation"""
    parser = argparse.ArgumentParser(
        description="Generate manufacturing batch for Sunflower AI devices"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of devices in batch (default: 100)"
    )
    
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="Software version (default: 1.0.0)"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per device (default: 3)"
    )
    
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing even if devices fail"
    )
    
    parser.add_argument(
        "--no-continue-on-error",
        dest="continue_on_error",
        action="store_false",
        help="Stop batch on first device failure"
    )
    
    parser.set_defaults(continue_on_error=True)
    
    args = parser.parse_args()
    
    # Create generator
    generator = BatchManufacturingGenerator(
        batch_size=args.batch_size,
        version=args.version,
        max_retries=args.max_retries,
        continue_on_error=args.continue_on_error
    )
    
    # Run generation
    success = generator.generate()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

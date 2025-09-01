#!/usr/bin/env python3
"""
Sunflower AI Professional System - USB Quality Control Validator
Validates manufactured dual-partition USB devices for production release
Version: 1.0.0
Author: Sunflower AI Quality Control Team
"""

import os
import sys
import json
import time
import hashlib
import platform
import subprocess
import struct
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import tempfile
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('manufacturing_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ValidationTest:
    """Base class for validation tests"""
    
    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical
        self.passed = False
        self.message = ""
        self.details = {}
        
    def run(self, context: Dict) -> bool:
        """Run the validation test"""
        raise NotImplementedError("Subclasses must implement run()")
        
    def get_result(self) -> Dict:
        """Get test result"""
        return {
            'name': self.name,
            'passed': self.passed,
            'critical': self.critical,
            'message': self.message,
            'details': self.details
        }


class PartitionStructureTest(ValidationTest):
    """Validate partition structure"""
    
    def __init__(self):
        super().__init__("Partition Structure", critical=True)
        
    def run(self, context: Dict) -> bool:
        """Check if device has correct partition structure"""
        try:
            device_path = context['device_path']
            platform_name = platform.system()
            
            partitions = []
            
            if platform_name == "Windows":
                import wmi
                c = wmi.WMI()
                
                for disk in c.Win32_DiskDrive(DeviceID=device_path):
                    for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                        partition_info = {
                            'size': int(partition.Size) if partition.Size else 0,
                            'type': partition.Type,
                            'index': partition.DiskIndex
                        }
                        
                        for logical in partition.associators("Win32_LogicalDiskToPartition"):
                            partition_info['filesystem'] = logical.FileSystem
                            partition_info['mount'] = logical.DeviceID
                            
                        partitions.append(partition_info)
                        
            elif platform_name == "Darwin":  # macOS
                result = subprocess.run(
                    ['diskutil', 'list', device_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Parse diskutil output
                for line in result.stdout.split('\n'):
                    if device_path in line and 's' in line.split()[-1]:
                        parts = line.split()
                        if len(parts) >= 4:
                            partitions.append({
                                'type': parts[1],
                                'name': parts[2] if len(parts) > 2 else 'Unknown',
                                'identifier': parts[-1]
                            })
                            
            else:  # Linux
                result = subprocess.run(
                    ['lsblk', '-J', '-o', 'NAME,SIZE,FSTYPE,MOUNTPOINT', device_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                lsblk_data = json.loads(result.stdout)
                for device in lsblk_data.get('blockdevices', []):
                    for child in device.get('children', []):
                        partitions.append({
                            'name': child.get('name'),
                            'size': child.get('size'),
                            'filesystem': child.get('fstype'),
                            'mount': child.get('mountpoint')
                        })
            
            # Validate partition count
            if len(partitions) != 2:
                self.passed = False
                self.message = f"Expected 2 partitions, found {len(partitions)}"
                self.details['partition_count'] = len(partitions)
                return False
                
            # Validate partition properties
            self.details['partitions'] = partitions
            self.passed = True
            self.message = "Partition structure validated successfully"
            
            return True
            
        except Exception as e:
            self.passed = False
            self.message = f"Partition validation failed: {e}"
            logger.error(self.message)
            return False


class FileSystemIntegrityTest(ValidationTest):
    """Validate file system integrity"""
    
    def __init__(self):
        super().__init__("File System Integrity", critical=True)
        
    def run(self, context: Dict) -> bool:
        """Check file system integrity on both partitions"""
        try:
            cdrom_mount = context.get('cdrom_mount')
            usb_mount = context.get('usb_mount')
            
            if not cdrom_mount or not usb_mount:
                self.passed = False
                self.message = "Partitions not mounted"
                return False
            
            # Required directories on CD-ROM partition
            cdrom_required = [
                'launchers',
                'models',
                'ollama',
                'documentation',
                'security'
            ]
            
            # Required directories on USB partition
            usb_required = [
                'profiles',
                'conversations',
                'progress',
                'logs',
                'config'
            ]
            
            # Check CD-ROM partition
            cdrom_missing = []
            for directory in cdrom_required:
                dir_path = Path(cdrom_mount) / directory
                if not dir_path.exists():
                    cdrom_missing.append(directory)
                    
            # Check USB partition
            usb_missing = []
            for directory in usb_required:
                dir_path = Path(usb_mount) / directory
                if not dir_path.exists():
                    usb_missing.append(directory)
            
            if cdrom_missing or usb_missing:
                self.passed = False
                self.message = "Missing required directories"
                self.details['cdrom_missing'] = cdrom_missing
                self.details['usb_missing'] = usb_missing
                return False
                
            self.passed = True
            self.message = "File system structure validated"
            self.details['cdrom_dirs'] = cdrom_required
            self.details['usb_dirs'] = usb_required
            
            return True
            
        except Exception as e:
            self.passed = False
            self.message = f"File system validation failed: {e}"
            logger.error(self.message)
            return False


class AuthenticationTokenTest(ValidationTest):
    """Validate device authentication token"""
    
    def __init__(self):
        super().__init__("Authentication Token", critical=True)
        
    def run(self, context: Dict) -> bool:
        """Validate authentication token on device"""
        try:
            cdrom_mount = context.get('cdrom_mount')
            if not cdrom_mount:
                self.passed = False
                self.message = "CD-ROM partition not mounted"
                return False
                
            token_path = Path(cdrom_mount) / 'security' / 'device.token'
            
            if not token_path.exists():
                self.passed = False
                self.message = "Authentication token not found"
                return False
                
            # Read and validate token
            with open(token_path, 'rb') as f:
                token_data = f.read()
                
            if len(token_data) < 36:  # Minimum token size
                self.passed = False
                self.message = "Invalid token size"
                self.details['token_size'] = len(token_data)
                return False
                
            # Unpack token header
            try:
                json_length, token_hash = struct.unpack('>I32s', token_data[:36])
                token_json = token_data[36:36+json_length].decode('utf-8')
                token_info = json.loads(token_json)
                
                # Verify token hash
                calculated_hash = hashlib.sha256(token_json.encode()).digest()
                if calculated_hash != token_hash:
                    self.passed = False
                    self.message = "Token hash mismatch"
                    return False
                    
                # Validate token fields
                required_fields = ['uuid', 'timestamp', 'platform', 'version']
                for field in required_fields:
                    if field not in token_info:
                        self.passed = False
                        self.message = f"Missing token field: {field}"
                        return False
                        
                self.details['device_uuid'] = token_info.get('uuid')
                self.details['token_version'] = token_info.get('version')
                self.details['token_platform'] = token_info.get('platform')
                
                self.passed = True
                self.message = "Authentication token validated"
                
                return True
                
            except struct.error:
                self.passed = False
                self.message = "Invalid token format"
                return False
                
        except Exception as e:
            self.passed = False
            self.message = f"Token validation failed: {e}"
            logger.error(self.message)
            return False


class ManifestValidationTest(ValidationTest):
    """Validate manifest and file checksums"""
    
    def __init__(self):
        super().__init__("Manifest Validation", critical=True)
        
    def run(self, context: Dict) -> bool:
        """Validate manifest and verify file checksums"""
        try:
            cdrom_mount = context.get('cdrom_mount')
            if not cdrom_mount:
                self.passed = False
                self.message = "CD-ROM partition not mounted"
                return False
                
            manifest_path = Path(cdrom_mount) / 'manifest.json'
            
            if not manifest_path.exists():
                self.passed = False
                self.message = "Manifest file not found"
                return False
                
            # Load manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                
            # Validate manifest structure
            if 'files' not in manifest:
                self.passed = False
                self.message = "Invalid manifest structure"
                return False
                
            # Sample verification (check 10% of files for performance)
            files_to_check = list(manifest['files'].items())
            sample_size = max(1, len(files_to_check) // 10)
            
            import random
            sample_files = random.sample(files_to_check, min(sample_size, len(files_to_check)))
            
            failed_checksums = []
            for file_path, file_info in sample_files:
                full_path = Path(cdrom_mount) / file_path
                
                if not full_path.exists():
                    failed_checksums.append(f"{file_path} (not found)")
                    continue
                    
                # Calculate checksum
                calculated = self._calculate_checksum(full_path)
                expected = file_info.get('checksum')
                
                if calculated != expected:
                    failed_checksums.append(f"{file_path} (checksum mismatch)")
                    
            if failed_checksums:
                self.passed = False
                self.message = f"Checksum validation failed for {len(failed_checksums)} files"
                self.details['failed_files'] = failed_checksums[:10]  # Limit to 10 for readability
                return False
                
            self.passed = True
            self.message = f"Manifest validated ({sample_size} files checked)"
            self.details['total_files'] = len(manifest['files'])
            self.details['checked_files'] = sample_size
            
            return True
            
        except Exception as e:
            self.passed = False
            self.message = f"Manifest validation failed: {e}"
            logger.error(self.message)
            return False
            
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


class ModelFilesTest(ValidationTest):
    """Validate AI model files"""
    
    def __init__(self):
        super().__init__("Model Files", critical=True)
        
    def run(self, context: Dict) -> bool:
        """Validate presence and integrity of AI models"""
        try:
            cdrom_mount = context.get('cdrom_mount')
            if not cdrom_mount:
                self.passed = False
                self.message = "CD-ROM partition not mounted"
                return False
                
            models_dir = Path(cdrom_mount) / 'models'
            
            # Required model variants
            required_models = [
                'llama3.2_7b',
                'llama3.2_3b',
                'llama3.2_1b',
                'llama3.2_1b_q4_0'
            ]
            
            # Required modelfiles
            required_modelfiles = [
                'Sunflower_AI_Kids.modelfile',
                'Sunflower_AI_Educator.modelfile'
            ]
            
            missing_models = []
            model_sizes = {}
            
            # Check model files
            for model in required_models:
                model_path = models_dir / model
                if not model_path.exists():
                    missing_models.append(model)
                else:
                    # Check model size (should be substantial)
                    size_mb = model_path.stat().st_size / (1024 * 1024)
                    model_sizes[model] = size_mb
                    
                    # Minimum expected sizes
                    min_sizes = {
                        'llama3.2_7b': 3500,  # ~3.5GB
                        'llama3.2_3b': 1500,  # ~1.5GB
                        'llama3.2_1b': 500,   # ~500MB
                        'llama3.2_1b_q4_0': 250  # ~250MB
                    }
                    
                    expected_min = min_sizes.get(model, 100)
                    if size_mb < expected_min:
                        missing_models.append(f"{model} (too small: {size_mb:.1f}MB)")
                        
            # Check modelfiles
            for modelfile in required_modelfiles:
                modelfile_path = models_dir / modelfile
                if not modelfile_path.exists():
                    missing_models.append(modelfile)
                    
            if missing_models:
                self.passed = False
                self.message = f"Missing or invalid model files"
                self.details['missing'] = missing_models
                return False
                
            self.passed = True
            self.message = "All model files validated"
            self.details['model_sizes'] = model_sizes
            
            return True
            
        except Exception as e:
            self.passed = False
            self.message = f"Model validation failed: {e}"
            logger.error(self.message)
            return False


class LauncherExecutableTest(ValidationTest):
    """Validate platform launchers"""
    
    def __init__(self):
        super().__init__("Launcher Executables", critical=True)
        
    def run(self, context: Dict) -> bool:
        """Validate launcher executables for platforms"""
        try:
            cdrom_mount = context.get('cdrom_mount')
            if not cdrom_mount:
                self.passed = False
                self.message = "CD-ROM partition not mounted"
                return False
                
            launchers_dir = Path(cdrom_mount) / 'launchers'
            platform_name = platform.system()
            
            # Platform-specific launcher requirements
            launcher_requirements = {
                'Windows': {
                    'path': launchers_dir / 'windows',
                    'files': ['SunflowerAI.exe', 'sunflower.ico', 'setup.bat']
                },
                'Darwin': {
                    'path': launchers_dir / 'macos',
                    'files': ['SunflowerAI.app', 'setup.sh', 'Info.plist']
                },
                'Linux': {
                    'path': launchers_dir / 'linux',
                    'files': ['sunflower-ai', 'setup.sh', 'sunflower.desktop']
                }
            }
            
            # Check for current platform launcher
            if platform_name in launcher_requirements:
                req = launcher_requirements[platform_name]
                missing_files = []
                
                for file_name in req['files']:
                    file_path = req['path'] / file_name
                    if not file_path.exists():
                        missing_files.append(str(file_path.relative_to(cdrom_mount)))
                        
                if missing_files:
                    self.passed = False
                    self.message = f"Missing launcher files for {platform_name}"
                    self.details['missing_files'] = missing_files
                    return False
                    
            # Check autorun.inf for Windows devices
            if platform_name == "Windows":
                autorun_path = Path(cdrom_mount) / 'autorun.inf'
                if not autorun_path.exists():
                    self.passed = False
                    self.message = "Missing autorun.inf for Windows"
                    return False
                    
            self.passed = True
            self.message = f"Launcher validated for {platform_name}"
            self.details['platform'] = platform_name
            
            return True
            
        except Exception as e:
            self.passed = False
            self.message = f"Launcher validation failed: {e}"
            logger.error(self.message)
            return False


class ConfigurationTest(ValidationTest):
    """Validate device configuration"""
    
    def __init__(self):
        super().__init__("Device Configuration", critical=False)
        
    def run(self, context: Dict) -> bool:
        """Validate device configuration files"""
        try:
            usb_mount = context.get('usb_mount')
            if not usb_mount:
                self.passed = False
                self.message = "USB partition not mounted"
                return False
                
            config_path = Path(usb_mount) / 'config' / 'device.json'
            
            if not config_path.exists():
                self.passed = False
                self.message = "Device configuration not found"
                return False
                
            # Load and validate configuration
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Required configuration fields
            required_fields = [
                'device_uuid',
                'version',
                'created',
                'platform',
                'initialized',
                'settings'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in config:
                    missing_fields.append(field)
                    
            if missing_fields:
                self.passed = False
                self.message = "Missing configuration fields"
                self.details['missing_fields'] = missing_fields
                return False
                
            # Validate settings
            settings = config.get('settings', {})
            expected_settings = {
                'auto_backup': True,
                'session_logging': True,
                'safety_level': 'maximum',
                'offline_mode': True
            }
            
            for key, expected_value in expected_settings.items():
                if settings.get(key) != expected_value:
                    self.passed = False
                    self.message = f"Invalid setting: {key}"
                    self.details['invalid_setting'] = {key: settings.get(key)}
                    return False
                    
            self.passed = True
            self.message = "Configuration validated"
            self.details['device_uuid'] = config.get('device_uuid')
            self.details['version'] = config.get('version')
            
            return True
            
        except Exception as e:
            self.passed = False
            self.message = f"Configuration validation failed: {e}"
            logger.error(self.message)
            return False


class USBValidator:
    """Main USB validation orchestrator"""
    
    def __init__(self):
        self.platform = platform.system()
        self.test_results = []
        self.device_info = {}
        self.temp_mount_path = Path(tempfile.mkdtemp(prefix="sunflower_validate_"))
        
    def mount_partitions(self, device_path: str) -> Tuple[Optional[Path], Optional[Path]]:
        """Mount both partitions for validation"""
        try:
            cdrom_mount = self.temp_mount_path / "cdrom"
            usb_mount = self.temp_mount_path / "usb"
            
            cdrom_mount.mkdir(exist_ok=True)
            usb_mount.mkdir(exist_ok=True)
            
            # Get partition paths
            partitions = self._get_partition_paths(device_path)
            
            if len(partitions) < 2:
                logger.error("Failed to detect partitions")
                return None, None
                
            if self.platform == "Windows":
                # Windows partitions are already mounted as drive letters
                return Path(partitions[0]), Path(partitions[1])
                
            else:
                # Mount for Unix-like systems
                subprocess.run(['mount', '-r', partitions[0], str(cdrom_mount)], check=True)
                subprocess.run(['mount', partitions[1], str(usb_mount)], check=True)
                
                return cdrom_mount, usb_mount
                
        except Exception as e:
            logger.error(f"Failed to mount partitions: {e}")
            return None, None
            
    def unmount_partitions(self, cdrom_mount: Path, usb_mount: Path):
        """Unmount partitions after validation"""
        try:
            if self.platform != "Windows":
                subprocess.run(['umount', str(cdrom_mount)], check=False)
                subprocess.run(['umount', str(usb_mount)], check=False)
        except Exception as e:
            logger.error(f"Failed to unmount partitions: {e}")
            
    def run_validation_suite(self, device_path: str) -> bool:
        """Run complete validation suite"""
        try:
            logger.info(f"Starting validation for device: {device_path}")
            start_time = time.time()
            
            # Mount partitions
            cdrom_mount, usb_mount = self.mount_partitions(device_path)
            
            if not cdrom_mount or not usb_mount:
                logger.error("Failed to mount partitions for validation")
                return False
                
            # Prepare context for tests
            context = {
                'device_path': device_path,
                'cdrom_mount': cdrom_mount,
                'usb_mount': usb_mount,
                'platform': self.platform
            }
            
            # Define test suite
            tests = [
                PartitionStructureTest(),
                FileSystemIntegrityTest(),
                AuthenticationTokenTest(),
                ManifestValidationTest(),
                ModelFilesTest(),
                LauncherExecutableTest(),
                ConfigurationTest()
            ]
            
            # Run tests
            all_passed = True
            critical_failed = False
            
            for test in tests:
                logger.info(f"Running test: {test.name}")
                test.run(context)
                self.test_results.append(test.get_result())
                
                if not test.passed:
                    all_passed = False
                    if test.critical:
                        critical_failed = True
                        logger.error(f"Critical test failed: {test.name}")
                    else:
                        logger.warning(f"Non-critical test failed: {test.name}")
                else:
                    logger.info(f"Test passed: {test.name}")
                    
            # Extract device info from tests
            for result in self.test_results:
                if result['name'] == 'Authentication Token' and result['passed']:
                    self.device_info['device_uuid'] = result['details'].get('device_uuid')
                elif result['name'] == 'Device Configuration' and result['passed']:
                    self.device_info['version'] = result['details'].get('version')
                    
            # Unmount partitions
            self.unmount_partitions(cdrom_mount, usb_mount)
            
            # Calculate validation time
            validation_time = time.time() - start_time
            
            # Generate validation report
            self._generate_validation_report(device_path, validation_time, not critical_failed)
            
            return not critical_failed
            
        except Exception as e:
            logger.error(f"Validation suite failed: {e}")
            return False
        finally:
            # Cleanup
            if self.temp_mount_path.exists():
                shutil.rmtree(self.temp_mount_path, ignore_errors=True)
                
    def _get_partition_paths(self, device_path: str) -> List[str]:
        """Get partition paths for device"""
        partitions = []
        
        try:
            if self.platform == "Windows":
                # For Windows, return drive letters (simplified)
                # In production, query WMI for actual assigned letters
                partitions = ["X:\\", "Y:\\"]
                
            elif self.platform == "Darwin":
                # macOS partition naming
                base_name = device_path.split('/')[-1]
                partitions = [f"/dev/{base_name}s1", f"/dev/{base_name}s2"]
                
            else:
                # Linux partition naming
                if 'nvme' in device_path or 'mmcblk' in device_path:
                    partitions = [f"{device_path}p1", f"{device_path}p2"]
                else:
                    partitions = [f"{device_path}1", f"{device_path}2"]
                    
        except Exception as e:
            logger.error(f"Failed to get partition paths: {e}")
            
        return partitions
        
    def _generate_validation_report(self, device_path: str, validation_time: float, passed: bool):
        """Generate validation report"""
        report = {
            'validation_id': str(uuid.uuid4()),
            'device_path': device_path,
            'device_uuid': self.device_info.get('device_uuid', 'Unknown'),
            'validation_date': datetime.now().isoformat(),
            'validation_time': validation_time,
            'platform': self.platform,
            'overall_result': 'PASS' if passed else 'FAIL',
            'test_results': self.test_results,
            'summary': {
                'total_tests': len(self.test_results),
                'passed_tests': sum(1 for r in self.test_results if r['passed']),
                'failed_tests': sum(1 for r in self.test_results if not r['passed']),
                'critical_failures': sum(1 for r in self.test_results if not r['passed'] and r['critical'])
            }
        }
        
        # Save report
        report_dir = Path('validation_reports')
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"validation_{report['validation_id']}.json"
        report_file.write_text(json.dumps(report, indent=2))
        
        logger.info(f"Validation report saved: {report_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Device: {device_path}")
        print(f"Device UUID: {self.device_info.get('device_uuid', 'Unknown')}")
        print(f"Overall Result: {report['overall_result']}")
        print(f"Tests Passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']}")
        
        if report['summary']['failed_tests'] > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    critical_marker = " [CRITICAL]" if result['critical'] else ""
                    print(f"  - {result['name']}{critical_marker}: {result['message']}")
                    
        print("=" * 60)


def main():
    """Main entry point for USB validation"""
    try:
        print("=" * 60)
        print("Sunflower AI Professional System - USB Validator")
        print("=" * 60)
        
        validator = USBValidator()
        
        # Check for command line arguments
        if len(sys.argv) > 1:
            device_path = sys.argv[1]
            print(f"\nValidating device: {device_path}")
        else:
            # Interactive mode
            print("\nEnter device path to validate")
            print("Examples:")
            print("  Windows: \\\\.\\PhysicalDrive2")
            print("  macOS: /dev/disk2")
            print("  Linux: /dev/sdb")
            
            device_path = input("\nDevice path: ").strip()
            
            if not device_path:
                print("No device specified. Exiting.")
                sys.exit(1)
                
        # Confirm validation
        print(f"\nValidating device: {device_path}")
        confirm = input("Continue? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("Validation cancelled.")
            sys.exit(0)
            
        # Run validation
        print("\nRunning validation suite...")
        success = validator.run_validation_suite(device_path)
        
        if success:
            print("\n✓ Device validation PASSED")
            sys.exit(0)
        else:
            print("\n✗ Device validation FAILED")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n✗ Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

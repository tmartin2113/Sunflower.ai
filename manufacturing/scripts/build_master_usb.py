#!/usr/bin/env python3
"""
Sunflower AI Professional System - Master USB Builder
Creates dual-partition USB devices with CD-ROM and writable partitions
Version: 1.0.0
Author: Sunflower AI Manufacturing Team
"""

import os
import sys
import json
import time
import shutil
import hashlib
import platform
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid
import struct
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('manufacturing_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class USBPartitioner:
    """Handles creation of dual-partition USB devices"""
    
    def __init__(self):
        self.platform = platform.system()
        self.master_files_path = Path(__file__).parent.parent / "master_files" / "current"
        self.temp_build_path = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        self.device_uuid = str(uuid.uuid4())
        self.build_metadata = {}
        
    def detect_usb_devices(self) -> List[Dict]:
        """Detect available USB devices for manufacturing"""
        devices = []
        
        try:
            if self.platform == "Windows":
                # Use WMI to detect USB drives
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive(InterfaceType="USB"):
                    device_info = {
                        'device_id': disk.DeviceID,
                        'model': disk.Model,
                        'size': int(disk.Size) if disk.Size else 0,
                        'serial': disk.SerialNumber,
                        'partitions': []
                    }
                    
                    # Get partition information
                    for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                        for logical in partition.associators("Win32_LogicalDiskToPartition"):
                            device_info['partitions'].append({
                                'letter': logical.DeviceID,
                                'filesystem': logical.FileSystem,
                                'size': int(logical.Size) if logical.Size else 0
                            })
                    
                    devices.append(device_info)
                    
            elif self.platform == "Darwin":  # macOS
                # Use diskutil to detect USB drives
                result = subprocess.run(
                    ['diskutil', 'list', '-plist'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                import plistlib
                plist_data = plistlib.loads(result.stdout.encode())
                
                for disk in plist_data.get('AllDisksAndPartitions', []):
                    if 'USB' in disk.get('Content', ''):
                        device_info = {
                            'device_id': f"/dev/{disk['DeviceIdentifier']}",
                            'model': disk.get('MediaName', 'Unknown'),
                            'size': disk.get('Size', 0),
                            'serial': disk.get('VolumeUUID', 'Unknown'),
                            'partitions': []
                        }
                        
                        for partition in disk.get('Partitions', []):
                            device_info['partitions'].append({
                                'identifier': partition.get('DeviceIdentifier'),
                                'filesystem': partition.get('Content', 'Unknown'),
                                'size': partition.get('Size', 0)
                            })
                        
                        devices.append(device_info)
                        
            else:  # Linux
                # Use lsblk for Linux systems
                result = subprocess.run(
                    ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,TRAN,SERIAL,FSTYPE'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                lsblk_data = json.loads(result.stdout)
                
                for device in lsblk_data.get('blockdevices', []):
                    if device.get('tran') == 'usb' and device.get('type') == 'disk':
                        device_info = {
                            'device_id': f"/dev/{device['name']}",
                            'model': device.get('model', 'Unknown'),
                            'size': self._parse_size(device.get('size', '0')),
                            'serial': device.get('serial', 'Unknown'),
                            'partitions': []
                        }
                        
                        for child in device.get('children', []):
                            if child.get('type') == 'part':
                                device_info['partitions'].append({
                                    'name': child['name'],
                                    'filesystem': child.get('fstype', 'Unknown'),
                                    'size': self._parse_size(child.get('size', '0'))
                                })
                        
                        devices.append(device_info)
                        
        except Exception as e:
            logger.error(f"Failed to detect USB devices: {e}")
            
        return devices
    
    def create_partitions(self, device_path: str) -> bool:
        """Create dual-partition structure on USB device"""
        try:
            logger.info(f"Creating partitions on {device_path}")
            
            # Calculate partition sizes (CD-ROM: 4GB, USB: remaining space)
            cdrom_size_mb = 4096  # 4GB for CD-ROM partition
            
            if self.platform == "Windows":
                # Windows partition creation using diskpart
                diskpart_script = f"""
select disk {self._get_disk_number(device_path)}
clean
convert mbr
create partition primary size={cdrom_size_mb}
format fs=udf quick label="SUNFLOWER_AI"
assign letter=X
create partition primary
format fs=ntfs quick label="SUNFLOWER_DATA"
assign letter=Y
exit
"""
                script_path = self.temp_build_path / "diskpart_script.txt"
                script_path.write_text(diskpart_script)
                
                result = subprocess.run(
                    ['diskpart', '/s', str(script_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    logger.error(f"Diskpart failed: {result.stderr}")
                    return False
                    
            elif self.platform == "Darwin":  # macOS
                # macOS partition creation using diskutil
                subprocess.run(
                    ['diskutil', 'eraseDisk', 'MS-DOS', 'SUNFLOWER', 'MBR', device_path],
                    check=True
                )
                
                # Create CD-ROM partition
                subprocess.run([
                    'diskutil', 'splitPartition', device_path,
                    '2', 'MS-DOS', 'SUNFLOWER_AI', f'{cdrom_size_mb}M',
                    'MS-DOS', 'SUNFLOWER_DATA', 'R'
                ], check=True)
                
            else:  # Linux
                # Linux partition creation using parted
                subprocess.run(['parted', '-s', device_path, 'mklabel', 'msdos'], check=True)
                subprocess.run([
                    'parted', '-s', device_path,
                    'mkpart', 'primary', 'fat32', '1MiB', f'{cdrom_size_mb}MiB'
                ], check=True)
                subprocess.run([
                    'parted', '-s', device_path,
                    'mkpart', 'primary', 'ntfs', f'{cdrom_size_mb}MiB', '100%'
                ], check=True)
                
                # Format partitions
                subprocess.run(['mkfs.vfat', '-n', 'SUNFLOWER_AI', f'{device_path}1'], check=True)
                subprocess.run(['mkfs.ntfs', '-f', '-L', 'SUNFLOWER_DATA', f'{device_path}2'], check=True)
            
            logger.info("Partitions created successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create partitions: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during partition creation: {e}")
            return False
    
    def write_cdrom_partition(self, device_path: str, partition_path: str) -> bool:
        """Write CD-ROM partition with system files"""
        try:
            logger.info("Writing CD-ROM partition with system files")
            
            # Mount the partition
            mount_point = self.temp_build_path / "cdrom_mount"
            mount_point.mkdir(exist_ok=True)
            
            if self.platform == "Windows":
                # Windows uses drive letters, partition already mounted
                mount_point = Path(partition_path)
            else:
                # Mount for Unix-like systems
                subprocess.run(['mount', partition_path, str(mount_point)], check=True)
            
            # Copy system files
            system_files = {
                'launchers': self.master_files_path / 'launchers',
                'models': self.master_files_path / 'models',
                'ollama': self.master_files_path / 'ollama',
                'documentation': self.master_files_path / 'documentation',
                'security': self.master_files_path / 'security'
            }
            
            for name, source_path in system_files.items():
                if source_path.exists():
                    dest_path = mount_point / name
                    logger.info(f"Copying {name} to CD-ROM partition")
                    
                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source_path, dest_path)
                else:
                    logger.warning(f"Source path {source_path} not found")
            
            # Create autorun configuration for Windows
            if self.platform == "Windows":
                autorun_content = """[autorun]
open=launchers\\windows\\SunflowerAI.exe
icon=launchers\\windows\\sunflower.ico
label=Sunflower AI Professional System
"""
                (mount_point / "autorun.inf").write_text(autorun_content)
            
            # Write device authentication token
            auth_token = self._generate_auth_token()
            auth_file = mount_point / "security" / "device.token"
            auth_file.parent.mkdir(exist_ok=True, parents=True)
            auth_file.write_bytes(auth_token)
            
            # Create manifest file
            manifest = self._create_manifest(mount_point)
            manifest_file = mount_point / "manifest.json"
            manifest_file.write_text(json.dumps(manifest, indent=2))
            
            # Set CD-ROM attributes (make read-only)
            if self.platform == "Windows":
                subprocess.run(['attrib', '+R', '+S', f'{mount_point}\\*', '/S', '/D'], check=False)
            
            # Unmount if needed
            if self.platform != "Windows":
                subprocess.run(['umount', str(mount_point)], check=True)
            
            logger.info("CD-ROM partition written successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write CD-ROM partition: {e}")
            return False
    
    def write_usb_partition(self, device_path: str, partition_path: str) -> bool:
        """Write USB partition with initial directory structure"""
        try:
            logger.info("Writing USB partition with initial structure")
            
            # Mount the partition
            mount_point = self.temp_build_path / "usb_mount"
            mount_point.mkdir(exist_ok=True)
            
            if self.platform == "Windows":
                mount_point = Path(partition_path)
            else:
                subprocess.run(['mount', partition_path, str(mount_point)], check=True)
            
            # Create directory structure
            directories = [
                'profiles',
                'profiles/children',
                'profiles/parent',
                'conversations',
                'progress',
                'logs',
                'config',
                'backup'
            ]
            
            for directory in directories:
                (mount_point / directory).mkdir(parents=True, exist_ok=True)
            
            # Create initial configuration
            config = {
                'device_uuid': self.device_uuid,
                'version': '1.0.0',
                'created': datetime.now().isoformat(),
                'platform': self.platform,
                'initialized': False,
                'family_profiles': [],
                'settings': {
                    'auto_backup': True,
                    'session_logging': True,
                    'safety_level': 'maximum',
                    'offline_mode': True
                }
            }
            
            config_file = mount_point / 'config' / 'device.json'
            config_file.write_text(json.dumps(config, indent=2))
            
            # Create README for users
            readme_content = """Sunflower AI Professional System - User Data Directory

This partition contains your family's profiles, conversations, and learning progress.
DO NOT modify files in this directory manually.

For support, refer to the documentation on the CD-ROM partition.

© 2025 Sunflower AI - All Rights Reserved
"""
            (mount_point / 'README.txt').write_text(readme_content)
            
            # Unmount if needed
            if self.platform != "Windows":
                subprocess.run(['umount', str(mount_point)], check=True)
            
            logger.info("USB partition written successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write USB partition: {e}")
            return False
    
    def finalize_device(self, device_path: str) -> bool:
        """Finalize device with security and validation"""
        try:
            logger.info("Finalizing device configuration")
            
            # Generate checksums for all files
            checksums = self._generate_checksums(device_path)
            
            # Write build metadata
            self.build_metadata = {
                'device_uuid': self.device_uuid,
                'build_date': datetime.now().isoformat(),
                'build_platform': self.platform,
                'build_machine': platform.machine(),
                'checksums': checksums,
                'version': '1.0.0',
                'serial': self._generate_serial_number()
            }
            
            # Save build metadata
            metadata_file = self.temp_build_path / f"build_{self.device_uuid}.json"
            metadata_file.write_text(json.dumps(self.build_metadata, indent=2))
            
            # Sync and flush buffers
            if self.platform != "Windows":
                subprocess.run(['sync'], check=True)
            
            logger.info(f"Device finalized with UUID: {self.device_uuid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to finalize device: {e}")
            return False
    
    def build_master_usb(self, device_path: str) -> bool:
        """Main build process for creating master USB"""
        try:
            logger.info(f"Starting master USB build for device: {device_path}")
            start_time = time.time()
            
            # Validate device
            if not self._validate_device(device_path):
                logger.error("Device validation failed")
                return False
            
            # Create partitions
            if not self.create_partitions(device_path):
                logger.error("Partition creation failed")
                return False
            
            # Wait for partitions to be available
            time.sleep(2)
            
            # Get partition paths
            partitions = self._get_partition_paths(device_path)
            if len(partitions) < 2:
                logger.error("Failed to detect created partitions")
                return False
            
            cdrom_partition = partitions[0]
            usb_partition = partitions[1]
            
            # Write CD-ROM partition
            if not self.write_cdrom_partition(device_path, cdrom_partition):
                logger.error("CD-ROM partition write failed")
                return False
            
            # Write USB partition
            if not self.write_usb_partition(device_path, usb_partition):
                logger.error("USB partition write failed")
                return False
            
            # Finalize device
            if not self.finalize_device(device_path):
                logger.error("Device finalization failed")
                return False
            
            build_time = time.time() - start_time
            logger.info(f"Master USB build completed in {build_time:.2f} seconds")
            
            # Generate build report
            self._generate_build_report(device_path, build_time)
            
            return True
            
        except Exception as e:
            logger.error(f"Master USB build failed: {e}")
            return False
        finally:
            # Cleanup temporary files
            if self.temp_build_path.exists():
                shutil.rmtree(self.temp_build_path, ignore_errors=True)
    
    def _validate_device(self, device_path: str) -> bool:
        """Validate device before building"""
        try:
            # Check if device exists
            if self.platform == "Windows":
                import wmi
                c = wmi.WMI()
                disks = c.Win32_DiskDrive(DeviceID=device_path)
                if not disks:
                    logger.error(f"Device {device_path} not found")
                    return False
                
                disk = disks[0]
                size_gb = int(disk.Size) / (1024**3) if disk.Size else 0
                
            else:
                if not Path(device_path).exists():
                    logger.error(f"Device {device_path} not found")
                    return False
                
                # Get device size
                if self.platform == "Darwin":
                    result = subprocess.run(
                        ['diskutil', 'info', device_path],
                        capture_output=True,
                        text=True
                    )
                    # Parse size from output
                    size_gb = 8  # Default minimum
                    for line in result.stdout.split('\n'):
                        if 'Total Size' in line:
                            # Extract size
                            parts = line.split('(')
                            if len(parts) > 1:
                                size_str = parts[1].split(' ')[0]
                                size_gb = float(size_str) / (1024**3)
                else:
                    stat = os.stat(device_path)
                    size_gb = stat.st_size / (1024**3)
            
            # Minimum 8GB required
            if size_gb < 8:
                logger.error(f"Device too small: {size_gb:.2f}GB (minimum 8GB required)")
                return False
            
            logger.info(f"Device validated: {size_gb:.2f}GB available")
            return True
            
        except Exception as e:
            logger.error(f"Device validation error: {e}")
            return False
    
    def _get_disk_number(self, device_path: str) -> int:
        """Get disk number for Windows diskpart"""
        try:
            import wmi
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                if disk.DeviceID == device_path:
                    # Extract disk number from DeviceID
                    return int(disk.Index)
            return -1
        except:
            return -1
    
    def _get_partition_paths(self, device_path: str) -> List[str]:
        """Get partition paths after creation"""
        partitions = []
        
        try:
            if self.platform == "Windows":
                # Return assigned drive letters
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
    
    def _generate_auth_token(self) -> bytes:
        """Generate unique authentication token for device"""
        token_data = {
            'uuid': self.device_uuid,
            'timestamp': int(time.time()),
            'platform': self.platform,
            'version': '1.0.0'
        }
        
        # Create binary token
        token_json = json.dumps(token_data)
        token_hash = hashlib.sha256(token_json.encode()).digest()
        
        # Pack token data
        token = struct.pack(
            '>I32s',
            len(token_json),
            token_hash
        ) + token_json.encode()
        
        return token
    
    def _generate_serial_number(self) -> str:
        """Generate manufacturing serial number"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = uuid.uuid4().hex[:6].upper()
        return f"SUN-{timestamp}-{random_part}"
    
    def _create_manifest(self, directory: Path) -> Dict:
        """Create manifest of all files in directory"""
        manifest = {
            'version': '1.0.0',
            'created': datetime.now().isoformat(),
            'files': {}
        }
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(directory)
                manifest['files'][str(relative_path)] = {
                    'size': file_path.stat().st_size,
                    'checksum': self._calculate_checksum(file_path),
                    'modified': datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                }
        
        return manifest
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _generate_checksums(self, device_path: str) -> Dict:
        """Generate checksums for all critical files"""
        checksums = {}
        
        # This would normally iterate through mounted partitions
        # For production, implement full checksum generation
        checksums['device_uuid'] = self.device_uuid
        checksums['timestamp'] = datetime.now().isoformat()
        
        return checksums
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        
        if size_str[-1] in multipliers:
            return int(float(size_str[:-1]) * multipliers[size_str[-1]])
        return int(size_str)
    
    def _generate_build_report(self, device_path: str, build_time: float):
        """Generate build report for manufacturing records"""
        report = {
            'build_id': self.device_uuid,
            'device_path': device_path,
            'build_time': build_time,
            'build_date': datetime.now().isoformat(),
            'platform': self.platform,
            'status': 'SUCCESS',
            'metadata': self.build_metadata
        }
        
        report_file = Path('manufacturing_reports') / f"build_{self.device_uuid}.json"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2))
        
        logger.info(f"Build report saved: {report_file}")


def main():
    """Main entry point for manufacturing build"""
    try:
        print("=" * 60)
        print("Sunflower AI Professional System - Master USB Builder")
        print("=" * 60)
        
        builder = USBPartitioner()
        
        # Detect available USB devices
        print("\nDetecting USB devices...")
        devices = builder.detect_usb_devices()
        
        if not devices:
            print("No USB devices detected. Please insert a USB device.")
            sys.exit(1)
        
        # Display available devices
        print("\nAvailable USB devices:")
        for i, device in enumerate(devices, 1):
            size_gb = device['size'] / (1024**3) if device['size'] else 0
            print(f"{i}. {device['model']} ({size_gb:.2f}GB) - {device['device_id']}")
        
        # Select device
        while True:
            try:
                choice = input("\nSelect device number (or 'q' to quit): ")
                if choice.lower() == 'q':
                    print("Build cancelled.")
                    sys.exit(0)
                    
                device_index = int(choice) - 1
                if 0 <= device_index < len(devices):
                    selected_device = devices[device_index]
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")
        
        # Confirm selection
        print(f"\nSelected device: {selected_device['model']}")
        print("WARNING: All data on this device will be erased!")
        confirm = input("Continue? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("Build cancelled.")
            sys.exit(0)
        
        # Build master USB
        print("\nBuilding master USB...")
        success = builder.build_master_usb(selected_device['device_id'])
        
        if success:
            print("\n✓ Master USB build completed successfully!")
            print(f"Device UUID: {builder.device_uuid}")
            print(f"Serial Number: {builder.build_metadata.get('serial', 'N/A')}")
        else:
            print("\n✗ Master USB build failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

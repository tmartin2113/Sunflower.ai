#!/usr/bin/env python3
"""
Prepare USB Partition for Sunflower AI Professional System
Creates the writable USB partition structure for user data storage.

This script handles USB partition preparation, formatting, and initialization
for the dual-partition manufacturing process.
"""

import os
import sys
import json
import shutil
import secrets
import platform
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import hashlib
import uuid
import zipfile
import psutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import standardized path configuration
from config.path_config import PathConfiguration

# FIX BUG-010: Define and enforce USB size validation constants
MINIMUM_USB_SIZE_MB = 512  # Absolute minimum for USB partition
RECOMMENDED_USB_SIZE_MB = 1024  # Recommended size for optimal performance
MAXIMUM_USB_SIZE_MB = 4096  # Maximum size to prevent waste

class USBPartitionPreparer:
    def __init__(self, batch_id=None, partition_size_mb=1024):
        self.root_dir = Path(__file__).parent.parent
        self.batch_id = batch_id or self.generate_batch_id()
        
        # FIX BUG-010: Validate partition size on initialization
        self.partition_size_mb = self._validate_partition_size(partition_size_mb)
        
        # Initialize path configuration
        self.path_config = PathConfiguration(auto_detect=False)
        
        # Paths
        self.staging_dir = self.root_dir / "usb_staging" / self.path_config.USB_PARTITION_NAME
        self.output_dir = self.root_dir / "manufacturing" / "usb_images"
        self.temp_mount = Path("/tmp/sunflower_usb_mount") if platform.system() != "Windows" else None
        
        # USB configuration using standardized names
        self.volume_label = self.path_config.USB_PARTITION_NAME
        self.filesystem = "FAT32"  # Compatible with all platforms
        
        # Security
        self.device_tokens = []
        self.encryption_keys = {}
    
    def _validate_partition_size(self, size_mb: int) -> int:
        """
        FIX BUG-010: Validate partition size meets requirements
        
        Args:
            size_mb: Requested partition size in MB
            
        Returns:
            Validated partition size in MB
            
        Raises:
            ValueError: If size doesn't meet requirements
        """
        if size_mb < MINIMUM_USB_SIZE_MB:
            raise ValueError(
                f"USB partition size {size_mb}MB is below minimum requirement of {MINIMUM_USB_SIZE_MB}MB. "
                f"The system requires at least {MINIMUM_USB_SIZE_MB}MB for proper operation."
            )
        
        if size_mb > MAXIMUM_USB_SIZE_MB:
            print(f"⚠️  Warning: USB partition size {size_mb}MB exceeds recommended maximum of {MAXIMUM_USB_SIZE_MB}MB")
            print(f"   Using maximum size of {MAXIMUM_USB_SIZE_MB}MB to prevent waste")
            return MAXIMUM_USB_SIZE_MB
        
        if size_mb < RECOMMENDED_USB_SIZE_MB:
            print(f"⚠️  Note: USB partition size {size_mb}MB is below recommended {RECOMMENDED_USB_SIZE_MB}MB")
            print(f"   Consider using {RECOMMENDED_USB_SIZE_MB}MB for optimal performance")
        
        return size_mb
    
    def _validate_target_device(self, device_path: str) -> bool:
        """
        FIX BUG-010: Validate target device has sufficient capacity
        
        Args:
            device_path: Path to target USB device
            
        Returns:
            True if device is valid, False otherwise
        """
        if not os.path.exists(device_path):
            print(f"❌ Error: Device {device_path} not found")
            return False
        
        try:
            # Get device size based on platform
            device_size_mb = 0
            
            if platform.system() == "Windows":
                # Windows: Use WMI to get device size
                try:
                    import wmi
                    c = wmi.WMI()
                    device_path_normalized = device_path.replace('/', '\\')
                    
                    for disk in c.Win32_DiskDrive():
                        if disk.DeviceID == device_path_normalized or disk.Caption in device_path:
                            device_size_mb = int(disk.Size) / (1024 * 1024) if disk.Size else 0
                            break
                except ImportError:
                    # Fallback: Use psutil if WMI not available
                    for disk in psutil.disk_partitions():
                        if device_path in disk.device:
                            usage = psutil.disk_usage(disk.mountpoint)
                            device_size_mb = usage.total / (1024 * 1024)
                            break
            
            elif platform.system() == "Darwin":
                # macOS: Use diskutil
                result = subprocess.run(
                    ['diskutil', 'info', device_path],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Disk Size' in line or 'Total Size' in line:
                            # Parse size from line like "Disk Size: 16.0 GB (16008609792 Bytes)"
                            parts = line.split('(')
                            if len(parts) > 1:
                                bytes_str = parts[1].split(' ')[0].replace(',', '')
                                try:
                                    device_size_mb = int(bytes_str) / (1024 * 1024)
                                except ValueError:
                                    pass
            
            else:
                # Linux: Use lsblk or stat
                result = subprocess.run(
                    ['lsblk', '-b', '-n', '-o', 'SIZE', device_path],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        device_size_mb = int(result.stdout.strip()) / (1024 * 1024)
                    except ValueError:
                        # Fallback to stat
                        stat_info = os.stat(device_path)
                        device_size_mb = stat_info.st_size / (1024 * 1024)
            
            # Validate device size
            if device_size_mb == 0:
                print(f"❌ Error: Unable to determine size of device {device_path}")
                return False
            
            # Need space for both CD-ROM partition (4GB) and USB partition
            required_size_mb = 4096 + self.partition_size_mb  # CD-ROM + USB partition
            
            if device_size_mb < required_size_mb:
                print(f"❌ Error: Device {device_path} has insufficient capacity")
                print(f"   Device size: {device_size_mb:.1f}MB")
                print(f"   Required: {required_size_mb}MB (4096MB CD-ROM + {self.partition_size_mb}MB USB)")
                print(f"   Minimum USB device size: {(required_size_mb / 1024):.1f}GB")
                return False
            
            print(f"✅ Device validated: {device_size_mb:.1f}MB available")
            print(f"   Required: {required_size_mb}MB")
            print(f"   Free space after partitioning: {(device_size_mb - required_size_mb):.1f}MB")
            
            return True
            
        except Exception as e:
            print(f"❌ Error validating device: {str(e)}")
            return False
    
    def generate_batch_id(self):
        """Generate unique batch identifier matching ISO batch"""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_id = secrets.token_hex(4).upper()
        return f"{timestamp}-{random_id}"
    
    def prepare(self, output_format="directory", target_device=None):
        """Main USB partition preparation process"""
        print(f"🌻 Sunflower AI USB Partition Preparer")
        print(f"📦 Batch ID: {self.batch_id}")
        print(f"💾 Partition Size: {self.partition_size_mb} MB")
        print(f"📁 Output Format: {output_format}")
        
        # FIX BUG-010: Display size validation status
        if self.partition_size_mb >= RECOMMENDED_USB_SIZE_MB:
            print(f"✅ Size Status: Optimal")
        elif self.partition_size_mb >= MINIMUM_USB_SIZE_MB:
            print(f"⚠️  Size Status: Minimum requirements met")
        
        print("-" * 60)
        
        # FIX BUG-010: Validate target device if specified
        if target_device:
            print(f"\n🔍 Validating target device: {target_device}")
            if not self._validate_target_device(target_device):
                raise ValueError(f"Target device {target_device} validation failed")
        
        try:
            # Create directory structure
            print("\n📁 Creating USB partition structure...")
            self.create_partition_structure()
            
            # Initialize user data directories
            print("\n📂 Initializing user data directories...")
            self.initialize_user_directories()
            
            # Setup security
            print("\n🔐 Setting up security...")
            self.setup_security()
            
            # Create device identifiers
            print("\n🆔 Creating device identifiers...")
            self.create_device_identifiers()
            
            # Generate documentation
            print("\n📝 Generating documentation...")
            self.generate_documentation()
            
            # Package output
            if output_format == "zip":
                print("\n📦 Creating ZIP archive...")
                return self.create_zip_package()
            elif output_format == "image":
                print("\n💿 Creating partition image...")
                return self.create_partition_image()
            else:
                print(f"\n✅ USB partition prepared at: {self.staging_dir}")
                return self.staging_dir
                
        except Exception as e:
            print(f"❌ Error: {e}")
            raise
    
    def create_partition_structure(self):
        """Create the base USB partition directory structure"""
        # Clean and recreate staging directory
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)
        self.staging_dir.mkdir(parents=True)
        
        # Create standardized directory structure
        for dir_key, dir_name in self.path_config.USB_STRUCTURE.items():
            dir_path = self.staging_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Add .gitkeep to preserve empty directories
            gitkeep = dir_path / ".gitkeep"
            gitkeep.touch()
    
    def initialize_user_directories(self):
        """Initialize user data storage directories"""
        # Profiles directory
        profiles_dir = self.staging_dir / self.path_config.USB_STRUCTURE['profiles']
        readme = profiles_dir / "README.txt"
        readme.write_text("""
Family Profiles Directory
========================
This directory stores individual profiles for each family member.
Each profile is encrypted and password-protected.

DO NOT manually edit files in this directory.
Use the Sunflower AI Parent Dashboard to manage profiles.
""")
        
        # Conversations directory
        conv_dir = self.staging_dir / self.path_config.USB_STRUCTURE['conversations']
        readme = conv_dir / "README.txt"
        readme.write_text("""
Conversation History
===================
Encrypted conversation logs for each child profile.
These files are automatically managed by the system.

Files are retained for parent review and learning progress tracking.
""")
        
        # Safety reports directory
        safety_dir = self.staging_dir / self.path_config.USB_STRUCTURE['safety']
        readme = safety_dir / "README.txt"
        readme.write_text("""
Safety Reports
=============
This directory contains safety incident reports and filtered content logs.
Review these regularly to ensure child safety.

All incidents are timestamped and linked to specific profiles.
""")
    
    def setup_security(self):
        """Setup security tokens and encryption keys"""
        security_dir = self.staging_dir / self.path_config.USB_STRUCTURE['security']
        
        # Generate device-specific security token
        device_token = {
            "device_id": str(uuid.uuid4()),
            "batch_id": self.batch_id,
            "created": datetime.now().isoformat(),
            "partition_size_mb": self.partition_size_mb,
            "security_version": "2.0",
            "encryption": {
                "algorithm": "AES-256-CBC",
                "key_derivation": "PBKDF2",
                "iterations": 100000
            }
        }
        
        token_file = security_dir / "device_token.json"
        with open(token_file, 'w') as f:
            json.dump(device_token, f, indent=2)
        
        # Create encryption key placeholder
        key_file = security_dir / "keys.encrypted"
        key_file.write_text("Encryption keys will be generated on first parent setup")
        
        # Platform compatibility file
        compat_file = security_dir / "platform_compatibility.json"
        compat = {
            "windows": {"min_version": "10", "tested": True},
            "macos": {"min_version": "11.0", "tested": True},
            "verified_date": datetime.now().isoformat()
        }
        with open(compat_file, 'w') as f:
            json.dump(compat, f, indent=2)
    
    def create_device_identifiers(self):
        """Create unique device identification files"""
        # Main identifier matching CD-ROM check
        id_file = self.staging_dir / self.path_config.USB_ID_FILE
        id_file.write_text(f"SUNFLOWER_DATA_{self.batch_id}")
        
        # Partition info file
        info_file = self.staging_dir / ".partition_info"
        info = {
            "type": "USB_WRITABLE",
            "version": "6.2",
            "batch_id": self.batch_id,
            "created": datetime.now().isoformat(),
            "size_mb": self.partition_size_mb,
            "filesystem": self.filesystem,
            "volume_label": self.volume_label
        }
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        # Initialization marker
        init_file = self.staging_dir / ".initialized"
        init_file.write_text(datetime.now().isoformat())
    
    def generate_documentation(self):
        """Generate user documentation files"""
        docs_dir = self.staging_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # Quick start guide
        quickstart = docs_dir / "QUICKSTART.txt"
        quickstart.write_text(f"""
Sunflower AI Professional System - Quick Start
==============================================
Version: 6.2
Batch: {self.batch_id}

FIRST TIME SETUP:
1. Insert this USB device into your computer
2. The Sunflower AI launcher will start automatically
3. Follow the on-screen setup wizard
4. Create a parent account with secure password
5. Add child profiles for each family member

DAILY USE:
1. Insert USB and wait for auto-launch
2. Select child profile
3. Enter parent PIN for access
4. Child can now interact with AI tutor
5. Review session logs in Parent Dashboard

IMPORTANT:
- Keep this USB device safe and secure
- Do not share parent PIN with children
- Review safety reports regularly
- Backup profiles monthly

For support, visit: sunflowerai.example.com/support
""")
        
        # Directory structure documentation
        structure_doc = docs_dir / "USB_STRUCTURE.txt"
        structure_doc.write_text(f"""
USB Partition Structure
======================

{self._generate_directory_tree()}

Directory Descriptions:
{self._generate_directory_descriptions()}

⚠️ DO NOT manually modify files in these directories.
Use the Sunflower AI application to manage all data.
""")
    
    def _generate_directory_tree(self) -> str:
        """Generate ASCII tree of directory structure"""
        tree_lines = ["USB_ROOT/"]
        for dir_key, dir_name in self.path_config.USB_STRUCTURE.items():
            if dir_name.startswith('.'):
                tree_lines.append(f"├── {dir_name:<20} [hidden]")
            else:
                tree_lines.append(f"├── {dir_name}/")
        return '\n'.join(tree_lines)
    
    def _generate_directory_descriptions(self) -> str:
        """Generate directory descriptions"""
        descriptions = {
            'profiles': 'Family member profiles and settings',
            'conversations': 'Encrypted conversation histories',
            'sessions': 'Learning session data and analytics',
            'logs': 'System, safety, and performance logs',
            'safety': 'Safety incident tracking and reports',
            'progress': 'Educational progress and achievements',
            'backups': 'Automatic and manual data backups',
            'cache': 'Temporary cache files (safe to delete)',
            'config': 'System configuration files',
            'security': 'Security tokens and encryption data'
        }
        
        lines = []
        for dir_key, dir_name in self.path_config.USB_STRUCTURE.items():
            desc = descriptions.get(dir_key, 'System directory')
            lines.append(f"- {dir_name:<20} {desc}")
        return '\n'.join(lines)
    
    def create_zip_package(self):
        """Create a ZIP package of the USB partition"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{self.path_config.USB_PARTITION_NAME}_{self.batch_id}_{timestamp}.zip"
        zip_path = self.output_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.staging_dir.rglob("*"):
                if file_path.is_file():
                    arc_name = file_path.relative_to(self.staging_dir)
                    zf.write(file_path, arc_name)
        
        # Calculate and display size information
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"✅ Created ZIP package: {zip_path}")
        print(f"   Size: {zip_size_mb:.2f} MB")
        
        # FIX BUG-010: Validate final package size
        if zip_size_mb > self.partition_size_mb:
            print(f"⚠️  Warning: ZIP package ({zip_size_mb:.2f}MB) exceeds partition size ({self.partition_size_mb}MB)")
            print(f"   This may cause issues during deployment")
        
        return zip_path
    
    def create_partition_image(self):
        """Create a disk image file for USB duplication"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"{self.path_config.USB_PARTITION_NAME}_{self.batch_id}_{timestamp}.img"
        image_path = self.output_dir / image_filename
        
        # Calculate image size (add some padding)
        content_size = sum(f.stat().st_size for f in self.staging_dir.rglob("*") if f.is_file())
        content_size_mb = content_size / (1024 * 1024)
        
        # FIX BUG-010: Ensure image size respects partition size limits
        image_size_mb = max(self.partition_size_mb, int(content_size_mb + 50))  # 50MB padding
        
        if image_size_mb > self.partition_size_mb:
            print(f"⚠️  Warning: Content size ({content_size_mb:.2f}MB) exceeds partition allocation")
            print(f"   Adjusting image size to {image_size_mb}MB")
        
        if platform.system() == "Windows":
            # Windows: Create VHD disk image
            self._create_windows_vhd(image_path, image_size_mb)
        elif platform.system() == "Darwin":
            # macOS: Create DMG disk image
            self._create_macos_dmg(image_path, image_size_mb)
        else:
            # Linux: Create raw disk image
            self._create_linux_img(image_path, image_size_mb)
        
        print(f"✅ Created partition image: {image_path}")
        print(f"   Size: {image_size_mb} MB")
        
        return image_path
    
    def _create_windows_vhd(self, image_path: Path, size_mb: int):
        """Create VHD disk image on Windows"""
        diskpart_script = f"""
create vdisk file="{image_path}" maximum={size_mb} type=fixed
select vdisk file="{image_path}"
attach vdisk
create partition primary
format fs=fat32 quick label="{self.volume_label}"
assign
detach vdisk
exit
"""
        script_file = self.output_dir / "diskpart_script.txt"
        script_file.write_text(diskpart_script)
        
        try:
            subprocess.run(
                ["diskpart", "/s", str(script_file)],
                check=True,
                capture_output=True
            )
        finally:
            script_file.unlink()
    
    def _create_macos_dmg(self, image_path: Path, size_mb: int):
        """Create DMG disk image on macOS"""
        subprocess.run([
            "hdiutil", "create",
            "-size", f"{size_mb}m",
            "-fs", "FAT32",
            "-volname", self.volume_label,
            "-layout", "NONE",
            str(image_path)
        ], check=True)
        
        # Mount, copy files, unmount
        mount_output = subprocess.run([
            "hdiutil", "attach", str(image_path)
        ], capture_output=True, text=True, check=True)
        
        # Extract mount point from output
        mount_point = None
        for line in mount_output.stdout.split('\n'):
            if self.volume_label in line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    mount_point = parts[2].strip()
                    break
        
        if mount_point:
            # Copy files to mounted image
            subprocess.run([
                "cp", "-r", f"{self.staging_dir}/.", mount_point
            ], check=True)
            
            # Unmount
            subprocess.run([
                "hdiutil", "detach", mount_point
            ], check=True)
    
    def _create_linux_img(self, image_path: Path, size_mb: int):
        """Create raw disk image on Linux"""
        # Create empty image file
        subprocess.run([
            "dd", "if=/dev/zero", f"of={image_path}",
            f"bs=1M", f"count={size_mb}"
        ], check=True)
        
        # Create FAT32 filesystem
        subprocess.run([
            "mkfs.vfat", "-F", "32", "-n", self.volume_label,
            str(image_path)
        ], check=True)
        
        # Mount and copy files (requires sudo)
        self.temp_mount.mkdir(exist_ok=True)
        
        try:
            subprocess.run([
                "sudo", "mount", "-o", "loop", str(image_path),
                str(self.temp_mount)
            ], check=True)
            
            subprocess.run([
                "sudo", "cp", "-r", f"{self.staging_dir}/.",
                str(self.temp_mount)
            ], check=True)
            
        finally:
            subprocess.run([
                "sudo", "umount", str(self.temp_mount)
            ], check=False)


def main():
    """Command-line interface for USB partition preparation"""
    parser = argparse.ArgumentParser(
        description="Prepare USB partition for Sunflower AI Professional System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create directory structure only
  python prepare_usb_partition.py
  
  # Create ZIP package with custom size
  python prepare_usb_partition.py --format zip --size 2048
  
  # Create disk image for production
  python prepare_usb_partition.py --format image --batch-id PROD-001
  
  # Validate and prepare specific device
  python prepare_usb_partition.py --device /dev/disk2 --size 1024
"""
    )
    
    parser.add_argument(
        "--batch-id",
        help="Batch identifier (auto-generated if not specified)"
    )
    
    parser.add_argument(
        "--size",
        type=int,
        default=RECOMMENDED_USB_SIZE_MB,
        help=f"Partition size in MB (minimum: {MINIMUM_USB_SIZE_MB}, recommended: {RECOMMENDED_USB_SIZE_MB})"
    )
    
    parser.add_argument(
        "--format",
        choices=["directory", "zip", "image"],
        default="directory",
        help="Output format (default: directory)"
    )
    
    parser.add_argument(
        "--device",
        help="Target USB device path (e.g., /dev/disk2 or \\\\.\\PhysicalDrive2)"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate device size, don't prepare partition"
    )
    
    args = parser.parse_args()
    
    # Create preparer instance
    try:
        preparer = USBPartitionPreparer(
            batch_id=args.batch_id,
            partition_size_mb=args.size
        )
        
        # Validate only mode
        if args.validate_only and args.device:
            if preparer._validate_target_device(args.device):
                print("✅ Device validation successful")
                return 0
            else:
                print("❌ Device validation failed")
                return 1
        
        # Prepare partition
        output = preparer.prepare(
            output_format=args.format,
            target_device=args.device
        )
        
        print(f"\n✅ Success! Output: {output}")
        return 0
        
    except ValueError as e:
        print(f"❌ Validation Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

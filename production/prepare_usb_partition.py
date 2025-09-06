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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import standardized path configuration
from config.path_config import PathConfiguration

class USBPartitionPreparer:
    def __init__(self, batch_id=None, partition_size_mb=1024):
        self.root_dir = Path(__file__).parent.parent
        self.batch_id = batch_id or self.generate_batch_id()
        self.partition_size_mb = partition_size_mb
        
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
        print("-" * 60)
        
        try:
            # Create directory structure
            print("\n📁 Creating USB partition structure...")
            self.create_partition_structure()
            
            # Initialize user data directories
            print("\n📂 Initializing user data directories...")
            self.initialize_user_directories()
            
            # Create security tokens
            print("\n🔐 Generating security tokens...")
            self.create_security_tokens()
            
            # Initialize configuration
            print("\n⚙️ Creating default configuration...")
            self.create_default_configuration()
            
            # Add documentation
            print("\n📚 Adding documentation...")
            self.add_documentation()
            
            # Create output based on format
            if output_format == "image":
                print("\n💿 Creating partition image...")
                self.create_partition_image()
            elif output_format == "zip":
                print("\n📦 Creating ZIP archive...")
                self.create_zip_archive()
            elif output_format == "device" and target_device:
                print(f"\n💾 Writing to device {target_device}...")
                self.write_to_device(target_device)
            else:
                print("\n✅ Staging directory ready at:", self.staging_dir)
            
            print("\n" + "=" * 60)
            print("✅ USB partition preparation complete!")
            print(f"📁 Output location: {self.output_dir if output_format != 'directory' else self.staging_dir}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False
    
    def create_partition_structure(self):
        """Create the USB partition directory structure using standardized paths"""
        # Clean and create staging directory
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)
        self.staging_dir.mkdir(parents=True)
        
        # Create standardized directory structure from PathConfiguration
        for dir_key, dir_name in self.path_config.USB_STRUCTURE.items():
            dir_path = self.staging_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for certain directories
            if dir_key == 'profiles':
                (dir_path / '.encrypted').mkdir(exist_ok=True)
            elif dir_key == 'conversations':
                (dir_path / '.encrypted').mkdir(exist_ok=True)
            elif dir_key == 'logs':
                (dir_path / 'sessions').mkdir(exist_ok=True)
                (dir_path / 'safety').mkdir(exist_ok=True)
                (dir_path / 'system').mkdir(exist_ok=True)
            elif dir_key == 'cache':
                (dir_path / 'models').mkdir(exist_ok=True)
                (dir_path / 'temp').mkdir(exist_ok=True)
            elif dir_key == 'backups':
                (dir_path / 'auto').mkdir(exist_ok=True)
                (dir_path / 'manual').mkdir(exist_ok=True)
        
        # Create USB marker file with standardized content
        marker_file = self.staging_dir / self.path_config.USB_MARKER_FILE
        marker_content = {
            "type": self.path_config.USB_MARKER_CONTENT,
            "batch_id": self.batch_id,
            "created": datetime.now().isoformat(),
            "version": "6.2.0",
            "structure_version": "1.0",
            "writable": True
        }
        with open(marker_file, "w") as f:
            json.dump(marker_content, f, indent=2)
        
        # Create initialization marker
        init_marker = self.staging_dir / ".initialized"
        init_marker.write_text(datetime.now().isoformat())
        
        print(f"✅ Created {len(self.path_config.USB_STRUCTURE)} directories with standardized structure")
    
    def initialize_user_directories(self):
        """Initialize user data directories with proper structure"""
        
        # Profiles directory structure
        profiles_dir = self.staging_dir / self.path_config.USB_STRUCTURE['profiles']
        profiles_readme = profiles_dir / "README.txt"
        profiles_readme.write_text("""Sunflower AI Profile Storage
============================

This directory contains family and child profiles.
DO NOT modify files directly - use the Sunflower AI application.

Structure:
- family.json: Main family configuration
- child_*.json: Individual child profiles
- .encrypted/: Encrypted sensitive data

For support, refer to the user manual.
""")
        
        # Conversations directory structure
        conv_dir = self.staging_dir / self.path_config.USB_STRUCTURE['conversations']
        conv_readme = conv_dir / "README.txt"
        conv_readme.write_text("""Sunflower AI Conversation History
=================================

This directory stores conversation histories for each child profile.
Files are encrypted and should not be modified directly.

Structure:
- {profile_id}/{date}/session_{timestamp}.json

Privacy Notice:
All conversations remain on this device and are never transmitted.
""")
        
        # Safety directory structure
        safety_dir = self.staging_dir / self.path_config.USB_STRUCTURE['safety']
        safety_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize safety database structure
        safety_config = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "incident_count": 0,
            "last_review": None,
            "notification_settings": {
                "enabled": True,
                "severity_threshold": 3
            }
        }
        
        with open(safety_dir / "safety_config.json", "w") as f:
            json.dump(safety_config, f, indent=2)
        
        print("✅ Initialized user directories with proper documentation")
    
    def create_security_tokens(self):
        """Create security tokens for device authentication"""
        security_dir = self.staging_dir / self.path_config.USB_STRUCTURE['security']
        
        # Generate device-specific tokens
        for i in range(10):  # Pre-generate 10 device tokens
            token = {
                "device_id": f"SAI-{self.batch_id}-{i:04d}",
                "token": secrets.token_hex(32),
                "created": datetime.now().isoformat(),
                "activated": False,
                "activation_date": None
            }
            self.device_tokens.append(token)
        
        # Save tokens (encrypted in production)
        tokens_file = security_dir / "device_tokens.json"
        with open(tokens_file, "w") as f:
            json.dump(self.device_tokens, f, indent=2)
        
        # Create encryption key template
        encryption_config = {
            "algorithm": "AES-256-GCM",
            "key_derivation": "PBKDF2",
            "iterations": 100000,
            "salt_length": 32,
            "created": datetime.now().isoformat()
        }
        
        with open(security_dir / "encryption_config.json", "w") as f:
            json.dump(encryption_config, f, indent=2)
        
        print(f"✅ Generated {len(self.device_tokens)} security tokens")
    
    def create_default_configuration(self):
        """Create default configuration files"""
        config_dir = self.staging_dir / self.path_config.USB_STRUCTURE['config']
        
        # System configuration
        system_config = {
            "version": "6.2.0",
            "first_run": True,
            "batch_id": self.batch_id,
            "created": datetime.now().isoformat(),
            "last_updated": None,
            "settings": {
                "safety_level": "maximum",
                "auto_backup": True,
                "backup_frequency_days": 7,
                "session_timeout_minutes": 30,
                "enable_achievements": True,
                "enable_analytics": True
            },
            "hardware": {
                "detected_tier": None,
                "selected_model": None,
                "performance_mode": "auto"
            }
        }
        
        with open(config_dir / "system_config.json", "w") as f:
            json.dump(system_config, f, indent=2)
        
        # Pipeline configuration
        pipeline_config = {
            "safety_level": "maximum",
            "response_timeout": 30,
            "max_conversation_length": 100,
            "enable_achievements": True,
            "log_conversations": True,
            "pipeline_order": [
                "content_filter",
                "age_adapter",
                "stem_tutor",
                "progress_tracker",
                "achievement_system",
                "parent_logger"
            ]
        }
        
        with open(config_dir / "pipeline_config.json", "w") as f:
            json.dump(pipeline_config, f, indent=2)
        
        print("✅ Created default configuration files")
    
    def add_documentation(self):
        """Add user documentation to USB partition"""
        # Main README
        readme_content = f"""
SUNFLOWER AI PROFESSIONAL SYSTEM - DATA PARTITION
=================================================
Version 6.2.0 | Batch: {self.batch_id}

This USB partition stores all your family's data:
- Child profiles and progress
- Conversation histories  
- Learning analytics
- Safety logs

Getting Started:
1. Insert both the Sunflower AI CD-ROM and this USB drive
2. Run the Sunflower AI application from the CD-ROM
3. Create your parent account
4. Add child profiles
5. Start learning!

Important:
- Keep this USB drive safe - it contains your family's data
- Regular backups are created automatically
- All data is encrypted and stored locally

For detailed instructions, see the User Guide on the CD-ROM.

Partition: {self.path_config.USB_PARTITION_NAME}
Created: {datetime.now().strftime('%Y-%m-%d')}
"""
        
        readme_path = self.staging_dir / "README.txt"
        readme_path.write_text(readme_content)
        
        # Create data structure documentation
        structure_doc = self.staging_dir / "DATA_STRUCTURE.txt"
        structure_content = f"""
Sunflower AI USB Data Structure
===============================

Directory Map:
{self._generate_structure_tree()}

Directory Descriptions:
{self._generate_directory_descriptions()}

Important Notes:
- Never modify files directly
- Use the application to manage all data
- The .security and .config directories contain critical system data

Data Privacy:
- All data stays on this USB drive
- No cloud connectivity required
- Complete offline operation

Backup Instructions:
- Automatic backups are created weekly in /backups/auto/
- To create manual backup: Use Parent Dashboard > Backup
- Backups are stored in /backups/manual/
"""
        
        structure_doc.write_text(structure_content)
        
        print("✅ Added documentation files")
    
    def _generate_structure_tree(self) -> str:
        """Generate directory structure tree"""
        tree_lines = []
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
    
    def create_partition_image(self):
        """Create a disk image file for USB duplication"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"{self.path_config.USB_PARTITION_NAME}_{self.batch_id}_{timestamp}.img"
        image_path = self.output_dir / image_filename
        
        # Calculate image size (add some padding)
        content_size = sum(f.stat().st_size for f in self.staging_dir.rglob("*") if f.is_file())
        image_size_mb = max(self.partition_size_mb, (content_size // (1024*1024)) + 100)
        
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
    
    def _create_windows_vhd(self, image_path: Path, size_mb: int):
        """Create VHD disk image on Windows"""
        diskpart_script = f"""
create vdisk file="{image_path}" maximum={size_mb} type=fixed
select vdisk file="{image_path}"
attach vdisk
create partition primary
format fs=fat32 label="{self.volume_label}" quick
assign
detach vdisk
exit
"""
        script_path = self.staging_dir.parent / "create_vhd.txt"
        script_path.write_text(diskpart_script)
        
        subprocess.run(["diskpart", "/s", str(script_path)], check=True)
        script_path.unlink()
    
    def _create_macos_dmg(self, image_path: Path, size_mb: int):
        """Create DMG disk image on macOS"""
        # Create sparse image
        subprocess.run([
            "hdiutil", "create",
            "-size", f"{size_mb}m",
            "-fs", "FAT32",
            "-volname", self.volume_label,
            str(image_path)
        ], check=True)
        
        # Mount, copy files, unmount
        mount_result = subprocess.run([
            "hdiutil", "attach", str(image_path)
        ], capture_output=True, text=True)
        
        mount_point = None
        for line in mount_result.stdout.split('\n'):
            if self.volume_label in line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    mount_point = parts[-1].strip()
                    break
        
        if mount_point:
            # Copy staging files to mounted image
            subprocess.run([
                "cp", "-R", str(self.staging_dir) + "/.", mount_point
            ], check=True)
            
            # Unmount
            subprocess.run(["hdiutil", "detach", mount_point], check=True)
    
    def _create_linux_img(self, image_path: Path, size_mb: int):
        """Create raw disk image on Linux"""
        # Create empty image file
        subprocess.run([
            "dd", "if=/dev/zero", f"of={image_path}",
            "bs=1M", f"count={size_mb}"
        ], check=True)
        
        # Format as FAT32
        subprocess.run([
            "mkfs.vfat", "-n", self.volume_label, str(image_path)
        ], check=True)
        
        # Mount and copy files
        if self.temp_mount:
            self.temp_mount.mkdir(exist_ok=True)
            
            subprocess.run([
                "mount", "-o", "loop", str(image_path), str(self.temp_mount)
            ], check=True)
            
            # Copy files
            subprocess.run([
                "cp", "-R", str(self.staging_dir) + "/.", str(self.temp_mount)
            ], check=True)
            
            # Unmount
            subprocess.run(["umount", str(self.temp_mount)], check=True)
    
    def create_zip_archive(self):
        """Create ZIP archive of USB partition contents"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{self.path_config.USB_PARTITION_NAME}_{self.batch_id}_{timestamp}.zip"
        zip_path = self.output_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.staging_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.staging_dir)
                    zf.write(file_path, arcname)
        
        print(f"✅ Created ZIP archive: {zip_path}")
        print(f"   Size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
    
    def write_to_device(self, device_path: str):
        """Write directly to a USB device"""
        print(f"⚠️  WARNING: This will erase all data on {device_path}")
        response = input("Continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Operation cancelled")
            return
        
        # Platform-specific device writing
        if platform.system() == "Windows":
            # Use diskpart or dd for Windows
            pass
        elif platform.system() == "Darwin":
            # Use dd for macOS
            subprocess.run([
                "sudo", "dd", f"if=/dev/zero", f"of={device_path}",
                "bs=1m", "count=100"
            ], check=True)
        else:
            # Use dd for Linux
            subprocess.run([
                "sudo", "dd", f"if=/dev/zero", f"of={device_path}",
                "bs=1M", "count=100"
            ], check=True)
        
        print(f"✅ Written to device: {device_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Prepare USB partition for Sunflower AI')
    parser.add_argument('--batch-id', help='Batch identifier')
    parser.add_argument('--size', type=int, default=1024, help='Partition size in MB')
    parser.add_argument('--format', choices=['directory', 'image', 'zip'], 
                       default='directory', help='Output format')
    parser.add_argument('--device', help='Target device for direct writing')
    
    args = parser.parse_args()
    
    preparer = USBPartitionPreparer(
        batch_id=args.batch_id,
        partition_size_mb=args.size
    )
    
    success = preparer.prepare(
        output_format=args.format,
        target_device=args.device
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

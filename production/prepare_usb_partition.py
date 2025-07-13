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

class USBPartitionPreparer:
    def __init__(self, batch_id=None, partition_size_mb=1024):
        self.root_dir = Path(__file__).parent.parent
        self.batch_id = batch_id or self.generate_batch_id()
        self.partition_size_mb = partition_size_mb
        
        # Paths
        self.staging_dir = self.root_dir / "usb_staging" / "SunflowerData"
        self.output_dir = self.root_dir / "manufacturing" / "usb_images"
        self.temp_mount = Path("/tmp/sunflower_usb_mount") if platform.system() != "Windows" else None
        
        # USB configuration
        self.volume_label = "SUNFLOWERDATA"
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
            
            # Generate security components
            print("\n🔒 Generating security components...")
            self.generate_security_components()
            
            # Create configuration files
            print("\n⚙️ Creating configuration files...")
            self.create_configuration_files()
            
            # Add documentation
            print("\n📚 Adding user documentation...")
            self.add_documentation()
            
            # Create partition image or prepare device
            if output_format == "image":
                print("\n💿 Creating partition image...")
                image_path = self.create_partition_image()
                print(f"\n✨ USB partition image created: {image_path}")
                self.save_build_record(image_path)
                return image_path
                
            elif output_format == "device" and target_device:
                print(f"\n💾 Preparing USB device: {target_device}")
                if self.prepare_usb_device(target_device):
                    print("\n✨ USB device prepared successfully")
                    return target_device
                else:
                    print("\n❌ USB device preparation failed")
                    return None
                    
            else:
                # Just prepare staging directory
                print("\n✨ USB partition structure prepared in staging directory")
                print(f"📍 Location: {self.staging_dir}")
                self.save_build_record(self.staging_dir)
                return self.staging_dir
                
        except Exception as e:
            print(f"\n❌ USB preparation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_partition_structure(self):
        """Create the USB partition directory structure"""
        # Clean and create staging directory
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)
        self.staging_dir.mkdir(parents=True)
        
        # Create directory structure
        directories = [
            "profiles",
            "profiles/.encrypted",
            "conversations",
            "conversations/.encrypted",
            "logs",
            "logs/sessions",
            "logs/safety",
            "logs/system",
            "cache",
            "cache/models",
            "cache/temp",
            "backups",
            "backups/auto",
            "backups/manual",
            ".security",
            ".config"
        ]
        
        for dir_name in directories:
            (self.staging_dir / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create USB marker file
        marker_file = self.staging_dir / "sunflower_data.id"
        marker_content = {
            "type": "SUNFLOWER_DATA_PARTITION",
            "batch_id": self.batch_id,
            "created": datetime.now().isoformat(),
            "version": "1.0"
        }
        with open(marker_file, "w") as f:
            json.dump(marker_content, f, indent=2)
        
        # Create initialization marker
        init_marker = self.staging_dir / ".initialized"
        init_marker.write_text(datetime.now().isoformat())
        
        print(f"✅ Created {len(directories)} directories")
    
    def initialize_user_directories(self):
        """Initialize user data directories with proper structure"""
        
        # Profiles directory structure
        profiles_readme = self.staging_dir / "profiles" / "README.txt"
        profiles_readme.write_text("""Sunflower AI Profile Storage
============================

This directory contains family and child profiles.
DO NOT modify files directly - use the Sunflower AI application.

Structure:
- family.json: Main family configuration
- .encrypted/: Encrypted individual profile data

For support, refer to the user manual.
""")
        
        # Conversations directory structure
        conv_readme = self.staging_dir / "conversations" / "README.txt"
        conv_readme.write_text("""Sunflower AI Conversation History
=================================

This directory stores conversation histories for each child profile.
Files are encrypted and should not be modified directly.

Privacy Notice:
- All conversations are stored locally on this USB
- No data is sent to external servers
- Parents can review all conversations through the dashboard
""")
        
        # Logs directory structure
        logs_config = {
            "version": "1.0",
            "retention_days": 90,
            "max_size_mb": 100,
            "categories": {
                "sessions": "Learning session logs",
                "safety": "Safety alerts and incidents",
                "system": "Application system logs"
            }
        }
        with open(self.staging_dir / "logs" / "config.json", "w") as f:
            json.dump(logs_config, f, indent=2)
        
        # Cache directory configuration
        cache_config = {
            "max_size_mb": 500,
            "auto_cleanup": True,
            "cleanup_age_days": 30
        }
        with open(self.staging_dir / "cache" / "config.json", "w") as f:
            json.dump(cache_config, f, indent=2)
        
        print("✅ Initialized user data directories")
    
    def generate_security_components(self):
        """Generate security and encryption components"""
        security_dir = self.staging_dir / ".security"
        
        # Generate device authentication token
        device_token = {
            "device_id": str(uuid.uuid4()),
            "batch_id": self.batch_id,
            "created": datetime.now().isoformat(),
            "auth_key": secrets.token_urlsafe(32),
            "pairing_code": self.generate_pairing_code()
        }
        
        with open(security_dir / "device_token.json", "w") as f:
            json.dump(device_token, f, indent=2)
        
        self.device_tokens.append(device_token)
        
        # Generate encryption keys for profile data
        encryption_config = {
            "version": "1.0",
            "algorithm": "AES-256-GCM",
            "key_derivation": "PBKDF2-SHA256",
            "iterations": 100000,
            "salt": secrets.token_hex(16)
        }
        
        with open(security_dir / "encryption_config.json", "w") as f:
            json.dump(encryption_config, f, indent=2)
        
        # Create keystore (will be populated on first parent login)
        keystore = {
            "initialized": False,
            "creation_date": None,
            "master_key_hash": None,
            "profile_keys": {}
        }
        
        with open(security_dir / "keystore.json", "w") as f:
            json.dump(keystore, f, indent=2)
        
        # Create integrity verification file
        integrity = {
            "batch_id": self.batch_id,
            "partition_type": "user_data",
            "created": datetime.now().isoformat(),
            "checksum_algorithm": "SHA256",
            "verified": False
        }
        
        with open(security_dir / "integrity.json", "w") as f:
            json.dump(integrity, f, indent=2)
        
        print("✅ Generated security components")
    
    def generate_pairing_code(self):
        """Generate human-readable pairing code for CD-ROM/USB verification"""
        # Generate 3 groups of 4 characters (like XXXX-XXXX-XXXX)
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Exclude confusing characters
        groups = []
        for _ in range(3):
            group = ''.join(secrets.choice(chars) for _ in range(4))
            groups.append(group)
        return '-'.join(groups)
    
    def create_configuration_files(self):
        """Create configuration files for the USB partition"""
        config_dir = self.staging_dir / ".config"
        
        # Partition configuration
        partition_config = {
            "version": "1.0",
            "partition_type": "user_data",
            "filesystem": self.filesystem,
            "size_mb": self.partition_size_mb,
            "features": {
                "encryption": True,
                "compression": False,
                "auto_backup": True,
                "cloud_sync": False
            }
        }
        
        with open(config_dir / "partition.json", "w") as f:
            json.dump(partition_config, f, indent=2)
        
        # Application settings template
        app_settings = {
            "first_run": True,
            "setup_complete": False,
            "family_created": False,
            "theme": "default",
            "language": "en-US",
            "timezone": "auto",
            "updates": {
                "check_enabled": False,
                "last_check": None,
                "channel": "stable"
            }
        }
        
        with open(config_dir / "settings.json", "w") as f:
            json.dump(app_settings, f, indent=2)
        
        # Backup configuration
        backup_config = {
            "auto_backup": {
                "enabled": True,
                "frequency": "weekly",
                "max_backups": 4,
                "include_conversations": True
            },
            "manual_backup": {
                "compression": True,
                "encryption": True
            }
        }
        
        with open(config_dir / "backup_config.json", "w") as f:
            json.dump(backup_config, f, indent=2)
        
        print("✅ Created configuration files")
    
    def add_documentation(self):
        """Add user documentation to USB partition"""
        # Create quick start guide
        quickstart = self.staging_dir / "QUICK_START.txt"
        quickstart.write_text("""Sunflower AI Quick Start Guide
==============================

Welcome to Sunflower AI!

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

Support: docs.sunflowerai.com
Version: 1.0
""")
        
        # Create data structure documentation
        structure_doc = self.staging_dir / "USB_STRUCTURE.txt"
        structure_doc.write_text("""Sunflower AI USB Data Structure
===============================

Directory Structure:
/profiles/          - Family and child profiles
/conversations/     - Encrypted conversation histories
/logs/             - System and safety logs
/cache/            - Temporary files (safe to delete)
/backups/          - Automatic and manual backups
/.security/        - Security and encryption files (DO NOT MODIFY)
/.config/          - Application configuration

Important Notes:
- Never modify files directly
- Use the application to manage all data
- The .security directory contains critical authentication data

Data Privacy:
- All data stays on this USB drive
- No cloud connectivity required
- Complete offline operation

Backup Instructions:
- Automatic backups are created weekly
- To create manual backup: Use Parent Dashboard > Backup
- Backups are stored in /backups/manual/
""")
        
        print("✅ Added documentation files")
    
    def create_partition_image(self):
        """Create a disk image file for USB duplication"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"sunflower_data_{self.batch_id}_{timestamp}.img"
        image_path = self.output_dir / image_filename
        
        # Calculate image size (add some padding)
        content_size = sum(f.stat().st_size for f in self.staging_dir.rglob("*") if f.is_file())
        image_size_mb = max(self.partition_size_mb, (content_size // (1024*1024)) + 100)
        
        if platform.system() == "Windows":
            # Windows: Create VHD disk image
            self._create_windows_vhd(image_path, image_size_mb)
        else:
            # Unix: Create raw disk image
            self._create_unix_disk_image(image_path, image_size_mb)
        
        # Also create a ZIP archive for easy distribution
        zip_path = image_path.with_suffix('.zip')
        print(f"📦 Creating ZIP archive: {zip_path.name}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.staging_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.staging_dir)
                    zf.write(file_path, arcname)
        
        print(f"✅ Created partition image: {image_path.name}")
        print(f"✅ Created ZIP archive: {zip_path.name}")
        
        return image_path
    
    def _create_windows_vhd(self, image_path, size_mb):
        """Create VHD disk image on Windows"""
        # Create diskpart script
        script_content = f"""create vdisk file="{image_path}" maximum={size_mb} type=fixed
select vdisk file="{image_path}"
attach vdisk
create partition primary
format fs=fat32 label="{self.volume_label}" quick
assign
"""
        script_path = Path("diskpart_script.txt")
        script_path.write_text(script_content)
        
        try:
            # Run diskpart
            result = subprocess.run(
                ["diskpart", "/s", str(script_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Diskpart failed: {result.stderr}")
            
            # Copy files to mounted VHD
            # This would require finding the assigned drive letter
            print("⚠️ Manual copy required for VHD contents")
            
        finally:
            script_path.unlink()
    
    def _create_unix_disk_image(self, image_path, size_mb):
        """Create disk image on Unix systems"""
        # Create empty image
        subprocess.run([
            "dd", "if=/dev/zero", f"of={image_path}",
            "bs=1M", f"count={size_mb}"
        ], check=True)
        
        # Create filesystem
        if platform.system() == "Darwin":
            # macOS
            subprocess.run([
                "hdiutil", "create", "-size", f"{size_mb}m",
                "-fs", "FAT32", "-volname", self.volume_label,
                str(image_path)
            ], check=True)
        else:
            # Linux
            subprocess.run([
                "mkfs.vfat", "-n", self.volume_label, str(image_path)
            ], check=True)
            
            # Mount and copy files
            if self.temp_mount:
                self.temp_mount.mkdir(exist_ok=True)
                
                try:
                    subprocess.run([
                        "mount", "-o", "loop", str(image_path), str(self.temp_mount)
                    ], check=True)
                    
                    # Copy all files
                    shutil.copytree(
                        self.staging_dir,
                        self.temp_mount,
                        dirs_exist_ok=True
                    )
                    
                finally:
                    subprocess.run(["umount", str(self.temp_mount)], check=True)
                    self.temp_mount.rmdir()
    
    def prepare_usb_device(self, device_path):
        """Prepare an actual USB device"""
        if not Path(device_path).exists():
            print(f"❌ Device not found: {device_path}")
            return False
        
        print(f"⚠️ WARNING: This will erase all data on {device_path}")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Aborted by user")
            return False
        
        try:
            if platform.system() == "Windows":
                return self._prepare_windows_usb(device_path)
            else:
                return self._prepare_unix_usb(device_path)
        except Exception as e:
            print(f"❌ Device preparation failed: {e}")
            return False
    
    def _prepare_windows_usb(self, device_path):
        """Prepare USB device on Windows"""
        # This would use diskpart to format and prepare the device
        print("⚠️ Windows USB preparation requires manual steps")
        print(f"1. Format {device_path} as FAT32 with label '{self.volume_label}'")
        print(f"2. Copy contents of {self.staging_dir} to the device")
        return True
    
    def _prepare_unix_usb(self, device_path):
        """Prepare USB device on Unix systems"""
        # Format device
        subprocess.run([
            "mkfs.vfat", "-n", self.volume_label, device_path
        ], check=True)
        
        # Mount and copy
        mount_point = Path(f"/tmp/sunflower_mount_{os.getpid()}")
        mount_point.mkdir(exist_ok=True)
        
        try:
            subprocess.run(["mount", device_path, str(mount_point)], check=True)
            
            # Copy all files
            for item in self.staging_dir.iterdir():
                if item.is_dir():
                    shutil.copytree(item, mount_point / item.name)
                else:
                    shutil.copy2(item, mount_point / item.name)
            
            print("✅ Files copied to USB device")
            
        finally:
            subprocess.run(["umount", str(mount_point)], check=True)
            mount_point.rmdir()
        
        return True
    
    def save_build_record(self, output_path):
        """Save build record for tracking"""
        records_dir = self.root_dir / "manufacturing" / "batch_records"
        records_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate content size
        if output_path.is_dir():
            total_size = sum(f.stat().st_size for f in output_path.rglob("*") if f.is_file())
        else:
            total_size = output_path.stat().st_size
        
        record = {
            "batch_id": self.batch_id,
            "type": "usb_partition",
            "created": datetime.now().isoformat(),
            "output_path": str(output_path),
            "size_mb": total_size / (1024**2),
            "partition_size_mb": self.partition_size_mb,
            "device_tokens": self.device_tokens,
            "filesystem": self.filesystem,
            "features": {
                "encryption": True,
                "auto_backup": True,
                "multi_profile": True
            }
        }
        
        record_file = records_dir / f"usb_{self.batch_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(record_file, "w") as f:
            json.dump(record, f, indent=2)
        
        print(f"✅ Build record saved: {record_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Prepare Sunflower AI USB Partition")
    parser.add_argument(
        "--batch-id",
        help="Batch ID (should match CD-ROM batch)"
    )
    parser.add_argument(
        "--size",
        type=int,
        default=1024,
        help="Partition size in MB (default: 1024)"
    )
    parser.add_argument(
        "--format",
        choices=["directory", "image", "device"],
        default="directory",
        help="Output format"
    )
    parser.add_argument(
        "--device",
        help="Target device path (for device format)"
    )
    
    args = parser.parse_args()
    
    preparer = USBPartitionPreparer(
        batch_id=args.batch_id,
        partition_size_mb=args.size
    )
    
    result = preparer.prepare(
        output_format=args.format,
        target_device=args.device
    )
    
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()

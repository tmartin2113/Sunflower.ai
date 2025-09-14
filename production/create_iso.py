#!/usr/bin/env python3
"""
Create ISO image for Sunflower AI CD-ROM partition.
This script builds the read-only ISO9660 partition containing the system files.

The ISO includes:
- Platform-specific executables (Windows/macOS)
- AI models (selected based on hardware)
- System resources and documentation
- Partition identifiers for auto-detection
"""

import os
import sys
import json
import shutil
import subprocess
import hashlib
import tempfile
import platform
import argparse
from pathlib import Path
from datetime import datetime
import secrets


class ISOCreator:
    def __init__(self, version="1.0.0", batch_id=None):
        self.root_dir = Path(__file__).parent.parent
        self.version = version
        self.batch_id = batch_id or self.generate_batch_id()
        self.build_date = datetime.now().strftime("%Y-%m-%d")
        
        # Paths
        self.cdrom_staging = self.root_dir / "cdrom_staging"
        self.iso_output_dir = self.root_dir / "manufacturing" / "iso_images"
        self.temp_iso_root = Path(tempfile.mkdtemp(prefix="sunflower_iso_"))
        
        # ISO configuration
        self.iso_filename = f"sunflower_cdrom_{self.version}_{self.batch_id}.iso"
        self.iso_volume_id = "SUNFLOWER_AI"
        self.iso_max_size_gb = 4  # CD-ROM partition size
        
        # Tracking
        self.manifest = {
            "version": self.version,
            "batch_id": self.batch_id,
            "build_date": self.build_date,
            "components": {},
            "checksums": {}
        }
        
        # FIX BUG-016: Track open file handles for cleanup
        self._open_handles = []
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.cleanup()
    
    def generate_batch_id(self):
        """Generate unique batch identifier"""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_id = secrets.token_hex(4).upper()
        return f"{timestamp}-{random_id}"
    
    def create(self):
        """Main ISO creation process"""
        print(f"💿 Sunflower AI ISO Creator")
        print(f"📦 Batch ID: {self.batch_id}")
        print(f"📌 Version: {self.version}")
        print(f"📅 Build Date: {self.build_date}")
        print("-" * 60)
        
        try:
            # Validate prerequisites
            print("\n🔍 Validating prerequisites...")
            if not self.validate_prerequisites():
                return False
            
            # Prepare ISO contents
            print("\n📁 Preparing ISO contents...")
            self.prepare_iso_contents()
            
            # Add platform-specific files
            print("\n🖥️ Adding platform executables...")
            self.add_platform_files()
            
            # Add AI models
            print("\n🤖 Adding AI models...")
            self.add_ai_models()
            
            # Add resources
            print("\n📚 Adding resources...")
            self.add_resources()
            
            # Create identifiers
            print("\n🆔 Creating partition identifiers...")
            self.create_identifiers()
            
            # Generate checksums
            print("\n🔐 Generating checksums...")
            self.generate_checksums()
            
            # Build ISO
            print("\n🔨 Building ISO image...")
            iso_path = self.build_iso()
            
            # Verify ISO
            print("\n✔️ Verifying ISO...")
            if self.verify_iso(iso_path):
                print(f"\n✅ ISO created successfully: {iso_path}")
                
                # Save build record
                self.save_build_record(iso_path)
                return iso_path
            else:
                print("\n❌ ISO verification failed")
                return False
                
        except Exception as e:
            print(f"\n❌ ISO creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Always cleanup temp directory
            self.cleanup()
    
    def cleanup(self):
        """Clean up temporary files and close any open handles"""
        # FIX BUG-016: Close all tracked file handles
        for handle in self._open_handles:
            try:
                if not handle.closed:
                    handle.close()
            except Exception:
                pass  # Handle already closed or invalid
        self._open_handles.clear()
        
        # Remove temp directory
        if self.temp_iso_root.exists():
            try:
                shutil.rmtree(self.temp_iso_root)
                print(f"🧹 Cleaned up temporary files")
            except Exception as e:
                print(f"⚠️ Warning: Could not remove temp directory: {e}")
    
    def validate_prerequisites(self):
        """Validate all required files are present"""
        required_paths = {
            "Windows executable": self.cdrom_staging / "Windows" / "SunflowerAI.exe",
            "macOS application": self.cdrom_staging / "macOS" / "SunflowerAI.app",
            "Models directory": self.cdrom_staging / "models",
            "Resources": self.root_dir / "resources"
        }
        
        missing = []
        for name, path in required_paths.items():
            if path.exists():
                print(f"✅ Found: {name}")
            else:
                print(f"❌ Missing: {name} at {path}")
                missing.append(name)
        
        if missing:
            print("\n❌ Prerequisites not met. Please build required components first.")
            return False
        
        return True
    
    def prepare_iso_contents(self):
        """Prepare the base ISO directory structure"""
        # Create base directories
        directories = [
            "Windows",
            "macOS",
            "models",
            "resources",
            "docs",
            "autorun"
        ]
        
        for dir_name in directories:
            (self.temp_iso_root / dir_name).mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Created ISO directory structure at {self.temp_iso_root}")
    
    def add_platform_files(self):
        """Add platform-specific executables"""
        # Windows files
        windows_src = self.cdrom_staging / "Windows"
        windows_dst = self.temp_iso_root / "Windows"
        
        if windows_src.exists():
            for file in windows_src.rglob("*"):
                if file.is_file():
                    relative = file.relative_to(windows_src)
                    dst_file = windows_dst / relative
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, dst_file)
            
            self.manifest["components"]["windows"] = True
            print(f"✅ Added Windows executables")
        
        # macOS files
        macos_src = self.cdrom_staging / "macOS"
        macos_dst = self.temp_iso_root / "macOS"
        
        if macos_src.exists():
            if (macos_src / "SunflowerAI.app").exists():
                shutil.copytree(
                    macos_src / "SunflowerAI.app",
                    macos_dst / "SunflowerAI.app",
                    symlinks=True
                )
            
            self.manifest["components"]["macos"] = True
            print(f"✅ Added macOS application")
    
    def add_ai_models(self):
        """Add AI models based on hardware requirements"""
        models_src = self.cdrom_staging / "models"
        models_dst = self.temp_iso_root / "models"
        
        if not models_src.exists():
            print("⚠️ No models directory found, skipping...")
            return
        
        # Define model variants to include
        model_variants = [
            "llama3.2-7b.gguf",    # High-end systems
            "llama3.2-3b.gguf",    # Mid-range systems
            "llama3.2-1b.gguf",    # Low-end systems
            "llama3.2-1b-q4_0.gguf"  # Minimum spec systems
        ]
        
        models_added = []
        total_size = 0
        
        for model_file in model_variants:
            src_path = models_src / model_file
            if src_path.exists():
                dst_path = models_dst / model_file
                shutil.copy2(src_path, dst_path)
                
                file_size = src_path.stat().st_size
                total_size += file_size
                models_added.append(model_file)
                
                print(f"  Added: {model_file} ({file_size / (1024**3):.2f} GB)")
        
        # Copy model selection script
        model_selector = self.root_dir / "src" / "model_selector.py"
        if model_selector.exists():
            shutil.copy2(model_selector, models_dst / "model_selector.py")
        
        self.manifest["components"]["models"] = models_added
        self.manifest["models_size_gb"] = total_size / (1024**3)
        
        print(f"✅ Added {len(models_added)} AI models ({total_size / (1024**3):.2f} GB total)")
    
    def add_resources(self):
        """Add documentation and resources"""
        resources_src = self.root_dir / "resources"
        resources_dst = self.temp_iso_root / "resources"
        
        if resources_src.exists():
            # Copy select resources (not everything)
            resource_files = [
                "icons/sunflower.ico",
                "images/splash.png",
                "docs/quickstart.pdf",
                "docs/parent_guide.pdf"
            ]
            
            for resource in resource_files:
                src_file = resources_src / resource
                if src_file.exists():
                    dst_file = resources_dst / resource
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
        
        # Add autorun files for Windows
        self.create_autorun_files()
        
        print(f"✅ Added resources and documentation")
    
    def create_autorun_files(self):
        """Create autorun.inf for Windows auto-launch"""
        autorun_content = f"""[autorun]
open=Windows\\SunflowerAI.exe
icon=Windows\\SunflowerAI.exe,0
label=Sunflower AI Professional System v{self.version}

[Content]
MusicFiles=false
PictureFiles=false
VideoFiles=false
"""
        
        # FIX BUG-016: Use context manager for file operations
        autorun_file = self.temp_iso_root / "autorun.inf"
        with open(autorun_file, "w", encoding='utf-8') as f:
            f.write(autorun_content)
        
        # Create desktop.ini for nice folder appearance
        desktop_ini_content = """[.ShellClassInfo]
IconResource=Windows\\SunflowerAI.exe,0
"""
        
        # FIX BUG-016: Use context manager for file operations
        desktop_file = self.temp_iso_root / "desktop.ini"
        with open(desktop_file, "w", encoding='utf-8') as f:
            f.write(desktop_ini_content)
        
        # Set files as hidden/system on Windows
        if platform.system() == "Windows":
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            FILE_ATTRIBUTE_SYSTEM = 0x04
            
            for file in [autorun_file, desktop_file]:
                ctypes.windll.kernel32.SetFileAttributesW(
                    str(file),
                    FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
                )
    
    def create_identifiers(self):
        """Create partition identification files"""
        # CD-ROM identifier (matches partition_manager.py check)
        # FIX BUG-016: Use context manager for file operations
        id_file = self.temp_iso_root / "sunflower_cd.id"
        with open(id_file, "w", encoding='utf-8') as f:
            f.write(f"SUNFLOWER_CDROM_{self.batch_id}")
        
        # Partition info
        partition_info = {
            "type": "CD-ROM",
            "version": self.version,
            "batch_id": self.batch_id,
            "build_date": self.build_date,
            "read_only": True,
            "partition_size_gb": self.iso_max_size_gb
        }
        
        # FIX BUG-016: Use context manager for file operations
        info_file = self.temp_iso_root / ".partition_info"
        with open(info_file, "w", encoding='utf-8') as f:
            json.dump(partition_info, f, indent=2)
        
        print(f"✅ Created partition identifiers")
    
    def generate_checksums(self):
        """Generate checksums for all files"""
        checksums = {}
        total_size = 0
        
        for root, dirs, files in os.walk(self.temp_iso_root):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.temp_iso_root)
                
                # Calculate checksum
                checksum = self.calculate_checksum(file_path)
                checksums[str(relative_path)] = checksum
                
                # Track size
                total_size += file_path.stat().st_size
        
        # Save checksums
        # FIX BUG-016: Use context manager for file operations
        checksum_file = self.temp_iso_root / "checksums.sha256"
        with open(checksum_file, "w", encoding='utf-8') as f:
            for path, checksum in sorted(checksums.items()):
                f.write(f"{checksum}  {path}\n")
        
        self.manifest["checksums"] = checksums
        self.manifest["size_mb"] = total_size / (1024**2)
        
        # Save manifest
        # FIX BUG-016: Use context manager for file operations
        manifest_file = self.temp_iso_root / "manifest.json"
        with open(manifest_file, "w", encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)
        
        print(f"✅ Generated checksums for {len(checksums)} files")
        print(f"📊 Total size: {total_size / (1024**3):.2f} GB")
    
    def calculate_checksum(self, file_path):
        """Calculate SHA256 checksum of a file with proper resource management"""
        sha256 = hashlib.sha256()
        
        # FIX BUG-016: Use context manager and chunked reading
        with open(file_path, "rb") as f:
            # Read in chunks to avoid memory issues with large files
            chunk_size = 8192  # 8KB chunks
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def build_iso(self):
        """Build the final ISO image"""
        self.iso_output_dir.mkdir(parents=True, exist_ok=True)
        iso_path = self.iso_output_dir / self.iso_filename
        
        if platform.system() == "Windows":
            # Use oscdimg.exe (Windows ADK)
            cmd = [
                "oscdimg.exe",
                "-m",  # Ignore maximum size limit
                "-o",  # Optimize storage
                "-u2",  # UDF file system
                "-udfver102",  # UDF version 1.02
                f"-l{self.iso_volume_id}",  # Volume label
                str(self.temp_iso_root),
                str(iso_path)
            ]
        else:
            # Use mkisofs/genisoimage
            mkisofs = shutil.which("mkisofs") or shutil.which("genisoimage")
            if not mkisofs:
                # Try hdiutil on macOS
                if platform.system() == "Darwin":
                    return self.build_iso_macos(iso_path)
                else:
                    raise RuntimeError("No ISO creation tool found (mkisofs/genisoimage)")
            
            cmd = [
                mkisofs,
                "-o", str(iso_path),
                "-V", self.iso_volume_id,
                "-J",  # Joliet extensions
                "-r",  # Rock Ridge extensions
                "-udf",  # UDF file system
                "-iso-level", "3",  # Allow large files
                "-allow-limited-size",  # Allow files larger than 4GB
                str(self.temp_iso_root)
            ]
        
        print(f"🔨 Building ISO: {iso_path.name}")
        print(f"📝 Command: {' '.join(cmd)}")
        
        # FIX BUG-016: Use subprocess with proper resource management
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ ISO build command completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ ISO creation failed: {e.stderr}")
            raise RuntimeError(f"ISO creation failed: {e.stderr}")
        except FileNotFoundError:
            print(f"❌ ISO creation tool not found: {cmd[0]}")
            raise RuntimeError(f"ISO creation tool not found: {cmd[0]}")
        
        return iso_path
    
    def build_iso_macos(self, iso_path):
        """Build ISO on macOS using hdiutil"""
        print(f"🍎 Using macOS hdiutil to create ISO...")
        
        # Create a temporary DMG first
        dmg_path = iso_path.with_suffix('.dmg')
        
        # Create hybrid image
        cmd = [
            "hdiutil", "create",
            "-volname", self.iso_volume_id,
            "-srcfolder", str(self.temp_iso_root),
            "-fs", "HFS+",
            "-format", "UDTO",  # DVD/CD master format
            str(dmg_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Convert to ISO
            cdr_path = dmg_path.with_suffix('.cdr')
            if cdr_path.exists():
                # Rename .cdr to .iso
                cdr_path.rename(iso_path)
                
                # Clean up DMG if it exists
                if dmg_path.exists() and dmg_path != cdr_path:
                    dmg_path.unlink()
                
                print(f"✅ ISO created using hdiutil")
                return iso_path
            else:
                raise RuntimeError("CDR file not created by hdiutil")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ hdiutil failed: {e.stderr}")
            raise RuntimeError(f"hdiutil failed: {e.stderr}")
    
    def verify_iso(self, iso_path):
        """Verify the created ISO"""
        if not iso_path.exists():
            return False
        
        # Check size
        size_gb = iso_path.stat().st_size / (1024**3)
        print(f"📏 ISO size: {size_gb:.2f} GB")
        
        if size_gb > self.iso_max_size_gb:
            print(f"⚠️ Warning: ISO exceeds target size of {self.iso_max_size_gb} GB")
        
        # Verify checksum
        iso_checksum = self.calculate_checksum(iso_path)
        print(f"🔐 ISO checksum: {iso_checksum}")
        
        # Try to mount and verify on Unix-like systems
        if platform.system() in ["Darwin", "Linux"]:
            mount_point = Path("/tmp/sunflower_iso_verify")
            mount_point.mkdir(exist_ok=True)
            
            try:
                if platform.system() == "Darwin":
                    # macOS mount
                    subprocess.run(["hdiutil", "attach", str(iso_path), "-mountpoint", str(mount_point)], 
                                 capture_output=True, check=True)
                else:
                    # Linux mount
                    subprocess.run(["sudo", "mount", "-o", "loop", str(iso_path), str(mount_point)], 
                                 capture_output=True, check=True)
                
                # Check for key files
                key_files = [
                    "sunflower_cd.id",
                    "manifest.json",
                    "checksums.sha256"
                ]
                
                verified = all((mount_point / f).exists() for f in key_files)
                
                # Unmount
                if platform.system() == "Darwin":
                    subprocess.run(["hdiutil", "detach", str(mount_point)], capture_output=True)
                else:
                    subprocess.run(["sudo", "umount", str(mount_point)], capture_output=True)
                
                mount_point.rmdir()
                
                return verified
                
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Could not mount ISO for verification: {e}")
                # If we can't mount, just check file exists and has reasonable size
                return iso_path.exists() and size_gb > 0.1
        
        # On Windows, just check that the file exists and has reasonable size
        return iso_path.exists() and size_gb > 0.1
    
    def save_build_record(self, iso_path):
        """Save build record for tracking with proper file handling"""
        records_dir = self.root_dir / "manufacturing" / "batch_records"
        records_dir.mkdir(parents=True, exist_ok=True)
        
        record = {
            "batch_id": self.batch_id,
            "version": self.version,
            "build_date": self.build_date,
            "iso_file": iso_path.name,
            "iso_size_gb": iso_path.stat().st_size / (1024**3),
            "iso_checksum": self.calculate_checksum(iso_path),
            "manifest": self.manifest,
            "build_machine": platform.node(),
            "build_system": f"{platform.system()} {platform.release()}"
        }
        
        # FIX BUG-016: Use context manager for file operations
        record_file = records_dir / f"batch_{self.batch_id}.json"
        with open(record_file, "w", encoding='utf-8') as f:
            json.dump(record, f, indent=2)
        
        print(f"✅ Build record saved: {record_file.name}")


def main():
    """Main entry point with proper resource management"""
    parser = argparse.ArgumentParser(description="Create Sunflower AI CD-ROM ISO")
    parser.add_argument("--version", default="1.0.0", help="Version number")
    parser.add_argument("--batch-id", help="Batch ID (auto-generated if not provided)")
    
    args = parser.parse_args()
    
    # FIX BUG-016: Use context manager to ensure cleanup
    try:
        with ISOCreator(version=args.version, batch_id=args.batch_id) as creator:
            iso_path = creator.create()
            success = bool(iso_path)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

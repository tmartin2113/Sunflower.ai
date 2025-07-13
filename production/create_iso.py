#!/usr/bin/env python3
"""
Create CD-ROM ISO for Sunflower AI Professional System
Builds a complete, production-ready ISO image containing all system files,
compiled applications, and pre-built AI models.

This script handles the entire CD-ROM partition creation process for manufacturing.
"""

import os
import sys
import json
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
import platform
import argparse
import zipfile
import secrets

class ISOCreator:
    def __init__(self, version="1.0.0", batch_id=None):
        self.root_dir = Path(__file__).parent.parent
        self.version = version
        self.batch_id = batch_id or self.generate_batch_id()
        self.build_date = datetime.now().strftime("%Y-%m-%d")
        
        # Paths
        self.staging_dir = self.root_dir / "cdrom_staging"
        self.iso_output_dir = self.root_dir / "manufacturing" / "iso_images"
        self.temp_iso_root = Path(tempfile.mkdtemp()) / "iso_root"
        
        # ISO configuration
        self.iso_filename = f"sunflower_ai_v{version}_{self.batch_id}.iso"
        self.iso_volume_id = f"SUNFLOWERAI_{version.replace('.', '')}"
        
        # Component tracking
        self.manifest = {
            "version": version,
            "batch_id": self.batch_id,
            "build_date": self.build_date,
            "platform": "universal",
            "components": {},
            "checksums": {},
            "size_mb": 0
        }
        
        # Security
        self.master_key = None
        self.security_tokens = {}
        
    def generate_batch_id(self):
        """Generate unique batch identifier"""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_id = secrets.token_hex(4).upper()
        return f"{timestamp}-{random_id}"
    
    def create(self):
        """Main ISO creation process"""
        print(f"🌻 Sunflower AI ISO Creator v{self.version}")
        print(f"📦 Batch ID: {self.batch_id}")
        print(f"📅 Build Date: {self.build_date}")
        print("-" * 60)
        
        try:
            # Pre-flight checks
            if not self.validate_prerequisites():
                return False
            
            # Create ISO structure
            print("\n📁 Creating ISO directory structure...")
            self.create_iso_structure()
            
            # Copy system files
            print("\n📄 Copying system files...")
            self.copy_system_files()
            
            # Add compiled applications
            print("\n🔨 Adding compiled applications...")
            self.add_compiled_applications()
            
            # Add AI models
            print("\n🤖 Adding AI models...")
            self.add_ai_models()
            
            # Add Ollama runtime
            print("\n🚀 Adding Ollama runtime...")
            self.add_ollama_runtime()
            
            # Generate security files
            print("\n🔒 Generating security components...")
            self.generate_security_files()
            
            # Create autorun configuration
            print("\n⚙️ Creating autorun configuration...")
            self.create_autorun_config()
            
            # Generate checksums
            print("\n🔍 Calculating checksums...")
            self.generate_checksums()
            
            # Create final ISO
            print("\n💿 Building ISO image...")
            iso_path = self.build_iso()
            
            # Verify ISO
            print("\n✅ Verifying ISO integrity...")
            if self.verify_iso(iso_path):
                print(f"\n✨ ISO created successfully: {iso_path}")
                print(f"📊 Size: {iso_path.stat().st_size / (1024**3):.2f} GB")
                self.save_build_record(iso_path)
                return True
            else:
                print("\n❌ ISO verification failed")
                return False
                
        except Exception as e:
            print(f"\n❌ ISO creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Cleanup
            if self.temp_iso_root.exists():
                shutil.rmtree(self.temp_iso_root, ignore_errors=True)
    
    def validate_prerequisites(self):
        """Validate all required components exist"""
        print("🔍 Validating prerequisites...")
        
        required_dirs = [
            self.staging_dir,
            self.staging_dir / "Windows",
            self.staging_dir / "macOS",
            self.staging_dir / "models"
        ]
        
        missing = []
        for dir_path in required_dirs:
            if not dir_path.exists():
                missing.append(str(dir_path))
        
        if missing:
            print("❌ Missing required directories:")
            for path in missing:
                print(f"   - {path}")
            print("\n📝 Run build scripts first:")
            print("   python build/compile_windows.py")
            print("   python build/compile_macos.py")
            print("   python build/create_models.py")
            return False
        
        # Check for ISO creation tools
        if platform.system() == "Windows":
            # Check for oscdimg.exe (Windows ADK tool)
            oscdimg = shutil.which("oscdimg.exe")
            if not oscdimg:
                print("❌ oscdimg.exe not found. Install Windows ADK.")
                return False
        else:
            # Check for mkisofs/genisoimage
            mkisofs = shutil.which("mkisofs") or shutil.which("genisoimage")
            if not mkisofs:
                print("❌ mkisofs/genisoimage not found. Install cdrtools.")
                return False
        
        print("✅ All prerequisites validated")
        return True
    
    def create_iso_structure(self):
        """Create ISO directory structure"""
        self.temp_iso_root.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        dirs = [
            "Windows",
            "macOS", 
            "models",
            "docs",
            "resources",
            ".security"
        ]
        
        for dir_name in dirs:
            (self.temp_iso_root / dir_name).mkdir(exist_ok=True)
        
        # Create marker file for CD-ROM detection
        marker_file = self.temp_iso_root / "sunflower_cd.id"
        marker_file.write_text(f"SUNFLOWER_AI_CDROM_{self.version}_{self.batch_id}")
        
        print(f"✅ Created ISO structure at: {self.temp_iso_root}")
    
    def copy_system_files(self):
        """Copy core system files"""
        # Copy launcher
        launcher_src = self.root_dir / "SUNFLOWER_LAUNCHER.py"
        if launcher_src.exists():
            shutil.copy2(launcher_src, self.temp_iso_root / "SUNFLOWER_LAUNCHER.py")
            self.manifest["components"]["launcher"] = "SUNFLOWER_LAUNCHER.py"
        
        # Copy platform launchers
        platform_src = self.root_dir / "platform_launchers"
        if platform_src.exists():
            shutil.copytree(
                platform_src,
                self.temp_iso_root / "platform_launchers",
                dirs_exist_ok=True
            )
        
        # Copy resources
        resources_src = self.root_dir / "resources"
        if resources_src.exists():
            shutil.copytree(
                resources_src,
                self.temp_iso_root / "resources",
                dirs_exist_ok=True
            )
        
        # Copy configuration files
        config_files = ["VERSION", "config/model_registry.json", "config/safety_patterns.json"]
        for config_file in config_files:
            src = self.root_dir / config_file
            if src.exists():
                dst = self.temp_iso_root / config_file
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        
        print(f"✅ Copied {len(self.manifest['components'])} system components")
    
    def add_compiled_applications(self):
        """Add platform-specific compiled applications"""
        copied = 0
        
        # Windows executable
        win_exe = self.staging_dir / "Windows" / "SunflowerAI.exe"
        if win_exe.exists():
            dst = self.temp_iso_root / "Windows" / "SunflowerAI.exe"
            shutil.copy2(win_exe, dst)
            self.manifest["components"]["windows_app"] = "Windows/SunflowerAI.exe"
            copied += 1
            
            # Copy Windows dependencies
            win_deps = self.staging_dir / "Windows" / "_internal"
            if win_deps.exists():
                shutil.copytree(
                    win_deps,
                    self.temp_iso_root / "Windows" / "_internal",
                    dirs_exist_ok=True
                )
        
        # macOS application
        mac_app = self.staging_dir / "macOS" / "SunflowerAI.app"
        if mac_app.exists():
            dst = self.temp_iso_root / "macOS" / "SunflowerAI.app"
            shutil.copytree(mac_app, dst, dirs_exist_ok=True)
            self.manifest["components"]["macos_app"] = "macOS/SunflowerAI.app"
            copied += 1
        
        print(f"✅ Added {copied} compiled applications")
    
    def add_ai_models(self):
        """Add pre-built AI models"""
        models_src = self.staging_dir / "models"
        models_dst = self.temp_iso_root / "models"
        
        if not models_src.exists():
            print("⚠️ No models found in staging directory")
            return
        
        model_count = 0
        total_size = 0
        
        # Copy all model files
        for model_file in models_src.glob("*"):
            if model_file.is_file():
                dst = models_dst / model_file.name
                shutil.copy2(model_file, dst)
                
                size = model_file.stat().st_size
                total_size += size
                model_count += 1
                
                # Add to manifest
                self.manifest["components"][f"model_{model_file.stem}"] = f"models/{model_file.name}"
        
        # Create model manifest
        model_manifest = {
            "version": self.version,
            "models": [],
            "total_size_gb": total_size / (1024**3)
        }
        
        for model_file in models_dst.glob("*"):
            if model_file.suffix != ".json":
                model_info = {
                    "name": model_file.stem,
                    "file": model_file.name,
                    "size_mb": model_file.stat().st_size / (1024**2),
                    "checksum": self.calculate_checksum(model_file)
                }
                model_manifest["models"].append(model_info)
        
        with open(models_dst / "model_manifest.json", "w") as f:
            json.dump(model_manifest, f, indent=2)
        
        print(f"✅ Added {model_count} AI models ({total_size / (1024**3):.2f} GB)")
    
    def add_ollama_runtime(self):
        """Add Ollama runtime for both platforms"""
        added = 0
        
        # Windows Ollama
        win_ollama = self.staging_dir / "Windows" / "ollama" / "ollama.exe"
        if win_ollama.exists():
            dst_dir = self.temp_iso_root / "Windows" / "ollama"
            dst_dir.mkdir(exist_ok=True)
            shutil.copy2(win_ollama, dst_dir / "ollama.exe")
            
            # Copy Ollama runtime files
            ollama_dir = win_ollama.parent
            for file in ollama_dir.glob("*"):
                if file.is_file():
                    shutil.copy2(file, dst_dir / file.name)
            
            self.manifest["components"]["ollama_windows"] = "Windows/ollama/ollama.exe"
            added += 1
        
        # macOS Ollama
        mac_ollama = self.staging_dir / "macOS" / "ollama-darwin"
        if mac_ollama.exists():
            dst = self.temp_iso_root / "macOS" / "ollama-darwin"
            shutil.copy2(mac_ollama, dst)
            # Make executable
            os.chmod(dst, 0o755)
            self.manifest["components"]["ollama_macos"] = "macOS/ollama-darwin"
            added += 1
        
        print(f"✅ Added Ollama runtime for {added} platform(s)")
    
    def generate_security_files(self):
        """Generate security and authentication files"""
        security_dir = self.temp_iso_root / ".security"
        
        # Generate master key
        self.master_key = secrets.token_bytes(32)
        
        # Create batch authentication token
        batch_token = {
            "batch_id": self.batch_id,
            "version": self.version,
            "created": datetime.now().isoformat(),
            "verification": secrets.token_urlsafe(32)
        }
        
        # Create fingerprint
        fingerprint = {
            "batch": self.batch_id,
            "build_date": self.build_date,
            "master_hash": hashlib.sha256(self.master_key).hexdigest(),
            "components": list(self.manifest["components"].keys())
        }
        
        # Save security files
        with open(security_dir / "batch_token.json", "w") as f:
            json.dump(batch_token, f, indent=2)
        
        with open(security_dir / "fingerprint.sig", "wb") as f:
            fingerprint_data = json.dumps(fingerprint).encode()
            f.write(fingerprint_data)
        
        # Create security manifest
        security_manifest = {
            "version": "1.0",
            "batch_id": self.batch_id,
            "security_level": "production",
            "features": {
                "cd_rom_verification": True,
                "usb_authentication": True,
                "model_encryption": False,  # Models are read-only
                "profile_encryption": True
            }
        }
        
        with open(security_dir / "security.manifest", "w") as f:
            json.dump(security_manifest, f, indent=2)
        
        print("✅ Generated security components")
    
    def create_autorun_config(self):
        """Create autorun configuration for Windows"""
        autorun_content = f"""[autorun]
open=Windows\\SunflowerAI.exe
icon=resources\\icons\\sunflower.ico
label=Sunflower AI v{self.version}

[Content]
BatchID={self.batch_id}
Version={self.version}
BuildDate={self.build_date}
"""
        
        with open(self.temp_iso_root / "autorun.inf", "w") as f:
            f.write(autorun_content)
        
        # Create desktop.ini for nice folder appearance
        desktop_ini = """[.ShellClassInfo]
IconResource=resources\\icons\\sunflower.ico,0
"""
        with open(self.temp_iso_root / "desktop.ini", "w") as f:
            f.write(desktop_ini)
        
        # Set hidden attribute on Windows
        if platform.system() == "Windows":
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(
                str(self.temp_iso_root / "desktop.ini"), 
                FILE_ATTRIBUTE_HIDDEN
            )
        
        print("✅ Created autorun configuration")
    
    def generate_checksums(self):
        """Generate checksums for all files"""
        checksums = {}
        total_size = 0
        
        for root, dirs, files in os.walk(self.temp_iso_root):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.temp_iso_root)
                
                # Calculate checksum
                checksum = self.calculate_checksum(file_path)
                checksums[str(relative_path)] = checksum
                
                # Track size
                total_size += file_path.stat().st_size
        
        # Save checksums
        checksum_file = self.temp_iso_root / "checksums.sha256"
        with open(checksum_file, "w") as f:
            for path, checksum in sorted(checksums.items()):
                f.write(f"{checksum}  {path}\n")
        
        self.manifest["checksums"] = checksums
        self.manifest["size_mb"] = total_size / (1024**2)
        
        # Save manifest
        with open(self.temp_iso_root / "manifest.json", "w") as f:
            json.dump(self.manifest, f, indent=2)
        
        print(f"✅ Generated checksums for {len(checksums)} files")
        print(f"📊 Total size: {total_size / (1024**3):.2f} GB")
    
    def calculate_checksum(self, file_path):
        """Calculate SHA256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
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
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ ISO creation failed: {result.stderr}")
            raise RuntimeError("ISO creation failed")
        
        return iso_path
    
    def verify_iso(self, iso_path):
        """Verify the created ISO"""
        if not iso_path.exists():
            return False
        
        # Check size
        size_gb = iso_path.stat().st_size / (1024**3)
        print(f"📏 ISO size: {size_gb:.2f} GB")
        
        if size_gb < 0.5:
            print("⚠️ ISO seems too small")
            return False
        
        if size_gb > 8.0:
            print("⚠️ ISO larger than typical USB size")
        
        # Mount and verify on supported platforms
        if platform.system() in ["Darwin", "Linux"]:
            # Try to mount and verify
            mount_point = Path(tempfile.mkdtemp())
            
            try:
                if platform.system() == "Darwin":
                    # macOS mount
                    subprocess.run(
                        ["hdiutil", "attach", str(iso_path), "-mountpoint", str(mount_point)],
                        check=True,
                        capture_output=True
                    )
                else:
                    # Linux mount
                    subprocess.run(
                        ["mount", "-o", "loop,ro", str(iso_path), str(mount_point)],
                        check=True,
                        capture_output=True
                    )
                
                # Verify key files exist
                marker = mount_point / "sunflower_cd.id"
                if marker.exists():
                    print("✅ ISO structure verified")
                    verified = True
                else:
                    print("❌ ISO structure invalid")
                    verified = False
                
            finally:
                # Unmount
                if platform.system() == "Darwin":
                    subprocess.run(["hdiutil", "detach", str(mount_point)], capture_output=True)
                else:
                    subprocess.run(["umount", str(mount_point)], capture_output=True)
                mount_point.rmdir()
            
            return verified
        
        # On Windows, just check that the file exists and has reasonable size
        return True
    
    def save_build_record(self, iso_path):
        """Save build record for tracking"""
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
        
        record_file = records_dir / f"batch_{self.batch_id}.json"
        with open(record_file, "w") as f:
            json.dump(record, f, indent=2)
        
        print(f"✅ Build record saved: {record_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Create Sunflower AI CD-ROM ISO")
    parser.add_argument("--version", default="1.0.0", help="Version number")
    parser.add_argument("--batch-id", help="Batch ID (auto-generated if not provided)")
    
    args = parser.parse_args()
    
    creator = ISOCreator(version=args.version, batch_id=args.batch_id)
    success = creator.create()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

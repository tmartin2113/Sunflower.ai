#!/usr/bin/env python3
"""
Master Build Script for Sunflower AI Professional System
Orchestrates the complete build process from source to production-ready USB images.

This script automates:
1. Code compilation for all platforms
2. AI model creation
3. Security component generation
4. ISO and USB image creation
5. Production package assembly
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
import time
from pathlib import Path
from datetime import datetime
import platform
import hashlib


class MasterBuilder:
    def __init__(self, version="1.0.0", skip_steps=None):
        self.root_dir = Path(__file__).parent.parent
        self.version = version
        self.skip_steps = skip_steps or []
        self.start_time = datetime.now()
        
        # Build configuration
        self.build_config = {
            "version": version,
            "build_date": self.start_time.isoformat(),
            "platform": platform.system(),
            "python_version": sys.version,
            "steps_completed": [],
            "errors": [],
            "warnings": []
        }
        
        # Paths
        self.build_dir = self.root_dir / "build"
        self.production_dir = self.root_dir / "production"
        self.staging_dir = self.root_dir / "cdrom_staging"
        self.output_dir = self.root_dir / "output"
        
        # Build steps
        self.build_steps = [
            ("validate", "Validate prerequisites", self.validate_prerequisites),
            ("clean", "Clean previous builds", self.clean_build),
            ("compile_windows", "Compile Windows application", self.compile_windows),
            ("compile_macos", "Compile macOS application", self.compile_macos),
            ("create_models", "Create AI models", self.create_models),
            ("generate_security", "Generate security components", self.generate_security),
            ("create_iso", "Create CD-ROM ISO", self.create_iso),
            ("prepare_usb", "Prepare USB partition", self.prepare_usb),
            ("create_batch", "Create production batch", self.create_batch),
            ("validate_output", "Validate build output", self.validate_output)
        ]
    
    def log(self, message, level="info"):
        """Log build messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            print(f"[{timestamp}] ❌ ERROR: {message}")
            self.build_config["errors"].append(message)
        elif level == "warning":
            print(f"[{timestamp}] ⚠️  WARNING: {message}")
            self.build_config["warnings"].append(message)
        elif level == "success":
            print(f"[{timestamp}] ✅ {message}")
        else:
            print(f"[{timestamp}] ℹ️  {message}")
    
    def run_command(self, cmd, cwd=None, env=None, capture=True):
        """Run a command and capture output"""
        if isinstance(cmd, str):
            cmd = cmd.split()
        
        self.log(f"Running: {' '.join(cmd)}")
        
        try:
            if capture:
                result = subprocess.run(
                    cmd,
                    cwd=cwd or self.root_dir,
                    env=env or os.environ.copy(),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    self.log(f"Command failed: {result.stderr}", "error")
                    return False, result.stderr
                
                return True, result.stdout
            else:
                # Stream output in real-time
                result = subprocess.run(
                    cmd,
                    cwd=cwd or self.root_dir,
                    env=env or os.environ.copy()
                )
                
                return result.returncode == 0, ""
                
        except Exception as e:
            self.log(f"Command exception: {e}", "error")
            return False, str(e)
    
    def build(self):
        """Execute complete build process"""
        print("=" * 80)
        print(f"🌻 SUNFLOWER AI MASTER BUILD SYSTEM v{self.version}")
        print(f"📅 Build Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖥️  Platform: {platform.system()} {platform.release()}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print("=" * 80)
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Execute build steps
        total_steps = len([s for s in self.build_steps if s[0] not in self.skip_steps])
        current_step = 0
        
        for step_id, step_name, step_func in self.build_steps:
            if step_id in self.skip_steps:
                self.log(f"Skipping: {step_name}")
                continue
            
            current_step += 1
            print(f"\n[{current_step}/{total_steps}] {step_name}")
            print("-" * 60)
            
            try:
                success = step_func()
                
                if success:
                    self.build_config["steps_completed"].append(step_id)
                    self.log(f"Completed: {step_name}", "success")
                else:
                    self.log(f"Failed: {step_name}", "error")
                    
                    if not self.should_continue():
                        break
                        
            except Exception as e:
                self.log(f"Exception in {step_name}: {e}", "error")
                import traceback
                traceback.print_exc()
                
                if not self.should_continue():
                    break
        
        # Generate build report
        self.generate_build_report()
        
        # Final summary
        self.display_summary()
        
        return len(self.build_config["errors"]) == 0
    
    def should_continue(self):
        """Ask whether to continue after error"""
        response = input("\n🤔 Continue build despite error? (y/N): ")
        return response.lower() == 'y'
    
    def validate_prerequisites(self):
        """Validate all prerequisites are met"""
        self.log("Validating prerequisites...")
        
        checks = {
            "Python version": sys.version_info >= (3, 8),
            "Git installed": shutil.which("git") is not None,
            "Source files": (self.root_dir / "src").exists(),
            "Modelfiles": (self.root_dir / "modelfiles").exists(),
            "Resources": (self.root_dir / "resources").exists()
        }
        
        # Platform-specific checks
        if platform.system() == "Windows":
            checks["PyInstaller"] = shutil.which("pyinstaller") is not None
            checks["Windows SDK"] = shutil.which("oscdimg.exe") is not None
        else:
            checks["PyInstaller"] = shutil.which("pyinstaller") is not None
            checks["mkisofs"] = shutil.which("mkisofs") or shutil.which("genisoimage")
        
        # Check Ollama
        checks["Ollama"] = shutil.which("ollama") is not None
        
        all_passed = True
        for check, passed in checks.items():
            if passed:
                self.log(f"✓ {check}")
            else:
                self.log(f"✗ {check}", "error")
                all_passed = False
        
        # Check dependencies
        self.log("Checking Python dependencies...")
        success, output = self.run_command([
            sys.executable, "-m", "pip", "check"
        ])
        
        if not success:
            self.log("Missing dependencies - run: pip install -r requirements.txt", "error")
            all_passed = False
        
        return all_passed
    
    def clean_build(self):
        """Clean previous build artifacts"""
        self.log("Cleaning previous builds...")
        
        dirs_to_clean = [
            self.staging_dir,
            self.output_dir,
            self.root_dir / "dist",
            self.root_dir / "build" / "compile_windows.build",
            self.root_dir / "build" / "compile_macos.build"
        ]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                self.log(f"Removing: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)
        
        # Clean temporary files
        patterns = ["*.pyc", "__pycache__", ".DS_Store", "*.spec"]
        for pattern in patterns:
            for file in self.root_dir.rglob(pattern):
                file.unlink()
        
        return True
    
    def compile_windows(self):
        """Compile Windows application"""
        if platform.system() != "Windows":
            self.log("Skipping Windows compilation on non-Windows platform", "warning")
            return True
        
        self.log("Compiling Windows application...")
        
        script = self.build_dir / "compile_windows.py"
        if not script.exists():
            self.log(f"Windows build script not found: {script}", "error")
            return False
        
        success, output = self.run_command(
            [sys.executable, str(script)],
            capture=False
        )
        
        # Verify output
        exe_path = self.staging_dir / "Windows" / "SunflowerAI.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024**2)
            self.log(f"Windows executable created: {size_mb:.1f} MB")
            return True
        else:
            self.log("Windows executable not found after compilation", "error")
            return False
    
    def compile_macos(self):
        """Compile macOS application"""
        if platform.system() != "Darwin":
            self.log("Skipping macOS compilation on non-macOS platform", "warning")
            return True
        
        self.log("Compiling macOS application...")
        
        script = self.build_dir / "compile_macos.py"
        if not script.exists():
            self.log(f"macOS build script not found: {script}", "error")
            return False
        
        success, output = self.run_command(
            [sys.executable, str(script)],
            capture=False
        )
        
        # Verify output
        app_path = self.staging_dir / "macOS" / "SunflowerAI.app"
        if app_path.exists():
            self.log("macOS application bundle created")
            return True
        else:
            self.log("macOS application not found after compilation", "error")
            return False
    
    def create_models(self):
        """Create AI models"""
        self.log("Creating AI models...")
        
        script = self.build_dir / "create_models.py"
        if not script.exists():
            self.log(f"Model creation script not found: {script}", "error")
            return False
        
        # Check if Ollama is running
        success, output = self.run_command(["ollama", "list"])
        if not success:
            self.log("Starting Ollama service...")
            subprocess.Popen(["ollama", "serve"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            time.sleep(5)  # Wait for service to start
        
        success, output = self.run_command(
            [sys.executable, str(script)],
            capture=False
        )
        
        # Verify models created
        models_dir = self.staging_dir / "models"
        if models_dir.exists():
            model_files = list(models_dir.glob("*"))
            total_size = sum(f.stat().st_size for f in model_files if f.is_file())
            self.log(f"Created {len(model_files)} model files, total size: {total_size / (1024**3):.2f} GB")
            return True
        else:
            self.log("Models directory not found after creation", "error")
            return False
    
    def generate_security(self):
        """Generate security components"""
        self.log("Generating security components...")
        
        security_dir = self.staging_dir / ".security"
        security_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate batch authentication
        batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d')}-BUILD"
        
        security_manifest = {
            "version": self.version,
            "batch_id": batch_id,
            "build_date": datetime.now().isoformat(),
            "platform": platform.system(),
            "security_features": {
                "cdrom_verification": True,
                "usb_authentication": True,
                "profile_encryption": True
            }
        }
        
        manifest_path = security_dir / "security.manifest"
        with open(manifest_path, 'w') as f:
            json.dump(security_manifest, f, indent=2)
        
        # Generate fingerprint
        fingerprint = hashlib.sha256(
            f"{batch_id}{self.version}{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        fingerprint_path = security_dir / "fingerprint.sig"
        fingerprint_path.write_text(fingerprint)
        
        self.log("Security components generated")
        return True
    
    def create_iso(self):
        """Create CD-ROM ISO"""
        self.log("Creating CD-ROM ISO...")
        
        script = self.production_dir / "create_iso.py"
        if not script.exists():
            self.log(f"ISO creation script not found: {script}", "error")
            return False
        
        success, output = self.run_command(
            [sys.executable, str(script), "--version", self.version],
            capture=False
        )
        
        # Find created ISO
        iso_dir = self.root_dir / "manufacturing" / "iso_images"
        if iso_dir.exists():
            iso_files = list(iso_dir.glob("*.iso"))
            if iso_files:
                latest_iso = max(iso_files, key=lambda p: p.stat().st_mtime)
                size_gb = latest_iso.stat().st_size / (1024**3)
                self.log(f"ISO created: {latest_iso.name} ({size_gb:.2f} GB)")
                
                # Copy to output
                shutil.copy2(latest_iso, self.output_dir / latest_iso.name)
                return True
        
        self.log("ISO file not found after creation", "error")
        return False
    
    def prepare_usb(self):
        """Prepare USB partition"""
        self.log("Preparing USB partition...")
        
        script = self.production_dir / "prepare_usb_partition.py"
        if not script.exists():
            self.log(f"USB preparation script not found: {script}", "error")
            return False
        
        success, output = self.run_command(
            [sys.executable, str(script), "--format", "image"],
            capture=False
        )
        
        # Find created image
        usb_dir = self.root_dir / "manufacturing" / "usb_images"
        if usb_dir.exists():
            img_files = list(usb_dir.glob("*.img"))
            zip_files = list(usb_dir.glob("*.zip"))
            
            if img_files or zip_files:
                self.log("USB partition image created")
                
                # Copy to output
                for f in img_files + zip_files:
                    shutil.copy2(f, self.output_dir / f.name)
                
                return True
        
        self.log("USB image not found after creation", "error")
        return False
    
    def create_batch(self):
        """Create production batch"""
        self.log("Creating production batch...")
        
        script = self.production_dir / "batch_generator.py"
        if not script.exists():
            self.log(f"Batch generator script not found: {script}", "error")
            return False
        
        success, output = self.run_command(
            [sys.executable, str(script), "--size", "10", "--version", self.version],
            capture=False
        )
        
        return success
    
    def validate_output(self):
        """Validate build output"""
        self.log("Validating build output...")
        
        required_files = {
            "ISO file": list(self.output_dir.glob("*.iso")),
            "USB image": list(self.output_dir.glob("*.img")) + list(self.output_dir.glob("*.zip")),
        }
        
        all_found = True
        for file_type, files in required_files.items():
            if files:
                self.log(f"✓ {file_type}: {files[0].name}")
            else:
                self.log(f"✗ {file_type}: Not found", "error")
                all_found = False
        
        # Check file sizes
        total_size = sum(f.stat().st_size for f in self.output_dir.glob("*") if f.is_file())
        self.log(f"Total output size: {total_size / (1024**3):.2f} GB")
        
        return all_found
    
    def generate_build_report(self):
        """Generate comprehensive build report"""
        duration = datetime.now() - self.start_time
        
        self.build_config["duration"] = str(duration)
        self.build_config["completed"] = datetime.now().isoformat()
        
        # List output files
        output_files = []
        for file in self.output_dir.glob("*"):
            if file.is_file():
                output_files.append({
                    "name": file.name,
                    "size_mb": file.stat().st_size / (1024**2),
                    "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
        
        self.build_config["output_files"] = output_files
        
        # Save report
        report_path = self.output_dir / f"build_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.build_config, f, indent=2)
        
        self.log(f"Build report saved: {report_path.name}")
    
    def display_summary(self):
        """Display build summary"""
        print("\n" + "=" * 80)
        print("BUILD SUMMARY")
        print("=" * 80)
        
        # Status
        if self.build_config["errors"]:
            print(f"Status: ❌ FAILED ({len(self.build_config['errors'])} errors)")
        else:
            print("Status: ✅ SUCCESS")
        
        # Duration
        print(f"Duration: {self.build_config.get('duration', 'unknown')}")
        
        # Steps completed
        print(f"Steps completed: {len(self.build_config['steps_completed'])}/{len(self.build_steps)}")
        
        # Output files
        if self.build_config.get("output_files"):
            print("\nOutput Files:")
            for file in self.build_config["output_files"]:
                print(f"  • {file['name']} ({file['size_mb']:.1f} MB)")
        
        # Errors
        if self.build_config["errors"]:
            print(f"\nErrors ({len(self.build_config['errors'])}):")
            for error in self.build_config["errors"][:5]:  # Show first 5
                print(f"  ✗ {error}")
        
        # Warnings
        if self.build_config["warnings"]:
            print(f"\nWarnings ({len(self.build_config['warnings'])}):")
            for warning in self.build_config["warnings"][:5]:  # Show first 5
                print(f"  ⚠️ {warning}")
        
        print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Master build script for Sunflower AI"
    )
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="Version to build"
    )
    parser.add_argument(
        "--skip",
        nargs='+',
        help="Steps to skip (e.g., --skip compile_windows compile_macos)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick build (skip models and batch generation)"
    )
    
    args = parser.parse_args()
    
    skip_steps = args.skip or []
    if args.quick:
        skip_steps.extend(["create_models", "create_batch"])
    
    builder = MasterBuilder(
        version=args.version,
        skip_steps=skip_steps
    )
    
    success = builder.build()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Sign executables for Windows and macOS to prevent security warnings.
Handles code signing certificates and notarization.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

class ExecutableSigner:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.staging_dir = self.root_dir / "cdrom_staging"
        
        # Platform detection
        self.platform = sys.platform
        
        # Certificate configuration
        self.config = self.load_signing_config()
        
    def load_signing_config(self):
        """Load signing configuration from environment or config file"""
        config_path = self.root_dir / "signing_config.json"
        
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)
        else:
            # Use environment variables
            return {
                "windows": {
                    "certificate_path": os.environ.get("WINDOWS_CERT_PATH"),
                    "certificate_password": os.environ.get("WINDOWS_CERT_PASSWORD"),
                    "timestamp_url": "http://timestamp.digicert.com"
                },
                "macos": {
                    "developer_id": os.environ.get("MACOS_DEVELOPER_ID"),
                    "apple_id": os.environ.get("APPLE_ID"),
                    "app_password": os.environ.get("APPLE_APP_PASSWORD"),
                    "team_id": os.environ.get("APPLE_TEAM_ID")
                }
            }
    
    def sign_windows_executable(self):
        """Sign Windows executable with certificate"""
        print("🖊️ Signing Windows executable...")
        
        exe_path = self.staging_dir / "Windows" / "SunflowerAI.exe"
        
        if not exe_path.exists():
            print("⚠️ Windows executable not found, skipping signing")
            return False
            
        cert_path = self.config["windows"]["certificate_path"]
        cert_password = self.config["windows"]["certificate_password"]
        
        if not cert_path or not Path(cert_path).exists():
            print("⚠️ Windows certificate not found, skipping signing")
            return False
        
        # Find signtool.exe
        signtool = self.find_signtool()
        if not signtool:
            print("⚠️ signtool.exe not found, skipping signing")
            return False
        
        # Sign the executable
        cmd = [
            str(signtool),
            "sign",
            "/f", cert_path,
            "/p", cert_password,
            "/t", self.config["windows"]["timestamp_url"],
            "/d", "Sunflower AI Education System",
            "/du", "https://sunflowerai.com",
            "/v",
            str(exe_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Windows executable signed successfully")
            
            # Verify signature
            verify_cmd = [str(signtool), "verify", "/pa", str(exe_path)]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
            
            if verify_result.returncode == 0:
                print("✅ Signature verified")
                return True
            else:
                print("⚠️ Signature verification failed")
                return False
        else:
            print(f"❌ Signing failed: {result.stderr}")
            return False
    
    def find_signtool(self):
        """Find signtool.exe on Windows"""
        # Common locations
        locations = [
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
            r"C:\Program Files\Microsoft SDKs\Windows\v10.0A\bin\NETFX 4.8 Tools\x64\signtool.exe"
        ]
        
        for loc in locations:
            if Path(loc).exists():
                return Path(loc)
                
        # Try to find via PATH
        signtool = shutil.which("signtool")
        if signtool:
            return Path(signtool)
            
        return None
    
    def sign_macos_app(self):
        """Sign macOS application bundle"""
        print("🖊️ Signing macOS application...")
        
        app_path = self.staging_dir / "macOS" / "SunflowerAI.app"
        
        if not app_path.exists():
            print("⚠️ macOS app bundle not found, skipping signing")
            return False
            
        developer_id = self.config["macos"]["developer_id"]
        
        if not developer_id:
            print("⚠️ Developer ID not configured, skipping signing")
            return False
        
        # Deep sign the app bundle
        cmd = [
            "codesign",
            "--deep",
            "--force",
            "--verify",
            "--verbose",
            "--sign", developer_id,
            "--options", "runtime",
            "--entitlements", str(self.root_dir / "platform_launchers" / "macos" / "entitlements.plist"),
            str(app_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ macOS app signed successfully")
            
            # Verify signature
            verify_cmd = ["codesign", "-vvv", "--deep", "--strict", str(app_path)]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
            
            if verify_result.returncode == 0:
                print("✅ Signature verified")
                
                # Notarize if credentials available
                if self.config["macos"]["apple_id"]:
                    return self.notarize_macos_app(app_path)
                else:
                    print("⚠️ Apple ID not configured, skipping notarization")
                    return True
            else:
                print("⚠️ Signature verification failed")
                return False
        else:
            print(f"❌ Signing failed: {result.stderr}")
            return False
    
    def notarize_macos_app(self, app_path):
        """Notarize macOS app with Apple"""
        print("📝 Notarizing macOS app...")
        
        # Create ZIP for notarization
        zip_path = app_path.parent / "SunflowerAI.zip"
        
        cmd = ["ditto", "-c", "-k", "--keepParent", str(app_path), str(zip_path)]
        subprocess.run(cmd, check=True)
        
        # Submit for notarization
        notarize_cmd = [
            "xcrun", "altool",
            "--notarize-app",
            "--primary-bundle-id", "com.sunflowerai.education",
            "--username", self.config["macos"]["apple_id"],
            "--password", self.config["macos"]["app_password"],
            "--team-id", self.config["macos"]["team_id"],
            "--file", str(zip_path),
            "--output-format", "json"
        ]
        
        result = subprocess.run(notarize_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            request_uuid = response.get("RequestUUID")
            
            if request_uuid:
                print(f"✅ Notarization submitted: {request_uuid}")
                print("⏳ Waiting for notarization (this may take several minutes)...")
                
                # Wait for notarization
                if self.wait_for_notarization(request_uuid):
                    # Staple the ticket
                    staple_cmd = ["xcrun", "stapler", "staple", str(app_path)]
                    staple_result = subprocess.run(staple_cmd, capture_output=True, text=True)
                    
                    if staple_result.returncode == 0:
                        print("✅ Notarization ticket stapled")
                        return True
                    else:
                        print("⚠️ Failed to staple ticket")
                        return False
                else:
                    return False
        else:
            print(f"❌ Notarization submission failed: {result.stderr}")
            return False
    
    def wait_for_notarization(self, request_uuid):
        """Wait for notarization to complete"""
        import time
        
        for i in range(60):  # Wait up to 30 minutes
            time.sleep(30)  # Check every 30 seconds
            
            check_cmd = [
                "xcrun", "altool",
                "--notarization-info", request_uuid,
                "--username", self.config["macos"]["apple_id"],
                "--password", self.config["macos"]["app_password"],
                "--output-format", "json"
            ]
            
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                status = response.get("Status")
                
                if status == "success":
                    print("✅ Notarization successful")
                    return True
                elif status == "invalid":
                    print("❌ Notarization failed")
                    print(response.get("LogFileURL", "No log URL"))
                    return False
                else:
                    print(f"⏳ Status: {status}")
        
        print("❌ Notarization timeout")
        return False
    
    def build(self):
        """Execute signing process"""
        print(f"🌻 Sunflower AI Executable Signing System")
        print(f"📅 Signing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        results = {
            "signing_date": datetime.now().isoformat(),
            "windows": {"signed": False},
            "macos": {"signed": False}
        }
        
        try:
            # Sign Windows executable
            if (self.staging_dir / "Windows" / "SunflowerAI.exe").exists():
                results["windows"]["signed"] = self.sign_windows_executable()
            
            # Sign macOS app
            if (self.staging_dir / "macOS" / "SunflowerAI.app").exists():
                results["macos"]["signed"] = self.sign_macos_app()
            
            print("\n📊 Signing Summary:")
            print(f"  Windows: {'✅ Signed' if results['windows']['signed'] else '⚠️ Not signed'}")
            print(f"  macOS: {'✅ Signed' if results['macos']['signed'] else '⚠️ Not signed'}")
            
            # Save signing record
            records_dir = self.root_dir / "manufacturing" / "batch_records"
            records_dir.mkdir(parents=True, exist_ok=True)
            
            with open(records_dir / f"signing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"\n❌ Signing process failed: {e}")
            raise


if __name__ == "__main__":
    signer = ExecutableSigner()
    signer.build()

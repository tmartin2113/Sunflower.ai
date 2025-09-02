#!/usr/bin/env python3
"""
Sunflower AI Professional System - Installation Package Creator
Creates platform-specific installation packages for Windows and macOS
Version: 6.2 | Platform: Windows/macOS | Architecture: Installer Builder
"""

import os
import sys
import json
import shutil
import hashlib
import platform
import subprocess
import tempfile
import zipfile
import tarfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import base64
import struct

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('package_creation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SunflowerPackageCreator')


class PackageType(Enum):
    """Supported package types"""
    MSI = "msi"          # Windows Installer
    NSIS = "nsis"        # NSIS Installer for Windows
    DMG = "dmg"          # macOS Disk Image
    PKG = "pkg"          # macOS Package
    UNIVERSAL = "universal"  # Cross-platform archive


class BuildStatus(Enum):
    """Build status codes"""
    INITIALIZED = "initialized"
    COLLECTING = "collecting"
    BUILDING = "building"
    SIGNING = "signing"
    PACKAGING = "packaging"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class InstallerConfiguration:
    """Configuration for installer package creation"""
    package_type: PackageType
    app_name: str = "Sunflower AI Professional"
    app_version: str = "6.2.0"
    app_publisher: str = "Sunflower AI Systems"
    app_url: str = "https://sunflowerai.education"
    install_dir: str = ""
    output_dir: str = "./dist"
    sign_package: bool = False
    certificate_path: str = ""
    certificate_password: str = ""
    include_models: List[str] = field(default_factory=lambda: [
        "llama3.2:7b", "llama3.2:3b", "llama3.2:1b", "llama3.2:1b-q4_0"
    ])
    hardware_requirements: Dict[str, Any] = field(default_factory=lambda: {
        "min_ram_gb": 4,
        "min_disk_gb": 8,
        "min_os_version": {"windows": "10", "macos": "10.15"}
    })
    
    def __post_init__(self):
        if not self.install_dir:
            if platform.system() == "Windows":
                self.install_dir = f"C:\\Program Files\\{self.app_name}"
            else:
                self.install_dir = f"/Applications/{self.app_name}.app"


class PackageBuilder:
    """Base class for package builders"""
    
    def __init__(self, config: InstallerConfiguration):
        self.config = config
        self.status = BuildStatus.INITIALIZED
        self.build_dir = Path(tempfile.mkdtemp(prefix="sunflower_build_"))
        self.source_dir = Path("../src")
        self.assets_dir = Path("../assets")
        self.output_path: Optional[Path] = None
        self.file_manifest: Dict[str, str] = {}
        self.errors: List[str] = []
        
    def build(self) -> bool:
        """Main build process"""
        try:
            logger.info(f"Starting {self.config.package_type.value} package build")
            
            self.status = BuildStatus.COLLECTING
            if not self._collect_files():
                return False
            
            self.status = BuildStatus.BUILDING
            if not self._create_package():
                return False
            
            if self.config.sign_package:
                self.status = BuildStatus.SIGNING
                if not self._sign_package():
                    logger.warning("Package signing failed, continuing unsigned")
            
            self.status = BuildStatus.VERIFYING
            if not self._verify_package():
                return False
            
            self.status = BuildStatus.COMPLETE
            logger.info(f"Package created successfully: {self.output_path}")
            return True
            
        except Exception as e:
            self.status = BuildStatus.ERROR
            self.errors.append(str(e))
            logger.error(f"Package build failed: {e}", exc_info=True)
            return False
        finally:
            self._cleanup()
    
    def _collect_files(self) -> bool:
        """Collect all files needed for the package"""
        try:
            logger.info("Collecting files for package")
            
            # Define file structure
            files_to_collect = {
                "executables": {
                    "windows": ["launcher.exe", "ollama.exe", "sunflower_service.exe"],
                    "macos": ["launcher.app", "ollama", "sunflower_service"],
                    "universal": ["launcher.py", "ollama_installer.py"]
                },
                "models": {
                    "all": self.config.include_models
                },
                "modelfiles": {
                    "all": ["Sunflower_AI_Kids.modelfile", "Sunflower_AI_Educator.modelfile"]
                },
                "interface": {
                    "all": ["gui.py", "cli.py", "web_interface.py", "parent_dashboard.py"]
                },
                "libraries": {
                    "all": ["requirements.txt", "vendor/"]
                },
                "documentation": {
                    "all": ["user_guide.pdf", "quick_start.pdf", "troubleshooting.pdf"]
                },
                "assets": {
                    "all": ["icon.ico", "icon.icns", "splash.png", "sounds/"]
                },
                "config": {
                    "all": ["default_config.json", "hardware_profiles.json"]
                }
            }
            
            platform_key = platform.system().lower()
            if platform_key == "darwin":
                platform_key = "macos"
            
            for category, items in files_to_collect.items():
                category_dir = self.build_dir / category
                category_dir.mkdir(parents=True, exist_ok=True)
                
                # Get platform-specific or universal files
                file_list = items.get(platform_key, items.get("all", []))
                
                for item in file_list:
                    source_path = self.source_dir / category / item
                    dest_path = category_dir / item
                    
                    if source_path.exists():
                        if source_path.is_dir():
                            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                        else:
                            shutil.copy2(source_path, dest_path)
                        
                        # Calculate checksum for manifest
                        if dest_path.is_file():
                            checksum = self._calculate_checksum(dest_path)
                            rel_path = dest_path.relative_to(self.build_dir)
                            self.file_manifest[str(rel_path)] = checksum
                    else:
                        logger.warning(f"Source not found: {source_path}")
            
            # Create version info file
            self._create_version_info()
            
            return True
            
        except Exception as e:
            self.errors.append(f"File collection failed: {e}")
            return False
    
    def _create_version_info(self) -> None:
        """Create version information file"""
        version_info = {
            "product_name": self.config.app_name,
            "version": self.config.app_version,
            "build_date": datetime.now().isoformat(),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": sys.version,
            "models_included": self.config.include_models,
            "hardware_requirements": self.config.hardware_requirements,
            "file_manifest": self.file_manifest
        }
        
        version_file = self.build_dir / "version_info.json"
        with open(version_file, 'w') as f:
            json.dump(version_info, f, indent=2)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _create_package(self) -> bool:
        """Create the actual package (to be overridden by subclasses)"""
        raise NotImplementedError("Subclasses must implement _create_package")
    
    def _sign_package(self) -> bool:
        """Sign the package (to be overridden by subclasses)"""
        return True
    
    def _verify_package(self) -> bool:
        """Verify the created package"""
        if not self.output_path or not self.output_path.exists():
            self.errors.append("Package file not found")
            return False
        
        # Check file size
        size_mb = self.output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Package size: {size_mb:.2f} MB")
        
        if size_mb < 100:
            logger.warning("Package seems unusually small")
        
        return True
    
    def _cleanup(self) -> None:
        """Clean up temporary files"""
        try:
            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


class WindowsMSIBuilder(PackageBuilder):
    """Windows MSI package builder"""
    
    def _create_package(self) -> bool:
        """Create Windows MSI package using WiX or msitools"""
        try:
            logger.info("Creating Windows MSI package")
            
            # Generate WiX source file
            wxs_content = self._generate_wix_source()
            wxs_file = self.build_dir / "sunflower.wxs"
            wxs_file.write_text(wxs_content)
            
            # Check if WiX is available
            if self._is_wix_available():
                return self._build_with_wix(wxs_file)
            else:
                logger.warning("WiX not found, using alternative MSI creation")
                return self._build_with_msitools()
                
        except Exception as e:
            self.errors.append(f"MSI creation failed: {e}")
            return False
    
    def _generate_wix_source(self) -> str:
        """Generate WiX source XML"""
        # Generate unique GUIDs
        import uuid
        product_guid = str(uuid.uuid4()).upper()
        upgrade_guid = str(uuid.uuid4()).upper()
        
        wxs_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
    <Product Id="{product_guid}" 
             Name="{self.config.app_name}" 
             Language="1033" 
             Version="{self.config.app_version}"
             Manufacturer="{self.config.app_publisher}" 
             UpgradeCode="{upgrade_guid}">
        
        <Package InstallerVersion="200" 
                 Compressed="yes" 
                 InstallScope="perMachine"
                 Description="{self.config.app_name} Installer"
                 Comments="Family-focused K-12 STEM Education System" />
        
        <MajorUpgrade DowngradeErrorMessage="A newer version is already installed." />
        <MediaTemplate EmbedCab="yes" />
        
        <Feature Id="ProductFeature" Title="{self.config.app_name}" Level="1">
            <ComponentGroupRef Id="ProductComponents" />
            <ComponentGroupRef Id="ModelComponents" />
            <ComponentGroupRef Id="DocumentationComponents" />
        </Feature>
        
        <!-- Installation Directory -->
        <Directory Id="TARGETDIR" Name="SourceDir">
            <Directory Id="ProgramFiles64Folder">
                <Directory Id="INSTALLFOLDER" Name="{self.config.app_name}">
                    <Directory Id="ModelsFolder" Name="models" />
                    <Directory Id="DocsFolder" Name="documentation" />
                </Directory>
            </Directory>
            
            <!-- Start Menu -->
            <Directory Id="ProgramMenuFolder">
                <Directory Id="ApplicationProgramsFolder" Name="{self.config.app_name}" />
            </Directory>
            
            <!-- Desktop -->
            <Directory Id="DesktopFolder" Name="Desktop" />
        </Directory>
        
        <!-- Components -->
        <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
            <Component Id="MainExecutable" Guid="{{GENERATED}}">
                <File Id="LauncherExe" Source="executables\\launcher.exe" KeyPath="yes">
                    <Shortcut Id="StartMenuShortcut"
                              Directory="ApplicationProgramsFolder"
                              Name="{self.config.app_name}"
                              WorkingDirectory="INSTALLFOLDER"
                              Icon="AppIcon.ico"
                              Advertise="yes" />
                    <Shortcut Id="DesktopShortcut"
                              Directory="DesktopFolder"
                              Name="{self.config.app_name}"
                              WorkingDirectory="INSTALLFOLDER"
                              Icon="AppIcon.ico"
                              Advertise="yes" />
                </File>
            </Component>
            
            <Component Id="OllamaExecutable" Guid="{{GENERATED}}">
                <File Id="OllamaExe" Source="executables\\ollama.exe" KeyPath="yes" />
            </Component>
            
            <Component Id="ServiceExecutable" Guid="{{GENERATED}}">
                <File Id="ServiceExe" Source="executables\\sunflower_service.exe" KeyPath="yes" />
                <ServiceInstall Id="SunflowerService"
                                Name="SunflowerAI"
                                DisplayName="Sunflower AI Service"
                                Type="ownProcess"
                                Start="auto"
                                ErrorControl="normal"
                                Description="Sunflower AI Background Service" />
                <ServiceControl Id="StartService"
                                Start="install"
                                Stop="both"
                                Remove="uninstall"
                                Name="SunflowerAI"
                                Wait="yes" />
            </Component>
        </ComponentGroup>
        
        <!-- Model Components -->
        <ComponentGroup Id="ModelComponents" Directory="ModelsFolder">
            <!-- Dynamically generated model components -->
        </ComponentGroup>
        
        <!-- Documentation Components -->
        <ComponentGroup Id="DocumentationComponents" Directory="DocsFolder">
            <Component Id="UserGuide" Guid="{{GENERATED}}">
                <File Id="UserGuidePdf" Source="documentation\\user_guide.pdf" KeyPath="yes" />
            </Component>
        </ComponentGroup>
        
        <!-- Icons -->
        <Icon Id="AppIcon.ico" SourceFile="assets\\icon.ico" />
        
        <!-- Properties -->
        <Property Id="ARPPRODUCTICON" Value="AppIcon.ico" />
        <Property Id="ARPHELPLINK" Value="{self.config.app_url}" />
        
        <!-- Launch Conditions -->
        <Condition Message="This application requires Windows 10 or higher.">
            <![CDATA[Installed OR (VersionNT >= 603)]]>
        </Condition>
        
        <Condition Message="This application requires at least 4GB of RAM.">
            <![CDATA[Installed OR (PhysicalMemory >= 4096)]]>
        </Condition>
        
        <!-- Custom Actions -->
        <CustomAction Id="LaunchApplication"
                      FileKey="LauncherExe"
                      ExeCommand=""
                      Execute="immediate"
                      Impersonate="yes"
                      Return="asyncNoWait" />
        
        <!-- UI -->
        <UIRef Id="WixUI_InstallDir" />
        <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />
        
    </Product>
</Wix>"""
        
        # Generate unique GUIDs for components
        import uuid
        wxs_template = wxs_template.replace("{GENERATED}", str(uuid.uuid4()).upper())
        
        return wxs_template
    
    def _is_wix_available(self) -> bool:
        """Check if WiX toolset is available"""
        try:
            result = subprocess.run(["candle", "-?"], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def _build_with_wix(self, wxs_file: Path) -> bool:
        """Build MSI using WiX toolset"""
        try:
            wixobj_file = self.build_dir / "sunflower.wixobj"
            msi_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}.msi"
            
            # Compile WiX source
            compile_cmd = [
                "candle",
                "-arch", "x64",
                "-out", str(wixobj_file),
                str(wxs_file)
            ]
            
            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"WiX compilation failed: {result.stderr}")
                return False
            
            # Link to create MSI
            link_cmd = [
                "light",
                "-ext", "WixUIExtension",
                "-out", str(msi_file),
                str(wixobj_file)
            ]
            
            result = subprocess.run(link_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"WiX linking failed: {result.stderr}")
                return False
            
            self.output_path = msi_file
            return True
            
        except Exception as e:
            self.errors.append(f"WiX build failed: {e}")
            return False
    
    def _build_with_msitools(self) -> bool:
        """Alternative MSI creation using Python msitools"""
        try:
            import msilib
            
            msi_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}.msi"
            
            # Create MSI database
            db = msilib.init_database(
                str(msi_file),
                msilib.schema,
                self.config.app_name,
                f"{{{str(uuid.uuid4()).upper()}}}",
                self.config.app_version,
                self.config.app_publisher
            )
            
            # Add files to MSI
            msilib.add_data(db, "Directory", [
                ("TARGETDIR", None, "SourceDir"),
                ("ProgramFiles64Folder", "TARGETDIR", "PFiles64"),
                ("INSTALLFOLDER", "ProgramFiles64Folder", self.config.app_name)
            ])
            
            # Add components and files
            cab = msilib.CAB("sunflower.cab")
            component_id = 1
            
            for root, dirs, files in os.walk(self.build_dir):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.build_dir)
                    
                    # Add file to CAB
                    cab.append(str(file_path), str(rel_path))
                    
                    # Add component entry
                    msilib.add_data(db, "Component", [(
                        f"Component{component_id}",
                        f"{{{str(uuid.uuid4()).upper()}}}",
                        "INSTALLFOLDER",
                        0,
                        None,
                        str(rel_path)
                    )])
                    
                    component_id += 1
            
            # Commit database
            cab.commit(db)
            db.Commit()
            
            self.output_path = msi_file
            return True
            
        except Exception as e:
            self.errors.append(f"MSI creation with msitools failed: {e}")
            return False
    
    def _sign_package(self) -> bool:
        """Sign Windows MSI package"""
        if not self.config.certificate_path:
            logger.warning("No certificate provided for signing")
            return False
        
        try:
            sign_cmd = [
                "signtool", "sign",
                "/f", self.config.certificate_path,
                "/p", self.config.certificate_password,
                "/t", "http://timestamp.digicert.com",
                "/d", self.config.app_name,
                str(self.output_path)
            ]
            
            result = subprocess.run(sign_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"Signing failed: {result.stderr}")
                return False
            
            logger.info("Package signed successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"Signing error: {e}")
            return False


class MacOSDMGBuilder(PackageBuilder):
    """macOS DMG package builder"""
    
    def _create_package(self) -> bool:
        """Create macOS DMG package"""
        try:
            logger.info("Creating macOS DMG package")
            
            # Create app bundle structure
            app_bundle = self.build_dir / f"{self.config.app_name}.app"
            self._create_app_bundle(app_bundle)
            
            # Create DMG
            dmg_file = Path(self.config.output_dir) / f"{self.config.app_name}-{self.config.app_version}.dmg"
            
            # Create temporary DMG
            temp_dmg = self.build_dir / "temp.dmg"
            
            create_cmd = [
                "hdiutil", "create",
                "-volname", self.config.app_name,
                "-srcfolder", str(self.build_dir),
                "-ov",
                "-format", "UDRW",
                str(temp_dmg)
            ]
            
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"DMG creation failed: {result.stderr}")
                return False
            
            # Mount DMG for customization
            mount_result = subprocess.run(
                ["hdiutil", "attach", str(temp_dmg), "-readwrite"],
                capture_output=True,
                text=True
            )
            
            if mount_result.returncode == 0:
                # Extract mount point
                mount_point = None
                for line in mount_result.stdout.split('\n'):
                    if '/Volumes/' in line:
                        mount_point = line.split('\t')[-1].strip()
                        break
                
                if mount_point:
                    # Add background image and layout
                    self._customize_dmg(mount_point)
                    
                    # Unmount
                    subprocess.run(["hdiutil", "detach", mount_point])
            
            # Convert to compressed DMG
            convert_cmd = [
                "hdiutil", "convert",
                str(temp_dmg),
                "-format", "UDZO",
                "-o", str(dmg_file)
            ]
            
            result = subprocess.run(convert_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"DMG conversion failed: {result.stderr}")
                return False
            
            self.output_path = dmg_file
            return True
            
        except Exception as e:
            self.errors.append(f"DMG creation failed: {e}")
            return False
    
    def _create_app_bundle(self, app_bundle: Path) -> None:
        """Create macOS app bundle structure"""
        # Create directory structure
        contents = app_bundle / "Contents"
        macos = contents / "MacOS"
        resources = contents / "Resources"
        frameworks = contents / "Frameworks"
        
        for directory in [macos, resources, frameworks]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Copy executables
        exec_src = self.build_dir / "executables" / "launcher"
        if exec_src.exists():
            shutil.copy2(exec_src, macos / self.config.app_name)
            os.chmod(macos / self.config.app_name, 0o755)
        
        # Copy resources
        for resource_type in ["models", "modelfiles", "documentation"]:
            src_dir = self.build_dir / resource_type
            if src_dir.exists():
                shutil.copytree(src_dir, resources / resource_type, dirs_exist_ok=True)
        
        # Create Info.plist
        info_plist = self._generate_info_plist()
        plist_path = contents / "Info.plist"
        plist_path.write_text(info_plist)
        
        # Copy icon
        icon_src = self.assets_dir / "icon.icns"
        if icon_src.exists():
            shutil.copy2(icon_src, resources / "AppIcon.icns")
    
    def _generate_info_plist(self) -> str:
        """Generate Info.plist for app bundle"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>{self.config.app_name}</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>education.sunflowerai.professional</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{self.config.app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{self.config.app_version}</string>
    <key>CFBundleVersion</key>
    <string>{self.config.app_version}</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2025 {self.config.app_publisher}. All rights reserved.</string>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.education</string>
</dict>
</plist>"""
    
    def _customize_dmg(self, mount_point: str) -> None:
        """Customize DMG appearance"""
        try:
            # Create Applications symlink
            apps_link = Path(mount_point) / "Applications"
            if not apps_link.exists():
                os.symlink("/Applications", str(apps_link))
            
            # Create .DS_Store for window settings (would need additional tools)
            # This is where you'd set window size, icon positions, background image
            
            # Add background image if available
            background_src = self.assets_dir / "dmg_background.png"
            if background_src.exists():
                dmg_resources = Path(mount_point) / ".background"
                dmg_resources.mkdir(exist_ok=True)
                shutil.copy2(background_src, dmg_resources / "background.png")
                
        except Exception as e:
            logger.warning(f"DMG customization failed: {e}")
    
    def _sign_package(self) -> bool:
        """Sign macOS DMG package"""
        if not self.config.certificate_path:
            logger.warning("No certificate provided for signing")
            return False
        
        try:
            # Sign the app bundle first
            app_bundle = self.build_dir / f"{self.config.app_name}.app"
            
            sign_cmd = [
                "codesign",
                "--force",
                "--deep",
                "--sign", self.config.certificate_path,
                str(app_bundle)
            ]
            
            result = subprocess.run(sign_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"App signing failed: {result.stderr}")
                return False
            
            # Sign the DMG
            dmg_sign_cmd = [
                "codesign",
                "--force",
                "--sign", self.config.certificate_path,
                str(self.output_path)
            ]
            
            result = subprocess.run(dmg_sign_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.errors.append(f"DMG signing failed: {result.stderr}")
                return False
            
            # Notarize for macOS Catalina and later
            if self.config.app_version:
                self._notarize_package()
            
            logger.info("Package signed successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"Signing error: {e}")
            return False
    
    def _notarize_package(self) -> bool:
        """Notarize package with Apple"""
        # This would require Apple Developer credentials
        # Implementation would use altool or notarytool
        logger.info("Notarization would be performed here with Apple credentials")
        return True


class UniversalPackageBuilder(PackageBuilder):
    """Universal package builder for cross-platform distribution"""
    
    def _create_package(self) -> bool:
        """Create universal package (ZIP/TAR)"""
        try:
            logger.info("Creating universal package")
            
            # Create launcher script for each platform
            self._create_universal_launcher()
            
            # Create archive
            archive_name = f"{self.config.app_name}-{self.config.app_version}-universal"
            
            # Create both ZIP and TAR.GZ
            zip_file = Path(self.config.output_dir) / f"{archive_name}.zip"
            tar_file = Path(self.config.output_dir) / f"{archive_name}.tar.gz"
            
            # Create ZIP archive
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(self.build_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arc_name = file_path.relative_to(self.build_dir)
                        zf.write(file_path, arc_name)
            
            # Create TAR.GZ archive
            with tarfile.open(tar_file, 'w:gz') as tf:
                tf.add(self.build_dir, arcname=self.config.app_name)
            
            self.output_path = zip_file  # Primary output
            logger.info(f"Created universal packages: {zip_file} and {tar_file}")
            
            return True
            
        except Exception as e:
            self.errors.append(f"Universal package creation failed: {e}")
            return False
    
    def _create_universal_launcher(self) -> None:
        """Create universal launcher scripts"""
        # Windows batch launcher
        windows_launcher = self.build_dir / "launch_windows.bat"
        windows_launcher.write_text(f"""@echo off
title {self.config.app_name}
echo Starting {self.config.app_name}...

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8 or later.
    pause
    exit /b 1
)

:: Check hardware requirements
for /f "tokens=2 delims==" %%i in ('wmic computersystem get TotalPhysicalMemory /value') do set mem=%%i
set /a mem_gb=%mem:~0,-9%/1
if %mem_gb% lss 4 (
    echo WARNING: System has less than 4GB RAM. Performance may be limited.
    pause
)

:: Launch application
cd /d "%~dp0"
python interface\\gui.py
if errorlevel 1 (
    echo Error launching application. Check error.log for details.
    pause
)
""")
        
        # macOS/Linux shell launcher
        unix_launcher = self.build_dir / "launch_unix.sh"
        unix_launcher.write_text(f"""#!/bin/bash
# {self.config.app_name} Launcher

echo "Starting {self.config.app_name}..."

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or later."
    exit 1
fi

# Check hardware requirements
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    mem_bytes=$(sysctl -n hw.memsize)
    mem_gb=$((mem_bytes / 1073741824))
else
    # Linux
    mem_kb=$(grep MemTotal /proc/meminfo | awk '{{print $2}}')
    mem_gb=$((mem_kb / 1048576))
fi

if [ $mem_gb -lt 4 ]; then
    echo "WARNING: System has less than 4GB RAM. Performance may be limited."
fi

# Launch application
cd "$(dirname "$0")"
python3 interface/gui.py || {{
    echo "Error launching application. Check error.log for details."
    exit 1
}}
""")
        
        # Make Unix launcher executable
        os.chmod(unix_launcher, 0o755)


def create_package(
    package_type: str,
    version: str = "6.2.0",
    sign: bool = False,
    cert_path: str = "",
    cert_pass: str = ""
) -> bool:
    """Main function to create installation package"""
    
    # Determine package type
    if package_type.lower() == "auto":
        if platform.system() == "Windows":
            pkg_type = PackageType.MSI
        elif platform.system() == "Darwin":
            pkg_type = PackageType.DMG
        else:
            pkg_type = PackageType.UNIVERSAL
    else:
        try:
            pkg_type = PackageType(package_type.lower())
        except ValueError:
            logger.error(f"Invalid package type: {package_type}")
            return False
    
    # Create configuration
    config = InstallerConfiguration(
        package_type=pkg_type,
        app_version=version,
        sign_package=sign,
        certificate_path=cert_path,
        certificate_password=cert_pass
    )
    
    # Create output directory
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Select appropriate builder
    if pkg_type == PackageType.MSI:
        builder = WindowsMSIBuilder(config)
    elif pkg_type == PackageType.DMG:
        builder = MacOSDMGBuilder(config)
    else:
        builder = UniversalPackageBuilder(config)
    
    # Build package
    success = builder.build()
    
    if success:
        logger.info(f"Package created successfully: {builder.output_path}")
    else:
        logger.error("Package creation failed")
        for error in builder.errors:
            logger.error(f"  - {error}")
    
    return success


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sunflower AI Professional System - Package Creator"
    )
    parser.add_argument(
        "--type",
        choices=["msi", "dmg", "universal", "auto"],
        default="auto",
        help="Package type to create"
    )
    parser.add_argument(
        "--version",
        default="6.2.0",
        help="Version number"
    )
    parser.add_argument(
        "--sign",
        action="store_true",
        help="Sign the package"
    )
    parser.add_argument(
        "--cert",
        help="Certificate path for signing"
    )
    parser.add_argument(
        "--cert-pass",
        help="Certificate password"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("SUNFLOWER AI PROFESSIONAL - PACKAGE CREATOR")
    print(f"Version: {args.version}")
    print(f"Package Type: {args.type}")
    print("="*60 + "\n")
    
    success = create_package(
        args.type,
        args.version,
        args.sign,
        args.cert or "",
        args.cert_pass or ""
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

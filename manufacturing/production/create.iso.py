#!/usr/bin/env python3
"""
Sunflower AI Professional System - CD-ROM Partition Creator
Creates read-only ISO9660 partition with system files and AI models.

Copyright (c) 2025 Sunflower AI Corporation
Version: 6.2.0
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
import platform
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from __init__ import (
    DeviceSpecification,
    PartitionType,
    ProductionStage,
    PartitionError,
    generate_device_id,
    generate_hardware_token,
    calculate_checksum,
    logger
)

class ISOCreator:
    """Handles creation of ISO9660 CD-ROM partitions."""
    
    def __init__(self, platform_target: str = 'universal'):
        """
        Initialize ISO creator.
        
        Args:
            platform_target: Target platform (windows, macos, universal)
        """
        self.platform_target = platform_target
        self.system_platform = platform.system().lower()
        self.master_path = Path(__file__).parent.parent / 'master_files' / 'current'
        self.temp_dir = None
        self.iso_path = None
        self.checksums = {}
        
        # Platform-specific ISO creation tools
        self.iso_tools = self._detect_iso_tools()
        
        # Verify master files exist
        if not self.master_path.exists():
            raise PartitionError(
                f"Master files not found at {self.master_path}",
                ProductionStage.PREPARATION
            )
    
    def _detect_iso_tools(self) -> Dict[str, Path]:
        """Detect available ISO creation tools."""
        tools = {}
        
        if self.system_platform == 'darwin':  # macOS
            # Use built-in hdiutil
            hdiutil = shutil.which('hdiutil')
            if hdiutil:
                tools['hdiutil'] = Path(hdiutil)
                logger.info(f"Found hdiutil at {hdiutil}")
        
        elif self.system_platform == 'windows':
            # Check for various Windows ISO tools
            oscdimg = Path("C:/Program Files (x86)/Windows Kits/10/Assessment and Deployment Kit/Deployment Tools/amd64/Oscdimg/oscdimg.exe")
            if oscdimg.exists():
                tools['oscdimg'] = oscdimg
                logger.info(f"Found oscdimg at {oscdimg}")
            
            # Alternative: mkisofs
            mkisofs = shutil.which('mkisofs')
            if mkisofs:
                tools['mkisofs'] = Path(mkisofs)
                logger.info(f"Found mkisofs at {mkisofs}")
        
        else:  # Linux
            # Use genisoimage or mkisofs
            for tool_name in ['genisoimage', 'mkisofs']:
                tool_path = shutil.which(tool_name)
                if tool_path:
                    tools[tool_name] = Path(tool_path)
                    logger.info(f"Found {tool_name} at {tool_path}")
                    break
        
        if not tools:
            raise PartitionError(
                "No ISO creation tools found. Please install required tools.",
                ProductionStage.PREPARATION
            )
        
        return tools
    
    def prepare_iso_contents(self, device_spec: DeviceSpecification) -> Path:
        """
        Prepare ISO contents in temporary directory.
        
        Args:
            device_spec: Device specification
            
        Returns:
            Path to prepared directory
        """
        logger.info(f"Preparing ISO contents for device {device_spec.device_id}")
        
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix='sunflower_iso_'))
        logger.info(f"Created temporary directory: {self.temp_dir}")
        
        try:
            # Copy platform-specific files
            if self.platform_target in ['windows', 'universal']:
                self._copy_windows_files(device_spec)
            
            if self.platform_target in ['macos', 'universal']:
                self._copy_macos_files(device_spec)
            
            # Copy shared files
            self._copy_shared_files(device_spec)
            
            # Copy AI models based on hardware variant
            self._copy_ai_models(device_spec)
            
            # Generate device-specific files
            self._generate_device_files(device_spec)
            
            # Create autorun files for Windows
            if self.platform_target in ['windows', 'universal']:
                self._create_autorun()
            
            # Calculate checksums for all files
            self._calculate_checksums()
            
            # Write manifest
            self._write_manifest(device_spec)
            
            return self.temp_dir
            
        except Exception as e:
            # Clean up on error
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            raise PartitionError(
                f"Failed to prepare ISO contents: {str(e)}",
                ProductionStage.FILE_DEPLOYMENT,
                device_spec.device_id
            )
    
    def _copy_windows_files(self, device_spec: DeviceSpecification):
        """Copy Windows-specific files."""
        windows_src = self.master_path / 'windows'
        if not windows_src.exists():
            logger.warning("Windows files not found in master files")
            return
        
        windows_dst = self.temp_dir / 'windows'
        windows_dst.mkdir(parents=True, exist_ok=True)
        
        # Copy launcher
        launcher_src = windows_src / 'launcher'
        if launcher_src.exists():
            shutil.copytree(launcher_src, windows_dst / 'launcher')
            logger.info("Copied Windows launcher")
        
        # Copy Ollama for Windows
        ollama_src = windows_src / 'ollama'
        if ollama_src.exists():
            shutil.copytree(ollama_src, windows_dst / 'ollama')
            logger.info("Copied Ollama for Windows")
    
    def _copy_macos_files(self, device_spec: DeviceSpecification):
        """Copy macOS-specific files."""
        macos_src = self.master_path / 'macos'
        if not macos_src.exists():
            logger.warning("macOS files not found in master files")
            return
        
        macos_dst = self.temp_dir / 'macos'
        macos_dst.mkdir(parents=True, exist_ok=True)
        
        # Copy launcher app
        launcher_src = macos_src / 'launcher.app'
        if launcher_src.exists():
            shutil.copytree(launcher_src, macos_dst / 'launcher.app')
            logger.info("Copied macOS launcher")
        
        # Copy Ollama for macOS
        ollama_src = macos_src / 'ollama'
        if ollama_src.exists():
            shutil.copytree(ollama_src, macos_dst / 'ollama')
            logger.info("Copied Ollama for macOS")
    
    def _copy_shared_files(self, device_spec: DeviceSpecification):
        """Copy shared files for all platforms."""
        shared_src = self.master_path / 'shared'
        if not shared_src.exists():
            logger.warning("Shared files not found in master files")
            return
        
        # Copy documentation
        docs_src = shared_src / 'documentation'
        if docs_src.exists():
            shutil.copytree(docs_src, self.temp_dir / 'documentation')
            logger.info("Copied documentation")
        
        # Copy modelfiles
        modelfiles_src = shared_src / 'modelfiles'
        if modelfiles_src.exists():
            shutil.copytree(modelfiles_src, self.temp_dir / 'modelfiles')
            logger.info("Copied modelfiles")
    
    def _copy_ai_models(self, device_spec: DeviceSpecification):
        """Copy AI models based on device specification."""
        models_dst = self.temp_dir / 'models'
        models_dst.mkdir(parents=True, exist_ok=True)
        
        # Determine which models to include
        if device_spec.model_variant == 'auto':
            # Include all models for auto-detection
            model_variants = ['7b', '3b', '1b', '1b-q4_0']
        else:
            # Include specific model only
            model_variants = [device_spec.model_variant]
        
        for variant in model_variants:
            model_name = f"llama3.2_{variant}"
            
            # Try platform-specific path first
            for platform_name in ['windows', 'macos']:
                model_src = self.master_path / platform_name / 'models' / model_name
                if model_src.exists():
                    model_dst = models_dst / model_name
                    if model_src.is_file():
                        shutil.copy2(model_src, model_dst)
                    else:
                        shutil.copytree(model_src, model_dst)
                    logger.info(f"Copied model: {model_name}")
                    break
            else:
                # Try shared models
                model_src = self.master_path / 'shared' / 'models' / model_name
                if model_src.exists():
                    model_dst = models_dst / model_name
                    if model_src.is_file():
                        shutil.copy2(model_src, model_dst)
                    else:
                        shutil.copytree(model_src, model_dst)
                    logger.info(f"Copied model: {model_name}")
                else:
                    logger.warning(f"Model not found: {model_name}")
    
    def _generate_device_files(self, device_spec: DeviceSpecification):
        """Generate device-specific authentication and configuration files."""
        config_dir = self.temp_dir / 'config'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate hardware token
        secret_key = os.environ.get('SUNFLOWER_SECRET_KEY', b'default_manufacturing_key_2025')
        if isinstance(secret_key, str):
            secret_key = secret_key.encode()
        
        hardware_token = generate_hardware_token(device_spec.device_id, secret_key)
        
        # Create device configuration
        device_config = {
            'device_id': device_spec.device_id,
            'batch_id': device_spec.batch_id,
            'platform': device_spec.platform,
            'model_variant': device_spec.model_variant,
            'hardware_token': hardware_token,
            'creation_date': device_spec.creation_timestamp.isoformat(),
            'version': '6.2.0',
            'cdrom_partition': {
                'type': 'iso9660',
                'size_mb': device_spec.cdrom_size_mb,
                'read_only': True
            },
            'usb_partition': {
                'type': 'fat32',
                'size_mb': device_spec.usb_size_mb,
                'read_only': False,
                'encrypted': True
            }
        }
        
        # Write device configuration
        config_path = config_dir / 'device.json'
        with open(config_path, 'w') as f:
            json.dump(device_config, f, indent=2)
        
        logger.info(f"Generated device configuration with token: {hardware_token[:8]}...")
    
    def _create_autorun(self):
        """Create autorun.inf for Windows auto-launch."""
        autorun_content = """[AutoRun]
OPEN=windows\\launcher\\SunflowerAI.exe
ICON=windows\\launcher\\sunflower.ico
LABEL=Sunflower AI Professional System
ACTION=Install Sunflower AI Professional System

[Content]
MusicFiles=false
PictureFiles=false
VideoFiles=false

[DeviceInstall]
DriverPath=windows\\drivers
"""
        
        autorun_path = self.temp_dir / 'autorun.inf'
        with open(autorun_path, 'w') as f:
            f.write(autorun_content)
        
        logger.info("Created autorun.inf for Windows")
    
    def _calculate_checksums(self):
        """Calculate SHA-256 checksums for all files."""
        logger.info("Calculating checksums for all files...")
        
        for file_path in self.temp_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.temp_dir)
                checksum = calculate_checksum(file_path)
                self.checksums[str(relative_path)] = checksum
                
        logger.info(f"Calculated {len(self.checksums)} checksums")
    
    def _write_manifest(self, device_spec: DeviceSpecification):
        """Write manifest file with checksums and metadata."""
        manifest = {
            'device_id': device_spec.device_id,
            'batch_id': device_spec.batch_id,
            'creation_timestamp': device_spec.creation_timestamp.isoformat(),
            'platform': self.platform_target,
            'version': '6.2.0',
            'checksums': self.checksums,
            'file_count': len(self.checksums),
            'total_size_bytes': sum(
                (self.temp_dir / Path(f)).stat().st_size 
                for f in self.checksums.keys()
            )
        }
        
        manifest_path = self.temp_dir / 'MANIFEST.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Also create a human-readable manifest
        manifest_txt = self.temp_dir / 'MANIFEST.txt'
        with open(manifest_txt, 'w') as f:
            f.write("SUNFLOWER AI PROFESSIONAL SYSTEM - FILE MANIFEST\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Device ID: {device_spec.device_id}\n")
            f.write(f"Batch ID: {device_spec.batch_id}\n")
            f.write(f"Created: {device_spec.creation_timestamp}\n")
            f.write(f"Platform: {self.platform_target}\n")
            f.write(f"Version: 6.2.0\n")
            f.write(f"Files: {len(self.checksums)}\n\n")
            f.write("FILE CHECKSUMS (SHA-256):\n")
            f.write("-" * 60 + "\n")
            
            for file_path, checksum in sorted(self.checksums.items()):
                f.write(f"{checksum}  {file_path}\n")
        
        logger.info("Written manifest files")
    
    def create_iso(self, device_spec: DeviceSpecification, output_path: Path) -> Path:
        """
        Create ISO file from prepared contents.
        
        Args:
            device_spec: Device specification
            output_path: Output path for ISO file
            
        Returns:
            Path to created ISO file
        """
        logger.info(f"Creating ISO file: {output_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.system_platform == 'darwin':  # macOS
            return self._create_iso_macos(output_path)
        elif self.system_platform == 'windows':
            return self._create_iso_windows(output_path)
        else:  # Linux
            return self._create_iso_linux(output_path)
    
    def _create_iso_macos(self, output_path: Path) -> Path:
        """Create ISO using macOS hdiutil."""
        if 'hdiutil' not in self.iso_tools:
            raise PartitionError(
                "hdiutil not found",
                ProductionStage.PARTITION_CREATION
            )
        
        # Create hybrid ISO for cross-platform compatibility
        cmd = [
            str(self.iso_tools['hdiutil']),
            'makehybrid',
            '-iso',
            '-joliet',
            '-default-volume-name', 'SUNFLOWER_AI',
            '-o', str(output_path),
            str(self.temp_dir)
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise PartitionError(
                f"ISO creation failed: {result.stderr}",
                ProductionStage.PARTITION_CREATION
            )
        
        logger.info(f"ISO created successfully: {output_path}")
        return output_path
    
    def _create_iso_windows(self, output_path: Path) -> Path:
        """Create ISO using Windows tools."""
        if 'oscdimg' in self.iso_tools:
            # Use Windows ADK oscdimg
            cmd = [
                str(self.iso_tools['oscdimg']),
                '-j1',  # Joliet support
                '-l', 'SUNFLOWER_AI',  # Volume label
                '-u2',  # UDF file system
                str(self.temp_dir),
                str(output_path)
            ]
        elif 'mkisofs' in self.iso_tools:
            # Use mkisofs as fallback
            cmd = [
                str(self.iso_tools['mkisofs']),
                '-J',  # Joliet support
                '-r',  # Rock Ridge
                '-V', 'SUNFLOWER_AI',  # Volume label
                '-o', str(output_path),
                str(self.temp_dir)
            ]
        else:
            raise PartitionError(
                "No suitable ISO tool found for Windows",
                ProductionStage.PARTITION_CREATION
            )
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise PartitionError(
                f"ISO creation failed: {result.stderr}",
                ProductionStage.PARTITION_CREATION
            )
        
        logger.info(f"ISO created successfully: {output_path}")
        return output_path
    
    def _create_iso_linux(self, output_path: Path) -> Path:
        """Create ISO using Linux tools."""
        tool_name = next(iter(self.iso_tools.keys()))
        tool_path = self.iso_tools[tool_name]
        
        cmd = [
            str(tool_path),
            '-J',  # Joliet support
            '-r',  # Rock Ridge
            '-V', 'SUNFLOWER_AI',  # Volume label
            '-o', str(output_path),
            str(self.temp_dir)
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise PartitionError(
                f"ISO creation failed: {result.stderr}",
                ProductionStage.PARTITION_CREATION
            )
        
        logger.info(f"ISO created successfully: {output_path}")
        return output_path
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and self.temp_dir.exists():
            logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None


def main():
    """Main entry point for ISO creation."""
    parser = argparse.ArgumentParser(
        description='Create CD-ROM partition for Sunflower AI device'
    )
    parser.add_argument(
        '--device-id',
        help='Device ID (auto-generated if not provided)'
    )
    parser.add_argument(
        '--batch-id',
        required=True,
        help='Batch ID for production run'
    )
    parser.add_argument(
        '--platform',
        choices=['windows', 'macos', 'universal'],
        default='universal',
        help='Target platform'
    )
    parser.add_argument(
        '--model-variant',
        choices=['7b', '3b', '1b', '1b-q4_0', 'auto'],
        default='auto',
        help='AI model variant to include'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output path for ISO file'
    )
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary files after creation'
    )
    
    args = parser.parse_args()
    
    # Generate device ID if not provided
    if not args.device_id:
        import random
        sequence = random.randint(1, 999999)
        args.device_id = generate_device_id(args.batch_id, sequence)
    
    # Default output path
    if not args.output:
        args.output = Path('output') / f'{args.device_id}.iso'
    
    # Create device specification
    device_spec = DeviceSpecification(
        device_id=args.device_id,
        batch_id=args.batch_id,
        capacity_gb=8,
        cdrom_size_mb=4096,
        usb_size_mb=1024,
        platform=args.platform,
        model_variant=args.model_variant,
        creation_timestamp=datetime.now(),
        validation_checksum='',
        hardware_token='',
        production_stage=ProductionStage.PARTITION_CREATION
    )
    
    # Create ISO
    creator = ISOCreator(args.platform)
    
    try:
        # Prepare contents
        creator.prepare_iso_contents(device_spec)
        
        # Create ISO
        iso_path = creator.create_iso(device_spec, args.output)
        
        # Calculate ISO checksum
        iso_checksum = calculate_checksum(iso_path)
        device_spec.validation_checksum = iso_checksum
        
        logger.info(f"ISO creation complete: {iso_path}")
        logger.info(f"Checksum: {iso_checksum}")
        
        # Write device spec
        spec_path = iso_path.with_suffix('.json')
        with open(spec_path, 'w') as f:
            json.dump(device_spec.to_dict(), f, indent=2)
        
        print(f"SUCCESS: ISO created at {iso_path}")
        print(f"Device ID: {device_spec.device_id}")
        print(f"Checksum: {iso_checksum}")
        
        return 0
        
    except Exception as e:
        logger.error(f"ISO creation failed: {str(e)}")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1
        
    finally:
        if not args.keep_temp:
            creator.cleanup()


if __name__ == '__main__':
    sys.exit(main())

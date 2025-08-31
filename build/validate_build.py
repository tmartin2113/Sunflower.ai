#!/usr/bin/env python3
"""
Sunflower AI Professional System - Build Validation Script
Validates build artifacts and ensures production readiness
Version: 6.2
"""

import os
import sys
import json
import hashlib
import zipfile
import platform
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('build_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BuildValidator')


class BuildValidator:
    """Comprehensive build validation for production deployment"""
    
    REQUIRED_FILES = {
        'windows': [
            'windows/SunflowerAI.exe',
            'launch.bat',
            'autorun.inf'
        ],
        'macos': [
            'macos/SunflowerAI.app',
            'launch.sh'
        ],
        'common': [
            'README.txt',
            'models/',
            'documentation/',
            'modelfiles/'
        ]
    }
    
    REQUIRED_PARTITION_FILES = {
        'cdrom': [
            'README.txt',
            'models/deployment_manifest.json'
        ],
        'usb': [
            'profiles/.encryption/config.json',
            'config/system.json',
            'README.txt'
        ]
    }
    
    MIN_FILE_SIZES = {
        'SunflowerAI.exe': 10 * 1024 * 1024,  # 10MB minimum
        'SunflowerAI.app': 15 * 1024 * 1024,  # 15MB minimum
        'models/': 500 * 1024 * 1024,  # 500MB minimum for models directory
    }
    
    def __init__(self, build_dir: Path):
        """Initialize validator with build directory"""
        self.build_dir = Path(build_dir)
        self.dist_dir = self.build_dir.parent / 'dist'
        self.cdrom_dir = self.dist_dir / 'cdrom_partition'
        self.usb_dir = self.dist_dir / 'usb_partition'
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'platform': platform.system(),
            'checks': [],
            'errors': [],
            'warnings': [],
            'passed': False
        }
    
    def validate_all(self) -> bool:
        """Run all validation checks"""
        logger.info("=" * 60)
        logger.info("Starting Build Validation")
        logger.info(f"Build Directory: {self.build_dir}")
        logger.info(f"Distribution Directory: {self.dist_dir}")
        logger.info("=" * 60)
        
        checks = [
            ('Directory Structure', self.check_directory_structure),
            ('Required Files', self.check_required_files),
            ('File Sizes', self.check_file_sizes),
            ('Partition Structure', self.check_partition_structure),
            ('Model Files', self.check_model_files),
            ('Executable Integrity', self.check_executable_integrity),
            ('Documentation', self.check_documentation),
            ('Security Files', self.check_security_files),
            ('Build Manifest', self.check_build_manifest),
            ('Checksums', self.check_checksums),
            ('Platform Compatibility', self.check_platform_compatibility),
            ('Dependencies', self.check_dependencies)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            logger.info(f"\nRunning: {check_name}")
            try:
                result = check_func()
                self.validation_results['checks'].append({
                    'name': check_name,
                    'passed': result,
                    'timestamp': datetime.now().isoformat()
                })
                
                if result:
                    logger.info(f"✓ {check_name} - PASSED")
                else:
                    logger.error(f"✗ {check_name} - FAILED")
                    all_passed = False
                    
            except Exception as e:
                logger.error(f"✗ {check_name} - ERROR: {str(e)}")
                self.validation_results['errors'].append({
                    'check': check_name,
                    'error': str(e)
                })
                all_passed = False
        
        self.validation_results['passed'] = all_passed
        
        # Generate validation report
        self.generate_report()
        
        return all_passed
    
    def check_directory_structure(self) -> bool:
        """Validate directory structure"""
        required_dirs = [
            self.dist_dir,
            self.cdrom_dir,
            self.usb_dir,
            self.cdrom_dir / 'models',
            self.cdrom_dir / 'documentation',
            self.usb_dir / 'profiles',
            self.usb_dir / 'config'
        ]
        
        missing_dirs = []
        for directory in required_dirs:
            if not directory.exists():
                missing_dirs.append(str(directory))
                logger.warning(f"Missing directory: {directory}")
        
        if missing_dirs:
            self.validation_results['errors'].append({
                'type': 'missing_directories',
                'directories': missing_dirs
            })
            return False
        
        return True
    
    def check_required_files(self) -> bool:
        """Check for all required files"""
        current_platform = platform.system().lower()
        platform_files = []
        
        # Determine which platform files to check
        if current_platform == 'windows':
            platform_files = self.REQUIRED_FILES['windows']
        elif current_platform == 'darwin':
            platform_files = self.REQUIRED_FILES['macos']
        
        # Add common files
        all_required = platform_files + self.REQUIRED_FILES['common']
        
        missing_files = []
        for file_path in all_required:
            full_path = self.cdrom_dir / file_path
            
            # Check if it's a directory or file
            if file_path.endswith('/'):
                if not full_path.exists() or not full_path.is_dir():
                    missing_files.append(file_path)
                    logger.warning(f"Missing directory: {file_path}")
            else:
                if not full_path.exists() or not full_path.is_file():
                    missing_files.append(file_path)
                    logger.warning(f"Missing file: {file_path}")
        
        if missing_files:
            self.validation_results['errors'].append({
                'type': 'missing_files',
                'files': missing_files
            })
            return False
        
        return True
    
    def check_file_sizes(self) -> bool:
        """Validate file sizes meet minimum requirements"""
        size_issues = []
        
        for file_pattern, min_size in self.MIN_FILE_SIZES.items():
            if file_pattern.endswith('/'):
                # Check directory size
                dir_path = self.cdrom_dir / file_pattern
                if dir_path.exists():
                    dir_size = self._get_directory_size(dir_path)
                    if dir_size < min_size:
                        size_issues.append({
                            'path': file_pattern,
                            'expected_min': min_size,
                            'actual': dir_size
                        })
                        logger.warning(
                            f"Directory {file_pattern} too small: "
                            f"{dir_size / (1024*1024):.2f}MB < {min_size / (1024*1024):.2f}MB"
                        )
            else:
                # Check file size
                # Search for file in platform directories
                for platform_dir in ['windows', 'macos']:
                    file_path = self.cdrom_dir / platform_dir / Path(file_pattern).name
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        if file_size < min_size:
                            size_issues.append({
                                'path': str(file_path),
                                'expected_min': min_size,
                                'actual': file_size
                            })
                            logger.warning(
                                f"File {file_path} too small: "
                                f"{file_size / (1024*1024):.2f}MB < {min_size / (1024*1024):.2f}MB"
                            )
        
        if size_issues:
            self.validation_results['warnings'].append({
                'type': 'file_size_issues',
                'issues': size_issues
            })
            # Size issues are warnings, not failures
            return True
        
        return True
    
    def check_partition_structure(self) -> bool:
        """Validate partition file structure"""
        all_valid = True
        
        # Check CD-ROM partition
        for file_path in self.REQUIRED_PARTITION_FILES['cdrom']:
            full_path = self.cdrom_dir / file_path
            if not full_path.exists():
                logger.error(f"Missing CD-ROM partition file: {file_path}")
                all_valid = False
        
        # Check USB partition
        for file_path in self.REQUIRED_PARTITION_FILES['usb']:
            full_path = self.usb_dir / file_path
            if not full_path.exists():
                logger.error(f"Missing USB partition file: {file_path}")
                all_valid = False
        
        return all_valid
    
    def check_model_files(self) -> bool:
        """Validate AI model files"""
        models_dir = self.cdrom_dir / 'models'
        
        if not models_dir.exists():
            logger.error("Models directory not found")
            return False
        
        # Check for deployment manifest
        manifest_path = models_dir / 'deployment_manifest.json'
        if not manifest_path.exists():
            logger.error("Model deployment manifest not found")
            return False
        
        # Validate manifest content
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            required_keys = ['version', 'models', 'hardware_detection']
            for key in required_keys:
                if key not in manifest:
                    logger.error(f"Missing key in deployment manifest: {key}")
                    return False
            
            # Check for at least one model variant
            total_models = len(manifest['models'].get('kids', [])) + \
                          len(manifest['models'].get('educator', []))
            
            if total_models == 0:
                logger.error("No model variants found in manifest")
                return False
            
            logger.info(f"Found {total_models} model variants")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid deployment manifest JSON: {e}")
            return False
        
        return True
    
    def check_executable_integrity(self) -> bool:
        """Check executable files for basic integrity"""
        current_platform = platform.system().lower()
        
        if current_platform == 'windows':
            exe_path = self.cdrom_dir / 'windows' / 'SunflowerAI.exe'
            if exe_path.exists():
                # Check PE header for Windows executable
                with open(exe_path, 'rb') as f:
                    header = f.read(2)
                    if header != b'MZ':
                        logger.error("Invalid Windows executable header")
                        return False
        
        elif current_platform == 'darwin':
            app_path = self.cdrom_dir / 'macos' / 'SunflowerAI.app'
            if app_path.exists():
                # Check for Info.plist
                plist_path = app_path / 'Contents' / 'Info.plist'
                if not plist_path.exists():
                    logger.error("Missing Info.plist in app bundle")
                    return False
        
        return True
    
    def check_documentation(self) -> bool:
        """Validate documentation files"""
        docs_dir = self.cdrom_dir / 'documentation'
        
        if not docs_dir.exists():
            logger.warning("Documentation directory not found")
            self.validation_results['warnings'].append({
                'type': 'missing_documentation',
                'path': str(docs_dir)
            })
            return True  # Warning only
        
        # Check for essential documentation
        essential_docs = ['user_guide.pdf', 'parent_guide.pdf', 'safety_guide.pdf']
        missing_docs = []
        
        for doc in essential_docs:
            doc_path = docs_dir / doc
            if not doc_path.exists():
                # Also check without .pdf extension
                alt_path = docs_dir / doc.replace('.pdf', '.txt')
                if not alt_path.exists():
                    missing_docs.append(doc)
        
        if missing_docs:
            logger.warning(f"Missing documentation: {missing_docs}")
            self.validation_results['warnings'].append({
                'type': 'missing_essential_docs',
                'files': missing_docs
            })
        
        return True
    
    def check_security_files(self) -> bool:
        """Validate security configuration files"""
        # Check encryption configuration
        encryption_config = self.usb_dir / 'profiles' / '.encryption' / 'config.json'
        
        if not encryption_config.exists():
            logger.error("Encryption configuration not found")
            return False
        
        try:
            with open(encryption_config, 'r') as f:
                config = json.load(f)
            
            required_fields = ['version', 'algorithm', 'key_derivation']
            for field in required_fields:
                if field not in config:
                    logger.error(f"Missing encryption config field: {field}")
                    return False
            
            # Validate encryption algorithm
            if config['algorithm'] != 'AES-256-GCM':
                logger.warning(f"Non-standard encryption algorithm: {config['algorithm']}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid encryption config JSON: {e}")
            return False
        
        return True
    
    def check_build_manifest(self) -> bool:
        """Validate build manifest"""
        manifest_path = self.dist_dir / 'build_manifest.json'
        
        if not manifest_path.exists():
            logger.warning("Build manifest not found")
            return True  # Not critical
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Check for successful build
            if not manifest.get('success', False):
                logger.error("Build manifest indicates failed build")
                return False
            
            logger.info(f"Build version: {manifest.get('version', 'unknown')}")
            logger.info(f"Build platform: {manifest.get('platform', 'unknown')}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid build manifest JSON: {e}")
            return False
        
        return True
    
    def check_checksums(self) -> bool:
        """Validate file checksums if available"""
        checksum_file = self.dist_dir / 'checksums.json'
        
        if not checksum_file.exists():
            logger.info("No checksum file found, skipping validation")
            return True
        
        try:
            with open(checksum_file, 'r') as f:
                checksums = json.load(f)
            
            mismatches = []
            checked = 0
            
            for file_path, expected_checksum in checksums.items():
                full_path = self.dist_dir / file_path
                
                if full_path.exists() and full_path.is_file():
                    actual_checksum = self._calculate_checksum(full_path)
                    checked += 1
                    
                    if actual_checksum != expected_checksum:
                        mismatches.append({
                            'file': file_path,
                            'expected': expected_checksum,
                            'actual': actual_checksum
                        })
                        logger.error(f"Checksum mismatch: {file_path}")
            
            logger.info(f"Verified {checked} file checksums")
            
            if mismatches:
                self.validation_results['errors'].append({
                    'type': 'checksum_mismatches',
                    'files': mismatches
                })
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid checksums JSON: {e}")
            return False
        
        return True
    
    def check_platform_compatibility(self) -> bool:
        """Check platform-specific compatibility"""
        current_platform = platform.system()
        
        if current_platform == 'Windows':
            # Check Windows version
            import sys
            if sys.getwindowsversion().major < 10:
                logger.warning("Windows version below minimum requirement (10)")
                self.validation_results['warnings'].append({
                    'type': 'platform_compatibility',
                    'issue': 'Windows version below 10'
                })
        
        elif current_platform == 'Darwin':
            # Check macOS version
            mac_ver = platform.mac_ver()[0]
            if mac_ver:
                major, minor = map(int, mac_ver.split('.')[:2])
                if major == 10 and minor < 14:
                    logger.warning("macOS version below minimum requirement (10.14)")
                    self.validation_results['warnings'].append({
                        'type': 'platform_compatibility',
                        'issue': 'macOS version below 10.14'
                    })
        
        # Check available memory
        try:
            import psutil
            available_memory = psutil.virtual_memory().total / (1024**3)
            if available_memory < 4:
                logger.warning(f"System memory below minimum: {available_memory:.1f}GB < 4GB")
                self.validation_results['warnings'].append({
                    'type': 'hardware_requirements',
                    'issue': f'Insufficient memory: {available_memory:.1f}GB'
                })
        except ImportError:
            pass
        
        return True
    
    def check_dependencies(self) -> bool:
        """Check for required runtime dependencies"""
        # Check for Ollama installation
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("Ollama is installed")
            else:
                logger.warning("Ollama not detected")
                self.validation_results['warnings'].append({
                    'type': 'missing_dependency',
                    'dependency': 'Ollama'
                })
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Ollama not found in PATH")
            self.validation_results['warnings'].append({
                'type': 'missing_dependency',
                'dependency': 'Ollama',
                'note': 'User must install separately'
            })
        
        return True
    
    def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory"""
        total = 0
        for path in directory.rglob('*'):
            if path.is_file():
                total += path.stat().st_size
        return total
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def generate_report(self) -> None:
        """Generate validation report"""
        report_path = self.dist_dir / 'validation_report.json'
        
        with open(report_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        total_checks = len(self.validation_results['checks'])
        passed_checks = sum(1 for c in self.validation_results['checks'] if c['passed'])
        
        logger.info(f"Total Checks: {total_checks}")
        logger.info(f"Passed: {passed_checks}")
        logger.info(f"Failed: {total_checks - passed_checks}")
        logger.info(f"Errors: {len(self.validation_results['errors'])}")
        logger.info(f"Warnings: {len(self.validation_results['warnings'])}")
        
        if self.validation_results['passed']:
            logger.info("\n✓ BUILD VALIDATION PASSED - Ready for production")
        else:
            logger.error("\n✗ BUILD VALIDATION FAILED - Review errors above")
        
        logger.info(f"\nDetailed report saved to: {report_path}")


def main():
    """Main entry point for build validation"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sunflower AI Build Validation'
    )
    parser.add_argument(
        '--build-dir',
        type=str,
        default='.',
        help='Build directory to validate'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    build_dir = Path(args.build_dir)
    if not build_dir.exists():
        logger.error(f"Build directory not found: {build_dir}")
        sys.exit(1)
    
    validator = BuildValidator(build_dir)
    
    try:
        success = validator.validate_all()
        
        if args.strict and validator.validation_results['warnings']:
            logger.error("Validation failed in strict mode due to warnings")
            success = False
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Validation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

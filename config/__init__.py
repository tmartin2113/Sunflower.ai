#!/usr/bin/env python3
"""
Sunflower AI Professional System - Configuration Manager
Version: 6.2 - Production Ready
Manages all system configuration with partition detection and hardware optimization
"""

import os
import sys
import json
import yaml
import platform
import logging
import hashlib
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SunflowerConfig')


class HardwareTier(Enum):
    """Hardware capability tiers"""
    HIGH_END = "high_end"
    MID_RANGE = "mid_range"
    LOW_END = "low_end"
    MINIMUM = "minimum"


@dataclass
class HardwareInfo:
    """Hardware detection results"""
    ram_gb: float
    cpu_cores: int
    cpu_threads: int
    cpu_freq_mhz: float
    gpu_available: bool
    gpu_vram_gb: float
    platform: str
    architecture: str
    tier: HardwareTier
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'ram_gb': self.ram_gb,
            'cpu_cores': self.cpu_cores,
            'cpu_threads': self.cpu_threads,
            'cpu_freq_mhz': self.cpu_freq_mhz,
            'gpu_available': self.gpu_available,
            'gpu_vram_gb': self.gpu_vram_gb,
            'platform': self.platform,
            'architecture': self.architecture,
            'tier': self.tier.value
        }


class ConfigurationManager:
    """
    Central configuration management for Sunflower AI System
    Handles partition detection, hardware optimization, and configuration loading
    """
    
    # Configuration schema version
    CONFIG_VERSION = "6.2.0"
    
    # Partition marker files
    CDROM_MARKER = "sunflower_cd.id"
    USB_MARKER = "sunflower_data.id"
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager"""
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.system = platform.system()
        
        # Initialize paths
        self.cdrom_partition = None
        self.usb_partition = None
        self.user_data_dir = None
        
        # Configuration storage
        self.env_config = {}
        self.family_config = {}
        self.model_mapping = {}
        self.version_info = {}
        self.hardware_info = None
        
        # Load configurations
        self._initialize()
    
    def _initialize(self):
        """Initialize all configuration components"""
        try:
            # Detect partitions
            self.cdrom_partition = self._detect_cdrom_partition()
            self.usb_partition = self._detect_usb_partition()
            
            # Set user data directory
            if self.usb_partition:
                self.user_data_dir = self.usb_partition / "sunflower_data"
                self.user_data_dir.mkdir(parents=True, exist_ok=True)
            else:
                # Fallback to home directory
                self.user_data_dir = Path.home() / ".sunflower" / "data"
                self.user_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Load configurations
            self._load_env_config()
            self._load_version_info()
            self._load_family_config()
            self._load_model_mapping()
            
            # Detect hardware
            self.hardware_info = self._detect_hardware()
            
            logger.info(f"Configuration initialized for {self.system}")
            logger.info(f"CD-ROM partition: {self.cdrom_partition}")
            logger.info(f"USB partition: {self.usb_partition}")
            logger.info(f"Hardware tier: {self.hardware_info.tier.value if self.hardware_info else 'unknown'}")
            
        except Exception as e:
            logger.error(f"Configuration initialization error: {e}")
            # Continue with defaults
    
    def _detect_cdrom_partition(self) -> Optional[Path]:
        """
        Detect CD-ROM read-only partition
        FIX BUG-006: Corrected Windows path format
        
        Returns:
            Path to CD-ROM partition or None
        """
        marker_file = self.CDROM_MARKER
        
        if self.system == "Windows":
            # FIX: Use correct Windows path format with backslashes
            import string
            for drive_letter in string.ascii_uppercase:
                # Windows requires backslash separator
                drive_path = Path(f"{drive_letter}:\\")
                
                try:
                    if drive_path.exists():
                        marker_path = drive_path / marker_file
                        if marker_path.exists():
                            logger.info(f"CD-ROM partition detected: {drive_path}")
                            return drive_path
                except (PermissionError, OSError) as e:
                    # Some drives may not be accessible
                    logger.debug(f"Cannot access drive {drive_letter}: {e}")
                    continue
                    
        elif self.system == "Darwin":  # macOS
            # Check /Volumes for mounted disks
            volumes_path = Path("/Volumes")
            if volumes_path.exists():
                for volume in volumes_path.iterdir():
                    try:
                        if (volume / marker_file).exists():
                            logger.info(f"CD-ROM partition detected: {volume}")
                            return volume
                    except (PermissionError, OSError):
                        continue
                        
        else:  # Linux and other Unix-like systems
            # Check common mount points
            mount_points = ["/media", "/mnt", "/run/media"]
            for mount_dir in mount_points:
                mount_path = Path(mount_dir)
                if mount_path.exists():
                    # Check user subdirectories for modern Linux
                    if mount_dir == "/run/media":
                        user_dir = mount_path / os.environ.get('USER', '')
                        if user_dir.exists():
                            mount_path = user_dir
                    
                    for volume in mount_path.iterdir():
                        try:
                            if (volume / marker_file).exists():
                                logger.info(f"CD-ROM partition detected: {volume}")
                                return volume
                        except (PermissionError, OSError):
                            continue
        
        logger.warning("CD-ROM partition not detected - using development mode")
        return None
    
    def _detect_usb_partition(self) -> Optional[Path]:
        """
        Detect USB writable partition for user data
        FIX BUG-006: Corrected Windows path format
        
        Returns:
            Path to USB partition or None
        """
        marker_file = self.USB_MARKER
        
        if self.system == "Windows":
            # FIX: Use correct Windows path format with backslashes
            import string
            for drive_letter in string.ascii_uppercase:
                # Windows requires backslash separator
                drive_path = Path(f"{drive_letter}:\\")
                
                try:
                    if drive_path.exists():
                        marker_path = drive_path / marker_file
                        if marker_path.exists():
                            # Verify it's writable
                            test_file = drive_path / ".write_test"
                            try:
                                test_file.touch()
                                test_file.unlink()
                                logger.info(f"USB partition detected: {drive_path}")
                                return drive_path
                            except (PermissionError, OSError):
                                logger.warning(f"USB partition {drive_path} is not writable")
                                continue
                except (PermissionError, OSError) as e:
                    logger.debug(f"Cannot access drive {drive_letter}: {e}")
                    continue
                    
        elif self.system == "Darwin":  # macOS
            volumes_path = Path("/Volumes")
            if volumes_path.exists():
                for volume in volumes_path.iterdir():
                    try:
                        if (volume / marker_file).exists():
                            # Verify it's writable
                            test_file = volume / ".write_test"
                            try:
                                test_file.touch()
                                test_file.unlink()
                                logger.info(f"USB partition detected: {volume}")
                                return volume
                            except (PermissionError, OSError):
                                continue
                    except (PermissionError, OSError):
                        continue
                        
        else:  # Linux and other Unix-like systems
            mount_points = ["/media", "/mnt", "/run/media"]
            for mount_dir in mount_points:
                mount_path = Path(mount_dir)
                if mount_path.exists():
                    # Check user subdirectories for modern Linux
                    if mount_dir == "/run/media":
                        user_dir = mount_path / os.environ.get('USER', '')
                        if user_dir.exists():
                            mount_path = user_dir
                    
                    for volume in mount_path.iterdir():
                        try:
                            if (volume / marker_file).exists():
                                # Verify it's writable
                                test_file = volume / ".write_test"
                                try:
                                    test_file.touch()
                                    test_file.unlink()
                                    logger.info(f"USB partition detected: {volume}")
                                    return volume
                                except (PermissionError, OSError):
                                    continue
                        except (PermissionError, OSError):
                            continue
        
        logger.warning("USB partition not detected - using local storage")
        return None
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load environment configuration from default.env"""
        env_file = self.config_dir / "default.env"
        config = {}
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            # Parse value with proper type detection
                            parsed_value = self._parse_value(value)
                            config[key] = parsed_value
                            os.environ[key] = str(parsed_value)
        
        self.env_config = config
        return config
    
    def _parse_value(self, value: str) -> Any:
        """
        Parse configuration value to appropriate type
        FIX BUG-017: Proper type detection for version strings and other values
        
        Args:
            value: String value to parse
            
        Returns:
            Parsed value with appropriate type
        """
        if not value:
            return ""
        
        # Handle boolean values
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Handle None/null
        if value.lower() in ('none', 'null'):
            return None
        
        # FIX: Check for version string pattern BEFORE numeric parsing
        # Version patterns: X.Y.Z, X.Y.Z-suffix, X.Y.Z.W
        version_pattern = r'^\d+\.\d+(\.\d+)?(\.\d+)?(-[a-zA-Z0-9]+)?$'
        if re.match(version_pattern, value):
            return value  # Keep as string
        
        # Check for IP address pattern
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(:\d+)?$'
        if re.match(ip_pattern, value):
            return value  # Keep as string
        
        # Check for file paths (contain slashes or backslashes)
        if '/' in value or '\\' in value:
            return value  # Keep as string
        
        # Try numeric parsing
        try:
            # Check if it's a valid integer
            if '.' not in value and 'e' not in value.lower():
                return int(value)
        except ValueError:
            pass
        
        try:
            # Check if it's a valid float (single decimal point)
            if value.count('.') == 1 and 'e' not in value.lower():
                return float(value)
        except ValueError:
            pass
        
        try:
            # Check for scientific notation
            if 'e' in value.lower():
                return float(value)
        except ValueError:
            pass
        
        # Return as string if no other type matches
        return value
    
    def _load_version_info(self) -> Dict[str, Any]:
        """Load version information"""
        version_file = self.config_dir / "version.json"
        
        if version_file.exists():
            with open(version_file, 'r') as f:
                self.version_info = json.load(f)
        else:
            self.version_info = {
                'version': self.CONFIG_VERSION,
                'build': 'unknown',
                'date': datetime.now().isoformat()
            }
        
        return self.version_info
    
    def _load_family_config(self) -> Dict[str, Any]:
        """Load family settings configuration"""
        # System config from CD-ROM (read-only)
        system_config_file = self.config_dir / "family_settings.yaml"
        
        # User config from USB partition (writable)
        user_config_file = self.user_data_dir / "profiles" / "family_settings.yaml"
        
        # Load system defaults
        system_config = {}
        if system_config_file.exists():
            with open(system_config_file, 'r') as f:
                system_config = yaml.safe_load(f) or {}
        
        # Load or create user config
        user_config = {}
        if user_config_file.exists():
            with open(user_config_file, 'r') as f:
                user_config = yaml.safe_load(f) or {}
        else:
            # Create default user configuration
            user_config = {
                'family_id': self._generate_family_id(),
                'created': datetime.now().isoformat(),
                'profiles': [],
                'settings': {
                    'content_filtering': True,
                    'session_recording': True,
                    'age_verification': True,
                    'max_session_minutes': 60,
                    'require_parent_pin': True,
                    'auto_logout_minutes': 15
                }
            }
            
            # Save initial configuration
            user_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(user_config_file, 'w') as f:
                yaml.safe_dump(user_config, f, default_flow_style=False)
        
        # Merge configurations (user overrides system)
        config = {**system_config, **user_config}
        self.family_config = config
        return config
    
    def _load_model_mapping(self) -> Dict[str, Any]:
        """Load hardware to model mapping configuration"""
        mapping_file = self.config_dir / "model_mapping.yaml"
        
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                self.model_mapping = yaml.safe_load(f) or {}
        else:
            # Default mapping
            self.model_mapping = {
                'hardware_tiers': {
                    'high_end': {
                        'min_ram_gb': 16,
                        'min_vram_gb': 8,
                        'model': 'llama3.2:7b',
                        'context_size': 8192
                    },
                    'mid_range': {
                        'min_ram_gb': 8,
                        'min_vram_gb': 4,
                        'model': 'llama3.2:3b',
                        'context_size': 4096
                    },
                    'low_end': {
                        'min_ram_gb': 4,
                        'min_vram_gb': 0,
                        'model': 'llama3.2:1b',
                        'context_size': 2048
                    },
                    'minimum': {
                        'min_ram_gb': 2,
                        'min_vram_gb': 0,
                        'model': 'llama3.2:1b-q4_0',
                        'context_size': 1024
                    }
                }
            }
        
        return self.model_mapping
    
    def _detect_hardware(self) -> HardwareInfo:
        """
        Comprehensive hardware detection with error handling
        FIX BUG-010: Complete implementation with proper error handling
        
        Returns:
            HardwareInfo object with detected capabilities
        """
        # Default values for safe fallback
        hardware = HardwareInfo(
            ram_gb=4.0,
            cpu_cores=2,
            cpu_threads=4,
            cpu_freq_mhz=2000,
            gpu_available=False,
            gpu_vram_gb=0.0,
            platform=self.system,
            architecture=platform.machine(),
            tier=HardwareTier.MINIMUM
        )
        
        try:
            # RAM detection
            hardware.ram_gb = self._detect_ram()
            
            # CPU detection
            cpu_info = self._detect_cpu()
            hardware.cpu_cores = cpu_info['cores']
            hardware.cpu_threads = cpu_info['threads']
            hardware.cpu_freq_mhz = cpu_info['freq_mhz']
            
            # GPU detection
            gpu_info = self._detect_gpu()
            hardware.gpu_available = gpu_info['available']
            hardware.gpu_vram_gb = gpu_info['vram_gb']
            
            # Determine hardware tier
            hardware.tier = self._determine_tier(hardware)
            
        except Exception as e:
            logger.error(f"Hardware detection error: {e}")
            # Continue with defaults
        
        return hardware
    
    def _detect_ram(self) -> float:
        """Detect system RAM with error handling"""
        try:
            import psutil
            ram_bytes = psutil.virtual_memory().total
            ram_gb = ram_bytes / (1024**3)
            logger.info(f"Detected RAM: {ram_gb:.1f}GB")
            return ram_gb
        except ImportError:
            logger.warning("psutil not available, using fallback RAM detection")
            
            # Fallback methods
            if self.system == "Windows":
                try:
                    import wmi
                    c = wmi.WMI()
                    total_ram = 0
                    for mem in c.Win32_ComputerSystem():
                        total_ram = int(mem.TotalPhysicalMemory) / (1024**3)
                    return total_ram
                except:
                    pass
                    
            elif self.system == "Darwin":
                try:
                    result = subprocess.run(
                        ['sysctl', '-n', 'hw.memsize'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return int(result.stdout.strip()) / (1024**3)
                except:
                    pass
                    
            elif self.system == "Linux":
                try:
                    with open('/proc/meminfo', 'r') as f:
                        for line in f:
                            if line.startswith('MemTotal'):
                                kb = int(line.split()[1])
                                return kb / (1024**2)
                except:
                    pass
        except Exception as e:
            logger.error(f"RAM detection failed: {e}")
        
        logger.warning("Using default RAM value: 4GB")
        return 4.0
    
    def _detect_cpu(self) -> Dict[str, Any]:
        """Detect CPU information with error handling"""
        cpu_info = {
            'cores': 2,
            'threads': 4,
            'freq_mhz': 2000
        }
        
        try:
            import psutil
            
            # Physical cores
            cpu_info['cores'] = psutil.cpu_count(logical=False) or 2
            
            # Logical cores (threads)
            cpu_info['threads'] = psutil.cpu_count(logical=True) or 4
            
            # CPU frequency
            freq = psutil.cpu_freq()
            if freq:
                cpu_info['freq_mhz'] = freq.current
                
            logger.info(f"Detected CPU: {cpu_info['cores']} cores, {cpu_info['threads']} threads, {cpu_info['freq_mhz']:.0f}MHz")
            
        except ImportError:
            logger.warning("psutil not available, using fallback CPU detection")
            
            # Platform-specific fallbacks
            if self.system == "Windows":
                try:
                    import wmi
                    c = wmi.WMI()
                    for proc in c.Win32_Processor():
                        cpu_info['cores'] = proc.NumberOfCores or 2
                        cpu_info['threads'] = proc.NumberOfLogicalProcessors or 4
                        cpu_info['freq_mhz'] = proc.MaxClockSpeed or 2000
                except:
                    pass
                    
            elif self.system == "Darwin":
                try:
                    # Physical cores
                    result = subprocess.run(
                        ['sysctl', '-n', 'hw.physicalcpu'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        cpu_info['cores'] = int(result.stdout.strip())
                    
                    # Logical cores
                    result = subprocess.run(
                        ['sysctl', '-n', 'hw.logicalcpu'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        cpu_info['threads'] = int(result.stdout.strip())
                except:
                    pass
                    
            elif self.system == "Linux":
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        cores = set()
                        threads = 0
                        for line in f:
                            if line.startswith('physical id'):
                                cores.add(line.split(':')[1].strip())
                            elif line.startswith('processor'):
                                threads += 1
                            elif line.startswith('cpu MHz'):
                                freq = float(line.split(':')[1].strip())
                                cpu_info['freq_mhz'] = freq
                        
                        cpu_info['cores'] = len(cores) if cores else 2
                        cpu_info['threads'] = threads if threads else 4
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"CPU detection failed: {e}")
        
        return cpu_info
    
    def _detect_gpu(self) -> Dict[str, Any]:
        """
        Detect GPU and VRAM with complete error handling
        FIX BUG-010: Complete implementation for all platforms
        
        Returns:
            Dictionary with GPU information
        """
        gpu_info = {
            'available': False,
            'vram_gb': 0.0,
            'name': 'None',
            'driver': 'None'
        }
        
        try:
            if self.system == "Windows":
                gpu_info = self._detect_gpu_windows()
                
            elif self.system == "Darwin":
                gpu_info = self._detect_gpu_macos()
                
            elif self.system == "Linux":
                gpu_info = self._detect_gpu_linux()
                
            logger.info(f"GPU detected: {gpu_info['name']}, VRAM: {gpu_info['vram_gb']:.1f}GB")
            
        except Exception as e:
            logger.warning(f"GPU detection failed: {e}")
        
        return gpu_info
    
    def _detect_gpu_windows(self) -> Dict[str, Any]:
        """Windows-specific GPU detection"""
        gpu_info = {
            'available': False,
            'vram_gb': 0.0,
            'name': 'None',
            'driver': 'None'
        }
        
        try:
            import wmi
            c = wmi.WMI()
            
            for gpu in c.Win32_VideoController():
                if gpu.AdapterRAM and gpu.AdapterRAM > 0:
                    gpu_info['available'] = True
                    gpu_info['vram_gb'] = gpu.AdapterRAM / (1024**3)
                    gpu_info['name'] = gpu.Name or 'Unknown GPU'
                    gpu_info['driver'] = gpu.DriverVersion or 'Unknown'
                    
                    # Stop at first discrete GPU
                    if 'NVIDIA' in gpu.Name or 'AMD' in gpu.Name or 'Radeon' in gpu.Name:
                        break
                        
        except ImportError:
            logger.debug("WMI not available for Windows GPU detection")
        except Exception as e:
            logger.debug(f"Windows GPU detection error: {e}")
            
            # Try DirectX fallback
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name,AdapterRAM'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            parts = line.split()
                            if len(parts) > 1 and parts[0].isdigit():
                                gpu_info['available'] = True
                                gpu_info['vram_gb'] = int(parts[0]) / (1024**3)
                                gpu_info['name'] = ' '.join(parts[1:])
                                break
            except:
                pass
        
        return gpu_info
    
    def _detect_gpu_macos(self) -> Dict[str, Any]:
        """macOS-specific GPU detection"""
        gpu_info = {
            'available': False,
            'vram_gb': 0.0,
            'name': 'None',
            'driver': 'Metal'
        }
        
        try:
            # Use system_profiler for GPU detection
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                for item in data.get('SPDisplaysDataType', []):
                    # Check for discrete GPU first
                    if 'spdisplays_discrete' in item:
                        gpu_info['available'] = True
                        gpu_info['name'] = item.get('sppci_model', 'Unknown GPU')
                        
                        # Parse VRAM
                        vram_str = item.get('spdisplays_vram', '0')
                        if 'GB' in vram_str:
                            gpu_info['vram_gb'] = float(vram_str.replace('GB', '').strip())
                        elif 'MB' in vram_str:
                            gpu_info['vram_gb'] = float(vram_str.replace('MB', '').strip()) / 1024
                        
                        break
                    
                    # Apple Silicon unified memory
                    elif 'apple_m' in item.get('sppci_model', '').lower():
                        gpu_info['available'] = True
                        gpu_info['name'] = item.get('sppci_model', 'Apple Silicon')
                        
                        # For Apple Silicon, use a portion of system RAM as "VRAM"
                        system_ram = self._detect_ram()
                        # Assume up to 75% can be used for GPU on Apple Silicon
                        gpu_info['vram_gb'] = system_ram * 0.75
                        gpu_info['driver'] = 'Metal (Unified Memory)'
                        break
                        
        except subprocess.TimeoutExpired:
            logger.debug("system_profiler timeout on macOS")
        except Exception as e:
            logger.debug(f"macOS GPU detection error: {e}")
        
        return gpu_info
    
    def _detect_gpu_linux(self) -> Dict[str, Any]:
        """Linux-specific GPU detection"""
        gpu_info = {
            'available': False,
            'vram_gb': 0.0,
            'name': 'None',
            'driver': 'None'
        }
        
        # Try NVIDIA first
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                if len(parts) >= 2:
                    gpu_info['available'] = True
                    gpu_info['name'] = parts[0].strip()
                    
                    # Parse VRAM (comes in MB)
                    vram_str = parts[1].strip()
                    if 'MiB' in vram_str:
                        vram_mb = float(vram_str.replace('MiB', '').strip())
                        gpu_info['vram_gb'] = vram_mb / 1024
                    
                    if len(parts) >= 3:
                        gpu_info['driver'] = parts[2].strip()
                    
                    return gpu_info
                    
        except FileNotFoundError:
            logger.debug("nvidia-smi not found")
        except Exception as e:
            logger.debug(f"NVIDIA detection error: {e}")
        
        # Try AMD ROCm
        try:
            result = subprocess.run(
                ['rocm-smi', '--showmeminfo', 'vram'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse ROCm output
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'VRAM Total' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            vram_str = parts[1].strip()
                            if 'MB' in vram_str:
                                vram_mb = float(vram_str.replace('MB', '').strip())
                                gpu_info['vram_gb'] = vram_mb / 1024
                                gpu_info['available'] = True
                                gpu_info['name'] = 'AMD GPU'
                                gpu_info['driver'] = 'ROCm'
                                return gpu_info
                                
        except FileNotFoundError:
            logger.debug("rocm-smi not found")
        except Exception as e:
            logger.debug(f"AMD ROCm detection error: {e}")
        
        # Try lspci as fallback
        try:
            result = subprocess.run(
                ['lspci', '-v'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    if 'VGA compatible controller' in line or 'Display controller' in line:
                        gpu_info['available'] = True
                        
                        # Extract GPU name
                        parts = line.split(': ')
                        if len(parts) >= 2:
                            gpu_info['name'] = parts[1].strip()
                        
                        # Look for memory in next few lines
                        for j in range(i+1, min(i+10, len(lines))):
                            if 'Memory' in lines[j] and 'prefetchable' in lines[j]:
                                # Try to parse memory size
                                import re
                                match = re.search(r'\[size=(\d+)([MG])\]', lines[j])
                                if match:
                                    size = int(match.group(1))
                                    unit = match.group(2)
                                    if unit == 'G':
                                        gpu_info['vram_gb'] = float(size)
                                    elif unit == 'M':
                                        gpu_info['vram_gb'] = size / 1024
                                    break
                        break
                        
        except FileNotFoundError:
            logger.debug("lspci not found")
        except Exception as e:
            logger.debug(f"lspci detection error: {e}")
        
        return gpu_info
    
    def _determine_tier(self, hardware: HardwareInfo) -> HardwareTier:
        """Determine hardware tier based on capabilities"""
        # Check tiers from highest to lowest
        for tier_name, tier_config in self.model_mapping.get('hardware_tiers', {}).items():
            min_ram = tier_config.get('min_ram_gb', 0)
            min_vram = tier_config.get('min_vram_gb', 0)
            
            # Check if hardware meets tier requirements
            if hardware.ram_gb >= min_ram:
                if min_vram > 0:
                    # GPU required for this tier
                    if hardware.gpu_vram_gb >= min_vram:
                        return HardwareTier(tier_name)
                else:
                    # No GPU required
                    return HardwareTier(tier_name)
        
        # Default to minimum tier
        return HardwareTier.MINIMUM
    
    def _generate_family_id(self) -> str:
        """Generate unique family ID"""
        import uuid
        return str(uuid.uuid4())
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key
        Supports nested keys with dot notation (e.g., 'family.settings.max_session_minutes')
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check environment config first
        if key in self.env_config:
            return self.env_config[key]
        
        # Check for nested keys
        if '.' in key:
            parts = key.split('.')
            config = None
            
            # Determine which config to search
            if parts[0] == 'family':
                config = self.family_config
                parts = parts[1:]
            elif parts[0] == 'model':
                config = self.model_mapping
                parts = parts[1:]
            elif parts[0] == 'version':
                config = self.version_info
                parts = parts[1:]
            elif parts[0] == 'hardware':
                if self.hardware_info:
                    config = self.hardware_info.to_dict()
                    parts = parts[1:]
            
            if config:
                value = config
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return default
                return value
        
        return default
    
    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Value to set
            persist: Whether to persist to disk (only for user data)
        """
        # Update in-memory config
        self.env_config[key] = value
        os.environ[key] = str(value)
        
        if persist and key.startswith('family.'):
            # Update family configuration on USB partition
            self._save_family_config()
    
    def _save_family_config(self) -> None:
        """Save family configuration to USB partition"""
        config_file = self.user_data_dir / "profiles" / "family_settings.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.safe_dump(self.family_config, f, default_flow_style=False)
        
        logger.info("Family configuration saved")
    
    def get_optimal_model(self) -> str:
        """
        Get optimal model based on detected hardware
        
        Returns:
            Model identifier string
        """
        if not self.hardware_info:
            return 'llama3.2:1b-q4_0'  # Safe default
        
        tier_name = self.hardware_info.tier.value
        tier_config = self.model_mapping.get('hardware_tiers', {}).get(tier_name, {})
        
        return tier_config.get('model', 'llama3.2:1b-q4_0')
    
    def get_hardware_info(self) -> Optional[HardwareInfo]:
        """Get detected hardware information"""
        return self.hardware_info
    
    def export_config(self, output_file: Optional[Path] = None) -> Path:
        """
        Export complete configuration for backup
        
        Args:
            output_file: Output file path (optional)
            
        Returns:
            Path to exported configuration file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.user_data_dir / f"config_backup_{timestamp}.json"
        
        export_data = {
            'version': self.CONFIG_VERSION,
            'export_date': datetime.now().isoformat(),
            'system': self.system,
            'partitions': {
                'cdrom': str(self.cdrom_partition) if self.cdrom_partition else None,
                'usb': str(self.usb_partition) if self.usb_partition else None
            },
            'environment': self.env_config,
            'family': self.family_config,
            'model_mapping': self.model_mapping,
            'hardware': self.hardware_info.to_dict() if self.hardware_info else None
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Configuration exported to {output_file}")
        return output_file


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass


# Singleton instance
_config_instance: Optional[ConfigurationManager] = None


def get_config() -> ConfigurationManager:
    """
    Get singleton configuration manager instance
    
    Returns:
        ConfigurationManager instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigurationManager()
    return _config_instance


def reset_config() -> None:
    """Reset configuration manager (mainly for testing)"""
    global _config_instance
    _config_instance = None


# Module exports
__all__ = [
    'ConfigurationManager',
    'ConfigurationError',
    'HardwareInfo',
    'HardwareTier',
    'get_config',
    'reset_config'
]

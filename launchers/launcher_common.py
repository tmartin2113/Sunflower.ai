#!/usr/bin/env python3
"""
Sunflower AI Professional System - Common Launcher Module
Shared functionality for Windows and macOS launchers with fallback detection
Version: 6.2.0 - Production Ready with Fixed Platform Detection
"""

import os
import sys
import platform
import subprocess
import json
import time
import socket
import hashlib
import sqlite3
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import webbrowser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SunflowerLauncher')


@dataclass
class SystemConfig:
    """System configuration data"""
    platform: str
    cdrom_path: Path
    usb_path: Path
    model_variant: str
    hardware_tier: str
    ram_gb: float
    cpu_cores: int
    ollama_port: int = 11434
    webui_port: int = 8080


class PartitionDetector:
    """Detect and validate partitioned device with fallback methods"""
    
    def __init__(self):
        self.platform = platform.system()
        self.cdrom_path = None
        self.usb_path = None
        
        # FIX: Track whether platform-specific modules are available
        self.windows_modules_available = False
        self.macos_modules_available = False
        
        # Check for platform-specific module availability
        self._check_platform_modules()
    
    def _check_platform_modules(self):
        """Check which platform-specific modules are available"""
        if self.platform == "Windows":
            try:
                import win32api
                import win32file
                self.windows_modules_available = True
                logger.info("Windows modules (pywin32) available")
            except ImportError:
                self.windows_modules_available = False
                logger.warning("Windows modules (pywin32) not available - using fallback detection")
        
        elif self.platform == "Darwin":
            try:
                import plistlib
                self.macos_modules_available = True
                logger.info("macOS modules available")
            except ImportError:
                self.macos_modules_available = False
                logger.warning("macOS modules not available - using fallback detection")
    
    def detect_partitions(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect CD-ROM and USB partitions with fallback support"""
        if self.platform == "Windows":
            return self._detect_windows()
        elif self.platform == "Darwin":
            return self._detect_macos()
        else:
            return self._detect_linux()
    
    def _detect_windows(self) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Detect partitions on Windows with fallback methods
        FIX: Handle missing pywin32 gracefully
        """
        # Try using win32 modules if available
        if self.windows_modules_available:
            return self._detect_windows_win32()
        else:
            # Use fallback detection method
            return self._detect_windows_fallback()
    
    def _detect_windows_win32(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect Windows partitions using pywin32 (if available)"""
        try:
            # FIX: Import only when we know they're available
            import win32api
            import win32file
            
            cdrom_path = None
            usb_path = None
            
            drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
            
            for drive in drives:
                try:
                    drive_type = win32file.GetDriveType(drive)
                    
                    # Check for CD-ROM partition marker
                    cd_marker = Path(drive) / "sunflower_cd.id"
                    if cd_marker.exists():
                        cdrom_path = Path(drive)
                        logger.info(f"Found CD-ROM partition: {cdrom_path}")
                    
                    # Check for USB data partition marker
                    data_marker = Path(drive) / "sunflower_data.id"
                    if data_marker.exists():
                        usb_path = Path(drive)
                        logger.info(f"Found USB partition: {usb_path}")
                        
                except Exception as e:
                    logger.debug(f"Error checking drive {drive}: {e}")
                    continue
            
            return cdrom_path, usb_path
            
        except Exception as e:
            logger.error(f"Error in Windows partition detection: {e}")
            # Fall back to alternative method
            return self._detect_windows_fallback()
    
    def _detect_windows_fallback(self) -> Tuple[Optional[Path], Optional[Path]]:
        """
        FIX: Fallback Windows partition detection without pywin32
        Uses native Windows commands and Python stdlib only
        """
        cdrom_path = None
        usb_path = None
        
        logger.info("Using fallback Windows partition detection")
        
        # Method 1: Try using wmic command (Windows Management Instrumentation)
        try:
            # Get all logical drives using wmic
            result = subprocess.run(
                ['wmic', 'logicaldisk', 'get', 'name,size,description'],
                capture_output=True,
                text=True,
                shell=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if parts:
                            drive = parts[-1]  # Drive letter is usually last
                            if ':' in drive:
                                drive_path = Path(f"{drive}\\")
                                if drive_path.exists():
                                    # Check for marker files
                                    cd_marker = drive_path / "sunflower_cd.id"
                                    data_marker = drive_path / "sunflower_data.id"
                                    
                                    if cd_marker.exists():
                                        cdrom_path = drive_path
                                        logger.info(f"Found CD-ROM partition via wmic: {cdrom_path}")
                                    
                                    if data_marker.exists():
                                        usb_path = drive_path
                                        logger.info(f"Found USB partition via wmic: {usb_path}")
        except Exception as e:
            logger.debug(f"wmic method failed: {e}")
        
        # Method 2: Iterate through drive letters A-Z
        if not cdrom_path or not usb_path:
            import string
            logger.info("Scanning drive letters directly")
            
            for letter in string.ascii_uppercase:
                drive_path = Path(f"{letter}:\\")
                
                # Check if drive exists and is accessible
                if drive_path.exists():
                    try:
                        # Try to list the directory (will fail if not accessible)
                        _ = list(drive_path.iterdir())
                        
                        # Check for marker files
                        cd_marker = drive_path / "sunflower_cd.id"
                        data_marker = drive_path / "sunflower_data.id"
                        
                        if not cdrom_path and cd_marker.exists():
                            cdrom_path = drive_path
                            logger.info(f"Found CD-ROM partition: {cdrom_path}")
                        
                        if not usb_path and data_marker.exists():
                            usb_path = drive_path
                            logger.info(f"Found USB partition: {usb_path}")
                            
                    except (PermissionError, OSError) as e:
                        # Drive exists but not accessible, skip it
                        logger.debug(f"Cannot access drive {letter}: {e}")
                        continue
        
        # Method 3: Check common USB drive letters if still not found
        if not usb_path:
            common_usb_letters = ['E', 'F', 'G', 'H', 'D']
            for letter in common_usb_letters:
                drive_path = Path(f"{letter}:\\")
                if drive_path.exists():
                    try:
                        data_marker = drive_path / "sunflower_data.id"
                        if data_marker.exists():
                            usb_path = drive_path
                            logger.info(f"Found USB partition at common location: {usb_path}")
                            break
                    except:
                        continue
        
        # Method 4: Use PowerShell as last resort
        if not cdrom_path or not usb_path:
            try:
                ps_command = "Get-PSDrive -PSProvider FileSystem | Select-Object Name, Root"
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[2:]:  # Skip headers
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 2:
                                drive = parts[1]
                                if ':\\' in drive:
                                    drive_path = Path(drive)
                                    if drive_path.exists():
                                        cd_marker = drive_path / "sunflower_cd.id"
                                        data_marker = drive_path / "sunflower_data.id"
                                        
                                        if not cdrom_path and cd_marker.exists():
                                            cdrom_path = drive_path
                                            logger.info(f"Found CD-ROM via PowerShell: {cdrom_path}")
                                        
                                        if not usb_path and data_marker.exists():
                                            usb_path = drive_path
                                            logger.info(f"Found USB via PowerShell: {usb_path}")
            except Exception as e:
                logger.debug(f"PowerShell method failed: {e}")
        
        return cdrom_path, usb_path
    
    def _detect_macos(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect partitions on macOS with fallback support"""
        cdrom_path = None
        usb_path = None
        
        # Primary method: Check /Volumes
        volumes_path = Path("/Volumes")
        
        if volumes_path.exists():
            for volume in volumes_path.iterdir():
                if volume.is_dir():
                    # Check for partition markers
                    cd_marker = volume / "sunflower_cd.id"
                    data_marker = volume / "sunflower_data.id"
                    
                    if cd_marker.exists():
                        cdrom_path = volume
                        logger.info(f"Found CD-ROM partition: {cdrom_path}")
                    
                    if data_marker.exists():
                        usb_path = volume
                        logger.info(f"Found USB partition: {usb_path}")
        
        # Fallback method: Use diskutil command
        if not cdrom_path or not usb_path:
            try:
                result = subprocess.run(
                    ['diskutil', 'list'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    # Parse diskutil output to find volumes
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'SUNFLOWER' in line.upper():
                            # Extract volume name and check
                            parts = line.split()
                            for part in parts:
                                if 'SUNFLOWER' in part.upper():
                                    volume_path = Path("/Volumes") / part
                                    if volume_path.exists():
                                        cd_marker = volume_path / "sunflower_cd.id"
                                        data_marker = volume_path / "sunflower_data.id"
                                        
                                        if cd_marker.exists():
                                            cdrom_path = volume_path
                                        if data_marker.exists():
                                            usb_path = volume_path
            except Exception as e:
                logger.debug(f"diskutil method failed: {e}")
        
        return cdrom_path, usb_path
    
    def _detect_linux(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Detect partitions on Linux with multiple fallback methods"""
        cdrom_path = None
        usb_path = None
        
        # Check common mount points
        mount_points = [
            Path("/media"),
            Path("/mnt"),
            Path("/run/media") / os.environ.get("USER", ""),
            Path(f"/media/{os.environ.get('USER', '')}"),
            Path("/Volumes")  # Some Linux distros use this
        ]
        
        for mount_base in mount_points:
            if not mount_base.exists():
                continue
            
            try:
                for mount in mount_base.iterdir():
                    if mount.is_dir():
                        cd_marker = mount / "sunflower_cd.id"
                        data_marker = mount / "sunflower_data.id"
                        
                        if cd_marker.exists():
                            cdrom_path = mount
                            logger.info(f"Found CD-ROM partition: {cdrom_path}")
                        
                        if data_marker.exists():
                            usb_path = mount
                            logger.info(f"Found USB partition: {usb_path}")
            except PermissionError:
                continue
        
        # Fallback: Use lsblk command
        if not cdrom_path or not usb_path:
            try:
                result = subprocess.run(
                    ['lsblk', '-o', 'NAME,MOUNTPOINT,LABEL', '-n'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'SUNFLOWER' in line.upper():
                            parts = line.split()
                            if len(parts) >= 2:
                                mount_point = parts[1]
                                if mount_point and mount_point != '':
                                    mount_path = Path(mount_point)
                                    if mount_path.exists():
                                        cd_marker = mount_path / "sunflower_cd.id"
                                        data_marker = mount_path / "sunflower_data.id"
                                        
                                        if cd_marker.exists():
                                            cdrom_path = mount_path
                                        if data_marker.exists():
                                            usb_path = mount_path
            except Exception as e:
                logger.debug(f"lsblk method failed: {e}")
        
        return cdrom_path, usb_path


class HardwareDetector:
    """Detect hardware capabilities for model selection"""
    
    def __init__(self):
        self.platform = platform.system()
        self.cpu_count = os.cpu_count() or 2
        self.ram_gb = self._detect_ram()
        self.gpu_available = self._detect_gpu()
        
    def _detect_ram(self) -> float:
        """Detect system RAM with fallback methods"""
        # Try using psutil if available
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            logger.warning("psutil not available for RAM detection")
        
        # Platform-specific fallbacks
        if self.platform == "Windows":
            return self._detect_ram_windows()
        elif self.platform == "Darwin":
            return self._detect_ram_macos()
        else:
            return self._detect_ram_linux()
    
    def _detect_ram_windows(self) -> float:
        """Detect RAM on Windows using fallback methods"""
        # FIX: Try multiple methods to get RAM info
        
        # Method 1: Try WMI through wmic command
        try:
            result = subprocess.run(
                ['wmic', 'computersystem', 'get', 'TotalPhysicalMemory'],
                capture_output=True,
                text=True,
                shell=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        try:
                            bytes_ram = int(line.strip())
                            return bytes_ram / (1024**3)
                        except ValueError:
                            continue
        except Exception as e:
            logger.debug(f"wmic RAM detection failed: {e}")
        
        # Method 2: Try PowerShell
        try:
            ps_command = "(Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory"
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                try:
                    bytes_ram = int(result.stdout.strip())
                    return bytes_ram / (1024**3)
                except ValueError:
                    pass
        except Exception as e:
            logger.debug(f"PowerShell RAM detection failed: {e}")
        
        # Method 3: Try using ctypes
        try:
            import ctypes
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            
            memstat = MEMORYSTATUSEX()
            memstat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memstat))
            return memstat.ullTotalPhys / (1024**3)
            
        except Exception as e:
            logger.debug(f"ctypes RAM detection failed: {e}")
        
        # Default fallback
        logger.warning("Could not detect RAM, assuming 4GB")
        return 4.0
    
    def _detect_ram_macos(self) -> float:
        """Detect RAM on macOS"""
        try:
            result = subprocess.run(
                ['sysctl', 'hw.memsize'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse output: hw.memsize: 17179869184
                parts = result.stdout.strip().split(':')
                if len(parts) == 2:
                    bytes_ram = int(parts[1].strip())
                    return bytes_ram / (1024**3)
        except Exception as e:
            logger.debug(f"sysctl RAM detection failed: {e}")
        
        # Default fallback
        logger.warning("Could not detect RAM, assuming 8GB")
        return 8.0
    
    def _detect_ram_linux(self) -> float:
        """Detect RAM on Linux"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        parts = line.split()
                        kb_ram = int(parts[1])
                        return kb_ram / (1024**2)  # Convert KB to GB
        except Exception as e:
            logger.debug(f"/proc/meminfo RAM detection failed: {e}")
        
        # Try free command
        try:
            result = subprocess.run(
                ['free', '-b'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.startswith('Mem:'):
                        parts = line.split()
                        bytes_ram = int(parts[1])
                        return bytes_ram / (1024**3)
        except Exception as e:
            logger.debug(f"free command RAM detection failed: {e}")
        
        # Default fallback
        logger.warning("Could not detect RAM, assuming 4GB")
        return 4.0
    
    def _detect_gpu(self) -> bool:
        """Detect if GPU is available"""
        # This is a simplified check
        # In production, would check for CUDA/ROCm/Metal
        
        if self.platform == "Darwin":
            # macOS with Apple Silicon always has GPU acceleration
            try:
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if 'Apple' in result.stdout:
                    return True
            except:
                pass
        
        # Check for NVIDIA GPU on Windows/Linux
        try:
            result = subprocess.run(
                ['nvidia-smi'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            pass
        
        return False
    
    def get_optimal_model(self) -> str:
        """Determine optimal model based on hardware"""
        if self.ram_gb >= 16:
            return "llama3.2:7b"
        elif self.ram_gb >= 8:
            return "llama3.2:3b"
        elif self.ram_gb >= 4:
            return "llama3.2:1b"
        else:
            return "llama3.2:1b-q4_0"
    
    def get_hardware_tier(self) -> str:
        """Classify hardware tier"""
        if self.ram_gb >= 16 and self.cpu_count >= 8:
            return "high"
        elif self.ram_gb >= 8 and self.cpu_count >= 4:
            return "medium"
        else:
            return "low"


class ServiceManager:
    """Manage Ollama and Open WebUI services"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        self.cdrom_path = cdrom_path
        self.usb_path = usb_path
        self.platform = platform.system()
        self.ollama_process = None
        self.webui_process = None
        
    def start_ollama(self) -> bool:
        """Start Ollama service"""
        ollama_binary = self._get_ollama_binary()
        
        if not ollama_binary or not ollama_binary.exists():
            logger.error(f"Ollama binary not found at {ollama_binary}")
            return False
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env['OLLAMA_MODELS'] = str(self.usb_path / 'ollama' / 'models')
            env['OLLAMA_HOST'] = '0.0.0.0:11434'
            
            # Start Ollama
            self.ollama_process = subprocess.Popen(
                [str(ollama_binary), 'serve'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for Ollama to start
            time.sleep(3)
            
            # Check if running
            if self.check_ollama_running():
                logger.info("Ollama service started successfully")
                return True
            else:
                logger.error("Ollama service failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False
    
    def _get_ollama_binary(self) -> Optional[Path]:
        """Get path to Ollama binary"""
        if self.platform == "Windows":
            return self.cdrom_path / 'ollama' / 'ollama.exe'
        elif self.platform == "Darwin":
            return self.cdrom_path / 'ollama' / 'ollama'
        else:
            return self.cdrom_path / 'ollama' / 'ollama'
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama service is running"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 11434))
            sock.close()
            return result == 0
        except:
            return False
    
    def stop_services(self):
        """Stop all services"""
        if self.ollama_process:
            try:
                self.ollama_process.terminate()
                self.ollama_process.wait(timeout=5)
            except:
                self.ollama_process.kill()
            self.ollama_process = None
        
        if self.webui_process:
            try:
                self.webui_process.terminate()
                self.webui_process.wait(timeout=5)
            except:
                self.webui_process.kill()
            self.webui_process = None


# Utility functions for launchers
def setup_logging(log_file: Optional[Path] = None) -> logging.Logger:
    """Set up logging configuration"""
    logger = logging.getLogger('SunflowerLauncher')
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def main():
    """Main entry point for testing launcher functionality"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sunflower AI Launcher')
    parser.add_argument('--cdrom-path', type=Path, help='CD-ROM partition path')
    parser.add_argument('--usb-path', type=Path, help='USB partition path')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Detect partitions
    detector = PartitionDetector()
    cdrom_path, usb_path = detector.detect_partitions()
    
    if not cdrom_path or not usb_path:
        print("\n⚠️  Partition Detection Results:")
        print(f"CD-ROM: {cdrom_path or 'NOT FOUND'}")
        print(f"USB: {usb_path or 'NOT FOUND'}")
        
        if not cdrom_path:
            print("\n❌ CD-ROM partition not found!")
            print("Please ensure the Sunflower AI device is properly connected.")
        if not usb_path:
            print("\n❌ USB partition not found!")
            print("The USB partition may need to be initialized.")
    else:
        print("\n✅ Partition Detection Successful!")
        print(f"CD-ROM: {cdrom_path}")
        print(f"USB: {usb_path}")
        
        # Detect hardware
        hw = HardwareDetector()
        print("\n💻 Hardware Detection:")
        print(f"Platform: {hw.platform}")
        print(f"CPU Cores: {hw.cpu_count}")
        print(f"RAM: {hw.ram_gb:.1f} GB")
        print(f"GPU Available: {hw.gpu_available}")
        print(f"Optimal Model: {hw.get_optimal_model()}")
        print(f"Hardware Tier: {hw.get_hardware_tier()}")


if __name__ == "__main__":
    main()

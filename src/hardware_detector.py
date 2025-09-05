#!/usr/bin/env python3
"""
Sunflower AI Professional System - Hardware Detector
Version: 6.2
Copyright (c) 2025 Sunflower AI

Detects system hardware capabilities and automatically selects the optimal
AI model variant for best performance. Handles both Windows and macOS with
graceful fallbacks for unsupported platforms.
"""

import os
import sys
import json
import platform
import subprocess
import psutil
import logging
import multiprocessing
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re
import shutil
import threading
import time

logger = logging.getLogger(__name__)


class HardwareTier(Enum):
    """Hardware performance tiers"""
    ULTRA = "ultra"      # 16GB+ RAM, 8+ cores, dedicated GPU
    HIGH = "high"        # 8-16GB RAM, 4-8 cores, possible GPU
    STANDARD = "standard"  # 4-8GB RAM, 2-4 cores, no GPU
    MINIMUM = "minimum"   # 4GB RAM, 2 cores, no GPU


class GPUVendor(Enum):
    """GPU vendors"""
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    APPLE = "apple"
    UNKNOWN = "unknown"


@dataclass
class CPUInfo:
    """CPU information"""
    name: str
    vendor: str
    cores: int
    threads: int
    frequency_mhz: int
    architecture: str
    features: List[str]
    cache_mb: Optional[float] = None
    temperature_c: Optional[float] = None
    usage_percent: Optional[float] = None


@dataclass
class MemoryInfo:
    """Memory information"""
    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float
    swap_total_gb: float
    swap_used_gb: float
    swap_percent_used: float


@dataclass
class GPUInfo:
    """GPU information"""
    available: bool
    vendor: str
    name: str
    memory_gb: float
    cuda_available: bool
    metal_available: bool
    compute_capability: Optional[str] = None
    driver_version: Optional[str] = None
    temperature_c: Optional[float] = None
    usage_percent: Optional[float] = None


@dataclass
class StorageInfo:
    """Storage information"""
    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float
    mount_point: str
    filesystem: str
    is_ssd: bool
    read_speed_mbps: Optional[float] = None
    write_speed_mbps: Optional[float] = None


@dataclass
class SystemInfo:
    """Complete system information"""
    platform: str
    platform_version: str
    architecture: str
    hostname: str
    cpu: CPUInfo
    memory: MemoryInfo
    gpu: GPUInfo
    storage: StorageInfo
    tier: str
    optimal_model: str
    capabilities: Dict[str, bool]
    performance_score: int


class HardwareDetector:
    """
    Comprehensive hardware detection and optimization system.
    Automatically profiles system capabilities and selects optimal AI model.
    """
    
    # Model requirements (RAM in GB)
    MODEL_REQUIREMENTS = {
        "llama3.2:7b": {"min_ram": 8, "recommended_ram": 16, "min_cores": 4},
        "llama3.2:3b": {"min_ram": 4, "recommended_ram": 8, "min_cores": 2},
        "llama3.2:1b": {"min_ram": 2, "recommended_ram": 4, "min_cores": 2},
        "llama3.2:1b-q4_0": {"min_ram": 2, "recommended_ram": 4, "min_cores": 1}
    }
    
    def __init__(self):
        """Initialize hardware detector"""
        self.platform_name = platform.system()
        self.platform_version = platform.version()
        self.architecture = platform.machine()
        
        # Cache for expensive operations
        self._cpu_info_cache: Optional[CPUInfo] = None
        self._gpu_info_cache: Optional[GPUInfo] = None
        self._system_info_cache: Optional[SystemInfo] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_duration = 300  # 5 minutes
        
        # Thread safety
        self._cache_lock = threading.Lock()
        
        logger.info(f"Hardware detector initialized on {self.platform_name} {self.architecture}")
    
    def get_system_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get complete system information.
        
        Args:
            force_refresh: Force refresh of cached data
        
        Returns:
            Dictionary containing all system information
        """
        with self._cache_lock:
            # Check cache validity
            if not force_refresh and self._system_info_cache:
                if self._cache_timestamp and (time.time() - self._cache_timestamp) < self._cache_duration:
                    return asdict(self._system_info_cache)
            
            # Gather system information
            logger.info("Detecting hardware capabilities...")
            
            cpu_info = self._detect_cpu()
            memory_info = self._detect_memory()
            gpu_info = self._detect_gpu()
            storage_info = self._detect_storage()
            
            # Determine hardware tier
            tier = self._determine_tier(cpu_info, memory_info, gpu_info)
            
            # Select optimal model
            optimal_model = self._select_optimal_model(tier, memory_info)
            
            # Determine capabilities
            capabilities = self._determine_capabilities(cpu_info, memory_info, gpu_info)
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(cpu_info, memory_info, gpu_info)
            
            # Create system info
            self._system_info_cache = SystemInfo(
                platform=self.platform_name,
                platform_version=self.platform_version,
                architecture=self.architecture,
                hostname=platform.node(),
                cpu=cpu_info,
                memory=memory_info,
                gpu=gpu_info,
                storage=storage_info,
                tier=tier.value,
                optimal_model=optimal_model,
                capabilities=capabilities,
                performance_score=performance_score
            )
            
            self._cache_timestamp = time.time()
            
            logger.info(f"System profile: {tier.value} tier, optimal model: {optimal_model}")
            
            return asdict(self._system_info_cache)
    
    def _detect_cpu(self) -> CPUInfo:
        """Detect CPU information"""
        if self._cpu_info_cache:
            return self._cpu_info_cache
        
        try:
            # Get basic CPU info
            cores = psutil.cpu_count(logical=False) or 1
            threads = psutil.cpu_count(logical=True) or cores
            
            # Get CPU frequency
            freq = psutil.cpu_freq()
            frequency_mhz = int(freq.current) if freq else 0
            
            # Get CPU name and vendor
            name, vendor = self._get_cpu_name_vendor()
            
            # Detect CPU features
            features = self._detect_cpu_features()
            
            # Get CPU usage
            usage_percent = psutil.cpu_percent(interval=0.1)
            
            # Try to get CPU temperature (platform-specific)
            temperature_c = self._get_cpu_temperature()
            
            self._cpu_info_cache = CPUInfo(
                name=name,
                vendor=vendor,
                cores=cores,
                threads=threads,
                frequency_mhz=frequency_mhz,
                architecture=self.architecture,
                features=features,
                temperature_c=temperature_c,
                usage_percent=usage_percent
            )
            
            logger.debug(f"CPU detected: {name} ({cores} cores, {threads} threads)")
            
        except Exception as e:
            logger.error(f"CPU detection failed: {e}")
            # Fallback to minimal info
            self._cpu_info_cache = CPUInfo(
                name="Unknown",
                vendor="Unknown",
                cores=multiprocessing.cpu_count() or 1,
                threads=multiprocessing.cpu_count() or 1,
                frequency_mhz=0,
                architecture=self.architecture,
                features=[]
            )
        
        return self._cpu_info_cache
    
    def _get_cpu_name_vendor(self) -> Tuple[str, str]:
        """Get CPU name and vendor"""
        name = "Unknown CPU"
        vendor = "Unknown"
        
        try:
            if self.platform_name == "Windows":
                # Use WMI on Windows
                result = subprocess.run(
                    ["wmic", "cpu", "get", "Name", "/value"],
                    capture_output=True, text=True, timeout=5
                )
                
                for line in result.stdout.split('\n'):
                    if line.startswith("Name="):
                        name = line.split('=', 1)[1].strip()
                        break
                
                # Detect vendor from name
                if "Intel" in name:
                    vendor = "Intel"
                elif "AMD" in name:
                    vendor = "AMD"
                elif "Apple" in name:
                    vendor = "Apple"
                    
            elif self.platform_name == "Darwin":
                # Use sysctl on macOS
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5
                )
                
                name = result.stdout.strip()
                
                if "Intel" in name:
                    vendor = "Intel"
                elif "Apple" in name:
                    vendor = "Apple"
                    
            else:
                # Linux
                cpuinfo_path = Path("/proc/cpuinfo")
                if cpuinfo_path.exists():
                    with open(cpuinfo_path) as f:
                        for line in f:
                            if line.startswith("model name"):
                                name = line.split(':', 1)[1].strip()
                                break
                            elif line.startswith("vendor_id"):
                                vendor_id = line.split(':', 1)[1].strip()
                                if "GenuineIntel" in vendor_id:
                                    vendor = "Intel"
                                elif "AuthenticAMD" in vendor_id:
                                    vendor = "AMD"
                                    
        except Exception as e:
            logger.debug(f"Failed to get CPU name/vendor: {e}")
        
        return name, vendor
    
    def _detect_cpu_features(self) -> List[str]:
        """Detect CPU features"""
        features = []
        
        try:
            if self.platform_name == "Windows":
                # Check for AVX support
                result = subprocess.run(
                    ["wmic", "cpu", "get", "Characteristics"],
                    capture_output=True, text=True, timeout=5
                )
                
                if "AVX" in result.stdout:
                    features.append("avx")
                if "AVX2" in result.stdout:
                    features.append("avx2")
                    
            elif self.platform_name == "Darwin":
                # Check for Apple Silicon
                result = subprocess.run(
                    ["sysctl", "-n", "hw.optional.arm64"],
                    capture_output=True, text=True, timeout=5
                )
                
                if result.stdout.strip() == "1":
                    features.append("apple_silicon")
                    features.append("neon")
                else:
                    # Intel Mac - check for AVX
                    result = subprocess.run(
                        ["sysctl", "-n", "hw.optional.avx1_0"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip() == "1":
                        features.append("avx")
                        
                    result = subprocess.run(
                        ["sysctl", "-n", "hw.optional.avx2_0"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip() == "1":
                        features.append("avx2")
                        
            else:
                # Linux
                cpuinfo_path = Path("/proc/cpuinfo")
                if cpuinfo_path.exists():
                    with open(cpuinfo_path) as f:
                        for line in f:
                            if line.startswith("flags"):
                                flags = line.split(':', 1)[1].strip().split()
                                if "avx" in flags:
                                    features.append("avx")
                                if "avx2" in flags:
                                    features.append("avx2")
                                if "sse4_2" in flags:
                                    features.append("sse4.2")
                                break
                                
        except Exception as e:
            logger.debug(f"Failed to detect CPU features: {e}")
        
        return features
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available"""
        try:
            # Try psutil sensors (Linux/macOS)
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.label in ['Core 0', 'CPU', 'Package']:
                                return entry.current
                                
        except Exception as e:
            logger.debug(f"Failed to get CPU temperature: {e}")
        
        return None
    
    def _detect_memory(self) -> MemoryInfo:
        """Detect memory information"""
        try:
            # Get virtual memory info
            vm = psutil.virtual_memory()
            
            # Get swap memory info
            swap = psutil.swap_memory()
            
            return MemoryInfo(
                total_gb=round(vm.total / (1024**3), 2),
                available_gb=round(vm.available / (1024**3), 2),
                used_gb=round(vm.used / (1024**3), 2),
                percent_used=vm.percent,
                swap_total_gb=round(swap.total / (1024**3), 2),
                swap_used_gb=round(swap.used / (1024**3), 2),
                swap_percent_used=swap.percent
            )
            
        except Exception as e:
            logger.error(f"Memory detection failed: {e}")
            # Return minimal info
            return MemoryInfo(
                total_gb=4.0,
                available_gb=2.0,
                used_gb=2.0,
                percent_used=50.0,
                swap_total_gb=0,
                swap_used_gb=0,
                swap_percent_used=0
            )
    
    def _detect_gpu(self) -> GPUInfo:
        """Detect GPU information"""
        if self._gpu_info_cache:
            return self._gpu_info_cache
        
        gpu_info = GPUInfo(
            available=False,
            vendor=GPUVendor.UNKNOWN.value,
            name="No GPU detected",
            memory_gb=0,
            cuda_available=False,
            metal_available=False
        )
        
        try:
            if self.platform_name == "Windows":
                gpu_info = self._detect_gpu_windows()
            elif self.platform_name == "Darwin":
                gpu_info = self._detect_gpu_macos()
            else:
                gpu_info = self._detect_gpu_linux()
                
        except Exception as e:
            logger.debug(f"GPU detection failed: {e}")
        
        self._gpu_info_cache = gpu_info
        return gpu_info
    
    def _detect_gpu_windows(self) -> GPUInfo:
        """Detect GPU on Windows"""
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM,DriverVersion", "/value"],
                capture_output=True, text=True, timeout=5
            )
            
            name = ""
            memory_bytes = 0
            driver_version = ""
            
            for line in result.stdout.split('\n'):
                if line.startswith("Name="):
                    name = line.split('=', 1)[1].strip()
                elif line.startswith("AdapterRAM="):
                    try:
                        memory_bytes = int(line.split('=', 1)[1].strip())
                    except:
                        pass
                elif line.startswith("DriverVersion="):
                    driver_version = line.split('=', 1)[1].strip()
            
            if name:
                # Determine vendor
                vendor = GPUVendor.UNKNOWN.value
                if "NVIDIA" in name.upper():
                    vendor = GPUVendor.NVIDIA.value
                elif "AMD" in name.upper() or "RADEON" in name.upper():
                    vendor = GPUVendor.AMD.value
                elif "INTEL" in name.upper():
                    vendor = GPUVendor.INTEL.value
                
                # Check CUDA availability
                cuda_available = False
                if vendor == GPUVendor.NVIDIA.value:
                    cuda_available = self._check_cuda_windows()
                
                return GPUInfo(
                    available=True,
                    vendor=vendor,
                    name=name,
                    memory_gb=round(memory_bytes / (1024**3), 2) if memory_bytes > 0 else 0,
                    cuda_available=cuda_available,
                    metal_available=False,
                    driver_version=driver_version
                )
                
        except Exception as e:
            logger.debug(f"Windows GPU detection failed: {e}")
        
        return GPUInfo(
            available=False,
            vendor=GPUVendor.UNKNOWN.value,
            name="No GPU detected",
            memory_gb=0,
            cuda_available=False,
            metal_available=False
        )
    
    def _check_cuda_windows(self) -> bool:
        """Check if CUDA is available on Windows"""
        try:
            # Check for nvidia-smi
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return True
                
        except:
            pass
        
        return False
    
    def _detect_gpu_macos(self) -> GPUInfo:
        """Detect GPU on macOS"""
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                displays = data.get("SPDisplaysDataType", [])
                for display in displays:
                    if "sppci_model" in display:
                        name = display["sppci_model"]
                        
                        # Check for Metal support (all modern Macs)
                        metal_available = True
                        
                        # Determine vendor
                        vendor = GPUVendor.UNKNOWN.value
                        if "Apple" in name:
                            vendor = GPUVendor.APPLE.value
                        elif "Intel" in name:
                            vendor = GPUVendor.INTEL.value
                        elif "AMD" in name or "Radeon" in name:
                            vendor = GPUVendor.AMD.value
                        
                        # Get VRAM if available
                        memory_gb = 0
                        if "sppci_vram" in display:
                            vram_str = display["sppci_vram"]
                            # Parse VRAM string (e.g., "8 GB")
                            match = re.match(r"(\d+(?:\.\d+)?)\s*GB", vram_str)
                            if match:
                                memory_gb = float(match.group(1))
                        
                        return GPUInfo(
                            available=True,
                            vendor=vendor,
                            name=name,
                            memory_gb=memory_gb,
                            cuda_available=False,
                            metal_available=metal_available
                        )
                        
        except Exception as e:
            logger.debug(f"macOS GPU detection failed: {e}")
        
        return GPUInfo(
            available=False,
            vendor=GPUVendor.UNKNOWN.value,
            name="No GPU detected",
            memory_gb=0,
            cuda_available=False,
            metal_available=False
        )
    
    def _detect_gpu_linux(self) -> GPUInfo:
        """Detect GPU on Linux"""
        try:
            # Try lspci first
            result = subprocess.run(
                ["lspci", "-v"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if "VGA compatible controller" in line or "3D controller" in line:
                        # Extract GPU name
                        parts = line.split(':', 2)
                        if len(parts) > 2:
                            name = parts[2].strip()
                            
                            # Determine vendor
                            vendor = GPUVendor.UNKNOWN.value
                            if "NVIDIA" in name.upper():
                                vendor = GPUVendor.NVIDIA.value
                            elif "AMD" in name.upper() or "RADEON" in name.upper():
                                vendor = GPUVendor.AMD.value
                            elif "INTEL" in name.upper():
                                vendor = GPUVendor.INTEL.value
                            
                            # Check CUDA for NVIDIA
                            cuda_available = False
                            if vendor == GPUVendor.NVIDIA.value:
                                cuda_available = self._check_cuda_linux()
                            
                            return GPUInfo(
                                available=True,
                                vendor=vendor,
                                name=name,
                                memory_gb=0,  # Would need nvidia-smi for memory
                                cuda_available=cuda_available,
                                metal_available=False
                            )
                            
        except Exception as e:
            logger.debug(f"Linux GPU detection failed: {e}")
        
        return GPUInfo(
            available=False,
            vendor=GPUVendor.UNKNOWN.value,
            name="No GPU detected",
            memory_gb=0,
            cuda_available=False,
            metal_available=False
        )
    
    def _check_cuda_linux(self) -> bool:
        """Check if CUDA is available on Linux"""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _detect_storage(self) -> StorageInfo:
        """Detect storage information"""
        try:
            # Get disk usage for root partition
            usage = psutil.disk_usage('/')
            
            # Try to detect SSD vs HDD
            is_ssd = self._detect_ssd()
            
            return StorageInfo(
                total_gb=round(usage.total / (1024**3), 2),
                available_gb=round(usage.free / (1024**3), 2),
                used_gb=round(usage.used / (1024**3), 2),
                percent_used=usage.percent,
                mount_point="/",
                filesystem="unknown",
                is_ssd=is_ssd
            )
            
        except Exception as e:
            logger.error(f"Storage detection failed: {e}")
            return StorageInfo(
                total_gb=100.0,
                available_gb=50.0,
                used_gb=50.0,
                percent_used=50.0,
                mount_point="/",
                filesystem="unknown",
                is_ssd=False
            )
    
    def _detect_ssd(self) -> bool:
        """Detect if system drive is SSD"""
        try:
            if self.platform_name == "Windows":
                # Check for SSD on Windows
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "MediaType"],
                    capture_output=True, text=True, timeout=5
                )
                return "SSD" in result.stdout
                
            elif self.platform_name == "Darwin":
                # macOS - most modern Macs have SSDs
                return True
                
            else:
                # Linux - check rotational flag
                rotational_path = Path("/sys/block/sda/queue/rotational")
                if rotational_path.exists():
                    with open(rotational_path) as f:
                        return f.read().strip() == "0"
                        
        except Exception as e:
            logger.debug(f"SSD detection failed: {e}")
        
        return False
    
    def _determine_tier(self, cpu: CPUInfo, memory: MemoryInfo, gpu: GPUInfo) -> HardwareTier:
        """Determine hardware tier based on specifications"""
        # Ultra tier
        if (memory.total_gb >= 16 and 
            cpu.cores >= 8 and 
            gpu.available and 
            (gpu.cuda_available or gpu.metal_available)):
            return HardwareTier.ULTRA
        
        # High tier
        if memory.total_gb >= 8 and cpu.cores >= 4:
            return HardwareTier.HIGH
        
        # Standard tier
        if memory.total_gb >= 4 and cpu.cores >= 2:
            return HardwareTier.STANDARD
        
        # Minimum tier
        return HardwareTier.MINIMUM
    
    def _select_optimal_model(self, tier: HardwareTier, memory: MemoryInfo) -> str:
        """Select optimal model based on tier and available memory"""
        # Leave some RAM for system
        available_ram = memory.available_gb
        
        # Model selection by tier
        tier_models = {
            HardwareTier.ULTRA: ["llama3.2:7b", "llama3.2:3b", "llama3.2:1b"],
            HardwareTier.HIGH: ["llama3.2:3b", "llama3.2:1b", "llama3.2:1b-q4_0"],
            HardwareTier.STANDARD: ["llama3.2:1b", "llama3.2:1b-q4_0"],
            HardwareTier.MINIMUM: ["llama3.2:1b-q4_0", "llama3.2:1b"]
        }
        
        # Select first model that fits in available RAM
        for model in tier_models[tier]:
            requirements = self.MODEL_REQUIREMENTS.get(model, {})
            min_ram = requirements.get("min_ram", 2)
            
            # Leave at least 2GB for system
            if available_ram >= min_ram + 2:
                logger.info(f"Selected model {model} for {tier.value} tier with {available_ram:.1f}GB available RAM")
                return model
        
        # Fallback to smallest model
        logger.warning(f"Insufficient RAM for tier {tier.value}, using minimal model")
        return "llama3.2:1b-q4_0"
    
    def _determine_capabilities(self, cpu: CPUInfo, memory: MemoryInfo, gpu: GPUInfo) -> Dict[str, bool]:
        """Determine system capabilities"""
        return {
            "multi_threading": cpu.threads > 2,
            "simd_acceleration": "avx" in cpu.features or "avx2" in cpu.features,
            "gpu_acceleration": gpu.available,
            "cuda": gpu.cuda_available,
            "metal": gpu.metal_available,
            "large_context": memory.total_gb >= 8,
            "batch_inference": memory.total_gb >= 4,
            "model_caching": memory.available_gb >= 2,
            "parallel_sessions": cpu.cores >= 4 and memory.total_gb >= 8,
            "real_time_inference": cpu.cores >= 4 or gpu.available,
            "apple_silicon": cpu.vendor == "Apple" and "apple_silicon" in cpu.features
        }
    
    def _calculate_performance_score(self, cpu: CPUInfo, memory: MemoryInfo, gpu: GPUInfo) -> int:
        """Calculate overall performance score (0-100)"""
        score = 0
        
        # CPU score (max 40 points)
        score += min(cpu.cores * 5, 20)  # Up to 20 points for cores
        score += min(cpu.threads * 2.5, 20)  # Up to 20 points for threads
        
        # Memory score (max 40 points)
        score += min(memory.total_gb * 2.5, 40)
        
        # GPU bonus (20 points)
        if gpu.available:
            score += 10
            if gpu.cuda_available or gpu.metal_available:
                score += 10
        
        return min(score, 100)
    
    def get_hardware_tier(self) -> str:
        """Get hardware tier as string"""
        info = self.get_system_info()
        return info.get("tier", "standard")
    
    def get_optimal_model(self) -> str:
        """Get optimal model for current hardware"""
        info = self.get_system_info()
        return info.get("optimal_model", "llama3.2:1b")
    
    def get_optimal_threads(self) -> int:
        """Get optimal thread count for inference"""
        cpu = self._detect_cpu()
        
        # Use 75% of available threads for inference
        optimal = max(1, int(cpu.threads * 0.75))
        
        # Cap at 8 threads to avoid diminishing returns
        return min(optimal, 8)
    
    def check_minimum_requirements(self) -> Tuple[bool, List[str]]:
        """
        Check if system meets minimum requirements.
        
        Returns:
            Tuple of (meets_requirements, list_of_issues)
        """
        issues = []
        
        # Get current system info
        info = self.get_system_info()
        
        # Check RAM (minimum 4GB)
        if info["memory"]["total_gb"] < 4:
            issues.append(f"Insufficient RAM: {info['memory']['total_gb']}GB < 4GB required")
        
        # Check CPU cores (minimum 2)
        if info["cpu"]["cores"] < 2:
            issues.append(f"Insufficient CPU cores: {info['cpu']['cores']} < 2 required")
        
        # Check disk space (minimum 8GB free)
        if info["storage"]["available_gb"] < 8:
            issues.append(f"Insufficient disk space: {info['storage']['available_gb']}GB < 8GB required")
        
        # Check platform
        supported_platforms = ["Windows", "Darwin"]
        if info["platform"] not in supported_platforms:
            issues.append(f"Unsupported platform: {info['platform']}")
        
        meets_requirements = len(issues) == 0
        return meets_requirements, issues
    
    def get_performance_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        info = self.get_system_info()
        
        # Memory recommendations
        if info["memory"]["available_gb"] < 2:
            recommendations.append("Close unnecessary applications to free up RAM")
        
        if info["memory"]["percent_used"] > 80:
            recommendations.append("System memory usage is high - consider closing some programs")
        
        # CPU recommendations
        if info["cpu"]["usage_percent"] and info["cpu"]["usage_percent"] > 80:
            recommendations.append("CPU usage is high - close CPU-intensive applications")
        
        # GPU recommendations
        if not info["gpu"]["available"]:
            recommendations.append("No GPU detected - CPU-only inference will be slower")
        elif info["gpu"]["available"] and not (info["gpu"]["cuda_available"] or info["gpu"]["metal_available"]):
            recommendations.append("GPU detected but acceleration not available - check drivers")
        
        # Storage recommendations
        if info["storage"]["available_gb"] < 10:
            recommendations.append("Low disk space - free up space for optimal performance")
        
        # Model recommendations
        if info["tier"] == "minimum":
            recommendations.append("System is running at minimum specifications - expect slower performance")
        
        return recommendations
    
    def get_status_summary(self) -> str:
        """Get human-readable status summary"""
        info = self.get_system_info()
        
        summary = f"""
Hardware Detection Summary:
---------------------------
Platform: {info['platform']} {info['architecture']}
CPU: {info['cpu']['name']} ({info['cpu']['cores']} cores, {info['cpu']['threads']} threads)
RAM: {info['memory']['total_gb']}GB total, {info['memory']['available_gb']}GB available
GPU: {info['gpu']['name']} ({'Available' if info['gpu']['available'] else 'Not available'})
Storage: {info['storage']['available_gb']}GB free of {info['storage']['total_gb']}GB
Performance Tier: {info['tier'].upper()}
Optimal Model: {info['optimal_model']}
Performance Score: {info['performance_score']}/100
"""
        return summary


# Testing
if __name__ == "__main__":
    # Test hardware detection
    detector = HardwareDetector()
    
    print("=" * 60)
    print("SUNFLOWER AI - HARDWARE DETECTION")
    print("=" * 60)
    
    # Get system info
    info = detector.get_system_info()
    
    # Display summary
    print(detector.get_status_summary())
    
    # Check requirements
    meets_reqs, issues = detector.check_minimum_requirements()
    
    if meets_reqs:
        print("✓ System meets minimum requirements")
    else:
        print("✗ System does not meet minimum requirements:")
        for issue in issues:
            print(f"  - {issue}")
    
    print()
    
    # Get recommendations
    recommendations = detector.get_performance_recommendations()
    
    if recommendations:
        print("Performance Recommendations:")
        for rec in recommendations:
            print(f"  • {rec}")
    else:
        print("✓ System is optimally configured")
    
    print("=" * 60)

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


@dataclass
class MemoryInfo:
    """Memory information"""
    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float
    swap_total_gb: float
    swap_used_gb: float


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
        "llama3.2:1b-q4_0": {"min_ram": 2, "recommended_ram": 4, "min_cores": 2}
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
        
        logger.info(f"Hardware detector initialized on {self.platform_name} {self.architecture}")
    
    def get_system_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get complete system information.
        
        Args:
            force_refresh: Force refresh of cached data
        
        Returns:
            Dictionary containing all system information
        """
        if self._system_info_cache and not force_refresh:
            return asdict(self._system_info_cache)
        
        try:
            # Gather all components
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
                capabilities=capabilities
            )
            
            return asdict(self._system_info_cache)
            
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return self._get_fallback_info()
    
    def _detect_cpu(self) -> CPUInfo:
        """Detect CPU information"""
        if self._cpu_info_cache:
            return self._cpu_info_cache
        
        try:
            # Basic info from psutil
            cpu_count = psutil.cpu_count(logical=False) or 2
            thread_count = psutil.cpu_count(logical=True) or cpu_count
            cpu_freq = psutil.cpu_freq()
            freq_mhz = int(cpu_freq.current) if cpu_freq else 2000
            
            # Get CPU name and vendor
            cpu_name = "Unknown CPU"
            cpu_vendor = "Unknown"
            cpu_features = []
            
            if self.platform_name == "Windows":
                cpu_name, cpu_vendor, cpu_features = self._get_windows_cpu_info()
            elif self.platform_name == "Darwin":  # macOS
                cpu_name, cpu_vendor, cpu_features = self._get_macos_cpu_info()
            elif self.platform_name == "Linux":
                cpu_name, cpu_vendor, cpu_features = self._get_linux_cpu_info()
            
            # Detect architecture features
            if "avx" in cpu_name.lower() or self._check_avx_support():
                cpu_features.append("avx")
            if "avx2" in cpu_name.lower() or self._check_avx2_support():
                cpu_features.append("avx2")
            
            self._cpu_info_cache = CPUInfo(
                name=cpu_name,
                vendor=cpu_vendor,
                cores=cpu_count,
                threads=thread_count,
                frequency_mhz=freq_mhz,
                architecture=self.architecture,
                features=cpu_features
            )
            
            logger.info(f"CPU detected: {cpu_name} ({cpu_count} cores, {thread_count} threads)")
            
            return self._cpu_info_cache
            
        except Exception as e:
            logger.error(f"CPU detection failed: {e}")
            return CPUInfo(
                name="Generic CPU",
                vendor="Unknown",
                cores=multiprocessing.cpu_count() or 2,
                threads=multiprocessing.cpu_count() or 2,
                frequency_mhz=2000,
                architecture=self.architecture,
                features=[]
            )
    
    def _get_windows_cpu_info(self) -> Tuple[str, str, List[str]]:
        """Get CPU info on Windows"""
        try:
            # Use wmic to get CPU info
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name,Manufacturer,NumberOfCores,ThreadCount", "/format:list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            cpu_name = "Unknown CPU"
            cpu_vendor = "Unknown"
            
            for line in result.stdout.split('\n'):
                if "Name=" in line:
                    cpu_name = line.split('=')[1].strip()
                elif "Manufacturer=" in line:
                    cpu_vendor = line.split('=')[1].strip()
            
            # Detect features
            features = []
            if "Intel" in cpu_vendor:
                if any(gen in cpu_name for gen in ["i3", "i5", "i7", "i9"]):
                    features.append("intel_core")
            elif "AMD" in cpu_vendor:
                if "Ryzen" in cpu_name:
                    features.append("amd_ryzen")
            
            return cpu_name, cpu_vendor, features
            
        except Exception as e:
            logger.warning(f"Windows CPU detection failed: {e}")
            return "Unknown CPU", "Unknown", []
    
    def _get_macos_cpu_info(self) -> Tuple[str, str, List[str]]:
        """Get CPU info on macOS"""
        try:
            # Use sysctl to get CPU info
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            cpu_name = result.stdout.strip() or "Unknown CPU"
            
            # Determine vendor
            cpu_vendor = "Unknown"
            features = []
            
            if "Intel" in cpu_name:
                cpu_vendor = "Intel"
                features.append("intel")
            elif "Apple" in cpu_name or "M1" in cpu_name or "M2" in cpu_name or "M3" in cpu_name:
                cpu_vendor = "Apple"
                features.extend(["apple_silicon", "arm64", "neural_engine"])
                
                # Detect specific Apple Silicon generation
                if "M1" in cpu_name:
                    features.append("m1")
                elif "M2" in cpu_name:
                    features.append("m2")
                elif "M3" in cpu_name:
                    features.append("m3")
            
            return cpu_name, cpu_vendor, features
            
        except Exception as e:
            logger.warning(f"macOS CPU detection failed: {e}")
            return "Unknown CPU", "Unknown", []
    
    def _get_linux_cpu_info(self) -> Tuple[str, str, List[str]]:
        """Get CPU info on Linux"""
        try:
            cpu_name = "Unknown CPU"
            cpu_vendor = "Unknown"
            features = []
            
            # Read /proc/cpuinfo
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_name = line.split(":")[1].strip()
                    elif "vendor_id" in line:
                        cpu_vendor = line.split(":")[1].strip()
                    elif "flags" in line:
                        flags = line.split(":")[1].strip().split()
                        if "avx" in flags:
                            features.append("avx")
                        if "avx2" in flags:
                            features.append("avx2")
                        break
            
            return cpu_name, cpu_vendor, features
            
        except Exception as e:
            logger.warning(f"Linux CPU detection failed: {e}")
            return "Unknown CPU", "Unknown", []
    
    def _check_avx_support(self) -> bool:
        """Check for AVX support"""
        try:
            if self.platform_name == "Windows":
                # Check using CPU-Z or similar would be needed
                return False
            else:
                # Try to check CPU flags
                result = subprocess.run(
                    ["grep", "avx", "/proc/cpuinfo"],
                    capture_output=True,
                    timeout=2
                )
                return result.returncode == 0
        except:
            return False
    
    def _check_avx2_support(self) -> bool:
        """Check for AVX2 support"""
        try:
            if self.platform_name == "Windows":
                return False
            else:
                result = subprocess.run(
                    ["grep", "avx2", "/proc/cpuinfo"],
                    capture_output=True,
                    timeout=2
                )
                return result.returncode == 0
        except:
            return False
    
    def _detect_memory(self) -> MemoryInfo:
        """Detect memory information"""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return MemoryInfo(
                total_gb=round(mem.total / (1024**3), 2),
                available_gb=round(mem.available / (1024**3), 2),
                used_gb=round(mem.used / (1024**3), 2),
                percent_used=mem.percent,
                swap_total_gb=round(swap.total / (1024**3), 2),
                swap_used_gb=round(swap.used / (1024**3), 2)
            )
        except Exception as e:
            logger.error(f"Memory detection failed: {e}")
            return MemoryInfo(
                total_gb=4.0,
                available_gb=2.0,
                used_gb=2.0,
                percent_used=50.0,
                swap_total_gb=0.0,
                swap_used_gb=0.0
            )
    
    def _detect_gpu(self) -> GPUInfo:
        """Detect GPU information"""
        if self._gpu_info_cache:
            return self._gpu_info_cache
        
        gpu_info = GPUInfo(
            available=False,
            vendor=GPUVendor.UNKNOWN.value,
            name="No GPU",
            memory_gb=0.0,
            cuda_available=False,
            metal_available=False
        )
        
        try:
            # Check for NVIDIA GPU
            if self._check_nvidia_gpu():
                gpu_info = self._get_nvidia_info()
            # Check for AMD GPU
            elif self._check_amd_gpu():
                gpu_info = self._get_amd_info()
            # Check for Apple Silicon GPU
            elif self.platform_name == "Darwin" and "arm" in self.architecture.lower():
                gpu_info = self._get_apple_gpu_info()
            # Check for Intel integrated GPU
            elif self._check_intel_gpu():
                gpu_info = self._get_intel_info()
            
            self._gpu_info_cache = gpu_info
            
            if gpu_info.available:
                logger.info(f"GPU detected: {gpu_info.name} ({gpu_info.memory_gb}GB VRAM)")
            else:
                logger.info("No dedicated GPU detected")
            
            return gpu_info
            
        except Exception as e:
            logger.error(f"GPU detection failed: {e}")
            return gpu_info
    
    def _check_nvidia_gpu(self) -> bool:
        """Check if NVIDIA GPU is present"""
        try:
            # Check if nvidia-smi is available
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _get_nvidia_info(self) -> GPUInfo:
        """Get NVIDIA GPU information"""
        try:
            # Get GPU name
            name_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            gpu_name = name_result.stdout.strip()
            
            # Get memory info
            mem_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            memory_mb = float(mem_result.stdout.strip())
            memory_gb = round(memory_mb / 1024, 2)
            
            # Check CUDA availability
            cuda_available = shutil.which("nvcc") is not None
            
            return GPUInfo(
                available=True,
                vendor=GPUVendor.NVIDIA.value,
                name=gpu_name,
                memory_gb=memory_gb,
                cuda_available=cuda_available,
                metal_available=False
            )
        except Exception as e:
            logger.warning(f"Failed to get NVIDIA GPU info: {e}")
            return GPUInfo(
                available=False,
                vendor=GPUVendor.UNKNOWN.value,
                name="Unknown GPU",
                memory_gb=0.0,
                cuda_available=False,
                metal_available=False
            )
    
    def _check_amd_gpu(self) -> bool:
        """Check if AMD GPU is present"""
        try:
            if self.platform_name == "Windows":
                # Check Windows registry or WMI
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return "AMD" in result.stdout or "Radeon" in result.stdout
            else:
                # Check lspci on Linux
                result = subprocess.run(
                    ["lspci"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return "AMD" in result.stdout or "Radeon" in result.stdout
        except:
            return False
    
    def _get_amd_info(self) -> GPUInfo:
        """Get AMD GPU information"""
        return GPUInfo(
            available=True,
            vendor=GPUVendor.AMD.value,
            name="AMD Radeon",
            memory_gb=4.0,  # Default estimate
            cuda_available=False,
            metal_available=False
        )
    
    def _check_intel_gpu(self) -> bool:
        """Check if Intel GPU is present"""
        try:
            cpu_info = self._detect_cpu()
            return "Intel" in cpu_info.vendor
        except:
            return False
    
    def _get_intel_info(self) -> GPUInfo:
        """Get Intel GPU information"""
        return GPUInfo(
            available=True,
            vendor=GPUVendor.INTEL.value,
            name="Intel Integrated Graphics",
            memory_gb=0.0,  # Shared memory
            cuda_available=False,
            metal_available=False
        )
    
    def _get_apple_gpu_info(self) -> GPUInfo:
        """Get Apple Silicon GPU information"""
        try:
            cpu_info = self._detect_cpu()
            
            # Estimate GPU memory based on system RAM
            mem_info = self._detect_memory()
            
            # Apple Silicon shares memory between CPU and GPU
            # Typically allocate up to 75% for GPU tasks
            gpu_memory = round(mem_info.total_gb * 0.75, 1)
            
            gpu_name = "Apple GPU"
            if "M1" in cpu_info.name:
                gpu_name = "Apple M1 GPU"
            elif "M2" in cpu_info.name:
                gpu_name = "Apple M2 GPU"
            elif "M3" in cpu_info.name:
                gpu_name = "Apple M3 GPU"
            
            return GPUInfo(
                available=True,
                vendor=GPUVendor.APPLE.value,
                name=gpu_name,
                memory_gb=gpu_memory,
                cuda_available=False,
                metal_available=True  # Metal is available on Apple Silicon
            )
        except Exception as e:
            logger.warning(f"Failed to get Apple GPU info: {e}")
            return GPUInfo(
                available=False,
                vendor=GPUVendor.UNKNOWN.value,
                name="Unknown GPU",
                memory_gb=0.0,
                cuda_available=False,
                metal_available=False
            )
    
    def _detect_storage(self) -> StorageInfo:
        """Detect storage information"""
        try:
            # Get disk usage for main partition
            usage = psutil.disk_usage('/')
            
            # Try to detect SSD vs HDD
            is_ssd = self._check_ssd()
            
            return StorageInfo(
                total_gb=round(usage.total / (1024**3), 2),
                available_gb=round(usage.free / (1024**3), 2),
                used_gb=round(usage.used / (1024**3), 2),
                percent_used=usage.percent,
                mount_point="/",
                filesystem="Unknown",
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
                filesystem="Unknown",
                is_ssd=False
            )
    
    def _check_ssd(self) -> bool:
        """Check if main drive is SSD"""
        try:
            if self.platform_name == "Windows":
                # Check using PowerShell
                result = subprocess.run(
                    ["powershell", "Get-PhysicalDisk | Select MediaType"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return "SSD" in result.stdout
            elif self.platform_name == "Darwin":
                # macOS - most modern Macs have SSDs
                return True
            else:
                # Linux - check rotational flag
                with open("/sys/block/sda/queue/rotational", "r") as f:
                    return f.read().strip() == "0"
        except:
            return False
    
    def _determine_tier(self, cpu: CPUInfo, memory: MemoryInfo, gpu: GPUInfo) -> HardwareTier:
        """Determine hardware tier based on components"""
        # Score based on components
        score = 0
        
        # CPU scoring
        if cpu.cores >= 8:
            score += 3
        elif cpu.cores >= 4:
            score += 2
        elif cpu.cores >= 2:
            score += 1
        
        # Memory scoring
        if memory.total_gb >= 16:
            score += 3
        elif memory.total_gb >= 8:
            score += 2
        elif memory.total_gb >= 4:
            score += 1
        
        # GPU scoring
        if gpu.available and gpu.memory_gb >= 4:
            score += 3
        elif gpu.available and gpu.memory_gb >= 2:
            score += 2
        elif gpu.available:
            score += 1
        
        # Special cases
        if cpu.vendor == "Apple" and "apple_silicon" in cpu.features:
            score += 1  # Apple Silicon bonus
        
        # Determine tier
        if score >= 8:
            return HardwareTier.ULTRA
        elif score >= 5:
            return HardwareTier.HIGH
        elif score >= 3:
            return HardwareTier.STANDARD
        else:
            return HardwareTier.MINIMUM
    
    def _select_optimal_model(self, tier: HardwareTier, memory: MemoryInfo) -> str:
        """Select optimal model based on hardware tier and available memory"""
        available_ram = memory.available_gb
        
        # Map tier to models with fallback
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
        
        memory = self._detect_memory()
        cpu = self._detect_cpu()
        storage = self._detect_storage()
        
        # Check RAM
        if memory.total_gb < 4:
            issues.append(f"Insufficient RAM: {memory.total_gb}GB (minimum 4GB required)")
        
        # Check CPU
        if cpu.cores < 2:
            issues.append(f"Insufficient CPU cores: {cpu.cores} (minimum 2 required)")
        
        # Check storage
        if storage.available_gb < 8:
            issues.append(f"Insufficient storage: {storage.available_gb}GB available (minimum 8GB required)")
        
        # Check platform
        if self.platform_name not in ["Windows", "Darwin"]:
            issues.append(f"Unsupported platform: {self.platform_name}")
        
        return len(issues) == 0, issues
    
    def get_performance_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        info = self.get_system_info()
        memory = info["memory"]
        cpu = info["cpu"]
        gpu = info["gpu"]
        tier = info["tier"]
        
        # Memory recommendations
        if memory["available_gb"] < 2:
            recommendations.append("Close unnecessary applications to free up RAM")
        
        if memory["total_gb"] < 8 and tier == "minimum":
            recommendations.append("Consider upgrading RAM to 8GB for better performance")
        
        # CPU recommendations
        if cpu["cores"] < 4:
            recommendations.append("Limit concurrent applications while using Sunflower AI")
        
        # GPU recommendations
        if not gpu["available"] and memory["total_gb"] >= 8:
            recommendations.append("Consider adding a dedicated GPU for faster inference")
        
        # Model recommendations
        if tier in ["ultra", "high"] and info["optimal_model"] == "llama3.2:1b-q4_0":
            recommendations.append("Your hardware supports larger models - check model availability")
        
        # Storage recommendations
        storage = info["storage"]
        if not storage["is_ssd"]:
            recommendations.append("Consider using an SSD for faster model loading")
        
        return recommendations
    
    def _get_fallback_info(self) -> Dict[str, Any]:
        """Get fallback system info when detection fails"""
        return {
            "platform": self.platform_name,
            "platform_version": self.platform_version,
            "architecture": self.architecture,
            "hostname": platform.node(),
            "cpu": asdict(CPUInfo(
                name="Generic CPU",
                vendor="Unknown",
                cores=2,
                threads=2,
                frequency_mhz=2000,
                architecture=self.architecture,
                features=[]
            )),
            "memory": asdict(MemoryInfo(
                total_gb=4.0,
                available_gb=2.0,
                used_gb=2.0,
                percent_used=50.0,
                swap_total_gb=0.0,
                swap_used_gb=0.0
            )),
            "gpu": asdict(GPUInfo(
                available=False,
                vendor="unknown",
                name="No GPU",
                memory_gb=0.0,
                cuda_available=False,
                metal_available=False
            )),
            "storage": asdict(StorageInfo(
                total_gb=100.0,
                available_gb=50.0,
                used_gb=50.0,
                percent_used=50.0,
                mount_point="/",
                filesystem="Unknown",
                is_ssd=False
            )),
            "tier": "standard",
            "optimal_model": "llama3.2:1b-q4_0",
            "capabilities": {
                "multi_threading": False,
                "simd_acceleration": False,
                "gpu_acceleration": False,
                "cuda": False,
                "metal": False,
                "large_context": False,
                "batch_inference": True,
                "model_caching": True,
                "parallel_sessions": False,
                "real_time_inference": False,
                "apple_silicon": False
            }
        }
    
    def generate_hardware_report(self, output_path: Optional[Path] = None) -> str:
        """Generate detailed hardware report"""
        info = self.get_system_info()
        
        report = []
        report.append("=" * 60)
        report.append("SUNFLOWER AI HARDWARE REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {platform.datetime.now().isoformat()}")
        report.append("")
        
        # System
        report.append("SYSTEM INFORMATION")
        report.append("-" * 40)
        report.append(f"Platform: {info['platform']} {info['architecture']}")
        report.append(f"Hostname: {info['hostname']}")
        report.append(f"Hardware Tier: {info['tier'].upper()}")
        report.append(f"Optimal Model: {info['optimal_model']}")
        report.append("")
        
        # CPU
        cpu = info['cpu']
        report.append("CPU INFORMATION")
        report.append("-" * 40)
        report.append(f"Model: {cpu['name']}")
        report.append(f"Vendor: {cpu['vendor']}")
        report.append(f"Cores: {cpu['cores']} physical, {cpu['threads']} logical")
        report.append(f"Frequency: {cpu['frequency_mhz']} MHz")
        report.append(f"Features: {', '.join(cpu['features']) if cpu['features'] else 'None detected'}")
        report.append("")
        
        # Memory
        mem = info['memory']
        report.append("MEMORY INFORMATION")
        report.append("-" * 40)
        report.append(f"Total RAM: {mem['total_gb']} GB")
        report.append(f"Available: {mem['available_gb']} GB")
        report.append(f"Used: {mem['used_gb']} GB ({mem['percent_used']:.1f}%)")
        report.append(f"Swap: {mem['swap_total_gb']} GB total, {mem['swap_used_gb']} GB used")
        report.append("")
        
        # GPU
        gpu = info['gpu']
        report.append("GPU INFORMATION")
        report.append("-" * 40)
        if gpu['available']:
            report.append(f"Model: {gpu['name']}")
            report.append(f"Vendor: {gpu['vendor']}")
            report.append(f"Memory: {gpu['memory_gb']} GB")
            report.append(f"CUDA: {'Yes' if gpu['cuda_available'] else 'No'}")
            report.append(f"Metal: {'Yes' if gpu['metal_available'] else 'No'}")
        else:
            report.append("No dedicated GPU detected")
        report.append("")
        
        # Storage
        storage = info['storage']
        report.append("STORAGE INFORMATION")
        report.append("-" * 40)
        report.append(f"Total: {storage['total_gb']} GB")
        report.append(f"Available: {storage['available_gb']} GB")
        report.append(f"Type: {'SSD' if storage['is_ssd'] else 'HDD'}")
        report.append("")
        
        # Capabilities
        caps = info['capabilities']
        report.append("SYSTEM CAPABILITIES")
        report.append("-" * 40)
        for cap, enabled in caps.items():
            report.append(f"{cap.replace('_', ' ').title()}: {'✓' if enabled else '✗'}")
        report.append("")
        
        # Recommendations
        recommendations = self.get_performance_recommendations()
        if recommendations:
            report.append("RECOMMENDATIONS")
            report.append("-" * 40)
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        report.append("=" * 60)
        
        report_text = "\n".join(report)
        
        # Save if path provided
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                logger.info(f"Hardware report saved to: {output_path}")
            except Exception as e:
                logger.error(f"Failed to save report: {e}")
        
        return report_text

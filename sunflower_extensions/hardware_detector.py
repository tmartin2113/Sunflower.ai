#!/usr/bin/env python3
"""
Hardware Detector for Sunflower AI
Detects essential system capabilities (CPU, RAM, GPU) for the application.
"""

import platform
import subprocess
import os
import multiprocessing
from typing import Dict, Optional, List


class HardwareDetector:
    """
    Detects essential hardware capabilities (CPU, RAM, GPU) to ensure
    the application can run smoothly. This class avoids external dependencies
    and uses cross-platform methods where possible.
    """

    def __init__(self):
        """Initialize hardware detector."""
        self.system = platform.system()
        self.cpu_cores = multiprocessing.cpu_count() or 1
        self.total_ram_gb = self._get_total_ram()

    def get_system_info(self) -> Dict:
        """
        Get a simplified, cross-platform summary of the system's hardware.
        """
        return {
            "platform": {
                "system": self.system,
                "architecture": platform.machine(),
            },
            "cpu_cores": self.cpu_cores,
            "total_ram_gb": self.total_ram_gb,
            "gpu_info": self.get_gpu_info(),
        }

    def _get_total_ram(self) -> float:
        """
        Get total system RAM in gigabytes using platform-specific commands
        as a fallback if `psutil` is not available. This method is designed
        to be resilient.
        """
        try:
            # First, try with psutil if it's installed (recommended)
            import psutil
            mem = psutil.virtual_memory()
            return round(mem.total / (1024**3), 1)
        except (ImportError, AttributeError):
            # Fallback to OS-specific commands
            if self.system == "Windows":
                return self._get_ram_windows()
            elif self.system == "Darwin":
                return self._get_ram_macos()
            elif self.system == "Linux":
                return self._get_ram_linux()
            return 4.0  # Reasonable default

    def _get_ram_windows(self) -> float:
        try:
            command = "wmic ComputerSystem get TotalPhysicalMemory /value"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if "TotalPhysicalMemory" in line:
                        bytes_val = int(line.split('=')[1])
                        return round(bytes_val / (1024**3), 1)
        except Exception:
            return 4.0
        return 4.0

    def _get_ram_macos(self) -> float:
        try:
            command = "sysctl -n hw.memsize"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                bytes_val = int(result.stdout.strip())
                return round(bytes_val / (1024**3), 1)
        except Exception:
            return 4.0
        return 4.0

    def _get_ram_linux(self) -> float:
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if "MemTotal" in line:
                        kb_val = int(line.split()[1])
                        return round(kb_val / (1024**2), 1)
        except Exception:
            return 4.0
        return 4.0

    def get_gpu_info(self) -> Dict:
        """
        Detects GPU information, prioritizing NVIDIA for CUDA support,
        then checking for AMD/Intel on Windows, and Apple Silicon on macOS.
        """
        if self.system == "Windows":
            return self._get_gpu_windows()
        elif self.system == "Darwin":
            return self._get_gpu_macos()
        elif self.system == "Linux":
            return self._get_gpu_linux()
        return {"detected": False, "model": "Unknown"}

    def _get_gpu_windows(self) -> Dict:
        try:
            # WMIC is reliable for getting GPU names on Windows
            command = "wmic path win32_VideoController get name"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                gpus = [line.strip() for line in result.stdout.split('\n') if line.strip() and "Name" not in line]
                if gpus:
                    # Prioritize known high-performance brands
                    for gpu in gpus:
                        if "NVIDIA" in gpu or "AMD" in gpu:
                            return {"detected": True, "model": gpu}
                    return {"detected": True, "model": gpus[0]}
        except Exception:
            pass
        return {"detected": False, "model": "Unknown"}

    def _get_gpu_macos(self) -> Dict:
        try:
            # On macOS, check for Apple Silicon first, which implies a powerful integrated GPU
            if "arm" in platform.machine().lower():
                return {"detected": True, "model": "Apple Silicon (M-series)"}

            # For Intel Macs, check system_profiler
            command = "system_profiler SPDisplaysDataType | grep Chipset"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                gpu_model = result.stdout.split(":")[1].strip()
                return {"detected": True, "model": gpu_model}
        except Exception:
            pass
        return {"detected": False, "model": "Unknown"}

    def _get_gpu_linux(self) -> Dict:
        try:
            # `lspci` is standard on Linux for listing hardware
            command = "lspci | grep -i 'vga\\|3d\\|display'"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                gpu_model = result.stdout.split(":")[-1].strip()
                # Clean up model name
                if '[' in gpu_model and ']' in gpu_model:
                    gpu_model = gpu_model.split('[')[1].split(']')[0]
                return {"detected": True, "model": gpu_model}
        except Exception:
            pass
        return {"detected": False, "model": "Unknown"}

    def has_sufficient_hardware(self, min_ram_gb: int = 4) -> bool:
        """
        Check if the system meets the minimum hardware requirements to run
        the application.
        """
        return self.total_ram_gb >= min_ram_gb

    def generate_report(self) -> str:
        """Generate a simple, human-readable hardware report."""
        info = self.get_system_info()
        report = (
            "--- Sunflower AI Hardware Report ---\n"
            f"Operating System: {info['platform']['system']} ({info['platform']['architecture']})\n"
            f"CPU Cores: {info['cpu_cores']}\n"
            f"Total RAM: {info['total_ram_gb']:.1f} GB\n"
            f"GPU Detected: {'Yes' if info['gpu_info']['detected'] else 'No'}\n"
        )
        if info['gpu_info']['detected']:
            report += f"GPU Model: {info['gpu_info']['model']}\n"

        if not self.has_sufficient_hardware():
            report += "\nWARNING: System RAM is below the recommended 4GB. Performance may be slow."
        
        report += "--------------------------------------"
        return report

_hardware_detector_instance = None

def get_hardware_detector():
    """Singleton accessor for the HardwareDetector object"""
    global _hardware_detector_instance
    if _hardware_detector_instance is None:
        _hardware_detector_instance = HardwareDetector()
    return _hardware_detector_instance

def get_total_vram_gb() -> float:
    """
    Detects the total VRAM of the primary GPU in gigabytes.

    This is a best-effort detection and may not be accurate on all systems.
    It returns a default value if VRAM cannot be determined. It prioritizes
    NVIDIA GPUs as they are the most common for AI tasks.

    Returns:
        float: The estimated VRAM in GB, or a default value (e.g., 2.0).
    """
    detector = get_hardware_detector()
    system = detector.system

    # On Apple Silicon, VRAM is unified with system RAM.
    # Return a portion of system RAM as an estimate.
    if "arm" in platform.machine().lower() and system == "Darwin":
        # A conservative estimate: 1/2 of system RAM, capped at a reasonable max for graphics
        return min(detector.total_ram_gb * 0.5, 16.0)

    # For dedicated GPUs, try to query via command line
    try:
        if system == "Windows":
            # Try to get VRAM from nvidia-smi first
            command = "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return round(int(result.stdout.strip()) / 1024, 1)
        elif system == "Linux":
            command = "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                return round(int(result.stdout.strip()) / 1024, 1)
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError):
        # nvidia-smi might not be present or fail
        pass

    # Fallback for non-NVIDIA or when nvidia-smi fails
    # This is a very rough estimate.
    gpu_info = detector.get_gpu_info()
    if gpu_info.get("detected"):
        model_name = gpu_info.get("model", "").lower()
        if "rtx 4090" in model_name or "rtx 3090" in model_name:
            return 24.0
        if "rtx 4080" in model_name or "rtx 3080" in model_name:
            return 10.0
        if "rtx 4070" in model_name or "rtx 3070" in model_name:
            return 8.0
        if "rtx 4060" in model_name or "rtx 3060" in model_name:
            return 6.0
    
    # If all else fails, return a safe default
    return 2.0


if __name__ == '__main__':
    detector = HardwareDetector()
    print(detector.generate_report())

#!/usr/bin/env python3
"""
Sunflower AI - Common Launcher Components
Shared functionality for platform-specific launchers
Version: 6.2.0
FIXED: BUG-008 - Added timeout configuration to all subprocess calls
"""

import os
import sys
import json
import time
import socket
import hashlib
import platform
import subprocess
import logging
import psutil
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('launcher_common')

# Timeout configuration constants
DEFAULT_SUBPROCESS_TIMEOUT = 30.0  # 30 seconds default
QUICK_COMMAND_TIMEOUT = 5.0        # 5 seconds for quick commands
LONG_RUNNING_TIMEOUT = 300.0       # 5 minutes for long operations
INSTALL_TIMEOUT = 600.0             # 10 minutes for installations
NETWORK_TIMEOUT = 60.0              # 1 minute for network operations


@dataclass
class TimeoutConfig:
    """
    Configuration for subprocess timeouts
    FIXED: Centralized timeout management
    """
    quick: float = QUICK_COMMAND_TIMEOUT
    default: float = DEFAULT_SUBPROCESS_TIMEOUT
    long: float = LONG_RUNNING_TIMEOUT
    install: float = INSTALL_TIMEOUT
    network: float = NETWORK_TIMEOUT
    
    def get_timeout(self, operation_type: str = 'default') -> float:
        """Get timeout for specific operation type"""
        timeouts = {
            'quick': self.quick,
            'default': self.default,
            'long': self.long,
            'install': self.install,
            'network': self.network
        }
        return timeouts.get(operation_type, self.default)


class SubprocessRunner:
    """
    Secure subprocess runner with timeout management
    FIXED: All subprocess calls now have proper timeouts
    """
    
    def __init__(self, timeout_config: Optional[TimeoutConfig] = None):
        self.timeout_config = timeout_config or TimeoutConfig()
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
    
    def run_command(
        self,
        command: List[str],
        operation_type: str = 'default',
        timeout: Optional[float] = None,
        capture_output: bool = True,
        check: bool = True,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        shell: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run a subprocess command with proper timeout
        
        Args:
            command: Command to execute
            operation_type: Type of operation for timeout selection
            timeout: Override timeout value (uses config if None)
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise on non-zero exit
            cwd: Working directory
            env: Environment variables
            shell: Whether to use shell execution
            
        Returns:
            CompletedProcess object
            
        Raises:
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If command fails and check=True
        """
        # Determine timeout
        if timeout is None:
            timeout = self.timeout_config.get_timeout(operation_type)
        
        # Log command execution
        logger.info(f"Running command: {' '.join(command)} (timeout={timeout}s)")
        
        try:
            # Run with timeout
            result = subprocess.run(
                command,
                timeout=timeout,
                capture_output=capture_output,
                check=check,
                cwd=cwd,
                env=env,
                shell=shell,
                text=True
            )
            
            logger.debug(f"Command completed successfully: {command[0]}")
            return result
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {timeout}s: {' '.join(command)}")
            # Kill the process if it's still running
            if e.stderr:
                logger.error(f"Partial stderr: {e.stderr}")
            raise
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed with exit code {e.returncode}: {' '.join(command)}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr}")
            raise
    
    def start_background_process(
        self,
        name: str,
        command: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ) -> subprocess.Popen:
        """
        Start a background process with monitoring
        
        Args:
            name: Identifier for the process
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            
        Returns:
            Popen object for the started process
        """
        logger.info(f"Starting background process '{name}': {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            text=True
        )
        
        with self._lock:
            self.active_processes[name] = process
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_process,
            args=(name, process),
            daemon=True
        )
        monitor_thread.start()
        
        return process
    
    def _monitor_process(self, name: str, process: subprocess.Popen):
        """Monitor a background process for issues"""
        start_time = time.time()
        warning_timeout = self.timeout_config.long
        
        while process.poll() is None:
            elapsed = time.time() - start_time
            
            # Warn if process runs too long
            if elapsed > warning_timeout:
                logger.warning(
                    f"Background process '{name}' has been running for "
                    f"{elapsed:.0f}s (PID: {process.pid})"
                )
                warning_timeout *= 2  # Double warning interval
            
            time.sleep(1)
        
        # Process ended
        with self._lock:
            if name in self.active_processes:
                del self.active_processes[name]
        
        if process.returncode != 0:
            logger.error(f"Background process '{name}' exited with code {process.returncode}")
    
    def stop_all_processes(self, timeout: float = 10.0):
        """Stop all active background processes"""
        with self._lock:
            processes = list(self.active_processes.items())
        
        for name, process in processes:
            try:
                logger.info(f"Stopping process '{name}'")
                process.terminate()
                process.wait(timeout=timeout / len(processes))
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing process '{name}'")
                process.kill()
                process.wait()
            except Exception as e:
                logger.error(f"Error stopping process '{name}': {e}")


class HardwareDetector:
    """Hardware detection and validation with timeouts"""
    
    def __init__(self):
        self.runner = SubprocessRunner()
    
    def detect_hardware(self) -> Dict[str, Any]:
        """Detect system hardware capabilities"""
        hardware = {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'ram_gb': psutil.virtual_memory().total / (1024**3),
            'cpu_count': psutil.cpu_count(logical=False),
            'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0
        }
        
        # Platform-specific detection with timeouts
        if platform.system() == 'Windows':
            hardware.update(self._detect_windows_gpu())
        elif platform.system() == 'Darwin':
            hardware.update(self._detect_macos_gpu())
        else:
            hardware.update(self._detect_linux_gpu())
        
        return hardware
    
    def _detect_windows_gpu(self) -> Dict[str, Any]:
        """Detect GPU on Windows with timeout"""
        gpu_info = {'gpu': 'Unknown', 'gpu_memory_gb': 0}
        
        try:
            # Use WMI to get GPU info with timeout
            result = self.runner.run_command(
                ['wmic', 'path', 'win32_videocontroller', 'get', 'name,adapterram'],
                operation_type='quick',
                check=False
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    gpu_info['gpu'] = lines[1].split()[0] if lines[1] else 'Unknown'
                    
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"GPU detection failed: {e}")
        
        return gpu_info
    
    def _detect_macos_gpu(self) -> Dict[str, Any]:
        """Detect GPU on macOS with timeout"""
        gpu_info = {'gpu': 'Unknown', 'gpu_memory_gb': 0}
        
        try:
            result = self.runner.run_command(
                ['system_profiler', 'SPDisplaysDataType', '-json'],
                operation_type='quick',
                check=False
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Parse GPU info from system_profiler output
                if 'SPDisplaysDataType' in data:
                    displays = data['SPDisplaysDataType']
                    if displays and len(displays) > 0:
                        gpu_info['gpu'] = displays[0].get('sppci_model', 'Unknown')
                        
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.warning(f"GPU detection failed: {e}")
        
        return gpu_info
    
    def _detect_linux_gpu(self) -> Dict[str, Any]:
        """Detect GPU on Linux with timeout"""
        gpu_info = {'gpu': 'Unknown', 'gpu_memory_gb': 0}
        
        try:
            result = self.runner.run_command(
                ['lspci', '-v'],
                operation_type='quick',
                check=False
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'VGA' in line or '3D' in line:
                        gpu_info['gpu'] = line.split(':', 1)[1].strip() if ':' in line else 'Unknown'
                        break
                        
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"GPU detection failed: {e}")
        
        return gpu_info
    
    def determine_hardware_tier(self) -> str:
        """Determine hardware tier for model selection"""
        hardware = self.detect_hardware()
        ram_gb = hardware['ram_gb']
        
        if ram_gb >= 16:
            return 'high'
        elif ram_gb >= 8:
            return 'medium'
        elif ram_gb >= 4:
            return 'low'
        else:
            return 'minimum'


class LauncherBase:
    """
    Base class for platform launchers with timeout management
    FIXED: All operations now have proper timeouts
    """
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        self.cdrom_path = Path(cdrom_path)
        self.usb_path = Path(usb_path)
        self.runner = SubprocessRunner()
        self.hardware = HardwareDetector()
        self.setup_complete = False
        
        logger.info(f"Launcher initialized - CD-ROM: {cdrom_path}, USB: {usb_path}")
    
    def check_ollama(self) -> bool:
        """Check if Ollama is installed with timeout"""
        try:
            result = self.runner.run_command(
                ['ollama', '--version'],
                operation_type='quick',
                check=False
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.error("Ollama check timed out")
            return False
        except FileNotFoundError:
            logger.info("Ollama not found in PATH")
            return False
    
    def check_models(self) -> bool:
        """Check if required models are installed with timeout"""
        try:
            result = self.runner.run_command(
                ['ollama', 'list'],
                operation_type='default',
                check=False
            )
            
            if result.returncode != 0:
                return False
            
            # Check for required models
            output = result.stdout.lower()
            required_models = ['sunflower', 'llama']
            return any(model in output for model in required_models)
            
        except subprocess.TimeoutExpired:
            logger.error("Model check timed out")
            return False
        except Exception as e:
            logger.error(f"Model check failed: {e}")
            return False
    
    def install_ollama(self) -> bool:
        """Install Ollama with appropriate timeout"""
        system = platform.system()
        
        try:
            if system == 'Windows':
                installer = self.cdrom_path / 'ollama' / 'ollama-windows.exe'
                if installer.exists():
                    result = self.runner.run_command(
                        [str(installer), '/S'],  # Silent install
                        operation_type='install',
                        check=False
                    )
                    return result.returncode == 0
                    
            elif system == 'Darwin':
                result = self.runner.run_command(
                    ['brew', 'install', 'ollama'],
                    operation_type='install',
                    check=False
                )
                return result.returncode == 0
                
            else:  # Linux
                result = self.runner.run_command(
                    ['curl', '-fsSL', 'https://ollama.ai/install.sh', '|', 'sh'],
                    operation_type='install',
                    shell=True,
                    check=False
                )
                return result.returncode == 0
                
        except subprocess.TimeoutExpired:
            logger.error("Ollama installation timed out")
            return False
        except Exception as e:
            logger.error(f"Ollama installation failed: {e}")
            return False
    
    def load_models(self) -> bool:
        """Load AI models with appropriate timeout"""
        tier = self.hardware.determine_hardware_tier()
        
        model_map = {
            'high': 'sunflower-kids-7b',
            'medium': 'sunflower-kids-3b',
            'low': 'sunflower-kids-1b',
            'minimum': 'sunflower-kids-1b-q4'
        }
        
        model = model_map[tier]
        model_file = self.cdrom_path / 'models' / f'{model}.gguf'
        
        if not model_file.exists():
            logger.error(f"Model file not found: {model_file}")
            return False
        
        try:
            logger.info(f"Loading model: {model} (this may take a few minutes)")
            
            # Create model from file with extended timeout
            result = self.runner.run_command(
                ['ollama', 'create', model, '-f', str(model_file)],
                operation_type='long',
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"Model {model} loaded successfully")
                return True
            else:
                logger.error(f"Failed to load model: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Model loading timed out after {self.runner.timeout_config.long}s")
            return False
        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            return False
    
    def start_ollama_serve(self) -> subprocess.Popen:
        """Start Ollama serve in background"""
        return self.runner.start_background_process(
            'ollama_serve',
            ['ollama', 'serve'],
            env=os.environ.copy()
        )
    
    def check_port(self, port: int, timeout: float = 5.0) -> bool:
        """Check if a port is open with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)  # Socket timeout
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    return True
                    
            except socket.error:
                pass
            
            time.sleep(0.5)
        
        return False
    
    def wait_for_service(self, service_name: str, port: int, timeout: float = 30.0) -> bool:
        """Wait for a service to become available"""
        logger.info(f"Waiting for {service_name} on port {port}...")
        
        if self.check_port(port, timeout):
            logger.info(f"{service_name} is ready")
            return True
        else:
            logger.error(f"{service_name} failed to start within {timeout}s")
            return False
    
    def setup_system(self) -> bool:
        """Complete system setup with all timeouts"""
        try:
            # Check/install Ollama
            if not self.check_ollama():
                logger.info("Installing Ollama...")
                if not self.install_ollama():
                    return False
            
            # Start Ollama serve
            ollama_process = self.start_ollama_serve()
            
            # Wait for Ollama to be ready
            if not self.wait_for_service('Ollama', 11434, timeout=60.0):
                return False
            
            # Load models
            if not self.check_models():
                logger.info("Loading AI models...")
                if not self.load_models():
                    return False
            
            # Configure Open WebUI
            if not self.configure_webui():
                return False
            
            # Create initial profiles
            self.create_profiles()
            
            self.setup_complete = True
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def configure_webui(self) -> bool:
        """Configure Open WebUI with timeout"""
        try:
            # Create configuration directory
            config_dir = self.usb_path / "config"
            config_dir.mkdir(exist_ok=True)
            
            # Write configuration
            config = {
                'host': 'localhost',
                'port': 8080,
                'data_path': str(self.usb_path / "data"),
                'ollama_url': 'http://localhost:11434'
            }
            
            config_file = config_dir / "webui.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("Open WebUI configured")
            return True
            
        except Exception as e:
            logger.error(f"WebUI configuration failed: {e}")
            return False
    
    def create_profiles(self):
        """Create initial profile structure"""
        profiles_dir = self.usb_path / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        
        # Create default directories
        (profiles_dir / "family").mkdir(exist_ok=True)
        (profiles_dir / "sessions").mkdir(exist_ok=True)
        (profiles_dir / "logs").mkdir(exist_ok=True)
        
        logger.info("Profile structure created")
    
    def launch_application(self):
        """Launch the main Sunflower AI application with timeout"""
        main_script = self.cdrom_path / "system" / "main.py"
        
        if main_script.exists():
            try:
                # Start main application
                process = self.runner.start_background_process(
                    'sunflower_main',
                    [
                        sys.executable,
                        str(main_script),
                        "--cdrom-path", str(self.cdrom_path),
                        "--usb-path", str(self.usb_path)
                    ]
                )
                
                # Wait for application to start
                if self.wait_for_service('Sunflower AI', 8080, timeout=30.0):
                    logger.info("Sunflower AI application started successfully")
                    return True
                else:
                    logger.error("Application failed to start")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to launch application: {e}")
                return False
        else:
            logger.error(f"Main script not found: {main_script}")
            return False
    
    def cleanup(self):
        """Clean up all processes on exit"""
        logger.info("Cleaning up launcher resources...")
        self.runner.stop_all_processes()
        logger.info("Cleanup complete")


# Example platform-specific launcher implementation
class WindowsLauncher(LauncherBase):
    """Windows-specific launcher implementation"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        super().__init__(cdrom_path, usb_path)
        self.setup_windows_specific()
    
    def setup_windows_specific(self):
        """Windows-specific setup"""
        # Set Windows-specific timeouts
        self.runner.timeout_config.quick = 3.0  # Faster on Windows
        
        # Add Windows Defender exclusion for performance
        try:
            result = self.runner.run_command(
                [
                    'powershell', '-Command',
                    f'Add-MpPreference -ExclusionPath "{self.usb_path}"'
                ],
                operation_type='quick',
                check=False
            )
            if result.returncode == 0:
                logger.info("Added Windows Defender exclusion")
        except:
            pass  # Not critical if it fails


class MacOSLauncher(LauncherBase):
    """macOS-specific launcher implementation"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        super().__init__(cdrom_path, usb_path)
        self.setup_macos_specific()
    
    def setup_macos_specific(self):
        """macOS-specific setup"""
        # Set macOS-specific timeouts
        self.runner.timeout_config.quick = 5.0  # Slower on macOS due to security
        
        # Request accessibility permissions if needed
        try:
            result = self.runner.run_command(
                ['osascript', '-e', 'tell application "System Events" to return'],
                operation_type='quick',
                check=False
            )
            if result.returncode != 0:
                logger.info("Accessibility permissions may be required")
        except:
            pass


# Testing
if __name__ == "__main__":
    # Test timeout configuration
    print("Testing Launcher Common Components")
    print("=" * 50)
    
    # Test subprocess runner with timeouts
    runner = SubprocessRunner()
    
    # Test quick command
    try:
        result = runner.run_command(['echo', 'Hello World'], operation_type='quick')
        print(f"✓ Quick command succeeded: {result.stdout.strip()}")
    except subprocess.TimeoutExpired:
        print("✗ Quick command timed out")
    
    # Test hardware detection
    detector = HardwareDetector()
    hardware = detector.detect_hardware()
    print(f"\nHardware detected:")
    for key, value in hardware.items():
        print(f"  {key}: {value}")
    
    print(f"\nHardware tier: {detector.determine_hardware_tier()}")
    
    # Test timeout config
    config = TimeoutConfig()
    print(f"\nTimeout configurations:")
    print(f"  Quick: {config.quick}s")
    print(f"  Default: {config.default}s")
    print(f"  Long: {config.long}s")
    print(f"  Install: {config.install}s")
    
    print("\nAll tests completed!")

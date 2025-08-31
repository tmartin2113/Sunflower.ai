#!/usr/bin/env python3
"""
Sunflower AI Professional System - Windows Runtime Hook
Configures runtime environment for Windows deployment
Version: 6.2
"""

import os
import sys
import ctypes
import logging
from pathlib import Path

# Configure logging for runtime
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('WindowsRuntimeHook')


def configure_windows_environment():
    """Configure Windows-specific runtime environment"""
    
    # Set DPI awareness for high-resolution displays
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        logger.info("DPI awareness configured for per-monitor scaling")
    except Exception as e:
        logger.warning(f"Could not set DPI awareness: {e}")
    
    # Configure Windows error mode to suppress error dialogs
    SEM_NOGPFAULTERRORBOX = 0x0002
    SEM_FAILCRITICALERRORS = 0x0001
    SEM_NOOPENFILEERRORBOX = 0x8000
    
    error_mode = SEM_NOGPFAULTERRORBOX | SEM_FAILCRITICALERRORS | SEM_NOOPENFILEERRORBOX
    ctypes.windll.kernel32.SetErrorMode(error_mode)
    
    # Set process priority for better performance
    try:
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
        ctypes.windll.kernel32.SetPriorityClass(handle, ABOVE_NORMAL_PRIORITY_CLASS)
        logger.info("Process priority set to above normal")
    except Exception as e:
        logger.warning(f"Could not set process priority: {e}")
    
    # Configure COM for multi-threading (needed for certain Windows APIs)
    try:
        import pythoncom
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        logger.info("COM initialized for multi-threading")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Could not initialize COM: {e}")


def setup_partition_detection():
    """Setup Windows partition detection for CD-ROM and USB"""
    
    # Add WMI to path if available
    try:
        import wmi
        logger.info("WMI module available for partition detection")
    except ImportError:
        logger.warning("WMI not available, using fallback partition detection")
    
    # Configure drive letter detection
    kernel32 = ctypes.windll.kernel32
    
    # Get logical drives
    drives = kernel32.GetLogicalDrives()
    drive_letters = []
    
    for i in range(26):
        if drives & (1 << i):
            drive_letter = chr(65 + i) + ":\\"
            drive_letters.append(drive_letter)
    
    # Set environment variables for partition detection
    os.environ['SUNFLOWER_AVAILABLE_DRIVES'] = ','.join(drive_letters)
    logger.info(f"Available drives: {drive_letters}")


def configure_ollama_paths():
    """Configure Ollama paths for Windows"""
    
    # Set Ollama home directory
    if 'OLLAMA_HOME' not in os.environ:
        ollama_home = Path(os.environ.get('LOCALAPPDATA', '')) / 'Ollama'
        os.environ['OLLAMA_HOME'] = str(ollama_home)
        logger.info(f"OLLAMA_HOME set to: {ollama_home}")
    
    # Set Ollama models directory
    if 'OLLAMA_MODELS' not in os.environ:
        # Check if models are on CD-ROM partition
        if getattr(sys, 'frozen', False):
            # Running in frozen environment
            base_path = Path(sys._MEIPASS)
            models_path = base_path / 'models'
            if models_path.exists():
                os.environ['OLLAMA_MODELS'] = str(models_path)
                logger.info(f"OLLAMA_MODELS set to bundled: {models_path}")


def setup_ssl_certificates():
    """Configure SSL certificates for Windows"""
    
    # Set certificate bundle path
    if getattr(sys, 'frozen', False):
        import certifi
        import ssl
        
        # Use bundled certificates
        cert_path = Path(sys._MEIPASS) / 'certs' / 'cacert.pem'
        if cert_path.exists():
            os.environ['SSL_CERT_FILE'] = str(cert_path)
            os.environ['REQUESTS_CA_BUNDLE'] = str(cert_path)
            ssl._create_default_https_context = ssl._create_unverified_context
            logger.info(f"SSL certificates configured: {cert_path}")
        else:
            # Fallback to certifi
            os.environ['SSL_CERT_FILE'] = certifi.where()
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()


def configure_temp_directories():
    """Configure temporary directories for Windows"""
    
    # Ensure temp directories exist and are writable
    temp_base = Path(os.environ.get('TEMP', os.environ.get('TMP', '')))
    
    if temp_base:
        sunflower_temp = temp_base / 'SunflowerAI'
        sunflower_temp.mkdir(parents=True, exist_ok=True)
        
        # Set custom temp directory
        os.environ['SUNFLOWER_TEMP'] = str(sunflower_temp)
        logger.info(f"Temporary directory configured: {sunflower_temp}")


def configure_console_output():
    """Configure console output for Windows"""
    
    # Enable ANSI color codes in Windows console
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    
    handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
    mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
    kernel32.SetConsoleMode(handle, mode)
    
    # Set UTF-8 encoding for console
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)
    
    # Configure Python stdout/stderr encoding
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    
    logger.info("Console configured for UTF-8 and ANSI colors")


def detect_antivirus():
    """Detect and log antivirus software for troubleshooting"""
    
    try:
        # Use WMI to detect antivirus
        import wmi
        c = wmi.WMI(namespace="root\\SecurityCenter2")
        
        antivirus_products = []
        for antivirus in c.AntiVirusProduct():
            antivirus_products.append(antivirus.displayName)
        
        if antivirus_products:
            logger.info(f"Detected antivirus software: {', '.join(antivirus_products)}")
            # Set environment variable for application to handle
            os.environ['SUNFLOWER_DETECTED_AV'] = ','.join(antivirus_products)
    except Exception as e:
        logger.debug(f"Could not detect antivirus: {e}")


def configure_firewall_exception():
    """Attempt to configure Windows Firewall exception"""
    
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        app_name = "Sunflower AI Professional"
        
        try:
            # Add firewall exception using netsh
            import subprocess
            
            # Check if rule already exists
            check_cmd = f'netsh advfirewall firewall show rule name="{app_name}"'
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            
            if result.returncode != 0:
                # Add firewall rule
                add_cmd = f'netsh advfirewall firewall add rule name="{app_name}" ' \
                         f'dir=in action=allow program="{exe_path}" enable=yes'
                subprocess.run(add_cmd, shell=True, capture_output=True)
                logger.info(f"Firewall exception added for {app_name}")
        except Exception as e:
            logger.debug(f"Could not configure firewall: {e}")


def setup_crash_handling():
    """Setup Windows crash handling and reporting"""
    
    # Disable Windows Error Reporting dialog
    try:
        import winreg
        
        key_path = r"Software\Microsoft\Windows\Windows Error Reporting"
        
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "DontShowUI", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.info("Windows Error Reporting UI disabled")
        except Exception as e:
            logger.debug(f"Could not modify WER settings: {e}")
    except ImportError:
        pass
    
    # Set up custom exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Custom exception handler for Windows"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Write crash report
        crash_dir = Path(os.environ.get('SUNFLOWER_TEMP', os.environ.get('TEMP', '.')))
        crash_file = crash_dir / f"crash_{os.getpid()}.log"
        
        with open(crash_file, 'w') as f:
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        
        logger.info(f"Crash report saved to: {crash_file}")
    
    sys.excepthook = handle_exception


def main():
    """Main runtime hook entry point"""
    logger.info("=" * 60)
    logger.info("Sunflower AI Windows Runtime Hook Starting")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"Executable: {sys.executable}")
    logger.info("=" * 60)
    
    # Configure Windows environment
    configure_windows_environment()
    
    # Setup partition detection
    setup_partition_detection()
    
    # Configure Ollama paths
    configure_ollama_paths()
    
    # Setup SSL certificates
    setup_ssl_certificates()
    
    # Configure temporary directories
    configure_temp_directories()
    
    # Configure console output
    configure_console_output()
    
    # Detect antivirus software
    detect_antivirus()
    
    # Configure firewall exception
    configure_firewall_exception()
    
    # Setup crash handling
    setup_crash_handling()
    
    logger.info("Windows runtime hook completed successfully")


# Execute hook when imported
if __name__ != "__main__":
    main()

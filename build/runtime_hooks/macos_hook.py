#!/usr/bin/env python3
"""
Sunflower AI Professional System - macOS Runtime Hook
Configures runtime environment for macOS deployment
Version: 6.2
"""

import os
import sys
import logging
import subprocess
import platform
from pathlib import Path

# Configure logging for runtime
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('macOSRuntimeHook')


def configure_macos_environment():
    """Configure macOS-specific runtime environment"""
    
    # Set macOS specific environment variables
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Configure Cocoa application settings
    try:
        from Foundation import NSBundle, NSUserDefaults
        
        # Get application bundle
        bundle = NSBundle.mainBundle()
        if bundle:
            # Set application name for menu bar
            bundle_id = bundle.bundleIdentifier()
            if bundle_id:
                os.environ['SUNFLOWER_BUNDLE_ID'] = bundle_id
                logger.info(f"Bundle identifier: {bundle_id}")
            
            # Configure user defaults
            defaults = NSUserDefaults.standardUserDefaults()
            defaults.setBool_forKey_(True, 'NSQuitAlwaysKeepsWindows')
            defaults.synchronize()
            
    except ImportError:
        logger.debug("PyObjC not available, skipping Cocoa configuration")
    except Exception as e:
        logger.warning(f"Could not configure Cocoa settings: {e}")


def setup_partition_detection():
    """Setup macOS partition detection for CD-ROM and USB"""
    
    # Detect mounted volumes
    volumes_path = Path('/Volumes')
    mounted_volumes = []
    
    if volumes_path.exists():
        for volume in volumes_path.iterdir():
            if volume.is_dir():
                mounted_volumes.append(str(volume))
                
                # Check for Sunflower partitions
                if 'SUNFLOWER_AI' in volume.name:
                    os.environ['SUNFLOWER_CDROM_PATH'] = str(volume)
                    logger.info(f"CD-ROM partition found: {volume}")
                elif 'SUNFLOWER_DATA' in volume.name:
                    os.environ['SUNFLOWER_USB_PATH'] = str(volume)
                    logger.info(f"USB partition found: {volume}")
    
    os.environ['SUNFLOWER_MOUNTED_VOLUMES'] = ','.join(mounted_volumes)
    logger.info(f"Mounted volumes: {mounted_volumes}")
    
    # Use diskutil for advanced detection
    try:
        result = subprocess.run(
            ['diskutil', 'list', '-plist'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            os.environ['SUNFLOWER_DISKUTIL_AVAILABLE'] = '1'
            logger.info("diskutil available for partition management")
    except Exception as e:
        logger.debug(f"diskutil not available: {e}")


def configure_ollama_paths():
    """Configure Ollama paths for macOS"""
    
    # Set Ollama home directory
    if 'OLLAMA_HOME' not in os.environ:
        ollama_home = Path.home() / '.ollama'
        os.environ['OLLAMA_HOME'] = str(ollama_home)
        logger.info(f"OLLAMA_HOME set to: {ollama_home}")
    
    # Set Ollama models directory
    if 'OLLAMA_MODELS' not in os.environ:
        # Check if models are in app bundle
        if getattr(sys, 'frozen', False):
            # Running in frozen environment
            base_path = Path(sys._MEIPASS)
            models_path = base_path / 'models'
            if models_path.exists():
                os.environ['OLLAMA_MODELS'] = str(models_path)
                logger.info(f"OLLAMA_MODELS set to bundled: {models_path}")
        else:
            # Check for models on CD-ROM partition
            cdrom_path = os.environ.get('SUNFLOWER_CDROM_PATH')
            if cdrom_path:
                models_path = Path(cdrom_path) / 'models'
                if models_path.exists():
                    os.environ['OLLAMA_MODELS'] = str(models_path)
                    logger.info(f"OLLAMA_MODELS set to CD-ROM: {models_path}")


def setup_ssl_certificates():
    """Configure SSL certificates for macOS"""
    
    # Set certificate bundle path
    if getattr(sys, 'frozen', False):
        import certifi
        
        # Use bundled certificates
        cert_path = Path(sys._MEIPASS) / 'certs' / 'cacert.pem'
        if cert_path.exists():
            os.environ['SSL_CERT_FILE'] = str(cert_path)
            os.environ['REQUESTS_CA_BUNDLE'] = str(cert_path)
            logger.info(f"SSL certificates configured: {cert_path}")
        else:
            # Fallback to certifi
            os.environ['SSL_CERT_FILE'] = certifi.where()
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    
    # Trust system keychain
    os.environ['CURL_CA_BUNDLE'] = '/etc/ssl/cert.pem'


def configure_temp_directories():
    """Configure temporary directories for macOS"""
    
    # Use user's temporary directory
    temp_base = Path(os.environ.get('TMPDIR', '/tmp'))
    sunflower_temp = temp_base / 'SunflowerAI'
    sunflower_temp.mkdir(parents=True, exist_ok=True)
    
    # Set custom temp directory
    os.environ['SUNFLOWER_TEMP'] = str(sunflower_temp)
    logger.info(f"Temporary directory configured: {sunflower_temp}")
    
    # Ensure proper permissions
    try:
        os.chmod(sunflower_temp, 0o700)
    except Exception as e:
        logger.warning(f"Could not set temp directory permissions: {e}")


def configure_sandbox_permissions():
    """Configure sandbox and entitlements for macOS"""
    
    # Check if running in sandbox
    sandbox_container = os.environ.get('HOME', '').startswith('/Users/') and \
                       '/Library/Containers/' in os.environ.get('HOME', '')
    
    if sandbox_container:
        logger.info("Running in macOS sandbox container")
        os.environ['SUNFLOWER_SANDBOXED'] = '1'
        
        # Adjust paths for sandboxed environment
        container_path = Path.home()
        
        # Create necessary directories in container
        dirs_to_create = [
            container_path / 'Documents' / 'SunflowerAI',
            container_path / 'Library' / 'Application Support' / 'SunflowerAI',
            container_path / 'Library' / 'Caches' / 'SunflowerAI',
            container_path / 'Library' / 'Logs' / 'SunflowerAI'
        ]
        
        for directory in dirs_to_create:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created sandbox directory: {directory}")
    else:
        os.environ['SUNFLOWER_SANDBOXED'] = '0'
        logger.info("Running without sandbox restrictions")


def setup_accessibility_permissions():
    """Check and request accessibility permissions if needed"""
    
    try:
        # Check if we have accessibility permissions
        result = subprocess.run(
            ['osascript', '-e', 
             'tell application "System Events" to get properties'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            os.environ['SUNFLOWER_ACCESSIBILITY_ENABLED'] = '1'
            logger.info("Accessibility permissions granted")
        else:
            logger.info("Accessibility permissions not granted")
            os.environ['SUNFLOWER_ACCESSIBILITY_ENABLED'] = '0'
    except Exception as e:
        logger.debug(f"Could not check accessibility permissions: {e}")


def configure_gatekeeper():
    """Handle macOS Gatekeeper and notarization"""
    
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
        
        # Check if app is quarantined
        try:
            result = subprocess.run(
                ['xattr', '-l', app_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'com.apple.quarantine' in result.stdout:
                logger.warning("Application is quarantined by Gatekeeper")
                os.environ['SUNFLOWER_QUARANTINED'] = '1'
                
                # Attempt to remove quarantine (requires user approval)
                try:
                    subprocess.run(
                        ['xattr', '-d', 'com.apple.quarantine', app_path],
                        capture_output=True,
                        timeout=5
                    )
                    logger.info("Quarantine attribute removed")
                except Exception:
                    logger.info("Could not remove quarantine - user approval required")
            else:
                os.environ['SUNFLOWER_QUARANTINED'] = '0'
        except Exception as e:
            logger.debug(f"Could not check quarantine status: {e}")


def detect_system_integrity_protection():
    """Detect SIP (System Integrity Protection) status"""
    
    try:
        result = subprocess.run(
            ['csrutil', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if 'enabled' in result.stdout.lower():
            os.environ['SUNFLOWER_SIP_ENABLED'] = '1'
            logger.info("System Integrity Protection is enabled")
        else:
            os.environ['SUNFLOWER_SIP_ENABLED'] = '0'
            logger.info("System Integrity Protection is disabled")
    except Exception as e:
        logger.debug(f"Could not check SIP status: {e}")


def configure_display_settings():
    """Configure display and graphics settings for macOS"""
    
    try:
        from AppKit import NSScreen
        
        # Get display information
        screens = NSScreen.screens()
        if screens:
            main_screen = screens[0]
            frame = main_screen.frame()
            
            os.environ['SUNFLOWER_DISPLAY_WIDTH'] = str(int(frame.size.width))
            os.environ['SUNFLOWER_DISPLAY_HEIGHT'] = str(int(frame.size.height))
            
            # Check for Retina display
            backing_scale = main_screen.backingScaleFactor()
            if backing_scale > 1.0:
                os.environ['SUNFLOWER_RETINA_DISPLAY'] = '1'
                logger.info(f"Retina display detected (scale: {backing_scale})")
            
            logger.info(f"Display resolution: {frame.size.width}x{frame.size.height}")
    except ImportError:
        logger.debug("AppKit not available, skipping display configuration")
    except Exception as e:
        logger.warning(f"Could not configure display settings: {e}")


def setup_crash_handling():
    """Setup macOS crash handling and reporting"""
    
    # Create crash report directory
    crash_dir = Path.home() / 'Library' / 'Logs' / 'DiagnosticReports' / 'SunflowerAI'
    crash_dir.mkdir(parents=True, exist_ok=True)
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Custom exception handler for macOS"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Write crash report
        from datetime import datetime
        crash_file = crash_dir / f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}.log"
        
        with open(crash_file, 'w') as f:
            import traceback
            f.write(f"Sunflower AI Crash Report\n")
            f.write(f"========================\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"PID: {os.getpid()}\n")
            f.write(f"Platform: {platform.platform()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"\nException:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        
        logger.info(f"Crash report saved to: {crash_file}")
        
        # Show user-friendly error dialog
        try:
            from AppKit import NSAlert
            
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Sunflower AI encountered an error")
            alert.setInformativeText_(
                f"An error report has been saved. Please restart the application.\n"
                f"Error: {exc_type.__name__}: {str(exc_value)}"
            )
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        except Exception:
            pass
    
    sys.excepthook = handle_exception


def check_hardware_capabilities():
    """Check hardware capabilities on macOS"""
    
    # Check CPU architecture
    machine = platform.machine()
    os.environ['SUNFLOWER_CPU_ARCH'] = machine
    logger.info(f"CPU architecture: {machine}")
    
    # Check if running on Apple Silicon
    if machine == 'arm64':
        os.environ['SUNFLOWER_APPLE_SILICON'] = '1'
        logger.info("Running on Apple Silicon")
        
        # Check if running through Rosetta
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'sysctl.proc_translated'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip() == '1':
                os.environ['SUNFLOWER_ROSETTA'] = '1'
                logger.info("Running under Rosetta 2 translation")
        except Exception:
            pass
    
    # Get memory information
    try:
        result = subprocess.run(
            ['sysctl', '-n', 'hw.memsize'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            memory_bytes = int(result.stdout.strip())
            memory_gb = memory_bytes / (1024**3)
            os.environ['SUNFLOWER_MEMORY_GB'] = str(int(memory_gb))
            logger.info(f"System memory: {memory_gb:.1f} GB")
    except Exception as e:
        logger.debug(f"Could not get memory info: {e}")
    
    # Check for Metal support (GPU acceleration)
    try:
        result = subprocess.run(
            ['system_profiler', 'SPDisplaysDataType'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if 'Metal' in result.stdout:
            os.environ['SUNFLOWER_METAL_SUPPORT'] = '1'
            logger.info("Metal GPU acceleration available")
    except Exception:
        pass


def configure_launch_services():
    """Configure Launch Services for file associations"""
    
    if getattr(sys, 'frozen', False):
        try:
            from LaunchServices import LSSetDefaultHandlerForURLScheme
            from CoreFoundation import CFStringCreateWithCString, kCFStringEncodingUTF8
            
            # Register URL scheme handler
            bundle_id = os.environ.get('SUNFLOWER_BUNDLE_ID', 'com.sunflowerai.professional')
            url_scheme = CFStringCreateWithCString(None, 'sunflowerai', kCFStringEncodingUTF8)
            bundle_id_cf = CFStringCreateWithCString(None, bundle_id, kCFStringEncodingUTF8)
            
            LSSetDefaultHandlerForURLScheme(url_scheme, bundle_id_cf)
            logger.info("URL scheme handler registered")
            
        except ImportError:
            logger.debug("Launch Services not available")
        except Exception as e:
            logger.warning(f"Could not configure Launch Services: {e}")


def main():
    """Main runtime hook entry point"""
    logger.info("=" * 60)
    logger.info("Sunflower AI macOS Runtime Hook Starting")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"macOS Version: {platform.mac_ver()[0]}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"Executable: {sys.executable}")
    logger.info("=" * 60)
    
    # Configure macOS environment
    configure_macos_environment()
    
    # Setup partition detection
    setup_partition_detection()
    
    # Configure Ollama paths
    configure_ollama_paths()
    
    # Setup SSL certificates
    setup_ssl_certificates()
    
    # Configure temporary directories
    configure_temp_directories()
    
    # Configure sandbox permissions
    configure_sandbox_permissions()
    
    # Setup accessibility permissions
    setup_accessibility_permissions()
    
    # Configure Gatekeeper
    configure_gatekeeper()
    
    # Detect System Integrity Protection
    detect_system_integrity_protection()
    
    # Configure display settings
    configure_display_settings()
    
    # Check hardware capabilities
    check_hardware_capabilities()
    
    # Configure Launch Services
    configure_launch_services()
    
    # Setup crash handling
    setup_crash_handling()
    
    logger.info("macOS runtime hook completed successfully")


# Execute hook when imported
if __name__ != "__main__":
    main()

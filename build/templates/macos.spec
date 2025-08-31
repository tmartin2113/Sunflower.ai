# -*- mode: python ; coding: utf-8 -*-
"""
Sunflower AI Professional System - macOS Build Specification
PyInstaller spec file for macOS deployment
Version: 6.2
"""

import os
import sys
from pathlib import Path

# Determine paths
PROJECT_ROOT = Path(SPECPATH).parent.parent
SRC_DIR = PROJECT_ROOT / 'src'
RESOURCES_DIR = PROJECT_ROOT / 'resources'
BUILD_DIR = PROJECT_ROOT / 'build'

# Application metadata
APP_NAME = 'SunflowerAI'
APP_VERSION = '6.2.0'
APP_BUNDLE_ID = 'com.sunflowerai.professional'
APP_DESCRIPTION = 'Sunflower AI Professional - Family-Focused K-12 STEM Education System'
APP_COPYRIGHT = 'Copyright © 2025 Sunflower AI Systems. All rights reserved.'
APP_COMPANY = 'Sunflower AI Systems'
APP_CATEGORY = 'public.app-category.education'

block_cipher = None

# Analysis configuration
a = Analysis(
    # Main entry point
    [str(SRC_DIR / 'main.py')],
    
    # Additional search paths
    pathex=[
        str(SRC_DIR),
        str(SRC_DIR / 'models'),
        str(SRC_DIR / 'ui'),
        str(SRC_DIR / 'utils'),
        str(SRC_DIR / 'security'),
        str(SRC_DIR / 'profiles'),
        str(SRC_DIR / 'monitoring'),
        str(SRC_DIR / 'ollama_integration'),
    ],
    
    # Binary dependencies
    binaries=[
        # Include Ollama binaries if present
        (str(RESOURCES_DIR / 'ollama' / 'macos' / 'ollama'), 'ollama'),
        (str(RESOURCES_DIR / 'ollama' / 'macos' / '*.dylib'), 'ollama'),
    ],
    
    # Data files to include
    datas=[
        # Configuration files
        (str(SRC_DIR / 'config'), 'config'),
        
        # UI resources
        (str(RESOURCES_DIR / 'icons'), 'resources/icons'),
        (str(RESOURCES_DIR / 'images'), 'resources/images'),
        (str(RESOURCES_DIR / 'fonts'), 'resources/fonts'),
        
        # Documentation
        (str(PROJECT_ROOT / 'docs' / 'user_guide.pdf'), 'docs'),
        (str(PROJECT_ROOT / 'docs' / 'parent_guide.pdf'), 'docs'),
        (str(PROJECT_ROOT / 'docs' / 'safety_guide.pdf'), 'docs'),
        
        # Modelfiles (templates only, actual models on CD-ROM)
        (str(SRC_DIR / 'modelfiles' / '*.modelfile'), 'modelfiles'),
        
        # SSL certificates
        (str(RESOURCES_DIR / 'certs'), 'certs'),
        
        # License files
        (str(PROJECT_ROOT / 'LICENSE'), '.'),
        (str(PROJECT_ROOT / 'THIRD_PARTY_LICENSES.txt'), '.'),
        
        # macOS-specific resources
        (str(RESOURCES_DIR / 'icons' / 'sunflower.icns'), 'resources/icons'),
    ],
    
    # Hidden imports (modules not detected automatically)
    hiddenimports=[
        # Standard library
        'subprocess',
        'multiprocessing',
        'concurrent.futures',
        'sqlite3',
        'json',
        'hashlib',
        'secrets',
        'uuid',
        'tempfile',
        'shutil',
        'pathlib',
        'configparser',
        'logging.handlers',
        'datetime',
        'time',
        'typing',
        'enum',
        'dataclasses',
        'collections',
        'itertools',
        'functools',
        'contextlib',
        'weakref',
        'inspect',
        'traceback',
        'warnings',
        'copy',
        'pickle',
        'base64',
        'binascii',
        'zlib',
        'gzip',
        'zipfile',
        'tarfile',
        'csv',
        'xml.etree.ElementTree',
        'platform',
        'sysconfig',
        
        # macOS-specific
        'Foundation',
        'AppKit',
        'CoreFoundation',
        'Cocoa',
        'IOKit',
        'objc',
        'PyObjCTools',
        
        # Cryptography
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        
        # UI Framework
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        '_tkinter',
        
        # Networking
        'socket',
        'ssl',
        'urllib',
        'urllib.request',
        'urllib.parse',
        'http.server',
        'socketserver',
        
        # Database
        'sqlite3',
        '_sqlite3',
        
        # Third-party essentials
        'requests',
        'psutil',
        'Pillow',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'certifi',
        
        # Project-specific modules
        'src.launcher',
        'src.profile_manager',
        'src.model_selector',
        'src.conversation_handler',
        'src.safety_filter',
        'src.parent_dashboard',
        'src.encryption_manager',
        'src.hardware_detector',
        'src.partition_manager',
        'src.ollama_wrapper',
    ],
    
    # Collect all submodules
    collect_submodules=[
        'encodings',
        'asyncio',
        'concurrent',
        'multiprocessing',
        'email',
        'html',
        'http',
        'urllib',
        'xml',
        'ctypes',
        'cryptography',
        'PIL',
        'Foundation',
        'AppKit',
        'objc',
        'CoreFoundation',
    ],
    
    # Collect all data
    collect_data=[
        'certifi',
        'cryptography',
    ],
    
    # Runtime hooks
    runtime_hooks=[
        str(BUILD_DIR / 'runtime_hooks' / 'macos_hook.py'),
    ],
    
    # Exclude unnecessary modules
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'sklearn',
        'torch',
        'tensorflow',
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'docutils',
        'alabaster',
        'babel',
        'jinja2',
        'markupsafe',
        'pygments',
        'setuptools',
        'wheel',
        'pip',
        'distutils',
        'test',
        'tests',
        'testing',
        'mock',
        'unittest',
        'xmlrpc',
        'pydoc',
        'doctest',
        'lib2to3',
        'idlelib',
        'turtledemo',
    ],
    
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ archive (Python ZIP)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols on macOS
    upx=False,   # UPX not recommended on macOS
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=True,  # Enable argv emulation on macOS
    target_arch='universal2',  # Build for both Intel and Apple Silicon
    codesign_identity=None,  # Will be set during post-processing if certificate available
    entitlements_file=str(BUILD_DIR / 'templates' / 'entitlements.plist') if (BUILD_DIR / 'templates' / 'entitlements.plist').exists() else None,
    
    # macOS-specific options
    icon=str(RESOURCES_DIR / 'icons' / 'sunflower.icns'),
)

# Collect all files
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name=APP_NAME
)

# Application bundle configuration
app = BUNDLE(
    coll,
    name=f'{APP_NAME}.app',
    icon=str(RESOURCES_DIR / 'icons' / 'sunflower.icns'),
    bundle_identifier=APP_BUNDLE_ID,
    
    # Info.plist configuration
    info_plist={
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': 'Sunflower AI Professional',
        'CFBundleIdentifier': APP_BUNDLE_ID,
        'CFBundleVersion': APP_VERSION,
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'SNFL',
        'CFBundleExecutable': APP_NAME,
        'CFBundleIconFile': 'sunflower.icns',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleDevelopmentRegion': 'en',
        
        # Application category
        'LSApplicationCategoryType': APP_CATEGORY,
        
        # Minimum OS version
        'LSMinimumSystemVersion': '10.14.0',
        
        # Copyright
        'NSHumanReadableCopyright': APP_COPYRIGHT,
        
        # High resolution support
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        
        # Privacy and permissions
        'NSMicrophoneUsageDescription': 'Sunflower AI needs microphone access for voice interactions.',
        'NSCameraUsageDescription': 'Sunflower AI needs camera access for visual learning features.',
        'NSAppleEventsUsageDescription': 'Sunflower AI needs to control other applications for educational content.',
        
        # File associations
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Sunflower AI Profile',
                'CFBundleTypeRole': 'Editor',
                'CFBundleTypeExtensions': ['sfprofile'],
                'CFBundleTypeIconFile': 'sunflower.icns',
                'LSHandlerRank': 'Owner'
            },
            {
                'CFBundleTypeName': 'Sunflower AI Conversation',
                'CFBundleTypeRole': 'Viewer',
                'CFBundleTypeExtensions': ['sfconv'],
                'CFBundleTypeIconFile': 'sunflower.icns',
                'LSHandlerRank': 'Owner'
            }
        ],
        
        # URL schemes
        'CFBundleURLTypes': [
            {
                'CFBundleURLName': 'Sunflower AI URL',
                'CFBundleURLSchemes': ['sunflowerai'],
            }
        ],
        
        # Background modes
        'LSBackgroundOnly': False,
        'LSUIElement': False,
        
        # Security and sandboxing
        'LSApplicationScriptsDirectory': '~/Library/Application Scripts/com.sunflowerai.professional',
        'LSApplicationSupportDirectory': '~/Library/Application Support/SunflowerAI',
        
        # Launch services
        'LSRequiresCarbon': False,
        'LSArchitecturePriority': ['arm64', 'x86_64'],
        
        # Additional metadata
        'DTCompiler': 'com.apple.compilers.llvm.clang.1_0',
        'DTPlatformBuild': '14E222b',
        'DTPlatformName': 'macosx',
        'DTPlatformVersion': '13.3',
        'DTSDKBuild': '22E245',
        'DTSDKName': 'macosx13.3',
        'DTXcode': '1430',
        'DTXcodeBuild': '14E222b',
        
        # Custom keys for Sunflower AI
        'SunflowerAIVersion': APP_VERSION,
        'SunflowerAIBuildDate': '2025-01-01',
        'SunflowerAIModelVersion': '6.2',
        'SunflowerAISafetyLevel': 'Maximum',
    }
)

# Create entitlements file if it doesn't exist
entitlements_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Basic entitlements -->
    <key>com.apple.security.app-sandbox</key>
    <false/>
    
    <!-- File access -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    
    <!-- Network access -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    
    <!-- Device access -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.camera</key>
    <true/>
    <key>com.apple.security.device.usb</key>
    <true/>
    
    <!-- Printing -->
    <key>com.apple.security.print</key>
    <true/>
    
    <!-- Personal information -->
    <key>com.apple.security.personal-information.addressbook</key>
    <false/>
    <key>com.apple.security.personal-information.calendars</key>
    <false/>
    <key>com.apple.security.personal-information.location</key>
    <false/>
    
    <!-- Hardened runtime -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
</dict>
</plist>"""

entitlements_path = BUILD_DIR / 'templates' / 'entitlements.plist'
entitlements_path.parent.mkdir(parents=True, exist_ok=True)

if not entitlements_path.exists():
    with open(entitlements_path, 'w') as f:
        f.write(entitlements_content)
    print(f"Entitlements file created: {entitlements_path}")

# Post-build verification
print("=" * 60)
print("MACOS BUILD CONFIGURATION COMPLETE")
print(f"Application Name: {APP_NAME}")
print(f"Bundle ID: {APP_BUNDLE_ID}")
print(f"Version: {APP_VERSION}")
print(f"Target Architecture: Universal (Intel + Apple Silicon)")
print(f"Minimum macOS: 10.14 Mojave")
print(f"Sandboxing: Disabled (for USB access)")
print("=" * 60)

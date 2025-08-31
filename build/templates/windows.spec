# -*- mode: python ; coding: utf-8 -*-
"""
Sunflower AI Professional System - Windows Build Specification
PyInstaller spec file for Windows deployment
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
APP_DESCRIPTION = 'Sunflower AI Professional - Family-Focused K-12 STEM Education System'
APP_COPYRIGHT = 'Copyright © 2025 Sunflower AI Systems. All rights reserved.'
APP_COMPANY = 'Sunflower AI Systems'

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
        (str(RESOURCES_DIR / 'ollama' / 'windows' / 'ollama.exe'), 'ollama'),
        (str(RESOURCES_DIR / 'ollama' / 'windows' / '*.dll'), 'ollama'),
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
        
        # Windows-specific
        'win32api',
        'win32con',
        'win32event',
        'win32process',
        'win32security',
        'win32file',
        'win32pipe',
        'win32com.client',
        'winreg',
        'ctypes',
        'ctypes.wintypes',
        
        # Cryptography
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        
        # UI Framework (if using)
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.scrolledtext',
        
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
        
        # Third-party essentials
        'requests',
        'psutil',
        'Pillow',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        
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
        'win32com',
        'cryptography',
        'PIL',
    ],
    
    # Collect all data
    collect_data=[
        'certifi',
        'cryptography',
    ],
    
    # Runtime hooks
    runtime_hooks=[
        str(BUILD_DIR / 'runtime_hooks' / 'windows_hook.py'),
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
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'ucrtbase.dll',
        'api-ms-*.dll',
        'python*.dll',
    ],
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
    # Windows-specific options
    icon=str(RESOURCES_DIR / 'icons' / 'sunflower.ico'),
    
    # Version information
    version_file=str(BUILD_DIR / 'version_info.txt'),
    
    # UAC settings
    uac_admin=False,  # Don't require admin rights
    uac_uiaccess=False,
    
    # Manifest settings
    manifest="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="6.2.0.0"
    processorArchitecture="*"
    name="SunflowerAI.Professional"
    type="win32"
  />
  <description>Sunflower AI Professional - Family-Focused K-12 STEM Education System</description>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
        type="win32"
        name="Microsoft.Windows.Common-Controls"
        version="6.0.0.0"
        processorArchitecture="*"
        publicKeyToken="6595b64144ccf1df"
        language="*"
      />
    </dependentAssembly>
  </dependency>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 and 11 -->
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
      <!-- Windows 8.1 -->
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/>
      <!-- Windows 8 -->
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"/>
      <!-- Windows 7 -->
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/>
    </application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    </windowsSettings>
  </application>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>""",
)

# Collect all files
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'ucrtbase.dll',
        'api-ms-*.dll',
        'python*.dll',
    ],
    name=APP_NAME
)

# Additional Windows-specific build steps
if sys.platform == 'win32':
    import os
    import shutil
    
    # Create version information file
    version_info = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({APP_VERSION.replace('.', ', ')}, 0),
    prodvers=({APP_VERSION.replace('.', ', ')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{APP_COMPANY}'),
         StringStruct(u'FileDescription', u'{APP_DESCRIPTION}'),
         StringStruct(u'FileVersion', u'{APP_VERSION}'),
         StringStruct(u'InternalName', u'{APP_NAME}'),
         StringStruct(u'LegalCopyright', u'{APP_COPYRIGHT}'),
         StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
         StringStruct(u'ProductName', u'{APP_NAME}'),
         StringStruct(u'ProductVersion', u'{APP_VERSION}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
    
    version_file_path = BUILD_DIR / 'version_info.txt'
    version_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(version_file_path, 'w') as f:
        f.write(version_info)
    
    print(f"Version information file created: {version_file_path}")

# Post-build verification
print("=" * 60)
print("WINDOWS BUILD CONFIGURATION COMPLETE")
print(f"Application Name: {APP_NAME}")
print(f"Version: {APP_VERSION}")
print(f"Target Architecture: x86_64")
print(f"Console Mode: Disabled")
print(f"UAC Requirements: Standard User")
print("=" * 60)

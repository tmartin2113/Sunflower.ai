# Sunflower AI Education System

Safe, adaptive AI-powered STEM education for children ages 2-18.

## Overview

Sunflower AI is a family-focused educational system that provides personalized STEM learning through age-adaptive AI tutors. The system runs completely offline from a USB drive, ensuring privacy and safety.

## Features

- **Age-Adaptive AI**: Automatically adjusts complexity based on child's age
- **Complete STEM Coverage**: Science, Technology, Engineering, Mathematics
- **Parent Controls**: Password-protected setup and session monitoring
- **Offline Operation**: No internet required after initial setup
- **Multi-Child Support**: Individual profiles for each family member
- **USB Portability**: Take your AI tutor anywhere

## System Requirements

### Minimum
- **OS**: Windows 10+ or macOS 10.14+
- **RAM**: 4GB
- **CPU**: 2 cores
- **Storage**: 16GB USB drive

### Recommended
- **RAM**: 8GB or more
- **CPU**: 4+ cores
- **GPU**: Optional but improves performance

## Quick Start

1. Insert the Sunflower AI USB drive
2. Windows: Run `SunflowerAI.exe` / macOS: Open `SunflowerAI.app`
3. Create a parent account
4. Add child profiles
5. Start learning!

## Development Setup

```bash
# Clone repository
git clone https://github.com/sunflowerai/sunflower-ai.git
cd sunflower-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run development version
python UNIVERSAL_LAUNCHER.py
```

## Building for Production

```bash
# Build all components
python scripts/build_all.py

# Create USB image
python deployment/create_usb.py
```

## Project Structure

```
sunflower-ai/
├── src/                  # Application source code
├── modelfiles/          # AI model configurations
├── build/               # Build scripts
├── resources/           # Images, icons, fonts
└── docs/               # Documentation
```

## License

Copyright © 2025 Sunflower AI. All rights reserved.
See LICENSE file for details.

## Support

This is a no-support product. Please refer to the included documentation.

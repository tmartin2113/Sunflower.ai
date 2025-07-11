#!/usr/bin/env python3
"""
Asset management for Sunflower AI images.
"""

import os
from pathlib import Path

def get_image_path(image_name: str) -> str:
    """
    Constructs the full path to an image in the assets directory.
    This handles running from source or from a bundled application.
    """
    # This path is relative to this file's location
    base_path = Path(__file__).parent.parent.parent / "assets" / "images"
    
    # In a real deployed app (e.g., using PyInstaller), assets might be
    # in a different location. This simple approach works for source-based runs.
    # A more robust solution would check `sys._MEIPASS` for bundled apps.
    
    image_path = base_path / image_name
    
    if not image_path.exists():
        print(f"Warning: Image not found at {image_path}")
        # Return path to a placeholder to avoid crashes
        return str(base_path / "ui_elements" / "placeholder.png")
        
    return str(image_path) 
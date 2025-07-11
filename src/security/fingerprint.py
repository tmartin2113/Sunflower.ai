#!/usr/bin/env python3
"""
Hardware Fingerprinting for Sunflower AI
Generates a unique and stable identifier for the host machine.
"""

import platform
import subprocess
import hashlib
from typing import Optional

def _get_machine_info() -> str:
    """
    Gathers a string of unique hardware identifiers.
    This is not foolproof but provides a reasonable "best effort" fingerprint.
    """
    system = platform.system()
    info_str = ""
    
    # Common identifiers
    info_str += platform.processor()
    info_str += platform.machine()
    info_str += platform.node()

    try:
        if system == "Windows":
            # Motherboard serial number is a good unique identifier
            command = "wmic baseboard get serialnumber"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                info_str += result.stdout.strip().split('\n')[-1]
            
            # CPU ID
            command = "wmic cpu get processorid"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                info_str += result.stdout.strip().split('\n')[-1]

        elif system == "Darwin": # macOS
            # System serial number
            command = "ioreg -l | grep IOPlatformSerialNumber"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                info_str += result.stdout.strip().split('=')[-1]

        elif system == "Linux":
            # Machine ID is usually stable
            with open("/var/lib/dbus/machine-id", "r") as f:
                info_str += f.read().strip()
            # Motherboard serial
            with open("/sys/class/dmi/id/board_serial", "r") as f:
                info_str += f.read().strip()

    except (IOError, IndexError, subprocess.CalledProcessError) as e:
        # If any command fails, we just get less unique info, which is fine.
        print(f"Could not get some machine info for fingerprint: {e}")

    return info_str


def generate_fingerprint() -> str:
    """
    Generates a SHA-256 hash of the machine's hardware info.

    Returns:
        A hex string representing the machine's fingerprint.
    """
    machine_info = _get_machine_info()
    
    # Hash the collected information
    fingerprint = hashlib.sha256(machine_info.encode()).hexdigest()
    
    return fingerprint


if __name__ == '__main__':
    print("--- Generating Machine Fingerprint ---")
    fp = generate_fingerprint()
    
    if fp:
        print(f"Machine Fingerprint: {fp}")
        print(f"Length: {len(fp)} characters")
        # Verify it's a valid SHA-256 hex string
        import re
        assert re.match(r"^[a-f0-9]{64}$", fp)
        print("Fingerprint appears valid.")
    else:
        print("Failed to generate fingerprint.")

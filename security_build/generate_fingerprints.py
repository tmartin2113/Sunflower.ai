import os
import hashlib
import json
from pathlib import Path
from typing import Dict

def generate_fingerprints(target_dir: Path) -> Dict[str, str]:
    """
    Scans a directory and generates SHA-256 fingerprints for all files.

    This function recursively walks through the target directory, calculates
    the SHA-256 hash for each file, and returns a dictionary mapping
    relative file paths to their hex-digest hashes.

    Args:
        target_dir: The directory to scan.

    Returns:
        A dictionary where keys are relative file paths (as strings) and
        values are their SHA-256 hashes.
    """
    fingerprints = {}
    if not target_dir.is_dir():
        print(f"Error: Target '{target_dir}' is not a valid directory.")
        return fingerprints

    print(f"Generating fingerprints for all files in '{target_dir}'...")

    for root, _, files in os.walk(target_dir):
        for filename in files:
            file_path = Path(root) / filename
            
            # Use binary read mode for consistent hashing
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            
            # Store the path relative to the target directory
            relative_path = file_path.relative_to(target_dir).as_posix()
            fingerprints[relative_path] = sha256_hash

    print(f"Generated fingerprints for {len(fingerprints)} files.")
    return fingerprints

def save_fingerprints(fingerprints: Dict[str, str], output_file: Path):
    """
    Saves the fingerprint dictionary to a JSON file.

    Args:
        fingerprints: The dictionary of file paths and hashes.
        output_file: The path to the output JSON file.
    """
    if not fingerprints:
        print("Warning: Fingerprint dictionary is empty. Nothing to save.")
        return

    # Ensure the parent directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving fingerprints to '{output_file}'...")
    try:
        with open(output_file, "w") as f:
            json.dump(fingerprints, f, indent=4)
        print("Fingerprints saved successfully.")
    except IOError as e:
        print(f"Error saving fingerprints to file: {e}")

if __name__ == '__main__':
    # This script would typically be run on the OBFUSCATED source,
    # but for a standalone test, we can run it on the normal source.
    project_root = Path(__file__).parent.parent
    source_to_scan = project_root / 'src'
    
    # The final manifest will be stored in the build directory
    build_path = project_root / 'build'
    fingerprint_file = build_path / 'fingerprints.json'

    print("--- Starting Fingerprint Generation ---")
    generated_prints = generate_fingerprints(source_to_scan)
    
    if generated_prints:
        save_fingerprints(generated_prints, fingerprint_file)
        print(f"\nFingerprint generation process finished. Manifest saved to {fingerprint_file}")
    else:
        print("\nFingerprint generation process failed.")

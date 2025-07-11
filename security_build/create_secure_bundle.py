import shutil
from pathlib import Path

from obfuscate_code import obfuscate_project
from generate_fingerprints import generate_fingerprints, save_fingerprints
from embed_protection import generate_keys, sign_fingerprints, save_secure_manifest

def main():
    """
    Main orchestration function to create the full secure bundle.
    """
    # --- 1. Define Paths ---
    project_root = Path(__file__).parent.parent
    source_dir = project_root / 'src'
    config_dir = project_root / 'config'
    
    # Build directories
    build_dir = project_root / 'build'
    obfuscated_dir = build_dir / 'obfuscated_src'
    
    # Distribution (final output) directory
    dist_dir = project_root / 'dist'
    dist_src_dir = dist_dir / 'src'
    dist_config_dir = dist_dir / 'config'
    
    # Intermediate and final artifact paths
    fingerprints_file = build_dir / 'fingerprints.json'
    secure_manifest_file = dist_dir / 'secure_manifest.json'
    private_key_file = build_dir / 'signing_key.pem'
    public_key_file = dist_dir / 'signing_key.pub' # Public key goes to dist

    print("--- Starting Secure Bundle Creation ---")
    print(f"Distribution directory: {dist_dir}")

    # --- 2. Clean and Prepare Directories ---
    if dist_dir.exists():
        print("Cleaning previous distribution build...")
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    print("Created clean distribution directory.")

    # --- 3. Obfuscate Source Code ---
    print("\nStep 1: Obfuscating source code...")
    if not obfuscate_project(source_dir, obfuscated_dir):
        print("Build failed: Code obfuscation error.")
        return
    print("Source code obfuscated successfully.")

    # --- 4. Generate Fingerprints for Obfuscated Code ---
    print("\nStep 2: Generating fingerprints for obfuscated code...")
    fingerprints = generate_fingerprints(obfuscated_dir)
    if not fingerprints:
        print("Build failed: Fingerprint generation error.")
        return
    # Save the intermediate (unsigned) fingerprints file
    save_fingerprints(fingerprints, fingerprints_file)
    print("Fingerprints generated successfully.")

    # --- 5. Sign the Fingerprint Manifest ---
    print("\nStep 3: Signing the fingerprint manifest...")
    # Ensure keys exist, generate if they don't
    if not private_key_file.exists():
        generate_keys(private_key_file, public_key_file)
        
    try:
        secure_manifest = sign_fingerprints(fingerprints_file, private_key_file)
        save_secure_manifest(secure_manifest, secure_manifest_file)
        print("Fingerprint manifest signed and saved successfully.")
    except Exception as e:
        print(f"Build failed: Could not sign manifest. Error: {e}")
        return

    # --- 6. Assemble the Distribution Bundle ---
    print("\nStep 4: Assembling final distribution bundle...")
    # Copy obfuscated source code to dist
    shutil.copytree(obfuscated_dir, dist_src_dir)
    print(f"Copied obfuscated source to {dist_src_dir}")
    
    # Copy configuration files to dist
    shutil.copytree(config_dir, dist_config_dir)
    print(f"Copied config files to {dist_config_dir}")

    # The public key and secure manifest are already saved to their final locations.
    print(f"Public key for runtime verification is at {public_key_file}")
    print(f"Secure manifest for runtime verification is at {secure_manifest_file}")

    print("\n--- Secure Bundle Creation Finished Successfully! ---")
    print(f"Ready for packaging from the '{dist_dir}' directory.")

if __name__ == '__main__':
    main()

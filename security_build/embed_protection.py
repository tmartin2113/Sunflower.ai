import json
from pathlib import Path
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

def generate_keys(private_key_path: Path, public_key_path: Path):
    """
    Generates a new RSA private and public key pair for signing.
    In a real production environment, you would generate this once and
    store the private key securely.
    """
    print("Generating new RSA key pair for signing...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # Serialize and save the private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    print(f"Private key saved to {private_key_path}")

    # Serialize and save the public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
    print(f"Public key saved to {public_key_path}")

def sign_fingerprints(fingerprint_path: Path, private_key_path: Path) -> dict:
    """
    Signs the fingerprint manifest with the private key.

    Args:
        fingerprint_path: Path to the JSON file containing fingerprints.
        private_key_path: Path to the private key (.pem file).

    Returns:
        A dictionary containing the original data and the signature.
    """
    if not fingerprint_path.exists():
        raise FileNotFoundError(f"Fingerprint file not found at {fingerprint_path}")
    if not private_key_path.exists():
        raise FileNotFoundError(f"Private key not found at {private_key_path}")

    print(f"Loading private key from {private_key_path}...")
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )

    print(f"Loading fingerprint data from {fingerprint_path}...")
    with open(fingerprint_path, "r") as f:
        fingerprint_data = json.load(f)

    # The data must be in a consistent, sorted format to ensure the hash is stable
    # We dump it to a string with no whitespace and sorted keys.
    serialized_data = json.dumps(fingerprint_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

    print("Signing fingerprint data...")
    signature = private_key.sign(
        serialized_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    # The signature is binary, so we encode it in Base64 for JSON serialization
    b64_signature = base64.b64encode(signature).decode('utf-8')
    
    secure_manifest = {
        "fingerprints": fingerprint_data,
        "signature": b64_signature
    }
    
    print("Data signed successfully.")
    return secure_manifest

def save_secure_manifest(manifest_data: dict, output_path: Path):
    """Saves the signed manifest to a file."""
    print(f"Saving secure manifest to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest_data, f, indent=4)
    print("Secure manifest saved.")


if __name__ == '__main__':
    project_root = Path(__file__).parent.parent
    build_dir = project_root / 'build'
    
    # Input file (created by the previous script)
    fingerprints_file = build_dir / 'fingerprints.json'
    
    # Output file
    secure_manifest_file = build_dir / 'secure_manifest.json'
    
    # Key paths
    private_key_file = build_dir / 'signing_key.pem'
    public_key_file = build_dir / 'signing_key.pub'

    print("--- Starting Security Embedding ---")

    # Step 1: Ensure keys exist. Generate them if they don't.
    if not private_key_file.exists():
        generate_keys(private_key_file, public_key_file)

    # Step 2: Sign the fingerprint file.
    try:
        signed_data = sign_fingerprints(fingerprints_file, private_key_file)
    
        # Step 3: Save the new secure manifest.
        save_secure_manifest(signed_data, secure_manifest_file)
        print("\nSecurity embedding process finished successfully.")
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please ensure 'generate_fingerprints.py' has been run first.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

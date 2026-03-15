"""
Phase 0: Security & Interface Foundation
- Keyring-based master password storage
- AES-256-GCM encryption/decryption with Nonce & Tag handling
"""

import os
import json
import base64
import uuid
import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# ============== Configuration ==============
SERVICE_NAME = "EncryptedCredentialManager"
KEYRING_USERNAME = "master_password"
DEFAULT_DATA_DIR = os.path.expanduser("~/.ecm_credentials")
CREDENTIALS_FILE = "credentials.json"

# ============== Keyring (Master Password) ==============
def get_master_password() -> str | None:
    """Retrieve master password from OS keyring."""
    return keyring.get_password(SERVICE_NAME, KEYRING_USERNAME)

def set_master_password(password: str) -> None:
    """Store master password in OS keyring."""
    keyring.set_password(SERVICE_NAME, KEYRING_USERNAME, password)

def delete_master_password() -> bool:
    """Delete master password from keyring. Returns True if deleted."""
    try:
        keyring.delete_password(SERVICE_NAME, KEYRING_USERNAME)
        return True
    except keyring.errors.PasswordDeleteError:
        return False

def has_master_password() -> bool:
    """Check if master password exists in keyring."""
    return get_master_password() is not None

# ============== Key Derivation ==============
def derive_key(master_password: str, salt: bytes) -> bytes:
    """
    Derive encryption key from master password using PBKDF2.
    For production, Argon2id is recommended (see note below).
    
    Returns 256-bit (32 bytes) key for AES-256.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for AES-256
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    return kdf.derive(master_password.encode("utf-8"))

# ============== AES-256-GCM Encryption ==============
def generate_salt(length: int = 32) -> bytes:
    """Generate cryptographically secure random salt."""
    return os.urandom(length)

def generate_nonce(length: int = 12) -> bytes:
    """Generate 12-byte nonce for AES-GCM (NIST recommended)."""
    return os.urandom(length)

def encrypt(plaintext: str, key: bytes) -> tuple[bytes, bytes]:
    """
    Encrypt plaintext using AES-256-GCM.
    
    Returns:
        nonce: 12 bytes
        ciphertext: encrypted data (includes 16-byte auth tag)
    """
    nonce = generate_nonce(12)
    aesgcm = AESGCM(key)
    # GCM appends the auth tag to ciphertext automatically
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce, ciphertext

def decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> str:
    """
    Decrypt ciphertext using AES-256-GCM.
    
    Returns:
        plaintext: decrypted string
    """
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")

# ============== Data Directory ==============
def ensure_data_dir(data_dir: str = None) -> str:
    """Ensure data directory exists."""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def get_credentials_path(data_dir: str = None) -> str:
    """Get full path to credentials file."""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    return os.path.join(data_dir, CREDENTIALS_FILE)

# ============== Initialization ==============
def initialize_credential_store(data_dir: str = DEFAULT_DATA_DIR, 
                                  force: bool = False) -> dict:
    """
    Initialize credential store if not exists.
    
    Returns the loaded/created store structure.
    """
    path = get_credentials_path(data_dir)
    
    if os.path.exists(path) and not force:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Create new store
    ensure_data_dir(data_dir)  # Ensure directory exists
    salt = generate_salt(32)
    store = {
        "version": "1.1",
        "kdf_params": {
            "algorithm": "pbkdf2",
            "salt": base64.b64encode(salt).decode("utf-8"),
            "iterations": 100_000
        },
        "entries": []
    }
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    
    return store

# ============== Utility Functions ==============
def generate_entry_id() -> str:
    """Generate unique entry ID."""
    return str(uuid.uuid4())

def store_to_json(store: dict, data_dir: str = DEFAULT_DATA_DIR) -> None:
    """Safely write credential store to disk."""
    path = get_credentials_path(data_dir)
    # Atomic write: write to temp, then rename
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)

def load_store(data_dir: str = DEFAULT_DATA_DIR) -> dict:
    """Load credential store from disk."""
    path = get_credentials_path(data_dir)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Credential store not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ============== CLI Demo (for testing) ==============
# Run with: python phase0_security_base.py
# For non-interactive testing, set ENV: ECM_TEST_MODE=1

if __name__ == "__main__":
    import sys
    import io
    
    print("=== ECM Security Base - Phase 0 ===\n")
    
    # Check/setup master password
    if not has_master_password():
        test_mode = os.environ.get("ECM_TEST_MODE", "0") == "1"
        if test_mode:
            # Non-interactive test mode
            test_pw = "TestPassword123!"
            set_master_password(test_pw)
            print("[*] Test mode: master password set\n")
        else:
            print("[*] No master password found. Please set one:")
            try:
                pw = input("Enter master password: ")
                set_master_password(pw)
                print("[OK] Master password stored in OS keyring\n")
            except EOFError:
                print("[!] Non-interactive mode detected. Run with ECM_TEST_MODE=1 for testing.")
                sys.exit(0)
    else:
        print("[OK] Master password exists in keyring\n")
    
    # Initialize store
    store = initialize_credential_store()
    print(f"[OK] Credential store initialized at: {get_credentials_path()}")
    print(f"    KDF salt (base64): {store['kdf_params']['salt'][:20]}...")
    print(f"    Entries count: {len(store['entries'])}\n")
    
    # Demo encryption/decryption
    print("[*] Testing encryption/decryption...")
    master_pw = get_master_password()
    salt = base64.b64decode(store["kdf_params"]["salt"])
    key = derive_key(master_pw, salt)
    
    test_data = "MySecretPassword123"
    nonce, ciphertext = encrypt(test_data, key)
    decrypted = decrypt(ciphertext, key, nonce)
    
    print(f"    Original:  {test_data}")
    print(f"    Nonce:     {base64.b64encode(nonce).decode()}")
    print(f"    Cipher:    {base64.b64encode(ciphertext).decode()[:40]}...")
    print(f"    Decrypted: {decrypted}")
    print(f"    Match:     {'OK' if test_data == decrypted else 'FAIL'}\n")
    
    print("[OK] Phase 0 ready for Phase 1!")

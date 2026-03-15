"""
Phase 1: Credential Management Module
- CRUD operations for credentials
- Secure storage with encryption
- Sanitized queries (no plaintext passwords to LLM)
"""

import os
import json
import base64
from typing import Optional
from phase0_security_base import (
    get_master_password,
    derive_key,
    encrypt,
    decrypt,
    generate_entry_id,
    load_store,
    store_to_json,
    get_credentials_path,
    ensure_data_dir,
)

# ============== Credential Entry Operations ==============

def add_credential(
    name: str,
    url: str,
    username: str,
    password: str,
    notes: str = "",
    data_dir: str = None
) -> dict:
    """
    Add a new credential entry.
    
    Args:
        name: Display name (e.g., "GitHub")
        url: Website URL
        username: Login username/email
        password: Plaintext password (will be encrypted)
        notes: Optional notes
        data_dir: Custom data directory
    
    Returns:
        Created entry with encrypted password
    """
    # Get master password and derive key
    master_pw = get_master_password()
    if not master_pw:
        raise PermissionError("Master password not found. Please set it first.")
    
    store = load_store(data_dir)
    salt = base64.b64decode(store["kdf_params"]["salt"])
    key = derive_key(master_pw, salt)
    
    # Encrypt password
    nonce, ciphertext = encrypt(password, key)
    
    # Create entry
    entry = {
        "id": generate_entry_id(),
        "name": name,
        "url": url,
        "username": username,
        "encryption_params": {
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "tag": base64.b64encode(ciphertext[-16:]).decode("utf-8")  # GCM tag is last 16 bytes
        },
        "password_encrypted": base64.b64encode(ciphertext).decode("utf-8"),
        "notes": notes
    }
    
    store["entries"].append(entry)
    store_to_json(store, data_dir)
    
    return {
        "id": entry["id"],
        "name": entry["name"],
        "url": entry["url"],
        "username": entry["username"],
        "status": "added"
    }

def list_credentials(data_dir: str = None) -> list[dict]:
    """
    List all credentials (SANITIZED - no plaintext passwords).
    
    Returns:
        List of entries with id, name, url, username only
    """
    store = load_store(data_dir)
    
    sanitized = []
    for entry in store["entries"]:
        sanitized.append({
            "id": entry["id"],
            "name": entry["name"],
            "url": entry["url"],
            "username": entry["username"],
            "notes": entry.get("notes", "")
        })
    
    return sanitized

def get_credential(entry_id: str, data_dir: str = None) -> Optional[dict]:
    """
    Get a single credential by ID (SANITIZED - no plaintext password).
    """
    store = load_store(data_dir)
    
    for entry in store["entries"]:
        if entry["id"] == entry_id:
            return {
                "id": entry["id"],
                "name": entry["name"],
                "url": entry["url"],
                "username": entry["username"],
                "notes": entry.get("notes", "")
            }
    
    return None

def get_credential_by_name(name: str, data_dir: str = None) -> Optional[dict]:
    """
    Find credential by name (SANITIZED).
    """
    store = load_store(data_dir)
    
    for entry in store["entries"]:
        if entry["name"].lower() == name.lower():
            return {
                "id": entry["id"],
                "name": entry["name"],
                "url": entry["url"],
                "username": entry["username"],
                "notes": entry.get("notes", "")
            }
    
    return None

def update_credential(
    entry_id: str,
    name: str = None,
    url: str = None,
    username: str = None,
    password: str = None,
    notes: str = None,
    data_dir: str = None
) -> dict:
    """
    Update an existing credential.
    
    Args:
        entry_id: ID of entry to update
        name: New name (optional)
        url: New URL (optional)
        username: New username (optional)
        password: New password - if provided, will be re-encrypted
        notes: New notes (optional)
    
    Returns:
        Updated entry (sanitized)
    """
    master_pw = get_master_password()
    if not master_pw:
        raise PermissionError("Master password not found.")
    
    store = load_store(data_dir)
    salt = base64.b64decode(store["kdf_params"]["salt"])
    key = derive_key(master_pw, salt)
    
    # Find entry
    for entry in store["entries"]:
        if entry["id"] == entry_id:
            # Update fields
            if name is not None:
                entry["name"] = name
            if url is not None:
                entry["url"] = url
            if username is not None:
                entry["username"] = username
            if notes is not None:
                entry["notes"] = notes
            
            # Re-encrypt password if provided
            if password is not None:
                nonce, ciphertext = encrypt(password, key)
                entry["encryption_params"]["nonce"] = base64.b64encode(nonce).decode("utf-8")
                entry["password_encrypted"] = base64.b64encode(ciphertext).decode("utf-8")
            
            store_to_json(store, data_dir)
            
            return {
                "id": entry["id"],
                "name": entry["name"],
                "url": entry["url"],
                "username": entry["username"],
                "status": "updated"
            }
    
    raise ValueError(f"Entry not found: {entry_id}")

def delete_credential(entry_id: str, data_dir: str = None) -> bool:
    """
    Delete a credential by ID.
    
    Returns:
        True if deleted, False if not found
    """
    store = load_store(data_dir)
    
    original_count = len(store["entries"])
    store["entries"] = [e for e in store["entries"] if e["id"] != entry_id]
    
    if len(store["entries"]) < original_count:
        store_to_json(store, data_dir)
        return True
    
    return False

def _decrypt_password(entry_id: str, data_dir: str = None) -> str:
    """
    Internal function to decrypt password.
    Used ONLY by auto-login module - never exposed to LLM.
    
    Returns:
        Plaintext password
    """
    master_pw = get_master_password()
    if not master_pw:
        raise PermissionError("Master password not found.")
    
    store = load_store(data_dir)
    salt = base64.b64decode(store["kdf_params"]["salt"])
    key = derive_key(master_pw, salt)
    
    for entry in store["entries"]:
        if entry["id"] == entry_id:
            nonce = base64.b64decode(entry["encryption_params"]["nonce"])
            ciphertext = base64.b64decode(entry["password_encrypted"])
            return decrypt(ciphertext, key, nonce)
    
    raise ValueError(f"Entry not found: {entry_id}")

# ============== CLI Demo ==============
if __name__ == "__main__":
    import sys
    
    print("=== ECM Credential Management - Phase 1 ===\n")
    
    # Demo: Add credentials
    print("[*] Adding demo credentials...")
    
    try:
        add_credential(
            name="GitHub",
            url="https://github.com",
            username="user@example.com",
            password="MySecretPass123",
            notes="Main account"
        )
        print("    [OK] Added GitHub")
        
        add_credential(
            name="Gmail",
            url="https://mail.google.com",
            username="myemail@gmail.com",
            password="AnotherPass456",
            notes="Personal email"
        )
        print("    [OK] Added Gmail")
        
    except Exception as e:
        print(f"    [INFO] {e}")
    
    # List credentials (sanitized)
    print("\n[*] Listing credentials (sanitized)...")
    creds = list_credentials()
    for c in creds:
        print(f"    - {c['name']} | {c['username']} | {c['url']}")
    
    # Get by name
    print("\n[*] Finding 'GitHub'...")
    gh = get_credential_by_name("GitHub")
    if gh:
        print(f"    Found: {gh['name']} ({gh['id']})")
    
    # Update
    print("\n[*] Updating GitHub username...")
    if gh:
        update_credential(gh["id"], username="newuser@example.com")
        print("    [OK] Updated")
    
    # List again
    print("\n[*] Final list:")
    for c in list_credentials():
        print(f"    - {c['name']} | {c['username']}")
    
    print("\n[OK] Phase 1 ready for Phase 2!")

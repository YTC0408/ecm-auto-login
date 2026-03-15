"""
ECM Auto Login - OpenClaw Skill Wrapper
Zero-Knowledge Credential Management & Auto-Login

This module exposes safe interfaces to LLM agents.
All decryption happens internally - LLM NEVER sees plaintext passwords.
"""

import os
import sys
import json
from typing import Optional

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from phase0_security_base import (
    get_master_password,
    set_master_password,
    has_master_password,
    get_credentials_path,
    ensure_data_dir,
)
from phase1_credential_manager import (
    add_credential,
    list_credentials,
    get_credential,
    get_credential_by_name,
    update_credential,
    delete_credential,
)
from phase2_auto_login import login_to_website


# ============== Tool Definitions ==============

def ecm_set_master_password(password: str) -> dict:
    """
    Set the master password in OS keyring.
    """
    try:
        set_master_password(password)
        return {"success": True, "message": "Master password stored securely"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def ecm_has_master_password() -> dict:
    """
    Check if master password exists.
    """
    return {"exists": has_master_password()}


def ecm_add_credential(
    name: str,
    url: str,
    username: str,
    password: str,
    notes: str = ""
) -> dict:
    """
    Add a new credential.
    
    NOTE: password is used internally and NEVER exposed to LLM.
    """
    try:
        result = add_credential(name, url, username, password, notes)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def ecm_list_credentials() -> dict:
    """
    List all credentials (sanitized - no passwords).
    """
    try:
        creds = list_credentials()
        return {"success": True, "credentials": creds}
    except Exception as e:
        return {"success": False, "error": str(e)}


def ecm_get_credential(name: str) -> dict:
    """
    Get credential by name (sanitized).
    """
    try:
        cred = get_credential_by_name(name)
        if cred:
            return {"success": True, "credential": cred}
        return {"success": False, "error": "Not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def ecm_update_credential(
    entry_id: str,
    name: str = None,
    url: str = None,
    username: str = None,
    password: str = None,
    notes: str = None
) -> dict:
    """
    Update a credential.
    """
    try:
        result = update_credential(entry_id, name, url, username, password, notes)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def ecm_delete_credential(entry_id: str) -> dict:
    """
    Delete a credential.
    """
    try:
        success = delete_credential(entry_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


def ecm_login(site_name: str, headless: bool = True) -> dict:
    """
    Auto-login to a website.
    
    This is a CLOSED-LOOP operation:
    - Looks up credential
    - Decrypts password internally (LLM never sees it)
    - Opens browser and performs login
    
    Returns:
        success: bool
        message: str
        paused: bool (if true, reason explains why)
    """
    import asyncio
    
    try:
        result = asyncio.run(login_to_website(site_name, headless=headless))
        return result
    except Exception as e:
        return {
            "success": False,
            "site": site_name,
            "message": str(e),
            "paused": False
        }


# ============== CLI / Testing ==============
if __name__ == "__main__":
    print("=== ECM Auto Login Skill ===\n")
    
    # Test basic functions
    print("[*] Checking master password...")
    result = ecm_has_master_password()
    print(f"    {result}")
    
    print("\n[*] Listing credentials...")
    result = ecm_list_credentials()
    print(f"    Success: {result.get('success')}")
    if result.get('credentials'):
        for c in result['credentials']:
            print(f"    - {c['name']}: {c['username']}")
    
    print("\n[OK] Skill wrapper ready!")

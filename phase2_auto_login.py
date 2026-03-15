"""
Phase 2: Auto-Login Module
- Playwright + stealth integration
- Closed-loop: decrypt -> fill -> submit
- 2FA/Captcha manual handover detection
"""

import os
import sys
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Playwright, Browser, Page, BrowserContext

# Import from Phase 0/1
from phase0_security_base import get_master_password, derive_key, decrypt, base64, load_store
from phase1_credential_manager import get_credential_by_name, _decrypt_password

# ============== Configuration ==============
DEFAULT_DATA_DIR = os.path.expanduser("~/.ecm_credentials")

# ============== Auto-Login Engine ==============
class AutoLoginEngine:
    """Closed-loop auto-login with stealth browser."""
    
    def __init__(self, data_dir: str = None, headless: bool = True):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Detection flags
        self.paused_for_manual = False
        self.pause_reason: Optional[str] = None
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """Initialize stealth browser."""
        self.playwright = await async_playwright().start()
        
        # Use stealth to bypass basic detection
        from playwright_stealth import stealth
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        
        # Apply stealth patches
        await stealth(self.page)
        
        print("[OK] Stealth browser started")
    
    async def close(self):
        """Clean up resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("[OK] Browser closed")
    
    async def navigate_to(self, url: str):
        """Navigate to URL and wait for load."""
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
    
    async def detect_blockers(self) -> tuple[bool, str]:
        """
        Detect captcha, 2FA, or other blockers.
        
        Returns:
            (is_blocked, reason)
        """
        # Check for common captcha indicators
        captcha_selectors = [
            'iframe[src*="captcha"]',
            '.captcha',
            '#captcha',
            '[class*="captcha"]',
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]'
        ]
        
        for sel in captcha_selectors:
            if await self.page.query_selector(sel):
                return True, "captcha"
        
        # Check for 2FA input (common patterns)
        twofa_selectors = [
            'input[name*="code"]',
            'input[name*="otp"]',
            'input[name*="totp"]',
            'input[aria-label*="code"]',
            'input[placeholder*="code"]',
            'input[placeholder*="OTP"]'
        ]
        
        for sel in twofa_selectors:
            if await self.page.query_selector(sel):
                return True, "twofa"
        
        # Check for verification/email confirmation
        verification_texts = [
            "check your email",
            "verify your",
            "confirmation",
            "two-factor",
            "2fa"
        ]
        
        page_text = await self.page.content()
        for text in verification_texts:
            if text.lower() in page_text.lower():
                return True, "verification"
        
        return False, ""
    
    async def fill_login_form(self, url: str, username: str, password: str) -> dict:
        """
        Attempt to fill and submit login form.
        
        Returns:
            {
                "success": bool,
                "message": str,
                "paused": bool,
                "reason": str (if paused)
            }
        """
        await self.navigate_to(url)
        
        # Detect blockers BEFORE trying to fill
        is_blocked, reason = await self.detect_blockers()
        if is_blocked:
            self.paused_for_manual = True
            self.pause_reason = reason
            return {
                "success": False,
                "message": f"Detected {reason}, pausing for manual intervention",
                "paused": True,
                "reason": reason
            }
        
        # Try common username selectors
        username_selectors = [
            'input[name="email"]',
            'input[name="username"]',
            'input[type="email"]',
            'input[id="email"]',
            'input[id="username"]',
            'input[aria-label*="email"]',
            'input[aria-label*="username"]',
            'input[placeholder*="email"]',
            'input[placeholder*="username"]'
        ]
        
        username_filled = False
        for sel in username_selectors:
            el = await self.page.query_selector(sel)
            if el:
                await el.fill(username)
                username_filled = True
                print(f"    [OK] Filled username: {sel}")
                break
        
        if not username_filled:
            return {
                "success": False,
                "message": "Could not find username field",
                "paused": False
            }
        
        # Try common password selectors
        password_selectors = [
            'input[name="password"]',
            'input[type="password"]',
            'input[id="password"]'
        ]
        
        password_filled = False
        for sel in password_selectors:
            el = await self.page.query_selector(sel)
            if el:
                await el.fill(password)
                password_filled = True
                print(f"    [OK] Filled password: {sel}")
                break
        
        if not password_filled:
            return {
                "success": False,
                "message": "Could not find password field",
                "paused": False
            }
        
        # Find and click submit button
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("sign in")',
            'button:has-text("login")',
            'button:has-text("log in")',
            'a:has-text("sign in")',
            'button:has-text("continue")'
        ]
        
        for sel in submit_selectors:
            el = await self.page.query_selector(sel)
            if el:
                await el.click()
                print(f"    [OK] Clicked submit: {sel}")
                break
        
        # Wait a bit and check for blockers again (post-submit)
        await asyncio.sleep(2)
        is_blocked, reason = await self.detect_blockers()
        if is_blocked:
            self.paused_for_manual = True
            self.pause_reason = reason
            return {
                "success": False,
                "message": f"Detected {reason} after submit, pausing",
                "paused": True,
                "reason": reason
            }
        
        # Check current URL for success indicators
        current_url = self.page.url
        if "login" not in current_url.lower() or "signin" not in current_url.lower():
            return {
                "success": True,
                "message": "Login appears successful",
                "paused": False
            }
        
        return {
            "success": False,
            "message": "Login form submitted but may have failed",
            "paused": False
        }
    
    async def resume_from_manual(self):
        """Resume automation after manual intervention."""
        if not self.paused_for_manual:
            return {"success": False, "message": "Not paused"}
        
        # Wait for user to signal done
        print("[*] Waiting for manual intervention to complete...")
        print("    Press Enter in console when done (or call resume())")
        
        # In real implementation, this would wait for a signal
        # For now, just mark as resumed
        self.paused_for_manual = False
        self.pause_reason = None
        
        return {"success": True, "message": "Resumed"}


async def login_to_website(
    site_name: str,
    data_dir: str = None,
    headless: bool = True
) -> dict:
    """
    Main entry point: login to a website by name.
    
    This is the CLOSED-LOOP function that:
    1. Looks up credential by name
    2. Decrypts password internally (NEVER exposed to LLM)
    3. Opens browser and performs login
    
    Args:
        site_name: Name of the site (e.g., "GitHub")
        data_dir: Custom data directory
        headless: Run browser in headless mode
    
    Returns:
        {
            "success": bool,
            "site": str,
            "message": str,
            "paused": bool,
            "reason": str (if paused)
        }
    """
    print(f"\n=== Auto-Login: {site_name} ===\n")
    
    # Step 1: Look up credential (sanitized - no password)
    credential = get_credential_by_name(site_name, data_dir)
    if not credential:
        return {
            "success": False,
            "site": site_name,
            "message": f"Credential not found for: {site_name}"
        }
    
    print(f"[*] Found credential for: {credential['name']}")
    print(f"    URL: {credential['url']}")
    print(f"    Username: {credential['username']}")
    
    # Step 2: Decrypt password (INTERNAL - LLM never sees this)
    try:
        password = _decrypt_password(credential["id"], data_dir)
        print(f"    [OK] Password decrypted internally")
    except Exception as e:
        return {
            "success": False,
            "site": site_name,
            "message": f"Failed to decrypt password: {e}"
        }
    
    # Step 3: Open browser and login
    try:
        async with AutoLoginEngine(data_dir, headless) as engine:
            result = await engine.fill_login_form(
                credential["url"],
                credential["username"],
                password
            )
            
            result["site"] = site_name
            return result
            
    except Exception as e:
        return {
            "success": False,
            "site": site_name,
            "message": f"Login error: {e}"
        }


# ============== CLI Demo ==============
if __name__ == "__main__":
    import sys
    
    print("=== ECM Auto-Login - Phase 2 ===\n")
    
    # Test login (will need credentials from Phase 1)
    # Note: This requires playwright-stealth and playwright installed
    
    async def main():
        # First check if we have any credentials
        from phase1_credential_manager import list_credentials
        creds = list_credentials()
        
        if not creds:
            print("[!] No credentials found. Run Phase 1 first.")
            return
        
        print(f"[*] Found {len(creds)} credential(s)")
        for c in creds:
            print(f"    - {c['name']}")
        
        # Try to login to first site (non-headless for demo)
        site = creds[0]["name"]
        result = await login_to_website(site, headless=False)
        
        print(f"\n[*] Result:")
        print(f"    Success: {result['success']}")
        print(f"    Message: {result['message']}")
        if result.get('paused'):
            print(f"    Paused:  {result['reason']}")
    
    # Check dependencies
    try:
        from playwright.async_api import async_playwright
        asyncio.run(main())
    except ImportError as e:
        print(f"[!] Missing dependency: {e}")
        print("[*] Install with: pip install playwright playwright-stealth")
        print("[*] Then run: playwright install chromium")

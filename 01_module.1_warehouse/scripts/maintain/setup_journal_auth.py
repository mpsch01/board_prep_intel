"""
setup_journal_auth.py
=====================
Saves browser cookies for JAMA Network and NEJM so exa_pdf_downloader.py
can make authenticated requests without manual steps on each run.

HOW IT WORKS
────────────
JAMA Network uses Cloudflare bot detection, which blocks automated browsers.
The solution is to export cookies from your already-logged-in Chrome session
using the "Cookie-Editor" extension, then import them here.

NEJM does not block automated browsers — this script opens a visible browser
window so you can log in normally, and saves the session automatically.

SETUP STEPS
────────────
JAMA (one-time manual export):
  1. In Chrome, go to jamanetwork.com (you must be logged in)
  2. Install the "Cookie-Editor" extension if you don't have it:
       https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalahu
  3. Click the Cookie-Editor icon → click "Export" (bottom right) → "Export as JSON"
  4. A JSON blob is copied to your clipboard
  5. Run:  python setup_journal_auth.py --jama
  6. Paste when prompted

NEJM (automated — browser opens, you log in):
  1. Run:  python setup_journal_auth.py --nejm
  2. A browser window opens — log in with your NEJM credentials
  3. Press Enter when done

Both together:
  python setup_journal_auth.py

Cookie files are saved to:
  key_data_files/browser_cookies/jama_cookies.json
  key_data_files/browser_cookies/nejm_cookies.json

Re-run this script when a session expires (typically weeks to months).

Usage:
    python setup_journal_auth.py          # both JAMA and NEJM
    python setup_journal_auth.py --jama   # JAMA only
    python setup_journal_auth.py --nejm   # NEJM only
"""

import argparse, json, time, sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
COOKIE_DIR   = PROJECT_ROOT / "key_data_files" / "browser_cookies"

JAMA_COOKIE_FILE = COOKIE_DIR / "jama_cookies.json"
NEJM_COOKIE_FILE = COOKIE_DIR / "nejm_cookies.json"

NEJM_LOGIN_URL = "https://www.nejm.org/action/showLogin"
NEJM_VERIFY_URL = "https://www.nejm.org"


def setup_jama_from_clipboard():
    """
    Import JAMA cookies from a Cookie-Editor JSON export (pasted by user).
    Normalises the format and saves to jama_cookies.json.
    """
    print(f"\n{'─'*60}")
    print("  JAMA Network — Cookie Import")
    print(f"{'─'*60}")
    print()
    print("  Steps:")
    print("  1. Open Chrome and go to https://jamanetwork.com")
    print("     (make sure you are logged in)")
    print("  2. Click the Cookie-Editor extension icon")
    print("  3. Click 'Export' (bottom right) → 'Export as JSON'")
    print("     (this copies the JSON to your clipboard)")
    print("  4. Come back here and paste below")
    print()
    print("  Paste the Cookie-Editor JSON export, then press Enter twice:")
    print("  (It will look like: [{\"name\": \"...\", \"value\": \"...\", ...}, ...])")
    print()

    lines = []
    try:
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
    except EOFError:
        pass

    raw = "\n".join(lines).strip()
    if not raw:
        print("  ✗ No input received")
        return False

    try:
        cookies = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ✗ Could not parse JSON: {e}")
        print("  Make sure you pasted the full export from Cookie-Editor")
        return False

    if not isinstance(cookies, list):
        print("  ✗ Expected a JSON array of cookies")
        return False

    # Normalise Cookie-Editor format → simple {name, value, domain} list
    normalised = []
    for c in cookies:
        if isinstance(c, dict) and "name" in c and "value" in c:
            normalised.append({
                "name":   c["name"],
                "value":  c["value"],
                "domain": c.get("domain", ".jamanetwork.com"),
                "path":   c.get("path", "/"),
            })

    if not normalised:
        print("  ✗ No valid cookies found in the pasted data")
        return False

    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    with open(JAMA_COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(normalised, f, indent=2)

    print(f"  ✓ {len(normalised)} JAMA cookies saved → {JAMA_COOKIE_FILE.name}")
    return True


def setup_nejm_via_browser():
    """
    Open a visible Playwright browser at the NEJM login page.
    User logs in manually; cookies are extracted and saved.
    """
    print(f"\n{'─'*60}")
    print("  NEJM — Browser Login Setup")
    print(f"{'─'*60}")
    print(f"  A browser window will open at: {NEJM_LOGIN_URL}")
    print("  Log in with your NEJM credentials.")
    print("  Once you are fully logged in, come back here and press Enter.")
    print()
    input("  Press Enter to open the browser...")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ERROR: playwright not installed.")
        print("  Run: pip install playwright && playwright install chromium")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--start-maximized"])
            context = browser.new_context(no_viewport=True)
            page    = context.new_page()
            page.goto(NEJM_LOGIN_URL)

            print("\n  Browser open. Log in to NEJM, then come back here.")
            input("  Press Enter once you are fully logged in...")

            # Verify logged-in state
            print(f"  Checking session at {NEJM_VERIFY_URL}...")
            page.goto(NEJM_VERIFY_URL, wait_until="domcontentloaded", timeout=15000)
            time.sleep(1)

            page_text = page.content().lower()
            confirmed = any(s in page_text for s in
                            ["sign out", "log out", "logout", "my account",
                             "account settings", "profile", "subscriber"])

            all_cookies = context.cookies()
            browser.close()

        if not all_cookies:
            print("  ✗ No cookies captured — did the login succeed?")
            return False

        normalised = [{
            "name":   c["name"],
            "value":  c["value"],
            "domain": c.get("domain", ".nejm.org"),
            "path":   c.get("path", "/"),
        } for c in all_cookies]

        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        with open(NEJM_COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(normalised, f, indent=2)

        if confirmed:
            print(f"  ✓ NEJM: logged-in state confirmed")
        else:
            print(f"  ⚠  NEJM: could not auto-confirm — cookies saved anyway")
            print(f"     If you successfully logged in, the session is usable.")

        print(f"  ✓ {len(normalised)} NEJM cookies saved → {NEJM_COOKIE_FILE.name}")
        return True

    except Exception as e:
        print(f"  ✗ NEJM setup error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jama", action="store_true", help="JAMA cookie import only")
    parser.add_argument("--nejm", action="store_true", help="NEJM browser login only")
    args = parser.parse_args()

    do_jama = args.jama or (not args.jama and not args.nejm)
    do_nejm = args.nejm or (not args.jama and not args.nejm)

    print("=" * 60)
    print("  Journal Auth Setup — exa_pdf_downloader.py")
    print("=" * 60)

    results = {}

    if do_jama:
        results["JAMA"] = setup_jama_from_clipboard()

    if do_nejm:
        results["NEJM"] = setup_nejm_via_browser()

    print(f"\n{'='*60}")
    print("  Setup Summary")
    print(f"{'='*60}")
    for journal, ok in results.items():
        status = "✓ ready" if ok else "✗ failed/skipped"
        print(f"  {journal}: {status}")
    print()
    print("  exa_pdf_downloader.py will load these cookies automatically.")
    print("  Re-run this script when a session expires.")
    print()


if __name__ == "__main__":
    main()


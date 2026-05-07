"""
Diagnostic: open AAFP with saved auth, print all search-related inputs
and see if URL-based search actually works after clicking through it.
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
AUTH_PATH  = SCRIPT_DIR / "_aafp_auth.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx_kwargs = dict(
        accept_downloads=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    if AUTH_PATH.exists():
        ctx_kwargs["storage_state"] = str(AUTH_PATH)
        print(f"Using saved auth: {AUTH_PATH.name}")
    context = browser.new_context(**ctx_kwargs)
    page = context.new_page()

    print("Loading aafp.org homepage...")
    page.goto("https://www.aafp.org/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    print(f"Final URL: {page.url}")

    # Dump ALL inputs visible on the page
    print("\n--- ALL <input> elements on homepage ---")
    inputs = page.evaluate("""
        () => Array.from(document.querySelectorAll('input')).map(el => ({
            type: el.type, name: el.name, id: el.id,
            placeholder: el.placeholder, role: el.getAttribute('role'),
            ariaLabel: el.getAttribute('aria-label'),
            visible: !!(el.offsetWidth || el.offsetHeight)
        }))
    """)
    for el in inputs:
        if any((el.get('type','')=='search',
                'search' in (el.get('name','') or '').lower(),
                'search' in (el.get('placeholder','') or '').lower(),
                'search' in (el.get('ariaLabel','') or '').lower(),
                el.get('role') == 'searchbox')):
            print(f"  SEARCH-LIKE: {el}")

    print("\n--- ALL <button> elements with search hints ---")
    buttons = page.evaluate("""
        () => Array.from(document.querySelectorAll('button, [role=\"button\"]')).map(el => ({
            text: (el.innerText || '').trim().slice(0,40),
            id: el.id, class: el.className,
            ariaLabel: el.getAttribute('aria-label'),
            visible: !!(el.offsetWidth || el.offsetHeight)
        }))
    """)
    for b in buttons:
        if any('search' in (b.get(k,'') or '').lower() for k in ['text','id','class','ariaLabel']):
            print(f"  SEARCH-BUTTON: {b}")

    # Now try url-based search and see what page we actually land on
    print("\n--- URL-driven search test ---")
    test_url = "https://www.aafp.org/pubs/afp/issues/2024/0500/cryptorchidism.html"
    print(f"Navigating to known AFP article: {test_url}")
    page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    print(f"Landed at: {page.url}")
    title_meta = page.evaluate("document.querySelector('meta[name=\"citation_title\"]')?.content || '(no meta)'")
    print(f"citation_title: {title_meta}")

    print("\nBrowser will stay open 20s so you can inspect.")
    time.sleep(20)
    browser.close()

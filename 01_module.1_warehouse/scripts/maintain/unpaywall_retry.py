"""Retry the 179 unpaywall download_failed entries using curl-cffi w/ Chrome impersonation.

Reads `unpaywall_results.csv`, filters for download_failed rows with pdf_url,
attempts download with browser-like headers and delays. Updates the CSV
in-place when successful (download_status='downloaded' + bytes + dest_filename).
"""

from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path

from curl_cffi import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
RESULTS_CSV = PROJECT_ROOT / "01_module.1_warehouse" / "scripts" / "maintain" / "unpaywall_results.csv"
TIER_ROOT = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"

# Skip publishers that we know require auth or blocked us
SKIP_HOST_PATTERNS = (
    "jamanetwork.com",
    "nejm.org",
    "watermark.silverchair.com",
    "watermark02.silverchair.com",
)

VALID_TIERS = {"VC_pass", "VC_fail", "local_lite", "right_click"}


def normalize_author(author: str) -> str:
    a = re.split(r"[\s,]+", author.strip())[0]
    a = re.sub(r"[^A-Za-z\-']", "", a)
    if not a:
        return "Unknown"
    return a[0].upper() + a[1:]


def codon_filename(author: str, year: str, article_id: str) -> str:
    return f"{normalize_author(author)}_{year}#@#{article_id}@#@.pdf"


def try_download(url: str, *, min_size: int = 10_000) -> tuple[bytes | None, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept": "application/pdf,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://scholar.google.com/",
    }
    try:
        r = requests.get(url, impersonate="chrome110", headers=headers, timeout=30, allow_redirects=True)
    except Exception as e:
        return None, f"err: {type(e).__name__}: {str(e)[:80]}"
    if r.status_code != 200:
        return None, f"http {r.status_code}"
    body = r.content
    if len(body) < min_size:
        return None, f"too small {len(body)}"
    if not body.startswith(b"%PDF"):
        return None, f"not pdf {body[:6]!r}"
    return body, "ok"


def main() -> int:
    if not RESULTS_CSV.exists():
        print(f"missing: {RESULTS_CSV}")
        return 1
    rows = list(csv.DictReader(open(RESULTS_CSV, encoding="utf-8")))
    fieldnames = list(rows[0].keys()) if rows else []
    targets = [r for r in rows if r.get("download_status") == "download_failed" and r.get("pdf_url")]
    print(f"Targets: {len(targets)}")
    skipped = ok = fail = 0
    for i, r in enumerate(targets, 1):
        url = r["pdf_url"]
        if any(p in url for p in SKIP_HOST_PATTERNS):
            skipped += 1
            continue
        author = r.get("author1") or "Unknown"
        year = r.get("year") or "0000"
        art = r["article_id"]
        tier = r.get("tier") or "VC_fail"
        if tier not in VALID_TIERS:
            tier = "VC_fail"
        fname = codon_filename(author, year, art)
        dest = TIER_ROOT / tier / fname
        if dest.exists():
            r["download_status"] = "downloaded"
            r["dest_filename"] = fname
            r["bytes"] = str(dest.stat().st_size)
            print(f"[{i:3d}/{len(targets)}] SKIP {art} (already on disk)")
            ok += 1
            continue
        body, msg = try_download(url)
        if body:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            r["download_status"] = "downloaded"
            r["dest_filename"] = fname
            r["bytes"] = str(len(body))
            ok += 1
            print(f"[{i:3d}/{len(targets)}] OK   {art} -> {fname} ({len(body)} bytes)")
        else:
            r["download_status"] = "download_failed"
            fail += 1
            print(f"[{i:3d}/{len(targets)}] FAIL {art}: {msg}")
        time.sleep(1.0)  # polite delay
    # Persist updated CSV
    with open(RESULTS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nSummary: {ok} ok, {fail} failed, {skipped} skipped (JAMA/NEJM blocklist)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
JAMA Chrome Harvester — uses Claude-in-Chrome's authenticated session to extract
the token-signed silverchair CDN URL, then downloads the PDF directly via curl-cffi.

Flow per article:
  1. Cowork Claude navigates Chrome tab to article page → reads Download PDF href
  2. Cowork Claude navigates Chrome tab to that articlepdf URL → redirects to
     silverchair watermark URL with signed token
  3. Cowork Claude calls this script with the silverchair URL + article metadata
  4. Script downloads PDF and saves with codon filename in tier folder

This script is invoked once per article. The orchestration loop lives in the
Cowork session because only Cowork has Chrome control.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from curl_cffi import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
TIER_ROOT = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"

CHROME_VIEWER_PREFIX = "chrome-extension://efaidnbmnnnibpcajpcglclefindmkaj/"


def normalize_author(author: str) -> str:
    """First-letter capitalize only. Never .title()."""
    a = re.split(r"[\s,]+", author.strip())[0]
    a = re.sub(r"[^A-Za-z\-']", "", a)
    if not a:
        return "Unknown"
    return a[0].upper() + a[1:]


def codon_filename(author: str, year: str, article_id: str) -> str:
    return f"{normalize_author(author)}_{year}#@#{article_id}@#@.pdf"


def extract_real_url(viewer_url: str) -> str:
    """Strip the chrome-extension:// PDF viewer prefix if present.

    Two patterns observed:
      A) chrome-extension://{id}/https://watermark02.silverchair.com/...
      B) chrome-extension://{id}/viewer.html?pdfurl=URL_ENCODED&tabId=...
    """
    from urllib.parse import unquote
    if viewer_url.startswith(CHROME_VIEWER_PREFIX):
        rest = viewer_url[len(CHROME_VIEWER_PREFIX):]
        if rest.startswith("viewer.html?pdfurl="):
            encoded = rest[len("viewer.html?pdfurl="):]
            # Strip trailing &tabId=... or other query params
            tab_marker = encoded.rfind("&tabId=")
            if tab_marker != -1:
                encoded = encoded[:tab_marker]
            return unquote(encoded)
        return rest
    return viewer_url


def download_pdf(url: str, dest: Path, *, min_size: int = 10_000) -> tuple[bool, str]:
    """Returns (ok, message). Validates PDF magic + min size."""
    try:
        r = requests.get(url, impersonate="chrome110", timeout=60)
    except Exception as e:
        return False, f"request error: {e}"
    if r.status_code != 200:
        return False, f"http {r.status_code}"
    body = r.content
    if len(body) < min_size:
        return False, f"too small: {len(body)} bytes"
    if not body.startswith(b"%PDF"):
        return False, f"not a pdf: starts with {body[:8]!r}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return True, f"ok: {len(body)} bytes"


def append_job(jobs_file: Path, article_id: str, tier: str, author: str, year: str, url: str) -> None:
    """Append a job entry to the JSON jobs file (creates if absent)."""
    import json
    jobs = []
    if jobs_file.exists():
        try:
            jobs = json.loads(jobs_file.read_text(encoding="utf-8"))
        except Exception:
            jobs = []
    jobs.append({
        "article_id": article_id,
        "tier": tier,
        "author": author,
        "year": year,
        "url": extract_real_url(url),
    })
    jobs_file.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    print(f"QUEUED {article_id} ({len(jobs)} total)")


def run_jobs(jobs_file: Path) -> int:
    """Process all queued jobs from a JSON file."""
    import json
    if not jobs_file.exists():
        print(f"No jobs file at {jobs_file}")
        return 1
    jobs = json.loads(jobs_file.read_text(encoding="utf-8"))
    remaining = []
    ok_count = fail_count = skip_count = 0
    for job in jobs:
        fname = codon_filename(job["author"], job["year"], job["article_id"])
        dest = TIER_ROOT / job["tier"] / fname
        if dest.exists():
            print(f"SKIP {job['article_id']}: already exists")
            skip_count += 1
            continue
        ok, msg = download_pdf(job["url"], dest)
        if ok:
            ok_count += 1
            print(f"OK   {job['article_id']} -> {fname}: {msg}")
        else:
            fail_count += 1
            print(f"FAIL {job['article_id']} -> {fname}: {msg}")
            remaining.append(job)
    # Persist only failed entries for retry
    jobs_file.write_text(json.dumps(remaining, indent=2), encoding="utf-8")
    print(f"\nSummary: {ok_count} ok, {skip_count} skipped, {fail_count} failed (remaining queue: {len(remaining)})")
    return 0 if fail_count == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p_one = sub.add_parser("one", help="Download one article immediately")
    p_one.add_argument("--article-id", required=True)
    p_one.add_argument("--tier", required=True, choices=["VC_pass", "VC_fail", "local_lite", "right_click"])
    p_one.add_argument("--author", required=True)
    p_one.add_argument("--year", required=True)
    p_one.add_argument("--url", required=True)

    p_q = sub.add_parser("queue", help="Append a job to the jobs file")
    p_q.add_argument("--jobs-file", default=str(SCRIPT_DIR / "_jama_silverchair_jobs.json"))
    p_q.add_argument("--article-id", required=True)
    p_q.add_argument("--tier", required=True, choices=["VC_pass", "VC_fail", "local_lite", "right_click"])
    p_q.add_argument("--author", required=True)
    p_q.add_argument("--year", required=True)
    p_q.add_argument("--url", required=True)

    p_run = sub.add_parser("run", help="Process all queued jobs")
    p_run.add_argument("--jobs-file", default=str(SCRIPT_DIR / "_jama_silverchair_jobs.json"))

    # Backward-compat: if no subcommand, treat as "one" mode (legacy flags)
    ap.add_argument("--article-id", help=argparse.SUPPRESS)
    ap.add_argument("--tier", choices=["VC_pass", "VC_fail", "local_lite", "right_click"], help=argparse.SUPPRESS)
    ap.add_argument("--author", help=argparse.SUPPRESS)
    ap.add_argument("--year", help=argparse.SUPPRESS)
    ap.add_argument("--url", help=argparse.SUPPRESS)

    args = ap.parse_args()

    if args.cmd == "queue":
        append_job(Path(args.jobs_file), args.article_id, args.tier, args.author, args.year, args.url)
        return 0
    if args.cmd == "run":
        return run_jobs(Path(args.jobs_file))
    if args.cmd == "one" or (args.article_id and args.url):
        real_url = extract_real_url(args.url)
        fname = codon_filename(args.author, args.year, args.article_id)
        dest = TIER_ROOT / args.tier / fname
        if dest.exists():
            print(f"SKIP {args.article_id}: already exists at {dest}")
            return 0
        ok, msg = download_pdf(real_url, dest)
        print(f"{'OK' if ok else 'FAIL'} {args.article_id} -> {fname}: {msg}")
        return 0 if ok else 1
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

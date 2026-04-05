"""
recover_unpaywall.py
====================
Re-downloads PDFs from unpaywall_results.csv that have a saved pdf_url
but are no longer present on disk. Uses the stored pdf_url directly
(no API calls needed — Unpaywall URLs are stable OA links).

Run this AFTER re-running exa_pdf_downloader.py and pmc_oa_downloader.py.

Usage:
    python recover_unpaywall.py           # re-download all missing
    python recover_unpaywall.py --dry-run # preview only
"""

import csv, re, time, requests, argparse
from pathlib import Path
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
RESULTS_CSV  = SCRIPT_DIR / "unpaywall_results.csv"

RATE_LIMIT  = 0.5
TIMEOUT     = 30
CHUNK_SIZE  = 8192
MAX_PDF_MB  = 50
CODON_RE    = re.compile(r'#@#(ART-\d+)@#@')

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
}


def get_art_ids_on_disk():
    found = set()
    if not PDF_ROOT.exists():
        return found
    for pdf in PDF_ROOT.rglob("*.pdf"):
        m = CODON_RE.search(pdf.name)
        if m:
            found.add(m.group(1))
    return found


def download_pdf(url, dest_path):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                            stream=True, allow_redirects=True)
        if resp.status_code != 200:
            return False, f"http_{resp.status_code}", 0

        content_type = resp.headers.get("Content-Type", "").lower()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        size = 0

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(CHUNK_SIZE):
                f.write(chunk)
                size += len(chunk)
                if size > MAX_PDF_MB * 1024 * 1024:
                    dest_path.unlink(missing_ok=True)
                    return False, "too_large", 0

        if size < 1024:
            dest_path.unlink(missing_ok=True)
            return False, "too_small", 0

        with open(dest_path, "rb") as f:
            if not f.read(4).startswith(b"%PDF"):
                dest_path.unlink(missing_ok=True)
                return False, "not_pdf", 0

        return True, "ok", size

    except Exception as e:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        return False, f"error: {e}", 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not RESULTS_CSV.exists():
        print(f"ERROR: {RESULTS_CSV} not found")
        return

    # Load all rows with download_status==downloaded and a pdf_url
    candidates = []
    with open(RESULTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("download_status") == "downloaded" and row.get("pdf_url"):
                candidates.append(row)

    print(f"Unpaywall CSV: {len(candidates)} previously-downloaded entries")

    # Skip those still on disk
    on_disk = get_art_ids_on_disk()
    to_recover = [r for r in candidates if r.get("article_id") not in on_disk]
    already_present = len(candidates) - len(to_recover)

    print(f"Already on disk: {already_present}")
    print(f"Need re-download: {len(to_recover)}")

    if not to_recover:
        print("Nothing to recover.")
        return

    if args.dry_run:
        print(f"\nDry run — {len(to_recover)} files would be downloaded:")
        for r in to_recover[:20]:
            print(f"  {r['article_id']} → {r.get('dest_filename','?')}")
            print(f"    {r['pdf_url'][:75]}")
        if len(to_recover) > 20:
            print(f"  ... and {len(to_recover) - 20} more")
        return

    print(f"\nStarting recovery: {len(to_recover)} files\n")
    counters = Counter()

    for i, row in enumerate(to_recover, 1):
        art_id   = row.get("article_id", "?")
        tier     = row.get("tier", "VC_fail")
        pdf_url  = row["pdf_url"]
        dest_fname = row.get("dest_filename") or f"Unknown_0000#@#{art_id}@#@.pdf"
        dest_path  = PDF_ROOT / tier / dest_fname

        print(f"[{i}/{len(to_recover)}] {art_id} [{tier}] {dest_fname[:55]}")
        print(f"  {pdf_url[:80]}")

        success, status, nbytes = download_pdf(pdf_url, dest_path)
        if success:
            print(f"  [OK] {nbytes//1024} KB")
            counters["recovered"] += 1
        else:
            print(f"  [FAIL] {status}")
            counters[status] += 1

        time.sleep(RATE_LIMIT)

    print(f"\n=== Recovery Summary ===")
    print(f"Recovered:   {counters['recovered']} / {len(to_recover)}")
    fails = sum(v for k, v in counters.items() if k != "recovered")
    print(f"Failed:      {fails}")
    for k, v in sorted(counters.items()):
        if k != "recovered":
            print(f"  {k}: {v}")
    print(f"\nTotal PDFs now on disk: {len(get_art_ids_on_disk())}")


if __name__ == "__main__":
    main()

"""
aafp_pdf_downloader.py
Download AAFP-only article PDFs to citation_files/AAFP/

16 confirmed downloadable articles: 9 PMC, 4 direct PDF, 2 OA, 1 university repo
Run from project root: python 01_module.1_warehouse/scripts/maintain/aafp_pdf_downloader.py

Each file is saved with its codon filename: Author_Year#@#ART-XXXX@#@.pdf
Skips any file already on disk.
"""

import requests
import time
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent   # maintain/ -> scripts/ -> M1 -> root
DEST = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "AAFP"
DEST.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_BYTES = 50 * 1024 * 1024   # 50 MB — nothing larger is a journal article
MIN_BYTES = 1_024               # 1 KB — anything smaller is an error page
RATE_LIMIT_SEC = 2

# (ART-ID, codon_filename, primary_url, fallback_url)
# PMC fallback = EuropePMC mirror
def pmc(pmcid):
    return (
        f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/",
        f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
    )

ARTICLES = [
    # ── PMC Full Text (9) ──────────────────────────────────────────────────────
    ("ART-1945", "Albalawi_2011#@#ART-1945@#@.pdf",   *pmc("PMC6492479")),
    ("ART-1949", "Keay_2012#@#ART-1949@#@.pdf",       *pmc("PMC4261928")),
    ("ART-1950", "Dennis_2008#@#ART-1950@#@.pdf",     *pmc("PMC6148705")),
    ("ART-0864", "Metlay_Waterer_2019#@#ART-0864@#@.pdf", *pmc("PMC6812437")),
    ("ART-1959", "Binic_2011#@#ART-1959@#@.pdf",      *pmc("PMC4996308")),
    ("ART-1972", "Byington_2012#@#ART-1972@#@.pdf",   *pmc("PMC4074609")),
    ("ART-1940", "Islam_2016#@#ART-1940@#@.pdf",      *pmc("PMC4748908")),
    ("ART-1967", "Verbalis_2007#@#ART-1967@#@.pdf",   *pmc("PMC2643091")),
    ("ART-1975", "Khan_2010#@#ART-1975@#@.pdf",       *pmc("PMC2943085")),

    # ── Direct PDF — official sources (4 high-confidence) ─────────────────────
    ("ART-0061", "American_Aroda_2022#@#ART-0061@#@.pdf",
     "https://diabetes.org/sites/default/files/2023-09/dc22s007.pdf", None),

    ("ART-1965", "Nahid_2016#@#ART-1965@#@.pdf",
     "https://www.cdc.gov/tb/publications/guidelines/pdf/clin-infect-dis.-2016-nahid-cid_ciw376.pdf", None),

    ("ART-1966", "Shonkoff_2011#@#ART-1966@#@.pdf",
     "https://www.kenyapaediatric.org/ecd/wp-content/uploads/2023/01/Shonkoff_2012_Pediatrics.pdf", None),

    ("ART-1948", "Yeung_2011#@#ART-1948@#@.pdf",
     "https://paulogentil.com/pdf/Interventions%20for%20preventing%20lower%20limb%20soft-tissue%20running%20injuries.pdf",
     None),

    # ── Open Access (2) ────────────────────────────────────────────────────────
    ("ART-1954", "Bocchetta_2006#@#ART-1954@#@.pdf",
     "https://cpementalhealth.biomedcentral.com/counter/pdf/10.1186/1745-0179-2-23.pdf", None),

    ("ART-1955", "Manske_2008#@#ART-1955@#@.pdf",
     "https://link.springer.com/content/pdf/10.1007/s12178-008-9031-6.pdf", None),

    # ── University repository (1) — medium confidence: verify Binks 2006 ──────
    # NOTE: agent found LeePsychological.pdf — different author than Binks. Verify content after download.
    ("ART-1946", "Binks_2006#@#ART-1946@#@.pdf",
     "https://eprints.hud.ac.uk/id/eprint/8909/1/LeePsychological.pdf", None),
]


# ─────────────────────────────────────────────────────────────────────────────

def try_download(url: str, dest: Path) -> tuple[bool, str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30,
                            stream=True, allow_redirects=True)
    except requests.RequestException as e:
        return False, f"Request error: {e}"

    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"

    content_type = resp.headers.get("Content-Type", "").lower()
    first_chunk = next(resp.iter_content(chunk_size=8), b"")
    is_pdf = (
        "pdf" in content_type
        or "octet-stream" in content_type
        or first_chunk.startswith(b"%PDF")
    )
    if not is_pdf:
        return False, f"Not a PDF (Content-Type: {content_type[:50]})"

    with open(dest, "wb") as f:
        f.write(first_chunk)
        size = len(first_chunk)
        for chunk in resp.iter_content(8192):
            f.write(chunk)
            size += len(chunk)
            if size > MAX_BYTES:
                dest.unlink(missing_ok=True)
                return False, "File too large (>50 MB)"

    if size < MIN_BYTES:
        dest.unlink(missing_ok=True)
        return False, f"File too small ({size} bytes) — likely an error page"

    return True, f"{size // 1024} KB"


def main():
    print(f"\naafp_pdf_downloader.py")
    print(f"Destination: {DEST}")
    print(f"Articles:    {len(ARTICLES)}\n")
    print("-" * 70)

    results = {"ok": [], "skip": [], "fail": []}

    for art_id, filename, primary_url, fallback_url in ARTICLES:
        dest_path = DEST / filename

        # Skip if already on disk
        if dest_path.exists():
            size_kb = dest_path.stat().st_size // 1024
            print(f"SKIP  {art_id}  {filename}  ({size_kb} KB already on disk)")
            results["skip"].append((art_id, filename))
            continue

        print(f"DL    {art_id}  {filename}")
        print(f"      → {primary_url[:80]}")

        ok, msg = try_download(primary_url, dest_path)

        if not ok and fallback_url:
            print(f"      Primary failed ({msg}), trying fallback...")
            print(f"      → {fallback_url[:80]}")
            ok, msg = try_download(fallback_url, dest_path)

        if ok:
            print(f"      ✅ OK ({msg})")
            results["ok"].append((art_id, filename, msg))
        else:
            print(f"      ❌ FAIL: {msg}")
            results["fail"].append((art_id, filename, msg))
            if dest_path.exists():
                dest_path.unlink()

        time.sleep(RATE_LIMIT_SEC)

    # ── Summary ──
    print("\n" + "=" * 70)
    print(f"SUMMARY")
    print(f"  Downloaded:  {len(results['ok'])}")
    print(f"  Skipped:     {len(results['skip'])}")
    print(f"  Failed:      {len(results['fail'])}")

    if results["ok"]:
        print("\n✅ Downloaded:")
        for art_id, fn, size in results["ok"]:
            print(f"   {art_id}  {fn}  ({size})")

    if results["fail"]:
        print("\n❌ Failed:")
        for art_id, fn, msg in results["fail"]:
            print(f"   {art_id}  {fn}  — {msg}")

    if results["skip"]:
        print(f"\n⏭  Skipped (already on disk): {len(results['skip'])}")

    print(f"\nDestination: {DEST}")
    print("NOTE: Verify ART-1946 (Binks_2006) — source PDF author may differ.")
    print("      Open the file and confirm it is the correct Binks 2006 Cochrane review.")


if __name__ == "__main__":
    main()

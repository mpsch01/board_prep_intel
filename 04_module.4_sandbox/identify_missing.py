"""
identify_missing.py
===================
Identifies which articles are NOT auto-recoverable by the re-download scripts.

Logic:
  Auto-recoverable = downloaded by exa_pdf_downloader OR pmc_oa_downloader OR unpaywall_scanner
  Safe = currently on disk (VC_pass + remaining VC_fail W-Z)
  NOT recoverable = was in the pre-EXA manual library, NOT safe, NOT in any script CSV

Output:
  04_module.4_sandbox/missing_articles.csv  -- the ~230 unrecoverable articles
  Console summary
"""

import csv, re, sqlite3
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MAINTAIN_DIR = PROJECT_ROOT / "01_module.1_warehouse" / "scripts" / "maintain"
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

EXA_QUEUE_CSV      = MAINTAIN_DIR / "exa_pdf_queue.csv"
EXA_RESULTS_CSV    = MAINTAIN_DIR / "exa_download_results.csv"
PMC_RESULTS_CSV    = MAINTAIN_DIR / "pmc_oa_results.csv"
UNPAYWALL_CSV      = MAINTAIN_DIR / "unpaywall_results.csv"
OUT_CSV            = SCRIPT_DIR / "missing_articles.csv"

CODON_RE = re.compile(r'#@#(ART-\d+)@#@')

def get_art_ids_on_disk():
    found = {}
    for pdf in PDF_ROOT.rglob("*.pdf"):
        m = CODON_RE.search(pdf.name)
        if m:
            found[m.group(1)] = pdf.parent.name  # tier name
    return found

def read_csv_ids(path, status_col, status_val, id_col="article_id"):
    ids = set()
    if not path.exists():
        print(f"  WARNING: {path.name} not found")
        return ids
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get(status_col, "").strip() in (status_val if isinstance(status_val, list) else [status_val]):
                ids.add(row.get(id_col, "").strip())
    ids.discard("")
    return ids

def main():
    print("=== Identifying unrecoverable articles ===\n")

    # 1. What's currently on disk
    on_disk = get_art_ids_on_disk()
    print(f"Currently on disk: {len(on_disk)} ART-IDs")
    tier_counts = {}
    for art_id, tier in on_disk.items():
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")

    # 2. Auto-recoverable: downloaded by scripts
    exa_ok  = read_csv_ids(EXA_RESULTS_CSV, "status", "ok")
    pmc_ok  = read_csv_ids(PMC_RESULTS_CSV, "download_status", "ok")
    unp_ok  = read_csv_ids(UNPAYWALL_CSV, "download_status", "downloaded")
    script_recovered = exa_ok | pmc_ok | unp_ok
    print(f"\nScript-downloadable ART-IDs:")
    print(f"  EXA downloader:      {len(exa_ok)}")
    print(f"  PMC OA downloader:   {len(pmc_ok)}")
    print(f"  Unpaywall scanner:   {len(unp_ok)}")
    print(f"  Union (unique):      {len(script_recovered)}")

    # 3. Articles that were in EXA queue (= were missing from disk when EXA ran)
    exa_queued = set()
    if EXA_QUEUE_CSV.exists():
        with open(EXA_QUEUE_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                exa_queued.add(row.get("article_id", "").strip())
    exa_queued.discard("")
    print(f"\nIn EXA queue (missing from disk at EXA-run time): {len(exa_queued)}")

    # 4. Pre-existing library = DB articles NOT in EXA queue (had PDFs when EXA ran)
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT article_id, author1, year, title, source_type, tier
        FROM articles
        ORDER BY article_id
    """)
    all_articles = {row[0]: {
        "article_id": row[0],
        "author1":    row[1] or "",
        "year":       str(row[2] or ""),
        "title":      (row[3] or "")[:80],
        "source_type":row[4] or "",
        "db_tier":    row[5] or ""
    } for row in cur.fetchall()}
    conn.close()
    print(f"DB articles total: {len(all_articles)}")

    pre_existing = {aid: meta for aid, meta in all_articles.items()
                    if aid not in exa_queued}
    print(f"Pre-existing (not in EXA queue): {len(pre_existing)}")

    # 5. Missing and not recoverable:
    #    pre-existing AND not currently on disk AND not script-downloadable
    missing = {}
    for art_id, meta in pre_existing.items():
        if art_id in on_disk:
            continue  # safe on disk
        if art_id in script_recovered:
            continue  # recoverable by scripts
        missing[art_id] = meta

    print(f"\n=== UNRECOVERABLE ARTICLES: {len(missing)} ===")
    print("(Were in manual pre-EXA library; not on disk; not in any script CSV)\n")

    # Breakdown by source_type and db_tier
    by_source = {}
    by_tier   = {}
    for meta in missing.values():
        s = meta["source_type"] or "unknown"
        t = meta["db_tier"] or "unknown"
        by_source[s] = by_source.get(s, 0) + 1
        by_tier[t]   = by_tier.get(t, 0) + 1

    print("By source_type:")
    for k, v in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print("\nBy DB tier:")
    for k, v in sorted(by_tier.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    # Write CSV
    fields = ["article_id", "author1", "year", "title", "source_type", "db_tier"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for meta in sorted(missing.values(), key=lambda x: x["article_id"]):
            w.writerow(meta)
    print(f"\nSaved to: {OUT_CSV}")
    print(f"\nFirst 20 missing articles:")
    for meta in sorted(missing.values(), key=lambda x: x["article_id"])[:20]:
        print(f"  {meta['article_id']} | {meta['author1'][:20]:20} | {meta['year']} | {meta['source_type']:12} | {meta['title'][:50]}")

    # Also: articles in EXA queue as landing_page/not_found that were somehow
    # on disk pre-deletion (edge case check)
    in_queue_but_lost = {}
    for art_id, meta in all_articles.items():
        if art_id in on_disk:
            continue
        if art_id in script_recovered:
            continue
        if art_id in missing:
            continue
        in_queue_but_lost[art_id] = meta

    if in_queue_but_lost:
        print(f"\nAlso lost (were in EXA queue but not script-downloaded): {len(in_queue_but_lost)}")
        print("  These may include landing_page/not_found articles that had manual PDFs")
        for meta in sorted(in_queue_but_lost.values(), key=lambda x: x["article_id"])[:10]:
            print(f"  {meta['article_id']} | {meta['author1'][:20]:20} | {meta['year']} | {meta['source_type']}")

if __name__ == "__main__":
    main()

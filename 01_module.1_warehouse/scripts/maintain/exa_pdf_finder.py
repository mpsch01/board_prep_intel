"""
exa_pdf_finder.py
=================
Finds articles missing physical PDFs, searches EXA for each, classifies results.

Usage:
    python exa_pdf_finder.py                          # all tiers
    python exa_pdf_finder.py --tier VC_pass           # VC_pass only
    python exa_pdf_finder.py --tier VC_fail           # VC_fail only
    python exa_pdf_finder.py --source "Guideline/Org" # filter by source_type
    python exa_pdf_finder.py --limit 10               # cap (for testing)
    python exa_pdf_finder.py --resume                 # skip already-processed
    python exa_pdf_finder.py --dry-run                # show counts, no EXA calls

Output:
    scripts/maintain/exa_pdf_queue.json    machine-readable queue
    scripts/maintain/exa_pdf_queue.csv     human-readable, sorted by classification
    scripts/maintain/exa_run.log           progress log (readable while running)

Classifications:
    direct_pdf    .pdf URL found — download immediately
    pmc_fulltext  PubMed Central — use PMC downloader
    open_access   BioMedCentral, Frontiers, GINA, USPSTF, etc.
    landing_page  Paywalled landing page — manual download
    not_found     EXA returned nothing usable
"""

import sqlite3, os, re, requests, json, csv, time, argparse, sys
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
OUTPUT_JSON  = SCRIPT_DIR / "exa_pdf_queue.json"
OUTPUT_CSV   = SCRIPT_DIR / "exa_pdf_queue.csv"
LOG_PATH     = SCRIPT_DIR / "exa_run.log"

# ── EXA ────────────────────────────────────────────────────────────────────
EXA_API_KEY    = os.environ.get("EXA_API_KEY", "")
EXA_SEARCH_URL = "https://api.exa.ai/search"
RATE_LIMIT_SEC = 1.2
NUM_RESULTS    = 5

# ── Codon regex ────────────────────────────────────────────────────────────
CODON_RE = re.compile(r'#@#(ART-\d+)@#@')

# ── Domain classifiers ─────────────────────────────────────────────────────
PMC_PATTERNS     = ["pmc.ncbi.nlm.nih.gov/articles/PMC",
                    "ncbi.nlm.nih.gov/pmc/articles",
                    "europepmc.org/articles/PMC"]
OA_PATTERNS      = ["biomedcentral.com/articles", "frontiersin.org", "mdpi.com",
                    "plos", "elifesciences.org", "bmj.com/content",
                    "academic.oup.com", "onlinelibrary.wiley.com/doi/full",
                    "ginasthma.org", "uspreventiveservicestaskforce.org",
                    "aafp.org/pubs/afp", "cdc.gov", "who.int", "cochranelibrary.com"]
PAYWALL_PATTERNS = ["jamanetwork.com", "nejm.org", "ahajournals.org",
                    "publications.aap.org", "pediatrics.aappublications.org",
                    "acc.org/Latest", "sciencedirect.com",
                    "link.springer.com/article", "journals.lww.com",
                    "annals.org", "thelancet.com"]

# ── Logging (writes to file AND stdout) ────────────────────────────────────
_log_fh = None

def log(msg):
    print(msg, flush=True)
    if _log_fh:
        _log_fh.write(msg + "\n")
        _log_fh.flush()

# ── Core logic ─────────────────────────────────────────────────────────────
def classify_url(url):
    if not url:
        return "not_found"
    u = url.lower()
    if u.endswith(".pdf"):
        return "direct_pdf"
    for p in PMC_PATTERNS:
        if p.lower() in u:
            return "pmc_fulltext"
    for p in OA_PATTERNS:
        if p.lower() in u:
            return "open_access"
    for p in PAYWALL_PATTERNS:
        if p.lower() in u:
            return "landing_page"
    return "landing_page"


def get_art_ids_on_disk():
    found = set()
    if not PDF_ROOT.exists():
        log(f"  WARNING: PDF root not found: {PDF_ROOT}")
        return found
    for pdf_file in PDF_ROOT.rglob("*.pdf"):
        m = CODON_RE.search(pdf_file.name)
        if m:
            found.add(m.group(1))
    return found


def get_articles_missing_pdfs(conn, tier, source_type, on_disk):
    where = ["1=1"]
    params = []
    if tier:
        where.append("tier = ?")
        params.append(tier)
    if source_type:
        where.append("source_type = ?")
        params.append(source_type)
    c = conn.cursor()
    c.execute(f"""
        SELECT article_id, title, author1, year, source_type,
               citation_display, clean_ref, tier
        FROM articles
        WHERE {' AND '.join(where)}
        ORDER BY
            CASE tier WHEN 'VC_pass' THEN 1 WHEN 'VC_fail' THEN 2 ELSE 3 END,
            article_id
    """, params)
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    return [r for r in rows if r["article_id"] not in on_disk]


def build_query(art):
    title  = (art.get("title") or "").strip()
    author = (art.get("author1") or "").strip().split()[0] if art.get("author1") else ""
    year   = str(art.get("year") or "").strip()
    stype  = art.get("source_type", "")
    parts  = [p for p in [title, author, year] if p]
    if stype in ("Guideline/Org", "Other Journal", "Cochrane"):
        parts.append("PDF")
    return " ".join(parts)


def search_exa(query):
    resp = requests.post(
        EXA_SEARCH_URL,
        headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
        json={"query": query, "type": "auto", "num_results": NUM_RESULTS,
              "contents": {"highlights": {"max_characters": 200}}},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def load_existing():
    if not OUTPUT_JSON.exists():
        return {}
    with open(OUTPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {r["article_id"]: r for r in data.get("results", [])}


def save(results, tier):
    counts = Counter(r["classification"] for r in results)
    output = {
        "generated": datetime.now().isoformat(),
        "tier_filter": tier or "all",
        "total": len(results),
        "summary": dict(counts),
        "results": results
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    order = {"direct_pdf": 0, "pmc_fulltext": 1, "open_access": 2,
             "landing_page": 3, "not_found": 4, "error": 5}
    fields = ["article_id", "tier", "classification", "top_url",
              "title", "author1", "year", "source_type", "query_used", "exa_title"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in sorted(results, key=lambda r: order.get(r.get("classification", ""), 9)):
            w.writerow(row)

    log(f"  Saved {len(results)} results → {OUTPUT_JSON.name} + {OUTPUT_CSV.name}")


def main():
    global _log_fh

    parser = argparse.ArgumentParser()
    parser.add_argument("--tier",    default=None,
                        choices=["VC_pass", "VC_fail", "local_lite", "right_click"])
    parser.add_argument("--source",  default=None)
    parser.add_argument("--limit",   type=int, default=0)
    parser.add_argument("--resume",  action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _log_fh = open(LOG_PATH, "w", encoding="utf-8")
    log(f"=== exa_pdf_finder.py — {datetime.now().isoformat()} ===")
    log(f"tier={args.tier} source={args.source} limit={args.limit} "
        f"resume={args.resume} dry_run={args.dry_run}")

    if not EXA_API_KEY and not args.dry_run:
        log("ERROR: EXA_API_KEY not set.")
        _log_fh.close()
        return

    log("\nScanning PDF folders for on-disk ART-IDs...")
    on_disk = get_art_ids_on_disk()
    log(f"  {len(on_disk)} PDFs found on disk.")

    conn = sqlite3.connect(DB_PATH)
    articles = get_articles_missing_pdfs(conn, args.tier, args.source, on_disk)
    conn.close()
    log(f"  {len(articles)} articles missing PDFs"
        + (f" in {args.tier}" if args.tier else " across all tiers") + ".")

    # Show tier breakdown
    tier_counts = Counter(a["tier"] for a in articles)
    for t, n in sorted(tier_counts.items()):
        log(f"    {t}: {n}")

    existing = load_existing() if args.resume else {}
    if existing:
        before = len(articles)
        articles = [a for a in articles if a["article_id"] not in existing]
        log(f"  Resuming: skipping {before - len(articles)} already done.")

    if args.limit:
        articles = articles[:args.limit]
        log(f"  Capped at {args.limit} (--limit).")

    if args.dry_run:
        log(f"\n── Dry run: {len(articles)} articles would be searched ──")
        src_counts = Counter(a["source_type"] for a in articles)
        log("\n  By source_type:")
        for s, n in src_counts.most_common():
            log(f"    {s}: {n}")
        log("\n  First 20:")
        for a in articles[:20]:
            log(f"    {a['article_id']} [{a['tier']}] {(a['source_type'] or ''):15} "
                f"{a['author1'] or ''} {a['year']} — {(a['title'] or '')[:50]}")
        if len(articles) > 20:
            log(f"  ... and {len(articles)-20} more")
        _log_fh.close()
        return

    log(f"\nSearching EXA for {len(articles)} articles...\n")
    results = list(existing.values())

    for i, art in enumerate(articles, 1):
        query = build_query(art)
        log(f"[{i}/{len(articles)}] {art['article_id']} [{art['tier']}] "
            f"{(art['title'] or '')[:55]}")

        try:
            hits = search_exa(query)
        except Exception as e:
            log(f"  ✗ Error: {e}")
            results.append({**art, "classification": "error",
                            "top_url": "", "exa_title": "", "query_used": query})
            time.sleep(RATE_LIMIT_SEC)
            continue

        if not hits:
            classification, top_url, exa_title = "not_found", "", ""
        else:
            top = hits[0]
            top_url   = top.get("url", "")
            exa_title = top.get("title", "")
            classification = classify_url(top_url)

        log(f"  → {classification}: {top_url[:75]}")
        results.append({**art, "classification": classification,
                        "top_url": top_url, "exa_title": exa_title,
                        "query_used": query})

        if i % 10 == 0:
            save(results, args.tier)

    save(results, args.tier)

    counts = Counter(r["classification"] for r in results)
    log("\n── Final Summary ─────────────────────────────")
    log(f"  direct_pdf:   {counts['direct_pdf']:4}  ← download now")
    log(f"  pmc_fulltext: {counts['pmc_fulltext']:4}  ← use PMC downloader")
    log(f"  open_access:  {counts['open_access']:4}  ← likely downloadable")
    log(f"  landing_page: {counts['landing_page']:4}  ← probably paywalled")
    log(f"  not_found:    {counts['not_found']:4}  ← manual search needed")
    log(f"  error:        {counts.get('error', 0):4}")
    log(f"\nDone. Review: {OUTPUT_CSV}")
    _log_fh.close()


if __name__ == "__main__":
    main()

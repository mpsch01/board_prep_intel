"""
match_tiers_to_library.py
=========================
Finds which Must-Read and Core tier references from ITE_Reference_Tiers_Expanded
are physically present in the M1 PDF warehouse.

MATCHING STRATEGY:
  - Extract author last names and publication year from CleanRef
  - Extract first ~1500 chars of PDF text (where authors always appear)
  - Score each ref against each PDF using author name hits + year confirmation
  - AFP articles: 2+ author last names must appear in PDF text
  - Guidelines/Org: org keywords + title words
  - NEJM/JAMA/journal: first author + year + 1-2 title keywords

OUTPUTS (→ archive_canonical/05_acquisition/):
  match_summary.csv    -- full results, every ref with best match
  matched_high.csv     -- confirmed matches (confidence >= 0.60)
  not_found.csv        -- refs with no library match (need sourcing)
  match_report.json    -- summary stats
"""

import os, re, json, csv, datetime
from pathlib import Path
import pandas as pd
import pdfplumber

# ── PATHS ───────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

TIERS_CSV    = PROJECT_ROOT / "archive_canonical" / "04_reference_data" / "ABFM_ITE_ReferenceTiers_Expanded_v1369.csv"
LIBRARY_ROOT = PROJECT_ROOT / "01_module.1_warehouse"
OUT_DIR      = PROJECT_ROOT / "archive_canonical" / "05_acquisition"
os.makedirs(OUT_DIR, exist_ok=True)

CONFIDENT_THRESHOLD = 0.60   # call it a match
LOW_THRESHOLD       = 0.35   # possible match, needs review


# ── Extract first-page text from PDF ────────────────────────────────────────
def get_pdf_header_text(path: str) -> str:
    """Extract text from first 2 pages — enough to find authors and title."""
    try:
        with pdfplumber.open(path) as pdf:
            text = ""
            for page in pdf.pages[:2]:
                t = page.extract_text() or ""
                text += t + "\n"
                if len(text) > 3000:
                    break
        return text[:3000].lower()
    except Exception as e:
        return ""


# ── Parse CleanRef into matchable signals ───────────────────────────────────
def parse_ref(clean_ref: str) -> dict:
    """
    Returns dict with:
      author_lastnames: list of last names (up to 4)
      year: 4-digit year string
      title_words: key content words from title
      org_signals: org/society name fragments for guideline refs
    """
    r = {"author_lastnames": [], "year": "", "title_words": [], "org_signals": []}

    # Year
    m = re.search(r'\b(199\d|200\d|201\d|202\d)\b', clean_ref)
    if m:
        r["year"] = m.group(1)

    # Author last names — pattern: "LastName XX, LastName XX, LastName XX:"
    AUTHOR_COLON_RE_AUTH = re.compile(r'^(?:[A-Z][a-z]+\s+[A-Z]{1,3}(?:\s+Jr|Sr)?(?:,\s+)?)+:')
    if AUTHOR_COLON_RE_AUTH.match(clean_ref):
        first_colon = clean_ref.find(':')
        search_zone = clean_ref[:first_colon + 1]
    else:
        search_zone = clean_ref.split('.')[0]
    author_hits = re.findall(r'\b([A-Z][a-z]{2,15})\s+[A-Z]{1,3}(?:\s+Jr|Sr|[IVX]+)?(?:,|\.|\s+et al|:)', search_zone)
    r["author_lastnames"] = [a.lower() for a in author_hits[:4]]

    # Title words
    JOURNAL_RE = re.compile(
        r'(?:\.\s*|\s+)(?:Am Fam Physician|N Engl J Med|JAMA\b|Lancet\b|Ann Intern Med|'
        r'Circulation\b|Chest\b|Pediatrics\b|Obstet Gynecol|J Clin Endocrinol|'
        r'Clin Infect Dis|Am J Kidney|BMJ\b|JACC\b|Cochrane|Annals\b|'
        r'J Am Coll Cardiol|Am J Med\b|Arch Intern|Mayo Clin|Thyroid\b)',
        re.IGNORECASE
    )
    AUTHOR_COLON_RE = re.compile(r'^(?:[A-Z][a-z]+\s+[A-Z]{1,3}(?:\s+Jr|Sr)?(?:,\s+)?)+:')

    colon_idx = clean_ref.find(':')
    is_author_colon = bool(AUTHOR_COLON_RE.match(clean_ref)) if colon_idx > 0 else False

    if is_author_colon:
        raw = clean_ref[colon_idx + 1:].strip()
        jm = JOURNAL_RE.search(raw)
        raw_title = raw[:jm.start()].strip() if jm else raw[:120]
    else:
        author_end = re.search(r'\.\s+([A-Z][a-zA-Z])', clean_ref)
        if author_end:
            raw = clean_ref[author_end.start() + 2:].strip()
            jm = JOURNAL_RE.search(raw)
            raw_title = raw[:jm.start()].strip() if jm else raw[:120]
        else:
            raw_title = ""

    stop = {'a','an','the','and','or','of','in','for','to','with','by','at','on','from',
            'its','is','are','was','were','been','be','this','that','using','management',
            'clinical','practice','guideline','guidelines','diagnosis','treatment'}
    words = [w.lower().strip('.,;:()[]') for w in raw_title.split()
             if len(w) > 3 and w.lower().strip('.,;:()[]') not in stop]
    r["title_words"] = words[:6]

    # Org signals for guideline refs (when no clear author pattern)
    if not r["author_lastnames"]:
        org_map = [
            (r'USPSTF|preventive services task force|final recommendation', 'uspstf'),
            (r'IDSA|infectious diseases society', 'idsa'),
            (r'american diabetes association|ADA\b', 'diabetes association'),
            (r'bright futures|american academy of pediatrics|AAP\b', 'pediatrics'),
            (r'endocrine society', 'endocrine society'),
            (r'AHA|american heart association', 'heart association'),
            (r'ACC|college of cardiology', 'cardiology'),
            (r'ACR|college of rheumatology', 'rheumatology'),
            (r'global initiative.*obstructive|GOLD\b|GINA\b', 'global initiative'),
            (r'WHO\b|world health organization', 'world health'),
            (r'CDC\b|centers for disease control', 'centers for disease'),
        ]
        for pattern, signal in org_map:
            if re.search(pattern, clean_ref, re.IGNORECASE):
                r["org_signals"].append(signal)

    return r


# ── Common English words that are also valid surnames ───────────────────────
AMBIGUOUS_SURNAMES = {
    "ring", "long", "short", "black", "white", "brown", "green", "gray", "grey",
    "young", "old", "cross", "mann", "new", "free", "stone", "wood", "ford",
    "gold", "rose", "lee", "lane", "park", "hunt", "king", "page", "price",
    "ward", "west", "east", "north", "south", "church", "hill", "hall", "wall",
    "bell", "bird", "wolf", "fox", "moss", "reed", "cole", "cook", "sharp",
    "best", "good", "wise", "rich", "light", "dark", "swift", "fine", "bright",
    "strong", "power", "stern", "stein", "mann", "burns", "waters", "wells",
    "miles", "weeks", "fields", "brooks", "rivers", "woods", "banks", "hayes",
    "smith", "jones", "johnson", "williams", "brown", "davis", "miller",
    "wilson", "moore", "taylor", "anderson", "thomas", "jackson", "white",
    "harris", "martin", "garcia", "martinez", "robinson", "clark", "lewis",
    "walker", "allen", "young", "king", "wright", "scott", "green", "baker",
    "adams", "nelson", "carter", "mitchell", "roberts", "turner", "phillips",
    "campbell", "parker", "evans", "edwards", "collins", "stewart", "morris",
    "rogers", "cook", "morgan", "bell", "murphy", "bailey", "cooper", "cox",
    "diaz", "gray", "james", "watson", "brooks", "kelly", "ward", "sanders",
    "price", "barnes", "ross", "henderson", "coleman", "jenkins", "perry",
    "powell", "long", "foster", "butler", "hayes", "fisher", "gonzalez",
    "burns", "graves", "crohn", "hodgkin", "cushing", "addison", "paget",
    "bright", "cooke", "little", "rich", "minor", "gross", "german", "french",
    "gold", "silver", "diamond", "stone", "reed", "stern", "mann", "baron",
    "geer", "hunt", "wolf", "ford", "hill", "hall", "bell", "cole", "neal",
    "wade", "dean", "shaw", "rice", "lane", "moss", "bond", "carr", "hart",
}


def _author_word_boundary_hit(name: str, text: str) -> bool:
    return bool(re.search(r'\b' + re.escape(name) + r'\b', text))


def _author_in_byline(name: str, text: str) -> bool:
    byline_zone = text[:600]
    if _author_word_boundary_hit(name, byline_zone):
        return True
    return False


# ── Score one ref against one PDF text ──────────────────────────────────────
def score_match(parsed: dict, pdf_text: str) -> float:
    if not pdf_text:
        return 0.0

    score = 0.0
    year  = parsed.get("year", "")

    authors = parsed["author_lastnames"]
    if authors:
        confirmed_hits = 0
        for a in authors:
            if a in AMBIGUOUS_SURNAMES:
                if _author_in_byline(a, pdf_text) and year and year in pdf_text:
                    confirmed_hits += 1
            else:
                if _author_word_boundary_hit(a, pdf_text):
                    confirmed_hits += 1

        if confirmed_hits >= 2:
            score += 0.55
        elif confirmed_hits == 1 and len(authors) == 1:
            if authors[0] in AMBIGUOUS_SURNAMES:
                score += 0.25
            else:
                score += 0.40
        elif confirmed_hits == 1:
            score += 0.18

    if year and year in pdf_text[:800]:
        score += 0.15

    title_words = parsed["title_words"]
    if title_words:
        word_hits = sum(
            1 for w in title_words
            if _author_word_boundary_hit(w, pdf_text)
        )
        score += 0.30 * (word_hits / len(title_words))

    for sig in parsed["org_signals"]:
        if sig in pdf_text:
            score += 0.40
            break

    return min(round(score, 3), 1.0)


# ── Collect all library PDFs ─────────────────────────────────────────────────
def collect_pdfs() -> list:
    pdfs = []
    for dirpath, _, files in os.walk(str(LIBRARY_ROOT)):
        for fname in sorted(files):
            if fname.lower().endswith('.pdf'):
                pdfs.append({
                    "path": os.path.join(dirpath, fname),
                    "filename": fname,
                    "subfolder": os.path.basename(dirpath),
                })
    return pdfs


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  Tier-to-Library Matcher")
    print("=" * 65)

    df = pd.read_csv(TIERS_CSV)
    priority = df[df["Tier"].isin(["Must-Read", "Core"])].drop_duplicates(subset="CleanRef").copy().reset_index(drop=True)
    print(f"  Priority refs: {len(priority)}  (Must-Read={len(df[df['Tier']=='Must-Read'])}, Core={len(df[df['Tier']=='Core'])})")

    pdfs = collect_pdfs()
    print(f"  Library PDFs:  {len(pdfs)}")

    print(f"\n  Extracting PDF header text...")
    pdf_cache = {}
    errors = 0
    for i, pdf in enumerate(pdfs):
        if i % 30 == 0:
            print(f"    [{i:3}/{len(pdfs)}] extracting...")
        text = get_pdf_header_text(pdf["path"])
        pdf_cache[pdf["path"]] = text
        if not text:
            errors += 1
    print(f"  Done. {errors} extraction errors (unreadable PDFs).\n")

    print(f"  Matching {len(priority)} refs against {len(pdfs)} PDFs...")
    results = []

    for _, row in priority.iterrows():
        ref_str  = str(row["CleanRef"])
        tier     = row["Tier"]
        src_type = row["SourceType"]
        cite_ct  = row["CitationCount"]

        parsed = parse_ref(ref_str)

        best_score = 0.0
        best_path  = ""
        best_file  = ""
        best_folder= ""
        second_score = 0.0
        second_file  = ""

        for pdf in pdfs:
            s = score_match(parsed, pdf_cache[pdf["path"]])
            if s > best_score:
                second_score = best_score
                second_file  = best_file
                best_score   = s
                best_path    = pdf["path"]
                best_file    = pdf["filename"]
                best_folder  = pdf["subfolder"]
            elif s > second_score:
                second_score = s
                second_file  = pdf["filename"]

        if best_score >= CONFIDENT_THRESHOLD:
            status = "MATCHED"
        elif best_score >= LOW_THRESHOLD:
            status = "POSSIBLE"
        else:
            status = "NOT_FOUND"

        results.append({
            "tier":            tier,
            "source_type":     src_type,
            "citation_count":  cite_ct,
            "status":          status,
            "confidence":      best_score,
            "matched_file":    best_file,
            "matched_folder":  best_folder,
            "matched_path":    best_path,
            "second_best":     second_file,
            "second_conf":     round(second_score, 3),
            "first_author":    parsed["author_lastnames"][0] if parsed["author_lastnames"] else "",
            "all_authors":     "|".join(parsed["author_lastnames"]),
            "year":            parsed["year"],
            "title_words":     " ".join(parsed["title_words"][:4]),
            "clean_ref":       ref_str,
        })

    matched  = [r for r in results if r["status"] == "MATCHED"]
    possible = [r for r in results if r["status"] == "POSSIBLE"]
    missing  = [r for r in results if r["status"] == "NOT_FOUND"]

    print(f"\n  {'='*65}")
    print(f"  RESULTS SUMMARY")
    print(f"  {'='*65}")
    print(f"  MATCHED    (conf >= {CONFIDENT_THRESHOLD}): {len(matched):4}")
    print(f"  POSSIBLE   (conf >= {LOW_THRESHOLD}):  {len(possible):4}  (needs manual review)")
    print(f"  NOT_FOUND:                    {len(missing):4}  (need to source PDFs)")

    for tier in ["Must-Read", "Core"]:
        t_all  = [r for r in results   if r["tier"] == tier]
        t_mat  = [r for r in matched   if r["tier"] == tier]
        t_pos  = [r for r in possible  if r["tier"] == tier]
        t_mis  = [r for r in missing   if r["tier"] == tier]
        print(f"\n  {tier} ({len(t_all)} total):")
        print(f"    Matched:   {len(t_mat)}")
        print(f"    Possible:  {len(t_pos)}")
        print(f"    Not found: {len(t_mis)}")

    print(f"\n  Core — by SourceType:")
    core_results = [r for r in results if r["tier"] == "Core"]
    src_types = sorted(set(r["source_type"] for r in core_results))
    for st in src_types:
        st_all = [r for r in core_results if r["source_type"] == st]
        st_mat = [r for r in st_all if r["status"] == "MATCHED"]
        st_pos = [r for r in st_all if r["status"] == "POSSIBLE"]
        st_mis = [r for r in st_all if r["status"] == "NOT_FOUND"]
        print(f"    {st:<22} n={len(st_all):3}  matched={len(st_mat):3}  possible={len(st_pos):2}  missing={len(st_mis):3}")

    cols = ["tier","source_type","citation_count","status","confidence",
            "matched_file","matched_folder","first_author","all_authors",
            "year","title_words","second_best","second_conf","clean_ref","matched_path"]

    out_summary = OUT_DIR / "match_summary.csv"
    pd.DataFrame(results)[cols].sort_values(["tier","status","confidence"],
                ascending=[True,True,False]).to_csv(out_summary, index=False)

    out_matched = OUT_DIR / "matched_high.csv"
    pd.DataFrame(matched)[cols].sort_values("confidence", ascending=False).to_csv(out_matched, index=False)

    out_missing = OUT_DIR / "not_found.csv"
    pd.DataFrame(missing)[cols].sort_values(["tier","source_type","citation_count"],
                ascending=[True,True,False]).to_csv(out_missing, index=False)

    report = {
        "run_timestamp": datetime.datetime.now().isoformat(),
        "tiers_csv": str(TIERS_CSV),
        "library_root": str(LIBRARY_ROOT),
        "total_priority_refs": len(priority),
        "library_pdfs_scanned": len(pdfs),
        "thresholds": {"confident": CONFIDENT_THRESHOLD, "possible": LOW_THRESHOLD},
        "totals": {"matched": len(matched), "possible": len(possible), "not_found": len(missing)},
        "by_tier": {
            tier: {
                "total":     len([r for r in results  if r["tier"] == tier]),
                "matched":   len([r for r in matched  if r["tier"] == tier]),
                "possible":  len([r for r in possible if r["tier"] == tier]),
                "not_found": len([r for r in missing  if r["tier"] == tier]),
            } for tier in ["Must-Read", "Core"]
        },
    }
    out_report = OUT_DIR / "match_report.json"
    with open(out_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Outputs written to: {OUT_DIR}")
    print(f"    match_summary.csv  ({len(results)} rows — all refs)")
    print(f"    matched_high.csv   ({len(matched)} confirmed matches)")
    print(f"    not_found.csv      ({len(missing)} refs needing PDFs)")
    print(f"    match_report.json")
    print(f"\n  {'='*65}\n")


if __name__ == "__main__":
    main()

"""
reconcile_reco.py — scan 4 RECO backup folders, cross-ref against missing_articles.csv
Outputs: reco_covered.csv, still_missing.csv, reco_summary.txt
"""
import re, csv
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

RECO_FOLDERS = [
    PROJECT_ROOT / "RECO_right_click",
    PROJECT_ROOT / "RECO_VC_fail",
    PROJECT_ROOT / "RECO_VC_pass",
    PROJECT_ROOT / "RECO_local_lite",
]

CITATION_ROOT = PROJECT_ROOT / "00_database" / "citation_files" / "ITE"
TIER_FOLDERS  = {
    "VC_fail":     CITATION_ROOT / "VC_fail",
    "VC_pass":     CITATION_ROOT / "VC_pass",
    "local_lite":  CITATION_ROOT / "local_lite",
    "right_click": CITATION_ROOT / "right_click",
}

MISSING_CSV    = SCRIPT_DIR / "missing_articles.csv"
RECO_COV_CSV   = SCRIPT_DIR / "reco_covered.csv"
STILL_MISS_CSV = SCRIPT_DIR / "still_missing.csv"
SUMMARY_TXT    = SCRIPT_DIR / "reco_summary.txt"

CODON_RE = re.compile(r'#@#(ART-\d+)@#@', re.IGNORECASE)

def extract_art_id(filename):
    m = CODON_RE.search(filename)
    return m.group(1).upper() if m else None

def scan_folder(folder):
    result = {}
    if not folder.exists():
        return result
    for f in folder.iterdir():
        if f.suffix.lower() == '.pdf':
            art_id = extract_art_id(f.name)
            if art_id:
                result[art_id] = f.name
    return result

def scan_on_disk():
    ids = set()
    for tier_path in TIER_FOLDERS.values():
        if tier_path.exists():
            for f in tier_path.iterdir():
                if f.suffix.lower() == '.pdf':
                    art_id = extract_art_id(f.name)
                    if art_id:
                        ids.add(art_id)
    return ids

def main():
    lines = []

    # 1. Scan RECO folders
    reco_found = {}
    for folder in RECO_FOLDERS:
        hits = scan_folder(folder)
        for art_id, fname in hits.items():
            reco_found[art_id] = {"folder": folder.name, "filename": fname}
        # count all PDFs including legacy-named
        all_pdfs   = list(folder.glob("*.pdf")) if folder.exists() else []
        codon_ct   = len(hits)
        legacy_ct  = len(all_pdfs) - codon_ct
        lines.append(f"  {folder.name}: {len(all_pdfs)} PDFs total  ({codon_ct} codon, {legacy_ct} legacy)")

    lines.append(f"\nTotal unique codon ART-IDs in RECO folders: {len(reco_found)}")

    # 2. Scan currently on-disk citation_files/ITE
    on_disk = scan_on_disk()
    lines.append(f"ART-IDs currently on disk (citation_files/ITE): {len(on_disk)}")

    # 3. Read missing_articles.csv
    if not MISSING_CSV.exists():
        lines.append(f"\nERROR: {MISSING_CSV} not found.")
        print('\n'.join(lines))
        return

    missing_rows = []
    with open(MISSING_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            missing_rows.append(row)
    lines.append(f"Rows in missing_articles.csv: {len(missing_rows)}")

    # 4. Categorize each missing article
    covered_by_reco = []
    covered_by_disk = []
    still_missing   = []

    for row in missing_rows:
        art_id = row['article_id'].upper()
        if art_id in reco_found:
            row['reco_folder']   = reco_found[art_id]['folder']
            row['reco_filename'] = reco_found[art_id]['filename']
            covered_by_reco.append(row)
        elif art_id in on_disk:
            covered_by_disk.append(row)
        else:
            still_missing.append(row)

    lines.append(f"\n── Coverage ───────────────────────────────")
    lines.append(f"  Covered by RECO backup:   {len(covered_by_reco)}")
    lines.append(f"  Already back on disk:     {len(covered_by_disk)}")
    lines.append(f"  STILL MISSING:            {len(still_missing)}")

    # 5. Write reco_covered.csv
    if covered_by_reco:
        fn = list(missing_rows[0].keys()) + ['reco_folder', 'reco_filename']
        with open(RECO_COV_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader(); w.writerows(covered_by_reco)
        lines.append(f"\nWrote reco_covered.csv  ({len(covered_by_reco)} rows)")

    # 6. Write still_missing.csv
    if still_missing:
        fn = list(missing_rows[0].keys())
        with open(STILL_MISS_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader(); w.writerows(still_missing)
        lines.append(f"Wrote still_missing.csv ({len(still_missing)} rows)")

    # 7. Breakdown by source_type
    if still_missing:
        by_src = {}
        for row in still_missing:
            st = row.get('source_type', 'unknown')
            by_src[st] = by_src.get(st, 0) + 1
        lines.append(f"\n── Still missing by source_type ────────────")
        for st, ct in sorted(by_src.items(), key=lambda x: -x[1]):
            lines.append(f"  {st:<32} {ct}")

    # 8. Breakdown by db_tier
    if still_missing:
        by_tier = {}
        for row in still_missing:
            t = row.get('db_tier', 'unknown')
            by_tier[t] = by_tier.get(t, 0) + 1
        lines.append(f"\n── Still missing by db_tier ─────────────────")
        for t, ct in sorted(by_tier.items(), key=lambda x: -x[1]):
            lines.append(f"  {t:<22} {ct}")

    summary = '\n'.join(lines)
    print(summary)
    with open(SUMMARY_TXT, 'w', encoding='utf-8') as f:
        f.write(summary + '\n')
    print(f"\nDone. Summary → {SUMMARY_TXT.name}")

if __name__ == "__main__":
    main()

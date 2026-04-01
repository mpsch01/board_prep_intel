#!/usr/bin/env python3
"""
build_pubmed_citation_icd10.py
02_module.2_processor/scripts/

Crawls JOURNAL_MISSING AAFP citations via NCBI eutils (no API key required).

Flow per citation:
  aafp_citations (JOURNAL_MISSING)
    -> parse raw_text  -> author / year / volume / first_page
    -> NCBI esearch    -> PMID
    -> NCBI efetch     -> MeSH headings
    -> DB lookup       -> ICD-10 code + desc
    -> INSERT OR IGNORE into aafp_question_icd10
    -> INSERT OR IGNORE into pubmed_pmid_cache  (Layer 2 seed)

Run:
    python scripts/build_pubmed_citation_icd10.py

Optional env var:
    NCBI_API_KEY  -- set to unlock 10 req/sec instead of 3 req/sec.
                     Register free at https://www.ncbi.nlm.nih.gov/account/
"""

import os
import re
import sys
import time
import sqlite3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- Paths -------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent   # scripts/ -> module.2/ -> project root
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"

# --- NCBI Config -------------------------------------------------------------
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
RATE_DELAY   = 0.11 if NCBI_API_KEY else 0.36   # 10/sec with key, ~3/sec without
BASE_URL     = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# --- Relevance mapping -------------------------------------------------------
RELEVANCE_MAJOR = "secondary"   # MajorTopicYN = "Y"
RELEVANCE_MINOR = "related"     # MajorTopicYN = "N"

# =============================================================================
# CITATION PARSER
# =============================================================================

def parse_citation(raw: str) -> dict:
    """
    Parse raw citation text into structured lookup fields.
    Returns dict: author, year, volume, first_page, journal (any may be None).
    Handles typical AAFP format:
      Mahajan P, et al. Title. Am Fam Physician. 2024;110(5):503-513.
    """
    r = dict(author=None, year=None, volume=None, first_page=None, journal=None)

    # First author last name
    m = re.match(r"^([A-Z][a-zA-Z\-']+)", raw.strip())
    if m:
        r["author"] = m.group(1)

    # Year -- 4-digit 19xx / 20xx
    m = re.search(r"\b(19[89]\d|20[0-3]\d)\b", raw)
    if m:
        r["year"] = m.group(1)

    # Volume + first page -- patterns: ;110(5):503, ;110:503, 110:503-513
    m = re.search(r";?\s*(\d{1,4})\s*(?:\(\d+\))?\s*:\s*(\d+)", raw)
    if m:
        r["volume"]     = m.group(1)
        r["first_page"] = m.group(2)

    # Journal -- text just before the year/volume block, after the last period
    if r["year"]:
        pre_year = raw[: raw.index(r["year"])]
        parts    = pre_year.rsplit(". ", 1)
        if len(parts) == 2:
            candidate = parts[1].strip().rstrip(". ;")
            if 2 < len(candidate) < 60:
                r["journal"] = candidate

    return r


# =============================================================================
# NCBI HELPERS
# =============================================================================

def _ncbi_get(endpoint: str, params: dict) -> str:
    """HTTP GET to NCBI eutils; returns response text or 'ERROR:...'."""
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    url = BASE_URL + endpoint + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return f"ERROR:{exc}"
    finally:
        time.sleep(RATE_DELAY)

def lookup_pmid(parsed: dict) -> str | None:
    """
    3-pass PMID lookup via esearch:
      Pass 1 -- author + year + journal (tight)
      Pass 2 -- author + year + volume + page (no journal)
      Pass 3 -- author + year only (accepts only unambiguous single result)
    Returns PMID string or None.
    """
    author = parsed.get("author")
    year   = parsed.get("year")
    if not author or not year:
        return None

    def _search(term: str) -> str | None:
        xml = _ncbi_get("esearch.fcgi", {
            "db": "pubmed", "term": term,
            "retmax": "3", "retmode": "xml",
        })
        if xml.startswith("ERROR"):
            return None
        try:
            root = ET.fromstring(xml)
            ids  = [el.text.strip() for el in root.findall(".//Id") if el.text]
            return ids[0] if len(ids) == 1 else None   # unambiguous only
        except ET.ParseError:
            return None

    journal = parsed.get("journal")
    if journal:
        pmid = _search(f'{author}[Author] AND {year}[PDAT] AND "{journal}"[Journal]')
        if pmid:
            return pmid

    vol  = parsed.get("volume")
    page = parsed.get("first_page")
    if vol and page:
        pmid = _search(f"{author}[Author] AND {year}[PDAT] AND {vol}[Volume] AND {page}[Page]")
        if pmid:
            return pmid

    return _search(f"{author}[Author] AND {year}[PDAT]")

def fetch_mesh(pmid: str) -> list:
    """
    Fetch MeSH headings for a PMID via efetch.
    Returns list of {term: str, major: bool}.
    """
    xml = _ncbi_get("efetch.fcgi", {
        "db": "pubmed", "id": pmid,
        "retmode": "xml", "rettype": "abstract",
    })
    if xml.startswith("ERROR"):
        return []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    results = []
    seen    = set()
    for heading in root.iter("MeshHeading"):
        desc = heading.find("DescriptorName")
        if desc is None:
            continue
        term  = (desc.text or "").strip()
        major = desc.get("MajorTopicYN", "N") == "Y"
        if term and term not in seen:
            results.append({"term": term, "major": major})
            seen.add(term)
        for qual in heading.findall("QualifierName"):
            q = (qual.text or "").strip()
            if q and q not in seen and qual.get("MajorTopicYN", "N") == "Y":
                results.append({"term": q, "major": True})
                seen.add(q)
    return results


# =============================================================================
# ICD-10 LOOKUP TABLE
# =============================================================================

def build_icd10_lookup(conn: sqlite3.Connection) -> list:
    """
    Build list of (code, desc, desc_lower) from article_icd10,
    icd10_rollup, and icd10_code_xref (whichever exist).
    Sorted longest-description-first for greedy substring match.
    """
    cur   = conn.cursor()
    pairs = {}

    cur.execute("""
        SELECT DISTINCT icd10_code, icd10_desc
        FROM article_icd10
        WHERE icd10_desc IS NOT NULL AND icd10_desc != ''
    """)
    for code, desc in cur.fetchall():
        pairs[code] = (code, desc, desc.lower())

    try:
        cur.execute("SELECT DISTINCT code, description FROM icd10_rollup WHERE description IS NOT NULL")
        for code, desc in cur.fetchall():
            if code not in pairs:
                pairs[code] = (code, desc, desc.lower())
    except Exception:
        pass

    try:
        cur.execute("SELECT DISTINCT icd10_code, display_name FROM icd10_code_xref WHERE display_name IS NOT NULL")
        for code, desc in cur.fetchall():
            if code not in pairs:
                pairs[code] = (code, desc, desc.lower())
    except Exception:
        pass

    return sorted(pairs.values(), key=lambda x: len(x[1]), reverse=True)


def mesh_term_to_icd10(term: str, lookup: list):
    """
    Map a MeSH heading to (code, desc) via:
      1. Exact match
      2. MeSH term is substring of ICD-10 desc
      3. ICD-10 desc is substring of MeSH term
    Returns (code, desc) or None.
    """
    base = term.lower().strip().split("/")[0].rstrip(" .,;:")
    if not base:
        return None

    for code, desc, desc_lower in lookup:
        if base == desc_lower:
            return (code, desc)
    for code, desc, desc_lower in lookup:
        if base in desc_lower:
            return (code, desc)
    for code, desc, desc_lower in lookup:
        if len(desc_lower) >= 4 and desc_lower in base:
            return (code, desc)
    return None


# =============================================================================
# DB OPERATIONS
# =============================================================================

def ensure_pubmed_cache_table(conn: sqlite3.Connection):
    """Create pubmed_pmid_cache if not present (Layer 2 seed table)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pubmed_pmid_cache (
            citation_id   TEXT    PRIMARY KEY,
            pmid          TEXT    NOT NULL,
            lookup_date   TEXT    DEFAULT (date('now')),
            mesh_count    INTEGER DEFAULT 0
        )
    """)


def load_journal_missing(conn: sqlite3.Connection) -> list:
    cur = conn.cursor()
    cur.execute("""
        SELECT ac.citation_id, ac.aafp_qid, acr.raw_text
        FROM   aafp_citations      ac
        JOIN   aafp_citation_raw   acr ON acr.citation_id = ac.citation_id
        WHERE  ac.unmatched_class = 'JOURNAL_MISSING'
          AND  acr.raw_text    IS NOT NULL
          AND  acr.raw_text    != ''
        ORDER  BY ac.citation_id
    """)
    return [{"citation_id": r[0], "aafp_qid": r[1], "raw_text": r[2]}
            for r in cur.fetchall()]


def already_cached_ids(conn: sqlite3.Connection) -> set:
    cur = conn.cursor()
    cur.execute("SELECT citation_id FROM pubmed_pmid_cache")
    return {r[0] for r in cur.fetchall()}


def insert_icd10_for_question(conn, aafp_qid, icd10_rows) -> int:
    cur      = conn.cursor()
    inserted = 0
    for row in icd10_rows:
        cur.execute("""
            INSERT OR IGNORE INTO aafp_question_icd10
                (aafp_qid, icd10_code, icd10_desc, relevance)
            VALUES (?, ?, ?, ?)
        """, (aafp_qid, row["icd10_code"], row["icd10_desc"], row["relevance"]))
        inserted += cur.rowcount
    return inserted


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 65)
    print("build_pubmed_citation_icd10.py")
    print("PubMed MeSH  ->  aafp_question_icd10")
    print("=" * 65)

    if NCBI_API_KEY:
        print("NCBI API key detected -- rate limit: 10 req/sec")
    else:
        print("No NCBI_API_KEY env var -- rate limit: ~3 req/sec (~4-5 min total)")
        print("  Set NCBI_API_KEY for faster processing.")

    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        ensure_pubmed_cache_table(conn)
        conn.commit()

        all_citations = load_journal_missing(conn)
        print(f"\nJOURNAL_MISSING citations:  {len(all_citations)}")

        cached     = already_cached_ids(conn)
        to_process = [c for c in all_citations if c["citation_id"] not in cached]
        print(f"Already cached (prior run): {len(cached)}")
        print(f"To process this run:        {len(to_process)}")

        if not to_process:
            print("\nAll citations already processed. Nothing to do.")
            return

        print("\nBuilding ICD-10 lookup from DB...", end=" ", flush=True)
        icd10_lookup = build_icd10_lookup(conn)
        print(f"{len(icd10_lookup):,} codes loaded")

        stats = dict(
            parse_fail=0, pmid_found=0, pmid_miss=0,
            mesh_found=0, mesh_miss=0,
            icd10_mapped=0, icd10_skip=0,
            rows_inserted=0,
        )

        print(f"\nProcessing {len(to_process)} citations...")
        print("-" * 65)

        for idx, cit in enumerate(to_process, 1):
            cid = cit["citation_id"]
            qid = cit["aafp_qid"]
            raw = cit["raw_text"]

            if idx % 25 == 1:
                pct = (idx - 1) / len(to_process) * 100
                print(f"  [{idx-1:>3}/{len(to_process)}]  {pct:.0f}%  "
                      f"pmid={stats['pmid_found']}  inserted={stats['rows_inserted']}")

            # 1. Parse
            parsed = parse_citation(raw)
            if not parsed["year"]:
                stats["parse_fail"] += 1
                conn.execute(
                    "INSERT OR IGNORE INTO pubmed_pmid_cache "
                    "(citation_id, pmid, mesh_count) VALUES (?, 'UNPARSEABLE', 0)",
                    (cid,)
                )
                conn.commit()
                continue

            # 2. PubMed PMID lookup
            pmid = lookup_pmid(parsed)
            if not pmid:
                stats["pmid_miss"] += 1
                continue

            stats["pmid_found"] += 1

            # 3. MeSH terms
            mesh_terms = fetch_mesh(pmid)
            if not mesh_terms:
                stats["mesh_miss"] += 1
                conn.execute(
                    "INSERT OR IGNORE INTO pubmed_pmid_cache "
                    "(citation_id, pmid, mesh_count) VALUES (?, ?, 0)",
                    (cid, pmid)
                )
                conn.commit()
                continue

            stats["mesh_found"] += 1

            # 4. Map MeSH -> ICD-10
            icd10_rows = []
            seen_codes = set()
            for m in mesh_terms:
                hit = mesh_term_to_icd10(m["term"], icd10_lookup)
                if hit and hit[0] not in seen_codes:
                    seen_codes.add(hit[0])
                    relevance = RELEVANCE_MAJOR if m["major"] else RELEVANCE_MINOR
                    icd10_rows.append({
                        "icd10_code": hit[0],
                        "icd10_desc": hit[1],
                        "relevance":  relevance,
                    })

            if not icd10_rows:
                stats["icd10_skip"] += 1
            else:
                stats["icd10_mapped"] += 1
                n = insert_icd10_for_question(conn, qid, icd10_rows)
                stats["rows_inserted"] += n

            # 5. Cache PMID
            conn.execute(
                "INSERT OR IGNORE INTO pubmed_pmid_cache "
                "(citation_id, pmid, mesh_count) VALUES (?, ?, ?)",
                (cid, pmid, len(mesh_terms))
            )
            conn.commit()

        # --- QC Report -------------------------------------------------------
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM pubmed_pmid_cache WHERE pmid != 'UNPARSEABLE'")
        cache_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT aafp_qid) FROM aafp_question_icd10")
        q_tagged_total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM aafp_question_icd10")
        icd10_total = cur.fetchone()[0]

        cur.execute("""
            SELECT relevance, COUNT(*) FROM aafp_question_icd10
            GROUP BY relevance ORDER BY relevance
        """)
        rel_counts = dict(cur.fetchall())

        n = len(to_process)
        print("\n" + "=" * 65)
        print("QC REPORT")
        print("=" * 65)
        print(f"Citations processed this run : {n}")
        print(f"  Parse failures (no year)   : {stats['parse_fail']}")
        print(f"  PMID not found             : {stats['pmid_miss']}")
        print(f"  PMID resolved              : {stats['pmid_found']}  "
              f"({stats['pmid_found']/max(n,1)*100:.1f}%)")
        print(f"  MeSH returned              : {stats['mesh_found']}")
        print(f"  MeSH->ICD-10 mapped        : {stats['icd10_mapped']}")
        print(f"  Rows inserted              : {stats['rows_inserted']}")
        print()
        print(f"pubmed_pmid_cache total      : {cache_count}")
        print()
        print(f"aafp_question_icd10 -- TOTALS")
        print(f"  Total rows                 : {icd10_total:,}")
        print(f"  Unique questions tagged    : {q_tagged_total:,}")
        for rel in ("primary", "secondary", "related"):
            cnt = rel_counts.get(rel, 0)
            pct = cnt / max(icd10_total, 1) * 100
            print(f"  {rel:<10}               : {cnt:>5}  ({pct:.1f}%)")

    except Exception as exc:
        conn.rollback()
        print(f"\nFATAL ERROR: {exc}")
        raise
    finally:
        conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()

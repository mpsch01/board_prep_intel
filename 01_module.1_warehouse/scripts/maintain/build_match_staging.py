"""
build_match_staging.py — Migration Step 1: Build Match Staging Report
======================================================================
Codon Migration | ITE Intelligence 2.0

Pairs every PDF in 01_pdf_guideline_library/ with its corresponding
article record in ite_intelligence.db. Produces a dry-run report —
no files are moved or renamed.

Three data sources feed the matching:
  1. crosswalk_index.json — links PDFs → enriched JSONs → QIDs/tiers
  2. Enriched JSONs (03_enriched_JSON/) — contain source.title, source.publication_year, etc.
  3. ite_intelligence.db — contains articles.codon_filename, article_id, author/year/title

Match Tiers:
  Tier 1 (high confidence):  Enriched JSON has ite_intelligence block with linked QIDs
                              → re-match to DB via author+year or title+year
  Tier 2 (medium confidence): Enriched JSON exists but no ite_intelligence block OR
                              ite_intelligence block has no linked QIDs
                              → match via source metadata (title, year, authors)
  Tier 3 (low confidence):   No enriched JSON at all
                              → match via PDF filename patterns only

Output:
  match_staging_report.json — full machine-readable report
  match_staging_report.txt  — human-readable summary for Mikey to review

Run:
  python scripts/build_match_staging.py
  python scripts/build_match_staging.py --verbose
"""

import sqlite3, json, re, os, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent          # 02_ite_intelligence/
PROJ_ROOT    = BASE_DIR.parent.parent                          # claude_knowledge/
DB_PATH      = PROJ_ROOT / "00_database" / "db" / "ite_intelligence.db"
CROSSWALK    = BASE_DIR / "crosswalk_index.json"
OVERRIDES    = BASE_DIR / "manual_overrides.json"
PDF_DIR      = PROJ_ROOT / "clinical_guidelines" / "01_pdf_guideline_library" / "pdf_non-codon"
ENRICHED_DIR = PROJ_ROOT / "clinical_guidelines" / "03_enriched_JSON"
OUTPUT_DIR   = BASE_DIR / "logs"

# ── Title stopwords (from enricher — keeps matching consistent) ────────────
_TITLE_STOPWORDS = {
    "diagnosis","management","treatment","guidelines","guideline","clinical",
    "practice","update","common","review","adults","adult","acute","chronic",
    "patient","evaluation","assessment","overview","approach","evidence","based",
    "rapid","initial","primary","secondary","prevention","detection","screening",
    "recommendations","recommendation","related","associated","versus","using",
    "questions","answers","disorders","disorder","disease","diseases",
}


# ═══════════════════════════════════════════════════════════════════════════
#  DB INDEX BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def build_db_indexes(conn):
    """
    Build lookup indexes from the articles table for fast matching.
    Returns dict with multiple index views into the same data.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT article_id, clean_ref, codon_filename, author1, author2,
               year, title, source_type, tier, citation_count, unique_years,
               exam_years, extraction_status, canonical_filename
        FROM articles
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    articles = []
    for row in rows:
        articles.append(dict(zip(cols, row)))

    # Index 1: article_id → article dict
    by_id = {a["article_id"]: a for a in articles}

    # Index 2: (author1_lower, year) → [article dicts]
    by_author_year = {}
    for a in articles:
        if a["author1"] and a["year"]:
            key = (a["author1"].lower().replace("'", ""), a["year"])
            by_author_year.setdefault(key, []).append(a)

    # Index 3: title keywords (5+ chars, non-stopword) → {year → [article dicts]}
    by_keyword_year = {}
    for a in articles:
        ref = (a["clean_ref"] or "").lower()
        words = set(re.findall(r'\b[a-z]{5,}\b', ref)) - _TITLE_STOPWORDS
        for w in words:
            by_keyword_year.setdefault(w, {}).setdefault(a["year"], []).append(a)

    # Index 4: qid → [article_ids] (for reverse QID lookup)
    cur.execute("SELECT qid, article_id FROM qid_art_xref")
    qid_to_articles = {}
    for qid, art_id in cur.fetchall():
        qid_to_articles.setdefault(qid, []).append(art_id)

    return {
        "all": articles,
        "by_id": by_id,
        "by_author_year": by_author_year,
        "by_keyword_year": by_keyword_year,
        "qid_to_articles": qid_to_articles,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  MATCHING ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def extract_author_year_from_filename(filename):
    """
    Try to parse author surname and year from various filename patterns.
    Returns (author, year) or (None, None).
    """
    stem = Path(filename).stem

    # Pattern A: NN_Topic_Author_Year (numbered series)
    # e.g. "01_Hip_Pain_Adults_Chamberlain_2021 (1)"
    m = re.search(r'_([A-Z][a-z]+)_(\d{4})', stem)
    if m:
        return m.group(1).lower(), m.group(2)

    # Pattern B: Author_Author_Year (canonical style)
    # e.g. "Gaitonde_Moore_2019", "Charles_Triscott_2017"
    m = re.match(r'^([A-Z][a-z]+)_([A-Z][a-z]+)_(\d{4})', stem)
    if m:
        return m.group(1).lower(), m.group(3)

    # Pattern C: prefix_topic with year embedded
    # e.g. "afp_HTN_combo_therapy" — no year in filename
    # (these rely on enriched JSON metadata)
    return None, None


def extract_metadata_from_enriched_json(ej_path):
    """
    Read enriched JSON and return source metadata useful for matching.
    Returns dict with title, year, authors, org, has_ite_block, qid_count.
    """
    try:
        with open(ej_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    src = data.get("source", {})
    ite = data.get("ite_intelligence", {})

    # Extract first author surname from citation_display
    citation = src.get("citation_display", "") or ""
    author_from_citation = None
    # Pattern: "Chamberlain R:" or "Dakkak M, Lanney H."
    m = re.match(r'^([A-Za-z\-\']+)\s', citation)
    if m:
        author_from_citation = m.group(1).lower().replace("'", "")

    # Year: prefer source.publication_year, fallback to parsing from citation_display
    year = str(src.get("publication_year", "") or "")
    if not year:
        # Try to extract year from citation: "... 2021;103(2):81-89" or "... 2020."
        yr_match = re.search(r'\b(19|20)\d{2}\b', citation)
        if yr_match:
            year = yr_match.group(0)

    # Extract linked QIDs from ite_intelligence block
    linked_qids = []
    for lq in (ite.get("linked_qids", []) or []):
        if isinstance(lq, dict) and lq.get("qid"):
            linked_qids.append(lq["qid"])
    # Fallback: question_ids field (older format)
    if not linked_qids:
        linked_qids = ite.get("question_ids", []) or []

    return {
        "title": src.get("title", ""),
        "year": year,
        "org": src.get("organization", ""),
        "file_name": src.get("file_name", ""),
        "citation_display": citation,
        "author_from_citation": author_from_citation,
        "linked_qids": linked_qids,
        "has_ite_block": bool(ite),
        "qid_count": len(ite.get("linked_qids", []) or ite.get("question_ids", []) or []),
        "match_method_used": ite.get("_match_method", ""),
        "enrichment_confidence": ite.get("enrichment_confidence", ""),
    }


def title_keywords(title):
    """Extract meaningful keywords from a title (5+ chars, non-stopword)."""
    words = re.findall(r'\b[a-zA-Z]{5,}\b', title or "")
    return [w.lower() for w in words if w.lower() not in _TITLE_STOPWORDS]


def match_pdf_to_article(pdf_name, crosswalk_entry, db_idx):
    """
    Attempt to match a PDF to an article in the DB.

    Returns dict:
      {
        "article_id": "ART-XXXX" or None,
        "codon_filename": "...",
        "match_tier": 1|2|3,
        "match_method": str,
        "confidence": "high"|"medium"|"low",
        "candidates": [...],  # if ambiguous
        "notes": str,
      }
    """
    result = {
        "article_id": None,
        "codon_filename": None,
        "match_tier": 3,
        "match_method": "unmatched",
        "confidence": "low",
        "candidates": [],
        "notes": "",
        "db_title": "",
        "db_author1": "",
        "db_year": "",
        "db_tier": "",
        "db_citation_count": 0,
    }

    ej_meta = None
    ej_path = None

    # Load enriched JSON metadata if available
    if crosswalk_entry and crosswalk_entry.get("enriched_json"):
        ej_file = crosswalk_entry["enriched_json"].get("path", "")
        if ej_file:
            ej_path = ENRICHED_DIR / ej_file
            if ej_path.exists():
                ej_meta = extract_metadata_from_enriched_json(ej_path)

    # ── Tier 1: Enriched JSON exists with ITE intelligence + QIDs ──────
    if ej_meta and ej_meta["has_ite_block"] and ej_meta["qid_count"] > 0:
        result["match_tier"] = 1

        # Strategy A: Reverse QID lookup — most reliable
        # If we have linked QIDs, look up which article(s) they map to in qid_art_xref
        if ej_meta.get("linked_qids"):
            art_id_votes = Counter()
            qid_idx = db_idx["qid_to_articles"]
            for qid in ej_meta["linked_qids"]:
                for art_id in qid_idx.get(qid, []):
                    art_id_votes[art_id] += 1
            if art_id_votes:
                best_id, best_count = art_id_votes.most_common(1)[0]
                total_qids = len(ej_meta["linked_qids"])
                article = db_idx["by_id"].get(best_id)
                if article:
                    _fill_result(result, article, "tier1_qid_reverse_lookup")
                    # Confidence based on vote strength + metadata cross-check
                    vote_ratio = best_count / total_qids if total_qids else 0

                    # Cross-check: does DB article's author/year match enriched JSON's?
                    metadata_match = False
                    db_author = (article.get("author1") or "").lower().replace("'", "")
                    ej_author = ej_meta.get("author_from_citation", "") or ""
                    ej_year = ej_meta.get("year", "")
                    db_year = article.get("year", "")
                    if db_author and ej_author and db_author == ej_author:
                        metadata_match = True
                    if db_year and ej_year and db_year == ej_year and metadata_match:
                        metadata_match = True  # both author AND year match

                    if metadata_match and best_count >= 1:
                        result["confidence"] = "high"
                    elif vote_ratio >= 0.5 and best_count >= 2:
                        result["confidence"] = "high"
                    elif best_count >= 2:
                        result["confidence"] = "medium"
                    else:
                        # Single QID vote, no metadata confirmation
                        # Likely a supplementary guideline, not the actual DB article
                        result["confidence"] = "low"
                    result["qid_vote_detail"] = {
                        "total_qids": total_qids,
                        "best_votes": best_count,
                        "vote_ratio": round(vote_ratio, 2),
                        "candidates": len(art_id_votes),
                    }
                    if len(art_id_votes) > 1:
                        result["notes"] = (
                            f"QID vote: {best_id}={best_count}/{total_qids} "
                            f"({len(art_id_votes)} candidates). "
                            f"Runner-up: {art_id_votes.most_common(2)[1][0]}={art_id_votes.most_common(2)[1][1]}"
                        )
                    return result

        # Strategy B: Author+year and title keyword matching from enriched metadata
        article = _try_match_metadata(ej_meta, db_idx)
        if article:
            _fill_result(result, article, "tier1_metadata")
            result["confidence"] = "high"
            return result

        # Tier 1 but couldn't re-resolve — flag it
        result["notes"] = "Has ITE block with QIDs but could not re-resolve to DB article"
        result["confidence"] = "medium"
        result["match_method"] = "tier1_unresolved"
        return result

    # ── Tier 2: Enriched JSON exists but no ITE block or no QIDs ───────
    if ej_meta:
        result["match_tier"] = 2

        # Try QID reverse lookup even for Tier 2 (some may have question_ids but no linked_qids)
        if ej_meta.get("linked_qids"):
            art_id_votes = Counter()
            qid_idx = db_idx["qid_to_articles"]
            for qid in ej_meta["linked_qids"]:
                for art_id in qid_idx.get(qid, []):
                    art_id_votes[art_id] += 1
            if art_id_votes:
                best_id, best_count = art_id_votes.most_common(1)[0]
                article = db_idx["by_id"].get(best_id)
                if article:
                    _fill_result(result, article, "tier2_qid_reverse_lookup")
                    result["confidence"] = "medium"
                    return result

        article = _try_match_metadata(ej_meta, db_idx)
        if article:
            _fill_result(result, article, "tier2_source_metadata")
            result["confidence"] = "medium"
            return result
        # Try author from citation
        if ej_meta["author_from_citation"] and ej_meta["year"]:
            key = (ej_meta["author_from_citation"], ej_meta["year"])
            candidates = db_idx["by_author_year"].get(key, [])
            if len(candidates) == 1:
                _fill_result(result, candidates[0], "tier2_citation_author_year")
                result["confidence"] = "medium"
                return result
            elif len(candidates) > 1:
                result["candidates"] = [
                    {"article_id": c["article_id"], "clean_ref": c["clean_ref"][:80]}
                    for c in candidates
                ]
                result["notes"] = f"Ambiguous: {len(candidates)} candidates for author+year"
                result["match_method"] = "tier2_ambiguous"
                return result
        result["notes"] = "Enriched JSON exists but no ITE data and metadata match failed"
        result["match_method"] = "tier2_unresolved"
        return result

    # ── Tier 3: No enriched JSON — filename-only matching ──────────────
    result["match_tier"] = 3
    author, year = extract_author_year_from_filename(pdf_name)
    if author and year:
        key = (author.replace("'", ""), year)
        candidates = db_idx["by_author_year"].get(key, [])
        if len(candidates) == 1:
            _fill_result(result, candidates[0], "tier3_filename_author_year")
            result["confidence"] = "medium"
            return result
        elif len(candidates) > 1:
            result["candidates"] = [
                {"article_id": c["article_id"], "clean_ref": c["clean_ref"][:80]}
                for c in candidates
            ]
            result["notes"] = f"Ambiguous: {len(candidates)} candidates for filename author+year"
            result["match_method"] = "tier3_ambiguous"
            return result

    # Last resort: try to extract topic keywords from filename
    stem = Path(pdf_name).stem.lower()
    # Remove common prefixes
    for prefix in ["afp_", "uspstf_", "idsa_", "aafp_", "peds_", "neuro_",
                    "rheum_", "tox_", "jacc_", "ajkd_", "apa_", "acog_", "ada_", "aap_"]:
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
            break
    # Remove leading numbers + underscore
    stem = re.sub(r'^\d+_', '', stem)

    words = [w for w in re.findall(r'[a-z]{5,}', stem) if w not in _TITLE_STOPWORDS]
    if len(words) >= 2:
        # Try to find articles where clean_ref contains both keywords
        candidates = []
        kw_idx = db_idx["by_keyword_year"]
        if words[0] in kw_idx:
            # Look across all years for this keyword combo
            for yr, arts in kw_idx[words[0]].items():
                for a in arts:
                    ref_lower = a["clean_ref"].lower()
                    if all(w in ref_lower for w in words[:3]):
                        candidates.append(a)
        # Deduplicate
        seen = set()
        unique = []
        for c in candidates:
            if c["article_id"] not in seen:
                seen.add(c["article_id"])
                unique.append(c)
        if len(unique) == 1:
            _fill_result(result, unique[0], "tier3_filename_keywords")
            result["confidence"] = "low"
            return result
        elif len(unique) > 1:
            result["candidates"] = [
                {"article_id": c["article_id"], "clean_ref": c["clean_ref"][:80]}
                for c in unique[:5]
            ]
            result["notes"] = f"Keyword match found {len(unique)} candidates"
            result["match_method"] = "tier3_keyword_ambiguous"
            return result

    result["notes"] = "No matching strategy succeeded"
    result["match_method"] = "unmatched"
    return result


def _try_match_metadata(ej_meta, db_idx):
    """
    Try matching enriched JSON metadata → DB article via author+year, then title keywords.
    Returns article dict or None.
    """
    # Try author from citation + year
    if ej_meta["author_from_citation"] and ej_meta["year"]:
        key = (ej_meta["author_from_citation"], ej_meta["year"])
        candidates = db_idx["by_author_year"].get(key, [])
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            # Disambiguate via title keywords
            tkws = title_keywords(ej_meta["title"])
            for c in candidates:
                ref_lower = c["clean_ref"].lower()
                if tkws and sum(1 for w in tkws[:4] if w in ref_lower) >= 2:
                    return c

    # Try title keywords + year
    if ej_meta["title"] and ej_meta["year"]:
        tkws = title_keywords(ej_meta["title"])
        specific = [w for w in tkws if w not in _TITLE_STOPWORDS][:3]
        if len(specific) >= 2:
            kw_idx = db_idx["by_keyword_year"]
            if specific[0] in kw_idx and ej_meta["year"] in kw_idx[specific[0]]:
                for a in kw_idx[specific[0]][ej_meta["year"]]:
                    ref_lower = a["clean_ref"].lower()
                    if all(w in ref_lower for w in specific[:2]):
                        return a

    return None


def _fill_result(result, article, method):
    """Fill result dict from a matched article."""
    result["article_id"] = article["article_id"]
    result["codon_filename"] = article["codon_filename"]
    result["match_method"] = method
    result["db_title"] = (article["title"] or "")[:100]
    result["db_author1"] = article["author1"] or ""
    result["db_year"] = article["year"] or ""
    result["db_tier"] = article["tier"] or ""
    result["db_citation_count"] = article["citation_count"] or 0


# ═══════════════════════════════════════════════════════════════════════════
#  REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def generate_text_report(results, output_path):
    """Write human-readable staging report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Separate active results from omitted
    active    = [r for r in results if r["match_method"] != "omitted"]
    omitted   = [r for r in results if r["match_method"] == "omitted"]
    manual    = [r for r in results if r["match_method"] == "manual_override"]
    dupes     = [r for r in results if r.get("is_duplicate")]
    matched   = sum(1 for r in active if r["article_id"])
    unmatched = sum(1 for r in active if not r["article_id"])

    method_counts = Counter(r["match_method"] for r in results)
    conf_counts = Counter(r["confidence"] for r in active if r["article_id"])

    lines = []
    lines.append("MATCH STAGING REPORT — Codon Migration Step 1")
    lines.append(f"Generated: {now}")
    lines.append("=" * 70)
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total PDFs:          {len(results)}")
    lines.append(f"  Omitted (non-ITE):   {len(omitted)}")
    lines.append(f"  Active (migration):  {len(active)}")
    lines.append(f"    Matched:           {matched}  ({matched*100//max(len(active),1)}%)")
    lines.append(f"    Manual overrides:  {len(manual)}  ({len(dupes)} are duplicate PDFs)")
    lines.append(f"    Unmatched:         {unmatched}")
    lines.append("")

    lines.append("MIGRATION READINESS")
    lines.append("-" * 40)
    unique_matched = len(set(r["article_id"] for r in active if r["article_id"]))
    lines.append(f"  Unique articles matched:  {unique_matched}")
    lines.append(f"  Ready for rename (Step 4): {matched - len(dupes)} PDFs → {unique_matched} codon filenames")
    lines.append(f"  Duplicate PDFs to discard: {len(dupes)}")
    lines.append(f"  Still unresolved:          {unmatched}")
    lines.append("")

    lines.append("BY MATCH TIER (active files only)")
    lines.append("-" * 40)
    tier_labels = {0: "Manual Override", 1: "Tier 1 (ITE metadata)", 2: "Tier 2 (source metadata)", 3: "Tier 3 (filename only)"}
    for t in [0, 1, 2, 3]:
        tier_results = [r for r in active if r["match_tier"] == t]
        if not tier_results:
            continue
        tier_matched = sum(1 for r in tier_results if r["article_id"])
        lines.append(f"  {tier_labels[t]}: {len(tier_results)} total, {tier_matched} matched")
    lines.append("")

    lines.append("BY CONFIDENCE (matched only)")
    lines.append("-" * 40)
    for c in ["high", "medium", "low"]:
        lines.append(f"  {c}: {conf_counts.get(c, 0)}")
    lines.append("")

    lines.append("BY MATCH METHOD")
    lines.append("-" * 40)
    for m, c in method_counts.most_common():
        lines.append(f"  {m}: {c}")
    lines.append("")

    # ── Manual overrides (human-reviewed) ────────────────────────────
    if manual:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"MANUAL OVERRIDES — HUMAN-REVIEWED ({len(manual)})")
        lines.append("Matched by Mikey during review. Highest confidence.")
        lines.append("=" * 70)
        for r in sorted(manual, key=lambda x: x["article_id"]):
            dup_flag = " *** DUPLICATE ***" if r.get("is_duplicate") else ""
            lines.append(f"  {r['pdf_filename']}{dup_flag}")
            lines.append(f"    → {r['article_id']}  {r['codon_filename']}")
            lines.append(f"      {r['notes']}")
            lines.append("")

    # ── Tier 1 matches (high confidence — just verify) ─────────────────
    t1 = [r for r in results if r["match_tier"] == 1 and r["article_id"]]
    if t1:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"TIER 1 MATCHES — HIGH CONFIDENCE ({len(t1)})")
        lines.append("These have ITE intelligence data. Spot-check a few.")
        lines.append("=" * 70)
        for r in sorted(t1, key=lambda x: x["article_id"]):
            lines.append(f"  {r['pdf_filename']}")
            lines.append(f"    → {r['article_id']}  {r['codon_filename']}")
            lines.append(f"      {r['db_author1']} {r['db_year']} | tier={r['db_tier']} | cites={r['db_citation_count']} | method={r['match_method']}")
            lines.append("")

    # ── Tier 2 matches (medium — review more carefully) ────────────────
    t2_matched = [r for r in results if r["match_tier"] == 2 and r["article_id"]]
    t2_unmatched = [r for r in results if r["match_tier"] == 2 and not r["article_id"]]
    if t2_matched:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"TIER 2 MATCHES — MEDIUM CONFIDENCE ({len(t2_matched)})")
        lines.append("Enriched JSON exists, matched via source metadata. Review these.")
        lines.append("=" * 70)
        for r in sorted(t2_matched, key=lambda x: x["article_id"]):
            lines.append(f"  {r['pdf_filename']}")
            lines.append(f"    → {r['article_id']}  {r['codon_filename']}")
            lines.append(f"      {r['db_author1']} {r['db_year']} | method={r['match_method']}")
            if r["notes"]:
                lines.append(f"      NOTE: {r['notes']}")
            lines.append("")

    if t2_unmatched:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"TIER 2 UNRESOLVED ({len(t2_unmatched)})")
        lines.append("Have enriched JSONs but could not match to DB. Need manual review or API batch.")
        lines.append("=" * 70)
        for r in sorted(t2_unmatched, key=lambda x: x["pdf_filename"]):
            lines.append(f"  {r['pdf_filename']}")
            lines.append(f"      method={r['match_method']}")
            if r["notes"]:
                lines.append(f"      NOTE: {r['notes']}")
            if r["candidates"]:
                lines.append(f"      CANDIDATES:")
                for c in r["candidates"]:
                    lines.append(f"        {c['article_id']}: {c['clean_ref']}")
            lines.append("")

    # ── Tier 3 (filename only — lowest confidence) ─────────────────────
    t3_matched = [r for r in results if r["match_tier"] == 3 and r["article_id"]]
    t3_unmatched = [r for r in results if r["match_tier"] == 3 and not r["article_id"]]
    if t3_matched:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"TIER 3 MATCHES — LOW CONFIDENCE ({len(t3_matched)})")
        lines.append("No enriched JSON, matched by filename patterns only. Review carefully.")
        lines.append("=" * 70)
        for r in sorted(t3_matched, key=lambda x: x["article_id"]):
            lines.append(f"  {r['pdf_filename']}")
            lines.append(f"    → {r['article_id']}  {r['codon_filename']}")
            lines.append(f"      {r['db_author1']} {r['db_year']} | method={r['match_method']}")
            if r["notes"]:
                lines.append(f"      NOTE: {r['notes']}")
            lines.append("")

    if t3_unmatched:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"TIER 3 UNMATCHED ({len(t3_unmatched)})")
        lines.append("No enriched JSON and filename matching failed. Candidates for API batch (Step 2).")
        lines.append("=" * 70)
        for r in sorted(t3_unmatched, key=lambda x: x["pdf_filename"]):
            lines.append(f"  {r['pdf_filename']}")
            if r["notes"]:
                lines.append(f"      NOTE: {r['notes']}")
            if r["candidates"]:
                lines.append(f"      CANDIDATES:")
                for c in r["candidates"]:
                    lines.append(f"        {c['article_id']}: {c['clean_ref']}")
            lines.append("")

    # ── Duplicate ART-ID check ─────────────────────────────────────────
    art_ids = [r["article_id"] for r in results if r["article_id"]]
    dupes = {k: v for k, v in Counter(art_ids).items() if v > 1}
    if dupes:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"⚠ DUPLICATE ART-ID ASSIGNMENTS ({len(dupes)})")
        lines.append("Multiple PDFs mapped to the same article. One may be a duplicate PDF.")
        lines.append("=" * 70)
        for art_id, count in sorted(dupes.items()):
            lines.append(f"  {art_id} assigned to {count} PDFs:")
            for r in results:
                if r["article_id"] == art_id:
                    lines.append(f"    - {r['pdf_filename']}")
            lines.append("")

    # ── Omitted files ────────────────────────────────────────────────
    if omitted:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"OMITTED FROM MIGRATION ({len(omitted)})")
        lines.append("Supplementary guidelines, algorithms, and non-ITE references.")
        lines.append("These stay in the library with their current names.")
        lines.append("=" * 70)
        for r in sorted(omitted, key=lambda x: x["pdf_filename"]):
            lines.append(f"  {r['pdf_filename']}")
        lines.append("")

    # ── Footer ─────────────────────────────────────────────────────────
    lines.append("")
    lines.append("=" * 70)
    lines.append("NEXT STEPS")
    lines.append("=" * 70)
    lines.append(f"  1. Spot-check ~10 Tier 1 high-confidence matches")
    lines.append(f"  2. Resolve remaining {unmatched} unmatched active files (API batch or manual)")
    lines.append(f"  3. Choose canonical PDF for {len(dupes)} duplicate pairs")
    lines.append(f"  4. Proceed to Step 4: rename_to_codon.py (dry-run first)")
    lines.append("")

    text = "\n".join(lines)
    output_path.write_text(text, encoding="utf-8")
    return text


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build match staging report for codon migration")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each match as it happens")
    args = parser.parse_args()

    # Validate paths
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        sys.exit(1)
    if not PDF_DIR.exists():
        print(f"ERROR: PDF directory not found: {PDF_DIR}")
        sys.exit(1)

    # Load crosswalk
    crosswalk_data = []
    if CROSSWALK.exists():
        with open(CROSSWALK, "r", encoding="utf-8") as f:
            crosswalk_data = json.load(f)
        print(f"Loaded crosswalk: {len(crosswalk_data)} entries")
    else:
        print("WARNING: crosswalk_index.json not found — Tier 1/2 matching unavailable")

    # Build crosswalk lookup: pdf_filename → crosswalk entry
    xwalk_by_pdf = {entry["pdf_filename"]: entry for entry in crosswalk_data}

    # Load manual overrides
    overrides = {}
    omit_list = set()
    duplicate_map = {}
    if OVERRIDES.exists():
        with open(OVERRIDES, "r", encoding="utf-8") as f:
            ovr = json.load(f)
        overrides = ovr.get("manual_matches", {})
        omit_list = set(ovr.get("omit_from_migration", []))
        duplicate_map = ovr.get("duplicates", {})
        print(f"Loaded overrides: {len(overrides)} manual matches, {len(omit_list)} omitted, {len(duplicate_map)} duplicate pairs")
    else:
        print("No manual_overrides.json found — running without overrides")

    # Connect to DB and build indexes
    conn = sqlite3.connect(str(DB_PATH))
    db_idx = build_db_indexes(conn)
    print(f"Loaded DB: {len(db_idx['all'])} articles, {len(db_idx['by_author_year'])} author+year keys")

    # Get all PDFs
    pdfs = sorted([f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")])
    print(f"Found {len(pdfs)} PDFs in library")
    print()

    # Match each PDF
    results = []
    for pdf in pdfs:
        # Check if omitted from migration
        if pdf in omit_list:
            result = {
                "pdf_filename": pdf,
                "article_id": None, "codon_filename": None,
                "match_tier": 0, "match_method": "omitted",
                "confidence": "n/a", "candidates": [], "notes": "Omitted from migration (supplementary/algorithm/non-ITE)",
                "db_title": "", "db_author1": "", "db_year": "", "db_tier": "", "db_citation_count": 0,
            }
            if pdf in duplicate_map:
                result["notes"] += f" | Duplicate of {duplicate_map[pdf]}"
            results.append(result)
            if args.verbose:
                print(f"  T0 [omit  ] {pdf[:50]:50s} → OMITTED")
            continue

        # Check for manual override
        if pdf in overrides:
            art_id = overrides[pdf]["article_id"]
            article = db_idx["by_id"].get(art_id)
            if article:
                result = {
                    "pdf_filename": pdf,
                    "article_id": None, "codon_filename": None,
                    "match_tier": 0, "match_method": "manual_override",
                    "confidence": "high", "candidates": [], "notes": overrides[pdf].get("reason", ""),
                    "db_title": "", "db_author1": "", "db_year": "", "db_tier": "", "db_citation_count": 0,
                }
                _fill_result(result, article, "manual_override")
                if pdf in duplicate_map:
                    result["notes"] += f" | DUPLICATE of {duplicate_map[pdf]}"
                    result["is_duplicate"] = True
                results.append(result)
                if args.verbose:
                    print(f"  MO [high  ] {pdf[:50]:50s} → {art_id}")
                continue

        xwalk_entry = xwalk_by_pdf.get(pdf)
        match = match_pdf_to_article(pdf, xwalk_entry, db_idx)
        match["pdf_filename"] = pdf
        results.append(match)

        if args.verbose:
            status = match["article_id"] or "UNMATCHED"
            print(f"  T{match['match_tier']} [{match['confidence']:6s}] {pdf[:50]:50s} → {status}")

    conn.close()

    # Write reports
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "match_staging_report.json"
    txt_path  = OUTPUT_DIR / "match_staging_report.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report: {json_path}")

    text_report = generate_text_report(results, txt_path)
    print(f"Text report: {txt_path}")

    # Print summary to console
    active    = [r for r in results if r["match_method"] != "omitted"]
    omitted   = [r for r in results if r["match_method"] == "omitted"]
    manual_c  = [r for r in results if r["match_method"] == "manual_override"]
    dupes_c   = [r for r in results if r.get("is_duplicate")]
    matched   = sum(1 for r in active if r["article_id"])
    unique_ids = len(set(r["article_id"] for r in active if r["article_id"]))
    unmatched = sum(1 for r in active if not r["article_id"])

    print(f"\n{'='*50}")
    print(f"  Total PDFs:        {len(results)}")
    print(f"  Omitted (non-ITE): {len(omitted)}")
    print(f"  Active:            {len(active)}")
    print(f"    Matched:         {matched} ({len(manual_c)} manual, {len(dupes_c)} duplicates)")
    print(f"    Unique articles: {unique_ids}")
    print(f"    Unmatched:       {unmatched}")
    art_ids = [r["article_id"] for r in active if r["article_id"]]
    dup_arts = {k: v for k, v in Counter(art_ids).items() if v > 1}
    if dup_arts:
        print(f"  ⚠ {len(dup_arts)} duplicate ART-ID assignments — review needed")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

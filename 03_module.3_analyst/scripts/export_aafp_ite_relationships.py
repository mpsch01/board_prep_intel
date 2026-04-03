#!/usr/bin/env python3
"""
Export AAFP↔ITE relationship reports.

Produces four CSVs:
1. AAFP questions linked to ITE by semantic similarity
2. AAFP questions with question-level citation overlap to ITE
3. Summary counts for citation overlap
4. Intersection of semantic similarity + citation overlap

Run from the repository root with:
  00_database/db/ite_intelligence.db
present on disk.
"""

import csv
import sqlite3
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────
DB_PATH = Path("00_database/db/ite_intelligence.db")
OUT_DIR = Path("00_database/readable_db_files")
OUT_DIR.mkdir(parents=True, exist_ok=True)

DIST_THRESHOLD = 0.30      # broader semantic similarity list
STRICT_THRESHOLD = 0.22    # high-confidence intersection list

# ── Queries ────────────────────────────────────────────────────────────
SEMANTIC_QUERY = """
SELECT
    aq.aafp_qid,
    aq.question_id,
    aq.assessment_id,
    aq.quiz_title,
    aq.question_number,
    aq.stem,
    aq.url,
    aq.ite_nearest_qid,
    aq.ite_nearest_dist,
    q.question_text AS ite_stem,
    q.exam_year     AS ite_exam_year,
    q.body_system   AS ite_body_system,
    COUNT(DISTINCT x.article_id) AS linked_articles
FROM aafp_questions aq
JOIN questions q
    ON q.qid = aq.ite_nearest_qid
JOIN aafp_qid_art_xref x
    ON x.aafp_qid = aq.aafp_qid
WHERE aq.ite_nearest_qid IS NOT NULL
  AND aq.ite_nearest_dist IS NOT NULL
  AND aq.ite_nearest_dist < ?
GROUP BY
    aq.aafp_qid,
    aq.question_id,
    aq.assessment_id,
    aq.quiz_title,
    aq.question_number,
    aq.stem,
    aq.url,
    aq.ite_nearest_qid,
    aq.ite_nearest_dist,
    q.question_text,
    q.exam_year,
    q.body_system
ORDER BY
    aq.ite_nearest_dist ASC,
    aq.aafp_qid;
"""

OVERLAP_QUERY = """
SELECT DISTINCT
    aq.aafp_qid,
    aq.question_id,
    aq.assessment_id,
    aq.quiz_title,
    aq.question_number,
    aq.stem,
    aq.url,
    ac.citation_id,
    ac.match_status,
    ac.article_id,
    a.clean_ref,
    qrp.qid AS ite_qid,
    q.exam_year AS ite_exam_year,
    q.body_system AS ite_body_system
FROM aafp_questions aq
JOIN aafp_citations ac
    ON ac.aafp_qid = aq.aafp_qid
JOIN articles a
    ON a.article_id = ac.article_id
JOIN question_ref_pairs qrp
    ON qrp.clean_ref = a.clean_ref
JOIN questions q
    ON q.qid = qrp.qid
WHERE ac.article_id IS NOT NULL
ORDER BY
    aq.aafp_qid,
    ac.citation_id,
    q.exam_year;
"""

SUMMARY_QUERY = """
SELECT
    aq.aafp_qid,
    aq.question_id,
    aq.assessment_id,
    aq.quiz_title,
    aq.question_number,
    COUNT(DISTINCT qrp.qid) AS ite_question_overlap_count,
    COUNT(DISTINCT ac.article_id) AS shared_article_count
FROM aafp_questions aq
JOIN aafp_citations ac
    ON ac.aafp_qid = aq.aafp_qid
JOIN articles a
    ON a.article_id = ac.article_id
JOIN question_ref_pairs qrp
    ON qrp.clean_ref = a.clean_ref
GROUP BY
    aq.aafp_qid,
    aq.question_id,
    aq.assessment_id,
    aq.quiz_title,
    aq.question_number
HAVING COUNT(DISTINCT qrp.qid) > 0
ORDER BY ite_question_overlap_count DESC, aq.aafp_qid;
"""

INTERSECTION_QUERY = """
WITH semantic AS (
    SELECT
        aq.aafp_qid,
        aq.question_id,
        aq.assessment_id,
        aq.quiz_title,
        aq.question_number,
        aq.stem,
        aq.url,
        aq.ite_nearest_qid,
        aq.ite_nearest_dist,
        q.question_text AS ite_stem,
        q.exam_year     AS ite_exam_year,
        q.body_system   AS ite_body_system,
        COUNT(DISTINCT x.article_id) AS linked_articles
    FROM aafp_questions aq
    JOIN questions q
        ON q.qid = aq.ite_nearest_qid
    JOIN aafp_qid_art_xref x
        ON x.aafp_qid = aq.aafp_qid
    WHERE aq.ite_nearest_qid IS NOT NULL
      AND aq.ite_nearest_dist IS NOT NULL
      AND aq.ite_nearest_dist < ?
    GROUP BY
        aq.aafp_qid,
        aq.question_id,
        aq.assessment_id,
        aq.quiz_title,
        aq.question_number,
        aq.stem,
        aq.url,
        aq.ite_nearest_qid,
        aq.ite_nearest_dist,
        q.question_text,
        q.exam_year,
        q.body_system
),
overlap AS (
    SELECT DISTINCT
        aq.aafp_qid
    FROM aafp_questions aq
    JOIN aafp_citations ac
        ON ac.aafp_qid = aq.aafp_qid
    JOIN articles a
        ON a.article_id = ac.article_id
    JOIN question_ref_pairs qrp
        ON qrp.clean_ref = a.clean_ref
)
SELECT s.*
FROM semantic s
JOIN overlap o
    ON o.aafp_qid = s.aafp_qid
ORDER BY s.ite_nearest_dist ASC, s.aafp_qid;
"""

# ── Helpers ────────────────────────────────────────────────────────────
def write_csv(path: Path, rows, header):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in rows:
            writer.writerow([r[h] for h in header])

# ── Main ──────────────────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    semantic_rows = conn.execute(SEMANTIC_QUERY, (DIST_THRESHOLD,)).fetchall()
    overlap_rows = conn.execute(OVERLAP_QUERY).fetchall()
    summary_rows = conn.execute(SUMMARY_QUERY).fetchall()
    intersection_rows = conn.execute(INTERSECTION_QUERY, (STRICT_THRESHOLD,)).fetchall()

    conn.close()

    semantic_path = OUT_DIR / "aafp_ite_semantic_similarity.csv"
    overlap_detail_path = OUT_DIR / "aafp_ite_question_level_citation_overlap_detail.csv"
    overlap_summary_path = OUT_DIR / "aafp_ite_question_level_citation_overlap_summary.csv"
    intersection_path = OUT_DIR / "aafp_ite_semantic_and_citation_intersection.csv"

    semantic_header = [
        "aafp_qid", "question_id", "assessment_id", "quiz_title",
        "question_number", "stem", "url",
        "ite_nearest_qid", "ite_nearest_dist",
        "ite_stem", "ite_exam_year", "ite_body_system",
        "linked_articles"
    ]

    overlap_detail_header = [
        "aafp_qid", "question_id", "assessment_id", "quiz_title",
        "question_number", "stem", "url",
        "citation_id", "match_status", "article_id", "clean_ref",
        "ite_qid", "ite_exam_year", "ite_body_system"
    ]

    overlap_summary_header = [
        "aafp_qid", "question_id", "assessment_id", "quiz_title",
        "question_number", "ite_question_overlap_count", "shared_article_count"
    ]

    write_csv(semantic_path, semantic_rows, semantic_header)
    write_csv(overlap_detail_path, overlap_rows, overlap_detail_header)
    write_csv(overlap_summary_path, summary_rows, overlap_summary_header)
    write_csv(intersection_path, intersection_rows, semantic_header)

    print(f"Wrote {len(semantic_rows)} rows to {semantic_path}")
    print(f"Wrote {len(overlap_rows)} rows to {overlap_detail_path}")
    print(f"Wrote {len(summary_rows)} rows to {overlap_summary_path}")
    print(f"Wrote {len(intersection_rows)} rows to {intersection_path}")

if __name__ == "__main__":
    main()
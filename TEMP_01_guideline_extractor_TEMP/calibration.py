"""
calibration.py
==============
Phase 2 calibration module for guideline_extractor_v2.

Analyzes extraction quality across unified_v1.0 documents, identifies
systematic gaps by engine type, and generates candidate prompt improvements
for low-performing areas.

WHAT IT DOES:
  1. Loads all unified_v1.0 JSONs from a target directory
  2. Scores each document on field quality (not just presence)
  3. Identifies systematic patterns by engine/document_type
  4. Generates a calibration report with specific gap findings
  5. Writes candidate improved prompts to prompts/candidates/
  6. Optionally runs A/B comparison on a sample document

QUALITY DIMENSIONS SCORED:
  - recommendations: strength populated, evidence_level populated, length of text
  - key_thresholds:  unit populated, context populated, value is specific (not vague)
  - medications:     dose populated, class populated
  - population:      all 5 sub-fields populated and non-trivial
  - summary:         length >= 2 sentences (>80 chars), clinical specificity

USAGE:
  # Full calibration report on migrated gold_list outputs
  python calibration.py

  # Point at a specific directory
  python calibration.py --source path/to/json/dir

  # Include A/B prompt test on one document (costs API calls)
  python calibration.py --ab-test path/to/document.pdf
"""

from __future__ import annotations
import argparse
import json
import os
import datetime
import sys
from collections import defaultdict

# Default paths

DEFAULT_SOURCE_DIR = (
    r"C:\Users\mpsch\Desktop\claude_knowledge\board_prep"
    r"\ite_refs\04_outputs\ingested\json"
)
DEFAULT_PROMPTS_DIR = os.path.join(
    os.path.dirname(__file__), "prompts"
)
DEFAULT_REPORT_DIR = os.path.join(
    os.path.dirname(__file__), "outputs", "calibration"
)


# Quality scoring

def _nonempty(val) -> bool:
    if val is None: return False
    if isinstance(val, str): return len(val.strip()) >= 1
    if isinstance(val, (list, dict)): return len(val) > 0
    return True

def _vague(text: str) -> bool:
    """Detect vague/placeholder text that passes presence checks but has no value."""
    vague_phrases = [
        "not specified", "not stated", "not provided", "n/a", "none mentioned",
        "not applicable", "unknown", "not mentioned", "not documented",
        "not available", "see document", "varies"
    ]
    return any(p in text.lower() for p in vague_phrases)


def score_recommendations(recs: list) -> dict:
    if not recs:
        return {"count": 0, "strength_rate": 0.0, "evidence_rate": 0.0, "avg_length": 0, "score": 0.0}

    has_strength  = sum(1 for r in recs if _nonempty(r.get("strength")))
    has_evidence  = sum(1 for r in recs if _nonempty(r.get("evidence_level")))
    avg_len       = sum(len(r.get("recommendation", "")) for r in recs) / len(recs)

    strength_rate = has_strength / len(recs)
    evidence_rate = has_evidence / len(recs)

    score = (0.4 * strength_rate) + (0.4 * evidence_rate) + (0.2 * min(avg_len / 100, 1.0))
    return {
        "count":         len(recs),
        "strength_rate": round(strength_rate, 3),
        "evidence_rate": round(evidence_rate, 3),
        "avg_length":    round(avg_len, 1),
        "score":         round(score, 3),
    }


def score_thresholds(thresholds: list) -> dict:
    if not thresholds:
        return {"count": 0, "unit_rate": 0.0, "context_rate": 0.0, "specific_rate": 0.0, "score": 0.0}

    has_unit    = sum(1 for t in thresholds if _nonempty(t.get("unit")))
    has_context = sum(1 for t in thresholds if _nonempty(t.get("context")))
    is_specific = sum(1 for t in thresholds if (
        _nonempty(t.get("value")) and not _vague(str(t.get("value", "")))
    ))

    unit_rate     = has_unit    / len(thresholds)
    context_rate  = has_context / len(thresholds)
    specific_rate = is_specific / len(thresholds)

    score = (0.3 * unit_rate) + (0.4 * context_rate) + (0.3 * specific_rate)
    return {
        "count":         len(thresholds),
        "unit_rate":     round(unit_rate,    3),
        "context_rate":  round(context_rate, 3),
        "specific_rate": round(specific_rate,3),
        "score":         round(score, 3),
    }


def score_medications(meds: list) -> dict:
    if not meds:
        return {"count": 0, "dose_rate": 0.0, "class_rate": 0.0, "score": 0.0}

    has_dose  = sum(1 for m in meds if _nonempty(m.get("dose")))
    has_class = sum(1 for m in meds if _nonempty(m.get("class")))

    dose_rate  = has_dose  / len(meds)
    class_rate = has_class / len(meds)

    score = (0.5 * dose_rate) + (0.5 * class_rate)
    return {
        "count":      len(meds),
        "dose_rate":  round(dose_rate,  3),
        "class_rate": round(class_rate, 3),
        "score":      round(score, 3),
    }


def score_population(pop: dict) -> dict:
    if not pop:
        return {"subfields_populated": 0, "vague_count": 0, "score": 0.0}

    subfields = ["age_criteria", "risk_criteria", "disease_definition", "exclusions", "severity_staging"]
    populated = sum(1 for f in subfields if _nonempty(pop.get(f)))
    vague     = sum(1 for f in subfields if (
        _nonempty(pop.get(f)) and _vague(str(pop.get(f, "")))
    ))

    score = (populated - vague) / len(subfields)
    return {
        "subfields_populated": populated,
        "vague_count":         vague,
        "score":               round(max(score, 0.0), 3),
    }


def score_summary(summary: str) -> dict:
    if not summary or not summary.strip():
        return {"length": 0, "sentences": 0, "score": 0.0}

    length    = len(summary)
    sentences = summary.count(".") + summary.count("!") + summary.count("?")
    is_vague  = _vague(summary)

    len_score      = min(length / 300, 1.0)
    sentence_score = min(sentences / 2, 1.0)
    vague_penalty  = 0.0 if is_vague else 1.0

    score = (0.4 * len_score) + (0.4 * sentence_score) + (0.2 * vague_penalty)
    return {
        "length":    length,
        "sentences": sentences,
        "score":     round(score, 3),
    }


def score_document(doc: dict) -> dict:
    ext = doc.get("extraction", {})
    src = doc.get("source", {})
    clf = doc.get("classification", {})

    rec_scores  = score_recommendations(ext.get("recommendations", []))
    thr_scores  = score_thresholds(ext.get("key_thresholds", []))
    med_scores  = score_medications(ext.get("medications", []))
    pop_scores  = score_population(ext.get("population", {}))
    sum_scores  = score_summary(ext.get("summary", ""))

    components = [
        ("recommendations", rec_scores["score"], 0.30),
        ("thresholds",      thr_scores["score"], 0.25),
        ("population",      pop_scores["score"], 0.20),
        ("summary",         sum_scores["score"], 0.15),
    ]
    if med_scores["count"] > 0:
        components.append(("medications", med_scores["score"], 0.10))
        total_weight = sum(w for _, _, w in components)
        components = [(n, s, w/total_weight) for n, s, w in components]

    overall = sum(score * weight for _, score, weight in components)

    return {
        "source_id":     src.get("source_id", ""),
        "title":         src.get("title", ""),
        "document_type": clf.get("document_type", "unknown"),
        "engine_used":   clf.get("engine_used", ""),
        "confidence":    clf.get("confidence", 0.0),
        "field_coverage_score": doc.get("metadata", {}).get("field_coverage_score", 0.0),
        "quality_scores": {
            "overall":         round(overall, 3),
            "recommendations": rec_scores,
            "thresholds":      thr_scores,
            "medications":     med_scores,
            "population":      pop_scores,
            "summary":         sum_scores,
        }
    }


# Gap analysis

def identify_gaps(scored_docs: list[dict]) -> dict:
    by_engine = defaultdict(list)
    for d in scored_docs:
        by_engine[d["engine_used"]].append(d)

    gaps = {}
    for engine, docs in by_engine.items():
        if not docs:
            continue

        n = len(docs)
        avg = lambda field: sum(d["quality_scores"][field]["score"] for d in docs) / n

        avg_rec   = avg("recommendations")
        avg_thr   = avg("thresholds")
        avg_pop   = avg("population")
        avg_sum   = avg("summary")

        med_docs  = [d for d in docs if d["quality_scores"]["medications"]["count"] > 0]
        avg_med   = (sum(d["quality_scores"]["medications"]["score"] for d in med_docs) / len(med_docs)
                     if med_docs else None)

        avg_strength = sum(d["quality_scores"]["recommendations"]["strength_rate"] for d in docs) / n
        avg_evidence = sum(d["quality_scores"]["recommendations"]["evidence_rate"]  for d in docs) / n
        avg_unit     = sum(d["quality_scores"]["thresholds"]["unit_rate"]           for d in docs) / n
        avg_context  = sum(d["quality_scores"]["thresholds"]["context_rate"]        for d in docs) / n
        avg_pop_vague = sum(d["quality_scores"]["population"]["vague_count"] for d in docs) / n
        avg_dose  = (sum(d["quality_scores"]["medications"]["dose_rate"]  for d in med_docs) / len(med_docs)
                     if med_docs else None)
        avg_class = (sum(d["quality_scores"]["medications"]["class_rate"] for d in med_docs) / len(med_docs)
                     if med_docs else None)

        findings = []

        if avg_rec < 0.70:
            findings.append({
                "field": "recommendations",
                "issue": f"avg quality score {avg_rec:.2f} -- below 0.70 target",
                "sub_issues": [
                    f"strength populated in only {avg_strength:.0%} of recs" if avg_strength < 0.80 else None,
                    f"evidence_level populated in only {avg_evidence:.0%} of recs" if avg_evidence < 0.80 else None,
                ],
                "priority": "HIGH" if avg_rec < 0.50 else "MEDIUM"
            })
        if avg_thr < 0.70:
            findings.append({
                "field": "key_thresholds",
                "issue": f"avg quality score {avg_thr:.2f} -- below 0.70 target",
                "sub_issues": [
                    f"unit missing in {1-avg_unit:.0%} of thresholds" if avg_unit < 0.80 else None,
                    f"context missing in {1-avg_context:.0%} of thresholds" if avg_context < 0.80 else None,
                ],
                "priority": "HIGH" if avg_thr < 0.50 else "MEDIUM"
            })
        if avg_pop < 0.70:
            findings.append({
                "field": "population",
                "issue": f"avg quality score {avg_pop:.2f} -- vague placeholder text detected",
                "sub_issues": [f"avg {avg_pop_vague:.1f} vague sub-fields per document"],
                "priority": "MEDIUM"
            })
        if avg_sum < 0.70:
            findings.append({
                "field": "summary",
                "issue": f"avg quality score {avg_sum:.2f} -- summaries may be too short or vague",
                "sub_issues": [],
                "priority": "MEDIUM"
            })
        if avg_med is not None and avg_med < 0.70:
            findings.append({
                "field": "medications",
                "issue": f"avg quality score {avg_med:.2f} (for docs with medications)",
                "sub_issues": [
                    f"dose missing in {1-avg_dose:.0%} of medications" if avg_dose is not None and avg_dose < 0.80 else None,
                    f"class missing in {1-avg_class:.0%} of medications" if avg_class is not None and avg_class < 0.80 else None,
                ],
                "priority": "MEDIUM"
            })

        for f in findings:
            f["sub_issues"] = [s for s in f["sub_issues"] if s is not None]

        gaps[engine] = {
            "document_count": n,
            "avg_scores": {
                "recommendations": round(avg_rec, 3),
                "thresholds":      round(avg_thr, 3),
                "population":      round(avg_pop, 3),
                "summary":         round(avg_sum, 3),
                "medications":     round(avg_med, 3) if avg_med is not None else "N/A (no med docs)",
            },
            "sub_metrics": {
                "rec_strength_rate":  round(avg_strength, 3),
                "rec_evidence_rate":  round(avg_evidence, 3),
                "thr_unit_rate":      round(avg_unit, 3),
                "thr_context_rate":   round(avg_context, 3),
                "pop_avg_vague":      round(avg_pop_vague, 2),
                "med_dose_rate":      round(avg_dose, 3) if avg_dose is not None else "N/A",
                "med_class_rate":     round(avg_class, 3) if avg_class is not None else "N/A",
            },
            "findings": findings,
            "needs_prompt_update": len(findings) > 0,
        }

    return gaps


# Prompt candidate generation

PROMPT_IMPROVEMENT_TEMPLATES = {
    "recommendations_strength": """
IMPORTANT: For EVERY recommendation, you MUST populate the 'strength' field.
Use the guideline's own grading system if present (e.g., "Strong", "Conditional", "Weak",
"Class I", "Class IIa", "Class IIb", "Class III", "Grade A", "Grade B", "Grade C").
If no explicit grade is given, infer from language:
  - "should", "recommend", "is indicated" -> "Strong"
  - "may", "consider", "is reasonable" -> "Conditional"
  - "insufficient evidence" -> "Insufficient Evidence"
Never leave strength as an empty string.
""",
    "recommendations_evidence": """
IMPORTANT: For EVERY recommendation, you MUST populate the 'evidence_level' field.
Use the guideline's own evidence coding (e.g., "A", "B", "C", "B-R", "B-NR", "C-EO",
"Level 1", "Level 2", "Level 3", "Expert Opinion").
If no code is explicitly stated, use:
  - RCT-supported -> "A"
  - Observational/cohort data -> "B"
  - Expert consensus/guideline panel -> "C"
  - Single case series -> "C"
Never leave evidence_level as an empty string.
""",
    "thresholds_units": """
IMPORTANT: For EVERY threshold entry, you MUST populate the 'unit' field.
Units should follow standard clinical notation:
  - Blood pressure: mmHg
  - Lab values: mg/dL, mmol/L, mEq/L, g/dL, IU/L, etc.
  - Weight: kg, lbs
  - Time: days, weeks, months, years
  - Scores/indices: "points", "score", or leave blank only if truly dimensionless
  - Percentages: "%"
Never leave unit blank if a numeric threshold is given.
""",
    "thresholds_context": """
IMPORTANT: For EVERY threshold entry, the 'context' field must clearly state
WHEN or WHY this threshold applies. Examples of good context:
  - "Indicates hypertension stage 2 in adults >=18"
  - "Threshold for initiating antibiotic therapy"
  - "Cutoff for referral to nephrology"
  - "Upper limit of normal; above this indicates cholestasis"
Bad context (too vague): "treatment", "diagnosis", "management"
Never use single-word context. Always write a clinical sentence fragment.
""",
    "medications_dose": """
IMPORTANT: For EVERY medication entry, populate the 'dose' field with the specific
dosing information from the document. Include:
  - Dose amount and unit (e.g., "500 mg", "0.5 mg/kg")
  - Frequency if stated (e.g., "twice daily", "every 8 hours")
  - Route if stated (e.g., "oral", "IV", "topical")
  - Weight-based dosing for pediatric medications
If the document states a dose range, capture the full range: "5-10 mg/day".
If no dose is stated, write "dose not specified" rather than leaving blank.
""",
    "medications_class": """
IMPORTANT: For EVERY medication entry, populate the 'class' field using standard
pharmacological classification:
  - ACE inhibitor, ARB, calcium channel blocker, thiazide diuretic
  - Fluoroquinolone, macrolide, beta-lactam, aminoglycoside
  - SSRI, SNRI, TCA, atypical antipsychotic
  - Inhaled corticosteroid, LABA, SABA, LAMA
  - Biologic (specify: TNF inhibitor, IL-6 inhibitor, etc.)
Never leave class as an empty string if the drug is a known pharmaceutical agent.
""",
}

def generate_prompt_candidates(gaps: dict, prompts_dir: str) -> list[str]:
    candidates_dir = os.path.join(prompts_dir, "candidates")
    os.makedirs(candidates_dir, exist_ok=True)

    written = []
    for engine, gap_data in gaps.items():
        if not gap_data["needs_prompt_update"]:
            continue

        improvements = []
        for finding in gap_data["findings"]:
            field = finding["field"]
            if field == "recommendations":
                sm = gap_data["sub_metrics"]
                if sm["rec_strength_rate"] < 0.80:
                    improvements.append(PROMPT_IMPROVEMENT_TEMPLATES["recommendations_strength"])
                if sm["rec_evidence_rate"] < 0.80:
                    improvements.append(PROMPT_IMPROVEMENT_TEMPLATES["recommendations_evidence"])
            elif field == "key_thresholds":
                sm = gap_data["sub_metrics"]
                if sm["thr_unit_rate"] < 0.80:
                    improvements.append(PROMPT_IMPROVEMENT_TEMPLATES["thresholds_units"])
                if sm["thr_context_rate"] < 0.80:
                    improvements.append(PROMPT_IMPROVEMENT_TEMPLATES["thresholds_context"])
            elif field == "medications":
                sm = gap_data["sub_metrics"]
                if sm["med_dose_rate"] != "N/A" and sm["med_dose_rate"] < 0.80:
                    improvements.append(PROMPT_IMPROVEMENT_TEMPLATES["medications_dose"])
                if sm["med_class_rate"] != "N/A" and sm["med_class_rate"] < 0.80:
                    improvements.append(PROMPT_IMPROVEMENT_TEMPLATES["medications_class"])

        if not improvements:
            continue

        improvement_block = "\n\n--- QUALITY IMPROVEMENTS (added by calibration) ---\n"
        improvement_block += "\n".join(imp.strip() for imp in improvements)
        improvement_block += "\n--- END IMPROVEMENTS ---\n"

        engine_slug = engine.lower().replace("engine", "").replace("  ", "_").strip("_")
        out_path = os.path.join(candidates_dir, f"{engine_slug}_candidate_v1.txt")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# Prompt candidate for: {engine}\n")
            f.write(f"# Generated: {datetime.datetime.utcnow().isoformat()}Z\n")
            f.write(f"# Gaps addressed: {[g['field'] for g in gap_data['findings']]}\n\n")
            f.write("PASTE THIS BLOCK INTO THE SYSTEM PROMPT AFTER THE EXISTING INSTRUCTIONS:\n\n")
            f.write(improvement_block)

        written.append(out_path)
        print(f"  [candidate] {out_path}")

    return written


# Main calibration logic

def run_calibration(source_dir: str, prompts_dir: str, report_dir: str):

    print(f"\n{'='*65}")
    print(f"  calibration.py  |  guideline_extractor_v2")
    print(f"{'='*65}")
    print(f"  Source:   {source_dir}")
    print(f"  Prompts:  {prompts_dir}")
    print(f"  Reports:  {report_dir}")
    print(f"{'='*65}\n")

    if not os.path.isdir(source_dir):
        print(f"[ERROR] Source directory not found: {source_dir}")
        sys.exit(1)

    json_files = [f for f in os.listdir(source_dir) if f.endswith(".json")]
    print(f"  Loading {len(json_files)} documents...\n")

    docs = []
    for fname in json_files:
        fpath = os.path.join(source_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
            schema_ver = doc.get("metadata", {}).get("schema_version", "")
            if "unified" not in schema_ver:
                print(f"  [skip] {fname} -- schema_version={schema_ver!r}")
                continue
            docs.append(doc)
        except Exception as e:
            print(f"  [ERROR] {fname}: {e}")

    print(f"  Loaded {len(docs)} unified_v1.0 documents\n")

    print("  Scoring documents...")
    scored = [score_document(d) for d in docs]

    print(f"\n  {'Title':<50} {'Engine':<22} {'Overall':>7} {'Recs':>5} {'Thr':>5} {'Pop':>5} {'Sum':>5}")
    print(f"  {'-'*50} {'-'*22} {'-'*7} {'-'*5} {'-'*5} {'-'*5} {'-'*5}")
    for s in sorted(scored, key=lambda x: x["quality_scores"]["overall"]):
        title   = s["title"][:48]
        engine  = s["engine_used"][:20]
        qs      = s["quality_scores"]
        print(
            f"  {title:<50} {engine:<22}"
            f"  {qs['overall']:>5.2f}"
            f"  {qs['recommendations']['score']:>5.2f}"
            f"  {qs['thresholds']['score']:>5.2f}"
            f"  {qs['population']['score']:>5.2f}"
            f"  {qs['summary']['score']:>5.2f}"
        )

    n = len(scored)
    avg_overall = sum(s["quality_scores"]["overall"] for s in scored) / n
    avg_recs    = sum(s["quality_scores"]["recommendations"]["score"] for s in scored) / n
    avg_thr     = sum(s["quality_scores"]["thresholds"]["score"] for s in scored) / n
    avg_pop     = sum(s["quality_scores"]["population"]["score"] for s in scored) / n
    avg_sum     = sum(s["quality_scores"]["summary"]["score"] for s in scored) / n

    avg_strength = sum(s["quality_scores"]["recommendations"]["strength_rate"] for s in scored) / n
    avg_evidence = sum(s["quality_scores"]["recommendations"]["evidence_rate"]  for s in scored) / n
    avg_unit     = sum(s["quality_scores"]["thresholds"]["unit_rate"]           for s in scored) / n
    avg_context  = sum(s["quality_scores"]["thresholds"]["context_rate"]        for s in scored) / n

    print(f"\n  {'--'*37}")
    print(f"  OVERALL AVERAGES  (n={n})")
    print(f"  Overall quality: {avg_overall:.3f}")
    print(f"  Recommendations: {avg_recs:.3f}  (strength={avg_strength:.0%}, evidence={avg_evidence:.0%})")
    print(f"  Thresholds:      {avg_thr:.3f}  (unit={avg_unit:.0%}, context={avg_context:.0%})")
    print(f"  Population:      {avg_pop:.3f}")
    print(f"  Summary:         {avg_sum:.3f}")
    print(f"  {'--'*37}\n")

    print("  Running gap analysis by engine...\n")
    gaps = identify_gaps(scored)

    any_gaps = any(v["needs_prompt_update"] for v in gaps.values())

    for engine, gap_data in gaps.items():
        status = "GAPS FOUND" if gap_data["needs_prompt_update"] else "within targets"
        print(f"  [{engine}]  n={gap_data['document_count']}  {status}")
        for finding in gap_data["findings"]:
            print(f"    {finding['priority']:6} | {finding['field']}: {finding['issue']}")
            for sub in finding["sub_issues"]:
                print(f"           -> {sub}")

    print()
    if any_gaps:
        print("  Generating prompt candidates for engines with gaps...\n")
        written = generate_prompt_candidates(gaps, prompts_dir)
        if written:
            print(f"\n  {len(written)} candidate prompt(s) written.")
        else:
            print("  No new candidate prompts generated (gaps below improvement threshold).")
    else:
        print("  All engines within quality targets -- no prompt updates needed.")
        written = []

    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(report_dir, f"calibration_report_{timestamp}.json")

    report = {
        "calibration_timestamp":     datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "source_dir":                source_dir,
        "documents_analyzed":        n,
        "overall_averages": {
            "quality_score":    round(avg_overall, 3),
            "recommendations":  round(avg_recs,    3),
            "thresholds":       round(avg_thr,     3),
            "population":       round(avg_pop,     3),
            "summary":          round(avg_sum,     3),
        },
        "sub_metrics": {
            "rec_strength_rate": round(avg_strength, 3),
            "rec_evidence_rate": round(avg_evidence, 3),
            "thr_unit_rate":     round(avg_unit,     3),
            "thr_context_rate":  round(avg_context,  3),
        },
        "gaps_by_engine":              gaps,
        "prompt_candidates_written":   written,
        "per_document":                scored,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n  Calibration report: {report_path}\n")
    print(f"{'='*65}")
    print(f"  CALIBRATION COMPLETE  |  overall quality: {avg_overall:.3f}")
    print(f"{'='*65}\n")

    return report


# CLI

def main():
    parser = argparse.ArgumentParser(
        description="Calibration module for guideline_extractor_v2 -- quality scoring and prompt improvement"
    )
    parser.add_argument(
        "--source", default=DEFAULT_SOURCE_DIR,
        help="Directory containing unified_v1.0 JSON files to analyze"
    )
    parser.add_argument(
        "--prompts", default=DEFAULT_PROMPTS_DIR,
        help="Prompt templates directory (for writing candidates)"
    )
    parser.add_argument(
        "--reports", default=DEFAULT_REPORT_DIR,
        help="Directory to write calibration reports"
    )
    args = parser.parse_args()
    run_calibration(args.source, args.prompts, args.reports)


if __name__ == "__main__":
    main()

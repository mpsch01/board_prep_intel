"""
calibrate.py — Portable extraction quality scorer with persistent self-improvement.

Three responsibilities:
  1. SCORE   — Evaluate extraction quality on 5 weighted dimensions
  2. PERSIST — Append results to calibration_history.json (trend database)
  3. IMPROVE — Detect chronic gaps across runs, auto-generate prompt_supplements.json

USAGE:
  python calibrate.py <file.json>           # Score single extraction
  python calibrate.py <folder>              # Score all JSONs in folder
  python calibrate.py <file.json> --report  # Write calibration_report.txt next to input

Scoring algorithm matches calibration.py verbatim (5 dimensions, same weights).
No imports from the project — completely standalone within oneclick/.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import datetime
from collections import defaultdict


# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(SCRIPT_DIR, "calibration_history.json")
SUPPLEMENTS_PATH = os.path.join(SCRIPT_DIR, "prompt_supplements.json")

PASS_THRESHOLD = 0.70
GAP_THRESHOLD = 0.70
SUB_METRIC_THRESHOLD = 0.80
CHRONIC_MIN_OCCURRENCES = 3
CHRONIC_LOOKBACK = 5


# ── Quality Scoring (verbatim from calibration.py) ──────────────────────

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

    has_strength = sum(1 for r in recs if _nonempty(r.get("strength")))
    has_evidence = sum(1 for r in recs if _nonempty(r.get("evidence_level")))
    avg_len      = sum(len(r.get("recommendation", "")) for r in recs) / len(recs)

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
        "unit_rate":     round(unit_rate,     3),
        "context_rate":  round(context_rate,  3),
        "specific_rate": round(specific_rate, 3),
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

    rec_scores = score_recommendations(ext.get("recommendations", []))
    thr_scores = score_thresholds(ext.get("key_thresholds", []))
    med_scores = score_medications(ext.get("medications", []))
    pop_scores = score_population(ext.get("population", {}))
    sum_scores = score_summary(ext.get("summary", ""))

    components = [
        ("recommendations", rec_scores["score"], 0.30),
        ("thresholds",      thr_scores["score"], 0.25),
        ("population",      pop_scores["score"], 0.20),
        ("summary",         sum_scores["score"], 0.15),
    ]
    if med_scores["count"] > 0:
        components.append(("medications", med_scores["score"], 0.10))
        total_weight = sum(w for _, _, w in components)
        components = [(n, s, w / total_weight) for n, s, w in components]

    overall = sum(s * w for _, s, w in components)

    return {
        "title":         src.get("title", ""),
        "document_type": clf.get("document_type", "unknown"),
        "engine_used":   clf.get("engine_used", ""),
        "quality_scores": {
            "overall":         round(overall, 3),
            "recommendations": rec_scores,
            "thresholds":      thr_scores,
            "medications":     med_scores,
            "population":      pop_scores,
            "summary":         sum_scores,
        }
    }


# ── Gap Detection ────────────────────────────────────────────────────────

def identify_gaps(scored: dict) -> list:
    """Identify gaps from a single scored document result."""
    qs = scored["quality_scores"]
    gaps = []

    dims = {
        "recommendations": {
            "score": qs["recommendations"]["score"],
            "sub_metrics": {
                "strength_rate": qs["recommendations"].get("strength_rate", 0),
                "evidence_rate": qs["recommendations"].get("evidence_rate", 0),
            }
        },
        "thresholds": {
            "score": qs["thresholds"]["score"],
            "sub_metrics": {
                "unit_rate":     qs["thresholds"].get("unit_rate", 0),
                "context_rate":  qs["thresholds"].get("context_rate", 0),
                "specific_rate": qs["thresholds"].get("specific_rate", 0),
            }
        },
        "population": {
            "score": qs["population"]["score"],
            "sub_metrics": {
                "vague_count": qs["population"].get("vague_count", 0),
            }
        },
        "summary": {
            "score": qs["summary"]["score"],
            "sub_metrics": {}
        },
    }
    if qs["medications"]["count"] > 0:
        dims["medications"] = {
            "score": qs["medications"]["score"],
            "sub_metrics": {
                "dose_rate":  qs["medications"].get("dose_rate", 0),
                "class_rate": qs["medications"].get("class_rate", 0),
            }
        }

    for dim_name, dim_data in dims.items():
        if dim_data["score"] < GAP_THRESHOLD:
            priority = "HIGH" if dim_data["score"] < 0.50 else "MEDIUM"
            sub_issues = []
            for sm_name, sm_val in dim_data["sub_metrics"].items():
                if sm_name == "vague_count":
                    if sm_val > 0:
                        sub_issues.append(f"{sm_val} vague sub-fields")
                elif sm_val < SUB_METRIC_THRESHOLD:
                    sub_issues.append(f"{sm_name}={sm_val:.0%}")
            gaps.append({
                "dimension":  dim_name,
                "score":      dim_data["score"],
                "priority":   priority,
                "sub_issues": sub_issues,
            })

    return gaps


# ── Persistence Layer ────────────────────────────────────────────────────

def load_history() -> dict:
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": [], "run_count": 0, "total_files_scored": 0}


def save_history(history: dict):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def append_run(history: dict, scored_list: list, gaps_list: list, mode: str) -> dict:
    """Append a calibration run to history."""
    n = len(scored_list)
    if n == 0:
        return history

    dim_names = ["recommendations", "thresholds", "population", "summary", "medications"]
    dim_avgs = {}
    for dim in dim_names:
        scores = [s["quality_scores"][dim]["score"] for s in scored_list]
        dim_avgs[dim] = round(sum(scores) / len(scores), 3)

    overall_avg = sum(s["quality_scores"]["overall"] for s in scored_list) / n

    # engine breakdown
    by_engine = defaultdict(list)
    for s in scored_list:
        by_engine[s["engine_used"]].append(s["quality_scores"]["overall"])
    engine_breakdown = {
        eng: {"count": len(scores), "avg_score": round(sum(scores) / len(scores), 3)}
        for eng, scores in by_engine.items()
    }

    # flatten gaps for storage — use standardized sub_metric keys
    flat_gaps = []
    for gap_set in gaps_list:
        for gap in gap_set:
            # Extract sub_metric keys from sub_issues text
            sub_metrics = []
            for si in gap["sub_issues"]:
                # Parse "strength_rate=45%" or "2 vague sub-fields" patterns
                if "=" in si:
                    sub_metrics.append(si.split("=")[0].strip())
                elif "vague" in si:
                    sub_metrics.append("vague_fields")
                else:
                    sub_metrics.append("overall")
            if not sub_metrics:
                sub_metrics = ["overall"]
            for sm in sub_metrics:
                flat_gaps.append({
                    "dimension":  gap["dimension"],
                    "sub_metric": sm,
                    "score":      gap["score"],
                    "priority":   gap["priority"],
                })

    run_entry = {
        "timestamp":        datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "mode":             mode,
        "files_scored":     n,
        "overall_score":    round(overall_avg, 3),
        "dimension_scores": dim_avgs,
        "gaps":             flat_gaps,
        "engine_breakdown": engine_breakdown,
    }

    history["runs"].append(run_entry)
    history["run_count"] = len(history["runs"])
    history["total_files_scored"] = history.get("total_files_scored", 0) + n
    return history


# ── Trend Detection ──────────────────────────────────────────────────────

def detect_chronic_gaps(history: dict) -> list:
    """Analyze last N runs for recurring gap patterns."""
    recent = history["runs"][-CHRONIC_LOOKBACK:]
    if len(recent) < CHRONIC_MIN_OCCURRENCES:
        return []

    gap_scores = defaultdict(list)
    for run in recent:
        for gap in run.get("gaps", []):
            key = f"{gap['dimension']}.{gap['sub_metric']}"
            gap_scores[key].append(gap["score"])

    chronic = []
    for key, scores in gap_scores.items():
        if len(scores) >= CHRONIC_MIN_OCCURRENCES:
            parts = key.split(".", 1)
            trend = "improving" if scores[-1] > scores[0] else ("stable" if scores[-1] == scores[0] else "declining")
            chronic.append({
                "dimension":   parts[0],
                "sub_metric":  parts[1] if len(parts) > 1 else "overall",
                "occurrences": len(scores),
                "avg_score":   round(sum(scores) / len(scores), 3),
                "trend":       trend,
            })
    return chronic


# ── Prompt Supplement Generation ─────────────────────────────────────────

PROMPT_IMPROVEMENT_TEMPLATES = {
    "recommendations.strength_rate": (
        "IMPORTANT: For EVERY recommendation, you MUST populate the 'strength' field. "
        "Use the guideline's own grading system if present (e.g., Strong, Conditional, Weak, "
        "Class I/IIa/IIb/III, Grade A/B/C). If no explicit grade is given, infer from language: "
        "'should/recommend/is indicated' -> Strong; 'may/consider/is reasonable' -> Conditional."
    ),
    "recommendations.evidence_rate": (
        "IMPORTANT: For EVERY recommendation, you MUST populate the 'evidence_level' field. "
        "Use the guideline's own evidence coding (A, B, C, B-R, B-NR, C-EO, Level 1/2/3). "
        "If no code is stated: RCT-supported -> A; observational data -> B; expert consensus -> C."
    ),
    "thresholds.unit_rate": (
        "IMPORTANT: For EVERY threshold entry, you MUST populate the 'unit' field. "
        "Use standard clinical notation: mmHg, mg/dL, mmol/L, mEq/L, %, points, etc. "
        "Never leave unit blank if a numeric threshold is given."
    ),
    "thresholds.context_rate": (
        "IMPORTANT: For EVERY threshold entry, the 'context' field must clearly state "
        "WHEN or WHY this threshold applies. Write a clinical sentence fragment, not a single word."
    ),
    "medications.dose_rate": (
        "IMPORTANT: For EVERY medication entry, populate the 'dose' field with specific "
        "dosing information: amount + unit + frequency + route if stated. "
        "If no dose is stated, write 'dose not specified' rather than leaving blank."
    ),
    "medications.class_rate": (
        "IMPORTANT: For EVERY medication entry, populate the 'class' field using standard "
        "pharmacological classification (ACE inhibitor, ARB, SSRI, LABA, etc.)."
    ),
    "population.vague_fields": (
        "IMPORTANT: For target_population fields (age_criteria, risk_criteria, disease_definition, "
        "exclusions, severity_staging), provide SPECIFIC clinical values. Instead of 'adults', write "
        "'adults aged 40-75'. Instead of 'not specified', extract the actual criteria from the document."
    ),
    "summary.overall": (
        "IMPORTANT: The clinical summary must be at least 2-3 sentences and clinically specific. "
        "Include the condition being addressed, the key recommendation or finding, and any notable "
        "thresholds or population details. Avoid vague placeholder language."
    ),
}


def generate_supplements(chronic_gaps: list, history: dict) -> dict:
    """Generate prompt_supplements.json from chronic gap patterns."""
    supplements = []
    for gap in chronic_gaps:
        key = f"{gap['dimension']}.{gap['sub_metric']}"
        template = PROMPT_IMPROVEMENT_TEMPLATES.get(key)
        if not template:
            continue

        # determine which engines are affected
        recent = history["runs"][-CHRONIC_LOOKBACK:]
        affected_engines = set()
        for run in recent:
            for g in run.get("gaps", []):
                if g["dimension"] == gap["dimension"]:
                    for eng in run.get("engine_breakdown", {}).keys():
                        affected_engines.add(eng)

        supplements.append({
            "target_engines": list(affected_engines) if affected_engines else ["all"],
            "dimension":      gap["dimension"],
            "sub_metric":     gap["sub_metric"],
            "instruction":    template,
            "occurrences":    gap["occurrences"],
            "avg_score":      gap["avg_score"],
            "trend":          gap["trend"],
        })

    return {
        "generated_at":  datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "based_on_runs": len(history["runs"]),
        "supplements":   supplements,
    }


def save_supplements(data: dict):
    with open(SUPPLEMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Console Display ──────────────────────────────────────────────────────

def bar(score: float, width: int = 10) -> str:
    filled = int(score * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def print_report(scored_list: list, gaps_list: list, history: dict, chronic: list):
    n = len(scored_list)
    total_scored = history.get("total_files_scored", n)
    run_num = history.get("run_count", 1)

    # Aggregate scores
    dim_names = ["recommendations", "thresholds", "population", "summary"]
    has_meds = any(s["quality_scores"]["medications"]["count"] > 0 for s in scored_list)
    if has_meds:
        dim_names.append("medications")

    dim_avgs = {}
    for dim in dim_names:
        scores = [s["quality_scores"][dim]["score"] for s in scored_list]
        dim_avgs[dim] = sum(scores) / len(scores)

    overall = sum(s["quality_scores"]["overall"] for s in scored_list) / n
    verdict = "PASS" if overall >= PASS_THRESHOLD else "NEEDS TUNING"

    weights = {"recommendations": 30, "thresholds": 25, "population": 20, "summary": 15, "medications": 10}

    # Check for active supplements
    active_supplements = 0
    if os.path.exists(SUPPLEMENTS_PATH):
        with open(SUPPLEMENTS_PATH, "r", encoding="utf-8") as f:
            active_supplements = len(json.load(f).get("supplements", []))

    # Previous scores for trend arrows
    prev_scores = {}
    if len(history.get("runs", [])) >= 2:
        prev = history["runs"][-2]
        prev_scores = prev.get("dimension_scores", {})

    print()
    print("\u2554" + "\u2550" * 52 + "\u2557")
    print(f"\u2551  EXTRACTION QUALITY REPORT{' ' * 26}\u2551")
    print(f"\u2551  Run #{run_num} | {total_scored} files scored total{' ' * max(0, 20 - len(str(total_scored)))}\u2551")
    print("\u2560" + "\u2550" * 52 + "\u2563")

    for dim in dim_names:
        s = dim_avgs[dim]
        w = weights[dim]
        label = dim.capitalize()[:16]
        line = f"\u2551  {label:<16} {s:.2f}  {bar(s)}  {w}%"

        # trend arrow
        if dim in prev_scores:
            prev_s = prev_scores[dim]
            if s > prev_s + 0.05:
                line += f"  \u2191 was {prev_s:.2f}"
            elif s < prev_s - 0.05:
                line += f"  \u2193 was {prev_s:.2f}"

        line = line + " " * max(0, 52 - len(line) + 1) + "\u2551"
        print(line)

    print("\u2560" + "\u2550" * 52 + "\u2563")
    print(f"\u2551  OVERALL SCORE    {overall:.2f}{' ' * 32}\u2551")
    print(f"\u2551  VERDICT          {verdict}{' ' * max(0, 32 - len(verdict))}\u2551")

    if active_supplements > 0 or chronic:
        print("\u2560" + "\u2550" * 52 + "\u2563")
        if active_supplements:
            print(f"\u2551  Active supplements: {active_supplements}{' ' * max(0, 30 - len(str(active_supplements)))}\u2551")
        resolved = sum(1 for c in chronic if c["trend"] == "improving" and c["avg_score"] >= GAP_THRESHOLD)
        if resolved:
            print(f"\u2551  Chronic gaps resolved: {resolved}{' ' * max(0, 27 - len(str(resolved)))}\u2551")

    print("\u255a" + "\u2550" * 52 + "\u255d")

    # Print gaps
    all_gaps = [g for gap_set in gaps_list for g in gap_set]
    if all_gaps:
        print("\nGaps found:")
        for gap in all_gaps:
            detail = ", ".join(gap["sub_issues"]) if gap["sub_issues"] else f"score={gap['score']:.2f}"
            print(f"  [{gap['priority']}] {gap['dimension']}: {detail}")

    # Print chronic gaps
    if chronic:
        print("\nChronic patterns (recurring across runs):")
        for c in chronic:
            print(f"  [{c['trend'].upper()}] {c['dimension']}.{c['sub_metric']}: "
                  f"avg={c['avg_score']:.2f} ({c['occurrences']} occurrences)")

    print()


def write_report_file(scored_list: list, gaps_list: list, history: dict, output_path: str):
    """Write a text report file next to the input."""
    n = len(scored_list)
    overall = sum(s["quality_scores"]["overall"] for s in scored_list) / n
    verdict = "PASS" if overall >= PASS_THRESHOLD else "NEEDS TUNING"

    lines = [
        f"Calibration Report — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Files scored: {n}",
        f"Overall score: {overall:.3f} ({verdict})",
        f"Run #{history.get('run_count', 1)} | {history.get('total_files_scored', n)} total files in history",
        "",
        "Dimension Scores:",
    ]

    dim_names = ["recommendations", "thresholds", "population", "summary", "medications"]
    for dim in dim_names:
        scores = [s["quality_scores"][dim]["score"] for s in scored_list]
        avg = sum(scores) / len(scores) if scores else 0
        lines.append(f"  {dim:<20} {avg:.3f}")

    all_gaps = [g for gap_set in gaps_list for g in gap_set]
    if all_gaps:
        lines.append("")
        lines.append("Gaps:")
        for gap in all_gaps:
            detail = ", ".join(gap["sub_issues"]) if gap["sub_issues"] else f"score={gap['score']:.2f}"
            lines.append(f"  [{gap['priority']}] {gap['dimension']}: {detail}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Report written: {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extraction quality scorer with persistent self-improvement")
    parser.add_argument("input", help="JSON file or directory of JSON files to score")
    parser.add_argument("--report", action="store_true", help="Write calibration_report.txt next to input")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)

    # Load JSON files
    if os.path.isdir(input_path):
        json_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(".json")]
        mode = "batch"
    elif os.path.isfile(input_path) and input_path.endswith(".json"):
        json_files = [input_path]
        mode = "single"
    else:
        print(f"[ERROR] Not a JSON file or directory: {input_path}")
        sys.exit(1)

    if not json_files:
        print(f"[ERROR] No JSON files found in: {input_path}")
        sys.exit(1)

    docs = []
    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
            # Accept docs with unified schema_version OR with the standard top-level keys
            schema_ver = doc.get("metadata", {}).get("schema_version", "")
            has_structure = all(k in doc for k in ("extraction", "classification", "metadata"))
            if not ("unified" in schema_ver or has_structure):
                continue
            docs.append(doc)
        except Exception as e:
            print(f"  [WARN] {os.path.basename(fpath)}: {e}")

    if not docs:
        print("[ERROR] No valid unified_v1.0 documents found.")
        sys.exit(1)

    # Score
    scored_list = [score_document(d) for d in docs]
    gaps_list = [identify_gaps(s) for s in scored_list]

    # Persist
    history = load_history()
    history = append_run(history, scored_list, gaps_list, mode)
    save_history(history)

    # Detect chronic gaps
    chronic = detect_chronic_gaps(history)

    # Generate supplements if chronic gaps found
    if chronic:
        supp_data = generate_supplements(chronic, history)
        if supp_data["supplements"]:
            save_supplements(supp_data)

    # Display
    print_report(scored_list, gaps_list, history, chronic)

    # Optional report file
    if args.report:
        if os.path.isfile(input_path):
            report_path = input_path.replace(".json", "_calibration_report.txt")
        else:
            report_path = os.path.join(input_path, "calibration_report.txt")
        write_report_file(scored_list, gaps_list, history, report_path)


if __name__ == "__main__":
    main()

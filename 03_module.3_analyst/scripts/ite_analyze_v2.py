#!/usr/bin/env python3
"""
ITE Score Analysis Pipeline v2 — Enhanced Edition

Upgraded CLI that combines:
  - Stage 1: PDF parsing (identical to v1)
  - Stage 2: analyze_v2() with plugin architecture + PGY-level benchmarking
  - Stage 3: Both v2 JS report builder + v1 HTML interactive charts
  - Backward compatibility: --v1-only flag to revert to v1 pipeline

Usage:
    python ite_analyze_v2.py \
        --blueprint "221051_Item_Blueprint_Performance.pdf" \
        --bodysystem "221051_Item_BodySystem_Performance.pdf" \
        --db "../02_ite_intelligence/db/ite_intelligence.db" \
        --output-dir "./reports/sarkar_2025/" \
        --pgy-level 2 \
        --plugins all

With --v1-only for backward compatibility:
    python ite_analyze_v2.py \
        --blueprint "221051_Item_Blueprint_Performance.pdf" \
        --bodysystem "221051_Item_BodySystem_Performance.pdf" \
        --db "../02_ite_intelligence/db/ite_intelligence.db" \
        --output-dir "./reports/sarkar_2025/" \
        --v1-only

Produces:
    - score_analysis.json       (raw parsed + v2 analysis data)
    - ITE_{year}_Score_Analysis_{name}.html    (v1 interactive report, always built)
    - ITE_{year}_Score_Analysis_{name}.docx    (v2 full analysis + questions)
    - ITE_{year}_Practice_Questions_{name}.docx (v2 questions-only exam)
"""

import argparse
import sys
import json
import os
import subprocess
from pathlib import Path

# Allow running from any directory
pipeline_dir = Path(__file__).parent
sys.path.insert(0, str(pipeline_dir))
sys.path.insert(0, str(pipeline_dir / "v1"))

from ite_parser import load_config, parse_blueprint, parse_bodysystem, merge_results, export_json, parse_score_report

# Import v3 analyzer (default) and v2 (legacy --v2-only flag)
from ite_analyzer_v3 import analyze_v3, _normalize_body_system

# v2 analyzer (DEPRECATED — kept for --v2-only flag)
try:
    from ite_analyzer_v2 import analyze_v2
except ImportError:
    analyze_v2 = None

# v1 modules may not exist — safe fallbacks
try:
    from ite_analyzer import analyze, export_analysis
except ImportError:
    analyze = None
    def export_analysis(data: dict, path: str):
        import json
        with open(path, "w", encoding="utf-8") as _f:
            json.dump(data, _f, indent=2, default=str)

try:
    from ite_report_builder import build_html_report, build_full_docx, build_questions_docx
except ImportError:
    def build_html_report(analysis, path): raise RuntimeError("v1 report builder not found — use v3 path")
    def build_full_docx(analysis, path): raise RuntimeError("v1 report builder not found — use v3 path")
    def build_questions_docx(analysis, path): raise RuntimeError("v1 report builder not found — use v3 path")


def parse_plugins_arg(plugins_arg: str) -> list:
    """Parse --plugins argument. Returns list of plugin names."""
    if plugins_arg.lower() == "all":
        return ["concept", "icd10", "cohort", "explanations"]
    if not plugins_arg:
        return []
    return [p.strip() for p in plugins_arg.split(",")]


def find_prior_analyses(output_dir: Path, current_year: int) -> dict:
    """
    Look for n-1 and n-2 year analyses in the same outputs/ directory.

    Expected structure:
        ITE_lastname_firstname/
            inputs/   ← raw PDFs go here
            outputs/  ← output_dir; contains analysis_v2_{YYYY}.json per year

    Looks for: outputs/analysis_v2_{YYYY-1}.json and outputs/analysis_v2_{YYYY-2}.json

    Returns dict with keys 'n1' and 'n2', each a loaded analysis dict or None.
    """
    result = {}
    for offset, key in [(1, "n1"), (2, "n2")]:
        prior_year = current_year - offset
        prior_json = output_dir / f"analysis_v2_{prior_year}.json"
        if prior_json.exists():
            try:
                with open(prior_json, encoding="utf-8") as f:
                    result[key] = json.load(f)
                print(f"  [FOUND] {prior_json.name}")
            except Exception as e:
                print(f"  [WARN] Could not load {prior_json.name}: {e}")
                result[key] = None
        else:
            result[key] = None
            print(f"  [SKIP] No prior analysis: {prior_json.name} not found in outputs/")

    return result


def compute_longitudinal_delta(current: dict, prior: dict) -> dict:
    """
    Compute year-over-year performance delta between two analysis dicts.

    Prefers official scaled score (from --score-report) for the primary delta metric.
    Falls back to raw % when official scores aren't available in both years.

    Returns a delta dict containing:
        - scaled score delta (official when available, estimated otherwise)
        - PGY mean delta (how much above/below the class mean, year-over-year)
        - overall raw % change
        - per-blueprint and per-body-system rate deltas
        - weak area trajectory (closed / persistent / new)
        - data_quality flags (what data was available for comparison)
    """
    THRESHOLD = 0.70  # matches report_config.json default

    def safe_perf(a, key):
        return a.get("performance", {}).get(key, {}) or {}

    curr_overall = current.get("performance", {}).get("overall", {}) or {}
    prior_overall = prior.get("performance", {}).get("overall", {}) or {}

    # --- Scaled score delta (prefer official, fall back to estimated) ---
    curr_scaled_official  = curr_overall.get("scaled_score_actual")
    prior_scaled_official = prior_overall.get("scaled_score_actual")

    if curr_scaled_official is not None and prior_scaled_official is not None:
        curr_scaled  = curr_scaled_official
        prior_scaled = prior_scaled_official
        scaled_delta  = curr_scaled - prior_scaled
        scaled_source = "official"
    else:
        # Fall back to v3 analyzer estimated scaled score
        curr_scaled  = curr_overall.get("scaled_score")
        prior_scaled = prior_overall.get("scaled_score")
        if curr_scaled is not None and prior_scaled is not None:
            scaled_delta  = curr_scaled - prior_scaled
            scaled_source = "estimated"
        else:
            scaled_delta  = None
            scaled_source = None   # no score data in one or both years

    # --- PGY mean delta (how much above/below class mean, year over year) ---
    curr_vs_pgy  = curr_overall.get("vs_pgy_mean")
    prior_vs_pgy = prior_overall.get("vs_pgy_mean")
    vs_pgy_delta = None
    if curr_vs_pgy is not None and prior_vs_pgy is not None:
        vs_pgy_delta = curr_vs_pgy - prior_vs_pgy  # positive = improving relative to peers

    # --- Raw % delta (None-safe) ---
    curr_pct  = curr_overall.get("pct")
    prior_pct = prior_overall.get("pct")
    if curr_pct is not None and prior_pct is not None:
        pct_delta = round(curr_pct - prior_pct, 1)
    else:
        pct_delta = None  # one or both years missing raw pct

    # --- vs MPS delta ---
    curr_vs_mps  = curr_overall.get("vs_mps")
    prior_vs_mps = prior_overall.get("vs_mps")
    vs_mps_delta = None
    if curr_vs_mps is not None and prior_vs_mps is not None:
        vs_mps_delta = curr_vs_mps - prior_vs_mps

    # --- Blueprint delta (raw rates) ---
    curr_bp  = safe_perf(current, "blueprint")
    prior_bp = safe_perf(prior, "blueprint")
    blueprint_delta = {}
    for cat in set(list(curr_bp) + list(prior_bp)):
        c = curr_bp.get(cat, {}).get("rate")
        p = prior_bp.get(cat, {}).get("rate")
        if c is not None and p is not None:
            blueprint_delta[cat] = round((c - p) * 100, 1)

    # --- Blueprint scaled score delta (when official scores available in both years) ---
    curr_bp_scaled  = safe_perf(current, "blueprint_scaled")
    prior_bp_scaled = safe_perf(prior, "blueprint_scaled")
    blueprint_scaled_delta = {}
    for cat in set(list(curr_bp_scaled) + list(prior_bp_scaled)):
        c = curr_bp_scaled.get(cat, {}).get("scaled")
        p = prior_bp_scaled.get(cat, {}).get("scaled")
        if c is not None and p is not None:
            blueprint_scaled_delta[cat] = c - p

    # --- Body system delta (raw rates) ---
    curr_bs  = safe_perf(current, "body_system")
    prior_bs = safe_perf(prior, "body_system")
    body_system_delta = {}
    for sys in set(list(curr_bs) + list(prior_bs)):
        c = curr_bs.get(sys, {}).get("rate")
        p = prior_bs.get(sys, {}).get("rate")
        if c is not None and p is not None:
            body_system_delta[sys] = round((c - p) * 100, 1)

    # --- Concept clustering comparison (top concepts from prior year for YoY context) ---
    prior_cc = prior.get("concept_clustering", {}) or {}
    concept_delta = {
        "prior_top_diagnoses": list((prior_cc.get("top_diagnoses") or {}).keys())[:10],
        "prior_top_drugs":     list((prior_cc.get("top_drugs")     or {}).keys())[:10],
        "prior_top_guidelines":list((prior_cc.get("top_guidelines") or {}).keys())[:10],
    }

    # --- Weak area trajectory ---
    # Only include systems/categories present in BOTH years for trajectory analysis
    # (avoids flagging categories as "new gaps" just because body_system wasn't run in a prior year)
    curr_bp_weak  = {k for k, v in curr_bp.items()  if isinstance(v, dict) and v.get("rate", 1) < THRESHOLD}
    prior_bp_weak = {k for k, v in prior_bp.items() if isinstance(v, dict) and v.get("rate", 1) < THRESHOLD}
    curr_bs_weak  = {k for k, v in curr_bs.items()  if isinstance(v, dict) and v.get("rate", 1) < THRESHOLD}
    prior_bs_weak = {k for k, v in prior_bs.items() if isinstance(v, dict) and v.get("rate", 1) < THRESHOLD}

    # Body system trajectory only reported when both years have body system data
    if curr_bs and prior_bs:
        curr_weak  = curr_bp_weak  | curr_bs_weak
        prior_weak = prior_bp_weak | prior_bs_weak
        bs_both_years = True
    else:
        curr_weak  = curr_bp_weak
        prior_weak = prior_bp_weak
        bs_both_years = False

    # --- Data quality flags (for report builder to make display decisions) ---
    data_quality = {
        "official_score_both_years":   (curr_scaled_official is not None and prior_scaled_official is not None),
        "pct_available_both_years":    (curr_pct is not None and prior_pct is not None),
        "body_system_both_years":      bs_both_years,
        "vs_pgy_both_years":           (curr_vs_pgy is not None and prior_vs_pgy is not None),
        "blueprint_categories_common": sorted(blueprint_delta.keys()),
        "body_system_categories_common": sorted(body_system_delta.keys()),
    }

    return {
        "prior_year":           prior.get("exam_year"),
        # Primary metrics
        "scaled_delta":         scaled_delta,
        "scaled_source":        scaled_source,        # "official" | "estimated" | None
        "prior_scaled":         prior_scaled,
        "current_scaled":       curr_scaled,
        "vs_pgy_delta":         vs_pgy_delta,         # improving vs peers (+ = better)
        "prior_vs_pgy":         prior_vs_pgy,
        "current_vs_pgy":       curr_vs_pgy,
        "vs_mps_delta":         vs_mps_delta,
        # Raw % (None when not available in one or both years)
        "prior_overall_pct":    prior_pct,
        "current_overall_pct":  curr_pct,
        "overall_delta_pct":    pct_delta,
        # Category deltas
        "blueprint_delta":          blueprint_delta,
        "blueprint_scaled_delta":   blueprint_scaled_delta,
        "body_system_delta":        body_system_delta,
        # Weak area trajectory
        "weak_area_trajectory": {
            "closed":     sorted(prior_weak - curr_weak),   # was weak, now strong
            "persistent": sorted(prior_weak & curr_weak),   # still weak
            "new":        sorted(curr_weak - prior_weak),   # newly weak
        },
        # Data quality — helps report builder communicate uncertainty clearly
        "data_quality":         data_quality,
        # Concept YoY — top concepts from prior year for persistent/new classification
        "concept_delta":        concept_delta,
    }


def build_v2_reports(analysis: dict, output_dir: Path, analysis_json_path: str,
                     skip_reading_list: bool = False):
    """
    Build v2 reports via Node.js ite_report_builder_v2.js.

    Args:
        analysis: dict from analyze_v2()
        output_dir: Path object for output directory
        analysis_json_path: path to the saved analysis JSON (passed to Node.js)
    """
    # Build filename-safe resident name
    name = analysis.get("resident", {}).get("name", "Unknown")
    safe_name = name.split(",")[0].strip().replace(" ", "_").replace(".", "")
    year = analysis.get("exam_year", "2025")

    # Output paths for v2 reports
    docx_path = output_dir / f"ITE_{year}_Score_Analysis_{safe_name}.docx"
    questions_path = output_dir / f"ITE_{year}_Practice_Questions_{safe_name}.docx"

    # Call Node.js report builder
    report_builder_js = Path(__file__).parent / "ite_report_builder_v2.js"

    print(f"\nCalling Node.js report builder: {report_builder_js}")
    try:
        cmd = ["node", str(report_builder_js), str(analysis_json_path), str(output_dir)]
        env = {**os.environ, "SKIP_READING_LIST": "1"} if skip_reading_list else None
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)

        if result.returncode != 0:
            print(f"  WARNING: Node.js report builder exited with code {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr}")
        else:
            print(f"  [OK] Report builder completed successfully")
            if result.stdout:
                print(f"  {result.stdout}")
    except FileNotFoundError:
        print(f"  WARNING: Node.js not found or ite_report_builder_v2.js missing")
        print(f"  Skipping v2 DOCX generation (will still have HTML + JSON)")
    except subprocess.TimeoutExpired:
        print(f"  WARNING: Node.js report builder timed out (>120s)")
    except Exception as e:
        print(f"  WARNING: Failed to build v2 reports: {e}")

    return docx_path, questions_path


def main():
    parser = argparse.ArgumentParser(
        description="ITE Score Analysis Pipeline v2 — parse ABFM PDFs, analyze, generate reports"
    )
    parser.add_argument("--blueprint", required=True, help="Path to Blueprint Performance PDF")
    parser.add_argument("--bodysystem", help="Path to Body System Performance PDF")
    parser.add_argument("--score-report", dest="score_report", help="Path to Overall Score Report PDF (provides actual scaled score, PGY mean, SE)")
    parser.add_argument("--db", required=True, help="Path to ite_intelligence.db")
    parser.add_argument("--config", help="Path to ite_parser_config.json (default: auto-detect)")
    parser.add_argument("--output-dir", default=".", help="Output directory for reports")
    parser.add_argument("--json-only", action="store_true", help="Only output JSON, skip reports")
    parser.add_argument("--skip-reading-list", action="store_true", help="Omit the High-Yield Reading List section from the report")
    parser.add_argument("--question-count", type=int, default=20, help="Number of practice questions to select (default: 20)")
    parser.add_argument(
        "--pgy-level",
        type=int,
        choices=[1, 2, 3, 4],
        default=2,
        help="PGY level for national benchmark comparison (1-4, default: 2)"
    )
    parser.add_argument(
        "--plugins",
        default="concept,icd10",
        help='Comma-separated plugins to enable or "all" (default: concept,icd10)'
    )
    parser.add_argument(
        "--v1-only",
        action="store_true",
        help="Fall back to v1 analyzer + v1 report builder (backward compat)"
    )
    parser.add_argument(
        "--v2-only",
        action="store_true",
        help="Use deprecated v2 analyzer (subcategory crash risk — for reference only)"
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    config = load_config(args.config)

    # ========================================================================
    # NAMING CHECK — directory convention validation for YoY continuity
    # ========================================================================
    print("=" * 60)
    print("NAMING CHECK")
    print("=" * 60)
    _out_name     = output_dir.name          # should be "outputs"
    _resident_dir = output_dir.parent        # should be ITE_lastname_firstname/
    _inputs_dir   = _resident_dir / "inputs"
    _is_outputs   = _out_name == "outputs"
    _has_inputs   = _inputs_dir.exists()

    print(f"\n  Resident folder  : {_resident_dir.name}")
    print(f"  Output folder    : {output_dir}")
    print(f"  inputs/ present  : {'✓ YES' if _has_inputs else '✗ NO — create it and put raw PDFs there'}")
    _out_ok_msg = "✓ YES" if _is_outputs else f"✗ NO — folder is '{_out_name}', expected 'outputs'"
    print(f"  outputs/ name OK : {_out_ok_msg}")
    print()

    if _is_outputs:
        print("  ✓ Folder structure OK")
        print("  ℹ  YoY lookup: will search outputs/ for analysis_v2_{{YYYY}}.json after PDF parsing")
    else:
        print("  ⚠ WARNING: Output folder is not named 'outputs'.")
        print("    Year-over-year tracking requires the following structure:")
        print()
        print("    ITE_{lastname}_{firstname}/")
        print("      inputs/                          ← raw PDFs from ABFM")
        print("        {lastname}_{firstname}_{YYYY}_blueprint.pdf")
        print("        {lastname}_{firstname}_{YYYY}_bodysystem.pdf")
        print("        {lastname}_{firstname}_{YYYY}_score.pdf")
        print("      outputs/                         ← pass this as --output-dir")
        print("        analysis_v2_{YYYY}.json        ← generated per run")
        print("        ITE_{YYYY}_v3_Analysis_....docx")
        print()
        print("    Example run command:")
        print("      python ite_analyze_v2.py \\")
        print("        --blueprint  \"ITE_scholl_michael/inputs/scholl_michael_2025_blueprint.pdf\" \\")
        print("        --bodysystem \"ITE_scholl_michael/inputs/scholl_michael_2025_bodysystem.pdf\" \\")
        print("        --score-report \"ITE_scholl_michael/inputs/scholl_michael_2025_score.pdf\" \\")
        print("        --db path/to/ite_intelligence.db \\")
        print("        --output-dir \"ITE_scholl_michael/outputs\"")
        print()
        print("    Continuing — YoY lookup will still run but may not find prior years.")

    # ========================================================================
    # STAGE 1: PDF Extraction (identical to v1)
    # ========================================================================
    print("=" * 60)
    print("STAGE 1: PDF Extraction")
    print("=" * 60)

    print(f"\nParsing blueprint: {args.blueprint}")
    blueprint = parse_blueprint(args.blueprint, config)
    print(f"  Items extracted: {blueprint['summary']['total']}")
    print(f"  Correct: {blueprint['summary']['correct']} ({blueprint['summary']['pct']}%)")
    print(f"  Incorrect: {blueprint['summary']['incorrect']}")
    print(f"  Deleted items: {blueprint['deleted_items']}")

    if args.bodysystem:
        print(f"\nParsing body system: {args.bodysystem}")
        bodysystem = parse_bodysystem(args.bodysystem, config)
        print(f"  Items extracted: {len(bodysystem['items'])}")
        print(f"  Systems found: {bodysystem['systems_found']}")

        print("\nMerging results...")
        merged = merge_results(blueprint, bodysystem)
        print(f"  Cross-report overlap: {merged['cross_report_overlap']} items")
        if merged["cross_report_mismatches"]:
            print(f"  WARNING: Mismatches on items: {merged['cross_report_mismatches']}")
        else:
            print("  Cross-report validation: PASS")
    else:
        print("\n(No body system PDF provided — blueprint-only analysis)")
        merged = {
            "resident": blueprint["resident"],
            "exam_year": blueprint.get("exam_year", ""),
            "deleted_items": blueprint["deleted_items"],
            "items": [{**i, "body_system": None} for i in blueprint["items"]],
            "summary": blueprint["summary"],
            "body_systems_found": [],
        }

    # ========================================================================
    # STAGE 1.5: Score Report Enrichment (optional — no-op if not provided)
    # ========================================================================
    score_report_data = None
    if args.score_report:
        print("\n" + "=" * 60)
        print("STAGE 1.5: Overall Score Report")
        print("=" * 60)
        try:
            score_report_data = parse_score_report(args.score_report)
            print(f"\n  Resident:          {score_report_data.get('name', 'unknown')}")
            print(f"  Actual scaled:     {score_report_data['scaled_score']}  (±{score_report_data['standard_error']})")
            print(f"  vs MPS (380):      {'+' if score_report_data['vs_mps'] >= 0 else ''}{score_report_data['vs_mps']}")
            pgy = score_report_data.get("pgy_level")
            mean = score_report_data.get("pgy_mean_scaled")
            diff = score_report_data.get("vs_pgy_mean")
            if pgy and mean:
                sign = "+" if diff >= 0 else ""
                print(f"  PGY{pgy} class mean: {mean}  (resident {sign}{diff} vs mean)")
            if score_report_data.get("unanswered_items"):
                print(f"  Unanswered items:  {score_report_data['unanswered_items']}")
        except Exception as e:
            print(f"  WARNING: Could not parse score report: {e}")
            print("  Continuing without official scaled score data.")
            score_report_data = None
    else:
        print("\n[Note] No --score-report provided — scaled score will be estimated from raw counts.")

    # Push exam year from score report into merged BEFORE analyzer runs
    if score_report_data and score_report_data.get("exam_year"):
        merged["exam_year"] = score_report_data["exam_year"]

    # ========================================================================
    # STAGE 1.75: DB Body System Backfill
    # ========================================================================
    # For legacy years (2018–2023) ABFM did not issue a distinct body system PDF.
    # Old "clinical category" PDFs should NOT be passed as --bodysystem — they map
    # to the old blueprint taxonomy, not body system taxonomy.
    # When items have body_system=None, backfill from the DB using matched QIDs.
    # This runs automatically whenever body_system is absent — no flag required.
    _exam_year_for_backfill = merged.get("exam_year", "")
    _needs_backfill = any(i.get("body_system") is None for i in merged["items"])

    # Snapshot which body systems came from the ABFM PDF BEFORE backfill runs.
    # This powers the "ABFM-Reported vs. Database-Derived" split in the report.
    _abfm_systems = sorted(set(
        i["body_system"] for i in merged["items"] if i.get("body_system")
    ))

    if _exam_year_for_backfill and _needs_backfill:
        print("\n" + "=" * 60)
        print("STAGE 1.75: DB Body System Backfill")
        print("=" * 60)
        _qid_lookup = {i["item"]: f"QID-{_exam_year_for_backfill}-{i['item']:04d}"
                       for i in merged["items"]}
        _all_qids = list(_qid_lookup.values())
        try:
            import sqlite3 as _sqlite3
            _conn = _sqlite3.connect(args.db)
            _conn.row_factory = _sqlite3.Row
            _ph = ",".join(["?"] * len(_all_qids))
            _rows = _conn.execute(
                f"SELECT qid, body_system FROM questions WHERE qid IN ({_ph})", _all_qids
            ).fetchall()
            _conn.close()
            _qid_to_bs = {r["qid"]: r["body_system"] for r in _rows if r["body_system"]}
            _backfilled = 0
            for _item in merged["items"]:
                if _item.get("body_system") is None:
                    _qid = _qid_lookup.get(_item["item"])
                    if _qid and _qid in _qid_to_bs:
                        _item["body_system"] = _qid_to_bs[_qid]
                        _backfilled += 1
            _coverage = round(_backfilled / len(merged["items"]) * 100, 1) if merged["items"] else 0
            print(f"  Backfilled body_system from DB: {_backfilled}/{len(merged['items'])} items ({_coverage}%)")
            if _backfilled < len(merged["items"]) * 0.5:
                print(f"  WARNING: Low backfill coverage — exam year '{_exam_year_for_backfill}' may not match DB year keys.")
        except Exception as _e:
            print(f"  WARNING: DB body system backfill failed: {_e}")
            print("  Continuing without body system data.")

    # Build body_system_sources after backfill: all systems now present minus ABFM set = DB-derived.
    _all_systems_after = sorted(set(
        i["body_system"] for i in merged["items"] if i.get("body_system")
    ))
    _db_systems = sorted(set(_all_systems_after) - set(_abfm_systems))
    merged["body_system_sources"] = {
        "abfm": _abfm_systems,   # from official ABFM score report PDF
        "db":   _db_systems,     # backfilled from ITE Intelligence DB (Stage 1.75)
    }

    # ========================================================================
    # STAGE 2: Analysis (v2 or v1 based on --v1-only flag)
    # ========================================================================
    print("\n" + "=" * 60)
    print("STAGE 2: Performance Analysis + Question Matching")
    print("=" * 60)

    pgy_level_map = {1: "PGY1", 2: "PGY2", 3: "PGY3", 4: "All"}
    pgy_str = pgy_level_map[args.pgy_level]

    if args.v1_only:
        print("\n--v1-only flag set, using v1 analyzer...")
        analysis = analyze(merged, args.db)
        print("(v1 analyzer used)")
    elif args.v2_only:
        print("\n--v2-only flag set, using v2 analyzer (DEPRECATED)...")
        plugins = parse_plugins_arg(args.plugins)
        print(f"  PGY Level: {pgy_str}")
        print(f"  Plugins: {plugins if plugins else 'none'}")
        analysis = analyze_v2(
            merged,
            args.db,
            pgy_level=pgy_str,
            plugins=plugins,
            question_count=10
        )
        print("(v2 analyzer used — DEPRECATED)")
    else:
        print("\nUsing v3 analyzer:")
        print(f"  PGY Level: {pgy_str}")
        print(f"  Practice questions: {20}")
        print(f"  Banks: ITE + AAFP BRQ")
        analysis = analyze_v3(
            merged,
            args.db,
            pgy_level=pgy_str,
            question_count=args.question_count,
        )
        print("(v3 analyzer used)")

    perf = analysis.get("performance", {})
    overall = perf.get("overall", {})
    print(f"\nOverall: {overall.get('pct', 0)}% ({overall.get('correct', 0)}/{overall.get('total', 0)})")

    if perf.get("blueprint"):
        print("\nBlueprint performance:")
        for name, p in perf["blueprint"].items():
            marker = " *** WEAK" if p.get("rate", 0) < 0.70 else ""
            print(f"  {name}: {round(p.get('rate', 0)*100, 1)}% ({p.get('correct', 0)}/{p.get('total', 0)}){marker}")

    if perf.get("body_system"):
        print("\nBody system performance:")
        for name, p in perf["body_system"].items():
            marker = " *** WEAK" if p.get("rate", 0) < 0.70 else ""
            print(f"  {name}: {round(p.get('rate', 0)*100, 1)}% ({p.get('correct', 0)}/{p.get('total', 0)}){marker}")

    weak = perf.get("weak_areas", {})
    if weak.get("cross_tab"):
        print(f"\nWeak cross-tab intersections ({len(weak['cross_tab'])}):")
        for k, v in sorted(weak["cross_tab"].items(), key=lambda x: x[1].get("rate", 0)):
            print(f"  {k}: {round(v.get('rate', 0)*100)}% ({v.get('correct', 0)}/{v.get('total', 0)})")

    question_count = len(analysis.get('practice_questions', []))
    print(f"\nPractice questions selected: {question_count}")

    # Enrich analysis with official score report data (when --score-report provided)
    if score_report_data:
        sr = score_report_data
        overall = analysis.setdefault("performance", {}).setdefault("overall", {})
        overall["scaled_score_actual"]   = sr["scaled_score"]
        overall["scaled_score_source"]   = "official"
        overall["scaled_score_se"]       = sr["standard_error"]
        overall["mps"]                   = sr["mps"]
        overall["vs_mps"]                = sr["vs_mps"]
        overall["pgy_level"]             = sr["pgy_level"]
        overall["pgy_mean_scaled"]       = sr["pgy_mean_scaled"]
        overall["vs_pgy_mean"]           = sr["vs_pgy_mean"]
        overall["unanswered_items"]      = sr["unanswered_items"]
        # Official per-category scaled scores (supplement the raw-rate analysis)
        analysis["performance"]["blueprint_scaled"] = sr["blueprint_scaled"]

        # Normalize body_system_scaled keys to match the canonical grid PDF names
        # used in BODYSYSTEM_PDF_TO_DB (e.g. "Musculoskeletal" → "Injuries/Musculoskeletal").
        # When two score-report names collapse to the same canonical key (e.g.
        # "Reproductive: Female" + "Reproductive: Male" → "Sexual and Reproductive"),
        # the second value overwrites — both are reasonable proxies for the merged system.
        normalized_bs_scaled = {}
        for bs_name, bs_data in sr["body_system_scaled"].items():
            canonical = _normalize_body_system(bs_name)
            normalized_bs_scaled[canonical] = bs_data
        analysis["performance"]["body_system_scaled"] = normalized_bs_scaled
    else:
        analysis.setdefault("performance", {}).setdefault("overall", {})["scaled_score_source"] = "estimated"

    # Export JSON — year-labeled so multiple years can coexist in the same outputs/ folder
    exam_year = analysis.get("exam_year", "unknown")
    json_v2_path = output_dir / f"analysis_v2_{exam_year}.json"
    json_path    = output_dir / f"score_analysis_{exam_year}.json"
    export_analysis(analysis, str(json_v2_path))
    export_analysis(analysis, str(json_path))
    print(f"\nAnalysis JSON exported: {json_v2_path.name}")

    # Shim: add weak_areas for v1 HTML builder compatibility
    if "weak_areas" not in analysis.get("performance", {}):
        weak_bp = {k: v for k, v in analysis.get("performance", {}).get("blueprint", {}).items() if v.get("rate", 1) < 0.70}
        weak_bs = {k: v for k, v in analysis.get("performance", {}).get("body_system", {}).items() if v.get("rate", 1) < 0.70}
        weak_xt = {k: v for k, v in analysis.get("performance", {}).get("cross_tab", {}).items() if v.get("rate", 1) < 0.70}
        analysis.setdefault("performance", {})["weak_areas"] = {
            "blueprints": weak_bp, "body_systems": weak_bs, "cross_tab": weak_xt
        }

    # ========================================================================
    # STAGE 2.5: Longitudinal Delta (automatic — no user input required)
    # ========================================================================
    print("\n" + "=" * 60)
    print("STAGE 2.5: Longitudinal Delta Check")
    print("=" * 60)

    prior_analyses = find_prior_analyses(output_dir, int(analysis.get("exam_year", 0)))
    longitudinal = {}

    for key, prior_analysis in [("n1", prior_analyses["n1"]), ("n2", prior_analyses["n2"])]:
        if prior_analysis:
            delta = compute_longitudinal_delta(analysis, prior_analysis)
            longitudinal[key] = delta
            label = "n-1 (last year)" if key == "n1" else "n-2 (two years ago)"
            print(f"\n  [{label}] vs {delta['prior_year']}:")
            # Prefer scaled score delta; fall back to raw %
            if delta.get("scaled_delta") is not None:
                sign = "+" if delta["scaled_delta"] >= 0 else ""
                src_tag = " (official)" if delta["scaled_source"] == "official" else " (est.)"
                print(f"    Scaled score: {delta['prior_scaled']} → {delta['current_scaled']}  ({sign}{delta['scaled_delta']}){src_tag}")
                if delta.get("vs_pgy_delta") is not None:
                    sign2 = "+" if delta["vs_pgy_delta"] >= 0 else ""
                    pvp = delta["prior_vs_pgy"]
                    cvp = delta["current_vs_pgy"]
                    print(f"    vs PGY mean:  {'+' if (pvp or 0) >= 0 else ''}{pvp} → {'+' if (cvp or 0) >= 0 else ''}{cvp}  ({sign2}{delta['vs_pgy_delta']} vs peers)")
            elif delta.get("overall_delta_pct") is not None:
                sign = "+" if delta["overall_delta_pct"] >= 0 else ""
                print(f"    Score: {delta['prior_overall_pct']}% → {delta['current_overall_pct']}%  ({sign}{delta['overall_delta_pct']}%)")
            else:
                print("    Score: insufficient data for delta comparison (missing pct/scaled in one or both years)")
            traj = delta["weak_area_trajectory"]
            if traj["closed"]:
                print(f"    Closed gaps:     {', '.join(traj['closed'])}")
            if traj["persistent"]:
                print(f"    Persistent gaps: {', '.join(traj['persistent'])}")
            if traj["new"]:
                print(f"    New gaps:        {', '.join(traj['new'])}")

    if longitudinal:
        analysis["longitudinal_delta"] = longitudinal
        # Re-export JSON so the report builder picks up the delta
        export_analysis(analysis, str(json_v2_path))
        export_analysis(analysis, str(json_path))
        print(f"\n  [OK] Longitudinal delta written to analysis JSON")
    else:
        print("  No prior analyses found — first-year baseline established")

    if args.json_only:
        print("\n--json-only flag set, skipping report generation.")
        print("\n" + "=" * 60)
        print("COMPLETE (JSON only)")
        print("=" * 60)
        return

    # ========================================================================
    # STAGE 3: Report Generation
    # ========================================================================
    print("\n" + "=" * 60)
    print("STAGE 3: Report Generation")
    print("=" * 60)

    # Build filename-safe resident name
    name = analysis.get("resident", {}).get("name", "Unknown")
    safe_name = name.split(",")[0].strip().replace(" ", "_").replace(".", "")
    year = analysis.get("exam_year", "2025")

    html_path = output_dir / f"ITE_{year}_Score_Analysis_{safe_name}.html"
    if args.v1_only:
        docx_path = output_dir / f"ITE_{year}_Score_Analysis_{safe_name}.docx"
        questions_path = output_dir / f"ITE_{year}_Practice_Questions_{safe_name}.docx"
    else:
        docx_path = output_dir / f"ITE_{year}_v2_Analysis_{safe_name}.docx"
        questions_path = output_dir / f"ITE_{year}_v2_Exam_{safe_name}.docx"

    # Always build v1 HTML interactive report
    print("\n[Report 1/3] Building HTML interactive report (v1)...")
    try:
        build_html_report(analysis, str(html_path))
        print(f"  [OK] {html_path}")
    except Exception as e:
        print(f"  WARNING v1 HTML report skipped: {e}")
        print(f"    (v2 DOCX reports are the primary output — v1 HTML is supplementary)")

    if args.v1_only:
        # Fall back to v1 DOCX builders
        print("\n[Report 2/3] Building full DOCX report (v1)...")
        build_full_docx(analysis, str(docx_path))
        print(f"  [OK] {docx_path}")

        print("\n[Report 3/3] Building questions-only DOCX (v1)...")
        build_questions_docx(analysis, str(questions_path))
        print(f"  [OK] {questions_path}")
    else:
        # Call v2 Node.js report builder
        print("\n[Report 2/3 & 3/3] Building v2 DOCX reports via Node.js...")
        try:
            build_v2_reports(analysis, output_dir, str(json_v2_path),
                             skip_reading_list=args.skip_reading_list)
            print(f"  [OK] {docx_path}")
            print(f"  [OK] {questions_path}")
        except Exception as e:
            print(f"  WARNING: v2 report generation failed: {e}")
            print("  Falling back to v1 DOCX builders...")
            build_full_docx(analysis, str(docx_path))
            build_questions_docx(analysis, str(questions_path))
            print(f"  [OK] {docx_path} (v1 fallback)")
            print(f"  [OK] {questions_path} (v1 fallback)")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"\nResident: {name}")
    print(f"Score: {overall.get('pct', 0)}% ({overall.get('correct', 0)}/{overall.get('total', 0)})")
    print(f"Exam Year: {year}")
    if not args.v1_only:
        print(f"PGY Level (benchmark): {pgy_str}")
        plugins = parse_plugins_arg(args.plugins)
        print(f"Plugins enabled: {', '.join(plugins) if plugins else 'none'}")

    print(f"\nAll outputs:")
    print(f"  {json_path}")
    print(f"  {html_path}")
    print(f"  {docx_path}")
    print(f"  {questions_path}")
    print()


if __name__ == "__main__":
    main()

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
import subprocess
from pathlib import Path

# Allow running from any directory
pipeline_dir = Path(__file__).parent
sys.path.insert(0, str(pipeline_dir))
sys.path.insert(0, str(pipeline_dir / "v1"))

from ite_parser import load_config, parse_blueprint, parse_bodysystem, merge_results, export_json

# Import v3 analyzer (default) and v2 (legacy --v2-only flag)
from ite_analyzer_v3 import analyze_v3

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


def build_v2_reports(analysis: dict, output_dir: Path, analysis_json_path: str):
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

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
    parser.add_argument("--db", required=True, help="Path to ite_intelligence.db")
    parser.add_argument("--config", help="Path to ite_parser_config.json (default: auto-detect)")
    parser.add_argument("--output-dir", default=".", help="Output directory for reports")
    parser.add_argument("--json-only", action="store_true", help="Only output JSON, skip reports")
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
            question_count=20,
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

    # Export JSON — v2 saves as analysis_v2.json (used by report builder v2)
    # Also saves score_analysis.json for v1 compatibility
    json_v2_path = output_dir / "analysis_v2.json"
    json_path = output_dir / "score_analysis.json"
    export_analysis(analysis, str(json_v2_path))
    export_analysis(analysis, str(json_path))
    print(f"\nAnalysis JSON exported: {json_v2_path}")

    # Shim: add weak_areas for v1 HTML builder compatibility
    if "weak_areas" not in analysis.get("performance", {}):
        weak_bp = {k: v for k, v in analysis.get("performance", {}).get("blueprint", {}).items() if v.get("rate", 1) < 0.70}
        weak_bs = {k: v for k, v in analysis.get("performance", {}).get("body_system", {}).items() if v.get("rate", 1) < 0.70}
        weak_xt = {k: v for k, v in analysis.get("performance", {}).get("cross_tab", {}).items() if v.get("rate", 1) < 0.70}
        analysis.setdefault("performance", {})["weak_areas"] = {
            "blueprints": weak_bp, "body_systems": weak_bs, "cross_tab": weak_xt
        }

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
            build_v2_reports(analysis, output_dir, str(json_v2_path))
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

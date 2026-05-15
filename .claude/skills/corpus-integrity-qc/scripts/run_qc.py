"""
run_qc.py
=========
Coordinator / orchestrator for the corpus-integrity-qc skill.

Phase 1 — Verify staging JSONs exist (per-year), report any missing.
Phase 2 — Run Layer A / B / C in parallel as subprocesses.
Phase 3 — Build qc_report.md (build_report.py).
Phase 4 — Generate fixes.sql (generate_fixes.py).
Phase 5 — Print summary + output dir.

This is the standalone, headless path. The skill's model-driven path
(parallel Agent-tool dispatch) is described in the `../agents/` README
and the per-layer `*-auditor.md` prompts; both paths produce the same
artifacts in OUTPUT_DIR.

Usage:
  python run_qc.py [--project-root <ROOT>] [--db-path <DB>] \\
                   [--staging-dir <DIR>] [--output-dir <DIR>] \\
                   [--years 2018 ... 2025] \\
                   [--skip-staging-check]

OUTPUT_DIR default:
  <project_root>/03_module.3_analyst/outputs/corpus_qc/{YYYY-MM-DD}/

Produces in OUTPUT_DIR:
  findings_layer_a.json
  findings_layer_b.json
  findings_layer_c.json
  qc_report.md
  fixes.sql
"""

from __future__ import annotations

import argparse
import datetime as _dt
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def _default_project_root() -> Path:
    return SCRIPT_DIR.parent.parent.parent.parent.parent.resolve()


def _resolve_paths(args) -> dict[str, Path]:
    project_root = (
        Path(args.project_root).resolve() if args.project_root
        else _default_project_root()
    )
    db_path = (
        Path(args.db_path).resolve() if args.db_path
        else project_root / "00_database" / "db" / "ite_intelligence.db"
    )
    staging_dir = (
        Path(args.staging_dir).resolve() if args.staging_dir
        else project_root / "02_module.2_processor" / "outputs"
    )
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        today = _dt.date.today().isoformat()
        output_dir = (
            project_root / "03_module.3_analyst" / "outputs"
            / "corpus_qc" / today
        )
    return {
        "project_root": project_root,
        "db": db_path,
        "staging": staging_dir,
        "output": output_dir,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 — staging verification
# ══════════════════════════════════════════════════════════════════════════════

def verify_staging(staging_dir: Path, years: list[int]) -> list[int]:
    missing = [
        y for y in years
        if not (staging_dir / f"{y}_critique_refs_staging.json").exists()
    ]
    return missing


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 — parallel layer dispatch
# ══════════════════════════════════════════════════════════════════════════════

def _run_layer(layer: str, cmd: list[str]) -> tuple[str, int, str, str]:
    """Run one layer script. Returns (layer, returncode, stdout, stderr)."""
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    return layer, proc.returncode, proc.stdout, proc.stderr


def run_layers_parallel(
    paths: dict[str, Path],
    years: list[int],
) -> dict[str, int]:
    """Dispatch A/B/C in parallel via ThreadPoolExecutor. Returns
    {layer: returncode}. Each layer script writes its findings JSON to
    OUTPUT_DIR before returning."""
    py = sys.executable
    out = str(paths["output"])
    db = str(paths["db"])
    staging = str(paths["staging"])
    project_root = str(paths["project_root"])

    cmds = {
        "A": [py, str(SCRIPT_DIR / "layer_a_text.py"),
              "--output-dir", out,
              "--db-path", db,
              "--project-root", project_root],
        "B": [py, str(SCRIPT_DIR / "layer_b_citation.py"),
              "--output-dir", out,
              "--db-path", db,
              "--staging-dir", staging,
              "--project-root", project_root,
              "--years", *[str(y) for y in years]],
        "C": [py, str(SCRIPT_DIR / "layer_c_structural.py"),
              "--output-dir", out,
              "--db-path", db,
              "--project-root", project_root],
    }

    results: dict[str, int] = {}
    print(f"Dispatching {len(cmds)} layers in parallel...")
    with ThreadPoolExecutor(max_workers=len(cmds)) as pool:
        futures = {
            pool.submit(_run_layer, layer, cmd): layer
            for layer, cmd in cmds.items()
        }
        for fut in as_completed(futures):
            layer, rc, stdout, stderr = fut.result()
            tag = "✓" if rc == 0 else "✗"
            print(f"  {tag} Layer {layer} (rc={rc})")
            if stdout.strip():
                for line in stdout.strip().splitlines():
                    print(f"      | {line}")
            if rc != 0 and stderr.strip():
                for line in stderr.strip().splitlines():
                    print(f"    err | {line}", file=sys.stderr)
            results[layer] = rc
    return results


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3/4 — report + fixes
# ══════════════════════════════════════════════════════════════════════════════

def run_report_and_fixes(paths: dict[str, Path]) -> tuple[int, int]:
    py = sys.executable
    out = str(paths["output"])
    db = str(paths["db"])
    project_root = str(paths["project_root"])

    print()
    print("Building qc_report.md...")
    r1 = subprocess.run(
        [py, str(SCRIPT_DIR / "build_report.py"), "--findings-dir", out],
        capture_output=True, text=True, check=False,
    )
    print(r1.stdout.strip() or "(no stdout)")
    if r1.returncode != 0:
        print(r1.stderr, file=sys.stderr)

    print("Generating fixes.sql...")
    r2 = subprocess.run(
        [py, str(SCRIPT_DIR / "generate_fixes.py"),
         "--findings-dir", out,
         "--db-path", db,
         "--project-root", project_root],
        capture_output=True, text=True, check=False,
    )
    print(r2.stdout.strip() or "(no stdout)")
    if r2.returncode != 0:
        print(r2.stderr, file=sys.stderr)

    return r1.returncode, r2.returncode


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Corpus-integrity-qc orchestrator")
    parser.add_argument("--project-root", help="Override PROJECT_ROOT")
    parser.add_argument("--db-path", help="ite_intelligence.db path")
    parser.add_argument("--staging-dir", help="M2 outputs/ dir")
    parser.add_argument("--output-dir", help="Output dir (default: corpus_qc/{today})")
    parser.add_argument("--years", nargs="+", type=int,
                        default=list(range(2018, 2026)),
                        help="Years for Layer B (default 2018-2025)")
    parser.add_argument("--skip-staging-check", action="store_true",
                        help="Do not abort if staging JSONs are missing")
    args = parser.parse_args()

    paths = _resolve_paths(args)
    paths["output"].mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("corpus-integrity-qc — orchestrator")
    print("=" * 70)
    print(f"PROJECT_ROOT : {paths['project_root']}")
    print(f"DB           : {paths['db']}")
    print(f"STAGING_DIR  : {paths['staging']}")
    print(f"OUTPUT_DIR   : {paths['output']}")
    print(f"YEARS        : {args.years}")
    print()

    if not paths["db"].exists():
        print(f"ERROR: DB not found: {paths['db']}", file=sys.stderr)
        return 1
    if not paths["staging"].exists():
        print(f"ERROR: staging dir not found: {paths['staging']}", file=sys.stderr)
        return 1

    # Phase 1 — staging verification
    print("Phase 1: verifying staging JSONs...")
    missing = verify_staging(paths["staging"], args.years)
    if missing:
        print(f"  ⚠  Missing staging for years: {missing}")
        print("    Run from PROJECT_ROOT/02_module.2_processor/scripts/:")
        for y in missing:
            print(f"      python extract_ite_critique_refs.py "
                  f"--pdf ../../01_module.1_warehouse/ite_exams/{y}_critique.pdf "
                  f"--year {y}")
        if not args.skip_staging_check:
            print("  Aborting. Re-run with --skip-staging-check to proceed anyway.",
                  file=sys.stderr)
            return 2
        print("  Proceeding with --skip-staging-check; Layer B coverage will be partial.")
    else:
        print(f"  ✓ All {len(args.years)} years present.")
    print()

    # Phase 2 — parallel layer dispatch
    print("Phase 2: parallel layer dispatch")
    layer_results = run_layers_parallel(paths, args.years)
    failures = [k for k, v in layer_results.items() if v != 0]
    if failures:
        print(f"\nERROR: layers failed: {failures}", file=sys.stderr)
        return 3

    # Phase 3+4 — report + fixes
    print()
    print("Phase 3+4: report + fixes")
    r1, r2 = run_report_and_fixes(paths)
    if r1 != 0 or r2 != 0:
        print(f"\nERROR: report/fixes generation failed (rc={r1},{r2})",
              file=sys.stderr)
        return 4

    # Phase 5 — summary
    print()
    print("=" * 70)
    print("DONE.")
    print(f"  Artifacts in: {paths['output']}")
    print("    findings_layer_a.json")
    print("    findings_layer_b.json")
    print("    findings_layer_c.json")
    print("    qc_report.md")
    print("    fixes.sql")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

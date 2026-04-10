#!/usr/bin/env python3
"""Repair manifest files after edit_block corruption."""
import json
import re
from pathlib import Path

project_root = Path(__file__).resolve().parent
claude_file = project_root / "CLAUDE.md"
readme_file = project_root / "README.json"
repo_map_file = project_root / "REPO_MAP.md"

# Check if files exist
if not claude_file.exists():
    print(f"ERROR: {claude_file} not found")
    exit(1)

# Read CLAUDE.md (may be corrupted)
try:
    with open(claude_file, 'r', encoding='utf-8', errors='ignore') as f:
        claude_content = f.read()
except Exception as e:
    print(f"ERROR reading CLAUDE.md: {e}")
    exit(1)

# Update BATON in CLAUDE.md
old_baton_051 = "BATON_active_051_20260409_module5_housekeeping.md"
new_baton_052 = "BATON_active_052_20260410_psychogenic_retirement.md"
if old_baton_051 in claude_content:
    claude_content = claude_content.replace(
        f"`{old_baton_051}` — Module 5 web scaffold documented; housekeeping sweep complete",
        f"`{new_baton_052}` — Psychogenic retired; practice Q coverage fixed (RC1+RC2+RC3)"
    )
    print(f"✓ Updated Active BATON in CLAUDE.md")
else:
    print("⚠ Could not find old BATON in CLAUDE.md")

# Update Git hash in CLAUDE.md
if "45065a1" in claude_content:
    claude_content = claude_content.replace("45065a1", "8fb7549")
    print("✓ Updated git hash in CLAUDE.md (45065a1 → 8fb7549)")

# Update Next Steps in CLAUDE.md
old_next_steps = """## Next Steps (as of BATON 051, 2026-04-09)

### Immediate
1. **DEFERRED-YOY-ROBUSTNESS** — Expand longitudinal_delta edge-case handling in ite_analyzer_v3.py
2. **DEFERRED-PRACTICE-Q-COVERAGE** — Query qid_art_xref for 0-question dims; investigate root cause
3. **DOCX review** — Mikey to verify Pjetergjoka_2024/2025 output

### Short-term
4. **Module 5 setup** — Provision Supabase project, run migrations, sync SQLite → Supabase, deploy Railway parser + Netlify frontend
5. **DEFERRED-PGY-BENCHMARKS** — Receive PGY baseline ranges from Mikey; integrate into Executive Summary
6. **DATABASE_GUIDE.md relocation** — Finalize git rename registration
7. **DEFERRED-AAFP-PDF-RETRY** — Re-run when AAFP site stabilizes"""

new_next_steps = """## Next Steps (as of BATON 052, 2026-04-10)

### Immediate
1. **DEFERRED-YOY-ROBUSTNESS** — Expand longitudinal_delta edge-case handling in ite_analyzer_v3.py
2. **DOCX review** — Mikey to verify Pjetergjoka_2024/2025 DOCX output (YoY table, practice Q spread now fixed)

### Short-term
3. **Module 5 setup** — Provision Supabase project, run migrations, sync SQLite → Supabase, deploy Railway FastAPI + Netlify
4. **DEFERRED-PGY-BENCHMARKS** — Receive PGY 1–4 data from Mikey; integrate into report
5. **DATABASE_GUIDE.md relocation** — git rm old + git add new; commit
6. **DEFERRED-AAFP-PDF-RETRY** — Re-run when AAFP site stabilizes"""

if old_next_steps in claude_content:
    claude_content = claude_content.replace(old_next_steps, new_next_steps)
    print("✓ Updated Next Steps in CLAUDE.md")
else:
    print("⚠ Could not find old Next Steps text in CLAUDE.md")

# Write CLAUDE.md
try:
    with open(claude_file, 'w', encoding='utf-8') as f:
        f.write(claude_content)
    print("✓ Wrote CLAUDE.md")
except Exception as e:
    print(f"ERROR writing CLAUDE.md: {e}")
    exit(1)

# Update README.json
try:
    with open(readme_file, 'r') as f:
        readme_data = json.load(f)
except Exception as e:
    print(f"ERROR reading README.json: {e}")
    exit(1)

readme_data["baton"] = "BATON_active_052_20260410_psychogenic_retirement.md"
readme_data["baton_description"] = "Psychogenic retired across 12 scripts + DB; practice Q coverage fixed (RC1+RC2+RC3)"
readme_data["git_hash"] = "8fb7549"
readme_data["last_updated"] = "2026-04-10"

try:
    with open(readme_file, 'w') as f:
        json.dump(readme_data, f, indent=2)
    print("✓ Updated README.json")
except Exception as e:
    print(f"ERROR writing README.json: {e}")
    exit(1)

# Update REPO_MAP.md
try:
    with open(repo_map_file, 'r', encoding='utf-8') as f:
        repo_map_content = f.read()
except Exception as e:
    print(f"ERROR reading REPO_MAP.md: {e}")
    exit(1)

old_header = "**Last Updated:** 2026-04-09 (BATON 051 — Git hash: 45065a1) — Module 5 web platform scaffold added; housekeeping sweep complete"
new_header = "**Last Updated:** 2026-04-10 (BATON 052 — Git hash: 8fb7549) — Psychogenic retired; practice Q coverage fixed"

if old_header in repo_map_content:
    repo_map_content = repo_map_content.replace(old_header, new_header)
    print("✓ Updated header in REPO_MAP.md")
else:
    print("⚠ Could not find old header in REPO_MAP.md")

try:
    with open(repo_map_file, 'w', encoding='utf-8') as f:
        f.write(repo_map_content)
    print("✓ Wrote REPO_MAP.md")
except Exception as e:
    print(f"ERROR writing REPO_MAP.md: {e}")
    exit(1)

print("\n✅ All manifest files updated successfully!")

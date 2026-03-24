"""
PDF Sourcer Agent
=================
Spawns Claude agents to find and download missing AFP article PDFs.
Each article gets its own agent call (isolated, trackable).

Usage:
    python pdf_sourcer_agent.py                  # Source all missing articles
    python pdf_sourcer_agent.py --dry-run        # Just show the manifest, don't source
    python pdf_sourcer_agent.py --article ART-0112   # Source a single article
    python pdf_sourcer_agent.py --from-json manifest.json  # Source from a custom manifest file

Overnight / scheduled batch:
    python pdf_sourcer_agent.py --all-missing --batch-size 25 --yes
    python pdf_sourcer_agent.py --all-missing --batch-size 25 --yes --model haiku

Prerequisites:
    pip install claude-agent-sdk
    npm install -g @anthropic-ai/claude-code
    ANTHROPIC_API_KEY in environment variables

Created: March 20, 2026
Project: ITE Intelligence / Clinical Guidelines Library
"""

import asyncio
import argparse
import json
import sqlite3
import os
import sys
from datetime import datetime

from claude_agent_sdk import query, ClaudeAgentOptions

# ╔══════════════════════════════════════════════════════════════╗
# ║  CONFIG — Adjust these paths to match your environment      ║
# ╚══════════════════════════════════════════════════════════════╝

DB_PATH = r"C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\02_ite_intelligence\db\ite_intelligence.db"
PDF_LIBRARY = r"C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\01_pdf_guideline_library"
STAGING_DIR = os.path.join(PDF_LIBRARY, "00_non-codon", "_sourced_staging")
AGENTS_DIR = r"C:\Users\mpsch\Desktop\claude_knowledge\agents"
RESULTS_LOG = os.path.join(AGENTS_DIR, "pdf_sourcer_results.json")

# Authentication — AAFP cookies for paywalled content
# Export your aafp.org cookies using a browser extension (e.g. "Get cookies.txt LOCALLY")
# Save the file as agents/aafp_cookies.txt
COOKIE_FILE = os.path.join(AGENTS_DIR, "aafp_cookies.txt")

# Structured output schema — SDK enforces this format, no prompt-hacking needed
OUTPUT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "article_id":      {"type": "string",           "description": "The ART-XXXX identifier"},
            "status":          {"type": "string",           "enum": ["downloaded", "paywall", "cookies_expired", "not_found"]},
            "url":             {"type": ["string", "null"], "description": "Article page URL, or null"},
            "pdf_url":         {"type": ["string", "null"], "description": "Direct PDF download URL, or null"},
            "saved_to":        {"type": ["string", "null"], "description": "Full path where PDF was saved, or null"},
            "file_size_bytes": {"type": "integer",          "description": "File size in bytes, 0 if not downloaded"},
            "notes":           {"type": "string",           "description": "Details about what was found or why it failed"},
        },
        "required": ["article_id", "status", "file_size_bytes", "notes"],
        "additionalProperties": False,
    }
}

# Agent tuning
MAX_TURNS = 25              # Max agentic loop iterations per article
AGENT_MODEL = "sonnet"      # "sonnet", "opus", or "haiku"
AGENT_EFFORT = "low"        # "low", "medium", "high", "max" — low is sufficient for search+download
AGENT_TIMEOUT_SEC = 180     # Kill a stuck agent after this many seconds (3 min per article)
MAX_BUDGET_USD = 5.00       # Hard cost ceiling for the entire run (0 = no limit)


# ╔══════════════════════════════════════════════════════════════╗
# ║  MANIFEST BUILDER                                           ║
# ╚══════════════════════════════════════════════════════════════╝

def get_all_library_pdfs():
    """Scan the PDF library and return a set of all filenames present."""
    pdf_files = set()
    for root, dirs, files in os.walk(PDF_LIBRARY):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdf_files.add(f)
    return pdf_files


def build_manifest(target_ids=None):
    """
    Query DB for articles missing from the PDF library.
    If target_ids is provided, only check those. Otherwise, check all articles.
    Returns a list of dicts with article metadata.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if target_ids:
        placeholders = ','.join(['?'] * len(target_ids))
        cur.execute(f"""
            SELECT article_id, author1, author2, year, title,
                   codon_filename, citation_count, source_type
            FROM articles
            WHERE article_id IN ({placeholders})
        """, target_ids)
    else:
        cur.execute("""
            SELECT article_id, author1, author2, year, title,
                   codon_filename, citation_count, source_type
            FROM articles
            WHERE codon_filename IS NOT NULL
        """)

    rows = cur.fetchall()
    conn.close()

    # Cross-reference against actual files on disk
    existing_pdfs = get_all_library_pdfs()

    manifest = []
    for row in rows:
        codon = row['codon_filename']
        if codon and codon not in existing_pdfs:
            manifest.append({
                'article_id': row['article_id'],
                'author1': row['author1'],
                'author2': row['author2'],
                'year': row['year'],
                'title': row['title'],
                'codon_filename': codon,
                'citation_count': row['citation_count'] or 0,
                'source_type': row['source_type'],
                'vc_cited': (row['citation_count'] or 0) > 0,
            })

    # Sort: VC-cited first, then by citation count descending
    manifest.sort(key=lambda x: (-int(x['vc_cited']), -x['citation_count']))
    return manifest


# ╔══════════════════════════════════════════════════════════════╗
# ║  AGENT PROMPT TEMPLATE                                      ║
# ╚══════════════════════════════════════════════════════════════╝

def build_agent_prompt(article, staging_dir, cookie_file=None):
    """Construct the prompt for a single PDF sourcing agent."""

    authors = article['author1'] or "Unknown"
    if article['author2']:
        authors += f", {article['author2']}"

    # Build the curl command with or without cookies
    # Use forward slashes to avoid Windows backslash escape issues in f-strings
    save_path = os.path.join(staging_dir, article['codon_filename']).replace('\\', '/')
    if cookie_file and os.path.exists(cookie_file):
        cookie_path = cookie_file.replace('\\', '/')
        curl_cmd = f'curl -L -b "{cookie_path}" -o "{save_path}"'
        auth_note = f"""
AUTHENTICATION:
You have an authenticated AAFP session via cookies. Use them on EVERY curl request:
  curl -L -b "{cookie_path}" -o "OUTPUT_PATH" "URL"
This means paywalled content on aafp.org should be accessible. If a download
returns an HTML login page instead of a PDF, the cookies may have expired —
report status as "cookies_expired" so the user can re-export."""
    else:
        curl_cmd = f'curl -L -o "{save_path}"'
        auth_note = """
AUTHENTICATION:
No cookie file available. If you hit a paywall, report the URL — don't try to log in."""

    return f"""You are a PDF sourcing agent. Your single task: find and download one specific medical journal article as a PDF.

ARTICLE TO FIND:
  Article ID:  {article['article_id']}
  Authors:     {authors}
  Year:        {article['year']}
  Title:       {article['title']}
  Save as:     {article['codon_filename']}
{auth_note}

SEARCH STRATEGY (try in order):
1. Search the web for: {authors} {article['year']} "{article['title']}" site:aafp.org
2. If step 1 fails, broaden: {authors} {article['year']} {article['title']} American Family Physician
3. If step 2 fails, try PubMed: search for the article, find the DOI, follow to publisher
4. If all searches fail, try Google Scholar as a last resort

DOWNLOAD INSTRUCTIONS:
1. When you find the article page, look for a PDF download link (often a "PDF" button or direct .pdf URL)
2. Download the PDF using: {curl_cmd} "URL_HERE"
3. Verify the download is a valid PDF by checking the first bytes:
   python -c "f=open('{save_path}','rb'); h=f.read(5); f.close(); print('VALID' if h==b'%%PDF-' else 'INVALID: '+str(h))"
4. If the file is HTML instead of PDF (common with paywalled redirects), delete it and report as paywall

IMPORTANT:
- The staging directory is: {staging_dir}
- Make sure it exists before downloading (mkdir if needed)
- Do NOT rename the file after downloading — use the exact filename specified above
- If you find the article but can't get the PDF, that's still useful — report the URL
- ALWAYS verify the downloaded file starts with %PDF- (5 bytes). HTML pages pretending to be PDFs are common.

WHEN DONE, report your result with these fields:
- article_id: "{article['article_id']}"
- status: one of "downloaded", "paywall", "cookies_expired", "not_found"
- url: the article page URL you found (or null)
- pdf_url: the direct PDF download URL (or null)
- saved_to: the full path where the PDF was saved (or null)
- file_size_bytes: file size in bytes (0 if not downloaded)
- notes: brief description of what happened
"""


# ╔══════════════════════════════════════════════════════════════╗
# ║  AGENT RUNNER                                               ║
# ╚══════════════════════════════════════════════════════════════╝

async def _run_agent(prompt):
    """Inner coroutine — runs one agent query. Wrapped with timeout in source_one_article."""
    result_text = ""

    # Build options — only pass max_budget_usd if set
    options_kwargs = dict(
        allowed_tools=["Bash", "Read", "Write", "Glob", "WebSearch", "WebFetch"],
        model=AGENT_MODEL,
        max_turns=MAX_TURNS,
        permission_mode="acceptEdits",
        effort=AGENT_EFFORT,
        output_format=OUTPUT_SCHEMA,   # SDK enforces structured JSON output
    )
    if MAX_BUDGET_USD > 0:
        options_kwargs["max_budget_usd"] = MAX_BUDGET_USD

    async for message in query(prompt=prompt, options=ClaudeAgentOptions(**options_kwargs)):
        if hasattr(message, "result"):
            result_text = message.result

    # Parse structured output — result_text should now always be valid JSON
    try:
        return json.loads(result_text) if result_text else {"status": "not_found", "notes": "No result returned"}
    except (json.JSONDecodeError, TypeError):
        return {"status": "not_found", "notes": f"Unparseable result: {result_text[:200]}"}


async def source_one_article(article, staging_dir, cookie_file=None):
    """Spawn a Claude agent to find and download one article PDF.
    Kills the agent if it exceeds AGENT_TIMEOUT_SEC."""

    prompt = build_agent_prompt(article, staging_dir, cookie_file=cookie_file)

    try:
        result_text = await asyncio.wait_for(
            _run_agent(prompt),
            timeout=AGENT_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        print(f"    ⏱ Timed out after {AGENT_TIMEOUT_SEC}s — moving on")
        result_text = {"status": "not_found", "notes": f"Agent timed out after {AGENT_TIMEOUT_SEC}s"}

    return result_text


def _save_results_incremental(results):
    """Save results after each article so progress survives Ctrl+C."""
    existing = []
    if os.path.exists(RESULTS_LOG):
        try:
            with open(RESULTS_LOG, 'r') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []
    existing.extend(results)
    with open(RESULTS_LOG, 'w') as f:
        json.dump(existing, f, indent=2)


async def run_sourcing(manifest, staging_dir, cookie_file=None):
    """Sequentially source each article in the manifest."""

    results = []
    succeeded = 0
    failed = 0

    for i, article in enumerate(manifest):
        vc_tag = " [VC-CITED]" if article['vc_cited'] else ""
        print(f"\n  [{i+1}/{len(manifest)}] {article['article_id']}: "
              f"{article['author1']} {article['year']} — {article['title'][:50]}...{vc_tag}")

        entry = None
        try:
            result = await source_one_article(article, staging_dir, cookie_file=cookie_file)
            entry = {
                "article_id": article["article_id"],
                "codon_filename": article["codon_filename"],
                "agent_output": result,
                "timestamp": datetime.now().isoformat(),
                "error": None,
            }
            # Quick check: did the file land?
            expected_path = os.path.join(staging_dir, article["codon_filename"])
            if os.path.exists(expected_path):
                size = os.path.getsize(expected_path)
                print(f"    ✓ Downloaded ({size:,} bytes)")
                succeeded += 1
            else:
                print(f"    ○ Agent finished — file not found in staging (check output)")
                failed += 1

        except Exception as e:
            entry = {
                "article_id": article["article_id"],
                "codon_filename": article["codon_filename"],
                "agent_output": None,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }
            print(f"    ✗ Error: {e}")
            failed += 1

        # Save after EACH article — progress survives Ctrl+C
        if entry:
            results.append(entry)
            _save_results_incremental([entry])

    return results, succeeded, failed


# ╔══════════════════════════════════════════════════════════════╗
# ║  MAIN                                                       ║
# ╚══════════════════════════════════════════════════════════════╝

def main():
    global AGENT_MODEL

    parser = argparse.ArgumentParser(description="PDF Sourcer Agent — find and download missing article PDFs")
    parser.add_argument("--dry-run", action="store_true", help="Show manifest only, don't source")
    parser.add_argument("--article", type=str, help="Source a single article by ART-ID (e.g. ART-0112)")
    parser.add_argument("--from-json", type=str, help="Load manifest from a JSON file instead of DB")
    parser.add_argument("--all-missing", action="store_true", help="Scan ALL articles in DB for missing PDFs (not just the known 10)")
    parser.add_argument("--model", type=str, default=AGENT_MODEL, choices=["sonnet", "opus", "haiku"], help="Model for the sourcing agents")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt (for unattended/scheduled runs)")
    parser.add_argument("--batch-size", type=int, default=0, help="Max articles to source per run (0 = unlimited)")
    args = parser.parse_args()

    AGENT_MODEL = args.model

    # ── Check for cookie file ──────────────────────────────────
    cookie_file = COOKIE_FILE if os.path.exists(COOKIE_FILE) else None

    print("=" * 65)
    print("  PDF SOURCER AGENT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    budget_str = f"${MAX_BUDGET_USD:.2f}" if MAX_BUDGET_USD > 0 else "unlimited"
    print(f"  Model: {AGENT_MODEL} | Effort: {AGENT_EFFORT} | Timeout: {AGENT_TIMEOUT_SEC}s | Budget cap: {budget_str}")
    if cookie_file:
        age_hrs = (datetime.now().timestamp() - os.path.getmtime(cookie_file)) / 3600
        print(f"  Auth:  AAFP cookies loaded ({age_hrs:.1f}h old)")
        if age_hrs > 72:
            print("  ⚠  Cookies are >72h old — consider re-exporting from browser")
    else:
        print("  Auth:  No cookie file (paywalled articles will be skipped)")
        print(f"         To enable: export aafp.org cookies → {COOKIE_FILE}")
    print("=" * 65)

    # ── Build or load manifest ──────────────────────────────────
    if args.from_json:
        print(f"\n[MANIFEST] Loading from {args.from_json}")
        with open(args.from_json, 'r') as f:
            manifest = json.load(f)
    elif args.article:
        print(f"\n[MANIFEST] Single article: {args.article}")
        manifest = build_manifest(target_ids=[args.article])
    elif args.all_missing:
        print(f"\n[MANIFEST] Scanning ALL articles for missing PDFs...")
        manifest = build_manifest(target_ids=None)
    else:
        # Default: the known missing articles from the BATON audit
        known_missing = [
            'ART-0112', 'ART-0272', 'ART-0457', 'ART-0569', 'ART-0713',
            'ART-0755', 'ART-1132', 'ART-1175', 'ART-1326', 'ART-1345',
        ]
        print(f"\n[MANIFEST] Checking {len(known_missing)} known missing articles...")
        manifest = build_manifest(target_ids=known_missing)

    # ── Display manifest ────────────────────────────────────────
    if not manifest:
        print("\n  No missing articles found! All PDFs are present in the library.")
        return

    # ── Apply batch size limit ─────────────────────────────────
    total_available = len(manifest)
    if args.batch_size > 0 and len(manifest) > args.batch_size:
        manifest = manifest[:args.batch_size]
        print(f"\n  {total_available} articles missing — batch limited to {args.batch_size}:\n")
    else:
        print(f"\n  Found {len(manifest)} articles to source:\n")

    vc_count = sum(1 for a in manifest if a['vc_cited'])
    print(f"  {vc_count} VC-cited (high priority) | {len(manifest) - vc_count} non-VC\n")

    for a in manifest:
        vc = "★" if a['vc_cited'] else " "
        auth = a['author1'] or "?"
        print(f"  {vc} {a['article_id']:10s}  {auth:15s} {a['year']}  {(a['title'] or '?')[:45]}")

    if args.dry_run:
        # Save manifest for reference
        manifest_path = os.path.join(AGENTS_DIR, "pdf_sourcer_manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f"\n  Manifest saved to: {manifest_path}")
        print("  (Dry run — no agents spawned)")
        return

    # ── Confirm before proceeding ───────────────────────────────
    print(f"\n  This will spawn {len(manifest)} agent(s) sequentially.")
    print(f"  Staging folder: {STAGING_DIR}")
    if not args.yes:
        resp = input("\n  Proceed? [y/N] ").strip().lower()
        if resp != 'y':
            print("  Aborted.")
            return
    else:
        print("  (--yes flag: skipping confirmation)")


    # ── Create staging dir ──────────────────────────────────────
    os.makedirs(STAGING_DIR, exist_ok=True)

    # ── Run agents ──────────────────────────────────────────────
    print(f"\n[SOURCING] Starting {len(manifest)} agent(s)...\n")
    results, succeeded, failed = asyncio.run(run_sourcing(manifest, STAGING_DIR, cookie_file=cookie_file))

    # Results already saved incrementally — no batch save needed

    # ── Summary ─────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  DONE")
    print(f"  Succeeded: {succeeded} | Failed/Unclear: {failed}")
    print(f"  Results log: {RESULTS_LOG}")
    print(f"  Staging dir: {STAGING_DIR}")
    print(f"\n  NEXT STEP: Review staging folder, then move verified PDFs")
    print(f"  to the appropriate library subfolder (02_codon or 00_non-codon).")
    print("=" * 65)


if __name__ == "__main__":
    main()

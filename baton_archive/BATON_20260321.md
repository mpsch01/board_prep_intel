# BATON — Agent SDK Introduction + PDF Sourcer Build

**Date:** March 21, 2026 (Session 1)
**Previous BATON:** `BATON_active_20260320_session2.md`
**Status:** MAJOR NEW CAPABILITY — Claude Agent SDK integrated. PDF Sourcer agent built and validated. All 10 known-missing articles downloaded. Overnight batch scheduled. Agent toolbox started.

---

## What Was Done This Session

### 1. Claude Agent SDK Introduced
User provided `import_asyncio.py` — a working Claude Agent SDK script. This opens the ability to spawn autonomous Claude agents programmatically from the user's Windows machine.

**Package:** `pip install claude-agent-sdk`
**Import:** `from claude_agent_sdk import query, ClaudeAgentOptions`
**Key API:** `async for message in query(prompt=..., options=ClaudeAgentOptions(...)):`

Reviewed both TypeScript and Python SDK reference docs. Key confirmed capabilities:
- `effort`: `"low" | "medium" | "high" | "max"` — controls thinking depth
- `max_budget_usd`: hard dollar ceiling per run
- `output_format`: JSON schema enforcement on agent output
- `max_turns`: loop limit
- `permission_mode`: `"acceptEdits"` for unattended runs
- `ClaudeSDKClient`: persistent session client for multi-turn agents (vs one-shot `query()`)
- `agents`: programmatically defined subagents
- `hooks`: PreToolUse/PostToolUse event callbacks

### 2. PDF Sourcer Agent Built (`agents/pdf_sourcer_agent.py`)
Full agent script that spawns Claude agents to find and download missing AFP article PDFs.

**Architecture:**
- Reads DB → builds manifest of missing articles (cross-referenced against actual files on disk)
- Spawns one agent per article (sequential, isolated)
- Agent searches aafp.org → PubMed → Google Scholar
- Downloads via `curl -L -b cookies.txt` (authenticated)
- Verifies PDF header (`%PDF-`)
- Saves to `_sourced_staging/` folder
- Results saved incrementally (survives Ctrl+C)

**Key features built:**
- AAFP cookie auth (`aafp_cookies.txt` — export from browser, overwrite to refresh)
- `effort='low'` for speed (sufficient for search+download tasks)
- `AGENT_TIMEOUT_SEC=180` — kills stuck agents after 3 min, logs timeout
- `MAX_BUDGET_USD=5.00` — hard cost ceiling per run
- `output_format=OUTPUT_SCHEMA` — JSON schema enforced by SDK (clean structured output)
- `--dry-run` — shows manifest, saves JSON, no agents spawned
- `--article ART-XXXX` — single article mode
- `--all-missing` — scans full DB for any article without a PDF
- `--batch-size N` — limits per run (for overnight batches)
- `--yes` / `-y` — skips confirmation (for scheduled/unattended runs)
- `--model` — override model per run

**Config knobs (top of file):**
```python
MAX_TURNS = 25
AGENT_MODEL = "sonnet"
AGENT_EFFORT = "low"
AGENT_TIMEOUT_SEC = 180
MAX_BUDGET_USD = 5.00
```

### 3. All 10 Known-Missing Articles Downloaded
100% success rate in staging folder:

| ART-ID | File | Size |
|---|---|---|
| ART-0112 | Baird_Batten_2022#@#ART-0112@#@.pdf | 352 KB |
| ART-0272 | Croteau_2014#@#ART-0272@#@.pdf | 432 KB |
| ART-0457 | Frazier_Santiago_Delgado_2021#@#ART-0457@#@.pdf | 1.0 MB |
| ART-0569 | Hauk_2017#@#ART-0569@#@.pdf | 153 KB |
| ART-0713 | Kravets_2016#@#ART-0713@#@.pdf | 645 KB |
| ART-0755 | Leeman_Dresang_2016#@#ART-0755@#@.pdf | 294 KB |
| ART-1132 | Sell_Nasir_2021#@#ART-1132@#@.pdf | 195 KB |
| ART-1175 | Smith_Olivas_2019#@#ART-1175@#@.pdf | 158 KB |
| ART-1326 | Westerfield_Koenig_2018#@#ART-1326@#@.pdf | 223 KB |
| ART-1345 | Williams_Moore_2023#@#ART-1345@#@.pdf | 266 KB |

**All 10 files are in staging — not yet moved to library.** See FLAG 46.

### 4. Overnight Batch Scheduled
**Task ID:** `pdf-sourcer-overnight`
**Schedule:** Every night at 1:09 AM (updated from weeknights to every night)
**Config:** 25 articles/night, --all-missing, --yes, sonnet
**Target:** 100 total articles sourced (10 done → 90 remaining → ~4 nights)
**Notification:** On completion each night

Manual run validated successfully (slow but working before tuning).

### 5. Bugs Fixed During This Session
- `SyntaxError`: `global AGENT_MODEL` declared after use — moved to top of function
- Path doubling: user ran script from wrong directory — documented correct invocation
- Windows path escaping: backslashes in f-strings mangled paths — fixed with `.replace('\\', '/')`
- Mangled cookie file created by pre-fix agent run — deleted

### 6. Agent Toolbox Started
Location: `C:\Users\mpsch\Desktop\claude_knowledge\agents\`

| File | Purpose |
|---|---|
| `import_asyncio.py` | Original SDK hello-world template |
| `pdf_sourcer_agent.py` | PDF sourcer — find & download missing articles |
| `pdf_sourcer_manifest.json` | Last dry-run manifest (10 articles) |
| `pdf_sourcer_results.json` | Cumulative sourcing results log |
| `aafp_cookies.txt` | AAFP session cookies (re-export when stale >72h) |

### 7. SDK Reference Docs Reviewed
User shared TypeScript and Python SDK reference. Saved to uploads. Key findings already applied to script. Notable for future agents:
- `ClaudeSDKClient` — persistent session, multi-turn, interrupt support → use for Pipeline Runner
- `output_format` JSON schema → now in pdf_sourcer, apply to all future agents
- `hooks` — PreToolUse/PostToolUse callbacks → useful for logging, rate limiting
- `agents` dict → programmatic subagent definition (alternative to prompt-based delegation)
- `can_use_tool` → custom permission callbacks (e.g., block writes outside staging dir)

---

## Agent Toolbox Roadmap (Discussed, Not Yet Built)

| Agent | Purpose | Status |
|---|---|---|
| `pdf_sourcer_agent.py` | Find & download missing PDFs | ✅ BUILT |
| `pipeline_runner_agent.py` | Batch-process PDFs through extract→enrich→synthesize→DOCX | Planned |
| `db_title_fixer_agent.py` | Fix page-number titles in DB using actual PDF content | Planned |
| `vc_citation_resolver_agent.py` | Match 27 unresolved VC citation strings to DB records | Planned |
| `ite_pipeline` skill | Bake project conventions into a Cowork skill | Planned |

**Best use of ClaudeSDKClient:** Pipeline Runner (needs session continuity across 146+ articles)
**Best use of output_format:** All agents (already in sourcer)

---

## Flags Inherited + Updated

### CRITICAL
- **FLAG 31:** 87 current codon PDFs misclassified — ITE-linked but not VC-cited. Must be re-tiered as `local_lite`.
- **FLAG 32:** 266 VC-cited articles have no PDF. Overnight batch is addressing this. (~4 nights to reach 100 sourced)
- **FLAG 33:** ART-ID rename (`nnn_XXXX`) not yet implemented.

### HIGH
- **FLAG 34:** 27 VC citation strings have no DB match.
- **FLAG 35:** QID format mismatch — only 75/229 resolve.
- **FLAG 44:** `clinical_guidelines` folder in OneDrive — causes permission locks. Workaround: `icacls /reset /T`.
- **FLAG 45:** DB title quality — many records have page numbers instead of real titles.
- **FLAG 46 [NEW]:** 10 downloaded PDFs sitting in `_sourced_staging/` — not yet moved to library. Review content, then move to `00_non-codon/` or `02_codon/` as appropriate.
- **FLAG 47 [NEW]:** Cookie refresh — `aafp_cookies.txt` needs re-export every ~72h. Overnight batch will report `cookies_expired` if stale.

### MEDIUM
- **FLAG 36:** ~~86 new AFP articles not in DB~~ Partially resolved.
- **FLAG 39:** Empty subfolders (`has_extraction/`, `needs_review/`, `unexamined/`) — can be deleted.
- **FLAG 40:** 14 orphaned pipeline outputs under old slugified filenames.

### LOW / DEFERRED
- FLAGS 1, 13, 15, 27, 28, 29, 30, 37 — unchanged from previous BATON.

---

## Key File Locations

### Agent Toolbox
```
claude_knowledge/agents/
  ├── pdf_sourcer_agent.py         Main sourcer script
  ├── pdf_sourcer_results.json     Cumulative results log
  ├── pdf_sourcer_manifest.json    Last dry-run manifest
  ├── aafp_cookies.txt             AAFP session cookies
  └── import_asyncio.py            SDK template
```

### Staging Folder (10 PDFs waiting for review)
```
clinical_guidelines/01_pdf_guideline_library/00_non-codon/_sourced_staging/
  └── 10 verified PDFs (see table above)
```

### Database
```
abfm_prep/02_ite_intelligence/db/ite_intelligence.db
  ├── articles:      1,547 rows (unchanged)
  ├── questions:     1,189 rows
  └── qid_art_xref:  1,818 rows
```

### Scheduled Task
```
C:\Users\mpsch\Documents\Claude\Scheduled\pdf-sourcer-overnight\SKILL.md
  Schedule: every night at 1:09 AM
  Command:  python pdf_sourcer_agent.py --all-missing --batch-size 25 --yes --model sonnet
```

---

## Next Session Candidates

1. **Process new goldmine of skills/code** (user flagged at session end — high priority)
2. **Move 10 staged PDFs to library** — review and classify (FLAG 46)
3. **Build Pipeline Runner agent** — batch-process 146-article backlog in `00_non-codon/`
4. **Build ite-pipeline Cowork skill** — bake project conventions into reusable skill
5. **Re-tier 87 misclassified PDFs** (FLAG 31)
6. **Fix 27 unmatched VC citation strings** (FLAG 34)

---

## Design Principles (Unchanged)

1. Fix the data, not the code.
2. The VC outline is the primary gate.
3. The ART-ID must carry tier information (post-migration).
4. Simplest reliable path. Always.
5. No files moved or renamed until the full migration plan is written and tested on a copy.

---

*BATON generated March 21, 2026, Session 1.*

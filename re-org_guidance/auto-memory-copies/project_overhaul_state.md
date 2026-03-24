---
name: project_overhaul_state
description: PROJECT_OVERHAUL current state - Agent SDK integration, PDF Sourcer built, overnight batch running, claude_knowledge overhaul planned
type: project
---

**Project:** ABFM Knowledge Base & Extraction Pipeline (claude_knowledge directory on user's Windows desktop)

**Current Phase:** Major re-org / PROJECT_OVERHAUL. Two tracks:
1. Agent SDK toolbox — building autonomous agents for pipeline tasks
2. claude_knowledge directory overhaul — streamlining into a learning engine

**Latest Session (March 21, 2026):**
- Claude Agent SDK integrated (Python: `claude-agent-sdk` package)
- `pdf_sourcer_agent.py` built and validated — downloads missing AFP articles
- All 10 known-missing articles successfully downloaded to `_sourced_staging/`
- Overnight batch scheduled: 25 articles/night at 1:09 AM, targeting 100 total
- Agent toolbox started at `claude_knowledge/agents/`

**Key Numbers:**
- DB: 1,547 articles, 1,189 questions, 1,818 QID-article pairs
- PDFs: 216 in library (146 codon-named, 70 non-codon)
- Intelligence 2.0: Layers 1 (ICD-10), 3 (Pathways), 4a (Trends) complete. Layer 2 (PubMed) not started
- 87 misclassified codon PDFs (FLAG 31), 266 VC-cited articles without PDFs (FLAG 32)

**Critical Flags:** 31 (misclassified codons), 32 (missing VC PDFs), 33 (ART-ID rename pending), 34 (27 unmatched VC citations), 35 (QID format mismatch), 45 (DB title quality), 46 (10 staged PDFs), 47 (cookie refresh)

**Why:** The project extends beyond exam prep into clinical decision support. The DB is the source of truth. Derivatives (JSONs, DOCXs) are disposable. Pre-compute everything deterministic at ingest.

**How to apply:** Always check the active BATON for current state. The MASTER_MAP.html shows the full pipeline architecture (7 modules: 0, F, A, B, C, D, E). Agent toolbox is the current growth edge.

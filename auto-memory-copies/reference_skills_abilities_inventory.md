---
name: reference_skills_abilities_inventory
description: skills_abilities/ folder contents — ITE data context skill, PDF sourcer agent, SDK reference files, API primer, Apify actor source
type: reference
---

## skills_abilities/ — Contents Inventory

### SDK Reference Files (17 files)
- `01_Agent SDK overview.txt` through `17_agent_sdk_reference.txt`
- Notebooks: `01_The_chief_of_staff_agent.ipynb`, `09_programmatic_tool_calling_ptc.ipynb`, `11_tool_search_with_embeddings.ipynb`
- `API_primer.md` — Claude API quick reference

### agents/
- `pdf_sourcer_agent.py` — primary PDF sourcing agent (Strategy 0 codon-first)
- `match_afp.py` — AFP article matcher
- `run_pdf_sourcer.bat` — Windows launcher
- `pdf_sourcer_results.json` — output log
- `aafp_cookies.txt` — auth cookies

### apify-actors/ (moved from root 2026-04-03)
- `citation_crawler/` — deployed PlaywrightCrawler actor
  - Actor ID: `rh50nQRP7BupbUF64` (`mpsch1~citation-crawler`)
  - Build: 0.3.1 (deployed ✅)
  - Purpose: follows citation URLs to source clinical guideline PDFs

### ite-data-context-skill/
- Domain skill for ITE DB queries (stale — needs AAFP update as of BATON 022)

**How to apply:** Reference when looking for agent scripts, SDK docs, or the Apify actor source. `skills_abilities/agents/` = local Python agents; `skills_abilities/apify-actors/` = cloud-deployed actors.

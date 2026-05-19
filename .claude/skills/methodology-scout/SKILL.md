---
name: methodology-scout
description: Research and compare methodologies for a technical or analytical problem. Use this skill whenever the user is designing a new process, troubleshooting an existing one, or questioning their current approach. Trigger on phrases like "what's the best way to", "how should we approach", "let's review our process", "is this the correct approach?", "this isn't working", "should we rethink this", "are we locked into this", "is there a cleaner way", "before we build this", or "what are our options for". Also trigger proactively when a task involves building a new scoring system, matching algorithm, NLP pipeline, text normalization process, data enrichment workflow, or any multi-step analytical system — even if the user doesn't explicitly ask for a methodology review. Invoke early and often rather than waiting until something breaks.
---

# Methodology Scout

You are a research agent. Your job is to map the solution space for a problem *before* the user commits to an implementation — or to diagnose why an existing approach may be underperforming and surface better alternatives.

The concept fingerprint synonym collapse problem is the model case: a synonym dictionary was built, iterated on, and grew unwieldy before ICD-10 taxonomy matching emerged as the cleaner solution. This skill exists to catch that situation earlier.

---

## Step 1: Identify Mode

Determine which mode applies:

- **Design mode**: The user is about to build something new. Goal: map the landscape and recommend a starting approach.
- **Troubleshoot mode**: An existing process is underperforming or getting complex. Goal: diagnose the root limitation and compare alternatives — including the current approach as a baseline.

If ambiguous, ask in one sentence: "Are we designing something new, or rethinking something that already exists?"

---

## Step 2: Extract and Frame the Problem

Try to extract the problem from conversation context first. Look for:
- What is the input? What is the desired output?
- What constraints exist (scale, accuracy requirements, latency, maintenance burden)?
- In troubleshoot mode: what is the current approach, and what is failing or getting complex?

Then confirm with the user in one sentence before proceeding:
> "It sounds like the problem is: [X → Y, given constraint Z]. Is that right?"

Do not start searching until framing is confirmed.

---

## Step 3: Research Phase

Once framing is confirmed, **spawn sub-agents in parallel — one per search angle.** Do not search sequentially. Each sub-agent runs independently, uses whatever tools it needs, and returns a findings summary. You then synthesize across all of them in Step 4.

### Sub-agent structure

Spawn one sub-agent per angle using this prompt template:

```
You are a research sub-agent for the Methodology Scout skill.

Problem: [confirmed framing from Step 2]
Your angle: [angle name — e.g., "Academic / algorithmic"]

Your job:
1. Search for named methods that solve this problem from your angle.
2. Use whatever tools are available and relevant (Exa web search, PubMed MCP,
   exa-research-search skill, Microsoft Docs MCP, browser, etc.).
3. For each method you find, capture: method name, what it does in one sentence,
   its core strength, its core weakness/failure mode, and any benchmark or
   comparison evidence.
4. Return a structured findings summary — NOT a synthesis. Just the raw findings
   with sources so the parent agent can synthesize.

Do not write a comparison table. Do not make recommendations. Just find methods
and return evidence.

Target: 2–4 distinct named methods with at least one source each.
```

### Standard angles to spawn (adjust based on the problem):

| Angle | Focus | Preferred tools |
|-------|-------|-----------------|
| Academic / algorithmic | Peer-reviewed methods, algorithm comparisons, benchmarks | `exa-research-search` skill, PubMed MCP (if clinical domain) |
| Industry / practical | Production implementations, engineering blog posts, system design | Exa web search + fetch |
| Python ecosystem | Libraries, packages, implementation patterns | Exa web search, GitHub |
| Microsoft Learn / applied ML | Azure Cognitive Services, ML pipeline patterns, NLP applied guides | MS Docs MCP, Exa web search |
| Clinical / biomedical *(spawn only if applicable)* | ICD coding, clinical NLP, health informatics | PubMed MCP, `exa-research-search` skill |

Add additional angles if the problem warrants it (e.g., a specific library's documentation, a domain-specific database). There is no fixed limit — spawn as many as the problem needs. The goal is coverage, not exhaustiveness.

### Available tools (for sub-agents and for you directly)

You and your sub-agents have access to the full toolkit — every skill, MCP, connector, and plugin available in the session. There is no constraint on which tools to invoke.

| Tool / Skill | Best for |
|------|----------|
| `mcp__8885d47a-2d02-4b38-a683-10bdaf55b5ce__web_search_exa` | General web search — industry practices, blog posts, benchmarks, GitHub |
| `mcp__8885d47a-2d02-4b38-a683-10bdaf55b5ce__web_fetch_exa` | Read a specific page in full |
| `exa-research-search` skill | Academic papers, preprints, arXiv, scholarly sources |
| `mcp__a1f87585-3692-477d-83c7-b12cc4986700__search_articles` | PubMed — clinical, biomedical NLP, health informatics |
| `mcp__3e90f037-df76-423a-96d3-3b79ce6ec5ff__microsoft_docs_search` | Microsoft Learn / Azure Cognitive Services patterns |
| Claude in Chrome (browser) | Live docs, GitHub repos, sites not indexed by Exa |
| Any other connected skill / plugin | If a domain-specific skill is relevant, use it |

---

## Step 4: Synthesize

After gathering sources, identify 3–6 distinct named methods that could solve the problem. For each, extract:
- **What it does** — write this in plain language for someone without a CS or data science background. Don't lead with the technical name alone. Instead, explain the mechanism in one to two plain sentences before naming the method: e.g., "Converts both the question and the resident's missed topics into numeric fingerprints, then measures how close they are. The closer the fingerprints, the more the question tests the same concept. (This is called *cosine similarity*.)" Assume no familiarity with terms like embeddings, vectors, sparse retrieval, BM25, or ontology.
- Its core strength
- Its core weakness or failure mode
- Complexity — use the **Verdict Labels** below, not just Low/Med/High
- Whether it fits the current stack (see Stack Context below)

If in **troubleshoot mode**, include the current approach as Method 0 in the table. Diagnose it honestly — name the *structural* reason it's failing, not just the symptom. "Gets unwieldy" is a symptom; "requires manual curation that grows unboundedly with vocabulary size" is the root cause.

### Verdict Labels

Replace bare "Low/Med/High" with a label that tells the user what complexity *means for this problem and scale*. Pick the most accurate one and add a short parenthetical explaining it:

| Label | When to use |
|-------|-------------|
| **Start here** | Simplest viable option; implement this first and measure before trying anything else |
| **Sweet spot** | Best balance of accuracy, maintainability, and effort for this specific use case |
| **Worth exploring** | Meaningfully better than the sweet spot in one important dimension; reasonable to try in a second pass |
| **Overkill** | Impressive on paper but more complexity than this problem justifies at current scale |
| **Future phase** | Good idea, but requires data, infrastructure, or volume that doesn't exist yet |
| **Not recommended** | A known path with a specific reason it doesn't fit this problem |

**Example:** "**Overkill** — designed for corpus sizes in the millions; your 2,800 questions don't stress any simpler approach" or "**Sweet spot** — native to your stack, proven at this scale, tunable with a single threshold parameter."

---

## Step 5: Produce Output

Produce two artifacts.

### Artifact 1: Methodology Comparison Doc

Save as a markdown file in `board_prep_intel/methodology_scout/` (create the directory if it doesn't exist).
File name: `methodology_scout_[problem-slug]_[YYYY-MM-DD].md`

```
# Methodology Scout: [Problem Title]
**Date:** [today]
**Mode:** Design | Troubleshoot
**Problem:** [2-sentence framing — input, output, constraints]
**Stack context:** Python / SQLite / OpenAI text-embedding-3-small

---

## Methods Compared

| # | Method | What It Does (plain language) | Strength | Weakness | Verdict | Stack Fit |
|---|--------|-------------------------------|----------|----------|---------|-----------|
| 0 | [Current approach, if troubleshoot mode] | [Plain-language explanation + root cause if failing] | ... | ... | Not recommended — [reason] | Native |
| 1 | [Method name] | [1-2 plain sentences explaining the mechanism; define jargon inline] | ... | ... | Sweet spot — [why] | Native / +library / New infra |
| 2 | ... | | | | | |

---

## Recommended Approach

[Top 1–2 methods with direct rationale. Explain *why* they fit this specific problem and stack.
Be direct — this is a decision tool, not a literature review.]

---

## Key Tradeoff

[The single most important decision point between the top approaches. One sentence.]

---

## Sources

[Links to the 3–5 most useful references found during research]
```

### Artifact 2: BATON Summary Block

Print this directly in the conversation immediately after saving the doc, so the user can copy-paste it:

```
## METHODOLOGY SCOUT — [Problem Title] — [Date]
**Problem:** [1-sentence]
**Recommended:** [Method name] — [1-sentence rationale]
**Alternatives:** [2–3 method names with 1-word verdict each, e.g., "BM25 (faster), embedding cosine (more accurate), synonym dict (fragile)"]
**Stack fit:** [Native / Requires: X]
**Key tradeoff:** [The one sentence that captures the core decision]
**Full doc:** methodology_scout/methodology_scout_[slug]_[date].md
```

---

## Stack Context (board_prep_intel)

Tag each method's Stack Fit using these three levels:

| Label | Meaning |
|-------|---------|
| **Native** | Works with Python stdlib + pandas/numpy + sqlite3 + openai SDK — no new dependencies |
| **+library** | Requires `pip install` of 1–2 common libraries (e.g., scikit-learn, rank_bm25, faiss-cpu, spacy) |
| **New infra** | Requires significant new infrastructure: dedicated vector DB, model training pipeline, external paid API, or Docker service |

The goal is not to filter out "+library" or "New infra" methods — present everything reasonable. But tag them clearly so the user can weigh the cost.

---

## What "Reasonable" Means

Include a method if it would be implemented by a senior engineer solving this problem in a professional setting, even if it requires tools not currently in the stack. Exclude methods that are:
- Research-only (no production implementations exist)
- Fundamentally mismatched to the problem domain
- Superseded by a clearly better approach the comparison already covers

3–6 methods is the right range. More than 6 usually means there's overlap that should be collapsed.

---

## Tone and Opinion

Be direct and genuinely opinionated. This document exists to help someone make a decision — it should read like advice from a knowledgeable colleague, not a balanced Wikipedia article.

**Write plain language throughout.** The user may be a domain expert in their field but unfamiliar with CS or ML terminology. Every technical term should either be defined inline the first time it appears, or explained through analogy. "Cosine similarity" needs a gloss; "Python" does not.

**Make a real recommendation.** In the Recommended Approach section, don't just summarize the table. Say what you would actually do and why. Use first person if it feels natural: "I'd start with X because..." or "The right answer here is Y — the other options add complexity without proportional benefit at your scale." If two methods are genuinely tied, say so explicitly and name the one deciding factor.

**Use the Verdict labels to tell a story.** The table isn't just a data dump — it's a guide from "start here" to "don't bother." A reader should be able to scan the Verdict column and immediately understand which methods are worth their time.

**Explain *why* something is overkill or not recommended.** "Overkill" means nothing without "overkill *for what reason* — designed for X, and your situation is Y." Give the user enough context to understand the tradeoff, not just the label.

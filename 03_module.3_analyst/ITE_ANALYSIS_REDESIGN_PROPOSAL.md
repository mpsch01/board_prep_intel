# ITE Analysis Redesign Proposal
*Prepared after audit of ite_analyzer_v3.py + ite_report_builder_v2.js + 2024/2025 ABFM ITE Score Results Handbooks*
*Date: 2026-04-10*

---

## Part 1: What the Handbooks Teach Us (Psychometric Ground Rules)

Before changing anything, the ABFM handbooks establish several hard constraints that should drive the redesign.

### The Score Scale
- 200–800 scale, MPS = 380
- Scoring uses the dichotomous **Rasch model**, equated to the FMCE scale (FMC-Scale) using ~40 shared anchor items
- 2024: 194 scored questions (6 deleted: 5 content, 1 psychometric)
- 2025: 191 scored questions (9 deleted: all content, 0 psychometric)

### The SEM — The Most Important Number Nobody Uses
The SEM for the ITE is approximately **38 points**.
- ±1 SEM = 68% confidence interval around the observed score
- ±2 SEM (±76 points) = 95% CI

**What this means in practice:** A resident scoring 400 has a "true ability" range of roughly 362–438 at the 68% level. The ABFM's own guidance says: *"Do not rely heavily on sub scores. ITE sub scores are not sufficiently precise to reliably confirm knowledge deficiencies within a content area."*

Our current report treats subscores as definitive findings. This is misaligned with ABFM's design intent. Subscores should generate hypotheses, not diagnoses.

### Score Interpretation Anchors (from ABFM)
| Score Range | ABFM Interpretation |
|-------------|---------------------|
| < 380 | Below MPS — needs attention |
| 380 | ~50–85% FMCE pass probability (depends on PGY + months remaining) |
| 380–440 | On track, progressing trajectory |
| 440+ | "Very reassuring" — very good probability of passing FMCE |

### Expected Year-over-Year Progression
- PGY1 → PGY2: **+40–60 points** (biggest jump)
- PGY2 → PGY3: **+25–35 points**
- PGY3 → 440+: strong FMCE pass signal

### National Means (both years)
| PGY | 2024 Mean (SD) | 2025 Mean (SD) | Delta |
|-----|---------------|---------------|-------|
| PGY1 | 414.1 (77.8) | 389.3 (76.0) | **-24.8** |
| PGY2 | 462.2 (76.3) | 443.4 (77.4) | **-18.8** |
| PGY3 | 494.0 (77.5) | 473.6 (78.1) | **-20.4** |
| Total | 455.5 (84.0) | 434.0 (84.7) | **-21.5** |

The 2025 exam was ~20 points harder across all PGY levels. This is exam-specific, not resident regression. A resident scoring 440 in 2025 is performing better relative to peers than a 440 in 2024.

### 2025 Format Change — Item Difficulty Now Visible
In 2025, ABFM changed the item performance report: questions are now **organized by difficulty (0–1000 scale)** rather than by sequential question number. This is a new source of data our pipeline doesn't currently use.

### The Bayesian Score Predictor (BSP)
- Available at: https://rtm.theabfm.org/bayesian/predictor
- Takes: licensing exam score (USMLE/COMLEX) + ITE score by PGY → outputs probability of passing FMCE
- Key insight: A PGY2 scoring 350 doesn't mean failure — the BSP shows the probability pathway forward

---

## Part 2: Current Pipeline Audit — What's Good, What's Weak

### What's Working Well (Keep)
1. **ite_parser.py color-coded item extraction** — reading green/red RGB to identify correct/incorrect items is solid. Handles COMPOUND_HEADERS (Psychiatric/Behavioral). Keep as-is.
2. **3-tier practice question engine** — direct ART-ID match → ICD-10 sibling → vector similarity. This is the right architecture. Keep.
3. **Blueprint + body system breakdown** — correctly mirrors ABFM's two-view structure (Figure 1a/1b). Keep.
4. **Longitudinal delta concept** — the idea of showing score trajectory is exactly right. Fix the edge cases, don't redesign it.
5. **Two-file output design** — analysis DOCX + exam version (no answers). Keep this.
6. **ICD-10 weakness map** — maps missed items → ICD-10 codes → knowledge gap clusters. This is genuinely differentiating capability ABFM doesn't provide.

### What's Weak (Fix)
1. **Subscores treated as definitive** — the report presents blueprint/body system scores without SEM context. ABFM explicitly says not to over-interpret these.
2. **DEFERRED-YOY-ROBUSTNESS** — longitudinal_delta() has edge cases around sparse temporal data and month-by-month aggregation that can produce misleading trends.
3. **Reference file is hardcoded to 2025** — `abfm_reference_2025.json` filename is hardcoded. If we run the analyzer on a 2024 exam, it uses 2025 national means. Wrong.
4. **SEM not used analytically** — we display it but never use it to flag "this subscore has wide error bars — don't act on it."
5. **AAFP concept_tags excluded from clustering** — the AAFP bank (1,221 questions, concept_tags 100% filled) is not feeding concept_clustering. This is noted as "future-proofing" in v3 but it's been sitting there for a while.

### What's Missing (Add)
1. **Article currency flags** — the `article_currency` table (1,985 rows) knows which guidelines are `updated`, `check_needed`, or `not_indexed`. The reading list never mentions if a recommended article is potentially superseded. This is a clinical safety issue.
2. **Score interpretation band** — we compute the score but never say "this places you in the 'needs monitoring' zone" in plain language.
3. **National percentile estimate** — national mean + SD is in the reference JSON. A z-score → percentile is a one-liner. Residents and program directors understand percentiles better than scaled scores.
4. **Item difficulty stratification** — for 2025+ exams, item difficulty (0–1000) is on the PDF. "You missed 8 easy items and 3 hard items" has completely different clinical significance than "you missed 11 items."
5. **Expected trajectory framing** — "Based on your PGY2 score of 430, you'd need to gain ~10-40 points to reach the 440 confidence threshold by PGY3" frames the gap as actionable, not alarming.

---

## Part 3: Proposed Redesign — Section by Section

The current 13-section report is long and ordered by analysis type, not by what a program director actually needs to know. The redesign reorders around **clinical decision flow**: Where are they → What are they missing → How do they fix it.

### New Output Structure (3 Parts, ~10-12 pages)

---

**PART 1: WHERE YOU STAND** *(pp. 1–3)*

**Section 1 — Score Interpretation**
- Overall scaled score
- Score band label (plain language): `Below MPS` / `Monitoring Zone` / `On Track` / `Strong`
- National context: percentile estimate (z-score vs national mean for their PGY)
- Expected trajectory: distance from 440 threshold + expected PGY-by-PGY gain
- SEM-based honest statement: "True ability range (68%): XXX–XXX"
- Note on 2025 national mean drop (if analyzing 2025 exam): adjusted interpretation

**Section 2 — Blueprint + Body System Performance**
- Current two-column layout (keep the visual)
- ADD: ± SEM range displayed on each row
- ADD: reliability flag on any subtest with SE > 50: *"Wide confidence interval — use to generate hypotheses, not confirm deficits"* (this is literally what ABFM says)
- ADD: highlight which blueprint category has the most exam questions → "This category drives your score most"

**Section 3 — Year-over-Year Trajectory** *(if multi-year data available)*
- Keep current longitudinal delta concept
- FIX: robustness for sparse data (DEFERRED-YOY-ROBUSTNESS)
- ADD: national cohort trajectory for context ("National PGY1→PGY2 gain is +48 points; yours was ___")
- If single year: show PGY national mean for their year as the sole reference point

---

**PART 2: WHAT YOU MISSED** *(pp. 4–6)*

**Section 4 — Item Difficulty Breakdown** *(2025+ exams only)*
- If difficulty data available: stratify missed items into Easy / Medium / Hard buckets
- Easy misses (difficulty 0–300): pure knowledge gaps — highest return on study time
- Medium misses (300–700): mixed knowledge + test-taking
- Hard misses (700–1000): not clinically concerning, expected pattern
- If difficulty data NOT available (2024 or older): skip this section gracefully

**Section 5 — Concept Clustering**
- Keep current cluster analysis
- FIX: include AAFP concept_tags in the clustering, not just ITE questions
- This significantly increases the signal — AAFP questions tagged with concept_tags 100%
- Surface: top 3–5 concept clusters where performance was weakest

**Section 6 — ICD-10 Weakness Map**
- Keep current approach (map missed items → ICD-10 clusters)
- This is genuinely differentiating. Keep.
- Minor: add "missed easy items in this ICD-10 cluster" flag if difficulty data available

---

**PART 3: HOW TO FIX IT** *(pp. 7–10)*

**Section 7 — Yield-Weighted Priorities**
- Keep current approach (high-yield intersection of missed items + blueprint weight)
- ADD: article currency flag on recommended articles
  - `[UPDATED]` — guideline has a newer version; read the latest
  - `[CHECK NEEDED]` — currency status uncertain; verify before using as study source
  - `[NOT INDEXED]` — may be older/inaccessible; de-prioritize slightly

**Section 8 — Clinical Pathway Gaps**
- Keep current pathway gap map
- Consider: show which clinical_pathways entries are linked to the most frequently tested ICD-10 codes

**Section 9 — Targeted Reading List**
- Keep current reading list
- ADD: article_currency status badge on every article
- ADD: explicit note when an article is `updated` or `check_needed`
- This is where article_currency has its highest clinical impact

**Section 10 — Practice Questions**
- Keep current two-bank design (ITE + AAFP)
- Keep the two-table layout (single-dim + cross-dim)

---

## Part 4: Implementation Tiers

### Tier 1 — Immediately Buildable (DB data only, no parser changes)
All of these use existing data already in ite_intelligence.db:

1. Score band labels + plain-language interpretation
2. National percentile estimate (z-score from reference JSON)
3. Expected trajectory statement (distance from 440, expected gain)
4. SEM-based reliability flags on subscores
5. article_currency status flags in reading list + article sections
6. AAFP concept_tags in concept clustering
7. Dynamic reference year lookup (not hardcoded 2025)
8. National cohort trajectory framing in YoY section
9. Fix DEFERRED-YOY-ROBUSTNESS

### Tier 2 — Requires ite_parser.py Changes
10. Item difficulty extraction — parse the 2025+ PDF difficulty layout (items organized 0–1000 by row)
    - New field: `item_difficulty` dict in the parse output
    - Graceful fallback: if difficulty data not present (pre-2025), skip Section 4

### Tier 3 — Future / Infrastructure Required
11. BSP probability integration — ABFM's BSP is web-only (no API documented). Could be scraped or replicated from published research, but not today.
12. COMLEX/USMLE score integration — would require intake form data not currently captured.

---

## Part 5: Summary of Recommendation

The current pipeline is mature and well-structured. The redesign is **not a rebuild** — it's:
- A reorder (around clinical decision flow, not analysis type)
- Four targeted additions (score band, percentile, article_currency, SE reliability flags)
- One significant fix (AAFP concept clustering)
- One new parser capability (item difficulty, 2025+ only)
- Two robustness fixes (YoY edge cases, reference year dynamic lookup)

The biggest win for clinical utility is the **article_currency integration** — telling a program director "this guideline has been superseded" when it appears in the reading list is the kind of thing that makes this tool feel like it was built by a physician, not a test-prep company.

The second biggest win is the **plain-language score interpretation band** — most residents and program directors don't know that 380 means "50% chance of passing right now" or that 440 is the meaningful threshold. We know this. We should say it.

---

*This is a proposal, not an implementation plan. Nothing changes until Mikey reviews and approves.*

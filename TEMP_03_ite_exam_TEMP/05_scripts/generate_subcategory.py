#!/usr/bin/env python3
"""
generate_subcategory.py

Assigns a clinical Subcategory to every ITE question using the full
four-layer context:
  1. Question stem (clinical vignette)
  2. Answer choices  (embedded in Full Text from QA file)
  3. Explanation     (Answer Explanation from QA file)
  4. Clinical reference (Ref: citation at end of explanation)

QA source (Updated_QA_Categories.xlsx) covers 2020-2024.
2025 questions fall back to stem + enriched explanation only.

Subcategory Taxonomy (question-action / clinical skill type):
  Pharmacology     — drug selection, mechanism, dosing, interactions, adverse effects
  Diagnosis        — most likely diagnosis, identifying condition
  Workup           — which test/imaging to order, initial evaluation
  Screening        — who/when to screen, screening interval/recommendation
  Treatment        — treatment choice, therapy selection (non-drug emphasis)
  Management       — next step in management, overall plan
  Prevention       — vaccines, prophylaxis, risk-reduction counseling
  Counseling       — patient education, lifestyle, anticipatory guidance
  Interpretation   — classify/stage, interpret findings, apply criteria
  Prognosis/Risk   — outcomes, risk factors, complications, prognosis
  Pathophysiology  — mechanism, cause of finding, why something occurs

Output:
  subcategory_labels.csv   — 1200 rows: QuestionID, ExamYear, Subcategory,
                             Subcat_Source, Subcat_Confidence, Reference
"""

import pandas as pd
import re
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ITE_BASE  = Path(__file__).resolve().parents[1]
PIPE_BASE = ITE_BASE.parent / "ite_pipeline/03_database"

SRC_ENRICHED = ITE_BASE / "03_database/ABFM_ITE_Enriched.xlsx"
SRC_QA       = PIPE_BASE / "Updated_QA_Categories.xlsx"
OUT_DIR      = ITE_BASE / "03_database"
RAW_DIR      = ITE_BASE / "03_database/raw_files"

RAW_DIR.mkdir(parents=True, exist_ok=True)

OUT_LABELS  = OUT_DIR / "subcategory_labels.csv"
OUT_REVIEW  = RAW_DIR / "subcategory_low_confidence.csv"


# ── Reference extraction ───────────────────────────────────────────────────────
def extract_reference(explanation: str) -> str:
    """
    Pull the citation(s) from an explanation block.

    Handles two formats:
      2020-2023:  "Ref: Author A, Author B: Title. Journal Year;Vol(N):pp."
      2024+:      "Reference\\n\\nAuthor A, Author B. Title. Journal. Year;..."
    """
    text = str(explanation)

    # Format 1 — inline "Ref:" prefix (2020-2023)
    m = re.search(r'Ref(?:erence)?s?:\s*(.+?)(?:\n\d{1,2}\s*$|\Z)', text,
                  re.DOTALL | re.IGNORECASE)
    if m:
        ref = m.group(1).strip()
        ref = re.sub(r'\s*\n\d{1,2}\s*$', '', ref).strip()
        return ' '.join(ref.split())

    # Format 2 — standalone "Reference" header followed by citation on next line(s) (2024)
    m = re.search(r'Reference\s*\n+\s*(.+?)(?:\n\d{1,2}\s*$|\Z)', text,
                  re.DOTALL | re.IGNORECASE)
    if m:
        ref = m.group(1).strip()
        ref = re.sub(r'\s*\n\d{1,2}\s*$', '', ref).strip()
        return ' '.join(ref.split())

    return ''


# ── Context builder ────────────────────────────────────────────────────────────
def build_context(stem: str, full_text: str, explanation: str, reference: str) -> str:
    """Combine all four layers into one classification string."""
    parts = [
        str(stem).strip(),
        str(full_text).strip(),
        str(explanation).strip(),
        str(reference).strip(),
    ]
    return ' '.join(p for p in parts if p and p.lower() not in ('nan', ''))


# ── Subcategory taxonomy + pattern rules ──────────────────────────────────────
#
# Evaluated in ORDER — first match wins.
# Patterns written to match the question clause (final sentence of stem)
# AND the full context block for disambiguation.

TAXONOMY = [

    # ── Pharmacology ──────────────────────────────────────────────────────────
    # Drug-selection, dosing, mechanism, side effects, interactions
    ("Pharmacology", [
        # Question asks about a specific drug or medication
        r"which (?:one )?(?:of the following )?(?:medication|drug|agent|antibiotic|antifungal|"
        r"antiviral|vaccine|supplement|vitamin|hormone|steroid|opioid|nsaid|statin|"
        r"ace inhibitor|beta.?blocker|diuretic|antidepressant|antipsychotic|"
        r"anticoagulant|antihypertensive|antidiabetic|insulin)",
        # Mechanism / adverse effect / interaction
        r"mechanism of action|adverse effect|side effect|drug interaction|"
        r"contraindicated|drug.of.choice|first.line agent|most appropriate (?:medication|drug|agent|antibiotic)",
        # Prescribe / initiate / discontinue a drug
        r"(?:prescribe|initiate|start|discontinue|switch|add|increase|decrease|adjust).{0,40}"
        r"(?:medication|drug|dose|therapy|antibiotic|mg\b)",
        # Dosing / pharmacokinetics
        r"dosing|pharmacokinetic|half.life|loading dose|renal.?adjust|"
        r"hepatic.?adjust|dose reduction",
        # Ref title suggests pharmacology
        r"(?:drug|medication|antibiotic|pharmacol|prescribing|formulary)",
    ]),

    # ── Screening ─────────────────────────────────────────────────────────────
    # Who to screen, which test, how often
    ("Screening", [
        r"screen(?:ing)?",
        r"(?:annual|biennial|every \d|how often|recommended interval|next mammograph|"
        r"colonoscopy|pap smear|pap test|bone density|dexa|lipid panel) .*(?:recommend|perform|order|schedule)",
        r"when (?:should|would) (?:you|this patient) (?:be screened|receive|undergo)",
        r"surveillance (?:for|after|follow)",
        r"recommended (?:for|in) (?:screening|detection|prevention of) cancer",
        r"uspstf|aafp.*screen|screen.*guideline",
    ]),

    # ── Prevention ────────────────────────────────────────────────────────────
    # Vaccines, prophylaxis, risk reduction
    ("Prevention", [
        r"vaccin(?:e|ation|ate)|immuniz",
        r"prophylax(?:is|tic)",
        r"prevent(?:ion)?(?:\s+of|\s+this|\s+future|\s+recurrence)",
        r"risk reduction|reduce (?:the )?risk|lower (?:the )?risk",
        r"chemoprophylax|post.?exposure",
        r"aspirin.*prevention|statin.*prevention",
    ]),

    # ── Counseling ───────────────────────────────────────────────────────────
    # Patient education, lifestyle advice, anticipatory guidance
    ("Counseling", [
        r"counsel(?:ing)?|advise|educate|tell (?:the )?patient|inform (?:the )?patient",
        r"patient.*education|anticipatory guidance",
        r"(?:lifestyle|diet|exercise|smoking|alcohol|substance).{0,30}(?:counsel|advise|discuss|recommend)",
        r"which.*(?:information|instruction|advice|statement).{0,20}(?:counsel|give|provide|tell|share)",
        r"what (?:should|would) you (?:tell|inform|advise|counsel|discuss)",
        r"motivational interview",
    ]),

    # ── Diagnosis ─────────────────────────────────────────────────────────────
    # Identifying the condition; most likely cause
    ("Diagnosis", [
        r"most likely (?:diagnosis|condition|cause|etiology|explanation|disorder)",
        r"best (?:explains?|accounts? for) (?:this|these|her|his|the)",
        r"consistent with which (?:one of the following|diagnosis|condition|disorder)",
        r"which (?:one of the following )?(?:condition|diagnosis|disorder|disease|syndrome) (?:best )?(?:explains?|accounts?|fits?|matches?)",
        r"what (?:is the|does the) (?:diagnosis|condition|most likely)",
        r"(?:identify|determine) (?:the )?(?:cause|etiology|diagnosis)",
        r"which (?:one of the following )?is most likely (?:causing|responsible for|contributing to)",
        r"most likely to (?:be diagnosed|have|present with|cause)",
        r"most consistent with",
    ]),

    # ── Workup ────────────────────────────────────────────────────────────────
    # Which test, imaging, lab to order; next step in evaluation
    ("Workup", [
        r"(?:best|most appropriate|initial|first|next) (?:diagnostic )?(?:test|study|imaging|laboratory|lab|work.?up|evaluation|assessment|step in (?:the )?(?:work.?up|evaluation))",
        r"which (?:one of the following )?(?:test|study|imaging|laboratory finding|lab|diagnostic)",
        r"(?:order|obtain|perform|send|check).{0,30}(?:test|study|imaging|culture|blood|urine|biopsy|biopsy|CT|MRI|ultrasound|x.ray|radiograph|echocardiogram)",
        r"most appropriate (?:next )?(?:step|action|approach).{0,20}(?:evaluat|work.?up|diagnos|determin)",
        r"(?:best|initial|appropriate) (?:approach to|evaluation of|assessment of|work.?up for)",
        r"prior to (?:surgery|procedure|treatment).{0,30}(?:order|obtain|perform)",
    ]),

    # ── Interpretation ───────────────────────────────────────────────────────
    # Classify/stage, interpret findings, apply clinical criteria
    ("Interpretation", [
        r"classif(?:y|ied|ication)|stage|staging",
        r"(?:interpret|interpretation of|explain) (?:these|the|this) (?:results?|findings?|values?|data|levels?)",
        r"according to (?:the )?(?:criteria|guidelines?|classification|definition|staging)",
        r"which (?:one of the following )?(?:criteria|finding|feature|characteristic|sign|symptom|result|value).{0,30}(?:consistent|associated|confirm|support|indicate|suggest)",
        r"what does (?:this|the) (?:finding|result|value|level|test).{0,20}(?:indicate|suggest|represent|mean)",
        r"which (?:one of the following )?(?:would|is) (?:most likely )?(?:explain|account for|be seen|be found|be present)",
        r"(?:new york heart|wells|chads|cha2ds2|frax|cage|audit|phq|gad|mmse|moca).{0,20}(?:score|criteria|classif)",
    ]),

    # ── Treatment ────────────────────────────────────────────────────────────
    # Treatment/therapy selection (non-pharmacologic or drug-agnostic context)
    ("Treatment", [
        r"(?:best|most appropriate) (?:treatment|therapy|therapeutic|intervention|approach|option|management) for",
        r"which (?:one of the following )?(?:treatment|therapy|intervention|procedure|surgery|option) (?:would|is|should)",
        r"(?:treat|therapy for|manage|surgical|non.?surgical|conservative|operative).{0,30}(?:this patient|her|his|the patient|condition|symptoms?)",
        r"first.?line (?:treatment|therapy|option)|second.?line",
        r"gold.?standard (?:treatment|therapy)|definitive (?:treatment|therapy|management)",
        r"(?:surgical|procedural|operative|interventional) (?:approach|option|management|correction|repair|removal)",
    ]),

    # ── Management ───────────────────────────────────────────────────────────
    # Broad next-step questions; overall care plan
    ("Management", [
        r"most appropriate (?:next )?(?:step|action|approach|course|plan|recommendation|management)",
        r"(?:next|best|initial|immediate) (?:step|action|management|course of action)",
        r"how (?:should|would) you (?:manage|handle|approach|address)",
        r"what (?:should|would) you (?:do|recommend|order|perform|consider) (?:next|at this time|now|for this patient)?",
        r"which (?:one of the following )?(?:would|is) (?:most )?appropriate (?:at this time|now|for|in)",
        r"which (?:one of the following )?(?:would you|should you) (?:recommend|order|advise|suggest|do|perform|obtain)",
        r"in (?:the )?management of|approach to (?:management|care)",
        r"which (?:one of the following )?(?:is|would be) (?:most )?(?:helpful|beneficial|effective|indicated) (?:for|in|at)",
        r"for (?:this|the) patient.{0,40}(?:recommend|appropriate|indicated|suggested)",
    ]),

    # ── Prognosis / Risk ─────────────────────────────────────────────────────
    # Outcomes, risk factors, complications, likelihood of events
    ("Prognosis/Risk", [
        r"prognos(?:is|tic)|surviv(?:al|e)|mortalit(?:y|ies)|morbidities?",
        r"risk factor(?:s)? (?:for|associated with)",
        r"(?:most likely to|which (?:one )?(?:of the following )?(?:is the )?)(?:complication|outcome|develop|progress|worsen|improve)",
        r"increase(?:s|d)? (?:risk|likelihood|chance) of",
        r"associated with (?:increased|higher|lower|decreased) (?:risk|mortality|morbidity|likelihood)",
        r"(?:chance|likelihood|probability|odds) of (?:survival|recurrence|progression|complication|death)",
        r"predictor(?:s)? of|prognostic (?:factor|indicator)",
    ]),

    # ── Pathophysiology ──────────────────────────────────────────────────────
    # Mechanism, cause of a finding, why something happens
    ("Pathophysiology", [
        r"pathophysiolog(?:y|ic)|mechanism",
        r"(?:why|how).{0,30}(?:occur|happen|cause|lead to|result in|develop|present)",
        r"which (?:one of the following )?(?:best )?(?:explains?|describes?|accounts? for|is responsible for) (?:this|the|her|his) (?:finding|sign|symptom|presentation|result)",
        r"(?:underlying|root) cause",
        r"mediated by|due to (?:which|the)",
    ]),
]


# ── Reference-based boost: if a subcategory pattern in the ref title ──────────
REF_BOOST = {
    "Pharmacology": r"(pharmacol|drug therapy|medication|antibiotic|prescribing|formulary|drug use)",
    "Screening":    r"(screen|detection|early.detection|preventive)",
    "Prevention":   r"(prevention|prophylax|vaccin|immuniz)",
    "Counseling":   r"(counsel|patient.education|lifestyle|behavioral)",
    "Diagnosis":    r"(diagnosis|diagnostic|clinical.presentation|classification)",
    "Workup":       r"(evaluation|assessment|work.?up|testing|laboratory)",
}


# ── Classify a single question ────────────────────────────────────────────────
def classify_question(context: str, question_clause: str, reference: str) -> tuple[str, str]:
    """
    Returns (subcategory, confidence_label).
    confidence_label: 'high' (strong pattern match on clause),
                      'medium' (full-context match),
                      'low' (reference boost only or fallback)
    """
    clause_lc  = question_clause.lower()
    context_lc = context.lower()
    ref_lc     = reference.lower()

    for subcat, patterns in TAXONOMY:
        for pat in patterns:
            if re.search(pat, clause_lc, re.IGNORECASE):
                return subcat, "high"

    for subcat, patterns in TAXONOMY:
        for pat in patterns:
            if re.search(pat, context_lc, re.IGNORECASE):
                return subcat, "medium"

    # Reference-title boost
    for subcat, pat in REF_BOOST.items():
        if re.search(pat, ref_lc, re.IGNORECASE):
            return subcat, "low"

    return "Management", "fallback"   # generic default


# ── Extract the final question clause from the stem ───────────────────────────
def get_question_clause(text: str) -> str:
    text = str(text)
    # Walk ? marks from left; grab the sentence up to each
    qmarks = [m.start() for m in re.finditer(r'\?', text)]
    for qpos in qmarks:
        start = text.rfind('\n', 0, qpos)
        start = max(0, start)
        snippet = text[start:qpos + 1].strip()
        if len(snippet) > 15:
            return snippet
    return text[-300:]   # fallback: last 300 chars


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

print("Loading enriched master...")
df_master = pd.read_excel(SRC_ENRICHED)[[
    "Question ID", "ExamYear", "QuestionStem", "Explanation"
]].rename(columns={"Question ID": "QuestionID"})
df_master["WithinYearPos"] = df_master.groupby("ExamYear").cumcount() + 1

print(f"  {len(df_master)} questions across years {sorted(df_master['ExamYear'].unique())}")

print("Loading QA source (with answer choices + references)...")
df_qa = pd.read_excel(SRC_QA)[["Year", "Answer Explanation", "Full Text"]]
df_qa = df_qa.rename(columns={"Year": "ExamYear"})
df_qa["WithinYearPos"] = df_qa.groupby("ExamYear").cumcount() + 1
df_qa["Reference"] = df_qa["Answer Explanation"].apply(extract_reference)

print(f"  {len(df_qa)} rows  |  years: {sorted(df_qa['ExamYear'].unique())}")
print(f"  References extracted: {(df_qa['Reference'] != '').sum()}")

# Merge QA into master by year + position
df = df_master.merge(
    df_qa[["ExamYear", "WithinYearPos", "Full Text", "Reference"]],
    on=["ExamYear", "WithinYearPos"],
    how="left"
)

# Fill missing fields for 2025 (no QA source)
df["Full Text"]  = df["Full Text"].fillna("")
df["Reference"]  = df["Reference"].fillna("")
df["Explanation"] = df["Explanation"].fillna("")
df["QuestionStem"] = df["QuestionStem"].fillna("")

print("\nClassifying subcategories...")
results = []
for _, row in df.iterrows():
    context = build_context(
        row["QuestionStem"],
        row["Full Text"],
        row["Explanation"],
        row["Reference"]
    )
    clause  = get_question_clause(str(row["QuestionStem"]))
    subcat, conf = classify_question(context, clause, row["Reference"])
    results.append({
        "QuestionID":        row["QuestionID"],
        "ExamYear":          row["ExamYear"],
        "Subcategory":       subcat,
        "Subcat_Source":     conf,
        "Reference":         row["Reference"],
    })

df_out = pd.DataFrame(results)

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n=== Subcategory Distribution (all 1200) ===")
counts = df_out["Subcategory"].value_counts()
for cat, n in counts.items():
    pct = n / len(df_out) * 100
    print(f"  {cat:20s}  {n:4d}  ({pct:.1f}%)")

print("\n=== Confidence Level Breakdown ===")
for conf, n in df_out["Subcat_Source"].value_counts().items():
    pct = n / len(df_out) * 100
    print(f"  {conf:12s}  {n:4d}  ({pct:.1f}%)")

print("\n=== Per-Year Subcategory Breakdown ===")
pivot = df_out.groupby(["ExamYear", "Subcategory"]).size().unstack(fill_value=0)
print(pivot.to_string())

# ── Save ──────────────────────────────────────────────────────────────────────
df_out.to_csv(OUT_LABELS, index=False)
print(f"\n  Saved: {OUT_LABELS.name}  ({len(df_out)} rows)")

low_conf = df_out[df_out["Subcat_Source"].isin(["low", "fallback"])]
low_conf.to_csv(OUT_REVIEW, index=False)
print(f"  Saved low-confidence for review: {OUT_REVIEW.name}  ({len(low_conf)} rows)")

print("\nDone.")

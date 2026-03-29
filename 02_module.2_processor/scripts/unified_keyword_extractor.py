#!/usr/bin/env python3
"""
Unified Keyword Extractor
━━━━━━━━━━━━━━━━━━━━━━━━━
Extracts clinical keywords from both ITE and AAFP question corpora using
the same TF-IDF method with clinical phrase detection. Produces directly
comparable stem_keywords columns across both tables.

Tokenizer pipeline (two phases):
  Phase 1 — Phrase extraction: multi-word clinical terms are matched first
             via PHRASE_PATTERNS and treated as atomic tokens (e.g.,
             "atrial fibrillation" scores as one term, not two).
  Phase 2 — Unigrams: remaining 3+ character alpha tokens, stopword filtered.
  Both phases feed into TF-IDF together.

Replaces:
  - backfill_keywords_2018_2019.py  (ITE, frequency-based)
  - add_keywords.py                  (ITE, frequency-based)
  - aafp_keyword_extractor.py        (AAFP, TF-IDF + bigrams)

Writes:
  ITE:  questions.stem_keywords        (overwrite)
        questions.explanation_keywords (overwrite)
        questions.all_keywords         (overwrite — union of stem + expl)
  AAFP: aafp_questions.stem_keywords        (overwrite)
        aafp_explanations.explanation_keywords (overwrite)

Each corpus uses its OWN IDF corpus — ITE IDF is computed across 1,629 ITE
questions; AAFP IDF is computed across 1,221 AAFP questions. They do not
share an IDF table. This keeps within-corpus term discrimination intact.

Run:
  python unified_keyword_extractor.py              ← both corpora (default top 12)
  python unified_keyword_extractor.py --corpus ite ← ITE only
  python unified_keyword_extractor.py --corpus aafp← AAFP only
  python unified_keyword_extractor.py --top 15     ← override top-N
  python unified_keyword_extractor.py --dry-run    ← preview, no writes
  python unified_keyword_extractor.py --stats      ← coverage report only
"""

import re
import math
import sys
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict

# ══════════════════════════════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH      = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
# ══════════════════════════════════════════════════════════════════════

# ── CLI flags ─────────────────────────────────────────────────────────
DRY_RUN = "--dry-run" in sys.argv
STATS   = "--stats"   in sys.argv

CORPUS = "both"
for i, arg in enumerate(sys.argv):
    if arg == "--corpus" and i + 1 < len(sys.argv):
        CORPUS = sys.argv[i + 1].lower()

TOP_N = 12
for i, arg in enumerate(sys.argv):
    if arg == "--top" and i + 1 < len(sys.argv):
        try:
            TOP_N = int(sys.argv[i + 1])
        except ValueError:
            pass

if CORPUS not in ("ite", "aafp", "both"):
    print(f"ERROR: --corpus must be 'ite', 'aafp', or 'both'. Got: {CORPUS}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────
# STOPWORDS
# Extended medical stopword list — general English + clinical noise
# that appears in virtually every question (adds no signal).
# Unified across both corpora.
# ─────────────────────────────────────────────────────────────────────
STOPWORDS = {
    # General English
    "a", "an", "the", "and", "or", "but", "not", "nor", "so", "yet",
    "in", "on", "at", "to", "for", "of", "with", "from", "by", "as",
    "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "shall", "must",
    "this", "that", "these", "those", "it", "its", "itself",
    "he", "she", "they", "their", "them", "we", "our", "you", "your",
    "who", "which", "what", "when", "where", "how", "why",
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "also", "both", "each", "few", "more", "most", "other", "some",
    "such", "than", "then", "very", "just", "now", "only", "same",
    "about", "above", "after", "all", "any", "because", "before",
    "between", "during", "even", "every", "following", "given", "if",
    "into", "like", "much", "per", "since", "still", "through", "too",
    "under", "up", "upon", "without", "within", "while", "already",
    "often", "never", "always", "usually", "typically", "generally",
    # Clinical filler — in nearly every question/explanation
    "patient", "patients", "year", "years", "old", "male", "female",
    "man", "woman", "child", "girl", "boy", "infant", "adult",
    "history", "presents", "presentation", "exam", "examination",
    "physical", "initial", "given", "known", "seen", "new", "well",
    "age", "first", "test", "use", "used", "using", "associated",
    "include", "includes", "including", "based", "findings", "finding",
    "result", "results", "recent", "further", "taking", "report",
    "reports", "status", "level", "levels", "current", "evaluation",
    "assessment", "show", "shows", "shown", "noted", "note", "notes",
    "appropriate", "indicate", "indicates", "indicated", "recommended",
    "consistent", "significant", "likely", "concerning", "additional",
    "increase", "increased", "decreased", "elevated", "normal",
    "abnormal", "best", "next", "management", "treatment", "therapy",
    "diagnosis", "clinical", "recommend", "concern", "prior",
    "develop", "developed", "develops", "negative", "positive",
    "mild", "moderate", "severe", "acute", "chronic", "recent",
    "cause", "causes", "caused", "due", "related", "present",
    "common", "commonly", "important", "most", "least", "high",
    "low", "poorly", "typically", "recently", "start",
    "started", "begins", "began", "undergo", "undergoes",
    "underwent", "review", "reviewed", "performed",
    "obtained", "ordered", "placed", "admitted",
    "referred", "consulted", "returned", "brought",
    # Units / abbreviations
    "via", "ref", "doi", "etal", "mg", "ml", "mcg", "mmhg",
    "ium", "ibid", "vol", "fig",
}


# ─────────────────────────────────────────────────────────────────────
# CLINICAL PHRASE PATTERNS
# Multi-word terms that lose meaning when split into unigrams.
# Matched before unigram tokenization — each match becomes one token.
# Organized by body system / drug class for maintainability.
# ─────────────────────────────────────────────────────────────────────
PHRASE_PATTERNS = [
    # ── Structural: drug classes (catch new agents automatically) ────
    r'\b[a-z]+ (?:inhibitor|antagonist|agonist|blocker|receptor|modulator)s?\b',
    r'\b[a-z]+ [a-z]+ (?:inhibitor|antagonist|agonist|blocker)s?\b',  # two-word prefix
    # ── Structural: disease naming conventions ───────────────────────
    r'\b[a-z]+-[a-z]+ (?:syndrome|disease|disorder|deficiency|failure|infection|anemia)\b',
    r'\b[a-z]+ (?:syndrome|disease|disorder|deficiency|failure|infection|anemia)\b',
    # ── Structural: treatment lines ─────────────────────────────────
    r'\b(?:first|second|third)[- ]line\b',
    # ── Structural: lab context ──────────────────────────────────────
    r'\b(?:serum|plasma|urine|blood|fasting) [a-z]{4,}\b',
    # ── Structural: risk/effect phrases ─────────────────────────────
    r'\brisk factors?\b',
    r'\badverse effects?\b',
    r'\bside effects?\b',
    # ── Cardiovascular ───────────────────────────────────────────────
    r'\batrial fibrillation\b',
    r'\bheart failure\b',
    r'\bheart rate\b',
    r'\bblood pressure\b',
    r'\bblood glucose\b',
    r'\bcoronary artery disease\b',
    r'\bacute coronary syndrome\b',
    r'\bmyocardial infarction\b',
    r'\bdeep vein thrombosis\b',
    r'\bpulmonary embolism\b',
    r'\bischemic stroke\b',
    r'\bhemorrhagic stroke\b',
    r'\btransient ischemic attack\b',
    r'\bcongestive heart failure\b',
    r'\bperipheral artery disease\b',
    r'\baortic stenosis\b',
    r'\baortic regurgitation\b',
    r'\bmitral regurgitation\b',
    r'\bmitral stenosis\b',
    r'\bcardiac tamponade\b',
    r'\bventricular tachycardia\b',
    r'\bventricular fibrillation\b',
    # ── Endocrine ────────────────────────────────────────────────────
    r'\btype [12] (?:diabetes|dm)\b',
    r'\bgestational diabetes\b',
    r'\bdiabetic ketoacidosis\b',
    r'\bhyperosmolar hyperglycemic state\b',
    r'\bblood sugar\b',
    r'\bcushing.s syndrome\b',
    r'\baddison.s disease\b',
    r'\badrenal insufficiency\b',
    r'\bprimary hyperaldosteronism\b',
    r'\bdiabetes insipidus\b',
    # ── Gastrointestinal ─────────────────────────────────────────────
    r'\bgastroesophageal reflux(?:\s+disease)?\b',
    r'\bpeptic ulcer disease\b',
    r'\binflammatory bowel disease\b',
    r'\birritable bowel syndrome\b',
    r'\bulcerative colitis\b',
    r'\bceliac disease\b',
    r'\bcirrhosis\b',
    r'\bacute pancreatitis\b',
    r'\bchronic pancreatitis\b',
    r'\bhepatic encephalopathy\b',
    # ── Renal ────────────────────────────────────────────────────────
    r'\bchronic kidney disease\b',
    r'\bacute kidney injury\b',
    r'\burinary tract infection\b',
    r'\bnephrotic syndrome\b',
    r'\bnephritic syndrome\b',
    r'\brenal artery stenosis\b',
    # ── Pulmonary ────────────────────────────────────────────────────
    r'\bupper respiratory infection\b',
    r'\bcommunity.acquired pneumonia\b',
    r'\bchronic obstructive pulmonary disease\b',
    r'\bpulmonary hypertension\b',
    r'\bpleural effusion\b',
    r'\bspontaneous pneumothorax\b',
    r'\brespiratory failure\b',
    r'\binterstitial lung disease\b',
    r'\bsleep apnea\b',
    # ── Musculoskeletal ──────────────────────────────────────────────
    r'\brheumatoid arthritis\b',
    r'\bseptic arthritis\b',
    r'\bpsoriatic arthritis\b',
    r'\bankylosing spondylitis\b',
    r'\bcarpal tunnel syndrome\b',
    r'\brotator cuff\b',
    r'\blateral epicondylitis\b',
    r'\bmedial epicondylitis\b',
    r'\blumbar stenosis\b',
    r'\bdisc herniation\b',
    r'\bosteoporosis\b',
    r'\bosteomalacia\b',
    r'\bcompartment syndrome\b',
    # ── Reproductive / OB-GYN ────────────────────────────────────────
    r'\bpolycystic ovary syndrome\b',
    r'\bgestational hypertension\b',
    r'\bpreterm labor\b',
    r'\bpreeclampsia\b',
    r'\bplacenta previa\b',
    r'\bplacental abruption\b',
    r'\bectopic pregnancy\b',
    r'\bpelvic inflammatory disease\b',
    r'\bbacterial vaginosis\b',
    r'\bendometrial cancer\b',
    r'\bovarian cancer\b',
    # ── Neurology / Psychiatry ────────────────────────────────────────
    r'\bmultiple sclerosis\b',
    r'\bparkinson.s disease\b',
    r'\balzheimer.s disease\b',
    r'\bsubarachnoid hemorrhage\b',
    r'\bintracranial hypertension\b',
    r'\bbipolar disorder\b',
    r'\banxiety disorder\b',
    r'\bpanic disorder\b',
    r'\bpost.traumatic stress disorder\b',
    r'\bsubstance use disorder\b',
    r'\bopioid use disorder\b',
    r'\balcohol use disorder\b',
    r'\battention deficit hyperactivity disorder\b',
    r'\beating disorder\b',
    r'\bborderline personality disorder\b',
    r'\bbell.s palsy\b',
    r'\btrigeminal neuralgia\b',
    r'\brestless leg syndrome\b',
    r'\bmyasthenia gravis\b',
    r'\bgullain.barre syndrome\b',
    # ── Infectious disease ────────────────────────────────────────────
    r'\bhepatitis [abc]\b',
    r'\blyme disease\b',
    r'\binfective endocarditis\b',
    r'\bcellulitis\b',
    r'\bnecrotizing fasciitis\b',
    r'\bseptic shock\b',
    r'\btoxic shock syndrome\b',
    r'\bclostridium difficile\b',
    r'\bhelicobacter pylori\b',
    r'\bchlamydia trachomatis\b',
    r'\bneisseria gonorrhoeae\b',
    # ── Oncology ─────────────────────────────────────────────────────
    r'\bcolorectal cancer\b',
    r'\bcervical cancer\b',
    r'\bbreast cancer\b',
    r'\blung cancer\b',
    r'\bprostate cancer\b',
    r'\bthyroid cancer\b',
    r'\bskin cancer\b',
    r'\bbasal cell carcinoma\b',
    r'\bsquamous cell carcinoma\b',
    r'\bmalignant melanoma\b',
    r'\bnon.hodgkin lymphoma\b',
    r'\bhodgkin lymphoma\b',
    r'\bacute myeloid leukemia\b',
    r'\bchronic myeloid leukemia\b',
    # ── Hematology / Immune ───────────────────────────────────────────
    r'\biron deficiency(?: anemia)?\b',
    r'\bvitamin b12 deficiency\b',
    r'\bfolate deficiency\b',
    r'\bsickle cell disease\b',
    r'\baplastic anemia\b',
    r'\bhemolytic anemia\b',
    r'\bimmune thrombocytopenia\b',
    r'\bvon willebrand disease\b',
    r'\bdisseminated intravascular coagulation\b',
    # ── Autoimmune ────────────────────────────────────────────────────
    r'\bsystemic lupus erythematosus\b',
    r'\blupus erythematosus\b',
    r'\bsjogren.s syndrome\b',
    r'\bsystemic sclerosis\b',
    r'\bpolymyalgia rheumatica\b',
    r'\bgiant cell arteritis\b',
    r'\bvasculitis\b',
    # ── Screening / Preventive ────────────────────────────────────────
    r'\b\w+ cancer screening\b',
    r'\bcolorectal screening\b',
    r'\bmammography screening\b',
    r'\bprevention target\b',
]

# Deduplicate patterns (in case of overlapping category entries)
PHRASE_PATTERNS = list(dict.fromkeys(PHRASE_PATTERNS))


# ─────────────────────────────────────────────────────────────────────
# TOKENIZER — phrase-aware, unigrams
# ─────────────────────────────────────────────────────────────────────
def tokenize(text: str) -> list[str]:
    """
    Two-phase tokenizer:
      Phase 1: extract multi-word clinical phrases as atomic tokens.
               Each matched phrase competes in TF-IDF as a single term.
      Phase 2: unigrams — 3+ char alpha tokens, stopword filtered.
    Both phases feed into TF-IDF together, so phrases can outrank
    their component words when they're the more specific signal.
    """
    text_lower = (text or "").lower()

    # Phase 1 — clinical phrase extraction
    # Guard: skip any phrase whose first word is a stopword
    # (prevents structural patterns from matching e.g. "of ace inhibitors")
    phrases = []
    for pattern in PHRASE_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            phrase = match.group(0).strip()
            if phrase.split()[0] not in STOPWORDS:
                phrases.append(phrase)

    # Phase 2 — unigrams
    raw      = re.findall(r"[a-zA-Z]{3,}", text_lower)
    unigrams = [t for t in raw if t not in STOPWORDS]

    return phrases + unigrams


# ─────────────────────────────────────────────────────────────────────
# TF-IDF ENGINE
# ─────────────────────────────────────────────────────────────────────
def build_tfidf(docs: list[str], top_n: int) -> list[list[str]]:
    """
    Compute TF-IDF for each document in docs.

    TF  = count(term in doc) / total_tokens_in_doc
    IDF = log((N+1) / (df+1)) + 1.0   [smoothed to avoid zero-division]

    IDF is corpus-local — computed only from the docs passed in.
    ITE and AAFP are called separately so their IDFs stay independent.

    Returns list of top_n term lists (strings only, score dropped).
    One list per document, same order as input.
    """
    N = len(docs)

    # Pass 1: tokenize all docs, build document-frequency map
    doc_token_lists: list[Counter] = []
    df: dict[str, int] = defaultdict(int)

    for doc in docs:
        tokens = tokenize(doc)
        counts = Counter(tokens)
        doc_token_lists.append(counts)
        for term in counts:
            df[term] += 1

    # Pass 2: score each doc
    results: list[list[str]] = []
    for counts in doc_token_lists:
        if not counts:
            results.append([])
            continue
        total = sum(counts.values())
        scored = []
        for term, count in counts.items():
            tf  = count / total
            idf = math.log((N + 1) / (df[term] + 1)) + 1.0
            scored.append((term, tf * idf))
        scored.sort(key=lambda x: x[1], reverse=True)
        results.append([term for term, _ in scored[:top_n]])

    return results


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str) -> None:
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
        print(f"  ✓ Added column: {table}.{column}")
    else:
        print(f"  · {table}.{column} already exists")


def merge_keywords(*lists: list[str]) -> str:
    """Union of keyword lists, deduplicated, preserving first-seen order."""
    seen, merged = set(), []
    for kw_list in lists:
        for kw in kw_list:
            k = kw.strip()
            if k and k not in seen and k not in STOPWORDS:
                seen.add(k)
                merged.append(k)
    return ", ".join(merged)


def pct(n: int, total: int) -> str:
    return f"{n / total * 100:.1f}" if total else "0"


def avg_len(conn: sqlite3.Connection, table: str, col: str) -> float:
    row = conn.execute(
        f"SELECT AVG(LENGTH({col})) FROM {table} WHERE {col} IS NOT NULL AND {col} != ''"
    ).fetchone()
    return round(row[0] or 0, 1)


# ─────────────────────────────────────────────────────────────────────
# STATS MODE
# ─────────────────────────────────────────────────────────────────────
def run_stats(conn: sqlite3.Connection) -> None:
    print("\n══ Keyword Coverage ═══════════════════════════════════════")
    checks = [
        ("questions",         "stem_keywords"),
        ("questions",         "explanation_keywords"),
        ("questions",         "all_keywords"),
        ("aafp_questions",    "stem_keywords"),
        ("aafp_explanations", "explanation_keywords"),
    ]
    for table, col in checks:
        try:
            total  = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            filled = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL AND {col} != ''"
            ).fetchone()[0]
            avg = avg_len(conn, table, col)
            print(f"  {table}.{col:<30}  {filled}/{total}  ({pct(filled, total)}%)  avg_len={avg}")
        except Exception as e:
            print(f"  {table}.{col}  — missing or error: {e}")


# ─────────────────────────────────────────────────────────────────────
# ITE CORPUS
# ─────────────────────────────────────────────────────────────────────
def run_ite(conn: sqlite3.Connection, top_n: int) -> None:
    print("\n══ ITE Corpus ══════════════════════════════════════════════")

    # Schema
    print("\nSchema check...")
    add_column_if_missing(conn, "questions", "stem_keywords")
    add_column_if_missing(conn, "questions", "explanation_keywords")
    add_column_if_missing(conn, "questions", "all_keywords")
    conn.commit()

    # Load stems
    print("\nLoading stems...")
    q_rows = conn.execute(
        "SELECT qid, question_text FROM questions ORDER BY qid"
    ).fetchall()
    q_qids = [r[0] for r in q_rows]
    stems  = [r[1] or "" for r in q_rows]
    print(f"  {len(stems)} stems loaded")

    # Load explanations
    print("Loading explanations...")
    e_rows = conn.execute(
        "SELECT qid, explanation FROM questions ORDER BY qid"
    ).fetchall()
    e_qids = [r[0] for r in e_rows]
    exps   = [r[1] or "" for r in e_rows]
    print(f"  {len(exps)} explanations loaded")

    # TF-IDF (separate pass per field — each field is its own corpus)
    print(f"\nComputing stem TF-IDF (top {top_n}, {len(stems)} docs)...")
    stem_kw_lists = build_tfidf(stems, top_n)

    print(f"Computing explanation TF-IDF (top {top_n}, {len(exps)} docs)...")
    exp_kw_lists  = build_tfidf(exps, top_n)

    # Preview
    print(f"\n══ ITE Sample (first 3) ════════════════════════════════════")
    for i in range(min(3, len(q_qids))):
        print(f"\n  {q_qids[i]}")
        print(f"  Stem preview:  {(stems[i] or '')[:100].replace(chr(10), ' ')}...")
        print(f"  stem_kw:       {', '.join(stem_kw_lists[i][:8])}")
        print(f"  expl_kw:       {', '.join(exp_kw_lists[i][:8])}")

    if DRY_RUN:
        print(f"\n[DRY RUN — ITE: {len(stems)} stems processed, no writes]")
        return

    # Write
    print(f"\nWriting {len(stem_kw_lists)} ITE stem_keywords rows...")
    for qid, sk, ek in zip(q_qids, stem_kw_lists, exp_kw_lists):
        sk_str  = ", ".join(sk)
        ek_str  = ", ".join(ek)
        all_str = merge_keywords(sk, ek)
        conn.execute(
            "UPDATE questions SET stem_keywords=?, explanation_keywords=?, all_keywords=? WHERE qid=?",
            (sk_str, ek_str, all_str, qid)
        )
    conn.commit()
    print(f"  ✓ {len(stem_kw_lists)} rows written")

    # Coverage check
    total  = len(q_qids)
    filled = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE stem_keywords IS NOT NULL AND stem_keywords != ''"
    ).fetchone()[0]
    avg = avg_len(conn, "questions", "stem_keywords")
    print(f"  Coverage: {filled}/{total} ({pct(filled, total)}%)  avg_len={avg} chars")


# ─────────────────────────────────────────────────────────────────────
# AAFP CORPUS
# ─────────────────────────────────────────────────────────────────────
def run_aafp(conn: sqlite3.Connection, top_n: int) -> None:
    print("\n══ AAFP Corpus ═════════════════════════════════════════════")

    # Schema
    print("\nSchema check...")
    add_column_if_missing(conn, "aafp_questions",    "stem_keywords")
    add_column_if_missing(conn, "aafp_explanations", "explanation_keywords")
    conn.commit()

    # Load stems
    print("\nLoading stems...")
    q_rows = conn.execute(
        "SELECT aafp_qid, stem FROM aafp_questions ORDER BY aafp_qid"
    ).fetchall()
    q_qids = [r[0] for r in q_rows]
    stems  = [r[1] or "" for r in q_rows]
    print(f"  {len(stems)} stems loaded")

    # Load explanations
    print("Loading explanations...")
    e_rows = conn.execute(
        "SELECT aafp_qid, explanation FROM aafp_explanations ORDER BY aafp_qid"
    ).fetchall()
    e_qids = [r[0] for r in e_rows]
    exps   = [r[1] or "" for r in e_rows]
    print(f"  {len(exps)} explanations loaded")

    # TF-IDF
    print(f"\nComputing stem TF-IDF (top {top_n}, {len(stems)} docs)...")
    stem_kw_lists = build_tfidf(stems, top_n)

    print(f"Computing explanation TF-IDF (top {top_n}, {len(exps)} docs)...")
    exp_kw_lists  = build_tfidf(exps, top_n)

    # Preview
    print(f"\n══ AAFP Sample (first 3) ═══════════════════════════════════")
    for i in range(min(3, len(q_qids))):
        print(f"\n  {q_qids[i]}")
        print(f"  Stem preview:  {(stems[i] or '')[:100].replace(chr(10), ' ')}...")
        print(f"  stem_kw:       {', '.join(stem_kw_lists[i][:8])}")
        print(f"  expl_kw:       {', '.join(exp_kw_lists[i][:8])}")

    if DRY_RUN:
        print(f"\n[DRY RUN — AAFP: {len(stems)} stems processed, no writes]")
        return

    # Write stem_keywords
    print(f"\nWriting {len(stem_kw_lists)} AAFP stem_keywords rows...")
    for qid, kw_list in zip(q_qids, stem_kw_lists):
        conn.execute(
            "UPDATE aafp_questions SET stem_keywords = ? WHERE aafp_qid = ?",
            (", ".join(kw_list), qid)
        )
    conn.commit()

    # Write explanation_keywords
    print(f"Writing {len(exp_kw_lists)} AAFP explanation_keywords rows...")
    for qid, kw_list in zip(e_qids, exp_kw_lists):
        conn.execute(
            "UPDATE aafp_explanations SET explanation_keywords = ? WHERE aafp_qid = ?",
            (", ".join(kw_list), qid)
        )
    conn.commit()
    print(f"  ✓ {len(stem_kw_lists)} stem rows + {len(exp_kw_lists)} explanation rows written")

    # Coverage check
    total  = len(q_qids)
    filled = conn.execute(
        "SELECT COUNT(*) FROM aafp_questions WHERE stem_keywords IS NOT NULL AND stem_keywords != ''"
    ).fetchone()[0]
    avg = avg_len(conn, "aafp_questions", "stem_keywords")
    print(f"  Coverage: {filled}/{total} ({pct(filled, total)}%)  avg_len={avg} chars")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found:\n  {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print(f"unified_keyword_extractor.py")
    print(f"  corpus={CORPUS}  top_n={TOP_N}  dry_run={DRY_RUN}")
    print(f"  DB: {DB_PATH}")

    if STATS:
        run_stats(conn)
        conn.close()
        return

    if CORPUS in ("ite", "both"):
        run_ite(conn, TOP_N)

    if CORPUS in ("aafp", "both"):
        run_aafp(conn, TOP_N)

    print("\n══ Final Coverage ══════════════════════════════════════════")
    run_stats(conn)

    conn.close()
    print("\nDone.")


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--help" in sys.argv:
        print(__doc__)
        sys.exit(0)
    main()

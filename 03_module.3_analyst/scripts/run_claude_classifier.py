"""
run_claude_classifier.py
========================
Pass 2 of the body system classification pipeline — production classifier using Claude API
with Chain-of-Thought reasoning and dynamic few-shot retrieval.

This script classifies ITE questions into one of 15 ABFM body system categories using:
1. Dynamic few-shot retrieval (K=5 most similar training examples via embedding cosine similarity)
2. Claude Sonnet 4.6 with structured JSON output
3. Confidence-based routing (sql_ready / human_review / flagged)
4. Centroid distance cross-check for outlier detection

Inputs:
  - ite_intelligence.db:            source of truth (questions + question_full_vec embeddings)
  - body_system_training_set.json:  verified 2022–2023 labels + embeddings
  - Unlabeled years (default):      2018, 2019, 2020, 2021, 2024, 2025

Output:
  - claude_classifications.json:    results with routing and confidence scores

Installation:
    pip install anthropic numpy

Usage:
    # Classify all unlabeled years with default params (K=5)
    python run_claude_classifier.py

    # Classify specific year with limit (for testing)
    python run_claude_classifier.py --years 2024 --limit 10

    # Classify specific QIDs only
    python run_claude_classifier.py --qids QID-2018-0001 QID-2018-0042 QID-2020-0055

    # Dry-run: show prompts without calling Claude API (no anthropic required)
    python run_claude_classifier.py --years 2024 --limit 5 --dry-run

    # Change K and output directory
    python run_claude_classifier.py --years 2024 --k 10 --output-dir ./custom_output/

Environment:
    ANTHROPIC_API_KEY: required for Claude API calls (set in env; not needed for --dry-run)

Notes:
    - Rate limiting: 0.5s between API calls to respect Claude API limits
    - Each question retrieves K most similar training examples by cosine similarity
    - Centroid distance > 0.4 with high confidence triggers human_review route
    - Progress reported per question (qid + body_system + confidence)
"""

import os
import sys
import json
import time
import argparse
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import defaultdict

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = PROJECT_ROOT / "00_database" / "db" / "ite_intelligence.db"
OUTPUT_DIR = PROJECT_ROOT / "03_module.3_analyst" / "outputs" / "body_system_labels"

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

FINAL_TAXONOMY = [
    "Cardiovascular",
    "Endocrine",
    "Gastrointestinal",
    "Hematologic/Immune",
    "Injuries/Musculoskeletal",
    "Integumentary",
    "Nephrologic",
    "Neurologic",
    "Nonspecific",
    "Patient-Based Systems",
    "Population-Based Care",
    "Psychiatric/Behavioral",
    "Respiratory",
    "Sexual and Reproductive",
    "Special Sensory",
]

TRAINING_YEARS = [2022, 2023]

SYSTEM_PROMPT = """You are an expert in ABFM Family Medicine board exam question classification.

Your task: classify each ITE question into exactly ONE of 15 body system categories
that the American Board of Family Medicine (ABFM) uses to organize exam content.

THE 15 CATEGORIES:
  Cardiovascular, Endocrine, Gastrointestinal, Hematologic/Immune, Injuries/Musculoskeletal,
  Integumentary, Nephrologic, Neurologic, Nonspecific, Patient-Based Systems,
  Population-Based Care, Psychiatric/Behavioral, Respiratory, Sexual and Reproductive,
  Special Sensory

CORE CLASSIFICATION RULES:
1. Classify by the ORGAN SYSTEM being tested, not by the drug or treatment used.
   (metformin question → Endocrine; lisinopril question → Cardiovascular)

2. Classify by PRIMARY pathophysiology — not secondary complications.
   (anemia in CKD → Nephrologic, not Hematologic/Immune)
   (cardiomyopathy from thyroid disease → Endocrine, not Cardiovascular)
   (proteinuria in diabetes → Nephrologic, not Endocrine)

3. Classify by WHAT ABFM IS TESTING, not what is mentioned in passing.
   (a question about HTN management in a diabetic patient tests Cardiovascular)
   (a question about HbA1c targets in a diabetic patient tests Endocrine)

DISAMBIGUATION RULES FOR DIFFICULT CATEGORIES:

NONSPECIFIC — Use ONLY when no single organ system dominates:
  YES: Multi-morbidity management (HTN + DM2 + CKD patient, question is about overall
       care coordination rather than any one condition)
  YES: Polypharmacy/medication reconciliation with no dominant system
  YES: Geriatric syndromes that are inherently cross-system (falls, delirium, frailty)
  NO:  A question that mentions multiple systems but tests one primary concept
  NO:  A question about a condition that happens to affect multiple organs

POPULATION-BASED CARE — Use when the question tests screening, prevention, or
epidemiology RATHER than clinical management:
  YES: Screening thresholds (when to screen, at what age, how often)
  YES: Preventive recommendations (vaccinations, counseling intervals)
  YES: Epidemiology, incidence, risk factor population data
  NO:  A question about treating a condition found on screening
  NO:  A question about pathophysiology of a preventable disease

PATIENT-BASED SYSTEMS — Use for healthcare DELIVERY and quality concepts:
  YES: Quality improvement methodology (PDSA cycles, Six Sigma)
  YES: Evidence-based medicine concepts (NNT, NNH, likelihood ratios, study design)
  YES: Healthcare systems concepts (transitions of care, care coordination frameworks)
  NO:  Clinical management of any specific condition
  NO:  Behavioral counseling (that is Psychiatric/Behavioral or the clinical body system)

ENDOCRINE vs SEXUAL AND REPRODUCTIVE — when both apply, classify by the core mechanism:
  Thyroid disease in pregnancy → Endocrine (thyroid physiology is tested)
  Gestational diabetes → Sexual and Reproductive (pregnancy complication is tested)
  PCOS → Sexual and Reproductive (reproductive dysfunction is the primary issue)
  Osteoporosis (post-menopausal) → Injuries/Musculoskeletal (bone physiology tested)

PSYCHIATRIC/BEHAVIORAL — mental health, behavioral health, substance use:
  YES: Depression, anxiety, bipolar, schizophrenia, PTSD
  YES: Substance use disorders (alcohol, opioids, stimulants)
  YES: Eating disorders, somatic symptom disorders
  NO:  Behavioral change counseling in a patient with a primary medical condition
       (smoking cessation for a COPD patient → Respiratory)

You will be shown (a) one verified ABFM example for EACH of the 15 categories, then
(b) additional similar examples retrieved for this specific question.
Reason step by step before giving your final answer."""

# ─────────────────────────────────────────────────────────────────────────────
# Database utilities
# ─────────────────────────────────────────────────────────────────────────────


def open_db(path: Path):
    """Open SQLite DB in immutable URI mode (read-only, no journal files)."""
    import sqlite3

    if not path.exists():
        raise FileNotFoundError(f"DB not found: {path}")
    uri = path.as_uri() + "?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def deserialize_embedding(blob: bytes) -> Optional[np.ndarray]:
    """Deserialize embedding from DB (float32 raw bytes)."""
    if not blob:
        return None
    try:
        count = len(blob) // 4
        return np.array(struct.unpack(f"{count}f", blob), dtype=np.float32)
    except Exception as e:
        print(f"ERROR deserializing embedding: {e}")
        return None


def load_training_set(output_dir: Path):
    """Load training set JSON with questions and their labels."""
    training_file = output_dir / "body_system_training_set.json"
    if not training_file.exists():
        raise FileNotFoundError(f"Training set not found: {training_file}")
    with open(training_file, "r", encoding="utf-8") as f:
        return json.load(f)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    if vec1 is None or vec2 is None:
        return 0.0
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def text_cosine_similarity(text1: str, text2: str) -> float:
    """Fallback: compute rough text similarity (character trigrams)."""

    def trigrams(s):
        s = s.lower()
        return set(s[i : i + 3] for i in range(len(s) - 2))

    tg1 = trigrams(text1)
    tg2 = trigrams(text2)
    if not tg1 or not tg2:
        return 0.0
    intersection = len(tg1 & tg2)
    union = len(tg1 | tg2)
    return intersection / union if union > 0 else 0.0


def retrieve_few_shot_examples(
    target_qid: str,
    target_embedding: Optional[np.ndarray],
    target_text: str,
    training_questions: list,
    training_embeddings: dict,
    k: int = 5,
) -> list:
    """
    Retrieve K most similar training questions by cosine similarity on embeddings.
    Falls back to text similarity if embeddings unavailable.
    """
    similarities = []

    for train_q in training_questions:
        train_qid = train_q["qid"]
        if train_qid == target_qid:
            continue  # skip self

        train_embedding = training_embeddings.get(train_qid)
        if target_embedding is not None and train_embedding is not None:
            sim = cosine_similarity(target_embedding, train_embedding)
        else:
            sim = text_cosine_similarity(
                target_text, train_q.get("question_text", "")
            )

        similarities.append((sim, train_qid, train_q))

    # Sort by similarity descending and take top K
    similarities.sort(reverse=True, key=lambda x: x[0])
    return [q for _, _, q in similarities[:k]]


def select_canonical_examples(
    training_questions: list,
    training_embeddings: dict,
) -> dict[str, dict]:
    """
    Select one canonical (most prototypical) example per category from the training set.
    Uses cosine similarity to the category centroid — the example closest to its class
    center is the clearest representative of that category.

    Returns: {category_name: question_dict}
    """
    # Group questions by category
    by_category: dict[str, list] = defaultdict(list)
    for q in training_questions:
        by_category[q["body_system"]].append(q)

    # Compute centroid per category
    canonicals = {}
    for cat, questions in by_category.items():
        vecs = [
            training_embeddings[q["qid"]]
            for q in questions
            if q["qid"] in training_embeddings and training_embeddings[q["qid"]] is not None
        ]
        if not vecs:
            # No embeddings — pick first question
            canonicals[cat] = questions[0]
            continue

        centroid = np.mean(np.stack(vecs), axis=0)
        centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-9)

        # Find the question closest to its category centroid
        best_sim, best_q = -1.0, questions[0]
        for q in questions:
            vec = training_embeddings.get(q["qid"])
            if vec is None:
                continue
            sim = cosine_similarity(vec, centroid_norm)
            if sim > best_sim:
                best_sim, best_q = sim, q

        canonicals[cat] = best_q

    return canonicals


def build_claude_prompt(
    target_question: dict,
    canonical_examples: dict,
    few_shot_examples: list,
) -> str:
    """
    Build the user message for Claude with two layers of examples:
      Layer 1 — Static canonical: one best example per all 15 categories (always included)
      Layer 2 — Dynamic retrieved: K most similar examples for this specific question

    Together they give Claude: full taxonomy coverage + specific context.
    """
    prompt_parts = []

    # ── LAYER 1: Static canonical examples (one per category, always included) ──
    prompt_parts.append(
        f"## Part A — One Verified ABFM Example Per Category (all 15 categories)\n"
        f"These establish the full taxonomy. Use them to understand what ABFM means by each category.\n"
    )
    for cat in sorted(canonical_examples.keys()):
        example = canonical_examples[cat]
        prompt_parts.append(f"### {cat}")
        # Truncate question to keep prompt manageable
        q_text = (example["question_text"] or "")[:300]
        prompt_parts.append(f"Q: {q_text}...")
        prompt_parts.append(
            f"Correct: {example.get('correct_letter','?')} — "
            f"{(example.get('correct_text','') or '')[:120]}\n"
        )

    # ── LAYER 2: Dynamic retrieved examples (K most similar to target) ──
    # Exclude any canonicals already shown (by qid) to avoid duplication
    canonical_qids = {v["qid"] for v in canonical_examples.values()}
    unique_retrieved = [ex for ex in few_shot_examples if ex["qid"] not in canonical_qids]

    if unique_retrieved:
        prompt_parts.append(
            f"## Part B — {len(unique_retrieved)} Most Similar Questions to the Target\n"
            f"These are the closest ABFM matches by clinical content. "
            f"Pay special attention to these when reasoning.\n"
        )
        for i, example in enumerate(unique_retrieved, 1):
            prompt_parts.append(f"### Similar Example {i} — {example.get('body_system', 'Unknown')}")
            prompt_parts.append(f"Q: {example['question_text']}")
            choices = example.get("choices", [])
            if choices:
                for choice in choices:
                    letter = choice.get("letter", "?")
                    text = choice.get("text", "")
                    prompt_parts.append(f"  {letter}) {text}")
            prompt_parts.append(
                f"Correct: {example.get('correct_letter', '?')} — {example.get('correct_text', '')}\n"
            )

    # ── TARGET QUESTION ────────────────────────────────────────────────────────
    prompt_parts.append("## Question to Classify\n")
    prompt_parts.append(f"**QID**: {target_question['qid']}")
    prompt_parts.append(f"**Q**: {target_question['question_text']}")
    choices = target_question.get("choices", [])
    if choices:
        for choice in choices:
            letter = choice.get("letter", "?")
            text = choice.get("text", "")
            prompt_parts.append(f"  {letter}) {text}")
    prompt_parts.append(
        f"**Correct**: {target_question.get('correct_letter', '?')} — {target_question.get('correct_text', '')}\n"
    )

    prompt_parts.append(
        "## Your Task\n"
        "Classify this question into ONE of the 15 categories. Return a JSON object with:\n"
        "- body_system: One of the 15 categories\n"
        "- confidence: Float 0.0–1.0\n"
        "- reasoning: 1–2 sentence clinical rationale\n"
        "- alternative: Second most likely category (or null)\n"
    )

    return "\n".join(prompt_parts)


def validate_classification(result: dict) -> tuple[bool, Optional[str]]:
    """
    Validate Claude's classification output.
    Returns (is_valid, error_message).
    """
    if "body_system" not in result:
        return False, "Missing 'body_system' field"

    body_system = result["body_system"]
    if body_system not in FINAL_TAXONOMY:
        return False, f"Invalid body_system '{body_system}' not in taxonomy"

    if "confidence" not in result:
        return False, "Missing 'confidence' field"

    conf = result["confidence"]
    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
        return False, f"Invalid confidence {conf} (must be 0.0–1.0)"

    return True, None


def compute_centroid_distance(
    target_embedding: Optional[np.ndarray],
    assigned_category: str,
    training_questions: list,
    training_embeddings: dict,
) -> Optional[float]:
    """
    Compute cosine distance from target embedding to centroid of assigned category.
    Returns None if embedding unavailable.
    """
    if target_embedding is None:
        return None

    # Gather all training embeddings for this category
    category_embeddings = []
    for train_q in training_questions:
        if train_q.get("body_system") == assigned_category:
            emb = training_embeddings.get(train_q["qid"])
            if emb is not None:
                category_embeddings.append(emb)

    if not category_embeddings:
        return None

    # Compute centroid
    centroid = np.mean(category_embeddings, axis=0)
    # Compute distance (1 - similarity)
    sim = cosine_similarity(target_embedding, centroid)
    return 1.0 - sim


def route_classification(
    confidence: float,
    centroid_distance: Optional[float],
) -> str:
    """
    Route classification based on confidence and centroid distance.
    Returns "sql_ready", "human_review", or "flagged".
    """
    centroid_flag = (
        centroid_distance is not None
        and centroid_distance > 0.4
        and confidence >= 0.85
    )
    if centroid_flag:
        return "human_review"

    if confidence >= 0.85:
        return "sql_ready"
    elif confidence >= 0.60:
        return "human_review"
    else:
        return "flagged"


def classify_questions(
    db_path: Path,
    output_dir: Path,
    target_years: Optional[list] = None,
    target_qids: Optional[list] = None,
    k: int = 5,
    limit: Optional[int] = None,
    dry_run: bool = False,
):
    """
    Classify unlabeled questions using Claude API.

    Args:
        db_path: Path to ite_intelligence.db
        output_dir: Output directory for results
        target_years: Years to classify (default: all unlabeled years)
        target_qids: Specific QIDs to classify (overrides target_years)
        k: Number of few-shot examples to retrieve
        limit: Maximum questions to classify (for testing)
        dry_run: If True, show prompts without calling Claude API
    """
    import sqlite3

    # For non-dry-run, require anthropic
    if not dry_run:
        try:
            from anthropic import Anthropic
        except ImportError:
            print(
                "ERROR: anthropic package not installed.\n"
                "Install dependencies with:\n"
                "  pip install anthropic numpy\n"
                "\n"
                "Or from this directory:\n"
                "  pip install -r ../../02_module.2_processor/requirements.txt\n",
                file=sys.stderr,
            )
            sys.exit(1)

    # Load training set
    print("[*] Loading training set...")
    training_data = load_training_set(output_dir)
    training_questions = training_data.get("questions", [])
    print(f"    {len(training_questions)} training questions loaded")

    # Load embeddings for training questions
    print("[*] Loading training embeddings...")
    db = open_db(db_path)
    training_embeddings = {}
    for train_q in training_questions:
        row = db.execute(
            "SELECT embedding FROM question_full_vec WHERE qid = ?",
            (train_q["qid"],),
        ).fetchone()
        if row and row[0]:
            training_embeddings[train_q["qid"]] = deserialize_embedding(row[0])
    db.close()
    print(f"    {len(training_embeddings)} embeddings loaded")

    # Determine target years
    if target_qids:
        print(f"[*] Classifying {len(target_qids)} specific QIDs")
    elif target_years is None:
        all_training_years = set(training_data.get("years", TRAINING_YEARS))
        # All years not in training set
        target_years = [y for y in range(2018, 2026) if y not in all_training_years]
        print(f"[*] Classifying unlabeled years: {target_years}")
    else:
        print(f"[*] Classifying target years: {target_years}")

    # Load questions to classify from DB
    print("[*] Loading questions from DB...")
    db = open_db(db_path)
    questions_to_classify = {}

    if target_qids:
        placeholders = ",".join("?" * len(target_qids))
        rows = db.execute(
            f"""
            SELECT qid, exam_year, body_system, question_text, choices,
                   correct_letter, correct_text
            FROM questions WHERE qid IN ({placeholders})
            """,
            target_qids,
        ).fetchall()
    else:
        placeholders = ",".join("?" * len(target_years))
        rows = db.execute(
            f"""
            SELECT qid, exam_year, body_system, question_text, choices,
                   correct_letter, correct_text
            FROM questions WHERE exam_year IN ({placeholders})
            """,
            target_years,
        ).fetchall()

    for row in rows:
        qid = row["qid"]
        # Parse choices JSON
        choices_raw = row["choices"]
        if isinstance(choices_raw, str):
            try:
                choices = json.loads(choices_raw)
            except Exception:
                choices = []
        else:
            choices = choices_raw or []

        questions_to_classify[qid] = {
            "qid": qid,
            "exam_year": row["exam_year"],
            "body_system_current_db": row["body_system"],
            "question_text": row["question_text"] or "",
            "choices": choices,
            "correct_letter": row["correct_letter"] or "",
            "correct_text": row["correct_text"] or "",
        }

    db.close()
    total_to_classify = len(questions_to_classify)
    print(f"    {total_to_classify} questions to classify")

    if limit:
        questions_to_classify = dict(list(questions_to_classify.items())[:limit])
        print(f"    Limited to {len(questions_to_classify)} (--limit {limit})")

    # Initialize Claude client (only if not dry-run)
    client = None
    if not dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set"
            )
        client = Anthropic(api_key=api_key)

    # Pre-compute canonical examples (one per category) — done ONCE, reused for every question
    print("[*] Selecting canonical examples (one per category)...")
    canonical_examples = select_canonical_examples(training_questions, training_embeddings)
    print(f"    {len(canonical_examples)} canonical examples selected (covering all 15 categories)")

    # Classify each question
    results = []
    routing_summary = defaultdict(int)

    print(f"\n[*] Classifying {len(questions_to_classify)} questions...")
    for idx, (qid, question) in enumerate(questions_to_classify.items(), 1):
        # Load embedding for this question
        db = open_db(db_path)
        target_embedding = None
        row = db.execute(
            "SELECT embedding FROM question_full_vec WHERE qid = ?", (qid,)
        ).fetchone()
        if row and row[0]:
            target_embedding = deserialize_embedding(row[0])
        db.close()

        # Retrieve K most similar training questions (from full 393-question pool)
        few_shot_examples = retrieve_few_shot_examples(
            qid,
            target_embedding,
            question["question_text"],
            training_questions,
            training_embeddings,
            k=k,
        )

        # Build prompt — Layer 1 (all 15 canonical) + Layer 2 (K dynamic retrieved)
        user_prompt = build_claude_prompt(question, canonical_examples, few_shot_examples)

        if dry_run:
            # Show system prompt once (first question only), then full user prompt each time
            if idx == 1:
                print("\n" + "=" * 80)
                print("SYSTEM PROMPT:")
                print("=" * 80)
                print(SYSTEM_PROMPT)

            print("\n" + "=" * 80)
            print(f"[DRY-RUN {idx}/{len(questions_to_classify)}] {qid}")
            print("=" * 80)

            # Split prompt into sections for readable output
            sections = user_prompt.split("## ")
            for section in sections:
                if not section.strip():
                    continue
                header = section.split("\n")[0]
                if "Part A" in header:
                    # Show just category names + first line of each canonical
                    print(f"\n## {header}")
                    print(f"  [{len(canonical_examples)} categories: {', '.join(sorted(canonical_examples.keys()))}]")
                elif "Part B" in header:
                    print(f"\n## {header}")
                    # Show each retrieved example's category and first 120 chars
                    lines = section.split("\n")
                    for line in lines[1:]:
                        if line.startswith("### Similar"):
                            print(f"  {line}")
                        elif line.startswith("Q:"):
                            print(f"    {line[:120]}...")
                            break
                elif "Question to Classify" in header:
                    print(f"\n## {header}")
                    lines = section.split("\n")
                    for line in lines[1:8]:
                        print(f"  {line}")
                elif "Your Task" in header:
                    print(f"\n## {header} [schema omitted]")

            results.append({
                "qid": qid,
                "exam_year": question.get("exam_year"),
                "dry_run": True,
            })
            routing_summary["dry_run"] += 1
            continue

        # Call Claude API
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            response_text = message.content[0].text

            # Parse JSON from response
            try:
                # Try to extract JSON from response
                classification = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to find JSON in the response text
                import re

                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    classification = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from response")

            # Validate
            is_valid, error_msg = validate_classification(classification)
            if not is_valid:
                print(
                    f"[ERROR {idx}] {qid}: Invalid classification: {error_msg}"
                )
                continue

            # Extract fields
            body_system = classification["body_system"]
            confidence = classification["confidence"]
            reasoning = classification.get("reasoning", "")
            alternative = classification.get("alternative")

            # Compute centroid distance
            centroid_distance = compute_centroid_distance(
                target_embedding,
                body_system,
                training_questions,
                training_embeddings,
            )
            centroid_flag = (
                centroid_distance is not None
                and centroid_distance > 0.4
                and confidence >= 0.85
            )

            # Route
            route = route_classification(confidence, centroid_distance)
            routing_summary[route] += 1

            # Retrieved example QIDs for reference
            retrieved_qids = [ex["qid"] for ex in few_shot_examples]

            # Build result
            result = {
                "qid": qid,
                "exam_year": question["exam_year"],
                "body_system_current_db": question["body_system_current_db"],
                "body_system_proposed": body_system,
                "confidence": confidence,
                "reasoning": reasoning,
                "alternative": alternative,
                "route": route,
                "centroid_distance": centroid_distance,
                "centroid_flag": centroid_flag,
                "retrieved_examples": retrieved_qids,
            }
            results.append(result)

            # Progress report
            print(
                f"[{idx}/{len(questions_to_classify)}] {qid} → "
                f"{body_system} (conf={confidence:.2f}, route={route})"
            )

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"[ERROR {idx}] {qid}: {e}")
            continue

    # Build output JSON
    output = {
        "generated": datetime.now().isoformat(),
        "model": "claude-sonnet-4-6",
        "training_years": training_data.get("years", TRAINING_YEARS),
        "target_years": target_years if target_years else None,
        "target_qids": target_qids if target_qids else None,
        "total_classified": len(results),
        "routing_summary": dict(routing_summary),
        "results": results,
    }

    # Write output
    output_file = output_dir / "claude_classifications.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n[✓] Classification complete!")
    print(f"    Total classified: {len(results)}")
    print(f"    Routing summary: {dict(routing_summary)}")
    print(f"    Output written to: {output_file}")

    return output_file


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        help="Target exam years to classify (default: unlabeled years)",
    )
    parser.add_argument(
        "--qids",
        nargs="+",
        help="Specific QIDs to classify (overrides --years)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of few-shot examples to retrieve (default: 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum questions to classify in this run (for testing)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show prompts without calling Claude API",
    )

    args = parser.parse_args()

    try:
        classify_questions(
            db_path=DB_PATH,
            output_dir=args.output_dir,
            target_years=args.years,
            target_qids=args.qids,
            k=args.k,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"\n[FATAL] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

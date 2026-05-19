# Methodology Scout: ITE Body System Classification Agent
**Date:** 2026-04-15
**Mode:** Design
**Problem:** Given ~400 ABFM-labeled ITE questions (stem + answer choices + correct answer only — no derived tags), train an agent to classify each question into one of ~16 body system categories. Training set: ~25 examples per class from 2022–2023 ABFM score reports (ground truth). Goal: generalize to ~1,200 questions from other years where body_system was AI-synthesized and unreliable. Output must include a confidence signal, because incorrect classifications propagate through concept tags, clinical pathways, and AAFP body system assignments downstream.
**Stack context:** Python / SQLite / OpenAI text-embedding-3-small (already computed) / Claude API

---

## Design Constraints That Matter

- **Input is deliberately minimal.** Only raw Q&A: question stem, answer choices, correct answer. Explanations, concept tags, ICD-10 codes, and citations are excluded because they were all built downstream of the contaminated body_system field.
- **~25 examples per class** is the training ceiling. This rules out heavy fine-tuning approaches.
- **~16 output classes** — 5 collapse into the post-2023 ABFM taxonomy; ~11 do not (Gastrointestinal, Endocrine, Neurologic, etc. remain distinct). Clinical adjacency between some classes is the hardest problem (Nephrologic vs. Hematologic/Immune; Reproductive:Female vs. Reproductive:Male).
- **Confidence is load-bearing.** Low-confidence outputs feed a human review queue, not SQL. High-confidence outputs feed SQL directly. Getting this threshold wrong costs data integrity.
- **OpenAI embeddings already exist** in the DB (question_full_vec, aafp_question_full_vec). Approaches that reuse them are free; approaches that require different encoders add infrastructure cost.

---

## Methods Compared

| # | Method | What It Does (plain language) | Strength | Weakness | Verdict | Stack Fit |
|---|--------|-------------------------------|----------|----------|---------|-----------|
| 0 | **Current (AI-synthesized)** | 2018–2019: Claude API with 16-category taxonomy different from DB. 2020–2021: SBERT + XGBoost classifier. 2024: 5-category collapsed report + remapped. Root cause: no consistent ground-truth anchor across years; each era used a different taxonomy and different signal | Produced values quickly | Different taxonomies per era; no internal consistency; downstream data built on contaminated base | **Not recommended** — structural inconsistency cannot be patched; requires rebuild from ground truth | Native |
| 1 | **SVM / Logistic Regression on existing embeddings** | Takes the vector fingerprints already computed for each question, trains a standard linear classifier in minutes, produces probability scores for each class. No new embeddings, no API calls. (This is "Support Vector Machine" or "logistic regression" — both are classic classifiers that draw decision boundaries between categories in the embedding space.) | Trains in seconds on existing embeddings. predict_proba() gives confidence directly. SVM with linear kernel particularly strong at separating text categories. Native to stack. | Cannot reason about WHY a question is in a category — pure pattern matching. Lower ceiling on adjacent category accuracy than LLM-based approaches (~82–97% on comparable tasks). | **Start here** — baseline accuracy measurement before committing to any heavier approach. Validates whether the embedding space already separates body systems cleanly. | Native |
| 2 | **Chain-of-Thought Claude classification with dynamic few-shot retrieval** | Before assigning a category, retrieves the N most similar labeled training questions (using existing embeddings), injects them into a Claude API prompt, and asks Claude to reason about why the question belongs to a specific body system before giving its answer. The reasoning trace is returned alongside the label and a verbalized confidence score. | Explicitly models the clinical reasoning ABFM uses. Interpretable — every classification comes with a reviewable rationale. Handles adjacent categories through reasoning rather than keyword matching. Naturally produces "I'm uncertain because this question spans X and Y" signals. | Costs API tokens per question (~1,200 calls). Slower than embedding-only approaches. Confidence verbalization must be validated against actual accuracy (LLMs can be confidently wrong). | **Sweet spot** — the right production approach for this problem. The reasoning trace makes every questionable classification auditable before it becomes SQL. The retrieval grounds the LLM in the actual training examples. | Native (Claude API already in use) |
| 3 | **SetFit (Sentence Transformer Fine-Tuning)** | Fine-tunes a pretrained text encoder using contrastive training — it learns to push examples from different classes apart and pull examples from the same class together, then trains a lightweight classifier head on top. Works with as few as 8 labeled examples per class. | State-of-the-art accuracy at low-data regimes. No prompting required. Competitive with GPT-3 fine-tuning at a fraction of the cost. | Cannot use the already-computed OpenAI embeddings directly — requires its own Sentence Transformer encoder. Adds a new model dependency. Less interpretable than CoT. Medical domain not in base training data. | **Worth exploring** — if SVM accuracy (Method 1) is unsatisfactory on adjacent categories, SetFit is the next step. Run it on a held-out validation year (train on 2022, test on 2023) before committing. | +library (pip install setfit + sentence-transformers) |
| 4 | **Prototypical Networks (class centroid + distance-based confidence)** | Computes one "prototype" vector per body system class (the average embedding of all training examples in that class). Classifies new questions by finding the nearest prototype. Distance to the nearest prototype is the confidence signal — far away means uncertain. | Elegant confidence signal: distance IS uncertainty. Naturally handles variable class sizes. Well-studied in medical text classification (73% accuracy on 5-shot disease coding). No training loop — just averaging. | Single prototype per class may not capture within-class variation (Reproductive:Female spans OB, contraception, oncology). Sensitive to outliers in small training sets. | **Worth exploring** — valuable specifically for the confidence signal. Can be implemented directly on existing OpenAI embeddings in 20 lines of code. Use as a confidence cross-check alongside Method 2. | Native |
| 5 | **Hierarchical Multi-Label Classification (HMLC)** | Structures the classification problem as a tree: first classify at a high level (e.g., organ-system group), then conditionally classify within that branch. Respects the clinical taxonomy rather than treating all 16 classes as flat peers. | Best handling of adjacent categories — hierarchy constraints prevent cross-branch errors. Well-validated on medical body system classification. Produces interpretable classification paths. | Requires the taxonomy to be formally defined as a tree before building. No clear tree structure exists for the full 16-class ABFM taxonomy (some categories are clinically orthogonal, not hierarchical). | **Future phase** — worth designing after Method 2 is validated. If certain category pairs are chronically confused (e.g., Reproductive:Male vs. Nephrologic), a local hierarchy for those pairs alone may fix the problem. | +library (scikit-learn hierarchical, or custom) |
| 6 | **Structured Output with Instructor / JSON mode** | Forces the LLM to return a schema-validated JSON object every time — no free-text parsing, no retries for malformed output. The schema includes category (enum), confidence (float 0–1), and reasoning (string). | Eliminates parsing failures entirely. Compatible with Claude's native structured output. Confidence field is explicit in the schema contract. | Doesn't improve classification accuracy — it improves output reliability. Must be layered on top of a classification method, not used alone. | **Use with Method 2** — this is the output layer for the CoT approach. Not a standalone method; a required component of any LLM-based classifier for production use. | Native (Claude structured output, Nov 2024 GA) |
| 7 | **BioBERT / PubMedBERT / ClinicalBERT fine-tuning** | Domain-specific language models pretrained on biomedical text (PubMed abstracts, clinical notes). Fine-tuned for the classification task. Better medical vocabulary coverage than general models. | Strong on medical domain terminology. Well-benchmarked on ICD coding and clinical category tasks. | Requires fine-tuning a full transformer model (100M–300M parameters). GPU recommended. No confidence calibration out of the box. Adds significant infrastructure complexity. At 1,200 questions, this is engineering overhead for marginal gains over Method 2 with Claude. | **Not recommended** — Claude API already provides superior medical reasoning at zero infrastructure cost. The marginal accuracy gain from a domain-specific model does not justify the infrastructure at this scale. | New infra (GPU recommended, model hosting) |
| 8 | **LLM Chain Ensemble (multi-model confidence routing)** | Sends each question to multiple LLMs in sequence. First model classifies with confidence; if confidence is below threshold, it escalates to a more capable model. Aggregates predictions across the chain. | Leverages different model strengths. Graceful degradation for hard cases. | Manages multiple API providers and calibration across models. Confidence metrics inconsistent across providers. Adds latency and cost. | **Overkill** — designed for multi-provider production environments. Single Claude model with CoT is sufficient for 1,200 questions. | New infra (multi-provider management) |

---

## Recommended Approach

**I'd build this in two passes.**

**Pass 1 — Baseline in a day:** Train SVM (or logistic regression with `predict_proba()`) directly on the existing OpenAI question embeddings using the 2022 labeled set. Test on the 2023 labeled set. This tells you, within hours, which body system categories are already well-separated in the embedding space and which are chronically confused. It costs nothing and runs in seconds. If accuracy is ≥85% overall and the confused pairs are predictable (you'll know which ones), that's enough information to design Pass 2 intelligently.

**Pass 2 — Production classifier:** Implement Method 2 — Chain-of-Thought Claude classification with dynamic few-shot retrieval. For each unlabeled question: embed it, retrieve the 5 most similar labeled training examples (from the combined 2022+2023 set), inject them into a Claude prompt with a structured output schema, and ask Claude to reason about which body system the question is testing before committing to a label. Return JSON: `{category, confidence, reasoning}`.

Route based on confidence:
- confidence ≥ 0.85 → SQL-ready (auto-generated UPDATE statement)
- confidence 0.60–0.85 → human review queue with reasoning trace visible
- confidence < 0.60 → flag as ambiguous, do not touch DB until resolved

Use the prototypical network distance (Method 4) as a cross-check: if the embedding distance to the assigned class centroid is high while Claude's confidence is also high, that's a warning sign worth flagging regardless of the confidence score.

---

## Key Tradeoff

**Method 1 (SVM) is fast and free but opaque; Method 2 (CoT + retrieval) is slow and costs tokens but produces reviewable reasoning for every classification that touches production data.** Given that incorrect body_system values cascade into concept tags, clinical pathways, AAFP assignments, and intersection centroid vectors, the reasoning trace is worth the token cost.

---

## Validation Strategy

Train on 2022 (200 questions) → test on 2023 (200 questions). This is a genuine out-of-year generalization test, not a random split — it tells you whether the agent handles the natural variation in how ABFM frames questions year to year. Target: ≥85% overall accuracy, ≥75% accuracy on every individual class. Classes below 75% are candidates for additional training examples or local hierarchy disambiguation.

---

## Sources

1. SetFit paper (Tunstall et al., 2022): https://arxiv.org/pdf/2209.11055
2. ProtoNets on medical text (Sharma et al., 2022): https://arxiv.org/pdf/2212.01552v1.pdf
3. CLUR — uncertainty-aware few-shot (He et al., KDD 2023): https://github.com/he159ok/CLUR_UncertaintyEst_FewShot_TextCls
4. Retrieval-augmented few-shot classification (Yu et al., EMNLP 2023): https://aclanthology.org/2023.findings-emnlp.447.pdf
5. Dynamic few-shot prompting for clinical notes (PubMed 2025): https://pubmed.ncbi.nlm.nih.gov/40460022/
6. Few-Shot GPT with hierarchical dictionary (Wang et al., 2023 — directly on ABFM exam blueprint, 100% accuracy): https://arxiv.org/abs/2312.03561
7. CoT prompting for USMLE (Singhal et al., 2022): https://arxiv.org/abs/2207.08143
8. PLM-ICD (Huang et al., ACL 2022): PLM-ICD Automatic ICD Coding with Pretrained Language Models
9. LLM Chain Ensemble (Chen et al., 2024): https://arxiv.org/pdf/2410.13006
10. Anthropic Structured Outputs (Nov 2024): https://docs.claude.com/structured-outputs
11. OpenAI embeddings + sklearn classifier cookbook: https://developers.openai.com/cookbook/examples/classification_using_embeddings
12. FLARE: LLM classification failure modes (Madhavan et al., OMMM 2025): https://aclanthology.org/2025.ommm-1.4/
13. SVM with LLM embeddings benchmark (MachineLearningMastery, 2026): https://machinelearningmastery.com/llm-embeddings-vs-tf-idf-vs-bag-of-words-which-works-better-in-scikit-learn/

# Modular Vector Architecture (BATON 056)

## Overview
BATON 056 introduced a **5-dimensional modular vector embedding scheme** to support semantic + structural matching in Tier 1 practice question retrieval. This architecture decomposes question and article similarity into separate dimensions, enabling more nuanced learner matching than keyword-only or full-embedding retrieval.

## Five Dimensions

### 1. Blueprint Category Vectors
- **Table:** blueprint_label_vec (5 rows)
- **Content:** 5 canonical ABFM blueprint category embeddings
  - Cardiovascular
  - Respiratory
  - Gastrointestinal
  - Musculoskeletal
  - Psychiatric/Behavioral (+ others as needed)
- **Use:** Anchor vector for question→blueprint matching; stable across exam years
- **Built by:** build_modular_vectors.py (read blueprint labels from questions table, embed 5 canonical labels)

### 2. Body System Vectors
- **Table:** bodysystem_label_vec (5 rows)
- **Content:** 5 canonical body system label embeddings (same canonical forms as in questions.body_system_merged)
- **Use:** Structural matching layer; stable across exam years
- **Built by:** build_modular_vectors.py

### 3. Concept Tag Vectors
- **Table:** question_concepttag_vec (2,850 rows)
- **Schema:** (question_id, concept_tag_id, embedding_blob)
- **Content:** Per-question, per-concept_tag OpenAI embedding (text-embedding-3-small, 1536d)
- **Use:** Fine-grained semantic matching within a question's concept signature
- **Built by:** build_modular_vectors.py (read question_concept_tags table, embed each tag, store as BLOB)

### 4. Full Question Vectors
- **Table:** question_full_vec (1,629 rows) — ITE
- **Table:** aafp_question_full_vec (1,221 rows) — AAFP
- **Schema:** (question_id, embedding_blob)
- **Content:** Full question + blueprint + body_system embedding (text-embedding-3-small, 1536d)
  - ITE: question_text + blueprint + body_system
  - AAFP: question_text + blueprint + body_system + all concept_tags (concatenated)
- **Use:** Holistic semantic similarity search
- **Built by:** compute_embeddings.py with updated text builders

### 5. Intersection Centroid Vectors
- **Table:** intersection_centroid_vec (135 rows)
- **Schema:** (blueprint_id, body_system_id, embedding_blob)
- **Content:** 71 ITE + 64 AAFP blueprint×body_system local centroids
  - Centroid = mean of all questions in the (blueprint, body_system) cell
  - Enables fast "what's similar in this cell?" queries
- **Use:** Tier 1 matching initialization; pre-compute common retrieval cells
- **Built by:** build_intersection_centroids.py

## Retrieval Strategy (Future)

**DEFERRED-VECTOR-TIER1-REWRITE** will implement multi-stage retrieval:

1. **Stage 0 (Quick Filter):** Use question blueprint + body_system to identify relevant centroid(s)
2. **Stage 1 (Local Similarity):** Retrieve top-K questions near intersection centroid
3. **Stage 2 (Concept Refinement):** Re-rank by concept_tag_vec similarity to learner's ICD-10 profile
4. **Stage 3 (Full Semantic):** Final ranking using full_vec similarity

This replaces keyword-only retrieval and enables learner model to focus on true learning gaps rather than exact QID matches.

## Why Modular?

- **Taxonomy Stability:** Blueprint + body_system labels are stable across exam years; don't churn with concept synonyms
- **Learner Personalization:** ICD-10 profile can weight concept_tag_vec independently from full_vec
- **Interpretability:** Analysts can inspect which dimension drove a retrieval decision
- **Incremental Build:** New questions only require embedding their new concept_tags, not full DB rebuild
- **Parallel Training:** Each dimension can be optimized independently (e.g., different model for body_system vs. concept)

## Tables Populated (BATON 056)

| Table | Rows | Status |
|-------|------|--------|
| blueprint_label_vec | 5 | ✓ Built + verified |
| bodysystem_label_vec | 5 | ✓ Built + verified |
| question_concepttag_vec | 2,850 | ✓ Built + verified |
| question_full_vec | 1,629 | ✓ Built + verified |
| aafp_question_full_vec | 1,221 | ✓ Built + verified |
| intersection_centroid_vec | 135 | ✓ Built + verified |

## Scripts

- **build_modular_vectors.py** (M1 build/step 7) — Generate all label + concept_tag embeddings
- **build_intersection_centroids.py** (M1 build/step 8) — Compute and store centroid embeddings
- **compute_embeddings.py** (M1 build/step 5, updated) — Now builds question_full_vec + aafp_question_full_vec with new text builders

## Future Work

- Wire dimensions into Tier 1 matching (DEFERRED-VECTOR-TIER1-REWRITE)
- Learner ICD-10 profile integration (match_practice_questions_v4 with modular scoring)
- Ablation studies (which dimensions drive best recall for different body systems?)

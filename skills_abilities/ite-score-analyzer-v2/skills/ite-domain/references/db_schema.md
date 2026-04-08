# ITE Intelligence DB — Key Tables for Score Analysis

Database: `C:\Users\mpsch\Desktop\board_prep_intel\00_database\db\ite_intelligence.db`

---

## ite_questions

Primary question bank — 1,629 questions (2018–2025).

```sql
CREATE TABLE ite_questions (
    qid          TEXT PRIMARY KEY,   -- QID-YYYY-NNNN format
    year         INTEGER,            -- exam year (2018–2025)
    question     TEXT,               -- full question stem
    correct_letter TEXT,             -- A/B/C/D/E
    correct_text   TEXT,             -- full correct answer
    explanation    TEXT,
    blueprint      TEXT,             -- ABFM blueprint category
    body_system    TEXT,             -- organ system
    difficulty     REAL,             -- 0–1 (higher = harder)
    correct_rate   REAL,             -- national correct rate (0–1)
    concept_tags   TEXT,             -- JSON array of clinical concepts
    pgy_level      INTEGER           -- PGY target level
);
```

**Key fields for analysis:**
- `blueprint` — matches blueprint PDF categories
- `body_system` — matches body system PDF categories
- `correct_rate` — national average; used to identify easy misses
- `difficulty` — item difficulty parameter

---

## aafp_questions

AAFP Board Review Questions — 1,221 questions.

```sql
CREATE TABLE aafp_questions (
    qid          TEXT PRIMARY KEY,   -- QID-YYYY-NNNN format
    year         INTEGER,
    question     TEXT,
    correct_letter TEXT,
    correct_text   TEXT,
    explanation    TEXT,
    blueprint      TEXT,
    body_system    TEXT,
    concept_tags   TEXT
);
```

---

## articles

Clinical guideline library — 1,985 articles.

```sql
CREATE TABLE articles (
    art_id        TEXT PRIMARY KEY,  -- ART-XXXX
    title         TEXT,
    authors       TEXT,
    year          INTEGER,
    journal       TEXT,
    category      TEXT,              -- clinical category
    tier          TEXT,              -- right_click / local_lite / VC_pass / VC_fail
    citation_count INTEGER,
    pdf_path      TEXT,
    url           TEXT
);
```

---

## qid_art_xref

Links ITE questions to articles — 2,470 rows.

```sql
CREATE TABLE qid_art_xref (
    qid    TEXT REFERENCES ite_questions(qid),
    art_id TEXT REFERENCES articles(art_id),
    PRIMARY KEY (qid, art_id)
);
```

---

## aafp_qid_art_xref

Links AAFP questions to articles — 864 rows.

```sql
CREATE TABLE aafp_qid_art_xref (
    qid    TEXT REFERENCES aafp_questions(qid),
    art_id TEXT REFERENCES articles(art_id),
    PRIMARY KEY (qid, art_id)
);
```

---

## article_icd10

Article → ICD-10 mappings — 4,020 rows.

```sql
CREATE TABLE article_icd10 (
    art_id    TEXT,
    icd10     TEXT,
    relevance REAL  -- 0–1
);
```

---

## question_icd10

Question → ICD-10 mappings — 5,218 rows (92.8% of ITE questions covered).

```sql
CREATE TABLE question_icd10 (
    qid       TEXT,
    icd10     TEXT,
    relevance REAL
);
```

---

## clinical_pathways

Diagnosis → article maps with pathway role — 3,971 rows.

```sql
CREATE TABLE clinical_pathways (
    pathway_id    INTEGER PRIMARY KEY,
    icd10         TEXT,
    art_id        TEXT,
    pathway_role  TEXT,    -- diagnosis / treatment / screening / monitoring
    blueprint     TEXT,
    confidence    REAL
);
```

---

## article_currency

Article freshness tracking — 1,985 rows. Added 2026-04-07.

```sql
CREATE TABLE article_currency (
    art_id          TEXT PRIMARY KEY,
    pmid            TEXT,
    pubmed_status   TEXT,   -- current / updated / check_needed / not_indexed
    superseded_by   TEXT,   -- newer article PMID if updated
    last_checked    TEXT,   -- ISO date
    title_signals   TEXT,   -- blueprint keywords from title
    notes           TEXT
);
```

**Status meanings:**
- `current` — article is up-to-date per PubMed
- `updated` — newer version exists (superseded_by populated)
- `check_needed` — indexed on PubMed but needs manual review
- `not_indexed` — not found in PubMed (older/specialty guidelines)

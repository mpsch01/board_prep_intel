#!/usr/bin/env python3
"""
fingerprint_clustering.py

"Exam Fingerprint" -- NLP clustering of ITE question stems to surface
recurring question archetypes beyond the existing Subcategory taxonomy.

While Subcategory tags *what type of skill* is tested (Pharmacology, Diagnosis,
Management, etc.), this script asks a deeper question:
  What stylistic / contextual archetypes does ABFM use repeatedly?

Examples of archetypes it may surface:
  "Acute presentation in ED/urgent care -- next best step"
  "Elderly patient, screening or prevention recommendation"
  "Pediatric developmental / growth milestone"
  "Chronic disease guideline -- who qualifies for X intervention"
  "Drug adverse effect or interaction"
  "Pregnant / postpartum patient management"
  "Laboratory interpretation -- act on this finding"

Methodology:
  1. TF-IDF (1-2 grams, 2000 features) on cleaned stems
  2. L2-normalize for cosine similarity
  3. K-Means clustering (k=12 chosen from elbow; tunable via N_CLUSTERS)
  4. TruncatedSVD (100 components) -> UMAP 2-D projection
  5. Cluster characterization: top TF-IDF terms + Subcategory/BodySystem dist
  6. Rule-based archetype naming (human-reviewable, editable)

Outputs (all in 04_outputs/fingerprint/):
  fingerprint_labels.csv          -- QuestionID + Cluster + ArchetypeName + UMAP x/y
  fingerprint_cluster_summary.csv -- per-cluster: size, top terms, dominant labels
  fingerprint_umap_coords.csv     -- raw UMAP coordinates for downstream plotting
  fingerprint_archetypes.json     -- cluster->archetype map + question ID lists
  fingerprint_elbow.csv           -- k vs inertia for elbow analysis

Run:
  python fingerprint_clustering.py

Adjust N_CLUSTERS at top of file if you want more or fewer archetypes.
The archetype names in infer_archetype() are heuristic -- review and rename
the cluster summary CSV after running, then re-run with updated rules.
"""

import pandas as pd
import numpy as np
import re
import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sklearn.decomposition import TruncatedSVD
import umap

# -- Paths --------------------------------------------------------------------
BASE    = Path(__file__).resolve().parents[1]
MASTER  = BASE / "03_database/ABFM_ITE_Master_v2.xlsx"
OUT_DIR = BASE / "04_outputs/fingerprint"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -- Config -------------------------------------------------------------------
N_CLUSTERS   = 12    # Change to test different granularities
RANDOM_SEED  = 42
TFIDF_FEATS  = 2000
SVD_COMPS    = 100
UMAP_NEIGH   = 20
UMAP_MINDIST = 0.08

# -- Medical stopwords (domain-specific) --------------------------------------
MED_STOPS = [
    'patient', 'one', 'following', 'which', 'year', 'old', 'presents', 'history',
    'treatment', 'diagnosis', 'management', 'female', 'male', 'office', 'medical',
    'significant', 'examination', 'report', 'reports', 'associated', 'including',
    'based', 'best', 'appropriate', 'next', 'step', 'would', 'should', 'likely',
    'also', 'time', 'week', 'month', 'day', 'past', 'current', 'given', 'result',
    'finding', 'findings', 'test', 'testing', 'show', 'shows', 'normal', 'abnormal',
    'level', 'levels', 'blood', 'pressure', 'rate', 'heart', 'temperature', 'new',
    'due', 'use', 'using', 'used', 'case', 'question', 'answer', 'option', 'noted',
    'referred', 'seen', 'comes', 'clinic', 'known', 'taking', 'currently', 'recently',
    'reported', 'well', 'controlled', 'started', 'placed', 'complains', 'complaint',
    'ask', 'asked', 'deny', 'denies', 'states', 'tells', 'otherwise', 'unremarkable',
    'performed', 'review', 'reviewed', 'scheduled', 'follow', 'however', 'without',
    'within', 'additional', 'further', 'physical', 'vital', 'signs', 'sign',
    'alert', 'oriented', 'person', 'place', 'office', 'follow-up',
]


# -- Load & clean -------------------------------------------------------------
print("=" * 62)
print("ITE Exam Fingerprint Clustering")
print("=" * 62)
print(f"\nLoading: {MASTER.name}")
df = pd.read_excel(MASTER)
print(f"  {len(df)} questions loaded | {df['ExamYear'].nunique()} years ({df['ExamYear'].min()}-{df['ExamYear'].max()})")


def clean_stem(text):
    """Strip answer choices block, normalize whitespace, lowercase."""
    if pd.isna(text):
        return ""
    text = str(text)
    # Remove everything from first newline-preceded answer choice onward
    text = re.sub(r'\n[A-E]\).*', '', text, flags=re.DOTALL)
    # Remove any remaining lone answer choice lines
    text = re.sub(r'^\s*[A-E]\)\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text


df['stem_clean'] = df['QuestionStem'].apply(clean_stem)
empty = (df['stem_clean'].str.len() < 10).sum()
if empty:
    print(f"  WARNING: {empty} stems are very short (<10 chars) -- check source data")
print(f"  Mean stem length: {df['stem_clean'].str.len().mean():.0f} chars")


# -- TF-IDF Vectorization -----------------------------------------------------
print(f"\nBuilding TF-IDF matrix (features={TFIDF_FEATS}, ngram=(1,2))...")
all_stops = list(ENGLISH_STOP_WORDS) + MED_STOPS

vec = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=TFIDF_FEATS,
    min_df=3,
    max_df=0.70,
    stop_words=all_stops,
    sublinear_tf=True
)
X = vec.fit_transform(df['stem_clean'])
X_norm = normalize(X)   # L2-normalize for cosine-like distance
print(f"  Matrix: {X.shape[0]} questions x {X.shape[1]} features")


# -- Elbow Analysis -----------------------------------------------------------
print(f"\nElbow analysis (k=6..20, step=2)...")
ks = list(range(6, 21, 2))
inertias = []
for k in ks:
    km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10, max_iter=300)
    km.fit(X_norm)
    inertias.append(km.inertia_)
    print(f"  k={k:2d}: inertia={km.inertia_:.5f}")

elbow_df = pd.DataFrame({'k': ks, 'inertia': inertias})
elbow_df.to_csv(OUT_DIR / "fingerprint_elbow.csv", index=False)

# Compute % drop to help identify elbow
drops = [0] + [100 * (inertias[i-1] - inertias[i]) / inertias[i-1] for i in range(1, len(inertias))]
print("\n  % inertia drop per step:")
for k, d in zip(ks, drops):
    print(f"  k={k:2d}: {d:.1f}%")


# -- Final Clustering ---------------------------------------------------------
print(f"\nFitting final KMeans (k={N_CLUSTERS}, n_init=20)...")
km_final = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_SEED, n_init=20, max_iter=500)
df['Cluster'] = km_final.fit_predict(X_norm)

print("  Cluster size distribution:")
for c, n in df['Cluster'].value_counts().sort_index().items():
    print(f"  Cluster {c:2d}: {n:3d} questions")


# -- Top Terms Per Cluster ----------------------------------------------------
print("\nTop TF-IDF terms per cluster:")
feature_names = vec.get_feature_names_out()
cluster_terms = {}
for c in range(N_CLUSTERS):
    center = km_final.cluster_centers_[c]
    top_idx = center.argsort()[::-1][:20]
    terms = [feature_names[i] for i in top_idx]
    cluster_terms[c] = terms
    print(f"  [{c:2d}] {', '.join(terms[:10])}")


# -- Archetype Name Inference -------------------------------------------------
def infer_archetype(cluster_id, top_terms_str, subcat_str, bs_str):
    """
    Rule-based heuristic archetype naming from cluster's top terms.
    Edit these rules after reviewing fingerprint_cluster_summary.csv.
    Priority: most-specific match wins (order matters).
    """
    t = top_terms_str.lower()

    if any(kw in t for kw in ['pregnant', 'pregnancy', 'prenatal', 'postpartum',
                                'gestational', 'trimester', 'obstetric', 'breastfeed',
                                'lactation', 'fetal', 'neonatal']):
        return 'Obstetric & Perinatal Care'

    if any(kw in t for kw in ['child', 'infant', 'pediatric', 'newborn', 'adolescent',
                                'immunization', 'growth', 'developmental', 'milestone',
                                'autism', 'adhd', 'school']):
        return 'Pediatric Care & Development'

    if any(kw in t for kw in ['elderly', 'nursing home', 'fall', 'dementia', 'cognitive',
                                'frail', 'geriatric', 'older adult', 'functional decline',
                                'assisted living', 'memory', 'confusion']):
        return 'Geriatric & Functional Medicine'

    if any(kw in t for kw in ['emergency', 'acute', 'sudden onset', 'chest pain',
                                'trauma', 'fracture', 'injury', 'urgent', 'shortness',
                                'dyspnea', 'syncope', 'unconscious', 'sepsis', 'shock']):
        return 'Acute / Emergent Presentation'

    if any(kw in t for kw in ['guideline', 'uspstf', 'screen', 'cancer screening',
                                'colon', 'mammogram', 'colonoscopy', 'preventive',
                                'recommendation', 'when should', 'which patients']):
        return 'Screening & Prevention Guidelines'

    if any(kw in t for kw in ['drug', 'medication', 'dose', 'adverse', 'side effect',
                                'interaction', 'prescribed', 'contraindicated', 'antibiotic',
                                'statin', 'anticoagul', 'first-line', 'preferred agent']):
        return 'Pharmacology & Drug Selection'

    if any(kw in t for kw in ['laboratory', 'lab', 'interpret', 'hba1c', 'sodium',
                                'potassium', 'ekg', 'ecg', 'biopsy', 'culture', 'imaging',
                                'ct scan', 'mri', 'ultrasound', 'x-ray',
                                'which test', 'next test', 'order']):
        return 'Diagnostic Workup & Lab Interpretation'

    if any(kw in t for kw in ['depression', 'anxiety', 'suicide', 'mental', 'psychiatric',
                                'alcohol', 'addiction', 'substance', 'therapy', 'counseling',
                                'behavioral', 'phobia', 'ptsd', 'bipolar', 'schizophrenia',
                                'insomnia', 'sleep disorder']):
        return 'Psychiatric & Behavioral Health'

    if any(kw in t for kw in ['diabetes', 'hypertension', 'chronic', 'control',
                                'goal', 'a1c', 'lipid', 'asthma', 'copd',
                                'inhaler', 'heart failure', 'renal disease', 'ckd',
                                'long-term', 'maintenance', 'titrate']):
        return 'Chronic Disease Management'

    if any(kw in t for kw in ['pain', 'back pain', 'knee', 'shoulder', 'hip', 'ankle',
                                'sprain', 'musculoskeletal', 'joint', 'sports', 'tendon',
                                'ligament', 'arthritis', 'gout', 'bursitis']):
        return 'Musculoskeletal & Pain'

    if any(kw in t for kw in ['rash', 'skin', 'lesion', 'dermatitis', 'eczema',
                                'psoriasis', 'acne', 'wound', 'ulcer', 'pruritus',
                                'melanoma', 'basal cell', 'squamous']):
        return 'Dermatologic Conditions'

    if any(kw in t for kw in ['menstrual', 'contraception', 'contraceptive', 'pelvic',
                                'cervical', 'ovarian', 'endometrial', 'menopause',
                                'hormone', 'iud', 'oral contraceptive']):
        return "Women's Health (Non-OB)"

    return 'General Adult Medicine -- Undifferentiated'


# -- Build Cluster Summary ----------------------------------------------------
print("\nBuilding cluster summary table...")
summary_rows = []
for c in range(N_CLUSTERS):
    sub = df[df['Cluster'] == c]
    n = len(sub)
    top_subcat = sub['Subcategory'].value_counts().head(4)
    top_bs     = sub['BodySystem'].value_counts().head(4)
    top_year   = sub['ExamYear'].value_counts().sort_index()
    terms_str  = ', '.join(cluster_terms[c][:15])
    subcat_str = '; '.join([f"{k}({v})" for k, v in top_subcat.items()])
    bs_str     = '; '.join([f"{k}({v})" for k, v in top_bs.items()])
    year_str   = str(dict(top_year))

    archetype = infer_archetype(c, terms_str, subcat_str, bs_str)

    summary_rows.append({
        'Cluster':           c,
        'ArchetypeName':     archetype,
        'Size':              n,
        'PctOfExam':         round(100 * n / len(df), 1),
        'TopTerms':          terms_str,
        'TopSubcategories':  subcat_str,
        'TopBodySystems':    bs_str,
        'YearDistribution':  year_str,
    })

summary_df = pd.DataFrame(summary_rows)

# Map archetype back to question rows
cluster_to_archetype = dict(zip(summary_df['Cluster'], summary_df['ArchetypeName']))
df['ArchetypeName'] = df['Cluster'].map(cluster_to_archetype)

print("\nArchetype assignments:")
for _, row in summary_df[['Cluster', 'Size', 'PctOfExam', 'ArchetypeName']].iterrows():
    print(f"  [{row['Cluster']:2d}] n={row['Size']:3d} ({row['PctOfExam']:4.1f}%)  {row['ArchetypeName']}")


# -- UMAP Projection ----------------------------------------------------------
print(f"\nRunning UMAP (SVD({SVD_COMPS}) -> UMAP(n={UMAP_NEIGH}))...")
svd = TruncatedSVD(n_components=SVD_COMPS, random_state=RANDOM_SEED)
X_svd = svd.fit_transform(X_norm)
print(f"  SVD explained variance: {svd.explained_variance_ratio_.sum():.3f}")

reducer = umap.UMAP(
    n_neighbors=UMAP_NEIGH,
    min_dist=UMAP_MINDIST,
    random_state=RANDOM_SEED,
    metric='cosine',
    n_components=2,
    verbose=False
)
coords = reducer.fit_transform(X_svd)
df['UMAP_X'] = coords[:, 0]
df['UMAP_Y'] = coords[:, 1]
print("  UMAP projection complete.")


# -- Save Outputs -------------------------------------------------------------
print("\nSaving outputs to:", OUT_DIR)

# 1. Full question-level labels (main integration output)
out_labels = df[['QuestionID', 'ExamYear', 'BodySystem', 'Subcategory',
                  'ArchetypeName', 'Cluster', 'UMAP_X', 'UMAP_Y']].copy()
out_labels.to_csv(OUT_DIR / "fingerprint_labels.csv", index=False)
print(f"  [1] fingerprint_labels.csv          {len(out_labels)} rows")

# 2. Cluster summary (review + rename archetypes here)
summary_df.to_csv(OUT_DIR / "fingerprint_cluster_summary.csv", index=False)
print(f"  [2] fingerprint_cluster_summary.csv {len(summary_df)} rows")

# 3. UMAP coords only
umap_df = df[['QuestionID', 'UMAP_X', 'UMAP_Y', 'Cluster', 'ArchetypeName']].copy()
umap_df.to_csv(OUT_DIR / "fingerprint_umap_coords.csv", index=False)
print(f"  [3] fingerprint_umap_coords.csv     {len(umap_df)} rows")

# 4. Elbow data already saved above
print(f"  [4] fingerprint_elbow.csv           {len(elbow_df)} rows")

# 5. JSON archetype map (for downstream enriched doc injection)
json_out = {}
for c, archetype in cluster_to_archetype.items():
    ids = df[df['Cluster'] == c]['QuestionID'].tolist()
    json_out[str(c)] = {
        'archetype':    archetype,
        'n':            len(ids),
        'pct_of_exam':  round(100 * len(ids) / len(df), 1),
        'top_terms':    cluster_terms[c][:15],
        'question_ids': ids,
    }
with open(OUT_DIR / "fingerprint_archetypes.json", 'w') as f:
    json.dump(json_out, f, indent=2)
print(f"  [5] fingerprint_archetypes.json     {N_CLUSTERS} archetypes")


# -- Final Summary ------------------------------------------------------------
print("\n" + "=" * 62)
print("CLUSTERING COMPLETE")
print("=" * 62)
print(f"\nArchetype coverage across {len(df)} questions:")
for _, row in summary_df.sort_values('Size', ascending=False).iterrows():
    bar = 'X' * int(row['PctOfExam'])
    print(f"  {row['ArchetypeName']:<45s} {row['Size']:3d} ({row['PctOfExam']:4.1f}%) {bar}")

print(f"""
Next steps:
  1. Review fingerprint_cluster_summary.csv
     -- Check TopTerms vs ArchetypeName for each cluster
     -- Edit infer_archetype() rules and re-run if names are off
  2. Run fingerprint_dashboard.py to launch interactive UMAP viewer
  3. Merge fingerprint_labels.csv into ABFM_ITE_Master_v2.xlsx
     (add ArchetypeName column via merge_and_rebuild.py)
  4. Inject ArchetypeName tags into BoardPrep enriched doc (v5+)

Outputs in: {OUT_DIR}
""")

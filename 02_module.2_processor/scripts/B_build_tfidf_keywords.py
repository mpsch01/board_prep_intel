"""
Script B: build_tfidf_keywords.py

Runs TF-IDF across all 48 processed transcript .txt files.
Identifies terms distinctive to each session vs. the full corpus.

Output: tfidf_keywords.json
  {
    "02": {
      "session_name": "Peripheral Vascular Disease",
      "top_terms": [
        {"term": "aneurysm", "tfidf": 0.342, "tf_count": 28},
        ...
      ]
    }, ...
  }

Approach:
  - Unigrams + bigrams (single words + two-word phrases)
  - Custom medical stopword list to filter noise
  - Top 40 terms per session by TF-IDF score
"""

import os, re, json
from pathlib import Path
from collections import Counter, defaultdict
import math

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
TXT_DIR      = SCRIPT_DIR.parent / "source" / "aafp_transcripts"
OUT_JSON     = PROJECT_ROOT / "key_data_files" / "tfidf_keywords.json"

# Sessions to include (02-49, skip 50-51 Q&A)
SESSION_RANGE = range(2, 50)

# ── Stopwords ──────────────────────────────────────────────────────────
# General English + medical filler words that appear in every session
STOPWORDS = set("""
a about actually after again ago all also always am an and any are as at
be because been before being between but by can cause could did do does
doing don done down each even ever every few for from get go going gonna
got great have he her here him his how i if in into is it its just know
let like little look make more most much need next no not now of on one
only or other our out over part per really right said same see she should
since so some something talk that the their them then there these they this
those though three through time to too two up us use very was way we well
were what when where which who will with would year years you your
also basically basically board call called cases common course cover discuss
doing especially exam everyone first found give good great hope important
keep kind let little look lot make mean much need next often one part
patient patients people pretty question questions really right see slide
slides something take talk tell thing things think time today topic trying
use used using want way well work
""".split())

# ── Session file map ───────────────────────────────────────────────────
SESSION_NAMES = {
    '02': 'Peripheral Vascular Disease',
    '03': 'Acute Coronary Syndrome & Hyperlipidemia',
    '04': 'Hypertension',
    '05': 'Heart Failure',
    '06': 'Managing Dysrhythmias',
    '07': 'Health Promotion & Prevention',
    '08': 'Epidemiology & Medical Literature',
    '09': 'Managing Common Cutaneous Problems',
    '10': 'Emergency Medicine I',
    '11': 'Emergency Medicine II',
    '12': 'Emergency Medicine III',
    '13': 'Obesity & Metabolic Syndrome',
    '14': 'Diabetes Mellitus',
    '15': 'Endocrine Diseases',
    '16': 'Lower GI Tract Diseases',
    '17': 'Upper GI Tract Diseases',
    '18': 'Geriatrics I',
    '19': 'Geriatrics II',
    '20': 'Geriatrics III',
    '21': 'Hematology Issues',
    '22': 'Fever & Infectious Disease in Children',
    '23': 'STIs Vaginitis & Vaginosis',
    '24': 'Renal Disease I',
    '25': 'Renal Disease II',
    '26': 'Common Neurological Disorders',
    '27': 'Maternity Care I',
    '28': 'Maternity Care II',
    '29': "Women's Health I",
    '30': "Women's Health II",
    '31': 'Musculoskeletal Medicine',
    '32': 'Fracture Care',
    '33': 'Sports Medicine',
    '34': 'Pediatric Orthopedics',
    '35': 'Common ENT Problems',
    '36': 'Management of Chronic Pain',
    '37': 'Common Newborn Issues',
    '38': 'Well-Child & Adolescent Issues',
    '39': 'Behavioral Medicine I - Depression',
    '40': 'Behavioral Medicine II - Bipolar & Anxiety',
    '41': 'Behavioral Medicine III - ADHD Autism OCD',
    '42': 'Pulmonary I - COPD',
    '43': 'Pulmonary II - Asthma',
    '44': 'Pulmonary III - Infections Part 1',
    '45': 'Pulmonary IV - Infections Part 2',
    '46': 'Pulmonary V - Lung Cancer OSA',
    '47': 'The Major Arthritides',
    '48': 'Preoperative Examination',
    '49': 'Urologic Problems',
}

# ── Text processing ────────────────────────────────────────────────────

def clean_text(text):
    """Lowercase, remove punctuation except hyphens in compounds."""
    text = text.lower()
    text = re.sub(r"[''`]s?\b", '', text)       # possessives
    text = re.sub(r'[^\w\s\-]', ' ', text)       # punct → space
    text = re.sub(r'\b\d+\b', '', text)          # standalone numbers
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def tokenize(text):
    """Return list of words, filtered by stopwords and min length."""
    return [w for w in clean_text(text).split()
            if w not in STOPWORDS and len(w) >= 3 and not w.isdigit()]

def get_ngrams(tokens, n):
    """Generate n-grams as underscore-joined strings."""
    return ['_'.join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

def get_all_terms(tokens):
    """Unigrams + bigrams."""
    return tokens + get_ngrams(tokens, 2)


# ── Load all transcripts ───────────────────────────────────────────────

def find_txt(snum):
    """Find transcript file for a session number."""
    prefix = str(int(snum))   # '02' → '2', for matching filenames like '02-...'
    for fname in os.listdir(TXT_DIR):
        if fname.endswith('.txt') and fname.startswith(snum + '-'):
            return os.path.join(TXT_DIR, fname)
    return None

print('Loading transcripts...')
corpus = {}   # snum -> list of terms
for snum, sname in SESSION_NAMES.items():
    fpath = find_txt(snum)
    if not fpath:
        print(f'  WARNING: no file for session {snum}')
        continue
    with open(fpath, encoding='utf-8') as f:
        text = f.read()
    tokens = tokenize(text)
    terms  = get_all_terms(tokens)
    corpus[snum] = terms
    print(f'  {snum}: {len(tokens):5d} tokens -> {len(terms):6d} terms (incl bigrams)')

N_DOCS = len(corpus)
print(f'\nLoaded {N_DOCS} sessions')


# ── TF-IDF ────────────────────────────────────────────────────────────

# Document frequency: how many sessions contain each term
print('\nCalculating document frequencies...')
df = Counter()
for snum, terms in corpus.items():
    for t in set(terms):   # unique per doc
        df[t] += 1

# TF-IDF per session
print('Calculating TF-IDF scores...')
results = {}

for snum, terms in corpus.items():
    total = len(terms)
    if total == 0:
        continue

    tf = Counter(terms)

    scores = {}
    for term, count in tf.items():
        # TF: raw count / total terms in doc
        term_tf = count / total
        # IDF: log(N / df) — terms appearing in all docs get 0
        term_df = df.get(term, 1)
        term_idf = math.log(N_DOCS / term_df)
        scores[term] = term_tf * term_idf

    # Sort by score, take top 60
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:60]

    # Format output — replace underscores back to spaces for bigrams
    top_terms = []
    for term, score in top:
        display = term.replace('_', ' ')
        raw_count = tf[term]
        top_terms.append({
            'term':     display,
            'tfidf':    round(score, 5),
            'tf_count': raw_count
        })

    results[snum] = {
        'session_name': SESSION_NAMES[snum],
        'total_tokens': total,
        'top_terms':    top_terms
    }
    print(f'  {snum}: top term = "{top_terms[0]["term"]}" ({top_terms[0]["tfidf"]:.4f})')


# ── Write output ──────────────────────────────────────────────────────
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f'\nDone. Output: {OUT_JSON}')
print(f'Sessions processed: {len(results)}')

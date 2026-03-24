"""
Script D: build_keyword_library.py

Merges all three sources into a unified session keyword library:
  - Source A: outline_terms.json      (structured topic terms)
  - Source B: tfidf_keywords.json     (distinctive transcript terms)
  - Source C: vtt_time_weights.json   (presenter time-on-topic weights)

Scoring logic per term:
  - tfidf_score:    raw TF-IDF value from Script B
  - time_weight:    fractional session time from Script C (0.0-1.0)
  - in_outline:     bool — does term appear in outline terms? (Script A)
  - composite:      weighted blend used for ranking

  composite = (tfidf_norm * 0.45) + (time_norm * 0.40) + (outline_bonus * 0.15)

  Where:
    tfidf_norm   = tfidf / max_tfidf_in_session   (normalized 0-1)
    time_norm    = time_weight / max_time_in_session
    outline_bonus = 1.0 if term or stem matches outline, else 0.0

Output: session_keyword_library.json
  {
    "02": {
      "session_name": "Peripheral Vascular Disease",
      "duration_sec": 1580,
      "keywords": [
        {
          "term": "aaa",
          "tfidf": 0.0129,
          "tfidf_norm": 1.0,
          "time_sec": 240,
          "time_weight": 0.152,
          "time_norm": 0.96,
          "in_outline": true,
          "composite": 0.921
        }, ...
      ]
    }
  }
"""

import json, re, os

A_JSON = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\raw_files\outline_terms.json'
B_JSON = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\raw_files\tfidf_keywords.json'
C_JSON = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\raw_files\vtt_time_weights.json'
OUT    = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\keyword_library\session_keyword_library.json'

# Load all three sources
with open(A_JSON, encoding='utf-8') as f: outline_data = json.load(f)
with open(B_JSON, encoding='utf-8') as f: tfidf_data   = json.load(f)
with open(C_JSON, encoding='utf-8') as f: time_data    = json.load(f)

print(f'Loaded: {len(outline_data)} outline | {len(tfidf_data)} tfidf | {len(time_data)} time sessions')


# ── Outline term matcher ───────────────────────────────────────────────

def outline_term_set(outline_entry):
    """
    Build a set of normalized (lowercase, stripped) outline terms
    for fast membership testing.
    """
    terms = outline_entry.get('terms', [])
    normalized = set()
    for t in terms:
        normalized.add(t.lower().strip())
        # Also add individual words for partial matching
        for word in t.lower().split():
            if len(word) > 3:
                normalized.add(word)
    return normalized

def in_outline(term, outline_set):
    """
    Check if a term (or its component words) appears in the outline set.
    Bigrams: check full phrase AND each word individually.
    """
    t = term.lower().strip()
    if t in outline_set:
        return True
    # Check each word of bigram
    words = t.split()
    if len(words) > 1:
        return any(w in outline_set for w in words if len(w) > 3)
    return False


# ── Composite scoring ─────────────────────────────────────────────────

def normalize(values):
    """Min-max normalize a list; returns list of 0-1 values."""
    if not values:
        return []
    mn, mx = min(values), max(values)
    if mx == mn:
        return [1.0] * len(values)
    return [(v - mn) / (mx - mn) for v in values]


# ── Main merge loop ───────────────────────────────────────────────────

results = {}

for snum in sorted(tfidf_data.keys()):
    if snum not in time_data:
        print(f'  {snum}: skipping — no time data')
        continue

    sname      = tfidf_data[snum]['session_name']
    top_terms  = tfidf_data[snum]['top_terms']       # [{term, tfidf, tf_count}]
    time_entry = time_data[snum]
    term_weights = time_entry.get('term_weights', {}) # {term: {seconds, weight}}
    duration   = time_entry.get('duration_sec', 0)

    # Build outline set for this session
    ol_entry = outline_data.get(snum, {})
    ol_set   = outline_term_set(ol_entry)

    # Collect raw scores for normalization
    tfidf_vals = [t['tfidf'] for t in top_terms]
    time_vals  = [term_weights.get(t['term'], {}).get('weight', 0.0) for t in top_terms]

    tfidf_norms = normalize(tfidf_vals)
    time_norms  = normalize(time_vals)

    keywords = []
    for i, entry in enumerate(top_terms):
        term        = entry['term']
        tfidf_score = entry['tfidf']
        tf_count    = entry['tf_count']
        tw          = term_weights.get(term, {})
        time_sec    = tw.get('seconds', 0.0)
        time_wt     = tw.get('weight',  0.0)
        outline_hit = in_outline(term, ol_set)

        tn = tfidf_norms[i]
        wn = time_norms[i]
        ob = 1.0 if outline_hit else 0.0

        composite = round((tn * 0.45) + (wn * 0.40) + (ob * 0.15), 4)

        keywords.append({
            'term':       term,
            'tfidf':      tfidf_score,
            'tfidf_norm': round(tn, 4),
            'tf_count':   tf_count,
            'time_sec':   time_sec,
            'time_weight': time_wt,
            'time_norm':  round(wn, 4),
            'in_outline': outline_hit,
            'composite':  composite
        })

    # Re-sort by composite score
    keywords.sort(key=lambda x: x['composite'], reverse=True)

    results[snum] = {
        'session_name': sname,
        'duration_sec': duration,
        'outline_term_count': len(ol_set),
        'keywords': keywords
    }

    top3 = [(k['term'], k['composite']) for k in keywords[:3]]
    print(f"  {snum}: {sname[:40]:40s} | top: {top3[0][0]}({top3[0][1]:.2f}), "
          f"{top3[1][0]}({top3[1][1]:.2f}), {top3[2][0]}({top3[2][1]:.2f})")


# ── Write output ──────────────────────────────────────────────────────
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f'\nDone. Output: {OUT}')
print(f'Sessions in library: {len(results)}')
total_kw = sum(len(v["keywords"]) for v in results.values())
print(f'Total keyword entries: {total_kw}')

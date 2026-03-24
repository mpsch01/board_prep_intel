"""
Script C: build_vtt_time_weights.py

Parses VTT files to calculate time-on-topic weights per session.

Approach:
  1. Parse each VTT into (start_sec, end_sec, text) cue tuples
  2. Merge consecutive cues into ~30-second windows
  3. For each window, check which TF-IDF top terms appear in the text
  4. Accumulate total seconds spoken for each term across all windows
  5. Normalize by session total duration -> fractional time weight (0.0-1.0)

Output: vtt_time_weights.json
  {
    "02": {
      "session_name": "Peripheral Vascular Disease",
      "duration_sec": 1580,
      "term_weights": {
        "aaa": {"seconds": 340, "weight": 0.215},
        "aneurysm": {"seconds": 290, "weight": 0.184},
        ...
      }
    }, ...
  }

Note: A window contributes its full duration to every matched term,
so weights will sum to > 1.0 (terms co-occur within windows).
What matters is relative weight between terms within a session.
"""

import os, re, json
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
VTT_DIR      = SCRIPT_DIR.parent / "source" / "aafp_vtt"          # TODO: VTT files not migrated — pre-computed vtt_time_weights.json in key_data_files/ is the preserved output
TFIDF_IN     = PROJECT_ROOT / "key_data_files" / "tfidf_keywords.json"
OUT_JSON     = PROJECT_ROOT / "key_data_files" / "vtt_time_weights.json"

WINDOW_SEC = 30   # merge cues into ~30-second windows


# ── VTT parser ─────────────────────────────────────────────────────────

def parse_timestamp(ts):
    """Convert HH:MM:SS.mmm or MM:SS.mmm to seconds (float)."""
    ts = ts.strip()
    parts = ts.split(':')
    if len(parts) == 3:
        h, m, s = parts
    else:
        h, m, s = 0, parts[0], parts[1]
    return int(h) * 3600 + int(m) * 60 + float(s)

def parse_vtt(filepath):
    """Return list of (start_sec, end_sec, text) tuples."""
    cues = []
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # Split on blank lines to get cue blocks
    blocks = re.split(r'\n\s*\n', content)
    ts_pattern = re.compile(
        r'(\d{1,2}:\d{2}[:\d]*\.\d+)\s*-->\s*(\d{1,2}:\d{2}[:\d]*\.\d+)'
    )

    for block in blocks:
        lines = block.strip().splitlines()
        ts_line = None
        text_lines = []

        for line in lines:
            m = ts_pattern.search(line)
            if m:
                ts_line = m
            elif ts_line and line and not line.strip().isdigit():
                # Strip VTT tags like <v Presenter> and <b>
                clean = re.sub(r'<[^>]+>', '', line).strip()
                if clean:
                    text_lines.append(clean)

        if ts_line and text_lines:
            start = parse_timestamp(ts_line.group(1))
            end   = parse_timestamp(ts_line.group(2))
            text  = ' '.join(text_lines).lower()
            cues.append((start, end, text))

    return cues


def build_windows(cues, window_sec=30):
    """
    Merge consecutive cues into windows of ~window_sec seconds.
    Returns list of (window_start, window_end, combined_text).
    """
    if not cues:
        return []

    windows = []
    w_start = cues[0][0]
    w_texts = []
    w_end   = cues[0][1]

    for start, end, text in cues:
        if start - w_start >= window_sec:
            windows.append((w_start, w_end, ' '.join(w_texts)))
            w_start = start
            w_texts = [text]
            w_end   = end
        else:
            w_texts.append(text)
            w_end = max(w_end, end)

    # Final window
    if w_texts:
        windows.append((w_start, w_end, ' '.join(w_texts)))

    return windows

# ── Term matcher ───────────────────────────────────────────────────────

def build_term_patterns(top_terms):
    """
    For each top term (unigram or bigram), build a regex pattern.
    Bigrams stored as 'word1 word2' — match with word boundary.
    Returns list of (display_term, compiled_pattern).
    """
    patterns = []
    for entry in top_terms:
        term = entry['term']
        escaped = re.escape(term)
        pat = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
        patterns.append((term, pat))
    return patterns


# ── Main loop ─────────────────────────────────────────────────────────

# Load TF-IDF results for term lists
with open(TFIDF_IN, encoding='utf-8') as f:
    tfidf_data = json.load(f)

# Map session number to VTT filename
def find_vtt(snum):
    prefix = snum + '-'
    for fname in os.listdir(VTT_DIR):
        if fname.endswith('.vtt') and fname.startswith(prefix):
            return os.path.join(VTT_DIR, fname)
    return None

results = {}
print('Processing VTT files...')

for snum, session_data in tfidf_data.items():
    sname     = session_data['session_name']
    top_terms = session_data['top_terms']   # list of {term, tfidf, tf_count}

    vtt_path = find_vtt(snum)
    if not vtt_path:
        print(f'  {snum}: WARNING - no VTT found')
        continue

    # Parse VTT
    cues = parse_vtt(vtt_path)
    if not cues:
        print(f'  {snum}: WARNING - no cues parsed')
        continue

    # Build time windows
    windows = build_windows(cues, WINDOW_SEC)
    total_duration = cues[-1][1] - cues[0][0]   # last end - first start

    # Build patterns for top 40 terms (skip the long tail)
    patterns = build_term_patterns(top_terms[:40])

    # Accumulate seconds per term
    term_seconds = defaultdict(float)

    for w_start, w_end, w_text in windows:
        w_dur = w_end - w_start
        for term, pat in patterns:
            if pat.search(w_text):
                term_seconds[term] += w_dur

    # Build output with normalized weights
    term_weights = {}
    for term, secs in sorted(term_seconds.items(), key=lambda x: x[1], reverse=True):
        weight = secs / total_duration if total_duration > 0 else 0.0
        term_weights[term] = {
            'seconds': round(secs, 1),
            'weight':  round(weight, 4)
        }

    results[snum] = {
        'session_name':  sname,
        'duration_sec':  round(total_duration, 1),
        'window_count':  len(windows),
        'term_weights':  term_weights
    }

    # Print top 5 by time
    top5 = list(term_weights.items())[:5]
    top5_str = ', '.join(f'{t}={v["seconds"]:.0f}s' for t, v in top5)
    print(f'  {snum}: {total_duration/60:.1f}min | {top5_str}')


# ── Write output ──────────────────────────────────────────────────────
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f'\nDone. Output: {OUT_JSON}')
print(f'Sessions processed: {len(results)}')

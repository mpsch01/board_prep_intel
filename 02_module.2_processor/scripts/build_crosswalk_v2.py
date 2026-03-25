import json, os, sys, re, csv
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

# ── PATHS ───────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Active session inserts file — update this constant when a new version is generated
INSERTS = PROJECT_ROOT / "key_data_files" / "session_hy_inserts_v7.json"

# JSON batch directories — add new batch folder here as each is extracted+migrated
# Format: (path, label)
# TODO: not yet migrated — paths point to extracted_json/ subdirs (to be created)
BATCH_DIRS = [
    (PROJECT_ROOT / "extracted_json" / "pre_calibration_archive",        "archive"),
    (PROJECT_ROOT / "extracted_json" / "afp_peds_uspstf_batch",          "afp_batch"),
    (PROJECT_ROOT / "extracted_json" / "id_renal_gi_hep_batch",          "id_renal_gi_hep_batch"),
    (PROJECT_ROOT / "extracted_json" / "jacc_pulm_batch",                "jacc_pulm_batch"),
    (PROJECT_ROOT / "extracted_json" / "neuro_tox_rheum_psych_batch",    "neuro_tox_rheum_psych_batch"),
]

OUT_DIR   = PROJECT_ROOT / "archive_canonical" / "04_reference_data"
OVERRIDES = SCRIPT_DIR / "crosswalk_overrides.json"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load overrides ──────────────────────────────────────────────────────────
with open(OVERRIDES, encoding="utf-8") as f:
    overrides = json.load(f)

GOLD_EXCLUSIONS = set(overrides.get("gold_list_exclusions", []))
NULL_FRAGMENTS  = [e["citation"] for e in overrides.get("null_overrides", []) if "citation" in e]
MANUAL_PINS     = overrides.get("manual_pins", [])

def is_nulled(cit):
    return any(frag.lower() in cit.lower() for frag in NULL_FRAGMENTS)

print(f"[INFO] Gold exclusions: {len(GOLD_EXCLUSIONS)} | Null overrides: {len(NULL_FRAGMENTS)} | Manual pins: {len(MANUAL_PINS)}")

# ── Load sessions ───────────────────────────────────────────────────────────
with open(INSERTS, encoding="utf-8-sig") as f:
    sessions = json.load(f)

session_refs = []
for sid, sess in sessions.items():
    stitle = sess.get("session_title", sid)
    for ref in sess.get("refs", []):
        citation = ref.get("citation","").strip()
        tier     = ref.get("tier","")
        if not citation: continue
        existing = next((r for r in session_refs if r["citation"] == citation), None)
        if existing:
            if sid not in existing["session_ids"]:
                existing["session_ids"].append(sid)
                existing["session_titles"].append(stitle)
        else:
            session_refs.append({"citation": citation, "tier": tier,
                                  "session_ids": [sid], "session_titles": [stitle]})

print(f"[INFO] Citations loaded from inserts: {len(session_refs)}")

# ── Load extracted JSONs (gold list excluded) ───────────────────────────────
extracted = {}
def load_json_dir(dirpath, label):
    dirpath = str(dirpath)
    if not os.path.isdir(dirpath):
        print(f"[WARN] Batch dir not found, skipping: {dirpath}")
        return
    count = 0
    for fname in sorted(os.listdir(dirpath)):
        if not fname.endswith(".json"): continue
        if fname in GOLD_EXCLUSIONS: continue
        if fname == "batch_summary.json": continue
        fpath = os.path.join(dirpath, fname)
        try:
            with open(fpath, encoding="utf-8") as f: d = json.load(f)
            title = d.get("source",{}).get("title","").strip()
            if title:
                extracted[title] = {"label": label, "fname": fname, "fpath": fpath, "data": d}
                count += 1
        except: pass
    print(f"[INFO]   {label}: {count} JSONs loaded")

for dirpath, label in BATCH_DIRS:
    load_json_dir(dirpath, label)

print(f"[INFO] Total matching pool: {len(extracted)} JSONs")

# ── Scoring ─────────────────────────────────────────────────────────────────
def normalize(s):
    return re.sub(r'[^a-z0-9 ]', ' ', s.lower())

def score_match(citation, ext_title):
    c_norm = normalize(citation)
    t_norm = normalize(ext_title)
    t_words = [w for w in t_norm.split() if len(w) > 3]
    if len(t_norm) > 10 and t_norm in c_norm:
        return (100 + len(t_norm), "A_exact")
    if len(t_words) >= 4:
        for i in range(len(t_words) - 3):
            phrase = " ".join(t_words[i:i+4])
            if phrase in c_norm:
                return (50 + len(phrase), "B_title_run")
    return (0, None)

# ── Build candidate matches ─────────────────────────────────────────────────
citation_candidates = {}
for ref in session_refs:
    cit = ref["citation"]
    if is_nulled(cit):
        citation_candidates[cit] = []
        continue
    candidates = []
    for ext_title, info in extracted.items():
        score, quality = score_match(cit, ext_title)
        if score > 0:
            candidates.append((score, quality, ext_title, info))
    candidates.sort(reverse=True)
    citation_candidates[cit] = candidates

# ── Greedy deduplication (Must-Read priority first) ─────────────────────────
all_pairs = []
for cit, cands in citation_candidates.items():
    for score, quality, ext_title, info in cands:
        tier = next(r["tier"] for r in session_refs if r["citation"] == cit)
        all_pairs.append((score, quality, cit, ext_title, info, tier))
all_pairs.sort(reverse=True)

assigned_json = {}
assigned_cit  = {}

for tier_filter in [{"Must-Read"}, {"Core","Supplementary","Unmatched"}]:
    for score, quality, cit, ext_title, info, tier in all_pairs:
        if tier not in tier_filter: continue
        if cit in assigned_cit: continue
        if ext_title in assigned_json: continue
        assigned_cit[cit]        = (ext_title, quality, score)
        assigned_json[ext_title] = cit

# ── Apply manual pins ───────────────────────────────────────────────────────
for pin in MANUAL_PINS:
    cit_fragment = pin.get("citation_fragment","")
    json_file    = pin.get("json_file","")
    if not cit_fragment or not json_file: continue
    matched_cit = next((r["citation"] for r in session_refs
                        if cit_fragment.lower() in r["citation"].lower()), None)
    if matched_cit:
        ext_title = next((t for t, i in extracted.items() if i["fname"] == json_file), None)
        if ext_title:
            assigned_cit[matched_cit]  = (ext_title, "manual_pin", 99)
            assigned_json[ext_title]   = matched_cit

# ── Build results ───────────────────────────────────────────────────────────
results = []
for ref in session_refs:
    cit, tier = ref["citation"], ref["tier"]
    if cit in assigned_cit:
        ext_title, quality, score = assigned_cit[cit]
        info = extracted[ext_title]
        results.append({"citation": cit, "tier": tier,
            "session_ids": "|".join(ref["session_ids"]),
            "session_titles": "|".join(ref["session_titles"]),
            "match_status": "MATCHED", "match_quality": quality, "match_score": score,
            "matched_json_title": ext_title, "matched_json_file": info["fname"],
            "matched_json_path": info["fpath"], "matched_label": info["label"]})
    else:
        results.append({"citation": cit, "tier": tier,
            "session_ids": "|".join(ref["session_ids"]),
            "session_titles": "|".join(ref["session_titles"]),
            "match_status": "NO_MATCH", "match_quality": "", "match_score": 0,
            "matched_json_title": "", "matched_json_file": "",
            "matched_json_path": "", "matched_label": ""})

matched   = [r for r in results if r["match_status"] == "MATCHED"]
unmatched = [r for r in results if r["match_status"] == "NO_MATCH"]

# ── QC REPORT ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  CROSSWALK v2 QC REPORT")
print(f"  Pool: {len(extracted)} JSONs  |  Gold excluded: {len(GOLD_EXCLUSIONS)}  |  Nulled: {len(NULL_FRAGMENTS)}")
print("=" * 70)
print(f"\n[1] OVERALL")
print(f"    Citations: {len(results)}  |  Matched: {len(matched)}  |  No match: {len(unmatched)}")
print(f"    A_exact={sum(1 for r in matched if r['match_quality']=='A_exact')}  B_title_run={sum(1 for r in matched if r['match_quality']=='B_title_run')}  manual_pin={sum(1 for r in matched if r['match_quality']=='manual_pin')}")

print(f"\n[2] TIER BREAKDOWN")
for t in ["Must-Read","Core","Supplementary","Unmatched"]:
    tm = sum(1 for r in matched   if r["tier"]==t)
    tu = sum(1 for r in unmatched if r["tier"]==t)
    print(f"    {t:15s}  matched={tm}  no_match={tu}")

print(f"\n[3] MUST-READ DETAIL  (gold list excluded from pool by design)")
for r in [x for x in results if x["tier"]=="Must-Read"]:
    s = "✓" if r["match_status"]=="MATCHED" else "-"
    print(f"    {s}  {r['citation'][:65]}")
    if r["match_status"]=="MATCHED":
        print(f"         -> {r['matched_json_title'][:60]}  [{r['match_quality']}]")

print(f"\n[4] DUPLICATE JSON CHECK")
json_usage = {}
for r in matched:
    json_usage[r["matched_json_file"]] = json_usage.get(r["matched_json_file"],0)+1
dupes = {k:v for k,v in json_usage.items() if v>1}
print(f"    {'✅ No duplicates' if not dupes else f'⚠️  WARNING: {len(dupes)} JSONs matched to multiple citations'}")

print(f"\n[5] B-QUALITY SPOT CHECK (review before doc generation)")
b_matches = [x for x in matched if x["match_quality"]=="B_title_run"]
if not b_matches:
    print(f"    None — all matches are A_exact or manual_pin ✅")
for r in b_matches:
    print(f"    [{r['tier']:12s}] CIT: {r['citation'][:60]}")
    print(f"                   JSN: {r['matched_json_title'][:60]}")
    print()

print(f"\n[6] DISPLACED CITATIONS (had candidate but lost dedup)")
displaced = [(ref["citation"], ref["tier"], citation_candidates[ref["citation"]][0][2],
              citation_candidates[ref["citation"]][0][1])
             for ref in session_refs
             if ref["citation"] not in assigned_cit and citation_candidates[ref["citation"]]]
print(f"    Total displaced: {len(displaced)}")
for cit, tier, ext_title, quality in displaced[:10]:
    print(f"    [{tier:12s}] {cit[:55]}")
    print(f"                   Wanted: {ext_title[:50]}  [{quality}]")

# ── Write CSV ───────────────────────────────────────────────────────────────
OUT_CSV = OUT_DIR / "linked_refs_crosswalk_v2.csv"
fieldnames = ["citation","tier","session_ids","session_titles","match_status",
              "match_quality","match_score","matched_json_title",
              "matched_json_file","matched_json_path","matched_label"]
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(results)

print(f"\n[7] OUTPUT → {OUT_CSV}")
print(f"    {len(matched)} matches written  ({len(results)} total citations)")

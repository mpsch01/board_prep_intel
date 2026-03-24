"""
extract_2025_refs_v3.py
Content-based matching: each master Q-stem is matched to its critique block
using keyword overlap between stem and rationale text.
Outputs ref_2025_extracted.csv and a detailed match_report.txt.
"""
import re, csv, sys
import pandas as pd
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

BASE   = Path(__file__).parent.parent
MASTER = BASE / "03_database" / "ABFM_ITE_Master_v2.xlsx"
TXT    = BASE / "02_working" / "2025_ITE_Critique.txt"
OUT    = BASE / "02_working" / "ref_2025_extracted.csv"
REPORT = BASE / "02_working" / "ref_2025_match_report.txt"

# ── Medical stopwords (high-frequency, non-discriminative) ───────────────────
MED_STOP = {
    'patient','patients','the','a','an','of','in','is','are','was','were',
    'for','to','with','and','or','not','be','been','being','have','has','had',
    'do','does','did','will','would','could','should','may','might','must',
    'that','this','these','those','it','its','which','who','what','when',
    'how','than','then','also','all','any','as','at','by','from','if','no',
    'on','per','up','us','use','used','using','one','two','three','based',
    'treatment','treated','therapy','diagnosis','clinical','disease','condition',
    'history','exam','evaluation','following','most','appropriate','next','step',
    'which','recommended','given','after','before','initial','first','second',
    'primary','secondary','associated','including','risk','factors','symptoms',
    'physical','laboratory','findings','normal','abnormal','elevated','decreased',
    'increased','levels','mg','mg/dl','years','old','male','female','weeks',
    'months','days','hours','present','presents','presenting','indicates',
    'suggest','suggests','indicated','likely','unlikely','significant','signs',
}

def tokenize(text):
    """Extract distinctive medical tokens from text."""
    text = text.lower()
    # Keep alphanumeric + hyphens, split on spaces/punctuation
    tokens = re.findall(r"[a-z][a-z0-9\-']{2,}", text)
    return [t for t in tokens if t not in MED_STOP and len(t) > 3]

def overlap_score(stem_tokens, rationale_tokens):
    """Jaccard-like overlap between two token sets."""
    s1 = set(stem_tokens)
    s2 = set(rationale_tokens)
    if not s1 or not s2:
        return 0.0
    intersection = len(s1 & s2)
    union = len(s1 | s2)
    # Also weight by rare terms (appearing in fewer questions)
    return intersection / max(len(s1), 1)

# ── 1. Load master Q2025 ─────────────────────────────────────────────────────
print("Loading master...")
df = pd.read_excel(MASTER, dtype=str)
q25 = df[df["ExamYear"] == "2025"][
    ["QuestionID", "CorrectAnswer", "ScoringStatus", "QuestionStem"]
].reset_index(drop=True)
print(f"  Q2025 rows: {len(q25)}")

# ── 2. Parse critique blocks ─────────────────────────────────────────────────
print(f"Parsing critique...")
text = TXT.read_text(encoding="utf-8", errors="replace")
blocks_raw = re.split(r'(?=ANSWER:\s+[A-E]\s*[\r\n])', text)

critique_blocks = []
for block in blocks_raw:
    block = block.strip()
    if not block.startswith("ANSWER:"):
        continue
    ans_match = re.match(r'ANSWER:\s+([A-E])', block)
    if not ans_match:
        continue
    answer = ans_match.group(1)

    # Rationale = text between answer line and References section
    rationale = ""
    rat_match = re.search(r'ANSWER:\s+[A-E]\s*[\r\n]+(.*?)(?:References\s*[\r\n]|$)',
                          block, re.DOTALL | re.IGNORECASE)
    if rat_match:
        rationale = rat_match.group(1).strip()

    # References
    ref_text = ""
    ref_match = re.search(r'References\s*[\r\n]+(.*?)$', block,
                          re.DOTALL | re.IGNORECASE)
    if ref_match:
        ref_text = ref_match.group(1).strip()

    raw_refs = [r.strip() for r in ref_text.split('\n') if r.strip()]
    clean_refs = []
    for r in raw_refs:
        if re.match(r'^ANSWER:', r):
            break
        if len(r) > 10:
            clean_refs.append(r)

    critique_blocks.append({
        "idx": len(critique_blocks),
        "answer": answer,
        "rationale": rationale,
        "rationale_tokens": tokenize(rationale),
        "refs": " | ".join(clean_refs),
        "ref_count": len(clean_refs),
        "matched": False
    })

print(f"  Critique blocks: {len(critique_blocks)}")

# ── 3. Build term rarity weights ─────────────────────────────────────────────
# Terms appearing in fewer critique blocks are more discriminative
term_counts = Counter()
for cb in critique_blocks:
    for t in set(cb["rationale_tokens"]):
        term_counts[t] += 1

def weighted_overlap(stem_tokens, rationale_tokens):
    s1 = set(stem_tokens)
    s2 = set(rationale_tokens)
    if not s1:
        return 0.0
    # Weighted: rare terms count more
    score = 0.0
    for t in s1 & s2:
        rarity = 1.0 / max(term_counts[t], 1)
        score += rarity
    # Normalize by max possible score for this stem
    max_score = sum(1.0 / max(term_counts[t], 1) for t in s1 if t in term_counts)
    return score / max(max_score, 1e-9)

# ── 4. Match each master question to best critique block ─────────────────────
print("\nMatching questions to critique blocks...")
assignments = {}
unmatched_q = []
report_lines = ["=== 2025 CONTENT-BASED MATCH REPORT ===\n"]

MATCH_THRESHOLD = 0.15  # require at least 15% weighted overlap

for i, row in q25.iterrows():
    qid   = row["QuestionID"]
    stem  = str(row["QuestionStem"])
    m_ans = str(row["CorrectAnswer"]).strip().upper()
    stem_tok = tokenize(stem)

    # Score all unmatched critique blocks
    scores = []
    for cb in critique_blocks:
        if cb["matched"]:
            continue
        # Answer must match (hard constraint)
        if cb["answer"] != m_ans:
            continue
        score = weighted_overlap(stem_tok, cb["rationale_tokens"])
        scores.append((score, cb["idx"]))

    if not scores:
        # Try without answer constraint (fallback)
        for cb in critique_blocks:
            if cb["matched"]:
                continue
            score = weighted_overlap(stem_tok, cb["rationale_tokens"])
            scores.append((score, cb["idx"]))

    if scores:
        scores.sort(reverse=True)
        best_score, best_idx = scores[0]
        if best_score >= MATCH_THRESHOLD:
            critique_blocks[best_idx]["matched"] = True
            assignments[qid] = {
                "refs": critique_blocks[best_idx]["refs"],
                "score": best_score,
                "crit_ans": critique_blocks[best_idx]["answer"],
                "master_ans": m_ans,
                "ans_match": critique_blocks[best_idx]["answer"] == m_ans
            }
        else:
            # Low confidence — assign best anyway, flag it
            critique_blocks[best_idx]["matched"] = True
            assignments[qid] = {
                "refs": critique_blocks[best_idx]["refs"],
                "score": best_score,
                "crit_ans": critique_blocks[best_idx]["answer"],
                "master_ans": m_ans,
                "ans_match": critique_blocks[best_idx]["answer"] == m_ans,
                "low_confidence": True
            }
            unmatched_q.append((qid, best_score))
    else:
        assignments[qid] = {"refs": "", "score": 0, "low_confidence": True}
        unmatched_q.append((qid, 0))

# ── 5. Report ─────────────────────────────────────────────────────────────────
matched_total   = sum(1 for v in assignments.values() if v.get("refs"))
ans_match_count = sum(1 for v in assignments.values() if v.get("ans_match"))
low_conf        = [qid for qid, s in unmatched_q]
unmatched_crit  = [cb["idx"] for cb in critique_blocks if not cb["matched"]]

report_lines.append(f"Master Q2025 rows:         {len(q25)}")
report_lines.append(f"Critique blocks:           {len(critique_blocks)}")
report_lines.append(f"Assigned refs:             {matched_total}/200")
report_lines.append(f"Answer letter confirmed:   {ans_match_count}/200")
report_lines.append(f"Low-confidence matches:    {len(low_conf)}")
report_lines.append(f"Unmatched critique blocks: {len(unmatched_crit)}")

if low_conf:
    report_lines.append(f"\nLOW CONFIDENCE QUESTIONS:")
    for qid in low_conf:
        v = assignments[qid]
        report_lines.append(f"  {qid} score={v.get('score',0):.3f} "
                           f"m_ans={v.get('master_ans','')} c_ans={v.get('crit_ans','')}")

if unmatched_crit:
    report_lines.append(f"\nUNMATCHED CRITIQUE BLOCKS (indices): {unmatched_crit}")
    for idx in unmatched_crit[:10]:
        cb = critique_blocks[idx]
        report_lines.append(f"  Block {idx}: ans={cb['answer']} refs={cb['refs'][:80]}")

report_text = "\n".join(report_lines)
print(report_text)
REPORT.write_text(report_text, encoding="utf-8")

# ── 6. Write CSV ──────────────────────────────────────────────────────────────
rows = []
for i, row in q25.iterrows():
    qid  = row["QuestionID"]
    info = assignments.get(qid, {})
    rows.append({
        "QuestionID": qid,
        "ExamYear": 2025,
        "References": info.get("refs", ""),
        "RefCount":   len(info["refs"].split(" | ")) if info.get("refs") else 0,
        "MatchScore": round(info.get("score", 0), 4),
        "AnsMatch":   info.get("ans_match", False),
        "LowConf":    info.get("low_confidence", False)
    })

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f,
        fieldnames=["QuestionID","ExamYear","References","RefCount",
                    "MatchScore","AnsMatch","LowConf"])
    writer.writeheader()
    writer.writerows(rows)

with_refs = sum(1 for r in rows if r["References"])
print(f"\nOutput: {OUT}")
print(f"Final:  {with_refs}/200 questions have refs")
print("Done.")

"""
Script 2: generate_hy_inserts.py
For each session in the crosswalk, pulls:
  - Cluster stats (Total_Qs, Trend_slope, high-yield designation)
  - Top 10 question IDs from matched clusters
  - Associated Must-Read and Core references
Output: session_hy_inserts.json (keyed by session number)
"""

import pandas as pd
import json
import os

# --- Paths ---
CROSSWALK_PATH  = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/aafp_integration/02_working/session_cluster_crosswalk.csv'
ITE_ENRICHED    = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/ite_exam/03_database/ABFM_ITE_Enriched.csv'
HY_CLUSTERS     = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/ite_exam/03_database/HighYield_Cluster_Summary.csv'
REF_TIERS       = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/ite_refs/03_database/ITE_Reference_Tiers_Final.csv'
OUTPUT_PATH     = r'C:/Users/mpsch/Desktop/claude_knowledge/board_prep/aafp_integration/02_working/session_hy_inserts.json'

TOP_N_QUESTIONS = 10

# --- Load data ---
crosswalk = pd.read_csv(CROSSWALK_PATH, dtype=str)
ite       = pd.read_csv(ITE_ENRICHED, dtype=str)
hy        = pd.read_csv(HY_CLUSTERS)
refs      = pd.read_csv(REF_TIERS, dtype=str)

# Normalize cluster column name in ite
ite['Subcategory_Cluster'] = ite['Subcategory_Cluster'].fillna('')

# Build cluster -> stats lookup
cluster_stats = {}
for _, row in hy.iterrows():
    cluster_stats[row['Cluster']] = {
        'total_qs': int(row['Total_Qs']),
        'trend_slope': float(row['Trend_slope']),
        'category': row['Category']
    }

# High-yield threshold: top 20 clusters by Total_Qs
hy_sorted = hy.sort_values('Total_Qs', ascending=False)
hy_threshold = int(hy_sorted.iloc[19]['Total_Qs'])  # 20th highest

def is_high_yield(cluster_name):
    stats = cluster_stats.get(cluster_name, {})
    return stats.get('total_qs', 0) >= hy_threshold

def trend_label(slope):
    if slope >= 0.5:
        return 'RISING'
    elif slope <= -0.5:
        return 'DECLINING'
    else:
        return 'STABLE'

# Build reference lookup: ref text -> tier + categories
ref_lookup = {}
for _, row in refs.iterrows():
    ref_lookup[row['CleanRef']] = {
        'tier': row['Tier'],
        'categories': row.get('Categories', ''),
        'citation_count': row.get('CitationCount', ''),
        'unique_years': row.get('UniqueYears', '')
    }

def extract_refs_from_question(ref_string):
    """Parse the References field from ITE enriched — it's free text."""
    if pd.isna(ref_string) or str(ref_string).strip() in ['', 'nan']:
        return []
    refs_raw = str(ref_string)
    # Split on numbered ref patterns like "1)" or just return as single ref
    parts = [refs_raw.strip()]
    return parts

def find_ref_tier(ref_text):
    """Fuzzy-ish match: check if any must-read ref is substring of question ref."""
    for clean_ref, info in ref_lookup.items():
        # Match on author last name + year as a minimal signal
        if info['tier'] == 'Must-Read':
            # Extract first author last name from clean_ref
            first_author = clean_ref.split(',')[0].strip()
            year = ''
            import re
            year_match = re.search(r'\b(20\d{2}|19\d{2})\b', clean_ref)
            if year_match:
                year = year_match.group(1)
            if first_author and first_author.lower() in ref_text.lower():
                if not year or year in ref_text:
                    return 'Must-Read', clean_ref
    return 'Standard', None

# --- Build insert payloads ---
inserts = {}

for _, session_row in crosswalk.iterrows():
    sess_num  = session_row['session_number']
    sess_name = session_row['session_name']
    clusters  = [c.strip() for c in session_row['top_clusters'].split(',')]

    # Aggregate stats across session clusters
    total_qs_session = sum(cluster_stats.get(c, {}).get('total_qs', 0) for c in clusters)
    primary_cluster  = clusters[0]
    primary_stats    = cluster_stats.get(primary_cluster, {})
    session_is_hy    = any(is_high_yield(c) for c in clusters)

    # Pull questions matching any of the session's clusters
    mask = ite['Subcategory_Cluster'].isin(clusters)
    session_qs = ite[mask].copy()

    # Sort by ExamYear descending to prioritize recent questions
    session_qs['ExamYear'] = pd.to_numeric(session_qs['ExamYear'], errors='coerce')
    session_qs = session_qs.sort_values('ExamYear', ascending=False)

    # Take top N unique question IDs
    top_qs = session_qs.head(TOP_N_QUESTIONS)

    # Build question list
    question_list = []
    ref_set = {}  # ref_text -> tier info

    for _, q in top_qs.iterrows():
        qid = str(q['Question ID'])
        year = str(int(q['ExamYear'])) if pd.notna(q['ExamYear']) else 'Unknown'
        cluster = str(q['Subcategory_Cluster'])
        ref_raw = str(q.get('References', ''))

        # Reference tier check
        tier, matched_ref = find_ref_tier(ref_raw)
        ref_entry = {
            'raw': ref_raw[:300] if ref_raw != 'nan' else '',
            'tier': tier,
            'matched_must_read': matched_ref
        }

        question_list.append({
            'question_id': qid,
            'exam_year': year,
            'cluster': cluster,
            'reference': ref_entry
        })

        if ref_raw and ref_raw != 'nan':
            ref_set[ref_raw[:300]] = ref_entry

    # Collect Must-Read refs for this session by category
    session_categories = [c.strip() for c in session_row['primary_categories'].split(',')]
    must_reads_for_session = []
    for _, ref_row in refs[refs['Tier'] == 'Must-Read'].iterrows():
        ref_cats = str(ref_row.get('Categories', ''))
        if any(cat in ref_cats for cat in session_categories):
            must_reads_for_session.append({
                'citation': ref_row['CleanRef'],
                'citation_count': str(ref_row.get('CitationCount', '')),
                'unique_years': str(ref_row.get('UniqueYears', '')),
                'categories': ref_cats
            })

    # Build cluster-level stats summary
    cluster_breakdown = []
    for c in clusters:
        stats = cluster_stats.get(c, {})
        if stats:
            cluster_breakdown.append({
                'cluster': c,
                'total_qs': stats['total_qs'],
                'trend': trend_label(stats['trend_slope']),
                'trend_slope': stats['trend_slope'],
                'high_yield': is_high_yield(c)
            })

    inserts[sess_num] = {
        'session_number': sess_num,
        'session_name': sess_name,
        'is_high_yield': session_is_hy,
        'total_qs_across_clusters': total_qs_session,
        'primary_cluster': primary_cluster,
        'clusters_mapped': clusters,
        'cluster_breakdown': cluster_breakdown,
        'top_questions': question_list,
        'must_read_refs': must_reads_for_session
    }

# --- Write output ---
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(inserts, f, indent=2, ensure_ascii=False)

print(f"Inserts written: {OUTPUT_PATH}")
print(f"Sessions processed: {len(inserts)}")

# Summary report
hy_sessions = [(k, v) for k, v in inserts.items() if v['is_high_yield']]
print(f"\nHigh-yield sessions ({len(hy_sessions)}):")
for sess_num, data in sorted(hy_sessions, key=lambda x: x[1]['total_qs_across_clusters'], reverse=True):
    print(f"  Session {sess_num}: {data['session_name']}")
    print(f"    Total Qs: {data['total_qs_across_clusters']} | Questions pulled: {len(data['top_questions'])} | Must-Reads: {len(data['must_read_refs'])}")

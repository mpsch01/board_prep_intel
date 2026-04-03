"""
# Export Script for AAFP Questions Linked to ITE Dataset

This script generates two CSV outputs from the SQLite database:

1. AAFP Questions linked to the ITE dataset by semantic similarity with a configurable distance threshold.
2. AAFP Questions with question-level citation overlap with the ITE dataset.

Usage:
- Ensure the SQLite database is accessible via the script.
- Adjust the `DISTANCE_THRESHOLD` parameter as needed for the semantic similarity calculation.
- Run the script in an environment with `pandas` installed to avoid issues with CSV creation.
"""

import sqlite3
import pandas as pd

# Configurable distance threshold for semantic similarity
DISTANCE_THRESHOLD = 0.5

# Establish a connection to the SQLite database
conn = sqlite3.connect('path/to/your/database.db')  # Adjust path accordingly

# Query 1: AAFP questions linked to the ITE dataset by semantic similarity
query1 = f"""
SELECT aq.*, aeq.ite_nearest_qid, aeq.ite_nearest_dist
FROM aafp_questions AS aq
JOIN aafp_questions_ite AS aeq ON aq.id = aeq.aafp_qid
WHERE aeq.ite_nearest_dist <= {DISTANCE_THRESHOLD}
"""

df_similarity = pd.read_sql_query(query1, conn)
output_similarity_path = 'outputs/aafp_ite_semantic_similarity.csv'

# Save to CSV
df_similarity.to_csv(output_similarity_path, index=False)
print(f"Saved semantic similarity output to {output_similarity_path}")

# Query 2: AAFP questions with question-level citation overlap
query2 = """
SELECT aq.*, ac.article_id
FROM aafp_questions AS aq
JOIN aafp_citations AS ac ON aq.id = ac.aafp_qid
JOIN articles AS art ON ac.article_id = art.id
JOIN question_ref_pairs AS qrp ON aq.id = qrp.aafp_qid
JOIN questions AS q ON qrp.question_id = q.id
"""

df_overlap = pd.read_sql_query(query2, conn)
output_overlap_path = 'outputs/aafp_ite_citation_overlap.csv'

# Save to CSV

df_overlap.to_csv(output_overlap_path, index=False)
print(f"Saved citation overlap output to {output_overlap_path}")

# Close the database connection
conn.close()
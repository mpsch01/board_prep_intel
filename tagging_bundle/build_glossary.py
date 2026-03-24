import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document
from datetime import date

doc = Document(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\04_outputs\ABFM_ITE_Reference report.docx')
table = doc.tables[4]
headers = [cell.text.strip() for cell in table.rows[0].cells]

rows = []
for row in table.rows[1:]:
    cells = [cell.text.strip() for cell in row.cells]
    rows.append(dict(zip(headers, cells)))

glossary = {
    "_meta": {
        "title": "ABFM ITE Must-Read Reference Glossary",
        "tier": "Gold",
        "source_document": "ABFM_ITE_Reference report.docx",
        "source_table": "Table 5 — Must-Read References",
        "total_refs": len(rows),
        "exam_years_covered": "2020-2025",
        "criteria": "Cited 3+ times across 3+ exam years, OR major guideline cited 2+ times across 2+ years",
        "generated": str(date.today()),
        "tier_label_mapping": {"Must-Read": "Gold", "Core": "Silver", "Supplementary": "Bronze"}
    },
    "references": []
}

for i, r in enumerate(rows):
    body_systems = [s.strip() for s in r["Body System"].split(";")]
    entry = {
        "id": "GOLD-" + str(i + 1).zfill(3),
        "rank": i + 1,
        "citation": r["Reference"],
        "citation_count": int(r["Cites"]),
        "exam_years_cited": int(r["Yrs"]),
        "source_type": r["Source"],
        "body_systems": body_systems,
        "tier": "Gold",
        "tier_legacy": "Must-Read",
        "cri_engine": None,
        "cri_json_path": None,
        "outline_qids": [],
        "notes": ""
    }
    glossary["references"].append(entry)

output_path = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\ite_refs\04_outputs\gold_tier_glossary.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(glossary, f, indent=2, ensure_ascii=False)

print("Written:", output_path)
print("Total entries:", len(glossary["references"]))
print()
for r in glossary["references"]:
    sys.stdout.write("GOLD-" + str(r["rank"]).zfill(3) + " | " + str(r["citation_count"]) + "x/" + str(r["exam_years_cited"]) + "yr | " + ", ".join(r["body_systems"]) + "\n    " + r["citation"][:90] + "\n")

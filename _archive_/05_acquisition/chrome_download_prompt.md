# Chrome Download Prompt — ITE Reference Acquisition

Paste this into the Claude-in-Chrome side panel at the start of each download session.

---

## PROMPT

You are helping me download and rename clinical guideline PDFs for my ABFM board prep library.

**Naming convention:**
`LastName1_LastName2_Year#@#ART-XXXX@#@.pdf`

- `LastName1_LastName2` = first two author surnames only, capitalized
- `Year` = 4-digit publication year
- `#@#ART-XXXX@#@` = the article ID codon — I will give you the ART ID for each download
- If only one author: `LastName_Year#@#ART-XXXX@#@.pdf`
- If no ART ID (article not in my DB): omit the codon entirely → `LastName_Year.pdf`

**For each article I give you:**
1. Tell me the correctly formatted filename
2. I will save the PDF and rename it manually using that filename

**Examples:**
- "Managing Hypertension Using Combination Therapy" — Smith JL, Lennon RP, 2020 — ART-1170
  → `Smith_Lennon_2020#@#ART-1170@#@.pdf`
- "Hip Pain in Adults" — Chamberlain R, 2021 — ART-0230
  → `Chamberlain_2021#@#ART-0230@#@.pdf`
- "ACC/AHA Hypertension Guidelines" — Whelton PK et al., 2017 — not in DB
  → `Whelton_2017.pdf`

Ready. I will now give you articles one at a time.

---

## Notes

- The codon delimiters are asymmetric by design: `#@#` = start, `@#@` = stop
- ART IDs come from `ite_intelligence.db` → `articles.article_id`
- Multiple QIDs per article use `__` separator inside the codon:
  `Smith_Lennon_2020#@#ART-1170__QID-2020-0042@#@.pdf`
  (QID encoding is optional — ART ID alone is sufficient for enrichment lookup)
- Ghost spaces and `.pdf.pdf` double extensions are handled automatically by the parser

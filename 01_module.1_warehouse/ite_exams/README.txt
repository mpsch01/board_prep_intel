ite_source/ — ITE Exam Source PDFs
===================================
Drop zone for ABFM-provided ITE exam PDFs. PDFs land here first — always.
M2 scripts read from this folder; nothing processes a PDF before it's warehoused.

Expected filename format:
    {YEAR}_ITE_Questions.pdf
    {YEAR}_ITE_Critique.pdf

Examples:
    2026_ITE_Questions.pdf
    2026_ITE_Critique.pdf
    2025_ITE_Questions.pdf
    2025_ITE_Critique.pdf

Pipeline entry point (after dropping PDFs here):
    python 02_module.2_processor/scripts/extract_ite_year.py --year 2026 --dry-run
    python 02_module.2_processor/scripts/extract_ite_year.py --year 2026

Migration note:
    2025 PDFs previously lived in 02_module.2_processor/source/ite_source/.
    Move those here. That folder is now retired.

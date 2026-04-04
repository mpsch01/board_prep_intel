@echo off
cd /d "C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL"
if exist ".git\index.lock" del /f ".git\index.lock"
git add -A
git commit -m "feat: ITE PDF pipeline + AAFP QA deliverables + M1 warehouse restructure" -m "- extract_ite_year.py: PDF-native ITE exam extractor (PDF to DB, QID assigned at INSERT)" -m "- classify_ite_year.py: SBERT+XGBoost body system classifier (separated for model load time)" -m "- build_aafp_qa_deliverables.py: 13-file AAFP Q&A generator, 26 files total (DOCX + XLSX, ~100Q each)" -m "- M1 restructure: practice_questions/ and ite_source/ data pools added to warehouse" -m "- repo_pre_severance.md: full 123-script inventory + Option B flatten analysis (path-safe)" -m "- Sweep: archive_canonical -> _archive_, aafp_transcripts renamed, 11 script path fixes" -m "- BATON 035 + 036 written; CLAUDE.md updated" -m "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git log --oneline -4

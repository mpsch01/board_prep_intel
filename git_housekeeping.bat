@echo off
set REPO=C:\Users\mpsch\Desktop\board_prep_intel
set GIT="C:\Program Files\Git\bin\git.exe"
set OUT=%REPO%\git_out.txt

echo === STATUS === > %OUT%
%GIT% -C %REPO% status --short >> %OUT% 2>&1

echo === ADD SCRIPTS === >> %OUT%
%GIT% -C %REPO% add 03_module.3_analyst/scripts/ite_analyzer_v3.py >> %OUT% 2>&1
%GIT% -C %REPO% add 03_module.3_analyst/scripts/ite_report_builder_v2.js >> %OUT% 2>&1
%GIT% -C %REPO% add 03_module.3_analyst/scripts/word_doc_defaults.py >> %OUT% 2>&1
%GIT% -C %REPO% add 03_module.3_analyst/scripts/package.json >> %OUT% 2>&1

echo === ADD DOCS === >> %OUT%
%GIT% -C %REPO% add CLAUDE.md >> %OUT% 2>&1
%GIT% -C %REPO% add README.json >> %OUT% 2>&1
%GIT% -C %REPO% add README_PROJECT.md >> %OUT% 2>&1
%GIT% -C %REPO% add _index.md >> %OUT% 2>&1
%GIT% -C %REPO% add BATON_active_045_20260406_ite_report_builder_overhaul.md >> %OUT% 2>&1
%GIT% -C %REPO% add baton_archive/BATON_active_044_20260405_aafp_pdf_recovery.md >> %OUT% 2>&1

echo === ADD MEMORY === >> %OUT%
%GIT% -C %REPO% add .auto-memory/MEMORY.md >> %OUT% 2>&1
%GIT% -C %REPO% add .auto-memory/project_current_db_state.md >> %OUT% 2>&1
%GIT% -C %REPO% add .auto-memory/project_overhaul_state.md >> %OUT% 2>&1
%GIT% -C %REPO% add auto-memory-copies/MEMORY.md >> %OUT% 2>&1
%GIT% -C %REPO% add auto-memory-copies/project_current_db_state.md >> %OUT% 2>&1
%GIT% -C %REPO% add auto-memory-copies/project_overhaul_state.md >> %OUT% 2>&1

echo === STAGED STATUS === >> %OUT%
%GIT% -C %REPO% status --short >> %OUT% 2>&1

echo === COMMIT === >> %OUT%
%GIT% -C %REPO% commit -m "ITE report builder overhaul + analyzer fixes (BATON 045)" -m "- ite_report_builder_v2.js: 20+ edits — de-identification, compact practice/appendix tables, page-break prevention, removed term key/pathway sections, crossover weaknesses added, ITE Performance Overview added" -m "- ite_analyzer_v3.py: AAFP quota fix (AAFP_MIN_QUESTIONS=4), no_match sentinel deleted from question_icd10 (-66) and clinical_pathways (-49), missed_items_detail and concept_qid_map added" -m "- Housekeeping: BATON 044 retired, BATON 045 written, memory files updated" -m "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>" >> %OUT% 2>&1

echo === FINAL STATUS === >> %OUT%
%GIT% -C %REPO% log --oneline -3 >> %OUT% 2>&1

echo DONE >> %OUT%

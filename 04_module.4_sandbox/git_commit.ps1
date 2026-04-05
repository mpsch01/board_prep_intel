$git = "C:\Program Files\Git\cmd\git.exe"
$repo = "C:\Users\mpsch\Desktop\board_prep_intel"
Set-Location $repo

$files = @(
    "CLAUDE.md",
    "README_PROJECT.md",
    "REPO_MAP.md",
    "_index.md",
    "01_module.1_warehouse/README.json",
    "auto-memory-copies/MEMORY.md",
    "auto-memory-copies/project_current_db_state.md",
    "auto-memory-copies/project_overhaul_state.md",
    "BATON_active_043_20260405_pdf_recovery_skills.md",
    "baton_archive/BATON_active_040_20260405_exa_pdf_pipeline.md",
    "baton_archive/BATON_active_042_20260405_recovery_complete.md",
    "BATON_active_040_20260405_exa_pdf_pipeline.md",
    "01_module.1_warehouse/scripts/maintain/exa_pdf_queue.csv",
    "01_module.1_warehouse/scripts/maintain/exa_pdf_queue.json",
    "01_module.1_warehouse/scripts/maintain/exa_download_results.csv",
    "01_module.1_warehouse/scripts/maintain/pmc_oa_results.csv",
    "01_module.1_warehouse/scripts/maintain/unpaywall_results.csv",
    "04_module.4_sandbox/check_doi.py",
    "04_module.4_sandbox/check_pmc.py",
    "04_module.4_sandbox/check_results.py",
    "04_module.4_sandbox/damage_check.py",
    "04_module.4_sandbox/find_active_state.py",
    "04_module.4_sandbox/fix_scanner.py",
    "04_module.4_sandbox/fix_unicode.py"
)

foreach ($f in $files) {
    & $git add $f
    Write-Host "Added: $f (exit $LASTEXITCODE)"
}

$msg = "housekeeping: BATON 043 -- PDF recovery 527->966, skills built`n`n- 3-step pipeline (exa+pmc+unpaywall) restored PDFs 527->966`n- 14 dupe ART-IDs quarantined in _dupe_archive/`n- BATON 040/042 archived; BATON 043 active`n- New M4 sandbox scripts committed`n- Download pipeline CSVs committed (exa_pdf_queue, results, pmc_oa, unpaywall)`n- Manifest updated: CLAUDE.md, REPO_MAP.md, README_PROJECT.md, _index.md, auto-memory-copies`n- Skills written: session-housekeeping (11-item parallel) + exa-research-search (Phase 1 fixed)`n`nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

& $git commit -m $msg
Write-Host "COMMIT EXIT: $LASTEXITCODE"
& $git log --oneline -3

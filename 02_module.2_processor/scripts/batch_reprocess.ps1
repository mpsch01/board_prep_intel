<#
.SYNOPSIS
    DB-guided batch reprocess — fills extraction blocks using ITE intelligence clues,
    then generates DOCXs for all enriched JSONs.

.DESCRIPTION
    Replacement for the old 3-API-call pipeline. Uses pre-computed DB intelligence
    (concept_tags, question stems, explanations) as extraction guidance, making ONE
    focused Claude call per file instead of three blind ones.

    Two modes:
      Mode A (default): Batch API — 50% cheaper, async (submit/poll/write)
      Mode B (-Sequential): Sequential API — one file at a time, live output

    After extraction, generates DOCXs for all files with populated extraction blocks.

    Pipeline flow:
      DB clue assembly → Claude extraction (1 call) → JSON merge → DOCX generation
      → crosswalk rebuild

.USAGE
    # Batch API mode (recommended for 141 files, ~$4-5):
    cd <project_root>\02_module.2_processor\scripts
    .\batch_reprocess.ps1

    # Poll batch status:
    .\batch_reprocess.ps1 -Poll

    # Write results after batch completes:
    .\batch_reprocess.ps1 -Write

    # Sequential mode (for small batches or testing):
    .\batch_reprocess.ps1 -Sequential -Limit 5

    # DOCX generation only (after extraction is done):
    .\batch_reprocess.ps1 -DocxOnly
#>

param(
    [switch]$Poll,
    [switch]$Write,
    [switch]$Sequential,
    [switch]$DocxOnly,
    [switch]$Force,
    [switch]$DryRun,
    [int]$Limit = 0
)

$ErrorActionPreference = "Continue"

# ── Paths ──────────────────────────────────────────────────────────────
$SCRIPT_DIR   = $PSScriptRoot
$MODULE2      = Split-Path $SCRIPT_DIR -Parent      # 02_module.2_processor/
$PROJECT_ROOT = Split-Path $MODULE2 -Parent         # project root

$JSON_DIR     = "$PROJECT_ROOT\extracted_json"
$DOCX_DIR     = "$PROJECT_ROOT\02_module.2_processor\docx_output"
$EXTRACTOR    = "$PROJECT_ROOT\02_module.2_processor\scripts\db_guided_extractor.py"
$BATCH_EXT    = "$PROJECT_ROOT\02_module.2_processor\scripts\batch_db_extract.py"
$CROSSWALK    = "$PROJECT_ROOT\01_module.1_warehouse\scripts\maintain\build_crosswalk_index.py"
$NODE_PATH    = "$PROJECT_ROOT\node_modules"

# ── API key ────────────────────────────────────────────────────────────
if (-not $env:ANTHROPIC_API_KEY) {
    $regKey = Get-ItemProperty -Path "HKCU:\Environment" -Name "ANTHROPIC_API_KEY" -ErrorAction SilentlyContinue
    if ($regKey) { $env:ANTHROPIC_API_KEY = $regKey.ANTHROPIC_API_KEY }
}
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Host "[ERROR] ANTHROPIC_API_KEY not set." -ForegroundColor Red
    exit 1
}

$env:NODE_PATH = $NODE_PATH
$env:NODE_OPTIONS = "--no-warnings"

# ── Ensure output dirs ────────────────────────────────────────────────
if (!(Test-Path $DOCX_DIR)) { New-Item -ItemType Directory -Path $DOCX_DIR | Out-Null }

# ── Mode: Poll ────────────────────────────────────────────────────────
if ($Poll) {
    Write-Host "Polling batch extraction status..." -ForegroundColor Cyan
    python $BATCH_EXT --poll
    exit $LASTEXITCODE
}

# ── Mode: Write ──────────────────────────────────────────────────────
if ($Write) {
    Write-Host "Writing batch extraction results..." -ForegroundColor Cyan
    python $BATCH_EXT --write
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Extraction complete. Run with -DocxOnly to generate DOCXs." -ForegroundColor Green
    }
    exit $LASTEXITCODE
}

# ── Mode: DOCX Only ─────────────────────────────────────────────────
if ($DocxOnly) {
    Write-Host "=" * 60
    Write-Host "  DOCX GENERATION - All extracted JSONs"
    Write-Host "=" * 60

    $jsons = Get-ChildItem "$JSON_DIR\*_extracted.json"
    $total = $jsons.Count
    $generated = 0
    $skipped = 0
    $failed = 0

    foreach ($jsonFile in $jsons) {
        # Check if extraction block exists
        $content = Get-Content $jsonFile.FullName -Raw | ConvertFrom-Json
        $summary = $content.extraction.summary
        if (-not $summary) {
            $skipped++
            continue
        }

        $docxOut = "$DOCX_DIR\$($jsonFile.BaseName -replace '_extracted$','')_summary.docx"
        try {
            node "$SCRIPT_DIR\build_summary.js" $jsonFile.FullName $docxOut 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $generated++
                Write-Host "  [OK] $($jsonFile.BaseName)" -ForegroundColor Green
            } else {
                $failed++
                Write-Host "  [ERR] $($jsonFile.BaseName)" -ForegroundColor Red
            }
        } catch {
            $failed++
            Write-Host "  [ERR] $($jsonFile.BaseName): $_" -ForegroundColor Red
        }
    }

    # Crosswalk rebuild
    Write-Host ""
    Write-Host "Rebuilding crosswalk index..." -ForegroundColor Yellow
    Set-Location $ROOT
    python $CROSSWALK

    Write-Host ""
    Write-Host "=" * 60
    Write-Host "  DOCX GENERATION COMPLETE"
    Write-Host "  Generated: $generated"
    Write-Host "  Skipped:   $skipped (no extraction)"
    Write-Host "  Failed:    $failed"
    Write-Host "  DOCX dir:  $DOCX_DIR"
    Write-Host "=" * 60
    exit 0
}

# ── Mode: Sequential ─────────────────────────────────────────────────
if ($Sequential) {
    Write-Host "=" * 60
    Write-Host "  DB-GUIDED EXTRACTION - Sequential Mode"
    Write-Host "=" * 60

    $args_list = @("--dir", $JSON_DIR)
    if ($Force) { $args_list += "--force" }
    if ($DryRun) { $args_list += "--dry-run" }
    if ($Limit -gt 0) { $args_list += @("--limit", $Limit) }

    python $EXTRACTOR @args_list

    if ($LASTEXITCODE -eq 0 -and -not $DryRun) {
        Write-Host ""
        Write-Host "Extraction complete. Run with -DocxOnly to generate DOCXs." -ForegroundColor Green
    }
    exit $LASTEXITCODE
}

# ── Mode: Batch API Submit (default) ─────────────────────────────────
Write-Host "=" * 60
Write-Host "  DB-GUIDED EXTRACTION - Batch API Mode (half price)"
Write-Host "=" * 60

$args_list = @("--submit", "--dir", $JSON_DIR)
if ($Force) { $args_list += "--force" }
if ($DryRun) { $args_list += "--dry-run" }
if ($Limit -gt 0) { $args_list += @("--limit", $Limit) }

python $BATCH_EXT @args_list

if ($LASTEXITCODE -eq 0 -and -not $DryRun) {
    Write-Host ""
    Write-Host "Batch submitted. Next steps:" -ForegroundColor Green
    Write-Host "  1. Poll:  .\batch_reprocess.ps1 -Poll"
    Write-Host "  2. Write: .\batch_reprocess.ps1 -Write"
    Write-Host "  3. DOCX:  .\batch_reprocess.ps1 -DocxOnly"
}

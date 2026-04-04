@echo off
setlocal enabledelayedexpansion
title Guideline Extractor
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
set "MODULE2_DIR=%SCRIPT_DIR%..\"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\"
set "NODE_MODULES=%PROJECT_ROOT%node_modules"
set "ENRICHER=%PROJECT_ROOT%02_module.2_processor\scripts\ite_intelligence_enricher.py"
set "CROSSWALK=%PROJECT_ROOT%01_module.1_warehouse\scripts\maintain\build_crosswalk_index.py"
set "NODE_PATH=%NODE_MODULES%"
set "NODE_OPTIONS=--no-warnings"
set "INPUT=%~1"
set "CALIBRATE=0"

REM -- Log file setup
set "LOG_DIR=%SCRIPT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "TS=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "TS=%TS: =0%"
set "LOGFILE=%LOG_DIR%\run_%TS%.log"
echo Guideline Extractor Run Log > "%LOGFILE%"
echo Date: %DATE%  Time: %TIME% >> "%LOGFILE%"
echo Input: %~1 >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM -- Check for --calibrate flag
if "%~2"=="--calibrate" set "CALIBRATE=1"
if "%~1"=="--calibrate" (
    set "CALIBRATE=1"
    set "INPUT=%~2"
)

REM -- First-run auto-calibrate
if not exist "%SCRIPT_DIR%.calibrated" set "CALIBRATE=1"

REM -- Resolve API key
if "%ANTHROPIC_API_KEY%"=="" (
    for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v ANTHROPIC_API_KEY 2^>nul ^| findstr ANTHROPIC_API_KEY') do set "ANTHROPIC_API_KEY=%%B"
)
if "%ANTHROPIC_API_KEY%"=="" (
    echo [ERROR] ANTHROPIC_API_KEY is not set.
    echo [ERROR] ANTHROPIC_API_KEY is not set. >> "%LOGFILE%"
    pause
    exit /b 1
)

REM -- Check input
if "%INPUT%"=="" (
    echo [ERROR] No file or folder provided.
    echo [ERROR] No file or folder provided. >> "%LOGFILE%"
    pause
    exit /b 1
)

REM -- Detect file vs directory
set "ATTR=%~a1"
if "%ATTR:~0,1%"=="d" (
    echo.
    echo  BATCH MODE: %INPUT%
    echo  BATCH MODE: %INPUT% >> "%LOGFILE%"
    set "SUCCESS=0"
    set "FAIL=0"
    set "TOTAL=0"

    for %%F in ("%INPUT%\*.pdf") do set /a TOTAL+=1
    if !TOTAL! equ 0 (
        echo [ERROR] No PDF files found in folder.
        echo [ERROR] No PDF files found in folder. >> "%LOGFILE%"
        pause
        exit /b 1
    )

    for %%D in ("%INPUT%") do set "FOLDER_NAME=%%~nxD"
    set "BATCH_OUT_DIR=%INPUT%\!FOLDER_NAME!-batch"
    if not exist "!BATCH_OUT_DIR!" mkdir "!BATCH_OUT_DIR!"
    echo  Found !TOTAL! PDF file(s)
    echo  Output folder: !FOLDER_NAME!-batch
    echo  Found !TOTAL! PDF file(s) >> "%LOGFILE%"
    echo  Output folder: !FOLDER_NAME!-batch >> "%LOGFILE%"
    echo.

    set "N=0"
    for %%F in ("%INPUT%\*.pdf") do (
        set /a N+=1
        echo  [!N!/!TOTAL!] %%~nxF
        echo  [!N!/!TOTAL!] %%~nxF >> "%LOGFILE%"
        call :process_single "%%F" "!BATCH_OUT_DIR!"
        if errorlevel 1 ( set /a FAIL+=1 ) else ( set /a SUCCESS+=1 )
        echo.
    )
    echo  Batch complete: !SUCCESS! succeeded, !FAIL! failed
    echo  DOCXs saved to: !BATCH_OUT_DIR!
    echo  Log saved to:   %LOGFILE%
    echo  Batch complete: !SUCCESS! succeeded, !FAIL! failed >> "%LOGFILE%"
    echo.
    echo  Rebuilding crosswalk index...
    echo  Rebuilding crosswalk index... >> "%LOGFILE%"
    python "%CROSSWALK%" >> "%LOGFILE%" 2>&1
) else (
    call :process_single "%INPUT%"
    echo.
    echo  Rebuilding crosswalk index...
    echo  Rebuilding crosswalk index... >> "%LOGFILE%"
    python "%CROSSWALK%" >> "%LOGFILE%" 2>&1
    echo.
    echo  Log saved to: %LOGFILE%
    echo  Log saved to: %LOGFILE% >> "%LOGFILE%"
)

echo.
pause
exit /b 0

:process_single
    set "PDF_PATH=%~1"
    set "PDF_NAME=%~n1"
    set "PDF_DIR=%~dp1"
    set "PDF_EXT=%~x1"

    if "%~2"=="" ( set "OUT_DIR=%PDF_DIR%" ) else ( set "OUT_DIR=%~2\" )

    if /i not "%PDF_EXT%"==".pdf" (
        echo    [SKIP] Not a PDF: %~nx1
        echo    [SKIP] Not a PDF: %~nx1 >> "%LOGFILE%"
        exit /b 1
    )

    if "%CALIBRATE%"=="1" ( set "STEPS=6" ) else ( set "STEPS=5" )
    set "JSON_TEMP=%TEMP%\%PDF_NAME%_extracted.json"

    echo    [1/!STEPS!] Extracting clinical content...
    echo    [1/!STEPS!] Extracting clinical content... >> "%LOGFILE%"
    cd /d "%MODULE2_DIR%"
    python -c "import json,sys;sys.path.insert(0,'.');from core.ingestion import ingest_document;r=ingest_document(r'%PDF_PATH%');f=open(r'%JSON_TEMP%','w',encoding='utf-8');json.dump(r,f,indent=2,ensure_ascii=False);f.close();c=r.get('classification',{});print('    Extraction OK: type='+str(c.get('document_type','?'))+' conf='+str(c.get('confidence','?')))" >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo    [ERROR] Python extraction failed
        echo    [ERROR] Python extraction failed >> "%LOGFILE%"
        exit /b 1
    )

    echo    [2/!STEPS!] Synthesizing clinical narrative...
    echo    [2/!STEPS!] Synthesizing clinical narrative... >> "%LOGFILE%"
    node "%SCRIPT_DIR%synthesize.js" "%JSON_TEMP%" >> "%LOGFILE%" 2>&1

    echo    [3/!STEPS!] ITE enrichment...
    echo    [3/!STEPS!] ITE enrichment... >> "%LOGFILE%"
    python "%ENRICHER%" --file "%JSON_TEMP%" >> "%LOGFILE%" 2>&1

    set "DOCX_OUT=%OUT_DIR%%PDF_NAME%_summary.docx"
    echo    [4/!STEPS!] Generating summary DOCX...
    echo    [4/!STEPS!] Generating summary DOCX... >> "%LOGFILE%"
    node "%SCRIPT_DIR%build_summary.js" "%JSON_TEMP%" "%DOCX_OUT%" >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo    [ERROR] DOCX generation failed
        echo    [ERROR] DOCX generation failed >> "%LOGFILE%"
        exit /b 1
    )

    if "%CALIBRATE%"=="1" (
        echo    [5/!STEPS!] Quality check...
        echo    [5/!STEPS!] Quality check... >> "%LOGFILE%"
        python "%SCRIPT_DIR%calibrate.py" "%JSON_TEMP%" >> "%LOGFILE%" 2>&1
        if not exist "%SCRIPT_DIR%.calibrated" echo calibrated> "%SCRIPT_DIR%.calibrated"
    )

    set "JSON_DEST=%PROJECT_ROOT%extracted_json\%PDF_NAME%_extracted.json"
    echo    [!STEPS!/!STEPS!] Persisting enriched JSON...
    echo    [!STEPS!/!STEPS!] Persisting enriched JSON... >> "%LOGFILE%"
    copy "%JSON_TEMP%" "%JSON_DEST%" >> "%LOGFILE%" 2>&1
    if exist "%JSON_DEST%" (
        del "%JSON_TEMP%" 2>nul
        echo    Enriched JSON saved to 03_enriched_JSON\
        echo    Enriched JSON saved to 03_enriched_JSON\ >> "%LOGFILE%"
    ) else (
        echo    [WARNING] JSON copy failed — temp file preserved at %JSON_TEMP%
        echo    [WARNING] JSON copy failed — temp file preserved at %JSON_TEMP% >> "%LOGFILE%"
    )
    echo    Done ^> %PDF_NAME%_summary.docx
    echo    Done ^> %PDF_NAME%_summary.docx >> "%LOGFILE%"
    exit /b 0

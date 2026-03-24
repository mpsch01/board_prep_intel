@echo off
setlocal enabledelayedexpansion
title JSON-Only Extractor
chcp 65001 >nul 2>&1

set "PROJECT_ROOT=C:\Users\mpsch\Desktop\claude_knowledge\abfm_prep\01_guideline_extractor"
set "JSON_OUT=C:\Users\mpsch\Desktop\claude_knowledge\clinical_guidelines\03_enriched_JSON"
set "INPUT=%~1"

if "%INPUT%"=="" (
    echo [ERROR] No folder provided.
    pause & exit /b 1
)

if "%ANTHROPIC_API_KEY%"=="" (
    for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v ANTHROPIC_API_KEY 2^>nul ^| findstr ANTHROPIC_API_KEY') do set "ANTHROPIC_API_KEY=%%B"
)
if "%ANTHROPIC_API_KEY%"=="" (
    echo [ERROR] ANTHROPIC_API_KEY not set.
    pause & exit /b 1
)

set "LOG_DIR=%PROJECT_ROOT%\oneclick\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "TS=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "TS=%TS: =0%"
set "LOGFILE=%LOG_DIR%\json_only_%TS%.log"

echo JSON-Only Extractor > "%LOGFILE%"
echo Date: %DATE% Time: %TIME% >> "%LOGFILE%"
echo Input: %INPUT% >> "%LOGFILE%"

set "TOTAL=0"
for %%F in ("%INPUT%\*.pdf") do set /a TOTAL+=1
if %TOTAL% equ 0 (
    echo [ERROR] No PDF files found in: %INPUT%
    pause & exit /b 1
)

echo.
echo  Input : %INPUT%
echo  Output: %JSON_OUT%
echo  PDFs  : %TOTAL%
echo.

set "SUCCESS=0"
set "FAIL=0"
set "N=0"

for %%F in ("%INPUT%\*.pdf") do (
    set /a N+=1
    set "PDF_NAME=%%~nF"
    set "JSON_TEMP=%TEMP%\%%~nF_extracted.json"

    echo  [!N!/%TOTAL%] %%~nxF
    echo  [!N!/%TOTAL%] %%~nxF >> "%LOGFILE%"

    cd /d "%PROJECT_ROOT%"
    python -c "import json,sys;sys.path.insert(0,'.');from core.ingestion import ingest_document;r=ingest_document(r'%%F');f=open(r'%TEMP%\%%~nF_extracted.json','w',encoding='utf-8');json.dump(r,f,indent=2,ensure_ascii=False);f.close();print('  OK')" >> "%LOGFILE%" 2>&1

    if errorlevel 1 (
        echo    [FAIL] extraction error
        echo    [FAIL] extraction error >> "%LOGFILE%"
        set /a FAIL+=1
    ) else (
        copy "%TEMP%\%%~nF_extracted.json" "%JSON_OUT%\%%~nF_extracted.json" >nul 2>&1
        if errorlevel 1 (
            echo    [FAIL] copy error
            set /a FAIL+=1
        ) else (
            echo    [OK] %%~nF_extracted.json
            echo    [OK] %%~nF_extracted.json >> "%LOGFILE%"
            set /a SUCCESS+=1
        )
        del "%TEMP%\%%~nF_extracted.json" 2>nul
    )
)

echo.
echo  Done: %SUCCESS% succeeded, %FAIL% failed
echo  Log: %LOGFILE%
echo  Done: %SUCCESS% succeeded, %FAIL% failed >> "%LOGFILE%"
echo.
pause
exit /b 0

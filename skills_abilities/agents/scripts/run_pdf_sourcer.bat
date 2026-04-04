@echo off
set "SCRIPT_DIR=%~dp0"

set PATH=%APPDATA%\npm;C:\Program Files\nodejs;%PATH%

cd /d "%SCRIPT_DIR%"
python pdf_sourcer_agent.py
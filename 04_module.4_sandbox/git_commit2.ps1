$git = "C:\Program Files\Git\cmd\git.exe"
Set-Location "C:\Users\mpsch\Desktop\board_prep_intel"
& $git add "01_module.1_warehouse/scripts/maintain/exa_download_results.csv"
& $git add "04_module.4_sandbox/git_commit.ps1"
& $git status --short
& $git commit -m "chore: add git_commit helper + update exa_download_results"
Write-Host "EXIT: $LASTEXITCODE"
& $git log --oneline -3

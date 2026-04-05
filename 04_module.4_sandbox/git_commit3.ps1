$git = "C:\Program Files\Git\cmd\git.exe"
Set-Location "C:\Users\mpsch\Desktop\board_prep_intel"
& $git add "_index.md" "README.json"
& $git commit -m "fix(qc): _index.md BATON ref 040->043; create root README.json"
Write-Host "EXIT: $LASTEXITCODE"
& $git log --oneline -3

$st="C:\Users\tusha\OneDrive\Desktop\Research\backend\data\bench\longqa.status"
while (-not (Select-String -Path $st -Pattern "exported to kaggle-hp" -Quiet)) { Start-Sleep 60 }
$team="$env:USERPROFILE\.kaggle_team"; $env:KAGGLE_CONFIG_DIR=$team
$env:KAGGLE_API_TOKEN=(Get-Content -Raw "$team\access_token").Trim(); $env:KAGGLE_USERNAME=(Get-Content -Raw "$team\username").Trim()
$env:KAGGLE_TAG="-hp"; $env:PYTHONIOENCODING="utf-8"; Set-Location "C:\Users\tusha\OneDrive\Desktop\Research"
& "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe" -u backend/scripts/bench/kaggle_run.py --skip-prepare --until-complete --rounds 3 *> backend\data\bench\kaggle-hp\run4.log

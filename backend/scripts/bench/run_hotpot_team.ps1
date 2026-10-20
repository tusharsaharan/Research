# HotpotQA-500 round on the teammate's Kaggle account (credentials in %USERPROFILE%\.kaggle_team,
# set up by the user). Waits for the 4 compression shards, exports prompts to data/bench/kaggle-hp,
# then runs kaggle_run.py with KAGGLE_TAG=-hp. The token is read from the file at run time only.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $here "..\..\..")
$hp = Join-Path $here "..\..\data\bench\hotpot"
while ((Get-ChildItem "$hp\r2shard*.log" | ForEach-Object { (Select-String -Path $_ -Pattern '^done').Count } | Measure-Object -Sum).Sum -lt 4) {
    Start-Sleep 60
}
$env:PYTHONIOENCODING = "utf-8"
$env:KAGGLE_TAG = "-hp"
& $py (Join-Path $here "hotpot.py") export-kaggle --limit 500 *> "$hp\export_hp.log"
$team = Join-Path $env:USERPROFILE ".kaggle_team"
$env:KAGGLE_CONFIG_DIR = $team
$env:KAGGLE_API_TOKEN = (Get-Content -Raw (Join-Path $team "access_token")).Trim()
$env:KAGGLE_USERNAME = (Get-Content -Raw (Join-Path $team "username")).Trim()
Set-Location $root
& $py -u backend/scripts/bench/kaggle_run.py --skip-prepare --until-complete --rounds 2 *> "$root\backend\data\bench\kaggle-hp\run.log"

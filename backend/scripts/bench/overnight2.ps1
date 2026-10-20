# Overnight 2026-10-20/21: Hinglish-focused graded variants for Belebele, then a Kaggle round on the
# teammate account after the HotpotQA round ends. Status lines go to data/bench/overnight2.status.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path (Join-Path $here "..\..\..")).Path
$bench = Join-Path $root "backend\data\bench"
$st = Join-Path $bench "overnight2.status"
function Say($m) { "$(Get-Date -Format 'HH:mm') $m" | Add-Content $st }
$env:PYTHONIOENCODING = "utf-8"
Say "start: building graded2 (4 shards)"
$procs = foreach ($i in 1..4) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "hybrid_build.py build-graded2 --shard $i/4" `
        -RedirectStandardOutput "$bench\belebele\g2_$i.log" -RedirectStandardError "$bench\belebele\g2_$i.err"
}
$procs | Wait-Process
Say "graded2 built"
# wait for the HotpotQA teammate runner to exit
while (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*kaggle_run.py*' }) { Start-Sleep 120 }
Say "hotpot runner finished"
$env:KAGGLE_TAG = "-hp"
& $py (Join-Path $here "hybrid_build.py") export-graded2 --tag -hp *> "$bench\belebele\g2_export.log"
Say ("exported: " + (Get-Content "$bench\belebele\g2_export.log" -Tail 1))
$team = Join-Path $env:USERPROFILE ".kaggle_team"
$env:KAGGLE_CONFIG_DIR = $team
$env:KAGGLE_API_TOKEN = (Get-Content -Raw (Join-Path $team "access_token")).Trim()
$env:KAGGLE_USERNAME = (Get-Content -Raw (Join-Path $team "username")).Trim()
Set-Location $root
& $py -u backend/scripts/bench/kaggle_run.py --skip-prepare --until-complete --rounds 3 *> "$bench\kaggle-hp\run2.log"
Say "graded2 kaggle round finished"

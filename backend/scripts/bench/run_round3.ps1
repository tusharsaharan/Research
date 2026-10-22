# Round 3: BM25-relevance hybrid + BM25-graded (both languages for Belebele), then teammate Kaggle round.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bench = (Resolve-Path (Join-Path $here "..\..\data\bench")).Path
$st = Join-Path $bench "round3.status"
function Say($m) { "$(Get-Date -Format 'HH:mm') $m" | Add-Content $st }
$env:PYTHONIOENCODING = "utf-8"
New-Item -ItemType Directory -Force "$bench\round3" | Out-Null
$procs = @()
foreach ($set in "belebele", "squad", "meetingbank", "hotpot") {
    $n = if ($set -eq "belebele") { 4 } else { 2 }
    foreach ($i in 1..$n) {
        $procs += Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
            -ArgumentList "baselines2.py build --set $set --shard $i/$n --methods bhybrid,bgraded --out round3" `
            -RedirectStandardOutput "$bench\round3\$set.$i.log" -RedirectStandardError "$bench\round3\$set.$i.err"
    }
}
Say "building ($($procs.Count) procs)"
$procs | Wait-Process
Say "built"
foreach ($s in "belebele", "squad", "meetingbank", "hotpot") {
    & $py (Join-Path $here "baselines2.py") export --set $s --tag=-hp --out round3 *>> $st
}
$team = Join-Path $env:USERPROFILE ".kaggle_team"
$env:KAGGLE_CONFIG_DIR = $team
$env:KAGGLE_API_TOKEN = (Get-Content -Raw (Join-Path $team "access_token")).Trim()
$env:KAGGLE_USERNAME = (Get-Content -Raw (Join-Path $team "username")).Trim()
$env:KAGGLE_TAG = "-hp"
Set-Location (Resolve-Path (Join-Path $here "..\..\..")).Path
Say "kaggle start"
& $py -u backend/scripts/bench/kaggle_run.py --skip-prepare --until-complete --rounds 3 *> "$bench\kaggle-hp\run6.log"
Say "kaggle done"

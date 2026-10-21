# Stronger baselines (LLMLingua-2 large, LongLLMLingua, BM25): build on CPU (3 procs, ~5 GB each), queue on kaggle-hp.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bench = (Resolve-Path (Join-Path $here "..\..\data\bench")).Path
$st = Join-Path $bench "baselines2.status"
function Say($m) { "$(Get-Date -Format 'HH:mm') $m" | Add-Content $st }
$env:PYTHONIOENCODING = "utf-8"
New-Item -ItemType Directory -Force "$bench\baselines2" | Out-Null
function Run($set, $shard) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "baselines2.py build --set $set --shard $shard" `
        -RedirectStandardOutput "$bench\baselines2\$set.$($shard -replace '/','of').log" -RedirectStandardError "$bench\baselines2\$set.$($shard -replace '/','of').err"
}
Say "belebele x3"
(1..3 | ForEach-Object { Run "belebele" "$_/3" }) | Wait-Process
Say "squad, meetingbank, hotpot"
@((Run "squad" "1/1"), (Run "meetingbank" "1/1"), (Run "hotpot" "1/1")) | Wait-Process
Say "built"
foreach ($s in "belebele", "squad", "meetingbank", "hotpot") {
    & $py (Join-Path $here "baselines2.py") export --set $s --tag=-hp *>> $st
}
$team = Join-Path $env:USERPROFILE ".kaggle_team"
$env:KAGGLE_CONFIG_DIR = $team
$env:KAGGLE_API_TOKEN = (Get-Content -Raw (Join-Path $team "access_token")).Trim()
$env:KAGGLE_USERNAME = (Get-Content -Raw (Join-Path $team "username")).Trim()
$env:KAGGLE_TAG = "-hp"
Set-Location (Resolve-Path (Join-Path $here "..\..\..")).Path
Say "kaggle runner start"
& $py -u backend/scripts/bench/kaggle_run.py --skip-prepare --until-complete --rounds 3 *> "$bench\kaggle-hp\run5.log"
Say "kaggle runner done"

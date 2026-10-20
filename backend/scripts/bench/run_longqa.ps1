# Out-of-domain check (frozen hybrid settings): compress 4 datasets on all cores, then queue on kaggle-hp.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bench = (Resolve-Path (Join-Path $here "..\..\data\bench")).Path
$st = Join-Path $bench "longqa.status"
function Say($m) { "$(Get-Date -Format 'HH:mm') $m" | Add-Content $st }
$env:PYTHONIOENCODING = "utf-8"
function Compress($ds) {
    foreach ($i in 1..3) {
        Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
            -ArgumentList "longqa.py compress --ds $ds --shard $i/3" `
            -RedirectStandardOutput "$bench\longqa_$ds\c$i.log" -RedirectStandardError "$bench\longqa_$ds\c$i.err"
    }
}
Say "compress musique + 2wiki"
$a = @(Compress "musique") + @(Compress "2wiki")
while (-not ((Test-Path "$bench\longqa_squad\items.jsonl") -and (Test-Path "$bench\longqa_meetingbank\items.jsonl"))) { Start-Sleep 30 }
Say "compress squad + meetingbank"
$b = @(Compress "squad") + @(Compress "meetingbank")
($a + $b) | Wait-Process
Say "all compressed"
$env:KAGGLE_TAG = "-hp"
foreach ($ds in "musique", "2wiki", "squad", "meetingbank") {
    & $py (Join-Path $here "longqa.py") export-kaggle --ds $ds *>> "$bench\longqa.status"
}
Say "exported to kaggle-hp (the running teammate runner answers them next round)"

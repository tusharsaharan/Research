# Detached CPU job: compress CondaQA passages with all methods (4 resumable shards), then export prompts
# to kaggle/prompts.jsonl so the Kaggle runner answers them in its next round.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$data = Join-Path $here "..\..\data\bench\condaqa"
$env:PYTHONIOENCODING = "utf-8"
$procs = foreach ($i in 1..4) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "condaqa.py compress --shard $i/4" `
        -RedirectStandardOutput "$data\shard$i.log" -RedirectStandardError "$data\shard$i.err"
}
$procs | Wait-Process
& $py (Join-Path $here "condaqa.py") export *> "$data\export.log"
"done $(Get-Date -Format s)" | Out-File "$data\run_condaqa.done"

# Detached CPU job: finish the guarded-compression shards (resumable), then merge
# results and compute meaning similarity. Survives the Claude session ending.
#   Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -File run_guarded.ps1"
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$data = Join-Path $here "..\..\data\bench"
$env:PYTHONIOENCODING = "utf-8"
$methods = "guarded@0.7,guarded@0.5,guarded@0.4,guarded@0.5+tokopt"
$procs = foreach ($i in 1..3) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "compress_eval.py --n 8000 --llmlingua --methods $methods --tag guarded --shard $i/3" `
        -RedirectStandardOutput "$data\gshard$i.log" -RedirectStandardError "$data\gshard$i.err"
}
$procs | Wait-Process
& $py (Join-Path $here "compress_eval.py") --summarize *> "$data\summarize.log"
& $py (Join-Path $here "sem_sim.py") *> "$data\sem_sim.log"
"done $(Get-Date -Format s)" | Out-File "$data\run_guarded.done"

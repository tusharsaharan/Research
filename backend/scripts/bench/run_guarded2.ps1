# Detached CPU job: re-run guarded compression with the digit-word fix (method
# names guarded2@r so they never mix with the pre-fix guarded@r rows). Waits for
# run_sweep.done (RAM), then 3 resumable shards, merge, semantic similarity.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$data = Join-Path $here "..\..\data\bench"
$env:PYTHONIOENCODING = "utf-8"
while (-not (Test-Path "$data\run_sweep.done")) { Start-Sleep -Seconds 120 }
$methods = "guarded2@0.4,guarded2@0.5,guarded2@0.6,guarded2@0.7,guarded2@0.8"
$procs = foreach ($i in 1..3) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "compress_eval.py --n 8000 --llmlingua --methods $methods --tag guarded2 --shard $i/3" `
        -RedirectStandardOutput "$data\g2shard$i.log" -RedirectStandardError "$data\g2shard$i.err"
}
$procs | Wait-Process
& $py (Join-Path $here "compress_eval.py") --summarize *> "$data\summarize.log"
& $py (Join-Path $here "sem_sim.py") *> "$data\sem_sim.log"
"done $(Get-Date -Format s)" | Out-File "$data\run_guarded2.done"

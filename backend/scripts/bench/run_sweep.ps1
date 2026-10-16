# Detached CPU job: compression-rate sweep (rate-distortion curve) for plain vs
# guarded LLMLingua-2. Waits for run_guarded.ps1 to finish (RAM), then runs
# 3 resumable shards, merges, recomputes semantic similarity.
#   Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File run_sweep.ps1"
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$data = Join-Path $here "..\..\data\bench"
$env:PYTHONIOENCODING = "utf-8"
while (-not (Test-Path "$data\run_guarded.done")) { Start-Sleep -Seconds 120 }
$methods = "guarded@0.3,guarded@0.6,guarded@0.8,llmlingua2+spans@0.3,llmlingua2+spans@0.4,llmlingua2+spans@0.6,llmlingua2+spans@0.8"
$procs = foreach ($i in 1..3) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "compress_eval.py --n 8000 --llmlingua --methods $methods --tag sweep --shard $i/3" `
        -RedirectStandardOutput "$data\sshard$i.log" -RedirectStandardError "$data\sshard$i.err"
}
$procs | Wait-Process
& $py (Join-Path $here "compress_eval.py") --summarize *> "$data\summarize.log"
& $py (Join-Path $here "sem_sim.py") *> "$data\sem_sim.log"
"done $(Get-Date -Format s)" | Out-File "$data\run_sweep.done"

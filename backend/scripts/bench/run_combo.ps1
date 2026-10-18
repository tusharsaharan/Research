# Detached CPU job: lexical-safe (2609.13154 replication + Hinglish), lexical-safe+guarded, crf+guarded
# on 8,000 prompts (3 resumable shards), then merge and similarity scoring.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$data = Join-Path $here "..\..\data\bench"
$env:PYTHONIOENCODING = "utf-8"
$methods = "lexical-safe,lexical-safe+guarded@0.5,crf+guarded@0.5"
$procs = foreach ($i in 1..3) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "compress_eval.py --n 8000 --llmlingua --methods $methods --tag combo --shard $i/3" `
        -RedirectStandardOutput "$data\cshard$i.log" -RedirectStandardError "$data\cshard$i.err"
}
$procs | Wait-Process
& $py (Join-Path $here "compress_eval.py") --summarize *> "$data\summarize.log"
& $py (Join-Path $here "method_sim.py") lexical-safe "lexical-safe+guarded@0.5" "crf+guarded@0.5" "guarded2@0.5" "crf+tokopt[o200k]" *> "$data\method_sim.log"
"done $(Get-Date -Format s)" | Out-File "$data\run_combo.done"

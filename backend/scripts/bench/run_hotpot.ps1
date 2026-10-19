# Overnight: compress 500 HotpotQA contexts (4 shards) -> export -> answer 200 items locally with Qwen2.5-1.5B (2 shards) -> grade.
$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$data = Join-Path $here "..\..\data\bench\hotpot"
$env:PYTHONIOENCODING = "utf-8"
$procs = foreach ($i in 1..4) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "hotpot.py compress --limit 500 --shard $i/4" `
        -RedirectStandardOutput "$data\cshard$i.log" -RedirectStandardError "$data\cshard$i.err"
}
$procs | Wait-Process
"compress done $(Get-Date -Format s)" | Out-File "$data\compress.done"
$procs = foreach ($i in 1..2) {
    Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru `
        -ArgumentList "hotpot.py answer --model Qwen/Qwen2.5-1.5B-Instruct --limit 200 --shard $i/2" `
        -RedirectStandardOutput "$data\ashard$i.log" -RedirectStandardError "$data\ashard$i.err"
}
$procs | Wait-Process
& $py (Join-Path $here "hotpot.py") grade --answers "answers.Qwen2.5-1.5B-Instruct.*.jsonl" *> "$data\grade.log"
"done $(Get-Date -Format s)" | Out-File "$data\run_hotpot.done"

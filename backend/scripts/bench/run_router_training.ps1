param([int]$Workers = 14)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot\..\..\..").Path
Set-Location $root
$py = (Get-Command python).Source
$out = "$root\backend\data\bench\router_training"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:HF_HUB_OFFLINE = '1'
$env:PYTHONUTF8 = '1'
$script = "$root\backend\scripts\bench\router_train.py"
$name = 'grades_pair2_paired_gsm8k'
& $py $script --grades grades_pair2.jsonl --paired-gsm8k --prepare
if ($LASTEXITCODE -ne 0) { throw 'Router preparation failed' }
$jobs = @()
foreach ($i in 1..$Workers) {
    $job = Start-Process -WindowStyle Hidden -FilePath $py -ArgumentList @(
        '-u', $script, '--input', "$out\${name}_input.json",
        '--embedding-cache', "$out\${name}_emb.npz", '--shard', "$i/$Workers"
    ) -RedirectStandardOutput "$out\cpu-$i.log" -RedirectStandardError "$out\cpu-$i.err.log" -PassThru
    $job.PriorityClass = 'BelowNormal'
    $jobs += $job
}
foreach ($job in $jobs) { $job.WaitForExit() }
if ($jobs | Where-Object { $_.ExitCode -ne 0 }) { throw 'Router shard failed; see cpu-*.err.log' }
& $py $script --input "$out\${name}_input.json" --embedding-cache "$out\${name}_emb.npz" --merge
if ($LASTEXITCODE -ne 0) { throw 'Router merge failed' }

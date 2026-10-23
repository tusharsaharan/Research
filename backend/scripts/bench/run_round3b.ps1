$ErrorActionPreference = "Continue"
$py = "C:\Users\tusha\AppData\Local\Programs\Python\Python313\python.exe"
$here = "C:\Users\tusha\OneDrive\Desktop\Research\backend\scripts\bench"
$bench = "C:\Users\tusha\OneDrive\Desktop\Research\backend\data\bench"
$st = "$bench\round3.status"
function Say($m) { "$(Get-Date -Format 'HH:mm') $m" | Add-Content $st }
$env:PYTHONIOENCODING = "utf-8"
while (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? { $_.CommandLine -like '*set belebele*' }) { Start-Sleep 60 }
Say "belebele built; next squad+meetingbank (4 procs)"
function Run($set, $i) { $p = Start-Process -FilePath $py -WorkingDirectory $here -WindowStyle Hidden -PassThru -ArgumentList "baselines2.py build --set $set --shard $i/2 --methods bhybrid,bgraded --out round3" -RedirectStandardOutput "$bench\round3\$set.$i.log" -RedirectStandardError "$bench\round3\$set.$i.err"; Start-Sleep 2; $p.PriorityClass = 'BelowNormal'; $p }
@((Run squad 1), (Run squad 2), (Run meetingbank 1), (Run meetingbank 2)) | Wait-Process
Say "hotpot (2 procs)"
@((Run hotpot 1), (Run hotpot 2)) | Wait-Process
Say "built"
foreach ($x in "belebele", "squad", "meetingbank", "hotpot") { & $py "$here\baselines2.py" export --set $x --tag=-hp --out round3 *>> $st }
$team = "$env:USERPROFILE\.kaggle_team"; $env:KAGGLE_CONFIG_DIR = $team
$env:KAGGLE_API_TOKEN = (Get-Content -Raw "$team\access_token").Trim(); $env:KAGGLE_USERNAME = (Get-Content -Raw "$team\username").Trim()
$env:KAGGLE_TAG = "-hp"; Set-Location "C:\Users\tusha\OneDrive\Desktop\Research"
Say "kaggle start"
& $py -u backend/scripts/bench/kaggle_run.py --skip-prepare --until-complete --rounds 3 *> "$bench\kaggle-hp\run6.log"
Say "kaggle done"

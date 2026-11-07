while (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? { $_.CommandLine -like '*baselines2.py build*' }) { Start-Sleep 120 }
$env:PYTHONIOENCODING="utf-8"; Set-Location C:\Users\tusha\OneDrive\Desktop\Research\backend\scripts\bench
foreach ($x in "meetingbank","hotpot") { python baselines2.py export --set $x --tag=-hp *>> ..\..\data\bench\baselines2.status }

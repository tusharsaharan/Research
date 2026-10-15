@echo off
rem Daily benchmark run for Windows Task Scheduler (see README.md).
rem Runs run_daily.py from the repo root and appends output to a dated log.
setlocal
rem Optional first argument: full path to python.exe (Task Scheduler may not see your PATH).
set "PYTHON_EXE=%~1"
if "%PYTHON_EXE%"=="" set "PYTHON_EXE=python"
set "REPO=%~dp0..\..\.."
cd /d "%REPO%"
set "LOGDIR=%REPO%\backend\data\bench\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%d"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo ===== start %DATE% %TIME% ===== >> "%LOGDIR%\daily-%TODAY%.log"
"%PYTHON_EXE%" backend\scripts\bench\run_daily.py >> "%LOGDIR%\daily-%TODAY%.log" 2>&1
echo ===== end %DATE% %TIME% (exit %ERRORLEVEL%) ===== >> "%LOGDIR%\daily-%TODAY%.log"
endlocal

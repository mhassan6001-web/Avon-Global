@echo off
rem AVEN GLOBAL - save a copy of the database into the "backups" folder.
setlocal
cd /d "%~dp0..\.."
if not exist "backups" mkdir "backups"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set STAMP=%%i
docker compose exec -T postgres pg_dump -U aven -d aven_global -Fc > "backups\aven-global-%STAMP%.dump"
if errorlevel 1 (
  echo The backup failed. Is AVEN GLOBAL running?
) else (
  echo Saved backups\aven-global-%STAMP%.dump
  echo Copy this file to another disk or to OneDrive. A backup on the same computer
  echo does not protect you if the computer is lost or its disk fails.
)
pause

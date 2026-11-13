@echo off
rem AVEN GLOBAL - stop the system. Data stays on this computer.
cd /d "%~dp0..\.."
docker compose stop
echo AVEN GLOBAL is stopped. Your data is kept.
pause

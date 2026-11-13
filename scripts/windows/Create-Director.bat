@echo off
rem AVEN GLOBAL - create the first Director sign-in (run once, after starting).
setlocal
cd /d "%~dp0..\.."
set /p EMAIL=Your email address: 
set /p NAME=Your full name: 
echo You will now be asked to choose a password (it is not shown while you type).
docker compose exec backend python -m app.cli create-director --email "%EMAIL%" --name "%NAME%"
echo.
echo Now sign in at http://localhost:3000 and set up two-factor sign-in when asked.
pause

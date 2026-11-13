@echo off
rem AVEN GLOBAL - start the system on this computer (trial use with test data).
rem Needs Docker Desktop to be installed and running.
setlocal
cd /d "%~dp0..\.."

docker info >nul 2>&1
if errorlevel 1 (
  echo.
  echo Docker Desktop is not running.
  echo Install it from https://www.docker.com/products/docker-desktop/ then start it,
  echo wait until it says "Engine running", and run this file again.
  echo.
  pause
  exit /b 1
)

if not exist ".env" copy ".env.example" ".env" >nul

echo Starting AVEN GLOBAL. The first start downloads and builds everything
echo and can take 10 to 20 minutes. Later starts take about a minute.
docker compose up --build -d
if errorlevel 1 (
  echo.
  echo The system did not start. Scroll up to see the error.
  pause
  exit /b 1
)

echo Preparing the database...
docker compose exec -T backend alembic upgrade head
if errorlevel 1 (
  echo The database could not be prepared. Run this file again in a minute.
  pause
  exit /b 1
)

echo.
echo AVEN GLOBAL is running. Opening http://localhost:3000
echo First time only: run Create-Director.bat to make your sign-in.
echo To stop the system, run Stop-AvenGlobal.bat. Your data is kept.
start "" http://localhost:3000
pause

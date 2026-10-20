@echo off
cd /d "%~dp0"
if exist "GoldenEmulator.exe" (
  start "" "%~dp0GoldenEmulator.exe"
  exit /b
)
where py >nul 2>nul
if errorlevel 1 (
  echo Download the Stage 3 Windows ZIP from the GitHub release to run without Python.
  pause
  exit /b 1
)
py -3 "%~dp0GoldenEmulator.py"
if errorlevel 1 pause

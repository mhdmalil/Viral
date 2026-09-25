@echo off
cd /d "%~dp0\.."
if not exist "backend\.venv\Scripts\pythonw.exe" (
  echo Missing backend\.venv. Create it first.
  pause
  exit /b 1
)
start "" "backend\.venv\Scripts\pythonw.exe" "%~dp0desktop_app.py"

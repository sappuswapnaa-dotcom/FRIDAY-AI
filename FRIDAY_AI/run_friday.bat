@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo FRIDAY Python environment not found. Run install_windows.bat first.
  pause
  exit /b 1
)
if not exist .env copy .env.example .env >nul
for /f "tokens=1,* delims==" %%A in ('findstr /b "FRIDAY_MODEL=" .env') do set FRIDAY_MODEL=%%B
start "FRIDAY AI" http://127.0.0.1:8765
.venv\Scripts\python.exe -m uvicorn friday.app:app --app-dir backend --host 127.0.0.1 --port 8765

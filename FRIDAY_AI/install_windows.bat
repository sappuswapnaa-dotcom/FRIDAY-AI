@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (echo Python 3.11+ is required. Install it from python.org and enable PATH.& pause & exit /b 1)
py -3 -m venv .venv
if errorlevel 1 (echo Could not create virtual environment.& pause & exit /b 1)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed.& pause & exit /b 1)
if not exist .env copy .env.example .env >nul
echo.
echo Installation complete. Ensure Ollama is installed and running, then run run_friday.bat.
echo Optional model setup: ollama pull qwen2.5:7b
pause

@echo off
setlocal
cd /d "%~dp0"
title FRIDAY AI - Stop
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" desktop\launcher.py stop
    goto :done
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 desktop\launcher.py stop
    goto :done
)
echo FRIDAY's local Python environment was not found. Nothing was stopped.
:done
echo.
pause
endlocal

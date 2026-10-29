@echo off
setlocal
cd /d "%~dp0"
title FRIDAY AI - Local Startup
where py >nul 2>&1
if not errorlevel 1 (
    py -3.11 -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        py -3.11 desktop\launcher.py start
        goto :done
    )
    py -3.12 -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        py -3.12 desktop\launcher.py start
        goto :done
    )
    py -3 desktop\launcher.py start
    goto :done
)
where python >nul 2>&1
if not errorlevel 1 (
    python desktop\launcher.py start
    goto :done
)
echo Python was not found. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ and enable the Python launcher.
echo No software or Windows security setting was changed.
:done
echo.
pause
endlocal

@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_director.ps1"
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Director process ended with exit code %EXITCODE%.
echo Logs: "%~dp0iidx_director\runtime\director.stdout.log"
echo Error log: "%~dp0iidx_director\runtime\director.stderr.log"
pause
endlocal & exit /b %EXITCODE%

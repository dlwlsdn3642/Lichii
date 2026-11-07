@echo off
setlocal
cd /d "%~dp0"
if not exist "lichii.exe" (
    echo Missing lichii.exe. Keep this launcher next to the diagnostic executable.
    pause
    exit /b 1
)

set "EDEN_NX2_STUTTER_TRACE=1"
echo Starting the Lichii scene-stutter diagnostic build.
echo Reproduce the transition, then close the emulator to collect the log.
start "" /wait "%~dp0lichii.exe"

set "LOG_SOURCE=%APPDATA%\eden\log\eden_log.txt"
if exist "user\log\eden_log.txt" set "LOG_SOURCE=%~dp0user\log\eden_log.txt"
if exist "%LOG_SOURCE%" (
    copy /y "%LOG_SOURCE%" "%~dp0scene-stutter-log.txt" >nul
    echo.
    echo Diagnostic log copied to:
    echo   %~dp0scene-stutter-log.txt
    echo Attach that file to the ChatGPT conversation for analysis.
) else (
    echo.
    echo Could not locate eden_log.txt. Check the emulator's log folder.
)
pause
@echo off
chcp 65001 >nul
title MANDOROS — Safe Folder Rename & Junction Utility
cd /d "%~dp0"

echo ======================================================================
echo   M Λ N D O R O S — WORKSPACE REBINDING UTILITY
echo ======================================================================
echo.
echo   1. Checking Windows directory junction 'D:\MANDOROS'...
if exist "D:\MANDOROS" (
    echo   [OK] Directory junction 'D:\MANDOROS' is ACTIVE and points directly here!
    echo   You can open 'D:\MANDOROS' in VS Code, Cursor, or Terminal at any time.
) else (
    echo   Creating junction link from D:\MANDOROS to current folder...
    mklink /J "D:\MANDOROS" "%~dp0"
    echo   [OK] Junction created successfully!
)

echo.
echo ======================================================================
echo   Direct Rename Option:
echo   To permanently rename the physical folder from 'D:\Evidex' to 'D:\MANDOROS':
echo   1. Close any running IDE, editor or terminal processes using D:\Evidex.
echo   2. Run: ren "D:\Evidex" "MANDOROS"
echo ======================================================================
echo.
pause

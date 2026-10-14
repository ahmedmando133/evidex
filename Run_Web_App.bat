@echo off
chcp 65001 >nul
title MANDOROS — Meta-Analysis & Predictive Engine
cd /d "%~dp0"

echo ======================================================================
echo   M Λ N D O R O S - LAUNCHING LOCAL INTERACTIVE WEB INTERFACE
echo ======================================================================
echo   Starting local server at http://localhost:7860...
echo.

start "" "http://localhost:7860"
python app.py

pause

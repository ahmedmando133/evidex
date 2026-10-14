@echo off
chcp 65001 >nul
title Evidex - Local Web Interface
cd /d "%~dp0"

echo ======================================================================
echo   EVIDEX 2.0 - LAUNCHING LOCAL INTERACTIVE WEB INTERFACE
echo ======================================================================
echo   Starting local server at http://localhost:7860...
echo.

start "" "http://localhost:7860"
python app.py

pause

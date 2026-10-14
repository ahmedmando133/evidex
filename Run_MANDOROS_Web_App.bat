@echo off
chcp 65001 >nul
title MANDOROS — Meta-Analysis Network for Data, Outcomes & Research Optimization Synthesis
cd /d "%~dp0"

echo ======================================================================
echo   M Λ N D O R O S
echo   Meta-Analysis Network for Data, Outcomes & Research Optimization Synthesis
echo ======================================================================
echo   Launching Apple Flagship Web Interface at http://localhost:7860...
echo.

start "" "http://localhost:7860"
python app.py

pause

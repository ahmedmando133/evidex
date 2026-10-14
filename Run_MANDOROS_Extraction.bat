@echo off
chcp 65001 >nul
title MANDOROS — Clinical Trial Stage-1 Extractor
cd /d "%~dp0"

echo ======================================================================
echo   M Λ N D O R O S
echo   Stage-1 Clinical Trial Extraction Engine (PDF to Structured Excel)
echo ======================================================================
echo   Scanning 'data\raw\' for all clinical trial PDF files...
echo.

python -m src.main --all

echo.
echo ======================================================================
echo   Extraction Completed Successfully!
echo   Opening outputs folder...
echo ======================================================================
start "" "%~dp0outputs"
echo.
pause

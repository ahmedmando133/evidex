@echo off
chcp 65001 >nul
title MANDOROS — Meta-Analysis & Predictive Engine
cd /d "%~dp0"

echo ======================================================================
echo   M Λ N D O R O S - AUTOMATIC CLINICAL TRIAL DATA EXTRACTION ENGINE
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

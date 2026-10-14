@echo off
chcp 65001 >nul
title Evidex - Automatic Clinical Trial Extractor
cd /d "%~dp0"

echo ======================================================================
echo   EVIDEX 2.0 - AUTOMATIC CLINICAL TRIAL DATA EXTRACTION ENGINE
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

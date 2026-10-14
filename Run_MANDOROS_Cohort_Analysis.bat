@echo off
chcp 65001 >nul
title MANDOROS — Cohort Meta-Analysis & Predictive Engine
cd /d "%~dp0"

echo ======================================================================
echo   M Λ N D O R O S
echo   Phase-2 Multi-Trial Cohort Meta-Analysis & Predictive Projections
echo ======================================================================
echo.

set /p COHORT="Enter Cohort Subfolder Name under analysis/ (e.g. Mixed_Metabolic_Cohort, Metformin): "
if "%COHORT%"=="" set COHORT=Mixed_Metabolic_Cohort

echo Running MANDOROS meta-analysis for cohort: %COHORT%...
python run.py analyze-cohort --cohort %COHORT%

echo.
echo ======================================================================
echo   Cohort Analysis Complete!
echo   Opening cohort outputs folder...
echo ======================================================================
start "" "%~dp0outputs\analysis\%COHORT%"
echo.
pause

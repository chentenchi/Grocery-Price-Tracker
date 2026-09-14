@echo off

set "PROJECT=C:\Users\chent\Documents\Projects\grocery-price-tracker"
set "PYTHON=C:\Users\chent\anaconda3\envs\grocery-tracker\python.exe"
set "LOG=%PROJECT%\logs\daily_collection.log"

echo. >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo Daily pipeline started: %date% %time% >> "%LOG%"
echo ============================================================ >> "%LOG%"

echo. >> "%LOG%"
echo [STEP 1] Collecting Kroger prices... >> "%LOG%"

"%PYTHON%" "%PROJECT%\scripts\collect_prices.py" >> "%LOG%" 2>&1

if errorlevel 1 (
    echo. >> "%LOG%"
    echo ERROR: Kroger price collection failed. >> "%LOG%"
    echo Pipeline stopped: %date% %time% >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo [STEP 2] Rebuilding Tableau datasets... >> "%LOG%"

"%PYTHON%" "%PROJECT%\scripts\build_tableau_data.py" >> "%LOG%" 2>&1

if errorlevel 1 (
    echo. >> "%LOG%"
    echo ERROR: Tableau data build failed. >> "%LOG%"
    echo Pipeline stopped: %date% %time% >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo DAILY PIPELINE COMPLETE >> "%LOG%"
echo Finished: %date% %time% >> "%LOG%"
echo Exit code: 0 >> "%LOG%"
echo ============================================================ >> "%LOG%"

exit /b 0
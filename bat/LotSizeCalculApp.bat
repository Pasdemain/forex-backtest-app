@echo off
echo Starting Forex Backtest Application...
echo.

REM Navigate to the project directory
cd /d "C:\Fiona\forex-backtest-app"

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Navigate to data folder
cd data

REM Run the Python application
echo Running LotSizeCalcul.py...
python LotSizeCalcul.py

REM Pause to see any output or errors
pause
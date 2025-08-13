@echo off
echo Starting Celery Worker for Windows...
echo.

REM Set Windows-specific environment variable
set FORKED_BY_MULTIPROCESSING=1

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start the Celery worker
echo Starting Celery worker with Windows-compatible settings...
python scripts\start_celery_worker.py

pause 
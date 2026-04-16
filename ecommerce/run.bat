@echo off
REM Script to run the Flask application on Windows

echo Starting ECommerce Platform...
echo =======================================

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if required environment variables are set
if not exist .env (
    echo Warning: .env file not found!
    echo Creating .env file...
)

REM Run the application
echo Starting Flask development server...
echo Access the application at: http://localhost:5000
echo.

python app.py

pause

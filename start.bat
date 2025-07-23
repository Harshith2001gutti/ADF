@echo off
REM Action Item Tracker - Startup Script for Windows
REM This script activates the virtual environment and starts the application

echo 🚀 Starting Action Item Tracker...

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found. Please run setup.py first.
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate

REM Check if .env file exists
if not exist ".env" (
    echo ❌ Configuration file (.env) not found. Please run setup.py first.
    pause
    exit /b 1
)

REM Start the application
echo 🌟 Starting application...
python run.py

pause
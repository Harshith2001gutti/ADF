#!/bin/bash

# Action Item Tracker - Startup Script for Unix/Linux/macOS
# This script activates the virtual environment and starts the application

echo "🚀 Starting Action Item Tracker..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.py first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Configuration file (.env) not found. Please run setup.py first."
    exit 1
fi

# Start the application
echo "🌟 Starting application..."
python run.py
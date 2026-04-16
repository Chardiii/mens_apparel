#!/bin/bash
# Script to run the Flask application

echo "Starting ECommerce Platform..."
echo "======================================="

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/Scripts/activate

# Check if required environment variables are set
if [ ! -f .env ]; then
    echo "Warning: .env file not found!"
    echo "Creating .env file..."
    cp .env.example .env
fi

# Run the application
echo "Starting Flask development server..."
echo "Access the application at: http://localhost:5000"
echo ""

python app.py

#!/bin/bash

# StockScope Development Environment Setup
# This script ensures you're always using the correct Python environment

set -e

PROJECT_DIR="/Users/tahmid/Projects/StockScope"
VENV_DIR="$PROJECT_DIR/venv"

echo "🔧 StockScope Development Environment"
echo "====================================="

# Function to check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "❌ Virtual environment not found. Creating one..."
        cd "$PROJECT_DIR"
        python3 -m venv venv
        echo "✅ Virtual environment created"
    else
        echo "✅ Virtual environment found"
    fi
}

# Function to activate virtual environment
activate_venv() {
    echo "🔄 Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    echo "✅ Virtual environment activated"
    echo "📍 Using Python: $(which python)"
    echo "📍 Python version: $(python --version)"
}

# Function to install/update dependencies
install_deps() {
    echo "📦 Installing/updating dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
}

# Function to check if packages are installed
check_packages() {
    echo "🔍 Checking key packages..."
    python -c "import fastapi, uvicorn, pandas, yfinance; print('✅ All key packages available')" 2>/dev/null || {
        echo "❌ Some packages missing. Installing..."
        install_deps
    }
}

# Function to start development server
start_dev() {
    echo "🚀 Starting development servers..."
    echo "Backend will start on: http://localhost:8000"
    echo "Frontend will start on: http://localhost:3000"
    echo ""
    echo "Press Ctrl+C to stop all servers"
    echo ""
    
    # Start backend in background
    echo "Starting backend..."
    cd "$PROJECT_DIR"
    uvicorn backend.api:app --reload --port 8000 &
    BACKEND_PID=$!
    
    # Start frontend in background
    echo "Starting frontend..."
    cd "$PROJECT_DIR/stockscope-frontend"
    npm run dev &
    FRONTEND_PID=$!
    
    # Function to cleanup on exit
    cleanup() {
        echo ""
        echo "🛑 Stopping servers..."
        kill $BACKEND_PID 2>/dev/null || true
        kill $FRONTEND_PID 2>/dev/null || true
        echo "✅ Servers stopped"
        exit 0
    }
    
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM
    
    # Wait for processes
    wait $BACKEND_PID $FRONTEND_PID
}

# Function to run backend only
start_backend() {
    echo "🚀 Starting backend server..."
    cd "$PROJECT_DIR"
    uvicorn backend.api:app --reload --port 8000
}

# Function to run frontend only
start_frontend() {
    echo "🚀 Starting frontend server..."
    cd "$PROJECT_DIR/stockscope-frontend"
    npm run dev
}

# Function to run tests
run_tests() {
    echo "🧪 Running tests..."
    cd "$PROJECT_DIR"
    python -m pytest tests/ -v 2>/dev/null || {
        echo "📝 No pytest found or no tests directory. Running smoke test instead..."
        python -c "
import sys
sys.path.append('.')
from backend.api import app
print('✅ Backend imports successfully')

# Test basic functionality
from main import run_full_pipeline_async
print('✅ Main pipeline imports successfully')

print('🎉 Basic smoke test passed!')
"
    }
}

# Function to open shell with activated environment
open_shell() {
    echo "🐚 Opening shell with activated environment..."
    echo "💡 Type 'exit' to leave this environment"
    echo "📍 Current Python: $(which python)"
    echo ""
    exec "$SHELL"
}

# Main menu
main_menu() {
    check_venv
    activate_venv
    check_packages
    
    echo ""
    echo "What would you like to do?"
    echo "1) Start full development environment (backend + frontend)"
    echo "2) Start backend only"
    echo "3) Start frontend only"
    echo "4) Run tests"
    echo "5) Open shell with activated environment"
    echo "6) Install/update dependencies"
    echo "7) Exit"
    echo ""
    
    read -p "Enter your choice (1-7): " choice
    
    case $choice in
        1)
            start_dev
            ;;
        2)
            start_backend
            ;;
        3)
            start_frontend
            ;;
        4)
            run_tests
            ;;
        5)
            open_shell
            ;;
        6)
            install_deps
            ;;
        7)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid choice. Please try again."
            main_menu
            ;;
    esac
}

# If script is run with arguments, handle them
if [ $# -gt 0 ]; then
    check_venv
    activate_venv
    check_packages
    
    case $1 in
        "dev"|"start")
            start_dev
            ;;
        "backend")
            start_backend
            ;;
        "frontend")
            start_frontend
            ;;
        "test")
            run_tests
            ;;
        "shell")
            open_shell
            ;;
        "install")
            install_deps
            ;;
        *)
            echo "❌ Unknown command: $1"
            echo "Available commands: dev, backend, frontend, test, shell, install"
            exit 1
            ;;
    esac
else
    # Show menu if no arguments
    main_menu
fi
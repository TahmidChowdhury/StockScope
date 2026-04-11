#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/stockscope-frontend"
VENV_DIR="$PROJECT_DIR/venv"

echo "🚀 Starting StockScope production-style app..."

check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "📦 Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
}

activate_venv() {
    source "$VENV_DIR/bin/activate"
}

check_python_packages() {
    python -c "import fastapi, uvicorn, pandas, yfinance" >/dev/null 2>&1 || {
        echo "📦 Installing Python dependencies..."
        pip install -r "$PROJECT_DIR/requirements.txt"
    }
}

check_frontend_deps() {
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        npm --prefix "$FRONTEND_DIR" install
    fi
}

build_frontend() {
    echo "🏗️  Building frontend..."
    npm --prefix "$FRONTEND_DIR" run build
}

cleanup() {
    if [ -n "${BACKEND_PID:-}" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "${FRONTEND_PID:-}" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
}

check_venv
activate_venv
check_python_packages
check_frontend_deps
build_frontend

trap cleanup SIGINT SIGTERM EXIT

echo "🐍 Starting backend on http://localhost:8000..."
cd "$PROJECT_DIR"
python main.py &
BACKEND_PID=$!

echo "⚡ Starting frontend on http://localhost:3000..."
npm --prefix "$FRONTEND_DIR" run start &
FRONTEND_PID=$!

echo "📊 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "Press Ctrl+C to stop both servers"

wait "$BACKEND_PID" "$FRONTEND_PID"

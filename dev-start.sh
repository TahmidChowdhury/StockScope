#!/bin/bash

# StockScope Development Startup Script
# This script starts both the FastAPI backend and Next.js frontend concurrently

echo "🚀 Starting StockScope Development Environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv venv"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "stockscope-frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd stockscope-frontend && npm install && cd ..
fi

# Function to cleanup background processes on exit
cleanup() {
    echo "🛑 Shutting down servers..."
    pkill -f "uvicorn backend.api:app"
    pkill -f "next dev"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

echo "🐍 Starting FastAPI backend on http://localhost:8000..."
source venv/bin/activate && uvicorn backend.api:app --reload --port 8000 &
BACKEND_PID=$!

echo "⚡ Starting Next.js frontend with Turbopack on http://localhost:3000..."
cd stockscope-frontend && npm run dev &
FRONTEND_PID=$!

echo "✅ Both servers are starting up..."
echo "📊 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
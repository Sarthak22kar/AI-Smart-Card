#!/bin/bash
# Simple script to start the backend

echo "🚀 Starting AI Smart Card Backend..."

cd backend

# Kill any existing backend
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Activate virtual environment and start backend
nohup ./venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000 > server.log 2>&1 &

sleep 3

# Test if it's running
if curl -s http://127.0.0.1:8000/ | grep -q "AI Smart"; then
    echo "✅ Backend is running on http://127.0.0.1:8000"
    echo "✅ Frontend should connect automatically"
    echo ""
    echo "📋 To view logs: tail -f backend/server.log"
    echo "🛑 To stop: lsof -ti:8000 | xargs kill -9"
else
    echo "❌ Backend failed to start. Check backend/server.log"
fi

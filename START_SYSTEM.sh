#!/bin/bash

# ============================================================================
# AI Smart Visiting Card System - Complete Startup Script
# ============================================================================
# This script will:
#   1. Kill any existing backend/frontend processes
#   2. Start the backend server (FastAPI on port 8000)
#   3. Start the frontend dev server (Vite on port 5173)
#   4. Show you the URLs to access the system
# ============================================================================

echo "🚀 Starting AI Smart Visiting Card System..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================================================
# Step 1: Kill existing processes
# ============================================================================
echo "🔄 Stopping any existing processes..."

# Kill uvicorn (backend)
pkill -f "uvicorn main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✅ Stopped existing backend"
else
    echo "  ℹ️  No existing backend found"
fi

# Kill vite/npm (frontend)
pkill -f "vite" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✅ Stopped existing frontend"
else
    echo "  ℹ️  No existing frontend found"
fi

# Wait a moment for processes to fully terminate
sleep 2

# ============================================================================
# Step 2: Check if virtual environment exists
# ============================================================================
if [ ! -d "backend/venv" ]; then
    echo ""
    echo "${RED}❌ ERROR: Virtual environment not found!${NC}"
    echo "Please run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# ============================================================================
# Step 3: Check if node_modules exists
# ============================================================================
if [ ! -d "frontend/node_modules" ]; then
    echo ""
    echo "${YELLOW}⚠️  Frontend dependencies not installed. Installing now...${NC}"
    cd frontend
    npm install
    cd ..
    echo "  ✅ Frontend dependencies installed"
fi

# ============================================================================
# Step 4: Start Backend
# ============================================================================
echo ""
echo "🔧 Starting Backend (FastAPI)..."

cd backend
source venv/bin/activate

# Start backend in background
nohup uvicorn main:app --reload --host 127.0.0.1 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!

cd ..

# Wait and check if backend started successfully
sleep 3

if ps -p $BACKEND_PID > /dev/null; then
    echo "  ${GREEN}✅ Backend started successfully (PID: $BACKEND_PID)${NC}"
    echo "  📍 Backend URL: http://127.0.0.1:8000"
    echo "  📄 Backend logs: backend.log"
else
    echo "  ${RED}❌ Backend failed to start. Check backend.log for errors${NC}"
    exit 1
fi

# ============================================================================
# Step 5: Start Frontend
# ============================================================================
echo ""
echo "🎨 Starting Frontend (Vite)..."

cd frontend

# Start frontend in background
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

cd ..

# Wait and check if frontend started successfully
sleep 3

if ps -p $FRONTEND_PID > /dev/null; then
    echo "  ${GREEN}✅ Frontend started successfully (PID: $FRONTEND_PID)${NC}"
    echo "  📍 Frontend URL: http://localhost:5173"
    echo "  📄 Frontend logs: frontend.log"
else
    echo "  ${RED}❌ Frontend failed to start. Check frontend.log for errors${NC}"
    exit 1
fi

# ============================================================================
# Step 6: Save PIDs for easy stopping later
# ============================================================================
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

# ============================================================================
# Success!
# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "${GREEN}✅ SYSTEM STARTED SUCCESSFULLY!${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📱 Open your browser and go to:"
echo "   ${GREEN}http://localhost:5173${NC}"
echo ""
echo "🔧 Backend API running at:"
echo "   ${GREEN}http://127.0.0.1:8000${NC}"
echo ""
echo "📊 View logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop the system, run:"
echo "   ${YELLOW}./STOP_SYSTEM.sh${NC}"
echo ""
echo "════════════════════════════════════════════════════════════════"

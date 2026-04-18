#!/bin/bash

# ============================================================================
# AI Smart Visiting Card System - Stop Script
# ============================================================================
# This script will gracefully stop both backend and frontend servers
# ============================================================================

echo "🛑 Stopping AI Smart Visiting Card System..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================================================
# Stop using saved PIDs (graceful)
# ============================================================================
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID
        echo "  ${GREEN}✅ Stopped backend (PID: $BACKEND_PID)${NC}"
    else
        echo "  ℹ️  Backend process not running"
    fi
    rm .backend.pid
fi

if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID
        echo "  ${GREEN}✅ Stopped frontend (PID: $FRONTEND_PID)${NC}"
    else
        echo "  ℹ️  Frontend process not running"
    fi
    rm .frontend.pid
fi

# ============================================================================
# Force kill any remaining processes
# ============================================================================
echo ""
echo "🔍 Checking for any remaining processes..."

pkill -f "uvicorn main:app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✅ Killed remaining backend processes"
fi

pkill -f "vite" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✅ Killed remaining frontend processes"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "${GREEN}✅ SYSTEM STOPPED${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "To start again, run: ${GREEN}./START_SYSTEM.sh${NC}"
echo ""

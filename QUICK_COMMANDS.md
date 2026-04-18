# 🎯 Quick Commands Reference

## 🚀 Start Everything
```bash
./START_SYSTEM.sh
```
Then open: **http://localhost:5173**

---

## 🛑 Stop Everything
```bash
./STOP_SYSTEM.sh
```

---

## 🔄 Restart (if you get "Network error")
```bash
./STOP_SYSTEM.sh && ./START_SYSTEM.sh
```

---

## 📊 View Logs
```bash
# Backend logs (OCR processing, errors)
tail -f backend.log

# Frontend logs (build errors, warnings)
tail -f frontend.log
```

---

## ✅ Check if Running
```bash
# Check backend
curl http://127.0.0.1:8000

# Check processes
ps aux | grep -E "(uvicorn|vite)" | grep -v grep
```

---

## 🔧 Manual Start (if scripts don't work)

### Backend:
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (in new terminal):
```bash
cd frontend
npm run dev
```

---

## 🆘 Emergency Stop
```bash
# Kill all backend processes
pkill -f "uvicorn main:app"

# Kill all frontend processes
pkill -f "vite"
pkill -f "npm run dev"
```

---

## 📍 URLs
- **Frontend:** http://localhost:5173
- **Backend API:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

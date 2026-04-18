# 🚀 How to Start/Stop the AI Smart Visiting Card System

## Quick Start

### ✅ Start the System (Backend + Frontend)

```bash
./START_SYSTEM.sh
```

This will:
1. ✅ Kill any existing backend/frontend processes
2. ✅ Start backend on `http://127.0.0.1:8000`
3. ✅ Start frontend on `http://localhost:5173`
4. ✅ Show you the URLs and status

**Then open your browser and go to:** `http://localhost:5173`

---

### 🛑 Stop the System

```bash
./STOP_SYSTEM.sh
```

This will gracefully stop both backend and frontend servers.

---

## 📍 File Locations

Both scripts are saved in the **root directory** of your project:

```
AI_Smart_Card/
├── START_SYSTEM.sh    ← Start script (run this!)
├── STOP_SYSTEM.sh     ← Stop script
├── backend/
│   ├── main.py
│   ├── venv/
│   └── ...
└── frontend/
    ├── package.json
    └── ...
```

---

## 🔧 Troubleshooting

### Problem: "Permission denied" error

**Solution:** Make the scripts executable:
```bash
chmod +x START_SYSTEM.sh STOP_SYSTEM.sh
```

---

### Problem: Backend fails to start

**Check the logs:**
```bash
cat backend.log
```

**Common fixes:**
1. Make sure virtual environment exists:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Check if port 8000 is already in use:
   ```bash
   lsof -i :8000
   # Kill the process if needed
   kill -9 <PID>
   ```

---

### Problem: Frontend fails to start

**Check the logs:**
```bash
cat frontend.log
```

**Common fixes:**
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Check if port 5173 is already in use:
   ```bash
   lsof -i :5173
   # Kill the process if needed
   kill -9 <PID>
   ```

---

### Problem: "Network error: Load failed"

This means the frontend can't connect to the backend.

**Solution:**
1. Stop everything: `./STOP_SYSTEM.sh`
2. Start fresh: `./START_SYSTEM.sh`
3. Wait 5 seconds for both servers to fully start
4. Refresh your browser

**Check if backend is running:**
```bash
curl http://127.0.0.1:8000
# Should return: {"message":"AI Smart Visiting Card API 🚀","version":"3.0.0"}
```

---

## 📊 View Live Logs

### Backend logs (see OCR processing, errors, etc.):
```bash
tail -f backend.log
```

### Frontend logs (see build errors, warnings, etc.):
```bash
tail -f frontend.log
```

Press `Ctrl+C` to stop viewing logs.

---

## 🔄 Restart the System

If you encounter any errors, just restart:

```bash
./STOP_SYSTEM.sh
./START_SYSTEM.sh
```

---

## 📱 Access URLs

After starting:

- **Frontend (User Interface):** http://localhost:5173
- **Backend API:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

---

## ⚙️ What the Scripts Do

### START_SYSTEM.sh
1. Kills any existing uvicorn/vite processes
2. Activates Python virtual environment
3. Starts backend with `uvicorn main:app --reload`
4. Starts frontend with `npm run dev`
5. Saves process IDs for clean shutdown
6. Shows you the URLs and status

### STOP_SYSTEM.sh
1. Reads saved process IDs
2. Gracefully kills backend and frontend
3. Force-kills any remaining processes
4. Cleans up PID files

---

## 🎯 First Time Setup

If this is your first time, make sure you have:

1. **Python virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd ..
   ```

2. **Node.js dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Make scripts executable:**
   ```bash
   chmod +x START_SYSTEM.sh STOP_SYSTEM.sh
   ```

Then run: `./START_SYSTEM.sh`

---

## 💡 Pro Tips

1. **Always use the scripts** instead of manually starting servers - they handle cleanup automatically

2. **Check logs if something fails** - they're saved in `backend.log` and `frontend.log`

3. **If you see "Address already in use"** - the script will automatically kill old processes, but you can also run `./STOP_SYSTEM.sh` first

4. **Backend takes 3-5 seconds to start** - wait for the "✅ Backend started successfully" message before opening the browser

---

## 🆘 Still Having Issues?

1. Stop everything: `./STOP_SYSTEM.sh`
2. Check what's running on the ports:
   ```bash
   lsof -i :8000  # Backend
   lsof -i :5173  # Frontend
   ```
3. Kill any processes manually if needed:
   ```bash
   kill -9 <PID>
   ```
4. Start fresh: `./START_SYSTEM.sh`

---

## ✅ Success Indicators

You'll know the system is running correctly when you see:

```
════════════════════════════════════════════════════════════════
✅ SYSTEM STARTED SUCCESSFULLY!
════════════════════════════════════════════════════════════════

📱 Open your browser and go to:
   http://localhost:5173

🔧 Backend API running at:
   http://127.0.0.1:8000
```

Then open `http://localhost:5173` in your browser and you should see the visiting card scanner interface!

---

**Need help?** Check the logs: `tail -f backend.log` or `tail -f frontend.log`

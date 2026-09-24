












# Chess Arena — Setup Guide

## Prerequisites
- Python 3.11+ (`python --version`)
- Stockfish binary

## Step 1 — Download Stockfish

1. Go to https://stockfishchess.org/download/
2. Download the Windows binary (e.g. `stockfish-windows-x86-64-avx2.exe`)
3. Create the folder: `backend/stockfish/`
4. Rename the binary to `stockfish.exe` and place it at:
   ```
   backend/stockfish/stockfish.exe
   ```

## Step 2 — Create Python virtual environment

```powershell
cd c:\Projects\chess-arena
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

## Step 3 — Run the backend

```powershell
uvicorn backend.main:app --reload --port 8000
```

The API will be live at http://localhost:8000
Interactive docs at http://localhost:8000/docs

## Step 4 — Open the frontend

Open `frontend/index.html` directly in your browser, OR visit http://localhost:8000
(FastAPI serves the frontend as static files too).

## Verify it works

- http://localhost:8000/health → `{"status":"ok",...}`
- http://localhost:8000/api/engine/eval → returns eval for starting position
- http://localhost:8000/docs → Swagger UI with all endpoints

## Docker (optional)

```powershell
docker-compose up --build
```

Then open http://localhost:8000

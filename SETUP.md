# Chess Arena — Production Setup & Deployment Guide

This guide covers running Chess Arena locally, launching the complete Docker Compose monitoring stack, and deploying to free-tier cloud platforms (Vercel & Render).

---

## 🚀 1. Local Development Quickstart

### Prerequisites
- Python 3.12+
- Stockfish chess engine binary (optional for local mock testing, required for local engine play)

### Setup Steps
```powershell
# 1. Navigate to workspace
cd c:\Projects\chess-arena

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Run all unit tests
pytest backend/tests/ -v

# 4. Start the FastAPI backend
uvicorn backend.main:app --reload --port 8000
```
* **Frontend**: Open `http://localhost:8000` (or `frontend/index.html`).
* **API Documentation**: Visit `http://localhost:8000/docs`.
* **Telemetry Metrics**: Visit `http://localhost:8000/metrics`.

---

## 🐳 2. Self-Hosted Docker Compose Stack (Backend + Prometheus + Grafana)

Run the entire system in an isolated containerized environment:
```bash
docker-compose up --build
```
* **Backend Application**: `http://localhost:8000`
* **Prometheus Telemetry**: `http://localhost:9090`
* **Grafana Dashboards**: `http://localhost:3000` (login `admin` / `admin`)

---

## ☁️ 3. Free-Tier Cloud Deployment

### A. Deploy Frontend to Vercel (Free)
1. Push your code to GitHub.
2. Link the repository on [Vercel](https://vercel.com).
3. The included `vercel.json` automatically configures static asset serving and proxies all `/api/*` calls to your cloud backend without CORS issues.

### B. Deploy Backend to Render (Free Web Service)
1. Link your GitHub repository on [Render](https://render.com).
2. Choose **Web Service** $\to$ **Docker** environment.
3. Select `Dockerfile.backend`. Render automatically builds the container and installs native Linux Stockfish via `apt-get`.
4. Set optional environment variable:
   * `OPENROUTER_API_KEYS`: Comma-separated list of free OpenRouter keys.

---

## 🧪 4. Running Automated Tests

Run the full 53-test integration suite:
```bash
pytest backend/tests/ -v
```
All tests run with zero external network calls and include mocks for local execution without a binary.

# Chess Arena — Setup & Evaluation Guide

A zero-budget, course-aligned AI platform featuring deterministic Stockfish-grounded coaching, local RAG knowledge retrieval, online adaptive difficulty modeling, and empirical performance analytics.

---

## 🚀 1. Local Development Quickstart

### Prerequisites
- **Python**: 3.12+ (standard virtual environment recommended)
- **Stockfish Engine**: (Optional) Automatically falls back to internal pure-Python heuristic $\alpha$-$\beta$ search if Stockfish is not present.

### Setup Steps
```powershell
# 1. Navigate to workspace
cd c:\Projects\chess-arena

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. (Optional) Download Stockfish binary
python scripts/download_stockfish.py

# 4. Start the FastAPI backend & UI server
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

- **Application UI**: Open [http://localhost:8000](http://localhost:8000) in your web browser.
- **Interactive API Documentation (Swagger)**: Visit [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🎮 2. Application Architecture (3 Core Tabs)

Chess Arena is structured around 3 course-aligned tabs:
1. **Play Mode**:
   - Play against an adaptive AI opponent.
   - Live centipawn evaluation bar & winning probability calculation using the standard Lichess logistic model.
   - Dynamic difficulty slider ranging from Beginner (Skill 0 / ~800 Elo) to Master (Skill 20 / ~2800 Elo), or toggle **Auto Difficulty** to let the statistical player model dynamically adapt to your performance.
2. **Coach Mode**:
   - Stockfish-grounded move quality taxonomy: classifies moves into **Best**, **Good**, **Inaccuracy**, **Mistake**, and **Blunder**.
   - Win% delta computation from mover's perspective.
   - Local RAG knowledge retrieval (<1 ms CPU latency) injecting opening theory, tactical motifs, and endgame principles.
   - Multi-tier explanation caching (SQLite $\to$ Local RAG $\to$ KeyRotator LLM).
3. **Analytics Dashboard**:
   - Player KPI summary: Win rate, lifetime record, skill estimate, average centipawn loss (ACPL), and blunder rate.
   - Four interactive Chart.js visualizations: ACPL progression trajectory, move-quality distribution doughnut, opening win rates, and White vs. Black performance asymmetry.

---

## 📊 3. Running Empirical AI Benchmarks

To generate evaluation metrics and empirical data for the course project report:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_ai.py
```

This script runs three empirical benchmarks across 20 standard positions:
1. **Benchmark 1 (State-Space Search)**: Measures latency (ms), branching factor $b$, nodes explored, and $\beta$-cutoffs across search depths.
2. **Benchmark 2 (Adaptive Difficulty)**: Simulates 15 matches across Novice, Club, and Master personas, demonstrating online Ridge regression convergence.
3. **Benchmark 3 (Neuro-Symbolic Latency)**: Compares Deterministic RAG (Tier 1) vs SQLite cache (Tier 2) vs LLM generation (Tier 3), demonstrating 99.8% latency reduction on cache hits.

**Outputs generated**:
- `benchmark_results/evaluation_report.md`: Markdown summary report with KaTeX equations and tables.
- `benchmark_results/benchmark_data.json`: Machine-readable raw metrics.

---

## 🧪 4. Running the Automated Test Suite

Run the full integration test suite with `pytest`:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/ -v
```

All 47 tests execute locally in under 20 seconds with zero external network or cloud dependencies.

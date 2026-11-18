# Chess Arena: Adaptive Chess AI Platform

> **Artificial Intelligence (AI) Final Project**  
> A course-aligned, zero-budget chess platform featuring deterministic Stockfish-grounded move analysis, local RAG knowledge retrieval, online adaptive difficulty modeling, and empirical performance analytics.

---

## 🏛 1. Core Architecture (3 Balanced Tabs)

Chess Arena is structured around three core workspaces aligned with the academic AI curriculum:

```
┌─────────────────────────────────────────────────────────────┐
│                         CHESS ARENA                         │
│   [ ⚔ Play Mode ]    [ 🎓 Coach Mode ]    [ 📊 Analytics ]   │
└─────────────────────────────────────────────────────────────┘
```

1. **⚔ Play Mode**:
   - **Hybrid Engine**: Full UCI Stockfish engine with pure-Python heuristic 1-ply search and evaluation fallback.
   - **Win Probability**: Calibrated using Lichess logistic mapping $W = 50 + 50 \times \left(\frac{2}{1 + e^{-0.00368 \cdot cp}} - 1\right)$.
   - **Adaptive Difficulty**: Auto-adjusts engine skill (0–20, ~800–2800 Elo) to match user strength using continuous online machine learning.

2. **🎓 Coach Mode**:
   - **Deterministic Move Classifier**: Evaluates win% delta from the mover's perspective; classifies moves into **Best**, **Good**, **Inaccuracy**, **Mistake**, and **Blunder**.
   - **Local RAG Grounding**: High-speed (<1 ms CPU) retrieval from curated opening theory, tactical motifs, and endgame principles.
   - **Neuro-Symbolic Multi-Tier Caching**: 3-tier architecture ensuring deterministic truth and sub-millisecond response on cached evaluations.

3. **📊 Analytics Dashboard**:
   - **KPI Metrics**: Real-time win rate, lifetime game record, estimated skill rating, average centipawn loss (ACPL), and blunder rate.
   - **Interactive Visualizations**: 4 responsive Chart.js graphs tracking performance trajectory, move quality distribution, opening repertoire win-rates, and color asymmetry.

---

## 🔬 2. Course Alignment & Algorithmic Foundations

| Academic Rubric Requirement | Chess Arena Implementation | Verification File |
| :--- | :--- | :--- |
| **State-Space Search & Heuristics** | Minimax with Alpha-Beta pruning, capture-first move ordering, material & positional square-table heuristics. | `backend/engine_service.py` |
| **Constraint Satisfaction & Legality** | Strict FEN parsing, king counts, pawn-rank validity, non-turn check validation. | `backend/coach_service.py` |
| **Machine Learning & Adaptation** | Online Ridge Regression mapping player ACPL, blunder rate, and game outcome to target skill level. | `backend/player_model.py` |
| **Knowledge Representation & RAG** | Indexed JSON knowledge bases (`openings.json`, `tactics.json`, `endgames.json`) with keyword & semantic matching. | `backend/rag_service.py` |
| **Neuro-Symbolic AI & Fact Grounding** | Deterministic chess facts verify move quality before prompt construction, completely eliminating LLM hallucinations. | `backend/coach_service.py` |

---

## 📊 3. Empirical AI Evaluation Suite

Run the automated benchmark suite to profile the platform across 20 standard chess test positions:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_ai.py
```

### Key Benchmark Results

1. **State-Space Search & Depth Latency** (Average Branching Factor $b = 29.5$):
   - **Depth 1 (1-ply heuristic)**: 3.7 ms latency | 30.5 nodes explored
   - **Depth 2 (2-ply $\alpha$-$\beta$)**: 17.4 ms latency | 140.2 nodes explored | 27.1 cutoffs
   - **Depth 3 (3-ply $\alpha$-$\beta$)**: 276.3 ms latency | 2,210.1 nodes explored | 166.9 cutoffs
   - *State-Space Reduction*: >90% node reduction achieved by Alpha-Beta pruning.

2. **Neuro-Symbolic Latency & Caching Efficiency**:
   - **Tier 1 (Deterministic Classifier + Local RAG)**: **0.72 ms**
   - **Tier 2 (SQLite Indexed Explanation Cache)**: **1.43 ms**
   - **Tier 3 (External LLM Generation API)**: **1,188 ms**
   - *Speedup Factor*: **831x faster** on cache hits (**99.8% latency reduction**).

---

## 🚀 4. Quickstart Guide

### Prerequisites
- Python 3.12+ (in virtual environment)

```powershell
# 1. Clone repository & navigate
cd c:\Projects\chess-arena

# 2. Run unit tests (47 tests passing)
.\.venv\Scripts\python.exe -m pytest backend/tests/ -v

# 3. Start local development server
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

- **Web Application**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Benchmark Reports**: Generated in `benchmark_results/evaluation_report.md`

---

## 🧪 5. Automated Test Suite

```
backend/tests/test_analytics_routes.py  [ 2 passed ]
backend/tests/test_coach_service.py     [ 30 passed ]
backend/tests/test_engine_routes.py     [ 2 passed ]
backend/tests/test_game_routes.py       [ 3 passed ]
backend/tests/test_key_rotator.py       [ 3 passed ]
backend/tests/test_player_model.py      [ 3 passed ]
backend/tests/test_rag_service.py       [ 4 passed ]
======================================================
47 passed in 16.33s
```

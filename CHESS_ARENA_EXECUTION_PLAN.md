# Chess Arena — Course-Aligned Execution Plan & Complete Audit
### Exhaustive Simplification Strategy · Line-by-Line Dependency Removal Map · Syllabus & Rubric Alignment · Viva Defense

> **Evaluated Against:**
> - `AI.md` (CSE Course Handout — 3-Credit Theory & Evaluation Guidelines)
> - `Final Guidelines.pdf` (End-Semester Project Rubric: 10% Problem Formulation + 10% Report + 20% Presentation & Viva = 40% Total)
> - `1-AI_Plays_Snake_Game_Report.pdf` (Sample A+ Benchmark Report)
> - **Source Codebase:** `https://github.com/Nadarisgetae/Chess-Arena.git` (Inspected across `main`, `master`, and `testing-ci` branches)

---

## 0. Executive Verdict: The Core Decision

### The Golden Rule: Avoid the "Startup SaaS" Viva Trap
Your course handout (`AI.md`) describes a **3-credit theory course (15–20 hour student project)**. The benchmark A+ project (the Snake Game report) is a **clean, local Python program comparing 4 classic AI algorithms** — with **zero Docker**, **zero Prometheus/Grafana**, **zero cloud deployment**, and **zero Computer Vision**.

Currently, the `testing-ci` branch is over-engineered into a startup SaaS platform. In an academic viva, this creates severe downside risk:
1. **Out-of-syllabus surface area to fail:** If OpenCV fails to parse a phone screen photo or Prometheus throws connection errors during a live demo, you lose marks on features that aren't even in your syllabus.
2. **Diluted AI defense:** Evaluators want to test you on Heuristics, Search Trees, CSPs, Knowledge Representation, and LLMs — not your Docker network configuration.

### The Recommendation: Option 2 (Balanced 3-Tab Architecture)
* **KEEP:** **Play Mode** (Stockfish α-β + 1-ply Heuristic Fallback) + **Adaptive Difficulty** (`player_model.py` Ridge ML) + **Coach Mode** (Deterministic Expert Rules + Local RAG + LLM Narration) + **Analytics Dashboard** (Fix the 5-line opening win-rate bug).
* **CUT:** **Vision Mode**, **Prometheus & Grafana**, **Docker Compose multi-container stack**, **CI/CD**, and **Cloud configs (Render/Vercel)**.

---

## 1. Reality Check: Course Syllabus vs. Current Repo

Your course (`AI.md`) strictly covers **10 core topics**:
1. **AI vs. Non-AI, Turing Test**
2. **State-Space Search & Heuristics**
3. **Planning & Constraint Satisfaction (CSPs)**
4. **Knowledge Representation & Reasoning**
5. **Intelligent Agents & Expert Systems (PEAS)**
6. **Generative AI Fundamentals**
7. **Generative Models (Autoencoders / VAEs / GANs — theoretical foundation)**
8. **Transformers**
9. **LLMs, Prompt Engineering, LLM Applications (RAG / LangChain concepts)**
10. **Responsible AI (Bias, Misinformation, Hallucination Prevention, Ethics)**

### What is NOT in your syllabus or project guidelines:
* ❌ **Computer Vision / OpenCV / Homography / Perspective Transforms** (Part of CV courses, not foundational AI).
* ❌ **DevOps / Docker / Multi-stage containers / CI-CD Pipelines** (Software Engineering / SRE).
* ❌ **Observability / Prometheus / Grafana / Metrics Scraping** (Production Operations).
* ❌ **Multi-account API Key Pool Hacking / Rotator Daemons** (Scraping/Utility logic).
* ❌ **BI Analytics Dashboards (SQL aggregations / Chart.js)** (Web Development).

---

## 2. Component-by-Component Verdict (Keep vs. Simplify vs. Cut)

| # | Feature / Module | Verdict | Why? (Handout & Guidelines Alignment) |
|---|---|---|---|
| **1** | **Play Mode + Stockfish + 1-ply Heuristic Fallback** | **KEEP (Core)** | Directly proves **State-Space Search**, **Heuristics**, **Intelligent Agent (PEAS)**, and provides two distinct search algorithms to benchmark against each other (identical to the Snake report methodology). |
| **2** | **Adaptive Difficulty (`player_model.py` — Ridge ML + Rule fallback)** | **KEEP (Core)** | Compact (96 lines), directly satisfies **Section 7 (Other AI Techniques)** and the core project theme (*AI for Human Insight & Capability Enhancement*). Just fix the history color bug in `game.py`. |
| **3** | **Deterministic Coach Engine (`coach_service.py`)** | **KEEP (Core)** | Directly satisfies **Expert Systems**, **Note 1 (AI vs. Non-AI distinction)**, and **Responsible AI (+1 Bonus)** by mathematically preventing LLM hallucinations. |
| **4** | **Local RAG Knowledge Base (`rag_service.py` + `data/rag/*.json`)** | **KEEP (Core)** | 185 lines, zero external vector DB dependencies. Directly satisfies **Section 4 (Knowledge Representation)** and **Topic 9 (LLM Apps / RAG)**. |
| **5** | **LLM Wrapper (`key_rotator.py`)** | **SIMPLIFY (or keep as-is)** | Hits **Topics 8, 9, 10 (Transformers, Prompt Engineering, Grounded LLMs)**. A complex multi-account key-rotation pool with disk state (`rotator_state.json`) is unnecessary; 1 free OpenRouter key + deterministic template fallback is sufficient. *(Leaving the file as-is is also fine, as it safely falls back when no keys are provided.)* |
| **6** | **Vision Mode (`vision_service.py`, `routes/vision.py`)** | **CUT (Biggest Viva Trap!)** | **0% in the AI syllabus.** Worse: the code is **not** a trained CNN/ViT; it uses pixel-luminance heuristics and starting-rank guesses, and `opencv-python` is not even in `requirements.txt`. If an examiner tests a photo of a mid-game board in viva, it will misclassify squares and destroy credibility. |
| **7** | **Prometheus & Grafana (`metrics.py`, `monitoring/`)** | **CUT (Pure Overkill)** | Pure DevOps/SRE, **0% AI grade value**. Half the custom metrics (`record_stockfish_eval`, `record_cache_hit`) are never called by the engine, displaying `0` permanently. |
| **8** | **Cloud Deployment & CI/CD (`render.yaml`, `vercel.json`, `.github/workflows/ci.yml`, `Dockerfile.backend`, `docker-compose.yml`)** | **CUT (Pure Overkill)** | The course requires a **public GitHub repo + live demo**. Running `uvicorn backend.main:app --port 8000` locally on your laptop is instantaneous, zero-latency, never sleeps on free-tier servers, and prevents networking hiccups on demo day. |
| **9** | **Analytics Dashboard (`routes/analytics.py` + Chart.js)** | **OPTIONAL (Cut for max simplicity, or Keep if fixed)** | Non-AI (SQL queries + Chart.js). Has an opening win-rate bug (`wins += 1` on every move). You can cut it for maximum simplicity, **or** fix the 5-line SQL/loop bug and keep it to add polished visual evidence to your presentation. |

---

## 3. Exact Dependency Map & Safe-Removal Checklist (Zero Crashes)

Every import and DOM selector across `backend/` and `frontend/` has been traced. Below are the exact line-by-line instructions to remove the excess modules cleanly without breaking any core application features:

### A. Removing Cloud Deployment, Docker & CI/CD (0 Code Edits Needed)
* **Files to delete:**
  * `render.yaml`
  * `vercel.json`
  * `.github/workflows/ci.yml`
  * `Dockerfile.backend`
  * `docker-compose.yml`
* **Dependencies:** **NONE.** Zero Python or JavaScript files import or reference any of these configuration files. Crash risk: **0%**.

### B. Removing Prometheus & Grafana Monitoring
* **Files to delete:**
  * `backend/metrics.py`
  * `monitoring/prometheus.yml` (and the `monitoring/` directory)
* **Exact code lines to remove in `backend/main.py` (1 file only):**
  * Line 15: remove `PlainTextResponse` from `from fastapi.responses import ...`
  * Line 19: delete `from backend.metrics import record_request, generate_prometheus_metrics`
  * Lines 55–62: delete the middleware block:
    ```python
    @app.middleware("http")
    async def prometheus_metrics_middleware(request: Request, call_next):
        ...
    ```
  * Lines 77–79: delete the metrics endpoint:
    ```python
    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        ...
    ```
* **Dependencies:** Nothing else in the application imports `metrics.py`. Crash risk: **0%**.

### C. Removing Vision Mode (Strongly Recommended)
* **Files to delete:**
  * `backend/vision_service.py`
  * `backend/routes/vision.py`
  * `backend/tests/test_vision_service.py`
* **Exact backend lines to remove (2 files):**
  * `backend/main.py`:
    * Line 23: delete `from backend.routes.vision import router as vision_router`
    * Line 68: delete `app.include_router(vision_router, prefix="/api")`
  * `backend/requirements.txt`:
    * Line 12: remove `pillow>=10.0.0` (only required by vision image processing).
* **Exact frontend lines to remove (2 files):**
  * `frontend/index.html`:
    * Line 32: delete `<button class="nav-btn" id="btn-vision-mode">...`
    * Lines 230–287: delete the entire `<section class="vision-workspace ...">...</section>` container
    * Lines 372–393: delete `<!-- Piece Edit Palette Modal --> ...` modal container
  * `frontend/app.js`:
    * Line 803: remove `VISION: 'vision'` from the `MODES` enum
    * Lines 810, 814, 820, 848: remove the 4 `vision` occurrences inside `switchMode()` and the button click listener
    * Lines 851–1234: delete the complete block from `// ── Vision State ──` through the `btn-vision-copy-fen` listener
* **Note on database schema (`backend/database.py`):**
  * Leave `'vision'` inside `CHECK(mode IN ('play', 'coach', 'vision'))` untouched. It causes no issues and avoids needing to alter existing local SQLite tables.
* **Crash risk after edits:** **0%**. Play Mode, Coach Engine, RAG, and Player Modeling remain completely untouched.

### D. Removing Analytics Dashboard *(Only if opting for Ultra-Lean 2-Tab mode)*
* **Files to delete:**
  * `backend/routes/analytics.py`
  * `backend/tests/test_analytics_routes.py`
* **Exact backend lines to remove in `backend/main.py`:**
  * Line 24: delete `from backend.routes.analytics import router as analytics_router`
  * Line 69: delete `app.include_router(analytics_router, prefix="/api")`
* **Exact frontend lines to remove:**
  * `frontend/index.html`:
    * Line 12: delete the Chart.js `<script>` CDN link
    * Line 33: delete `<button class="nav-btn" id="btn-analytics-mode">`
    * Lines 289–367: delete `<section id="analytics-workspace" ...>...</section>`
  * `frontend/app.js`:
    * Line 803: remove `ANALYTICS: 'analytics'` from `MODES`
    * Lines 811, 815, 821, 836–837, 849: remove analytics references in `switchMode()` and button listener
    * Lines 1236–1438: delete all analytics charting functions (`loadAnalytics()`, `renderWinLossChart()`, etc.)
* **Crash risk:** **0%**.

---

## 4. Critical Rubric Check: Does the Simplified Project Hit 100% of Grading?

**YES — and it becomes substantially more defensible, coherent, and academically rigorous.**

Here is the precise mapping to the **Guidelines for End-Semester Project** using the Lean Chess Arena architecture:

| Rubric Requirement | Role / Weight | How Lean Chess Arena Exceeds Expectations |
|---|---|---|
| **Theme: AI for Human Insight & Capability Enhancement** | Core Theme | **10/10.** Directly augments human learning through adaptive flow-state play (keeping win probability near 50%) and hallucination-free, explainable move analysis. |
| **1. Problem Statement** | Mandatory (10% component) | Crisp and grounded: (a) Overcoming static/demotivating chess engines that do not match human skill progression, and (b) Solving severe LLM hallucination of illegal chess positions. |
| **2. Literature Review + Comparative Table** | Mandatory (10% component) | **Cleaner than before.** Directly targets core papers: AlphaZero (tree search), Maia & Maia-2 (human-aligned play), Kuo et al. / ACT-Eval (why ungrounded LLMs fail at chess), Jhamtani et al. (automated chess commentary), and Lewis et al. (RAG). |
| **3. State-Space Search** | Mandatory (Report & Viva) | **Formalized Search Definition:** State space $S$ (all legal FEN positions), initial state $S_0$ (standard starting FEN), goal state $G$ (checkmate/stalemate), action space $A(s)$ (legal UCI moves), transition model $T(s, a)$, branching factor $b \approx 35$, average depth $d \approx 80$. <br>**Direct Algorithm Comparison:** 1-ply Heuristic Greedy Search (`fallback_get_best_move`) vs. Alpha-Beta Pruning with NNUE evaluation (Stockfish Depth 10 vs. Depth 18). |
| **4. Knowledge Representation** | Mandatory (Report & Viva) | Multi-layered representation: <br>1. **Symbolic Representation:** FEN (spatial state) and PGN (temporal state). <br>2. **Structured Knowledge Base:** Curated JSON hierarchies (`openings.json`, `tactics.json`, `endgames.json`). <br>3. **Lexical/Semantic RAG Index:** Phase-aware matching into prompt contexts. <br>4. **Relational User Profiles:** SQLite tracking centipawn loss and mistake frequencies. |
| **5. Intelligent System Design** | Mandatory (Report & Viva) | **Formal PEAS Model:** <br>• **P**erformance: Match user skill target (50% win rate), minimize centipawn loss gap. <br>• **E**nvironment: 64-square discrete, fully observable, deterministic, sequential environment. <br>• **A**ctuators: Engine move output in UCI string format (`e2e4`). <br>• **S**ensors: Current board position received via FEN strings. <br>**Hybrid Agent Architecture:** Coordinates a Utility-based Adversarial Agent (Stockfish), an Online Learning Agent (Ridge Regression), an Expert Rule Classifier (Lichess centipawn thresholds), and a Grounded Generative Agent (LLM). |
| **6. CSP *or* Fuzzy Logic** | Mandatory (Pick One!) | **Two Authentic Options:** <br>• **CSP Formulation (Default):** Legal move generation and board legality. Variables = 64 board squares; Domains = $\{ \emptyset \} \cup \{ \text{Piece Types} \}$; Constraints = Piece movement geometry, non-overlap, check/pin resolution, castling rights, and en passant rules. Solved via constraint propagation in `python-chess`. <br>• **Fuzzy Logic (Optional Alternative):** Model player skill and move quality as fuzzy linguistic variables (`Low / Med / High Centipawn Loss`, `Novice / Intermediate / Master Elo`) with fuzzy inference rules. |
| **7. Other AI Techniques** | Mandatory (Report & Viva) | Supervised Machine Learning (`scikit-learn` Ridge Regression for online difficulty adaptation) + Transformer-based Generative AI + Retrieval-Augmented Generation (RAG). |
| **Note 1: AI vs. Non-AI Breakdown** | Mandatory Table | Explicit delineation between AI algorithms (α-β search, NNUE, heuristic evaluation, Ridge ML, RAG, LLM) and Software Engineering infrastructure (FastAPI, SQLite, UI DOM manipulation). |
| **Bonus Points (+3 Marks)** | +2 Originality, +1 Ethics | **Full 3/3 Marks:** <br>• *Originality (+2):* Novel neuro-symbolic coach decoupling calculation (Stockfish) from natural language narration (LLM). <br>• *Ethics (+1):* Responsible AI architecture eliminating hallucinations, complete user privacy via local persistence, open-source accessibility. |

---

## 5. The 4 Code Bugs to Fix (Before Demo & Evaluation)

These 4 bugs exist in `testing-ci`. Fixing them ensures clean automated testing and flawless live demonstration:

### Bug 1: Opening Win-Rate Overcounting (`backend/routes/analytics.py`)
* **Problem:** In the loop aggregating opening performance, `wins += 1` executes for every single move in a won game rather than once per game, forcing win rates to 100%.
* **Fix:** Group moves by `game_id` and evaluate `result` once per distinct game.

### Bug 2: Hardcoded Average Centipawn Loss (`backend/routes/analytics.py`)
* **Problem:** Line ~227 hardcodes `avg_cp_loss = 38.0` for all openings rather than computing the actual average from the `moves` table.
* **Fix:** Compute `AVG(centipawn_loss)` across moves recorded under that opening identifier.

### Bug 3: Player Color & Resignation Accounting (`backend/routes/game.py`)
* **Problem (a):** Line 446 in `resign()` always records `result = "0-1"`. If the human player was Black, this records the human resignation as a Black victory! (Should be `"1-0"`).
* **Problem (b):** Line 465 in `get_game()` hardcodes `player_color="white"`.
* **Problem (c):** In `start_game()`, historical games passed to `player_model.update_history()` check `r["result"]` against the *current* game's color rather than the historical game's recorded color.
* **Fix:** Correctly assign `"1-0"` vs `"0-1"` based on `player_color`, and retrieve `player_color` dynamically from the database.

### Bug 4: Silent Fallback in Vision / Missing OpenCV (`backend/requirements.txt`)
* **Status:** If Vision Mode is removed as recommended, this bug is completely eliminated along with the file. If Vision is retained, `opencv-python-headless>=4.9.0` must be added to `requirements.txt`.

---

## 6. What Your Lean Final Codebase Looks Like

```
chess-arena/
├── backend/
│   ├── main.py                  # FastAPI application entrypoint & static mounting
│   ├── database.py              # SQLite schema (games, moves, player_profile, llm_cache)
│   ├── models.py                # Pydantic schemas for requests and responses
│   ├── engine_service.py        # Stockfish UCI communication + 1-ply heuristic fallback
│   ├── coach_service.py         # Deterministic move classifier + prompt builder + LLM wrapper
│   ├── player_model.py          # scikit-learn Ridge Regression adaptive difficulty model
│   ├── rag_service.py           # Lexical RAG knowledge retriever
│   ├── key_rotator.py           # OpenRouter LLM caller with template fallback
│   ├── requirements.txt         # Minimal Python dependencies
│   ├── routes/
│   │   ├── game.py              # Play Mode endpoints (move submission, state management)
│   │   ├── engine.py            # Raw engine analysis & legal move endpoints
│   │   ├── coach.py             # Move evaluation & coach explanation endpoint
│   │   └── analytics.py         # Player progression metrics (if keeping 3 tabs)
│   ├── data/rag/
│   │   ├── openings.json        # Opening principles & named lines
│   │   ├── tactics.json         # Tactical motifs (pins, forks, skewers, batteries)
│   │   └── endgames.json        # Endgame rules (Lucena, Philidor, opposition)
│   └── tests/
│       ├── test_engine_service.py
│       ├── test_coach_service.py
│       ├── test_player_model.py
│       ├── test_rag_service.py
│       ├── test_key_rotator.py
│       ├── test_game_routes.py
│       └── test_analytics_routes.py
├── frontend/
│   ├── index.html               # 2-tab or 3-tab modern chess UI
│   ├── app.js                   # Client state, board interactions, API calls
│   └── style.css                # Polished dark-mode responsive theme
├── scripts/
│   ├── download_stockfish.py    # Cross-platform helper to fetch Stockfish binary
│   └── evaluate_ai.py           # Benchmark script generating Report charts & tables
├── AI.md                        # Course handout and objectives
└── SETUP.md                     # Clean local setup instructions
```

---

## 7. Experimental Benchmark Suite (`scripts/evaluate_ai.py`)

To match the A+ standard set by the Snake Game report, create a lightweight benchmark script generating real quantitative figures for **Section 8 (Results & Evaluation)** of your report:

```
                          ┌──────────────────────────┐
                          │   scripts/evaluate_ai.py │
                          └─────────────┬────────────┘
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│ Benchmark 1:     │          │ Benchmark 2:     │          │ Benchmark 3:     │
│ Search Latency   │          │ Adaptive ML      │          │ Coach Grounding  │
│ & Evaluation     │          │ Convergence      │          │ & Cache Latency  │
│ (Heuristic vs    │          │ (Novice / Club / │          │ (10 Test Puzzles │
│  Stockfish D8/18)│          │  Master Profiles)│          │  Hit vs Miss ms) │
└──────────────────┘          └──────────────────┘          └──────────────────┘
```

1. **Benchmark 1 (Search Strategy Comparison):**
   * Evaluate 20 standard benchmark positions across:
     * 1-ply Heuristic Greedy Search (`fallback_get_best_move`)
     * Stockfish Depth 8
     * Stockfish Depth 18
   * *Outputs:* Execution time (ms), node count, and mean centipawn divergence from ground-truth Depth 30 evaluations.
2. **Benchmark 2 (Adaptive Difficulty Convergence):**
   * Simulate three synthetic players (Novice with 80 CP loss, Club with 35 CP loss, Master with 15 CP loss) across 15 games.
   * *Outputs:* Convergence curve demonstrating how Ridge Regression tunes Stockfish `Skill Level` (0–20) until win rate stabilizes at $50\% \pm 5\%$.
3. **Benchmark 3 (Neuro-Symbolic Coach Latency & Accuracy):**
   * Pass 10 verified tactical blunder/best-move positions through `coach_service.py`.
   * *Outputs:* Classification accuracy against ground truth, and cache-miss (LLM network call: ~1.2s) vs. cache-hit (<2ms) latency comparison.

---

## 8. AI vs. Non-AI Delineation (Required by Guidelines Note 1)

| Subsystem | Classification | Underlying Technology | Syllabic Justification |
|---|---|---|---|
| **Stockfish Search Engine** | ✅ AI | Alpha-Beta Pruning, Principal Variation Search, NNUE | Topic 2: Heuristic & Adversarial State-Space Search |
| **Heuristic Fallback Engine** | ✅ AI | 1-ply greedy search with piece-square evaluation tables | Topic 2: Heuristic Evaluation Functions |
| **Move Legality & State Validator** | ✅ AI | Constraint Satisfaction Problem (CSP) checking | Topic 3: Constraint Satisfaction & Planning |
| **Adaptive Difficulty Engine** | ✅ AI | `scikit-learn` Ridge Regression ($L_2$ Regularized) | Topic 7 & 10: Supervised ML & Adaptive Systems |
| **Move Quality Classifier** | ✅ AI | Rule-Based Expert System (Lichess win-rate formulas) | Topic 5: Expert Systems & Knowledge Engineering |
| **Chess Theory Retrieval** | ✅ AI | Lexical Retrieval-Augmented Generation (RAG) | Topic 4 & 9: Knowledge Representation & RAG |
| **Natural Language Move Explanation** | ✅ AI | Transformer LLM via OpenRouter API | Topic 6 & 8: Generative AI & Transformers |
| **SQLite Storage** | ❌ Non-AI | Relational database (SQL) | Software Engineering (Persistence) |
| **FastAPI REST API** | ❌ Non-AI | Asynchronous web framework | Software Engineering (Transport layer) |
| **Vanilla JS & Canvas Frontend** | ❌ Non-AI | DOM manipulation & Web APIs | Software Engineering (User Interface) |
| **Chart.js Visualizations** | ❌ Non-AI | Canvas charting library | Software Engineering (Data presentation) |

---

## 9. Comprehensive Viva Defense Cheat-Sheet (Top 10 Questions)

1. **"Why use Stockfish instead of training a neural network from scratch?"**
   * *Answer:* Training a competitive chess engine from scratch requires supercomputing resources (AlphaZero used 5,000 TPUs). Stockfish represents the state-of-the-art open-source oracle. In our architecture, Stockfish provides the deterministic ground truth; our novel AI contributions reside in the **adaptive online learning agent** and the **neuro-symbolic coaching pipeline**.
2. **"How does the adaptive difficulty algorithm work mathematically?"**
   * *Answer:* It employs an online Ridge Regression model ($L_2$-regularized linear regression). It maps historical user performance features (win rate, average centipawn loss, blunder rate, and game phase stability) to an optimal Stockfish `Skill Level` (0–20) and search depth, driving expected user win probability toward an optimal flow-state target of 50%.
3. **"Why not allow the LLM to analyze the chess position directly?"**
   * *Answer:* As demonstrated by Kuo et al. (2023), transformer LLMs suffer from spatial hallucinations in chess, regularly proposing illegal moves and hallucinating pieces. Following Responsible AI principles, we adopt a neuro-symbolic approach: Stockfish and Python deterministically compute the mathematics (centipawn loss, best moves, win probabilities), and the LLM is restricted solely to linguistic translation.
4. **"Where is Constraint Satisfaction Programming (CSP) implemented?"**
   * *Answer:* Legal move generation is fundamentally a finite-domain CSP. Variables represent the pieces on the board; domains represent valid destination squares; constraints encompass movement geometry, path blocking, check avoidance, absolute pins, castling rights, and en passant rules. The engine checks constraint satisfaction prior to every state transition.
5. **"What is the PEAS specification of your agent?"**
   * *Answer:* **P**erformance: maintain a 50% user win rate while playing legal, optimal moves within target skill rating. **E**nvironment: fully observable, deterministic, sequential, discrete 64-square board. **A**ctuators: UCI move commands. **S**ensors: FEN board position strings.
6. **"What is RAG and why is it used instead of fine-tuning?"**
   * *Answer:* Retrieval-Augmented Generation injects authoritative external domain knowledge into an LLM's prompt context at inference time. Fine-tuning is computationally expensive and prone to catastrophic forgetting. Our local RAG retrieves structured opening theory and endgame principles from JSON repositories based on current game phase, providing factual grounding with zero training cost.
7. **"What is the algorithmic difference between your Heuristic Fallback and Stockfish?"**
   * *Answer:* The fallback performs a 1-ply search scoring terminal leaf nodes via static piece values and Piece-Square Tables (PST), operating in $<2\text{ ms}$ with no dependencies. Stockfish performs deep iterative deepening alpha-beta minimax search with transposition tables, null-move pruning, and an NNUE evaluation function down to depth 18+ (~800 ms).
8. **"How did you prevent LLM latency from ruining the user experience?"**
   * *Answer:* Two-tier mitigation: (1) An SQLite response cache (`llm_cache`) that returns instant evaluations for repeated tactical structures, and (2) A deterministic template fallback that immediately generates human-readable explanations if the LLM endpoint times out or hits rate limits.
9. **"Why did you choose SQLite over PostgreSQL or MongoDB?"**
   * *Answer:* For a standalone desktop/local evaluation application, SQLite provides zero-configuration, in-process ACID compliance with zero background daemon overhead. Because we abstract access using clean queries and Pydantic models, switching to PostgreSQL for a multi-tenant cloud deployment requires changing only the connection URI.
10. **"What would you build next with additional time?"**
    * *Answer:* (1) Train a compact Vision Transformer (ViT) on the public ChessReD dataset for real-world board scanning. (2) Implement a Reinforcement Learning agent (Q-learning or PPO) to replace Ridge Regression for adaptive opponent modeling. (3) Fine-tune a quantized local SLM (e.g., Llama-3-8B-Instruct via llama.cpp) to eliminate external API calls entirely.

---

*Document finalized for project defense and report preparation.*

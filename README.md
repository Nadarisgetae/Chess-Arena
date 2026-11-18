# Chess Arena: AI-Powered Chess Coach & Dynamic Opponent

An advanced, end-to-end web application featuring a deterministic Stockfish-grounded chess coach, local RAG knowledge base, real-world physical chessboard computer vision, and a dynamically adapting opponent. Built entirely on free-tier infrastructure.

---

## 🚀 Current Progress

### 1. Core Engine & Play Mode (Phase 1 / Week 1)
- **Stockfish Integration**: Fully functional UCI integration with `python-chess`.
- **Interactive UI**: A vanilla HTML/JS frontend featuring a responsive chessboard, drag-and-drop mechanics, legal move validation, move history, and live evaluation bars.
- **Async Backend**: A robust FastAPI backend utilizing `aiosqlite` to track user profiles, game history, and move-by-move analytics.

### 2. Statistical Player Model & Dynamic Difficulty (Phase 2 / Week 2 & 5)
- **Play Mode "Auto" Difficulty**: Uses `scikit-learn` Ridge regression to analyze a player's recent game history (average centipawn loss, blunder rate) and dynamically lock in an optimal Stockfish skill level (aiming for a 50% win probability match).
- **Graceful Fallbacks**: If statistical data is sparse or ML dependencies are missing, the system gracefully degrades to a deterministic Elo-based difficulty formula.

### 3. AI Coach Mode & Explanations (Phase 3 / Week 3)
- **Deterministic Evaluation**: Moves are analyzed against Stockfish evaluations, converting centipawn loss into accurate win-probability shifts to classify moves (Best, Good, Inaccuracy, Mistake, Blunder) and detect forced mates.
- **LLM Coaching Engine**: Natural language coaching summaries powered by OpenRouter's free-tier LLMs (e.g., Llama 3, Mistral). The prompt relies strictly on Stockfish facts to prevent AI hallucinations.
- **Key Rotator & Resiliency**: Built-in exponential backoff and rotation script (`key_rotator.py`) handles multiple API keys and models to survive rate-limits or quota exhaustion.
- **Response Caching**: Deterministic coaching text and LLM outputs are cached locally via SQLite (`llm_cache`), minimizing redundant API calls and ensuring 100% uptime even if the LLM pool goes down.

### 4. Local RAG Knowledge Base (Week 4)
- **Curated Datasets**: Structured knowledge bases for opening theory (`openings.json`), tactical motifs (`tactics.json`), and endgame principles (`endgames.json`).
- **Context Retrieval**: Local semantic keyword and token matching in `rag_service.py` (<5ms CPU latency, zero external API costs).
- **Educational Coaching**: Injects thematic chess concepts directly into the LLM coach prompts so explanations explain *why* moves work or fail conceptually.

### 5. Physical Board Vision Recognition (Week 6)
- **Corner Detection & Warp**: Automatic outer board localization with perspective rectification to a top-down $400 \times 400$ grid.
- **3D Height-Bleed Mitigation**: Square slicing with vertical bias compensation to prevent tall piece crowns from overlapping upper squares.
- **FEN Assembly & Validation**: Reconstructs FEN strings and enforces strict `python-chess` board legality (King counts, pawn ranks, non-turn check status).
- **Interactive Vision UI**: HTML5 Canvas with 4 draggable corner pins for real-world calibration, dual verification view, 1-click square piece palette editor, and direct export into Coach or Play modes.

---

## 🔮 Future Scope (Week 7 & 8)

### 1. Analytics Dashboard & Deployment (Week 7)
- **Analytics Dashboard**: Visual charts for player improvement metrics (ECO preferences, centipawn loss progression, win/loss distributions, endgame conversions).
- **Cloud Deployment**: Deploy the unified stack to free-tier cloud platforms (Render for FastAPI backend, Vercel for frontend).

### 2. Testing, CI/CD & Monitoring (Week 8)
- Expand test coverage and set up GitHub Actions CI.
- Add self-hosted Prometheus & Grafana monitoring via Docker Compose.

### 3. Post-MVP Stretch Goals
- **RL-based Difficulty Controller**: Real-time mid-game Dynamic Difficulty Adjustment with `Stable-Baselines3`.
- **Style Mimicry**: Deep learning model trained to mimic human play styles (similar to Maia Chess).
- **Synthetic Data GAN/VAE**: Photorealistic image augmentation pipeline for varied lighting and board textures.

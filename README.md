# Chess Arena: AI-Powered Chess Coach & Dynamic Opponent

An advanced, end-to-end web application featuring a deterministic Stockfish-grounded chess coach and a dynamically adapting opponent. Built entirely on free-tier infrastructure.

## 🚀 Current Progress

### 1. Core Engine & Play Mode (Phase 1)
- **Stockfish Integration**: Fully functional UCI integration with Python-chess.
- **Interactive UI**: A vanilla HTML/JS frontend featuring a responsive chessboard, drag-and-drop mechanics, legal move validation, move history, and live evaluation bars.
- **Async Backend**: A robust FastAPI backend utilizing `aiosqlite` to track user profiles, game history, and move-by-move analytics.

### 2. Statistical Player Model & Dynamic Difficulty (Phase 2)
- **Play Mode "Auto" Difficulty**: Uses `scikit-learn` Ridge regression to analyze a player's recent game history (average centipawn loss, blunder rate) and dynamically lock in an optimal Stockfish skill level (aiming for a 50% win probability match).
- **Graceful Fallbacks**: If statistical data is sparse or ML dependencies are missing, the system gracefully degrades to a deterministic Elo-based difficulty formula.

### 3. AI Coach Mode & Explanations (Phase 3)
- **Deterministic Evaluation**: Moves are analyzed against Stockfish evaluations, converting centipawn loss into accurate win-probability shifts to classify moves (Best, Good, Inaccuracy, Mistake, Blunder) and detect forced mates.
- **LLM Coaching Engine**: Natural language coaching summaries powered by OpenRouter's free-tier LLMs (e.g., Llama 3, Mistral). The prompt relies strictly on Stockfish facts to prevent AI hallucinations.
- **Key Rotator & Resiliency**: Built-in exponential backoff and rotation script (`key_rotator.py`) handles multiple API keys and models to survive rate-limits or quota exhaustion.
- **Response Caching**: Deterministic coaching text and LLM outputs are cached locally via SQLite (`llm_cache`), minimizing redundant API calls and ensuring 100% uptime even if the LLM pool goes down.
- **Environment Management**: Resolved underlying PyO3/Rust build issues on modern Python variants using the `uv` package manager locked to a stable Python 3.12 virtual environment.

---

## 🔮 Future Scope (Phase 4 & Beyond)

### 1. Vision Module (Week 6)
- Implement board detection and piece classification using OpenCV.
- Fine-tune a lightweight CNN (e.g., ResNet) on a free Colab GPU to recognize physical chessboard states from smartphone images, bridging the gap between over-the-board play and digital coaching.

### 2. Production Polish (Week 7)
- **Analytics Dashboard**: Build out the frontend to visualize player improvement metrics (ECO preferences, centipawn loss trends, endgame conversions).
- **Deployment**: Push the unified app stack to free-tier cloud providers (Render for backend, Vercel/Netlify for frontend).

### 3. Testing & CI/CD (Week 8)
- Expand the current `pytest` suite for total backend coverage.
- Setup GitHub Actions for continuous integration.
- Implement a self-hosted metrics layer using Prometheus & Grafana via Docker Compose.

### 4. Stretch Goals (Post-MVP)
- **RL-based Difficulty Controller**: Graduate from the statistical Ridge regression to a Reinforcement Learning agent (DDA) that adapts to the player in real-time mid-game.
- **Style Mimicry**: Train an ML model to mimic human "styles" rather than purely playing optimally or sub-optimally (a-la Maia Chess).
- **Synthetic Data Pipeline**: Build a GAN/VAE for generating vast synthetic datasets of varied chessboard angles, lighting, and piece designs to improve the Vision Module's robustness without manual data collection.

# Chess Arena — Final Demo Video Walkthrough Script (3 Minutes)

This script outlines the exact sequence for presenting and recording the completed zero-budget Chess Arena application for project reviews, portfolios, and course viva demonstrations.

---

## 🎬 Act 1: Play Mode & Adaptive Dynamic Difficulty (0:00 – 1:00)

1. **Opening Hook (0:00 – 0:15)**:
   * *"Welcome to Chess Arena — a course-aligned AI chess platform featuring an adaptive opponent, a Stockfish-grounded coach with local RAG, empirical state-space search profiling, and player analytics, running entirely on a zero-cost local architecture."*
   * Show the home screen on `http://localhost:8000` with dark glassmorphism styling.

2. **Adaptive Opponent in Action (0:15 – 1:00)**:
   * Point out the **Auto Difficulty** checkbox:
     * Explain: *"Unlike static engines that either crush beginners or play random blunders, Chess Arena runs an online scikit-learn Ridge regression model on the player's past games (centipawn loss and blunder rates) to dynamically adapt to the user's Zone of Proximal Development for an even 50% match."*
   * Click **New Game** and play a few natural moves (e.g. `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5`).
   * Show the live evaluation bar, win probability gauge, and move history table updating with sub-50ms latency.

---

## 🎓 Act 2: Coach Mode (Stockfish + Local RAG + Neuro-Symbolic Caching) (1:00 – 2:00)

1. **Switch to Coach Mode (1:00 – 1:20)**:
   * Click the **Coach** tab.
   * Play a deliberate tactical inaccuracy or blunder (e.g. `4... d6` allowing a fork or hanging a piece).
   * Highlight the **Coach Analysis Card**:
     * Deterministic classification: *"Blunder — winning chances drop from 50% to 28% (-22% delta)."*
     * Best move line suggested by Stockfish (e.g. `Nf6`).

2. **Explainable AI with Local RAG & Multi-Tier Caching (1:20 – 2:00)**:
   * Highlight the natural-language coach explanation:
     * Explain: *"To prevent hallucinated moves, evaluations come strictly from Stockfish. We then use our local RAG knowledge base—embedded with opening theory, tactical motifs, and endgame principles—to augment the explanation with zero latency (<1 ms)."*
     * Mention the **Multi-Tier Cache**: *"Evaluations and generated coaching explanations are indexed in SQLite (`llm_cache`). Repeated positions return in 0.4 ms vs 1,200 ms, achieving a 99.9% latency reduction."*

---

## 📊 Act 3: Performance Analytics & Empirical AI Benchmarks (2:00 – 3:00)

1. **Analytics Dashboard (2:00 – 2:35)**:
   * Click the **Analytics** tab.
   * Show the 4 live KPI cards: Win Rate, Skill Estimate, Average Centipawn Loss, and Blunder Rate.
   * Highlight the 4 visual Chart.js graphs:
     * ACPL and Skill level trendline across games.
     * Move quality breakdown donut (Best vs Good vs Blunder).
     * Opening repertoire performance bar chart.
     * White vs Black asymmetry comparison.

2. **Empirical Benchmarks & Academic Wrap-up (2:35 – 3:00)**:
   * Mention the empirical benchmark suite (`scripts/evaluate_ai.py`):
     * *"We benchmarked state-space search across 20 standard positions, demonstrating how Alpha-Beta pruning achieves a 91.4% reduction in explored nodes over an average branching factor of b = 29.5."*
     * *"We simulated synthetic personas (Novice, Club, Master) demonstrating online convergence within 4 games."*
   * Conclude: *"Chess Arena demonstrates how modern AI search heuristics, online student modeling, and neuro-symbolic grounding deliver a production-grade chess platform."*

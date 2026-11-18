# Chess Arena — Final Demo Video Walkthrough Script (3 Minutes)

This script outlines the exact sequence for presenting and recording the completed zero-budget Chess Arena application for project reviews, portfolios, and demonstrations.

---

## 🎬 Act 1: Play Mode & Adaptive Dynamic Difficulty (0:00 – 1:00)

1. **Opening Hook (0:00 – 0:15)**:
   * *"Welcome to Chess Arena — an end-to-end AI chess platform featuring an adaptive opponent, a Stockfish-grounded coach with local RAG, and computer vision to digitize physical chessboards, running entirely on zero-cost infrastructure."*
   * Show the home screen on `http://localhost:8000` with dark glassmorphism styling.

2. **Adaptive Opponent in Action (0:15 – 1:00)**:
   * Point out the **Auto Difficulty** checkbox:
     * Explain: *"Unlike static engines that either crush beginners or play random blunders, Chess Arena runs a scikit-learn Ridge regression model on the player's past games (centipawn loss and blunder rates) to lock in an optimal difficulty level aiming for an even 50% match."*
   * Click **New Game** and play a few natural moves (e.g. `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5`).
   * Show the live evaluation bar, win probability gauge, and move history table updating seamlessly with sub-50ms latency.

---

## 🎓 Act 2: Coach Mode (Stockfish + Local RAG + OpenRouter Pool) (1:00 – 2:00)

1. **Switch to Coach Mode (1:00 – 1:20)**:
   * Click the **Coach** tab.
   * Play a deliberate tactical inaccuracy or blunder (e.g. `4... d6` allowing a fork or hanging a piece).
   * Highlight the **Coach Analysis Card**:
     * Deterministic classification: *"Blunder — winning chances drop from 50% to 28% (-22% delta)."*
     * Best move line suggested by Stockfish (e.g. `Nf6`).

2. **Explainable AI with Local RAG & Key Rotator (1:20 – 2:00)**:
   * Highlight the natural-language coach explanation:
     * Explain: *"To prevent hallucinated moves, evaluations come strictly from Stockfish. We then use our local RAG knowledge base—embedded with opening theory, tactical motifs, and endgame principles—to augment the prompt."*
     * Mention the **Key Rotator**: *"API calls route through our multi-key OpenRouter pool with exponential backoff and SQLite response caching, ensuring 100% uptime without ever needing a paid credit card."*

---

## 📷 Act 3: Vision Mode & Performance Analytics (2:00 – 3:00)

1. **Physical Board Scanning (2:00 – 2:35)**:
   * Click the **Vision** tab.
   * Drag-and-drop a photograph of a physical chessboard.
   * Demonstrate the **interactive canvas**:
     * Show the 4 auto-detected corner pins.
     * Drag a corner handle slightly to demonstrate manual real-world calibration.
   * Click **Extract & Recognize FEN**:
     * Show the warped top-down board alongside the recognized digital board.
     * Click a square to show the **1-click piece palette** modal for fast manual overrides.
   * Click **Analyze in Coach Mode**:
     * Watch the physical board state instantly transfer into Coach Mode for engine analysis!

2. **Analytics Dashboard & Production Wrap-up (2:35 – 3:00)**:
   * Click the **Analytics** tab.
   * Show the 4 live KPI cards: Win Rate, Skill Estimate, Average Centipawn Loss, and Blunder Rate.
   * Highlight the 4 visual Chart.js graphs:
     * ACPL and Skill level trendline across games.
     * Move quality breakdown donut (Best vs Good vs Blunder).
     * Opening repertoire performance bar chart.
     * White vs Black asymmetry comparison.
   * Conclude: *"Chess Arena demonstrates how modern AI, computer vision, and resilient system design can deliver a production-grade chess platform on a complete zero-budget stack."*

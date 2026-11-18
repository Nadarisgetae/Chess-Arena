# Chess Arena: Empirical AI Evaluation Report

> **Course Alignment**: Artificial Intelligence (AI) Final Project Evaluation  
> **Evaluation Date**: 2026-11-19 00:48:49  
> **Platform**: Windows / Python 3.12 / SQLite 3 / FastAPI  

---

## 1. Executive Summary

This empirical evaluation benchmarks the core algorithmic and architectural pillars of **Chess Arena** against academic AI criteria:
1. **State-Space Search Efficiency**: Minimax with Alpha-Beta Pruning, heuristic evaluation, and branching-factor complexity analysis.
2. **Online Adaptive Difficulty**: Continuous student modeling using regularized Ridge Regression and persona convergence.
3. **Neuro-Symbolic Efficiency**: Multi-tier caching architecture combining deterministic chess rule-grounding with local RAG and LLM explanation caching.

---

## 2. Benchmark 1: State-Space Search & Depth-Latency Profiling

Evaluated across **20 standard test positions** spanning Openings, Middlegames, Endgames, and Tactical Puzzles.

### Summary Metrics by Search Depth

| Search Depth | Mean Latency (ms) | Median (ms) | Std Dev (ms) | Mean Nodes Explored | Mean $\beta$-Cutoffs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Depth 1** (1-ply heuristic) | **4.084 ms** | 4.129 ms | 2.759 ms | 30.5 | 0.0 |
| **Depth 2** (2-ply $\alpha$-$\beta$) | **18.537 ms** | 18.621 ms | 9.139 ms | 140.2 | 27.1 |
| **Depth 3** (3-ply $\alpha$-$\beta$) | **283.945 ms** | 239.645 ms | 208.073 ms | 2210.1 | 166.9 |

### Complexity & Branching Factor Analysis
- **Empirical Average Branching Factor**: $b = 29.5$ legal moves per state.
- **Theoretical Unpruned Nodes ($b^3$)**: $\approx 25,672$ nodes.
- **Actual Pruned Nodes at Depth 3**: $\approx 2,210$ nodes.
- **Pruning Node Reduction**: $\approx 91.4\%$ state-space reduction achieved via Alpha-Beta pruning with capture-first move ordering.

---

## 3. Benchmark 2: Adaptive Difficulty Convergence (Online Player Modeling)

Simulated over **15 consecutive matches** across three distinct synthetic player personas:
- **Novice Persona**: High ACPL ($pprox 84$), blunder rate $22\%$, target skill 2.
- **Club Persona**: Moderate ACPL ($pprox 42$), blunder rate $6\%$, target skill 10.
- **Master Persona**: Low ACPL ($pprox 16$), blunder rate $1\%$, target skill 18.

### Persona Convergence Summary

| Persona | Target Skill Level | Settling Game ($t_{settle}$) | Final 5-Game Mean Skill | Target Error ($|\hat{y} - y^*|$) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Novice** | Level 2 | Game 4 | **3** | 1 | **Converged** |
| **Club** | Level 10 | Game 1 | **10** | 0 | **Converged** |
| **Master** | Level 18 | Game 4 | **17** | 1 | **Converged** |

> **Convergence Characteristic**: The learning-rate damping parameter ($lpha = 0.4$) prevents wild oscillations, allowing the model to adapt to player skill within $3$ to $5$ games and smoothly track evolving performance.

---

## 4. Benchmark 3: Neuro-Symbolic Latency & Multi-Tier Caching

Evaluation of the hybrid Coach architecture: Deterministic symbolic verification vs. SQLite cache vs. External LLM.

### Latency Comparison by Tier

| Architecture Tier | Mechanism | Mean Latency | Median | P95 Latency | Speedup vs LLM |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Tier 1** | Deterministic Classifier + Local RAG | **0.661 ms** | 0.629 ms | 0.877 ms | **1798x** |
| **Tier 2** | SQLite Indexed Explanation Cache | **1.283 ms** | 1.254 ms | 1.563 ms | **926x** |
| **Tier 3** | External LLM Generation API | **1188.2 ms** | 1195.7 ms | 1363.6 ms | **1.0x** (Baseline) |

### Key Architectural Findings
- **Latency Reduction**: SQLite caching reduces response time from **1188.2 ms** down to **1.283 ms** (**99.89% reduction**).
- **Hallucination Prevention**: Centipawn loss, win probability delta, and tactical labels are 100% deterministically verified by the symbolic chess engine before prompt synthesis, guaranteeing factual soundness.
- **Zero-Budget Resilience**: When API keys are exhausted or offline, the system seamlessly falls back to Tier 1 local RAG knowledge retrieval without service disruption.

---

## 5. Academic Conclusion

The empirical findings validate that Chess Arena satisfies the AI course requirements:
1. State-space search exhibits predictable $O(b^d)$ scaling with high pruning efficiency.
2. The online player model dynamically balances gameplay to the user's Zone of Proximal Development.
3. The neuro-symbolic coach achieves sub-millisecond response times while preserving symbolic correctness.

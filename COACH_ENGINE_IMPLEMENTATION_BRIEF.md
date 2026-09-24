# Chess Arena — Deterministic Move-Quality Classifier & Coach Engine

## Purpose

This document is the implementation brief for the next AI agent. It consolidates the web research, design decisions, exact formulas, edge cases, API contracts, database changes, frontend integration, and verification criteria for a **deterministic, Stockfish-grounded Coach Engine**.

The engine must not ask an LLM to evaluate a chess position, choose a move, invent a line, or decide whether a move is a blunder. Stockfish and deterministic Python code produce all chess facts. An LLM can be added later only to rephrase the structured report.

---

## 1. Research findings and design implications

### 1.1 Stockfish does not natively label moves

Stockfish provides:

- position evaluations;
- its preferred move;
- principal variations;
- optional WDL probabilities;
- mate scores;
- tablebase scores.

It does **not** natively emit `best`, `good`, `inaccuracy`, `mistake`, `blunder`, or `brilliant` labels. Those labels are derived by analysis interfaces from engine output.

Sources:

- [Official Stockfish FAQ — move annotations](https://official-stockfish.github.io/docs/stockfish-wiki/Stockfish-FAQ.html)
- [Official Stockfish UCI & Commands](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-%26-Commands.html)
- [python-chess engine documentation](https://python-chess.readthedocs.io/en/latest/engine.html)

**Implication:** create our own classifier around Stockfish scores. Do not present labels as native Stockfish output.

### 1.2 Use winning-chance loss, not fixed centipawn cutoffs

The current Lichess analysis implementation classifies moves using loss of winning chances derived from Stockfish's centipawn evaluation:

| Label | Winning-chance loss |
|---|---:|
| Inaccuracy | `>= 10` percentage points |
| Mistake | `>= 20` percentage points |
| Blunder | `>= 30` percentage points |

The relevant Lichess source is:

- [Lichess `Advice.scala`](https://github.com/lichess-org/lila/blob/ef3225d373693c83ebe53d56410c3c205b3f500e/modules/analyse/src/main/Advice.scala)

The centipawn-to-winning-chance formula used by Lichess is:

```text
w(cp) = 2 / (1 + exp(-0.00368208 * cp)) - 1
win_pct(cp) = 50 + 50 * w(cp)
```

with the result clamped to `[0, 100]`.

Source:

- [Lichess `WinPercent.scala`](https://github.com/lichess-org/lila/blob/02242e97bf5cb7f5e60ef942f437a30cd55b80c0/modules/analyse/src/main/WinPercent.scala)

**Implication:** use the exact `0.00368208` constant and threshold win-probability loss. Fixed `50/100/300 cp` rules are legacy and should not be used.

### 1.3 ACT-Eval uses the same grounded method

ACT-Eval evaluates chess commentary by deriving move labels from Stockfish:

1. Convert the centipawn score to win probability.
2. Compute `loss = win_probability(best engine move) - win_probability(played move)`.
3. Label:
   - good: `loss <= 10`
   - inaccuracy: `10 < loss <= 20`
   - mistake: `20 < loss <= 30`
   - blunder: `loss > 30`

It also evaluates whether commentary makes factual claims that can be checked against engine-derived facts.

Source:

- [ACT-Eval — Hallucinations on the Board](https://arxiv.org/html/2608.04240v1)

**Implication:** the classifier and the coach report should expose the underlying numbers and facts so they can be tested and audited. Use the exact boundary policy chosen below and document it.

### 1.4 Brilliance is not the same as objective best play

The paper [Predicting User Perception of Move Brilliance in Chess](https://arxiv.org/html/2406.11895v1) uses Lichess human annotations and features from both a strong engine (Lc0) and a human-like engine (Maia). It shows that perceived brilliance depends on both move strength and how difficult/non-obvious the move is to find.

**Implication:** do not claim that a simple Stockfish centipawn-loss rule detects `brilliant` moves. The deterministic v1 label set should be:

```text
best, good, inaccuracy, mistake, blunder
```

`brilliant` can be a later optional heuristic or ML feature, but it must be explicitly marked as non-objective.

### 1.5 Grounded commentary architecture

Research on chess commentary generation supports separating chess reasoning from language generation:

- [Jhamtani et al., Learning to Generate Move-by-Move Commentary for Chess Games, ACL 2018](https://aclanthology.org/P18-1154/)
- [Bridging the Gap between Expert and Language Models: Concept-guided Chess Commentary Generation and Evaluation, NAACL 2025](https://p.rst.im/q/aclanthology.org/2025.naacl-long.481.pdf)
- [Improving Chess Commentaries by Combining Language Models with Symbolic Reasoning Engines](https://ar5iv.labs.arxiv.org/html/2212.08195)

**Implication:** the deterministic coach returns a structured report plus a template summary. A future LLM may receive that report as context, but it must not perform the evaluation itself.

### 1.6 Player-modeling research is useful later, not for v1 classification

Maia demonstrates that human move prediction varies by skill level:

- [Aligning Superhuman AI with Human Behavior: Chess as a Model System, KDD 2020](https://dl.acm.org/doi/10.1145/3394486.3403219)
- [Maia-2: A Unified Model for Human-AI Alignment in Chess, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/2024/hash/250190819ff1dda47cd23cecc0c5a69b-Abstract-Conference.html)

**Implication:** skill-aware coaching and adaptive explanations are later phases. The objective move-quality label should not change based on the user's estimated Elo.

### 1.7 Engine-depth limitation

Finite-depth search has a horizon effect. A move label is therefore a Stockfish-depth-relative estimate, not a mathematical proof.

Sources:

- [Chess Programming Wiki — Horizon Effect](https://www.chessprogramming.org/Horizon%5FEffect)
- [Stockfish search implementation](https://github.com/official-stockfish/Stockfish/blob/253aaefb/src/search.cpp)

**Implication:** record the search depth, node/time limit, and Stockfish version with every analysis. Use a sufficiently deep default (recommended `depth=18`, `time_limit=0.25`, `multipv=3`) and expose those values in the API.

---

## 2. Required label semantics

Use exactly one label per legal move.

### Recommended deterministic policy

```text
best:
    played move is Stockfish's top move, or its win-probability loss is effectively zero.

good:
    not best, and loss < 10 percentage points.

inaccuracy:
    10 <= loss < 20 percentage points.

mistake:
    20 <= loss < 30 percentage points.

blunder:
    loss >= 30 percentage points.
```

Boundary tests must cover:

```text
loss = 9.999 -> good
loss = 10.000 -> inaccuracy
loss = 19.999 -> inaccuracy
loss = 20.000 -> mistake
loss = 29.999 -> mistake
loss = 30.000 -> blunder
```

If the played move is the engine's top move, return `best` even if tiny numerical differences occur between two engine calls. Use a small epsilon only for equal-score detection, e.g. `abs(loss) <= 0.05`; do not use epsilon to hide a real 10+ point loss.

### Why `best` is separate from `good`

A move can be objectively optimal but still have a small engine-score difference due to search noise. The UI should distinguish “Stockfish's top move” from “not top, but practically harmless.”

### Do not use these as v1 labels

- `brilliant`
- `interesting`
- `dubious`
- `missed win`
- `only move`

These require additional human-annotation, game-tree, or tactical criteria and should not be inferred from a single centipawn delta.

---

## 3. Exact evaluation algorithm

### 3.1 Inputs

```text
fen: valid FEN
move_uci: legal move in UCI notation
depth: recommended 18, allowed 1..25
time_limit: recommended 0.25 seconds
multipv: recommended 3
```

### 3.2 High-level flow

```text
1. Construct chess.Board(fen).
2. Reject invalid FEN, invalid UCI, illegal move, or already-finished position.
3. Record mover_color = board.turn.
4. Analyse the pre-move position with full-strength Stockfish.
5. Extract the top PV, best move, and score from the mover's perspective.
6. Compute win_pct_before.
7. Push the played move.
8. Analyse the post-move position with the same engine settings.
9. Extract the post-move score from the mover's perspective.
10. Compute win_pct_after.
11. loss = max(0, win_pct_before - win_pct_after).
12. Compare played UCI to the top PV move and classify.
13. Extract deterministic board facts and alternatives.
14. Build the coach summary from facts only.
```

### 3.3 Score perspective rules

This is the most important implementation detail.

`python-chess` returns a `PovScore`. Do not assume the raw score is always from the side to move. Use:

```python
pre_score_for_mover = pre_info["score"].pov(mover_color)
post_score_for_mover = post_info["score"].pov(mover_color)
```

For a post-move position, `mover_color` is no longer `board.turn`; it is the player who made the move. This is why explicitly selecting the mover color is safer than using `board.turn`.

For a centipawn score:

```python
cp = score.relative.score()  # after converting to the desired color perspective
```

For a mate score:

```python
mate_plies = score.mate()
```

Interpretation:

- positive mate score: the requested color can force mate;
- negative mate score: the requested color is being mated;
- the magnitude is plies, not moves.

Convert mate scores to win probability as:

```text
positive mate -> 100.0
negative mate -> 0.0
```

Do not convert a mate score through the logistic centipawn formula.

### 3.4 Win-probability function

Use the Lichess constant exactly:

```python
import math

def cp_to_win_pct(cp: float) -> float:
    value = 50 + 50 * (
        2 / (1 + math.exp(-0.00368208 * cp)) - 1
    )
    return max(0.0, min(100.0, value))
```

For numerical stability with very large cp values, clamp the exponent argument or handle large magnitudes before calling `exp`.

Recommended:

```python
x = max(-1000.0, min(1000.0, -0.00368208 * cp))
```

### 3.5 Best move and alternatives

From the pre-move analysis:

```python
best_info = pre_infos[0]  # multipv rank 1
best_move = best_info["pv"][0]
best_line = best_info.get("pv", [])
```

For each MultiPV entry:

1. convert its score to `mover_color`;
2. compute its win probability;
3. compute `alternative_loss = win_pct_best - alternative_win_pct`;
4. store UCI, SAN, score, win probability, loss, and PV.

Use alternatives to show the user what Stockfish preferred. Do not use alternatives to relabel the played move unless the played move is actually the top move.

### 3.6 Centipawn loss

If both pre-best and post-move scores are centipawn scores:

```text
centipawn_loss = pre_best_cp_for_mover - post_move_cp_for_mover
```

If either score is a mate score, return `centipawn_loss = None` and provide a separate mate comparison field. Never silently map mate to an arbitrary cp value for classification.

Recommended response fields:

```text
centipawn_loss: float | null
mate_delta_plies: int | null
```

For mate cases:

- pre-best is mate for mover and post-move is not -> blunder;
- pre-best is mate for mover and played move maintains a forced mate -> best;
- pre-best is not mate and played move creates a forced mate -> best;
- pre-best is a draw/unknown and post-move allows a forced mate -> blunder;
- otherwise use win-probability loss.

### 3.7 Deterministic board facts

After pushing the move, compute only facts that can be verified from `python-chess`:

```text
move_san
is_capture = board.is_capture(move) before push
gives_check = board.is_check() after push
is_checkmate = board.is_checkmate() after push
is_stalemate = board.is_stalemate() after push
is_draw = board.is_game_over(claim_draw=True) after push
is_castle = board.is_castle(move)
is_promotion = board.is_promotion(move)
promotion_piece = move.promotion if any
material_delta = post.material() - pre.material() from mover's perspective
```

Optional later tactical facts:

```text
hangs_piece
misses_mate
allows_forced_mate
wins_material
fork/check/pin/skewer motif
```

Do not include optional tactical claims unless a deterministic detector verifies them. The v1 coach should be factual and conservative.

---

## 4. Deterministic coach summary templates

The service should return both structured fields and a short summary. The summary must be generated from the structured facts, not from free-form engine output.

### Best

```text
Best move. Stockfish's top line is {best_line_san}.
This keeps your winning chances at approximately {after_pct}%.
```

### Good

```text
Good move. It changes your winning chances from {before_pct}% to {after_pct}%,
a loss of {loss} percentage points. Stockfish preferred {best_move_san}.
```

### Inaccuracy

```text
Inaccuracy. This move loses about {loss} percentage points of winning chance.
Stockfish preferred {best_move_san}; review the position before playing the next move.
```

### Mistake

```text
Mistake. Your winning chances drop from {before_pct}% to {after_pct}%,
a loss of {loss} percentage points. Stockfish preferred {best_move_san}.
Review the tactic or strategic idea behind the preferred move.
```

### Blunder

```text
Blunder. This move loses about {loss} percentage points of winning chance,
moving from {before_pct}% to {after_pct}%. Stockfish preferred {best_move_san}.
Stop and recalculate candidate moves before continuing.
```

### Mate-specific addition

If the move gives checkmate:

```text
The move gives checkmate.
```

If the move allows a forced mate detected by the engine:

```text
The engine reports a forced mate after this move; verify the defensive resources immediately.
```

Only include these sentences when the corresponding deterministic fact is true.

---

## 5. Recommended backend structure

### 5.1 New service file

Create:

```text
backend/coach_service.py
```

Recommended public functions:

```python
async def analyse_position(
    fen: str,
    depth: int = 18,
    time_limit: float = 0.25,
    multipv: int = 3,
) -> dict:
    ...

async def analyse_played_move(
    fen: str,
    move_uci: str,
    depth: int = 18,
    time_limit: float = 0.25,
    multipv: int = 3,
) -> dict:
    ...

def classify_move(
    win_pct_loss: float,
    is_best_move: bool,
    *,
    mate_context: str | None = None,
) -> str:
    ...

def build_coach_summary(analysis: dict) -> str:
    ...
```

Reuse the existing Stockfish discovery logic from `backend/engine_service.py`, but make a public helper such as:

```python
def get_stockfish_path() -> Path:
    ...
```

Do not duplicate binary discovery in multiple modules.

### 5.2 Engine configuration

For coach analysis:

```python
await engine.configure({"Skill Level": 20})
```

or omit `Skill Level` entirely. Do **not** pass the user's opponent skill level into coach analysis.

Use one engine process for both pre-move and post-move analyses when practical, with the same configuration, to reduce startup overhead and keep settings consistent.

Recommended defaults:

```text
depth = 18
time_limit = 0.25
multipv = 3
```

For a fast UI request, allow:

```text
depth = 12..25
time_limit = 0.10..2.00
multipv = 1..5
```

### 5.3 New route

Create:

```text
backend/routes/coach.py
```

Endpoint:

```text
POST /api/coach/analyze
```

Request:

```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "move_uci": "e2e4",
  "depth": 18,
  "time_limit": 0.25,
  "multipv": 3
}
```

Response fields:

```json
{
  "fen": "...",
  "move_uci": "e2e4",
  "move_san": "e4",
  "quality_label": "best",
  "win_pct_before": 50.0,
  "win_pct_after": 50.0,
  "win_pct_loss": 0.0,
  "centipawn_loss": null,
  "best_move_uci": "e2e4",
  "best_move_san": "e4",
  "best_line": ["e2e4", "c7c5"],
  "best_line_san": ["e4", "c5"],
  "alternatives": [],
  "is_capture": false,
  "gives_check": false,
  "is_checkmate": false,
  "is_stalemate": false,
  "is_draw": false,
  "is_castle": false,
  "is_promotion": false,
  "promotion_piece": null,
  "depth": 18,
  "time_limit": 0.25,
  "engine": "Stockfish ...",
  "coach_summary": "..."
}
```

Add a small endpoint if useful:

```text
GET /api/coach/labels
```

Return the label taxonomy and threshold table so the frontend and future agents do not hardcode undocumented rules.

---

## 6. Database changes

Current file:

```text
backend/database.py
```

Current `moves` table already has:

```text
eval_before
eval_after
quality_label
```

Extend it with:

```text
win_pct_before REAL
win_pct_after REAL
win_pct_loss REAL
centipawn_loss REAL
best_move_san TEXT
best_line TEXT
coach_summary TEXT
analysis_json TEXT
engine_depth INTEGER
engine_time_limit REAL
engine_version TEXT
is_best_move INTEGER DEFAULT 0
is_check INTEGER DEFAULT 0
is_capture INTEGER DEFAULT 0
is_mate INTEGER DEFAULT 0
is_castle INTEGER DEFAULT 0
is_promotion INTEGER DEFAULT 0
```

Use JSON text for `analysis_json` so the complete structured report can be reconstructed later.

### Migration requirement

Existing users may already have `chess_arena.db`. Do not rely only on `CREATE TABLE IF NOT EXISTS`.

Implement an idempotent migration:

```python
async def migrate_moves_table(db):
    columns = await get_table_columns(db, "moves")
    for column_name, definition in ADDITIONAL_MOVE_COLUMNS.items():
        if column_name not in columns:
            await db.execute(f"ALTER TABLE moves ADD COLUMN {column_name} {definition}")
```

Use a fixed allowlist of column names and definitions; never interpolate user input.

### Game-route integration

In `backend/routes/game.py`, inside `make_move`:

1. Load current FEN and ply.
2. Validate/apply the player's move.
3. Before or immediately after applying it, call:

```python
coach_analysis = await analyse_played_move(
    current_fen,
    req.move_uci,
    depth=18,
    time_limit=0.25,
    multipv=3,
)
```

4. Persist all analysis fields with the player's move row.
5. Return the analysis in `MoveResult`.

Do not classify Stockfish's response as the player's move quality. The opponent's `Skill Level` must not affect the player's objective label.

---

## 7. Frontend integration

Current files:

```text
frontend/index.html
frontend/app.js
frontend/style.css
```

### Required UI changes

1. Change the Coach navigation badge from `Soon` to an active state.
2. Add a coach card to the right panel with:
   - quality badge;
   - win-probability loss;
   - best move;
   - deterministic summary.
3. In `submitMove`, preserve the pre-move FEN and submitted UCI:

```javascript
const preMoveFen = state.fen;
const submittedMove = moveUci;
```

4. After the game endpoint succeeds, call:

```javascript
POST /api/coach/analyze
{
  fen: preMoveFen,
  move_uci: submittedMove
}
```

5. Display the returned label and summary.
6. If the coach call fails, keep the game functional and show a small “Coach analysis unavailable” message.
7. Do not block move submission on the coach request unless the product explicitly requires synchronous analysis.

### Suggested DOM IDs

```text
coach-card
coach-quality-badge
coach-loss
coach-best-move
coach-summary
```

### Visual treatment

Use existing palette:

- best: emerald;
- good: cyan/green;
- inaccuracy: gold;
- mistake: orange;
- blunder: rose.

Keep the card compact so the existing board and move history remain usable.

---

## 8. Tests required

Create:

```text
backend/tests/test_coach_service.py
backend/tests/test_coach_api.py
```

### 8.1 Pure unit tests

Test `cp_to_win_pct`:

- `cp = 0` -> `50.0`
- large positive -> near `100.0`
- large negative -> near `0.0`
- clamping behavior

Test `classify_move` boundaries:

```text
9.999 -> good
10.0 -> inaccuracy
19.999 -> inaccuracy
20.0 -> mistake
29.999 -> mistake
30.0 -> blunder
```

Test `best` precedence:

```text
is_best_move=True, loss=12 -> best
```

### 8.2 Perspective tests

Use mocked `PovScore` objects or a fake engine to verify:

- pre-move score is taken from mover perspective;
- post-move score is also taken from mover perspective even though `board.turn` changed;
- black mover scores are not accidentally interpreted as white scores.

### 8.3 Mate tests

Cover:

- played move gives checkmate -> `is_checkmate=True`;
- move allows a forced mate -> blunder;
- move maintains a forced mate -> best;
- mate scores are not passed into `exp()`;
- `centipawn_loss` is `None` when a mate score is involved.

### 8.4 Illegal input tests

Verify 400/422 responses for:

- malformed FEN;
- malformed UCI;
- illegal move;
- move in a finished game;
- invalid depth/time/multipv.

### 8.5 API tests

Test:

```text
POST /api/coach/analyze
```

with a legal starting-position move and assert:

- HTTP 200;
- `quality_label` is one of the five allowed values;
- `win_pct_before` and `win_pct_after` are in `[0, 100]`;
- `win_pct_loss >= 0`;
- `best_move_san` is present;
- `coach_summary` is non-empty;
- response includes depth and engine metadata.

### 8.6 Integration test

If Stockfish is available:

1. start the real engine;
2. analyse a known legal move;
3. assert the PV and labels are deterministic for fixed settings;
4. run the same request twice and compare all non-timing fields.

---

## 9. Documentation to add

Create:

```text
COACH_ENGINE.md
```

Include:

- research basis and citations above;
- exact label thresholds;
- formula and perspective rules;
- API example;
- explanation that labels are Stockfish-depth-relative;
- explicit statement that `brilliant` is not detected in v1;
- explanation that an LLM is not used for chess reasoning;
- instructions for running tests and starting the backend.

Update `SETUP.md` with:

```text
POST /api/coach/analyze
curl example
label table
Coach Mode UI note
```

---

## 10. Implementation order for the other AI

Use this exact order to minimize rework:

1. Add public Stockfish path helper and score-perspective helpers to `backend/engine_service.py`.
2. Implement pure `cp_to_win_pct` and `classify_move` in `backend/coach_service.py`.
3. Implement `analyse_position` and `analyse_played_move`.
4. Add Pydantic request/response models.
5. Add `/api/coach/analyze` and `/api/coach/labels`.
6. Add SQLite migration and persist player-move analysis in `game.py`.
7. Add unit/API tests.
8. Add the minimal frontend Coach card.
9. Add `COACH_ENGINE.md` and update `SETUP.md`.
10. Run compile, pytest, API smoke test, and browser smoke test.

---

## 11. Acceptance criteria

The implementation is complete only when all of these are true:

- [ ] A legal move can be analysed through `POST /api/coach/analyze`.
- [ ] The response includes before/after win percentages, loss, best move, best line, label, facts, and summary.
- [ ] Labels use winning-chance loss thresholds `10/20/30`, not fixed cp cutoffs.
- [ ] Pre- and post-move scores are always converted to the mover's perspective.
- [ ] Mate scores are handled without logistic conversion or arbitrary cp mapping.
- [ ] `Skill Level` never affects objective move-quality classification.
- [ ] Existing Play Mode still works after game-route integration.
- [ ] Existing SQLite databases migrate without data loss.
- [ ] Unit tests cover all threshold boundaries and mate/perspective cases.
- [ ] The frontend displays a coach result without breaking when the analysis endpoint is unavailable.
- [ ] Documentation clearly states the deterministic guarantees and the non-claim about brilliance.

---

## 12. Key source links

- [Stockfish FAQ](https://official-stockfish.github.io/docs/stockfish-wiki/Stockfish-FAQ.html)
- [Stockfish UCI & Commands](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-%26-Commands.html)
- [python-chess engine docs](https://python-chess.readthedocs.io/en/latest/engine.html)
- [Lichess Advice.scala](https://github.com/lichess-org/lila/blob/ef3225d373693c83ebe53d56410c3c205b3f500e/modules/analyse/src/main/Advice.scala)
- [Lichess WinPercent.scala](https://github.com/lichess-org/lila/blob/02242e97bf5cb7f5e60ef942f437a30cd55b80c0/modules/analyse/src/main/WinPercent.scala)
- [ACT-Eval](https://arxiv.org/html/2608.04240v1)
- [Predicting User Perception of Move Brilliance in Chess](https://arxiv.org/html/2406.11895v1)
- [Jhamtani et al. — Chess commentary generation](https://aclanthology.org/P18-1154/)
- [Concept-guided Chess Commentary, NAACL 2025](https://p.rst.im/q/aclanthology.org/2025.naacl-long.481.pdf)
- [Maia — human move prediction](https://dl.acm.org/doi/10.1145/3394486.3403219)
- [Maia-2](https://proceedings.neurips.cc/paper_files/2024/hash/250190819ff1dda47cd23cecc0c5a69b-Abstract-Conference.html)
- [Lichess Open Database](https://database.lichess.org/)
- [Lichess chess puzzles dataset](https://huggingface.co/datasets/Lichess/chess-puzzles)
- [Chess Debate Puzzles — Stockfish-labeled move-quality bands](https://huggingface.co/datasets/kvoudouris/chess-debate-puzzles)

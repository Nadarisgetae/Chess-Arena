"""
coach_service.py — Deterministic Stockfish-grounded move-quality classifier.

Design principles (from COACH_ENGINE_IMPLEMENTATION_BRIEF.md):
  - All chess facts come from Stockfish + python-chess; no LLM for evaluation.
  - Win-probability loss (not fixed centipawn cutoffs) drives the label.
  - Mover-perspective scores are computed explicitly so black moves are correct.
  - Mate scores never pass through the logistic formula.
  - Skill Level is always 20 for coach analysis — the user's opponent setting
    must not contaminate move-quality classification.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import chess
import chess.engine

from backend.engine_service import _find_stockfish  # reuse existing discovery
from backend.database import get_db
from backend.key_rotator import KeyRotator, load_keys_from_env_or_file
import threading
import asyncio

_rotator_instance = None
_rotator_lock = threading.Lock()

def get_rotator() -> Optional[KeyRotator]:
    global _rotator_instance
    if _rotator_instance is None:
        with _rotator_lock:
            if _rotator_instance is None:
                try:
                    _rotator_instance = KeyRotator(load_keys_from_env_or_file())
                except RuntimeError:
                    _rotator_instance = "NO_KEYS"
    return _rotator_instance if _rotator_instance != "NO_KEYS" else None


# ── Public path helper ──────────────────────────────────────────────────────────

def get_stockfish_path() -> Path:
    """Return the Stockfish binary path (raises FileNotFoundError if missing)."""
    return _find_stockfish()


# ── Win-probability conversion ─────────────────────────────────────────────────

def cp_to_win_pct(cp: float) -> float:
    """
    Convert centipawn score (mover's perspective) to win probability 0–100.

    Uses the exact Lichess constant 0.00368208.
    Input must already be from the mover's perspective (positive = mover winning).
    Clamps the exponent argument for numerical stability with very large |cp|.
    """
    x = max(-700.0, min(700.0, -0.00368208 * cp))
    value = 50 + 50 * (2 / (1 + math.exp(x)) - 1)
    return round(max(0.0, min(100.0, value)), 4)


def _score_to_win_pct(pov_score: chess.engine.PovScore, color: chess.Color) -> tuple[Optional[float], Optional[int]]:
    """
    Convert a PovScore to (win_pct, mate_plies) from `color`'s perspective.

    Returns:
        (win_pct, None)           for a centipawn score
        (100.0 or 0.0, mate)      for a mate score
    """
    relative = pov_score.pov(color)
    if relative.is_mate():
        mate = relative.mate()          # positive = color can force mate
        win_pct = 100.0 if mate > 0 else 0.0
        return win_pct, mate
    else:
        cp = relative.score()
        return cp_to_win_pct(cp), None


# ── Move classifier ─────────────────────────────────────────────────────────────

# Threshold constants (win-probability-loss percentage points)
_INACCURACY_THRESHOLD = 10.0
_MISTAKE_THRESHOLD    = 20.0
_BLUNDER_THRESHOLD    = 30.0
_BEST_EPSILON         = 0.05   # treat loss < epsilon as effectively zero

LABEL_TAXONOMY = [
    {
        "label": "best",
        "description": "Played move is Stockfish's top move, or win-probability loss is effectively zero.",
        "threshold_pp_loss": None,
    },
    {
        "label": "good",
        "description": "Not best, but loss < 10 percentage points.",
        "threshold_pp_loss": "< 10",
    },
    {
        "label": "inaccuracy",
        "description": "Win-probability loss >= 10 and < 20 percentage points.",
        "threshold_pp_loss": "10 <= loss < 20",
    },
    {
        "label": "mistake",
        "description": "Win-probability loss >= 20 and < 30 percentage points.",
        "threshold_pp_loss": "20 <= loss < 30",
    },
    {
        "label": "blunder",
        "description": "Win-probability loss >= 30 percentage points.",
        "threshold_pp_loss": ">= 30",
    },
]


def classify_move(
    win_pct_loss: float,
    is_best_move: bool,
    *,
    mate_context: Optional[str] = None,
) -> str:
    """
    Return one of: best | good | inaccuracy | mistake | blunder.

    Args:
        win_pct_loss:  max(0, win_pct_before - win_pct_after); always >= 0.
        is_best_move:  True when the played UCI matches Stockfish's top PV move.
        mate_context:  Optional string hint for mate edge-cases (not used for
                       threshold classification — only for 'best' short-circuit).
    """
    # Best-move short-circuit: top move is always "best" regardless of
    # search noise causing tiny score differences.
    if is_best_move or win_pct_loss <= _BEST_EPSILON:
        return "best"

    if win_pct_loss < _INACCURACY_THRESHOLD:
        return "good"
    elif win_pct_loss < _MISTAKE_THRESHOLD:
        return "inaccuracy"
    elif win_pct_loss < _BLUNDER_THRESHOLD:
        return "mistake"
    else:
        return "blunder"


# ── Board facts ────────────────────────────────────────────────────────────────

def _extract_board_facts(board_before: chess.Board, move: chess.Move) -> dict:
    """
    Compute deterministic, python-chess-verifiable facts about a move.
    board_before must be the state BEFORE the move is pushed.
    """
    is_capture   = board_before.is_capture(move)
    is_castle    = board_before.is_castling(move)
    is_promotion = bool(move.promotion)
    promotion_piece = chess.piece_name(move.promotion) if move.promotion else None

    board_after = board_before.copy()
    board_after.push(move)

    gives_check  = board_after.is_check()
    is_checkmate = board_after.is_checkmate()
    is_stalemate = board_after.is_stalemate()
    is_draw      = board_after.is_game_over(claim_draw=True) and not is_checkmate and not is_stalemate

    return {
        "is_capture":       is_capture,
        "gives_check":      gives_check,
        "is_checkmate":     is_checkmate,
        "is_stalemate":     is_stalemate,
        "is_draw":          is_draw,
        "is_castle":        is_castle,
        "is_promotion":     is_promotion,
        "promotion_piece":  promotion_piece,
    }


# ── Coach summary builder ──────────────────────────────────────────────────────

def build_coach_summary(analysis: dict) -> str:
    """
    Generate a short deterministic coaching text from the structured analysis dict.
    Never calls an LLM; only uses facts already present in `analysis`.
    """
    label         = analysis.get("quality_label", "good")
    before_pct    = analysis.get("win_pct_before", 50.0)
    after_pct     = analysis.get("win_pct_after", 50.0)
    loss          = analysis.get("win_pct_loss", 0.0)
    best_san      = analysis.get("best_move_san", "?")
    best_line_san = analysis.get("best_line_san", [])
    is_checkmate  = analysis.get("is_checkmate", False)
    allows_mate   = analysis.get("allows_forced_mate", False)

    best_line_str = " ".join(best_line_san[:5]) if best_line_san else best_san

    if is_checkmate:
        return "The move gives checkmate. Well done!"

    parts: list[str] = []

    if label == "best":
        parts.append(
            f"Best move. Stockfish's top line is {best_line_str}. "
            f"This keeps your winning chances at approximately {after_pct:.1f}%."
        )
    elif label == "good":
        parts.append(
            f"Good move. It changes your winning chances from {before_pct:.1f}% to {after_pct:.1f}%, "
            f"a loss of {loss:.1f} percentage points. Stockfish preferred {best_san}."
        )
    elif label == "inaccuracy":
        parts.append(
            f"Inaccuracy. This move loses about {loss:.1f} percentage points of winning chance. "
            f"Stockfish preferred {best_san}; review the position before playing the next move."
        )
    elif label == "mistake":
        parts.append(
            f"Mistake. Your winning chances drop from {before_pct:.1f}% to {after_pct:.1f}%, "
            f"a loss of {loss:.1f} percentage points. Stockfish preferred {best_san}. "
            f"Review the tactic or strategic idea behind the preferred move."
        )
    elif label == "blunder":
        parts.append(
            f"Blunder. This move loses about {loss:.1f} percentage points of winning chance, "
            f"moving from {before_pct:.1f}% to {after_pct:.1f}%. Stockfish preferred {best_san}. "
            f"Stop and recalculate candidate moves before continuing."
        )

    if allows_mate:
        parts.append(
            "The engine reports a forced mate after this move; verify the defensive resources immediately."
        )

    return " ".join(parts)


async def get_coach_explanation(analysis: dict) -> str:
    """
    Tries to generate an LLM explanation using the KeyRotator pool,
    with a database cache check to avoid duplicate calls.
    Falls back to deterministic `build_coach_summary` if no keys or all keys rate-limited.
    """
    fen = analysis.get("fen")
    move_san = analysis.get("move_san")
    # 1. Check DB cache
    if fen and move_san:
        try:
            async with get_db() as db:
                async with db.execute(
                    "SELECT explanation FROM llm_cache WHERE fen = ? AND move_san = ?",
                    (fen, move_san)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return row["explanation"]
        except Exception:
            pass  # fallback if db missing

    canned = build_coach_summary(analysis)
    # 2. Try LLM
    rotator = get_rotator()
    if rotator:
        prompt = [
            {"role": "system", "content": "You are a concise, encouraging chess coach. Do not hallucinate moves or evaluations. Ground your explanation in the provided Stockfish analysis."},
            {"role": "user", "content": f"Explain this move in 1-3 sentences based on this analysis:\n{canned}\nFEN: {fen}\nMove: {move_san}"}
        ]
        loop = asyncio.get_running_loop()
        llm_response = await loop.run_in_executor(None, rotator.call_llm, prompt)
        if llm_response:
            # 3. Cache it
            if fen and move_san:
                try:
                    async with get_db() as db:
                        await db.execute(
                            "INSERT OR IGNORE INTO llm_cache (fen, move_san, explanation, model_used) VALUES (?, ?, ?, ?)",
                            (fen, move_san, llm_response, "openrouter-pool")
                        )
                        await db.commit()
                except Exception:
                    pass
            return llm_response
    # 4. Fallback
    return canned


# ── Core analysis functions ────────────────────────────────────────────────────

async def analyse_position(
    fen: str,
    depth: int = 18,
    time_limit: float = 0.25,
    multipv: int = 3,
) -> dict:
    """
    Analyse a position (before any move is played) and return structured info
    about the top engine lines.
    """
    path = get_stockfish_path()
    board = chess.Board(fen)
    mover_color = board.turn

    transport, engine = await chess.engine.popen_uci(str(path))
    try:
        await engine.configure({"Skill Level": 20})
        engine_id = getattr(engine, "id", {})
        engine_name = engine_id.get("name", "Stockfish") if isinstance(engine_id, dict) else str(engine_id)

        limit = chess.engine.Limit(depth=depth, time=time_limit)
        infos = await engine.analyse(
            board, limit, multipv=multipv,
            info=chess.engine.INFO_ALL,
        )
    finally:
        await engine.quit()

    if not isinstance(infos, list):
        infos = [infos]

    top = infos[0]
    top_score = top.get("score")
    top_pv = top.get("pv", [])

    win_pct_top = 50.0
    mate_in_top = None
    cp_top = None

    if top_score:
        win_pct_top, mate_in_top = _score_to_win_pct(top_score, mover_color)
        if mate_in_top is None:
            cp_top = top_score.pov(mover_color).score()

    best_move = top_pv[0] if top_pv else None
    best_move_uci = best_move.uci() if best_move else None
    best_move_san = board.san(best_move) if best_move else None

    best_line_san: list[str] = []
    _b = board.copy()
    for m in top_pv[:6]:
        try:
            best_line_san.append(_b.san(m))
            _b.push(m)
        except Exception:
            break

    alternatives = []
    for info in infos[1:]:
        pv = info.get("pv", [])
        if not pv:
            continue
        alt_move = pv[0]
        alt_score = info.get("score")
        alt_win_pct = 50.0
        alt_mate = None
        alt_cp = None
        if alt_score:
            alt_win_pct, alt_mate = _score_to_win_pct(alt_score, mover_color)
            if alt_mate is None:
                alt_cp = alt_score.pov(mover_color).score()
        try:
            alt_san = board.san(alt_move)
        except Exception:
            alt_san = alt_move.uci()
        alternatives.append({
            "move_uci":   alt_move.uci(),
            "move_san":   alt_san,
            "win_pct":    alt_win_pct,
            "centipawns": alt_cp,
            "mate_in":    alt_mate,
            "win_pct_loss_vs_best": round(max(0.0, win_pct_top - alt_win_pct), 4),
        })

    return {
        "engine_version":  engine_name,
        "depth":           top.get("depth", depth),
        "time_limit":      time_limit,
        "multipv":         multipv,
        "best_move_uci":   best_move_uci,
        "best_move_san":   best_move_san,
        "best_line":       [m.uci() for m in top_pv[:6]],
        "best_line_san":   best_line_san,
        "alternatives":    alternatives,
        "win_pct":         win_pct_top,
        "centipawns":      cp_top,
        "mate_in":         mate_in_top,
    }


async def analyse_played_move(
    fen: str,
    move_uci: str,
    depth: int = 18,
    time_limit: float = 0.25,
    multipv: int = 3,
) -> dict:
    """
    Full coach analysis for a move played by the user.

    Steps:
      1. Validate FEN and UCI; reject illegal moves.
      2. Analyse pre-move position (mover's perspective).
      3. Push move; analyse post-move position (still mover's perspective).
      4. Compute win-pct loss and classify.
      5. Extract board facts and build summary.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise ValueError(f"Invalid FEN: {exc}") from exc

    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError as exc:
        raise ValueError(f"Invalid UCI: {exc}") from exc

    if move not in board.legal_moves:
        raise ValueError(f"Illegal move {move_uci!r} in position {fen!r}")

    if board.is_game_over():
        raise ValueError("Cannot analyse a move in a finished position.")

    mover_color = board.turn
    move_san = board.san(move)

    facts = _extract_board_facts(board, move)

    path = get_stockfish_path()

    transport, engine = await chess.engine.popen_uci(str(path))
    try:
        await engine.configure({"Skill Level": 20})
        engine_id = getattr(engine, "id", {})
        engine_name = engine_id.get("name", "Stockfish") if isinstance(engine_id, dict) else str(engine_id)

        limit = chess.engine.Limit(depth=depth, time=time_limit)

        # Pre-move analysis
        pre_infos = await engine.analyse(
            board, limit, multipv=multipv,
            info=chess.engine.INFO_ALL,
        )
        if not isinstance(pre_infos, list):
            pre_infos = [pre_infos]

        # Post-move analysis
        board_after = board.copy()
        board_after.push(move)
        post_infos = await engine.analyse(
            board_after, limit, multipv=1,
            info=chess.engine.INFO_ALL,
        )
        if not isinstance(post_infos, list):
            post_infos = [post_infos]

    finally:
        await engine.quit()

    # Pre-move scores (mover's perspective)
    top_pre = pre_infos[0]
    pre_score = top_pre.get("score")
    pre_pv = top_pre.get("pv", [])

    win_pct_before = 50.0
    mate_before = None
    cp_before = None

    if pre_score:
        win_pct_before, mate_before = _score_to_win_pct(pre_score, mover_color)
        if mate_before is None:
            cp_before = pre_score.pov(mover_color).score()

    best_move_obj = pre_pv[0] if pre_pv else None
    best_move_uci_str = best_move_obj.uci() if best_move_obj else None
    try:
        best_move_san = board.san(best_move_obj) if best_move_obj else None
    except Exception:
        best_move_san = best_move_uci_str

    best_line_san: list[str] = []
    _b = board.copy()
    for m in pre_pv[:6]:
        try:
            best_line_san.append(_b.san(m))
            _b.push(m)
        except Exception:
            break

    # Post-move scores (mover's perspective — NOT board_after.turn)
    top_post = post_infos[0]
    post_score = top_post.get("score")

    win_pct_after = 50.0
    mate_after = None
    cp_after = None

    if post_score:
        win_pct_after, mate_after = _score_to_win_pct(post_score, mover_color)
        if mate_after is None:
            cp_after = post_score.pov(mover_color).score()

    win_pct_loss = round(max(0.0, win_pct_before - win_pct_after), 4)

    centipawn_loss: Optional[float] = None
    if cp_before is not None and cp_after is not None:
        centipawn_loss = round(cp_before - cp_after, 2)

    is_best_move = (best_move_uci_str is not None and move_uci == best_move_uci_str)

    # Mate context overrides
    mate_context: Optional[str] = None
    if facts["is_checkmate"]:
        mate_context = "checkmate_by_player"
    elif mate_before is not None and mate_before > 0 and mate_after is not None and mate_after > 0:
        is_best_move = True
        mate_context = "maintains_mate"
    elif mate_before is not None and mate_before > 0 and (mate_after is None or mate_after <= 0):
        mate_context = "missed_forced_mate"
    elif mate_after is not None and mate_after < 0:
        mate_context = "allows_forced_mate"

    allows_forced_mate = (mate_after is not None and mate_after < 0)

    if facts["is_checkmate"]:
        quality_label = "best"
    else:
        quality_label = classify_move(win_pct_loss, is_best_move, mate_context=mate_context)

    # Alternatives
    alternatives = []
    for info in pre_infos[1:]:
        pv = info.get("pv", [])
        if not pv:
            continue
        alt_move = pv[0]
        alt_score = info.get("score")
        alt_win_pct = 50.0
        alt_mate_in = None
        alt_cp = None
        if alt_score:
            alt_win_pct, alt_mate_in = _score_to_win_pct(alt_score, mover_color)
            if alt_mate_in is None:
                alt_cp = alt_score.pov(mover_color).score()
        try:
            alt_san = board.san(alt_move)
        except Exception:
            alt_san = alt_move.uci()
        alternatives.append({
            "move_uci":   alt_move.uci(),
            "move_san":   alt_san,
            "win_pct":    alt_win_pct,
            "centipawns": alt_cp,
            "mate_in":    alt_mate_in,
            "win_pct_loss_vs_best": round(max(0.0, win_pct_before - alt_win_pct), 4),
        })

    analysis = {
        "fen":               fen,
        "move_uci":          move_uci,
        "move_san":          move_san,
        "quality_label":     quality_label,
        "win_pct_before":    round(win_pct_before, 4),
        "win_pct_after":     round(win_pct_after, 4),
        "win_pct_loss":      win_pct_loss,
        "centipawn_loss":    centipawn_loss,
        "best_move_uci":     best_move_uci_str,
        "best_move_san":     best_move_san,
        "best_line":         [m.uci() for m in pre_pv[:6]],
        "best_line_san":     best_line_san,
        "alternatives":      alternatives,
        "is_capture":        facts["is_capture"],
        "gives_check":       facts["gives_check"],
        "is_checkmate":      facts["is_checkmate"],
        "is_stalemate":      facts["is_stalemate"],
        "is_draw":           facts["is_draw"],
        "is_castle":         facts["is_castle"],
        "is_promotion":      facts["is_promotion"],
        "promotion_piece":   facts["promotion_piece"],
        "allows_forced_mate": allows_forced_mate,
        "depth":             top_pre.get("depth", depth),
        "time_limit":        time_limit,
        "engine":            engine_name,
    }

    analysis["coach_summary"] = await get_coach_explanation(analysis)
    return analysis

"""
engine_service.py — Async Stockfish wrapper using python-chess.

Exposes clean, high-level functions consumed by route handlers.
All chess logic and evaluation lives here; routes are thin.

Stockfish binary must be placed at:
    backend/stockfish/stockfish.exe  (Windows)
    backend/stockfish/stockfish      (Linux/macOS)

Or set STOCKFISH_PATH environment variable to the full path.
"""

import asyncio
import math
import os
from pathlib import Path
from typing import Optional
import chess
import chess.engine
import chess.pgn

# ── Configuration ──────────────────────────────────────────────────────────────

def _find_stockfish() -> Path:
    """Locate the Stockfish binary. Check env var first, then bundled path."""
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    base = Path(__file__).parent / "stockfish"
    candidates = [
        base / "stockfish.exe",
        base / "stockfish",
        base / "stockfish-windows-x86-64.exe",
        base / "stockfish-ubuntu-x86-64",
    ]
    for c in candidates:
        if c.exists():
            return c

    raise FileNotFoundError(
        "Stockfish binary not found. Download from https://stockfishchess.org/download/ "
        "and place it in backend/stockfish/ or set STOCKFISH_PATH env var."
    )


STOCKFISH_PATH = _find_stockfish() if Path(Path(__file__).parent / "stockfish").exists() else None
_engine_lock = asyncio.Lock()


# ── Win Probability Conversion ─────────────────────────────────────────────────

def cp_to_win_pct(cp: Optional[int], side: chess.Color = chess.WHITE) -> float:
    """
    Convert centipawn score to white's win probability (0–100).
    Uses the Lichess logistic formula, which is well-calibrated against real games.
    """
    if cp is None:
        return 50.0
    # Adjust sign: cp is always from the perspective of the side to move in
    # python-chess's PovScore. Normalise to white's perspective.
    if side == chess.BLACK:
        cp = -cp
    win = 50 + 50 * (2 / (1 + math.exp(-0.00368 * cp)) - 1)
    return round(win, 2)


# ── Core Engine Functions ──────────────────────────────────────────────────────

async def _run_analysis(
    fen: str,
    depth: int = 15,
    time_limit: float = 0.1,
    skill_level: int = 20,
    multipv: int = 1,
) -> list[chess.engine.InfoDict]:
    """
    Open a transient Stockfish process, analyse the given FEN, return raw info dicts.
    Each call creates and cleanly terminates its own engine process so that the
    service stays stateless and safe for concurrent requests.
    """
    path = _find_stockfish()
    board = chess.Board(fen)

    transport, engine = await chess.engine.popen_uci(str(path))
    try:
        await engine.configure({"Skill Level": skill_level})
        limit = chess.engine.Limit(depth=depth, time=time_limit)
        result = await engine.analyse(
            board, limit, multipv=multipv,
            info=chess.engine.INFO_ALL,
        )
    finally:
        await engine.quit()

    return result if isinstance(result, list) else [result]


async def get_eval(fen: str, depth: int = 15) -> dict:
    """
    Return centipawn evaluation and win percentage for a given FEN.
    Mate scores are surfaced as mate_in (positive = mate for side to move).
    """
    board = chess.Board(fen)
    infos = await _run_analysis(fen, depth=depth, time_limit=0.2, skill_level=20)
    info = infos[0]

    score = info.get("score")
    cp = None
    mate_in = None
    if score:
        pov_score = score.white()
        if pov_score.is_mate():
            mate_in = pov_score.mate()
            # Convert mate to a large centipawn equivalent for win_pct
            cp = 10000 if mate_in and mate_in > 0 else -10000
        else:
            cp = pov_score.score()

    win_pct = cp_to_win_pct(cp, side=chess.WHITE)

    return {
        "fen": fen,
        "centipawns": cp if mate_in is None else None,
        "mate_in": mate_in,
        "win_pct": win_pct,
        "depth": info.get("depth", depth),
    }


async def get_best_move(
    fen: str,
    skill_level: int = 10,
    depth: int = 15,
    time_limit: float = 0.1,
) -> dict:
    """
    Return the best move for the current position, optionally with a skill cap.
    """
    board = chess.Board(fen)
    path = _find_stockfish()

    transport, engine = await chess.engine.popen_uci(str(path))
    try:
        await engine.configure({"Skill Level": skill_level})
        limit = chess.engine.Limit(depth=depth, time=time_limit)
        result = await engine.play(board, limit)
        info = await engine.analyse(board, limit)
    finally:
        await engine.quit()

    move = result.move
    move_san = board.san(move)
    board.push(move)

    score = info.get("score")
    cp = None
    mate_in = None
    if score:
        pov = score.white()
        if pov.is_mate():
            mate_in = pov.mate()
            cp_equiv = 10000 if mate_in and mate_in > 0 else -10000
        else:
            cp = pov.score()
            cp_equiv = cp

    win_pct = cp_to_win_pct(cp, side=chess.WHITE)

    return {
        "fen": fen,
        "best_move_uci": move.uci(),
        "best_move_san": move_san,
        "ponder": result.ponder.uci() if result.ponder else None,
        "centipawns": cp,
        "mate_in": mate_in,
        "win_pct": win_pct,
        "depth": info.get("depth", depth),
    }


def get_legal_moves(fen: str) -> list[str]:
    """Return all legal moves in UCI notation for the given position."""
    board = chess.Board(fen)
    return [m.uci() for m in board.legal_moves]


def apply_move(fen: str, move_uci: str) -> dict:
    """
    Validate and apply a UCI move to a position.
    Returns the new FEN, SAN, check/game-over status, and result string.
    Raises ValueError if the move is illegal.
    """
    board = chess.Board(fen)
    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError:
        raise ValueError(f"Invalid UCI format: {move_uci!r}")

    if move not in board.legal_moves:
        raise ValueError(f"Illegal move {move_uci!r} in position {fen!r}")

    san = board.san(move)
    board.push(move)
    new_fen = board.fen()

    game_over = board.is_game_over()
    result_str = board.result() if game_over else None

    termination = None
    if game_over:
        if board.is_checkmate():
            termination = "checkmate"
        elif board.is_stalemate():
            termination = "stalemate"
        elif board.is_insufficient_material():
            termination = "insufficient_material"
        elif board.is_seventyfive_moves():
            termination = "75_move_rule"
        elif board.is_fivefold_repetition():
            termination = "fivefold_repetition"
        else:
            termination = "draw"

    return {
        "new_fen": new_fen,
        "san": san,
        "game_over": game_over,
        "result": result_str,
        "termination": termination,
        "is_check": board.is_check(),
    }


def fen_to_pgn(moves_san: list[str], starting_fen: str = chess.STARTING_FEN) -> str:
    """Build a PGN string from a list of SAN moves and an optional starting FEN."""
    game = chess.pgn.Game()
    if starting_fen != chess.STARTING_FEN:
        game.headers["FEN"] = starting_fen
        game.setup(chess.Board(starting_fen))

    node = game
    board = chess.Board(starting_fen)
    for san in moves_san:
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)

    return str(game)

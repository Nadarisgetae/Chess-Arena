"""
routes/engine.py — Pure engine analysis endpoints.
No game state, no DB — these are stateless evaluation helpers.
"""

from fastapi import APIRouter, Query, HTTPException
from backend.engine_service import get_eval, get_best_move, get_legal_moves
from backend.models import EvalResponse, BestMoveResponse, LegalMovesResponse
import chess

router = APIRouter(prefix="/engine", tags=["Engine"])


@router.get("/eval", response_model=EvalResponse, summary="Evaluate a position")
async def evaluate_position(
    fen: str = Query(
        default=chess.STARTING_FEN,
        description="FEN string of the position to evaluate"
    ),
    depth: int = Query(default=15, ge=1, le=25, description="Search depth"),
):
    """
    Return the centipawn evaluation and win probability for a FEN position.
    If a forced mate is detected, centipawns will be None and mate_in is set.
    """
    try:
        chess.Board(fen)  # Validate FEN
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {fen!r}")

    try:
        result = await get_eval(fen, depth=depth)
        return EvalResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine error: {e}")


@router.get("/bestmove", response_model=BestMoveResponse, summary="Get best move")
async def best_move(
    fen: str = Query(default=chess.STARTING_FEN, description="FEN string"),
    depth: int = Query(default=15, ge=1, le=25),
    skill_level: int = Query(default=10, ge=0, le=20),
    time_limit: float = Query(default=0.1, ge=0.05, le=5.0),
):
    """
    Return the best move in UCI and SAN notation for the given position.
    skill_level 0 = weakest (Elo ~800), 20 = strongest (full Stockfish).
    """
    try:
        chess.Board(fen)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {fen!r}")

    try:
        result = await get_best_move(fen, skill_level=skill_level, depth=depth, time_limit=time_limit)
        return BestMoveResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine error: {e}")


@router.get("/legalmoves", response_model=LegalMovesResponse, summary="Get legal moves")
async def legal_moves(
    fen: str = Query(default=chess.STARTING_FEN, description="FEN string"),
):
    """Return all legal moves in UCI notation for the given FEN position."""
    try:
        chess.Board(fen)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {fen!r}")

    moves = get_legal_moves(fen)
    return LegalMovesResponse(fen=fen, legal_moves=moves)

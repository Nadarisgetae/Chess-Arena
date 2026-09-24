"""
routes/coach.py — Coach Mode API endpoints.

POST /api/coach/analyze   — full deterministic move-quality analysis
GET  /api/coach/labels    — label taxonomy (thresholds, descriptions)
"""

import chess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.coach_service import analyse_played_move, LABEL_TAXONOMY

router = APIRouter(prefix="/coach", tags=["Coach"])


# ── Request / Response models ──────────────────────────────────────────────────

class CoachAnalyzeRequest(BaseModel):
    fen: str = Field(
        default=chess.STARTING_FEN,
        description="FEN of the position BEFORE the move was played",
    )
    move_uci: str = Field(
        description="Move in UCI notation, e.g. 'e2e4', 'e7e8q'"
    )
    depth: int = Field(
        default=18, ge=12, le=25,
        description="Stockfish search depth (12–25)"
    )
    time_limit: float = Field(
        default=0.25, ge=0.10, le=2.0,
        description="Stockfish time limit in seconds"
    )
    multipv: int = Field(
        default=3, ge=1, le=5,
        description="Number of top lines to analyse"
    )


class AlternativeMove(BaseModel):
    move_uci: str
    move_san: str
    win_pct: float
    centipawns: Optional[int] = None
    mate_in: Optional[int] = None
    win_pct_loss_vs_best: float


class CoachAnalyzeResponse(BaseModel):
    # Position
    fen: str
    move_uci: str
    move_san: str
    # Classification
    quality_label: str
    win_pct_before: float
    win_pct_after: float
    win_pct_loss: float
    centipawn_loss: Optional[float] = None
    # Best move info
    best_move_uci: Optional[str] = None
    best_move_san: Optional[str] = None
    best_line: list[str] = []
    best_line_san: list[str] = []
    alternatives: list[AlternativeMove] = []
    # Board facts
    is_capture: bool = False
    gives_check: bool = False
    is_checkmate: bool = False
    is_stalemate: bool = False
    is_draw: bool = False
    is_castle: bool = False
    is_promotion: bool = False
    promotion_piece: Optional[str] = None
    allows_forced_mate: bool = False
    # Engine metadata
    depth: int
    time_limit: float
    engine: str
    # Coach output
    coach_summary: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=CoachAnalyzeResponse,
    summary="Analyse a played move — deterministic coach report",
)
async def analyze_move(req: CoachAnalyzeRequest):
    """
    Perform a full Stockfish-grounded move-quality analysis.

    Returns win-probability before/after, a quality label (best/good/inaccuracy/
    mistake/blunder), best move and principal variation, deterministic board facts,
    and a short coaching summary — all without any LLM involvement.

    Skill Level is always 20 for this endpoint; the user's game opponent skill
    level must not contaminate objective move-quality classification.
    """
    # Validate FEN
    try:
        chess.Board(req.fen)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {req.fen!r}")

    try:
        result = await analyse_played_move(
            fen=req.fen,
            move_uci=req.move_uci,
            depth=req.depth,
            time_limit=req.time_limit,
            multipv=req.multipv,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Engine error: {exc}")

    return CoachAnalyzeResponse(**result)


@router.get(
    "/labels",
    summary="Return the move-quality label taxonomy and thresholds",
)
async def get_labels():
    """
    Return the complete label taxonomy with descriptions and threshold rules.

    Intended for frontend consumers and future agents so they do not need to
    hardcode undocumented threshold logic.
    """
    return {
        "labels": LABEL_TAXONOMY,
        "notes": [
            "Labels are based on win-probability-loss (percentage points), not fixed centipawn cutoffs.",
            "Win probability uses the Lichess logistic formula with constant 0.00368208.",
            "The 'brilliant' label is not implemented in v1; it requires additional criteria.",
            "Labels reflect Stockfish depth-relative analysis, not mathematical proof.",
        ],
    }

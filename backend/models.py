"""
models.py — Pydantic v2 request/response schemas for the Chess Arena API.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ── Engine Models ──────────────────────────────────────────────────────────────

class EvalResponse(BaseModel):
    fen: str
    centipawns: Optional[int] = None      # None when forced mate is detected
    mate_in: Optional[int] = None         # positive = engine wins, negative = engine loses
    win_pct: float                        # 0–100, white's winning probability
    depth: int


class BestMoveResponse(BaseModel):
    fen: str
    best_move_uci: str
    best_move_san: str
    ponder: Optional[str] = None
    centipawns: Optional[int] = None
    mate_in: Optional[int] = None
    win_pct: float
    depth: int


class LegalMovesResponse(BaseModel):
    fen: str
    legal_moves: list[str]               # UCI notation


# ── Game Models ────────────────────────────────────────────────────────────────

class NewGameRequest(BaseModel):
    player_id: str = Field(default="guest", description="Player identifier")
    skill_level: int | str = Field(
        default="auto",
        description="Stockfish Skill Level 0-20, or 'auto' for Statistical Player Model"
    )
    player_color: str = Field(
        default="white",
        pattern="^(white|black)$",
        description="Which color the human plays"
    )


class NewGameResponse(BaseModel):
    game_id: str
    fen: str
    player_color: str
    skill_level: int
    # If player chose black, engine plays first automatically
    engine_move: Optional[str] = None
    engine_move_san: Optional[str] = None
    fen_after_engine: Optional[str] = None


class MakeMoveRequest(BaseModel):
    move_uci: str = Field(
        description="Move in UCI format, e.g. 'e2e4', 'e7e8q' for promotion"
    )
    time_limit: float = Field(
        default=0.1,
        ge=0.05, le=5.0,
        description="Seconds Stockfish has to respond"
    )


class MoveResult(BaseModel):
    legal: bool
    fen_after_player: str                # position after player's move
    player_move_san: str
    engine_move_uci: Optional[str] = None
    engine_move_san: Optional[str] = None
    fen_after_engine: Optional[str] = None
    eval_centipawns: Optional[int] = None
    eval_mate_in: Optional[int] = None
    win_pct: Optional[float] = None
    game_over: bool = False
    game_result: Optional[str] = None    # "1-0", "0-1", "1/2-1/2"
    termination: Optional[str] = None    # "checkmate", "stalemate", "draw", etc.
    is_check: bool = False
    # Coach analysis (populated when Stockfish analysis succeeds)
    coach_quality_label: Optional[str] = None
    coach_win_pct_before: Optional[float] = None
    coach_win_pct_after: Optional[float] = None
    coach_win_pct_loss: Optional[float] = None
    coach_best_move_san: Optional[str] = None
    coach_best_line_san: Optional[list[str]] = None
    coach_summary: Optional[str] = None



class GameStatusResponse(BaseModel):
    game_id: str
    fen: str
    skill_level: int
    player_color: str
    game_over: bool
    result: Optional[str] = None
    termination: Optional[str] = None
    pgn: Optional[str] = None
    move_count: int


class ResignRequest(BaseModel):
    player_id: str = "guest"


class ResignResponse(BaseModel):
    game_id: str
    result: str
    message: str

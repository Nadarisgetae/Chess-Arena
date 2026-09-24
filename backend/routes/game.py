"""
routes/game.py — Stateful game management endpoints.
Persists game state (FEN, moves, PGN) in SQLite.
"""

import json
import uuid
import chess
import chess.pgn
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.engine_service import apply_move, get_best_move
from backend.coach_service import analyse_played_move
from backend.player_model import PlayerDifficultyModel
from backend.models import (
    NewGameRequest, NewGameResponse,
    MakeMoveRequest, MoveResult,
    GameStatusResponse,
    ResignRequest, ResignResponse,
)

router = APIRouter(prefix="/game", tags=["Game"])


# ── Helper ─────────────────────────────────────────────────────────────────────

async def _load_game(game_id: str) -> dict:
    """Fetch a game row from DB. Raises 404 if not found."""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM games WHERE id = ?", (game_id,)
        ) as cur:
            row = await cur.fetchone()
    finally:
        await db.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id!r} not found")
    return dict(row)


async def _load_moves(game_id: str) -> list[dict]:
    """Return all move rows for a game, ordered by ply."""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM moves WHERE game_id = ? ORDER BY ply_number",
            (game_id,),
        ) as cur:
            rows = await cur.fetchall()
    finally:
        await db.close()
    return [dict(r) for r in rows]


def _current_fen(game: dict, moves: list[dict]) -> str:
    """Return the latest FEN: last move's fen_after, or the starting FEN."""
    if moves:
        return moves[-1]["fen_after"]
    return chess.STARTING_FEN


def _rebuild_pgn(moves: list[dict]) -> str:
    """Rebuild PGN from stored SAN moves."""
    game = chess.pgn.Game()
    node = game
    board = chess.Board()
    for m in moves:
        move = board.parse_san(m["move_san"])
        node = node.add_variation(move)
        board.push(move)
    return str(game)


async def _update_player_stats(player_id: str) -> None:
    """Update aggregated stats in player_profile after a game ends."""
    db = await get_db()
    try:
        async with db.execute("""
            SELECT                COUNT(DISTINCT g.id) as games,
                AVG(m.centipawn_loss) as avg_cp_loss,
                CAST(SUM(CASE WHEN m.quality_label = 'blunder' THEN 1 ELSE 0 END) AS FLOAT) /
                    NULLIF(COUNT(m.id), 0) as blunder_rate
            FROM games g
            LEFT JOIN moves m ON g.id = m.game_id
            WHERE g.player_id = ? AND g.result IS NOT NULL
        """, (player_id,)) as cur:
            stats = await cur.fetchone()
               if stats and stats["games"] > 0:
            await db.execute("""
                INSERT INTO player_profile (player_id, games_played, avg_centipawn_loss, blunder_rate)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(player_id) DO UPDATE SET
                    games_played = excluded.games_played,
                    avg_centipawn_loss = excluded.avg_centipawn_loss,
                    blunder_rate = excluded.blunder_rate,
                    updated_at = datetime('now')
            """, (player_id, stats["games"], stats["avg_cp_loss"], stats["blunder_rate"]))
            await db.commit()
    finally:
        await db.close()

# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/new", response_model=NewGameResponse, summary="Start a new game")
async def new_game(req: NewGameRequest):
    """
    Create a new game record in the DB. If the player chose black,
    Stockfish plays the first move immediately.
    """
    game_id = str(uuid.uuid4())
    starting_fen = chess.STARTING_FEN

    db = await get_db()

    actual_skill = 10
    if req.skill_level == "auto":
        # Load player profile and history to predict optimal skill
        try:
            async with db.execute("SELECT * FROM player_profile WHERE player_id = ?", (req.player_id,)) as cur:
                profile_row = await cur.fetchone()
                       profile = dict(profile_row) if profile_row else {}

            async with db.execute("""
                SELECT                    g.engine_skill_level,
                    g.result,
                    AVG(m.centipawn_loss) as avg_cp_loss
                FROM games g
                LEFT JOIN moves m ON g.id = m.game_id
                WHERE g.player_id = ? AND g.result IS NOT NULL
                GROUP BY g.id
                ORDER BY g.started_at DESC LIMIT 50
            """, (req.player_id,)) as cur:
                history_rows = await cur.fetchall()

            history = []
            for r in history_rows:
                res_score = 0.5
                if r["result"] == "1-0":
                    res_score = 1.0 if req.player_color == "white" else 0.0
                elif r["result"] == "0-1":
                    res_score = 0.0 if req.player_color == "white" else 1.0

                history.append({
                    "engine_skill_level": r["engine_skill_level"],
                    "result_score": res_score,
                    "avg_cp_loss": r["avg_cp_loss"] or 50.0,
                })

            model = PlayerDifficultyModel()
            model.fit(history)
            actual_skill = model.predict_optimal_skill(profile)
        except Exception:
            actual_skill = 10
    else:
        actual_skill = int(req.skill_level)

    try:
        await db.execute(
            """INSERT INTO games (id, player_id, mode, engine_skill_level, pgn)
               VALUES (?, ?, 'play', ?, '')""",
            (game_id, req.player_id, actual_skill),
        )
        await db.commit()
    finally:
        await db.close()

    response = NewGameResponse(
        game_id=game_id,
        fen=starting_fen,
        player_color=req.player_color,
        skill_level=actual_skill,
    )

    # If player chose black, engine makes the first move
    if req.player_color == "black":
        engine_result = await get_best_move(
            starting_fen,
            skill_level=actual_skill,
            time_limit=0.1,
        )
        move_data = apply_move(starting_fen, engine_result["best_move_uci"])

        # Persist engine's first move
        move_id = str(uuid.uuid4())
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO moves
                   (id, game_id, ply_number, move_san, move_uci, fen_before, fen_after)
                   VALUES (?, ?, 1, ?, ?, ?, ?)""",
                (
                    move_id, game_id, 1,
                    move_data["san"],
                    engine_result["best_move_uci"],
                    starting_fen,
                    move_data["new_fen"],
                ),
            )
            await db.commit()
        finally:
            await db.close()

        response.engine_move = engine_result["best_move_uci"]
        response.engine_move_san = move_data["san"]
        response.fen_after_engine = move_data["new_fen"]

    return response


@router.post("/{game_id}/move", response_model=MoveResult, summary="Make a move")
async def make_move(game_id: str, req: MakeMoveRequest):
    """
    Apply the player's move, validate it, persist it, then get and apply
    Stockfish's response. Returns both positions and full eval info.
    """
    game = await _load_game(game_id)
    if game["ended_at"]:
        raise HTTPException(status_code=400, detail="This game has already ended.")

    moves = await _load_moves(game_id)
    current_fen = _current_fen(game, moves)
    ply = len(moves) + 1

    # --- Player move ---
    try:
        player_data = apply_move(current_fen, req.move_uci)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Persist player move (initial row — coach fields written below)
    player_move_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO moves
               (id, game_id, ply_number, move_san, move_uci, fen_before, fen_after)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                player_move_id, game_id, ply,
                player_data["san"], req.move_uci,
                current_fen, player_data["new_fen"],
            ),
        )
        await db.commit()
    finally:
        await db.close()

    # Run coach analysis on the player's move (non-blocking on failure)
    coach_data: dict = {}
    try:
        coach_data = await analyse_played_move(
            fen=current_fen,
            move_uci=req.move_uci,
            depth=18,
            time_limit=0.25,
            multipv=3,
        )
        # Persist coach fields back into the move row
        db = await get_db()
        try:
            await db.execute(
                """UPDATE moves SET
                   quality_label = ?, win_pct_before = ?, win_pct_after = ?,
                   win_pct_loss = ?, centipawn_loss = ?, best_move_san = ?,
                   best_line = ?, coach_summary = ?, analysis_json = ?,
                   engine_depth = ?, engine_time_limit = ?, engine_version = ?,
                   is_best_move = ?, is_check = ?, is_capture = ?,
                   is_castle = ?, is_promotion = ?
                   WHERE id = ?""",
                (
                    coach_data.get("quality_label"),
                    coach_data.get("win_pct_before"),
                    coach_data.get("win_pct_after"),
                    coach_data.get("win_pct_loss"),
                    coach_data.get("centipawn_loss"),
                    coach_data.get("best_move_san"),
                    json.dumps(coach_data.get("best_line", [])),
                    coach_data.get("coach_summary"),
                    json.dumps(coach_data),
                    coach_data.get("depth"),
                    coach_data.get("time_limit"),
                    coach_data.get("engine"),
                    int(coach_data.get("quality_label") == "best"),
                    int(coach_data.get("gives_check", False)),
                    int(coach_data.get("is_capture", False)),
                    int(coach_data.get("is_castle", False)),
                    int(coach_data.get("is_promotion", False)),
                    player_move_id,
                ),
            )
            await db.commit()
        finally:
            await db.close()
    except Exception:
        # Coach analysis failure must never break the game flow
        pass

    if player_data["game_over"]:
        # Update game record
        db = await get_db()
        try:
            await db.execute(
                "UPDATE games SET result = ?, ended_at = datetime('now') WHERE id = ?",
                (player_data["result"], game_id),
            )
            await db.commit()
        finally:
            await db.close()

        await _update_player_stats(game["player_id"])

        return MoveResult(
            legal=True,
            fen_after_player=player_data["new_fen"],
            player_move_san=player_data["san"],
            game_over=True,
            game_result=player_data["result"],
            termination=player_data["termination"],
            is_check=player_data["is_check"],
            coach_quality_label=coach_data.get("quality_label"),
            coach_win_pct_before=coach_data.get("win_pct_before"),
            coach_win_pct_after=coach_data.get("win_pct_after"),
            coach_win_pct_loss=coach_data.get("win_pct_loss"),
            coach_best_move_san=coach_data.get("best_move_san"),
            coach_best_line_san=coach_data.get("best_line_san"),
            coach_summary=coach_data.get("coach_summary"),
        )

    # --- Engine response ---
    engine_result = await get_best_move(
        player_data["new_fen"],
        skill_level=game["engine_skill_level"],
        time_limit=req.time_limit,
    )

    engine_move_data = apply_move(
        player_data["new_fen"], engine_result["best_move_uci"]
    )

    engine_ply = ply + 1
    engine_move_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO moves
               (id, game_id, ply_number, move_san, move_uci, fen_before, fen_after)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                engine_move_id, game_id, engine_ply,
                engine_move_data["san"],
                engine_result["best_move_uci"],
                player_data["new_fen"],
                engine_move_data["new_fen"],
            ),
        )
        if engine_move_data["game_over"]:
            await db.execute(
                "UPDATE games SET result = ?, ended_at = datetime('now') WHERE id = ?",
                (engine_move_data["result"], game_id),
            )
        await db.commit()
    finally:
        await db.close()

    if engine_move_data["game_over"]:
        await _update_player_stats(game["player_id"])

    return MoveResult(
        legal=True,
        fen_after_player=player_data["new_fen"],
        player_move_san=player_data["san"],
        engine_move_uci=engine_result["best_move_uci"],
        engine_move_san=engine_move_data["san"],
        fen_after_engine=engine_move_data["new_fen"],
        eval_centipawns=engine_result.get("centipawns"),
        eval_mate_in=engine_result.get("mate_in"),
        win_pct=engine_result.get("win_pct"),
        game_over=engine_move_data["game_over"],
        game_result=engine_move_data["result"] if engine_move_data["game_over"] else None,
        termination=engine_move_data["termination"],
        is_check=engine_move_data["is_check"],
        coach_quality_label=coach_data.get("quality_label"),
        coach_win_pct_before=coach_data.get("win_pct_before"),
        coach_win_pct_after=coach_data.get("win_pct_after"),
        coach_win_pct_loss=coach_data.get("win_pct_loss"),
        coach_best_move_san=coach_data.get("best_move_san"),
        coach_best_line_san=coach_data.get("best_line_san"),
        coach_summary=coach_data.get("coach_summary"),
    )


@router.get("/{game_id}", response_model=GameStatusResponse, summary="Get game status")
async def get_game(game_id: str):
    """Return the current state and history of a game."""
    game = await _load_game(game_id)
    moves = await _load_moves(game_id)
    current_fen = _current_fen(game, moves)

    board = chess.Board(current_fen)
    game_over = board.is_game_over() or bool(game["ended_at"])
    pgn = _rebuild_pgn(moves) if moves else ""

    return GameStatusResponse(
        game_id=game_id,
        fen=current_fen,
        skill_level=game["engine_skill_level"],
        player_color="white",  # stored in session in Phase 1
        game_over=game_over,
        result=game["result"],
        termination=None,
        pgn=pgn,
        move_count=len(moves),
    )


@router.post("/{game_id}/resign", response_model=ResignResponse, summary="Resign the game")
async def resign(game_id: str, req: ResignRequest):
    """Resign the game — records result as 0-1 (engine wins)."""
    game = await _load_game(game_id)
    if game["ended_at"]:
        raise HTTPException(status_code=400, detail="Game already ended.")

    db = await get_db()
    try:
        await db.execute(
            "UPDATE games SET result = '0-1', ended_at = datetime('now') WHERE id = ?",
            (game_id,),
        )
        await db.commit()
    finally:
        await db.close()

    await _update_player_stats(game["player_id"])

    return ResignResponse(
        game_id=game_id,
        result="0-1",
        message="You resigned. Better luck next time!",
    )

"""
routes/analytics.py — Player Performance Analytics API endpoints.

GET /api/analytics/player/{player_id} — Comprehensive KPI breakdown, historical progression,
                                       move quality distributions, and repertoire stats.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import get_db
from backend.rag_service import get_rag_knowledge_base

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = logging.getLogger("analytics_routes")


class PlayerSummaryKPI(BaseModel):
    games_played: int
    wins: int
    draws: int
    losses: int
    win_rate_pct: float
    current_skill_estimate: float
    avg_centipawn_loss: float
    blunder_rate_pct: float


class GameHistoryPoint(BaseModel):
    game_id: str
    date: str
    result: str
    player_color: str
    acpl: float
    blunders: int
    skill_level: int


class MoveQualityDistribution(BaseModel):
    best: int
    good: int
    inaccuracy: int
    mistake: int
    blunder: int


class OpeningStats(BaseModel):
    eco: str
    name: str
    games: int
    win_rate_pct: float
    avg_cp_loss: float


class ColorStats(BaseModel):
    games: int
    win_rate_pct: float
    avg_cp_loss: float


class PlayerAnalyticsResponse(BaseModel):
    player_id: str
    summary: PlayerSummaryKPI
    move_quality_distribution: MoveQualityDistribution
    history_progression: List[GameHistoryPoint]
    openings_repertoire: List[OpeningStats]
    color_asymmetry: Dict[str, ColorStats]


@router.get(
    "/player/{player_id}",
    response_model=PlayerAnalyticsResponse,
    summary="Get complete analytical KPI breakdown for a player",
)
async def get_player_analytics(
    player_id: str,
    limit: int = Query(default=30, ge=5, le=100),
):
    db = await get_db()
    try:
        # 1. Fetch player profile
        async with db.execute(
            "SELECT * FROM player_profile WHERE player_id = ?",
            (player_id,),
        ) as cur:
            profile_row = await cur.fetchone()

        skill_estimate = float(profile_row["skill_estimate"]) if profile_row and profile_row["skill_estimate"] else 1200.0

        # 2. Fetch completed games
        async with db.execute(
            """
            SELECT id, mode, pgn, result, engine_skill_level, started_at,
                   COALESCE(player_color, 'white') as player_color
            FROM games
            WHERE player_id = ? AND result IS NOT NULL
            ORDER BY started_at DESC
            """,
            (player_id,),
        ) as cur:
            games = await cur.fetchall()

        total_games = len(games)
        wins = 0
        draws = 0
        losses = 0

        color_records: Dict[str, Dict[str, Any]] = {
            "white": {"games": 0, "wins": 0, "cp_sum": 0.0, "moves": 0},
            "black": {"games": 0, "wins": 0, "cp_sum": 0.0, "moves": 0},
        }

        for g in games:
            color = g["player_color"].lower() if g["player_color"] else "white"
            res = g["result"]
            if color not in color_records:
                color = "white"

            color_records[color]["games"] += 1

            if res in ("1/2-1/2", "draw"):
                draws += 1
            elif (res == "1-0" and color == "white") or (res == "0-1" and color == "black"):
                wins += 1
                color_records[color]["wins"] += 1
            else:
                losses += 1

        win_rate = round((wins / total_games) * 100.0, 1) if total_games > 0 else 0.0

        # 3. Move Quality Distribution & ACPL
        async with db.execute(
            """
            SELECT m.quality_label, m.centipawn_loss, g.player_color, m.move_san, m.ply_number
            FROM moves m
            JOIN games g ON m.game_id = g.id
            WHERE g.player_id = ? AND g.result IS NOT NULL
            """,
            (player_id,),
        ) as cur:
            all_moves = await cur.fetchall()

        mq_counts = {"best": 0, "good": 0, "inaccuracy": 0, "mistake": 0, "blunder": 0}
        total_cp_loss = 0.0
        evaluated_moves_count = 0

        opening_moves_sample: List[str] = []

        for m in all_moves:
            lbl = (m["quality_label"] or "").lower()
            if lbl in mq_counts:
                mq_counts[lbl] += 1

            cp = m["centipawn_loss"]
            if cp is not None:
                total_cp_loss += float(cp)
                evaluated_moves_count += 1

                c = (m["player_color"] or "white").lower()
                if c in color_records:
                    color_records[c]["cp_sum"] += float(cp)
                    color_records[c]["moves"] += 1

            if m["ply_number"] in (1, 2) and m["move_san"]:
                opening_moves_sample.append(m["move_san"])

        global_acpl = round(total_cp_loss / evaluated_moves_count, 1) if evaluated_moves_count > 0 else 45.0
        blunder_rate = round((mq_counts["blunder"] / max(1, evaluated_moves_count)) * 100.0, 1)

        # 4. History Progression (last N games)
        progression: List[GameHistoryPoint] = []
        recent_games = games[:limit]
        for g in reversed(recent_games):
            g_id = g["id"]
            async with db.execute(
                """
                SELECT AVG(centipawn_loss) as acpl,
                       SUM(CASE WHEN quality_label = 'blunder' THEN 1 ELSE 0 END) as blunders
                FROM moves WHERE game_id = ?
                """,
                (g_id,),
            ) as m_cur:
                row = await m_cur.fetchone()
                g_acpl = round(float(row["acpl"] or 45.0), 1) if row else 45.0
                g_blunders = int(row["blunders"] or 0) if row else 0

            date_str = (g["started_at"] or "")[:10] or "Recent"
            progression.append(
                GameHistoryPoint(
                    game_id=g_id,
                    date=date_str,
                    result=g["result"] or "*",
                    player_color=g["player_color"] or "white",
                    acpl=g_acpl,
                    blunders=g_blunders,
                    skill_level=g["engine_skill_level"] or 10,
                )
            )

        # 5. Openings Repertoire from Knowledge Base
        rag = get_rag_knowledge_base()
        repertoire_map: Dict[str, Dict[str, Any]] = {}
        for op in rag.openings[:6]:
            repertoire_map[op["name"]] = {
                "eco": op.get("eco", "A00"),
                "name": op["name"],
                "games": 0,
                "wins": 0,
                "cp_sum": 0.0,
                "cp_moves": 0,
            }

        # For each game, identify opening and calculate distinct game performance
        for g in games:
            g_id = g["id"]
            async with db.execute(
                """
                SELECT move_san, ply_number, centipawn_loss
                FROM moves
                WHERE game_id = ?
                ORDER BY ply_number ASC
                """,
                (g_id,),
            ) as m_cur:
                g_moves = await m_cur.fetchall()

            if not g_moves:
                continue

            matched_name = None
            for mv in g_moves[:2]:
                if mv["move_san"]:
                    matched = rag.match_opening(mv["move_san"], ply=mv["ply_number"])
                    if matched and matched["name"] in repertoire_map:
                        matched_name = matched["name"]
                        break

            if matched_name:
                repertoire_map[matched_name]["games"] += 1
                p_col = (g["player_color"] or "white").lower()
                res = g["result"]
                is_win = (p_col == "white" and res == "1-0") or (p_col == "black" and res == "0-1")
                if is_win:
                    repertoire_map[matched_name]["wins"] += 1

                for mv in g_moves:
                    if mv["centipawn_loss"] is not None:
                        repertoire_map[matched_name]["cp_sum"] += float(mv["centipawn_loss"])
                        repertoire_map[matched_name]["cp_moves"] += 1

        openings_list: List[OpeningStats] = []
        for name, data in repertoire_map.items():
            g_count = data["games"]
            w_pct = round((data["wins"] / g_count) * 100.0, 1) if g_count > 0 else 0.0
            avg_cp = round(data["cp_sum"] / max(1, data["cp_moves"]), 1) if data["cp_moves"] > 0 else 40.0
            openings_list.append(
                OpeningStats(
                    eco=data["eco"],
                    name=name,
                    games=g_count,
                    win_rate_pct=w_pct,
                    avg_cp_loss=avg_cp,
                )
            )

        # 6. Color Asymmetry
        color_asymmetry: Dict[str, ColorStats] = {}
        for c in ("white", "black"):
            g_c = color_records[c]["games"]
            w_c = color_records[c]["wins"]
            m_c = color_records[c]["moves"]
            w_pct_c = round((w_c / g_c) * 100.0, 1) if g_c > 0 else 50.0
            acpl_c = round(color_records[c]["cp_sum"] / m_c, 1) if m_c > 0 else 40.0
            color_asymmetry[c] = ColorStats(
                games=g_c,
                win_rate_pct=w_pct_c,
                avg_cp_loss=acpl_c,
            )

        return PlayerAnalyticsResponse(
            player_id=player_id,
            summary=PlayerSummaryKPI(
                games_played=total_games,
                wins=wins,
                draws=draws,
                losses=losses,
                win_rate_pct=win_rate,
                current_skill_estimate=skill_estimate,
                avg_centipawn_loss=global_acpl,
                blunder_rate_pct=blunder_rate,
            ),
            move_quality_distribution=MoveQualityDistribution(**mq_counts),
            history_progression=progression,
            openings_repertoire=openings_list,
            color_asymmetry=color_asymmetry,
        )

    finally:
        await db.close()

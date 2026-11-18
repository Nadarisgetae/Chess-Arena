"""
test_analytics_routes.py — Unit tests for the Analytics API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import init_db, get_db


@pytest.mark.anyio
async def test_get_player_analytics_empty():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/analytics/player/test-nonexistent-player")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == "test-nonexistent-player"
        assert "summary" in data
        assert data["summary"]["games_played"] == 0
        assert "move_quality_distribution" in data
        assert "history_progression" in data
        assert "openings_repertoire" in data
        assert "color_asymmetry" in data


@pytest.mark.anyio
async def test_get_player_analytics_with_games():
    await init_db()
    # Insert a dummy finished game and moves
    db = await get_db()
    try:
        player_id = "test-analytics-player"
        game_id = "test-analytics-game-1"

        await db.execute(
            """INSERT OR REPLACE INTO games (id, player_id, mode, result, engine_skill_level, player_color)
               VALUES (?, ?, 'play', '1-0', 10, 'white')""",
            (game_id, player_id),
        )
        await db.execute(
            """INSERT OR REPLACE INTO moves
               (id, game_id, ply_number, move_san, move_uci, quality_label, centipawn_loss)
               VALUES
               ('m1', ?, 1, 'e4', 'e2e4', 'best', 5.0),
               ('m2', ?, 2, 'e5', 'e7e5', 'good', 12.0),
               ('m3', ?, 3, 'Nf3', 'g1f3', 'inaccuracy', 28.0)""",
            (game_id, game_id, game_id),
        )
        await db.commit()
    finally:
        await db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/analytics/player/{player_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == player_id
        assert data["summary"]["games_played"] >= 1
        assert data["summary"]["wins"] >= 1
        assert data["move_quality_distribution"]["best"] >= 1
        assert len(data["history_progression"]) >= 1

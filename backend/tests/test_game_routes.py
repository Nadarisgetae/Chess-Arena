"""
test_game_routes.py — Integration tests for Game lifecycle endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import init_db


@pytest.fixture(autouse=True)
def mock_engine(monkeypatch):
    """Mocks Stockfish calls for machines without binary installed."""
    async def mock_best_move(fen=None, *args, **kwargs):
        is_white = True
        if fen and " b " in fen:
            is_white = False
        return {
            "best_move_uci": "e2e4" if is_white else "e7e5",
            "best_move_san": "e4" if is_white else "e5",
            "depth": 10,
            "skill_level": 10,
        }

    async def mock_analyse(*args, **kwargs):
        return {
            "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "move_uci": "e2e4",
            "move_san": "e4",
            "quality_label": "best",
            "win_pct_before": 50.0,
            "win_pct_after": 52.0,
            "win_pct_loss": 0.0,
            "centipawn_loss": 0.0,
            "best_move_uci": "e2e4",
            "best_move_san": "e4",
            "best_line": ["e2e4", "e7e5"],
            "best_line_san": ["e4", "e5"],
            "alternatives": [],
            "coach_summary": "Best move.",
            "is_capture": False,
            "gives_check": False,
            "is_checkmate": False,
            "is_stalemate": False,
            "is_draw": False,
            "is_castle": False,
            "is_promotion": False,
            "promotion_piece": None,
            "allows_forced_mate": False,
            "depth": 10,
            "time_limit": 0.1,
            "engine": "Stockfish Mock",
        }

    monkeypatch.setattr("backend.routes.game.get_best_move", mock_best_move)
    monkeypatch.setattr("backend.routes.game.analyse_played_move", mock_analyse)


@pytest.mark.anyio
async def test_create_new_game_player_white():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "player_id": "test-player-white",
            "player_color": "white",
            "skill_level": 10,
        }
        res = await client.post("/api/game/new", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "game_id" in data
        assert data["player_color"] == "white"
        assert data["engine_move"] is None


@pytest.mark.anyio
async def test_create_new_game_auto_difficulty():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "player_id": "guest",
            "player_color": "white",
            "skill_level": "auto",
        }
        res = await client.post("/api/game/new", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "game_id" in data
        assert 0 <= data["skill_level"] <= 20


@pytest.mark.anyio
async def test_create_new_game_player_black():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "player_id": "test-player-black",
            "player_color": "black",
            "skill_level": "auto",
        }
        res = await client.post("/api/game/new", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "game_id" in data
        assert data["player_color"] == "black"
        assert data["engine_move"] is not None
        assert data["engine_move_san"] is not None


@pytest.mark.anyio
async def test_make_move_legal():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. New game
        new_res = await client.post("/api/game/new", json={"player_id": "test-mover", "player_color": "white"})
        game_id = new_res.json()["game_id"]

        # 2. Player plays 1. e4
        move_res = await client.post(f"/api/game/{game_id}/move", json={"move_uci": "e2e4"})
        assert move_res.status_code == 200
        data = move_res.json()
        assert data["player_move_san"] == "e4"
        assert data["engine_move_uci"] == "e7e5"


@pytest.mark.anyio
async def test_resign_game():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        new_res = await client.post("/api/game/new", json={"player_id": "test-resigner", "player_color": "white"})
        game_id = new_res.json()["game_id"]

        resign_res = await client.post(f"/api/game/{game_id}/resign", json={"player_id": "test-resigner"})
        assert resign_res.status_code == 200
        data = resign_res.json()
        assert data["result"] == "0-1"
        assert "game_id" in data

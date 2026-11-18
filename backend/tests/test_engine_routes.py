"""
test_engine_routes.py — Unit tests for Engine UCI endpoints and Prometheus telemetry.
"""

import pytest
from httpx import AsyncClient, ASGITransport
import chess
from backend.main import app
from backend.database import init_db


@pytest.fixture(autouse=True)
def mock_engine_helpers(monkeypatch):
    async def mock_best(fen=chess.STARTING_FEN, *args, **kwargs):
        return {
            "fen": fen,
            "best_move_uci": "e7e5",
            "best_move_san": "e5",
            "ponder": "g1f3",
            "centipawns": 20,
            "mate_in": None,
            "win_pct": 50.0,
            "depth": 10,
        }

    async def mock_eval(fen=chess.STARTING_FEN, *args, **kwargs):
        return {
            "fen": fen,
            "centipawns": 20,
            "mate_in": None,
            "win_pct": 52.0,
            "depth": 10,
        }

    monkeypatch.setattr("backend.routes.engine.get_best_move", mock_best)
    monkeypatch.setattr("backend.routes.engine.get_eval", mock_eval)


@pytest.mark.anyio
async def test_engine_bestmove_endpoint():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/engine/bestmove?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201")
        assert res.status_code == 200
        data = res.json()
        assert data["best_move_uci"] == "e7e5"
        assert data["best_move_san"] == "e5"


@pytest.mark.anyio
async def test_engine_evaluate_endpoint():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/engine/eval?fen=rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR%20w%20KQkq%20-%200%201")
        assert res.status_code == 200
        data = res.json()
        assert data["centipawns"] == 20
        assert data["win_pct"] == 52.0


@pytest.mark.anyio
async def test_prometheus_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/metrics")
        assert res.status_code == 200
        content = res.text
        assert "chess_arena_uptime_seconds" in content
        assert "chess_arena_stockfish_eval_calls_total" in content
        assert "chess_arena_llm_cache_hits_total" in content

"""
main.py — FastAPI application entry point for Chess Arena.

Run locally:
    cd chess-arena
    uvicorn backend.main:app --reload --port 8000

API docs available at: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.database import init_db
from backend.routes.engine import router as engine_router
from backend.routes.game import router as game_router
from backend.routes.coach import router as coach_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Chess Arena API",
    description=(
        "Adaptive Chess AI platform — Play Mode, Coach Mode, Vision Mode.\n\n"
        "Phase 2: Deterministic Coach Engine — win-probability move classification, "
        "best-move analysis, and coaching summaries powered entirely by Stockfish."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Allow the frontend (served from file:// or a local dev server) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ─────────────────────────────────────────────────────────────────
app.include_router(engine_router, prefix="/api")
app.include_router(game_router, prefix="/api")
app.include_router(coach_router, prefix="/api")


# ── Static Frontend ────────────────────────────────────────────────────────────
_frontend = Path(__file__).parent.parent / "frontend"
if _frontend.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_frontend / "index.html"))


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "service": "chess-arena", "version": "0.1.0"}

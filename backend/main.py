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
from fastapi.responses import FileResponse, PlainTextResponse
from pathlib import Path

from backend.database import init_db
from backend.metrics import record_request, generate_prometheus_metrics
from backend.routes.engine import router as engine_router
from backend.routes.game import router as game_router
from backend.routes.coach import router as coach_router
from backend.routes.vision import router as vision_router
from backend.routes.analytics import router as analytics_router


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

# ── Telemetry Middleware ───────────────────────────────────────────────────────
@app.middleware("http")
async def prometheus_metrics_middleware(request, call_next):
    response = await call_next(request)
    endpoint = request.url.path
    if endpoint not in ("/metrics", "/health"):
        record_request(endpoint, request.method, response.status_code)
    return response

# ── API Routes ─────────────────────────────────────────────────────────────────
app.include_router(engine_router, prefix="/api")
app.include_router(game_router, prefix="/api")
app.include_router(coach_router, prefix="/api")
app.include_router(vision_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")


# ── Static Frontend ────────────────────────────────────────────────────────────
_frontend = Path(__file__).parent.parent / "frontend"
if _frontend.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_frontend / "index.html"))


# ── Health & Metrics ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "service": "chess-arena", "version": "0.2.0"}

@app.get("/metrics", response_class=PlainTextResponse, tags=["Monitoring"])
async def metrics():
    return generate_prometheus_metrics()

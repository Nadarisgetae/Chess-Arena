"""
database.py — SQLite async setup via aiosqlite.
Creates tables on startup; provides a reusable connection context.
Applies idempotent column migrations for schema evolution.
"""

import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent / "chess_arena.db"


CREATE_PLAYERS = """
CREATE TABLE IF NOT EXISTS players (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

CREATE_PLAYER_PROFILE = """
CREATE TABLE IF NOT EXISTS player_profile (
    player_id           TEXT PRIMARY KEY REFERENCES players(id),
    skill_estimate      REAL DEFAULT 1000,
    avg_centipawn_loss  REAL,
    blunder_rate        REAL,
    games_played        INTEGER DEFAULT 0,
    preferred_eco       TEXT,
    time_variance       REAL,
    endgame_conversion  REAL,
    updated_at          TEXT DEFAULT (datetime('now'))
);
"""

CREATE_GAMES = """
CREATE TABLE IF NOT EXISTS games (
    id                  TEXT PRIMARY KEY,
    player_id           TEXT REFERENCES players(id),
    mode                TEXT CHECK(mode IN ('play', 'coach', 'vision')) DEFAULT 'play',
    pgn                 TEXT,
    result              TEXT,
    engine_skill_level  INTEGER DEFAULT 10,
    started_at          TEXT DEFAULT (datetime('now')),
    ended_at            TEXT
);
"""

CREATE_MOVES = """
CREATE TABLE IF NOT EXISTS moves (
    id              TEXT PRIMARY KEY,
    game_id         TEXT REFERENCES games(id),
    ply_number      INTEGER,
    move_san        TEXT,
    move_uci        TEXT,
    fen_before      TEXT,
    fen_after       TEXT,
    eval_before     REAL,
    eval_after      REAL,
    quality_label   TEXT,
    is_mate_line    INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

CREATE_LLM_CACHE = """
CREATE TABLE IF NOT EXISTS llm_cache (
    fen TEXT,
    move_san TEXT,
    explanation TEXT,
    model_used TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now')),
    PRIMARY KEY (fen, move_san)
);
"""

# ── Coach & Player Model columns added in Phase 2 ──────────────────────────────
# Use an ordered dict so migrations are applied in a predictable order.
# Values are the SQL type + default clause.
ADDITIONAL_PLAYER_PROFILE_COLUMNS: dict[str, str] = {
    "preferred_eco": "TEXT",
    "time_variance": "REAL",
    "endgame_conversion": "REAL",
}

# ── Coach columns added in Phase 2 ─────────────────────────────────────────────
# Use an ordered dict so migrations are applied in a predictable order.
# Values are the SQL type + default clause.
ADDITIONAL_MOVE_COLUMNS: dict[str, str] = {
    "win_pct_before":   "REAL",
    "win_pct_after":    "REAL",
    "win_pct_loss":     "REAL",
    "centipawn_loss":   "REAL",
    "best_move_san":    "TEXT",
    "best_line":        "TEXT",   # JSON array of UCI strings
    "coach_summary":    "TEXT",
    "analysis_json":    "TEXT",   # full structured report JSON
    "engine_depth":     "INTEGER",
    "engine_time_limit": "REAL",
    "engine_version":   "TEXT",
    "is_best_move":     "INTEGER DEFAULT 0",
    "is_check":         "INTEGER DEFAULT 0",
    "is_capture":       "INTEGER DEFAULT 0",
    "is_mate":          "INTEGER DEFAULT 0",
    "is_castle":        "INTEGER DEFAULT 0",
    "is_promotion":     "INTEGER DEFAULT 0",
}


async def _get_table_columns(db: aiosqlite.Connection, table: str) -> set[str]:
    """Return the set of existing column names for `table`."""
    async with db.execute(f"PRAGMA table_info({table})") as cur:
        rows = await cur.fetchall()
    return {row[1] for row in rows}  # column name is index 1


async def _migrate_moves_table(db: aiosqlite.Connection) -> None:
    """
    Idempotently add coach columns to the moves table.
    Skips any column that already exists. Column name allowlist prevents
    SQL injection — user input must never reach this function.
    """
    existing = await _get_table_columns(db, "moves")
    for column_name, definition in ADDITIONAL_MOVE_COLUMNS.items():
        if column_name not in existing:
            await db.execute(
                f"ALTER TABLE moves ADD COLUMN {column_name} {definition}"
            )
    await db.commit()


async def _migrate_player_profile_table(db: aiosqlite.Connection) -> None:
    """Idempotently add new features to player_profile table."""
    existing = await _get_table_columns(db, "player_profile")
    for column_name, definition in ADDITIONAL_PLAYER_PROFILE_COLUMNS.items():
        if column_name not in existing:
            await db.execute(
                f"ALTER TABLE player_profile ADD COLUMN {column_name} {definition}"
            )
    await db.commit()


async def init_db() -> None:
    """Create all tables and apply pending column migrations."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_PLAYERS)
        await db.execute(CREATE_PLAYER_PROFILE)
        await db.execute(CREATE_GAMES)
        await db.execute(CREATE_MOVES)
        await db.execute(CREATE_LLM_CACHE)
        await db.commit()
        await _migrate_moves_table(db)
        await _migrate_player_profile_table(db)


async def get_db() -> aiosqlite.Connection:
    """Open and return a raw aiosqlite connection. Caller must close it."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn

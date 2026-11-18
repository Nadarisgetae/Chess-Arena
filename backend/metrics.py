"""
metrics.py — Prometheus-compatible metrics collector for Chess Arena.

Exposes standard Prometheus text format on GET /metrics for scraping.
Zero external dependencies required.
"""

import time
from typing import Dict, Tuple

START_TIME = time.time()

# Counters: (endpoint, method, status_code) -> count
REQUEST_COUNTERS: Dict[Tuple[str, str, int], int] = {}

# Engine timers: total seconds, total calls
STOCKFISH_EVAL_CALLS = 0
STOCKFISH_EVAL_TOTAL_SECONDS = 0.0

# Cache counters
CACHE_HITS = 0
CACHE_MISSES = 0


def record_request(endpoint: str, method: str, status_code: int) -> None:
    key = (endpoint, method, status_code)
    REQUEST_COUNTERS[key] = REQUEST_COUNTERS.get(key, 0) + 1


def record_stockfish_eval(duration_seconds: float) -> None:
    global STOCKFISH_EVAL_CALLS, STOCKFISH_EVAL_TOTAL_SECONDS
    STOCKFISH_EVAL_CALLS += 1
    STOCKFISH_EVAL_TOTAL_SECONDS += duration_seconds


def record_cache_hit(is_hit: bool) -> None:
    global CACHE_HITS, CACHE_MISSES
    if is_hit:
        CACHE_HITS += 1
    else:
        CACHE_MISSES += 1


def generate_prometheus_metrics() -> str:
    """Generates standard Prometheus text-format exposition (v0.0.4)."""
    lines = []

    # Uptime
    uptime = time.time() - START_TIME
    lines.append("# HELP chess_arena_uptime_seconds Total runtime of backend in seconds.")
    lines.append("# TYPE chess_arena_uptime_seconds gauge")
    lines.append(f"chess_arena_uptime_seconds {uptime:.1f}")

    # HTTP requests total
    lines.append("# HELP chess_arena_http_requests_total Total HTTP requests handled.")
    lines.append("# TYPE chess_arena_http_requests_total counter")
    if not REQUEST_COUNTERS:
        lines.append('chess_arena_http_requests_total{endpoint="total",method="ALL",status="200"} 0')
    else:
        for (ep, method, status), count in sorted(REQUEST_COUNTERS.items()):
            lines.append(f'chess_arena_http_requests_total{{endpoint="{ep}",method="{method}",status="{status}"}} {count}')

    # Stockfish metrics
    lines.append("# HELP chess_arena_stockfish_eval_calls_total Total Stockfish engine evaluations.")
    lines.append("# TYPE chess_arena_stockfish_eval_calls_total counter")
    lines.append(f"chess_arena_stockfish_eval_calls_total {STOCKFISH_EVAL_CALLS}")

    lines.append("# HELP chess_arena_stockfish_eval_seconds_total Total duration of Stockfish engine evaluations.")
    lines.append("# TYPE chess_arena_stockfish_eval_seconds_total counter")
    lines.append(f"chess_arena_stockfish_eval_seconds_total {STOCKFISH_EVAL_TOTAL_SECONDS:.3f}")

    # LLM Cache metrics
    lines.append("# HELP chess_arena_llm_cache_hits_total Total coach explanation cache hits.")
    lines.append("# TYPE chess_arena_llm_cache_hits_total counter")
    lines.append(f"chess_arena_llm_cache_hits_total {CACHE_HITS}")

    lines.append("# HELP chess_arena_llm_cache_misses_total Total coach explanation cache misses.")
    lines.append("# TYPE chess_arena_llm_cache_misses_total counter")
    lines.append(f"chess_arena_llm_cache_misses_total {CACHE_MISSES}")

    return "\n".join(lines) + "\n"

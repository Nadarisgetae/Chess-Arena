# Adaptive Chess AI — Full Masterplan (Zero-Budget Build)
### Play Mode + Coach Mode + Vision, powered entirely by free-tier infrastructure and OpenRouter's free LLM pool

---

## 0. What Changed From the Original Ideation

Every component that originally implied a paid service has been swapped for a free-tier or self-hosted equivalent. The single biggest cost risk in the original plan was the LLM layer (OpenAI/paid inference) — this is now solved with **OpenRouter's free model pool + a multi-key rotation system**, detailed fully in Section 5. Nothing else in the architecture requires a credit card.

| Original (paid-implying) | Replacement (free) |
|---|---|
| OpenAI GPT-4 | OpenRouter free models (rotated across multiple keys) |
| Pinecone (paid tiers) | Chroma / FAISS — local, free, no network dependency |
| AWS/GCP deployment | Render free web service / Fly.io free allowance / Railway free trial / Oracle Cloud Free Tier |
| Managed PostgreSQL | Supabase free tier / Neon free tier / local SQLite for MVP |
| Redis (paid tiers) | Upstash Redis free tier (10k commands/day) or in-memory dict for MVP |
| Prometheus + Grafana (hosted) | Self-hosted via Docker Compose (free) or Grafana Cloud free tier |
| GPU training instances | Google Colab free tier / Kaggle Notebooks free GPU (30 hrs/week) |
| MLflow hosted | Self-hosted MLflow (free, local SQLite backend) |
| Domain + SSL | Vercel/Render subdomains are free; custom domain optional later |

Nothing below assumes you will ever enter payment details anywhere. Every "free tier" mentioned has been chosen because it has a genuinely usable no-card-required (or card-required-but-$0-charged) free plan as of the plan's writing — you should still verify current limits before depending on them, since free tiers shift over time.

---

## 1. System Architecture (Revised for Free-Tier Deployment)

```
┌───────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Vercel/Netlify free)                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐         │
│   │  PLAY MODE   │  │ COACH MODE   │  │  VISION MODE      │        │
│   └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘        │
└──────────┼─────────────────┼───────────────────┼───────────────────┘
           │                 │                   │
           ▼                 ▼                   ▼
┌───────────────────────────────────────────────────────────────────┐
│         BACKEND — FastAPI + WebSocket (Render/Fly.io free tier)    │
└──────┬──────────────┬──────────────┬──────────────┬────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌───────────┐  ┌───────────┐  ┌────────────────┐  ┌───────────┐
│  PLAYER   │  │  ENGINE   │  │  COACH MODULE   │  │  VISION   │
│  MODEL    │  │  MODULE   │  │  (OpenRouter    │  │  MODULE   │
│(rule-based│  │(Stockfish │  │   free LLMs +   │  │ (ViT/CNN, │
│ → RL)     │  │  local)   │  │   key-rotator   │  │  HF free) │
└───────────┘  └───────────┘  └────────────────┘  └───────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌───────────────────────────────────────────────────────────────────┐
│   DATA LAYER — SQLite/Supabase-free (games+profiles) │             │
│   Chroma/FAISS local (vector/RAG) │ Upstash-free or in-mem (cache) │
└───────────────────────────────────────────────────────────────────┘
```

Everything below the frontend can run as a **single Docker Compose stack**, which is important because it means the whole thing can also run 100% locally on your own laptop for development and demo purposes with zero hosting cost at all, and only needs to go to a free-tier host when you want a public link.

---

## 2. Module-by-Module Detailed Plan

### 2.1 Engine Module (Stockfish) — Free, no changes needed
- Stockfish is open-source and free regardless of scale. Run it as a subprocess via `python-chess`'s `chess.engine.SimpleEngine`.
- Pin a specific Stockfish version binary (download from the official GitHub releases) into your Docker image so behavior is reproducible.
- Expose a thin wrapper service (`engine_service.py`) with functions: `get_best_moves(fen, depth, multipv)`, `get_eval(fen)`, `get_mate_in_n(fen)`. This isolates the only C++-adjacent dependency from the rest of the stack.
- For MCTS/alternative search experiments (optional, later phase), Leela Chess Zero (`lc0`) is also fully free and can run on CPU (slower) for demo purposes.

### 2.2 Play Mode — Adaptive Opponent
**Phase 1 (MVP, no ML): rule-based adaptive difficulty**
- Maintain a per-user `skill_estimate` (start at 1000 Elo-equivalent).
- After each game: if user won convincingly → increase Stockfish's `Skill Level`/depth/time limit for next game; if user lost badly → decrease. This alone satisfies "adaptive difficulty" for the MVP and needs zero ML infrastructure.
- Store this in a simple `player_profile` table (see schema in Section 6).

**Phase 2 (upgrade): lightweight statistical player model**
- Track features per game: opening ECO code played, average centipawn loss, blunder count, time-per-move variance, endgame conversion rate.
- Use a simple free, local library (`scikit-learn`, free/open-source) to fit a small classifier/regressor that maps these features to a "next-game difficulty" recommendation. No GPU, no paid compute needed — trains in seconds on your own history.

**Phase 3 (stretch, optional): RL-based difficulty controller**
- Use `Stable-Baselines3` (free, open-source) with a custom Gymnasium environment where the "action" is the engine's skill parameter and the "reward" is how close the game's outcome margin was to a target "flow-state" band (e.g., user wins 40–60% of games, no game decided too early).
- This can be trained entirely on synthetic/simulated games or on your own logged games — no paid infra required, but do this only after Phases 1–2 are working, per the roadmap in Section 7.

**Style Mimicker (stretch)**: skip for MVP — it needs a large annotated game corpus to be worth building and isn't necessary to demonstrate the core adaptive-difficulty idea. Mark it "future work" in your report rather than building it, to avoid scope creep.

### 2.3 Coach Mode — Real-Time Guidance
This is the module most affected by moving to OpenRouter. Full design in Section 4.

Components, all free:
- **Best move + eval**: from the Stockfish wrapper (Section 2.1) — no LLM needed for the numbers themselves.
- **Move quality classification** (Brilliant/Best/Good/Inaccuracy/Mistake/Blunder): pure rule-based thresholding on centipawn-loss delta before/after the move. No ML or LLM required — this is deterministic and free.
- **Win probability**: convert Stockfish centipawn eval to a win% using the standard logistic mapping `win% = 50 + 50 * (2/(1+exp(-0.00368*cp)) - 1)` (this is the same formula Lichess uses, publicly documented, free to reuse).
- **Mate-in-N**: Stockfish reports this natively when it finds a forced mate — just surface it.
- **Threat detection**: run Stockfish one ply deep on the opponent's reply to flag hanging pieces / tactical shots — free, deterministic.
- **Natural-language explanation + personalised advice**: this is the only part that needs an LLM → OpenRouter free models, described in Section 4.

### 2.4 Vision Mode — Board Recognition
- **Board detection**: OpenCV (`cv2.findContours`, `cv2.HoughLines`) — free, local, no GPU needed.
- **Piece classification**: instead of training a ViT from scratch (expensive), start with a free pretrained checkpoint. Search Hugging Face Hub for existing open chess-piece-classification models (several MIT/Apache-licensed ones exist from prior hackathon/research projects) and fine-tune on a small custom dataset using free Colab/Kaggle GPU hours — this collapses weeks of training into hours and costs nothing.
- **Synthetic data generation**: rather than a full GAN/VAE pipeline (heavy, slow to get right), an MVP-appropriate free approach is programmatic rendering — take free/open-license chess piece SVG sets (e.g., the Lichess/`cburnett` piece set, which is open-licensed) and composite them onto rendered boards with randomized lighting/rotation/noise using PIL/OpenCV. This gives you thousands of labeled training images for free without needing a generative model at all. Keep the VAE/GAN idea in the report as a documented "Phase 3 stretch" for course-outcome coverage, but don't block the MVP on it.
- **FEN reconstruction + validation**: `python-chess` (free) validates that the recognized position is legal and flags likely misreads.

### 2.5 Analytics Dashboard
- Frontend: React + `react-chessboard` (free, MIT-licensed) for the interactive board, or Streamlit for the fastest possible MVP (both free).
- Charting: `recharts` (free) or Streamlit's built-in charts.
- No paid dashboard/BI tool needed anywhere.

---

## 3. Free Hosting & Infrastructure Map

| Layer | Free option | Notes |
|---|---|---|
| Frontend hosting | Vercel (Hobby, free) or Netlify (free) | Auto-deploys from GitHub, generous free bandwidth |
| Backend hosting | Render (free web service tier) or Fly.io (free allowance) or Railway (free trial credits) | Free tiers sleep after inactivity — acceptable for a student/demo project |
| Database | Supabase (free Postgres tier) or Neon (free Postgres tier) or plain SQLite file for local/demo | Supabase also gives free auth if you want real accounts |
| Vector store (RAG) | Chroma (local, embedded, free) or FAISS (free, local) | No need for a hosted vector DB at your scale |
| Cache/session store | Upstash Redis (free tier, request-based) or an in-process dict for MVP | Only add Redis once you actually need multi-instance state |
| GPU compute for training | Google Colab (free tier) / Kaggle Notebooks (free ~30 GPU hrs/week) | Enough for ViT fine-tuning and small RL runs |
| CI/CD | GitHub Actions (free minutes for public/small private repos) | Lint, test, build Docker image on every push |
| Containerization | Docker + Docker Compose (free, open-source) | Run the whole stack locally identically to production |
| Monitoring | Self-hosted Prometheus + Grafana via Docker Compose (free) or Grafana Cloud free tier | Optional for MVP, add in Phase 3 for the "industry-grade" checklist |
| Experiment tracking | Self-hosted MLflow with local/SQLite backend (free) | No hosted MLflow needed |
| Auth | Supabase Auth (free tier) or simple JWT you issue yourself | Skip OAuth providers that require paid verification if not needed |
| Piece/board art assets | `cburnett` piece set + open chessboard textures (open-licensed, free) | Check license file, credit as required |

---

## 4. LLM Layer — OpenRouter Free Models

### 4.1 Why OpenRouter
OpenRouter exposes a single OpenAI-compatible `/chat/completions`-style endpoint that routes to many underlying model providers, and it maintains a set of models tagged with `:free` in their model ID that can be used at no cost, subject to per-key rate limits (both a per-minute and a per-day cap, and the exact numbers vary and are enforced server-side). Because this project needs the LLM only as a **thin natural-language wrapper around Stockfish's numeric output** (see Section 2.3), a free general-purpose instruction-tuned model is entirely sufficient — the plan does not depend on a frontier paid model.

### 4.2 Integration pattern
- Use the `openai` Python SDK (free/open-source) pointed at OpenRouter's base URL, since OpenRouter is OpenAI-API-compatible. This means the coach module's code is standard and portable — if you ever do add a paid key later, no code changes are needed, only a config change.
- Keep the LLM call stateless and narrow: pass it a structured JSON blob (eval, best line, move quality label, player's known weaknesses) and ask it to produce 2–4 sentences of coaching text. This keeps token usage — and therefore rate-limit pressure — low, which matters a lot on a free tier.
- Cache LLM responses keyed by `(fen, move_played)` so the same position is never explained twice for the same user — this alone can cut real LLM calls by more than half in a typical session, since users often revisit lines.

### 4.3 Multiple free models as a fallback chain, not just multiple keys
Beyond rotating API keys (Section 5), also rotate across **multiple different free-tagged models** on OpenRouter, since each model has its own independent free-tier quota. If one free model is rate-limited or temporarily unavailable, fall back to the next one in a configured priority list. Maintain this list in a config file rather than hardcoding it, since which models carry a `:free` tag on OpenRouter changes over time — check OpenRouter's models page for the current free list before finalizing your priority order, and re-check periodically during the build.

### 4.4 RAG knowledge base (unchanged, already free)
- Opening theory, tactical motifs, endgame rules, and the user's own game history are all embedded with a free local embedding model (e.g., a small open `sentence-transformers` model run locally on CPU — no API cost) and stored in Chroma/FAISS.
- Retrieval happens locally; only the final generation step touches OpenRouter, minimizing paid/rate-limited surface area.

---

## 5. API Key Rotation & Exhaustion Handling (Core New Requirement)

This is the piece that makes "using a free API for a real product" actually viable: a **key pool manager** that transparently rotates across several OpenRouter API keys (you can generate multiple free keys, e.g., one per throwaway/alt account or one per teammate who contributes a key) and across the fallback model list from Section 4.3, so a single key's rate limit or exhaustion never takes the coach feature down.

### 5.1 Design
- Maintain a pool of keys in an environment variable or a local `keys.json` file (never commit this file — add it to `.gitignore`).
- Each key gets tracked state: `last_used_at`, `consecutive_failures`, `cooldown_until`.
- On every call: pick the next "healthy" key (not currently in cooldown) round-robin style.
- On a `429` (rate limited) or `402`/quota-exhausted style response, or a timeout, put that key into cooldown (exponential backoff: 30s → 60s → 120s → up to a capped max like 15 min) and immediately retry the same request with the next key in the pool, up to a max retry count.
- If **all** keys are in cooldown, fall back to a cached/generic canned explanation ("Move quality: Inaccuracy — this loses material tactically; review the line with the engine.") built from the deterministic Stockfish data alone, so the app degrades gracefully instead of failing the request outright.
- Log every rotation event (key index used, reason for rotation) so you can see usage patterns and tune your key count.
- Persist cooldown/failure state to a small local file or Redis (if you're already using Upstash) so state survives a backend restart on the free hosting tier (which may restart your instance after inactivity).

### 5.2 Reference implementation (Python)

```python
# key_rotator.py
"""
Free-tier-friendly OpenRouter key/model rotation manager.
Rotates across multiple API keys AND multiple free models,
with exponential-backoff cooldowns and graceful degradation.
"""

import time
import json
import random
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from openai import OpenAI, RateLimitError, APIStatusError, APITimeoutError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("key_rotator")

STATE_FILE = Path("rotator_state.json")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Priority-ordered list of free-tagged models on OpenRouter.
# NOTE: verify current free-model IDs on OpenRouter's model list before
# relying on this — free-tier model availability changes over time.
FREE_MODEL_PRIORITY = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2-7b-instruct:free",
]

MAX_BACKOFF_SECONDS = 900  # 15 minutes cap
BASE_BACKOFF_SECONDS = 30
MAX_RETRIES_PER_REQUEST = 4


@dataclass
class KeyState:
    key: str
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    total_calls: int = 0
    total_failures: int = 0

    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    def register_success(self):
        self.consecutive_failures = 0
        self.cooldown_until = 0.0
        self.total_calls += 1

    def register_failure(self):
        self.consecutive_failures += 1
        self.total_calls += 1
        self.total_failures += 1
        backoff = min(
            BASE_BACKOFF_SECONDS * (2 ** (self.consecutive_failures - 1)),
            MAX_BACKOFF_SECONDS,
        )
        self.cooldown_until = time.time() + backoff
        logger.warning(
            "Key ...%s cooling down for %.0fs (failure #%d)",
            self.key[-4:], backoff, self.consecutive_failures,
        )


class KeyRotator:
    def __init__(self, keys: list[str], state_file: Path = STATE_FILE):
        if not keys:
            raise ValueError("No OpenRouter API keys configured.")
        self.state_file = state_file
        self.keys: dict[str, KeyState] = {k: KeyState(key=k) for k in keys}
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                for k, saved in data.items():
                    if k in self.keys:
                        self.keys[k].cooldown_until = saved.get("cooldown_until", 0.0)
                        self.keys[k].consecutive_failures = saved.get("consecutive_failures", 0)
            except Exception:
                logger.exception("Failed to load rotator state, starting fresh.")

    def _save_state(self):
        data = {
            k: {
                "cooldown_until": s.cooldown_until,
                "consecutive_failures": s.consecutive_failures,
                "total_calls": s.total_calls,
                "total_failures": s.total_failures,
            }
            for k, s in self.keys.items()
        }
        self.state_file.write_text(json.dumps(data, indent=2))

    def _available_keys(self) -> list[KeyState]:
        return [s for s in self.keys.values() if s.is_available()]

    def get_next_key(self) -> Optional[KeyState]:
        available = self._available_keys()
        if not available:
            return None
        # Prefer the key with the fewest recent failures; break ties randomly
        # to spread load evenly across a healthy pool.
        available.sort(key=lambda s: s.consecutive_failures)
        best_failure_count = available[0].consecutive_failures
        candidates = [s for s in available if s.consecutive_failures == best_failure_count]
        return random.choice(candidates)

    def call_llm(self, messages: list[dict], max_tokens: int = 300) -> Optional[str]:
        """
        Attempts the chat completion across the key pool and the free-model
        fallback chain. Returns the response text, or None if every
        combination is exhausted (caller should fall back to a canned
        deterministic explanation in that case).
        """
        attempts = 0
        for model in FREE_MODEL_PRIORITY:
            for _ in range(len(self.keys)):
                if attempts >= MAX_RETRIES_PER_REQUEST:
                    logger.error("Max retries reached across keys/models.")
                    self._save_state()
                    return None

                key_state = self.get_next_key()
                if key_state is None:
                    logger.error("All keys currently in cooldown.")
                    break  # try next model in priority list, if any keys free up sooner there

                client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key_state.key)
                try:
                    attempts += 1
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        timeout=20,
                    )
                    key_state.register_success()
                    self._save_state()
                    return response.choices[0].message.content

                except RateLimitError:
                    logger.warning("Rate limited on key ...%s / model %s", key_state.key[-4:], model)
                    key_state.register_failure()

                except APIStatusError as e:
                    # Treat 402 (quota exhausted) and 5xx similarly: cool down and rotate.
                    logger.warning("API status error %s on key ...%s / model %s",
                                   getattr(e, "status_code", "?"), key_state.key[-4:], model)
                    key_state.register_failure()

                except APITimeoutError:
                    logger.warning("Timeout on key ...%s / model %s", key_state.key[-4:], model)
                    key_state.register_failure()

                except Exception:
                    logger.exception("Unexpected error calling OpenRouter")
                    key_state.register_failure()

        self._save_state()
        return None


def load_keys_from_env_or_file() -> list[str]:
    import os
    env_keys = os.environ.get("OPENROUTER_API_KEYS", "")
    if env_keys:
        return [k.strip() for k in env_keys.split(",") if k.strip()]
    keys_file = Path("keys.json")
    if keys_file.exists():
        return json.loads(keys_file.read_text())["keys"]
    raise RuntimeError(
        "No keys found. Set OPENROUTER_API_KEYS='key1,key2,key3' or create keys.json "
        '{"keys": ["key1", "key2"]}'
    )


if __name__ == "__main__":
    rotator = KeyRotator(load_keys_from_env_or_file())
    coaching_prompt = [
        {"role": "system", "content": "You are a concise, encouraging chess coach."},
        {"role": "user", "content": "Position eval: -1.8 after 12...Nxe4. Explain the mistake in 2 sentences."},
    ]
    result = rotator.call_llm(coaching_prompt)
    if result:
        print(result)
    else:
        print("[Fallback] Move quality: Mistake — this loses material tactically.")
```

### 5.3 Practical notes on the free-tier key pool
- Each OpenRouter account can generate its own key; a small team (you + 2 co-founders, per your usual project pattern) can each contribute a free key to the pool, multiplying effective free throughput without anyone paying anything.
- Keep the pool size configurable (`OPENROUTER_API_KEYS` env var, comma-separated) so you can add/remove keys without redeploying code.
- Because free-tier rate limits and the exact set of `:free`-tagged models can change, treat `FREE_MODEL_PRIORITY` and the key count as things to review periodically rather than "set and forget."
- Document this rotation system explicitly in your final report/demo — it's a genuinely good engineering talking point ("designed a resilient multi-provider fallback layer to guarantee uptime on a zero-cost inference budget") and maps directly to the "Explainability/Responsible AI" and "system reliability" course/industry angles already in the original plan.

---

## 6. Data Schema (Free Postgres/SQLite — unchanged in spirit, refined)

```sql
-- players
CREATE TABLE players (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- player_profile: adaptive-difficulty state (Section 2.2)
CREATE TABLE player_profile (
    player_id UUID REFERENCES players(id),
    skill_estimate FLOAT DEFAULT 1000,
    avg_centipawn_loss FLOAT,
    blunder_rate FLOAT,
    preferred_openings TEXT[],   -- ECO codes
    updated_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (player_id)
);

-- games
CREATE TABLE games (
    id UUID PRIMARY KEY,
    player_id UUID REFERENCES players(id),
    mode TEXT CHECK (mode IN ('play', 'coach', 'vision')),
    pgn TEXT,
    result TEXT,
    engine_skill_level INT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);

-- moves
CREATE TABLE moves (
    id UUID PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    ply_number INT,
    move_san TEXT,
    fen_before TEXT,
    fen_after TEXT,
    eval_before FLOAT,
    eval_after FLOAT,
    quality_label TEXT,   -- Brilliant/Best/Good/Inaccuracy/Mistake/Blunder
    llm_explanation TEXT, -- cached OpenRouter output, keyed for reuse
    is_mate_line BOOLEAN DEFAULT FALSE
);

-- llm_cache: dedupes coach explanations across users/sessions
CREATE TABLE llm_cache (
    fen TEXT,
    move_san TEXT,
    explanation TEXT,
    model_used TEXT,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (fen, move_san)
);
```

---

## 7. Revised Roadmap (8 Weeks, Zero-Budget Track)

| Week | Milestone | Cost |
|---|---|---|
| 1 | Stockfish integration, board UI, legal move handling, Docker Compose skeleton | $0 |
| 2 | Coach Mode v1: best move, eval bar, deterministic move-quality rating, win% | $0 |
| 3 | Mate-in-N, threat detection; set up OpenRouter account(s) + key pool + rotator script (Section 5) | $0 |
| 4 | LLM coaching text wired through the rotator; RAG with local Chroma + local embeddings; response caching | $0 |
| 5 | Player profiler (rule-based Phase 1 from Section 2.2) + difficulty controller | $0 |
| 6 | Vision module: board detection (OpenCV) + fine-tune pretrained piece classifier on Colab free GPU | $0 |
| 7 | Unified app, analytics dashboard, deploy to Render/Vercel free tiers | $0 |
| 8 | Testing (pytest), GitHub Actions CI, self-hosted Prometheus/Grafana via Docker Compose, docs, demo video | $0 |

Stretch (post-week-8, optional): RL-based difficulty controller (Section 2.2 Phase 3), style mimicker, synthetic-data GAN/VAE pipeline for vision — keep these explicitly labeled "future work" in your report so scope stays controlled during the core 8 weeks.

---

## 8. Updated Risk Register

| Risk | Mitigation |
|---|---|
| LLM hallucinations about chess | Always ground the LLM prompt in Stockfish's numeric output; never let it invent evals or lines itself |
| **A free OpenRouter key gets rate-limited or exhausted mid-demo** | Key + model rotation system (Section 5) with graceful fallback to deterministic canned explanations |
| Free model quality is inconsistent across providers | Fallback priority list ordered by observed quality; cache good responses so a flaky model's bad output isn't repeated |
| Free hosting tier "sleeps" the backend after inactivity | Acceptable for a student/portfolio project; document a manual "wake" step for live demos, or add a free uptime-pinger (e.g., a scheduled free GitHub Actions cron hitting a health endpoint) |
| Vision accuracy on varied physical boards | Programmatic synthetic-data augmentation (Section 2.4) before investing in a full GAN/VAE pipeline |
| Scope creep | Strict phase gating per the Week 1–8 roadmap; RL and style-mimicry explicitly deferred |
| Free-tier limits change over time (OpenRouter free-model list, Colab GPU hours, etc.) | Treat all free-tier specifics as "verify before relying on," not hardcoded assumptions — re-check periodically during the build |

---

## 9a. Supporting Research Papers (For Report Citations / Literature Review)

These are real, published papers that map directly onto specific modules above — useful for your literature review section and to justify design choices.

**Play Mode — adaptive difficulty / player modeling**
- Silver, D. et al. (2018). *A general reinforcement learning algorithm that masters chess, shogi, and Go through self-play* — Science 362(6419), 1140–1144 (also arXiv:1712.01815, "Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm"). The foundational self-play/MCTS-plus-neural-network paper (AlphaZero) — it demonstrates that a general-purpose reinforcement learning algorithm, given no domain knowledge except the rules, can reach superhuman chess performance from random play within 24 hours. Cite this for the Engine/Play-Mode search-and-learning background, even though your project uses Stockfish rather than retraining AlphaZero.
- McIlroy-Young, R., Sen, S., Kleinberg, J., Anderson, A. (2020). *Aligning Superhuman AI with Human Behavior: Chess as a Model System* (arXiv:2006.01855) — introduces **Maia**, a neural chess engine trained to predict human moves rather than optimal moves; directly relevant to your player-profiling and "keep the user in a flow state" difficulty design, since it replaces AlphaZero's self-play training with training on human games and removes tree search because it degrades human-move-prediction accuracy.
- Tang, Z. et al. (2024). *Maia-2: A Unified Model for Human-AI Alignment in Chess* — NeurIPS 2024. Follow-up unifying skill-level-conditioned human-like play into one model; good citation for "why we track a per-user skill estimate" in Section 2.2.
- A Behavior-Based Knowledge Representation Improves Prediction of Players' Moves in Chess by 25% (arXiv:2504.05425) — a 2025 paper that benchmarks against Maia and improves human-move prediction with an explicit cognitive/behavior model; useful for discussing possible upgrades to your Phase-2 statistical player model.
- General DDA (Dynamic Difficulty Adjustment) background, useful for framing Play Mode as an instance of a broader, well-studied problem:
  - "Personalized Dynamic Difficulty Adjustment — Imitation Learning Meets Reinforcement Learning" (arXiv:2408.06818) — combines imitation learning with RL to train a personalized opponent quickly, addressing the "DRL converges too slowly for real-time use" problem, which is directly relevant if you attempt the Phase-3 RL stretch goal.
  - "Continuous Reinforcement Learning-based Dynamic Difficulty Adjustment in a Visual Working Memory Game" (arXiv:2308.12726) — a clean, well-evaluated example of RL-based DDA with a human user study, good methodology template for evaluating your own difficulty controller.
  - "Investigating Reinforcement Learning for Dynamic Difficulty Adjustment" (ACM SBGames 2023, dl.acm.org/doi/10.1145/3631085.3631229) — proposes a reward function that keeps a player's relative skill similar to their opponent's while penalizing the agent's win rate to avoid the AI being too strong or too weak, essentially the exact mechanism you'd implement for the RL stretch goal in Section 2.2.

**Coach Mode — explanation, commentary, and LLM-chess research**
- Jhamtani, H., Gangal, V., Hovy, E., Neubig, G., Berg-Kirkpatrick, T. (2018). *Learning to Generate Move-by-Move Commentary for Chess Games from Large-Scale Social Forum Data* (ACL 2018, aclanthology.org/P18-1154). Introduces a large-scale chess commentary dataset of over 298,000 move-commentary pairs across 11,000 games and a neural model that generates commentary conditioned on multiple pragmatic aspects of the game state. This is the closest prior academic work to your "natural-language move explanation" feature — cite it directly and consider using its dataset as extra RAG/fine-tuning material later.
- Kuo, M-T., Hsueh, C-C., Tsai, R. T-H. (2023). *Large Language Models on the Chessboard: A Study on ChatGPT's Formal Language Comprehension and Complex Reasoning Skills* (arXiv:2308.15118). Evaluates an LLM's actual chess understanding and legality/quality of its move choices — good citation for **why your design deliberately does not let the LLM choose moves or evaluate positions itself**, and instead only asks it to narrate Stockfish's numeric output (Section 2.3/4.2).
- Zhang, Y. et al. *Complete Chess Games Enable LLM Become A Chess Master* (ChessLLM) — trains an LLM on complete game sequences at scale; useful contrast case if you want to discuss why fine-tuning an LLM to play chess directly is a much heavier alternative to your Stockfish-plus-thin-LLM-wrapper design.
- Lewis, P. et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* — NeurIPS 2020 (arXiv:2005.11401). The foundational RAG paper — combines a pre-trained parametric generator with a non-parametric dense-vector retrieval index and shows RAG models generate more specific, diverse, and factual language than parametric-only baselines. Cite this directly for the RAG design in Section 4.4 (your local Chroma/FAISS index over opening theory, tactics, and the user's own games plays the same architectural role as RAG's Wikipedia index).

**Vision Mode — board and piece recognition**
- Abeykoon, L., Patel, V., Senthilvelan, G., Kasundra, D. (2025). *CVChess: A Deep Learning Framework for Converting Chessboard Images to Forsyth-Edwards Notation* (arXiv:2511.11522). Directly matches your Vision Mode pipeline: a residual CNN processes RGB smartphone images through Hough Line Transform edge detection, a projective transform for top-down alignment, segmentation into 64 squares, and 13-class piece classification, trained on the ChessReD dataset of 10,800 annotated smartphone images. The **ChessReD dataset** it uses is worth locating directly — it would save you from having to build your own physical-board dataset from scratch.
- Shan, A., Ju, B. (Stanford CS231n project). *Chessboard Understanding with Convolutional Learning for Object Recognition and Detection.* Proposes a three-part pipeline — a board detector, a per-square occupancy detector, and a piece classifier — trained independently and evaluated on a Blender-generated synthetic dataset of nearly 5,000 game states using ResNet and InceptionV3 backbones. Directly supports the "programmatic synthetic data instead of a full GAN/VAE" shortcut recommended in Section 2.4 — this paper proves synthetic-render training data works well for this exact task.
- Stojanovic et al. (2017), cited inside the CVChess paper, and Chess-CV (Rizo-Ramirez, 2021): earlier CNN/classical-CV approaches worth a one-line mention in a literature review for historical context — Stojanovic et al.'s approach detects the board via straight-line and intersection detection then classifies pieces by color/shape/height descriptors, reaching 95% piece-detection accuracy.
- Informatica journal (2024/25). *Predicting Forsyth-Edwards Notation with Chess Images: An Advanced Analysis Using Convolutional Neural Networks.* Another recent CNN-plus-EDA/PCA approach to the same FEN-prediction task — useful as a second data point for your related-work comparison table.

**How to use these in your report**: group them under three literature-review subsections mirroring Sections 2.2 (Play), 2.3 (Coach), 2.4 (Vision) of this plan, and explicitly state where your design follows prior work (Stockfish-grounded LLM narration, CNN-based FEN pipeline) versus where you've deliberately simplified it for a zero-budget/time-boxed student project (rule-based difficulty instead of full RL, synthetic-render data instead of GAN/VAE).

---

## 9. What to Build First (If You Want One Concrete Next Action)

1. Stand up the Docker Compose skeleton (FastAPI + Postgres/SQLite + Stockfish binary).
2. Get the deterministic Coach Mode pipeline (eval, move quality, win%, mate-in-N) fully working with **no LLM at all** — this alone is a demoable feature.
3. Only then wire in `key_rotator.py` and the OpenRouter call for natural-language explanations, since it's the one component with genuine external-service risk and benefits most from being isolated and tested last.

This ordering means that even if OpenRouter's free tier becomes unusable for any reason during your build window, 90% of the product (engine analysis, adaptive difficulty, vision) still stands on its own.

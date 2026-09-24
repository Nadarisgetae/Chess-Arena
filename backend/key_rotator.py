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
    return []

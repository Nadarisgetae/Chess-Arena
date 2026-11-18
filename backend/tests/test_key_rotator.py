"""
test_key_rotator.py — Unit tests for OpenRouter KeyRotator, backoff, and model fallback.
"""

import time
import pytest
from pathlib import Path
from backend.key_rotator import KeyState, KeyRotator


def test_key_state_lifecycle():
    ks = KeyState(key="test-key-1234")
    assert ks.is_available() is True
    assert ks.consecutive_failures == 0

    # Failure registers backoff
    ks.register_failure()
    assert ks.consecutive_failures == 1
    assert ks.cooldown_until > time.time()
    assert ks.is_available() is False

    # Second failure doubles backoff (exponential: 30s -> 60s)
    old_cooldown = ks.cooldown_until
    ks.register_failure()
    assert ks.consecutive_failures == 2
    assert ks.cooldown_until > old_cooldown

    # Success resets cooldown
    ks.register_success()
    assert ks.consecutive_failures == 0
    assert ks.cooldown_until == 0.0
    assert ks.is_available() is True


def test_key_rotator_round_robin(tmp_path: Path):
    state_file = tmp_path / "rotator_state.json"
    keys = ["key-alpha-1111", "key-beta-2222"]
    rotator = KeyRotator(keys=keys, state_file=state_file)

    selected = rotator.get_next_key()
    assert selected is not None
    assert selected.key in keys

    # Put first key in cooldown
    selected.register_failure()
    # Next pick must be the other key
    next_pick = rotator.get_next_key()
    assert next_pick is not None
    assert next_pick.key != selected.key


def test_key_rotator_all_cooling_down(tmp_path: Path):
    state_file = tmp_path / "rotator_state.json"
    keys = ["key-alpha-1111"]
    rotator = KeyRotator(keys=keys, state_file=state_file)

    k = rotator.get_next_key()
    k.register_failure()
    assert rotator.get_next_key() is None

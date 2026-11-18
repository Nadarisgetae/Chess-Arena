"""
test_player_model.py — Unit tests for PlayerDifficultyModel and Ridge regression.
"""

import pytest
from backend.player_model import PlayerDifficultyModel


def test_player_model_initialization():
    model = PlayerDifficultyModel()
    assert model.is_fitted is False
    # Fallback with no history should return level 0 for default 1000 Elo
    pred = model.predict_optimal_skill({})
    assert 0 <= pred <= 20
    assert pred == 0


def test_player_model_fallback_with_profile():
    model = PlayerDifficultyModel()
    profile = {
        "avg_centipawn_loss": 25.0,
        "blunder_rate": 0.02,
        "skill_estimate": 1600.0,
    }
    pred = model.predict_optimal_skill(profile)
    # (1600 - 1000) / 75 = 8
    assert pred == 8


def test_player_model_fit_and_predict():
    model = PlayerDifficultyModel()
    history = [
        {"engine_skill_level": 5, "result_score": 1.0, "avg_cp_loss": 30.0},
        {"engine_skill_level": 7, "result_score": 1.0, "avg_cp_loss": 28.0},
        {"engine_skill_level": 9, "result_score": 0.5, "avg_cp_loss": 35.0},
        {"engine_skill_level": 11, "result_score": 0.0, "avg_cp_loss": 45.0},
        {"engine_skill_level": 10, "result_score": 0.5, "avg_cp_loss": 38.0},
        {"engine_skill_level": 10, "result_score": 1.0, "avg_cp_loss": 32.0},
    ]
    model.fit(history)
    assert model.is_fitted is True

    # Prediction should be clamped between 0 and 20
    pred = model.predict_optimal_skill({"avg_centipawn_loss": 35.0, "blunder_rate": 0.05})
    assert 0 <= pred <= 20

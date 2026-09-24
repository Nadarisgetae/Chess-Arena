"""
player_model.py — Phase 2 Statistical Player Model

Uses scikit-learn to map a player's historical features to a recommended
Stockfish skill level (0-20). The model trains on the fly using the
player's own past games to find the "Goldilocks" difficulty.
"""

import logging
from typing import Optional

try:
    from sklearn.linear_model import Ridge
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

# Features used for the model
# [avg_centipawn_loss, blunder_rate, time_variance, endgame_conversion, target_result_score]
# target_result_score: 1.0 (win), 0.5 (draw), 0.0 (loss)


class PlayerDifficultyModel:
    def __init__(self):
        if SKLEARN_AVAILABLE:
            # Simple regularized linear model
            self.model = Ridge(alpha=1.0)
        else:
            self.model = None
        self.is_fitted = False

    def fit(self, historical_data: list[dict]) -> None:
        """
        historical_data is a list of dicts:
        {
            "avg_cp_loss": float,
            "blunder_rate": float,
            "time_variance": float,
            "endgame_conversion": float,
            "result_score": float,  # 1.0 win, 0.5 draw, 0.0 loss
            "engine_skill_level": int  # the target label
        }
        """
        if not SKLEARN_AVAILABLE or len(historical_data) < 3:
            self.is_fitted = False
            return

        X = []
        y = []
        for row in historical_data:
            X.append([
                row.get("avg_cp_loss", 50.0),
                row.get("blunder_rate", 0.05),
                row.get("time_variance", 10.0),
                row.get("endgame_conversion", 0.5),
                row.get("result_score", 0.5)
            ])
            y.append(row.get("engine_skill_level", 10))

        try:
            self.model.fit(np.array(X), np.array(y))
            self.is_fitted = True
        except Exception as e:
            logger.error(f"Failed to fit player model: {e}")
            self.is_fitted = False

    def predict_optimal_skill(self, profile: dict) -> int:
        """
        Predict the engine skill level that would result in a draw (result_score = 0.5)
        for the given player profile.
        """
        if not self.is_fitted or not SKLEARN_AVAILABLE:
            # Fallback to rule-based mapping from skill_estimate if model isn't ready
            skill_est = profile.get("skill_estimate", 1000)
            # Roughly: 1000 Elo -> Level 0, 2500 Elo -> Level 20
            fallback_level = int((skill_est - 1000) / 75)
            return max(0, min(20, fallback_level))

        X_pred = np.array([[
            profile.get("avg_centipawn_loss", 50.0),
            profile.get("blunder_rate", 0.05),
            profile.get("time_variance", 10.0),
            profile.get("endgame_conversion", 0.5),
            0.5  # target result score: we want an even match
        ]])

        try:
            pred = self.model.predict(X_pred)[0]
            # Clamp between 0 and 20
            return int(max(0, min(20, round(pred))))
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return 10

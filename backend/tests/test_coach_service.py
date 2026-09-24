"""
test_coach_service.py — Pure unit tests for coach_service.py

Tests that do NOT require Stockfish (no IO, no async):
  - cp_to_win_pct: Lichess formula, clamping
  - classify_move: all boundary values from the brief
  - build_coach_summary: template output for each label

Run with:
    cd c:\\Projects\\chess-arena
    .\\venv\\Scripts\\Activate.ps1
    pytest backend/tests/test_coach_service.py -v
"""

import pytest
from backend.coach_service import cp_to_win_pct, classify_move, build_coach_summary


# ── cp_to_win_pct ──────────────────────────────────────────────────────────────

class TestCpToWinPct:
    def test_zero_is_fifty(self):
        assert cp_to_win_pct(0) == pytest.approx(50.0, abs=0.01)

    def test_large_positive_near_hundred(self):
        result = cp_to_win_pct(10_000)
        assert result >= 99.0

    def test_large_negative_near_zero(self):
        result = cp_to_win_pct(-10_000)
        assert result <= 1.0

    def test_clamp_upper(self):
        assert cp_to_win_pct(1_000_000) <= 100.0

    def test_clamp_lower(self):
        assert cp_to_win_pct(-1_000_000) >= 0.0

    def test_symmetric(self):
        """Win pct for +cp should equal 100 - win_pct for -cp."""
        assert cp_to_win_pct(200) == pytest.approx(100 - cp_to_win_pct(-200), abs=0.01)

    def test_positive_above_fifty(self):
        assert cp_to_win_pct(100) > 50.0

    def test_negative_below_fifty(self):
        assert cp_to_win_pct(-100) < 50.0

    def test_lichess_constant(self):
        """Spot-check against the known formula with constant 0.00368208."""
        import math
        cp = 300
        expected = 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)
        assert cp_to_win_pct(cp) == pytest.approx(expected, abs=0.001)


# ── classify_move ──────────────────────────────────────────────────────────────

class TestClassifyMove:
    """Boundary tests per COACH_ENGINE_IMPLEMENTATION_BRIEF.md §8.1"""

    # ── best ──
    def test_is_best_move_true_always_best(self):
        assert classify_move(12.0, is_best_move=True) == "best"

    def test_zero_loss_best(self):
        assert classify_move(0.0, is_best_move=False) == "best"

    def test_epsilon_below_loss_best(self):
        assert classify_move(0.04, is_best_move=False) == "best"

    def test_epsilon_boundary_best(self):
        # Exactly 0.05 is still <= epsilon → best
        assert classify_move(0.05, is_best_move=False) == "best"

    # ── good ──
    def test_good_just_above_epsilon(self):
        assert classify_move(0.06, is_best_move=False) == "good"

    def test_good_upper_boundary(self):
        # 9.999 → good
        assert classify_move(9.999, is_best_move=False) == "good"

    # ── inaccuracy ──
    def test_inaccuracy_lower_boundary(self):
        # 10.000 → inaccuracy
        assert classify_move(10.0, is_best_move=False) == "inaccuracy"

    def test_inaccuracy_upper_boundary(self):
        # 19.999 → inaccuracy
        assert classify_move(19.999, is_best_move=False) == "inaccuracy"

    # ── mistake ──
    def test_mistake_lower_boundary(self):
        # 20.000 → mistake
        assert classify_move(20.0, is_best_move=False) == "mistake"

    def test_mistake_upper_boundary(self):
        # 29.999 → mistake
        assert classify_move(29.999, is_best_move=False) == "mistake"

    # ── blunder ──
    def test_blunder_lower_boundary(self):
        # 30.000 → blunder
        assert classify_move(30.0, is_best_move=False) == "blunder"

    def test_blunder_large_loss(self):
        assert classify_move(80.0, is_best_move=False) == "blunder"

    # ── is_best_move overrides all ──
    def test_best_move_overrides_large_loss(self):
        """When is_best_move=True, always 'best' regardless of loss."""
        assert classify_move(50.0, is_best_move=True) == "best"


# ── build_coach_summary ────────────────────────────────────────────────────────

class TestBuildCoachSummary:
    """Smoke tests: ensure each label produces non-empty, label-appropriate text."""

    def _make(self, label, extra=None):
        base = {
            "quality_label": label,
            "win_pct_before": 60.0,
            "win_pct_after": 55.0,
            "win_pct_loss": 5.0,
            "best_move_san": "Nf3",
            "best_line_san": ["Nf3", "d5"],
            "is_checkmate": False,
            "allows_forced_mate": False,
        }
        if extra:
            base.update(extra)
        return base

    def test_checkmate_short_circuits(self):
        analysis = self._make("best", {"is_checkmate": True})
        summary = build_coach_summary(analysis)
        assert "checkmate" in summary.lower()

    def test_best_mentions_line(self):
        analysis = self._make("best")
        summary = build_coach_summary(analysis)
        assert "best" in summary.lower() or "Nf3" in summary

    def test_good_mentions_best_move(self):
        analysis = self._make("good")
        summary = build_coach_summary(analysis)
        assert "Nf3" in summary

    def test_inaccuracy_mentions_loss(self):
        analysis = self._make("inaccuracy", {"win_pct_loss": 15.0})
        summary = build_coach_summary(analysis)
        assert "15.0" in summary

    def test_mistake_mentions_both_pcts(self):
        analysis = self._make("mistake", {"win_pct_before": 70.0, "win_pct_after": 45.0, "win_pct_loss": 25.0})
        summary = build_coach_summary(analysis)
        assert "70.0" in summary
        assert "45.0" in summary

    def test_blunder_warns_recalculate(self):
        analysis = self._make("blunder", {"win_pct_loss": 40.0})
        summary = build_coach_summary(analysis)
        assert "blunder" in summary.lower() or "recalculate" in summary.lower()

    def test_allows_mate_appends_warning(self):
        analysis = self._make("blunder", {"allows_forced_mate": True, "win_pct_loss": 40.0})
        summary = build_coach_summary(analysis)
        assert "forced mate" in summary.lower()

    def test_summary_non_empty_for_all_labels(self):
        for label in ["best", "good", "inaccuracy", "mistake", "blunder"]:
            s = build_coach_summary(self._make(label))
            assert len(s) > 10, f"Summary too short for label={label!r}"

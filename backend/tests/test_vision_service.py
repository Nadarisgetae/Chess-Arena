"""
test_vision_service.py — Unit tests for the Vision module.
"""

import io
from PIL import Image, ImageDraw
import pytest

from backend.vision_service import (
    detect_board_corners,
    warp_board_perspective,
    extract_square_crops,
    reconstruct_fen,
    process_board_image,
)


@pytest.fixture
def synthetic_board_image():
    """Generates a clean synthetic 400x400 checkerboard image for testing."""
    img = Image.new("RGB", (400, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    sq_size = 50
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 1:
                # Dark square
                draw.rectangle(
                    [c * sq_size, r * sq_size, (c + 1) * sq_size, (r + 1) * sq_size],
                    fill=(118, 150, 86),
                )
            else:
                # Light square
                draw.rectangle(
                    [c * sq_size, r * sq_size, (c + 1) * sq_size, (r + 1) * sq_size],
                    fill=(238, 238, 210),
                )
    return img


def test_detect_board_corners_fallback(synthetic_board_image):
    corners = detect_board_corners(synthetic_board_image)
    assert len(corners) == 4
    for pt in corners:
        assert len(pt) == 2
        assert 0 <= pt[0] <= 400
        assert 0 <= pt[1] <= 400


def test_warp_board_perspective(synthetic_board_image):
    corners = [[0, 0], [400, 0], [400, 400], [0, 400]]
    warped = warp_board_perspective(synthetic_board_image, corners, out_size=400)
    assert warped.size == (400, 400)


def test_extract_square_crops(synthetic_board_image):
    squares = extract_square_crops(synthetic_board_image)
    assert len(squares) == 64
    assert squares[0]["square"] == "a8"
    assert squares[-1]["square"] == "h1"


def test_reconstruct_fen_legal():
    # Build standard starting grid
    starting_grid = [
        ["r", "n", "b", "q", "k", "b", "n", "r"],
        ["p", "p", "p", "p", "p", "p", "p", "p"],
        ["empty"] * 8,
        ["empty"] * 8,
        ["empty"] * 8,
        ["empty"] * 8,
        ["P", "P", "P", "P", "P", "P", "P", "P"],
        ["R", "N", "B", "Q", "K", "B", "N", "R"],
    ]
    square_preds = []
    for r in range(8):
        for f in range(8):
            square_preds.append({
                "square": f"{chr(97 + f)}{8 - r}",
                "rank_idx": r,
                "file_idx": f,
                "piece": starting_grid[r][f],
                "confidence": 0.95,
            })

    fen, is_legal, errors, conf = reconstruct_fen(square_preds)
    assert is_legal is True
    assert len(errors) == 0
    assert fen.startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")


def test_process_board_image_end_to_end(synthetic_board_image):
    buf = io.BytesIO()
    synthetic_board_image.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    result = process_board_image(raw_bytes)
    assert "fen" in result
    assert "detected_corners" in result
    assert "warped_image_base64" in result
    assert len(result["squares"]) == 64

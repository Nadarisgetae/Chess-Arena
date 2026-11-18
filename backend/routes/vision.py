"""
routes/vision.py — Vision Mode API endpoints.

POST /api/vision/detect-corners — Detects 4 board corners for canvas overlay
POST /api/vision/predict        — Full vision pipeline: corners, warp, classify, legal FEN
"""

import json
import logging
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from PIL import Image
import io

from backend.vision_service import detect_board_corners, process_board_image

router = APIRouter(prefix="/vision", tags=["Vision"])
logger = logging.getLogger("vision_routes")


class DetectCornersResponse(BaseModel):
    corners: List[List[int]]
    image_width: int
    image_height: int


class SquarePrediction(BaseModel):
    square: str
    piece: str
    confidence: float


class VisionPredictResponse(BaseModel):
    fen: str
    is_legal: bool
    validation_errors: List[str]
    confidence_score: float
    detected_corners: List[List[int]]
    warped_image_base64: str
    squares: List[SquarePrediction]


@router.post(
    "/detect-corners",
    response_model=DetectCornersResponse,
    summary="Detect outer chessboard corners for canvas overlay",
)
async def api_detect_corners(file: UploadFile = File(...)):
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")
        corners = detect_board_corners(image)
        return DetectCornersResponse(
            corners=corners,
            image_width=image.width,
            image_height=image.height,
        )
    except Exception as e:
        logger.exception("Error detecting board corners")
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")


@router.post(
    "/predict",
    response_model=VisionPredictResponse,
    summary="Classify physical chessboard image and reconstruct FEN",
)
async def api_predict_board(
    file: UploadFile = File(...),
    corners: Optional[str] = Form(None),
    player_color: str = Form("white"),
):
    try:
        content = await file.read()
        manual_corners = None
        if corners:
            try:
                manual_corners = json.loads(corners)
            except Exception:
                logger.warning("Failed to parse manual corners JSON; using auto-detect")

        result = process_board_image(
            image_bytes=content,
            manual_corners=manual_corners,
            player_color=player_color,
        )
        return VisionPredictResponse(**result)
    except Exception as e:
        logger.exception("Error during board vision recognition")
        raise HTTPException(status_code=400, detail=f"Failed to recognize board: {str(e)}")

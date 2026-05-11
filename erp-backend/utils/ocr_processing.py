from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException

# Assuming OCR libraries are installed
try:
    from paddleocr import PaddleOCR

    _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en")
except Exception:
    _ocr_engine = None


class VLMEngine:
    async def extract(self, image_path: str) -> Dict[str, Any]:
        return {"vlm_data": "placeholder", "confidence": 0.9}


_vlm_engine = VLMEngine()


async def process_paddleocr(image_path: str) -> Tuple[Dict[str, Any], float]:
    if not _ocr_engine:
        raise HTTPException(status_code=500, detail="PaddleOCR not available")
    _ocr_engine.ocr(image_path, cls=True)
    extracted: Dict[str, Any] = {}
    confidence = 0.9
    return extracted, confidence


async def process_vlm(image_path: str) -> Tuple[Dict[str, Any], float]:
    result = await _vlm_engine.extract(image_path)
    return result, float(result.get("confidence", 0.9))


async def save_document(*args, **kwargs):
    return None


async def save_ocr_result(*args, **kwargs):
    return None


async def get_credit_balance(*args, **kwargs) -> float:
    return 100.0


async def deduct_credit(*args, **kwargs):
    return None


def cleanup_temp_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


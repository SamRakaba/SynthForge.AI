"""
SynthForge.AI Services.

Provides Azure cognitive services integrations:
- OCR Service (Document Intelligence / Vision / GPT-4o)
"""

from synthforge.services.ocr_service import (
    OCRService,
    OCRResult,
    ExtractedText,
    get_ocr_service,
    extract_text_from_image,
)

__all__ = [
    "OCRService",
    "OCRResult",
    "ExtractedText",
    "get_ocr_service",
    "extract_text_from_image",
]

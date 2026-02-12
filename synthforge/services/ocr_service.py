"""
OCR Service for SynthForge.AI.

Provides text extraction from architecture diagrams using:
1. Azure Computer Vision (RECOMMENDED for diagrams) - Best for scene text in images
2. GPT-4o (fallback) - Uses vision model's built-in OCR

For architecture diagrams, Computer Vision is preferred because:
- Diagrams are images with scattered text labels, not structured documents
- CV handles mixed content (icons + text) better
- Optimized for "scene text" extraction
- Better bounding boxes for labels near visual elements
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from synthforge.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedText:
    """A piece of text extracted from the diagram."""
    text: str
    x: float  # 0.0 to 1.0, left to right
    y: float  # 0.0 to 1.0, top to bottom
    width: float  # 0.0 to 1.0
    height: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0


@dataclass
class OCRResult:
    """Result from OCR text extraction."""
    texts: List[ExtractedText]
    source: str  # "computer_vision", "document_intelligence", or "gpt4o"
    image_width: int
    image_height: int


class OCRService:
    """
    OCR service for extracting text from architecture diagrams.
    
    Preference order for diagrams:
    1. Azure Computer Vision - Best for scene text in images/diagrams
    2. GPT-4o - Fallback using vision model's built-in OCR
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def extract_text(self, image_path: str) -> OCRResult:
        """
        Extract text from an image using the best available OCR service.
        
        For architecture diagrams, Computer Vision is preferred.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            OCRResult with extracted text and positions
        """
        ocr_service = self.settings.ocr_service.lower()
        
        # Allow explicit service selection
        if ocr_service == "vision" or ocr_service == "computer_vision":
            if self._has_vision():
                try:
                    return await self._extract_with_computer_vision(image_path)
                except Exception as e:
                    logger.warning(f"Computer Vision OCR failed: {e}")
        
        # Auto mode: try Computer Vision first (better for diagrams), fallback to GPT-4o
        if ocr_service == "auto":
            if self._has_vision():
                try:
                    return await self._extract_with_computer_vision(image_path)
                except Exception as e:
                    logger.warning(f"Computer Vision OCR failed, falling back to GPT-4o: {e}")
        
        # Default/fallback: return empty (let GPT-4o do OCR in the agent)
        logger.info("Using GPT-4o for text extraction (no specialized OCR configured)")
        return OCRResult(texts=[], source="gpt4o", image_width=0, image_height=0)
    
    def _has_vision(self) -> bool:
        """
        Check if Azure Computer Vision is available.
        
        Computer Vision is available if:
        1. Explicit vision_endpoint is configured, OR
        2. We can derive endpoint from Foundry project (AI Services backing)
        """
        # Explicit configuration
        if self.settings.vision_endpoint:
            return True
        
        # Can derive from Foundry endpoint
        if self.settings.project_endpoint:
            return True
        
        return False
    
    def _get_vision_endpoint(self) -> str:
        """
        Get the Computer Vision endpoint.
        
        If not explicitly configured, derives from Foundry project endpoint.
        Azure AI Foundry projects are backed by Azure AI Services which includes CV.
        """
        if self.settings.vision_endpoint:
            return self.settings.vision_endpoint
        
        # Derive from Foundry endpoint
        # PROJECT_ENDPOINT format: https://<resource>.services.ai.azure.com/api/projects/<project-id>
        # AI Services endpoint: https://<resource>.cognitiveservices.azure.com/
        if self.settings.project_endpoint:
            # Extract the resource name
            endpoint = self.settings.project_endpoint
            if ".services.ai.azure.com" in endpoint:
                # Extract base: https://<resource>.services.ai.azure.com
                base = endpoint.split("/api/projects")[0]
                # The AI Services endpoint uses the same base for the new unified API
                return base
        
        raise ValueError("No Computer Vision endpoint available")
    
    async def _extract_with_computer_vision(self, image_path: str) -> OCRResult:
        """
        Extract text using Azure AI Vision (Image Analysis 4.0).
        
        This is the RECOMMENDED method for architecture diagrams because:
        - Optimized for scene text in images
        - Better handling of scattered text labels
        - Returns tight bounding boxes for text near icons
        
        Uses the same Azure AI Services that backs your Foundry project,
        so no additional resources or keys are needed.
        """
        # Try the new Image Analysis SDK first (preferred)
        try:
            return await self._extract_with_image_analysis_sdk(image_path)
        except ImportError:
            logger.debug("azure-ai-vision-imageanalysis not available, trying legacy SDK")
        except Exception as e:
            logger.warning(f"Image Analysis SDK failed: {e}, trying legacy SDK")
        
        # Fallback to legacy Computer Vision SDK
        try:
            return await self._extract_with_legacy_cv_sdk(image_path)
        except ImportError:
            raise ImportError(
                "No Computer Vision SDK available. Install one of:\n"
                "  pip install azure-ai-vision-imageanalysis  (recommended)\n"
                "  pip install azure-cognitiveservices-vision-computervision  (legacy)"
            )
    
    async def _extract_with_image_analysis_sdk(self, image_path: str) -> OCRResult:
        """
        Extract text using Azure AI Vision via REST API with DefaultAzureCredential.
        
        Uses direct REST API call instead of SDK for better compatibility with
        Azure AI Services unified endpoints.
        """
        import httpx
        from azure.identity import DefaultAzureCredential
        
        logger.info("Extracting text with Azure AI Vision (Image Analysis 4.0 REST API)...")
        
        # Get endpoint (auto-derived from Foundry if not explicit)
        endpoint = self._get_vision_endpoint()
        
        # Get token using DefaultAzureCredential
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        )
        
        # Get access token for Cognitive Services
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        
        # Read image
        path = Path(image_path)
        with open(path, "rb") as f:
            image_bytes = f.read()
        
        # Get image dimensions
        from PIL import Image
        with Image.open(path) as img:
            image_width, image_height = img.size
        
        # Call the Image Analysis 4.0 REST API
        # API docs: https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/how-to/call-analyze-image-40
        api_url = f"{endpoint.rstrip('/')}/computervision/imageanalysis:analyze"
        params = {
            "api-version": "2024-02-01",
            "features": "read",  # OCR feature
        }
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/octet-stream",
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                api_url,
                params=params,
                headers=headers,
                content=image_bytes,
            )
            
            if response.status_code != 200:
                raise Exception(f"Image Analysis API error: {response.status_code} - {response.text}")
            
            result = response.json()
        
        # Extract text with positions
        texts = []
        
        read_result = result.get("readResult", {})
        blocks = read_result.get("blocks", [])
        
        for block in blocks:
            for line in block.get("lines", []):
                # Get bounding polygon
                polygon = line.get("boundingPolygon", [])
                if polygon:
                    x_coords = [p.get("x", 0) for p in polygon]
                    y_coords = [p.get("y", 0) for p in polygon]
                    
                    x_min = min(x_coords)
                    x_max = max(x_coords)
                    y_min = min(y_coords)
                    y_max = max(y_coords)
                    
                    # Normalize to 0-1
                    texts.append(ExtractedText(
                        text=line.get("text", ""),
                        x=x_min / image_width,
                        y=y_min / image_height,
                        width=(x_max - x_min) / image_width,
                        height=(y_max - y_min) / image_height,
                        confidence=0.9,
                    ))
                
                # Also extract individual words
                for word in line.get("words", []):
                    polygon = word.get("boundingPolygon", [])
                    if polygon:
                        x_coords = [p.get("x", 0) for p in polygon]
                        y_coords = [p.get("y", 0) for p in polygon]
                        
                        x_min = min(x_coords)
                        x_max = max(x_coords)
                        y_min = min(y_coords)
                        y_max = max(y_coords)
                        
                        texts.append(ExtractedText(
                            text=word.get("text", ""),
                            x=x_min / image_width,
                            y=y_min / image_height,
                            width=(x_max - x_min) / image_width,
                            height=(y_max - y_min) / image_height,
                            confidence=word.get("confidence", 0.9),
                        ))
        
        logger.info(f"Azure AI Vision extracted {len(texts)} text elements")
        
        return OCRResult(
            texts=texts,
            source="computer_vision",
            image_width=image_width,
            image_height=image_height,
        )
    
    async def _extract_with_legacy_cv_sdk(self, image_path: str) -> OCRResult:
        """
        Extract text using the legacy Computer Vision SDK.
        
        This is a fallback for when the new SDK isn't available.
        Requires explicit AZURE_VISION_KEY configuration.
        """
        from azure.cognitiveservices.vision.computervision import ComputerVisionClient
        from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
        from msrest.authentication import CognitiveServicesCredentials
        
        if not self.settings.vision_key:
            raise ValueError(
                "Legacy Computer Vision SDK requires AZURE_VISION_KEY. "
                "Install azure-ai-vision-imageanalysis for key-less auth with DefaultAzureCredential."
            )
        
        logger.info("Extracting text with Computer Vision Read API (legacy SDK)...")
        
        # Initialize client
        client = ComputerVisionClient(
            endpoint=self._get_vision_endpoint(),
            credentials=CognitiveServicesCredentials(self.settings.vision_key),
        )
        
        # Read image
        path = Path(image_path)
        with open(path, "rb") as f:
            image_bytes = f.read()
        
        # Get image dimensions
        from PIL import Image
        with Image.open(path) as img:
            image_width, image_height = img.size
        
        # Start the Read operation (async OCR)
        read_response = client.read_in_stream(
            image=image_bytes,
            raw=True,
        )
        
        # Get the operation location (URL with operation ID)
        operation_location = read_response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]
        
        # Poll for results
        max_retries = 30
        retry_delay = 1  # seconds
        
        for _ in range(max_retries):
            result = client.get_read_result(operation_id)
            
            if result.status == OperationStatusCodes.succeeded:
                break
            elif result.status == OperationStatusCodes.failed:
                raise RuntimeError("Computer Vision Read operation failed")
            
            await asyncio.sleep(retry_delay)
        else:
            raise RuntimeError("Computer Vision Read operation timed out")
        
        # Extract text with positions
        texts = []
        
        for read_result in result.analyze_result.read_results:
            page_width = read_result.width or image_width
            page_height = read_result.height or image_height
            
            for line in read_result.lines:
                # Get bounding box [x1,y1,x2,y2,x3,y3,x4,y4]
                bbox = line.bounding_box
                if bbox and len(bbox) >= 8:
                    x_coords = [bbox[i] for i in range(0, 8, 2)]
                    y_coords = [bbox[i] for i in range(1, 8, 2)]
                    
                    x_min = min(x_coords)
                    x_max = max(x_coords)
                    y_min = min(y_coords)
                    y_max = max(y_coords)
                    
                    # Normalize to 0-1
                    texts.append(ExtractedText(
                        text=line.text,
                        x=x_min / page_width,
                        y=y_min / page_height,
                        width=(x_max - x_min) / page_width,
                        height=(y_max - y_min) / page_height,
                        confidence=line.confidence if hasattr(line, 'confidence') else 0.9,
                    ))
                
                # Also extract individual words for finer granularity
                for word in line.words:
                    word_bbox = word.bounding_box
                    if word_bbox and len(word_bbox) >= 8:
                        x_coords = [word_bbox[i] for i in range(0, 8, 2)]
                        y_coords = [word_bbox[i] for i in range(1, 8, 2)]
                        
                        x_min = min(x_coords)
                        x_max = max(x_coords)
                        y_min = min(y_coords)
                        y_max = max(y_coords)
                        
                        texts.append(ExtractedText(
                            text=word.text,
                            x=x_min / page_width,
                            y=y_min / page_height,
                            width=(x_max - x_min) / page_width,
                            height=(y_max - y_min) / page_height,
                            confidence=word.confidence if hasattr(word, 'confidence') else 0.9,
                        ))
        
        logger.info(f"Computer Vision extracted {len(texts)} text elements")
        
        return OCRResult(
            texts=texts,
            source="computer_vision",
            image_width=image_width,
            image_height=image_height,
        )


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get the singleton OCR service instance."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


async def extract_text_from_image(image_path: str) -> OCRResult:
    """
    Convenience function to extract text from an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        OCRResult with extracted text and positions
    """
    service = get_ocr_service()
    return await service.extract_text(image_path)

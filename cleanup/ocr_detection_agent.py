"""
OCR Detection Agent for SynthForge.AI.

Performs OCR text detection on Azure architecture diagrams to:
1. Extract all visible text from the diagram
2. Identify Azure resources from naming patterns (CAF conventions)
3. Handle multi-line text split due to space constraints
4. Complement icon-based detection with text-based detection

Can run in parallel with VisionAgent for faster processing.

NO STATIC MAPPINGS - Uses Bing Grounding and MCP tools for dynamic lookups.
Agent chooses best tool for each task.
"""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional, List

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    MessageRole,
    ListSortOrder,
    MessageInputImageUrlBlock,
    MessageImageUrlParam,
    MessageInputTextBlock,
)

from synthforge.config import get_settings
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.prompts import (
    get_agent_instructions, 
    get_user_prompt_template, 
    get_response_schema_json,
)

logger = logging.getLogger(__name__)

# =============================================================================
# OCR DETECTION RESULT MODELS (Compatible with VisionAgent output)
# =============================================================================

class TextFragment:
    """A fragment of text detected in the diagram."""
    def __init__(self, text: str, x: float, y: float):
        self.text = text
        self.x = x
        self.y = y


class DiagramMetadata:
    """Metadata extracted from the diagram for file naming."""
    def __init__(
        self,
        title: Optional[str] = None,
        suggested_filename: Optional[str] = None,
        version: Optional[str] = None,
        date_detected: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        self.title = title
        self.suggested_filename = suggested_filename
        self.version = version
        self.date_detected = date_detected
        self.environment = environment

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "suggested_filename": self.suggested_filename,
            "version": self.version,
            "date_detected": self.date_detected,
            "environment": self.environment,
        }


class OCRDetectedIcon:
    """
    OCR detection formatted as DetectedIcon for compatibility with VisionAgent.
    Uses same structure as VisionAgent's detected_icons.
    """
    def __init__(
        self,
        service_type: str,
        instance_name: Optional[str] = None,
        position: Optional[dict] = None,
        confidence: float = 0.5,
        arm_resource_type: Optional[str] = None,
        connections: Optional[List[str]] = None,
        needs_clarification: bool = False,
        clarification_options: Optional[List[str]] = None,
        source: str = "OCR detection",
        ocr_details: Optional[dict] = None,
    ):
        self.service_type = service_type
        self.instance_name = instance_name
        self.position = position or {"x": 0, "y": 0}
        self.confidence = confidence
        self.arm_resource_type = arm_resource_type
        self.connections = connections or []
        self.needs_clarification = needs_clarification
        self.clarification_options = clarification_options or []
        self.source = source
        self.ocr_details = ocr_details

    def to_dict(self) -> dict:
        """Convert to dictionary matching VisionAgent's detected_icons format."""
        return {
            "service_type": self.service_type,
            "instance_name": self.instance_name,
            "position": self.position,
            "confidence": self.confidence,
            "arm_resource_type": self.arm_resource_type,
            "connections": self.connections,
            "needs_clarification": self.needs_clarification,
            "clarification_options": self.clarification_options,
            "source": self.source,
            "ocr_details": self.ocr_details,
        }


class OCRDetectionResult:
    """
    Result from OCR detection analysis.
    Compatible with VisionAgent's DetectionResult format.
    """
    def __init__(
        self,
        diagram_metadata: Optional[DiagramMetadata] = None,
        detected_icons: Optional[List[OCRDetectedIcon]] = None,
        detected_text: Optional[List[dict]] = None,
        vnet_boundaries: Optional[List[dict]] = None,
        data_flows: Optional[List[dict]] = None,
    ):
        self.diagram_metadata = diagram_metadata or DiagramMetadata()
        self.detected_icons = detected_icons or []
        self.detected_text = detected_text or []
        self.vnet_boundaries = vnet_boundaries or []
        self.data_flows = data_flows or []

    def to_dict(self) -> dict:
        """Convert to dictionary matching VisionAgent's output format."""
        return {
            "diagram_metadata": self.diagram_metadata.to_dict(),
            "detected_icons": [d.to_dict() for d in self.detected_icons],
            "detected_text": self.detected_text,
            "vnet_boundaries": self.vnet_boundaries,
            "data_flows": self.data_flows,
        }
    
    @property
    def suggested_filename(self) -> Optional[str]:
        """Get suggested filename from diagram metadata."""
        return self.diagram_metadata.suggested_filename


# =============================================================================
# OCR DETECTION AGENT
# =============================================================================

class OCRDetectionAgent:
    """
    OCR Detection Agent for extracting text from Azure architecture diagrams.
    
    Uses GPT-4o Vision via Azure AI Agents with Bing Grounding to:
    - Extract all visible text from diagrams
    - Identify Azure resources from CAF naming patterns
    - Handle multi-line text reconstruction
    - Provide text-based detections for merger with icon detection
    
    NO STATIC MAPPINGS - Uses Bing grounding to look up naming conventions.
    """
    
    def __init__(self):
        """Initialize the OCR Detection Agent."""
        self.settings = get_settings()
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
        self._tool_config = None
    
    def _build_instructions(self) -> str:
        """
        Build agent instructions from YAML configuration with tool guidance.
        """
        base_instructions = get_agent_instructions("ocr_detection_agent")
        tool_instructions = get_tool_instructions()
        return f"{base_instructions}\n\n{tool_instructions}"
    
    async def __aenter__(self) -> "OCRDetectionAgent":
        """Initialize the agent with Bing Grounding and MCP tools."""
        # Create credential and client
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
        
        self._client = AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=credential,
        )
        
        # Build instructions from YAML
        instructions = self._build_instructions()
        
        # Configure tools: Bing Grounding + Microsoft Learn MCP
        # Bing Grounding: Fast CAF naming lookups and service info (PRIMARY)
        # Microsoft Learn MCP: Complete naming rules, constraints, security best practices
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,  # Microsoft Learn MCP for detailed naming rules
            mcp_servers=["mslearn"],  # https://learn.microsoft.com/api/mcp
        )
        
        # Create the agent with tools
        agent = self._client.create_agent(
            model=self.settings.vision_model_deployment_name,
            name="OCRDetectionAgent",
            instructions=instructions,
            tools=self._tool_config.tools,
            tool_resources=self._tool_config.tool_resources,
            temperature=self.settings.model_temperature,
            top_p=0.95,
        )
        self._agent_id = agent.id
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the agent."""
        if self._client and self._agent_id:
            try:
                self._client.delete_agent(self._agent_id)
            except Exception:
                pass  # Ignore cleanup errors
    
    async def analyze_image(self, image_path: str) -> OCRDetectionResult:
        """
        Analyze an architecture diagram for text detection.
        
        Uses a two-phase approach for best accuracy:
        1. Extract raw text using Azure Document Intelligence (if configured)
        2. Use GPT-4o to infer Azure resources from the extracted text
        
        If Document Intelligence is not configured, falls back to GPT-4o for both.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            OCRDetectionResult with all detected text and inferred resources
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
        # Phase 1: Try to extract text with specialized OCR service first
        pre_extracted_text = None
        try:
            from synthforge.services.ocr_service import extract_text_from_image
            ocr_result = await extract_text_from_image(image_path)
            if ocr_result.texts:
                # Format extracted text for the agent
                pre_extracted_text = self._format_ocr_result(ocr_result)
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Pre-extracted {len(ocr_result.texts)} text elements using {ocr_result.source}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"OCR service not available, using GPT-4o: {e}")
        
        # Read and encode the image
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        image_bytes = path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode()
        
        # Determine MIME type
        suffix = path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        mime_type = mime_types.get(suffix, 'image/png')
        
        # Create the OCR prompt (include pre-extracted text if available)
        ocr_prompt = self._build_ocr_prompt(pre_extracted_text=pre_extracted_text)
        
        # Create thread
        thread = self._client.threads.create()
        
        # Create data URL for the image
        data_url = f"data:{mime_type};base64,{image_base64}"
        
        # Create message with text and image content blocks
        content_blocks = [
            MessageInputTextBlock(type="text", text=ocr_prompt),
            MessageInputImageUrlBlock(
                type="image_url",
                image_url=MessageImageUrlParam(url=data_url, detail="high"),
            ),
        ]
        
        self._client.messages.create(
            thread_id=thread.id,
            role="user",
            content=content_blocks,
        )
        
        # Run the agent with toolset (allows agent to use MCP or Bing as needed)
        run = self._client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self._agent_id,
            toolset=self._tool_config.toolset if self._tool_config else None,
        )
        
        if run.status == "failed":
            raise RuntimeError(f"OCR analysis failed: {run.last_error}")
        
        # Get the response
        last_msg = self._client.messages.get_last_message_text_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            raise RuntimeError("No response from OCR detection agent")
        
        response_text = last_msg.text.value
        
        # Parse the response
        return self._parse_response(response_text)
    
    def _format_ocr_result(self, ocr_result) -> str:
        """
        Format OCR service result for inclusion in the prompt.
        
        This gives GPT-4o pre-extracted text to work with, improving accuracy.
        Includes guidance on multi-line text reconstruction.
        """
        lines = ["## Pre-extracted Text (from Azure Computer Vision)", ""]
        lines.append("The following text has been extracted from the diagram with positions.")
        lines.append("")
        lines.append("**IMPORTANT: Multi-Line Text Reconstruction**")
        lines.append("- Many Azure resource names are SPLIT across multiple lines due to space constraints")
        lines.append("- Look for text fragments that are VERTICALLY CLOSE (within ~5% y distance)")
        lines.append("- Combine fragments that form valid Azure naming patterns when merged")
        lines.append("- Example: 'Azure' at y=0.45, 'Data' at y=0.47, 'Factory' at y=0.49 → 'Azure Data Factory'")
        lines.append("- Example: 'func-' at y=0.30, 'processor' at y=0.32 → 'func-processor'")
        lines.append("")
        lines.append("**IMPORTANT: Same Name, Different Position = SEPARATE Resources**")
        lines.append("- If you see 'Azure Storage' at position (0.2, 0.3) AND at position (0.7, 0.5)")
        lines.append("- These are TWO DIFFERENT storage accounts - report both as separate detections!")
        lines.append("- Position is critical for distinguishing resource instances")
        lines.append("")
        lines.append("Extracted text elements:")
        lines.append("")
        
        # Group text by approximate vertical position for easier multi-line analysis
        sorted_texts = sorted(ocr_result.texts, key=lambda t: (round(t.x, 1), t.y))
        
        for text in sorted_texts:
            # Include position info
            lines.append(f"- \"{text.text}\" at ({text.x:.3f}, {text.y:.3f})")
        
        lines.append("")
        lines.append("Use this pre-extracted text to identify Azure resources. Cross-reference with the image.")
        lines.append("Remember: Reconstruct multi-line names AND report each resource instance separately by position.")
        lines.append("")
        
        return "\n".join(lines)
    
    def _build_ocr_prompt(self, pre_extracted_text: str = None) -> str:
        """Build the prompt for OCR analysis using template from YAML."""
        prompt_template = get_user_prompt_template("ocr_detection_agent")
        response_schema = get_response_schema_json("ocr_detection")
        
        # Include pre-extracted text if available
        extra_context = ""
        if pre_extracted_text:
            extra_context = f"\n{pre_extracted_text}\n"
        
        prompt = prompt_template.format(
            response_schema=response_schema,
            pre_extracted_text=extra_context,
        )
        
        return prompt
    
    def _parse_response(self, response_text: str) -> OCRDetectionResult:
        """Parse the agent's JSON response into OCRDetectionResult."""
        # Extract JSON from response (may be wrapped in markdown)
        json_str = response_text.strip()
        
        # Remove markdown code block if present
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            # Find start and end of JSON
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    start_idx = i + 1
                    break
            end_idx = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() == "```":
                    end_idx = i
                    break
            json_str = "\n".join(lines[start_idx:end_idx])
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try to extract JSON object
            import re
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    # Return empty result on parse failure
                    return OCRDetectionResult()
            else:
                return OCRDetectionResult()
        
        # Parse diagram metadata
        metadata_data = data.get("diagram_metadata", {})
        diagram_metadata = DiagramMetadata(
            title=metadata_data.get("title"),
            suggested_filename=metadata_data.get("suggested_filename"),
            version=metadata_data.get("version"),
            date_detected=metadata_data.get("date_detected"),
            environment=metadata_data.get("environment"),
        )
        
        # Parse detected_icons (compatible with VisionAgent format)
        detected_icons = []
        for item in data.get("detected_icons", []):
            icon = OCRDetectedIcon(
                service_type=item.get("service_type", "Unknown"),
                instance_name=item.get("instance_name"),
                position=item.get("position", {"x": 0, "y": 0}),
                confidence=item.get("confidence", 0.5),
                arm_resource_type=item.get("arm_resource_type"),
                connections=item.get("connections", []),
                needs_clarification=item.get("needs_clarification", False),
                clarification_options=item.get("clarification_options", []),
                source=item.get("source", "OCR detection"),
                ocr_details=item.get("ocr_details"),
            )
            detected_icons.append(icon)

        # Normalize and deduplicate OCR detections
        detected_icons = self._normalize_and_dedupe_icons(detected_icons)
        
        return OCRDetectionResult(
            diagram_metadata=diagram_metadata,
            detected_icons=detected_icons,
            detected_text=data.get("detected_text", []),
            vnet_boundaries=data.get("vnet_boundaries", []),
            data_flows=data.get("data_flows", []),
        )

    def _normalize_and_dedupe_icons(self, icons: List[OCRDetectedIcon]) -> List[OCRDetectedIcon]:
        """Normalize service types and merge duplicate OCR detections."""
        import math
        import re

        def normalize_type(value: Optional[str]) -> str:
            if not value:
                return ""
            cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", value)
            cleaned = " ".join(cleaned.split())
            return cleaned.strip().lower()

        def normalize_name(value: Optional[str]) -> str:
            if not value:
                return ""
            cleaned = " ".join(value.split())
            return cleaned.strip().lower()

        def has_default_position(pos: dict) -> bool:
            return not pos or (pos.get("x", 0) == 0 and pos.get("y", 0) == 0)

        def is_network_label(value: Optional[str]) -> bool:
            if not value:
                return False
            text = value.lower()
            return any(term in text for term in [
                "subnet",
                "integration",
                "private endpoint",
                "managed vnet",
                "delegation",
            ])

        deduped: List[OCRDetectedIcon] = []
        MERGE_THRESHOLD = 0.10  # 10% distance

        for icon in icons:
            service_type = icon.service_type or ""
            instance_name = icon.instance_name or ""

            # Strip parenthetical labels from service_type; move to instance_name if empty
            if "(" in service_type and ")" in service_type:
                match = re.search(r"\(([^)]*)\)", service_type)
                if match and not instance_name:
                    instance_name = match.group(1).strip()
                    icon.instance_name = instance_name
                service_type = re.sub(r"\s*\([^)]*\)\s*", " ", service_type)
                service_type = " ".join(service_type.split()).strip()
                icon.service_type = service_type

            merged = False
            for existing in deduped:
                if normalize_type(existing.service_type) != normalize_type(service_type):
                    continue

                pos_a = existing.position or {"x": 0, "y": 0}
                pos_b = icon.position or {"x": 0, "y": 0}

                name_a = normalize_name(existing.instance_name)
                name_b = normalize_name(instance_name)

                # Merge if instance names match (multi-line labels)
                if name_a and name_b and name_a == name_b:
                    merged = True
                # Treat network-isolation labels as duplicates of the base service
                elif is_network_label(existing.instance_name) or is_network_label(instance_name):
                    merged = True

                # Treat default (0,0) positions as likely duplicates
                if not merged and has_default_position(pos_b):
                    merged = True
                
                # Merge if positions are close
                if not merged:
                    dist = math.sqrt((pos_a.get("x", 0) - pos_b.get("x", 0))**2 + (pos_a.get("y", 0) - pos_b.get("y", 0))**2)
                    if dist < MERGE_THRESHOLD:
                        merged = True

                if merged:
                    # Prefer higher confidence
                    if icon.confidence > existing.confidence:
                        existing.confidence = icon.confidence
                    # Prefer non-default position
                    if has_default_position(pos_a) and not has_default_position(pos_b):
                        existing.position = pos_b
                    # Prefer non-network labels for instance_name
                    if instance_name:
                        if not existing.instance_name or (is_network_label(existing.instance_name) and not is_network_label(instance_name)):
                            existing.instance_name = instance_name
                        elif len(instance_name) > len(existing.instance_name):
                            existing.instance_name = instance_name
                    break

            if not merged:
                deduped.append(icon)

        return deduped


# =============================================================================
# ASYNC HELPER FOR PARALLEL EXECUTION
# =============================================================================

async def run_ocr_detection(image_path: str) -> OCRDetectionResult:
    """
    Run OCR detection on an image.
    
    This can be called in parallel with VisionAgent.analyze_image().
    
    Args:
        image_path: Path to the architecture diagram
        
    Returns:
        OCRDetectionResult with all text detections (compatible with VisionAgent format)
    """
    async with OCRDetectionAgent() as agent:
        return await agent.analyze_image(image_path)

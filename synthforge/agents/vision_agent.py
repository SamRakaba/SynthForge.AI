"""
Vision Agent for SynthForge.AI.

Analyzes Azure architecture diagrams to detect service icons using GPT-4o Vision.
Uses azure.ai.agents.AgentsClient (same as Labfiles examples).

NO STATIC MAPPINGS - All service identification is dynamic via:
1. GPT-4o Vision's inherent knowledge
2. Azure Icon Matcher for unknown icons
3. Official Azure Architecture Icons library
4. Bing Grounding and MCP tools for documentation lookup
"""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

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
from synthforge.models import (
    DetectionResult,
    DetectedIcon,
    DetectedText,
    VNetBoundary,
    DataFlow,
    Position,
)
from synthforge.prompts import get_vision_agent_instructions, get_user_prompt_template, get_response_schema_json
from synthforge.agents.azure_icon_matcher import get_icon_matcher, AzureIconMatcher
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions

logger = logging.getLogger(__name__)


# =============================================================================
# ICON MATCHER FOR DYNAMIC LOOKUPS - NO STATIC MAPPINGS
# =============================================================================

_icon_matcher: Optional[AzureIconMatcher] = None


def _get_matcher() -> AzureIconMatcher:
    """Get or initialize the icon matcher (loads from official MS icons)."""
    global _icon_matcher
    if _icon_matcher is None:
        _icon_matcher = get_icon_matcher()
    return _icon_matcher


async def _normalize_service_name(service_name: str) -> tuple[str, Optional[str]]:
    """
    Normalize a service name using the dynamically-loaded icon library.
    
    NO STATIC MAPPING - looks up from official Azure Architecture Icons.
    
    Returns:
        Tuple of (normalized_name, arm_resource_type)
    """
    matcher = _get_matcher()
    
    # Ensure icons are loaded
    await matcher.ensure_icons_available()
    
    # Look up in dynamic icon library
    service_info = matcher.get_service_by_name(service_name)
    
    if service_info:
        return service_info.name, service_info.arm_type
    
    # Not found - return as-is with Azure prefix if not present
    name = service_name.strip()
    if not name.lower().startswith('azure ') and not name.lower().startswith('microsoft '):
        name = f"Azure {name}"
    
    return name, None


# =============================================================================
# VISION AGENT - NO STATIC MAPPINGS
# =============================================================================

class VisionAgent:
    """
    Vision Agent for detecting Azure resources from architecture diagrams.
    
    Uses GPT-4o Vision via Azure AI Agents to identify:
    - Azure service icons
    - Instance names/labels
    - Network boundaries (VNets, subnets)
    - Data flows and connections
    
    NO STATIC MAPPINGS - Uses dynamic icon library from official MS source.
    """
    
    def __init__(self, use_icon_matcher: bool = True):
        """
        Initialize the Vision Agent.
        
        Args:
            use_icon_matcher: Whether to use the Azure Icon Matcher for
                unknown icon identification. Icons are downloaded dynamically
                from official Microsoft Azure Architecture Icons.
        """
        self.settings = get_settings()
        self.use_icon_matcher = use_icon_matcher
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
        self._icon_matcher: Optional[AzureIconMatcher] = None
        self._tool_config = None
    
    async def _build_instructions(self) -> str:
        """
        Build instructions with dynamically-loaded icon context.
        
        NO STATIC MAPPINGS - Gets service list from official Azure icons.
        """
        base_instructions = get_vision_agent_instructions()
        
        if not self.use_icon_matcher:
            return base_instructions
        
        # Initialize icon matcher and load icons
        matcher = _get_matcher()
        await matcher.ensure_icons_available()
        
        # Get dynamic service list from icon library
        services = matcher.get_all_services()
        
        if not services:
            return base_instructions
        
        # Build dynamic icon reference from official icons
        service_list = []
        for svc in services[:100]:  # Limit to avoid token overflow
            line = f"- {svc.name}"
            if svc.category:
                line += f" ({svc.category})"
            service_list.append(line)
        
        service_ref = "\n".join(service_list)
        
        enhanced_instructions = f"""{base_instructions}

## Azure Services Reference (from official Azure Architecture Icons)
These are official Azure services from Microsoft's icon library. Use these
official names when identifying icons:

{service_ref}
"""
        return enhanced_instructions
    
    async def __aenter__(self) -> "VisionAgent":
        """Initialize the agent with Bing Grounding and MCP tools."""
        # Initialize icon matcher
        if self.use_icon_matcher:
            self._icon_matcher = _get_matcher()
            await self._icon_matcher.ensure_icons_available()
        
        # Create credential and client
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
        
        self._client = AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=credential,
        )
        
        # Build instructions with dynamic icon context and tool guidance
        base_instructions = await self._build_instructions()
        tool_instructions = get_tool_instructions()
        instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Configure tools: Bing Grounding + Microsoft Learn MCP
        # Bing Grounding: Fast Azure service lookups and icon verification (PRIMARY)
        # Microsoft Learn MCP: Deep documentation, security best practices, ARM resource details
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,  # Microsoft Learn MCP for enhanced analysis
            mcp_servers=["mslearn"],  # https://learn.microsoft.com/api/mcp
        )
        
        # Create the agent with tools for icon verification
        agent = self._client.create_agent(
            model=self.settings.vision_model_deployment_name,
            name="VisionAgent",
            instructions=instructions,
            tools=self._tool_config.tools,
            tool_resources=self._tool_config.tool_resources,
            temperature=0.0,  # Deterministic icon detection
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
    
    async def analyze_image(
        self, 
        image_path: str,
        description_context: Optional[str] = None,
    ) -> DetectionResult:
        """
        Analyze an architecture diagram image.
        
        Args:
            image_path: Path to the image file
            description_context: Optional context from DescriptionAgent to improve detection
            
        Returns:
            DetectionResult with all detected components
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
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
        
        # Get image dimensions if PIL available
        try:
            from PIL import Image
            with Image.open(path) as img:
                width, height = img.size
            image_dimensions = {"width": width, "height": height}
        except ImportError:
            image_dimensions = None
        
        # Create the vision prompt (include description context if available)
        vision_prompt = self._build_vision_prompt(
            image_dimensions=image_dimensions,
            description_context=description_context,
        )
        
        # DEBUG: Log the prompt being sent
        logger.info("=" * 80)
        logger.info("VISION AGENT PROMPT (first 500 chars):")
        logger.info(vision_prompt[:500])
        logger.info(f"... (total length: {len(vision_prompt)} chars)")
        if description_context:
            logger.info(f"Description context included: {len(description_context)} chars")
        logger.info("=" * 80)
        
        # Create thread
        thread = self._client.threads.create()
        
        # Create data URL for the image
        data_url = f"data:{mime_type};base64,{image_base64}"
        
        # Create message with text and image content blocks
        content_blocks = [
            MessageInputTextBlock(type="text", text=vision_prompt),
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
        logger.info("Starting vision agent run...")
        run = self._client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self._agent_id,
            toolset=self._tool_config.toolset if self._tool_config else None,
        )
        
        logger.info(f"Vision agent run completed with status: {run.status}")
        logger.info(f"Run ID: {run.id}")
        
        if run.status == "failed":
            # Log detailed error info for debugging
            error_info = {
                "status": run.status,
                "last_error": str(run.last_error) if run.last_error else None,
                "run_id": run.id,
            }
            logger.error(f"Vision agent run failed: {error_info}")
            raise RuntimeError(f"Vision analysis failed: {run.last_error}")
        
        # Get the response
        last_msg = self._client.messages.get_last_message_text_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            logger.error("No response message from vision agent")
            raise RuntimeError("No response from vision agent")
        
        response_text = last_msg.text.value
        
        # DEBUG: Log the raw response
        logger.info("=" * 80)
        logger.info("VISION AGENT RAW RESPONSE:")
        logger.info(f"Response length: {len(response_text)} chars")
        logger.info("First 1000 chars:")
        logger.info(response_text[:1000])
        if len(response_text) > 1000:
            logger.info("... (truncated)")
            logger.info("Last 500 chars:")
            logger.info(response_text[-500:])
        logger.info("=" * 80)
        
        # Parse the response and attempt to identify unknown icons
        return await self._parse_response(
            response_text, 
            image_path=str(path),
            image_dimensions=image_dimensions,
        )
    
    def _build_vision_prompt(
        self, 
        image_dimensions: Optional[dict] = None,
        description_context: Optional[str] = None,
    ) -> str:
        """Build the prompt for vision analysis using template from YAML."""
        # Load user prompt template and response schema from YAML configuration
        prompt_template = get_user_prompt_template("vision_agent")
        response_schema = get_response_schema_json("vision_detection")
        
        dimension_info = ""
        if image_dimensions:
            dimension_info = f"\nImage dimensions: {image_dimensions['width']}x{image_dimensions['height']} pixels"
        
        # Build prompt from template with placeholders
        prompt = prompt_template.format(
            dimension_info=dimension_info,
            response_schema=response_schema,
        )
        
        # Add description context if provided (as hints AFTER main instructions)
        if description_context:
            prompt = f"""{prompt}

---

**CONTEXT HINTS (Optional Guidance Only):**

{description_context}

**IMPORTANT**: The hints above are for reference only. Your primary task is to INDEPENDENTLY detect what YOU SEE using your vision capabilities. Do not limit detection to the hints - detect ALL visible icons whether or not they appear in the hints above.
"""
        
        return prompt
    
    async def _parse_response(
        self, 
        response_text: str,
        image_path: Optional[str] = None,
        image_dimensions: Optional[dict] = None,
    ) -> DetectionResult:
        """
        Parse the agent response into DetectionResult.
        
        For icons with low confidence or "Unknown" type, attempts to identify
        them using the AzureIconMatcher's template/feature matching.
        """
        # Extract JSON from response
        try:
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            logger.info(f"Attempting to parse JSON (start={json_start}, end={json_end})")
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                logger.info(f"Extracted JSON string length: {len(json_str)} chars")
                logger.info("JSON string preview (first 500 chars):")
                logger.info(json_str[:500])
                data = json.loads(json_str)
                logger.info(f"Successfully parsed JSON with keys: {list(data.keys())}")
            else:
                logger.error(f"No JSON braces found in response (start={json_start}, end={json_end})")
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Failed JSON string (first 500 chars): {json_str[:500] if 'json_str' in locals() else 'N/A'}")
            raise ValueError(f"Failed to parse vision response: {e}")
        
        # Parse detected icons
        icons = []
        unknown_icons = []  # Track icons needing icon matcher lookup
        
        detected_icons_list = data.get("detected_icons", [])
        logger.info(f"Parsing {len(detected_icons_list)} detected icons from response")
        
        # Also check for alternative key names
        if not detected_icons_list:
            # Try alternative keys
            detected_icons_list = data.get("components", [])
            if detected_icons_list:
                logger.info(f"Found icons under 'components' key instead: {len(detected_icons_list)} icons")
        
        if not detected_icons_list:
            logger.warning("No detected_icons or components found in response!")
            logger.warning(f"Available keys in response: {list(data.keys())}")
        
        for icon_data in detected_icons_list:
            # Normalize the service name using icon matcher
            service_type = icon_data.get("service_type", icon_data.get("type", "Unknown"))
            normalized_name, arm_type = await _normalize_service_name(service_type)
            
            # CRITICAL: Validate ARM type consistency
            # If agent provided arm_resource_type but it doesn't match normalized service,
            # this indicates a mismatch (e.g., "Azure Storage Mover" with "Microsoft.Storage/storageAccounts")
            agent_arm_type = icon_data.get("arm_resource_type")
            if agent_arm_type and arm_type and agent_arm_type != arm_type:
                # Agent's ARM type doesn't match the normalized service - keep agent's version
                # but flag for review if confidence is high
                final_arm_type = agent_arm_type
            else:
                # Use agent's ARM type if provided, otherwise use normalized
                final_arm_type = agent_arm_type or arm_type
            
            # If no ARM type found and service was normalized, mark for clarification
            needs_clarification = icon_data.get("needs_clarification", False)
            if not final_arm_type and service_type != normalized_name:
                # Service was normalized but no ARM type found - uncertain detection
                needs_clarification = True
            
            pos_data = icon_data.get("position", {})
            icon = DetectedIcon(
                type=normalized_name,
                name=icon_data.get("instance_name", icon_data.get("name")),
                position=Position(
                    x=pos_data.get("x", 0.0),
                    y=pos_data.get("y", 0.0),
                ),
                confidence=icon_data.get("confidence", 0.5),
                arm_resource_type=final_arm_type,
                needs_clarification=needs_clarification,
                clarification_options=icon_data.get("clarification_options", []),
                reasoning=icon_data.get("reasoning"),
            )
            
            # Check if this icon needs icon matcher identification
            if (icon.type.lower() in ("unknown", "azure unknown", "unidentified") 
                or icon.confidence < 0.6 
                or icon.needs_clarification):
                unknown_icons.append((len(icons), icon, icon_data))
            
            icons.append(icon)
        
        # Attempt to identify unknown icons using icon matcher
        if unknown_icons and image_path and image_dimensions and self._icon_matcher:
            await self._try_identify_unknown_icons(
                icons, unknown_icons, image_path, image_dimensions
            )
        
        # Parse detected text
        texts = []
        for text_data in data.get("detected_text", []):
            pos_data = text_data.get("position", {})
            text = DetectedText(
                text=text_data.get("text", ""),
                position=Position(
                    x=pos_data.get("x", 0.0),
                    y=pos_data.get("y", 0.0),
                ),
                confidence=text_data.get("confidence", 0.8),
                classification=text_data.get("type", "label"),
            )
            texts.append(text)
        
        # Parse VNet boundaries
        vnets = []
        for vnet_data in data.get("vnet_boundaries", []):
            vnet = VNetBoundary(
                name=vnet_data.get("name", ""),
                type=vnet_data.get("type", "vnet"),
                position=Position(x=0, y=0),  # Will be refined
                contained_resources=vnet_data.get("contained_resources", []),
            )
            vnets.append(vnet)
        
        # Parse data flows
        flows = []
        for flow_data in data.get("data_flows", []):
            flow = DataFlow(
                source=flow_data.get("source", ""),
                target=flow_data.get("target", ""),
                protocol=flow_data.get("protocol"),
                flow_type=flow_data.get("flow_type", "data"),
            )
            flows.append(flow)
        
        return DetectionResult(
            icons=icons,
            texts=texts,
            vnet_boundaries=vnets,
            data_flows=flows,
        )
    
    async def _try_identify_unknown_icons(
        self,
        icons: list[DetectedIcon],
        unknown_icons: list[tuple],
        image_path: str,
        image_dimensions: dict,
    ) -> None:
        """
        Attempt to identify unknown icons using template/feature matching.
        
        Uses the AzureIconMatcher to crop icon regions from the source image
        and match against the official Azure icon library.
        
        Args:
            icons: List of all detected icons (modified in place)
            unknown_icons: List of (index, icon, original_data) tuples for unknown icons
            image_path: Path to the source diagram image
            image_dimensions: Dict with 'width' and 'height' keys
        """
        if not self._icon_matcher:
            return
        
        width = image_dimensions.get("width", 1)
        height = image_dimensions.get("height", 1)
        
        for idx, icon, original_data in unknown_icons:
            try:
                # Convert relative position to bounding box
                # Assume icon is roughly 8% of image width/height
                pos_data = original_data.get("position", {})
                x_pct = pos_data.get("x", pos_data.get("x_percent", 50))
                y_pct = pos_data.get("y", pos_data.get("y_percent", 50))
                w_pct = pos_data.get("width", pos_data.get("width_percent", 8))
                h_pct = pos_data.get("height", pos_data.get("height_percent", 10))
                
                # Normalize percentages (some may be 0-1, some 0-100)
                if x_pct <= 1.0 and y_pct <= 1.0:
                    x_pct *= 100
                    y_pct *= 100
                    w_pct *= 100 if w_pct <= 1.0 else w_pct
                    h_pct *= 100 if h_pct <= 1.0 else h_pct
                
                bounding_box = {
                    "x": x_pct,
                    "y": y_pct,
                    "width": w_pct,
                    "height": h_pct,
                }
                
                # Try to identify using icon matcher
                match = await self._icon_matcher.identify_unknown_icon(
                    source_image=image_path,
                    bounding_box=bounding_box,
                    image_size=(width, height),
                )
                
                if match and match.confidence >= 0.6:
                    # Update the icon with matched information
                    icons[idx] = DetectedIcon(
                        type=match.service_name,
                        name=icon.name,
                        position=icon.position,
                        confidence=max(icon.confidence, match.confidence),
                        arm_resource_type=match.arm_resource_type or icon.arm_resource_type,
                        needs_clarification=False,  # Resolved by icon matcher
                        clarification_options=None,
                        reasoning=f"Identified via {match.match_method} matching",
                    )
                    
            except Exception as e:
                # Icon matching failed - keep original detection
                continue

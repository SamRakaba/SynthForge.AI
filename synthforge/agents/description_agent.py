"""
Description Agent for SynthForge.AI.

Performs a free-form description of an Azure architecture diagram BEFORE
structured detection. This provides context hints that improve icon detection.

The insight: When asked to "describe" an image rather than "detect objects",
LLMs provide more comprehensive coverage because they're not constrained
by strict JSON output requirements.

This agent:
1. Describes the overall architecture
2. Lists all visible components in natural language
3. Identifies groupings (zones, regions, VNets)
4. Notes relationships and data flows

The description is then passed to VisionAgent as context for structured detection.

Uses Bing Grounding and MCP tools for dynamic Azure documentation lookup.
NO STATIC MAPPINGS - Agent chooses best tool for each task.
"""

import base64
import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    MessageRole,
    MessageInputImageUrlBlock,
    MessageImageUrlParam,
    MessageInputTextBlock,
)

from synthforge.config import get_settings
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureDescription:
    """Result from architecture description analysis."""
    title: Optional[str] = None
    overview: Optional[str] = None
    azure_components: List[str] = None
    infrastructure: List[str] = None
    network_topology: List[str] = None
    external_sources: List[str] = None
    supporting_services: List[str] = None
    users_actors: List[str] = None
    groupings: List[str] = None
    network_associations: List[str] = None
    raw_description: str = ""
    
    def __post_init__(self):
        self.azure_components = self.azure_components or []
        self.infrastructure = self.infrastructure or []
        self.network_topology = self.network_topology or []
        self.external_sources = self.external_sources or []
        self.supporting_services = self.supporting_services or []
        self.users_actors = self.users_actors or []
        self.groupings = self.groupings or []
        self.network_associations = self.network_associations or []
    
    def get_all_components(self) -> List[str]:
        """Get all components as a flat list (excludes supporting services, network topology, and external sources), deduplicated."""
        all_components = []
        all_components.extend(self.azure_components)
        all_components.extend(self.infrastructure)
        # NOTE: Supporting services, network topology, and external sources are excluded from critical requirements
        # They are reference-only and should be detected only if explicitly visible
        # Deduplicate while preserving order
        return self._deduplicate_components(all_components)
    
    def _deduplicate_components(self, components: List[str]) -> List[str]:
        """
        Remove duplicate components based on normalized service names.
        
        Handles cases like:
        - "Azure Functions" and "Azure Function" (singular/plural)
        - "Azure SQL Database" and "Azure SQL" (partial match)
        - "App Service" and "Azure App Service" (with/without Azure prefix)
        """
        seen = set()
        deduplicated = []
        
        for comp in components:
            # Normalize: lowercase, strip whitespace, remove "Azure " prefix for comparison
            normalized = comp.lower().strip()
            normalized = normalized.replace("azure ", "").replace("microsoft ", "")
            # Remove trailing 's' for singular/plural matching
            if normalized.endswith('s') and not normalized.endswith('ss'):
                normalized_singular = normalized[:-1]
            else:
                normalized_singular = normalized
            
            # Check if we've seen this or a similar component
            if normalized not in seen and normalized_singular not in seen:
                seen.add(normalized)
                seen.add(normalized_singular)
                deduplicated.append(comp)
        
        return deduplicated
    
    def to_context_hints(self) -> str:
        """Format as context hints for VisionAgent - Suggestive guidance, not requirements."""
        # Load context hints template from YAML
        from synthforge.prompts import get_prompt_template
        hints_template = get_prompt_template(
            "description_agent",
            "context_hints_template",
            from_iac=False
        )
        
        # Build components list
        components_list_items = []
        all_components = []
        
        if self.azure_components:
            components_list_items.append("### Expected Azure Managed Services:")
            for i, comp in enumerate(self.azure_components, 1):
                components_list_items.append(f"  {i}. {comp}")
                all_components.append(comp)
            components_list_items.append("")
        
        if self.infrastructure:
            components_list_items.append("### Expected Infrastructure Components:")
            start = len(all_components) + 1
            for i, comp in enumerate(self.infrastructure, start):
                components_list_items.append(f"  {i}. {comp}")
                all_components.append(comp)
            components_list_items.append("")
        
        # Network topology listed as hints
        if self.network_topology:
            components_list_items.append("### Expected Network Topology:")
            components_list_items.append("Look for these network boundaries/containers if visible:")
            for comp in self.network_topology:
                components_list_items.append(f"  - {comp}")
            components_list_items.append("")
        
        # External sources as hints
        if self.external_sources:
            components_list_items.append("### Possible External Sources:")
            components_list_items.append("Check for these non-Azure systems if depicted:")
            for comp in self.external_sources:
                components_list_items.append(f"  - {comp}")
            components_list_items.append("")
        
        # Supporting services as hints
        if self.supporting_services:
            components_list_items.append("### Possible Supporting Services:")
            components_list_items.append("Look for these shared services if shown as icons:")
            for comp in self.supporting_services:
                components_list_items.append(f"  - {comp}")
            components_list_items.append("")
        
        # Groupings/Zones
        if self.groupings:
            components_list_items.append("### Possible Groupings/Zones:")
            components_list_items.append("Check for these if explicitly labeled in the diagram:")
            for group in self.groupings:
                components_list_items.append(f"  - {group}")
            components_list_items.append("")
        
        components_list_str = "\n".join(components_list_items)
        
        # Format the template with context
        formatted_hints = hints_template.format(
            diagram_title=self.title or "Azure Architecture Diagram",
            expected_count=len(all_components),
            components_list=components_list_str
        )
        
        return formatted_hints
        lines.append("If you detect fewer, verify you scanned thoroughly. Do NOT add undetected items.")
        lines.append("=" * 60)
        lines.append("")
        
        result = "\n".join(lines)
        
        # DEBUG: Log the context hints
        logger.info("=" * 80)
        logger.info("CONTEXT HINTS FOR VISION AGENT:")
        logger.info(f"Total length: {len(result)} chars")
        logger.info(f"Component count: {len(all_components)}")
        logger.info(result[:800])
        if len(result) > 800:
            logger.info("... (truncated)")
        logger.info("=" * 80)
        
        return result
    
    def to_filter_hints(self) -> dict:
        """
        Format as hints for FilterAgent classification.
        
        IMPORTANT: These hints are advisory only. The Filter Agent should:
        1. Use MS Learn MCP + Bing Grounding to research ARM resource types
        2. Apply first-principles reasoning about deployment patterns
        3. If MCP/Bing research conflicts with these hints, trust the research
        
        Returns:
            Dictionary with classification hints for the filter agent
        """
        return {
            "architectural_components": list(set(
                self.azure_components + self.infrastructure
            )),
            "reference_only": {
                "network_topology": list(set(self.network_topology)),
                "external_sources": list(set(self.external_sources)),
                "supporting_services": list(set(self.supporting_services)),
                "users_actors": list(set(self.users_actors))
            },
            "classification_guidance": {
                "architectural": "Core application components deployed per-app - INCLUDE in IaC",
                "network_topology": "Network boundaries/containers - typically reference only unless standalone firewalls/load balancers",
                "external_sources": "Non-Azure systems - FILTER OUT (not deployable via Azure IaC)",
                "supporting_services": "Shared monitoring/identity/DevOps - typically FILTER OUT unless deployed per-app",
                "users_actors": "User types/actors - FILTER OUT (not Azure resources)"
            },
            "mcp_research_priority": {
                "note": "If research shows a different ARM resource type or deployment pattern than suggested here, TRUST THE RESEARCH",
                "example": "If hint says 'supporting' but research shows per-app ARM type → classify as architectural"
            }
        }


class DescriptionAgent:
    """
    Description Agent for free-form architecture analysis.
    
    Uses GPT-4o Vision to describe the architecture before structured detection.
    This provides better coverage because the model isn't constrained by
    JSON output requirements.
    
    NOTE: All prompts are centralized in synthforge/prompts/agent_instructions.yaml
    User prompt is loaded dynamically via get_user_prompt_template('description_agent')
    """

    def __init__(self):
        """Initialize the Description Agent."""
        self.settings = get_settings()
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
        self._tool_config = None
    
    async def __aenter__(self) -> "DescriptionAgent":
        """Initialize the agent with Bing Grounding and MCP tools."""
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
        
        self._client = AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=credential,
        )
        
        # Load instructions from YAML
        from synthforge.prompts import get_description_agent_instructions
        
        base_instructions = get_description_agent_instructions()
        
        # Add tool usage instructions
        tool_instructions = get_tool_instructions()
        instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Configure tools: Bing Grounding + Microsoft Learn MCP
        # Bing Grounding: Fast Azure documentation and service descriptions (PRIMARY)
        # Microsoft Learn MCP: Deep documentation, recommendations, best practices, security analysis
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,  # Microsoft Learn MCP for enhanced recommendations
            mcp_servers=["mslearn"],  # https://learn.microsoft.com/api/mcp
        )
        
        agent = self._client.create_agent(
            model=self.settings.vision_model_deployment_name,
            name="DescriptionAgent",
            instructions=instructions,
            tools=self._tool_config.tools,
            tool_resources=self._tool_config.tool_resources,
            temperature=0.0,  # Fully deterministic for consistent component counts
            top_p=0.95,  # Nucleus sampling for quality
            response_format={"type": "json_object"},  # Force structured JSON output
        )
        self._agent_id = agent.id
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the agent."""
        if self._client and self._agent_id:
            try:
                self._client.delete_agent(self._agent_id)
            except Exception:
                pass
    
    async def describe_architecture(self, image_path: str) -> ArchitectureDescription:
        """
        Describe an architecture diagram.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ArchitectureDescription with all identified components
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
        logger.info("Describing architecture diagram...")
        
        # Read and encode the image
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        image_bytes = path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode()
        
        # Generate image hash for consistency tracking
        import hashlib
        image_hash = hashlib.sha256(image_bytes).hexdigest()[:12]
        self._current_image_hash = image_hash  # Store for logging
        logger.debug(f"Image hash: {image_hash} - tracking for consistency")
        
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
        
        # Create thread
        thread = self._client.threads.create()
        
        # Create data URL for the image
        data_url = f"data:{mime_type};base64,{image_base64}"
        
        # Load user prompt from YAML (centralized prompts)
        from synthforge.prompts import get_user_prompt_template
        user_prompt = get_user_prompt_template('description_agent')
        
        # Create message with image
        content_blocks = [
            MessageInputTextBlock(type="text", text=user_prompt),
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
        
        # Run the agent with toolset
        run = self._client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self._agent_id,
            toolset=self._tool_config.toolset if self._tool_config else None,
        )
        
        if run.status == "failed":
            raise RuntimeError(f"Description failed: {run.last_error}")
        
        # Get the response
        last_msg = self._client.messages.get_last_message_text_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            raise RuntimeError("No response from description agent")
        
        response_text = last_msg.text.value
        
        # DEBUG: Log description agent response
        logger.info("=" * 80)
        logger.info("DESCRIPTION AGENT RESPONSE:")
        logger.info(f"Response length: {len(response_text)} chars")
        logger.info(response_text[:500])
        if len(response_text) > 500:
            logger.info("... (truncated)")
        logger.info("=" * 80)
        
        # Parse the response
        return self._parse_response(response_text)
    
    def _parse_response(self, response_text: str) -> ArchitectureDescription:
        """Parse the agent's JSON response."""
        # Extract JSON from response
        json_str = response_text.strip()
        
        # Remove markdown code block if present
        if json_str.startswith("```"):
            lines = json_str.split("\n")
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
        except json.JSONDecodeError:
            # Try to extract JSON object
            import re
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    # Return with just raw description
                    return ArchitectureDescription(raw_description=response_text)
            else:
                return ArchitectureDescription(raw_description=response_text)
        
        # Build ArchitectureDescription
        description = ArchitectureDescription(
            title=data.get("title"),
            overview=data.get("overview"),
            azure_components=data.get("azure_components", []),
            external_sources=data.get("external_sources", []),
            infrastructure=data.get("infrastructure", []),
            network_topology=data.get("network_topology", []),
            supporting_services=data.get("supporting_services", []),
            users_actors=data.get("users_actors", []),
            groupings=data.get("groupings", []),
            network_associations=data.get("network_associations", []),
            raw_description=response_text,
        )
        
        total_components = len(description.get_all_components())
        image_hash = getattr(self, '_current_image_hash', 'unknown')
        logger.info(f"Description identified {total_components} components (image: {image_hash})")
        logger.debug(f"NOTE: Vision models may have ±2-3 component variance even at temperature=0.0")
        
        return description


async def describe_architecture(image_path: str) -> ArchitectureDescription:
    """
    Convenience function to describe an architecture diagram.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        ArchitectureDescription with all identified components
    """
    async with DescriptionAgent() as agent:
        return await agent.describe_architecture(image_path)

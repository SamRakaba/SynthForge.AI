"""
Detection Merger Agent for SynthForge.AI.

Merges icon-based detections (from VisionAgent) with text-based detections
(from OCRDetectionAgent) to produce a unified, deduplicated list of Azure resources.

Key responsibilities:
1. Spatial deduplication - merge detections in same vicinity
2. Information enrichment - combine icon service type with OCR resource names
3. Conflict resolution - handle cases where sources disagree
4. Clarification resolution - use cross-source info to resolve uncertain detections
5. Statistics reporting - track merge operations for debugging

NO STATIC MAPPINGS - Uses Bing Grounding and MCP tools for any needed lookups.
Agent chooses best tool for each task.
"""

import asyncio
import json
import math
from typing import Any, Optional, List, Dict

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole

from synthforge.config import get_settings
from synthforge.models import DetectionResult, DetectedIcon
from synthforge.agents.ocr_detection_agent import OCRDetectionResult, OCRDetectedIcon
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.prompts import (
    get_agent_instructions,
    get_user_prompt_template,
    get_response_schema_json,
)


# =============================================================================
# MERGE RESULT MODELS
# =============================================================================

class MergedResource:
    """A resource after merging icon and OCR detections."""
    def __init__(
        self,
        service_type: str,
        instance_name: Optional[str] = None,
        position: Optional[dict] = None,
        confidence: float = 0.5,
        arm_resource_type: Optional[str] = None,
        detection_sources: Optional[List[str]] = None,
        merge_notes: Optional[str] = None,
        needs_clarification: bool = False,
        naming_constraints: Optional[dict] = None,
    ):
        self.service_type = service_type
        self.instance_name = instance_name
        self.position = position or {}
        self.confidence = confidence
        self.arm_resource_type = arm_resource_type
        self.detection_sources = detection_sources or []
        self.merge_notes = merge_notes
        self.needs_clarification = needs_clarification
        self.naming_constraints = naming_constraints

    def to_dict(self) -> dict:
        return {
            "service_type": self.service_type,
            "instance_name": self.instance_name,
            "position": self.position,
            "confidence": self.confidence,
            "arm_resource_type": self.arm_resource_type,
            "detection_sources": self.detection_sources,
            "merge_notes": self.merge_notes,
            "needs_clarification": self.needs_clarification,
            "naming_constraints": self.naming_constraints,
        }


class ResolutionAttempt:
    """Record of an attempt to resolve an uncertain detection."""
    def __init__(
        self,
        original_detection: str,
        resolution_method: str,
        resolved_to: Optional[str] = None,
        confidence: float = 0.0,
    ):
        self.original_detection = original_detection
        self.resolution_method = resolution_method
        self.resolved_to = resolved_to
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "original_detection": self.original_detection,
            "resolution_method": self.resolution_method,
            "resolved_to": self.resolved_to,
            "confidence": self.confidence,
        }


class MergeStatistics:
    """Statistics about the merge operation."""
    def __init__(
        self,
        total_icon_detections: int = 0,
        total_ocr_detections: int = 0,
        merged_duplicates: int = 0,
        ocr_only_additions: int = 0,
        icon_only_kept: int = 0,
        resolved_clarifications: int = 0,
        remaining_clarifications: int = 0,
    ):
        self.total_icon_detections = total_icon_detections
        self.total_ocr_detections = total_ocr_detections
        self.merged_duplicates = merged_duplicates
        self.ocr_only_additions = ocr_only_additions
        self.icon_only_kept = icon_only_kept
        self.resolved_clarifications = resolved_clarifications
        self.remaining_clarifications = remaining_clarifications

    def to_dict(self) -> dict:
        return {
            "total_icon_detections": self.total_icon_detections,
            "total_ocr_detections": self.total_ocr_detections,
            "merged_duplicates": self.merged_duplicates,
            "ocr_only_additions": self.ocr_only_additions,
            "icon_only_kept": self.icon_only_kept,
            "resolved_clarifications": self.resolved_clarifications,
            "remaining_clarifications": self.remaining_clarifications,
        }


class MergeResult:
    """Result from detection merging."""
    def __init__(
        self,
        merged_resources: Optional[List[MergedResource]] = None,
        ocr_only_resources: Optional[List[dict]] = None,
        unresolved_detections: Optional[List[dict]] = None,
        resolution_attempts: Optional[List[ResolutionAttempt]] = None,
        merge_statistics: Optional[MergeStatistics] = None,
    ):
        self.merged_resources = merged_resources or []
        self.ocr_only_resources = ocr_only_resources or []
        self.unresolved_detections = unresolved_detections or []
        self.resolution_attempts = resolution_attempts or []
        self.merge_statistics = merge_statistics or MergeStatistics()

    def to_dict(self) -> dict:
        return {
            "merged_resources": [r.to_dict() for r in self.merged_resources],
            "ocr_only_resources": self.ocr_only_resources,
            "unresolved_detections": self.unresolved_detections,
            "resolution_attempts": [r.to_dict() for r in self.resolution_attempts],
            "merge_statistics": self.merge_statistics.to_dict(),
        }

    def get_all_resources(self) -> List[MergedResource]:
        """Get all confirmed resources (merged + OCR-only)."""
        all_resources = list(self.merged_resources)
        
        # Convert OCR-only to MergedResource
        for ocr_res in self.ocr_only_resources:
            all_resources.append(MergedResource(
                service_type=ocr_res.get("inferred_service", "Unknown"),
                instance_name=ocr_res.get("instance_name"),
                position=ocr_res.get("position"),
                confidence=ocr_res.get("confidence", 0.5),
                detection_sources=["ocr"],
                needs_clarification=ocr_res.get("needs_clarification", False),
            ))
        
        return all_resources


# =============================================================================
# SERVICE NAME NORMALIZATION FOR DEDUPLICATION
# =============================================================================
# 
# NO STATIC MAPPINGS - Service name equivalence is determined by:
# 1. Simple text normalization (lowercase, strip prefixes)
# 2. The agent's reasoning using Bing grounding for lookups
# 3. Position proximity (same location = same resource)
#
# The DetectionMergerAgent instructions guide the LLM to recognize
# equivalent service names dynamically using its knowledge + tools.
# =============================================================================


def normalize_service_name_simple(name: str) -> str:
    """
    Simple text normalization for comparison purposes.
    
    NO STATIC MAPPINGS - just normalizes text format:
    - Lowercase
    - Strip whitespace
    - Remove common prefixes for comparison
    
    The agent handles semantic equivalence via reasoning + tools.
    """
    if not name:
        return ""
    normalized = name.lower().strip()
    # Remove Azure/Microsoft prefix for comparison (but don't map to specific services)
    for prefix in ["azure ", "microsoft ", "ms "]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return normalized


def are_same_service_by_position(pos1: tuple, pos2: tuple, threshold: float = 0.14) -> bool:
    """
    Check if two positions are close enough to be the same resource.
    
    Primary deduplication signal - position proximity.
    If two detections are at the same position, they're the same resource
    regardless of name variations.
    """
    import math
    distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    return distance < threshold


# =============================================================================
# DETECTION MERGER AGENT
# =============================================================================

class DetectionMergerAgent:
    """
    Detection Merger Agent for combining icon and OCR detections.
    
    Uses Azure AI Agents to intelligently merge detections:
    - Spatial deduplication based on position proximity
    - Information enrichment from both sources
    - Conflict resolution when sources disagree
    - Attempts to resolve uncertain detections
    """
    
    # Proximity thresholds (as percentage of diagram)
    SAME_RESOURCE_THRESHOLD = 0.10  # 10% x and y distance
    TEXT_LABEL_THRESHOLD = 0.15     # 15% for text near icon
    
    def __init__(self):
        """Initialize the Detection Merger Agent."""
        self.settings = get_settings()
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
        self._tool_config = None
    
    def _build_instructions(self) -> str:
        """Build agent instructions from YAML configuration."""
        base_instructions = get_agent_instructions("detection_merger_agent")
        tool_instructions = get_tool_instructions()
        return f"{base_instructions}\n\n{tool_instructions}"
    
    async def __aenter__(self) -> "DetectionMergerAgent":
        """Initialize the agent with Bing Grounding and MCP tools."""
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
        
        self._client = AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=credential,
        )
        
        instructions = self._build_instructions()
        
        # Configure tools: Bing Grounding > MS Learn MCP
        # MS Learn MCP: Official documentation
        # Bing Grounding: Service disambiguation and verification
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"],
        )
        
        # Create the agent with tools for dynamic service name verification
        agent = self._client.create_agent(
            model=self.settings.model_deployment_name,
            name="DetectionMergerAgent",
            instructions=instructions,
            tools=self._tool_config.tools,
            tool_resources=self._tool_config.tool_resources,
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
    
    async def merge_detections(
        self,
        vision_result: DetectionResult,
        ocr_result: OCRDetectionResult,
    ) -> MergeResult:
        """
        Merge icon detections with OCR detections.
        
        Uses deterministic position-based clustering instead of LLM for consistency.
        
        Args:
            vision_result: Result from VisionAgent (icon-based detections)
            ocr_result: Result from OCRDetectionAgent (text-based detections)
            
        Returns:
            MergeResult with deduplicated, enriched resources
        """
        import logging
        logger = logging.getLogger(__name__)
        
        vision_count = len(vision_result.icons)
        ocr_count = len(ocr_result.detected_icons) if ocr_result.detected_icons else 0
        logger.info(f"🔀 MERGE INPUT: Vision={vision_count} icons, OCR={ocr_count} detections")
        logger.info(f"Using deterministic position-based merge (not LLM) for consistency")
        
        # Use deterministic fallback merge instead of unreliable LLM
        result = self._fallback_merge(vision_result, ocr_result)
        
        logger.info(f"🔀 MERGE OUTPUT: merged_resources={len(result.merged_resources)}, ocr_only={len(result.ocr_only_resources)}")
        logger.info(f"Total via get_all_resources()={len(result.get_all_resources())}")
        
        return result
    
    def _icon_result_to_json(self, result: DetectionResult) -> str:
        """Convert icon detection result to JSON string."""
        icons = []
        for icon in result.icons:
            icons.append({
                "service_type": icon.type,
                "instance_name": icon.name,
                "position": {
                    "x_percent": icon.position.x * 100 if icon.position else 0,
                    "y_percent": icon.position.y * 100 if icon.position else 0,
                },
                "confidence": icon.confidence,
                "arm_resource_type": icon.arm_resource_type,
                "needs_clarification": icon.needs_clarification,
                "clarification_options": icon.clarification_options,
            })
        
        return json.dumps({"icon_detections": icons}, indent=2)
    
    def _ocr_result_to_json(self, result: OCRDetectionResult) -> str:
        """Convert OCR detection result to JSON string (compatible format)."""
        # OCR now uses same format as vision - detected_icons
        icons = []
        for icon in result.detected_icons:
            icons.append({
                "service_type": icon.service_type,
                "instance_name": icon.instance_name,
                "position": icon.position,
                "confidence": icon.confidence,
                "arm_resource_type": icon.arm_resource_type,
                "needs_clarification": icon.needs_clarification,
                "clarification_options": icon.clarification_options,
                "source": icon.source,
                "ocr_details": icon.ocr_details,
            })
        
        return json.dumps({
            "diagram_metadata": result.diagram_metadata.to_dict() if result.diagram_metadata else {},
            "detected_icons": icons,
            "detected_text": result.detected_text,
            "vnet_boundaries": result.vnet_boundaries,
            "data_flows": result.data_flows,
        }, indent=2)
    
    def _build_merge_prompt(self, icon_json: str, ocr_json: str) -> str:
        """Build the merge prompt from template."""
        prompt_template = get_user_prompt_template("detection_merger_agent")
        response_schema = get_response_schema_json("merged_detections")
        
        prompt = prompt_template.format(
            icon_detections=icon_json,
            ocr_detections=ocr_json,
            response_schema=response_schema,
        )
        
        return prompt
    
    def _parse_response(
        self,
        response_text: str,
        icon_result: DetectionResult,
        ocr_result: OCRDetectionResult,
    ) -> MergeResult:
        """Parse the agent's JSON response into MergeResult."""
        # Extract JSON
        json_str = response_text.strip()
        
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
            import re
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    # Fallback to basic merge
                    return self._fallback_merge(icon_result, ocr_result)
            else:
                return self._fallback_merge(icon_result, ocr_result)
        
        # Parse merged resources
        merged_resources = []
        for item in data.get("merged_resources", []):
            merged_resources.append(MergedResource(
                service_type=item.get("service_type", "Unknown"),
                instance_name=item.get("instance_name"),
                position=item.get("position"),
                confidence=item.get("confidence", 0.5),
                arm_resource_type=item.get("arm_resource_type"),
                detection_sources=item.get("detection_sources", []),
                merge_notes=item.get("merge_notes"),
                needs_clarification=item.get("needs_clarification", False),
                naming_constraints=item.get("naming_constraints"),
            ))
        
        # Parse resolution attempts
        resolution_attempts = []
        for item in data.get("resolution_attempts", []):
            resolution_attempts.append(ResolutionAttempt(
                original_detection=item.get("original_detection", ""),
                resolution_method=item.get("resolution_method", ""),
                resolved_to=item.get("resolved_to"),
                confidence=item.get("confidence", 0.0),
            ))
        
        # Parse statistics
        stats_data = data.get("merge_statistics", {})
        ocr_icons = ocr_result.detected_icons if ocr_result.detected_icons else []
        merge_statistics = MergeStatistics(
            total_icon_detections=stats_data.get("total_icon_detections", len(icon_result.icons)),
            total_ocr_detections=stats_data.get("total_ocr_detections", len(ocr_icons)),
            merged_duplicates=stats_data.get("merged_duplicates", 0),
            ocr_only_additions=stats_data.get("ocr_only_additions", 0),
            icon_only_kept=stats_data.get("icon_only_kept", 0),
            resolved_clarifications=stats_data.get("resolved_clarifications", 0),
            remaining_clarifications=stats_data.get("remaining_clarifications", 0),
        )
        
        return MergeResult(
            merged_resources=merged_resources,
            ocr_only_resources=data.get("ocr_only_resources", []),
            unresolved_detections=data.get("unresolved_detections", []),
            resolution_attempts=resolution_attempts,
            merge_statistics=merge_statistics,
        )
    
    def _fallback_merge(
        self,
        icon_result: DetectionResult,
        ocr_result: OCRDetectionResult,
    ) -> MergeResult:
        """
        Fallback merge using simple proximity matching with deduplication.
        Used when agent response parsing fails.
        
        NOTE: Both icon_result and ocr_result now use compatible formats
        with detected_icons arrays using x/y positions (0.0-1.0 scale).
        
        DEDUPLICATION STRATEGY:
        1. Group all detections by position proximity
        2. Within each position cluster, merge into single resource
        3. Use service name normalization to identify duplicates
        """
        merged = []
        used_ocr_indices = set()
        used_icon_indices = set()
        
        # Get OCR detected_icons (now compatible format)
        ocr_icons = ocr_result.detected_icons if ocr_result.detected_icons else []
        
        # Build position clusters - group detections at similar positions
        position_clusters = []  # List of {"position": (x, y), "icons": [...], "ocrs": [...]}
        
        def get_position(item, is_icon=True):
            """Extract normalized position from detection."""
            if is_icon:
                return (item.position.x if item.position else 0, 
                        item.position.y if item.position else 0)
            else:
                pos = item.position if hasattr(item, 'position') else item.get("position", {})
                if isinstance(pos, dict):
                    return (pos.get("x", 0), pos.get("y", 0))
                return (pos.x if hasattr(pos, 'x') else 0, pos.y if hasattr(pos, 'y') else 0)
        
        def distance(p1, p2):
            return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        
        def find_or_create_cluster(pos):
            """Find existing cluster near position, or create new one."""
            for cluster in position_clusters:
                if distance(cluster["position"], pos) < 0.14:  # ~10% diagonal
                    return cluster
            # Create new cluster
            new_cluster = {"position": pos, "icons": [], "ocrs": []}
            position_clusters.append(new_cluster)
            return new_cluster
        
        # Add all icon detections to clusters
        for idx, icon in enumerate(icon_result.icons):
            pos = get_position(icon, is_icon=True)
            # DEBUG: Log first few icon positions
            if idx < 5:
                print(f"🔍 Icon {idx}: type={icon.type}, position object={icon.position}, extracted pos={pos}")
            cluster = find_or_create_cluster(pos)
            cluster["icons"].append((idx, icon))
        
        # Add all OCR detections to clusters
        for idx, ocr in enumerate(ocr_icons):
            pos = get_position(ocr, is_icon=False)
            cluster = find_or_create_cluster(pos)
            cluster["ocrs"].append((idx, ocr))
        
        # DEBUG: Log clustering results
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"📊 CLUSTERING: Created {len(position_clusters)} clusters from {len(icon_result.icons)} icons + {len(ocr_icons)} OCR")
        for i, cluster in enumerate(position_clusters):
            logger.info(f"  Cluster {i+1}: {len(cluster['icons'])} icons + {len(cluster['ocrs'])} OCR at position {cluster['position']}")
        
        # Process each cluster - merge all detections in cluster into ONE resource
        for cluster in position_clusters:
            icons_in_cluster = cluster["icons"]
            ocrs_in_cluster = cluster["ocrs"]
            
            if not icons_in_cluster and not ocrs_in_cluster:
                continue
            
            # DEBUG: Log cluster composition
            if len(icons_in_cluster) > 1:
                icon_types = [icon.type for _, icon in icons_in_cluster]
                print(f"⚠️  CLUSTER MERGING {len(icons_in_cluster)} ICONS AT POSITION {cluster['position']}: {icon_types}")
            
            # Determine best service type (prefer icon, use normalization for matching)
            service_type = None
            instance_name = None
            arm_type = None
            confidence = 0.0
            sources = []
            needs_clarification = True
            
            # Process icon detections in cluster
            for idx, icon in icons_in_cluster:
                used_icon_indices.add(idx)
                if not service_type or icon.confidence > confidence:
                    service_type = icon.type
                    confidence = icon.confidence
                    arm_type = icon.arm_resource_type or arm_type
                if not instance_name:
                    instance_name = icon.name
                needs_clarification = needs_clarification and icon.needs_clarification
                if "icon" not in sources:
                    sources.append("icon")
            
            # Process OCR detections in cluster
            for idx, ocr in ocrs_in_cluster:
                used_ocr_indices.add(idx)
                ocr_service = ocr.service_type if hasattr(ocr, 'service_type') else ocr.get("service_type", "")
                ocr_instance = ocr.instance_name if hasattr(ocr, 'instance_name') else ocr.get("instance_name", "")
                ocr_arm = ocr.arm_resource_type if hasattr(ocr, 'arm_resource_type') else ocr.get("arm_resource_type")
                ocr_conf = ocr.confidence if hasattr(ocr, 'confidence') else ocr.get("confidence", 0.5)
                ocr_needs_clar = ocr.needs_clarification if hasattr(ocr, 'needs_clarification') else ocr.get("needs_clarification", False)
                
                # Use OCR service type if no icon or if it's more specific
                if not service_type and ocr_service:
                    service_type = ocr_service
                    confidence = ocr_conf
                elif ocr_service:
                    # Compare using simple normalization - position proximity is the primary signal
                    # If they're in the same cluster, they're the same resource
                    normalized_current = normalize_service_name_simple(service_type)
                    normalized_ocr = normalize_service_name_simple(ocr_service)
                    if normalized_current == normalized_ocr:
                        # Same service - merge confidence
                        confidence = max(confidence, ocr_conf)
                    # If different service names at same position, prefer icon detection
                    # (icon visual identification is usually more reliable)
                
                # Prefer OCR for instance name (more accurate text)
                if ocr_instance:
                    instance_name = ocr_instance
                
                arm_type = arm_type or ocr_arm
                needs_clarification = needs_clarification and ocr_needs_clar
                if "ocr" not in sources:
                    sources.append("ocr")
            
            if service_type:
                merged.append(MergedResource(
                    service_type=service_type,
                    instance_name=instance_name,
                    position={"x": cluster["position"][0], "y": cluster["position"][1]},
                    confidence=confidence,
                    arm_resource_type=arm_type,
                    detection_sources=sources,
                    merge_notes=f"Cluster merge: {len(icons_in_cluster)} icons + {len(ocrs_in_cluster)} OCR",
                    needs_clarification=needs_clarification,
                ))
        
        # Calculate statistics
        ocr_icons = ocr_result.detected_icons if ocr_result.detected_icons else []
        merged_count = sum(1 for c in position_clusters if c["icons"] and c["ocrs"])
        icon_only_count = sum(1 for c in position_clusters if c["icons"] and not c["ocrs"])
        ocr_only_count = sum(1 for c in position_clusters if c["ocrs"] and not c["icons"])
        
        return MergeResult(
            merged_resources=merged,
            ocr_only_resources=[],  # All OCR detections now merged via clusters
            merge_statistics=MergeStatistics(
                total_icon_detections=len(icon_result.icons),
                total_ocr_detections=len(ocr_icons),
                merged_duplicates=merged_count,
                ocr_only_additions=ocr_only_count,
                icon_only_kept=icon_only_count,
            ),
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def merge_icon_and_ocr_detections(
    icon_result: DetectionResult,
    ocr_result: OCRDetectionResult,
) -> MergeResult:
    """
    Merge icon and OCR detection results.
    
    Args:
        icon_result: Result from VisionAgent
        ocr_result: Result from OCRDetectionAgent
        
    Returns:
        MergeResult with unified, deduplicated resources
    """
    async with DetectionMergerAgent() as agent:
        return await agent.merge_detections(icon_result, ocr_result)


async def run_parallel_detection(image_path: str) -> MergeResult:
    """
    Run VisionAgent and OCRDetectionAgent in parallel, then merge results.
    
    This is the recommended way to analyze diagrams for best accuracy.
    
    Args:
        image_path: Path to the architecture diagram
        
    Returns:
        MergeResult with all detected resources
    """
    from synthforge.agents.vision_agent import VisionAgent
    from synthforge.agents.ocr_detection_agent import OCRDetectionAgent
    
    # Run both agents in parallel
    async def run_vision():
        async with VisionAgent() as agent:
            return await agent.analyze_image(image_path)
    
    async def run_ocr():
        async with OCRDetectionAgent() as agent:
            return await agent.analyze_image(image_path)
    
    icon_result, ocr_result = await asyncio.gather(run_vision(), run_ocr())
    
    # Merge the results
    async with DetectionMergerAgent() as merger:
        return await merger.merge_detections(icon_result, ocr_result)

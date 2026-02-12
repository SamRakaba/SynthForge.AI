"""
Workflow orchestrator for SynthForge.AI.

Orchestrates the multi-agent pipeline:
  Vision → Filter → Interactive → Network Flow → Security
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Awaitable, AsyncIterator, Any, List
from datetime import datetime

from synthforge.config import get_settings, Settings
from synthforge.models import (
    DetectionResult,
    FilterResult,
    ClarificationResponse,
    SecurityRecommendation,
    AzureResource,
    ArchitectureAnalysis,
    DetectedIcon,
    DataFlow,
    Position,
    SecurityConfig,
    ManagedIdentityConfig,
    PrivateEndpointConfig,
    VNetIntegrationConfig,
    RBACAssignment,
    RBACScope,
    ManagedIdentityType,
    NetworkAccessType,
)
from synthforge.agents.vision_agent import VisionAgent
from synthforge.agents.filter_agent import FilterAgent
from synthforge.agents.security_agent import SecurityAgent
from synthforge.agents.interactive_agent import InteractiveAgent, UserReviewResult
from synthforge.agents.network_flow_agent import NetworkFlowAgent, NetworkFlowResult
from synthforge.agents.description_agent import DescriptionAgent, ArchitectureDescription


# =============================================================================
# CUSTOM EXCEPTIONS FOR GRACEFUL ERROR HANDLING
# =============================================================================

class SynthForgeError(Exception):
    """Base exception for SynthForge.AI errors."""
    pass


class AzureServiceError(SynthForgeError):
    """Error communicating with Azure AI Foundry services."""
    
    def __init__(self, message: str, stage: str = None, original_error: Exception = None):
        self.stage = stage
        self.original_error = original_error
        super().__init__(message)


class TimeoutError(AzureServiceError):
    """Azure API request timed out."""
    pass


class AuthenticationError(SynthForgeError):
    """Azure authentication failed."""
    pass


def _classify_azure_error(error: Exception, stage: str = None) -> SynthForgeError:
    """
    Classify an Azure SDK error into a user-friendly exception.
    
    Args:
        error: The original exception
        stage: The workflow stage where the error occurred
        
    Returns:
        A SynthForgeError subclass with a user-friendly message
    """
    error_str = str(error).lower()
    
    # Check for timeout errors
    if "timed out" in error_str or "timeout" in error_str:
        return TimeoutError(
            f"Azure AI Foundry request timed out during {stage or 'processing'}. "
            "This is usually temporary - please try again in a few moments. "
            "If the issue persists, check Azure service status at https://status.azure.com/",
            stage=stage,
            original_error=error,
        )
    
    # Check for authentication errors
    if "authentication" in error_str or "credential" in error_str or "unauthorized" in error_str:
        return AuthenticationError(
            "Azure authentication failed. Please ensure you're logged in:\n"
            "  az login\n"
            "or\n"
            "  azd auth login --scope https://cognitiveservices.azure.com/.default"
        )
    
    # Check for quota/rate limiting
    if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
        return AzureServiceError(
            f"Azure AI Foundry rate limit exceeded during {stage or 'processing'}. "
            "Please wait a moment and try again.",
            stage=stage,
            original_error=error,
        )
    
    # Check for model deployment issues
    if "deployment" in error_str and ("not found" in error_str or "does not exist" in error_str):
        return AzureServiceError(
            f"Model deployment not found. Please check that MODEL_DEPLOYMENT_NAME and "
            "VISION_MODEL_DEPLOYMENT_NAME are correctly configured in your .env file.",
            stage=stage,
            original_error=error,
        )
    
    # Check for JSON parsing errors (often from empty/timeout responses)
    if "json" in error_str and ("invalid" in error_str or "expecting value" in error_str):
        return AzureServiceError(
            f"Received invalid response from Azure AI Foundry during {stage or 'processing'}. "
            "This often indicates a timeout or service issue. Please try again.",
            stage=stage,
            original_error=error,
        )
    
    # Generic Azure service error
    return AzureServiceError(
        f"Azure service error during {stage or 'processing'}: {str(error)}",
        stage=stage,
        original_error=error,
    )


@dataclass
class WorkflowProgress:
    """Progress update for workflow execution."""
    stage: str
    message: str
    progress: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[dict] = None


@dataclass
class WorkflowResult:
    """Result of the complete workflow execution."""
    success: bool
    analysis: Optional[ArchitectureAnalysis]
    detection_result: Optional[DetectionResult] = None
    filter_result: Optional[FilterResult] = None
    clarifications: Optional[list[ClarificationResponse]] = None
    network_flow_result: Optional[NetworkFlowResult] = None
    security_recommendations: Optional[list[SecurityRecommendation]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class ArchitectureWorkflow:
    """
    Orchestrates the complete architecture analysis workflow.
    
    Pipeline stages:
    1. Vision Agent - Analyze diagram image, detect icons and structure
    2. Filter Agent - Classify resources using first-principles reasoning
    3. Interactive Agent - User review and clarification of detections
    4. Network Flow Agent - Analyze network flows, VNets, and connections
    5. Security Agent - Generate RBAC and security recommendations
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        input_handler: Optional[Callable[[str, list[str]], Awaitable[str]]] = None,
        interactive: bool = True,
        include_security: bool = True,
    ):
        """
        Initialize the workflow.
        
        Args:
            settings: Optional settings override
            input_handler: Async callback for user input (for interactive agent)
            interactive: Whether to use interactive agent for clarifications
            include_security: Whether to include security recommendations
        """
        self.settings = settings or get_settings()
        self.input_handler = input_handler
        self.interactive = interactive
        self.include_security = include_security
        
        self._progress_callback: Optional[Callable[[WorkflowProgress], Awaitable[None]]] = None
    
    def on_progress(
        self, 
        callback: Callable[[WorkflowProgress], Awaitable[None]],
    ) -> "ArchitectureWorkflow":
        """Register a progress callback."""
        self._progress_callback = callback
        return self
    
    async def _emit_progress(
        self, 
        stage: str, 
        message: str, 
        progress: float,
        data: Optional[dict] = None,
    ):
        """Emit a progress update."""
        if self._progress_callback:
            update = WorkflowProgress(
                stage=stage,
                message=message,
                progress=progress,
                data=data,
            )
            await self._progress_callback(update)
    
    def _log_resource_state(self, stage_name: str, resources: list):
        """Log resource state for debugging - shows service_type and instance_name."""
        logger = logging.getLogger(__name__)
        logger.info(f"\n{'-'*60}")
        logger.info(f"STAGE: {stage_name} - {len(resources)} resources")
        logger.info(f"{'-'*60}")
        for i, r in enumerate(resources, 1):
            service_type = getattr(r, 'type', getattr(r, 'service_type', 'UNKNOWN'))
            instance_name = getattr(r, 'name', getattr(r, 'instance_name', None))
            confidence = getattr(r, 'confidence', 'N/A')
            logger.info(f"  {i}. {service_type}" + (f" ({instance_name})" if instance_name else "") + f" - conf: {confidence}")
        logger.info(f"{'-'*60}\n")
    
    async def analyze(
        self, 
        image_path: str | Path,
    ) -> WorkflowResult:
        """
        Run the complete analysis workflow.
        
        Args:
            image_path: Path to the architecture diagram image
            
        Returns:
            WorkflowResult with complete analysis
        """
        start_time = asyncio.get_event_loop().time()
        logger = logging.getLogger(__name__)
        
        try:
            # Stage 0: Run Description Agent first for comprehensive component list
            # This provides context hints that improve icon detection
            await self._emit_progress(
                "description",
                "Stage 0: Describing architecture (provides context for detection)...",
                0.02,
            )
            
            description = None
            description_context = None
            try:
                async with DescriptionAgent() as desc_agent:
                    description = await desc_agent.describe_architecture(str(image_path))
                    description_context = description.to_context_hints()
                    component_count = len(description.get_all_components())
                    logger.info(f"Description phase identified {component_count} components")
                    
                    await self._emit_progress(
                        "description",
                        f"Stage 0: {component_count} components identified",
                        0.05,
                        {"component_count": component_count},
                    )
            except Exception as e:
                logger.warning(f"Description phase failed (continuing without context): {e}")
                # Don't raise - description is supplementary, vision can work alone
            
            # Stage 1: Run Vision Agent to detect Azure icons
            await self._emit_progress(
                "vision", 
                "Stage 1: Detecting Azure icons...", 
                0.08,
            )
            
            # Run Vision agent only - Vision now has description context for better detection
            vision_result = await self._run_vision_analysis(image_path, description_context=description_context)
            
            # Handle any exceptions
            if isinstance(vision_result, Exception):
                logger.error(f"Vision analysis failed: {vision_result}")
                raise vision_result
            
            vision_count = len(vision_result.icons) if vision_result else 0
            
            await self._emit_progress(
                "vision",
                f"Stage 1: {vision_count} icons detected",
                0.18,
                {"vision_count": vision_count},
            )
            
            # Use Vision detections directly (no OCR or merge)
            detection_result = vision_result
            
            # Check for resources in description that weren't detected (informational only)
            if description is not None and description_context and detection_result and detection_result.icons:
                self._check_missing_resources(
                    description=description,
                    detected_icons=detection_result.icons,
                )
            
            if not detection_result or not detection_result.icons:
                return WorkflowResult(
                    success=False,
                    analysis=None,
                    detection_result=detection_result,
                    error="No icons detected in the diagram",
                    duration_seconds=asyncio.get_event_loop().time() - start_time,
                )
            
            await self._emit_progress(
                "vision_complete",
                f"Stage 1: {len(detection_result.icons)} resources detected",
                0.25,
                {"icon_count": len(detection_result.icons)},
            )
            
            # Stage 2: Filter Resources
            await self._emit_progress(
                "filter",
                "Stage 2: Classifying detected resources...",
                0.30,
            )
            
            filter_result = await self._run_filter(detection_result, description=description)
            
            # Log network isolation patterns if any (these become recommendations, not resources)
            network_isolation_count = len(filter_result.network_isolation) if filter_result.network_isolation else 0
            if network_isolation_count > 0:
                logger.info(f"Identified {network_isolation_count} network isolation patterns (will become recommendations)")
            
            await self._emit_progress(
                "filter",
                f"Stage 2: {len(filter_result.architectural)} Azure resources, "
                f"{len(filter_result.needs_clarification)} need clarification"
                + (f", {network_isolation_count} network patterns" if network_isolation_count > 0 else ""),
                0.45,
                {
                    "architectural_count": len(filter_result.architectural),
                    "clarification_count": len(filter_result.needs_clarification),
                    "network_isolation_count": network_isolation_count,
                },
            )
            
            # Log classified resources for debugging
            logger.info(f"Filtered {len(filter_result.architectural)} architectural from {len(detection_result.icons)} total")
            self._log_resource_state("AFTER CLASSIFICATION (Stage 2) - Architectural", filter_result.architectural)
            if filter_result.non_architectural:
                self._log_resource_state("AFTER CLASSIFICATION (Stage 2) - Non-Architectural", filter_result.non_architectural)
            
            # Stage 3: Interactive Review & Clarification (if enabled)
            clarifications = []
            final_resources = filter_result.architectural.copy()
            
            if self.interactive:
                # First: Allow user to review ALL detected resources
                await self._emit_progress(
                    "interactive",
                    "Stage 3: User review of detected resources...",
                    0.50,
                )
                
                # Combine architectural and needs_clarification for full review
                # NOTE: network_isolation patterns are NOT included - they become recommendations
                all_detected = filter_result.architectural + filter_result.needs_clarification
                
                review_result = await self._run_user_review(all_detected, description=description)
                
                if review_result:
                    # Use the reviewed resources instead
                    final_resources = review_result.get_final_resources()
                    
                    await self._emit_progress(
                        "interactive",
                        f"Stage 3: {len(review_result.confirmed)} confirmed, "
                        f"{len(review_result.corrected)} corrected, "
                        f"{len(review_result.added)} added, "
                        f"{len(review_result.removed)} removed",
                        0.55,
                    )
                
                # Second: Handle any remaining clarifications needed
                # Filter out resources already handled by user review
                remaining_clarifications = []
                if review_result:
                    # Match resources by attributes (type, position) not id()
                    # because objects may be copied/recreated
                    def resource_key(r: DetectedIcon) -> tuple:
                        """Create unique key for resource matching."""
                        return (r.type, r.position.x, r.position.y)
                    
                    handled_keys = {resource_key(orig) for orig, _ in review_result.corrected}
                    handled_keys.update(resource_key(r) for r in review_result.removed)
                    
                    # Only clarify resources NOT already handled
                    remaining_clarifications = [
                        r for r in filter_result.needs_clarification
                        if resource_key(r) not in handled_keys
                    ]
                else:
                    remaining_clarifications = filter_result.needs_clarification
                
                if remaining_clarifications:
                    await self._emit_progress(
                        "interactive",
                        f"Clarifying {len(remaining_clarifications)} uncertain items...",
                        0.58,
                    )
                    
                    # Create a temporary FilterResult with only remaining items
                    from synthforge.models import FilterResult
                    temp_filter_result = FilterResult(
                        architectural=filter_result.architectural,
                        network_isolation=filter_result.network_isolation,
                        needs_clarification=remaining_clarifications,
                    )
                    
                    clarifications = await self._run_interactive(temp_filter_result)
                    
                    await self._emit_progress(
                        "interactive",
                        f"Received {len(clarifications)} clarifications",
                        0.60,
                        {"clarification_count": len(clarifications)},
                    )
                    
                    # Merge any additional clarified resources
                    final_resources = self._merge_clarifications(
                        final_resources,
                        clarifications,
                    )
            else:
                # Non-interactive mode: just use architectural resources
                final_resources = filter_result.architectural.copy()
            
            # Stage 4: Network Flow Analysis
            network_flow_result = None
            await self._emit_progress(
                "network_flows",
                "Stage 4: Analyzing network flows and connections...",
                0.62,
            )
            
            network_flow_result = await self._run_network_flow_analysis(
                image_path,
                final_resources,
            )
            
            # Merge network flow results into detection_result
            if network_flow_result:
                # Add detected flows
                if network_flow_result.flows:
                    detection_result.data_flows.extend(network_flow_result.flows)
                
                # Add VNet boundaries
                if network_flow_result.vnets:
                    detection_result.vnet_boundaries.extend(network_flow_result.vnets)
                
                await self._emit_progress(
                    "network_flows",
                    f"Stage 4: {len(network_flow_result.flows)} network flows, "
                    f"{len(network_flow_result.vnets)} VNet boundaries detected",
                    0.68,
                    {
                        "flow_count": len(network_flow_result.flows),
                        "vnet_count": len(network_flow_result.vnets),
                    },
                )
                
                # Infer additional flows based on Azure patterns
                inferred_flows = await self._run_flow_inference(
                    final_resources,
                    network_flow_result.flows,
                )
                
                if inferred_flows:
                    detection_result.data_flows.extend(inferred_flows)
                    await self._emit_progress(
                        "network_flows",
                        f"Inferred {len(inferred_flows)} additional flows from patterns",
                        0.69,
                    )
            
            # Stage 5: Security Recommendations (if enabled)
            security_recommendations = []
            if self.include_security and final_resources:
                await self._emit_progress(
                    "security",
                    "Stage 5: Generating security recommendations...",
                    0.70,
                )
                
                # Collect all flows for RBAC inference
                all_flows = list(detection_result.data_flows) if detection_result.data_flows else []
                
                security_recommendations = await self._run_security(
                    final_resources,
                    all_flows,
                )
                
                await self._emit_progress(
                    "security",
                    f"Stage 5: {len(security_recommendations)} security recommendations generated",
                    0.85,
                    {"recommendation_count": len(security_recommendations)},
                )
            
            # Stage 6: Build Final Analysis
            await self._emit_progress(
                "finalize",
                "Stage 6: Building final analysis...",
                0.90,
            )
            
            analysis = self._build_analysis(
                detection_result=detection_result,
                filter_result=filter_result,
                clarifications=clarifications,
                final_resources=final_resources,
                security_recommendations=security_recommendations,
                network_flow_result=network_flow_result,
                image_path=str(image_path),
            )
            
            await self._emit_progress(
                "complete",
                "Analysis complete!",
                1.0,
            )
            
            return WorkflowResult(
                success=True,
                analysis=analysis,
                detection_result=detection_result,
                filter_result=filter_result,
                clarifications=clarifications,
                network_flow_result=network_flow_result,
                security_recommendations=security_recommendations,
                duration_seconds=asyncio.get_event_loop().time() - start_time,
            )
            
        except Exception as e:
            await self._emit_progress(
                "error",
                f"Error: {str(e)}",
                0.0,
            )
            
            return WorkflowResult(
                success=False,
                analysis=None,
                error=str(e),
                duration_seconds=asyncio.get_event_loop().time() - start_time,
            )
    
    async def _run_vision_analysis(
        self, 
        image_path: str | Path,
        description_context: Optional[str] = None,
    ) -> DetectionResult:
        """Run vision analysis stage with optional description context."""
        logger = logging.getLogger(__name__)
        
        try:
            async with VisionAgent() as agent:
                result = await agent.analyze_image(
                    image_path,
                    description_context=description_context,
                )
                
                # Mark low-confidence detections for user clarification
                # Agent orchestrates icon catalog lookup - if not found, ask user
                clarification_threshold = self.settings.clarification_threshold
                
                for icon in result.icons:
                    # If Vision Agent marked needs_clarification or confidence is low
                    if (hasattr(icon, 'needs_clarification') and icon.needs_clarification) or \
                       icon.confidence < clarification_threshold:
                        icon.needs_clarification = True
                
                return result
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            raise _classify_azure_error(e, stage="Icon Detection")
    
    def _check_missing_resources(
        self,
        description: Any,
        detected_icons: List[DetectedIcon],
    ) -> None:
        """
        Check if description identified resources that weren't detected by vision.
        Log any missing resources for user awareness.
        """
        logger = logging.getLogger(__name__)
        
        if not description:
            return
        
        # Get all components from description
        all_description_components = description.get_all_components()
        if not all_description_components:
            return
        
        # Get all detected service types (normalize for comparison)
        detected_types = set()
        for icon in detected_icons:
            # Normalize: lowercase, remove "azure" prefix
            normalized = icon.type.lower().replace("azure ", "").replace("microsoft ", "").strip()
            detected_types.add(normalized)
        
        # Check for missing resources
        missing = []
        for comp in all_description_components:
            # Normalize component name
            normalized_comp = comp.lower().replace("azure ", "").replace("microsoft ", "").strip()
            
            # Check if any detected type contains this component or vice versa
            found = False
            for detected in detected_types:
                # Fuzzy matching: check substring match in either direction
                if normalized_comp in detected or detected in normalized_comp:
                    found = True
                    break
            
            if not found:
                missing.append(comp)
        
        if missing:
            logger.warning("=" * 80)
            logger.warning("RESOURCES IN DESCRIPTION BUT NOT DETECTED:")
            logger.warning(f"Description agent identified {len(all_description_components)} components")
            logger.warning(f"Vision detected {len(detected_icons)} resources")
            logger.warning(f"Missing {len(missing)} resources:")
            for i, resource in enumerate(missing, 1):
                logger.warning(f"  {i}. {resource}")
            logger.warning("")
            logger.warning("Possible reasons:")
            logger.warning("  - Resource is a network boundary (VNet, subnet) not an icon")
            logger.warning("  - Resource is external/on-premises (users, internet)")
            logger.warning("  - Supporting service without distinct icon")
            logger.warning("  - Vision agent unable to identify specific icon")
            logger.warning("  - Description agent over-identified components")
            logger.warning("=" * 80)
        else:
            logger.info(f"✓ All {len(all_description_components)} description components detected by vision/OCR")
        
    async def _run_filter(self, detection_result: DetectionResult, description: Optional[Any] = None) -> FilterResult:
        """Run filter stage with optional description context for enrichment."""
        logger = logging.getLogger(__name__)
        
        try:
            async with FilterAgent() as agent:
                return await agent.filter_resources(detection_result, description_context=description)
        except Exception as e:
            logger.error(f"Filter stage failed: {e}")
            raise _classify_azure_error(e, stage="Resource Classification")
    
    async def _run_interactive(self, filter_result: FilterResult) -> list[ClarificationResponse]:
        """Run interactive clarification stage."""
        logger = logging.getLogger(__name__)
        
        try:
            async with InteractiveAgent(input_handler=self.input_handler) as agent:
                return await agent.clarify_resources(filter_result)
        except Exception as e:
            logger.error(f"Interactive stage failed: {e}")
            raise _classify_azure_error(e, stage="Design Review")
    
    async def _run_user_review(
        self,
        detected_resources: list[DetectedIcon],
        description: Optional[Any] = None,
    ):
        """
        Run user review of all detected resources.
        
        This stage allows users to:
        1. Review all detected resources
        2. Correct misidentified resources
        3. Add missing resources (including suggestions from description)
        4. Remove incorrect detections
        
        Args:
            detected_resources: All resources detected by Vision/Filter agents
            description: Optional description context for suggesting missing resources
            
        Returns:
            UserReviewResult with user's modifications, or None if no changes
        """
        from synthforge.agents.interactive_agent import UserReviewResult
        logger = logging.getLogger(__name__)
        
        try:
            async with InteractiveAgent(input_handler=self.input_handler, description_context=description) as agent:
                return await agent.review_all_resources(detected_resources)
        except Exception as e:
            logger.error(f"User review stage failed: {e}")
            raise _classify_azure_error(e, stage="Design Review")
    
    async def _run_network_flow_analysis(
        self,
        image_path: str | Path,
        resources: list[DetectedIcon],
    ) -> NetworkFlowResult:
        """
        Run network flow analysis stage.
        
        Analyzes the architecture diagram to detect:
        - Network connections between resources
        - Data flows and directions
        - VNet boundaries and subnets
        - VNet integration requirements per service
        
        Args:
            image_path: Path to the architecture diagram
            resources: List of detected resources
            
        Returns:
            NetworkFlowResult with flows, vnets, and configs
        """
        logger = logging.getLogger(__name__)
        
        try:
            async with NetworkFlowAgent() as agent:
                return await agent.analyze_flows(image_path, resources)
        except Exception as e:
            logger.error(f"Network flow analysis failed: {e}")
            raise _classify_azure_error(e, stage="Network Topology")
    
    async def _run_flow_inference(
        self,
        resources: list[DetectedIcon],
        existing_flows: list[DataFlow],
    ) -> list[DataFlow]:
        """
        Infer additional flows based on Azure patterns.
        
        Uses agent knowledge to infer typical connections between
        detected services that may not be visible in the diagram.
        
        Args:
            resources: List of detected resources
            existing_flows: Already detected flows
            
        Returns:
            List of inferred additional flows
        """
        logger = logging.getLogger(__name__)
        
        try:
            async with NetworkFlowAgent() as agent:
                return await agent.infer_flows(resources, existing_flows)
        except Exception as e:
            logger.error(f"Flow inference failed: {e}")
            # Don't fail the entire workflow for flow inference
            return []
    
    async def _run_security(
        self,
        resources: list[DetectedIcon],
        flows: list[DataFlow],
    ) -> list[SecurityRecommendation]:
        """Run security recommendations stage."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with SecurityAgent() as agent:
                recommendations = await agent.get_recommendations(resources, flows)
            
            # Debug logging to see what recommendations the agent returned
            for rec in recommendations:
                logger.debug(f"Security recommendation for {rec.resource_type}:")
                if rec.private_endpoint:
                    logger.debug(f"  PE: enabled={rec.private_endpoint.enabled}, dns={rec.private_endpoint.private_dns_zone}, group_ids={rec.private_endpoint.group_ids}")
                logger.debug(f"  RBAC assignments: {len(rec.rbac_assignments)}")
            
            return recommendations
        except Exception as e:
            import traceback
            logger.error(f"Security analysis failed: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            # Return empty list but don't fail the entire workflow
            # The workflow can still produce useful output without security recommendations
            await self._emit_progress(
                "security",
                f"Error: {str(e)}",
                0.82,
            )
            return []
    
    def _merge_clarifications(
        self,
        architectural: list[DetectedIcon],
        clarifications: list[ClarificationResponse],
    ) -> list[DetectedIcon]:
        """
        Merge clarified resources into the architectural list.
        
        Updates existing resources instead of creating duplicates.
        """
        final_resources = list(architectural)
        
        for clarification in clarifications:
            if clarification.should_include and clarification.clarified_type:
                original = clarification.original_resource
                
                # Find existing resource by matching position (unique identifier)
                existing_idx = None
                for idx, resource in enumerate(final_resources):
                    if (resource.position.x == original.position.x and 
                        resource.position.y == original.position.y):
                        existing_idx = idx
                        break
                
                # Create updated icon with clarified type
                updated = DetectedIcon(
                    type=clarification.clarified_type,
                    name=clarification.clarified_name or original.name,
                    position=original.position,
                    bounding_box=original.bounding_box,
                    confidence=0.9,  # User-confirmed
                    arm_resource_type=clarification.clarified_arm_type or original.arm_resource_type,
                    resource_category=original.resource_category,  # Preserve category
                    connections=original.connections if hasattr(original, 'connections') else [],
                )
                
                if existing_idx is not None:
                    # UPDATE existing resource (prevent duplicate)
                    final_resources[existing_idx] = updated
                else:
                    # ADD new resource (user added via clarification)
                    final_resources.append(updated)
        
        return final_resources
    
    def _build_analysis(
        self,
        detection_result: DetectionResult,
        filter_result: FilterResult,
        clarifications: list[ClarificationResponse],
        final_resources: list[DetectedIcon],
        security_recommendations: list[SecurityRecommendation],
        network_flow_result: Optional[NetworkFlowResult] = None,
        image_path: str = "",
    ) -> ArchitectureAnalysis:
        """Build the final ArchitectureAnalysis result (IaC-ready)."""
        from datetime import datetime
        import logging
        logger = logging.getLogger(__name__)
        
        # Convert DetectedIcons to IaC-ready AzureResources
        resources = []
        resource_id_map = {}  # Map name to id for flow lookup
        
        # Log security recommendations received
        logger.debug(f"Received {len(security_recommendations)} security recommendations")
        for rec in security_recommendations:
            logger.debug(f"  Rec: type={rec.resource_type}, name={rec.resource_name}, PE recommended={rec.private_endpoint.recommended if rec.private_endpoint else 'None'}")
        
        for idx, icon in enumerate(final_resources, 1):
            resource_id = f"resource-{idx}"
            resource_name = icon.name or f"{icon.type}-{idx}"
            resource_id_map[icon.type] = resource_id
            resource_id_map[resource_name] = resource_id
            
            # Find security recommendations for this resource
            # Match by resource_type (case-insensitive) or resource_name
            matching_recs = [
                rec for rec in security_recommendations
                if (rec.resource_type.lower() == icon.type.lower() or 
                    (rec.resource_name and rec.resource_name.lower() == (icon.name or "").lower()))
            ]
            
            logger.debug(f"Resource {icon.type}/{icon.name}: {len(matching_recs)} matching recommendations")
            
            # Build SecurityConfig from recommendations
            security_config = self._build_security_config(icon.type, matching_recs)
            
            # Build recommendations list
            recommendations = []
            for rec in matching_recs:
                recommendations.extend(rec.additional_recommendations)
                recommendations.extend(rec.documentation_urls)
            
            resource = AzureResource(
                id=resource_id,
                name=resource_name,
                service_type=icon.type,
                resource_type=icon.arm_resource_type,
                bounding_box=icon.bounding_box,
                detected_by="gpt4o_vision",
                confidence=icon.confidence,
                user_verified=icon.confidence >= 0.9,
                needs_user_validation=icon.needs_clarification,
                security=security_config,
                recommendations=recommendations,
                position=icon.position,
                connections=[],
            )
            resources.append(resource)
        
        # Build network flows from detection result
        network_flows = []
        if detection_result.data_flows:
            for flow in detection_result.data_flows:
                # Map source/target to resource IDs
                source_id = resource_id_map.get(flow.source, flow.source)
                target_id = resource_id_map.get(flow.target, flow.target)
                
                network_flow = DataFlow(
                    source=source_id,
                    target=target_id,
                    flow_type=flow.flow_type,
                    direction=flow.direction,
                    protocol=flow.protocol,
                    port=flow.port,
                    description=flow.description,
                    is_private=flow.is_private,
                )
                network_flows.append(network_flow)
                
                # Update resource inbound/outbound flows
                for resource in resources:
                    if resource.id == source_id:
                        resource.outbound_flows.append(network_flow)
                        if target_id not in resource.connections:
                            resource.connections.append(target_id)
                    if resource.id == target_id:
                        resource.inbound_flows.append(network_flow)
        
        # Extract vnets and subnets from network flow result
        vnets = []
        subnets = []
        if network_flow_result:
            for vnet in network_flow_result.vnets:
                vnets.append({
                    "name": vnet.name,
                    "type": vnet.type,
                    "contained_resources": vnet.contained_resources,
                })
            subnets = network_flow_result.subnets
        
        # Build summary recommendation lists
        architecture_recs = []
        security_recs = []
        
        for rec in security_recommendations:
            # Add high-level security summary for each resource
            summary_line = f"{rec.resource_type}"
            if rec.resource_name:
                summary_line += f" ({rec.resource_name})"
            summary_line += ":"
            
            rec_items = []
            # Check if managed_identity is present and enabled
            if rec.managed_identity and rec.managed_identity.enabled:
                rec_items.append(f"managed identity ({rec.managed_identity.identity_type.value})")
            if rec.private_endpoint and rec.private_endpoint.recommended:
                rec_items.append("private endpoint")
            if rec.rbac_assignments:
                rec_items.append(f"{len(rec.rbac_assignments)} RBAC roles")
            if rec.vnet_integration and rec.vnet_integration.recommended:
                rec_items.append("VNet integration")
            
            if rec_items:
                summary_line += " " + ", ".join(rec_items)
                security_recs.append(summary_line)
        
        return ArchitectureAnalysis(
            image_path=str(image_path),
            analyzed_at=datetime.utcnow().isoformat(),
            total_detected=len(detection_result.icons),
            total_identified=len(final_resources),
            detection_methods={"gpt4o_vision": len(detection_result.icons)},
            resources=resources,
            network_flows=network_flows,
            vnet_boundaries=detection_result.vnet_boundaries,
            vnets=vnets,
            subnets=subnets,
            data_flows=detection_result.data_flows,
            detected_texts=detection_result.texts,
            architecture_recommendations=architecture_recs,
            security_recommendations=security_recs,
            summary=self._generate_summary(resources, security_recommendations),
        )
    
    def _build_security_config(
        self,
        service_type: str,
        recommendations: list[SecurityRecommendation],
    ) -> SecurityConfig:
        """Build SecurityConfig from agent recommendations (no static mappings).
        
        PE group IDs and DNS zones are extracted from the Security Agent's 
        recommendations, which uses Bing grounding to look up Azure documentation.
        """
        # Build RBAC assignments from recommendations
        rbac_assignments = []
        for rec in recommendations:
            for rbac in rec.rbac_assignments:
                rbac_assignments.append(rbac)
        
        # Build private endpoint config from agent recommendations
        private_endpoint = PrivateEndpointConfig(
            enabled=False,
            recommended=False,
        )
        
        for rec in recommendations:
            if rec.private_endpoint:
                # Use group_ids from agent - no static fallback
                # The Security Agent should provide both DNS zone and group_ids
                group_ids = rec.private_endpoint.group_ids or []
                
                private_endpoint = PrivateEndpointConfig(
                    enabled=rec.private_endpoint.enabled,
                    recommended=rec.private_endpoint.recommended,
                    private_dns_zone=rec.private_endpoint.private_dns_zone,
                    group_ids=group_ids,
                    guidance=rec.private_endpoint.guidance,
                )
                break
        
        # Build VNet integration config from agent recommendations
        vnet_integration = VNetIntegrationConfig(
            enabled=False,
            recommended=False,
        )
        
        for rec in recommendations:
            if rec.vnet_integration:
                vnet_integration = rec.vnet_integration
                break
        
        # Build managed identity config from recommendations (fallback to enabled)
        managed_identity = ManagedIdentityConfig(
            enabled=True,
            identity_type=ManagedIdentityType.SYSTEM_ASSIGNED,
        )
        
        for rec in recommendations:
            if rec.managed_identity:
                managed_identity = ManagedIdentityConfig(
                    enabled=True,
                    identity_type=rec.managed_identity.identity_type,
                    justification=rec.managed_identity.justification,
                )
                break
        
        return SecurityConfig(
            managed_identity=managed_identity,
            private_endpoint=private_endpoint,
            vnet_integration=vnet_integration,
            rbac_assignments=rbac_assignments,
            network_access=NetworkAccessType.PRIVATE_ENDPOINT if private_endpoint.enabled else NetworkAccessType.VNET_INTEGRATED,
            disable_public_access=True,
        )
    
    def _generate_summary(
        self,
        resources: list[AzureResource],
        security_recommendations: list[SecurityRecommendation],
    ) -> str:
        """Generate a text summary of the analysis."""
        resource_types = {}
        for r in resources:
            resource_types[r.service_type] = resource_types.get(r.service_type, 0) + 1
        
        type_summary = ", ".join(
            f"{count}x {rtype}" 
            for rtype, count in sorted(resource_types.items(), key=lambda x: -x[1])
        )
        
        summary = f"Detected {len(resources)} Azure resources: {type_summary}."
        
        if security_recommendations:
            summary += f" Generated {len(security_recommendations)} security recommendations."
        
        return summary


async def run_analysis(
    image_path: str | Path,
    interactive: bool = True,
    include_security: bool = True,
    progress_callback: Optional[Callable[[WorkflowProgress], Awaitable[None]]] = None,
) -> WorkflowResult:
    """
    Convenience function to run the complete analysis workflow.
    
    Args:
        image_path: Path to the architecture diagram image
        interactive: Whether to prompt for clarifications
        include_security: Whether to include security recommendations
        progress_callback: Optional async callback for progress updates
        
    Returns:
        WorkflowResult with complete analysis
    """
    workflow = ArchitectureWorkflow(
        interactive=interactive,
        include_security=include_security,
    )
    
    if progress_callback:
        workflow.on_progress(progress_callback)
    
    return await workflow.analyze(image_path)

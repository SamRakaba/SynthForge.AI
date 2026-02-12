"""
Phase 2: Infrastructure as Code (IaC) Generation Workflow

This module orchestrates the generation of IaC templates (Bicep/Terraform)
and CI/CD pipelines from Phase 1 analysis outputs.

Architecture:
- Reads Phase 1 JSON outputs (architecture_analysis.json, etc.)
- Uses Bicep MCP, Terraform MCP, and Azure DevOps/GitHub MCP servers
- Generates deployable IaC templates with proper dependencies
- Creates CI/CD pipelines for infrastructure deployment

Pipeline:
    Stage 0: Load Phase 1 Analysis
             ↓
    Stage 1: Service Analysis
             ↓
    Stage 2: User Validation
             ↓
    Stage 3: Module Mapping
             ↓
    Stage 4: Module Generation (Reusable Modules)
             ↓
    Stage 5: Deployment Wrappers (Orchestration)
             ↓
    Stage 6: ADO Pipelines (CI/CD)
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential

from synthforge.config import get_settings
from synthforge.models import ArchitectureAnalysis
from synthforge.agents.service_analysis_agent import ServiceAnalysisAgent, ServiceAnalysisResult
from synthforge.agents.module_mapping_agent import ModuleMappingAgent, ModuleMappingResult
from synthforge.agents.user_validation_workflow import UserValidationWorkflow
from synthforge.agents.module_development_agent import ModuleDevelopmentAgent, ModuleDevelopmentResult

logger = logging.getLogger(__name__)


class Phase2Workflow:
    """
    Phase 2: IaC Generation Workflow.
    
    Orchestrates multi-agent pipeline for generating Infrastructure as Code
    from Phase 1 architecture analysis.
    """
    
    def __init__(
        self,
        output_dir: Path,
        iac_dir: Optional[Path] = None,
        iac_format: str = "bicep",  # "bicep", "terraform", or "both"
        pipeline_platform: str = "azure-devops",  # "azure-devops" or "github"
    ):
        """
        Initialize Phase 2 workflow.
        
        Args:
            output_dir: Directory containing Phase 1 outputs
            iac_dir: Root directory for Phase 2 IaC outputs (default: from settings.iac_dir)
            iac_format: IaC format to generate ("bicep", "terraform", or "both")
            pipeline_platform: CI/CD platform ("azure-devops" or "github")
        """
        self.settings = get_settings()
        self.output_dir = Path(output_dir)
        self.iac_dir = Path(iac_dir) if iac_dir else self.settings.iac_dir
        self.iac_format = iac_format
        self.pipeline_platform = pipeline_platform
        
        # Phase 1 output files (from output_dir)
        self.phase1_analysis = self.output_dir / "architecture_analysis.json"
        self.phase1_resources = self.output_dir / "resource_summary.json"
        self.phase1_network = self.output_dir / "network_flows.json"
        self.phase1_security = self.output_dir / "rbac_assignments.json"
        self.phase1_endpoints = self.output_dir / "private_endpoints.json"
        
        # Phase 2 output subdirectories (flat structure - all modules at same level)
        self.modules_output = self.iac_dir / "modules"  # All modules (service + common)
        self.environments_output = self.iac_dir / "environments"  # Environment configs
        self.pipelines_output = self.iac_dir / "pipelines"  # CI/CD
        self.docs_output = self.iac_dir / "docs"  # Documentation
        
        # Create IaC output directories (flat structure)
        self.iac_dir.mkdir(parents=True, exist_ok=True)
        self.modules_output.mkdir(parents=True, exist_ok=True)
        self.environments_output.mkdir(parents=True, exist_ok=True)
        self.pipelines_output.mkdir(parents=True, exist_ok=True)
        self.docs_output.mkdir(parents=True, exist_ok=True)
        
        # Initialize Azure AI Agents clients
        phase2_endpoint = self.settings.iac_project_endpoint or self.settings.project_endpoint
        
        # Log which project is being used
        if self.settings.iac_project_endpoint:
            logger.info(f"Phase 2 using dedicated IaC project: {phase2_endpoint}")
            logger.info(f"  IaC Model: {self.settings.iac_model_deployment_name}")
            if self.settings.iac_model_deployment_name_alt:
                logger.info(f"  Fallback Model: {self.settings.iac_model_deployment_name_alt}")
        else:
            logger.warning(f"Phase 2 using same project as Phase 1: {phase2_endpoint}")
            logger.info(f"  IaC Model: {self.settings.iac_model_deployment_name}")
        
        self.agents_client = AgentsClient(
            endpoint=phase2_endpoint,
            credential=DefaultAzureCredential(),
        )
        self.mapping_agents_client = AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=DefaultAzureCredential(),
        )
        
        # Progress tracking
        self._progress_callback = None
        
        logger.info(f"Phase 2 Workflow initialized:")
        logger.info(f"  - IaC Format: {iac_format}")
        logger.info(f"  - Pipeline Platform: {pipeline_platform}")
        logger.info(f"  - Phase 1 Outputs: {self.output_dir}")
        logger.info(f"  - IaC Root Directory: {self.iac_dir}")
        logger.info(f"  - Phase 2 Project Endpoint: {phase2_endpoint}")
        logger.info(f"  - Mapping Project Endpoint: {self.settings.project_endpoint}")
    
    def _create_common_module_mappings(self, iac_format: str, common_patterns: Dict[str, Any] = None) -> List:
        """
        Create mappings for common infrastructure modules DYNAMICALLY from Service Analysis.
        
        Instead of hardcoding common modules, this extracts them from Phase 1 analysis
        where the Service Analysis Agent identified repeated patterns across services.
        
        The agent uses Bing + MS Learn MCP to research:
        - Which services need private endpoints (from security recommendations)
        - Which services need diagnostics (from monitoring recommendations)
        - Which services need RBAC (from identity recommendations)
        - Which services need locks (from governance recommendations)
        
        Args:
            iac_format: "terraform" or "bicep"
            common_patterns: Dictionary from Service Analysis Agent with pattern analysis
                            If None, falls back to hardcoded defaults (legacy behavior)
            
        Returns:
            List of ModuleMapping for common modules
        """
        from synthforge.agents.module_mapping_agent import ModuleMapping, ServiceRequirement
        
        common_modules = []
        
        # If no common_patterns provided by agent, use fallback (legacy mode)
        if not common_patterns:
            logger.warning("⚠️  No common_patterns from Service Analysis Agent - using fallback defaults")
            logger.warning("   This is legacy mode. Agent should analyze Phase 1 and provide common_patterns.")
            common_patterns = self._get_fallback_common_patterns()
        else:
            logger.info(f"✓ Using {len(common_patterns)} common patterns from Service Analysis Agent")
        
        # Process each pattern identified by the agent
        for pattern_key, pattern_data in common_patterns.items():
            # Skip if not required or usage count too low (agent determines threshold)
            if not pattern_data.get('required', False):
                logger.debug(f"   Skipping {pattern_key}: not required by agent analysis")
                continue
                
            usage_count = pattern_data.get('usage_count', 0)
            if usage_count < 2:  # Only create common modules if used by 2+ services
                logger.debug(f"   Skipping {pattern_key}: usage_count={usage_count} (threshold: 2)")
                continue
            
            # Get ARM type and folder path from agent analysis
            arm_type = pattern_data.get('arm_type')
            folder_path = pattern_data.get('folder_path')
            description = pattern_data.get('description', f"{pattern_key} common module")
            justification = pattern_data.get('justification', '')
            
            if not arm_type:
                logger.warning(f"   ⚠️  Skipping {pattern_key}: missing ARM type")
                continue
            
            # If agent didn't provide folder_path, derive from ARM type
            if not folder_path:
                folder_path = arm_type.replace('Microsoft.', '').replace('/', '-').lower()
            
            logger.info(f"   ✓ Creating common module: {folder_path} (used by {usage_count} services)")
            logger.debug(f"     Justification: {justification}")
            
            # Create service requirement for the common module
            service_req = ServiceRequirement(
                resource_name=folder_path,
                service_type=description,
                arm_type=arm_type,
                configurations=pattern_data.get('configurations', {}),
                dependencies=[],
                network_requirements={},
                security_requirements={},
                priority=1,  # Foundation priority
                phase1_recommendations=[justification] if justification else [],
                research_sources=pattern_data.get('research_sources', [])
            )
            
            # Determine AVM source (agent may have provided this from research)
            avm_source = pattern_data.get('avm_source')
            if not avm_source:
                # Fallback: construct from ARM type
                provider = arm_type.split('/')[0].replace('Microsoft.', '').lower()
                resource = arm_type.split('/')[1].lower()
                if iac_format == "terraform":
                    avm_source = f"avm/res/{provider}/{resource}"
                else:
                    avm_source = f"avm/res/{provider}/{resource}"
            
            # Create module mapping
            mapping = ModuleMapping(
                service_requirement=service_req,
                module_source=avm_source,
                module_version=pattern_data.get('version', 'latest'),
                module_documentation=pattern_data.get('documentation', f"https://azure.github.io/Azure-Verified-Modules/indexes/{iac_format}/"),
                required_inputs=pattern_data.get('required_inputs', []),
                optional_inputs=pattern_data.get('optional_inputs', []),
                folder_path=f"modules/{folder_path}",
                environment_path="",
                best_practices=pattern_data.get('best_practices', ["Common module used across multiple services"])
            )
            
            common_modules.append(mapping)
        
        if len(common_modules) == 0:
            logger.warning("⚠️  No common modules created! Check Service Analysis Agent output.")
        
        return common_modules
    
    def _get_fallback_common_patterns(self) -> Dict[str, Any]:
        """
        Fallback common patterns when Service Analysis Agent doesn't provide them.
        
        This is LEGACY mode - ideally the agent should analyze Phase 1 outputs
        and determine which common modules are needed based on actual service requirements.
        
        Returns:
            Dictionary of common patterns (same format as agent output)
        """
        return {
            "private_endpoint": {
                "required": True,
                "usage_count": 10,  # Assume most services need it
                "arm_type": "Microsoft.Network/privateEndpoints",
                "folder_path": "network-privateendpoints",
                "description": "Private Endpoint configuration for network isolation",
                "justification": "Fallback mode: assuming most services need private endpoints",
            },
            "diagnostics": {
                "required": True,
                "usage_count": 10,
                "arm_type": "Microsoft.Insights/diagnosticSettings",
                "folder_path": "insights-diagnosticsettings",
                "description": "Diagnostic settings for monitoring and logging",
                "justification": "Fallback mode: assuming all services need diagnostics",
            },
            "rbac": {
                "required": True,
                "usage_count": 10,
                "arm_type": "Microsoft.Authorization/roleAssignments",
                "folder_path": "authorization-roleassignments",
                "description": "Role-based access control assignments",
                "justification": "Fallback mode: assuming most services need RBAC",
            },
            "lock": {
                "required": True,
                "usage_count": 5,
                "arm_type": "Microsoft.Authorization/locks",
                "folder_path": "authorization-locks",
                "description": "Resource locks for protection",
                "justification": "Fallback mode: assuming some services need locks",
            },
        }
    
    def _create_naming_module_mapping(self, iac_format: str):
        """
        Create a module mapping for the CAF naming module.
        
        The naming module is a special common module that generates resource names
        according to Cloud Adoption Framework conventions. It includes:
        - CAF abbreviations for all detected Azure services
        - Constraint enforcement (length, character rules, global uniqueness)
        - Instance number support for multiple resources of same type
        
        Args:
            iac_format: "terraform" or "bicep"
            
        Returns:
            ModuleMapping for naming module
        """
        from synthforge.agents.module_mapping_agent import ModuleMapping, ServiceRequirement
        
        # Extract ALL resources from Phase 1 to understand naming requirements
        resource_types = set()
        resource_counts = {}
        
        # Load Phase 1 architecture analysis
        phase1_data = None
        if self.phase1_analysis.exists():
            with open(self.phase1_analysis, "r", encoding="utf-8") as f:
                phase1_data = json.load(f)
        
        if phase1_data and "resources" in phase1_data:
            for resource in phase1_data["resources"]:
                arm_type = resource.get("arm_type", "")
                if arm_type:
                    resource_types.add(arm_type)
                    resource_counts[arm_type] = resource_counts.get(arm_type, 0) + 1
        
        # Create service requirement for naming module
        service_req = ServiceRequirement(
            resource_name="naming",
            service_type="CAF Naming Convention Module",
            arm_type="Microsoft.Naming/conventions",  # Synthetic type
            configurations={
                "caf_compliant": True,
                "resource_types": list(resource_types),
                "resource_counts": resource_counts,
                "supports_instances": True,  # Multiple instances of same resource
            },
            dependencies=[],
            network_requirements={},
            security_requirements={},
            priority=0,  # Highest priority - generated first
            phase1_recommendations=[
                f"CAF naming module for {len(resource_types)} unique resource types",
                f"Total resources: {sum(resource_counts.values())}",
                f"Supports multiple instances: {any(c > 1 for c in resource_counts.values())}",
            ],
            research_sources=[]
        )
        
        # Create module mapping
        mapping = ModuleMapping(
            service_requirement=service_req,
            module_source="custom/naming",  # Not an AVM module
            module_version="1.0.0",
            module_documentation="Cloud Adoption Framework naming conventions",
            required_inputs=["workload_name", "environment", "location"],
            optional_inputs=["resource_suffix", "instance_number"],
            folder_path="modules/naming",
            environment_path="",
            best_practices=[
                "Follow CAF abbreviations from Microsoft documentation",
                "Enforce service-specific constraints (length, characters, uniqueness)",
                "Support instance numbers for multiple resources of same type",
                "Validate naming rules at plan time",
            ]
        )
        
        logger.info(f"   ✓ Created naming module mapping (covers {len(resource_types)} resource types)")
        return mapping
    
    def _deduplicate_by_arm_type(self, mappings: List) -> List:
        """
        Deduplicate module mappings by ARM resource type.
        
        When multiple service instances share the same ARM type (e.g., multiple 
        "Azure App Service" instances all using Microsoft.Web/sites), only create 
        ONE module per unique ARM type.
        
        This prevents duplicate module folders like both "web-site" and "web-sites".
        Also normalizes folder_path to always match ARM type naming.
        
        Args:
            mappings: List of ModuleMapping objects
            
        Returns:
            Deduplicated list with one mapping per unique ARM type
        """
        from collections import OrderedDict
        
        # Use OrderedDict to preserve order and deduplicate by ARM type
        deduplicated = OrderedDict()
        
        for mapping in mappings:
            arm_type = mapping.service_requirement.arm_type
            
            if not arm_type:
                # If no ARM type specified, use service_type as fallback key
                key = mapping.service_requirement.service_type
                logger.warning(f"⚠ No ARM type for {key}, using service_type as dedup key")
            else:
                key = arm_type
            
            if key in deduplicated:
                # Already have a mapping for this ARM type, skip duplicate
                existing = deduplicated[key]
                logger.debug(f"   Skipping duplicate: {mapping.service_requirement.service_type} (ARM type {arm_type}) - already have {existing.service_requirement.service_type}")
            else:
                # First mapping for this ARM type, keep it
                # Normalize folder_path based on ARM type (consistent naming)
                if arm_type:
                    module_name = arm_type.replace('Microsoft.', '').replace('/', '-').lower()
                    normalized_folder = f"modules/{module_name}"
                    
                    # Update folder_path if agent returned inconsistent value
                    if mapping.folder_path != normalized_folder:
                        logger.debug(f"   Normalizing folder_path: {mapping.folder_path} → {normalized_folder}")
                        mapping.folder_path = normalized_folder
                
                deduplicated[key] = mapping
                logger.debug(f"   Keeping: {mapping.service_requirement.service_type} (ARM type {arm_type}) → {mapping.folder_path}")
        
        # Return list of unique mappings
        return list(deduplicated.values())
    
    def on_progress(self, callback):
        """Set progress callback function."""
        self._progress_callback = callback
    
    async def _emit_progress(
        self, 
        stage: str, 
        message: str, 
        progress: float,
        data: Optional[dict] = None,
    ):
        """Emit a progress update."""
        if self._progress_callback:
            from synthforge.workflow import WorkflowProgress
            update = WorkflowProgress(
                stage=stage,
                message=message,
                progress=progress,
                data=data,
            )
            await self._progress_callback(update)
    
    async def run(self) -> Dict[str, Any]:
        """
        Execute Phase 2 workflow.
        
        Args:
            progress_callback: Optional callback for progress updates (stage, message)
        
        Returns:
            Dictionary with Phase 2 results and generated file paths
        """
        logger.info("=" * 80)
        logger.info("PHASE 2: Infrastructure as Code Generation")
        logger.info("=" * 80)
        
        try:
            # Stage 0: Load Phase 1 outputs (0-5%)
            await self._emit_progress("load", "Loading Phase 1 analysis...", 0.0)
            phase1_data = await self._load_phase1_outputs()
            
            # Log resource count from Phase 1
            resource_count = len(phase1_data.get("resources", {}).get("resources", []))
            await self._emit_progress("load", f"Found {resource_count} services in Phase 1 outputs", 0.05)
            
            # Stage 1: Service Analysis - Extract services from Phase 1 (5-25%)
            await self._emit_progress("service_analysis", "Extracting Azure services from Phase 1 design...", 0.05)
            
            service_analysis_agent = ServiceAnalysisAgent(
                agents_client=self.mapping_agents_client,
                model_name=self.settings.model_deployment_name,  # Use primary model for analysis
                bing_connection_name=self.settings.bing_connection_id,
                ms_learn_mcp_url=self.settings.ms_learn_mcp_url,
            )
            
            try:
                await self._emit_progress("service_analysis", "Analyzing configurations, dependencies, and best practices...", 0.10)
                service_result = await service_analysis_agent.analyze_services(phase1_data)
                await self._emit_progress("service_analysis", f"{len(service_result.services)} services extracted and analyzed", 0.25)
            finally:
                service_analysis_agent.cleanup()
            
            # Extract recommendations summary from service result
            recommendations_summary = service_result.recommendations_summary if hasattr(service_result, 'recommendations_summary') else None
            
            # Stage 2: User Validation - Get user approval (25-35%)
            await self._emit_progress("validation", "Presenting services and recommendations for review...", 0.25)
            
            user_validation = UserValidationWorkflow()
            validation_result = await user_validation.validate_services(
                services=service_result.services,
                recommendations_summary=recommendations_summary,
                needs_clarification=getattr(service_result, 'needs_clarification', None),
                excluded_services=getattr(service_result, 'excluded_services', None),
            )
            
            if not validation_result.approved:
                logger.warning("\n⚠ Phase 2 cancelled by user")
                return {
                    "phase": 2,
                    "status": "cancelled",
                    "reason": "User cancelled during validation",
                }
            
            await self._emit_progress("validation", f"{len(validation_result.modified_services)} services approved for IaC generation", 0.35)
            
            # Use validated/modified services
            approved_services = validation_result.modified_services
            
            # Filter out services with Unknown ARM type (cannot generate modules)
            valid_services = []
            skipped_services = []
            for svc in approved_services:
                if not svc.arm_type or svc.arm_type == "Unknown" or not svc.arm_type.startswith("Microsoft."):
                    skipped_services.append(svc)
                    logger.warning(f"⚠️  Skipping {svc.service_type}: Invalid ARM type '{svc.arm_type}'")
                else:
                    valid_services.append(svc)
            
            if skipped_services:
                logger.warning(f"\n⚠️  {len(skipped_services)} service(s) skipped due to invalid ARM types:")
                for svc in skipped_services:
                    logger.warning(f"   - {svc.service_type} (ARM type: {svc.arm_type or 'None'})")
                logger.warning("   These services need proper ARM resource types to generate modules.")
                logger.warning("   Phase 1 Filter Agent should resolve ARM types using available tools.\n")
            
            if not valid_services:
                logger.error("\n❌ No valid services to generate! All services have invalid ARM types.")
                return {
                    "phase": 2,
                    "status": "failed",
                    "reason": "No services with valid ARM types",
                    "skipped_services": [s.service_type for s in skipped_services]
                }
            
            approved_services = valid_services
            logger.info(f"\n✓ {len(approved_services)} services validated with proper ARM types")
            
            # Stage 3: Module Mapping - Map to AVM/Terraform modules (35-70%)
            await self._emit_progress("module_mapping", f"Searching Azure Verified Modules for {self.iac_format.upper()}...", 0.35)
            
            module_mapping_agent = ModuleMappingAgent(
                agents_client=self.mapping_agents_client,
                model_name=self.settings.model_deployment_name,
                bing_connection_name=self.settings.bing_connection_id,
                ms_learn_mcp_url=self.settings.ms_learn_mcp_url,
            )
            
            mapping_result = None
            try:
                await self._emit_progress("module_mapping", "Mapping services to reusable infrastructure modules...", 0.40)
                mapping_result = await module_mapping_agent.map_services(
                    services=approved_services,
                    iac_format=self.iac_format,
                )
                
                # Deduplicate mappings by ARM resource type BEFORE adding common modules
                logger.info(f"\n🔍 Deduplicating service modules by ARM resource type...")
                deduplicated_mappings = self._deduplicate_by_arm_type(mapping_result.mappings)
                original_count = len(mapping_result.mappings)
                dedup_count = len(deduplicated_mappings)
                if original_count > dedup_count:
                    logger.info(f"   ✓ Deduplicated {original_count} services → {dedup_count} unique ARM types")
                else:
                    logger.info(f"   ✓ All {original_count} services have unique ARM types")
                
                # Add common modules FIRST (so they exist when service modules reference them)
                logger.info(f"\n📦 Adding common infrastructure modules...")
                
                # Extract common_patterns from Service Analysis Agent result
                common_patterns = None
                if hasattr(service_result, 'common_patterns') and service_result.common_patterns:
                    common_patterns = service_result.common_patterns
                    logger.info(f"   ✓ Using common_patterns from Service Analysis Agent ({len(common_patterns)} patterns detected)")
                else:
                    logger.warning(f"   ⚠️  Service Analysis Agent did not provide common_patterns - using fallback")
                
                # Create common modules dynamically from agent analysis
                common_modules = self._create_common_module_mappings(
                    iac_format=self.iac_format,
                    common_patterns=common_patterns
                )
                
                # Add naming module as a special common module (generated from Phase 1 resources)
                naming_module_mapping = self._create_naming_module_mapping(
                    iac_format=self.iac_format
                )
                # NOTE: Naming module will be generated in Stage 5 by DeploymentWrapperAgent
                # Do NOT add it to Stage 4 module generation (needs special instructions)
                if naming_module_mapping:
                    logger.info(f"   ✓ Naming module will be generated in Stage 5 (Deployment Wrappers)")
                    # Don't add to common_modules list for Stage 4
                    # common_modules.insert(0, naming_module_mapping)
                
                # Insert common modules at the BEGINNING so they're generated first
                mapping_result.mappings = common_modules + deduplicated_mappings
                mapping_result.total_count = len(mapping_result.mappings)
                
                logger.info(f"   ✓ Added {len(common_modules)} common modules total: {[m.service_requirement.resource_name for m in common_modules]}")
                
                await self._emit_progress("module_mapping", f"Mapped {mapping_result.total_count} modules (services + common)", 0.65)
                
                # Debug logging
                logger.info(f"\n📊 Module Mapping Result Summary:")
                logger.info(f"   - Total mappings: {len(mapping_result.mappings)}")
                logger.info(f"   - IAC Format: {self.iac_format}")
                if len(mapping_result.mappings) == 0:
                    logger.error("   ⚠️ CRITICAL: Module Mapping Agent returned 0 mappings!")
                    logger.error("   This will cause Module Development to skip code generation.")
                else:
                    logger.info(f"   ✓ Found {len(mapping_result.mappings)} mappings to generate")
                    for i, mapping in enumerate(mapping_result.mappings[:3], 1):
                        logger.info(f"     {i}. {mapping.service_requirement.service_type}")
                    if len(mapping_result.mappings) > 3:
                        logger.info(f"     ... and {len(mapping_result.mappings) - 3} more")
                
            finally:
                module_mapping_agent.cleanup()
                if mapping_result:
                    await self._emit_progress("module_mapping", f"{mapping_result.total_count} services mapped to modules", 0.70)
                else:
                    await self._emit_progress("module_mapping", "Module mapping failed", 0.70)
            
            # Stage 4: Module Development - Generate IaC modules (70-85%)
            await self._emit_progress("module_development", f"Generating {self.iac_format.upper()} module wrappers...", 0.70)
            
            # Use format-agnostic modules directory (file extensions indicate format)
            output_dir = self.modules_output
            
            # Get fallback model from settings
            fallback_model = getattr(self.settings, 'iac_model_deployment_name_alt', self.settings.model_deployment_name)
            
            module_dev_agent = ModuleDevelopmentAgent(
                agents_client=self.agents_client,
                model_name=self.settings.iac_model_deployment_name,  # Use IaC model for code generation
                iac_format=self.iac_format,
                bing_connection_name=self.settings.bing_connection_id,
                ms_learn_mcp_url=self.settings.ms_learn_mcp_url,
            )
            # Set fallback model
            module_dev_agent.fallback_model = fallback_model
            
            # Track module creation progress with detailed updates
            total_modules = len(mapping_result.mappings)
            async def module_progress_async(stage: str, message: str, progress: float):
                """Progress callback for individual module generation."""
                await self._emit_progress("module_development", message, progress)
            
            try:
                await self._emit_progress("module_development", f"Creating {total_modules} modules using {self.settings.iac_model_deployment_name}...", 0.72)
                dev_result = await module_dev_agent.generate_modules(
                    mappings=mapping_result.mappings,
                    output_dir=output_dir,
                    progress_callback=module_progress_async,
                )
                await self._emit_progress("module_development", f"Generated {dev_result.total_count} module wrappers", 0.85)
            finally:
                module_dev_agent.cleanup()
            
            # Stage 5: Deployment Wrappers - Generate deployment orchestration (85-90%)
            # NOTE: Stage 5 progress is handled by the deployment wrapper agent's callback
            # await self._emit_progress("deployment_wrappers", "Generating deployment wrappers...", 0.85)
            # await self._emit_progress("deployment_wrappers", f"Creating {self.iac_format.upper()} deployment orchestration...", 0.87)
            
            # Import deployment wrapper agent
            from synthforge.agents.deployment_wrapper_agent import (
                DeploymentWrapperAgent,
                DeploymentWrapperResult,
            )
            
            # Initialize deployment wrapper agent
            wrapper_agent = DeploymentWrapperAgent(
                agents_client=self.agents_client,
                model_name=self.settings.iac_model_deployment_name,  # Use IaC model
                iac_format=self.iac_format,
                bing_connection_name=self.settings.bing_connection_id,
                ms_learn_mcp_url=self.settings.ms_learn_mcp_url,
            )
            
            try:
                # Generate single parameterized deployment wrapper (user specifies environment at deploy time)
                async def wrapper_progress(env, msg):
                    # Progress for single template generation
                    if env == "naming":
                        progress = 0.85  # Start of Stage 5
                    elif env == "deployment":
                        progress = 0.87  # Main deployment template
                    else:
                        progress = 0.85
                    await self._emit_progress("deployment_wrappers", f"[{env}] {msg}", progress)
                
                wrapper_result = await wrapper_agent.generate_deployment_wrappers(
                    phase1_outputs={
                        "architecture_analysis": self.phase1_analysis,
                        "resource_summary": self.phase1_resources,
                        "network_flows": self.phase1_network,
                        "rbac_assignments": self.phase1_security,
                        "private_endpoints": self.phase1_endpoints,
                    },
                    module_mappings=[m.to_dict() for m in mapping_result.mappings],
                    output_dir=output_dir,
                    progress_callback=wrapper_progress,
                )
                
                logger.info(f"Generated parameterized deployment wrapper")
                if wrapper_result.naming_module:
                    logger.info(f"  • Naming module: {wrapper_result.naming_module.folder_path}")
                if wrapper_result.deployment:
                    logger.info(f"  • Deployment template: {wrapper_result.deployment.folder_path}")
                    logger.info(f"    - Files: {len(wrapper_result.deployment.files)}")
                    logger.info(f"    - Required inputs: {len(wrapper_result.deployment.required_inputs)}")
            
            finally:
                wrapper_agent.cleanup()
            
            # NOTE: Stage 5 completion is handled by wrapper_progress callback
            # await self._emit_progress("deployment_wrappers", "Deployment wrappers configured", 0.90)
            
            # Stage 6: ADO Pipelines - Generate CI/CD pipelines (90-95%)
            await self._emit_progress("ado_pipelines", "Generating CI/CD pipelines...", 0.90)
            await self._emit_progress("ado_pipelines", f"Creating {self.pipeline_platform} pipeline configurations...", 0.92)
            
            # TODO: Add pipeline generation agent here
            # For now, log that this stage is planned
            logger.info(f"CI/CD pipelines for {self.pipeline_platform} will be generated in future update")
            
            await self._emit_progress("ado_pipelines", "CI/CD pipelines configured", 0.95)
            
            # Finalization (95-100%)
            await self._emit_progress("finalize", "Saving Phase 2 results and documentation...", 0.95)
            
            results_file = self.iac_dir / f"phase2_results_{self.iac_format}.json"
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "phase": 2,
                        "iac_format": self.iac_format,
                        "service_analysis": service_result.to_dict(),
                        "module_mapping": mapping_result.to_dict(),
                        "module_development": dev_result.to_dict(),
                        "deployment_wrappers": wrapper_result.to_dict(),
                        "status": "completed",
                    },
                    f,
                    indent=2,
                )
            
            await self._emit_progress("complete", "Infrastructure as Code generation complete!", 1.0)
            logger.info(f"\n[Summary]")
            logger.info(f"  • Services analyzed: {service_result.total_count}")
            logger.info(f"  • Modules mapped: {mapping_result.total_count}")
            logger.info(f"  • Modules generated: {dev_result.total_count}")
            logger.info(f"  • Environments generated: {wrapper_result.total_environments}")
            logger.info(f"  • Output directory: {output_dir}")
            logger.info(f"  • Results file: {results_file.name}")
            logger.info("")
            
            return {
                "phase": 2,
                "iac_format": self.iac_format,
                "service_analysis": service_result.to_dict(),
                "module_mapping": mapping_result.to_dict(),
                "module_development": dev_result.to_dict(),
                "deployment_wrappers": wrapper_result.to_dict(),
                "results_file": str(results_file),
                "status": "completed",
            }
        
        except Exception as e:
            logger.error(f"\n✗ Phase 2 failed: {e}", exc_info=True)
            return {
                "phase": 2,
                "status": "failed",
                "error": str(e),
            }
    
    async def _load_phase1_outputs(self) -> Dict[str, Any]:
        """
        Load all Phase 1 output files.
        
        Returns:
            Dictionary with loaded Phase 1 data
        """
        phase1_data = {}
        loaded_count = 0
        
        # Load architecture analysis
        if self.phase1_analysis.exists():
            with open(self.phase1_analysis, "r", encoding="utf-8") as f:
                phase1_data["architecture"] = json.load(f)
            logger.info(f"   -> Loaded: {self.phase1_analysis.name}")
            loaded_count += 1
        else:
            logger.warning(f"   ⚠ Not found: {self.phase1_analysis.name}")
        
        # Load resource summary
        if self.phase1_resources.exists():
            with open(self.phase1_resources, "r", encoding="utf-8") as f:
                phase1_data["resources"] = json.load(f)
            logger.info(f"   -> Loaded: {self.phase1_resources.name}")
            loaded_count += 1
        else:
            logger.warning(f"   ⚠ Not found: {self.phase1_resources.name}")
        
        # Load network flows
        if self.phase1_network.exists():
            with open(self.phase1_network, "r", encoding="utf-8") as f:
                phase1_data["network"] = json.load(f)
            logger.info(f"   -> Loaded: {self.phase1_network.name}")
            loaded_count += 1
        else:
            logger.warning(f"   ⚠ Not found: {self.phase1_network.name}")
        
        # Load security (RBAC)
        if self.phase1_security.exists():
            with open(self.phase1_security, "r", encoding="utf-8") as f:
                phase1_data["security"] = json.load(f)
            logger.info(f"   -> Loaded: {self.phase1_security.name}")
            loaded_count += 1
        else:
            logger.warning(f"   ⚠ Not found: {self.phase1_security.name}")
        
        # Load private endpoints
        if self.phase1_endpoints.exists():
            with open(self.phase1_endpoints, "r", encoding="utf-8") as f:
                phase1_data["private_endpoints"] = json.load(f)
            logger.info(f"   -> Loaded: {self.phase1_endpoints.name}")
            loaded_count += 1
        else:
            logger.warning(f"   ⚠ Not found: {self.phase1_endpoints.name}")
        
        if not phase1_data:
            logger.error("\n✗ No Phase 1 outputs found!")
            logger.error("   Please run Phase 1 first: python main.py <diagram> --phase 1")
            raise FileNotFoundError("Phase 1 outputs not found")
        
        logger.info(f"   -> Loaded {loaded_count} Phase 1 output file(s)")
        return phase1_data
    
    def cleanup(self):
        """Cleanup resources (agents, threads, etc.)"""
        # Future: Cleanup any Phase 2 agents/threads
        pass


async def run_phase2_workflow(
    output_dir: Path,
    iac_dir: Optional[Path] = None,
    iac_format: str = "bicep",
    pipeline_platform: str = "azure-devops",
) -> Dict[str, Any]:
    """
    Main entry point for Phase 2 workflow.
    
    Args:
        output_dir: Directory with Phase 1 outputs
        iac_dir: Root directory for IaC outputs (default: from settings.iac_dir)
        iac_format: IaC format to generate ("bicep", "terraform", or "both")
        pipeline_platform: CI/CD platform ("azure-devops" or "github")
        
    Returns:
        Dictionary with Phase 2 results
    """
    workflow = Phase2Workflow(
        output_dir=output_dir,
        iac_dir=iac_dir,
        iac_format=iac_format,
        pipeline_platform=pipeline_platform,
    )
    
    try:
        results = await workflow.run()
        return results
    finally:
        workflow.cleanup()

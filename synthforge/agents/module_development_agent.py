"""
ModuleDevelopmentAgent: Generates complete IaC modules (Terraform/Bicep).

This agent generates production-ready Infrastructure as Code following:
- HashiCorp best practices for Terraform
- Microsoft best practices for Bicep
- Azure Verified Module patterns
- NO HARD CODING - always references documentation

Generates complete, deployment-ready modules with:
- Main resource definitions
- Variables with validation
- Outputs
- Best practice configurations (networking, security)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole, ThreadRun, RunStatus

from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.agents.module_mapping_agent import ModuleMapping
from synthforge.prompts import get_module_development_agent_instructions, get_prompt_template
from synthforge.code_quality_pipeline import CodeQualityPipeline, create_validation_report

logger = logging.getLogger(__name__)


@dataclass
class GeneratedModule:
    """Represents a generated IaC module."""
    
    module_name: str  # e.g., "openai-service"
    iac_format: str  # "terraform" or "bicep"
    file_path: Path  # Where the module is saved
    content: str  # Full module code
    variables: List[str] = field(default_factory=list)  # Required variables
    outputs: List[str] = field(default_factory=list)  # Module outputs
    dependencies: List[str] = field(default_factory=list)  # Other modules it depends on
    validation_status: str = "not_validated"  # not_validated, pass, warning, fail
    validation_errors: int = 0
    validation_warnings: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "module_name": self.module_name,
            "iac_format": self.iac_format,
            "file_path": str(self.file_path),
            "content": self.content,
            "variables": self.variables,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "validation_status": self.validation_status,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
        }


@dataclass
class ModuleDevelopmentResult:
    """Result from module development stage."""
    
    modules: List[GeneratedModule]
    total_count: int
    iac_format: str
    output_directory: Path
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    validation_enabled: bool = False
    validation_summary: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "modules": [m.to_dict() for m in self.modules],
            "total_count": self.total_count,
            "iac_format": self.iac_format,
            "output_directory": str(self.output_directory),
            "agent_id": self.agent_id,
            "thread_id": self.thread_id,
            "validation_enabled": self.validation_enabled,
            "validation_summary": self.validation_summary,
        }


class ModuleDevelopmentAgent:
    """
    Agent for generating complete IaC modules (Terraform or Bicep).
    
    Uses Azure AI Foundry with Bing Grounding + MS Learn MCP to:
    1. Reference latest Terraform/Bicep best practices
    2. Generate complete, production-ready modules
    3. Include variables, outputs, and resource dependencies
    4. Follow Azure Verified Module patterns
    5. Implement security and networking best practices
    """
    
    AGENT_NAME = "ModuleDevelopmentAgent"

    def __init__(
        self,
        agents_client: AgentsClient,
        model_name: str,
        iac_format: str,
        bing_connection_name: str,
        ms_learn_mcp_url: Optional[str] = None,
        enable_validation: bool = True,
        max_fix_iterations: int = 3,
    ):
        """
        Initialize ModuleDevelopmentAgent.
        
        Args:
            agents_client: Azure AI Agents client
            model_name: Model deployment name (e.g., "gpt-4o")
            iac_format: "terraform" or "bicep"
            bing_connection_name: Bing Grounding connection name
            ms_learn_mcp_url: MS Learn MCP server URL
        """
        self.agents_client = agents_client
        self.model_name = model_name
        self.iac_format = iac_format
        self.agent = None
        self.thread = None
        self.enable_validation = enable_validation
        
        # Initialize code quality pipeline with agent
        if enable_validation:
            # Import here to avoid circular dependency
            from synthforge.agents.code_quality_agent import CodeQualityAgent
            
            # Create code quality agent instance (will be initialized when used)
            quality_agent = CodeQualityAgent(
                agents_client=agents_client,
                model_name=model_name,
                iac_format=iac_format
            )
            
            self.validation_pipeline = CodeQualityPipeline(
                iac_type=iac_format,
                max_fix_iterations=max_fix_iterations,
                quality_agent=quality_agent
            )
            logger.info(f"Code quality validation: ENABLED (max {max_fix_iterations} fix iterations)")
        else:
            self.validation_pipeline = None
            logger.info("Code quality validation: DISABLED")
        
        logger.info(f"Initializing {self.AGENT_NAME} ({iac_format})...")
        logger.info(f"  Primary Model: {model_name}")
        
        # Create toolset with Bing + MS Learn MCP + format-specific MCP
        mcp_servers = ["mslearn"]
        if iac_format == "bicep":
            mcp_servers.append("bicep")
            logger.info("  Added Bicep MCP server for format-specific guidance")
        elif iac_format == "terraform":
            mcp_servers.append("terraform")
            logger.info("  Added Terraform MCP server for format-specific guidance")
        
        self.tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=mcp_servers,
        )
        
        # Load instructions from YAML based on IaC format
        base_instructions = get_module_development_agent_instructions(iac_format)
        
        tool_instructions = get_tool_instructions()
        self.full_instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Create agent
        self._create_agent()
        
        logger.info(f"✓ {self.AGENT_NAME} initialized (Agent ID: {self.agent.id})")
    
    def _create_agent(self):
        """Create the Azure AI agent."""
        try:
            logger.info(f"Creating agent with model: {self.model_name}")
            self.agent = self.agents_client.create_agent(
                model=self.model_name,
                name=f"{self.AGENT_NAME}_{self.iac_format}",
                instructions=self.full_instructions,
                tools=self.tool_config.tools,
                tool_resources=self.tool_config.tool_resources,
            )
            logger.debug(f"Agent created: {self.agent.id}")
            logger.info(f"✓ Agent created successfully with {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to create agent with model '{self.model_name}': {e}")
            # Try fallback model if configured
            if hasattr(self, 'fallback_model') and self.fallback_model:
                logger.warning(f"Retrying with fallback model: {self.fallback_model}")
                self.agent = self.agents_client.create_agent(
                    model=self.fallback_model,
                    name=f"{self.AGENT_NAME}_{self.iac_format}",
                    instructions=self.full_instructions,
                    tools=self.tool_config.tools,
                    tool_resources=self.tool_config.tool_resources,
                )
                logger.info(f"✓ Agent created with fallback model: {self.agent.id}")
            else:
                raise
    
    async def generate_modules(
        self,
        mappings: List[ModuleMapping],
        output_dir: Path,
        progress_callback=None,
    ) -> ModuleDevelopmentResult:
        """
        Generate IaC modules from module mappings.
        
        Args:
            mappings: List of module mappings from ModuleMappingAgent
            output_dir: Directory to save generated modules
            progress_callback: Optional callback(module_name, file_path) for progress updates
        
        Returns:
            ModuleDevelopmentResult with generated modules
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"STAGE 4: Module Development ({self.iac_format.upper()})")
        logger.info("=" * 80)
        logger.info(f"Modules to generate: {len(mappings)}")
        logger.info(f"Output directory: {output_dir}")
        
        # Debug: Log what mappings we received
        if len(mappings) == 0:
            logger.error("⚠️ CRITICAL: No mappings provided to module development agent!")
            logger.error("   Cannot generate modules without mappings.")
            logger.error("   This indicates Module Mapping Agent returned empty results.")
            return ModuleDevelopmentResult(
                modules=[],
                total_count=0,
                iac_format=self.iac_format,
                output_directory=output_dir,
                agent_id=self.agent.id if self.agent else None,
                thread_id=None,
            )
        
        logger.info(f"✓ Received {len(mappings)} module mappings:")
        for i, mapping in enumerate(mappings[:3], 1):  # Show first 3
            logger.info(f"  {i}. {mapping.service_requirement.service_type} -> {mapping.module_source}")
        if len(mappings) > 3:
            logger.info(f"  ... and {len(mappings) - 3} more")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create thread
        self.thread = self.agents_client.threads.create()
        logger.info(f"Created thread: {self.thread.id}")
        
        # Initialize CodeQualityAgent ONCE before parallel generation (if validation enabled)
        quality_agent_context = None
        if self.enable_validation and self.validation_pipeline and self.validation_pipeline.quality_agent:
            quality_agent = self.validation_pipeline.quality_agent
            logger.info(f"Initializing CodeQualityAgent for validation across all modules...")
            quality_agent_context = quality_agent.__aenter__()
            await quality_agent_context  # Enter the context
            logger.info(f"✓ CodeQualityAgent initialized (will be reused for all {len(mappings)} modules)")
        
        try:
            # Generate modules IN PARALLEL using multiple concurrent agents
            logger.info(f"\n{'='*80}")
            logger.info("PARALLEL MODULE GENERATION (Stage 4: Reusable Modules Only)")
            logger.info(f"{'='*80}")
            logger.info(f"Spawning {len(mappings)} concurrent module generation tasks...")
            
            # Create parallel generation tasks
            tasks = []
            for i, mapping in enumerate(mappings, 1):
                task = self._generate_module_with_retry(
                    mapping=mapping,
                    output_dir=output_dir,
                    index=i,
                    total=len(mappings),
                    progress_callback=progress_callback
                )
                tasks.append(task)
            
            # Execute all module generations in parallel
            logger.info(f"🚀 Starting parallel generation of {len(tasks)} reusable modules...")
            generated_modules = await asyncio.gather(*tasks, return_exceptions=True)
        
        finally:
            # Cleanup CodeQualityAgent after all modules are generated
            if quality_agent_context is not None:
                try:
                    # Call __aexit__ on the agent itself (not through validation_pipeline)
                    if self.validation_pipeline and self.validation_pipeline.quality_agent:
                        quality_agent = self.validation_pipeline.quality_agent
                        await quality_agent.__aexit__(None, None, None)
                        logger.info(f"✓ CodeQualityAgent cleaned up after processing {len(mappings)} modules")
                        
                        # Clear the agent reference
                        self.validation_pipeline.quality_agent = None
                except Exception as e:
                    logger.warning(f"Failed to cleanup CodeQualityAgent: {e}", exc_info=True)
        
        # Filter out exceptions and log any failures
        successful_modules = []
        for i, result in enumerate(generated_modules, 1):
            if isinstance(result, Exception):
                mapping = mappings[i-1]
                logger.error(f"❌ [{i}/{len(mappings)}] Failed: {mapping.service_requirement.resource_name}")
                logger.error(f"   Error: {str(result)}")
            else:
                successful_modules.append(result)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ Successfully generated {len(successful_modules)}/{len(mappings)} reusable modules")
        if len(successful_modules) < len(mappings):
            logger.warning(f"⚠️  {len(mappings) - len(successful_modules)} modules failed to generate")
        
        # Validation summary
        validation_summary = {}
        if self.enable_validation:
            validation_stats = {
                "passed": len([m for m in successful_modules if m.validation_status == "pass"]),
                "warnings": len([m for m in successful_modules if m.validation_status == "warning"]),
                "failed": len([m for m in successful_modules if m.validation_status == "fail"]),
                "not_validated": len([m for m in successful_modules if m.validation_status == "not_validated"]),
                "total_errors": sum(m.validation_errors for m in successful_modules),
                "total_warnings": sum(m.validation_warnings for m in successful_modules),
            }
            
            validation_summary = validation_stats
            
            logger.info(f"\n{'='*80}")
            logger.info("CODE QUALITY VALIDATION SUMMARY")
            logger.info(f"{'='*80}")
            logger.info(f"✅ Passed:        {validation_stats['passed']}/{len(successful_modules)}")
            if validation_stats['warnings'] > 0:
                logger.warning(f"⚠️  With Warnings: {validation_stats['warnings']}/{len(successful_modules)} ({validation_stats['total_warnings']} warnings)")
            if validation_stats['failed'] > 0:
                logger.error(f"❌ Failed:        {validation_stats['failed']}/{len(successful_modules)} ({validation_stats['total_errors']} errors)")
            if validation_stats['not_validated'] > 0:
                logger.info(f"⏭️  Not Validated: {validation_stats['not_validated']}/{len(successful_modules)}")
            
            # List failed modules for user attention
            if validation_stats['failed'] > 0:
                logger.error(f"\n⚠️  Modules requiring attention:")
                for module in successful_modules:
                    if module.validation_status == "fail":
                        logger.error(f"   • {module.module_name} ({module.validation_errors} errors)")
                        report_path = Path(module.file_path).parent / "validation_report.json"
                        if report_path.exists():
                            logger.error(f"     Report: {report_path}")
        
        result = ModuleDevelopmentResult(
            modules=successful_modules,  # Use successful_modules, not generated_modules (which contains exceptions)
            total_count=len(successful_modules),
            iac_format=self.iac_format,
            output_directory=output_dir,
            agent_id=self.agent.id,
            thread_id=self.thread.id,
            validation_enabled=self.enable_validation,
            validation_summary=validation_summary,
        )
        
        logger.info(f"\n✓ Successfully generated {result.total_count} modules")
        return result
    
    async def _generate_module_with_retry(
        self,
        mapping: ModuleMapping,
        output_dir: Path,
        index: int,
        total: int,
        progress_callback: Optional[callable] = None,
        max_retries: int = 5
    ) -> GeneratedModule:
        """Generate a single module with retry logic and throttle handling."""
        import time
        import random
        
        service_name = mapping.service_requirement.resource_name
        service_type = mapping.service_requirement.service_type
        arm_type = getattr(mapping.service_requirement, 'arm_type', None)
        
        # Extract module folder name from arm_type or fall back to service_type
        if arm_type:
            # e.g., Microsoft.ApiManagement/service -> apimanagement-service
            module_type = arm_type.replace('Microsoft.', '').replace('/', '-').lower()
        else:
            # Fallback: use service_type and sanitize
            module_type = service_type.lower().replace(' ', '-').replace('_', '-')
            logger.warning(f"   ⚠️  arm_type missing, using service_type: {module_type}")
        
        # Calculate progress percentage
        progress_pct = 0.70 + (0.15 * (index - 1) / total)
        
        logger.info(f"\n📦 [{index}/{total}] Module Type: {module_type}")
        logger.info(f"   ARM Type: {arm_type}")
        logger.info(f"   Service: {service_name}")
        logger.info(f"   AVM Source: {mapping.module_source}")
        
        # Progress callback - starting (show module type, not resource name)
        if progress_callback and asyncio.iscoroutinefunction(progress_callback):
            await progress_callback("generating", f"[{index}/{total}] Module: {module_type} - Generating complete reusable module...", progress_pct)
        
        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                module = await self._generate_single_module(
                    mapping=mapping,
                    output_dir=output_dir,
                    index=index,
                    total=total,
                    progress_callback=progress_callback
                )
                
                logger.info(f"   ✅ [{index}/{total}] Module: {module_type} complete")
                logger.info(f"      Path: {module.file_path}")
                logger.info(f"      Files: main.tf, variables.tf, outputs.tf, README.md")
                
                # Progress callback - completed (show module type)
                if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                    complete_pct = 0.70 + (0.15 * index / total)
                    await progress_callback("completed", f"[{index}/{total}] ✅ Module: {module_type}", complete_pct)
                
                return module
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a throttling error (429)
                if "429" in error_msg or "throttl" in error_msg.lower() or "rate limit" in error_msg.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"   ⏳ [{index}/{total}] Throttled: Module {module_type}")
                        logger.warning(f"      Cooling down for {wait_time:.1f}s (attempt {attempt+1}/{max_retries})...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"   ❌ [{index}/{total}] Max retries reached: Module {module_type}")
                        raise
                else:
                    # Non-throttling error - fail immediately
                    logger.error(f"   ❌ [{index}/{total}] Error: Module {module_type}")
                    logger.error(f"      {error_msg}")
                    raise
        
        raise Exception(f"Failed to generate module after {max_retries} attempts")
    
    async def _generate_single_module(
        self,
        mapping: ModuleMapping,
        output_dir: Path,
        index: int = 1,
        total: int = 1,
        progress_callback = None,
    ) -> GeneratedModule:
        """Generate a single IaC module."""
        import json
        
        # Extract module type for logging and progress callbacks
        service_name = mapping.service_requirement.resource_name
        service_type = mapping.service_requirement.service_type
        arm_type = getattr(mapping.service_requirement, 'arm_type', None)
        
        # Extract module folder name from arm_type or fall back to service_type
        if arm_type:
            # e.g., Microsoft.ApiManagement/service -> apimanagement-service
            module_type = arm_type.replace('Microsoft.', '').replace('/', '-').lower()
        else:
            # Fallback: use service_type and sanitize
            module_type = service_type.lower().replace(' ', '-').replace('_', '-')
            logger.warning(f"   ⚠️  arm_type missing, using service_type: {module_type}")
        
        # Calculate progress percentage for validation callbacks
        progress_pct = 0.70 + (0.15 * (index - 1) / total) if total > 0 else 0.70
        
        logger.info(f"Starting module generation for: {service_name}")
        logger.debug(f"Module type: {module_type}")
        logger.debug(f"Reference module: {mapping.module_source}")
        logger.debug(f"IaC format: {self.iac_format}")
        
        # Load prompt template from external file based on IaC format
        template_name = f"module_development_{self.iac_format.lower()}"
        template = get_prompt_template(template_name)
        
        # Prepare template variables
        service_info_json = json.dumps(mapping.service_requirement.to_dict(), indent=2)
        required_inputs_str = ', '.join(mapping.required_inputs)
        optional_inputs_str = ', '.join(mapping.optional_inputs[:10]) + ('...' if len(mapping.optional_inputs) > 10 else '')
        best_practices_str = ', '.join(mapping.best_practices[:5]) + ('...' if len(mapping.best_practices) > 5 else '')
        
        # Format prompt with service-specific values
        prompt = template.format(
            iac_format_upper=self.iac_format.upper(),
            iac_format=self.iac_format,
            service_info_json=service_info_json,
            module_source=mapping.module_source,
            module_documentation=mapping.module_documentation,
            module_version=mapping.module_version,
            folder_path=mapping.folder_path if mapping.folder_path else 'modules/resource',
            required_inputs=required_inputs_str,
            optional_inputs=optional_inputs_str,
            best_practices=best_practices_str,
            arm_type=mapping.service_requirement.arm_type,
            service_type=mapping.service_requirement.service_type
        )
        
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        # Send message
        logger.info("Sending module generation request to agent...")
        message = self.agents_client.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=prompt,
        )
        logger.debug(f"Message created: {message.id}")
        
        # Run agent
        logger.info("Running agent to generate code...")
        run = self.agents_client.runs.create_and_process(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
            max_completion_tokens=8000,  # Sufficient for module code generation
        )
        
        logger.info(f"Agent run completed with status: {run.status}")
        
        # Check for truncation
        if run.status == "completed" and hasattr(run, 'incomplete_details') and run.incomplete_details:
            logger.warning(f"⚠️ Response may be truncated: {run.incomplete_details.reason}")
            if run.incomplete_details.reason == "max_completion_tokens":
                logger.error("❌ Module code was truncated due to token limit!")
        
        if run.status != "completed":
            logger.error(f"Module generation failed: {run.status}")
            if hasattr(run, 'last_error') and run.last_error:
                logger.error(f"Error details: {run.last_error}")
            raise RuntimeError(f"Module generation failed: {run.status}")
        
        # Get last message from agent (Phase 1 pattern)
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            raise RuntimeError("No response from agent")
        
        generated_code = last_msg.text.value
        
        # Debug: Save raw response for troubleshooting
        debug_file = output_dir / "_debug_agent_response.txt"
        debug_file.write_text(f"=== AGENT RESPONSE START ===\n{generated_code}\n=== AGENT RESPONSE END ===", encoding='utf-8')
        logger.debug(f"Saved raw agent response to: {debug_file}")
        
        # Parse and save files - now handles both modules/ and deployment/ layers
        # The agent generates complete folder structure in response
        if self.iac_format == "terraform":
            files = self._parse_terraform_files(generated_code, output_dir)
        else:
            files = self._parse_bicep_files(generated_code, output_dir)
        
        # Return first file path as primary (for logging)
        primary_file = files[0] if files else output_dir / "main.tf"
        
        # Use mapping folder_path for module_name tracking
        module_path = mapping.folder_path if mapping.folder_path else mapping.service_requirement.resource_name
        
        # Extract module directory (where the module was saved)
        module_dir = primary_file.parent
        
        # VALIDATION PIPELINE: Validate generated code
        validation_status = "not_validated"
        validation_errors = 0
        validation_warnings = 0
        
        if self.enable_validation and self.validation_pipeline:
            logger.info(f"   🔍 Validating module: {module_dir.name}")
            
            # Progress callback - validating
            if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                await progress_callback("validating", f"[{index}/{total}] 🔍 Validating: {module_type}...", progress_pct + 0.02)
            
            try:
                # Read back the generated files for validation
                generated_files = {}
                for file_path in files:
                    rel_path = file_path.relative_to(module_dir)  # Relative to module_dir, not output_dir
                    generated_files[str(rel_path)] = file_path.read_text(encoding='utf-8')
                
                # Run validation pipeline (CodeQualityAgent already initialized at module-level)
                # No need to use async with - agent is shared across all parallel tasks
                validated_code, validation_result = await self.validation_pipeline.run(
                    generated_code=generated_files,
                    output_dir=module_dir
                )
                
                validation_status = validation_result.status
                validation_errors = validation_result.error_count
                validation_warnings = validation_result.warning_count
                
                # PHASE 1 validation: Only format/syntax checks (no provider/module validation)
                if validation_result.status == "pass":
                    logger.info(f"   ✅ Syntax OK: {module_dir.name}")
                    if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback("syntax_ok", f"[{index}/{total}] ✅ Syntax OK: {module_type}", progress_pct + 0.04)
                elif validation_result.status == "warning":
                    logger.warning(f"   ⚠️  Format issues ({validation_warnings}): {module_dir.name}")
                    if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback("syntax_warning", f"[{index}/{total}] ⚠️  {validation_warnings} format issues: {module_type}", progress_pct + 0.04)
                else:
                    # Syntax errors (not provider/module errors which are expected in PHASE 1)
                    logger.error(f"   ⚠️  Syntax errors ({validation_errors}): {module_dir.name}")
                    if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback("syntax_errors", f"[{index}/{total}] ⚠️  {validation_errors} syntax errors: {module_type}", progress_pct + 0.04)
                
                # Save validation report
                report_path = module_dir / "validation_report.json"
                create_validation_report(validation_result, report_path)
                logger.debug(f"   📄 Validation report: {report_path.name}")
                
            except Exception as e:
                logger.error(f"   ⚠️  Validation error for {module_dir.name}: {e}")
                validation_status = "error"
                if progress_callback and asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("validation_error", f"[{index}/{total}] ⚠️  Validation error: {module_type}", progress_pct + 0.04)
        
        return GeneratedModule(
            module_name=module_path,
            iac_format=self.iac_format,
            file_path=primary_file,
            content=generated_code,
            variables=mapping.required_inputs,
            outputs=[],  # Could parse from generated code
            dependencies=mapping.service_requirement.dependencies,
            validation_status=validation_status,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
        )
    
    def _parse_terraform_files(self, code: str, base_dir: Path) -> List[Path]:
        """Parse and save Terraform files from agent response with full folder structure.
        
        Expected format:
        # FILE: modules/cognitive-services-account/main.tf
        # FILE: environments/dev/main.tf
        """
        saved_files = []
        
        # Simple parser to extract files with paths
        current_file = None
        current_content = []
        
        for line in code.split('\n'):
            if 'FILE:' in line and '.tf' in line:
                # Save previous file
                if current_file and current_content:
                    # Clean content: remove code fences and empty lines at start/end
                    cleaned_content = self._clean_code_content(current_content)
                    file_path = base_dir / current_file
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(cleaned_content, encoding='utf-8')
                    saved_files.append(file_path)
                    logger.debug(f"  Saved: {current_file}")
                
                # Start new file - extract full path (e.g., "modules/storage/main.tf")
                file_marker = line.split('FILE:')[1].strip()
                # Remove any markdown code fence markers
                current_file = file_marker.split('```')[0].strip()
                # Strip leading modules/ or deployment/ since base_dir already includes it
                if current_file.startswith('modules/'):
                    current_file = current_file[len('modules/'):]
                elif current_file.startswith('deployment/'):
                    current_file = current_file[len('deployment/'):]
                current_content = []
            elif 'FILE:' in line and '.md' in line:
                # Handle README.md files
                if current_file and current_content:
                    cleaned_content = self._clean_markdown_content(current_content)
                    file_path = base_dir / current_file
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(cleaned_content, encoding='utf-8')
                    saved_files.append(file_path)
                    logger.debug(f"  Saved: {current_file}")
                
                file_marker = line.split('FILE:')[1].strip()
                current_file = file_marker.split('```')[0].strip()
                # Strip leading modules/ or deployment/
                if current_file.startswith('modules/'):
                    current_file = current_file[len('modules/'):]
                elif current_file.startswith('deployment/'):
                    current_file = current_file[len('deployment/'):]
                current_content = []
            elif 'FILE:' in line and '.example' in line:
                # Handle .example files like terraform.tfvars.example
                if current_file and current_content:
                    cleaned_content = self._clean_code_content(current_content)
                    file_path = base_dir / current_file
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(cleaned_content, encoding='utf-8')
                    saved_files.append(file_path)
                    logger.debug(f"  Saved: {current_file}")
                
                file_marker = line.split('FILE:')[1].strip()
                current_file = file_marker.split('```')[0].strip()
                # Strip leading modules/ or deployment/
                if current_file.startswith('modules/'):
                    current_file = current_file[len('modules/'):]
                elif current_file.startswith('deployment/'):
                    current_file = current_file[len('deployment/'):]
                current_content = []
            elif current_file:
                # Skip marker lines but keep all content
                current_content.append(line)
        
        # Save last file
        if current_file and current_content:
            if current_file.endswith('.md'):
                cleaned_content = self._clean_markdown_content(current_content)
            else:
                cleaned_content = self._clean_code_content(current_content)
            file_path = base_dir / current_file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(cleaned_content, encoding='utf-8')
            saved_files.append(file_path)
            logger.debug(f"  Saved: {current_file}")
        
        # If no files detected, save as single main.tf in modules/ subdirectory
        if not saved_files:
            fallback_path = base_dir / "modules" / "default" / "main.tf"
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            fallback_path.write_text(code, encoding='utf-8')
            saved_files.append(fallback_path)
            logger.debug(f"  Saved: modules/default/main.tf (fallback)")
        
        return saved_files
    
    def _clean_code_content(self, lines: List[str]) -> str:
        """Clean code content by removing markdown fences and normalizing whitespace."""
        content = '\n'.join(lines)
        
        # Remove markdown code fences (```hcl, ```terraform, ```bicep, ```)
        import re
        content = re.sub(r'^```(?:hcl|terraform|bicep)?\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
        
        # Split back into lines and remove leading/trailing empty lines
        clean_lines = content.split('\n')
        
        # Remove leading empty lines
        while clean_lines and not clean_lines[0].strip():
            clean_lines.pop(0)
        
        # Remove trailing empty lines
        while clean_lines and not clean_lines[-1].strip():
            clean_lines.pop()
        
        return '\n'.join(clean_lines)
    
    def _clean_markdown_content(self, lines: List[str]) -> str:
        """Clean markdown content by normalizing whitespace but preserving formatting."""
        content = '\n'.join(lines)
        
        # For markdown, only remove code fences if they're wrapping the entire content
        import re
        content = re.sub(r'^```(?:markdown|md)?\s*\n', '', content)
        content = re.sub(r'\n```\s*$', '', content)
        
        # Remove leading/trailing whitespace but preserve internal structure
        return content.strip()
    
    def _parse_bicep_files(self, code: str, base_dir: Path) -> List[Path]:
        """Parse and save Bicep files from agent response with full folder structure.
        
        Expected format:
        # FILE: modules/cognitive-services-account/main.bicep
        # FILE: environments/dev/main.bicep
        """
        saved_files = []
        
        # Log first 500 chars for debugging
        logger.debug(f"Parsing Bicep response (first 500 chars): {code[:500]}")
        
        # Simple parser for Bicep files
        current_file = None
        current_content = []
        
        for line in code.split('\n'):
            # Look for FILE: markers (with or without #)
            if 'FILE:' in line and ('.bicep' in line or '.json' in line or '.md' in line):
                # Save previous file
                if current_file and current_content:
                    self._save_bicep_file(base_dir, current_file, current_content, saved_files)
                
                # Start new file - extract full path
                file_marker = line.split('FILE:')[1].strip()
                current_file = file_marker.split('```')[0].strip()
                # Strip leading modules/ or deployment/ since base_dir already includes it
                if current_file.startswith('modules/'):
                    current_file = current_file[len('modules/'):]
                elif current_file.startswith('deployment/'):
                    current_file = current_file[len('deployment/'):]
                current_content = []
            elif current_file:
                current_content.append(line)
        
        # Save last file
        if current_file and current_content:
            self._save_bicep_file(base_dir, current_file, current_content, saved_files)
        
        # If no files detected with FILE: markers, try to detect JSON structure
        if not saved_files:
            logger.warning("No FILE: markers found, attempting JSON parse...")
            saved_files = self._parse_bicep_json_response(code, base_dir)
        
        # Final fallback: save as single main.bicep
        if not saved_files:
            logger.warning("No structured response detected, using fallback...")
            cleaned_code = self._clean_bicep_code(code)
            if cleaned_code.strip():
                fallback_path = base_dir / "modules" / "default" / "main.bicep"
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
                fallback_path.write_text(cleaned_code, encoding='utf-8')
                saved_files.append(fallback_path)
                logger.debug(f"  Saved: modules/default/main.bicep (fallback)")
        
        return saved_files
    
    def _save_bicep_file(self, base_dir: Path, filename: str, content_lines: List[str], saved_files: List[Path]):
        """Helper to save a Bicep file with content cleaning."""
        file_path = base_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        content_str = '\n'.join(content_lines)
        cleaned_content = self._clean_bicep_code(content_str)
        
        if cleaned_content.strip():  # Only save if there's actual content
            file_path.write_text(cleaned_content, encoding='utf-8')
            saved_files.append(file_path)
            logger.debug(f"  Saved: {filename} ({len(cleaned_content)} bytes)")
        else:
            logger.warning(f"  Skipped: {filename} (empty after cleaning)")
    
    def _clean_bicep_code(self, code: str) -> str:
        """Clean Bicep code by removing markdown fences."""
        if '```bicep' in code:
            code = code.split('```bicep')[1].split('```')[0]
        elif '```' in code:
            # Try to extract first code block
            parts = code.split('```')
            if len(parts) >= 3:
                code = parts[1]
        
        return code.strip()
    
    def _parse_bicep_json_response(self, code: str, base_dir: Path) -> List[Path]:
        """Try to parse response as JSON with files dictionary."""
        import json
        import re
        
        saved_files = []
        
        try:
            # Try to find JSON block
            json_match = re.search(r'\{[\s\S]*"files"[\s\S]*\}', code)
            if json_match:
                json_data = json.loads(json_match.group())
                files_dict = json_data.get('files', {})
                
                for filename, content in files_dict.items():
                    file_path = base_dir / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
                    saved_files.append(file_path)
                    logger.debug(f"  Saved from JSON: {filename}")
        except Exception as e:
            logger.debug(f"JSON parse attempt failed: {e}")
        
        return saved_files
    
    def cleanup(self):
        """Cleanup agent and thread resources (Phase 1 pattern)."""
        # Note: CodeQualityAgent is now managed in generate_modules() lifecycle
        # It's initialized before parallel generation and cleaned up after
        # No need to cleanup here as it's already done in the finally block
        
        if self.agent:
            try:
                self.agents_client.delete_agent(self.agent.id)
                logger.info(f"Deleted ModuleDevelopmentAgent: {self.agent.id}")
            except Exception as e:
                logger.warning(f"Failed to delete agent: {e}")
            self.agent = None
        
        if self.thread:
            try:
                self.agents_client.threads.delete(self.thread.id)
                logger.info(f"Deleted thread: {self.thread.id}")
            except Exception as e:
                logger.warning(f"Failed to delete thread: {e}")
            self.thread = None
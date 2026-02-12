"""
ModuleMappingAgent: Maps Azure services to Azure Verified Modules (AVM) or Terraform modules.

This agent uses Bing Grounding + MS Learn MCP to find the best module patterns
for each service, following Azure/HashiCorp best practices.

NO HARD CODING - Always references latest documentation and module registry.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole, ThreadRun, RunStatus

from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.agents.service_analysis_agent import ServiceRequirement
from synthforge.prompts import get_module_mapping_agent_instructions, get_iac_prompt_template

logger = logging.getLogger(__name__)


@dataclass
class ModuleMapping:
    """Represents a mapping from service requirement to IaC module."""
    
    service_requirement: ServiceRequirement
    module_source: str  # AVM module name or Terraform registry URL
    module_version: str  # Latest stable version
    module_documentation: str  # URL to module docs
    required_inputs: List[str] = field(default_factory=list)  # Required module inputs
    optional_inputs: List[str] = field(default_factory=list)  # Optional module inputs
    folder_path: str = ""  # Path for the module (modules/service-name)
    environment_path: str = ""  # Path for environment orchestration (environments/dev)
    best_practices: List[str] = field(default_factory=list)  # Best practice notes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_requirement": self.service_requirement.to_dict(),
            "module_source": self.module_source,
            "module_version": self.module_version,
            "module_documentation": self.module_documentation,
            "required_inputs": self.required_inputs,
            "optional_inputs": self.optional_inputs,
            "folder_path": self.folder_path,
            "environment_path": self.environment_path,
            "best_practices": self.best_practices,
        }


@dataclass
class ModuleMappingResult:
    """Result from module mapping stage."""
    
    mappings: List[ModuleMapping]
    total_count: int
    failed_count: int = 0  # Number of failed mappings
    iac_format: str = "terraform"  # "terraform", "bicep", or "both"
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mappings": [m.to_dict() for m in self.mappings],
            "total_count": self.total_count,
            "failed_count": self.failed_count,
            "iac_format": self.iac_format,
            "agent_id": self.agent_id,
            "thread_id": self.thread_id,
        }


class ModuleMappingAgent:
    """
    Agent for mapping services to IaC modules (AVM for Bicep, Terraform Registry for Terraform).
    
    Uses Azure AI Foundry with Bing Grounding + MS Learn MCP to:
    1. Find Azure Verified Modules (AVM) for Bicep
    2. Find official Terraform azurerm provider modules
    3. Identify module versions, inputs, and best practices
    4. Generate module usage examples
    """
    
    AGENT_NAME = "ModuleMappingAgent"
    
    def __init__(
        self,
        agents_client: AgentsClient,
        model_name: str,
        bing_connection_name: str,
        ms_learn_mcp_url: Optional[str] = None,
    ):
        """
        Initialize ModuleMappingAgent.
        
        Args:
            agents_client: Azure AI Agents client
            model_name: Model deployment name (e.g., "gpt-4o")
            bing_connection_name: Bing Grounding connection name
            ms_learn_mcp_url: MS Learn MCP server URL
        """
        self.agents_client = agents_client
        self.model_name = model_name
        self.agent = None
        self.thread = None
        
        logger.info(f"Initializing {self.AGENT_NAME}...")
        
        # Create toolset with Bing + MS Learn MCP
        self.tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"],
        )
        
        # Load agent instructions from YAML
        base_instructions = get_module_mapping_agent_instructions()
        tool_instructions = get_tool_instructions()
        self.full_instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Create agent
        self._create_agent()
        
        logger.info(f"✓ {self.AGENT_NAME} initialized (Agent ID: {self.agent.id})")
    
    def _create_agent(self):
        """Create the Azure AI agent."""
        self.agent = self.agents_client.create_agent(
            model=self.model_name,
            name=self.AGENT_NAME,
            instructions=self.full_instructions,
            tools=self.tool_config.tools,
            tool_resources=self.tool_config.tool_resources,
            temperature=0.1,  # Slight creativity for module selection
            top_p=0.95,
            response_format={"type": "json_object"},  # Prevent markdown wrapping
        )
        logger.debug(f"Agent created: {self.agent.id}")
    
    async def map_services(
        self,
        services: List[ServiceRequirement],
        iac_format: str = "terraform",
    ) -> ModuleMappingResult:
        """
        Map services to IaC modules (parallelized per service).
        
        Args:
            services: List of service requirements from ServiceAnalysisAgent
            iac_format: "terraform", "bicep", or "both"
        
        Returns:
            ModuleMappingResult with module mappings
        """
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 3: Module Mapping")
        logger.info("=" * 80)
        logger.info(f"IaC Format: {iac_format}")
        logger.info(f"Services to map: {len(services)}")
        logger.info("Parallelizing mapping for each service...")
        
        # Map each service in parallel using asyncio.gather
        import asyncio
        
        mapping_tasks = [
            self._map_single_service(service, iac_format, idx + 1, len(services))
            for idx, service in enumerate(services)
        ]
        
        logger.info(f"Launching {len(mapping_tasks)} parallel mapping tasks...")
        
        # Execute all mappings in parallel
        mapping_results = await asyncio.gather(*mapping_tasks, return_exceptions=True)
        
        # Collect successful mappings and log failures
        successful_mappings = []
        failed_count = 0
        
        for idx, result in enumerate(mapping_results):
            service = services[idx]
            if isinstance(result, Exception):
                logger.error(f"✗ Failed to map {service.service_type}: {result}")
                failed_count += 1
            elif result:
                successful_mappings.append(result)
                logger.info(f"✓ Mapped {service.service_type} to {result.module_source}")
            else:
                logger.warning(f"⚠ No mapping returned for {service.service_type}")
                failed_count += 1
        
        logger.info(f"\nMapping complete: {len(successful_mappings)} successful, {failed_count} failed")
        
        return ModuleMappingResult(
            mappings=successful_mappings,
            total_count=len(successful_mappings),
            failed_count=failed_count,
            iac_format=iac_format,
        )
    
    async def _map_single_service(
        self,
        service: ServiceRequirement,
        iac_format: str,
        index: int,
        total: int,
    ) -> Optional[ModuleMapping]:
        """
        Map a single service to an IaC module.
        
        Args:
            service: Service requirement to map
            iac_format: "terraform" or "bicep"
            index: Current service index (for logging)
            total: Total number of services
        
        Returns:
            ModuleMapping or None if mapping fails
        """
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            thread = None
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"[{index}/{total}] Retry {attempt}/{max_retries} for {service.service_type} after {delay}s delay...")
                    await asyncio.sleep(delay)
                else:
                    logger.info(f"[{index}/{total}] Mapping {service.service_type}...")
                
                # Create a separate thread for this service
                thread = self.agents_client.threads.create()
                
                try:
                    # Prepare mapping prompt for single service
                    prompt = self._create_single_service_prompt(service, iac_format)
                    
                    # Send message
                    message = self.agents_client.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content=prompt,
                    )
                    
                    # Create and poll run
                    run = self.agents_client.runs.create_and_process(
                        thread_id=thread.id,
                        agent_id=self.agent.id,
                        max_completion_tokens=4000,  # Smaller limit per service
                    )
                    
                    # Process result
                    if run.status == "completed":
                        result = await self._process_single_service_result(run, thread.id, service, iac_format)
                        if result:  # Successfully got a mapping
                            return result
                        else:
                            logger.warning(f"[{index}/{total}] Empty result for {service.service_type}, attempt {attempt + 1}/{max_retries}")
                            if attempt == max_retries - 1:
                                return None
                            # Otherwise continue to retry
                    else:
                        logger.error(f"[{index}/{total}] Mapping failed for {service.service_type}: {run.status}, attempt {attempt + 1}/{max_retries}")
                        if attempt == max_retries - 1:
                            return None
                        # Otherwise continue to retry
                        
                except Exception as e:
                    logger.error(f"[{index}/{total}] Error mapping {service.service_type}: {e}, attempt {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        return None
                    # Otherwise continue to retry
                    
                finally:
                    # Clean up thread after each attempt (success or failure)
                    if thread:
                        try:
                            self.agents_client.threads.delete(thread.id)
                            logger.debug(f"[{index}/{total}] Deleted thread: {thread.id}")
                        except Exception as cleanup_error:
                            logger.warning(f"[{index}/{total}] Failed to delete thread {thread.id}: {cleanup_error}")
                
            except Exception as outer_e:
                logger.error(f"[{index}/{total}] Outer exception for {service.service_type}: {outer_e}, attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    return None
        
        logger.error(f"[{index}/{total}] Failed to map {service.service_type} after {max_retries} attempts")
        return None
    
    def _create_single_service_prompt(
        self,
        service: ServiceRequirement,
        iac_format: str,
    ) -> str:
        """Create mapping prompt for a single service."""
        import json
        
        service_json = json.dumps(service.to_dict(), indent=2)
        
        # Load prompt template from external file
        template = get_iac_prompt_template("module_mapping_single_service")
        
        # Format template with service-specific values
        prompt = template.format(
            iac_format_upper=iac_format.upper(),
            service_json=service_json,
            service_type=service.service_type,
            arm_type=service.arm_type if service.arm_type else 'N/A'
        )
        
        return prompt
    
    def _create_mapping_prompt(
        self,
        services: List[ServiceRequirement],
        iac_format: str,
    ) -> str:
        """Create the mapping prompt with service list."""
        import json
        
        services_json = json.dumps([s.to_dict() for s in services], indent=2)
        
        prompt = f"""# Service to Module Mapping Task

Map the following Azure services to appropriate IaC modules for {iac_format.upper()}.

## Service Requirements
```json
{services_json}
```

## Your Task
For EACH service:
1. Use Bing Grounding to search for the latest module:
   - For Bicep: "Azure Verified Modules {{service_type}} site:github.com/Azure"
   - For Terraform: "Terraform azurerm {{resource_type}} site:registry.terraform.io"

2. Use MS Learn MCP to find best practices:
   - microsoft_docs_search for Azure service documentation
   - Look for ARM schemas, configuration options

3. Extract complete module information:
   - Module source/name
   - Latest stable version
   - Required inputs
   - Optional inputs
   - Example usage from docs
   - Best practices

4. Consider service dependencies and configurations from the ServiceRequirement

## Output
Generate the ModuleMappingResult JSON with all mappings.
Output JSON directly (no markdown, just the JSON object).
"""
        
        return prompt
    
    async def _process_single_service_result(
        self,
        run,
        thread_id: str,
        service: ServiceRequirement,
        iac_format: str,
    ) -> Optional[ModuleMapping]:
        """Process result for a single service mapping."""
        import json
        import re
        
        # Get last message from agent
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=thread_id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            logger.error(f"No response from agent for {service.service_type}")
            return None
        
        # Extract JSON from response
        response_text = last_msg.text.value
        response_length = len(response_text)
        logger.debug(f"Response for {service.service_type}: {response_length} chars")
        
        # Check for empty response
        if not response_text or response_text.strip() == "":
            logger.error(f"❌ Empty response from agent for {service.service_type}")
            logger.error(f"Run status: {run.status}")
            if hasattr(run, 'incomplete_details') and run.incomplete_details:
                logger.error(f"Incomplete details: {run.incomplete_details.reason}")
            return None
        
        # Check for truncation
        if hasattr(run, 'incomplete_details') and run.incomplete_details:
            logger.warning(f"⚠️ Response truncated for {service.service_type}: {run.incomplete_details.reason}")
        
        # Clean and extract JSON
        response_text = response_text.strip()
        
        # IMPROVED: Try to find JSON object even if there's text before/after
        import re
        
        # Look for largest JSON structure (starts with { and ends with })
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        json_matches = list(re.finditer(json_pattern, response_text, re.DOTALL))
        
        if json_matches:
            # Use the largest JSON match (most complete)
            largest_match = max(json_matches, key=lambda m: len(m.group(0)))
            response_text = largest_match.group(0)
            logger.debug(f"Extracted JSON from position {largest_match.start()}-{largest_match.end()} ({len(response_text)} chars)")
        elif "```json" in response_text or "```" in response_text:
            # Fallback: Handle markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Manual fence removal
                response_text = response_text.replace("```json", "").replace("```", "")
        
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            result_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {service.service_type}: {e}")
            logger.error(f"Response length: {len(response_text)} chars")
            logger.error(f"First 500 chars of response: {response_text[:500]}")
            
            # Try repair
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            last_brace = response_text.rfind("}")
            if last_brace > 0:
                response_text = response_text[:last_brace + 1]
            
            try:
                result_data = json.loads(response_text)
                logger.info(f"✓ JSON repair successful for {service.service_type}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON even after repair for {service.service_type}")
                logger.error(f"Repaired text first 500 chars: {response_text[:500]}")
                return None
        
        # Create ModuleMapping from result
        try:
            mapping = ModuleMapping(
                service_requirement=service,
                module_source=result_data.get("module_source", ""),
                module_version=result_data.get("module_version", "latest"),
                module_documentation=result_data.get("module_documentation", ""),
                required_inputs=result_data.get("required_inputs", []),
                optional_inputs=result_data.get("optional_inputs", []),
                folder_path=result_data.get("folder_path", f"modules/{service.service_type.lower().replace(' ', '-')}"),
                environment_path=result_data.get("environment_path", "environments/dev"),
                best_practices=result_data.get("best_practices", []),
            )
            return mapping
        except Exception as e:
            logger.error(f"Failed to create ModuleMapping for {service.service_type}: {e}")
            return None
    
    async def _process_result(
        self,
        run: ThreadRun,
        services: List[ServiceRequirement],
        iac_format: str,
    ) -> ModuleMappingResult:
        """Process the agent's response and extract module mappings."""
        import json
        
        # Get last message from agent (Phase 1 pattern)
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            raise RuntimeError("No response from agent")
        
        # Extract JSON from response
        response_text = last_msg.text.value
        response_length = len(response_text)
        logger.info(f"Agent response length: {response_length} characters")
        
        # Check run status for truncation
        if run.status == "completed" and hasattr(run, 'incomplete_details') and run.incomplete_details:
            logger.warning(f"⚠️ Response may be truncated: {run.incomplete_details.reason}")
            if run.incomplete_details.reason == "max_completion_tokens":
                logger.error("❌ Response was truncated due to token limit!")
                logger.error("   Consider processing fewer services at once or increasing max_completion_tokens")
        
        logger.debug(f"Agent response:\n{response_text[:500]}...")
        
        # Parse JSON (handle markdown code blocks if present)
        response_text = response_text.strip()
        
        # Handle markdown code blocks - extract JSON between ``` markers
        if "```json" in response_text or "```" in response_text:
            # Find the JSON content between code fences using regex
            import re
            # Match ```json...``` or ```...```
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
                logger.info("✓ Extracted JSON from markdown code block")
            else:
                # Fallback: remove code fences manually
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                elif response_text.startswith("```"):
                    response_text = response_text[3:]
                
                # Remove everything after the closing code fence
                if "```" in response_text:
                    response_text = response_text[:response_text.index("```")]
        
        response_text = response_text.strip()
        
        try:
            result_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text (first 2000 chars):\n{response_text[:2000]}")
            logger.error(f"Around error position (char {e.pos}):\n{response_text[max(0, e.pos-200):min(len(response_text), e.pos+200)]}")
            
            # Try to fix common JSON issues
            logger.warning("Attempting to repair JSON...")
            
            # Remove trailing commas before closing braces/brackets
            import re
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            # Remove any text after the final closing brace (extra explanations)
            # Find the last } and truncate everything after it
            last_brace = response_text.rfind("}")
            if last_brace > 0 and last_brace < len(response_text) - 1:
                response_text = response_text[:last_brace + 1]
                logger.info("✓ Removed extra text after JSON")
            
            # Try parsing again
            try:
                result_data = json.loads(response_text)
                logger.info("✓ JSON repaired successfully")
            except json.JSONDecodeError as e2:
                logger.error(f"JSON repair failed: {e2}")
                raise RuntimeError(f"Agent returned invalid JSON. Error: {e}. Check logs for details.")
        
        # Log what the agent returned
        mappings_key = "mappings" if "mappings" in result_data else "service_mappings"
        logger.info(f"Module mapping agent returned {len(result_data.get(mappings_key, []))} mappings (using key: '{mappings_key}')")
        
        if len(result_data.get(mappings_key, [])) == 0:
            logger.warning("⚠ Agent returned 0 mappings!")
            logger.warning(f"Result data keys: {list(result_data.keys())}")
            logger.warning(f"Full agent response (first 1000 chars): {response_text[:1000]}")
        
        # Convert to ModuleMappingResult (handle both 'mappings' and 'service_mappings')
        mappings = []
        for mapping_data in result_data.get(mappings_key, []):
            # Handle different response structures
            if "main_module" in mapping_data:
                # Agent returned nested structure with main_module
                main_mod = mapping_data["main_module"]
                module_source = main_mod.get("module_source", "")
                required_inputs = main_mod.get("required_inputs", [])
                optional_inputs = main_mod.get("optional_inputs", [])
                best_practices = main_mod.get("built_in_features", [])
                documentation_url = main_mod.get("document_url", "")
                module_version = mapping_data.get("latest_version", "latest")
            else:
                # Agent returned flat structure
                module_source = mapping_data.get("module_source", "")
                required_inputs = mapping_data.get("required_inputs", [])
                optional_inputs = mapping_data.get("optional_inputs", [])
                best_practices = mapping_data.get("best_practices", [])
                documentation_url = mapping_data.get("module_documentation", "")
                module_version = mapping_data.get("module_version", "latest")
            
            # Reconstruct or extract ServiceRequirement
            if "service_requirement" in mapping_data:
                service_req = ServiceRequirement(**mapping_data["service_requirement"])
            else:
                # Build from flat fields
                service_req = ServiceRequirement(
                    service_type=mapping_data.get("service_type", ""),
                    resource_name=mapping_data.get("resource_name", ""),
                )
            
            # Create ModuleMapping
            mapping = ModuleMapping(
                service_requirement=service_req,
                iac_format=mapping_data.get("iac_format", iac_format),
                module_source=module_source,
                module_version=module_version,
                module_documentation=documentation_url,
                required_inputs=required_inputs,
                optional_inputs=optional_inputs,
                example_usage=mapping_data.get("example_usage", ""),
                best_practices=best_practices,
            )
            mappings.append(mapping)
        
        result = ModuleMappingResult(
            mappings=mappings,
            total_count=len(mappings),
            iac_format=iac_format,
            agent_id=self.agent.id,
            thread_id=self.thread.id,
        )
        
        logger.info(f"\n✓ Mapped {result.total_count} services to IaC modules")
        for mapping in mappings[:5]:  # Show first 5
            logger.info(f"  - {mapping.service_requirement.service_type}: {mapping.module_source}")
        if len(mappings) > 5:
            logger.info(f"  ... and {len(mappings) - 5} more")
        
        return result
    
    def cleanup(self):
        """Cleanup agent and thread resources (Phase 1 pattern)."""
        if self.agent:
            try:
                self.agents_client.delete_agent(self.agent.id)
                logger.info(f"Deleted agent: {self.agent.id}")
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

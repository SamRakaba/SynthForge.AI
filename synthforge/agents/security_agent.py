"""
Security Agent for SynthForge.AI.

Provides RBAC and security recommendations based on Azure Well-Architected Framework.

Uses azure.ai.agents.AgentsClient with Bing Grounding and MCP tools for Azure documentation lookup.
Agent chooses the best tool for each task - NO STATIC MAPPINGS.
"""

import asyncio
import json
import logging
from typing import Optional, List

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole

from synthforge.config import get_settings
from synthforge.models import (
    DataFlow,
    DetectedIcon,
    SecurityRecommendation,
    RBACAssignment,
    ManagedIdentityConfig,
    PrivateEndpointConfig,
    VNetIntegrationConfig,
    RBACScope,
    ManagedIdentityType,
)
from synthforge.prompts import get_security_agent_instructions, get_user_prompt_template, get_response_schema_json
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions

logger = logging.getLogger(__name__)


class SecurityAgent:
    """
    Security Agent for RBAC and security recommendations.
    
    Uses Azure Well-Architected Framework Security Pillar principles
    to provide security guidance for detected Azure resources.
    
    Tools Available:
    - Bing Grounding: Search Azure documentation for RBAC roles, PE configs
    - MCP Server: Access Microsoft Learn structured content
    
    Agent chooses best tool for each lookup - NO STATIC MAPPINGS.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
        self._tool_config = None
    
    async def __aenter__(self) -> "SecurityAgent":
        """Initialize the agent with Bing Grounding and MCP tools."""
        credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        )
        
        self._client = AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=credential,
        )
        
        # Get base instructions from YAML
        base_instructions = get_security_agent_instructions()
        
        # Add tool usage instructions
        tool_instructions = get_tool_instructions()
        instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Configure tools: Bing Grounding > MS Learn MCP
        # MS Learn MCP: Official security documentation
        # Bing Grounding: RBAC roles, security best practices, PE DNS zones
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"],
        )
        
        agent = self._client.create_agent(
            model=self.settings.model_deployment_name,
            name="SecurityAgent",
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
                pass
    
    async def get_recommendations(
        self, 
        resources: List[DetectedIcon],
        flows: Optional[List[DataFlow]] = None,
    ) -> List[SecurityRecommendation]:
        """
        Generate security recommendations for resources.
        Processes resources in batches to avoid token limits.
        Focuses on: Network Isolation + RBAC only.
        
        Args:
            resources: List of detected Azure resources
            flows: Optional list of network flows for RBAC inference
            
        Returns:
            List of SecurityRecommendation for each resource
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
        if not resources:
            return []
        
        logger = logging.getLogger(__name__)
        logger.info(f"SecurityAgent: Analyzing {len(resources)} resources with {len(flows) if flows else 0} flows")
        
        # Process in batches to avoid token limits
        # Reduced from 10 to 5 to improve per-resource recommendation quality
        BATCH_SIZE = 5
        
        # Create batch tasks for parallel processing
        batch_tasks = []
        for batch_start in range(0, len(resources), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(resources))
            batch_resources = resources[batch_start:batch_end]
            batch_num = batch_start//BATCH_SIZE + 1
            
            logger.info(f"SecurityAgent: Queueing batch {batch_num} ({len(batch_resources)} resources)")
            
            # Create async task for this batch
            task = self._process_batch(
                batch_resources,
                flows,
                batch_num=batch_num,
            )
            batch_tasks.append(task)
        
        # Execute all batches in parallel
        logger.info(f"SecurityAgent: Processing {len(batch_tasks)} batches in parallel...")
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Collect recommendations from all batches
        all_recommendations = []
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"SecurityAgent: Batch {i+1} failed with error: {result}")
                # Continue with other batches
            else:
                all_recommendations.extend(result)
        
        logger.info(f"SecurityAgent: Completed. Generated {len(all_recommendations)} recommendations")
        return all_recommendations
    
    async def _process_batch(
        self,
        resources: List[DetectedIcon],
        flows: Optional[List[DataFlow]],
        batch_num: int,
    ) -> List[SecurityRecommendation]:
        """Process a single batch of resources."""
        logger = logging.getLogger(__name__)
        
        # Build resource data for analysis
        resources_json = json.dumps([
            {
                "type": r.type,
                "name": r.name,
                "arm_resource_type": r.arm_resource_type,
            }
            for r in resources
        ], indent=2)
        
        # Build flows data for RBAC inference
        flows_json = "No network flows available"
        if flows:
            flows_json = json.dumps([
                {
                    "source": f.source,
                    "target": f.target,
                    "flow_type": f.flow_type,
                    "direction": f.direction,
                    "rbac_implication": f.rbac_implication,
                }
                for f in flows
            ], indent=2)
        
        # Load user prompt template and response schema from YAML configuration
        prompt_template = get_user_prompt_template("security_agent")
        response_schema = get_response_schema_json("security_recommendations")
        
        # Build prompt from template with placeholders
        prompt = prompt_template.format(
            resources_json=resources_json,
            flows_json=flows_json,
            response_schema=response_schema,
            batch_num=batch_num,
            resource_count=len(resources),
        )
        
        # Log prompt length for debugging
        logger.info(f"SecurityAgent: Sending prompt with {len(prompt)} characters, {len(resources)} resources")
        logger.debug(f"SecurityAgent: Prompt preview (first 500 chars): {prompt[:500]}")
        
        # Create thread and send message
        thread = self._client.threads.create()
        
        try:
            self._client.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt,
            )
            
            # Run the agent with toolset (allows agent to use MCP or Bing as needed)
            run = self._client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self._agent_id,
                toolset=self._tool_config.toolset if self._tool_config else None,
                max_completion_tokens=16000,  # Ensure agent can complete all resources
            )
            
            if run.status == "failed":
                error_msg = run.last_error if hasattr(run, 'last_error') else "Unknown error"
                logger.error(f"Security agent run failed. Status: {run.status}, Error: {error_msg}")
                
                # Check if it's an MCP server error - these are often transient
                error_str = str(error_msg)
                if "MCP" in error_str or "503" in error_str:
                    logger.warning("⚠ MCP server error detected (likely MS Learn server unavailable)")
                    logger.warning("  This is often transient. Continuing without MCP - using Bing Grounding only.")
                    logger.warning(f"  Batch {batch_idx + 1}/{total_batches} will have limited recommendations")
                    return []  # Return empty results for this batch, workflow continues
                
                raise RuntimeError(f"Security analysis failed: {error_msg}")
            
            # Get the response
            try:
                last_msg = self._client.messages.get_last_message_text_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT,
                )
            except Exception as msg_error:
                logger.error(f"Failed to get agent message: {msg_error}")
                logger.error(f"Run status: {run.status}")
                raise RuntimeError(f"Failed to retrieve agent response: {msg_error}")
            
            if not last_msg:
                logger.error("No message returned from security agent")
                raise RuntimeError("No response from security agent")
            
            if not last_msg.text or not last_msg.text.value:
                logger.error(f"Message has no text content. Message type: {type(last_msg)}")
                logger.error(f"Message attributes: {dir(last_msg)}")
                raise RuntimeError("Security agent message has no text content")
            
            response_text = last_msg.text.value
            
            # Log response for debugging
            logger.info(f"SecurityAgent: Received response with {len(response_text)} characters")
            
            # TEMPORARY: Write full response to file for debugging
            import os
            debug_file = os.path.join("output", "security_agent_response_debug.txt")
            os.makedirs("output", exist_ok=True)
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(f"SECURITY AGENT RESPONSE ({len(response_text)} chars):\n")
                f.write("="*80 + "\n")
                f.write(response_text)
                f.write("\n" + "="*80 + "\n")
            logger.info(f"SecurityAgent: Full response written to {debug_file}")
            
            logger.debug(f"SecurityAgent: Response preview (first 300 chars): {response_text[:300]}")
            
            recommendations = self._parse_response(response_text, resources)
            logger.info(f"SecurityAgent: Parsed {len(recommendations)} recommendations from response")
            
            return recommendations
        finally:
            # Always cleanup thread
            try:
                self._client.threads.delete(thread.id)
            except Exception:
                pass  # Ignore cleanup errors
    
    def _parse_response(
        self, 
        response_text: str, 
        resources: List[DetectedIcon],
    ) -> List[SecurityRecommendation]:
        """Parse the agent response into SecurityRecommendations."""
        import logging
        import re
        logger = logging.getLogger(__name__)
        
        try:
            # Try to extract JSON from markdown code blocks first
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Fall back to finding raw JSON
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                else:
                    # Log the response to help debug
                    logger.error(f"No valid JSON object found in response")
                    logger.error(f"Response text length: {len(response_text)}")
                    logger.error(f"Response text (full): {response_text}")
                    logger.error(f"json_start={json_start}, json_end={json_end}")
                    raise ValueError("No JSON object found in response (missing { or })")
            
            # Clean up common JSON issues
            json_str = json_str.strip()
            
            # Remove trailing commas before } or ]
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix missing commas between objects in arrays: }{ -> },{
            json_str = re.sub(r'\}(\s*)\{', r'},\1{', json_str)
            
            # Fix missing commas between array elements: ][ -> ],[
            json_str = re.sub(r'\](\s*)\[', r'],\1[', json_str)
            
            # Fix missing commas after string values followed by quotes: "value""key" -> "value","key"
            json_str = re.sub(r'\"(\s*)\"(?=[a-zA-Z_])', r'",\1"', json_str)
            
            # Fix missing commas after closing brackets followed by quotes: }"key" -> },"key"
            json_str = re.sub(r'\}(\s*)\"', r'},\1"', json_str)
            json_str = re.sub(r'\](\s*)\"', r'],\1"', json_str)
            
            # But undo the fix if it's the end of the object (before final })
            # This is tricky, so let's try parsing and if it fails, try more aggressive fixes
            
            logger.debug(f"Attempting to parse JSON: {json_str[:500]}...")
            
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as first_error:
                # Try more aggressive JSON repair
                logger.debug(f"First parse failed, attempting repair: {first_error}")
                
                # Sometimes models add extra text after the JSON - find balanced braces
                brace_count = 0
                json_end_idx = 0
                for i, char in enumerate(json_str):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end_idx = i + 1
                            break
                
                if json_end_idx > 0:
                    json_str = json_str[:json_end_idx]
                
                # Try parsing again
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Last resort: try to fix unescaped quotes in strings
                    # This is a common issue with URLs containing quotes
                    raise first_error  # Re-raise original error if still failing
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Extracted json_str (first 500 chars): {json_str[:500] if 'json_str' in locals() else 'N/A'}")
            logger.error(f"Raw response (first 1000 chars): {response_text[:1000]}")
            raise ValueError(f"Failed to parse security response: {e}")
        
        recommendations = []
        recommendations_array = data.get("recommendations", [])
        
        # Validate we got recommendations for all resources
        expected_count = len(resources)
        actual_count = len(recommendations_array)
        if actual_count < expected_count:
            logger.warning(
                f"Security agent returned {actual_count} recommendations for {expected_count} resources. "
                f"Some resources may not have security guidance. "
                f"Agent response length: {len(response_text)} characters."
            )
        
        for rec_data in recommendations_array:
            # Parse RBAC assignments
            rbac_assignments = []
            for rbac in rec_data.get("rbac_assignments", []):
                scope_str = (rbac.get("scope") or "RESOURCE").upper()
                try:
                    scope = RBACScope(scope_str)
                except ValueError:
                    scope = RBACScope.RESOURCE
                
                assignment = RBACAssignment(
                    role_name=rbac.get("role_name", ""),
                    role_definition_id=rbac.get("role_id"),
                    scope=scope,
                    justification=rbac.get("justification", ""),
                    source_service=rbac.get("source_service"),
                )
                rbac_assignments.append(assignment)
            
            # Parse network isolation (new structure)
            network_isolation = rec_data.get("network_isolation", {})
            
            # Parse private endpoint from network_isolation
            pe_data = network_isolation.get("private_endpoint")
            private_endpoint = None
            if pe_data:
                group_ids = pe_data.get("subresource_names", [])
                logger.debug(f"PE data from agent: {pe_data}")
                logger.debug(f"Extracted group_ids: {group_ids}")
                private_endpoint = PrivateEndpointConfig(
                    enabled=pe_data.get("recommended", True),
                    recommended=pe_data.get("recommended", True),
                    group_ids=group_ids,
                    private_dns_zone=pe_data.get("private_dns_zone"),
                    guidance=pe_data.get("justification", ""),
                )
            
            # Parse VNet integration from network_isolation  
            vnet_data = network_isolation.get("vnet_integration")
            vnet_integration = None
            if vnet_data:
                vnet_integration = VNetIntegrationConfig(
                    enabled=vnet_data.get("recommended", False),
                    recommended=vnet_data.get("recommended", False),
                    subnet_delegation=vnet_data.get("subnet_delegation"),
                    guidance=vnet_data.get("justification", ""),
                )
            
            recommendation = SecurityRecommendation(
                resource_type=rec_data.get("resource_type", ""),
                resource_name=rec_data.get("resource_name"),
                rbac_assignments=rbac_assignments,
                managed_identity=None,  # Removed from simplified schema
                private_endpoint=private_endpoint,
                vnet_integration=vnet_integration,
                additional_recommendations=[],  # Removed from simplified schema
                documentation_urls=rec_data.get("documentation_urls", []),
            )
            recommendations.append(recommendation)
        
        return recommendations
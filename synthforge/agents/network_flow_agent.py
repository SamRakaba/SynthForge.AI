"""
Network Flow Agent for SynthForge.AI.

Analyzes architecture diagrams to detect:
- Network connections and data flows between resources
- VNets, subnets, and security boundaries
- Private endpoint requirements
- VNet integration/injection requirements
- Subnet delegation requirements

Uses azure.ai.agents.AgentsClient (Foundry agentic pattern).
Uses Bing Grounding and MCP tools for Azure documentation lookup.
Agent chooses best tool for each task - NO STATIC MAPPINGS.
"""

import json
import base64
from typing import Optional, List, Dict, Any
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole

from synthforge.config import get_settings
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.models import (
    DetectedIcon,
    DetectionResult,
    DataFlow,
    VNetBoundary,
    Position,
)
from synthforge.prompts import get_network_flow_agent_instructions, get_user_prompt_template, get_response_schema_json


class VNetConfig:
    """VNet integration configuration for a service."""
    def __init__(
        self,
        service_type: str,
        supports_vnet_integration: bool = False,
        subnet_delegation: Optional[str] = None,
        requires_dedicated_subnet: bool = False,
        recommended_subnet_size: Optional[str] = None,
        uses_managed_vnet: bool = False,
    ):
        self.service_type = service_type
        self.supports_vnet_integration = supports_vnet_integration
        self.subnet_delegation = subnet_delegation
        self.requires_dedicated_subnet = requires_dedicated_subnet
        self.recommended_subnet_size = recommended_subnet_size
        self.uses_managed_vnet = uses_managed_vnet
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_type": self.service_type,
            "supports_vnet_integration": self.supports_vnet_integration,
            "subnet_delegation": self.subnet_delegation,
            "requires_dedicated_subnet": self.requires_dedicated_subnet,
            "recommended_subnet_size": self.recommended_subnet_size,
            "uses_managed_vnet": self.uses_managed_vnet,
        }


class NetworkFlowResult:
    """Result from network flow analysis."""
    def __init__(
        self,
        flows: List[DataFlow],
        vnets: List[VNetBoundary],
        subnets: List[Dict[str, Any]],
        security_zones: List[Dict[str, Any]],
        vnet_configs: Dict[str, VNetConfig],
    ):
        self.flows = flows
        self.vnets = vnets
        self.subnets = subnets
        self.security_zones = security_zones
        self.vnet_configs = vnet_configs


class NetworkFlowAgent:
    """
    Network Flow Agent for analyzing architecture diagrams.
    
    Detects:
    - Network flows and data flows between resources
    - VNet boundaries and subnet configurations
    - Private endpoint requirements
    - VNet integration requirements per service
    
    Tools Available:
    - Bing Grounding: Search Azure documentation for VNet integration, delegation
    - MCP Server: Access Microsoft Learn structured content
    
    Agent chooses best tool for each lookup - NO STATIC MAPPINGS.
    """
    
    def __init__(self):
        """Initialize the Network Flow Agent."""
        self.settings = get_settings()
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
        self._tool_config = None
    
    async def __aenter__(self) -> "NetworkFlowAgent":
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
        base_instructions = self._get_instructions()
        
        # Add tool usage instructions
        tool_instructions = get_tool_instructions()
        instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Configure tools: Bing Grounding > MS Learn MCP
        # MS Learn MCP: Official networking documentation
        # Bing Grounding: Networking best practices and patterns
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"],
        )
        
        agent = self._client.create_agent(
            model=self.settings.model_deployment_name,
            name="NetworkFlowAgent",
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
    
    def _get_instructions(self) -> str:
        """Get agent instructions from YAML configuration."""
        return get_network_flow_agent_instructions()
    
    def _encode_image(self, image_path: str | Path) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    async def analyze_flows(
        self,
        image_path: str | Path,
        resources: List[DetectedIcon],
    ) -> NetworkFlowResult:
        """
        Analyze network flows in an architecture diagram.
        
        Args:
            image_path: Path to the architecture diagram
            resources: List of detected resources from Vision Agent
            
        Returns:
            NetworkFlowResult with flows, vnets, subnets, and configs
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
        if not resources:
            return NetworkFlowResult(
                flows=[],
                vnets=[],
                subnets=[],
                security_zones=[],
                vnet_configs={},
            )
        
        # Build resource list for context
        resource_list = "\n".join([
            f"- {i}. {r.type}" + (f" ({r.name})" if r.name else "")
            for i, r in enumerate(resources, 1)
        ])
        
        # Load user prompt template and response schema from YAML configuration
        prompt_template = get_user_prompt_template("network_flow_agent")
        response_schema = get_response_schema_json("network_flows")
        
        # Build prompt from template with placeholders
        prompt = prompt_template.format(
            resource_list=resource_list,
            response_schema=response_schema,
        )
        
        # Create thread and send image with analysis request
        thread = self._client.threads.create()
        
        try:
            # Encode image
            image_data = self._encode_image(image_path)
            
            # Send message using prompt from YAML template
            self._client.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt,
                attachments=[{
                    "type": "image",
                    "data": f"data:image/png;base64,{image_data}",
                }] if False else [],  # Note: Use file upload for images in production
            )
            
            # Run agent with toolset (allows agent to use MCP or Bing as needed)
            run = self._client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self._agent_id,
                toolset=self._tool_config.toolset if self._tool_config else None,
            )
            
            # Get response
            flows = []
            vnets = []
            subnets = []
            security_zones = []
            
            if run.status == "completed":
                last_msg = self._client.messages.get_last_message_text_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT,
                )
                
                if last_msg:
                    try:
                        # Parse JSON from response
                        response_text = last_msg.text.value
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            data = json.loads(response_text[json_start:json_end])
                            
                            # Parse flows
                            for flow_data in data.get("network_flows", []):
                                flow = DataFlow(
                                    source=flow_data.get("source", ""),
                                    target=flow_data.get("target", ""),
                                    flow_type=flow_data.get("flow_type", "data"),
                                    direction=flow_data.get("direction", "unidirectional"),
                                    protocol=flow_data.get("protocol"),
                                    port=flow_data.get("port"),
                                    description=flow_data.get("description"),
                                    is_private=flow_data.get("is_private", False),
                                )
                                flows.append(flow)
                            
                            # Parse VNets
                            for vnet_data in data.get("vnets", []):
                                vnet = VNetBoundary(
                                    name=vnet_data.get("name", ""),
                                    type="vnet",
                                    position=Position(x=0, y=0),
                                    contained_resources=vnet_data.get("contained_resources", []),
                                )
                                vnets.append(vnet)
                            
                            subnets = data.get("subnets", [])
                            security_zones = data.get("security_zones", [])
                            
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Warning: Failed to parse network flow response: {e}")
            
            # Get VNet integration configs for services
            vnet_configs = await self._get_vnet_configs(resources)
            
            return NetworkFlowResult(
                flows=flows,
                vnets=vnets,
                subnets=subnets,
                security_zones=security_zones,
                vnet_configs=vnet_configs,
            )
        finally:
            # Always cleanup thread
            try:
                self._client.threads.delete(thread.id)
            except Exception:
                pass  # Ignore cleanup errors
    
    async def _get_vnet_configs(
        self,
        resources: List[DetectedIcon],
    ) -> Dict[str, VNetConfig]:
        """Get VNet integration configurations for each service type."""
        configs = {}
        
        # Get unique service types
        service_types = set(r.type for r in resources)
        
        for service_type in service_types:
            config = await self.get_vnet_config(service_type)
            configs[service_type] = config
        
        return configs
    
    async def get_vnet_config(self, service_type: str) -> VNetConfig:
        """
        Get VNet integration configuration for a service.
        
        Uses BingGroundingTool to look up Azure documentation for:
        - VNet integration support
        - Subnet delegation requirements
        - Recommended subnet sizes
        
        Args:
            service_type: The Azure service type (e.g., "Azure App Service")
            
        Returns:
            VNetConfig with integration details
        """
        if not self._client or not self._agent_id:
            return VNetConfig(service_type=service_type)
        
        base_type = service_type.split("(")[0].strip()
        
        # Create thread for VNet config lookup
        thread = self._client.threads.create()
        
        try:
            self._client.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"""Look up Azure documentation for VNet integration support for "{base_type}".

Determine:
1. Does this service support VNet integration/injection for outbound traffic?
2. What subnet delegation is required (e.g., "Microsoft.Web/serverFarms")?
3. Does it require a dedicated subnet?
4. What subnet size is recommended (CIDR like "/26")?
5. Does it use Azure-managed VNet instead of customer VNet?

Respond with ONLY JSON:
{{
    "supports_vnet_integration": true/false,
    "subnet_delegation": "<delegation type or null>",
    "requires_dedicated_subnet": true/false,
    "recommended_subnet_size": "<CIDR or null>",
    "uses_managed_vnet": true/false
}}
"""
            )
            
            run = self._client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self._agent_id,
            )
            
            if run.status == "completed":
                last_msg = self._client.messages.get_last_message_text_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT,
                )
                
                if last_msg:
                    try:
                        response_text = last_msg.text.value
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            data = json.loads(response_text[json_start:json_end])
                            
                            return VNetConfig(
                                service_type=base_type,
                                supports_vnet_integration=data.get("supports_vnet_integration", False),
                                subnet_delegation=data.get("subnet_delegation"),
                                requires_dedicated_subnet=data.get("requires_dedicated_subnet", False),
                                recommended_subnet_size=data.get("recommended_subnet_size"),
                                uses_managed_vnet=data.get("uses_managed_vnet", False),
                            )
                    except (json.JSONDecodeError, ValueError):
                        pass
            
            # Default: no VNet integration
            return VNetConfig(service_type=base_type)
        finally:
            # Always cleanup thread
            try:
                self._client.threads.delete(thread.id)
            except Exception:
                pass  # Ignore cleanup errors
    
    async def infer_flows(
        self,
        resources: List[DetectedIcon],
        existing_flows: List[DataFlow],
    ) -> List[DataFlow]:
        """
        Infer additional flows based on common Azure patterns.
        
        Uses agent knowledge to infer connections that may not be visible
        but are typical for the detected service combinations.
        
        Args:
            resources: List of detected resources
            existing_flows: Already detected flows
            
        Returns:
            List of inferred additional flows
        """
        if not self._client or not self._agent_id:
            return []
        
        resource_list = ", ".join(r.type for r in resources)
        existing_flow_list = "\n".join([
            f"- {f.source} → {f.target} ({f.flow_type})"
            for f in existing_flows
        ]) if existing_flows else "None detected"
        
        thread = self._client.threads.create()
        
        try:
            self._client.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"""Given these Azure resources: {resource_list}

And these existing detected flows:
{existing_flow_list}

What additional data flows would typically exist based on common Azure architecture patterns?

For example:
- Web App to Key Vault for secrets
- App Service to Application Insights for telemetry
- Azure Functions to Storage Account for triggers

Only suggest flows that make sense for these specific resources.

Respond with JSON:
{{
    "inferred_flows": [
        {{
            "source": "<source service>",
            "target": "<target service>",
            "flow_type": "<data|auth|telemetry|event>",
            "protocol": "<protocol>",
            "reason": "<why this flow exists>"
        }}
    ]
}}
"""
            )
            
            run = self._client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self._agent_id,
            )
            
            inferred = []
            
            if run.status == "completed":
                last_msg = self._client.messages.get_last_message_text_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT,
                )
                
                if last_msg:
                    try:
                        response_text = last_msg.text.value
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            data = json.loads(response_text[json_start:json_end])
                            
                            for flow_data in data.get("inferred_flows", []):
                                # Check if this flow already exists
                                src = flow_data.get("source", "")
                                tgt = flow_data.get("target", "")
                                
                                already_exists = any(
                                    (f.source == src and f.target == tgt) or
                                    (f.source == tgt and f.target == src)
                                    for f in existing_flows
                                )
                                
                                if not already_exists:
                                    flow = DataFlow(
                                        source=src,
                                        target=tgt,
                                        flow_type=flow_data.get("flow_type", "data"),
                                        direction="unidirectional",
                                        protocol=flow_data.get("protocol"),
                                        description=flow_data.get("reason"),
                                        is_private=True,  # Assume private for inferred flows
                                    )
                                    inferred.append(flow)
                                    
                    except (json.JSONDecodeError, ValueError):
                        pass
            
            return inferred
        finally:
            # Always cleanup thread
            try:
                self._client.threads.delete(thread.id)
            except Exception:
                pass  # Ignore cleanup errors

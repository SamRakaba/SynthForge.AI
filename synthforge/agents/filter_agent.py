"""
Filter Agent for SynthForge.AI.

Filters detected resources into architectural vs non-architectural categories
using first-principles reasoning (not static lists).

Uses azure.ai.agents.AgentsClient with Bing Grounding and MCP tools.
Agent chooses best tool for classification - NO STATIC MAPPINGS.
"""

import json
from typing import Optional, Any

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole

from synthforge.config import get_settings
from synthforge.models import (
    DetectionResult,
    DetectedIcon,
    FilterResult,
    FilterDecision,
    FilterCategory,
)
from synthforge.prompts import get_filter_agent_instructions, get_user_prompt_template, get_response_schema_json
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions


class FilterAgent:
    """
    Filter Agent for classifying resources as architectural or non-architectural.
    
    Uses first-principles reasoning to evaluate each resource:
    - Does it have an ARM resource type?
    - Is it deployed per-application?
    - Is it infrastructure or observability?
    - Is it Azure-native or third-party?
    
    Tools Available:
    - Bing Grounding: Search Azure WAF documentation for classification
    - MCP Server: Access Microsoft Learn structured content
    
    Agent chooses best tool for each lookup - NO STATIC MAPPINGS.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[AgentsClient] = None
        self._agent_id: Optional[str] = None
        self._tool_config = None
    
    async def __aenter__(self) -> "FilterAgent":
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
        base_instructions = get_filter_agent_instructions()
        
        # Add tool usage instructions
        tool_instructions = get_tool_instructions()
        instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Configure tools: Bing Grounding > MS Learn MCP
        # Bing Grounding: Best practices for architectural patterns
        # MS Learn MCP: Official documentation
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"],
        )
        
        agent = self._client.create_agent(
            model=self.settings.model_deployment_name,
            name="FilterAgent",
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
    
    async def filter_resources(self, detection_result: DetectionResult, description_context: Optional[Any] = None) -> FilterResult:
        """
        Filter detected resources using first-principles reasoning.
        
        Uses description context to:
        - Identify foundational services (AI Foundry, Search, OpenAI, Storage, Key Vault, etc.)
        - Enrich detections with additional context from description
        - Validate detected services against described components
        
        Args:
            detection_result: Result from vision agent
            description_context: Optional description from description agent for enrichment
            
        Returns:
            FilterResult with categorized resources
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
        # Build resource data for analysis
        resources_json = json.dumps([
            {
                "type": icon.type,
                "name": icon.name,
                "arm_resource_type": icon.arm_resource_type,
                "confidence": icon.confidence,
                "needs_clarification": icon.needs_clarification,
            }
            for icon in detection_result.icons
        ], indent=2)
        
        # Include description context if available
        description_text = ""
        if description_context:
            # Load foundational services guidance from YAML
            from synthforge.prompts import get_prompt_template
            foundational_guidance = get_prompt_template(
                "filter_agent",
                "foundational_services_guidance",
                from_iac=False
            )
            
            description_text = f"\n\n## Architecture Description Context\n\n"
            description_text += f"The diagram description identified the following Azure components:\n\n"
            if hasattr(description_context, 'azure_components'):
                description_text += "**Azure Services:**\n"
                for comp in description_context.azure_components[:10]:  # Limit to first 10
                    description_text += f"- {comp}\n"
            if hasattr(description_context, 'overview'):
                description_text += f"\n**Solution Overview:** {description_context.overview}\n"
            description_text += "\nUse this context to:\n"
            description_text += foundational_guidance
            description_text += "\n2. **Enrich detections** - Add missing context or validate service identification\n"
            description_text += "3. **Determine service purpose** - Understand if services are core infrastructure vs supporting\n"
        
        # Load user prompt template and response schema from YAML configuration
        prompt_template = get_user_prompt_template("filter_agent")
        response_schema = get_response_schema_json("filter_decisions")
        
        # Build prompt from template with placeholders
        prompt = prompt_template.format(
            resources_json=resources_json,
            response_schema=response_schema,
        ) + description_text
        
        # Create thread and send message
        thread = self._client.threads.create()
        
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
        )
        
        if run.status == "failed":
            raise RuntimeError(f"Filter analysis failed: {run.last_error}")
        
        # Get the response
        last_msg = self._client.messages.get_last_message_text_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            raise RuntimeError("No response from filter agent")
        
        response_text = last_msg.text.value
        
        return self._parse_response(response_text, detection_result)
    
    def _parse_response(self, response_text: str, detection_result: DetectionResult) -> FilterResult:
        """Parse the agent response into FilterResult."""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse filter response: {e}")
        
        # Build decision lookup
        decisions_by_type = {}
        for decision in data.get("decisions", []):
            decisions_by_type[decision.get("resource_type", "")] = decision
        
        # Categorize resources
        architectural = []
        non_architectural = []
        network_isolation = []  # NEW: Network patterns become recommendations
        needs_clarification = []
        decisions = []
        
        for icon in detection_result.icons:
            decision_data = decisions_by_type.get(icon.type, {})
            category_str = decision_data.get("category", "architectural").lower().replace(" ", "_")
            
            try:
                category = FilterCategory(category_str)
            except ValueError:
                # Default to ARCHITECTURAL to preserve core resources
                category = FilterCategory.ARCHITECTURAL
            
            decision = FilterDecision(
                resource_type=icon.type,
                category=category,
                reasoning=decision_data.get("reasoning", ""),
                confidence=decision_data.get("confidence", 0.5),
            )
            decisions.append(decision)
            
            # CRITICAL: Auto-flag resources with Unknown ARM type for clarification
            # Regardless of agent's category decision, Unknown ARM types need user input
            has_unknown_arm_type = (
                not icon.arm_resource_type or 
                icon.arm_resource_type.strip() == "" or 
                icon.arm_resource_type.lower() == "unknown"
            )
            
            if has_unknown_arm_type or category == FilterCategory.NEEDS_CLARIFICATION:
                # Flag for clarification if:
                # 1. ARM type is Unknown/missing (ALWAYS needs clarification)
                # 2. Agent explicitly categorized as NEEDS_CLARIFICATION
                needs_clarification.append(icon)
            elif category == FilterCategory.ARCHITECTURAL:
                architectural.append(icon)
            elif category == FilterCategory.NON_ARCHITECTURAL:
                non_architectural.append(icon)
            elif category == FilterCategory.NETWORK_ISOLATION_PATTERN:
                # Network isolation patterns go to a separate list - they become recommendations
                network_isolation.append(icon)
        
        return FilterResult(
            architectural=architectural,
            non_architectural=non_architectural,
            network_isolation=network_isolation,
            needs_clarification=needs_clarification,
            decisions=decisions,
            summary=data.get("summary", ""),
        )

"""
ServiceAnalysisAgent: Extracts Azure service requirements from Phase 1 analysis.

This agent reads Phase 1 JSON outputs and dynamically generates a list of
Azure services that need IaC modules, including dependencies and configurations.

NO STATIC MAPPING - All services extracted dynamically from design analysis.
Uses Bing Grounding to research service configurations and dependencies.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole, ThreadMessage, ThreadRun, RunStatus

from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.prompts import get_service_analysis_agent_instructions

logger = logging.getLogger(__name__)


@dataclass
class ServiceRequirement:
    """Represents an Azure service requirement extracted from design."""
    
    service_type: str  # e.g., "Azure OpenAI", "Azure Cosmos DB", "API Management"
    resource_name: str  # Logical name from design
    arm_type: Optional[str] = None  # ARM resource type (e.g., "Microsoft.Web/sites")
    resource_category: str = "Unknown"  # Azure service category (e.g., "Compute", "AI + Machine Learning")
    configurations: Dict[str, Any] = field(default_factory=dict)  # SKU, features, etc.
    dependencies: List[str] = field(default_factory=list)  # Other services this depends on
    network_requirements: Dict[str, Any] = field(default_factory=dict)  # VNet, private endpoints
    security_requirements: Dict[str, Any] = field(default_factory=dict)  # RBAC, managed identity
    priority: int = 1  # Deployment priority (1=foundation, 2=services, 3=integration)
    phase1_recommendations: List[str] = field(default_factory=list)  # Recommendations from Phase 1
    research_sources: List[str] = field(default_factory=list)  # URLs from Bing/MCP research
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_type": self.service_type,
            "resource_name": self.resource_name,
            "arm_type": self.arm_type,
            "resource_category": self.resource_category,
            "configurations": self.configurations,
            "dependencies": self.dependencies,
            "network_requirements": self.network_requirements,
            "security_requirements": self.security_requirements,
            "priority": self.priority,
            "phase1_recommendations": self.phase1_recommendations,
            "research_sources": self.research_sources,
        }


@dataclass
@dataclass
class ServiceAnalysisResult:
    """Result from service analysis stage."""
    
    services: List[ServiceRequirement]
    total_count: int
    foundation_services: List[ServiceRequirement]  # Priority 1: VNet, Key Vault, etc.
    application_services: List[ServiceRequirement]  # Priority 2: OpenAI, Cosmos DB, etc.
    integration_services: List[ServiceRequirement]  # Priority 3: API Management, etc.
    recommendations_summary: Dict[str, List[str]] = field(default_factory=dict)  # Consolidated recommendations
    common_patterns: Dict[str, Any] = field(default_factory=dict)  # Common infrastructure patterns detected
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "services": [s.to_dict() for s in self.services],
            "total_count": self.total_count,
            "foundation_services": [s.to_dict() for s in self.foundation_services],
            "application_services": [s.to_dict() for s in self.application_services],
            "integration_services": [s.to_dict() for s in self.integration_services],
            "recommendations_summary": self.recommendations_summary,
            "common_patterns": self.common_patterns,
            "agent_id": self.agent_id,
            "thread_id": self.thread_id,
        }


class ServiceAnalysisAgent:
    """
    Agent for analyzing Phase 1 outputs and extracting service requirements.
    
    Uses Azure AI Foundry with Bing Grounding + MS Learn MCP to:
    1. Parse Phase 1 JSON files (architecture, resources, network, security)
    2. Extract all APPLICATION Azure services dynamically (NO static mapping)
    3. Use Bing Grounding to research configurations, dependencies, best practices
    4. Identify deployment priorities and relationships
    5. Generate comprehensive service development list
    
    EXCLUDES foundational infrastructure (VNet, NSG, Subnets) unless requested.
    """
    
    AGENT_NAME = "Azure Service Requirements Analyst"
    
    def __init__(
        self,
        agents_client: AgentsClient,
        model_name: str,
        bing_connection_name: Optional[str] = None,
        ms_learn_mcp_url: Optional[str] = None,
    ):
        """
        Initialize ServiceAnalysisAgent.
        
        Args:
            agents_client: Azure AI Agents client
            model_name: Model deployment name (e.g., "gpt-4o")
            bing_connection_name: Bing Grounding connection name (optional but recommended)
            ms_learn_mcp_url: MS Learn MCP server URL (optional)
        """
        self.agents_client = agents_client
        self.model_name = model_name
        self.agent = None
        self.thread = None
        
        logger.info(f"Initializing {self.AGENT_NAME}...")
        
        # Load instructions from YAML (Phase 1 pattern)
        base_instructions = get_service_analysis_agent_instructions()
        
        # Create toolset with Bing Grounding + MS Learn MCP for research
        use_bing = bing_connection_name is not None
        self.tool_config = create_agent_toolset(
            include_bing=use_bing,
            include_mcp=True,
            mcp_servers=["mslearn"],
        )
        
        # Add tool usage instructions
        tool_instructions = get_tool_instructions()
        self.full_instructions = f"{base_instructions}\n\n{tool_instructions}"
        
        # Create agent
        self._create_agent()
        
        logger.info(f"✓ {self.AGENT_NAME} initialized (Agent ID: {self.agent.id})")
        if use_bing:
            logger.info("  - Bing Grounding enabled for service research")
        if ms_learn_mcp_url:
            logger.info("  - MS Learn MCP enabled for documentation research")
    
    def _create_agent(self):
        """Create the Azure AI agent."""
        self.agent = self.agents_client.create_agent(
            model=self.model_name,
            name=self.AGENT_NAME,
            instructions=self.full_instructions,
            tools=self.tool_config.tools,
            tool_resources=self.tool_config.tool_resources,
            temperature=0.0,  # Deterministic service extraction
            top_p=0.95,
            response_format={"type": "json_object"},  # Prevent markdown wrapping
        )
        logger.debug(f"Agent created: {self.agent.id}")
    
    def _clean_json_response(self, text: str) -> str:
        """Clean common JSON formatting issues from agent response."""
        import re
        
        # Fix control characters in strings (newlines, tabs, etc.)
        def fix_control_chars(text):
            result = []
            in_string = False
            escape_next = False
            
            for i, char in enumerate(text):
                # Handle escape sequences
                if escape_next:
                    result.append(char)
                    escape_next = False
                    continue
                
                if char == '\\':
                    result.append(char)
                    escape_next = True
                    continue
                
                # Track string boundaries (quotes not preceded by backslash)
                if char == '"':
                    in_string = not in_string
                    result.append(char)
                    continue
                
                # Replace control characters inside strings
                if in_string and ord(char) < 32:
                    # Control character (0-31): newline, tab, carriage return, etc.
                    result.append(' ')  # Replace with space
                else:
                    result.append(char)
            
            return ''.join(result)
        
        text = fix_control_chars(text)
        
        # Remove comments and abbreviations
        text = re.sub(r'\s*//[^\n]*', '', text)  # Inline comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)  # Multi-line comments
        text = re.sub(r'\.{3,}', '', text)  # "..." abbreviations
        text = re.sub(r',(\s*[}\]])', r'\1', text)  # Trailing commas
        
        return text
    
    async def analyze_services(
        self,
        phase1_data: Dict[str, Any],
    ) -> ServiceAnalysisResult:
        """
        Analyze Phase 1 outputs and extract service requirements.
        
        Args:
            phase1_data: Dictionary with Phase 1 JSON data
                {
                    "architecture": {...},
                    "resources": {...},
                    "network": {...},
                    "security": {...},
                    "private_endpoints": {...}
                }
        
        Returns:
            ServiceAnalysisResult with extracted services
        """
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 1: Service Analysis")
        logger.info("=" * 80)
        
        # Create thread
        self.thread = self.agents_client.threads.create()
        logger.info(f"Created thread: {self.thread.id}")
        
        # Extract resource count from Phase 1 for validation
        resource_count = len(phase1_data.get("resources", {}).get("resources", []))
        
        # Diagnostic logging for token limit investigation
        import json
        phase1_json_size = len(json.dumps(phase1_data))
        logger.info(f"📊 Phase 1 Analysis Metrics:")
        logger.info(f"   Resource count: {resource_count} services")
        logger.info(f"   Phase 1 data size: {phase1_json_size:,} characters")
        logger.info(f"   Estimated tokens: ~{phase1_json_size // 4:,} tokens")
        
        # Prepare analysis prompt
        prompt = self._create_analysis_prompt(phase1_data)
        
        # Send message
        logger.info("Sending Phase 1 data for service extraction...")
        message = self.agents_client.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=prompt,
        )
        
        # Create and poll run with increased token limit for large JSON output
        logger.info("Running service analysis...")
        run = self.agents_client.runs.create_and_process(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
            max_completion_tokens=32000,  # Increased to 32K to support 12+ services (~18K needed)
        )
        
        # Process result
        if run.status == "completed":
            logger.info("✓ Service analysis completed")
            result = await self._process_result(
                run, 
                resource_count=resource_count,
                phase1_resources=phase1_data.get("resources", {}).get("resources", [])
            )
            return result
        else:
            logger.error(f"✗ Service analysis failed: {run.status}")
            raise RuntimeError(f"Service analysis failed with status: {run.status}")
    
    async def _ensure_complete_extraction(
        self,
        initial_services: List[Dict[str, Any]],
        phase1_resources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Validation-driven re-extraction: Request missing services if initial extraction incomplete.
        
        This safety net ensures 100% extraction by specifically requesting services that
        were missing from the initial analysis.
        
        Args:
            initial_services: Services extracted in first pass
            phase1_resources: Original Phase 1 resources list
            
        Returns:
            Complete list of services (initial + missing)
        """
        import json
        
        # Identify missing services
        extracted_names = {s.get('resource_name', s.get('name', '')) for s in initial_services}
        expected_names = {r.get('name', '') for r in phase1_resources}
        missing_names = expected_names - extracted_names - {''}  # Exclude empty strings
        
        if not missing_names:
            logger.info("✅ All services classified successfully")
            return initial_services
        
        logger.info(f"🔄 Validation-driven re-classification triggered")
        logger.info(f"   Unclassified services: {', '.join(sorted(missing_names))}")
        
        # Get Phase 1 data for missing services only
        missing_resources = [r for r in phase1_resources if r.get('name') in missing_names]
        
        # Create focused prompt for missing services
        missing_prompt = f"""# Re-extraction Request: Missing Services

The previous analysis was incomplete. Please extract ONLY the following missing services:

**Missing Services:** {', '.join(sorted(missing_names))}

**Phase 1 Data for Missing Services:**
```json
{json.dumps(missing_resources, indent=2)}
```

# Task
Extract ONLY these {len(missing_names)} services with complete details:
- service_type
- resource_name
- arm_type (REQUIRED - copy from Phase 1 data above)
- configurations
- dependencies
- network_requirements
- security_requirements
- priority
- phase1_recommendations

**Output Format:**
```json
{{
  "services": [
    // List all {len(missing_names)} services here
  ]
}}
```

**CRITICAL:**
- NO abbreviations or "..."
- Include ALL {len(missing_names)} services completely
- Valid JSON only (no markdown blocks)
- NO extra text
"""
        
        # Send re-extraction request
        logger.info("Requesting missing services from agent...")
        message = self.agents_client.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=missing_prompt,
        )
        
        # Run agent for missing services
        run = self.agents_client.runs.create_and_process(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
            max_completion_tokens=16000,  # Smaller limit OK for subset of services
        )
        
        if run.status != "completed":
            logger.error(f"❌ Re-extraction failed: {run.status}")
            return initial_services  # Return what we have
        
        # Get and parse response
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            logger.error("❌ No response from re-extraction")
            return initial_services
        
        # Parse JSON
        response_text = last_msg.text.value.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            missing_data = json.loads(response_text)
            missing_services = missing_data.get("services", [])
            
            if missing_services:
                logger.info(f"✅ Re-extracted {len(missing_services)} missing services")
                
                # Log what was recovered
                recovered_names = [s.get('resource_name', s.get('name', 'Unknown')) for s in missing_services]
                logger.info(f"   Recovered: {', '.join(recovered_names)}")
                
                # Combine with initial services
                complete_services = initial_services + missing_services
                logger.info(f"✅ Complete extraction: {len(complete_services)} total services")
                return complete_services
            else:
                logger.warning("⚠️  Re-extraction returned no services")
                return initial_services
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Re-extraction JSON parsing failed: {e}")
            logger.debug(f"Response (first 500 chars): {response_text[:500]}")
            return initial_services
    
    def _create_analysis_prompt(self, phase1_data: Dict[str, Any]) -> str:
        """Create the analysis prompt with Phase 1 data."""
        import json
        from synthforge.prompts import get_iac_user_prompt_template
        
        # Load template from YAML (centralized prompts)
        template = get_iac_user_prompt_template('service_analysis_agent')
        
        # Build Phase 1 data sections for injection
        phase1_sections = ""
        for key, data in phase1_data.items():
            phase1_sections += f"\n## {key.upper()} Data\n"
            phase1_sections += f"```json\n{json.dumps(data, indent=2)}\n```\n"
        
        # Count resources from Phase 1
        resource_count = len(phase1_data.get("resources", {}).get("resources", []))
        
        # Inject Phase 1 data into template
        prompt = template.format(
            phase1_data_sections=phase1_sections,
            resource_count=resource_count
        )
        
        return prompt
    
    async def _process_result(
        self, 
        run: ThreadRun, 
        resource_count: int = 12,
        phase1_resources: List[Dict[str, Any]] = None
    ) -> ServiceAnalysisResult:
        """Process the agent's response and extract services."""
        import json
        
        # Enhanced diagnostic logging for token usage
        if run.usage and hasattr(run.usage, 'completion_tokens'):
            completion_tokens = run.usage.completion_tokens
            max_tokens = 32000
            utilization = (completion_tokens / max_tokens) * 100
            
            logger.info(f"📊 Agent Response Metrics:")
            logger.info(f"   Completion tokens: {completion_tokens:,}/{max_tokens:,}")
            logger.info(f"   Token utilization: {utilization:.1f}%")
            
            # Warn if approaching limit (>85%)
            if completion_tokens >= max_tokens * 0.85:
                logger.warning(f"⚠️  High token usage ({utilization:.1f}%) - response may be truncated!")
            
            # Error if at/near limit
            if completion_tokens >= max_tokens - 100:
                logger.error(f"❌ CRITICAL: Token limit reached! Response is likely truncated.")
        
        # Get last message from agent
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            raise RuntimeError("No response from agent")
        
        # Extract response text - with response_format=json_object, this should be valid JSON
        response_text = last_msg.text.value.strip()
        
        # Log response for debugging
        logger.debug(f"Raw agent response (first 500 chars):\n{response_text[:500]}")
        
        # Simple JSON parsing with fallback cleanup
        try:
            result_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}")
            logger.debug(f"Response text (first 1000 chars):\n{response_text[:1000]}")
            
            # Try to extract JSON if wrapped in markdown or has extra text
            import re
            
            # Look for JSON object boundaries
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')
            
            if first_brace >= 0 and last_brace > first_brace:
                # Extract JSON portion
                json_text = response_text[first_brace:last_brace + 1]
                logger.info(f"Extracted JSON from position {first_brace} to {last_brace}, length: {len(json_text)}")
                
                # Count ALL control characters including newlines (which are INVALID in JSON strings)
                newlines_before = json_text.count('\n')
                tabs_before = json_text.count('\t')
                carriage_returns_before = json_text.count('\r')
                logger.info(f"Before cleanup: {newlines_before} newlines, {tabs_before} tabs, {carriage_returns_before} CRs")
                
                # Clean up any remaining issues
                json_text = self._clean_json_response(json_text)
                
                # Count after cleanup
                newlines_after = json_text.count('\n')
                tabs_after = json_text.count('\t')
                carriage_returns_after = json_text.count('\r')
                logger.debug(f"After cleanup: {newlines_after} newlines, {tabs_after} tabs, {carriage_returns_after} CRs")
                
                # Check for control characters INSIDE strings (which would be invalid)
                # Newlines between JSON keys/values are fine for formatting
                import re
                # Find string values (excluding keys and structural characters)
                string_pattern = r':\s*"([^"\\]*(?:\\.[^"\\]*)*)"'
                invalid_control_in_strings = []
                
                for match in re.finditer(string_pattern, json_text):
                    string_value = match.group(1)
                    for i, c in enumerate(string_value):
                        if ord(c) < 32 and c not in ['\n', '\t', '\r']:  # Allow common formatting
                            invalid_control_in_strings.append((match.start() + i, ord(c), repr(c)))
                
                if invalid_control_in_strings:
                    logger.warning(f"⚠️  Found {len(invalid_control_in_strings)} invalid control characters inside JSON strings")
                    for pos, code, char_repr in invalid_control_in_strings[:3]:
                        logger.warning(f"  Position {pos}: ord({code}) {char_repr}")
                else:
                    logger.debug("✓ No invalid control characters in JSON string values")
                
                try:
                    result_data = json.loads(json_text)
                    logger.info("✓ JSON successfully extracted and parsed")
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON extraction failed: {e2}")
                    logger.error(f"Error at position {e2.pos if hasattr(e2, 'pos') else 'unknown'}")
                    logger.error(f"Cleaned text (first 1000 chars):\n{json_text[:1000]}")
                    raise RuntimeError(f"Agent returned invalid JSON. Error: {e}. Check logs for details.")
            else:
                logger.error("No JSON object found in response")
                raise RuntimeError(f"Agent returned invalid JSON. Error: {e}. Check logs for details.")
        
        # CRITICAL VALIDATION: Check classification completeness
        extracted_count = len(result_data.get("services", []))
        excluded_count = len(result_data.get("excluded_services", []))
        clarification_count = len(result_data.get("needs_clarification", []))
        total_classified = extracted_count + excluded_count + clarification_count
        
        logger.info(f"\n📊 Service Classification Summary:")
        logger.info(f"   Application services (IaC): {extracted_count}")
        logger.info(f"   Excluded (foundational): {excluded_count}")
        logger.info(f"   Needs clarification: {clarification_count}")
        logger.info(f"   Total classified: {total_classified}/{resource_count}")
        logger.info(f"   Classification rate: {(total_classified/resource_count)*100:.1f}%")
        
        # Log excluded services for transparency
        if excluded_count > 0:
            excluded_names = [s.get('service_type', 'Unknown') for s in result_data.get("excluded_services", [])]
            logger.info(f"   🚫 Excluded from IaC: {', '.join(excluded_names)}")
        
        # Log services needing clarification
        if clarification_count > 0:
            clarify_names = [s.get('service_type', 'Unknown') for s in result_data.get("needs_clarification", [])]
            logger.warning(f"   ❓ Needs clarification: {', '.join(clarify_names)}")
        
        # Check if classification is incomplete
        if total_classified < resource_count:
            missing = resource_count - total_classified
            logger.info(f"📊 Service Classification: {extracted_count}/{resource_count} services for IaC generation")
            logger.info(f"   {missing} services excluded or pending classification")
            logger.info(f"   Response token usage: {run.usage.completion_tokens if run.usage else 'unknown'}/32000")
            logger.info(f"   Validating classification...")
            
            # Log which services were extracted
            extracted_names = [s.get('resource_name', s.get('name', 'Unknown')) for s in result_data.get("services", [])]
            logger.debug(f"   Extracted services: {', '.join(extracted_names)}")            
            # Trigger validation-driven re-extraction if total classification is incomplete
            if phase1_resources and total_classified < resource_count:
                logger.info("🔧 Triggering validation-driven re-classification...")
                complete_services = await self._ensure_complete_extraction(
                    initial_services=result_data.get("services", []),
                    phase1_resources=phase1_resources,
                )
                # Update result data with complete services
                result_data["services"] = complete_services
                extracted_count = len(complete_services)
                logger.info(f"✅ Final classification: {extracted_count} application services for IaC")        
        # Normalize and deduplicate services before building results
        result_data["services"] = self._deduplicate_services(result_data.get("services", []))

        # Convert to ServiceAnalysisResult with flexible field mapping
        services = []
        for s in result_data.get("services", []):
            # Handle agent possibly using different field names
            if "recommendations" in s and "phase1_recommendations" not in s:
                s["phase1_recommendations"] = s.pop("recommendations")
            if "name" in s and "resource_name" not in s:
                s["resource_name"] = s.pop("name")
            if "type" in s and "service_type" not in s:
                s["service_type"] = s.pop("type")
            
            # Ensure required fields have defaults
            s.setdefault("configurations", {})
            s.setdefault("dependencies", [])
            s.setdefault("network_requirements", {})
            s.setdefault("security_requirements", {})
            s.setdefault("priority", 2)
            s.setdefault("phase1_recommendations", [])
            s.setdefault("research_sources", [])
            
            # CRITICAL VALIDATION: arm_type must be present
            if "arm_type" not in s or not s["arm_type"]:
                resource_name = s.get("resource_name", "Unknown")
                logger.error(f"❌ Service '{resource_name}' is missing arm_type field!")
                logger.error("   This is REQUIRED for module generation.")
                logger.error("   Agent must extract arm_type from Phase 1 resource_summary.json")
                raise ValueError(f"Service '{resource_name}' missing required arm_type field. Check Service Analysis Agent prompt.")
            
            # Filter to only fields that ServiceRequirement expects
            valid_fields = {
                "service_type", "resource_name", "arm_type", "resource_category", "configurations",
                "dependencies", "network_requirements", "security_requirements",
                "priority", "phase1_recommendations", "research_sources"
            }
            filtered_data = {k: v for k, v in s.items() if k in valid_fields}
            
            services.append(ServiceRequirement(**filtered_data))
        
        # Extract recommendations summary
        recommendations_summary = result_data.get("recommendations_summary", {
            "security": [],
            "networking": [],
            "configuration": [],
            "dependencies": [],
            "cost_optimization": []
        })
        
        # Extract common_patterns from agent analysis (NEW: Dynamic common module detection)
        common_patterns = result_data.get("common_patterns", {})
        if common_patterns:
            logger.info(f"\n✓ Agent detected {len(common_patterns)} common patterns:")
            for pattern_key, pattern_data in common_patterns.items():
                usage_count = pattern_data.get('usage_count', 0)
                required = pattern_data.get('required', False)
                arm_type = pattern_data.get('arm_type', 'N/A')
                logger.info(f"   - {pattern_key}: {arm_type} (used by {usage_count} services, required={required})")
        else:
            logger.warning(f"\n⚠️  Agent did not provide common_patterns - workflow will use fallback defaults")
            logger.warning("   Update Service Analysis Agent prompt to include common_patterns output")
        
        result = ServiceAnalysisResult(
            services=services,
            total_count=len(services),
            foundation_services=[s for s in services if s.priority == 1],
            application_services=[s for s in services if s.priority == 2],
            integration_services=[s for s in services if s.priority == 3],
            recommendations_summary=recommendations_summary,
            common_patterns=common_patterns,  # NEW: Pass common patterns to Phase 2
            agent_id=self.agent.id,
            thread_id=self.thread.id,
        )
        
        logger.info(f"\n✓ Extracted {result.total_count} services:")
        logger.info(f"  - Foundation (Priority 1): {len(result.foundation_services)} services")
        logger.info(f"  - Application (Priority 2): {len(result.application_services)} services")
        logger.info(f"  - Integration (Priority 3): {len(result.integration_services)} services")
        
        # Log recommendations summary
        total_recommendations = sum(len(v) for v in recommendations_summary.values())
        logger.info(f"✓ Generated recommendations summary with {total_recommendations} recommendations:")
        for category, items in recommendations_summary.items():
            if items:
                logger.info(f"  - {category.replace('_', ' ').title()}: {len(items)} recommendations")
        
        return result

    def _normalize_service_type(self, value: Optional[str]) -> str:
        """Normalize service type for deduplication (no static mapping)."""
        if not value:
            return ""
        import re
        cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", value)
        cleaned = " ".join(cleaned.split())
        return cleaned.strip().lower()

    def _deduplicate_services(self, services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate services by normalized type + arm_type + resource_name."""
        import re
        deduped: Dict[tuple, Dict[str, Any]] = {}

        for raw in services:
            s = dict(raw)

            # Normalize field names early
            if "name" in s and "resource_name" not in s:
                s["resource_name"] = s.pop("name")
            if "type" in s and "service_type" not in s:
                s["service_type"] = s.pop("type")

            service_type = s.get("service_type", "") or ""
            arm_type = s.get("arm_type", "") or ""
            resource_name = s.get("resource_name", "") or ""

            # Strip parenthetical labels from service_type; move to resource_name if missing
            if "(" in service_type and ")" in service_type:
                match = re.search(r"\(([^)]*)\)", service_type)
                if match and not resource_name:
                    resource_name = match.group(1).strip()
                    s["resource_name"] = resource_name
                service_type = re.sub(r"\s*\([^)]*\)\s*", " ", service_type)
                service_type = " ".join(service_type.split()).strip()
                s["service_type"] = service_type

            key = (
                self._normalize_service_type(service_type),
                (arm_type or "").strip().lower(),
                (resource_name or "").strip().lower(),
            )

            if key in deduped:
                existing = deduped[key]

                # Merge list fields
                for list_field in [
                    "dependencies",
                    "phase1_recommendations",
                    "research_sources",
                ]:
                    existing_list = existing.get(list_field, []) or []
                    incoming_list = s.get(list_field, []) or []
                    merged_list = list(dict.fromkeys(existing_list + incoming_list))
                    existing[list_field] = merged_list

                # Merge dict fields without overwriting existing keys
                for dict_field in [
                    "configurations",
                    "network_requirements",
                    "security_requirements",
                ]:
                    existing_dict = existing.get(dict_field, {}) or {}
                    incoming_dict = s.get(dict_field, {}) or {}
                    for k, v in incoming_dict.items():
                        if k not in existing_dict:
                            existing_dict[k] = v
                    existing[dict_field] = existing_dict

                # Prefer higher priority (lower number)
                existing_priority = existing.get("priority", 2)
                incoming_priority = s.get("priority", 2)
                existing["priority"] = min(existing_priority, incoming_priority)

            else:
                deduped[key] = s

        return list(deduped.values())
    
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

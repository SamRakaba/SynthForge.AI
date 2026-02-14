# GitHub Copilot Instructions for SynthForge.AI

**Project:** SynthForge.AI - Azure Architecture Diagram Analyzer  
**Framework:** Microsoft Agent Framework with Azure AI Foundry  
**Last Updated:** February 13, 2026

---

## Core Principles

When generating code for SynthForge.AI, **ALWAYS** follow these fundamental principles:

### 1. Agent-First Architecture ⚡

**DO:**
- Design solutions using the Microsoft Agent Framework pattern
- Create specialized agents for specific tasks (vision analysis, security recommendations, IaC generation)
- Use `azure.ai.agents.AgentsClient` for all agent implementations
- Leverage agent autonomy - let agents choose appropriate tools dynamically
- Implement agents with clear, single responsibilities

**DON'T:**
- Create monolithic functions that should be agents
- Hardcode tool selection - let agents decide based on task
- Bypass the agent framework for AI operations

**Example - Correct Agent Pattern:**
```python
# ✅ CORRECT: Agent-based approach with tool autonomy
class ServiceAnalysisAgent:
    """Agent that analyzes Azure services and recommends patterns."""
    
    def __init__(self, agents_client: AgentsClient):
        self.agents_client = agents_client
        self.tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"]
        )
    
    async def analyze_services(self, resources: List[Resource]) -> AnalysisResult:
        """Agent decides which tool (Bing/MCP) to use dynamically."""
        agent = self._create_agent()
        # Agent autonomously selects appropriate tool for each query
        result = await self._run_agent(agent, resources)
        return result
```

**Example - Incorrect Monolithic Approach:**
```python
# ❌ WRONG: Monolithic function with hardcoded logic
def analyze_services(resources: List[Resource]) -> AnalysisResult:
    """Non-agent approach - avoid this pattern."""
    results = []
    for resource in resources:
        # Hardcoded logic instead of agent decision-making
        if resource.type == "storage":
            result = _analyze_storage(resource)
        elif resource.type == "function":
            result = _analyze_function(resource)
    return results
```

---

### 2. No Repetition - DRY Principle 🚫

**DO:**
- Extract common patterns into reusable functions, classes, or agents
- Use configuration files (YAML) for agent instructions instead of embedding in code
- Reference shared principles (e.g., `global_agent_principles.yaml`) instead of duplicating
- Create utility modules for repeated operations

**DON'T:**
- Duplicate code across multiple agents or modules
- Copy-paste logic - refactor into shared utilities
- Repeat the same instructions in multiple YAML files

**Example - Correct DRY Pattern:**
```python
# ✅ CORRECT: Shared utility for all agents
# synthforge/agents/tool_setup.py
def create_agent_toolset(
    include_bing: bool = True,
    include_mcp: bool = True,
    mcp_servers: Optional[List[str]] = None
) -> ToolConfiguration:
    """Shared tool setup used by all agents."""
    # Single source of truth for tool configuration
    return ToolConfiguration(...)

# Usage in agents
class VisionAgent:
    def __init__(self):
        self.tool_config = create_agent_toolset(include_bing=True)

class SecurityAgent:
    def __init__(self):
        self.tool_config = create_agent_toolset(include_bing=True, include_mcp=True)
```

**Example - Incorrect Repetition:**
```python
# ❌ WRONG: Duplicated tool setup in each agent
class VisionAgent:
    def __init__(self):
        # Repeated code - should use shared utility
        toolset = ToolSet()
        toolset.add(BingGroundingTool(...))
        toolset.add(McpTool(...))

class SecurityAgent:
    def __init__(self):
        # Same code duplicated - violates DRY
        toolset = ToolSet()
        toolset.add(BingGroundingTool(...))
        toolset.add(McpTool(...))
```

---

### 3. No Hardcoding - Dynamic Lookups Only 🔍

**DO:**
- Use Bing Grounding and MCP tools for ALL Azure service information
- Load configuration from environment variables and .env files
- Query documentation dynamically using search patterns
- Let agents discover information at runtime through tools

**DON'T:**
- Hardcode Azure service names, ARM types, or resource properties
- Embed static lists of services, regions, or SKUs
- Store documentation URLs directly in code
- Create static mappings or lookup tables

**Example - Correct Dynamic Lookup:**
```python
# ✅ CORRECT: Dynamic lookup using agent tools
async def get_rbac_roles(self, service_type: str) -> List[RBACRole]:
    """Query Azure documentation for RBAC roles dynamically."""
    query = f"Azure {service_type} built-in RBAC roles site:learn.microsoft.com"
    
    # Agent uses Bing Grounding to find current information
    agent_instructions = f"""
    Search for built-in RBAC roles for {service_type}.
    Extract role names, IDs, and descriptions from Microsoft Learn.
    Cite documentation URLs.
    """
    
    result = await self._run_agent_query(agent_instructions, query)
    return self._parse_rbac_roles(result)
```

**Example - Incorrect Hardcoding:**
```python
# ❌ WRONG: Hardcoded service information
STORAGE_RBAC_ROLES = {
    "Storage Blob Data Contributor": "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
    "Storage Blob Data Reader": "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",
}

# ❌ WRONG: Static service mappings
ARM_TYPE_MAP = {
    "storage": "Microsoft.Storage/storageAccounts",
    "function": "Microsoft.Web/sites",
}
```

---

### 4. Accuracy, Consistency & Pattern Following ✅

**DO:**
- Follow existing code patterns in the repository
- Use Pydantic models for data validation (see `synthforge/models.py`)
- Follow established naming conventions (see examples below)
- Validate all inputs and outputs
- Include type hints for all function parameters and returns
- Write descriptive docstrings following Google/NumPy style

**DON'T:**
- Invent new patterns when existing ones work
- Skip validation or error handling
- Use inconsistent naming conventions
- Generate code without understanding existing patterns

**Naming Conventions:**
```python
# ✅ CORRECT: Follow SynthForge.AI patterns

# Classes: PascalCase
class NetworkFlowAgent:
    """Agent for analyzing network flows."""

# Functions/Methods: snake_case
def analyze_network_topology(self, resources: List[Resource]) -> NetworkTopology:
    """Analyze network topology from detected resources."""

# Constants: UPPER_SNAKE_CASE
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
MAX_RETRY_ATTEMPTS = 3

# Private methods: _snake_case
def _validate_resource(self, resource: Resource) -> bool:
    """Internal validation method."""

# Agents: {Purpose}Agent pattern
class VisionAgent:  # Correct
class SecurityAgent:  # Correct
class ModuleDevelopmentAgent:  # Correct

# Module names: snake_case
# synthforge/agents/network_flow_agent.py
# synthforge/services/icon_catalog.py
# synthforge/models.py

# IaC modules: kebab-case
# modules/storage-account/
# modules/key-vault/
# modules/cognitive-services-account/
```

**Type Hints and Validation:**
```python
# ✅ CORRECT: Comprehensive type hints and validation
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

class DetectedResource(BaseModel):
    """A resource detected from architecture diagram."""
    
    type: str = Field(description="Azure service type")
    name: Optional[str] = Field(default=None, description="Resource name")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence")
    arm_resource_type: Optional[str] = Field(default=None)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

async def process_detections(
    resources: List[DetectedResource],
    threshold: float = 0.7
) -> List[DetectedResource]:
    """
    Filter resources by confidence threshold.
    
    Args:
        resources: List of detected resources to filter
        threshold: Minimum confidence level (0.0-1.0)
        
    Returns:
        Filtered list of high-confidence resources
        
    Raises:
        ValueError: If threshold is invalid
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"Invalid threshold: {threshold}")
    
    return [r for r in resources if r.confidence >= threshold]
```

---

### 5. Modular Coding Approach 🧩

**DO:**
- Create small, focused modules with single responsibilities
- Separate concerns: agents, models, services, utilities
- Use dependency injection for flexibility
- Make components testable in isolation
- Follow the existing project structure

**DON'T:**
- Create large, monolithic files
- Mix different concerns in the same module
- Create tight coupling between components
- Skip modular design for "quick fixes"

**Project Structure Pattern:**
```
synthforge/
├── agents/              # Agent implementations (one agent per file)
│   ├── vision_agent.py
│   ├── security_agent.py
│   ├── network_flow_agent.py
│   └── tool_setup.py    # Shared tool configuration
├── models.py            # Pydantic data models (shared)
├── services/            # Utility services
│   ├── icon_catalog.py  # Icon matching service
│   └── ocr_service.py   # OCR service wrapper
├── prompts/             # Agent instructions (YAML)
│   ├── global_agent_principles.yaml
│   ├── agent_instructions.yaml
│   └── iac_agent_instructions.yaml
├── config.py            # Configuration management
└── workflow.py          # Orchestration logic
```

**Example - Correct Modular Design:**
```python
# ✅ CORRECT: Modular, focused components

# synthforge/services/icon_matcher.py
class IconMatcher:
    """Service for matching detected icons to Azure services."""
    
    def match_icon(self, icon_data: bytes) -> Optional[AzureService]:
        """Match icon to Azure service catalog."""
        # Focused responsibility: icon matching only
        pass

# synthforge/agents/vision_agent.py
class VisionAgent:
    """Agent for analyzing diagrams using GPT-4 Vision."""
    
    def __init__(self, icon_matcher: IconMatcher):
        # Dependency injection for testability
        self.icon_matcher = icon_matcher
    
    async def analyze_diagram(self, image: bytes) -> List[DetectedResource]:
        """Analyze diagram and detect resources."""
        # Uses injected icon_matcher service
        pass
```

**Example - Incorrect Monolithic Design:**
```python
# ❌ WRONG: Everything in one file, mixed concerns
class DiagramAnalyzer:
    """Does everything - avoid this pattern."""
    
    def __init__(self):
        # Too many responsibilities
        self.ocr_engine = ...
        self.icon_matcher = ...
        self.security_analyzer = ...
        self.iac_generator = ...
    
    def analyze_everything(self, image: bytes) -> Dict[str, Any]:
        """One method that does too much."""
        # OCR logic
        # Icon matching logic
        # Security analysis logic
        # IaC generation logic
        pass  # 1000+ lines of mixed concerns
```

---

### 6. MCP Server Validation 🔒

**DO:**
- Verify MCP server URLs are accessible before use
- Check environment variables for MCP server configuration
- Gracefully handle missing or unavailable MCP servers
- Use fallback mechanisms (e.g., Bing Grounding if MCP unavailable)
- Document which MCP servers are legitimate and their purposes

**DON'T:**
- Hardcode MCP server URLs in code
- Assume MCP servers are always available
- Generate code that requires MCP servers without validation
- Use unofficial or unverified MCP server endpoints

**Legitimate MCP Servers for SynthForge.AI:**
```python
# ✅ CORRECT: Validated MCP servers from configuration

LEGITIMATE_MCP_SERVERS = {
    "mslearn": {
        "url_env": "MS_LEARN_MCP_URL",
        "expected": "https://mcp.ai.azure.com",
        "purpose": "Microsoft Learn documentation and Azure resources",
        "required_for": ["Phase 1", "Phase 2"],
        "tools": ["microsoft_docs_search", "microsoft_docs_fetch", "microsoft_code_sample_search"]
    },
    "bicep": {
        "url_env": "BICEP_MCP_URL",
        "expected": "http://localhost:3101",
        "purpose": "Bicep templates and Azure Verified Modules",
        "required_for": ["Phase 2 - Bicep generation"],
        "command": ["npx", "-y", "@microsoft/mcp-server-bicep"]
    },
    "terraform": {
        "url_env": "TERRAFORM_MCP_URL",
        "expected": "http://localhost:3102",
        "purpose": "Terraform provider docs and registry modules",
        "required_for": ["Phase 2 - Terraform generation"],
        "command": ["docker", "run", "-p", "3102:3102", "hashicorp/terraform-mcp-server"]
    },
    "github": {
        "url_env": "GITHUB_MCP_URL",
        "expected": "https://api.githubcopilot.com/mcp",
        "purpose": "GitHub Actions and workflow templates",
        "required_for": ["Phase 2 - CI/CD generation"],
        "note": "Cloud-hosted, no installation required"
    }
}

# ✅ CORRECT: MCP server validation pattern
def validate_mcp_server(server_name: str) -> bool:
    """
    Validate MCP server is configured and accessible.
    
    Args:
        server_name: Name of MCP server to validate
        
    Returns:
        True if server is accessible, False otherwise
    """
    settings = get_settings()
    
    if server_name not in LEGITIMATE_MCP_SERVERS:
        logger.warning(f"Unknown MCP server: {server_name}")
        return False
    
    server_config = LEGITIMATE_MCP_SERVERS[server_name]
    url_env = server_config["url_env"]
    
    # Check environment variable
    server_url = getattr(settings, url_env.lower(), None)
    if not server_url:
        logger.info(f"MCP server {server_name} not configured")
        return False
    
    # Validate URL format
    if not server_url.startswith(("http://", "https://")):
        logger.error(f"Invalid MCP server URL: {server_url}")
        return False
    
    return True

# ✅ CORRECT: Graceful fallback when MCP unavailable
async def get_service_documentation(service_type: str) -> str:
    """Get service documentation with fallback strategy."""
    
    # Try MCP first if available
    if validate_mcp_server("mslearn"):
        try:
            return await _query_mcp_docs(service_type)
        except Exception as e:
            logger.warning(f"MCP query failed: {e}, falling back to Bing")
    
    # Fallback to Bing Grounding
    return await _query_bing_docs(service_type)
```

**Example - Incorrect MCP Usage:**
```python
# ❌ WRONG: Hardcoded MCP URL, no validation
MCP_URL = "https://mcp.example.com"  # Don't hardcode

# ❌ WRONG: No fallback if MCP unavailable
async def get_docs(service: str) -> str:
    # Assumes MCP is always available - will fail
    return await mcp_client.query(service)

# ❌ WRONG: Using unverified MCP server
CUSTOM_MCP_URL = "http://random-server.com/mcp"  # Not legitimate
```

---

## SynthForge.AI-Specific Patterns

### Agent Implementation Pattern

When creating new agents for SynthForge.AI:

```python
"""
{Agent Purpose} Agent for SynthForge.AI.

This agent is responsible for {specific task description}.
Part of the {phase} pipeline.
"""

from typing import List, Optional
from azure.ai.agents import AgentsClient
from synthforge.models import {RelevantModels}
from synthforge.config import get_settings
from synthforge.agents.tool_setup import create_agent_toolset

class {Purpose}Agent:
    """
    {One-line description of agent purpose}.
    
    This agent:
    - {Primary responsibility 1}
    - {Primary responsibility 2}
    - {Primary responsibility 3}
    
    Tools:
    - Bing Grounding: {How used}
    - MCP Servers: {Which ones and why}
    """
    
    def __init__(self, agents_client: Optional[AgentsClient] = None):
        """
        Initialize the {Purpose}Agent.
        
        Args:
            agents_client: Optional AgentsClient instance for testing
        """
        self.settings = get_settings()
        self.agents_client = agents_client or self._create_agents_client()
        
        # Configure tools - agent decides which to use
        self.tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"]  # Specify required MCP servers
        )
    
    def _create_agents_client(self) -> AgentsClient:
        """Create Azure AI Agents client."""
        from azure.ai.agents import AgentsClient
        from azure.identity import DefaultAzureCredential
        
        return AgentsClient(
            endpoint=self.settings.project_endpoint,
            credential=DefaultAzureCredential(),
        )
    
    async def {primary_method}(self, input_data: {InputType}) -> {OutputType}:
        """
        {Description of what this method does}.
        
        Args:
            input_data: {Description of input}
            
        Returns:
            {Description of output}
            
        Raises:
            {Any exceptions that might be raised}
        """
        # 1. Validate input
        self._validate_input(input_data)
        
        # 2. Create agent with instructions
        agent = self._create_agent()
        
        # 3. Run agent with toolset
        result = await self._run_agent(agent, input_data)
        
        # 4. Parse and return result
        return self._parse_result(result)
    
    def _create_agent(self) -> Agent:
        """Create agent with instructions from YAML."""
        # Load instructions from YAML file
        instructions = self._load_instructions()
        
        return self.agents_client.create_agent(
            model=self.settings.model_deployment_name,
            name="{agent-name}",
            instructions=instructions,
            tools=self.tool_config.tools,
            tool_resources=self.tool_config.tool_resources,
        )
    
    def _load_instructions(self) -> str:
        """Load agent instructions from YAML file."""
        # Load from synthforge/prompts/{agent}_instructions.yaml
        import yaml
        from pathlib import Path
        
        prompts_dir = Path(__file__).parent.parent / "prompts"
        instruction_file = prompts_dir / "{agent}_instructions.yaml"
        
        with open(instruction_file) as f:
            config = yaml.safe_load(f)
        
        # Extract instructions for this agent
        return config["{agent_key}"]["instructions"]
    
    def _validate_input(self, input_data: {InputType}) -> None:
        """Validate input data."""
        if not input_data:
            raise ValueError("Input data cannot be empty")
        # Add specific validation
    
    async def _run_agent(self, agent: Agent, input_data: {InputType}) -> str:
        """Execute agent with toolset."""
        # Create thread
        thread = self.agents_client.create_thread()
        
        # Create message
        message = self.agents_client.create_message(
            thread_id=thread.id,
            role="user",
            content=self._format_input(input_data),
        )
        
        # Run agent with toolset (agent chooses which tool to use)
        run = self.agents_client.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
            toolset=self.tool_config.toolset,
        )
        
        # Get response
        messages = self.agents_client.list_messages(thread_id=thread.id)
        return messages.data[0].content[0].text.value
    
    def _format_input(self, input_data: {InputType}) -> str:
        """Format input data for agent."""
        # Convert input to agent-friendly format
        pass
    
    def _parse_result(self, result: str) -> {OutputType}:
        """Parse agent response into structured output."""
        import json
        
        try:
            # Parse JSON response
            data = json.loads(result)
            # Validate with Pydantic model
            return {OutputType}(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse agent result: {e}")
```

### Tool Usage Patterns

```python
# ✅ CORRECT: Agent chooses tool dynamically

# Phase 1 agents: Use Bing Grounding primarily
tool_config = create_agent_toolset(
    include_bing=True,      # Primary tool for Phase 1
    include_mcp=True,       # Optional enhancement
    mcp_servers=["mslearn"] # Microsoft Learn docs
)

# Phase 2 agents: Use Bing + specialized MCP servers
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn", "bicep"]  # Bicep for IaC generation
)

# Agent instruction pattern - let agent choose
agent_instructions = """
You have access to:
1. Bing Grounding - Use for searching Azure documentation and best practices
2. Microsoft Learn MCP - Use for structured Microsoft Learn content

Choose the best tool for each query. Use Bing for broad searches,
MCP for specific documentation lookups.
"""
```

### Configuration Management

```python
# ✅ CORRECT: Load all config from environment

from synthforge.config import get_settings

settings = get_settings()

# Access configuration
project_endpoint = settings.project_endpoint
model_name = settings.model_deployment_name
mcp_url = settings.ms_learn_mcp_url
bing_connection = settings.bing_connection_id

# ❌ WRONG: Hardcoded configuration
PROJECT_ENDPOINT = "https://my-project.services.ai.azure.com"  # Don't do this
```

### Error Handling Pattern

```python
# ✅ CORRECT: Comprehensive error handling

import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def process_resource(resource: Resource) -> Optional[ProcessedResource]:
    """
    Process a detected resource with comprehensive error handling.
    
    Returns None if processing fails, logs error for debugging.
    """
    try:
        # Validate input
        if not resource.type:
            logger.warning(f"Resource missing type: {resource}")
            return None
        
        # Process with error recovery
        result = await _process_with_retry(resource)
        
        # Validate output
        if not _is_valid_result(result):
            logger.error(f"Invalid processing result for {resource.type}")
            return None
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error for {resource.type}: {e}")
        return None
    except ConnectionError as e:
        logger.error(f"Connection error processing {resource.type}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error processing {resource.type}")
        return None

async def _process_with_retry(
    resource: Resource,
    max_retries: int = 3
) -> ProcessedResource:
    """Process with retry logic for transient failures."""
    for attempt in range(max_retries):
        try:
            return await _do_process(resource)
        except TransientError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Retry {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

---

## Anti-Patterns to Avoid

### ❌ Static Service Definitions

```python
# ❌ WRONG: Hardcoded service list
AZURE_SERVICES = [
    "Azure Functions",
    "Azure Storage",
    "Azure SQL Database",
    # ... long hardcoded list
]

# ✅ CORRECT: Dynamic discovery via tools
async def discover_services(diagram: Image) -> List[str]:
    """Let agent discover services using vision and tools."""
    agent_instructions = """
    Analyze the diagram and identify Azure services.
    Use icon matching and documentation lookup to identify services.
    DO NOT use a predefined list - discover dynamically.
    """
    return await agent.analyze(diagram, agent_instructions)
```

### ❌ Hardcoded Documentation URLs

```python
# ❌ WRONG: Hardcoded URLs
STORAGE_DOCS = "https://learn.microsoft.com/azure/storage/..."
FUNCTION_DOCS = "https://learn.microsoft.com/azure/functions/..."

# ✅ CORRECT: Dynamic documentation lookup
async def get_service_docs(service_type: str) -> str:
    """Search for current documentation dynamically."""
    query = f"Azure {service_type} documentation site:learn.microsoft.com"
    return await bing_tool.search(query)
```

### ❌ Mixed Concerns

```python
# ❌ WRONG: One class doing too much
class DiagramProcessor:
    def process_diagram(self, image: bytes):
        # OCR extraction
        text = self._extract_text(image)
        
        # Icon detection
        icons = self._detect_icons(image)
        
        # Security analysis
        security = self._analyze_security(icons)
        
        # IaC generation
        iac_code = self._generate_iac(icons, security)
        
        return iac_code

# ✅ CORRECT: Separate agents for each concern
class VisionAgent:
    """Focused on icon detection only."""
    
class SecurityAgent:
    """Focused on security analysis only."""
    
class ModuleDevelopmentAgent:
    """Focused on IaC generation only."""
```

### ❌ Tight Coupling

```python
# ❌ WRONG: Direct dependencies, hard to test
class VisionAgent:
    def __init__(self):
        self.ocr = OCRService()  # Tightly coupled
        self.matcher = IconMatcher()  # Tightly coupled

# ✅ CORRECT: Dependency injection
class VisionAgent:
    def __init__(
        self,
        ocr_service: OCRService,
        icon_matcher: IconMatcher
    ):
        self.ocr = ocr_service  # Injected, testable
        self.matcher = icon_matcher  # Injected, testable
```

---

## Testing Guidelines

When generating test code:

```python
# ✅ CORRECT: Comprehensive test pattern

import pytest
from unittest.mock import Mock, AsyncMock, patch
from synthforge.agents.vision_agent import VisionAgent
from synthforge.models import DetectedResource

@pytest.fixture
def mock_agents_client():
    """Mock AgentsClient for testing."""
    client = Mock()
    client.create_agent = Mock(return_value=Mock(id="test-agent"))
    client.create_thread = Mock(return_value=Mock(id="test-thread"))
    client.runs.create_and_process = AsyncMock(return_value=Mock())
    return client

@pytest.fixture
def vision_agent(mock_agents_client):
    """Create VisionAgent with mocked dependencies."""
    return VisionAgent(agents_client=mock_agents_client)

@pytest.mark.asyncio
async def test_analyze_diagram_success(vision_agent):
    """Test successful diagram analysis."""
    # Arrange
    test_image = b"test_image_data"
    expected_resources = [
        DetectedResource(
            type="Azure Functions",
            confidence=0.95,
            arm_resource_type="Microsoft.Web/sites"
        )
    ]
    
    # Mock agent response
    vision_agent.agents_client.list_messages = Mock(
        return_value=Mock(
            data=[Mock(
                content=[Mock(
                    text=Mock(value=json.dumps({
                        "resources": [r.dict() for r in expected_resources]
                    }))
                )]
            )]
        )
    )
    
    # Act
    result = await vision_agent.analyze_diagram(test_image)
    
    # Assert
    assert len(result) == 1
    assert result[0].type == "Azure Functions"
    assert result[0].confidence >= 0.9
    assert result[0].arm_resource_type == "Microsoft.Web/sites"

@pytest.mark.asyncio
async def test_analyze_diagram_handles_error(vision_agent):
    """Test error handling in diagram analysis."""
    # Arrange
    vision_agent.agents_client.runs.create_and_process = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await vision_agent.analyze_diagram(b"test_image")
    
    assert "API Error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_analyze_diagram_validates_input(vision_agent):
    """Test input validation."""
    # Act & Assert
    with pytest.raises(ValueError):
        await vision_agent.analyze_diagram(None)
    
    with pytest.raises(ValueError):
        await vision_agent.analyze_diagram(b"")
```

---

## YAML Instruction File Guidelines

When creating agent instruction YAML files:

```yaml
# ✅ CORRECT: Reference shared principles, avoid repetition

# Include shared principles instead of duplicating
includes:
  - global_agent_principles.yaml

# Agent-specific instructions only
agent_name:
  role: "Specific role description"
  
  instructions: |
    You are a {specific role} agent in the SynthForge.AI pipeline.
    
    Your specific responsibilities:
    1. {Specific task 1}
    2. {Specific task 2}
    
    Follow all common_principles from global_agent_principles.yaml.
    
    Use tools dynamically:
    - Bing Grounding for {specific use case}
    - MS Learn MCP for {specific use case}
  
  output_format:
    type: "json"
    schema: "{reference to Pydantic model}"
    
  examples:
    - input: "{example input}"
      output: "{example output}"

# ❌ WRONG: Duplicating shared principles in each file
agent_name:
  instructions: |
    # Don't repeat these in every file:
    - NO STATIC DEFINITIONS
    - DYNAMIC LOOKUPS REQUIRED
    - CITE ALL SOURCES
    # These are in global_agent_principles.yaml
```

---

## Summary Checklist

Before generating code for SynthForge.AI, verify:

- [ ] **Agent-First**: Is this implemented as an agent using Microsoft Agent Framework?
- [ ] **No Repetition**: Is there any duplicated code that could be extracted?
- [ ] **No Hardcoding**: Are all lookups dynamic using Bing/MCP tools?
- [ ] **Accurate & Consistent**: Does this follow existing patterns in the codebase?
- [ ] **Modular**: Is this properly separated with single responsibility?
- [ ] **MCP Validated**: Are all MCP servers verified as legitimate and accessible?
- [ ] **Type Hints**: Are all functions properly typed?
- [ ] **Documentation**: Are docstrings clear and complete?
- [ ] **Error Handling**: Are errors handled gracefully with logging?
- [ ] **Testable**: Can this code be easily tested in isolation?

---

## Additional Resources

- **Project Documentation**: `README.md` - Project overview and setup
- **Agent Principles**: `synthforge/prompts/global_agent_principles.yaml` - Shared agent rules
- **Configuration Guide**: `docs/GITHUB_COPILOT_CONFIGURATION.md` - Copilot setup
- **Data Models**: `synthforge/models.py` - All Pydantic models
- **Tool Setup**: `synthforge/agents/tool_setup.py` - Shared tool configuration

---

**Remember**: When in doubt, look at existing code in the repository for patterns and examples. Consistency is key!

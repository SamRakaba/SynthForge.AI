# Step-by-Step Guide: Converting SynthForge.AI to GitHub Copilot Agents

**Document Version:** 1.0  
**Date:** February 14, 2026  
**Audience:** Developers converting Azure AI Foundry agents to GitHub Copilot Agents

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Phase 1: Project Setup](#2-phase-1-project-setup)
3. [Phase 2: Agent Migration](#3-phase-2-agent-migration)
4. [Phase 3: Tool System Migration](#4-phase-3-tool-system-migration)
5. [Phase 4: Instruction System Migration](#5-phase-4-instruction-system-migration)
6. [Phase 5: Orchestration Migration](#6-phase-5-orchestration-migration)
7. [Phase 6: Testing & Validation](#7-phase-6-testing--validation)
8. [Phase 7: GitHub Integration](#8-phase-7-github-integration)
9. [Phase 8: Deployment](#9-phase-8-deployment)

---

## 1. Prerequisites

### 1.1 Required Access & Accounts

- [ ] GitHub organization or personal account
- [ ] GitHub Copilot license (Enterprise or Business)
- [ ] Access to GitHub Copilot Agents (beta feature)
- [ ] GitHub Personal Access Token with `repo`, `workflow`, `admin:org` scopes

### 1.2 Development Environment

```bash
# Required tools
- Python 3.11+
- Git
- GitHub CLI (gh)
- Node.js 18+ (for GitHub Actions local testing)
- Docker (for containerized agent deployment)

# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Authenticate
gh auth login
```

### 1.3 Knowledge Requirements

- [ ] Familiarity with SynthForge.AI architecture (see COPILOT_AGENTS_ANALYSIS.md)
- [ ] Understanding of GitHub Actions workflows
- [ ] Basic understanding of GitHub Copilot Agents API
- [ ] Python async/await patterns

### 1.4 Repository Setup

```bash
# Create new repository for Copilot-enabled version
gh repo create MyOrg/SynthForge.AI-Copilot --public --clone
cd SynthForge.AI-Copilot

# Copy SynthForge.AI codebase as starting point
git remote add upstream https://github.com/SamRakaba/SynthForge.AI.git
git fetch upstream
git merge upstream/main --allow-unrelated-histories
```

---

## 2. Phase 1: Project Setup

### Step 1.1: Create Project Structure

```bash
# Create directory structure
mkdir -p .github/agents
mkdir -p .github/workflows
mkdir -p .github/copilot
mkdir -p src/agents
mkdir -p src/tools
mkdir -p src/models
mkdir -p src/orchestration
mkdir -p config
mkdir -p tests
```

**Directory Purpose:**

| Directory | Purpose |
|-----------|---------|
| `.github/agents/` | Agent configuration files (replacements for YAML instructions) |
| `.github/workflows/` | GitHub Actions for orchestration |
| `.github/copilot/` | Copilot-specific configurations |
| `src/agents/` | Agent implementation code |
| `src/tools/` | Tool implementations for agents |
| `src/models/` | Data models (Pydantic) |
| `src/orchestration/` | Workflow orchestration logic |
| `config/` | Configuration files |
| `tests/` | Test suites |

### Step 1.2: Initialize Configuration

```bash
# Create base configuration file
cat > config/copilot_agents_config.yaml << 'EOF'
# GitHub Copilot Agents Configuration
project:
  name: "SynthForge.AI Copilot"
  version: "2.0.0"
  description: "Azure architecture diagram analyzer powered by GitHub Copilot Agents"

agents:
  vision:
    enabled: true
    model: "gpt-4o"
    timeout: 300
  
  filter:
    enabled: true
    model: "gpt-4o"
    timeout: 120
  
  network_flow:
    enabled: true
    model: "gpt-4o"
    timeout: 180
  
  security:
    enabled: true
    model: "gpt-4o"
    timeout: 180

orchestration:
  mode: "github_actions"  # or "webhook", "manual"
  phase1_workflow: ".github/workflows/phase1-analysis.yml"
  phase2_workflow: ".github/workflows/phase2-iac-generation.yml"

github:
  artifacts:
    retention_days: 30
    phase1_output: "architecture-analysis"
    phase2_output: "iac-modules"
  
  checks:
    enabled: true
    validation_check_name: "IaC Validation"
EOF
```

### Step 1.3: Set Up Dependencies

```bash
# Create requirements.txt for Copilot version
cat > requirements.txt << 'EOF'
# Core dependencies
pydantic>=2.0.0
pydantic-settings>=2.0.0
pyyaml>=6.0
aiohttp>=3.9.0
asyncio>=3.4.3

# GitHub integration
PyGithub>=2.1.1
gidgethub>=5.3.0

# Data processing
pillow>=10.0.0
python-dotenv>=1.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.1

# Type checking
mypy>=1.5.0
types-PyYAML>=6.0.0

# Logging
rich>=13.5.0
EOF

# Install dependencies
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

---

## 3. Phase 2: Agent Migration

### Step 2.1: Create Agent Base Class

Create `src/agents/base_agent.py`:

```python
"""
Base class for all GitHub Copilot Agents.
Replaces Azure AI Foundry AgentsClient pattern.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

import aiohttp
from pydantic import BaseModel


@dataclass
class AgentConfig:
    """Configuration for a Copilot Agent."""
    name: str
    model: str
    instructions: str
    tools: list[str]
    timeout: int = 300


class CopilotAgent(ABC):
    """
    Base class for GitHub Copilot Agents.
    
    Provides common functionality:
    - Lifecycle management (__aenter__, __aexit__)
    - Instruction loading from config
    - Tool registration
    - Request/response handling
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self._thread_id: Optional[str] = None
    
    async def __aenter__(self):
        """Initialize agent resources."""
        self.logger.info(f"Initializing {self.config.name}")
        
        # Create HTTP session for API calls
        self.session = aiohttp.ClientSession()
        
        # Load instructions
        await self._load_instructions()
        
        # Register tools
        await self._register_tools()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup agent resources."""
        self.logger.info(f"Cleaning up {self.config.name}")
        
        if self.session:
            await self.session.close()
    
    async def _load_instructions(self):
        """Load agent instructions from configuration."""
        # Instructions are already in self.config.instructions
        pass
    
    async def _register_tools(self):
        """Register tools for this agent."""
        # Tool registration handled by GitHub Copilot platform
        pass
    
    @abstractmethod
    async def process(self, input_data: BaseModel) -> BaseModel:
        """
        Main processing method - must be implemented by subclass.
        
        Args:
            input_data: Typed input (Pydantic model)
        
        Returns:
            Typed output (Pydantic model)
        """
        pass
    
    async def _call_copilot_api(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Call GitHub Copilot Agents API.
        
        Args:
            prompt: The prompt to send to the agent
            context: Optional context data
        
        Returns:
            Agent response as string
        """
        # Placeholder - replace with actual Copilot API call
        # In production, this would use GitHub Copilot Agents API
        
        endpoint = "https://api.github.com/copilot/agents/run"  # Example
        headers = {
            "Authorization": f"Bearer {self._get_github_token()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "agent": self.config.name,
            "model": self.config.model,
            "instructions": self.config.instructions,
            "prompt": prompt,
            "context": context or {},
            "tools": self.config.tools
        }
        
        async with self.session.post(endpoint, json=payload, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            return result.get("response", "")
    
    def _get_github_token(self) -> str:
        """Get GitHub token from environment."""
        import os
        return os.environ.get("GITHUB_TOKEN", "")
```

### Step 2.2: Migrate Vision Agent

Create `src/agents/vision_agent.py`:

```python
"""
Vision Agent - Detects Azure service icons from architecture diagrams.
Migrated from Azure AI Foundry to GitHub Copilot Agents.
"""

import base64
from pathlib import Path
from typing import List

from pydantic import BaseModel

from .base_agent import CopilotAgent, AgentConfig
from ..models.detection import DetectionResult, DetectedIcon


class VisionAgent(CopilotAgent):
    """
    Analyzes Azure architecture diagrams to detect service icons.
    
    Uses GPT-4o Vision capabilities via GitHub Copilot Agents.
    """
    
    def __init__(self):
        # Load instructions from config file
        instructions = self._load_vision_instructions()
        
        config = AgentConfig(
            name="VisionAgent",
            model="gpt-4o",
            instructions=instructions,
            tools=[
                "vision_analysis",      # Vision capabilities
                "web_search",           # Replace Bing Grounding
                "file_search"           # Search in codebase
            ],
            timeout=300
        )
        super().__init__(config)
    
    async def process(self, input_data: Path) -> DetectionResult:
        """
        Analyze architecture diagram image.
        
        Args:
            input_data: Path to image file
        
        Returns:
            DetectionResult with detected icons
        """
        self.logger.info(f"Analyzing diagram: {input_data}")
        
        # Encode image as base64
        image_data = self._encode_image(input_data)
        
        # Create prompt
        prompt = self._create_vision_prompt()
        
        # Call Copilot API with image
        context = {
            "image": image_data,
            "image_path": str(input_data)
        }
        
        response = await self._call_copilot_api(prompt, context)
        
        # Parse response to DetectionResult
        result = DetectionResult.model_validate_json(response)
        
        self.logger.info(f"Detected {len(result.icons)} icons")
        return result
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image as base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _create_vision_prompt(self) -> str:
        """Create prompt for vision analysis."""
        return """
        Analyze this Azure architecture diagram and identify ALL Azure service icons.
        
        For each detected icon, provide:
        1. Service name (use tools to validate against official Azure services)
        2. Position in the diagram (x, y coordinates, bounding box)
        3. Confidence level (0.0 to 1.0)
        4. ARM resource type (look up using web_search if needed)
        
        Return results as JSON matching the DetectionResult schema.
        """
    
    def _load_vision_instructions(self) -> str:
        """Load vision agent instructions."""
        # Load from .github/agents/vision_agent.md or YAML
        from ..config import load_agent_instructions
        return load_agent_instructions("vision_agent")
```

### Step 2.3: Create Agent Factory

Create `src/agents/factory.py`:

```python
"""
Agent factory for creating and managing agents.
"""

from typing import Type
from .base_agent import CopilotAgent
from .vision_agent import VisionAgent
from .filter_agent import FilterAgent
from .network_flow_agent import NetworkFlowAgent
from .security_agent import SecurityAgent


class AgentFactory:
    """Factory for creating agents."""
    
    _AGENT_REGISTRY = {
        "vision": VisionAgent,
        "filter": FilterAgent,
        "network_flow": NetworkFlowAgent,
        "security": SecurityAgent,
    }
    
    @classmethod
    def create(cls, agent_name: str) -> CopilotAgent:
        """
        Create an agent by name.
        
        Args:
            agent_name: Name of agent to create (e.g., "vision", "filter")
        
        Returns:
            Instantiated agent
        
        Raises:
            ValueError: If agent name not recognized
        """
        agent_class = cls._AGENT_REGISTRY.get(agent_name)
        if not agent_class:
            raise ValueError(
                f"Unknown agent: {agent_name}. "
                f"Available: {list(cls._AGENT_REGISTRY.keys())}"
            )
        
        return agent_class()
    
    @classmethod
    def register(cls, name: str, agent_class: Type[CopilotAgent]):
        """Register a new agent type."""
        cls._AGENT_REGISTRY[name] = agent_class
```

### Step 2.4: Migrate Remaining Agents

**Repeat the pattern above for:**

1. **FilterAgent** (`src/agents/filter_agent.py`)
   - Input: `DetectionResult`
   - Output: `FilterResult`
   - Tools: `web_search`, `file_search`

2. **NetworkFlowAgent** (`src/agents/network_flow_agent.py`)
   - Input: `FilterResult` + image
   - Output: `NetworkFlowResult`
   - Tools: `vision_analysis`, `web_search`

3. **SecurityAgent** (`src/agents/security_agent.py`)
   - Input: `NetworkFlowResult`
   - Output: `SecurityRecommendation`
   - Tools: `web_search`, `github_search`

4. **ServiceAnalysisAgent** (`src/agents/service_analysis_agent.py`)
   - Input: `ArchitectureAnalysis` (from Phase 1)
   - Output: `ServiceAnalysisResult`
   - Tools: `web_search`, `github_search`

5. **ModuleDevelopmentAgent** (`src/agents/module_development_agent.py`)
   - Input: `ModuleMappingResult`
   - Output: Generated IaC code
   - Tools: `web_search`, `github_search`, `file_search`

---

## 4. Phase 3: Tool System Migration

### Step 3.1: Define Tool Interface

Create `src/tools/base_tool.py`:

```python
"""
Base interface for agent tools.
Replaces Azure AI Foundry tool system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Tool definition for GitHub Copilot."""
    name: str
    description: str
    parameters: Dict[str, Any]


class BaseTool(ABC):
    """Base class for all agent tools."""
    
    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """Return tool definition for Copilot."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute tool with given parameters."""
        pass
```

### Step 3.2: Implement Web Search Tool (replaces Bing Grounding)

Create `src/tools/web_search_tool.py`:

```python
"""
Web Search Tool - Replaces Bing Grounding.
Uses GitHub Copilot's built-in search capabilities.
"""

from typing import List, Dict, Any
from .base_tool import BaseTool, ToolDefinition


class WebSearchTool(BaseTool):
    """
    Web search tool for finding Azure documentation.
    
    Replaces: BingGroundingTool from Azure AI Foundry
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the web for Azure documentation, best practices, and official guidance",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'Azure Storage ARM type')"
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["azure_docs", "microsoft_learn", "github", "all"],
                        "description": "Scope of search"
                    }
                },
                "required": ["query"]
            }
        )
    
    async def execute(self, query: str, scope: str = "azure_docs") -> List[Dict[str, Any]]:
        """
        Execute web search.
        
        Args:
            query: Search query
            scope: Search scope
        
        Returns:
            List of search results with title, url, snippet
        """
        # Implementation would use GitHub Copilot's search API
        # or external search service
        pass
```

### Step 3.3: Implement GitHub Search Tool (replaces GitHub MCP)

Create `src/tools/github_search_tool.py`:

```python
"""
GitHub Search Tool - Search GitHub repositories and code.
Replaces GitHub MCP server.
"""

from typing import List, Dict, Any
from .base_tool import BaseTool, ToolDefinition


class GitHubSearchTool(BaseTool):
    """
    Search GitHub repositories and code.
    
    Primary use: Find Azure Verified Modules for reference.
    """
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="github_search",
            description="Search GitHub repositories, code, and Azure Verified Modules",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["repositories", "code", "issues"],
                        "description": "Type of search"
                    },
                    "org": {
                        "type": "string",
                        "description": "Optional: Scope to specific organization (e.g., 'Azure')"
                    }
                },
                "required": ["query", "type"]
            }
        )
    
    async def execute(
        self, 
        query: str, 
        type: str = "code",
        org: str = None
    ) -> List[Dict[str, Any]]:
        """Execute GitHub search."""
        # Use PyGithub or GitHub API directly
        pass
```

### Step 3.4: Register Tools

Create `src/tools/registry.py`:

```python
"""
Tool registry for managing available tools.
"""

from typing import Dict, List
from .base_tool import BaseTool, ToolDefinition
from .web_search_tool import WebSearchTool
from .github_search_tool import GitHubSearchTool
from .vision_tool import VisionAnalysisTool
from .file_search_tool import FileSearchTool


class ToolRegistry:
    """Central registry for all agent tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register all default tools."""
        self.register("web_search", WebSearchTool())
        self.register("github_search", GitHubSearchTool())
        self.register("vision_analysis", VisionAnalysisTool())
        self.register("file_search", FileSearchTool())
    
    def register(self, name: str, tool: BaseTool):
        """Register a tool."""
        self._tools[name] = tool
    
    def get(self, name: str) -> BaseTool:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_definitions(self, tool_names: List[str]) -> List[ToolDefinition]:
        """Get tool definitions for specified tools."""
        return [
            self._tools[name].get_definition()
            for name in tool_names
            if name in self._tools
        ]


# Global registry instance
tool_registry = ToolRegistry()
```

---

## 5. Phase 4: Instruction System Migration

### Step 4.1: Convert YAML to Markdown Agent Files

GitHub Copilot Agents use Markdown files in `.github/agents/` for instructions.

Create `.github/agents/vision_agent.md`:

```markdown
# Vision Agent

**Purpose:** Analyze Azure architecture diagrams to detect service icons

**Model:** gpt-4o

## Instructions

You are an expert Azure architecture diagram analyzer with deep knowledge of:
- All Azure service icons and their visual representations
- Azure Architecture Icons library
- Azure Well-Architected Framework patterns
- Common diagram patterns and layouts

## Available Tools

You have access to the following tools:

1. **vision_analysis**: Analyze images to detect icons, shapes, text
2. **web_search**: Search Azure documentation for service information
3. **file_search**: Search the codebase for reference data

## Core Rules (BLOCKING severity)

These rules MUST be followed or output will be rejected:

1. **Return ONLY valid JSON** matching the DetectionResult schema exactly
2. **Preserve all data** - don't lose information during processing
3. **No static definitions** - Use tools to look up all service information

## High Priority Rules

These are critical for quality:

1. **Dynamic lookups** - Research all service names, ARM types via tools
2. **Cite sources** - Include documentation URLs for all lookups
3. **Validate detections** - Cross-reference uncertain detections

## Detection Process

1. **Visual Analysis**: Use vision_analysis tool to detect icons
2. **Service Identification**: For each detected icon:
   - Search for official service name using web_search
   - Query: "Azure [visual description] service icon"
3. **ARM Type Lookup**: Get ARM resource type
   - Query: "Azure [service name] ARM resource type"
4. **Confidence Assessment**: Assign confidence level (0.0 to 1.0)
   - 0.9-1.0: Official Azure icon, clearly identifiable
   - 0.7-0.9: Recognizable but some uncertainty
   - < 0.7: Mark as needs_clarification

## Output Format

Return JSON matching this schema:

```json
{
  "icons": [
    {
      "service_name": "Azure Storage Account",
      "arm_type": "Microsoft.Storage/storageAccounts",
      "position": {"x": 100, "y": 200},
      "confidence": 0.95,
      "visual_description": "Blue rectangle with white storage icon"
    }
  ],
  "text_elements": [...],
  "metadata": {...}
}
```

## Tool Usage Strategy

### For Icon Validation
1. Try vision_analysis first (detect icon)
2. Use web_search: "Azure [icon description] official service"
3. If uncertain AND confidence < 0.7, mark needs_clarification

### For ARM Types
- Use web_search: "[service name] ARM resource type"
- Look for "Microsoft.*/resourceType" format

### Failure Handling
- If tool fails, try alternative query
- If still fails, mark item for clarification
- Never guess or use hardcoded values
```

### Step 4.2: Convert Global Principles

Create `.github/copilot/global_principles.md`:

```markdown
# Global Agent Principles

**Shared guidance for ALL agents**

## Core Rules (ALL AGENTS MUST FOLLOW)

### 1. NO STATIC DEFINITIONS
- Never hardcode service names, ARM types, or resource properties
- Implementation: Use tools (web_search, github_search) for all lookups

### 2. DYNAMIC LOOKUPS REQUIRED
- All naming conventions, constraints, properties must come from documentation
- Always research current information, don't rely on training data

### 3. CITE ALL SOURCES
- Every recommendation must reference its documentation source
- Include URLs in all outputs for traceability

### 4. AGENT AUTONOMY
- Agents decide which tools to use based on their specific task
- Instructions provide guidance, not mandates

### 5. THOROUGH VALIDATION
- Validate all detections/lookups against official documentation
- Use multiple tools to cross-reference when uncertain

## Requirement Severity Framework

Use this system for all requirements:

### BLOCKING
**Meaning:** Must be met or output will be rejected/invalid

**Examples:**
- Return ONLY valid JSON matching exact schema
- Preserve all arm_type fields from input exactly
- Never modify or lose data from inputs

### HIGH
**Meaning:** Critical for production quality, security, accuracy

**Examples:**
- Use dynamic lookups, not static lists
- Generate native resources, not module sources
- Cite documentation sources
- Research patterns from official sources

### MEDIUM
**Meaning:** Important for best practices and user experience

**Examples:**
- Detect all resources inside VNets
- Include confidence levels for uncertain detections
- Add descriptions to all parameters

### LOW
**Meaning:** Nice to have, improves quality but not essential

**Examples:**
- Follow consistent formatting conventions
- Add helpful comments in generated code

## Tool Selection Guide

### Phase 1 (Detection/Analysis)
**Primary:** web_search (current Azure documentation)
**Secondary:** github_search (Azure Verified Modules for patterns)
**Fallback:** Mark uncertain items for clarification

### Phase 2 (IaC Generation)
**Primary:** web_search (best practices, ARM schemas)
**Secondary:** github_search (Azure Verified Modules reference)
**Tertiary:** file_search (previous generated code patterns)

## Error Handling

1. **Tool Failures**
   - Retry with simplified query
   - Try alternative tool
   - Mark item as needs_clarification if all fail

2. **Uncertain Detections**
   - Include confidence level in output
   - Mark needs_clarification if confidence < 0.7
   - Never guess or make up information

3. **Missing Information**
   - Document what's missing in output
   - Suggest queries for user to provide clarification
   - Continue processing other items

## Output Standards

- All outputs must be valid JSON matching schema
- Include reasoning/justification for decisions
- Preserve all unique information - don't lose data
- Document merge/transformation decisions
```

### Step 4.3: Create Instruction Loader

Create `src/config/instructions_loader.py`:

```python
"""
Load agent instructions from .github/agents/ directory.
"""

from pathlib import Path
from typing import Optional


def load_agent_instructions(agent_name: str) -> str:
    """
    Load instructions for specified agent.
    
    Args:
        agent_name: Name of agent (e.g., "vision_agent")
    
    Returns:
        Combined instructions (agent-specific + global principles)
    """
    # Load global principles
    global_path = Path(".github/copilot/global_principles.md")
    global_instructions = ""
    if global_path.exists():
        global_instructions = global_path.read_text()
    
    # Load agent-specific instructions
    agent_path = Path(f".github/agents/{agent_name}.md")
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent instructions not found: {agent_path}")
    
    agent_instructions = agent_path.read_text()
    
    # Combine
    return f"{global_instructions}\n\n---\n\n{agent_instructions}"
```

---

## 6. Phase 5: Orchestration Migration

### Step 5.1: Create Phase 1 Workflow

Create `.github/workflows/phase1-analysis.yml`:

```yaml
name: Phase 1 - Architecture Analysis

on:
  workflow_dispatch:
    inputs:
      image_url:
        description: 'URL to architecture diagram image'
        required: true
        type: string
      
      pr_number:
        description: 'PR number to post results to'
        required: false
        type: number

  issues:
    types: [labeled]

jobs:
  setup:
    name: Setup Analysis
    runs-on: ubuntu-latest
    if: github.event.label.name == 'analyze-diagram' || github.event_name == 'workflow_dispatch'
    outputs:
      image_path: ${{ steps.download.outputs.path }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download diagram
        id: download
        run: |
          wget ${{ inputs.image_url }} -O diagram.png
          echo "path=diagram.png" >> $GITHUB_OUTPUT
  
  vision-agent:
    name: Vision Analysis
    needs: setup
    runs-on: ubuntu-latest
    outputs:
      detection_result: ${{ steps.analyze.outputs.result }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run Vision Agent
        id: analyze
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m src.agents.run_agent vision ${{ needs.setup.outputs.image_path }}
      
      - name: Upload detection result
        uses: actions/upload-artifact@v4
        with:
          name: detection-result
          path: output/detection_result.json
  
  filter-agent:
    name: Filter Resources
    needs: vision-agent
    runs-on: ubuntu-latest
    outputs:
      filter_result: ${{ steps.filter.outputs.result }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download detection result
        uses: actions/download-artifact@v4
        with:
          name: detection-result
          path: input/
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run Filter Agent
        id: filter
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m src.agents.run_agent filter input/detection_result.json
      
      - name: Upload filter result
        uses: actions/upload-artifact@v4
        with:
          name: filter-result
          path: output/filter_result.json
  
  network-flow-agent:
    name: Network Flow Analysis
    needs: [setup, filter-agent]
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: filter-result
          path: input/
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run Network Flow Agent
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m src.agents.run_agent network_flow \
            input/filter_result.json \
            ${{ needs.setup.outputs.image_path }}
      
      - name: Upload network flow result
        uses: actions/upload-artifact@v4
        with:
          name: network-flow-result
          path: output/network_flow_result.json
  
  security-agent:
    name: Security Recommendations
    needs: [filter-agent, network-flow-agent]
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          pattern: '*-result'
          path: input/
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run Security Agent
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m src.agents.run_agent security input/
      
      - name: Upload security recommendations
        uses: actions/upload-artifact@v4
        with:
          name: security-recommendations
          path: output/security_recommendations.json
  
  combine-results:
    name: Combine Analysis Results
    needs: [vision-agent, filter-agent, network-flow-agent, security-agent]
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          pattern: '*-result'
          path: artifacts/
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Combine results
        run: |
          python -m src.orchestration.combine_phase1_results artifacts/
      
      - name: Upload architecture analysis
        uses: actions/upload-artifact@v4
        with:
          name: architecture-analysis
          path: output/architecture_analysis.json
          retention-days: 30
      
      - name: Post results to PR
        if: inputs.pr_number
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const analysis = JSON.parse(
              fs.readFileSync('output/architecture_analysis.json', 'utf8')
            );
            
            const comment = `## 📊 Architecture Analysis Complete
            
            **Detected Resources:** ${analysis.resources.length}
            **Network Flows:** ${analysis.data_flows.length}
            **Security Recommendations:** ${analysis.security_recommendations.length}
            
            [Download Full Analysis](../actions/runs/${context.runId})
            `;
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ inputs.pr_number }},
              body: comment
            });
```

### Step 5.2: Create Agent Runner

Create `src/agents/run_agent.py`:

```python
"""
CLI for running individual agents.
Used by GitHub Actions workflows.
"""

import asyncio
import json
import sys
from pathlib import Path

from .factory import AgentFactory
from ..models import load_model_from_json


async def run_agent(agent_name: str, input_path: str, output_dir: str = "output"):
    """
    Run a single agent.
    
    Args:
        agent_name: Name of agent to run
        input_path: Path to input data (JSON file or image)
        output_dir: Directory for output files
    """
    print(f"Running {agent_name} agent...")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load input
    input_data = load_input(agent_name, input_path)
    
    # Create and run agent
    agent = AgentFactory.create(agent_name)
    async with agent:
        result = await agent.process(input_data)
    
    # Save output
    output_file = output_path / f"{agent_name}_result.json"
    with open(output_file, "w") as f:
        f.write(result.model_dump_json(indent=2))
    
    print(f"✓ Results saved to {output_file}")
    print(f"result={result.model_dump_json()}" >> $GITHUB_OUTPUT)


def load_input(agent_name: str, input_path: str):
    """Load input data based on agent type."""
    path = Path(input_path)
    
    if agent_name == "vision":
        # Vision agent takes image path
        return path
    else:
        # Other agents take JSON
        return load_model_from_json(path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m src.agents.run_agent <agent_name> <input_path>")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    input_path = sys.argv[2]
    
    asyncio.run(run_agent(agent_name, input_path))
```

---

## 7. Phase 6: Testing & Validation

### Step 6.1: Create Test Suite

Create `tests/test_vision_agent.py`:

```python
"""
Tests for Vision Agent.
"""

import pytest
from pathlib import Path

from src.agents.vision_agent import VisionAgent
from src.models.detection import DetectionResult


@pytest.mark.asyncio
async def test_vision_agent_initialization():
    """Test agent can be created and initialized."""
    async with VisionAgent() as agent:
        assert agent is not None
        assert agent.config.name == "VisionAgent"


@pytest.mark.asyncio
async def test_vision_agent_analyze(test_diagram):
    """Test vision agent can analyze a diagram."""
    async with VisionAgent() as agent:
        result = await agent.process(test_diagram)
        
        assert isinstance(result, DetectionResult)
        assert len(result.icons) > 0
        assert all(icon.confidence > 0 for icon in result.icons)


@pytest.mark.asyncio
async def test_vision_agent_output_schema(test_diagram):
    """Test output matches expected schema."""
    async with VisionAgent() as agent:
        result = await agent.process(test_diagram)
        
        # Validate schema
        json_data = result.model_dump_json()
        validated = DetectionResult.model_validate_json(json_data)
        
        assert validated == result


@pytest.fixture
def test_diagram():
    """Fixture providing test diagram path."""
    return Path("tests/fixtures/test_diagram.png")
```

### Step 6.2: Create Integration Tests

Create `tests/test_workflow_integration.py`:

```python
"""
Integration tests for full Phase 1 workflow.
"""

import pytest
from pathlib import Path

from src.orchestration.workflow import Phase1Workflow


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase1_workflow_end_to_end(test_diagram):
    """Test complete Phase 1 workflow."""
    workflow = Phase1Workflow()
    
    result = await workflow.run(
        image_path=test_diagram,
        enable_user_review=False,  # Skip for automated test
        enable_security=True
    )
    
    assert result.resources is not None
    assert len(result.resources) > 0
    assert result.data_flows is not None
    assert result.security_recommendations is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_workflow_artifact_generation(test_diagram, tmp_path):
    """Test workflow generates all expected artifacts."""
    workflow = Phase1Workflow()
    
    await workflow.run(
        image_path=test_diagram,
        output_dir=tmp_path,
        enable_user_review=False
    )
    
    # Check all expected files exist
    expected_files = [
        "architecture_analysis.json",
        "resource_summary.json",
        "network_flows.json",
        "security_recommendations.json",
        "vnet_config.json"
    ]
    
    for filename in expected_files:
        filepath = tmp_path / filename
        assert filepath.exists(), f"Missing output: {filename}"
```

### Step 6.3: Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock pytest-cov

# Run unit tests
pytest tests/test_vision_agent.py -v

# Run integration tests (requires Copilot access)
pytest tests/ -m integration -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## 8. Phase 7: GitHub Integration

### Step 8.1: Create Issue Template

Create `.github/ISSUE_TEMPLATE/analyze-diagram.yml`:

```yaml
name: Analyze Architecture Diagram
description: Analyze an Azure architecture diagram to generate IaC code
title: "[Analysis] "
labels: ["analyze-diagram", "automation"]
assignees: []

body:
  - type: markdown
    attributes:
      value: |
        ## Architecture Diagram Analysis Request
        
        Upload your Azure architecture diagram and our Copilot Agents will:
        1. Detect all Azure resources
        2. Analyze network topology
        3. Generate security recommendations
        4. Create IaC code (Bicep/Terraform)
  
  - type: input
    id: diagram_url
    attributes:
      label: Diagram URL
      description: URL to your architecture diagram image
      placeholder: https://example.com/diagram.png
    validations:
      required: true
  
  - type: dropdown
    id: iac_format
    attributes:
      label: IaC Format
      description: Choose your preferred Infrastructure as Code format
      options:
        - Bicep
        - Terraform
        - Both
    validations:
      required: true
  
  - type: dropdown
    id: enable_security
    attributes:
      label: Generate Security Recommendations
      options:
        - "Yes"
        - "No"
      default: 0
  
  - type: textarea
    id: additional_context
    attributes:
      label: Additional Context
      description: Any additional information about your architecture
      placeholder: |
        - Environment: Production/Dev/Test
        - Specific compliance requirements
        - Existing infrastructure to consider
```

### Step 8.2: Create PR Comment Handler

Create `.github/workflows/pr-diagram-comment.yml`:

```yaml
name: Handle Diagram PR Comments

on:
  issue_comment:
    types: [created]

jobs:
  check-command:
    name: Check for Analyze Command
    if: github.event.issue.pull_request && startsWith(github.event.comment.body, '/analyze-diagram')
    runs-on: ubuntu-latest
    
    steps:
      - name: Extract diagram URL
        id: extract
        uses: actions/github-script@v7
        with:
          script: |
            const comment = context.payload.comment.body;
            const urlMatch = comment.match(/https?:\/\/[^\s]+\.(png|jpg|jpeg|svg)/i);
            
            if (!urlMatch) {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.issue.number,
                body: '❌ No image URL found. Usage: `/analyze-diagram <url>`'
              });
              return;
            }
            
            core.setOutput('diagram_url', urlMatch[0]);
      
      - name: Trigger analysis
        if: steps.extract.outputs.diagram_url
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.actions.createWorkflowDispatch({
              owner: context.repo.owner,
              repo: context.repo.repo,
              workflow_id: 'phase1-analysis.yml',
              ref: 'main',
              inputs: {
                image_url: '${{ steps.extract.outputs.diagram_url }}',
                pr_number: String(context.issue.number)
              }
            });
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '✅ Analysis started! Results will be posted here when complete.'
            });
```

### Step 8.3: Add Status Checks

Create `.github/workflows/validation-check.yml`:

```yaml
name: IaC Validation Check

on:
  workflow_run:
    workflows: ["Phase 2 - IaC Generation"]
    types: [completed]

jobs:
  create-check:
    name: Create Validation Check
    runs-on: ubuntu-latest
    
    steps:
      - name: Download validation results
        uses: actions/download-artifact@v4
        with:
          name: validation-results
          github-token: ${{ secrets.GITHUB_TOKEN }}
          run-id: ${{ github.event.workflow_run.id }}
      
      - name: Parse validation results
        id: parse
        run: |
          STATUS=$(jq -r '.overall_status' validation_report.json)
          ERRORS=$(jq -r '.validation_summary.error_count' validation_report.json)
          WARNINGS=$(jq -r '.validation_summary.warning_count' validation_report.json)
          
          echo "status=$STATUS" >> $GITHUB_OUTPUT
          echo "errors=$ERRORS" >> $GITHUB_OUTPUT
          echo "warnings=$WARNINGS" >> $GITHUB_OUTPUT
      
      - name: Create GitHub Check
        uses: actions/github-script@v7
        with:
          script: |
            const status = '${{ steps.parse.outputs.status }}';
            const errors = ${{ steps.parse.outputs.errors }};
            const warnings = ${{ steps.parse.outputs.warnings }};
            
            let conclusion = 'success';
            if (status === 'fail') conclusion = 'failure';
            else if (status === 'warning') conclusion = 'neutral';
            
            await github.rest.checks.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              name: 'IaC Validation',
              head_sha: context.payload.workflow_run.head_sha,
              status: 'completed',
              conclusion: conclusion,
              output: {
                title: 'IaC Validation Results',
                summary: `Errors: ${errors}, Warnings: ${warnings}`,
                text: 'See workflow artifacts for full report'
              }
            });
```

---

## 9. Phase 8: Deployment

### Step 9.1: Environment Setup

Create `.github/workflows/setup-environment.yml`:

```yaml
name: Setup Environment

on:
  workflow_dispatch:

jobs:
  configure:
    name: Configure Repository
    runs-on: ubuntu-latest
    
    steps:
      - name: Create secrets
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.ADMIN_TOKEN }}
          script: |
            // Create repository secrets
            await github.rest.actions.createOrUpdateRepoSecret({
              owner: context.repo.owner,
              repo: context.repo.repo,
              secret_name: 'COPILOT_API_KEY',
              encrypted_value: process.env.COPILOT_API_KEY
            });
      
      - name: Enable GitHub Actions
        run: |
          gh api repos/${{ github.repository }}/actions/permissions \
            --method PUT \
            -F enabled=true \
            -F allowed_actions=all
      
      - name: Configure branch protection
        run: |
          gh api repos/${{ github.repository }}/branches/main/protection \
            --method PUT \
            -F required_status_checks[strict]=true \
            -F required_status_checks[contexts][]=IaC\ Validation
```

### Step 9.2: Create Deployment Guide

Create `docs/DEPLOYMENT.md`:

```markdown
# Deployment Guide

## Prerequisites

1. GitHub Copilot Enterprise or Business license
2. Repository admin access
3. GitHub Personal Access Token with required scopes

## Step 1: Fork or Clone Repository

```bash
gh repo create MyOrg/SynthForge-AI-Copilot \
  --template SamRakaba/SynthForge.AI-Copilot \
  --public
```

## Step 2: Configure Secrets

Navigate to repository Settings → Secrets and variables → Actions

Add these secrets:

| Secret | Description | How to Get |
|--------|-------------|------------|
| `GITHUB_TOKEN` | Auto-provided | Automatic |
| `COPILOT_API_KEY` | Copilot API access | Contact GitHub support |

## Step 3: Enable Workflows

1. Go to Actions tab
2. Enable workflows
3. Run "Setup Environment" workflow

## Step 4: Test Installation

Create a test issue with label `analyze-diagram`:

```
Title: Test Analysis
Body: <url-to-test-diagram>
```

Verify Phase 1 workflow runs successfully.

## Step 5: Configure Agents

Edit agent configurations in `.github/agents/`:

- `vision_agent.md` - Vision analysis settings
- `filter_agent.md` - Filtering rules
- `security_agent.md` - Security recommendations

## Troubleshooting

### Workflow fails with "Agent not found"
- Check Copilot license is active
- Verify agent files exist in `.github/agents/`

### API rate limit errors
- Add `GITHUB_TOKEN` with higher rate limits
- Add delays between agent calls

### Validation check not appearing
- Ensure "IaC Validation" check is configured in branch protection
- Verify validation workflow completed successfully
```

---

## 10. Next Steps & Advanced Topics

### 10.1 Parallel Agent Execution

Modify workflow to run compatible agents in parallel:

```yaml
# Run Network Flow and Security agents in parallel
parallel-agents:
  strategy:
    matrix:
      agent: [network_flow, security]
  needs: filter-agent
  runs-on: ubuntu-latest
  steps:
    - name: Run ${{ matrix.agent }} Agent
      run: python -m src.agents.run_agent ${{ matrix.agent }} input/
```

### 10.2: Add Caching

Speed up workflows with caching:

```yaml
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

- name: Cache agent models
  uses: actions/cache@v4
  with:
    path: ~/.copilot/models
    key: ${{ runner.os }}-copilot-models
```

### 10.3: Add Monitoring

Track agent performance:

```python
import time
from functools import wraps

def monitor_agent(func):
    """Decorator to monitor agent performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            
            # Log to GitHub Actions
            print(f"::notice title=Agent Performance::{func.__name__} completed in {duration:.2f}s")
            
            return result
        except Exception as e:
            duration = time.time() - start
            print(f"::error title=Agent Error::{func.__name__} failed after {duration:.2f}s: {e}")
            raise
    
    return wrapper
```

### 10.4: Implement Webhooks

For real-time processing, add webhook support:

```python
# src/webhooks/diagram_upload.py
from flask import Flask, request
import asyncio

app = Flask(__name__)

@app.route('/webhook/diagram', methods=['POST'])
def handle_diagram_upload():
    """Handle diagram upload webhook."""
    data = request.json
    
    # Trigger workflow
    asyncio.run(trigger_analysis(data['diagram_url'], data['pr_number']))
    
    return {'status': 'accepted'}, 202
```

---

## Conclusion

You now have a complete step-by-step guide for converting SynthForge.AI from Azure AI Foundry to GitHub Copilot Agents. The conversion preserves the core architecture while adapting to GitHub's platform capabilities.

**Key Takeaways:**

1. **Preserve Agent Structure**: Keep the same agent responsibilities and boundaries
2. **Adapt SDK Calls**: Replace Azure AI Foundry SDK with Copilot APIs
3. **Leverage GitHub Features**: Use Actions, artifacts, PR comments natively
4. **Maintain Type Safety**: Keep Pydantic models for data contracts
5. **Preserve Instructions**: Convert YAML to Markdown but keep same guidance

**Next Documentation:**
- See `AGENT_ORCHESTRATION_PATTERNS.md` for advanced orchestration
- See `COPILOT_AGENTS_ANALYSIS.md` for architecture deep-dive
- See `CREATING_NEW_PROJECTS.md` for project scaffolding guide

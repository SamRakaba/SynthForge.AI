# SynthForge.AI Architecture Analysis for GitHub Copilot Agents Conversion

**Document Version:** 1.0  
**Date:** February 14, 2026  
**Purpose:** Comprehensive analysis of SynthForge.AI architecture to inform GitHub Copilot Agents conversion

---

## Executive Summary

SynthForge.AI is a sophisticated multi-agent system built on Azure AI Foundry that analyzes Azure architecture diagrams and generates IaC code. The system consists of 11 specialized agents orchestrated across two phases (Analysis and Code Generation), with a YAML-based instruction system and dynamic tool selection pattern.

**Key Characteristics:**
- **Agent Framework:** Azure AI Foundry Agents (Microsoft Agent Framework)
- **Orchestration:** Sequential pipeline with explicit data passing
- **Configuration:** YAML-based instruction system with inheritance
- **Tool System:** Dynamic selection from Bing Grounding + multiple MCP servers
- **Data Flow:** Strongly-typed Pydantic models for inter-agent communication

---

## 1. Current Architecture Overview

### 1.1 Agent Inventory

| Agent | Phase | Purpose | Input | Output |
|-------|-------|---------|-------|--------|
| **VisionAgent** | 1 | Detect Azure service icons using GPT-4o Vision | Image | DetectionResult |
| **FilterAgent** | 1 | Classify resources as architectural/non-architectural | DetectionResult | FilterResult |
| **InteractiveAgent** | 1 | User review and correction of detected resources | FilterResult | UserReviewResult |
| **NetworkFlowAgent** | 1 | Analyze network topology, VNets, data flows | Image + Resources | NetworkFlowResult |
| **SecurityAgent** | 1 | Generate RBAC and security recommendations | Resources + Flows | SecurityRecommendation |
| **DescriptionAgent** | 1 | Provide component context hints (optional) | Image | ArchitectureDescription |
| **ServiceAnalysisAgent** | 2 | Extract services from Phase 1 analysis | ArchitectureAnalysis | ServiceAnalysisResult |
| **ModuleMappingAgent** | 2 | Map services to Bicep/Terraform modules | ServiceAnalysisResult | ModuleMappingResult |
| **ModuleDevelopmentAgent** | 2 | Generate native IaC code | ModuleMappingResult | Generated Code |
| **DeploymentWrapperAgent** | 2 | Create orchestration templates | Modules | Orchestration Code |
| **CodeQualityAgent** | 2 | Validate IaC code quality | Generated Code | ValidationResult |

### 1.2 Orchestration Pattern

**Phase 1: Architecture Analysis Workflow**

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: ANALYSIS                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Input: Architecture Diagram Image]                        │
│                    ↓                                        │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 0: Description Agent (Optional) │                 │
│  │ Purpose: Provide component context    │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [ArchitectureDescription]             │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 1: Vision Agent                │                 │
│  │ Purpose: Detect Azure service icons  │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [DetectionResult]                      │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 2: Filter Agent                │                 │
│  │ Purpose: Classify resources          │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [FilterResult]                         │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 3: Interactive Agent (Optional)│                 │
│  │ Purpose: User review/correction      │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [UserReviewResult]                     │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 4: Network Flow Agent          │                 │
│  │ Purpose: Analyze network topology    │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [NetworkFlowResult]                    │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 5: Security Agent (Optional)   │                 │
│  │ Purpose: RBAC & security             │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [SecurityRecommendation]              │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 6: Analysis Builder            │                 │
│  │ Purpose: Combine all outputs         │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓                                        │
│  [Output: ArchitectureAnalysis + 5 JSON files]            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Phase 2: IaC Generation Workflow**

```
┌─────────────────────────────────────────────────────────────┐
│                PHASE 2: IAC GENERATION                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Input: Phase 1 JSON outputs]                              │
│                    ↓                                        │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 1: Service Analysis Agent      │                 │
│  │ Purpose: Extract service requirements│                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [ServiceAnalysisResult]               │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 2: User Validation Workflow    │                 │
│  │ Purpose: Confirm service list        │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [Validated Services]                   │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 3: Module Mapping Agent        │                 │
│  │ Purpose: Map services to modules     │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [ModuleMappingResult]                 │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 4: Module Development Agent    │                 │
│  │ Purpose: Generate IaC code           │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [Generated Modules]                    │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 5: Deployment Wrapper Agent    │                 │
│  │ Purpose: Create orchestration        │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓ [Orchestration Templates]              │
│  ┌──────────────────────────────────────┐                 │
│  │ Stage 6: CI/CD Pipeline Generation   │                 │
│  │ Purpose: DevOps pipeline templates   │                 │
│  └──────────────────────────────────────┘                 │
│                    ↓                                        │
│  [Output: Complete IaC solution + CI/CD]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Data Flow Architecture

**Inter-Agent Communication Pattern:**

```python
# Explicit data passing between agents
async def run_workflow(self, image_path: Path) -> ArchitectureAnalysis:
    # Stage 1: Vision detection
    detection_result: DetectionResult = await self._run_vision_analysis(image_path)
    
    # Stage 2: Filter resources (receives detection_result)
    filter_result: FilterResult = await self._run_filter(detection_result)
    
    # Stage 3: User review (receives filter_result)
    final_resources: List[AzureResource] = await self._run_interactive_review(filter_result)
    
    # Stage 4: Network flow (receives final_resources)
    network_result: NetworkFlowResult = await self._run_network_flow_analysis(
        image_path, final_resources
    )
    
    # Stage 5: Security (receives final_resources + network_result)
    security_recs: List[SecurityRecommendation] = await self._run_security_analysis(
        final_resources, network_result
    )
    
    # Stage 6: Combine all outputs
    return ArchitectureAnalysis(
        resources=final_resources,
        data_flows=network_result.flows,
        security_recommendations=security_recs,
        ...
    )
```

**Key Data Structures:**

```python
# Phase 1 outputs
DetectionResult          # Icons, text, initial flows
FilterResult            # Classified resources
UserReviewResult        # User corrections
NetworkFlowResult       # Network topology
SecurityRecommendation  # RBAC and security config
ArchitectureAnalysis    # Final combined output

# Phase 2 outputs
ServiceAnalysisResult   # Extracted services
ModuleMappingResult     # Service-to-module mappings
Generated Modules       # Bicep/Terraform code
Orchestration Templates # Deployment files
CI/CD Pipelines         # DevOps automation
```

---

## 2. Instruction System Architecture

### 2.1 YAML Hierarchy

```
synthforge/prompts/
├── global_agent_principles.yaml          # Foundation (inherited by all)
│   ├── common_principles                # Core rules for all agents
│   ├── requirement_severity             # BLOCKING/HIGH/MEDIUM/LOW
│   ├── mcp_tools_guide                  # Tool selection strategies
│   ├── common_iac_principles            # IaC generation rules
│   └── failure_handling                 # Error handling patterns
│
├── agent_instructions.yaml               # Phase 1 agents
│   ├── includes: [global_agent_principles.yaml]
│   ├── vision_agent                     # Icon detection instructions
│   ├── filter_agent                     # Classification instructions
│   ├── interactive_agent                # User review instructions
│   ├── network_flow_agent               # Network analysis instructions
│   ├── security_agent                   # Security recommendations
│   └── description_agent                # Component context
│
├── iac_agent_instructions.yaml           # Phase 2 agents
│   ├── includes: [global_agent_principles.yaml]
│   ├── service_analysis_agent           # Service extraction instructions
│   ├── module_mapping_agent             # Module mapping instructions
│   ├── module_development_agent         # Code generation instructions
│   └── deployment_wrapper_agent         # Orchestration instructions
│
└── code_quality_agent.yaml               # Code validation
    ├── includes: [global_agent_principles.yaml]
    └── code_quality_agent                # Validation rules
```

### 2.2 Instruction Loading Mechanism

```python
# In synthforge/prompts/__init__.py
def load_yaml_with_includes(yaml_path: Path) -> dict:
    """Load YAML with support for includes directive."""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Process includes
    if 'includes' in data:
        for include_file in data['includes']:
            include_path = yaml_path.parent / include_file
            include_data = load_yaml_with_includes(include_path)
            # Merge included data (included data takes lower priority)
            data = {**include_data, **data}
    
    return data

# Agent retrieves its instructions
def get_vision_agent_instructions() -> str:
    """Get instructions for Vision Agent."""
    instructions = load_yaml_with_includes(AGENT_INSTRUCTIONS_PATH)
    return instructions['vision_agent']['instructions']
```

### 2.3 Key Instruction Patterns

**Common Principles (Applied to ALL Agents):**

```yaml
common_principles:
  core_rules:
    - rule: "NO STATIC DEFINITIONS"
      guidance: "Never hardcode service names, ARM types, or resource properties"
      implementation: "Use tools (Bing, MS Learn MCP) for all lookups"
      
    - rule: "DYNAMIC LOOKUPS REQUIRED"
      guidance: "All naming conventions, constraints must come from documentation"
      
    - rule: "CITE ALL SOURCES"
      guidance: "Every recommendation must reference documentation URL"
      
    - rule: "AGENT AUTONOMY"
      guidance: "Agents decide which tools to use based on task"
```

**Severity Framework:**

```yaml
requirement_severity:
  BLOCKING:
    description: "Must be met or output will be rejected/invalid"
    examples:
      - "Return ONLY valid JSON matching exact schema"
      - "Preserve all arm_type fields from input exactly"
      
  HIGH:
    description: "Critical for production quality"
    examples:
      - "Use dynamic lookups, not static lists"
      - "Cite documentation sources"
      
  MEDIUM:
    description: "Important for best practices"
    examples:
      - "Include confidence levels for uncertain detections"
      
  LOW:
    description: "Nice to have, improves quality"
    examples:
      - "Follow consistent formatting conventions"
```

---

## 3. Tool System Architecture

### 3.1 Tool Inventory

| Tool | Type | Purpose | When to Use |
|------|------|---------|-------------|
| **Bing Grounding** | Web Search | Search Azure documentation, current best practices | Real-time docs, RBAC roles, naming rules |
| **MS Learn MCP** | Structured Docs | Official Azure documentation, ARM schemas | Official docs, API versions, code samples |
| **Azure MCP** | Azure Operations | Azure CLI, Resource Manager, Bicep support | Azure resource operations |
| **Bicep MCP** | IaC | Bicep templates, Azure Verified Modules | Bicep code generation |
| **Terraform MCP** | IaC | Terraform azurerm provider, modules | Terraform code generation |
| **Azure DevOps MCP** | CI/CD | ADO pipeline templates, DevOps patterns | ADO pipeline generation |
| **GitHub MCP** | CI/CD | GitHub Actions, repo search | GitHub workflow generation |

### 3.2 Tool Selection Strategy

**Phase 1 (Analysis) Tool Priority:**
```
Primary: Bing Grounding (current documentation)
Secondary: MS Learn MCP (official Azure docs)
Fallback: Agent reasoning with confidence marking
```

**Phase 2 (IaC Generation) Tool Priority:**
```
Primary: Bing Grounding (best practices)
Secondary: MS Learn MCP (ARM schemas)
Tertiary: Format-specific MCP (Bicep/Terraform)
Quaternary: GitHub MCP (Azure Verified Modules reference)
```

### 3.3 Tool Setup Pattern

```python
# In synthforge/agents/tool_setup.py
def create_agent_toolset(
    include_bing: bool = True,
    include_mcp: bool = True,
    mcp_servers: list[str] = None
) -> ToolSet:
    """Create unified toolset for agents."""
    tools = []
    
    if include_bing:
        tools.append(BingGroundingTool(connection_id=BING_CONNECTION_ID))
    
    if include_mcp and mcp_servers:
        for server in mcp_servers:
            tools.append(McpTool(server_label=server))
    
    return ToolSet(tools=tools)

# Usage in agent initialization
async def __aenter__(self):
    toolset = create_agent_toolset(
        include_bing=True,
        include_mcp=True,
        mcp_servers=["mslearn"]  # MS Learn MCP
    )
    
    self.agent = await self.agents_client.create_agent(
        instructions=self.instructions,
        tools=toolset.tools,
        ...
    )
```

---

## 4. Agent Implementation Pattern

### 4.1 Standard Agent Structure

```python
class VisionAgent:
    """Analyzes Azure architecture diagrams to detect service icons."""
    
    def __init__(self):
        self.config = get_settings()
        self.logger = logging.getLogger(__name__)
        self.agents_client = None
        self.agent = None
        self.agent_id = None
    
    async def __aenter__(self):
        """Initialize agent with Azure AI Foundry."""
        # Create AgentsClient
        credential = DefaultAzureCredential()
        self.agents_client = AgentsClient(
            endpoint=self.config.project_endpoint,
            credential=credential
        )
        
        # Load instructions
        self.instructions = get_vision_agent_instructions()
        
        # Setup tools
        toolset = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=["mslearn"]
        )
        
        # Create agent
        self.agent = await self.agents_client.create_agent(
            model=self.config.model_name,
            name="VisionAgent",
            instructions=self.instructions,
            tools=toolset.tools
        )
        self.agent_id = self.agent.id
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup agent."""
        if self.agent_id:
            await self.agents_client.delete_agent(self.agent_id)
    
    async def analyze(self, image_path: Path) -> DetectionResult:
        """Main agent method - implements specific logic."""
        # Create thread
        thread = await self.agents_client.create_thread()
        
        # Upload image
        file_id = await self._upload_image(image_path)
        
        # Send message
        message = await self.agents_client.create_message(
            thread_id=thread.id,
            role="user",
            content="Analyze this Azure architecture diagram",
            file_ids=[file_id]
        )
        
        # Run agent
        run = await self.agents_client.create_run(
            thread_id=thread.id,
            agent_id=self.agent_id
        )
        
        # Wait for completion
        while run.status in ["queued", "in_progress"]:
            await asyncio.sleep(1)
            run = await self.agents_client.get_run(thread.id, run.id)
        
        # Parse response
        messages = await self.agents_client.list_messages(thread.id)
        response_text = messages.data[0].content[0].text.value
        
        # Convert to typed result
        return DetectionResult.model_validate_json(response_text)
```

### 4.2 Common Agent Patterns

**Pattern 1: Context Manager for Lifecycle**
```python
async with VisionAgent() as agent:
    result = await agent.analyze(image_path)
# Agent automatically cleaned up
```

**Pattern 2: Typed Input/Output**
```python
def analyze(self, input: DetectionResult) -> FilterResult:
    """Strongly typed inputs and outputs."""
    pass
```

**Pattern 3: Tool Access in Instructions**
```yaml
vision_agent:
  instructions: |
    You have access to tools:
    - normalize_service_name: Look up Azure service names
    - Bing Grounding: Search Azure documentation
    - MS Learn MCP: Official Azure docs
    
    Use these tools to validate all detections.
```

---

## 5. Key Design Patterns

### 5.1 No Static Definitions Pattern

**Problem:** Hardcoded lists become outdated

**Solution:** Dynamic lookups via tools

```python
# ❌ BAD: Static mapping
SERVICE_MAPPINGS = {
    "Storage": "Microsoft.Storage/storageAccounts",
    "VM": "Microsoft.Compute/virtualMachines"
}

# ✅ GOOD: Dynamic lookup
async def get_arm_type(service_name: str) -> str:
    """Look up ARM type dynamically using tools."""
    # Agent uses Bing or MCP to find current ARM type
    return await self.tool.lookup_arm_type(service_name)
```

### 5.2 Agent Autonomy Pattern

**Problem:** Pre-defined tool assignments limit flexibility

**Solution:** Agents decide which tools to use

```yaml
# Instructions guide, don't mandate
tool_usage_strategy: |
  You have multiple tools available. Choose the best one:
  
  For icon validation:
    1. Try normalize_service_name first (official catalog)
    2. If not found, use Bing: "Azure [icon description] service"
    3. If still uncertain, mark needs_clarification
  
  For ARM types:
    - Use resolve_arm_type for confirmed services
    - Use MS Learn MCP for ARM schema details
```

### 5.3 Severity-Based Requirements Pattern

**Problem:** All requirements treated equally

**Solution:** Tiered severity system

```yaml
# BLOCKING - must work or pipeline fails
- "Return ONLY valid JSON matching schema"

# HIGH - critical quality/security
- "Use dynamic lookups, not static lists"

# MEDIUM - best practices
- "Include confidence levels for detections"

# LOW - nice to have
- "Follow consistent formatting"
```

### 5.4 Includes-Based Configuration Pattern

**Problem:** Duplicate instructions across agents

**Solution:** Inheritance via includes

```yaml
# agent_instructions.yaml
includes:
  - global_agent_principles.yaml

vision_agent:
  instructions: |
    [Agent-specific instructions]
    
    # Global principles automatically inherited:
    # - NO STATIC DEFINITIONS
    # - DYNAMIC LOOKUPS
    # - CITE SOURCES
```

---

## 6. Current Limitations & Considerations

### 6.1 Sequential Processing

**Current State:** Agents run sequentially in strict order

**Implication for Copilot:** 
- Need to preserve dependencies (e.g., Filter requires Vision output)
- Some agents could potentially run in parallel (e.g., Network Flow + Security)
- Consider event-driven orchestration vs sequential

### 6.2 Azure AI Foundry Dependency

**Current State:** Tightly coupled to Azure AI Foundry SDK

**Implication for Copilot:**
- Replace `AgentsClient` with GitHub Copilot Agents API
- Adapt tool system to Copilot's tool format
- Migrate from Bing Grounding to Copilot-compatible tools

### 6.3 File-Based Persistence

**Current State:** Phase 1 outputs saved as JSON files for Phase 2 input

**Implication for Copilot:**
- Consider GitHub repository as state store
- Use PR descriptions, comments, or artifacts for inter-phase communication
- Leverage GitHub Actions for workflow orchestration

### 6.4 User Interaction Model

**Current State:** CLI-based user review (InteractiveAgent)

**Implication for Copilot:**
- Shift to GitHub PR review comments
- Use Copilot Chat for user interaction
- Consider GitHub Issues for clarification requests

---

## 7. Strengths of Current Architecture

### 7.1 Separation of Concerns
- Each agent has single, well-defined responsibility
- Clear boundaries between agents
- Easy to modify individual agents without affecting others

### 7.2 Dynamic Configuration
- YAML-based instructions enable behavior changes without code changes
- Includes system reduces duplication
- Tool selection guidance vs hardcoded tool usage

### 7.3 Type Safety
- Pydantic models for all data structures
- Compile-time validation of data flow
- Clear contracts between agents

### 7.4 Research-Based Approach
- Agents use tools to research current information
- No static definitions that become outdated
- Documentation citations for traceability

### 7.5 Extensibility
- Easy to add new agents (follow established pattern)
- Easy to add new tools (unified tool setup)
- Easy to add new instructions (YAML-based)

---

## 8. Recommended Conversion Approach

### 8.1 Phase 1: Direct Translation (Preserve Architecture)

**Goal:** Minimal changes, preserve agent structure and orchestration

**Steps:**
1. Replace Azure AI Foundry SDK with Copilot Agents API
2. Convert tool system to Copilot-compatible format
3. Migrate YAML instructions to Copilot agent configurations
4. Adapt data flow for GitHub environment (PR artifacts vs JSON files)
5. Replace CLI interaction with GitHub PR comments

### 8.2 Phase 2: GitHub-Native Optimization

**Goal:** Leverage GitHub-specific features

**Steps:**
1. Use GitHub Actions for workflow orchestration
2. Store state in PR descriptions, comments, or workflow artifacts
3. Implement user review via PR comments/reviews
4. Add GitHub Checks API integration for validation reports
5. Use GitHub Copilot Chat for interactive scenarios

### 8.3 Phase 3: Advanced Patterns

**Goal:** Optimize for Copilot Agents platform

**Steps:**
1. Implement parallel agent execution where possible
2. Add event-driven orchestration for long-running workflows
3. Implement agent collaboration patterns (multi-agent reasoning)
4. Add continuous learning from user feedback
5. Integrate with GitHub Copilot Workspace for IDE experience

---

## 9. Technical Debt & Improvement Opportunities

### 9.1 Identified Improvements

1. **Parallel Execution**
   - Network Flow Agent and Security Agent could run in parallel
   - Multiple ModuleDevelopmentAgent instances for different services

2. **Error Recovery**
   - Add retry logic for transient failures
   - Implement checkpointing for long workflows
   - Add rollback capabilities

3. **Testing**
   - Add integration tests for full pipeline
   - Add unit tests for individual agents
   - Add performance benchmarks

4. **Monitoring**
   - Add telemetry for agent performance
   - Add cost tracking for API calls
   - Add quality metrics for outputs

### 9.2 Migration Considerations

**Keep:**
- Agent separation and responsibilities
- YAML-based instruction system
- Dynamic lookup pattern
- Severity framework
- Type safety with Pydantic

**Adapt:**
- SDK calls (Azure AI Foundry → Copilot)
- Tool system (Bing/MCP → Copilot tools)
- State management (JSON files → GitHub)
- User interaction (CLI → GitHub UI)

**Enhance:**
- Add parallel execution
- Add GitHub-native features (Checks, Status, Reviews)
- Add webhook-based triggers
- Add collaboration features

---

## 10. Appendix: Code Examples

### 10.1 Agent Initialization Pattern

```python
# Current (Azure AI Foundry)
async with VisionAgent() as agent:
    result = await agent.analyze(image_path)

# Proposed (GitHub Copilot)
async with CopilotAgent(
    name="VisionAgent",
    instructions=load_instructions("vision_agent"),
    tools=["vision_analysis", "bing_search"]
) as agent:
    result = await agent.analyze(image_path)
```

### 10.2 Tool Invocation Pattern

```python
# Current (Azure AI Foundry)
toolset = ToolSet([
    BingGroundingTool(connection_id=BING_ID),
    McpTool(server_label="mslearn")
])

# Proposed (GitHub Copilot)
tools = [
    CopilotTool(name="web_search", description="Search documentation"),
    CopilotTool(name="github_search", description="Search GitHub repos"),
    CopilotTool(name="file_search", description="Search in codebase")
]
```

### 10.3 Data Flow Pattern

```python
# Current (JSON files)
with open("architecture_analysis.json") as f:
    analysis = ArchitectureAnalysis.model_validate_json(f.read())

# Proposed (GitHub artifacts)
artifact = await github.download_artifact("architecture-analysis")
analysis = ArchitectureAnalysis.model_validate_json(artifact.content)
```

---

## Conclusion

SynthForge.AI demonstrates a well-architected multi-agent system with clear separation of concerns, dynamic configuration, and research-based decision making. The architecture is well-suited for conversion to GitHub Copilot Agents, with the main adaptation points being:

1. **SDK Migration:** Azure AI Foundry → GitHub Copilot Agents API
2. **Tool System:** Bing/MCP → Copilot-native tools
3. **State Management:** JSON files → GitHub artifacts/PR data
4. **User Interaction:** CLI → GitHub UI (PR comments, reviews)
5. **Orchestration:** Python async → GitHub Actions/webhooks

The existing YAML-based instruction system, severity framework, and agent patterns can be preserved, making this a primarily technical migration rather than an architectural redesign.

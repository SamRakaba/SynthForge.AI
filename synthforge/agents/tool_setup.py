"""
Tool Setup Utility for SynthForge.AI Agents.

Provides a unified way to configure both Bing Grounding and MCP tools
for agents. Agents can use whichever tool is best suited for their task.

Design Principles:
- NO STATIC MAPPINGS - All lookups are dynamic via tools
- Agent chooses best tool based on the task at hand
- Bing Grounding: Web search for Azure documentation
- MCP Server: Direct access to Microsoft Learn structured content

Usage Pattern (from lab 03c-use-agent-tools-with-mcp):
    from azure.ai.agents.models import McpTool, ToolSet, BingGroundingTool
    
    toolset = ToolSet()
    toolset.add(bing_tool)  # BingGroundingTool
    toolset.add(mcp_tool)   # McpTool
    
    run = agents_client.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id,
        toolset=toolset  # Agent can use any tool in the set
    )
"""

from typing import Optional, Tuple, List
from dataclasses import dataclass, field

from azure.ai.agents.models import (
    BingGroundingTool,
    McpTool,
    ToolSet,
)

from synthforge.config import get_settings


@dataclass
class ToolConfiguration:
    """Container for configured tools and their resources."""
    toolset: ToolSet
    tools: List  # Tool definitions for create_agent
    tool_resources: Optional[dict]  # Tool resources for create_agent
    has_bing: bool
    has_mcp: bool
    mcp_servers: List[str] = field(default_factory=list)  # Labels of active MCP servers


def create_agent_toolset(
    include_bing: bool = True,
    include_mcp: bool = True,
    mcp_servers: Optional[List[str]] = None,
) -> ToolConfiguration:
    """
    Create a ToolSet with Bing Grounding and multiple MCP servers.
    
    The agent can use whichever tool is best for the task:
    - Bing Grounding: Best for searching web documentation, finding examples, current best practices
    - MS Learn MCP: Best for structured Microsoft Learn content, API specs, code samples
      * microsoft_docs_search - semantic search across MS Learn
      * microsoft_docs_fetch - fetch full documentation
      * microsoft_code_sample_search - search code samples with language filter
    - Azure MCP: All Azure tools in one server (RECOMMENDED for Phase 2)
      * Azure CLI, Resource Manager, Bicep support, and more
      * Replaces the need for separate Bicep and Azure DevOps MCPs
    - Bicep MCP: Bicep template generation, Azure Verified Modules (AVM), best practices
      * Use only if Azure MCP is not available
    - Terraform MCP (HashiCorp Official): 
      * Terraform Registry API integration (providers, modules, policies)
      * HCP Terraform & Terraform Enterprise support
      * Workspace operations (create, update, delete, variables, runs)
      * Private registry access
      * azurerm provider documentation
    - Azure DevOps MCP: Pipeline templates, DevOps best practices
      * Use only if Azure MCP is not available
    - GitHub MCP: GitHub Actions workflows, CI/CD templates
    
    Args:
        include_bing: Whether to include Bing Grounding tool
        include_mcp: Whether to include MCP servers
        mcp_servers: List of MCP server labels to include. If None, includes all Phase 1 servers.
                    Options: ["mslearn", "azure", "bicep", "terraform", "azure-devops", "github"]
        
    Returns:
        ToolConfiguration with toolset and tool definitions
    """
    settings = get_settings()
    
    toolset = ToolSet()
    tools = []
    tool_resources = None
    has_bing = False
    has_mcp = False
    active_mcp_servers = []
    
    # Default to MS Learn only for Phase 1
    if mcp_servers is None:
        mcp_servers = ["mslearn"]
    
    # Add Bing Grounding if connection ID is available
    if include_bing and settings.bing_connection_id:
        bing_tool = BingGroundingTool(connection_id=settings.bing_connection_id)
        toolset.add(bing_tool)
        tools.extend(bing_tool.definitions)
        tool_resources = bing_tool.resources
        has_bing = True
    
    # Add MCP servers based on configuration
    if include_mcp:
        mcp_configs = {
            # Microsoft Foundry MCP (Azure AI Foundry operations)
            # HTTP-based MCP server for model management, deployments, evaluations
            # Documentation: https://learn.microsoft.com/azure/ai-foundry/mcp/
            "mslearn": settings.ms_learn_mcp_url,  # Now points to Foundry MCP
            "azure": settings.azure_mcp_url,
            "bicep": settings.bicep_mcp_url,
            "terraform": settings.terraform_mcp_url,
            "azure-devops": settings.azure_devops_mcp_url,
            "github": settings.github_mcp_url,
        }
        
        for server_label in mcp_servers:
            server_url = mcp_configs.get(server_label)
            if server_url:
                mcp_tool = McpTool(
                    server_label=server_label,
                    server_url=server_url,
                )
                # Set to "never" to allow automatic tool execution
                # Foundry MCP tools are discovered dynamically via natural language
                mcp_tool.set_approval_mode("never")
                toolset.add(mcp_tool)
                active_mcp_servers.append(server_label)
                has_mcp = True
    
    return ToolConfiguration(
        toolset=toolset,
        tools=tools if tools else None,
        tool_resources=tool_resources,
        has_bing=has_bing,
        has_mcp=has_mcp,
        mcp_servers=active_mcp_servers,
    )


def get_tool_instructions() -> str:
    """
    Get instructions for agents on how to use available tools.
    
    Returns:
        String with tool usage guidance for agent instructions
    """
    settings = get_settings()
    
    instructions = []
    
    if settings.bing_connection_id:
        instructions.append("""
## Bing Grounding Tool
Use Bing Grounding for web searches to find Azure documentation:
- Search pattern: "Azure [service] [topic] site:learn.microsoft.com"
- Best for: Finding examples, best practices, current documentation
- Examples:
  - "Azure Storage private endpoint DNS zone site:learn.microsoft.com"
  - "Azure Functions RBAC built-in roles site:learn.microsoft.com"
  - "Azure Cosmos DB naming conventions site:learn.microsoft.com"
""")
    
    if settings.ms_learn_mcp_url:
        instructions.append("""
## Microsoft Learn MCP Server (Phase 1)
Use MCP tools for structured Microsoft Learn content:
- Available tools: microsoft_docs_search, microsoft_docs_fetch, microsoft_code_sample_search
- Best for: Official documentation, API specifications, code samples, ARM schemas
- The agent will automatically discover and invoke available MCP tools
""")
    
    if settings.bicep_mcp_url:
        instructions.append("""
## Bicep MCP Server (Phase 2)
Use for Bicep template generation and best practices:
- Azure Verified Modules (AVM) catalog and usage
- Bicep syntax and best practices
- Resource type schemas and properties
- Module composition and parameterization
""")
    
    if settings.terraform_mcp_url:
        instructions.append("""
## Terraform MCP Server - HashiCorp Official (Phase 2)
Use for Terraform infrastructure code generation:
- **Terraform Registry Integration**:
  * Search and retrieve provider documentation (azurerm, etc.)
  * Find and use modules from public Terraform Registry
  * Access policy documentation and best practices
- **HCP Terraform & Terraform Enterprise** (if TFE_TOKEN configured):
  * List organizations, projects, and workspaces
  * Create, update, delete workspaces
  * Manage workspace variables and tags
  * Trigger and monitor runs
  * Access private registry modules
- **Azure Provider Focus**:
  * azurerm provider resource documentation
  * Terraform Azure examples and patterns
  * Module composition for Azure resources
- **Available Tools**: Automatically discovered at runtime
- **Best Practices**: HashiCorp-maintained Terraform patterns
""")
    
    if settings.azure_devops_mcp_url:
        instructions.append("""
## Azure DevOps MCP Server (Phase 2)
Use for CI/CD pipeline generation:
- Azure Pipelines YAML templates
- DevOps best practices
- Infrastructure deployment workflows
- Testing and validation strategies
""")
    
    if settings.github_mcp_url:
        instructions.append("""
## GitHub MCP Server (Phase 2)
Use for GitHub Actions workflows:
- GitHub Actions workflow templates
- Azure deployment actions
- CI/CD best practices
- Secret management and OIDC
""")
    
    instructions.append("""
## Tool Selection Strategy
1. For current best practices - Use Bing Grounding (most up-to-date)
2. For official documentation - Use MS Learn MCP (structured content)
3. For ARM resource schemas - Use MS Learn MCP + Bing Grounding
4. For code samples - Use MS Learn MCP (microsoft_code_sample_search)
5. For Bicep templates - Use Bicep MCP + MS Learn MCP
6. For Terraform code - Use Terraform MCP (HashiCorp official) + MS Learn MCP
   * Terraform MCP for: provider docs, module search, workspace management
   * MS Learn MCP for: Azure-specific Terraform examples and patterns
7. For CI/CD pipelines - Use Azure DevOps MCP or GitHub MCP
8. If one tool fails - Try the alternative tool

IMPORTANT: Never hardcode values. Always use tools to look up:
- ARM resource type schemas and properties
- Private endpoint DNS zones and group IDs
- RBAC role names and IDs  
- Service naming conventions
- Subnet delegation requirements
- API versions for resource types
- Bicep/Terraform module versions
- Terraform provider versions and resource schemas
- Pipeline task versions and parameters
""")
    
    return "\n".join(instructions)

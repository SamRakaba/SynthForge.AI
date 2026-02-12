# MCP Server Integration Guide for SynthForge.AI

**Last Updated:** January 9, 2026  
**Status:** Configuration Required for Phase 2 Servers

---

## Overview

SynthForge.AI integrates with multiple MCP (Model Context Protocol) servers to provide agents with access to specialized tools and documentation. This guide provides information on available MCP servers, their URLs, setup requirements, and usage patterns.

## MCP Server Status

| Server | Status | Priority | Description |
|--------|--------|----------|-------------|
| **MS Learn** | ✅ Active | Critical | Microsoft Learn documentation and ARM schemas |
| **Bicep** | ⚠️ Setup Required | High | Bicep templates, AVM modules, best practices |
| **Terraform** | ⚠️ Setup Required | High | HashiCorp Terraform Registry, provider docs |
| **Azure DevOps** | ⚠️ Setup Required | Medium | CI/CD pipeline templates |
| **GitHub** | ⚠️ Setup Required | Medium | GitHub Actions workflows |

---

## 1. Microsoft Learn MCP Server

### Status: ✅ **ACTIVE**

### Overview
Provides access to Microsoft Learn documentation, code samples, and ARM resource schemas. This is the primary documentation source for all Azure-related lookups.

### Configuration

```bash
# .env
MS_LEARN_MCP_URL=https://learn.microsoft.com/api/mcp
```

### Available Tools

| Tool | Purpose | Example Query |
|------|---------|---------------|
| `microsoft_docs_search` | Semantic search across MS Learn | "Azure Functions VNet integration" |
| `microsoft_docs_fetch` | Fetch full document content | URL to specific doc page |
| `microsoft_code_sample_search` | Search code samples by language | "Azure Storage Python SDK" |

### Usage in Agents

All agents have access to MS Learn MCP by default:

```python
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn"],  # Default
)
```

### Requirements
- ✅ No authentication required
- ✅ Public endpoint
- ✅ No rate limiting for Azure AI Foundry users

### Test Connection
```python
from synthforge.agents.tool_setup import create_agent_toolset
from synthforge.config import get_settings

settings = get_settings()
tool_config = create_agent_toolset(include_mcp=True, mcp_servers=["mslearn"])
# If no errors, connection is successful
```

---

## 2. Bicep MCP Server

### Status: ⚠️ **SETUP REQUIRED**

### Overview
Provides access to Bicep-specific tools, Azure Verified Modules (AVM), resource type schemas, and Bicep best practices. Essential for generating Bicep templates in Phase 2.

### Official Sources

**Option 1: Azure AI Foundry Marketplace (Recommended)**
- Check Azure AI Foundry portal for official Bicep MCP integration
- Pre-configured and hosted by Microsoft
- Automatic updates

**Option 2: GitHub Copilot MCP Registry**
- MCP server available through GitHub Copilot ecosystem
- May require GitHub Copilot subscription

**Option 3: Self-Hosted (Advanced)**
- Clone from: https://github.com/Azure/bicep-mcp-server (if available)
- Host using Docker or Azure Container Apps
- Requires maintenance

### Expected URL Format

```bash
# .env
BICEP_MCP_URL=https://mcp.azure.com/bicep/v1
# OR
BICEP_MCP_URL=https://bicep-mcp.azurewebsites.net/v1
```

### Expected Tools

Based on the Bicep ecosystem, the MCP server should provide:

- `mcp_bicep_experim_get_bicep_best_practices` - Best practices for Bicep
- `mcp_bicep_experim_list_avm_metadata` - List Azure Verified Modules
- `mcp_bicep_experim_get_az_resource_type_schema` - Get resource type schema
- `mcp_bicep_experim_list_az_resource_types_for_provider` - List resource types

### Usage Pattern

```python
# For Bicep code generation
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn", "bicep"],  # Add bicep for Bicep generation
)
```

### Requirements
- Azure subscription (possibly)
- API key or authentication token (TBD)
- Network access to Azure endpoints

### Setup Steps

1. **Research endpoint:**
   ```bash
   # Check Azure AI Foundry portal
   az extension add --name azure-ai-foundry
   az ai-foundry mcp list  # If command exists
   ```

2. **Test connectivity:**
   ```bash
   curl -X GET https://mcp.azure.com/bicep/v1/health
   ```

3. **Add to .env:**
   ```bash
   BICEP_MCP_URL=<discovered-url>
   ```

4. **Verify in code:**
   ```python
   from synthforge.config import get_settings
   settings = get_settings()
   print(settings.bicep_mcp_url)
   ```

### Alternative: Use Bing Grounding Only

If Bicep MCP is unavailable, agents will fall back to:
- Bing Grounding for Bicep documentation
- MS Learn MCP for ARM schemas
- Slightly reduced accuracy for Bicep-specific patterns

---

## 3. Terraform MCP Server (HashiCorp Official)

### Status: ⚠️ **SETUP REQUIRED**

### Overview
Official HashiCorp MCP server providing access to Terraform Registry, provider documentation, module search, and workspace management.

### Official Source

**HashiCorp Official MCP Server:**
- Documentation: https://developer.hashicorp.com/terraform/mcp
- Registry: https://registry.terraform.io/mcp
- GitHub: https://github.com/hashicorp/terraform-mcp-server

### Expected URL Format

```bash
# .env
TERRAFORM_MCP_URL=https://mcp.hashicorp.com/terraform/v1
# OR
TERRAFORM_MCP_URL=https://registry.terraform.io/mcp/v1
```

### Expected Tools

Based on HashiCorp documentation:

- **Registry Tools:**
  - `search_modules` - Search Terraform Registry modules
  - `get_module_details` - Get module documentation
  - `search_providers` - Search provider documentation
  - `get_provider_details` - Get provider resource docs
  - `search_policies` - Search Sentinel policies
  - `get_policy_details` - Get policy documentation

- **Workspace Tools (if HCP Terraform token configured):**
  - `list_organizations` - List HCP Terraform organizations
  - `list_workspaces` - List workspaces
  - `create_workspace` - Create new workspace
  - `update_workspace` - Update workspace configuration
  - `delete_workspace` - Delete workspace
  - `manage_workspace_variables` - Manage variables
  - `trigger_run` - Trigger Terraform run

### Usage Pattern

```python
# For Terraform code generation
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn", "terraform"],  # Add terraform
)
```

### Requirements

**Basic (Registry Access):**
- ✅ No authentication for public registry
- ✅ Public endpoint

**Advanced (HCP Terraform/Enterprise):**
- HCP Terraform account
- API token: `TFE_TOKEN` environment variable
- Organization access

### Setup Steps

1. **Research official endpoint:**
   ```bash
   # Check HashiCorp Developer documentation
   # Visit: https://developer.hashicorp.com/terraform/mcp
   ```

2. **For HCP Terraform integration (optional):**
   ```bash
   # Create API token in HCP Terraform
   # Settings > Tokens > Create API token
   export TFE_TOKEN=<your-token>
   ```

3. **Add to .env:**
   ```bash
   TERRAFORM_MCP_URL=https://mcp.hashicorp.com/terraform/v1
   TFE_TOKEN=<optional-for-workspace-management>
   ```

4. **Test connection:**
   ```bash
   curl -X GET https://mcp.hashicorp.com/terraform/v1/providers/hashicorp/azurerm
   ```

### Alternative: Use MS Learn + Bing

If Terraform MCP is unavailable:
- MS Learn MCP for Azure Provider docs
- Bing Grounding for Terraform examples
- Reduced access to HashiCorp best practices

---

## 4. Azure DevOps MCP Server

### Status: ⚠️ **SETUP REQUIRED**

### Overview
Provides pipeline templates, DevOps best practices, and Azure Pipelines YAML generation tools.

### Expected Sources

**Option 1: Microsoft-Hosted MCP**
- Part of Azure AI Foundry marketplace
- Pre-configured templates

**Option 2: Custom Implementation**
- Azure DevOps REST API wrapper
- Pipeline template library

### Expected URL Format

```bash
# .env
AZURE_DEVOPS_MCP_URL=https://mcp.azure.com/devops/v1
# OR
AZURE_DEVOPS_MCP_URL=https://dev.azure.com/_mcp/v1
```

### Expected Tools

- `search_pipeline_templates` - Find pipeline templates
- `get_template_details` - Get template YAML
- `list_task_versions` - List available task versions
- `get_best_practices` - Get DevOps best practices

### Usage Pattern

```python
# For deployment wrapper generation
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn", "azure-devops"],
)
```

### Requirements
- Azure DevOps organization (possibly)
- Personal Access Token (PAT) with read access
- Network access to dev.azure.com

### Setup Steps

1. **Research Azure AI Foundry:**
   - Check for Azure DevOps MCP in marketplace
   
2. **Alternative - Azure DevOps REST API:**
   ```bash
   # Create PAT in Azure DevOps
   # User Settings > Personal Access Tokens
   # Scope: Code (Read)
   ```

3. **Add to .env:**
   ```bash
   AZURE_DEVOPS_MCP_URL=<discovered-url>
   AZURE_DEVOPS_PAT=<optional-pat>
   ```

### Alternative: Use Bing Grounding

If unavailable:
- Bing search for Azure Pipelines documentation
- MS Learn MCP for pipeline examples
- Manual template selection

---

## 5. GitHub MCP Server

### Status: ⚠️ **SETUP REQUIRED**

### Overview
Provides GitHub Actions workflow templates, marketplace actions, and CI/CD best practices.

### Official Source

**GitHub Copilot MCP:**
- Part of GitHub Copilot subscription
- Access to GitHub marketplace
- Workflow templates

### Expected URL Format

```bash
# .env
GITHUB_MCP_URL=https://mcp.github.com/actions/v1
# OR
GITHUB_MCP_URL=https://api.github.com/mcp/v1
```

### Expected Tools

- `search_actions` - Search GitHub Actions marketplace
- `get_action_details` - Get action documentation
- `search_workflows` - Search workflow templates
- `get_workflow_template` - Get template YAML

### Usage Pattern

```python
# For GitHub Actions generation
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn", "github"],
)
```

### Requirements
- GitHub account
- GitHub Copilot subscription (possibly)
- GitHub PAT with repo/workflow access

### Setup Steps

1. **Check GitHub Copilot integration:**
   - Visit GitHub Copilot settings
   - Look for MCP server configuration

2. **Create GitHub PAT:**
   ```bash
   # GitHub Settings > Developer settings > PAT
   # Scope: repo, workflow
   ```

3. **Add to .env:**
   ```bash
   GITHUB_MCP_URL=<discovered-url>
   GITHUB_TOKEN=<your-pat>
   ```

### Alternative: Use Bing Grounding

If unavailable:
- Bing search for GitHub Actions docs
- MS Learn MCP for GitHub examples
- Manual workflow creation

---

## Testing MCP Server Connections

### Test Script

Create `test_mcp_servers.py`:

```python
"""Test MCP server connectivity."""
import asyncio
from synthforge.config import get_settings
from synthforge.agents.tool_setup import create_agent_toolset

async def test_mcp_servers():
    settings = get_settings()
    
    servers_to_test = {
        "mslearn": settings.ms_learn_mcp_url,
        "bicep": settings.bicep_mcp_url,
        "terraform": settings.terraform_mcp_url,
        "azure-devops": settings.azure_devops_mcp_url,
        "github": settings.github_mcp_url,
    }
    
    results = {}
    
    for server_name, server_url in servers_to_test.items():
        if not server_url:
            results[server_name] = "❌ Not configured"
            continue
        
        try:
            tool_config = create_agent_toolset(
                include_mcp=True,
                mcp_servers=[server_name]
            )
            
            if tool_config.has_mcp and server_name in tool_config.mcp_servers:
                results[server_name] = f"✅ Connected ({server_url})"
            else:
                results[server_name] = f"⚠️  Configured but not active ({server_url})"
                
        except Exception as e:
            results[server_name] = f"❌ Error: {str(e)}"
    
    print("\\nMCP Server Connection Test Results:")
    print("=" * 80)
    for server, status in results.items():
        print(f"{server:15} {status}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_mcp_servers())
```

Run the test:
```bash
cd c:\\Users\\srakaba\\ai-agents\\SynthForge.AI
python test_mcp_servers.py
```

---

## Configuration Priority

### Phase 1 (Current) - Working ✅
- MS Learn MCP: **Required**
- Bing Grounding: **Required**

### Phase 2 (IaC Generation) - Setup Required ⚠️
- Bicep MCP: **High Priority** for Bicep generation
- Terraform MCP: **High Priority** for Terraform generation
- MS Learn MCP: **Still required** for Azure docs

### Phase 3 (DevOps) - Optional 📋
- Azure DevOps MCP: Medium priority
- GitHub MCP: Medium priority
- Can use Bing Grounding as fallback

---

## Fallback Behavior

When MCP servers are unavailable, agents automatically fall back to:

1. **Bing Grounding** - Search web for documentation
2. **MS Learn MCP** - Always available for Azure docs
3. **Built-in Knowledge** - Model's training data

**Example:**
```python
# Agent will try in order:
# 1. Bicep MCP (if configured)
# 2. MS Learn MCP (for ARM templates)
# 3. Bing Grounding (for Bicep docs)
```

---

## Recommended Action Plan

### Immediate (This Week)
1. ✅ Verify MS Learn MCP is working
2. ✅ Verify Bing Grounding connection
3. Test Phase 1 agents with sample diagrams

### Short Term (Next 2 Weeks)
1. Research official Bicep MCP endpoint
2. Research HashiCorp Terraform MCP endpoint
3. Configure and test both servers
4. Update `.env.example` with discovered URLs

### Medium Term (Next Month)
1. Research Azure DevOps MCP options
2. Research GitHub MCP integration
3. Document authentication requirements
4. Create automated connection tests

---

## Support & Resources

### Microsoft Resources
- Azure AI Foundry: https://ai.azure.com
- MS Learn MCP: https://learn.microsoft.com/api/mcp
- Azure AI Foundry Marketplace: Check portal for MCP integrations

### HashiCorp Resources
- Terraform Developer: https://developer.hashicorp.com/terraform
- Terraform Registry: https://registry.terraform.io
- HCP Terraform: https://app.terraform.io

### GitHub Resources
- GitHub Copilot: https://github.com/features/copilot
- GitHub Marketplace: https://github.com/marketplace
- GitHub API: https://docs.github.com/api

### Community
- Azure Tech Community: https://techcommunity.microsoft.com/azure
- Terraform Community: https://discuss.hashicorp.com
- GitHub Community: https://github.community

---

## Questions to Resolve

1. **Bicep MCP:**
   - Is there an official Microsoft-hosted Bicep MCP server?
   - What authentication is required?
   - Is it part of Azure AI Foundry marketplace?

2. **Terraform MCP:**
   - What is the official HashiCorp MCP endpoint?
   - Is authentication required for public registry access?
   - How to enable HCP Terraform integration?

3. **Azure DevOps MCP:**
   - Is there a Microsoft-hosted MCP server for Azure DevOps?
   - Can we use Azure DevOps REST API as MCP wrapper?

4. **GitHub MCP:**
   - Is MCP integration part of GitHub Copilot subscription?
   - What's the endpoint for GitHub Actions marketplace?

**Next Steps:** Contact Microsoft Azure AI Foundry support and HashiCorp support for official endpoints.

---

**Document Status:** Living document - Update as MCP servers are discovered and configured.

# SynthForge.AI Tool Configuration Guide

## Tool Stack Overview

SynthForge.AI uses a **dual-tool approach** for comprehensive Azure architecture analysis and IaC generation:

### 🔵 PRIMARY: Bing Grounding (Required - Always Use First)
- **Purpose**: Fast Azure documentation search
- **Used by**: ALL agents (Phase 1 & Phase 2)
- **Speed**: Instant lookups
- **Provides**: Quick service info, naming conventions, basic best practices
- **Configuration**: `BING_CONNECTION_ID` in `.env` (REQUIRED)

### 🟢 REQUIRED: Microsoft Learn MCP Server (Deep Analysis)
- **Purpose**: Deep documentation and comprehensive analysis
- **URL**: `https://learn.microsoft.com/api/mcp`
- **Repository**: https://github.com/microsoftdocs/mcp
- **Authentication**: None (public server)
- **Configuration**: `MS_LEARN_MCP_URL=https://learn.microsoft.com/api/mcp` (REQUIRED)

**Available Tools**:
- `microsoft_docs_search` - Semantic search across Microsoft Learn
- `microsoft_docs_fetch` - Fetch complete doc page content
- `microsoft_code_sample_search` - Search code samples with language filter

**Phase 1 Usage** (Description, Vision, OCR):
- Security best practices and compliance
- Architecture recommendations
- Well-Architected Framework guidance
- Complete naming rules and constraints
- Service configuration best practices

**Phase 2 Usage** (IaC Generation):
- ARM resource type schemas (REQUIRED)
- API version lookups (REQUIRED)
- Azure Verified Module patterns
- Complete resource configuration schemas
- Bicep/ARM template examples

### 🟡 OPTIONAL: GitHub MCP Server
- **Purpose**: Azure Verified Modules and architecture samples
- **Configuration**: `GITHUB_MCP_URL` in `.env`
- **Repositories**:
  - `Azure/bicep-registry-modules`
  - `Azure/azure-quickstart-templates`
  - `Azure/Well-Architected-Framework`

**When to Use**:
- Phase 2 IaC generation
- Finding Bicep module examples
- Looking up quickstart templates

### 🟠 OPTIONAL: HashiCorp Terraform MCP Server
- **Purpose**: Terraform provider documentation
- **Configuration**: `TERRAFORM_MCP_URL` in `.env`
- **Provides**: azurerm provider docs, Terraform Registry modules

**When to Use**:
- Generating Terraform instead of Bicep
- Looking up Terraform azurerm resources

---

## Configuration Steps

### 1. Required: Bing Grounding

```bash
# In .env file
BING_CONNECTION_ID=/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{account}/projects/{project}/connections/{connection-name}
```

### 2. Required: Microsoft Learn MCP

```bash
# In .env file
MS_LEARN_MCP_URL=https://learn.microsoft.com/api/mcp
```

All agents are configured to use both tools:

```python
self._tool_config = create_agent_toolset(
    include_bing=True,              # PRIMARY - fast lookups
    include_mcp=True,                # REQUIRED - deep analysis
    mcp_servers=["mslearn"],         # Microsoft Learn MCP
)
```

### 3. Optional: Additional MCP Servers

```bash
# In .env file
GITHUB_MCP_URL=<github-mcp-endpoint>  # If using GitHub MCP
TERRAFORM_MCP_URL=<terraform-mcp-endpoint>  # If generating Terraform
```

---

## Agent Tool Usage

### Phase 1 Agents (Description, Vision, OCR)

**Configuration**: Bing Grounding + Microsoft Learn MCP

```python
# All Phase 1 agents use:
self._tool_config = create_agent_toolset(
    include_bing=True,              # PRIMARY - fast lookups
    include_mcp=True,                # REQUIRED - recommendations
    mcp_servers=["mslearn"],         # Microsoft Learn MCP
)
```

**Tool Usage Strategy**:
1. **Bing Grounding (first)**: Quick service lookups, basic info
2. **Microsoft Learn MCP (deep)**: 
   - Security best practices
   - Architecture recommendations
   - Well-Architected Framework patterns
   - Complete naming rules
   - Service configuration guidance

**Why Both Tools?**:
- **Bing**: Fast, great for "What is Azure X?"
- **MS Learn MCP**: Deep, great for "How should I configure X?" and "What are the security recommendations?"

### Phase 2 Agents (IaC Generation)

**Configuration**: Bing Grounding + Microsoft Learn MCP + Optional GitHub/Terraform

```python
# Phase 2 IaC agents use:
self._tool_config = create_agent_toolset(
    include_bing=True,              # PRIMARY for quick checks
    include_mcp=True,                # REQUIRED for ARM schemas
    mcp_servers=["mslearn"],         # Microsoft Learn MCP (required)
    # mcp_servers=["mslearn", "github", "terraform"],  # Optional additional
)
```

**Tool Usage Strategy**:
1. **Bing Grounding**: Quick ARM type lookups, service references
2. **Microsoft Learn MCP (REQUIRED)**:
   - ARM resource type schemas
   - API versions
   - Resource property definitions
   - Azure Verified Module patterns
3. **GitHub MCP (optional)**: Bicep module examples
4. **Terraform MCP (optional)**: Terraform azurerm provider docs

---

## Tool Selection Logic

### When to Use Bing Grounding
✅ Quick Azure service lookups  
✅ CAF naming conventions  
✅ Security best practices  
✅ Architecture patterns  
✅ "What is Azure X?" questions  

### When to Use Microsoft Learn MCP
✅ ARM resource type schemas  
✅ Specific API versions  
✅ Complete documentation pages  
✅ Code samples with language filters  
✅ Detailed property definitions  

### When to Use GitHub MCP
✅ Finding Bicep module examples  
✅ Azure Verified Modules  
✅ Quickstart templates  
✅ Well-Architected patterns  

### When to Use Terraform MCP
✅ Generating Terraform (not Bicep)  
✅ azurerm provider documentation  
✅ Terraform module registry  

---

## Validation

Run the validation script to check configuration:

```bash
python validate_mcp_config.py
```

**Expected Output** (Minimal Configuration):
```
✅ CONFIGURATION VALID - Ready to run

Tool Configuration:
  • Bing Grounding: PRIMARY (required) ✓
  • MCP Servers: 0 configured (using Bing Grounding only)
```

**Expected Output** (With Microsoft Learn MCP):
```
✅ CONFIGURATION VALID - Ready to run

Tool Configuration:
  • Bing Grounding: PRIMARY (required) ✓
  • MCP Servers: 1 configured (optional enhancement)
    - Microsoft Learn MCP ✓ (recommended)
```

---

## Migration from Previous Configuration

### What Changed

**REMOVED**: Microsoft Foundry MCP (`https://mcp.ai.azure.com`)
- **Why**: Foundry MCP is for AI model lifecycle management (deployments, evaluations)
- **Not needed for**: Azure architecture documentation or IaC generation

**ADDED**: Microsoft Learn MCP (`https://learn.microsoft.com/api/mcp`)
- **Why**: Provides actual Azure documentation and code samples
- **Needed for**: ARM schemas, API versions, code examples

### Update Your .env

```bash
# OLD (WRONG)
MS_LEARN_MCP_URL=https://mcp.ai.azure.com  # ❌ This is Foundry MCP

# NEW (CORRECT)
MS_LEARN_MCP_URL=https://learn.microsoft.com/api/mcp  # ✅ This is Learn MCP
```

---

## References

- **Microsoft Learn MCP**: https://github.com/microsoftdocs/mcp
- **Azure AI Agents SDK**: https://learn.microsoft.com/python/api/azure-ai-agents/
- **Bing Grounding**: https://learn.microsoft.com/azure/ai-foundry/bing-grounding
- **Azure Architecture Icons**: https://learn.microsoft.com/azure/architecture/icons/

---

## Summary

| Tool | Status | Purpose | Configuration |
|------|--------|---------|---------------|
| **Bing Grounding** | ✅ REQUIRED | Fast Azure doc search | `BING_CONNECTION_ID` |
| **Microsoft Learn MCP** | 🟢 RECOMMENDED | Deep docs & schemas | `MS_LEARN_MCP_URL` |
| **GitHub MCP** | 🟡 OPTIONAL | Bicep modules | `GITHUB_MCP_URL` |
| **Terraform MCP** | 🟠 OPTIONAL | Terraform docs | `TERRAFORM_MCP_URL` |

**Minimal Setup** (Phase 1 only): Bing Grounding  
**Recommended Setup** (All phases): Bing Grounding + Microsoft Learn MCP  
**Full Setup** (Advanced IaC): All four tools configured

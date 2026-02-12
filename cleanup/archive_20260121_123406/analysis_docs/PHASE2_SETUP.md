# Phase 2: IaC Generation - Setup Complete ✅

*Date: January 2, 2026*

## Summary

Phase 2 infrastructure is now configured and ready for IaC generation development. The foundation includes multiple MCP servers for Bicep, Terraform, and DevOps best practices, along with CLI argument handling for phase selection.

---

## What's Been Added

### 1. MCP Server Configuration

#### New Environment Variables (.env)
```bash
# Phase 1 (existing)
MS_LEARN_MCP_URL=https://learn.microsoft.com/api/mcp

# Phase 2 (new)
BICEP_MCP_URL=          # Microsoft Bicep best practices & AVM
TERRAFORM_MCP_URL=      # HashiCorp Terraform best practices  
AZURE_DEVOPS_MCP_URL=   # Azure Pipelines templates
GITHUB_MCP_URL=         # GitHub Actions workflows
```

#### Configuration Fields (config.py)
- `bicep_mcp_url` - Bicep MCP server for templates and AVM
- `terraform_mcp_url` - Terraform MCP server for azurerm provider
- `azure_devops_mcp_url` - Azure DevOps pipelines and best practices
- `github_mcp_url` - GitHub Actions CI/CD workflows

### 2. Enhanced Tool Setup

**Updated:** `synthforge/agents/tool_setup.py`

#### Multi-MCP Server Support
```python
create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn", "bicep", "terraform"]  # Flexible selection
)
```

**ToolConfiguration** now includes:
- `mcp_servers: List[str]` - List of active MCP server labels
- Support for 5 MCP servers: mslearn, bicep, terraform, azure-devops, github

#### Tool Instructions
Added guidance for Phase 2 MCP servers:
- Bicep MCP: AVM, templates, best practices
- Terraform MCP: Provider docs, module structure
- Azure DevOps MCP: Pipeline templates, DevOps patterns
- GitHub MCP: Actions workflows, OIDC auth

### 3. Phase Selection CLI

**Updated:** `main.py`

```bash
# Run Phase 1 only (default)
python main.py diagram.png

# Run Phase 2 only (requires Phase 1 outputs)
python main.py diagram.png --phase 2

# Run both phases sequentially
python main.py diagram.png --phase both
python main.py diagram.png --phase all

# Custom output directory
python main.py diagram.png --output ./analysis --phase all
```

**New Argument:**
- `--phase {1,2,both,all}` - Select which phase(s) to execute

**Restructured main.py:**
- `main()` - Entry point wrapper (synchronous)
- `async_main()` - Main async logic with argument parsing
- `run_phase1_analysis(args)` - Execute Phase 1 workflow
- `export_phase1_outputs(result, output_dir, format)` - Export JSON files
- Phase 2 calls `run_phase2_workflow()` when `--phase 2` or `--phase both`

### 4. Phase 2 Workflow Module

**New File:** `synthforge/workflow_phase2.py`

```python
class Phase2Workflow:
    """Phase 2: IaC Generation Workflow"""
    
    def __init__(
        self,
        output_dir: Path,
        iac_format: str = "bicep",  # "bicep", "terraform", or "both"
        pipeline_platform: str = "azure-devops",  # "azure-devops" or "github"
    )
```

**Features:**
- Loads Phase 1 outputs (architecture_analysis.json, etc.)
- Creates subdirectories: bicep/, terraform/, pipelines/, docs/
- AgentsClient initialization ready for Phase 2 agents
- Placeholder for 4-stage workflow:
  - Stage 0: Load Phase 1 Analysis
  - Stage 1: IaC Template Generation
  - Stage 2: Pipeline Generation
  - Stage 3: Validation & Testing
  - Stage 4: Documentation Generation

**Status:** Infrastructure complete, implementation pending

---

## File Structure

```
synthforge/
├── config.py                    ✅ Updated (4 new MCP server URLs)
├── agents/
│   └── tool_setup.py            ✅ Updated (multi-MCP support)
└── workflow_phase2.py           ✅ NEW (Phase 2 orchestrator)

main.py                          ✅ Updated (phase selection + async restructure)
.env                             ✅ Updated (Phase 2 MCP server URLs)
```

---

## Microsoft MCP Servers

Reference: https://github.com/microsoft/mcp

### Available Servers (as of Jan 2026)

| MCP Server | Purpose | URL Pattern |
|------------|---------|-------------|
| **MS Learn** | Documentation, code samples | `https://learn.microsoft.com/api/mcp` |
| **Bicep** | Bicep templates, AVM | `https://github.com/microsoft/mcp/tree/main/servers/bicep` |
| **Azure DevOps** | Pipeline templates, DevOps | `https://github.com/microsoft/mcp/tree/main/servers/azure-devops` |
| **GitHub** | GitHub Actions, workflows | `https://github.com/microsoft/mcp/tree/main/servers/github` |

### HashiCorp Terraform MCP

**Status:** Check https://registry.terraform.io/ or HashiCorp docs for official MCP server

**Note:** Terraform MCP might be community-hosted or require local server setup

---

## Output Directory Structure

When Phase 2 runs, output directory will be organized:

```
output/
├── architecture_analysis.json    # Phase 1: Full analysis
├── resource_summary.json         # Phase 1: Resource list
├── rbac_assignments.json         # Phase 1: RBAC recommendations
├── private_endpoints.json        # Phase 1: PE/VNet configs
├── network_flows.json            # Phase 1: Network topology
├── bicep/                        # Phase 2: Bicep templates
│   ├── main.bicep
│   ├── modules/
│   └── ...
├── terraform/                    # Phase 2: Terraform code
│   ├── main.tf
│   ├── variables.tf
│   └── ...
├── pipelines/                    # Phase 2: CI/CD pipelines
│   ├── azure-pipelines.yml
│   ├── github-actions.yml
│   └── ...
└── docs/                         # Phase 2: Generated docs
    ├── architecture.md
    ├── deployment.md
    └── ...
```

---

## Next Steps

### Phase 2 Development Roadmap

1. **Setup MCP Server URLs** (User Action Required)
   - [ ] Configure BICEP_MCP_URL in .env
   - [ ] Configure TERRAFORM_MCP_URL in .env
   - [ ] Configure AZURE_DEVOPS_MCP_URL in .env (optional)
   - [ ] Configure GITHUB_MCP_URL in .env (optional)

2. **Stage 1: IaC Template Generation Agent**
   - [ ] Create `BicepGenerationAgent` in `synthforge/agents/`
   - [ ] Create `TerraformGenerationAgent` (optional)
   - [ ] Map Phase 1 JSON outputs to IaC resource definitions
   - [ ] Generate modular templates (main + modules)
   - [ ] Use Bicep MCP for AVM (Azure Verified Modules)
   - [ ] Use Terraform MCP for provider documentation

3. **Stage 2: Pipeline Generation Agent**
   - [ ] Create `PipelineGenerationAgent`
   - [ ] Generate Azure Pipelines YAML (azure-pipelines.yml)
   - [ ] Generate GitHub Actions workflows (.github/workflows/)
   - [ ] Include deployment stages, validation, testing
   - [ ] Use Azure DevOps MCP / GitHub MCP for templates

4. **Stage 3: Validation & Testing**
   - [ ] Bicep lint/validate (via bicep CLI or MCP)
   - [ ] Terraform validate/plan (via terraform CLI)
   - [ ] What-if deployment analysis
   - [ ] ARM template test toolkit integration

5. **Stage 4: Documentation Generation**
   - [ ] Generate architecture.md from Phase 1 analysis
   - [ ] Generate deployment.md with step-by-step instructions
   - [ ] Generate README.md for IaC repository
   - [ ] Include network diagrams, RBAC matrix, security configs

---

## Usage Examples

### Phase 1 Only (Current Behavior)
```bash
python main.py input/Architecture_DataFlow_v1.png
# Outputs: architecture_analysis.json, resource_summary.json, etc.
```

### Phase 2 Only (Requires Phase 1 outputs)
```bash
# First run Phase 1 if not already done
python main.py input/Architecture_DataFlow_v1.png --phase 1

# Then run Phase 2
python main.py input/Architecture_DataFlow_v1.png --phase 2
# Outputs: bicep/, terraform/, pipelines/, docs/
```

### Both Phases Together
```bash
python main.py input/Architecture_DataFlow_v1.png --phase both --output ./deployment
# Runs Phase 1 → Exports JSON → Runs Phase 2 → Generates IaC
```

### Phase 2 Current State
```bash
python main.py input/Architecture_DataFlow_v1.png --phase 2 --output ./test-output
```
**Output:**
```
PHASE 2: Infrastructure as Code Generation
===========================================================

Stage 0: Loading Phase 1 Analysis...
✓ Loaded: architecture_analysis.json
✓ Loaded: resource_summary.json
✓ Loaded: network_flows.json
✓ Loaded: rbac_assignments.json
✓ Loaded: private_endpoints.json

Loaded 5 Phase 1 output file(s)

===========================================================
Phase 2 implementation coming soon!
===========================================================

Planned Stages:
  Stage 1: IaC Template Generation (Bicep/Terraform)
  Stage 2: Pipeline Generation (Azure DevOps/GitHub)
  Stage 3: Validation & Testing
  Stage 4: Documentation Generation

Phase 1 outputs loaded and ready for Phase 2 development.

===========================================================
Phase 2 infrastructure ready, implementation pending
===========================================================
```

---

## Configuration Reference

### Required for Phase 1
- `PROJECT_ENDPOINT` - Azure AI Foundry endpoint
- `MODEL_DEPLOYMENT_NAME` - GPT-4o deployment
- `BING_CONNECTION_ID` - Bing Grounding connection
- `MS_LEARN_MCP_URL` - MS Learn MCP server

### Optional for Phase 2
- `BICEP_MCP_URL` - Bicep template generation
- `TERRAFORM_MCP_URL` - Terraform code generation
- `AZURE_DEVOPS_MCP_URL` - Azure Pipelines
- `GITHUB_MCP_URL` - GitHub Actions

### Default Behavior
- **Phase:** 1 (Design Extraction only)
- **Output:** ./output
- **Format:** summary
- **Log Level:** WARNING (quiet mode)

---

## Architecture Pattern

### Phase 1 → Phase 2 Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Design Extraction (Implemented ✅)             │
│  - Vision Agent (icon detection)                        │
│  - OCR Agent (text extraction)                          │
│  - Filter Agent (classification)                        │
│  - Network Flow Agent (topology)                        │
│  - Security Agent (RBAC/PE/MI)                          │
└─────────────────────────────────────────────────────────┘
                        ↓
               ┌─────────────────┐
               │  JSON Outputs   │
               │  (IaC-ready)    │
               └─────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 2: IaC Generation (Infrastructure Ready 📋)       │
│  Stage 1: IaC Template Generation                       │
│     ├─ BicepGenerationAgent (Bicep MCP + MS Learn)     │
│     └─ TerraformGenerationAgent (Terraform MCP)        │
│  Stage 2: Pipeline Generation                           │
│     └─ PipelineGenerationAgent (DevOps/GitHub MCP)     │
│  Stage 3: Validation & Testing                          │
│     └─ ValidationAgent (bicep/terraform CLI)           │
│  Stage 4: Documentation                                 │
│     └─ DocGenerationAgent (architecture.md, etc.)      │
└─────────────────────────────────────────────────────────┘
                        ↓
               ┌─────────────────┐
               │  Deployable IaC │
               │  + CI/CD        │
               └─────────────────┘
```

---

## Tool Selection Strategy (Phase 2)

Agents will use the following tool selection logic:

### Bicep Generation
1. **Bicep MCP** - AVM modules, best practices, syntax
2. **MS Learn MCP** - ARM resource schemas, API versions
3. **Bing Grounding** - Latest Bicep features, examples

### Terraform Generation
1. **Terraform MCP** - azurerm provider, module patterns
2. **MS Learn MCP** - Azure resource documentation
3. **Bing Grounding** - Terraform Azure examples

### Pipeline Generation
1. **Azure DevOps MCP** - Azure Pipelines templates
2. **GitHub MCP** - GitHub Actions workflows
3. **MS Learn MCP** - Azure deployment docs
4. **Bing Grounding** - CI/CD best practices

---

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Configuration** | ✅ Complete | 4 new MCP server URLs added |
| **Tool Setup** | ✅ Complete | Multi-MCP server support |
| **CLI Arguments** | ✅ Complete | --phase flag implemented |
| **main.py** | ✅ Complete | Async restructure, phase routing |
| **Phase2Workflow** | ✅ Infrastructure | Loads Phase 1, creates dirs |
| **Bicep Agent** | 📋 Planned | Not started |
| **Terraform Agent** | 📋 Planned | Not started |
| **Pipeline Agent** | 📋 Planned | Not started |
| **Validation** | 📋 Planned | Not started |
| **Documentation** | 📋 Planned | Not started |

---

## Testing Phase 2 Infrastructure

```bash
# Test Phase 2 loads Phase 1 outputs correctly
python main.py input/Architecture_DataFlow_v1.png --phase 2

# Should output:
# - Loads 5 Phase 1 JSON files
# - Creates bicep/, terraform/, pipelines/, docs/ subdirectories
# - Shows "implementation pending" message
```

---

## Developer Notes

### Why Multi-MCP Architecture?

1. **Specialization** - Each MCP server provides domain-specific knowledge
2. **Best Practices** - Bicep/Terraform MCPs ensure code quality
3. **Up-to-date** - MCP servers maintained by Microsoft/HashiCorp
4. **Modularity** - Agents can mix/match tools as needed
5. **Extensibility** - Easy to add more MCP servers later

### Agent Design for Phase 2

Each IaC generation agent should:
- Read Phase 1 JSON outputs (resource_summary.json, network_flows.json, etc.)
- Use appropriate MCP server(s) for code generation
- Generate modular, maintainable IaC code
- Follow Azure Well-Architected Framework principles
- Include proper resource naming (CAF naming conventions)
- Implement security best practices (RBAC, PE, MI)

### Example Agent Workflow

```python
# Bicep Generation Agent (future)
async def generate_bicep_template(resources: List[Resource]):
    # 1. Use Bicep MCP to get AVM module recommendations
    avm_modules = await bicep_mcp.get_avm_modules(resource_types)
    
    # 2. Use MS Learn MCP for resource schemas
    schemas = await ms_learn_mcp.get_resource_schemas(resource_types)
    
    # 3. Generate main.bicep with modules
    template = build_bicep_template(resources, avm_modules, schemas)
    
    # 4. Validate with Bicep MCP
    validation = await bicep_mcp.validate(template)
    
    return template
```

---

## Ready for Development ✅

Phase 2 infrastructure is complete and ready for IaC generation agent development. All prerequisites are in place:

- ✅ MCP server configuration
- ✅ Tool setup with multi-MCP support
- ✅ CLI phase selection
- ✅ Phase 2 workflow orchestrator
- ✅ Output directory structure
- ✅ Phase 1 → Phase 2 data flow

**Next:** Implement BicepGenerationAgent as the first Phase 2 agent!

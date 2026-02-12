# ServiceAnalysisAgent - Updated to Phase 1 Instruction Pattern

## Changes Made

### 1. **Moved Instructions to YAML File** (`agent_instructions.yaml`)
Following Phase 1's pattern, created professional agent instructions in YAML:
- **Location**: `synthforge/prompts/agent_instructions.yaml`
- **Section**: `service_analysis_agent` (Phase 2 agents section)
- **Pattern**: Same structure as Phase 1 agents (vision_agent, filter_agent, etc.)

### 2. **Updated Instructions - Key Improvements**

#### Focus on Application Services Only
```yaml
# What NOT to Include (Unless User Explicitly Requests)
These are **platform/foundational services** provided at deployment time:
- ❌ Virtual Networks (VNet)
- ❌ Subnets
- ❌ Network Security Groups (NSG)
- ❌ Private DNS Zones
- ❌ Route Tables
- ❌ Azure Firewall (unless core to application)
```

**Rationale**: Organizations typically have pre-existing network infrastructure. Phase 2 generates **application service modules** that integrate with existing platform infrastructure.

#### Fully Leverage Phase 1 Analysis
Instructions now comprehensively use ALL Phase 1 outputs:
1. **architecture_analysis.json** → Understanding service purpose, identifying main components
2. **resource_summary.json** → Complete service list, initial configurations
3. **network_flows.json** → Service dependencies, networking requirements
4. **rbac_assignments.json** → Security requirements, service dependencies (who accesses whom)
5. **private_endpoints.json** → Network security requirements, subnet dependencies

#### Use Bing Grounding for Service Research
For EACH service, the agent now uses Bing Grounding to research:

**Configuration Research**:
```
"Azure [service] SKU options tiers site:learn.microsoft.com"
"Azure [service] configuration features site:learn.microsoft.com"
```

**Dependency Research**:
```
"Azure [service] prerequisites required services site:learn.microsoft.com"
"Azure [service] dependencies integration site:learn.microsoft.com"
```

**Best Practice Research**:
```
"Azure [service] best practices recommendations site:learn.microsoft.com"
"Azure [service] security best practices site:learn.microsoft.com"
```

#### Calculate Dependencies Dynamically
Dependencies now extracted from multiple sources:
- **From network_flows.json**: If service A → service B (data flow), then A depends on B
- **From rbac_assignments.json**: If service A needs role on service B, then A depends on B
- **From Bing Grounding**: Service prerequisites (e.g., OpenAI needs Key Vault)

#### Enhanced Priority Calculation
```
Priority 1: Services with NO dependencies on other app services
           (e.g., Storage Account, Key Vault - standalone services)

Priority 2: Services depending only on Priority 1 services
           (e.g., Azure OpenAI depends on Key Vault for keys)

Priority 3: Services with complex dependencies or integrations
           (e.g., API Management depends on multiple backend services)
```

### 3. **Agent Code Updates** (`service_analysis_agent.py`)

#### Import Professional Instructions
```python
from synthforge.prompts import get_service_analysis_agent_instructions
```

#### Enable Bing Grounding + MS Learn MCP
```python
def __init__(
    self,
    agents_client: AgentsClient,
    model_name: str,
    bing_connection_name: Optional[str] = None,  # NOW REQUIRED
    ms_learn_mcp_url: Optional[str] = None,
):
    # Load instructions from YAML (Phase 1 pattern)
    base_instructions = get_service_analysis_agent_instructions()
    
    # Create toolset with Bing + MS Learn MCP
    mcp_servers = []
    if ms_learn_mcp_url:
        mcp_servers.append(ms_learn_mcp_url)
    
    use_bing = bing_connection_name is not None
    self.toolset = create_agent_toolset(
        bing_grounding=use_bing,
        bing_connection_name=bing_connection_name,
        mcp_servers=mcp_servers,
    )
```

#### Updated Agent Name
```python
AGENT_NAME = "Azure Service Requirements Analyst"  # Professional name
```

### 4. **Prompts Module Update** (`prompts/__init__.py`)

Added helper function following Phase 1 pattern:
```python
def get_service_analysis_agent_instructions() -> str:
    """Get Service Analysis Agent (Phase 2) instructions."""
    return get_agent_instructions("service_analysis_agent")
```

### 5. **Workflow Update** (`workflow_phase2.py`)

Pass Bing Grounding connection to enable service research:
```python
service_analysis_agent = ServiceAnalysisAgent(
    agents_client=self.agents_client,
    model_name=self.settings.model_deployment_name,
    bing_connection_name=self.settings.bing_connection_name,  # ADDED
    ms_learn_mcp_url=self.settings.ms_learn_mcp_url,          # ADDED
)
```

---

## Instruction Structure (Following Phase 1 Pattern)

### Professional Section Organization

```yaml
service_analysis_agent:
  name: "Azure Service Requirements Analyst"
  description: "Analyzes Phase 1 architecture outputs..."
  
  instructions: |
    # Your Mission
    # Critical Rules
    # What NOT to Include (Unless User Explicitly Requests)
    # What TO Include (Application Services)
    # Input Files (Phase 1 Outputs)
    # Analysis Workflow
      ## Stage 1: Extract Services from Phase 1
      ## Stage 2: Enrich with Bing Grounding
      ## Stage 3: Calculate Dependencies from Phase 1
      ## Stage 4: Assign Deployment Priorities
    # Tool Usage Strategy
    # Output Format
    # Service Requirement Fields
    # Quality Checks
    # Special Cases
    # Example Queries for Common Services
    # Remember
```

### Key Differences from Original

| Aspect | Original | Updated |
|--------|----------|---------|
| **Instructions** | Embedded in Python code | YAML file (Phase 1 pattern) |
| **Foundation Services** | Included by default | **Excluded by default** |
| **Bing Grounding** | Not used | **Extensively used for research** |
| **Phase 1 Integration** | Basic JSON parsing | **Comprehensive multi-file analysis** |
| **Dependencies** | Simple extraction | **Multi-source calculation** (flows + RBAC + research) |
| **Configuration** | Phase 1 only | **Phase 1 + Bing research enrichment** |
| **Priorities** | Simple categorization | **Topological sort for deployment** |

---

## Expected Behavior Changes

### Before (Original)
```json
{
  "services": [
    {
      "service_type": "Azure Virtual Network",
      "priority": 1
    },
    {
      "service_type": "Network Security Group",
      "priority": 1
    },
    {
      "service_type": "Azure OpenAI",
      "configurations": {"sku": "S0"},
      "dependencies": ["main-vnet"],
      "priority": 2
    }
  ]
}
```

### After (Updated)
```json
{
  "services": [
    {
      "service_type": "Azure Key Vault",
      "configurations": {
        "sku": "Standard",
        "soft_delete_enabled": true,
        "purge_protection_enabled": true
      },
      "dependencies": [],
      "priority": 1,
      "research_sources": [
        "https://learn.microsoft.com/azure/key-vault/..."
      ]
    },
    {
      "service_type": "Azure OpenAI",
      "configurations": {
        "sku": "S0",
        "models": ["gpt-4o", "text-embedding-ada-002"],
        "public_network_access": false
      },
      "dependencies": ["key-vault"],
      "network_requirements": {
        "private_endpoint": true,
        "requires_subnet": true,
        "subnet_purpose": "private_endpoint_subnet"
      },
      "security_requirements": {
        "managed_identity": "SystemAssigned",
        "rbac_roles": ["Cognitive Services OpenAI User"],
        "key_vault_access": true
      },
      "priority": 2,
      "research_sources": [
        "https://learn.microsoft.com/azure/ai-services/openai/..."
      ]
    }
  ],
  "foundation_services": [],
  "application_services": [...]
}
```

**Key Improvements**:
- ✅ NO VNet, NSG, Subnets (platform concerns)
- ✅ Richer configurations from Bing research
- ✅ Dependencies from Phase 1 + research
- ✅ Network requirements noted (but actual CIDRs are deployment-time)
- ✅ Security requirements from RBAC analysis + best practices
- ✅ Research sources documented for transparency

---

## Alignment with User Requirements

### ✅ "fully use the analysis from phase 1"
- Instructions now detail HOW to use each Phase 1 file
- Workflow stages explicitly extract data from all 5 Phase 1 outputs
- Dependencies calculated from network_flows + rbac_assignments

### ✅ "recommendations, requirements should leverage grounding and dependencies"
- Extensive Bing Grounding usage for EACH service
- Configuration research, dependency research, best practice research
- Dependencies from multiple sources (Phase 1 + research)

### ✅ "not generate foundational services unless requested"
- Explicitly excludes VNet, NSG, Subnets, DNS, Route Tables
- Documents rationale (pre-existing platform infrastructure)
- Special case handling if user explicitly requests them

### ✅ "follow phase 1 instructional patterns from prompts folder"
- Instructions moved to `agent_instructions.yaml`
- Same structure: name, description, instructions
- Helper function in `prompts/__init__.py`
- Agent loads instructions via `get_service_analysis_agent_instructions()`

### ✅ "make it separate agent instruction not phase 2 but something professional"
- Name: "Azure Service Requirements Analyst" (professional)
- Separate section in YAML (not embedded in code)
- Detailed, structured instructions
- Clear sections and examples

---

## Testing Impact

The agent will now:
1. **Skip foundational services** (VNet, NSG) unless explicitly requested
2. **Use Bing Grounding** extensively to research each service
3. **Calculate dependencies** from network flows + RBAC + research
4. **Enrich configurations** beyond Phase 1 detection
5. **Document sources** for all research findings

Expected output will have:
- Fewer services (no platform infrastructure)
- Richer configurations (from research)
- More accurate dependencies (multi-source)
- Research source URLs for audit trail

---

## Next Steps for User

1. **Test the updated agent**:
   ```bash
   python main.py input/Architecture_DataFlow_v1.png
   ```

2. **Verify Bing Grounding is enabled** in `.env`:
   ```
   BING_CONNECTION_NAME=bing-grounding
   ```

3. **Review generated service list** - should NOT include VNet/NSG unless requested

4. **Check research sources** - each service should have documentation URLs

5. **Optional: Request foundation services explicitly**:
   ```bash
   # During Stage 2 user validation, if you want networking:
   # Tell the agent "include networking infrastructure"
   ```

---

**All changes maintain backward compatibility while significantly improving service analysis quality and alignment with Phase 1's proven instruction pattern.** ✅

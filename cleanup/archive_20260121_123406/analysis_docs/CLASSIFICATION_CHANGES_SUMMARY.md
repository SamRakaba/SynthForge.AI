# Classification System Updates - Summary

## Changes Made ✅

### 1. Split Infrastructure Category
**Before:**
```python
infrastructure: List[str]  # Mixed: VNets, App Service, Function App
```

**After:**
```python
infrastructure: List[str]        # Compute/storage per-app (MUST detect)
network_topology: List[str]      # Network boundaries (reference only)
```

**Rationale:** Network topology elements (VNets, Subnets, NSGs) are often containers/boundaries, not standalone deployable resources. Separating them allows Vision agent to focus on core infrastructure.

---

### 2. Made External Sources Reference Only
**Before:**
- External sources mixed with critical components
- Counted in "MUST detect all N components"

**After:**
- `external_sources` explicitly marked as reference only
- NOT counted in critical detection requirements
- Vision agent detects only if explicitly visible

**Rationale:** External systems (SAP, CSV files, APIs) are not Azure resources and shouldn't inflate detection requirements.

---

### 3. Updated Component Priorities

**Critical (MUST Detect):**
- `azure_components`: Core Azure managed services
- `infrastructure`: Compute/storage deployed per-app

**Reference Only:**
- `network_topology`: VNets, Subnets, NSGs
- `external_sources`: Non-Azure systems
- `supporting_services`: Monitoring, Identity, DevOps
- `users_actors`: User types

---

### 4. Added Filter Hints with MCP Priority

New method: `to_filter_hints()` returns:
```python
{
    "architectural_components": [...],
    "reference_only": {
        "network_topology": [...],
        "external_sources": [...],
        "supporting_services": [...],
        "users_actors": [...]
    },
    "classification_guidance": {...},
    "mcp_research_priority": {
        "note": "If Azure MCP shows different pattern → TRUST MCP"
    }
}
```

**Conflict Resolution Rule:**
**Azure MCP research > Description hints > Bing/MS Learn**

---

## Updated Classification Categories

| Category | Examples | Critical? | Filter Decision |
|----------|----------|-----------|-----------------|
| **azure_components** | API Management, Cosmos DB, Functions | ✅ MUST detect | INCLUDE (architectural) |
| **infrastructure** | App Service, VMs, Storage Account | ✅ MUST detect | INCLUDE (architectural) |
| **network_topology** | VNet, Subnet, NSG, Private Endpoint | ⚠️ Reference | Include as boundary/container |
| **external_sources** | SAP, CSV files, Third-party APIs | ⚠️ Reference | FILTER OUT (non-Azure) |
| **supporting_services** | Azure Monitor, DevOps, Entra ID | ⚠️ Reference | FILTER OUT (unless per-app) |
| **users_actors** | Business Users, Data Analysts | ⚠️ Reference | FILTER OUT (not resources) |

---

## Impact on Agent Pipeline

### Stage 0: Description Agent
- Now categorizes into 6 distinct categories
- Provides clearer guidance to Vision agent
- Reduces over-counting of reference items

### Stage 1: Vision Agent
**Receives updated context hints:**
```
### Azure Managed Services (DETECT ALL):
  1. Azure Functions
  2. Azure Cosmos DB

### Infrastructure Components (DETECT ALL):
  3. App Service
  4. Storage Account

### Network Topology (Reference Only - NOT in critical count):
  - VNet
  - Integration Subnet

### External Sources (Reference Only - NOT in critical count):
  - SAP System

### Supporting Services (Reference Only - NOT in critical count):
  - Azure Monitor

CRITICAL REQUIREMENT: You MUST detect ALL 4 components listed above.
```

### Stage 3: Filter Agent (Future)
**Will receive filter hints with MCP priority:**
1. Check description hint → Initial suggestion
2. Query Azure MCP → Authoritative ARM type
3. If conflict → **Trust MCP research**
4. Apply classification decision

---

## Examples

### Example 1: VNet and Subnets
**Old behavior:** VNet counted in critical components → inflates requirements
**New behavior:** VNet in network_topology → reference only, detected if visible

### Example 2: Azure Firewall in VNet
**network_topology:** ["VNet", "Firewall Subnet"]
**infrastructure:** ["Azure Firewall"]  ← Standalone appliance
**Result:** Firewall = architectural (deployed), VNet = boundary

### Example 3: SAP Integration
**external_sources:** ["SAP System"]
**Result:** Detected if visible, but NOT counted in critical requirements, filtered out by filter agent

### Example 4: Key Vault Classification Conflict
**Description hint:** supporting_services (misclassified as shared)
**MCP research:** Microsoft.KeyVault/vaults with per-app deployment
**Filter decision:** **INCLUDE as architectural** (MCP overrides hint)

---

## Testing Verification

Run this to test the implementation:
```bash
cd SynthForge.AI
python -c "
from synthforge.agents.description_agent import ArchitectureDescription

desc = ArchitectureDescription(
    azure_components=['Azure Functions', 'Cosmos DB'],
    infrastructure=['App Service', 'Storage Account'],
    network_topology=['VNet', 'Integration Subnet'],
    external_sources=['SAP System'],
    supporting_services=['Azure Monitor']
)

print('Critical components (MUST detect):', desc.get_all_components())
print('Count:', len(desc.get_all_components()))

hints = desc.to_filter_hints()
print('\nArchitectural:', hints['architectural_components'])
print('Network topology:', hints['reference_only']['network_topology'])
print('MCP priority rule:', hints['mcp_research_priority']['note'])
"
```

**Expected output:**
```
Critical components (MUST detect): ['Azure Functions', 'Cosmos DB', 'App Service', 'Storage Account']
Count: 4

Architectural: ['Azure Functions', 'Cosmos DB', 'App Service', 'Storage Account']
Network topology: ['VNet', 'Integration Subnet']
MCP priority rule: If Azure MCP research shows a different ARM resource type or deployment pattern than suggested here, TRUST THE MCP RESEARCH
```

---

## Next Steps (Not Yet Implemented)

1. **Update workflow.py:** Pass description hints to filter agent
2. **Update filter_agent.py:** Accept hints and implement MCP priority logic
3. **Update filter agent prompt:** Add conflict resolution instructions
4. **Add integration tests:** Test MCP override scenarios

---

## Files Modified

1. `synthforge/agents/description_agent.py`
   - Added `network_topology` field
   - Updated `get_all_components()` logic
   - Updated `to_context_hints()` with reference sections
   - Added `to_filter_hints()` method with MCP priority
   - Updated DESCRIPTION_PROMPT with new categories

2. `RESOURCE_CLASSIFICATION_FLOW.md`
   - Updated category definitions
   - Added MCP priority documentation
   - Updated decision tree
   - Added conflict resolution examples
   - Updated test scenarios

3. `CLASSIFICATION_CHANGES_SUMMARY.md` (this file)
   - Complete change documentation

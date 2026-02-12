# Dynamic Common Module Detection

## Overview

**BEFORE**: Common infrastructure modules (private endpoints, diagnostics, RBAC, locks) were **hardcoded** in `workflow_phase2.py` with a static list of 4 modules.

**AFTER**: Common modules are **dynamically detected** by the Service Analysis Agent based on actual Phase 1 recommendations and service requirements.

## How It Works

### 1. Service Analysis Agent Detects Patterns

The Service Analysis Agent (Stage 1 of Phase 2) now analyzes Phase 1 recommendations and outputs a `common_patterns` section:

```json
{
  "services": [...],
  "common_patterns": {
    "private_endpoint": {
      "required": true,
      "usage_count": 8,
      "arm_type": "Microsoft.Network/privateEndpoints",
      "folder_path": "network-privateendpoints",
      "description": "Private Endpoint configuration for network isolation",
      "justification": "8 services require private endpoints for secure access",
      "subresource_types": ["vault", "blob", "sites"],
      "avm_source": "avm/res/network/private-endpoint",
      "best_practices": [
        "Use private endpoints for all data services",
        "Deploy in same region as parent resource"
      ]
    },
    "diagnostics": {
      "required": true,
      "usage_count": 10,
      "arm_type": "Microsoft.Insights/diagnosticSettings",
      "folder_path": "insights-diagnosticsettings",
      "description": "Diagnostic settings for monitoring and logging",
      "justification": "All services need diagnostics for observability"
    }
  }
}
```

### 2. Agent Uses MCP Tools for Research

The Service Analysis Agent leverages **existing MCP servers** (no new ones needed):

- **Bing Grounding**: Searches for latest Azure best practices, AVM implementations
- **MS Learn MCP**: Retrieves official Azure documentation for each resource type

Example research queries:
```
"Azure verified module for private endpoints terraform"
"Microsoft.Network/privateEndpoints best practices"
"diagnostic settings common patterns Azure"
```

### 3. Workflow Creates Modules Dynamically

`workflow_phase2.py` extracts `common_patterns` from Service Analysis result:

```python
# Extract common_patterns from agent analysis
common_patterns = service_result.common_patterns

# Create common modules dynamically (not hardcoded)
common_modules = self._create_common_module_mappings(
    iac_format=self.iac_format,
    common_patterns=common_patterns  # Agent-detected patterns
)
```

### 4. Threshold Logic Determines Which Patterns Become Modules

Only patterns meeting criteria become common modules:
- `required == true` (pattern is essential)
- `usage_count >= 2` (used by 2+ services)

Example:
```python
for pattern_key, pattern_data in common_patterns.items():
    if pattern_data.get('required') and pattern_data.get('usage_count', 0) >= 2:
        # Create common module for this pattern
        create_module(pattern_data['arm_type'])
```

## What Changed

### Files Modified

1. **workflow_phase2.py**
   - `_create_common_module_mappings()` now accepts `common_patterns` parameter
   - Loops through agent-detected patterns instead of hardcoded list
   - Falls back to defaults only if agent doesn't provide patterns
   - Logs detailed reasoning for each common module

2. **service_analysis_agent.py**
   - Added `common_patterns` field to `ServiceAnalysisResult`
   - Extracts `common_patterns` from agent response JSON
   - Logs detected patterns with usage counts
   - Passes patterns to Phase 2 workflow

3. **iac_agent_instructions.yaml** (already had instructions)
   - Lines 297-324: Documents `common_patterns` output format
   - Line 778: "analyze the common_patterns section"
   - Line 790: "FOR EACH pattern: IF required=true AND count>=2"

## Agent Instructions

The Service Analysis Agent prompt (in `iac_agent_instructions.yaml`) includes:

```yaml
7. Analyze Common Patterns (NEW):
   - Review all services' security_requirements, network_requirements
   - Identify repeated infrastructure patterns:
     * private_endpoint: Services requiring private endpoint (>=2 services)
     * diagnostics: Services requiring diagnostic settings (>=2 services)
     * rbac: Services requiring role assignments (>=2 services)
     * backup: Services requiring backup vaults (>=2 services)
     * encryption: Services requiring customer-managed keys (>=2 services)
   - FOR EACH pattern:
     * Set required=true if essential for architecture
     * Count usage_count across all services
     * Use Bing Grounding to find AVM source
     * Use MS Learn MCP for best practices
```

## Benefits

### 1. **No Hardcoding**
- System works for ANY common pattern, not just 4 hardcoded ones
- Supports new patterns: backup, encryption, monitoring, etc.

### 2. **Agent-Driven Intelligence**
- Service Analysis Agent detects patterns from Phase 1 analysis
- Uses MCP tools to research each pattern's implementation
- Adapts to specific architecture requirements

### 3. **Accurate Pattern Detection**
- Only creates common modules that are actually needed
- Usage count ensures module is genuinely common (used by 2+ services)
- Avoids creating unnecessary modules

### 4. **Extensible**
- Easy to add new pattern types (just update agent instructions)
- No code changes needed for new patterns
- Agent figures out ARM types and AVM sources

## Example Scenarios

### Scenario 1: Standard Web Application
**Phase 1 Recommendations**:
- App Service needs private endpoint
- Cosmos DB needs private endpoint
- Key Vault needs private endpoint
- All services need diagnostics

**Agent Output**:
```json
"common_patterns": {
  "private_endpoint": {
    "required": true,
    "usage_count": 3,
    "arm_type": "Microsoft.Network/privateEndpoints"
  },
  "diagnostics": {
    "required": true,
    "usage_count": 3,
    "arm_type": "Microsoft.Insights/diagnosticSettings"
  }
}
```

**Result**: 2 common modules created (private_endpoint + diagnostics)

### Scenario 2: Data Platform with Backup
**Phase 1 Recommendations**:
- SQL Database needs backup vault
- PostgreSQL needs backup vault
- Blob Storage needs backup vault
- All need diagnostics

**Agent Output**:
```json
"common_patterns": {
  "backup": {
    "required": true,
    "usage_count": 3,
    "arm_type": "Microsoft.DataProtection/backupVaults"
  },
  "diagnostics": {
    "required": true,
    "usage_count": 3,
    "arm_type": "Microsoft.Insights/diagnosticSettings"
  }
}
```

**Result**: 2 common modules (backup + diagnostics), NO private_endpoint (not needed)

## Fallback Behavior

If Service Analysis Agent doesn't provide `common_patterns`, workflow uses fallback defaults:

```python
def _get_fallback_common_patterns(self) -> Dict[str, Any]:
    """Fallback when agent doesn't provide patterns (legacy mode)."""
    return {
        "private_endpoint": {...},
        "diagnostics": {...},
        "rbac": {...},
        "lock": {...}
    }
```

This ensures backward compatibility during transition period.

## MCP Server Requirements

### Question: Do we need additional MCP servers?

**Answer: NO** - Current MCP servers are sufficient:

1. **Bing Grounding** (already configured):
   - Searches web for latest AVM implementations
   - Finds Azure best practices documentation
   - Example: "Azure verified module for private endpoints terraform"

2. **MS Learn MCP** (already configured):
   - Searches official Microsoft documentation
   - Retrieves Azure resource schema details
   - Example: `microsoft_docs_search("Microsoft.Network/privateEndpoints")`

### What Agents Can Do with Current MCP Tools

```python
# Example: Agent researching private endpoint pattern

# 1. Use Bing to find AVM module
query = "Azure verified module private endpoint terraform latest"
results = bing_grounding_search(query)
# Finds: https://github.com/Azure/terraform-azurerm-avm-res-network-privateendpoint

# 2. Use MS Learn to get resource details
query = "Microsoft.Network/privateEndpoints configuration properties"
docs = ms_learn_search(query)
# Gets: Subnet requirements, DNS settings, etc.

# 3. Agent synthesizes into common_patterns output
common_patterns["private_endpoint"] = {
    "arm_type": "Microsoft.Network/privateEndpoints",
    "avm_source": "avm/res/network/private-endpoint",
    "required_inputs": ["subnet_id", "private_connection_resource_id"],
    "best_practices": ["Deploy in same region", "Use private DNS zones"]
}
```

## Testing

To test the dynamic common module detection:

1. Run Phase 1 with different architectures
2. Check Phase 2 Stage 1 output for `common_patterns`
3. Verify common modules match detected patterns
4. Confirm no hardcoded modules are created unnecessarily

Example test command:
```bash
python -m synthforge.cli phase2 \
  --phase1-dir "./phase1_outputs" \
  --iac-format terraform \
  --output-dir "./phase2_outputs"
```

Look for log entries:
```
✓ Agent detected 3 common patterns:
   - private_endpoint: Microsoft.Network/privateEndpoints (used by 5 services, required=True)
   - diagnostics: Microsoft.Insights/diagnosticSettings (used by 7 services, required=True)
   - backup: Microsoft.DataProtection/backupVaults (used by 2 services, required=True)

✓ Creating common module: network-privateendpoints (used by 5 services)
✓ Creating common module: insights-diagnosticsettings (used by 7 services)
✓ Creating common module: dataprotection-backupvaults (used by 2 services)
```

## Future Enhancements

1. **Pattern Learning**: Track which patterns are used frequently across projects
2. **Custom Thresholds**: Allow users to configure `usage_count` threshold (default: 2)
3. **Pattern Suggestions**: Agent suggests additional patterns based on service types
4. **Cost Analysis**: Estimate cost impact of common infrastructure modules

## Summary

- ✅ **Dynamic Detection**: Agent analyzes Phase 1 to detect common patterns
- ✅ **No Hardcoding**: Works for ANY pattern, not just 4 hardcoded ones
- ✅ **MCP Research**: Uses existing Bing + MS Learn (no new servers needed)
- ✅ **Threshold Logic**: Only creates modules used by 2+ services
- ✅ **Extensible**: Easy to add new patterns in agent instructions
- ✅ **Fallback Safe**: Falls back to defaults if agent doesn't provide patterns

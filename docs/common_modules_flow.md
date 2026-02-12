# Common Modules Generation Flow

## Overview
This document explains how common/shared modules (private-endpoint, diagnostic-settings, role-assignment, lock) are **dynamically determined from best practices and solution requirements**, then communicated between stages and generated.

**Key Principle**: Common modules are NOT generic - they are **justified by Azure best practices, security benchmarks, and actual solution needs**.

## Quick Decision Rules

**Should I create a common module?**

✅ **YES** - Create common module IF:
1. **2+ services need it** (e.g., 3 services need private endpoints)
2. **Best practice requires it** (e.g., Azure Security Benchmark NS-2 requires private connectivity)
3. **You can cite the specific requirement** (e.g., link to WAF documentation)

❌ **NO** - Inline the resource IF:
1. Only 1 service needs it
2. No best practice requires it
3. Service-specific configuration (not reusable)

**Each common module MUST include**:
- `source`: Specific Azure Security Benchmark control or WAF pillar
- `justification`: WHY this solution needs it
- `services_needing`: WHICH services need it
- `best_practice_url`: Official documentation URL

---

## Data Flow: Stage 2 → Stage 3 → Stage 4

### Stage 2: Service Analysis Agent

**Detects Common Patterns FROM ACTUAL ARCHITECTURE**

The Service Analysis Agent analyzes Phase 1 outputs and detects which common patterns are needed across multiple services:

```json
{
  "common_patterns": {
    "private_endpoint": {
      "required": true,
      "services_needing": ["openai-service", "storage-account", "key-vault"],
      "rationale": "3+ services require private connectivity"
    },
    "diagnostics": {
      "required": true,
      "services_needing": ["openai-service", "storage-account", "key-vault", "apim"],
      "rationale": "All services need logging to Log Analytics"
    },
    "rbac": {
      "required": true,
      "services_needing": ["openai-service", "key-vault"],
      "rationale": "Services need RBAC assignments for managed identities"
    },
    "lock": {
      "required": false,
      "services_needing": [],
      "rationale": "No production lock requirements detected"
    }
  }
}
```

**Key Fields**:
- `required`: Boolean - Should this common module be generated?
- `services_needing`: Array - Which services need this pattern
- `rationale`: String - Why this is needed

---

### Stage 3: Module Mapping Agent

**Converts Common Patterns → Common Modules List WITH JUSTIFICATION**

The Module Mapping Agent receives Service Analysis output and:
1. **Reviews each common_patterns entry**
2. **Researches best practices** for each pattern (Azure Security Benchmark, WAF, service docs)
3. **Determines if a common module is justified** (2+ services need it AND best practice requires it)
4. **Creates grounded justification** for each common module

**Example: Private Endpoint Decision**:
```
INPUT: common_patterns.private_endpoint.required = true, services_needing = 3

RESEARCH:
→ Query: "Azure private endpoint security baseline site:learn.microsoft.com"
→ Finding: Azure Security Benchmark NS-2 requires private connectivity for PaaS services
→ URL: https://learn.microsoft.com/azure/security/benchmarks/security-controls-v3-network-security#ns-2

DECISION: CREATE common module
JUSTIFICATION: "Azure Security Benchmark NS-2: 3 services require private endpoints for secure network connectivity"
```

**Output: Grounded common_modules Array**:

```json
{
  "service_name": "Azure OpenAI Service",
  "module_structure": {
    "main_module": { ... },
    "supporting_modules": [ ... ]
  },
  "common_modules": [
    {
      "module_name": "private-endpoint",
      "folder_path": "modules/common/private-endpoint",
      "required": true,
      "source": "Azure Security Benchmark NS-2: Secure network connectivity",
      "justification": "3 services require private endpoints for secure, isolated connectivity",
      "services_needing": ["cognitive-services-account", "storage-account", "key-vault"],
      "avm_pattern_reference": "Azure/avm-res-network-privateendpoint/azurerm",
      "best_practice_url": "https://learn.microsoft.com/azure/security/benchmarks/security-controls-v3-network-security#ns-2"
    },
    {
      "module_name": "diagnostic-settings",
      "folder_path": "modules/common/diagnostic-settings",
      "required": true,
      "source": "Well-Architected Framework: Operational Excellence",
      "justification": "All 5 services require diagnostic logging to Log Analytics workspace for monitoring",
      "services_needing": ["cognitive-services-account", "storage-account", "key-vault", "api-management", "function-app"],
      "avm_pattern_reference": "Built-in diagnostic_settings parameter in AVM modules",
      "best_practice_url": "https://learn.microsoft.com/azure/well-architected/operational-excellence/observability"
    },
    {
      "module_name": "role-assignment",
      "folder_path": "modules/common/role-assignment",
      "required": true,
      "source": "Azure Security Benchmark IM-1: Use managed identities",
      "justification": "API Management and Function App need RBAC assignments for managed identity authentication to OpenAI",
      "services_needing": ["api-management", "function-app"],
      "avm_pattern_reference": "Built-in role_assignments parameter in AVM modules",
      "best_practice_url": "https://learn.microsoft.com/azure/security/benchmarks/security-controls-v3-identity-management#im-1"
    }
  ],
      "folder_path": "modules/common/role-assignment",
      "required": true,
      "source": "Detected from common_patterns.rbac in Service Analysis",
      "avm_pattern_reference": "Built-in to most AVM modules"
    }
  ],
  "best_practices": [ ... ]
}
```

**Key Fields**:
- `module_name`: Kebab-case module name (matches folder name)
- `folder_path`: Where to generate the module (`modules/common/<module-name>`)
- `required`: Boolean - MUST generate this module
- `source`: Explanation of where this requirement came from
- `avm_pattern_reference`: AVM module to study for patterns

**Mapping Logic (GENERIC - NO HARDCODING)**:
```
For EACH pattern in common_patterns:
  IF pattern.required = true AND pattern.count >= 2:
    module_name = pattern_name.replace("_", "-")  # private_endpoint → private-endpoint
    folder_path = f"modules/common/{module_name}"
    
    # Research best practices for THIS pattern
    research_query = f"Azure {pattern_name} best practices site:learn.microsoft.com"
    
    # Add to common_modules array
    common_modules[] += {
      module_name, folder_path, required: true,
      source: <RESEARCHED>, justification: <RESEARCHED>,
      best_practice_url: <RESEARCHED>
    }
```

**KEY BENEFIT**: Works for ANY pattern type - no code changes needed for new patterns!

---

### Stage 4: Module Development Agent

**Generates Common Modules FIRST, Then Service Modules**

#### Step 5A: Generate Common Modules

The Module Development Agent receives the `common_modules` array from Stage 3 and:

1. **Iterates through common_modules array**:
   ```python
   for common_module in mapping_result.common_modules:
       if common_module["required"]:
           generate_common_module(
               module_name=common_module["module_name"],
               folder_path=common_module["folder_path"],
               avm_pattern=common_module["avm_pattern_reference"]
           )
   ```

2. **For each common module**:
   - Creates `modules/common/<module-name>/` folder
   - Generates files:
     * `main.tf` or `main.bicep` - Native resource definition
     * `variables.tf` or `parameters.bicep` - All inputs
     * `outputs.tf` or `outputs.bicep` - Module outputs
     * `versions.tf` (Terraform only) - Provider requirements
     * `README.md` - Usage documentation

3. **Example: Generate private-endpoint module**:
   ```
   modules/common/private-endpoint/
     main.tf              <- resource "azurerm_private_endpoint" "this" { ... }
     variables.tf         <- var.name, var.subnet_id, var.resource_id, etc.
     outputs.tf           <- output "id", output "private_ip_address"
     versions.tf          <- terraform { required_providers { ... } }
     README.md            <- Usage docs
   ```

#### Step 5B: Service Modules Call Common Modules

When generating service-specific modules, the agent:

1. **Checks if common module exists** (from common_modules list)
2. **Uses module call instead of inline resources**:
   ```hcl
   # Instead of:
   resource "azurerm_private_endpoint" "this" {
     count = var.enable_private_endpoint ? 1 : 0
     # ... 30 lines ...
   }
   
   # Generate:
   module "private_endpoint" {
     source = "../common/private-endpoint"
     count  = var.enable_private_endpoint ? 1 : 0
     
     name                 = "${var.name}-pe"
     location             = var.location
     resource_group_name  = var.resource_group_name
     subnet_id            = var.private_endpoint_subnet_id
     resource_id          = azurerm_cognitive_account.this.id
     subresource_names    = ["account"]  # Service-specific
     private_dns_zone_ids = var.private_dns_zone_ids
     tags                 = var.tags
   }
   ```

---

## Resulting Folder Structure

After Stage 4 completes:

```
modules/
  common/                          <- Generated from common_modules array
    private-endpoint/              <- If common_patterns.private_endpoint.required = true
      main.tf
      variables.tf
      outputs.tf
      versions.tf
      README.md
    diagnostic-settings/           <- If common_patterns.diagnostics.required = true
      main.tf
      variables.tf
      outputs.tf
      versions.tf
      README.md
    role-assignment/               <- If common_patterns.rbac.required = true
      main.tf
      variables.tf
      outputs.tf
      versions.tf
      README.md
    lock/                          <- If common_patterns.lock.required = true (optional)
      main.tf
      variables.tf
      outputs.tf
      versions.tf
      README.md
  
  cognitive-services-account/      <- Service-specific module
    main.tf                        <- Calls ../common/private-endpoint, ../common/diagnostic-settings
    variables.tf
    outputs.tf
    versions.tf
    README.md
  
  storage-account/                 <- Service-specific module
    main.tf                        <- Calls ../common/private-endpoint, ../common/diagnostic-settings
    variables.tf
    outputs.tf
    versions.tf
    README.md
```

---

## Benefits

### 1. **DRY Principle**
- Common modules written once, used by all service modules
- No duplicate private endpoint code across 5+ service modules

### 2. **Consistency**
- All private endpoints have same configuration pattern
- All diagnostic settings use same structure
- Easier to maintain and update

### 3. **Reusability**
- `modules/common/private-endpoint/` can be used by ANY Azure service
- `modules/common/diagnostic-settings/` works with ANY monitored resource

### 4. **Separation of Concerns**
- **Common modules**: Generic, reusable patterns
- **Service modules**: Service-specific business logic
- **Environment orchestration**: Deployment-specific configs (Stage 5)

---

## Validation Checklist

After Stage 4 completes, verify:

- [ ] `modules/common/` folder exists
- [ ] Each required common module has its own subfolder
- [ ] Each common module has: main, variables, outputs, README
- [ ] Service modules in `modules/<service-type>/` call common modules via `source = "../common/<module-name>"`
- [ ] No inline `azurerm_private_endpoint` resources in service modules (should be module calls)
- [ ] No common modules generated if `common_patterns.<pattern>.required = false`

---

## Example Workflow

### Input: Phase 1 Analysis
```
Phase 1 detects:
- 3 services need private endpoints
- All services need diagnostics
- 2 services need RBAC
- No locks required
```

### Stage 2: Service Analysis
```json
{
  "common_patterns": {
    "private_endpoint": { "required": true, "services_needing": 3 },
    "diagnostics": { "required": true, "services_needing": 5 },
    "rbac": { "required": true, "services_needing": 2 },
    "lock": { "required": false, "services_needing": 0 }
  }
}
```

### Stage 3: Module Mapping
```json
{
  "common_modules": [
    { "module_name": "private-endpoint", "required": true, ... },
    { "module_name": "diagnostic-settings", "required": true, ... },
    { "module_name": "role-assignment", "required": true, ... }
  ]
}
```
**Note**: `lock` NOT included because `required: false`

### Stage 4: Module Development
```bash
Step 5A: Generate Common Modules
  ✓ Generated modules/common/private-endpoint/
  ✓ Generated modules/common/diagnostic-settings/
  ✓ Generated modules/common/role-assignment/
  ✗ Skipped modules/common/lock/ (not required)

Step 6: Generate Service Modules
  ✓ modules/cognitive-services-account/ (calls ../common/private-endpoint, ../common/diagnostic-settings)
  ✓ modules/storage-account/ (calls ../common/private-endpoint, ../common/diagnostic-settings)
  ✓ modules/key-vault/ (calls ../common/private-endpoint, ../common/diagnostic-settings, ../common/role-assignment)
```

---

## Implementation Notes

### For Stage 3 (Module Mapping Agent)

**Instructions Updated**:
- Line 761-790: Added `common_modules` array to output format
- Line 847-853: Added note explaining common_modules detection from common_patterns

**Logic**:
```python
common_modules = []
if service_analysis.common_patterns.private_endpoint.required:
    common_modules.append({
        "module_name": "private-endpoint",
        "folder_path": "modules/common/private-endpoint",
        "required": True,
        "source": "Detected from common_patterns.private_endpoint",
        "avm_pattern_reference": "Azure/avm-res-network-privateendpoint/azurerm"
    })
# Repeat for diagnostics, rbac, lock
```

### For Stage 4 (Module Development Agent)

**Instructions Updated**:
- Line 1596-1603: Added INPUT section explaining common_modules array format
- Line 1943-1950: Added note explaining dynamic generation based on common_modules list

**Logic**:
```python
# Step 5A: Generate common modules
for common_module in mapping_result.common_modules:
    if common_module["required"]:
        generate_module(
            folder_path=common_module["folder_path"],
            module_type="common",
            avm_pattern=common_module["avm_pattern_reference"]
        )

# Step 6: Generate service modules
for service_mapping in mapping_result.mappings:
    generate_module(
        folder_path=service_mapping.folder_path,
        module_type="service",
        common_modules_available=mapping_result.common_modules
    )
```

---

## Summary

**Detection**: Stage 2 analyzes patterns → `common_patterns` object  
**Mapping**: Stage 3 converts patterns → `common_modules` array  
**Generation**: Stage 4 generates common modules FIRST, then service modules call them  

This ensures:
- ✅ DRY: No duplicate code
- ✅ Dynamic: Only generates what's needed
- ✅ Reusable: Common modules work for any service
- ✅ Clear: Explicit data flow between stages

🎉 **Result**: Production-ready IaC with shared, reusable common modules!

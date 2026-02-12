# Step 3 & Step 4 Consistency - Implementation Summary

## Overview
Resolved conflicts between Step 3 (Module Mapping) and Step 4 (Module Development) to ensure both focus on **modules/ only**, with environments/ reserved for Stage 5.

---

## Key Changes

### 1. **Step 3 (Module Mapping Agent) - Modules Focus**

#### ✅ **Removed `environment_wrapper` from Output**
- **Before**: Step 3 output included `environment_wrapper` with `folder_path: "environments/dev"`
- **After**: Step 3 outputs only module mappings with `folder_path: "modules/<resource-type>"`
- **Rationale**: Stage 3 maps services to modules. Stage 5 handles environment orchestration.

#### ✅ **Updated `folder_structure` Section**
- **Before**: Showed both `modules/` and `environments/` as if both generated in Stage 3
- **After**: Clearly states Stage 3 outputs mappings, Stage 4 generates modules/, Stage 5 creates environments/

```yaml
"folder_structure": {
  "stage": "Stage 3: Module Mapping - Modules Only",
  "pattern": "Reusable modules following Terraform Registry and AVM patterns",
  "description": "Stage 3 outputs module mappings. Stage 4 generates modules/. Stage 5 creates environments/.",
  "structure": [
    "modules/                          # Stage 4 generates these",
    "  cognitive-services-account/     # Service-specific module",
    "  common/                         # Shared patterns",
    "",
    "environments/                     # Stage 5 generates these (NOT Stage 3/4)",
    "  dev/",
    "  staging/",
    "  prod/"
  ]
}
```

#### ✅ **Updated Quality Checks**
Added explicit checks:
- ✓ folder_path specifies modules/ directory
- ✓ NO environment_path or deployment references (those are Stage 5)

#### ✅ **Updated Important Notes**
- **Stage 3 Focus**: Map services to modules/, define folder paths for modules only
- **Modules Only**: Output folder_path for modules/ directory
- **No Environments**: Do NOT include environment_path - those are Stage 5

---

### 2. **Step 4 (Module Development Agent) - Native Resources**

#### ✅ **Removed Old "Layer 1/Layer 2" Pattern**
- **Before**: Had examples showing:
  - Layer 1: Wrap AVM module sources (`module "x" { source = "Azure/avm-..." }`)
  - Layer 2: Deployment wrappers in `Deployment/` folder
- **After**: Single pattern showing:
  - Native resources (`resource "azurerm_x" "this" { ... }`)
  - Calls to common modules from `modules/common/`
  - environments/ reserved for Stage 5

#### ✅ **Updated Examples to Show Native Resources**
```hcl
# modules/cognitive-services-account/main.tf (Stage 4)
resource "azurerm_cognitive_account" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  # ... native resource properties
}

# Call common modules
module "private_endpoint" {
  source = "../common/private-endpoint"
  # ...
}

# environments/dev/main.tf (Stage 5 - NOT Stage 4)
module "openai_service" {
  source = "../../modules/cognitive-services-account"
  # ...
}
```

#### ✅ **Updated Folder Structure Example**
```
modules/                           <- Stage 4 generates
  cognitive-services-account/
    main.tf                        <- Native resources
    variables.tf
    outputs.tf
    README.md
  common/                          <- Shared patterns
    private-endpoint/
    diagnostic-settings/

environments/                      <- Stage 5 generates (NOT Stage 4)
  dev/
  staging/
  prod/
```

#### ✅ **Updated Tool Usage Section**
- **Before**: "Find AVM Module" to use as source
- **After**: "Find AVM Module for Pattern Reference"
- Clarified: Study AVM GitHub to see patterns, but generate native resources

---

## Naming Convention Consistency

Both Step 3 and Step 4 now use:

### ✅ **Lowercase Folder Names**
- `modules/` (NOT `Modules/`)
- `environments/` (NOT `Deployment/`)
- `common/` (NOT `Common/`)

### ✅ **Kebab-Case Resource Types**
- `storage-account/`
- `cognitive-services-account/`
- `key-vault/`

### ✅ **Format-Agnostic Structure**
- No `terraform/` or `bicep/` folders
- File extensions indicate format (`.tf`, `.bicep`)

---

## Stage Boundaries Clarified

| Stage | Agent | Scope | Output |
|-------|-------|-------|--------|
| **Stage 3** | Module Mapping | Map services to modules | JSON with `folder_path: "modules/..."` |
| **Stage 4** | Module Development | Generate native resource modules | `modules/` folder with `.tf` or `.bicep` files |
| **Stage 5** | Deployment Wrappers | Environment orchestration | `environments/` folder with orchestration |

### Key Separation:
- **Stage 3**: Plans (mapping only)
- **Stage 4**: Generates reusable modules
- **Stage 5**: Generates environment-specific configs

---

## Files Modified

### 1. **iac_agent_instructions.yaml** (Module Mapping - Step 3)

**Line 789**: Removed `environment_wrapper` section
```yaml
# REMOVED:
"environment_wrapper": {
  "folder_path": "environments/dev",
  ...
}
```

**Lines 800-831**: Updated `folder_structure` to clarify stage boundaries
```yaml
"folder_structure": {
  "stage": "Stage 3: Module Mapping - Modules Only",
  ...
}
```

**Lines 1107-1124**: Updated Quality Checks
- Added: ✓ folder_path specifies modules/ directory
- Added: ✓ NO environment_path references

**Lines 1126-1134**: Updated Important Notes
- Clarified Stage 3 focus on modules only

**Lines 1038-1053**: Updated Priority 3 section
- Removed references to `/deployment/`
- Added note: "Stage 5 generates (NOT Stage 3)"

### 2. **iac_agent_instructions.yaml** (Module Development - Step 4)

**Line 1176**: Updated scope note
- Changed: `DO NOT generate deployment/` → `DO NOT generate environments/`

**Lines 1241-1269**: Updated folder structure example
- Changed: `/modules/` → `modules/`
- Changed: `/deployment/` → `environments/`
- Added: "Stage 5 generates (NOT Stage 4)"

**Lines 1303-1312**: Updated naming rules
- Removed: "Deployment folder naming rules"
- Added: "Environment folder naming rules (Stage 5 - NOT Stage 4)"

**Lines 1318-1410**: Replaced old Layer 1/Layer 2 pattern
- Removed: Examples with AVM module sources
- Added: Native resource examples
- Added: Stage 5 environment orchestration example

**Lines 1412-1435**: Updated Tool Usage section
- Changed: "Find AVM Module" → "Find AVM Module for Pattern Reference"
- Added: "DO NOT copy module source blocks - generate native resources!"

---

## Validation Checklist

After these changes, both Step 3 and Step 4:

- [x] Use lowercase folder names (`modules/`, `environments/`)
- [x] Focus on `modules/` only (no `environments/` in Stage 3/4)
- [x] Use kebab-case resource names
- [x] Generate native resources (NOT AVM module sources)
- [x] Call common modules from `modules/common/`
- [x] Reserve `environments/` for Stage 5
- [x] Use format-agnostic structure (file extensions indicate format)
- [x] Follow Terraform Registry and AVM patterns
- [x] Clarify stage boundaries in documentation

---

## Testing Recommendations

### Test Step 3 Output:
```bash
python main.py --skip-phase1 --iac-format terraform
```

**Check Module Mapping Output:**
- ✓ No `environment_wrapper` in JSON
- ✓ All `folder_path` values start with `modules/`
- ✓ No `environment_path` properties
- ✓ `folder_structure` clarifies Stage 3/4/5 boundaries

### Test Step 4 Output:
- ✓ Generates `modules/` folder (not `Modules/`)
- ✓ Contains native resources (`resource "azurerm_..."`)
- ✓ Does NOT generate `environments/` folder
- ✓ Calls common modules from `../common/`
- ✓ All folder names lowercase

---

## Benefits

### ✅ **Clear Stage Separation**
- No confusion about when environments/ are generated
- Step 3 maps, Step 4 generates modules, Step 5 orchestrates

### ✅ **Consistent Naming**
- Both steps use identical folder conventions
- No mixed case (Modules/ vs modules/)

### ✅ **Native Resources**
- Step 4 generates real infrastructure code
- No AVM module sources that need resolution

### ✅ **Reusable Modules**
- `modules/` contains truly reusable components
- `environments/` (Stage 5) orchestrates for specific deployments

### ✅ **Industry Standard**
- Matches Terraform Registry conventions
- Aligns with AVM folder structure
- Follows GitOps best practices

---

## Summary

Successfully resolved all conflicts between Step 3 and Step 4:

1. **Step 3** now focuses exclusively on mapping services to `modules/` folder paths
2. **Step 4** generates only `modules/` folder with native resources
3. **Stage 5** (future) will handle `environments/` orchestration
4. Both steps use consistent lowercase naming conventions
5. No more references to AVM module sources - only pattern learning
6. Clear documentation of stage boundaries

All instructions now follow the same pattern established in the folder structure implementation. 🎉

---

## Next Steps

1. ✅ All instruction conflicts resolved
2. ⏳ Test Phase 2 run to validate Step 3/4 consistency
3. ⏳ Verify agent generates correct folder structure
4. ⏳ Implement Stage 5 (Deployment Wrappers) with consistent pattern
5. ⏳ Update any remaining documentation

---

## References

- **Previous Work**: docs/folder_structure_implementation.md
- **Conflict Analysis**: docs/folder_structure_conflicts.md
- **Instructions File**: synthforge/prompts/iac_agent_instructions.yaml

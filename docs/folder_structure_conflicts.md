# Folder Structure Conflicts and Resolution

## Current Problems Identified

### 1. **Workflow Creates Format-Specific Folders (workflow_phase2.py:86-94)**
```python
self.bicep_output = self.iac_dir / "bicep"
self.terraform_output = self.iac_dir / "terraform"
self.pipeline_output = self.iac_dir / "pipelines"
```
**Problem**: Creates separate `bicep/` and `terraform/` top-level directories.

### 2. **Instructions Show Mixed Conventions (iac_agent_instructions.yaml:847-892)**
The instructions show **separate examples** for Terraform and Bicep:
```yaml
## Terraform AVM Structure
project-root/
├── modules/
├── deployment/

## Bicep AVM Structure  
project-root/
├── modules/
├── deployment/
```
**Problem**: Implies separate folder trees, but examples are actually identical.

### 3. **Capital vs Lowercase Inconsistency**
- Instructions: `Modules/` and `Deployment/` (capitalized)
- Agent prompts: `modules/` and `deployment/` (lowercase)
- Code fallback: `modules/default/` (lowercase)

### 4. **No DevOps Best Practice Guidance**
Instructions don't reference:
- Industry standards (Terraform Registry conventions, Microsoft IaC patterns)
- Repository patterns (monorepo vs polyrepo)
- Environment organization (dev/staging/prod)
- GitOps patterns

---

## Industry Best Practices Research

### **Terraform Registry Module Convention** (HashiCorp Standard)
```
terraform-<PROVIDER>-<NAME>/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── README.md
├── examples/
│   └── complete/
│       ├── main.tf
│       └── README.md
└── modules/
    └── <SUBMODULE>/
```
Source: https://developer.hashicorp.com/terraform/registry/modules/publish

### **Azure Verified Modules Structure** (Microsoft Standard)
```
avm-<res|ptn>-<provider>-<resource>/
├── main.tf / main.bicep
├── variables.tf / parameters.bicep
├── outputs.tf / outputs.bicep
├── locals.tf (optional)
├── README.md
├── examples/
│   ├── default/
│   └── complete/
└── modules/
    ├── private-endpoint/
    ├── diagnostic-settings/
    └── role-assignments/
```
Source: https://azure.github.io/Azure-Verified-Modules/specs/shared/

### **Microsoft Enterprise-Scale / ALZ Pattern**
```
infra-as-code/
├── modules/                    # Reusable modules
│   ├── networking/
│   ├── security/
│   └── compute/
├── live/                       # Environment-specific configurations
│   ├── dev/
│   ├── staging/
│   └── prod/
└── policies/
```
Source: https://learn.microsoft.com/azure/cloud-adoption-framework/

### **GitOps Repository Pattern** (Best Practice)
```
<REPO_ROOT>/
├── infrastructure/
│   ├── modules/               # Reusable modules (format-agnostic)
│   │   ├── storage-account/
│   │   ├── key-vault/
│   │   └── cognitive-services/
│   ├── environments/          # Environment-specific deployments
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── common/                # Shared modules (private-endpoint, diagnostics, rbac)
├── .github/workflows/         # CI/CD pipelines (GitHub Actions)
├── .azure-pipelines/          # CI/CD pipelines (Azure DevOps)
└── docs/
```

---

## Recommended Unified Folder Structure

### **Format-Agnostic Root Structure** (Based on Industry Standards)
```
<IaC_OUTPUT_ROOT>/
├── modules/                              # Reusable modules (LOWERCASE)
│   ├── common/                           # Shared patterns across services
│   │   ├── private-endpoint/
│   │   │   ├── main.tf OR main.bicep
│   │   │   ├── variables.tf OR parameters.bicep
│   │   │   ├── outputs.tf OR outputs.bicep
│   │   │   └── README.md
│   │   ├── diagnostic-settings/
│   │   ├── role-assignment/
│   │   └── resource-lock/
│   │
│   ├── storage-account/                  # Service-specific module
│   │   ├── main.tf OR main.bicep
│   │   ├── variables.tf OR parameters.bicep
│   │   ├── outputs.tf OR outputs.bicep
│   │   ├── locals.tf (optional)
│   │   ├── versions.tf (Terraform only)
│   │   └── README.md
│   │
│   ├── key-vault/
│   ├── cognitive-services-account/
│   └── cosmos-db-account/
│
├── environments/                         # Environment-specific deployments
│   ├── dev/
│   │   ├── main.tf OR main.bicep         # Orchestrates modules
│   │   ├── variables.tf OR parameters.bicep
│   │   ├── outputs.tf OR outputs.bicep
│   │   ├── terraform.tfvars.example
│   │   └── README.md
│   │
│   ├── staging/
│   └── prod/
│
├── pipelines/                            # CI/CD definitions
│   ├── azure-pipelines.yml              # Azure DevOps
│   └── github-workflows/                # GitHub Actions
│       ├── plan.yml
│       └── apply.yml
│
└── docs/
    ├── architecture-overview.md
    └── deployment-guide.md
```

### **Key Design Decisions**

| Decision | Rationale | Industry Standard |
|----------|-----------|-------------------|
| **No `bicep/` or `terraform/` folders** | File extensions (`.tf`, `.bicep`) already indicate format | ✅ Terraform Registry, AVM |
| **Lowercase folder names** | Unix/Linux compatibility, consistent with git repos | ✅ HashiCorp, Microsoft AVM |
| **`modules/` not `Modules/`** | Follows Terraform module conventions | ✅ Terraform Registry |
| **`environments/` not `deployment/`** | Clearer intent (dev/staging/prod), standard GitOps pattern | ✅ Enterprise Scale, GitOps |
| **`common/` subfolder in modules** | Separates shared patterns from service-specific | ✅ AVM submodule pattern |
| **`pipelines/` at root** | CI/CD is infrastructure concern, not environment-specific | ✅ Microsoft ALZ |

---

## Required Changes

### 1. **Update workflow_phase2.py** - Remove Format-Specific Folders
```python
# BEFORE (WRONG):
self.bicep_output = self.iac_dir / "bicep"
self.terraform_output = self.iac_dir / "terraform"

# AFTER (CORRECT):
self.modules_output = self.iac_dir / "modules"
self.environments_output = self.iac_dir / "environments"
self.pipelines_output = self.iac_dir / "pipelines"
self.docs_output = self.iac_dir / "docs"

# Create standard directory structure
(self.modules_output / "common").mkdir(parents=True, exist_ok=True)
self.environments_output.mkdir(parents=True, exist_ok=True)
self.pipelines_output.mkdir(parents=True, exist_ok=True)
self.docs_output.mkdir(parents=True, exist_ok=True)
```

### 2. **Update iac_agent_instructions.yaml** - Single Unified Example
Replace lines 847-892 with:

```yaml
# Unified Folder Structure (CRITICAL)

Follow industry-standard IaC repository patterns:

## Standard Structure (Format-Agnostic)
```
<ROOT>/
├── modules/                              # Reusable modules (file extension indicates format)
│   ├── common/                           # Shared patterns (private-endpoint, diagnostics, rbac, lock)
│   │   ├── private-endpoint/
│   │   │   ├── main.tf OR main.bicep
│   │   │   ├── variables.tf OR parameters.bicep
│   │   │   ├── outputs.tf OR outputs.bicep
│   │   │   └── README.md
│   │   ├── diagnostic-settings/
│   │   ├── role-assignment/
│   │   └── resource-lock/
│   │
│   ├── <resource-type>/                  # Service-specific modules
│   │   ├── main.tf OR main.bicep         # Native resource definition
│   │   ├── variables.tf OR parameters.bicep
│   │   ├── outputs.tf OR outputs.bicep
│   │   ├── versions.tf (Terraform only)
│   │   └── README.md
│   │
│   ├── storage-account/
│   ├── key-vault/
│   ├── cognitive-services-account/
│   └── cosmos-db-account/
│
├── environments/                         # Environment-specific orchestrations
│   ├── dev/
│   │   ├── main.tf OR main.bicep         # Calls modules, sets env-specific values
│   │   ├── variables.tf OR parameters.bicep
│   │   ├── outputs.tf OR outputs.bicep
│   │   ├── terraform.tfvars.example (Terraform)
│   │   └── README.md
│   │
│   ├── staging/
│   └── prod/
│
├── pipelines/
│   ├── azure-pipelines.yml
│   └── github-workflows/
│
└── docs/
```

## Naming Conventions (CRITICAL)

1. **Lowercase Everything**: `modules/`, `environments/`, `common/`
   - Rationale: Unix/Linux compatibility, git best practices
   
2. **Kebab-Case for Resources**: `storage-account/`, `key-vault/`, `cognitive-services-account/`
   - Rationale: Matches Azure resource provider naming
   
3. **Descriptive Environment Names**: `dev/`, `staging/`, `prod/`
   - NOT: `deployment/openai-service/` (too specific)
   - USE: `environments/dev/` (reusable pattern)

4. **Common Folder for Shared Modules**: `modules/common/`
   - Contains: private-endpoint, diagnostic-settings, role-assignment, resource-lock
   - Used by: Multiple service-specific modules

## File Extensions Indicate Format

**NO separate Terraform/Bicep folders** - Use file extensions:
- Terraform: `.tf`, `.tfvars`
- Bicep: `.bicep`, `.bicepparam`

Example - Same folder, different formats:
```
modules/storage-account/
├── main.tf              ← Terraform version
└── main.bicep           ← Bicep version (if generating both)
```
```

### 3. **Update Module Mapping Agent Prompts**
Change all references:
- `Modules/` → `modules/`
- `Deployment/` → `environments/`
- `deployment_wrapper_path` → `environment_path`

### 4. **Update Module Development Agent**
- Change folder parsing to expect `modules/` and `environments/`
- Update FILE markers in prompts
- Change default fallback paths

---

## Benefits of This Approach

### ✅ **Industry Standard Compliance**
- Matches Terraform Registry conventions
- Aligns with Azure Verified Modules structure
- Follows Microsoft Enterprise Scale / ALZ patterns
- Compatible with GitOps workflows

### ✅ **Format Agnostic**
- No `bicep/` or `terraform/` folders
- File extensions indicate format
- Easy to support both formats side-by-side

### ✅ **DevOps Friendly**
- `environments/` clearly separates dev/staging/prod
- `pipelines/` at root for CI/CD
- Monorepo-friendly structure

### ✅ **Scalable**
- `modules/common/` prevents duplication
- Service-specific modules are reusable
- Easy to add new environments or modules

### ✅ **Git Best Practices**
- Lowercase for cross-platform compatibility
- Clear separation of concerns
- Standard .gitignore patterns apply

---

## Migration Path (Existing Codebases)

If you have existing output with `bicep/` or `terraform/` folders:

```bash
# Flatten format-specific folders
mv iac/bicep/modules/* iac/modules/
mv iac/bicep/deployment/* iac/environments/
mv iac/terraform/modules/* iac/modules/
mv iac/terraform/deployment/* iac/environments/
rmdir iac/bicep iac/terraform
```

---

## References

1. **Terraform Module Registry Structure**
   - https://developer.hashicorp.com/terraform/registry/modules/publish

2. **Azure Verified Modules Specifications**
   - https://azure.github.io/Azure-Verified-Modules/specs/shared/

3. **Microsoft Cloud Adoption Framework - IaC Patterns**
   - https://learn.microsoft.com/azure/cloud-adoption-framework/ready/considerations/infrastructure-as-code

4. **Enterprise-Scale Architecture (ALZ)**
   - https://github.com/Azure/Enterprise-Scale

5. **GitOps Principles**
   - https://www.gitops.tech/

---

## Validation Checklist

After implementing changes:

- [ ] No `bicep/` or `terraform/` folders exist
- [ ] All folder names are lowercase
- [ ] `modules/common/` contains shared patterns
- [ ] `environments/` contains orchestration files
- [ ] `pipelines/` exists at root
- [ ] File extensions indicate format (`.tf`, `.bicep`)
- [ ] README.md in every module
- [ ] Module structure matches Terraform Registry pattern
- [ ] Environment structure supports dev/staging/prod
- [ ] CI/CD pipelines reference correct paths

---

## Next Steps

1. **Update workflow_phase2.py** - Remove format-specific folders
2. **Update iac_agent_instructions.yaml** - Single unified structure
3. **Update agent_instructions.yaml** - Consistent folder references
4. **Update module_mapping_agent.py** - Change data model paths
5. **Update module_development_agent.py** - Update FILE markers
6. **Test with sample run** - Validate folder creation
7. **Update documentation** - Reflect new structure

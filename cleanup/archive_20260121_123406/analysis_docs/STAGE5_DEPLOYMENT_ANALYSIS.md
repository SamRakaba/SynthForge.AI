# Stage 5 Deployment Wrapper Analysis

## Executive Summary

Stage 5 generates **production-ready deployment orchestration** that calls reusable modules from Stage 4 and applies Phase 1 architectural recommendations. This stage creates the `deployment/` folder with environment-parameterized templates and a `modules/naming/` module for CAF-compliant resource naming.

---

## Architecture Overview

### Stage 5 Purpose

**Input**: 
- Phase 1 analysis outputs (architecture_analysis.json, rbac_assignments.json, network_flows.json, etc.)
- Stage 3 module mappings (which modules to use)
- Stage 4 reusable modules (already generated in `modules/` folder)

**Output**:
```
deployment/
  main.tf / main.bicep           # Orchestrates Stage 4 modules
  variables.tf / parameters.bicep # User inputs (subscription, location, etc.)
  outputs.tf / outputs.bicep      # Deployment outputs
  terraform.tfvars.example / main.bicepparam.example  # Example values
  backend.tf / backend config     # Remote state configuration
  providers.tf / provider config  # Azure provider setup
  README.md                       # Deployment guide

modules/
  naming/                         # CAF naming module (generated in Stage 5)
    main.tf / main.bicep
    variables.tf / parameters.bicep
    outputs.tf / outputs.bicep
    README.md
```

### Key Differences from Stage 4

| Aspect | Stage 4 (Reusable Modules) | Stage 5 (Deployment Wrappers) |
|--------|----------------------------|-------------------------------|
| **Location** | `modules/{service-type}/` | `deployment/` |
| **Purpose** | Reusable building blocks | Environment-specific orchestration |
| **Scope** | Single resource type | Full architecture deployment |
| **Configuration** | Generic, parameterized | Applies Phase 1 recommendations |
| **Module Calls** | None (defines resources) | Calls Stage 4 modules |
| **Naming** | Variables for names | Uses naming module |
| **Backend Config** | None | Terraform/Bicep backend setup |
| **DevOps** | Not pipeline-ready | Pipeline-ready parameter files |

---

## Agent Implementation

### File: `deployment_wrapper_agent.py`

#### Core Responsibilities

1. **Load Phase 1 Outputs**: Read architecture analysis, RBAC, network topology, etc.
2. **Generate Naming Module**: CAF-compliant naming with service-specific constraints
3. **Generate Deployment Template**: Parameterized orchestration calling Stage 4 modules
4. **Apply Phase 1 Recommendations**: Security, network isolation, RBAC, monitoring
5. **Create Example Parameters**: `.tfvars.example` or `.bicepparam.example`
6. **Document Required Inputs**: Clear list of values users must provide

#### Key Methods

```python
async def generate_deployment_wrapper(
    phase1_outputs: Dict[str, Path],      # Phase 1 analysis files
    module_mappings: List[Dict[str, Any]], # Stage 3 mappings
    output_dir: Path,                      # IaC root directory
    progress_callback: Optional[Callable]
) -> DeploymentWrapperResult
```

**Workflow**:
1. Load Phase 1 analysis data (JSON)
2. Generate naming module (Step 1)
3. Generate deployment template (Step 2)
4. Save all files to disk
5. Return result with file metadata

---

## Instructions Structure (YAML)

### File: `iac_agent_instructions.yaml`

#### Section: `deployment_wrapper_agent`

**Location**: Lines 4595-7000+ (2400+ lines of instructions)

#### Subsections

1. **terraform_instructions** (Lines 4600-6200)
   - Mission and scope definition
   - Phase 1 recommendation application rules
   - Naming module generation (400+ lines)
   - Environment template generation
   - DevOps integration patterns

2. **bicep_instructions** (Lines 6200-7000+)
   - Bicep-specific syntax patterns
   - Module calls with Bicep syntax
   - Parameter file generation
   - Bicep backend configuration

---

## Naming Module Generation

### Research-Driven Approach

The agent performs **live research** for each naming module generation:

#### Step 1: CAF Abbreviations Research
```
Bing Search: "Microsoft Cloud Adoption Framework abbreviate recommend site:learn.microsoft.com"
MS Learn MCP: "Azure resource naming and tagging decision guide"
```

**Extracts**: Official CAF abbreviations for all detected services
- `rg` = Resource Group
- `st` = Storage Account
- `kv` = Key Vault
- `cog` = Cognitive Services
- `cosmos` = Cosmos DB
- etc.

#### Step 2: Service Naming Constraints Research

For **EACH** service detected in Phase 1:
```
Bing Search: "{service} naming rules constraints site:learn.microsoft.com"
Example: "storage account naming rules constraints site:learn.microsoft.com"
```

**Extracts**:
- Min/max length
- Allowed characters
- Case sensitivity
- Global vs resource group uniqueness
- Validation patterns

#### Step 3: Phase 1 Constraint Extraction

From `architecture_analysis.json`:
```json
{
  "recommendations": {
    "naming_constraints": [
      {
        "resource_type": "Microsoft.Storage/storageAccounts",
        "constraints": {
          "min_length": 3,
          "max_length": 24,
          "allowed_chars": "lowercase alphanumeric",
          "pattern": "^[a-z0-9]{3,24}$",
          "globally_unique": true
        }
      }
    ]
  }
}
```

### Naming Module Structure

#### `modules/naming/main.tf` (Terraform)

```hcl
# CAF abbreviations (research-based)
locals {
  abbreviations = {
    "storage_account"    = "st"
    "key_vault"          = "kv"
    "cognitive_services" = "cog"
    # ... ALL detected services
  }
  
  environment_abbr = {
    "development" = "dev"
    "staging"     = "stg"
    "production"  = "prd"
  }
  
  location_abbr = {
    "eastus"  = "eus"
    "westus2" = "wus2"
    # ... ALL Azure regions
  }
  
  # Base naming patterns
  base_name = "${var.workload_name}-${local.env_abbr}-${local.loc_abbr}"
  base_name_alphanum = "${local.workload_clean}${local.env_abbr}${local.loc_abbr}"
}

# Outputs with constraint enforcement
output "storage_account_name" {
  # Constraint: 3-24 chars, lowercase alphanumeric ONLY, globally unique
  value = substr(
    lower(replace("${local.abbreviations["storage_account"]}${local.base_name_alphanum}${var.resource_suffix}", "/[^a-z0-9]/", "")),
    0,
    24
  )
  description = <<-EOT
    Storage Account name
    Constraints: 3-24 chars, lowercase alphanumeric ONLY (no hyphens)
    Uniqueness: GLOBAL - Must be unique across ALL Azure
    CLI Check: az storage account check-name --name <name>
  EOT
}

output "key_vault_name" {
  # Constraint: 3-24 chars, alphanumeric + hyphens, globally unique
  value = substr("${local.abbreviations["key_vault"]}-${local.base_name}${var.resource_suffix}", 0, 24)
  description = <<-EOT
    Key Vault name
    Constraints: 3-24 chars, alphanumeric and hyphens
    Uniqueness: GLOBAL - Must be unique across ALL Azure
  EOT
}

# ... outputs for ALL detected services
```

#### Input Validation

```hcl
variable "workload_name" {
  type        = string
  description = "Workload or application name (2-10 chars, alphanumeric)"
  validation {
    condition     = can(regex("^[a-z0-9]{2,10}$", var.workload_name))
    error_message = "Workload name must be 2-10 characters, lowercase alphanumeric only."
  }
}

variable "environment" {
  type        = string
  description = "Environment name"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be: development, staging, or production."
  }
}

variable "resource_suffix" {
  type        = string
  description = "Optional suffix for global uniqueness (e.g., random 4 chars)"
  default     = ""
}
```

### Uniqueness Validation Script

The naming module generates a **standalone validation script** (`validate-names.ps1` or `validate-names.sh`) that works with **BOTH** Terraform and Bicep:

```powershell
# validate-names.ps1
# Tests GLOBAL uniqueness for services that require it

param(
    [Parameter(Mandatory=$true)]
    [string]$WorkloadName,
    
    [Parameter(Mandatory=$true)]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [string]$Location,
    
    [string]$ResourceSuffix = ""
)

# Build names using same logic as naming module
$storageAccountName = "st${workloadName}${envAbbr}${locAbbr}${resourceSuffix}"
$keyVaultName = "kv-${workloadName}-${envAbbr}-${locAbbr}${resourceSuffix}"

# Check global uniqueness
Write-Host "Checking Storage Account: $storageAccountName"
az storage account check-name --name $storageAccountName

Write-Host "Checking Key Vault: $keyVaultName"
$kvExists = az keyvault list --query "[?name=='$keyVaultName']" | ConvertFrom-Json
if ($kvExists.Count -gt 0) {
    Write-Error "Key Vault name already exists!"
} else {
    Write-Success "Key Vault name available"
}

# ... check ALL globally unique services
```

**Usage**:
```bash
# Before deploying
./validate-names.ps1 -WorkloadName "contoso" -Environment "dev" -Location "eastus" -ResourceSuffix "abc1"
```

---

## Deployment Template Generation

### Phase 1 Recommendation Application

#### Security Recommendations (from `rbac_assignments.json`)

**Applied in deployment template**:

```hcl
# Extract from Phase 1
locals {
  # RBAC assignments from Phase 1
  rbac_recommendations = jsondecode(file("../outputs/phase1/rbac_assignments.json"))
  
  # Security configurations from Phase 1
  security_config = {
    enable_managed_identity = true  # Phase 1 recommendation
    disable_local_auth      = true  # Phase 1 recommendation
    enable_cmk_encryption   = true  # Phase 1 recommendation if recommended
  }
}

# Call Stage 4 module with security settings
module "cognitive_services" {
  source = "../modules/cognitive-services-account"
  
  name                = module.naming.cognitive_services_account_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  
  # Apply Phase 1 security recommendations
  managed_identities = {
    system_assigned = local.security_config.enable_managed_identity
  }
  
  disable_local_auth = local.security_config.disable_local_auth
  
  # Apply Phase 1 CMK if recommended
  customer_managed_key = local.security_config.enable_cmk_encryption ? {
    key_vault_key_id          = azurerm_key_vault_key.cmk.id
    user_assigned_identity_id = azurerm_user_assigned_identity.cmk.id
  } : null
  
  # Apply Phase 1 RBAC assignments
  role_assignments = local.rbac_recommendations.cognitive_services_assignments
}
```

#### Network Recommendations (from `network_flows.json`, `private_endpoints.json`)

```hcl
# Extract from Phase 1
locals {
  network_config = jsondecode(file("../outputs/phase1/network_flows.json"))
  private_endpoints = jsondecode(file("../outputs/phase1/private_endpoints.json"))
}

module "cognitive_services" {
  source = "../modules/cognitive-services-account"
  
  # ... other config
  
  # Apply Phase 1 network isolation
  public_network_access_enabled = false  # Phase 1 recommendation
  
  # Apply Phase 1 private endpoint recommendations
  private_endpoints = {
    for pe in local.private_endpoints.cognitive_services :
    pe.name => {
      subnet_id                     = azurerm_subnet.private_endpoints.id
      subresource_names             = ["account"]
      private_dns_zone_ids          = [azurerm_private_dns_zone.cognitive_services.id]
      application_security_group_ids = pe.asg_ids
    }
  }
}
```

#### Monitoring Recommendations

```hcl
# Apply Phase 1 monitoring recommendations
module "cognitive_services" {
  source = "../modules/cognitive-services-account"
  
  # ... other config
  
  diagnostic_settings = {
    default = {
      log_analytics_workspace_id = azurerm_log_analytics_workspace.central.id
      
      # Phase 1 recommended log categories
      log_categories = [
        "Audit",
        "RequestResponse",
        "Trace"
      ]
      
      # Phase 1 recommended metrics
      metric_categories = [
        "AllMetrics"
      ]
    }
  }
}
```

### Environment-Specific Configuration

The deployment template uses **parameters** to differentiate environments:

```hcl
# variables.tf
variable "environment" {
  type        = string
  description = "Environment name: development, staging, production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be: development, staging, or production."
  }
}

variable "sku_tier" {
  type        = string
  description = "SKU tier based on WAF guidance per environment"
  default     = null  # Computed based on environment
}

# locals.tf
locals {
  # WAF-recommended SKUs per environment
  environment_skus = {
    development = {
      cognitive_services = "S0"
      storage_account    = "Standard_LRS"
      key_vault          = "standard"
    }
    staging = {
      cognitive_services = "S0"
      storage_account    = "Standard_ZRS"
      key_vault          = "standard"
    }
    production = {
      cognitive_services = "S1"
      storage_account    = "Standard_GRS"
      key_vault          = "premium"
    }
  }
  
  selected_skus = local.environment_skus[var.environment]
}

# Module call with environment-specific SKU
module "cognitive_services" {
  source = "../modules/cognitive-services-account"
  
  sku_name = local.selected_skus.cognitive_services
  # ... other config
}
```

### Example Parameter Files

#### `terraform.tfvars.example` (Terraform)

```hcl
# ============================================================================
# Required User Inputs
# ============================================================================
# Copy this file to terraform.tfvars and fill in the values

# Azure Configuration
subscription_id = "00000000-0000-0000-0000-000000000000"  # Your Azure subscription ID
location        = "eastus"                                 # Azure region

# Environment Configuration
environment     = "development"  # Options: development, staging, production
workload_name   = "contoso"      # Your workload/app name (2-10 chars, alphanumeric)

# Naming Configuration
resource_suffix = "abc1"  # Optional: 4-char suffix for global uniqueness

# Network Configuration
vnet_address_space         = ["10.0.0.0/16"]
subnet_address_prefixes    = {
  services         = ["10.0.1.0/24"]
  private_endpoints = ["10.0.2.0/24"]
}

# Security Configuration
enable_private_endpoints = true   # Recommended for production
enable_cmk_encryption    = false  # Optional: Customer-managed keys

# Monitoring Configuration
log_analytics_workspace_id = "/subscriptions/.../resourceGroups/.../providers/Microsoft.OperationalInsights/workspaces/..."

# Tags
tags = {
  Environment = "Development"
  CostCenter  = "IT"
  Owner       = "team@contoso.com"
}
```

#### `main.bicepparam.example` (Bicep)

```bicep
using './main.bicep'

// ============================================================================
// Required User Inputs
// ============================================================================
// Copy this file to main.bicepparam and fill in the values

// Azure Configuration
param location = 'eastus'

// Environment Configuration
param environment = 'development'  // Options: development, staging, production
param workloadName = 'contoso'     // Your workload/app name (2-10 chars)

// Naming Configuration
param resourceSuffix = 'abc1'  // Optional: 4-char suffix for global uniqueness

// Network Configuration
param vnetAddressSpace = ['10.0.0.0/16']
param subnetAddressPrefixes = {
  services: ['10.0.1.0/24']
  privateEndpoints: ['10.0.2.0/24']
}

// Security Configuration
param enablePrivateEndpoints = true
param enableCmkEncryption = false

// Monitoring Configuration
param logAnalyticsWorkspaceId = '/subscriptions/.../resourceGroups/.../providers/Microsoft.OperationalInsights/workspaces/...'

// Tags
param tags = {
  Environment: 'Development'
  CostCenter: 'IT'
  Owner: 'team@contoso.com'
}
```

---

## Backend Configuration

### Terraform Backend (`backend.tf`)

```hcl
# backend.tf
# Remote state configuration for Terraform

terraform {
  backend "azurerm" {
    # Backend configuration is provided via backend config file or CLI
    # Example: terraform init -backend-config=backend.conf
    
    # Required values (provided at init):
    # resource_group_name  = "rg-terraform-state"
    # storage_account_name = "sttfstateXXXX"
    # container_name       = "tfstate"
    # key                  = "contoso-dev.tfstate"
  }
}
```

### Backend Config File (`backend.conf`)

```hcl
# backend.conf
# Terraform backend configuration for Azure Storage

resource_group_name  = "rg-terraform-state"
storage_account_name = "sttfstateeus001"
container_name       = "tfstate"
key                  = "contoso-dev.tfstate"

# Optional: Managed identity authentication
use_msi              = true
# OR: Use subscription ID + client ID
# subscription_id      = "00000000-0000-0000-0000-000000000000"
# tenant_id            = "00000000-0000-0000-0000-000000000000"
```

### Bicep Configuration File

Bicep doesn't have built-in state management like Terraform. The agent generates deployment scripts:

```powershell
# deploy.ps1
# Bicep deployment script with consistent parameters

param(
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$true)]
    [string]$Location,
    
    [Parameter(Mandatory=$true)]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [string]$WorkloadName,
    
    [string]$ResourceSuffix = ""
)

# Set subscription context
az account set --subscription $SubscriptionId

# Create resource group
$rgName = "rg-$WorkloadName-$Environment"
az group create --name $rgName --location $Location

# Deploy Bicep template
az deployment group create `
    --resource-group $rgName `
    --template-file main.bicep `
    --parameters main.bicepparam `
    --parameters environment=$Environment workloadName=$WorkloadName resourceSuffix=$ResourceSuffix
```

---

## Deployment README Generation

### Structure

```markdown
# {Workload} Deployment - {Environment}

Production-ready deployment orchestration generated by SynthForge.AI Phase 2.

## Architecture Overview

This deployment creates:
- {List of Stage 4 modules being called}
- Phase 1 security recommendations applied
- Phase 1 network isolation applied
- CAF-compliant naming
- Monitoring and diagnostic settings

## Prerequisites

- Azure subscription with appropriate permissions
- Terraform >= 1.6 (or Azure CLI for Bicep)
- Azure CLI authenticated
- Phase 1 architecture analysis completed

## Required User Inputs

Before deploying, you MUST provide:

### Azure Configuration
- `subscription_id`: Your Azure subscription ID
- `location`: Azure region (e.g., eastus, westus2)

### Environment Configuration
- `environment`: Environment name (development, staging, production)
- `workload_name`: Your workload/app name (2-10 chars, alphanumeric)

### Naming Configuration
- `resource_suffix`: Optional 4-char suffix for global uniqueness
  - **IMPORTANT**: Run `validate-names.ps1` before deployment to check uniqueness

### Network Configuration
- `vnet_address_space`: VNet CIDR ranges
- `subnet_address_prefixes`: Subnet configurations

### Security Configuration (Optional)
- `enable_private_endpoints`: Enable private endpoints (recommended for prod)
- `enable_cmk_encryption`: Customer-managed keys (optional)

### Monitoring Configuration
- `log_analytics_workspace_id`: Central Log Analytics workspace

## Deployment Steps

### Terraform

1. **Validate Names** (CRITICAL for globally unique resources):
   ```bash
   ./validate-names.ps1 -WorkloadName "contoso" -Environment "dev" -Location "eastus" -ResourceSuffix "abc1"
   ```

2. **Copy Example Parameters**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. **Edit Parameters**: Fill in required values in `terraform.tfvars`

4. **Initialize Backend**:
   ```bash
   terraform init -backend-config=backend.conf
   ```

5. **Plan Deployment**:
   ```bash
   terraform plan -out=tfplan
   ```

6. **Apply Deployment**:
   ```bash
   terraform apply tfplan
   ```

### Bicep

1. **Validate Names**:
   ```bash
   ./validate-names.ps1 -WorkloadName "contoso" -Environment "dev" -Location "eastus" -ResourceSuffix "abc1"
   ```

2. **Copy Example Parameters**:
   ```bash
   cp main.bicepparam.example main.bicepparam
   ```

3. **Edit Parameters**: Fill in required values in `main.bicepparam`

4. **Deploy**:
   ```bash
   az deployment group create \
     --resource-group rg-contoso-dev \
     --template-file main.bicep \
     --parameters main.bicepparam
   ```

## Phase 1 Recommendations Applied

### Security
- ✅ Managed identities enabled
- ✅ Local authentication disabled
- ✅ RBAC assignments applied
- ✅ Customer-managed keys (if enabled)

### Network
- ✅ Private endpoints configured
- ✅ Public access disabled
- ✅ VNet integration
- ✅ Private DNS zones

### Monitoring
- ✅ Diagnostic settings enabled
- ✅ Log Analytics integration
- ✅ Service-specific metrics

## Outputs

After successful deployment:
- `resource_group_id`: Resource group ID
- `service_endpoints`: All service endpoints
- `identity_principal_ids`: Managed identity IDs for RBAC
- `private_endpoint_ips`: Private IP addresses

## Troubleshooting

### Name Conflicts
If deployment fails with name already exists:
1. Run `validate-names.ps1` to check availability
2. Change `resource_suffix` to a different value
3. Re-run deployment

### Permission Errors
Ensure your Azure identity has:
- `Contributor` role on subscription or resource group
- `User Access Administrator` for RBAC assignments

### Network Errors
Verify:
- VNet address spaces don't overlap
- Subnets have sufficient IP addresses
- Private DNS zones are correctly configured

## References

- [Phase 1 Architecture Analysis](../outputs/phase1/architecture_analysis.json)
- [Stage 4 Reusable Modules](../modules/)
- [Naming Module Documentation](../modules/naming/README.md)
```

---

## Prompt Construction

### Naming Module Prompt

The agent builds prompts dynamically from Phase 1 data:

```python
def _build_naming_module_prompt(self, phase1_data: Dict[str, Any]) -> str:
    """Build prompt for naming module generation."""
    
    # Extract ALL resources from Phase 1
    resource_list = []
    resource_counts = {}
    
    for resource in phase1_data["architecture_analysis"].get("resources", []):
        resource_type = resource["resource_type"]
        arm_type = resource["arm_type"]
        
        resource_list.append({
            "type": resource_type,
            "arm_type": arm_type
        })
        
        if arm_type not in resource_counts:
            resource_counts[arm_type] = 0
        resource_counts[arm_type] += 1
    
    # Load template from YAML
    template = get_prompt_template("deployment_wrapper_naming_module")
    
    # Format with dynamic data
    return template.format(
        resource_section=json.dumps(resource_list, indent=2),
        resource_counts=json.dumps(resource_counts, indent=2),
        constraints_section=json.dumps(service_constraints, indent=2)
    )
```

### Environment Prompt

```python
def _build_environment_prompt(
    self,
    env_name: str,
    module_mappings: List[Dict[str, Any]],
    phase1_data: Dict[str, Any],
    naming_module_available: bool,
    iac_format: str,
) -> str:
    """Build prompt for environment generation."""
    
    # Extract Phase 1 recommendations
    security_recs = phase1_data.get("rbac_assignments", {})
    network_recs = phase1_data.get("network_flows", {})
    monitoring_recs = phase1_data.get("monitoring_config", {})
    
    # Build module list section
    module_section = "## Stage 4 Modules to Call\n"
    for mapping in module_mappings:
        module_section += f"- {mapping['module_name']}: {mapping['folder_path']}\n"
    
    # Build recommendations section
    recs_section = f"""
## Phase 1 Recommendations to Apply

### Security Recommendations
{json.dumps(security_recs, indent=2)}

### Network Recommendations
{json.dumps(network_recs, indent=2)}

### Monitoring Recommendations
{json.dumps(monitoring_recs, indent=2)}
"""
    
    # Load template from YAML (terraform_instructions or bicep_instructions)
    if iac_format == "terraform":
        template = get_prompt_template("deployment_wrapper_environment_terraform")
    else:
        template = get_prompt_template("deployment_wrapper_environment_bicep")
    
    return template.format(
        env_name=env_name,
        module_section=module_section,
        recommendations_section=recs_section,
        naming_available="YES" if naming_module_available else "NO"
    )
```

---

## JSON Response Parsing

### Expected Output Format

The agent expects JSON responses with this structure:

```json
{
  "files": {
    "main.tf": "# File content here...",
    "variables.tf": "# File content here...",
    "outputs.tf": "# File content here...",
    "terraform.tfvars.example": "# File content here...",
    "backend.tf": "# File content here...",
    "providers.tf": "# File content here...",
    "README.md": "# File content here..."
  },
  "required_user_inputs": [
    {
      "name": "subscription_id",
      "description": "Azure subscription ID",
      "type": "string",
      "required": true
    },
    {
      "name": "location",
      "description": "Azure region",
      "type": "string",
      "required": true,
      "example": "eastus"
    }
  ],
  "phase1_recommendations_applied": {
    "security": [
      "Managed identities enabled",
      "Local authentication disabled",
      "RBAC assignments applied"
    ],
    "network": [
      "Private endpoints configured",
      "Public access disabled"
    ],
    "monitoring": [
      "Diagnostic settings enabled",
      "Log Analytics integration"
    ]
  }
}
```

### Parser Implementation

```python
def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
    """Parse JSON from agent response with fallback strategies."""
    
    # Strategy 1: Direct JSON parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code block
    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find JSON object in text
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # If all fail, raise error
    raise ValueError(f"Could not parse JSON from response")
```

---

## Key Insights

### 1. **Single Deployment Template (Not 3 Environments)**

**Changed in recent updates**: Instead of generating `dev/`, `staging/`, `prod/` folders, Stage 5 now generates a **single parameterized deployment** in `deployment/`:

- Users specify environment at deployment time via parameters
- Reduces code duplication
- Makes environment promotion easier
- Follows modern IaC best practices

### 2. **Naming Module is Stage 5 Responsibility**

The naming module is **NOT** generated in Stage 4 with other modules. It's generated in Stage 5 because:

- Requires knowledge of ALL services being deployed
- Needs Phase 1 constraint data
- Must validate global uniqueness
- Is deployment-specific (uses workload name)

### 3. **Phase 1 Recommendations are Applied Automatically**

The agent **automatically extracts and applies** Phase 1 recommendations:
- No manual translation required
- Security hardening from Phase 1
- Network isolation from Phase 1
- RBAC assignments from Phase 1
- Monitoring configuration from Phase 1

### 4. **Research-Driven Naming**

The naming module is **NOT** based on hardcoded templates. The agent:
- Researches CAF abbreviations live
- Researches service-specific constraints live
- Extracts Phase 1 constraint data
- Generates custom validation scripts

### 5. **DevOps-Ready Output**

All generated files are **production-ready**:
- Backend configuration for state management
- Example parameter files with documentation
- Validation scripts for uniqueness checks
- Comprehensive README with deployment steps

---

## Common Patterns

### Module Call Pattern (Terraform)

```hcl
module "cognitive_services" {
  source = "../modules/cognitive-services-account"  # Stage 4 module
  
  # Naming from naming module
  name                = module.naming.cognitive_services_account_name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  
  # Phase 1 security recommendations
  managed_identities = {
    system_assigned = true
  }
  disable_local_auth = true
  
  # Phase 1 network recommendations
  public_network_access_enabled = false
  private_endpoints = {
    default = {
      subnet_id            = azurerm_subnet.private_endpoints.id
      subresource_names    = ["account"]
      private_dns_zone_ids = [azurerm_private_dns_zone.cognitive_services.id]
    }
  }
  
  # Phase 1 monitoring recommendations
  diagnostic_settings = {
    default = {
      log_analytics_workspace_id = var.log_analytics_workspace_id
      log_categories             = ["Audit", "RequestResponse"]
      metric_categories          = ["AllMetrics"]
    }
  }
  
  # Phase 1 RBAC recommendations
  role_assignments = {
    contributor = {
      principal_id         = data.azurerm_client_config.current.object_id
      role_definition_name = "Cognitive Services Contributor"
    }
  }
  
  tags = var.tags
}
```

### Module Call Pattern (Bicep)

```bicep
module cognitiveServices '../modules/cognitive-services-account/main.bicep' = {
  name: 'cognitive-services-deployment'
  params: {
    // Naming from naming module
    name: naming.outputs.cognitiveServicesAccountName
    location: location
    
    // Phase 1 security recommendations
    managedIdentities: {
      systemAssigned: true
    }
    disableLocalAuth: true
    
    // Phase 1 network recommendations
    publicNetworkAccessEnabled: false
    privateEndpoints: {
      default: {
        subnetId: privateEndpointsSubnet.id
        subresourceNames: ['account']
        privateDnsZoneIds: [cognitiveServicesPrivateDnsZone.id]
      }
    }
    
    // Phase 1 monitoring recommendations
    diagnosticSettings: {
      default: {
        logAnalyticsWorkspaceId: logAnalyticsWorkspaceId
        logCategories: ['Audit', 'RequestResponse']
        metricCategories: ['AllMetrics']
      }
    }
    
    // Phase 1 RBAC recommendations
    roleAssignments: {
      contributor: {
        principalId: principalId
        roleDefinitionIdOrName: 'Cognitive Services Contributor'
      }
    }
    
    tags: tags
  }
}
```

---

## Summary

Stage 5 Deployment Wrapper generation is the **orchestration layer** that:

✅ **Calls Stage 4 modules** using relative paths  
✅ **Applies Phase 1 recommendations** automatically  
✅ **Generates CAF naming module** with live research  
✅ **Creates environment-parameterized templates** (single deployment, not 3 environments)  
✅ **Provides DevOps-ready configuration** (backend, parameters, validation)  
✅ **Documents all required inputs** clearly  

The agent uses **2400+ lines of instructions** in YAML, **live research** for naming constraints, and **dynamic prompt construction** from Phase 1 data to generate production-ready deployment orchestration.

---

*Generated: 2025*  
*Analysis based on: `deployment_wrapper_agent.py` and `iac_agent_instructions.yaml` (lines 4595-7000+)*

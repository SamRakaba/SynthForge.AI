# Quick Start: Using Stage 5 Deployment Wrappers

## What Stage 5 Generates

Stage 5 creates **environment-specific deployment orchestration** for your infrastructure:

```
iac-output/
  ├── modules/                    # Stage 4: Reusable modules
  │   ├── naming/                 # Stage 5: CAF naming module
  │   ├── cognitive-services-account/
  │   ├── storage-account/
  │   └── ...
  └── environments/               # Stage 5: Deployment wrappers
      ├── dev/                    # Development environment
      ├── staging/                # Staging environment
      └── prod/                   # Production environment
```

## Running the Full Pipeline

```bash
# Generate everything (Phase 1 + Phase 2 including Stage 5)
python main.py architecture.png --iac --iac-format terraform --output output/

# Or run Phase 2 only (if Phase 1 already completed)
python main.py --skip-phase1 --iac --iac-format terraform --output output/
```

## What Gets Created for Each Environment

### Naming Module (`modules/naming/`)
- **main.tf**: CAF abbreviations + naming logic
- **variables.tf**: `workload_name`, `environment`, `location`
- **outputs.tf**: Resource-specific name outputs
- **README.md**: Usage documentation

### Environment Folder (`environments/dev/`, `staging/`, `prod/`)
- **main.tf**: Orchestrates modules with environment-specific configs
- **variables.tf**: Input parameters (subscription, location, etc.)
- **outputs.tf**: Environment outputs (resource IDs, endpoints)
- **terraform.tfvars.example**: Example parameter values
- **backend.tf**: Remote state configuration
- **providers.tf**: Azure provider setup
- **README.md**: Deployment guide with required user inputs

## Deploying an Environment

### 1. Navigate to Environment
```bash
cd output/iac-output/environments/dev
```

### 2. Configure Parameters
```bash
# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required Values** (documented in README.md):
```hcl
# Azure Platform
subscription_id = "00000000-0000-0000-0000-000000000000"  # az account show --query id -o tsv
tenant_id       = "00000000-0000-0000-0000-000000000000"  # az account show --query tenantId -o tsv
location        = "eastus"                                # Azure region

# Naming
workload_name   = "contoso"                              # Your app name (2-10 chars)
environment     = "development"                          # development/staging/production

# Security (Phase 1 recommendations applied)
enable_private_endpoints = true                          # RECOMMENDED in Phase 1
public_network_access   = false                          # RECOMMENDED in Phase 1

# Networking (if private endpoints enabled)
virtual_network_id          = "/subscriptions/.../virtualNetworks/vnet-dev"
private_endpoint_subnet_id  = "/subscriptions/.../subnets/pe-subnet"
```

### 3. Initialize Terraform
```bash
terraform init
```

### 4. Preview Changes
```bash
terraform plan
```

### 5. Deploy
```bash
terraform apply
```

## Environment Differences

### Development
- **Purpose**: Testing, development, experimentation
- **SKUs**: Minimal (Basic, Standard) for cost optimization
- **Networking**: May allow public access for testing convenience
- **Monitoring**: Basic diagnostic settings
- **Example**: Cognitive Services S0, Storage Standard/LRS

### Staging
- **Purpose**: Pre-production testing, UAT
- **SKUs**: Production-like for accurate testing
- **Networking**: Private endpoints enabled, public access disabled
- **Monitoring**: Full diagnostic settings
- **Example**: Cognitive Services S0, Storage Standard/LRS, private endpoints

### Production
- **Purpose**: Live workloads, customer-facing
- **SKUs**: High availability (Premium where applicable)
- **Networking**: Private endpoints required, NO public access
- **Monitoring**: Comprehensive diagnostic settings + alerts
- **Backup**: Enabled with 35-day retention
- **Example**: Cognitive Services S0, Storage Premium/ZRS, private endpoints, soft delete, purge protection

## Phase 1 Recommendations Applied

Stage 5 **automatically applies** recommendations from Phase 1:

### Security
- ✅ Managed Identity enabled (SystemAssigned/UserAssigned)
- ✅ RBAC roles assigned per Phase 1 security analysis
- ✅ Least privilege access
- ✅ Customer-managed keys (if recommended)

### Networking
- ✅ Private endpoints for services marked in Phase 1
- ✅ Public network access disabled per recommendations
- ✅ VNet integration configured
- ✅ Private DNS zones for private endpoints

### Monitoring
- ✅ Diagnostic settings enabled for all services
- ✅ Central Log Analytics workspace
- ✅ Service-specific metrics

**Check `README.md` in each environment** for complete list of applied recommendations.

## Naming Convention (CAF-Compliant)

Stage 5 generates a `modules/naming/` module that produces CAF-compliant resource names:

**Pattern**: `{abbreviation}-{workload}-{environment}-{location}`

**Examples**:
- Resource Group: `rg-contoso-dev-eus`
- Storage Account: `stcontosodeveusXXXX` (no hyphens, max 24 chars)
- Key Vault: `kv-contoso-dev-eus` (max 24 chars)
- Cognitive Services: `cog-contoso-dev-eus`

**Abbreviations** (from Microsoft CAF):
- `rg` = Resource Group
- `st` = Storage Account
- `kv` = Key Vault
- `cog` = Cognitive Services
- `cosmos` = Cosmos DB
- `apim` = API Management
- `log` = Log Analytics Workspace

## Remote State Configuration

Each environment includes `backend.tf` for remote state:

```hcl
terraform {
  backend "azurerm" {
    # Configured via backend.tfvars or environment variables
  }
}
```

**Initialize with backend**:
```bash
terraform init -backend-config=backend.tfvars
```

**Example `backend.tfvars`**:
```hcl
resource_group_name  = "rg-terraform-state-dev"
storage_account_name = "sttfstatedev<unique>"
container_name       = "tfstate"
key                  = "contoso-dev.tfstate"
```

## Cost Estimation

Estimated monthly costs (as of implementation):

- **Development**: ~$50-100/month (minimal SKUs)
- **Staging**: ~$200-400/month (production-like SKUs)
- **Production**: ~$500-1000/month (high availability SKUs)

Use [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) for accurate estimates based on your specific services.

## Troubleshooting

### Terraform validate fails
```bash
# Ensure all module sources exist
ls -la ../../modules/

# Check syntax
terraform fmt -check -diff

# Validate
terraform validate
```

### Missing required variables
Check `README.md` for complete list of required inputs. All variables are documented with:
- Description
- Example value
- How to find the value

### Private endpoint errors
If using private endpoints:
1. VNet and subnet must exist before deployment
2. Subnet must have `privateEndpointNetworkPolicies` disabled
3. Private DNS zones must be created or referenced

## Next Steps

1. **Test deployment in dev environment**
2. **Verify Phase 1 recommendations applied** (check resources in Azure Portal)
3. **Validate naming conventions** (resources use CAF-compliant names)
4. **Promote to staging** after dev testing
5. **Deploy to production** with appropriate approvals

## Support

- **Phase 1 Analysis**: Review `output/architecture_analysis.json`
- **Phase 1 Recommendations**: Review environment `README.md` for applied recommendations
- **Module Documentation**: Check `modules/<service>/README.md` for module usage
- **Azure Documentation**: [Well-Architected Framework](https://learn.microsoft.com/azure/well-architected/)

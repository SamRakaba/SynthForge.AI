# Phase 2: Infrastructure as Code Generation - Prerequisites

## Overview

Phase 2 generates production-ready Infrastructure as Code (Terraform/Bicep) from your architecture design. Before deploying the generated modules, you'll need to provide platform-specific configuration.

**Note:** SynthForge.AI focuses on **module generation** based on your design. Platform-specific deployment configuration (naming conventions, tags, network addresses, etc.) is assumed to be handled by your existing deployment infrastructure.

---

## Required Platform Inputs (For Deployment)

The generated IaC modules will require the following inputs at deployment time:

### 1. **Azure Subscription & Resource Group**
- **Subscription ID**: Target Azure subscription
- **Resource Group**: Resource group name (or create new)
- **Location/Region**: Azure region (e.g., `eastus`, `westus2`)

```terraform
# Example: terraform.tfvars
subscription_id    = "12345678-1234-1234-1234-123456789012"
resource_group_name = "rg-myapp-prod"
location           = "eastus"
```

```bicep
// Example: parameters.json
{
  "location": { "value": "eastus" },
  "resourceGroupName": { "value": "rg-myapp-prod" }
}
```

---

### 2. **Naming Conventions**
- **Prefix**: Organizational prefix (e.g., `contoso`, `acme`)
- **Environment**: Environment name (e.g., `dev`, `test`, `prod`)
- **Application**: Application identifier (e.g., `myapp`, `api`)

**Generated modules will use variables for naming**, allowing you to apply your organization's naming conventions at deployment.

```terraform
# Example naming pattern: {prefix}-{app}-{environment}-{resource}
prefix      = "contoso"
environment = "prod"
application = "ai-platform"

# Results in: contoso-ai-platform-prod-openai, contoso-ai-platform-prod-vnet
```

---

### 3. **Network Configuration**
If your design includes virtual networks, private endpoints, or network security:

- **VNet Address Space**: CIDR range (e.g., `10.0.0.0/16`)
- **Subnet Ranges**: Subnet CIDRs (e.g., `10.0.1.0/24`, `10.0.2.0/24`)
- **DNS Servers**: Custom DNS servers (optional)
- **Network Security Rules**: Inbound/outbound rules (optional)

```terraform
# Example: network inputs
vnet_address_space    = ["10.0.0.0/16"]
app_subnet_cidr       = "10.0.1.0/24"
data_subnet_cidr      = "10.0.2.0/24"
enable_private_endpoint = true
```

---

### 4. **Tags (Metadata)**
Azure resource tags for governance, cost tracking, and organization:

```terraform
# Example: tags
tags = {
  Environment = "Production"
  Project     = "AI Platform"
  Owner       = "Platform Team"
  CostCenter  = "Engineering"
  ManagedBy   = "Terraform"
}
```

```bicep
// Example: Bicep tags parameter
param tags object = {
  Environment: 'Production'
  Project: 'AI Platform'
  Owner: 'Platform Team'
}
```

---

### 5. **Security Configuration**
For services with security requirements (managed identities, Key Vault, RBAC):

- **Managed Identity Type**: System-assigned or user-assigned
- **Key Vault Name**: For secrets/certificates (if using Key Vault)
- **RBAC Roles**: Azure AD principal IDs for role assignments

```terraform
# Example: security inputs
enable_system_identity = true
key_vault_name         = "kv-contoso-prod"
rbac_assignments = [
  {
    principal_id = "12345678-1234-1234-1234-123456789012"  # Azure AD User/Group/SP
    role         = "Cognitive Services OpenAI User"
  }
]
```

---

### 6. **Service-Specific Configuration**
Each service may have specific requirements:

#### Azure OpenAI
- **SKU**: `S0` (standard)
- **Models**: Model deployments (e.g., `gpt-4o`, `text-embedding-ada-002`)
- **Custom Subdomain**: Unique subdomain name

#### Azure Cosmos DB
- **Consistency Level**: `Session`, `Strong`, etc.
- **Throughput**: Autoscale or manual RU/s
- **Geo-replication**: Additional regions (optional)

#### Azure Kubernetes Service (AKS)
- **Node Pool Size**: VM size and count
- **Kubernetes Version**: Target version
- **Network Plugin**: Azure CNI or kubenet

**Generated modules will expose these as variables with sensible defaults.**

---

## Deployment Prerequisites Summary

| Category | Required Inputs | Example |
|----------|----------------|---------|
| **Subscription** | Subscription ID, Resource Group, Location | `eastus`, `rg-myapp-prod` |
| **Naming** | Prefix, Environment, Application | `contoso-prod-ai` |
| **Network** | VNet CIDR, Subnet CIDRs, DNS | `10.0.0.0/16`, `10.0.1.0/24` |
| **Tags** | Environment, Project, Owner, CostCenter | `Production`, `AI Platform` |
| **Security** | Managed Identity, Key Vault, RBAC | System-assigned, `kv-contoso-prod` |
| **Service Config** | SKU, Models, Features | `S0`, `gpt-4o`, autoscale |

---

## How Generated Modules Handle These Inputs

### Terraform Modules
Each module includes `variables.tf` with all required inputs:

```terraform
# variables.tf (generated)
variable "name" {
  description = "Resource name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint"
  type        = bool
  default     = false
}
```

You provide values via `terraform.tfvars` or environment variables.

### Bicep Modules
Each module includes parameters with decorators:

```bicep
// main.bicep (generated)
@description('Resource name')
param name string

@description('Azure region')
param location string = resourceGroup().location

@description('Resource tags')
param tags object = {}

@description('Enable private endpoint')
param enablePrivateEndpoint bool = false
```

You provide values via `parameters.json` or command-line args.

---

## Recommended Deployment Workflow

1. **Phase 1**: Extract design (SynthForge.AI generates `./output/*.json`)
2. **Phase 2**: Generate IaC modules (SynthForge.AI generates `./iac/terraform/` or `./iac/bicep/`)
3. **Review Generated Modules**: Check variables and configurations
4. **Prepare Deployment Config**: Create `terraform.tfvars` or `parameters.json` with your platform inputs
5. **Deploy**:
   - **Terraform**: `terraform init`, `terraform plan`, `terraform apply`
   - **Bicep**: `az deployment group create --template-file main.bicep --parameters parameters.json`

---

## Example: End-to-End Deployment

### Generated Module Structure (Terraform)
```
iac/terraform/
├── openai-service/
│   ├── main.tf          # Resource definitions
│   ├── variables.tf     # Required inputs
│   └── outputs.tf       # Exported values
├── cosmos-db/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
└── vnet/
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```

### Your Deployment Configuration
```terraform
# terraform.tfvars (you create this)
prefix              = "contoso"
environment         = "prod"
location            = "eastus"
resource_group_name = "rg-contoso-prod"

vnet_address_space = ["10.0.0.0/16"]
app_subnet_cidr    = "10.0.1.0/24"

tags = {
  Environment = "Production"
  Project     = "AI Platform"
  Owner       = "Platform Team"
}
```

### Deploy
```bash
cd iac/terraform/
terraform init
terraform plan -var-file="../../terraform.tfvars"
terraform apply -var-file="../../terraform.tfvars"
```

---

## Best Practices

1. **Use Variable Files**: Keep platform config in `terraform.tfvars` or `parameters.json`, not hardcoded
2. **Version Control**: Store deployment config separately from generated modules
3. **Environments**: Use workspaces (Terraform) or separate parameter files (Bicep) for dev/test/prod
4. **State Management**: Use remote state (Azure Storage, Terraform Cloud) for team collaboration
5. **Validation**: Run `terraform validate` or `az bicep build` before deployment
6. **Secrets**: Never commit secrets to version control - use Azure Key Vault or environment variables

---

## Support for Platform Input Collection (Future)

**Current Approach**: Assumes you have existing deployment infrastructure and can provide platform inputs manually.

**Future Enhancement**: SynthForge.AI could add an interactive platform configuration wizard (Stage 4.5) to collect these inputs and generate `terraform.tfvars` or `parameters.json` automatically.

For now, the focus is on **generating high-quality, parameterized modules** that integrate with your existing deployment processes.

---

## Questions?

If you encounter issues with deployment or need help adapting modules to your platform:
1. Check generated `variables.tf` / parameters in Bicep files for required inputs
2. Review Azure documentation for service-specific configuration
3. Use Bing Grounding / MS Learn MCP to search for best practices
4. Refer to Azure Verified Modules (AVM) examples: https://aka.ms/avm

Generated modules follow industry best practices and are designed to be deployment-ready with minimal customization.

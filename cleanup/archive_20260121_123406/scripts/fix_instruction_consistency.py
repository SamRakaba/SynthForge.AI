"""
Priority 1: Fix Bicep Deployment Wrapper placeholder
Priority 2: Add explicit MCP tool usage to 4 agents
"""

import re

yaml_file = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\iac_agent_instructions.yaml"

with open(yaml_file, 'r', encoding='utf-8') as f:
    content = f.read()

fixes_applied = []

# ============================================================================
# FIX 1: Replace Bicep Deployment Wrapper placeholder
# ============================================================================
bicep_placeholder = r'\[Similar structure to Terraform, adapted for Bicep syntax with \.bicep and \.bicepparam files\]'

bicep_instructions = """You are a DeploymentWrapperAgent specialized in generating production-ready Bicep deployment orchestration following Azure DevOps best practices.

## Your Mission
Generate deployment wrapper that:
1. Orchestrates reusable Bicep modules from Stage 4
2. Applies Phase 1 security/network/RBAC recommendations  
3. Generates CAF-compliant naming modules
4. Follows WAF sizing guidance per environment
5. Creates DevOps-ready parameter files
6. Documents all required user inputs

## CRITICAL: Consult DevOps Best Practices FIRST
BEFORE generating any code, use mcp_bicep_experim_get_bicep_best_practices to consult Bicep best practices for:
- File organization patterns
- Module composition
- Parameter management
- Naming conventions
- DevOps integration

Apply discovered patterns dynamically - DO NOT hardcode all structures.

## Output Structure
Generate deployment/ folder with:
- main.bicep - Entry point, resource group, naming modules, module orchestration
- infrastructure.bicep - Core infrastructure (ACR, Event Hub, etc.) if applicable
- applications.bicep - Application resources if applicable
- databases.bicep - Data platform if applicable
- security.bicep - RBAC, private endpoints if applicable
- parameters.bicep - Input parameters with environment validation
- outputs.bicep - Important outputs
- parameters.dev.json - Development parameter values
- parameters.staging.json - Staging parameter values  
- parameters.prod.json - Production parameter values
- README.md - Deployment guide

## Key Principles
1. **Multiple Naming Modules**: Instantiate per workload/location if services span multiple areas
2. **File Separation**: Organize by logical concern (infrastructure, applications, databases, security)
3. **Configuration Objects**: Use variables for reusable network/DNS/tag configuration
4. **Environment Logic**: Single template with environment parameter driving SKU/HA/retention
5. **Module Composition**: Reference modules with relative paths: '../../modules/{name}/main.bicep'
6. **Dynamic Generation**: Generate only files needed based on detected services

## Response Format
Return JSON with deployment wrapper details and all generated files."""

if re.search(bicep_placeholder, content):
    content = re.sub(bicep_placeholder, bicep_instructions, content)
    fixes_applied.append("✅ Fixed Bicep Deployment Wrapper (replaced placeholder)")
else:
    fixes_applied.append("⚠️ Bicep placeholder not found or already fixed")

# ============================================================================
# FIX 2: Add MCP tool usage to Filter Agent
# ============================================================================
filter_pattern = r'(filter_agent:.*?instructions: \|)(.*?)(response_format:)'

def add_mcp_to_filter(match):
    header = match.group(1)
    existing = match.group(2)
    footer = match.group(3)
    
    # Check if MCP already mentioned
    if 'MCP' in existing or 'mcp_' in existing:
        return match.group(0)  # Already has MCP
    
    mcp_addition = """
    
    ## Tool Usage
    Use MCP Azure documentation tools to validate Azure service types, resource classifications, 
    and architectural patterns. Consult documentation to distinguish between architectural resources
    (VMs, databases, networks) and non-architectural elements (icons, labels, decorations).
    """
    
    return header + existing + mcp_addition + "\n\n    " + footer

if re.search(filter_pattern, content, re.DOTALL):
    content = re.sub(filter_pattern, add_mcp_to_filter, content, flags=re.DOTALL)
    fixes_applied.append("✅ Added MCP tool usage to Filter Agent")
else:
    fixes_applied.append("⚠️ Filter Agent pattern not found")

# ============================================================================
# FIX 3: Add MCP tool usage to Network Flow Agent
# ============================================================================
network_pattern = r'(network_flow_agent:.*?instructions: \|)(.*?)(response_format:)'

def add_mcp_to_network(match):
    header = match.group(1)
    existing = match.group(2)
    footer = match.group(3)
    
    if 'Use MCP' in existing or 'use mcp_' in existing.lower():
        return match.group(0)
    
    mcp_addition = """
    
    ## Tool Usage
    Use MCP tools to consult Azure networking best practices, VNET design patterns, and security group configurations.
    Ground network flow analysis in official Azure networking documentation.
    """
    
    return header + existing + mcp_addition + "\n\n    " + footer

if re.search(network_pattern, content, re.DOTALL):
    content = re.sub(network_pattern, add_mcp_to_network, content, flags=re.DOTALL)
    fixes_applied.append("✅ Added MCP tool usage to Network Flow Agent")
else:
    fixes_applied.append("⚠️ Network Flow Agent pattern not found")

# ============================================================================
# FIX 4: Add MCP tool usage to Service Analysis Agent
# ============================================================================
service_pattern = r'(service_analysis_agent:.*?instructions: \|)(.*?)(response_format:)'

def add_mcp_to_service(match):
    header = match.group(1)
    existing = match.group(2)
    footer = match.group(3)
    
    if 'Use MCP' in existing or 'use mcp_' in existing.lower():
        return match.group(0)
    
    mcp_addition = """
    
    ## Tool Usage
    Use MCP Azure documentation tools to validate service configurations, dependencies, and required settings.
    Consult official Azure service documentation when analyzing services and their parameters.
    """
    
    return header + existing + mcp_addition + "\n\n    " + footer

if re.search(service_pattern, content, re.DOTALL):
    content = re.sub(service_pattern, add_mcp_to_service, content, flags=re.DOTALL)
    fixes_applied.append("✅ Added MCP tool usage to Service Analysis Agent")
else:
    fixes_applied.append("⚠️ Service Analysis Agent pattern not found")

# ============================================================================
# FIX 5: Add MCP tool usage to Vision Agent (in agent_instructions.yaml)
# ============================================================================
# This is in a different file - will handle separately

# Write updated YAML
with open(yaml_file, 'w', encoding='utf-8') as f:
    f.write(content)

# Report results
print("\n" + "="*70)
print("INSTRUCTION CONSISTENCY FIXES APPLIED")
print("="*70)
for fix in fixes_applied:
    print(fix)

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"✅ Fixed {len([f for f in fixes_applied if '✅' in f])} issues")
print(f"⚠️  {len([f for f in fixes_applied if '⚠️' in f])} items need manual review")
print("\nNext: Fix Vision Agent in agent_instructions.yaml")

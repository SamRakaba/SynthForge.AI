"""
Add concise DevOps consultation instructions to iac_agent_instructions.yaml
"""
import yaml
import re

yaml_file = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\iac_agent_instructions.yaml"

# Read YAML as text (too large for yaml.safe_load)
with open(yaml_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Concise instructions to add at the END of terraform_instructions and bicep_instructions
concise_instructions = """

## CRITICAL: Consult IaC DevOps Best Practices Before Generation

Before generating deployment wrapper code, you MUST:

1. **Use available MCP tools**:
   - Terraform: Use `mcp_hashicorp_ter_*` tools for Terraform best practices
   - Bicep: Use `mcp_bicep_experim_get_bicep_best_practices` for Bicep best practices
   - Consult documentation for latest patterns

2. **Apply enterprise-grade patterns discovered from tools**:
   - **Multiple naming modules** if services span workloads/locations (NOT single global)
   - **Separate files by concern** (infrastructure, applications, databases, security) 
   - **Configuration objects** (network_config, dns_config, common_tags)
   - **Single parameterized template** with environment logic
   - **Generate only needed files** based on detected services

3. **Module composition**: Use relative paths `../../modules/{name}`, pass config objects

4. **Document**: Create README with deployment order if multiple layers exist

Key: DO NOT hardcode structure - consult tools and apply discovered best practices dynamically.
"""

# Check if already added
if "Consult IaC DevOps Best Practices" in content:
    print("✓ Instructions already present in YAML")
else:
    # Find terraform_instructions section and add before the next major section
    # Look for patterns like:
    # terraform_instructions: |
    #   ...content...
    # bicep_instructions: |
    
    # Simple approach: add to the end of the file with clear section marker
    if not content.endswith('\n'):
        content += '\n'
    
    content += f"""
# ==============================================================================
# DEPLOYMENT WRAPPER - DEVOPS BEST PRACTICES CONSULTATION
# ==============================================================================
# These instructions tell agents to CONSULT available tools for best practices
# rather than hardcoding patterns. Agents should use MCP servers, documentation
# tools, and apply discovered patterns dynamically.
# ==============================================================================

deployment_wrapper_devops_consultation: |
{concise_instructions}
"""
    
    # Write back
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Added concise DevOps consultation instructions to YAML")
    print("   - Instructs agent to use MCP tools (Terraform, Bicep best practices)")
    print("   - Provides key principles without hardcoding patterns")
    print("   - Enables dynamic best practice discovery")

"""
Final simple implementation - add consultation constant
"""

file_path = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\__init__.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check if already added
if any('DEVOPS_CONSULTATION' in line for line in lines):
    print("✓ Already added")
    exit(0)

# Find import section end (after from pathlib import Path)
insert_point = None
for i, line in enumerate(lines):
    if 'from typing import Any' in line or 'from functools import lru_cache' in line:
        insert_point = i + 2  # After imports
        break

if insert_point is None:
    print("ERROR: Could not find insertion point")
    exit(1)

# Add the consultation constant
consultation_constant = '''
# Concise instructions for deployment wrapper to consult DevOps best practices
DEVOPS_CONSULTATION = """

## Generate Production-Grade Deployment Wrapper

Consult available tools for best practices BEFORE generating code:
1. **Use MCP tools**: mcp_hashicorp_ter_* (Terraform) or mcp_bicep_experim_get_bicep_best_practices (Bicep)
2. **Apply discovered patterns**:
   - Multiple naming modules for different workloads/locations (NOT single global)
   - Separate files by concern (infrastructure, applications, databases, security)
   - Configuration objects (network_config, dns_config, common_tags)
   - Single parameterized template with environment logic
   - Dynamic file generation based on detected services
3. **Use relative module paths**: ../../modules/{name}
4. **Document deployment order** in README

Consult tools dynamically - DO NOT hardcode all patterns.
"""

'''

lines.insert(insert_point, consultation_constant)

# Now find and update get_deployment_wrapper_agent_instructions
for i, line in enumerate(lines):
    if 'def get_deployment_wrapper_agent_instructions' in line:
        # Find the return statement
        for j in range(i, min(i + 20, len(lines))):
            if 'return base_instructions' in lines[j]:
                # Update to append consultation
                lines[j] = lines[j].replace(
                    'return base_instructions',
                    'return base_instructions + DEVOPS_CONSULTATION'
                )
                break
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Added DEVOPS_CONSULTATION constant")
print("✅ Updated function to append consultation instructions")
print("   - Agent will consult MCP tools for best practices")
print("   - No hardcoded patterns")
print("   - Concise and precise instructions")

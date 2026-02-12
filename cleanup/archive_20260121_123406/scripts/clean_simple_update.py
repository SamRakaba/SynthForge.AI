"""
Clean, simple implementation of DevOps consultation
"""

file_path = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\__init__.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add constant after imports
constant_to_add = '''

# ============================================================================
# DevOps Best Practices Consultation Instructions
# Tells deployment wrapper agent to consult MCP tools for best practices
# ============================================================================
DEVOPS_CONSULTATION = """

## Generate Production-Grade Deployment Wrapper

Consult available tools BEFORE generating code:
1. **Use MCP tools**: mcp_hashicorp_ter_* (Terraform) or mcp_bicep_experim_get_bicep_best_practices (Bicep)
2. **Apply patterns**: Multiple naming modules, separate files by concern, configuration objects, environment parameterization
3. **Dynamic generation**: Generate only needed files based on detected services

Consult tools dynamically - DO NOT hardcode all files.
"""
'''

# Find where to insert (after imports, before first @lru_cache or def)
import re
insertion_pattern = r'(from functools import lru_cache.*?\n\n)'
if re.search(insertion_pattern, content):
    content = re.sub(insertion_pattern, r'\1' + constant_to_add + '\n', content, count=1)
    print("✓ Added DEVOPS_CONSULTATION constant")
else:
    print("ERROR: Could not find insertion point")
    exit(1)

# 2. Update get_deployment_wrapper_agent_instructions to append constant
old_function = r'(def get_deployment_wrapper_agent_instructions\(iac_format: str = "terraform"\) -> str:.*?""".*?""")\s+(instructions_data = load_iac_instructions\(\))\s+(agent_config = instructions_data\.get\("deployment_wrapper_agent", \{\}\))\s+(if iac_format\.lower\(\) == "bicep":)\s+(return agent_config\.get\("bicep_instructions", ""\))\s+(else:)\s+(return agent_config\.get\("terraform_instructions", ""\))'

new_function = r'''\1
    instructions_data = load_iac_instructions()
    agent_config = instructions_data.get("deployment_wrapper_agent", {})
    
    if iac_format.lower() == "bicep":
        return agent_config.get("bicep_instructions", "") + DEVOPS_CONSULTATION
    else:
        return agent_config.get("terraform_instructions", "") + DEVOPS_CONSULTATION'''

if re.search(old_function, content, re.DOTALL):
    content = re.sub(old_function, new_function, content, flags=re.DOTALL)
    print("✓ Updated function to append DEVOPS_CONSULTATION")
else:
    print("ERROR: Could not find function pattern")
    exit(1)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ SUCCESS")
print("   - Added concise consultation instructions")
print("   - Agent will use MCP tools for best practices")
print("   - No hardcoded patterns")

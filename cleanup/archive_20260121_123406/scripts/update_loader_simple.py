"""
Update prompts loader to include DevOps consultation instructions
"""

file_path = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\__init__.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find get_deployment_wrapper_agent_instructions function
import re

# Check if already updated
if 'deployment_wrapper_devops_consultation' in content:
    print("✓ Function already updated")
    exit(0)

# Find and update the function
old_pattern = r'(def get_deployment_wrapper_agent_instructions\(iac_format: str = "terraform"\) -> str:.*?""".*?""")\s+(instructions_data = load_iac_instructions\(\))\s+(agent_config = instructions_data\.get\("deployment_wrapper_agent", \{\}\))\s+(if iac_format\.lower\(\) == "bicep":)\s+(return agent_config\.get\("bicep_instructions", ""\))\s+(else:)\s+(return agent_config\.get\("terraform_instructions", ""\))'

new_function = r'''\1
    instructions_data = load_iac_instructions()
    agent_config = instructions_data.get("deployment_wrapper_agent", {})
    
    # Get base instructions
    if iac_format.lower() == "bicep":
        base_instructions = agent_config.get("bicep_instructions", "")
    else:
        base_instructions = agent_config.get("terraform_instructions", "")
    
    # Append DevOps consultation instructions (tells agent to use MCP tools)
    devops_consultation = instructions_data.get("deployment_wrapper_devops_consultation", "")
    if devops_consultation:
        return f"{base_instructions}\n\n{devops_consultation}"
    
    return base_instructions'''

content = re.sub(old_pattern, new_function, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated prompts loader to include DevOps consultation instructions")
print("   - Agent will be instructed to use MCP tools")
print("   - No hardcoded patterns")
print("   - Dynamic best practice discovery")

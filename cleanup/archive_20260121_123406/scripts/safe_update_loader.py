"""
Safely update prompts loader - proper Python syntax
"""

file_path = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\__init__.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the get_deployment_wrapper_agent_instructions function
func_start = None
for i, line in enumerate(lines):
    if 'def get_deployment_wrapper_agent_instructions' in line:
        func_start = i
        break

if func_start is None:
    print("ERROR: Function not found")
    exit(1)

# Find the return statements (should be around line +12 to +15)
replaced = False
for i in range(func_start, min(func_start + 20, len(lines))):
    if 'if iac_format.lower() == "bicep":' in lines[i]:
        # Found the conditional - replace the next 4 lines
        indent = '    '
        new_code = [
            f'{indent}# Get base instructions\n',
            f'{indent}if iac_format.lower() == "bicep":\n',
            f'{indent}    base_instructions = agent_config.get("bicep_instructions", "")\n',
            f'{indent}else:\n',
            f'{indent}    base_instructions = agent_config.get("terraform_instructions", "")\n',
            f'{indent}\n',
            f'{indent}# Append DevOps consultation (instructs agent to use MCP tools)\n',
            f'{indent}devops_consultation = instructions_data.get("deployment_wrapper_devops_consultation", "")\n',
            f'{indent}if devops_consultation:\n',
            f'{indent}    return base_instructions + "\\n\\n" + devops_consultation\n',
            f'{indent}\n',
            f'{indent}return base_instructions\n'
        ]
        
        # Replace old return logic
        # Remove the old if/else with returns (4-5 lines)
        del lines[i:i+5]
        
        # Insert new code
        for j, new_line in enumerate(new_code):
            lines.insert(i + j, new_line)
        
        replaced = True
        break

if not replaced:
    print("ERROR: Could not find replacement point")
    exit(1)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Successfully updated prompts loader")
print("   - Proper Python syntax")
print("   - Appends DevOps consultation instructions")
print("   - Instructs agent to use MCP tools dynamically")

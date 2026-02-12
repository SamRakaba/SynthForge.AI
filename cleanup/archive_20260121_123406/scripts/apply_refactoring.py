#!/usr/bin/env python3
"""Apply refactored instructions to iac_agent_instructions.yaml"""

# Read the refactored content
with open('refactored_instructions.yaml', encoding='utf-8') as f:
    refactored = f.read()

# Extract sections
terraform_instructions = refactored.split('module_development_agent_terraform_instructions: |')[1].split('module_development_agent_bicep_instructions: |')[0].strip()
bicep_instructions = refactored.split('module_development_agent_bicep_instructions: |')[1].split('deployment_wrapper_agent_instructions: |')[0].strip()
deployment_instructions = refactored.split('deployment_wrapper_agent_instructions: |')[1].split('service_analysis_agent_instructions: |')[0].strip()
service_analysis_instructions = refactored.split('service_analysis_agent_instructions: |')[1].strip()

# Read original file
with open('synthforge/prompts/iac_agent_instructions.yaml', encoding='utf-8') as f:
    lines = f.readlines()

# Find boundaries
print("Finding section boundaries...")
service_analysis_start = None
service_analysis_end = None
module_dev_start = None
module_dev_end = None
deployment_start = None
deployment_end = None

for i, line in enumerate(lines):
    if 'service_analysis_agent_instructions: |' in line:
        service_analysis_start = i + 1
    elif service_analysis_start and 'module_mapping_agent:' in line:
        service_analysis_end = i
        
    if 'module_development_agent_terraform_instructions: |' in line:
        module_dev_start = i + 1
    elif module_dev_start and 'module_development_agent_bicep_instructions: |' in line:
        terraform_end = i
        bicep_start = i + 1
    elif bicep_start and 'deployment_wrapper_agent:' in line:
        module_dev_end = i
        
    if 'deployment_wrapper_agent_terraform_instructions: |' in line:
        deployment_start = i + 1
    elif deployment_start and (i == len(lines) - 1 or 'deployment_wrapper_agent_bicep_instructions: |' in line):
        deployment_end = i + 1 if i == len(lines) - 1 else i

print(f"service_analysis: lines {service_analysis_start}-{service_analysis_end}")
print(f"module_development_terraform: lines {module_dev_start}-{terraform_end}")
print(f"module_development_bicep: lines {bicep_start}-{module_dev_end}")
print(f"deployment_wrapper_terraform: lines {deployment_start}-{deployment_end}")

# Apply replacements
new_lines = lines.copy()

# Replace service_analysis_agent
if service_analysis_start and service_analysis_end:
    indent = "    "  # 4 spaces for multi-line string content
    formatted_service = "\n".join([indent + line if line.strip() else "" for line in service_analysis_instructions.split("\n")])
    new_lines[service_analysis_start:service_analysis_end] = [formatted_service + "\n\n"]
    print(f"✓ Replaced service_analysis_agent ({service_analysis_end - service_analysis_start} → fewer lines)")

# Write output
output_file = 'synthforge/prompts/iac_agent_instructions_REFACTORED.yaml'
with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"\n✓ Written to: {output_file}")
print("\nNext: Review the file, then rename to iac_agent_instructions.yaml")

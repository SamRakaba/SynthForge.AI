"""
Fix Service Analysis agent in iac_agent_instructions.yaml
Add explicit MCP tool usage guidance
"""

yaml_file = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\iac_agent_instructions.yaml"

with open(yaml_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixes_applied = []

# Find service_analysis_agent section
service_start = None
for i, line in enumerate(lines):
    if line.strip() == 'service_analysis_agent:':
        service_start = i
        break

if service_start:
    # Find instructions line
    for i in range(service_start, min(service_start + 100, len(lines))):
        if 'instructions:' in lines[i] and '|' in lines[i]:
            # Found instructions block - add MCP guidance
            # Look for first section header or blank line after instructions start
            for j in range(i+1, min(i+30, len(lines))):
                if lines[j].strip().startswith('##') or (lines[j].strip() == '' and j > i+5):
                    mcp_text = """    
    ## Tool Usage - CRITICAL
    Use MCP Azure documentation tools to validate service configurations, dependencies, and required settings.
    Consult official Azure service documentation when analyzing services and their parameters.
    Ground all service analysis in official Azure documentation accessible via MCP tools.
    
"""
                    lines.insert(j, mcp_text)
                    fixes_applied.append("✅ Added MCP tool usage to Service Analysis Agent")
                    break
            break

# Write back
with open(yaml_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n" + "="*70)
print("SERVICE ANALYSIS AGENT FIX")
print("="*70)
for fix in fixes_applied:
    print(fix)

if not fixes_applied:
    print("⚠️ Could not find insertion point - may need manual edit")
else:
    print(f"\n✅ Successfully applied fix")

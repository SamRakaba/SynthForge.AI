"""
Fix Phase 1 agents in agent_instructions.yaml
Add MCP tool usage guidance to Vision, Filter, and Network Flow agents
"""

yaml_file = r"c:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\agent_instructions.yaml"

with open(yaml_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixes_applied = []

# Find and update each agent
def find_agent_section(lines, agent_name):
    """Find the line range for an agent section"""
    start = None
    end = None
    
    for i, line in enumerate(lines):
        if f'{agent_name}:' in line and not line.strip().startswith('#'):
            start = i
        elif start is not None and line.strip() and not line.startswith(' ') and ':' in line:
            end = i
            break
    
    if start and not end:
        end = len(lines)
    
    return start, end

# ============================================================================
# FIX 1: Vision Agent - Add MCP tool usage
# ============================================================================
vision_start, vision_end = find_agent_section(lines, 'vision_agent')
if vision_start:
    # Find instructions section
    for i in range(vision_start, vision_end):
        if 'instructions:' in lines[i]:
            # Add MCP guidance after instructions line
            mcp_text = """    
    ## Tool Usage
    Use available vision, OCR, and MCP services for accurate icon detection and validation.
    Leverage MCP Azure documentation tools to verify detected Azure service types.
    
"""
            # Insert after instructions block starts (find a good insertion point)
            # Look for the first blank line after instructions start
            for j in range(i+1, min(i+20, vision_end)):
                if lines[j].strip() == '' or lines[j].strip().startswith('##'):
                    lines.insert(j, mcp_text)
                    fixes_applied.append("✅ Added MCP tool usage to Vision Agent")
                    break
            break

# ============================================================================
# FIX 2: Filter Agent - Add MCP tool usage
# ============================================================================
filter_start, filter_end = find_agent_section(lines, 'filter_agent')
if filter_start:
    for i in range(filter_start, filter_end):
        if 'instructions:' in lines[i]:
            mcp_text = """    
    ## Tool Usage
    Use MCP Azure documentation tools to validate Azure service types and resource classifications.
    Consult documentation to accurately distinguish between architectural resources and non-architectural elements.
    
"""
            for j in range(i+1, min(i+20, filter_end)):
                if lines[j].strip() == '' or lines[j].strip().startswith('##'):
                    lines.insert(j, mcp_text)
                    fixes_applied.append("✅ Added MCP tool usage to Filter Agent")
                    break
            break

# ============================================================================
# FIX 3: Network Flow Agent - Add MCP tool usage
# ============================================================================
network_start, network_end = find_agent_section(lines, 'network_flow_agent')
if network_start:
    for i in range(network_start, network_end):
        if 'instructions:' in lines[i]:
            mcp_text = """    
    ## Tool Usage
    Use MCP tools to consult Azure networking best practices, VNET design patterns, and NSG configurations.
    Ground network flow analysis in official Azure networking documentation accessible via MCP tools.
    
"""
            for j in range(i+1, min(i+20, network_end)):
                if lines[j].strip() == '' or lines[j].strip().startswith('##'):
                    lines.insert(j, mcp_text)
                    fixes_applied.append("✅ Added MCP tool usage to Network Flow Agent")
                    break
            break

# Write updated YAML
with open(yaml_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Report
print("\n" + "="*70)
print("PHASE 1 AGENT FIXES APPLIED (agent_instructions.yaml)")
print("="*70)
for fix in fixes_applied:
    print(fix)

if not fixes_applied:
    print("⚠️ No fixes applied - agents may already have MCP guidance or pattern not matched")
else:
    print(f"\n✅ Successfully applied {len(fixes_applied)} fixes")

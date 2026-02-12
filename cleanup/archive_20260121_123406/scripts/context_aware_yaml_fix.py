#!/usr/bin/env python3
"""
Proper YAML indentation fix using context-aware rules.
Key insight: Lines at column 0 that are NOT top-level keys need indenting.
Top-level keys in this file: common_iac_principles, validation_pipeline, validation_strategy, workflow, integration_points, service_analysis_agent, module_mapping_agent, module_development_agent, deployment_wrapper_agent
"""

# Known top-level sections
TOP_LEVEL_KEYS = {
    'common_iac_principles',
    'validation_pipeline',
    'validation_strategy',
    'workflow',
    'integration_points',
    'service_analysis_agent',
    'module_mapping_agent',
    'module_development_agent',
    'deployment_wrapper_agent',
    'status_reporting',  # From the file
}

with open('synthforge/prompts/iac_agent_instructions.yaml.corrupted', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = []
context_stack = []  # Stack of (indent_level, key_name)

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Preserve empty and comment lines
    if not stripped or stripped.startswith('#'):
        fixed.append(line)
        continue
    
    current_indent = len(line) - len(line.lstrip())
    
    # Extract key name if this is a key line
    key_name = None
    is_list_item = stripped.startswith('- ')
    if ':' in stripped and not is_list_item:
        key_name = stripped.split(':', 1)[0].strip()
    
    # Determine if this should be a top-level key
    is_top_level = key_name in TOP_LEVEL_KEYS
    
    # If line is at column 0
    if current_indent == 0:
        # Should it be at column 0?
        if is_top_level or (i < 90):  # First 90 lines are common_iac_principles content
            fixed.append(line)
            if key_name and key_name in TOP_LEVEL_KEYS:
                context_stack = [(0, key_name)]
        else:
            # This should be indented - find the right level
            if context_stack:
                parent_indent = context_stack[-1][0]
                new_indent = parent_indent + 2
                fixed.append(' ' * new_indent + stripped + '\n')
            else:
                # Fallback - indent by 2 if we don't know context
                fixed.append('  ' + stripped + '\n')
    else:
        # Line already has indentation
        fixed.append(line)
        
        # Update context stack
        if key_name:
            # Remove items from stack that are at same or deeper level
            while context_stack and context_stack[-1][0] >= current_indent:
                context_stack.pop()
            # Add this key to stack
            context_stack.append((current_indent, key_name))

with open('synthforge/prompts/iac_agent_instructions.yaml', 'w', encoding='utf-8') as f:
    f.writelines(fixed)

print(f'Fixed {len(lines)} lines using top-level key detection')

#!/usr/bin/env python3
"""
Comprehensive YAML indent fix - properly identify top-level vs nested keys
"""

# ONLY these are true top-level keys at column 0
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
}

with open('synthforge/prompts/iac_agent_instructions.yaml.corrupted', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = []
indent_stack = []  # Track current indentation context

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Empty and comments - preserve
    if not stripped or stripped.startswith('#'):
        fixed.append(line)
        continue
    
    current_indent = len(line) - len(line.lstrip())
    is_list = stripped.startswith('- ')
    
    # Extract key name
    key_name = None
    if ':' in stripped and not is_list:
        key_name = stripped.split(':', 1)[0].strip()
    
    # Is this a top-level key?
    is_top_level = key_name in TOP_LEVEL_KEYS
    
    # If at column 0, decide if it should stay there or be indented
    if current_indent == 0:
        if is_top_level:
            # Keep at column 0
            fixed.append(line)
            indent_stack = [0]
        else:
            # Should be indented - use last indent + 2
            if indent_stack:
                new_indent = indent_stack[-1] + 2
            else:
                new_indent = 2  # Default
            
            fixed.append(' ' * new_indent + stripped + '\n')
            
            # Update stack for nested tracking
            if key_name:
                indent_stack.append(new_indent)
    else:
        # Already has indentation
        fixed.append(line)
        
        # Update indent stack
        if key_name:
            # Pop stack items at same or deeper level
            while indent_stack and indent_stack[-1] >= current_indent:
                indent_stack.pop()
            indent_stack.append(current_indent)

with open('synthforge/prompts/iac_agent_instructions.yaml', 'w', encoding='utf-8') as f:
    f.writelines(fixed)

print(f'Fixed {len(lines)} lines')

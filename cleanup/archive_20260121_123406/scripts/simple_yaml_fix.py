#!/usr/bin/env python3
"""Simple and correct YAML indentation fix"""

with open('synthforge/prompts/iac_agent_instructions.yaml.corrupted', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = []
last_parent_indent = -1
last_was_parent = False

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Empty or comment - keep exactly
    if not stripped or stripped.startswith('#'):
        fixed.append(line)
        last_was_parent = False
        continue
    
    current_indent = len(line) - len(line.lstrip())
    
    # Check if this line is a parent key (ends with : and no value)
    is_parent = False
    if ':' in stripped and not stripped.startswith('-'):
        parts = stripped.split(':', 1)
        if len(parts) == 2:
            value = parts[1].strip()
            is_parent = (not value)
    
    # If current line is at column 0 but we just had a parent
    # This line should be indented under that parent
    if current_indent == 0 and last_was_parent:
        new_indent = last_parent_indent + 2
        fixed.append(' ' * new_indent + stripped + '\n')
    else:
        fixed.append(line)
        
    # Track parent for next iteration
    if is_parent:
        last_was_parent = True
        last_parent_indent = current_indent if current_indent > 0 else len(fixed[-1]) - len(fixed[-1].lstrip())
    else:
        last_was_parent = False

with open('synthforge/prompts/iac_agent_instructions.yaml', 'w', encoding='utf-8') as f:
    f.writelines(fixed)

print(f'Fixed {len(lines)} lines')

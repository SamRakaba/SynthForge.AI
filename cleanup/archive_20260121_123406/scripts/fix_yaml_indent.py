#!/usr/bin/env python3
"""Fix YAML indentation without changing content"""

with open('synthforge/prompts/iac_agent_instructions.yaml.corrupted', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = []
for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Empty lines and comments - preserve exactly
    if not stripped or stripped.startswith('#'):
        fixed.append(line)
        continue
    
    current_indent = len(line) - len(line.lstrip())
    
    # If this is a key at column 0 that contains a colon
    if current_indent == 0 and ':' in stripped and not stripped.startswith('-'):
        should_indent = False
        target_indent = 0
        
        # Look back for parent context
        for j in range(len(fixed) - 1, max(0, len(fixed) - 20), -1):
            prev = fixed[j].strip()
            if not prev or prev.startswith('#'):
                continue
            
            prev_indent = len(fixed[j]) - len(fixed[j].lstrip())
            
            if ':' in prev:
                parts = prev.split(':', 1)
                if len(parts) == 2:
                    val = parts[1].strip()
                    
                    # Parent key with no value - children should be indented
                    if not val:
                        should_indent = True
                        target_indent = prev_indent + 2
                        break
        
        if should_indent:
            fixed.append(' ' * target_indent + stripped + '\n')
        else:
            fixed.append(line)
    else:
        fixed.append(line)

# Write fixed content
with open('synthforge/prompts/iac_agent_instructions.yaml', 'w', encoding='utf-8') as f:
    f.writelines(fixed)

print(f'Fixed {len(lines)} lines')

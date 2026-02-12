#!/usr/bin/env python3
"""Comprehensive YAML indentation fix - properly handle all nesting levels"""

def fix_yaml_indentation(input_file, output_file):
    """Fix YAML indentation by tracking context and proper nesting"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    indent_stack = [0]  # Track indentation levels
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Preserve empty lines and comments
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue
        
        # Detect list items
        is_list_item = stripped.startswith('- ')
        
        # Detect keys (have : but not list items with :)
        is_key = ':' in stripped and not (is_list_item and '":' not in stripped.split('-', 1)[1])
        
        # Check if this is a parent key (ends with : and no value after)
        is_parent_key = False
        if is_key:
            parts = stripped.split(':', 1)
            if len(parts) == 2:
                value = parts[1].strip()
                # Parent key if no value, or value is just a quote
                is_parent_key = not value or value in ['""', "''"]
        
        # Determine correct indentation
        current_raw_indent = len(line) - len(line.lstrip())
        
        # If line is at column 0 but should be indented
        if current_raw_indent == 0 and i > 0:
            # Look for context in previous non-empty lines
            parent_indent = 0
            for j in range(len(fixed_lines) - 1, -1, -1):
                prev_line = fixed_lines[j]
                prev_stripped = prev_line.strip()
                
                if not prev_stripped or prev_stripped.startswith('#'):
                    continue
                
                prev_indent = len(prev_line) - len(prev_line.lstrip())
                prev_is_parent = False
                
                if ':' in prev_stripped:
                    parts = prev_stripped.split(':', 1)
                    if len(parts) == 2:
                        val = parts[1].strip()
                        prev_is_parent = not val or val in ['""', "''"]
                
                # If previous line was a parent key, indent this line
                if prev_is_parent:
                    parent_indent = prev_indent + 2
                    break
                
                # If we find a line at same or less indent with content, we're likely a sibling or new section
                if prev_indent <= current_raw_indent:
                    # Check if this could be a top-level key (no parent above)
                    # Look further back for any parent
                    found_parent = False
                    for k in range(j - 1, max(0, j - 30), -1):
                        check_line = fixed_lines[k]
                        check_stripped = check_line.strip()
                        if not check_stripped or check_stripped.startswith('#'):
                            continue
                        check_indent = len(check_line) - len(check_line.lstrip())
                        if check_indent < prev_indent and ':' in check_stripped:
                            parts = check_stripped.split(':', 1)
                            if len(parts) == 2 and not parts[1].strip():
                                parent_indent = check_indent + 2
                                found_parent = True
                                break
                    
                    if not found_parent:
                        # Likely a top-level key or sibling at same level
                        parent_indent = 0
                    break
            
            # Apply the determined indentation
            fixed_lines.append(' ' * parent_indent + stripped + '\n')
        else:
            # Line already has some indentation, preserve it
            fixed_lines.append(line)
    
    # Write fixed content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed {len(lines)} lines")
    return len(lines)

if __name__ == '__main__':
    fix_yaml_indentation(
        'synthforge/prompts/iac_agent_instructions.yaml.corrupted',
        'synthforge/prompts/iac_agent_instructions.yaml'
    )

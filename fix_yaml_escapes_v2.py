"""
Fix YAML escape sequences in iac_agent_instructions.yaml - Version 2.

Uses simple string replacement instead of unicode_escape to avoid character encoding issues.
"""

import re

def simple_unescape(escaped_str: str) -> str:
    """
    Convert escaped string to plain text using simple replacements.
    Avoids unicode_escape issues.
    """
    # Remove surrounding quotes
    if escaped_str.startswith('"') and escaped_str.endswith('"'):
        escaped_str = escaped_str[1:-1]
    
    # Remove line continuations (backslash + spaces + backslash)
    escaped_str = re.sub(r'\\\s+\\', '', escaped_str)
    
    # Replace common escape sequences
    escaped_str = escaped_str.replace('\\n', '\n')
    escaped_str = escaped_str.replace('\\"', '"')
    escaped_str = escaped_str.replace('\\\\', '\\')
    escaped_str = escaped_str.replace('\\t', '\t')
    
    return escaped_str


def convert_file():
    """Convert iac_agent_instructions.yaml to use proper YAML block scalars."""
    
    input_file = 'synthforge/prompts/iac_agent_instructions.yaml'
    output_file = 'synthforge/prompts/iac_agent_instructions.yaml'
    backup_file = 'cleanup/iac_agent_instructions.yaml.backup'
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup original
    print(f"Creating backup at {backup_file}...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\nConverting escaped instruction strings to YAML block scalars...\n")
    
    # Pattern: finds lines like: key: "escaped string content...
    # We'll process specific keys we know about
    keys_to_convert = [
        'service_analysis_agent_instructions',
        'module_mapping_agent_instructions', 
        'module_development_agent_terraform_instructions',
        'module_development_agent_bicep_instructions',
        'deployment_wrapper_agent_terraform_instructions',
        'deployment_wrapper_agent_bicep_instructions'
    ]
    
    for key in keys_to_convert:
        print(f"Converting {key}...")
        
        # Find the start of this key
        pattern = rf'^(\s+){key}: "'
        match = re.search(pattern, content, re.MULTILINE)
        
        if not match:
            print(f"  ⚠️  Not found, skipping")
            continue
        
        indent = match.group(1)
        start_pos = match.start()
        
        # Find the end quote - it's on a line that ends with "\n alone
        # Look for pattern: ...\n" followed by either blank line or next key
        end_pattern = r'\\n"\s*\n'
        
        # Search from start position
        search_start = start_pos + len(match.group(0))
        end_match = re.search(end_pattern, content[search_start:])
        
        if not end_match:
            print(f"  ⚠️  Could not find end quote, skipping")
            continue
        
        end_pos = search_start + end_match.end()
        
        # Extract the escaped string
        old_block = content[start_pos:end_pos]
        
        # Get just the content between quotes
        escaped_content = content[start_pos + len(match.group(0)):end_pos - 2]  # Remove trailing "\n
        
        # Unescape
        unescaped = simple_unescape(escaped_content)
        
        # Create new YAML block scalar
        lines = unescaped.split('\n')
        new_lines = [f"{indent}{key}: |"]
        for line in lines:
            if line or lines.index(line) < len(lines) - 1:  # Include empty lines except trailing
                new_lines.append(f"{indent}  {line}".rstrip())
        
        new_block = '\n'.join(new_lines) + '\n'
        
        # Replace in content
        content = content[:start_pos] + new_block + content[end_pos:]
        
        print(f"  ✓ Converted ({len(old_block)} → {len(new_block)} chars)")
    
    print(f"\nWriting {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Done!")
    print(f"\nBackup saved at: {backup_file}")
    print("\nValidate with:")
    print("  python -c \"import yaml; yaml.safe_load(open('synthforge/prompts/iac_agent_instructions.yaml', encoding='utf-8'))\"")


if __name__ == '__main__':
    convert_file()

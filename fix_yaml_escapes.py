"""
Fix YAML escape sequences in iac_agent_instructions.yaml.

Converts escaped string literals to proper YAML block scalars using | notation.
"""

import re
import codecs

def unescape_string(escaped_str: str) -> str:
    """
    Convert escaped string literal to plain text.
    Handles \n, \", \\, etc.
    """
    # Remove surrounding quotes if present
    if escaped_str.startswith('"') and escaped_str.endswith('"'):
        escaped_str = escaped_str[1:-1]
    
    # Use Python's decode to handle escape sequences
    # Need to replace \    \ (continuation with backslash + spaces + backslash) with empty
    escaped_str = re.sub(r'\\\s+\\', '', escaped_str)
    
    # Decode standard escape sequences
    try:
        decoded = codecs.decode(escaped_str, 'unicode_escape')
    except:
        # If decode fails, try manual replacement
        decoded = escaped_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
    
    return decoded


def find_instruction_blocks(content: str) -> list:
    """Find all instruction blocks that use escaped strings."""
    # Pattern: key ending in _instructions: "..."
    pattern = r'^(\s+)(\w+_instructions):\s+"'
    
    blocks = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(pattern, line)
        if match:
            indent = match.group(1)
            key = match.group(2)
            
            # Find the closing quote - it could be many lines later
            # The string continues until we find a line ending with "\n alone followed by next key or section
            start_line = i
            escaped_content = line[match.end():]  # Get content after opening quote
            
            i += 1
            # Keep reading until we find the end of the string
            while i < len(lines):
                current = lines[i]
                
                # Check if this line ends the string (ends with " and next line starts a new key at same/lower indent)
                if '"' in current and i + 1 < len(lines):
                    # Check if next line is a new key at same or lower indentation
                    next_line = lines[i + 1]
                    if re.match(r'^(\s{0,' + str(len(indent)) + r'})\w+:', next_line):
                        # This is the end
                        escaped_content += '\n' + current
                        end_line = i
                        blocks.append({
                            'key': key,
                            'indent': indent,
                            'start_line': start_line,
                            'end_line': end_line,
                            'escaped_content': escaped_content
                        })
                        break
                
                escaped_content += '\n' + current
                i += 1
        
        i += 1
    
    return blocks


def convert_block_to_yaml(block: dict) -> str:
    """Convert an escaped instruction block to proper YAML block scalar."""
    indent = block['indent']
    key = block['key']
    escaped = block['escaped_content']
    
    # Unescape the string
    unescaped = unescape_string(escaped)
    
    # Create YAML block scalar
    # Add | and indent all lines
    lines = unescaped.split('\n')
    yaml_lines = [f"{indent}{key}: |"]
    
    for line in lines:
        if line.strip():  # Non-empty lines
            yaml_lines.append(f"{indent}  {line}")
        else:  # Empty lines
            yaml_lines.append("")
    
    return '\n'.join(yaml_lines)


def main():
    input_file = 'synthforge/prompts/iac_agent_instructions.yaml'
    output_file = 'synthforge/prompts/iac_agent_instructions_fixed.yaml'
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Finding instruction blocks with escape sequences...")
    blocks = find_instruction_blocks(content)
    
    print(f"Found {len(blocks)} blocks to convert:")
    for block in blocks:
        print(f"  - {block['key']} (lines {block['start_line']}-{block['end_line']})")
    
    # Convert blocks from end to start (so line numbers stay valid)
    lines = content.split('\n')
    for block in reversed(blocks):
        print(f"\nConverting {block['key']}...")
        new_block = convert_block_to_yaml(block)
        
        # Replace lines
        start = block['start_line']
        end = block['end_line']
        lines[start:end+1] = new_block.split('\n')
    
    # Write output
    new_content = '\n'.join(lines)
    
    print(f"\nWriting {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Done! Review the output file and replace the original if correct.")
    print("\nValidate with:")
    print("  python -c \"import yaml; yaml.safe_load(open('synthforge/prompts/iac_agent_instructions_fixed.yaml', encoding='utf-8'))\"")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Safe emoji removal - ONLY removes emojis, preserves ALL formatting and indentation
"""
import os

# List of emoji characters to remove
EMOJIS_TO_REMOVE = [
    '🔍', '🔧', '📚', '🤖', '🎯', '✓', '✅', '❌', '⚠️', '🔄'
]

def remove_emojis_safe(content):
    """Remove emojis without touching any other characters, especially whitespace"""
    for emoji in EMOJIS_TO_REMOVE:
        content = content.replace(emoji, '')
    return content

def process_file(filepath):
    """Process a single YAML file"""
    print(f"\nProcessing: {filepath}")
    
    # Read original
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    # Count emojis
    emoji_count = sum(original.count(emoji) for emoji in EMOJIS_TO_REMOVE)
    
    if emoji_count == 0:
        print(f"  ✓ No emojis found - skipping")
        return False
    
    print(f"  Found {emoji_count} emojis to remove")
    
    # Remove emojis only
    cleaned = remove_emojis_safe(original)
    
    # Verify we didn't break anything
    if len(cleaned) > len(original):
        print(f"  ✗ ERROR: File got bigger! Aborting.")
        return False
    
    # Create backup
    backup_path = filepath + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original)
    print(f"  ✓ Backup created: {backup_path}")
    
    # Write cleaned version
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    print(f"  ✓ Removed {emoji_count} emojis")
    return True

def main():
    files_to_process = [
        'synthforge/prompts/agent_instructions.yaml',
        'synthforge/prompts/iac_agent_instructions.yaml',
        'synthforge/prompts/code_quality_agent.yaml',
    ]
    
    processed = 0
    for filepath in files_to_process:
        if os.path.exists(filepath):
            if process_file(filepath):
                processed += 1
        else:
            print(f"\n✗ File not found: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"Completed: {processed} files modified")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

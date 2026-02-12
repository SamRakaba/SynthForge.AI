"""Test the JSON cleanup function with the actual problematic pattern."""

def fix_control_chars(text):
    result = []
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text):
        # Handle escape sequences
        if escape_next:
            result.append(char)
            escape_next = False
            continue
        
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
        
        # Track string boundaries (quotes not preceded by backslash)
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        
        # Replace control characters inside strings
        if in_string and ord(char) < 32:
            # Control character (0-31): newline, tab, carriage return, etc.
            result.append(' ')  # Replace with space
        else:
            result.append(char)
    
    return ''.join(result)

# Test with the pattern from the error
test_json = '''{
  "service_type": "Azure Application
Gateway",
  "dependencies": ["Azure Web
Application Firewall-2", "Azure
Firewall-7"],
  "requires_subnet": true
}'''

print("Original JSON:")
print(repr(test_json))
print("\nNewlines in original:", test_json.count('\n'))

cleaned = fix_control_chars(test_json)
print("\nCleaned JSON:")
print(repr(cleaned))
print("\nNewlines in cleaned:", cleaned.count('\n'))

# Try to parse
import json
try:
    parsed = json.loads(cleaned)
    print("\n✓ Cleaned JSON parsed successfully!")
    print(f"Result: {parsed}")
except json.JSONDecodeError as e:
    print(f"\n✗ Parse failed: {e}")
    print(f"Error at position {e.pos}")
    if e.pos:
        context_start = max(0, e.pos - 30)
        context_end = min(len(cleaned), e.pos + 30)
        print(f"Context: {cleaned[context_start:context_end]}")

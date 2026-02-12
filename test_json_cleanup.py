import json

# Test JSON with embedded newline (control character)
test_json = '{"test": ["Frontend IP\nConfiguration"]}'

print("Test JSON with embedded newline:")
print(repr(test_json))
print()

# Try to parse - should fail
try:
    json.loads(test_json)
    print("✓ Direct parse succeeded (unexpected)")
except json.JSONDecodeError as e:
    print(f"✗ Direct parse failed as expected: {e}")
print()

# Test cleanup function
def fix_control_chars(text):
    result = []
    in_string = False
    escape_next = False
    
    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue
        
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
        
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        
        # Replace ALL control chars inside strings with spaces
        if in_string:
            if ord(char) < 32:  # Control character
                result.append(' ')
            else:
                result.append(char)
        else:
            result.append(char)
    
    return ''.join(result)

cleaned = fix_control_chars(test_json)
print("After cleanup:")
print(repr(cleaned))
print()

# Try to parse cleaned version
try:
    result = json.loads(cleaned)
    print("✓ Cleaned JSON parsed successfully")
    print("Result:", result)
except json.JSONDecodeError as e:
    print(f"✗ Cleaned JSON still failed: {e}")

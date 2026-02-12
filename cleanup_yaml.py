import re

# Read the file
with open(r'C:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\agent_instructions.yaml', 'r', encoding='utf-8') as f:
    content = f.read()

# Split into lines
lines = content.split('\n')

# Find line numbers for sections
agent_lines = {}
for i, line in enumerate(lines):
    if re.match(r'^(ocr_detection_agent|detection_merger_agent|description_agent|filter_agent|security_agent|interactive_agent):', line):
        agent_name = line.split(':')[0]
        agent_lines[agent_name] = i

print("Agent positions:")
for name, line_num in sorted(agent_lines.items(), key=lambda x: x[1]):
    print(f"  {name}: line {line_num}")

# Define ranges to remove
remove_ranges = []
if 'ocr_detection_agent' in agent_lines and 'description_agent' in agent_lines:
    remove_ranges.append((agent_lines['ocr_detection_agent'], agent_lines['description_agent']))
    print(f"\nWill remove: ocr_detection_agent (lines {agent_lines['ocr_detection_agent']}-{agent_lines['description_agent']-1})")
    
if 'detection_merger_agent' in agent_lines and 'filter_agent' in agent_lines:
    remove_ranges.append((agent_lines['detection_merger_agent'], agent_lines['filter_agent']))
    print(f"Will remove: detection_merger_agent (lines {agent_lines['detection_merger_agent']}-{agent_lines['filter_agent']-1})")

# Remove the ranges
new_lines = []
for i, line in enumerate(lines):
    should_keep = True
    for start, end in remove_ranges:
        if start <= i < end:
            should_keep = False
            break
    if should_keep:
        new_lines.append(line)

# Write back
with open(r'C:\Users\srakaba\ai-agents\SynthForge.AI\synthforge\prompts\agent_instructions.yaml', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print(f"\nRemoved {len(lines) - len(new_lines)} lines")
print("File updated successfully!")

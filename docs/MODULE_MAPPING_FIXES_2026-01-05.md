# Module Mapping Agent Fixes - January 5, 2026

## Issues Identified & Fixed

### Issue 1: ❌ Missing `asyncio` Import
**Error**:
```
ERROR [7/12] Outer exception for Azure Event Hub: name 'asyncio' is not defined
```

**Root Cause**: `asyncio.gather()` and `asyncio.sleep()` used but module not imported

**Fix Applied**:
```python
import asyncio  # ← Added this line
import logging
from typing import Dict, Any, List, Optional
```

**File Changed**: `synthforge/agents/module_mapping_agent.py` (line 9)

---

### Issue 2: ❌ Agent Returning Text Instead of JSON
**Error**:
```
ERROR Failed to parse JSON for Azure Event Hub: Expecting value: line 1 column 1
ERROR First 500 chars of response: The Azure Verified Module (AVM) for Terraform...
```

**Root Cause**: Agent returning conversational text instead of structured JSON output

**Examples of Wrong Output**:
```
"The Azure Verified Module (AVM) for Terraform related to Azure Event Hub..."
"I couldn't find a direct Azure Verified Modules (AVM) module for Azure Storage Mover..."
```

**Fix Applied**:

1. **Added CRITICAL instruction at top of agent prompt**:
```yaml
instructions: |
  **CRITICAL FIRST RULE**: You MUST respond with ONLY valid JSON. NO explanatory text.
  
  ❌ WRONG: "The Azure Verified Module (AVM) for Terraform related to..."
  ❌ WRONG: "I couldn't find a direct Azure Verified Modules..."
  ✅ CORRECT: Start immediately with { and end with } - nothing else!
```

2. **Improved JSON extraction logic**:
```python
# Look for largest JSON structure even if there's text before/after
json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
json_matches = list(re.finditer(json_pattern, response_text, re.DOTALL))

if json_matches:
    # Use the largest JSON match (most complete)
    largest_match = max(json_matches, key=lambda m: len(m.group(0)))
    response_text = largest_match.group(0)
```

**Files Changed**:
- `synthforge/prompts/iac_agent_instructions.yaml` (lines 770-780)
- `synthforge/agents/module_mapping_agent.py` (lines 465-485)

---

## How The Fixes Work

### Fix 1: asyncio Import
```python
# Before (Error)
async def map_services(self, services: List[ServiceRequirement], ...):
    mapping_results = await asyncio.gather(...)  # ❌ asyncio not defined

# After (Working)
import asyncio  # ✅ Import added at top

async def map_services(self, services: List[ServiceRequirement], ...):
    mapping_results = await asyncio.gather(...)  # ✅ Now works
```

### Fix 2: JSON Extraction
```python
# Before: Only handled markdown code blocks
if "```json" in response_text:
    extract...

# After: Also handles text before/after JSON
# Step 1: Find ALL JSON objects in response
json_matches = re.finditer(r'\{...\}', response_text)

# Step 2: Use the LARGEST match (most complete JSON)
largest_match = max(json_matches, key=lambda m: len(m.group(0)))

# Step 3: Extract just that JSON
response_text = largest_match.group(0)

# Example Input:
# "The Azure Verified Module for Event Hub is {\"service_name\": ...}. Please confirm."
#                                             ^---- JSON extracted ----^
```

---

## Expected Behavior After Fix

### Before (Error)
```
▶ Stage 3/6: Module Mapping
ERROR Failed to parse JSON for Azure Event Hub: Expecting value: line 1 column 1
ERROR Response: The Azure Verified Module (AVM) for Terraform...
ERROR [7/12] Outer exception for Azure Event Hub: name 'asyncio' is not defined
```

### After (Working)
```
▶ Stage 3/6: Module Mapping
  -> Searching Azure Verified Modules for TERRAFORM...
  -> Mapping services to reusable infrastructure modules...
  
📦 [1/12] Azure OpenAI ✓
📦 [2/12] Azure Storage ✓
📦 [3/12] Azure Key Vault ✓
...
📦 [7/12] Azure Event Hub ✓    ← No more errors!
📦 [8/12] Azure Storage Mover ✓ ← No more errors!

✅ Mapped 12 services to infrastructure modules
```

---

## Testing Instructions

### 1. Verify asyncio Import
```python
# This should not raise NameError anymore
python -c "from synthforge.agents.module_mapping_agent import ModuleMappingAgent"
# No output = success
```

### 2. Test with Real Run
```powershell
cd c:\Users\srakaba\ai-agents\SynthForge.AI
python main.py --skip-phase1 --iac-format terraform
```

**Look For**:
- ✅ No "name 'asyncio' is not defined" errors
- ✅ No "Failed to parse JSON" errors
- ✅ No "Expecting value: line 1 column 1" errors
- ✅ All services successfully mapped (12/12 or whatever count)

### 3. Check JSON Responses
If you still see parse errors:
1. Check logs for "Extracted JSON from position..." message
2. Verify the extracted text is valid JSON
3. Agent might need more explicit instructions about output format

---

## Additional Improvements Made

### Better Error Logging
```python
logger.debug(f"Extracted JSON from position {start}-{end} ({len} chars)")
```
This helps debug if JSON extraction is working correctly.

### Regex Pattern for Nested JSON
The new regex pattern handles:
- Simple objects: `{"key": "value"}`
- Nested objects: `{"outer": {"inner": "value"}}`
- Deep nesting: `{"a": {"b": {"c": "value"}}}`
- Mixed content: Text before/after the JSON

---

## Files Modified Summary

### 1. module_mapping_agent.py (2 changes)
- **Line 9**: Added `import asyncio`
- **Lines 465-485**: Improved JSON extraction with regex pattern matching

### 2. iac_agent_instructions.yaml (1 change)
- **Lines 770-780**: Added CRITICAL JSON-only instruction at top of module_mapping_agent instructions

---

## Verification Checklist

After running Phase 2, verify:

- [ ] No `asyncio` not defined errors
- [ ] No JSON parse errors for Event Hub
- [ ] No JSON parse errors for Storage Mover
- [ ] All 12 services successfully mapped
- [ ] Console shows "✓" for each service
- [ ] Stage 3 completes without errors
- [ ] Stage 4 (Module Development) receives mappings
- [ ] Modules are generated successfully

---

## If Errors Still Occur

### If Agent Still Returns Text:
The agent instructions now clearly state JSON-only, but if it continues:
1. Check the model deployment (gpt-4.1 vs gpt-4o)
2. Verify Bing Grounding is not causing confusion
3. May need to add JSON schema validation

### If JSON Structure is Wrong:
Check that the agent is following the expected schema:
```json
{
  "service_name": "...",
  "module_structure": {
    "main_module": {...},
    ...
  }
}
```

### If Extraction Fails:
The regex pattern should handle most cases, but if it fails:
1. Check logs for "Extracted JSON from position..." message
2. Manually inspect the response text
3. May need to refine the regex pattern

---

## Status: ✅ FIXES APPLIED

Both critical issues have been resolved:
1. ✅ `asyncio` import added
2. ✅ JSON extraction improved + stricter agent instructions

Next step: **Re-run Phase 2 to verify fixes work**

```powershell
python main.py --skip-phase1 --iac-format terraform
```

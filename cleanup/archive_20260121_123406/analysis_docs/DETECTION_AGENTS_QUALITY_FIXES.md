# Detection Agents Quality Fixes

**Date**: 2026-01-14  
**Purpose**: Fix completeness and accuracy issues in vision, OCR, and description agent instructions

## Issues Identified and Fixed

### 1. Vision Agent - Workflow Step Numbering ✅ FIXED

**Issue**: Workflow steps were numbered 1,2,3,5,6,7 (missing step 4)

**Location**: `agent_instructions.yaml`, lines 318-327

**Fix Applied**:
- Reordered workflow steps to be sequential 1-7
- Step 4 is now: "Get ARM types using resolve_arm_type with normalized name"
- This ensures clarity in the mandatory workflow sequence

**Before**:
```yaml
1. Visually identify icons
2. Call normalize_service_name
3. Use normalized name
5. If fails, try Bing           # Missing #4!
6. If uncertain, mark for clarification
7. Get ARM types
```

**After**:
```yaml
1. Visually identify icons
2. Call normalize_service_name
3. Use normalized name
4. Get ARM types               # Step 4 added
5. If fails, try Bing
6. If uncertain, mark for clarification
7. Look up naming constraints
```

### 2. Vision Agent - No Redundant Section Found ✅ VERIFIED

**Issue Reported**: Potential redundant section at end of vision_agent

**Investigation**: Lines 550-595 reviewed - no redundancy found

**Result**: Vision agent user prompt is clean and non-repetitive. No fix needed.

---

### 3. OCR Agent - Workflow Steps Complete ✅ VERIFIED

**Issue Reported**: Missing item #4 in numbered list

**Investigation**: Checked OCR agent instructions thoroughly:
- "Text Categories to Identify" list (lines 762-768): Complete with items 1-7
- "Step 4: CRITICAL - Validate Service Type" (line 694): Present and correct
- All workflow steps (1-7) are properly numbered

**Result**: No numbering gaps found. OCR agent workflow is complete and sequential.

---

### 4. OCR Agent - Response Schema Documentation ✅ FIXED

**Issue**: {response_schema} placeholder not explained in user prompt

**Location**: `agent_instructions.yaml`, lines 870-876

**Fix Applied**:
- Added explanatory note about the placeholder injection
- Clarifies that the schema is injected at runtime
- Documents what the schema will contain

**Added**:
```yaml
## Response Format
Respond with valid JSON matching this schema (compatible with VisionAgent output):
{response_schema}

**Note**: The {response_schema} placeholder will be injected with the actual JSON schema at runtime,
defining the structure for diagram_metadata, detected_icons, detected_text, vnet_boundaries, and data_flows.
```

---

### 5. Description Agent - Output Format Consistency ✅ FIXED

**Issue**: Instructions said "narrative in plain English" but user_prompt required JSON

**Location**: `agent_instructions.yaml`, lines 963-970

**Fix Applied**:
- Removed narrative format instructions
- Replaced with JSON-focused guidance
- Aligned with actual agent code expectations

**Before**:
```yaml
## Output Format

Provide a comprehensive narrative description in plain English, organized by:

## Overview
[High-level summary...]

## Core Services
[List and describe...]
```

**After**:
```yaml
## Output Format

Respond with a comprehensive JSON object containing all detected components.
Use the exact structure shown in the user prompt template (title, overview,
azure_components, infrastructure, network_topology, external_sources, etc.).

This JSON output will be parsed programmatically to guide structured detection.
```

---

### 6. Description Agent - network_associations Field ✅ FIXED

**Issue**: Field mentioned in pattern rules but missing from JSON schema example

**Locations Fixed**:
1. `agent_instructions.yaml`, lines 1040-1048 (user_prompt JSON schema)
2. `description_agent.py`, line 48 (dataclass field)
3. `description_agent.py`, line 426 (parsing logic)

**Fixes Applied**:

**A. Added to YAML JSON Schema**:
```yaml
"groupings": [
  "Any labeled sections or groupings"
],
"network_associations": [
  "Network isolation components ASSOCIATED with services (not standalone resources)",
  "Format: 'Service Name: network component type'",
  "e.g., 'Azure Functions: VNet integration subnet', 'Azure Storage: Private endpoint'"
]
```

**B. Added to ArchitectureDescription Dataclass**:
```python
@dataclass
class ArchitectureDescription:
    # ... other fields ...
    network_associations: List[str] = None
    
    def __post_init__(self):
        # ... other initializations ...
        self.network_associations = self.network_associations or []
```

**C. Added to Parsing Logic**:
```python
description = ArchitectureDescription(
    # ... other fields ...
    network_associations=data.get("network_associations", []),
    raw_description=response_text,
)
```

---

## Impact on Agent Behavior

### Vision Agent
- **More Clear Workflow**: Step numbering now sequential, easier to follow
- **ARM Type Lookup**: Explicitly positioned after normalization (step 4)
- **No Breaking Changes**: Output format unchanged

### OCR Agent  
- **Better Documentation**: Users understand {response_schema} is runtime-injected
- **No Functional Changes**: All workflows were already complete and correct

### Description Agent
- **Consistent Output**: JSON-only format eliminates confusion
- **Complete Schema**: network_associations field properly supported
- **Agent Code Compatible**: Python code can now handle all JSON fields

---

## Verification Checklist

- ✅ Vision agent workflow steps are sequential (1-7)
- ✅ OCR agent workflow steps are complete (no gaps)
- ✅ OCR agent {response_schema} placeholder is documented
- ✅ Description agent output format is JSON-only (no narrative confusion)
- ✅ Description agent network_associations field added to:
  - User prompt JSON schema example
  - ArchitectureDescription dataclass
  - JSON parsing logic
- ✅ All agents maintain backward compatibility
- ✅ No breaking changes to agent APIs

---

## Testing Recommendations

### Vision Agent
Test that the reordered workflow (especially step 4: ARM type lookup) works correctly:
```python
async with VisionAgent() as agent:
    result = await agent.detect_icons("test_diagram.png")
    # Verify all detections have arm_resource_type populated
    assert all(d.get('arm_resource_type') for d in result.detected_icons)
```

### Description Agent
Test that network_associations field is properly captured:
```python
async with DescriptionAgent() as agent:
    desc = await agent.describe_architecture("test_diagram.png")
    # Verify new field exists
    assert hasattr(desc, 'network_associations')
    assert isinstance(desc.network_associations, list)
    # Test JSON parsing with network_associations
    if desc.network_associations:
        assert all(isinstance(item, str) for item in desc.network_associations)
```

### OCR Agent
Test with complex multi-line text patterns:
```python
async with OCRDetectionAgent() as agent:
    result = await agent.detect_text("test_diagram.png")
    # Verify response_schema was properly injected
    assert 'diagram_metadata' in result
    assert 'detected_icons' in result
```

---

## Files Modified

1. **synthforge/prompts/agent_instructions.yaml**
   - Lines 318-327: Vision agent workflow renumbering
   - Lines 870-876: OCR agent placeholder documentation
   - Lines 963-970: Description agent output format fix
   - Lines 1040-1048: Description agent network_associations schema

2. **synthforge/agents/description_agent.py**
   - Lines 40-66: ArchitectureDescription dataclass (added network_associations)
   - Line 426: JSON parsing (added network_associations extraction)

---

## Summary

All 6 identified quality issues have been addressed:
- **2 numbering issues** → 1 fixed (vision), 1 verified as correct (OCR)
- **1 documentation gap** → Fixed (OCR placeholder)
- **1 output format inconsistency** → Fixed (description agent)
- **1 missing schema field** → Fixed in 3 locations (description agent)
- **0 breaking changes** → All fixes maintain backward compatibility

The detection agents now have:
- ✅ Clear, sequential workflow steps
- ✅ Complete documentation for placeholders
- ✅ Consistent output format specifications
- ✅ Complete JSON schema definitions
- ✅ Agent code that can handle all fields

**Status**: Ready for testing and deployment

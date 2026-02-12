# Agent Instruction Analysis Report

## Executive Summary

**Total Instruction Files:** 2 main files (Phase 1 + Phase 2)
**Total Agents:** 12 agents
**Total Lines:** 9,401 lines
**Total Words:** 40,285 words

### Critical Issues Found:
1. ⚠️ **EXCESSIVE WORDINESS**: 7 of 12 agents exceed 2000 words
2. ⚠️ **HARDCODED EXAMPLES**: All agents contain hardcoded service names/examples
3. ⚠️ **DUPLICATION**: 1 agent has repeated content
4. ⚠️ **INCONSISTENCY**: Different agents use different instruction styles

---

## Phase 1: Detection Agents (3,415 lines, 16,387 words)

### 1. vision_agent
- **Lines:** 31-431 (401 lines)
- **Words:** 2,631 words
- **Issues:**
  - ⚠️ VERY WORDY (2,631 words - 31% over recommended 2000)
  - ⚠️ HARDCODED EXAMPLES: Contains Azure service category lists ("Compute", "Storage", "Networking", "Databases")
  - ⚠️ 23 example sections (teaching examples, but could be more concise)

**Recommendations:**
- Remove hardcoded category examples (use pure MCP/Bing lookup)
- Consolidate duplicate workflow instructions
- Move detailed examples to separate reference doc

---

### 2. ocr_detection_agent
- **Lines:** 432-804 (373 lines)
- **Words:** 2,073 words
- **Issues:**
  - ⚠️ VERY WORDY (2,073 words - 4% over recommended 2000)
  - ⚠️ HARDCODED EXAMPLES: Contains service name examples
  - ⚠️ 9 example sections

**Recommendations:**
- Remove hardcoded service name examples
- Consolidate OCR pattern instructions
- Reduce repetitive text extraction guidelines

---

### 3. description_agent
- **Lines:** 805-1029 (225 lines)
- **Words:** 1,269 words
- **Issues:**
  - ⚠️ Wordy (1,269 words - 27% over recommended 1000)
  - ⚠️ HARDCODED EXAMPLES: 2 patterns detected
  - ⚠️ 3 example sections

**Recommendations:**
- Consolidate description generation rules
- Remove redundant examples
- Focus on core principles only

---

### 4. detection_merger_agent
- **Lines:** 1030-1334 (305 lines)
- **Words:** 1,688 words
- **Issues:**
  - ⚠️ Wordy (1,688 words - 69% over recommended 1000)
  - ⚠️ HARDCODED EXAMPLES: 3 patterns detected
  - ⚠️ 11 example sections

**Recommendations:**
- Simplify merging logic instructions
- Remove duplicate confidence calculation examples
- Consolidate overlap detection rules

---

### 5. filter_agent
- **Lines:** 1335-1699 (365 lines)
- **Words:** 1,975 words
- **Issues:**
  - ⚠️ Wordy (1,975 words - 98% over recommended 1000)
  - ⚠️ HARDCODED EXAMPLES: 1 pattern detected
  - ⚠️ 10 example sections
  - ⚠️ Contains Network Isolation Pattern detection logic (very detailed)

**Recommendations:**
- Simplify architectural vs deployment categorization
- Consolidate network pattern detection rules
- Reduce Well-Architected Framework references (move to separate doc)

---

### 6. security_agent
- **Lines:** 1700-2163 (464 lines)
- **Words:** 2,501 words
- **Issues:**
  - ⚠️ VERY WORDY (2,501 words - 25% over recommended 2000)
  - ⚠️ HARDCODED EXAMPLES: 2 patterns detected
  - ⚠️ 23 example sections
  - ⚠️ Contains extensive security rule documentation

**Recommendations:**
- Move detailed security rules to external reference
- Consolidate validation patterns
- Reduce redundant best practice examples

---

### 7. interactive_agent
- **Lines:** 2164-3128 (965 lines)
- **Words:** 2,684 words
- **Issues:**
  - ⚠️ VERY WORDY (2,684 words - 34% over recommended 2000)
  - ⚠️ HARDCODED EXAMPLES: 2 patterns detected
  - ⚠️ 12 example sections
  - ⚠️ Contains extensive clarification workflow logic

**Recommendations:**
- Simplify user interaction patterns
- Consolidate similar clarification scenarios
- Remove redundant examples (review, correct, resolve flows very similar)

---

### 8. network_flow_agent
- **Lines:** 3129-3416 (288 lines)
- **Words:** 1,566 words
- **Issues:**
  - ⚠️ Wordy (1,566 words - 57% over recommended 1000)
  - ⚠️ HARDCODED EXAMPLES: 2 patterns detected
  - ⚠️ 5 example sections

**Recommendations:**
- Consolidate network flow detection rules
- Remove redundant connectivity examples
- Simplify flow direction logic

---

## Phase 2: IaC Generation Agents (6,005 lines, 23,898 words)

### 9. service_analysis_agent
- **Lines:** 209-988 (780 lines)
- **Words:** 3,934 words
- **Issues:**
  - ⚠️ VERY WORDY (3,934 words - **97% OVER recommended 2000**)
  - ⚠️ HARDCODED EXAMPLES: 3 patterns detected
  - ⚠️ 18 example sections
  - ⚠️ Contains extensive service dependency analysis rules

**Recommendations:**
- **URGENT**: Reduce by 50% - consolidate dependency analysis rules
- Move service classification examples to external reference
- Simplify requirement extraction logic
- Remove redundant Azure-native vs third-party detection examples

---

### 10. module_mapping_agent
- **Lines:** 989-1672 (684 lines)
- **Words:** 3,285 words
- **Issues:**
  - ⚠️ VERY WORDY (3,285 words - 64% over recommended 2000)
  - ⚠️ HARDCODED EXAMPLES: 2 patterns detected
  - ⚠️ 50 example sections (HIGHEST example density)
  - ⚠️ Contains AVM pattern documentation (should use MCP instead)

**Recommendations:**
- **URGENT**: Reduce by 40% - remove inline AVM documentation
- Use MCP tools for AVM pattern lookup instead of hardcoding
- Consolidate module structure examples
- Remove redundant naming convention examples

---

### 11. module_development_agent
- **Lines:** 1673-4658 (2986 lines)
- **Words:** 11,179 words
- **Issues:**
  - ⚠️ **EXTREMELY WORDY** (11,179 words - **459% OVER recommended 2000**)
  - ⚠️ HARDCODED EXAMPLES: 2 patterns detected
  - ⚠️ 145 example sections (far too many)
  - ⚠️ DUPLICATION: 2 repeated sentences found
  - ⚠️ Contains massive Bicep/Terraform code generation rules

**Recommendations:**
- **CRITICAL**: Reduce by 70-80% - this is the largest agent
- Move Bicep/Terraform patterns to external reference or MCP tools
- Remove extensive code examples (agent should generate based on MCP best practices)
- Consolidate duplicate module structure documentation
- Split into smaller, focused instruction sections
- Use Bicep MCP and Terraform MCP for best practices instead of hardcoding

---

### 12. deployment_wrapper_agent
- **Lines:** 4659-6006 (1348 lines)
- **Words:** 5,500 words
- **Issues:**
  - ⚠️ VERY WORDY (5,500 words - **175% OVER recommended 2000**)
  - ⚠️ DUPLICATION: 5 repeated sentences found
  - ⚠️ HARDCODED EXAMPLES: 2 patterns detected
  - ⚠️ 78 example sections
  - ⚠️ Contains extensive deployment pipeline documentation

**Recommendations:**
- **URGENT**: Reduce by 60% - remove redundant pipeline examples
- Consolidate duplicate deployment pattern instructions
- Move pipeline templates to external files
- Simplify variable naming conventions
- Remove repetitive validation rules

---

## Consistency Issues

### Different Instruction Styles:
1. **vision_agent & ocr_detection_agent**: Step-by-step workflow format
2. **filter_agent & security_agent**: Rule-based format with extensive examples
3. **module_development_agent**: Massive reference manual style
4. **interactive_agent**: Conversational workflow style

### Recommendation:
Standardize all agents to use:
```
1. Core Objective (1-2 sentences)
2. Tool Usage (MCP/Bing references only)
3. Key Principles (bullet list, < 10 items)
4. Output Format (JSON schema reference)
5. Edge Cases (< 5 scenarios)
```

---

## Hardcoded Examples Summary

### All Agents Violate "No Hardcoding" Principle:

**Phase 1 Agents:**
- vision_agent: Azure service categories ("Compute", "Storage", etc.)
- ocr_detection_agent: Service name examples ("Azure Functions", "Azure Storage")
- All agents: CORRECT/WRONG example comparisons with specific service names

**Phase 2 Agents:**
- service_analysis_agent: Service dependency examples
- module_mapping_agent: AVM pattern documentation (should use MCP)
- module_development_agent: Extensive Bicep/Terraform code examples (should use MCP)
- deployment_wrapper_agent: Pipeline template examples

### Recommendation:
**Replace ALL hardcoded examples with:**
- MCP tool references (MS Learn, Bicep, Terraform)
- Bing grounding queries
- Dynamic lookup instructions
- Principle-based guidance only

---

## Duplication Analysis

### deployment_wrapper_agent (5 duplicates):
- Repeated validation rules
- Duplicate pipeline stage documentation
- Redundant variable naming instructions

### module_development_agent (2 duplicates):
- Repeated module structure documentation
- Duplicate best practice references

### Recommendation:
- Create shared instruction sections (DRY principle)
- Reference global_agent_principles.yaml for common patterns
- Remove all duplicate content

---

## Action Plan

### Priority 1 (Critical - Reduce Immediately):
1. **module_development_agent**: Reduce from 11,179 → 2,000 words (82% reduction)
2. **deployment_wrapper_agent**: Reduce from 5,500 → 2,000 words (64% reduction)
3. **service_analysis_agent**: Reduce from 3,934 → 2,000 words (49% reduction)

### Priority 2 (High - Reduce Soon):
4. **module_mapping_agent**: Reduce from 3,285 → 2,000 words (39% reduction)
5. **interactive_agent**: Reduce from 2,684 → 2,000 words (26% reduction)
6. **security_agent**: Reduce from 2,501 → 2,000 words (20% reduction)
7. **vision_agent**: Reduce from 2,631 → 2,000 words (24% reduction)

### Priority 3 (Medium - Optimize):
8. Remove ALL hardcoded examples (18 Phase 1 + 9 Phase 2 = 27 instances)
9. Consolidate duplicate content (7 instances)
10. Standardize instruction format across all agents

### Priority 4 (Low - Refactor):
11. Move detailed examples to external reference docs
12. Create reusable instruction modules
13. Enhance MCP tool usage to replace hardcoded knowledge

---

## Target Metrics

**Current State:**
- Total: 40,285 words
- Average: 3,357 words/agent
- Largest: 11,179 words (module_development_agent)

**Target State:**
- Total: ~20,000 words (50% reduction)
- Average: ~1,500 words/agent
- Largest: ~2,000 words (any agent)
- Zero hardcoded examples
- Zero duplication
- Consistent format

**Estimated Impact:**
- 50% reduction in token usage per agent call
- Faster agent response times
- Reduced hallucination risk
- Easier maintenance and updates
- Better adherence to agent-first, tool-based architecture

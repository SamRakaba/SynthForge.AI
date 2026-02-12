# Comprehensive Instruction Review - Consistency, Conciseness, Tool Utilization

## Executive Summary

### Critical Issues Found
1. ❌ **Bicep Deployment Wrapper has placeholder text** (line 5965) - Only 314 chars vs Terraform's 46K chars
2. ⚠️ **Filter Agent (Phase 1 Stage 2)** - No MCP mention, no explicit tool usage guidance
3. ⚠️ **Network Flow Agent** - MCP mentioned but no explicit tool usage guidance
4. ⚠️ **Service Analysis Agent** - MCP mentioned but no explicit tool usage guidance
5. ⚠️ **Inconsistent MCP tool guidance** - Some agents have "consult tools", others don't

### Strengths
✅ All instructions centralized in YAML (iac_agent_instructions.yaml + agent_instructions.yaml)
✅ Most agents (7/10) mention MCP or tool usage
✅ All agents have grounding/documentation references except Bicep deployment wrapper

## Detailed Analysis by Agent

### Phase 1: Architecture Analysis

#### 1. Vision Agent (Stage 0-1)
- **Length**: 8,101 chars
- **MCP**: ✅ Yes
- **Tool usage**: ❌ No explicit guidance
- **Grounding**: ✅ Yes
- **Recommendation**: Add explicit instruction to "use available vision/OCR tools and MCP services"

#### 2. Filter Agent (Stage 2 - Classification)
- **Length**: 12,744 chars  
- **MCP**: ❌ No mention
- **Tool usage**: ❌ No guidance
- **Grounding**: ✅ Yes
- **Issue**: Should leverage MCP Azure documentation tools to validate Azure service types
- **Recommendation**: Add "Consult MCP Azure documentation tools to validate service classifications"

#### 3. Network Flow Agent (Stage 4)
- **Length**: 5,986 chars
- **MCP**: ✅ Mentioned
- **Tool usage**: ❌ No explicit guidance
- **Grounding**: ✅ Yes
- **Recommendation**: Add "Use MCP tools to consult Azure networking best practices"

#### 4. Security Agent (Stage 5)
- **Length**: 15,324 chars
- **MCP**: ✅ Yes
- **Tool usage**: ✅ Yes - "consult" mentioned
- **Grounding**: ✅ Yes
- **Status**: ✅ GOOD - Has proper tool usage guidance

### Phase 2: IaC Generation

#### 5. Service Analysis Agent (Stage 1)
- **Length**: 24,035 chars
- **MCP**: ✅ Mentioned
- **Tool usage**: ❌ No explicit guidance
- **Grounding**: ✅ Yes
- **Recommendation**: Add "Use MCP Azure documentation tools to validate service configurations"

#### 6. Module Mapping Agent (Stage 3)
- **Length**: 29,730 chars
- **MCP**: ✅ Yes
- **Tool usage**: ✅ Yes - "consult available tools"
- **Grounding**: ✅ Yes  
- **Status**: ✅ GOOD - Has proper tool usage guidance

#### 7. Module Development Agent - Terraform (Stage 4)
- **Length**: 68,647 chars
- **MCP**: ✅ Yes
- **Tool usage**: ✅ Yes - "use mcp_hashicorp_ter_* tools"
- **Grounding**: ✅ Yes
- **Status**: ✅ GOOD - Has proper tool usage guidance

#### 8. Module Development Agent - Bicep (Stage 4)
- **Length**: 30,599 chars
- **MCP**: ✅ Yes
- **Tool usage**: ✅ Yes - "use mcp_bicep_experim_* tools"
- **Grounding**: ✅ Yes
- **Status**: ✅ GOOD - Has proper tool usage guidance

#### 9. Deployment Wrapper Agent - Terraform (Stage 5)
- **Length**: 46,263 chars
- **MCP**: ✅ Yes
- **Tool usage**: ✅ Yes - "Consult available MCP tools"
- **Grounding**: ✅ Yes
- **Status**: ✅ GOOD - Has proper tool usage guidance

#### 10. Deployment Wrapper Agent - Bicep (Stage 5)
- **Length**: 314 chars ❌ **CRITICAL**
- **MCP**: ✅ Yes (in appended consultation)
- **Tool usage**: ✅ Yes (in appended consultation)
- **Grounding**: ❌ No - only placeholder text
- **Issue**: YAML line 5965 has placeholder: "[Similar structure to Terraform, adapted for Bicep syntax...]"
- **Status**: ❌ **BROKEN** - Needs full Bicep instructions

## Consistency Issues

### 1. MCP Tool Naming Inconsistency
- ✅ Some say: "mcp_hashicorp_ter_*" or "mcp_bicep_experim_*" (specific)
- ⚠️ Others say: "MCP" or "available tools" (vague)
- **Recommendation**: Standardize to specific tool names where applicable

### 2. Tool Usage Instruction Format
- **Security Agent**: "consult available tools"
- **Module Mapping**: "consult available tools"  
- **Module Development**: "use mcp_hashicorp_ter_* tools"
- **Deployment Wrapper**: "Consult available MCP tools BEFORE generating"
- **Recommendation**: Standardize to: "Use available MCP tools: [specific tools]"

### 3. Grounding Instruction Consistency
- Most agents: "ground in documentation"
- Some agents: "follow best practices"
- **Recommendation**: All should say: "Ground decisions in official Azure documentation via MCP tools"

## Verbosity Analysis

### Overly Verbose (>40K chars)
1. **Module Development Terraform**: 68,647 chars
   - May have redundant examples
   - Consider consolidating repetitive sections

### Appropriately Sized (10K-40K chars)
2. Service Analysis: 24,035 chars ✅
3. Module Mapping: 29,730 chars ✅
4. Module Development Bicep: 30,599 chars ✅
5. Deployment Wrapper Terraform: 46,263 chars ✅

### Concise (<10K chars)
6. Vision: 8,101 chars ✅
7. Filter: 12,744 chars ✅
8. Security: 15,324 chars ✅
9. Network Flow: 5,986 chars ✅

### Critically Short
10. **Deployment Wrapper Bicep**: 314 chars ❌ **BROKEN**

## Conflicting Instructions

### None Found ✅
- No direct conflicts detected
- All agents follow similar patterns
- Consistent JSON response format requirements

## Centralization Status

✅ **GOOD** - All instructions properly centralized:
- `synthforge/prompts/agent_instructions.yaml` - Phase 1 agents
- `synthforge/prompts/iac_agent_instructions.yaml` - Phase 2 agents  
- `synthforge/prompts/__init__.py` - Loader functions only
- No hardcoded instructions in agent Python files ✅

## Recommendations Summary

### Priority 1: CRITICAL FIXES

1. **Fix Bicep Deployment Wrapper Instructions**
   - File: `iac_agent_instructions.yaml` line 5965
   - Action: Replace placeholder with full Bicep-specific deployment wrapper instructions
   - Template from: Terraform version (lines ~3800-5963) adapted for Bicep syntax

### Priority 2: ADD EXPLICIT TOOL USAGE

2. **Filter Agent** - Add:
   ```yaml
   Use MCP Azure documentation tools to validate Azure service types and classifications.
   ```

3. **Network Flow Agent** - Add:
   ```yaml
   Use MCP tools to consult Azure networking best practices and VNET design patterns.
   ```

4. **Service Analysis Agent** - Add:
   ```yaml
   Use MCP Azure documentation tools to validate service configurations and dependencies.
   ```

5. **Vision Agent** - Add:
   ```yaml
   Use available vision, OCR, and MCP services for accurate icon detection and validation.
   ```

### Priority 3: STANDARDIZE FORMAT

6. **Standardize MCP Tool References**
   - Replace vague "available tools" with specific tool names
   - Format: "Use MCP tools: `mcp_tool_name_*` for [purpose]"

7. **Standardize Grounding Instructions**
   - All agents should include:
   ```yaml
   Ground all decisions in official Azure documentation accessible via MCP documentation tools.
   ```

### Priority 4: OPTIMIZE VERBOSITY

8. **Review Terraform Module Development** (68K chars)
   - Check for redundant examples
   - Consider moving extensive examples to separate reference section
   - Target: Reduce to ~40K chars if possible

## Tool Utilization Score

| Agent | MCP | Tools | Grounding | Score |
|-------|-----|-------|-----------|-------|
| Vision | ✅ | ⚠️ | ✅ | 67% |
| Filter | ❌ | ❌ | ✅ | 33% |
| Security | ✅ | ✅ | ✅ | 100% |
| Network Flow | ✅ | ⚠️ | ✅ | 67% |
| Service Analysis | ✅ | ⚠️ | ✅ | 67% |
| Module Mapping | ✅ | ✅ | ✅ | 100% |
| Module Dev (TF) | ✅ | ✅ | ✅ | 100% |
| Module Dev (Bicep) | ✅ | ✅ | ✅ | 100% |
| Deploy Wrap (TF) | ✅ | ✅ | ✅ | 100% |
| Deploy Wrap (Bicep) | ✅ | ✅ | ❌ | 67% |

**Overall Average**: 80%
**Target**: 100%

## Implementation Plan

1. **Immediate** (Today):
   - Fix Bicep Deployment Wrapper (CRITICAL)
   
2. **High Priority** (This Week):
   - Add explicit tool usage to Filter, Network Flow, Service Analysis, Vision agents
   
3. **Medium Priority** (Next Week):
   - Standardize MCP tool references across all agents
   - Standardize grounding instructions
   
4. **Low Priority** (Future):
   - Optimize Terraform Module Development verbosity

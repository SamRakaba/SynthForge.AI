# Stage 4 & 5 Analysis: Patterns, Consistency, and Architecture

## Executive Summary

**Analysis Date**: January 8, 2026  
**Scope**: Stage 4 (Module Development) and Stage 5 (Deployment Wrappers)  
**Goal**: Ensure similar patterns for Bicep/Terraform, consistent instructions, no static mappings, externalized prompts

---

## ✅ GOOD PRACTICES FOUND

### 1. Instructions Externalized to YAML ✅
**Status**: EXCELLENT
- **Stage 4**: `get_module_development_agent_instructions(iac_format)` from `iac_agent_instructions.yaml`
- **Stage 5**: `get_deployment_wrapper_agent_instructions(iac_format)` from `iac_agent_instructions.yaml`
- **Location**: `synthforge/prompts/__init__.py` + `synthforge/prompts/iac_agent_instructions.yaml`
- **Benefit**: All base instructions are externalized, version-controlled YAML

### 2. Consistent Tool Setup Pattern ✅
**Status**: EXCELLENT

Both Stage 4 and Stage 5 use identical tool configuration:
```python
# Stage 4 (module_development_agent.py:158-162)
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn"],
)

# Stage 5 (deployment_wrapper_agent.py:162-166)
tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=["mslearn"],
)
```

### 3. Format-Specific Parsing (Bicep vs Terraform) ✅
**Status**: GOOD

Stage 4 correctly branches based on format:
```python
# module_development_agent.py:540-543
if self.iac_format == "terraform":
    files = self._parse_terraform_files(generated_code, output_dir)
else:
    files = self._parse_bicep_files(generated_code, output_dir)
```

---

## ⚠️ ISSUES FOUND

### 1. **CRITICAL: Embedded Prompts in Stage 5** ❌
**Status**: NON-COMPLIANT

**Problem**: Stage 5 has large embedded prompt strings in code:
- **File**: `deployment_wrapper_agent.py`
- **Lines**: 458-808 (350+ lines of embedded prompt text)
- **Methods**:
  - `_build_naming_module_prompt()` (lines 458-788)
  - `_build_environment_prompt()` (lines 784-859)

**Evidence**:
```python
# deployment_wrapper_agent.py:507-514
return f"""
Generate a standalone CAF-compliant naming module (custom implementation, not importing AVM).
{resource_section}
{constraints_section}

## CRITICAL Requirements

### 1. Research AVM Naming Patterns for GUIDANCE ONLY (MANDATORY FIRST STEP)
... [300+ more lines of embedded prompt text]
"""
```

**Impact**:
- ❌ **Not externalized**: Violates "all instructions and prompts are not embedded in codebase"
- ❌ **Hard to maintain**: Changes require code edits, not YAML edits
- ❌ **Version control**: Harder to track prompt evolution
- ❌ **Testing**: Cannot A/B test prompts without code changes

**Recommendation**: **URGENT - Move to YAML**
```yaml
# Should be in iac_agent_instructions.yaml
deployment_wrapper_agent:
  prompts:
    naming_module_generation: |
      Generate a standalone CAF-compliant naming module...
      [full prompt text here]
    
    environment_generation: |
      Generate {environment} deployment orchestration...
      [full prompt text here]
```

---

### 2. **MODERATE: Inconsistent Parsing Patterns** ⚠️
**Status**: PARTIALLY COMPLIANT

**Problem**: Stage 4 and Stage 5 use different response parsing approaches.

**Stage 4 (module_development_agent.py)**:
```python
# Lines 523-526
last_msg = self.agents_client.messages.get_last_message_text_by_role(
    thread_id=self.thread.id,
    role=MessageRole.AGENT,
)
generated_code = last_msg.text.value
```

**Stage 5 (deployment_wrapper_agent.py)**:
```python
# Lines 346-355 (naming module)
last_msg = self.agents_client.messages.get_last_message_text_by_role(
    thread_id=self.thread.id,
    role=MessageRole.AGENT,
)
response_text = last_msg.text.value
naming_data = self._parse_json_response(response_text)

# Lines 423-432 (environment)
last_msg = self.agents_client.messages.get_last_message_text_by_role(
    thread_id=self.thread.id,
    role=MessageRole.AGENT,
)
response_text = last_msg.text.value
env_data = self._parse_json_response(response_text)
```

**Analysis**:
- ✅ **Similar API usage**: Both use `get_last_message_text_by_role()` correctly
- ⚠️ **Different output expectations**:
  - Stage 4 expects code with `FILE:` markers
  - Stage 5 expects JSON with `{"files": {...}}`
- ⚠️ **Different parsing logic**:
  - Stage 4: `_parse_terraform_files()` / `_parse_bicep_files()` (line-by-line parser)
  - Stage 5: `_parse_json_response()` (JSON extractor)

**Impact**: Minor - Both approaches work, but not unified

**Recommendation**: Standardize on JSON response format for both stages
```python
# Unified response format
{
  "files": {
    "filename": "content"
  },
  "metadata": { ... }
}
```

---

### 3. **MINOR: No Static Mappings** ✅
**Status**: COMPLIANT

**Finding**: No hardcoded service-to-module mappings found.
- ✅ Stage 3 (Module Mapping Agent) generates mappings dynamically
- ✅ Stage 4 receives mappings as input, no static defaults
- ✅ Stage 5 receives module_mappings from Stage 3 results

**Evidence**:
```python
# workflow_phase2.py:493-503 (Stage 4)
module_result = await module_dev_agent.generate_modules(
    mappings=mapping_result.mappings,  # Dynamic from Stage 3
    output_dir=output_dir,
    progress_callback=...
)

# workflow_phase2.py:641 (Stage 5)
wrapper_result = await wrapper_agent.generate_deployment_wrappers(
    module_mappings=[m.to_dict() for m in mapping_result.mappings],  # From Stage 3
    ...
)
```

---

### 4. **MINOR: Format-Specific MCP Server Usage** ⚠️
**Status**: PARTIALLY IMPLEMENTED

**Finding**: CodeQualityAgent uses format-specific MCP, but Stage 4/5 don't.

**CodeQualityAgent** (code_quality_agent.py:97-101):
```python
mcp_servers = ["mslearn"]
if self.iac_format == "bicep":
    mcp_servers.append("bicep")  # Bicep-specific MCP
elif self.iac_format == "terraform":
    mcp_servers.append("terraform")  # Terraform-specific MCP
```

**Stage 4 & 5**: Only use `["mslearn"]` - generic MCP server

**Impact**: 
- ⚠️ Stage 4/5 miss format-specific tools for module generation
- ⚠️ Naming module prompt references "Bicep MCP" and "Terraform MCP" but they're not enabled

**Recommendation**: Apply same pattern to Stage 4 & 5
```python
# module_development_agent.py and deployment_wrapper_agent.py
mcp_servers = ["mslearn"]
if self.iac_format == "bicep":
    mcp_servers.append("bicep")
elif self.iac_format == "terraform":
    mcp_servers.append("terraform")

tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=mcp_servers,
)
```

---

## 📊 COMPLIANCE SCORECARD

| Requirement | Stage 4 | Stage 5 | Overall |
|------------|---------|---------|---------|
| **Similar patterns for Bicep/Terraform** | ✅ Good | ✅ Good | ✅ **PASS** |
| **Consistent instructions (no conflicts)** | ✅ Excellent | ✅ Good | ✅ **PASS** |
| **No static mappings** | ✅ Excellent | ✅ Excellent | ✅ **PASS** |
| **Instructions not embedded in code** | ✅ Excellent | ❌ **CRITICAL** | ❌ **FAIL** |

**Overall Grade**: 🔴 **NON-COMPLIANT** (1 critical issue)

---

## 🔧 RECOMMENDED FIXES

### Priority 1: CRITICAL - Externalize Stage 5 Prompts
**Impact**: High | **Effort**: Medium

**Action Items**:
1. Move `_build_naming_module_prompt()` content to `iac_agent_instructions.yaml`
2. Move `_build_environment_prompt()` content to `iac_agent_instructions.yaml`
3. Update `deployment_wrapper_agent.py` to load from YAML
4. Add unit tests for prompt loading

**Implementation**:
```yaml
# iac_agent_instructions.yaml
deployment_wrapper_agent:
  instructions: |
    [Base instructions remain]
  
  prompts:
    naming_module_generation:
      template: |
        Generate a standalone CAF-compliant naming module...
        {resource_section}
        {constraints_section}
        [full prompt]
      
      variables:
        - resource_section
        - constraints_section
    
    environment_generation:
      template: |
        Generate deployment orchestration for {env_name}...
        {module_mappings}
        {phase1_data}
        [full prompt]
      
      variables:
        - env_name
        - module_mappings
        - phase1_data
        - naming_module_available
```

```python
# deployment_wrapper_agent.py
def _build_naming_module_prompt(self, phase1_data: Dict[str, Any]) -> str:
    """Build prompt for naming module generation."""
    # Build dynamic sections
    resource_section = self._build_resource_section(phase1_data)
    constraints_section = self._build_constraints_section(phase1_data)
    
    # Load template from YAML
    template = get_prompt_template("naming_module_generation")
    
    # Format with dynamic data
    return template.format(
        resource_section=resource_section,
        constraints_section=constraints_section
    )
```

---

### Priority 2: MEDIUM - Add Format-Specific MCP to Stage 4/5
**Impact**: Medium | **Effort**: Low

**Action Items**:
1. Update `module_development_agent.py` MCP setup (line 158)
2. Update `deployment_wrapper_agent.py` MCP setup (line 162)
3. Test with Bicep/Terraform specific tools enabled

**Implementation**:
```python
# module_development_agent.py:158-167
mcp_servers = ["mslearn"]
if self.iac_format == "bicep":
    mcp_servers.append("bicep")
elif self.iac_format == "terraform":
    mcp_servers.append("terraform")

self.tool_config = create_agent_toolset(
    include_bing=True,
    include_mcp=True,
    mcp_servers=mcp_servers,
)
```

---

### Priority 3: LOW - Standardize Response Format
**Impact**: Low | **Effort**: High

**Action Items**:
1. Update Stage 4 instructions to return JSON format
2. Unify `_parse_terraform_files()` and `_parse_bicep_files()` to handle JSON
3. Update YAML instructions for consistent format expectations

---

## 📈 METRICS & VALIDATION

### Code Statistics
- **Total embedded prompt lines**: ~350 lines
- **Prompt locations**: 2 methods in `deployment_wrapper_agent.py`
- **Externalized instructions**: ~95% (Stage 4 = 100%, Stage 5 base = 100%, Stage 5 prompts = 0%)

### Test Coverage Gaps
- ❌ No unit tests for embedded prompts
- ❌ No validation that prompts match YAML
- ✅ Integration tests exist for agent workflows

---

## 🎯 CONCLUSION

**Current State**: 
- Architecture is **strong** for Stage 4 (fully externalized)
- Architecture has **critical gap** in Stage 5 (embedded prompts)

**Priority Actions**:
1. 🔴 **URGENT**: Externalize Stage 5 prompts to YAML (blocks compliance)
2. 🟡 **IMPORTANT**: Add format-specific MCP servers to Stage 4/5
3. 🟢 **NICE-TO-HAVE**: Standardize JSON response format

**Timeline**:
- Priority 1: **1-2 days** (critical path)
- Priority 2: **2-4 hours** (quick win)
- Priority 3: **3-5 days** (long-term improvement)

---

## 📚 REFERENCES

### Files Analyzed
- `synthforge/agents/module_development_agent.py` (875 lines)
- `synthforge/agents/deployment_wrapper_agent.py` (880 lines)
- `synthforge/agents/code_quality_agent.py` (132 lines)
- `synthforge/prompts/__init__.py` (262 lines)
- `synthforge/prompts/iac_agent_instructions.yaml`
- `synthforge/workflow_phase2.py` (808 lines)

### Key Methods
- `module_development_agent.generate_modules()` (lines 187-325)
- `deployment_wrapper_agent.generate_deployment_wrappers()` (lines 197-278)
- `deployment_wrapper_agent._build_naming_module_prompt()` (lines 458-788)
- `deployment_wrapper_agent._build_environment_prompt()` (lines 784-859)

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-08  
**Next Review**: After Priority 1 fixes implemented

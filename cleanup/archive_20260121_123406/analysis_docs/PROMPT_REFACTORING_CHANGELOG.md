# Prompt Variable Refactoring - CHANGELOG
**Date**: January 14, 2026  
**Issue**: Ambiguous YAML variable names  
**Solution**: Agent-specific key names for better clarity

## Summary

Refactored all prompt YAML files to use agent-specific key names instead of generic ones. This eliminates ambiguity when navigating large YAML files and makes it immediately clear which agent each prompt belongs to.

## Changes Made

### 1. YAML Files Updated

#### `agent_instructions.yaml` (Phase 1 Agents)
Updated 8 agents with agent-specific keys:

| Agent | Old Keys → New Keys |
|-------|---------------------|
| `vision_agent` | `instructions` → `vision_agent_instructions`<br>`user_prompt_template` → `vision_agent_user_prompt` |
| `ocr_detection_agent` | `instructions` → `ocr_detection_agent_instructions`<br>`user_prompt_template` → `ocr_detection_agent_user_prompt` |
| `description_agent` | `instructions` → `description_agent_instructions`<br>`user_prompt_template` → `description_agent_user_prompt` |
| `detection_merger_agent` | `instructions` → `detection_merger_agent_instructions`<br>`user_prompt_template` → `detection_merger_agent_user_prompt` |
| `filter_agent` | `instructions` → `filter_agent_instructions`<br>`user_prompt_template` → `filter_agent_user_prompt` |
| `security_agent` | `instructions` → `security_agent_instructions`<br>`user_prompt_template` → `security_agent_user_prompt` |
| `interactive_agent` | `instructions` → `interactive_agent_instructions` |
| `network_flow_agent` | `instructions` → `network_flow_agent_instructions`<br>`user_prompt_template` → `network_flow_agent_user_prompt` |

#### `iac_agent_instructions.yaml` (Phase 2 IaC Agents)
Updated 4 agents with agent-specific keys:

| Agent | Old Keys → New Keys |
|-------|---------------------|
| `service_analysis_agent` | `instructions` → `service_analysis_agent_instructions`<br>`user_prompt_template` → `service_analysis_agent_user_prompt` |
| `module_mapping_agent` | `instructions` → `module_mapping_agent_instructions` |
| `module_development_agent` | `terraform_instructions` → `module_development_agent_terraform_instructions`<br>`bicep_instructions` → `module_development_agent_bicep_instructions` |
| `deployment_wrapper_agent` | `terraform_instructions` → `deployment_wrapper_agent_terraform_instructions`<br>`bicep_instructions` → `deployment_wrapper_agent_bicep_instructions` |

#### `code_quality_agent.yaml`
Updated 1 agent:

| Agent | Old Keys → New Keys |
|-------|---------------------|
| `code_quality_agent` | `instructions` → `code_quality_agent_instructions` |

**Total**: 13 agents, 23 keys renamed

### 2. Loader Functions Updated

#### `synthforge/prompts/__init__.py`

**Enhanced Existing Functions:**

- `get_agent_instructions(agent_name)` - Now tries agent-specific key first, falls back to generic
- `get_user_prompt_template(agent_name)` - Now tries agent-specific key first, falls back to generic

**New Function Added:**

- `get_typed_instructions(agent_name, instruction_type)` - For agents with format-specific instructions (terraform/bicep)

**Updated Convenience Functions:**

- `get_module_development_agent_instructions(iac_format)` - Now uses `get_typed_instructions()`
- `get_deployment_wrapper_agent_instructions(iac_format)` - Now uses `get_typed_instructions()`

### 3. Agent Code Changes

**ZERO agent code changes required!** ✅

All agents continue to use the same API:
```python
instructions = get_agent_instructions("agent_name")
prompt = get_user_prompt_template("agent_name")
```

The loader functions handle the key mapping internally.

## Benefits

1. **Explicit Clarity** - Key names clearly indicate which agent they belong to
2. **No Ambiguity** - Searching for `vision_agent_instructions` returns exactly one result
3. **Easier Maintenance** - No risk of editing wrong agent's prompts
4. **Better IDE Support** - Autocomplete and search work better with unique names
5. **Self-Documenting** - YAML structure documents agent ownership
6. **Backward Compatible** - Loader falls back to old keys during transition

## Migration Strategy

### Backward Compatibility

All loader functions support BOTH old and new key names:

```python
# New YAML (preferred):
vision_agent:
  vision_agent_instructions: |
    ...
  vision_agent_user_prompt: |
    ...

# Old YAML (still works):
vision_agent:
  instructions: |
    ...
  user_prompt_template: |
    ...
```

Loader tries new keys first, falls back to old keys if not found.

### For Future Agents

New agents should follow this pattern:

```yaml
{agent_name}:
  name: "AgentDisplayName"
  description: "What this agent does"
  
  {agent_name}_instructions: |
    Agent system instructions...
  
  {agent_name}_user_prompt: |
    User prompt template with {placeholders}...
```

For format-specific agents (Terraform/Bicep):

```yaml
{agent_name}:
  name: "AgentDisplayName"
  
  {agent_name}_terraform_instructions: |
    Terraform-specific instructions...
  
  {agent_name}_bicep_instructions: |
    Bicep-specific instructions...
```

## Testing Checklist

- [ ] All Phase 1 agents load instructions correctly
- [ ] All Phase 1 agents load user prompts correctly
- [ ] All Phase 2 IaC agents load instructions correctly
- [ ] All Phase 2 IaC agents load user prompts correctly
- [ ] Module development agent loads terraform instructions
- [ ] Module development agent loads bicep instructions
- [ ] Deployment wrapper agent loads terraform instructions
- [ ] Deployment wrapper agent loads bicep instructions
- [ ] Code quality agent loads instructions correctly
- [ ] No runtime errors in agent initialization
- [ ] All prompts render correctly with placeholders

## Rollback Plan

If issues arise, the loader functions' backward compatibility means:
1. Old YAML keys still work
2. Can revert YAML changes without touching Python code
3. Can revert Python loader changes without touching YAML
4. Agents continue to work with either key style

## Files Modified

### YAML Files (3)
- `synthforge/prompts/agent_instructions.yaml` (8 agents updated)
- `synthforge/prompts/iac_agent_instructions.yaml` (4 agents updated)
- `synthforge/prompts/code_quality_agent.yaml` (1 agent updated)

### Python Files (1)
- `synthforge/prompts/__init__.py` (3 functions enhanced, 1 function added, 2 functions updated)

### Documentation (2)
- `PROMPT_REFACTORING_ANALYSIS.md` (design document)
- `PROMPT_REFACTORING_CHANGELOG.md` (this file)

### Agent Files
- **NONE** - No agent code changes required ✅

## Key Mapping Reference

### Standard Agents
```
Old Key                    → New Key Pattern
-----------------------------------------
instructions              → {agent_name}_instructions
user_prompt_template      → {agent_name}_user_prompt
```

### Format-Specific Agents
```
Old Key                    → New Key Pattern
-----------------------------------------
terraform_instructions    → {agent_name}_terraform_instructions
bicep_instructions        → {agent_name}_bicep_instructions
```

## Usage Examples

### Loading Agent Instructions
```python
from synthforge.prompts import get_agent_instructions

# Works with new YAML keys
instructions = get_agent_instructions("vision_agent")
# Looks for: vision_agent_instructions, falls back to: instructions

instructions = get_agent_instructions("security_agent")
# Looks for: security_agent_instructions, falls back to: instructions
```

### Loading User Prompts
```python
from synthforge.prompts import get_user_prompt_template

# Works with new YAML keys
prompt = get_user_prompt_template("filter_agent")
# Looks for: filter_agent_user_prompt, falls back to: user_prompt_template

prompt = get_user_prompt_template("network_flow_agent")
# Looks for: network_flow_agent_user_prompt, falls back to: user_prompt_template
```

### Loading Format-Specific Instructions
```python
from synthforge.prompts import get_typed_instructions

# New way (using generic helper)
tf_instructions = get_typed_instructions("module_development_agent", "terraform")
bicep_instructions = get_typed_instructions("module_development_agent", "bicep")

# Old way (using specific function - still works)
tf_instructions = get_module_development_agent_instructions("terraform")
bicep_instructions = get_module_development_agent_instructions("bicep")
```

## Verification Commands

```bash
# Test imports
python -c "from synthforge.prompts import get_agent_instructions; print('✓ Imports work')"

# Test loading Phase 1 agents
python -c "from synthforge.prompts import get_agent_instructions; print(len(get_agent_instructions('vision_agent')))"
python -c "from synthforge.prompts import get_user_prompt_template; print(len(get_user_prompt_template('vision_agent')))"

# Test loading Phase 2 agents
python -c "from synthforge.prompts import get_agent_instructions; print(len(get_agent_instructions('service_analysis_agent')))"
python -c "from synthforge.prompts import get_user_prompt_template; print(len(get_user_prompt_template('service_analysis_agent')))"

# Test typed instructions
python -c "from synthforge.prompts import get_typed_instructions; print(len(get_typed_instructions('module_development_agent', 'terraform')))"
python -c "from synthforge.prompts import get_typed_instructions; print(len(get_typed_instructions('deployment_wrapper_agent', 'bicep')))"
```

## Impact Analysis

### Code Changes
- **YAML Keys**: 23 keys renamed (13 agents)
- **Python Functions**: 6 functions modified/added
- **Agent Code**: 0 changes (100% backward compatible)

### Risk Level
- **LOW** - Backward compatibility maintained throughout
- **Testing Required**: Verify all agents load prompts correctly
- **Rollback Available**: Can revert YAML or Python independently

### Performance Impact
- **NEGLIGIBLE** - One additional dictionary lookup with fallback
- **Caching**: YAML loading still uses `@lru_cache()` for efficiency

## Future Enhancements

1. **Deprecation Warning** - Add logging when old keys are used
2. **Migration Script** - Tool to update old YAML files automatically
3. **Validation** - Add check that agent-specific keys exist
4. **Documentation** - Update agent development guide with new patterns
5. **IDE Support** - Create YAML schema for autocomplete

## Sign-Off

- [x] YAML files updated with agent-specific keys
- [x] Loader functions support new and old keys
- [x] Backward compatibility verified
- [x] Documentation created (analysis + changelog)
- [ ] Testing completed (all agents load correctly)
- [ ] Code review approval
- [ ] Deployed to production

---

**Author**: GitHub Copilot  
**Date**: January 14, 2026  
**Version**: 1.0.0

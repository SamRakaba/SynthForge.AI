# Prompt Variable Refactoring Analysis
**Date**: January 14, 2026  
**Objective**: Remove ambiguity in YAML variable names by making them agent-specific

## Problem Statement

Currently, all agents use generic YAML keys:
- `instructions:` - Used by every agent
- `user_prompt_template:` - Used by agents with user prompts

This creates ambiguity when:
1. Scrolling through large YAML files (which `instructions` am I looking at?)
2. Searching for specific agent prompts (many matches for "instructions:")
3. Maintaining and updating prompts (easy to edit wrong section)

## Current Structure

### agent_instructions.yaml (Phase 1 Agents)
```yaml
vision_agent:
  name: "VisionAgent"
  instructions: |
    ...
  user_prompt_template: |
    ...

ocr_detection_agent:
  name: "OCRDetectionAgent"
  instructions: |
    ...
  user_prompt_template: |
    ...

# Pattern repeated for all agents
```

**Agents in this file:**
1. `vision_agent` - Icon detection (has both)
2. `ocr_detection_agent` - Text detection (has both)
3. `description_agent` - Free-form analysis (has both)
4. `detection_merger_agent` - Merge detections (has both)
5. `filter_agent` - Resource filtering (has both)
6. `security_agent` - Security analysis (has both)
7. `network_flow_agent` - Network flows (has both)
8. `interactive_agent` - User clarification (instructions only)

### iac_agent_instructions.yaml (Phase 2 IaC Agents)
```yaml
service_analysis_agent:
  name: "Azure Service Requirements Analyst"
  instructions: |
    ...
  user_prompt_template: |
    ...

module_mapping_agent:
  name: "ModuleMappingAgent"
  instructions: |
    ...
  # No user_prompt_template (uses dynamic prompts)

module_development_agent:
  name: "ModuleDevelopmentAgent"
  terraform_instructions: |  # Already agent-specific!
    ...
  bicep_instructions: |      # Already agent-specific!
    ...
  # No user_prompt_template

deployment_wrapper_agent:
  name: "DeploymentWrapperAgent"
  terraform_instructions: |  # Already agent-specific!
    ...
  bicep_instructions: |      # Already agent-specific!
    ...
```

**Agents in this file:**
1. `service_analysis_agent` - Service requirements (has both)
2. `module_mapping_agent` - Module mapping (instructions only)
3. `module_development_agent` - Code generation (terraform_instructions, bicep_instructions)
4. `deployment_wrapper_agent` - Deployment wrapper (terraform_instructions, bicep_instructions)

### code_quality_agent.yaml
```yaml
code_quality_agent:
  name: "CodeQualityAgent"
  instructions: |
    ...
  # No user_prompt_template
```

**Agent:**
1. `code_quality_agent` - Code validation (instructions only)

## Proposed Solution

### Naming Convention
Replace generic keys with agent-specific keys:
- `instructions` → `{agent_name}_instructions`
- `user_prompt_template` → `{agent_name}_user_prompt`

Examples:
```yaml
vision_agent:
  name: "VisionAgent"
  vision_agent_instructions: |      # Was: instructions
    ...
  vision_agent_user_prompt: |       # Was: user_prompt_template
    ...

ocr_detection_agent:
  name: "OCRDetectionAgent"
  ocr_detection_agent_instructions: |
    ...
  ocr_detection_agent_user_prompt: |
    ...
```

### Special Cases

**module_development_agent** and **deployment_wrapper_agent** already have specific keys:
- `terraform_instructions` → `{agent_name}_terraform_instructions`
- `bicep_instructions` → `{agent_name}_bicep_instructions`

Updated:
```yaml
module_development_agent:
  module_development_agent_terraform_instructions: |
    ...
  module_development_agent_bicep_instructions: |
    ...
```

## Implementation Plan

### Step 1: Update YAML Files
For each agent section, rename keys:
1. `agent_instructions.yaml` - 8 agents
2. `iac_agent_instructions.yaml` - 4 agents  
3. `code_quality_agent.yaml` - 1 agent

### Step 2: Update Loader Functions
Modify `synthforge/prompts/__init__.py`:

**Current loader logic:**
```python
def get_agent_instructions(agent_name: str) -> str:
    config = get_agent_config(agent_name)
    return config.get("instructions", "")

def get_user_prompt_template(agent_name: str) -> str:
    config = get_agent_config(agent_name)
    return config.get("user_prompt_template", "")
```

**New loader logic:**
```python
def get_agent_instructions(agent_name: str) -> str:
    config = get_agent_config(agent_name)
    # Try agent-specific key first, fallback to generic for compatibility
    key = f"{agent_name}_instructions"
    return config.get(key, config.get("instructions", ""))

def get_user_prompt_template(agent_name: str) -> str:
    config = get_agent_config(agent_name)
    # Try agent-specific key first
    key = f"{agent_name}_user_prompt"
    return config.get(key, config.get("user_prompt_template", ""))
```

### Step 3: No Agent Code Changes Required!
Since agents call `get_agent_instructions('agent_name')` and the loader constructs the key dynamically, **NO agent code changes needed**.

Example (existing code continues to work):
```python
# vision_agent.py
instructions = get_agent_instructions("vision_agent")
# Loader will look for "vision_agent_instructions" in YAML

prompt = get_user_prompt_template("vision_agent")  
# Loader will look for "vision_agent_user_prompt" in YAML
```

### Step 4: Special Function for IaC Type-Specific Instructions
For `module_development_agent` and `deployment_wrapper_agent`:

```python
def get_typed_instructions(agent_name: str, instruction_type: str) -> str:
    """Get type-specific instructions (terraform, bicep, etc.)"""
    config = get_agent_config(agent_name)
    key = f"{agent_name}_{instruction_type}_instructions"
    return config.get(key, "")

# Usage:
tf_instructions = get_typed_instructions("module_development_agent", "terraform")
bicep_instructions = get_typed_instructions("module_development_agent", "bicep")
```

## Benefits

1. **Explicit Clarity**: Each key name clearly indicates which agent it belongs to
2. **No Ambiguity**: Searching for "vision_agent_instructions" returns exactly one result
3. **Easier Maintenance**: No risk of editing the wrong agent's prompts
4. **Better IDE Support**: Autocomplete and search work better with unique names
5. **Self-Documenting**: YAML structure itself documents agent ownership
6. **Backward Compatible**: Loader can fall back to old keys during transition

## Migration Checklist

- [ ] Update agent_instructions.yaml (8 agents)
- [ ] Update iac_agent_instructions.yaml (4 agents)
- [ ] Update code_quality_agent.yaml (1 agent)
- [ ] Update __init__.py loader functions
- [ ] Add get_typed_instructions() for IaC agents
- [ ] Verify all agents load correctly (run tests)
- [ ] Update this document with "COMPLETED" status
- [ ] Create CHANGELOG.md entry

## Agent-by-Agent Mapping

### Phase 1 Agents (agent_instructions.yaml)

| Agent | Old Keys | New Keys |
|-------|----------|----------|
| vision_agent | instructions<br>user_prompt_template | vision_agent_instructions<br>vision_agent_user_prompt |
| ocr_detection_agent | instructions<br>user_prompt_template | ocr_detection_agent_instructions<br>ocr_detection_agent_user_prompt |
| description_agent | instructions<br>user_prompt_template | description_agent_instructions<br>description_agent_user_prompt |
| detection_merger_agent | instructions<br>user_prompt_template | detection_merger_agent_instructions<br>detection_merger_agent_user_prompt |
| filter_agent | instructions<br>user_prompt_template | filter_agent_instructions<br>filter_agent_user_prompt |
| security_agent | instructions<br>user_prompt_template | security_agent_instructions<br>security_agent_user_prompt |
| network_flow_agent | instructions<br>user_prompt_template | network_flow_agent_instructions<br>network_flow_agent_user_prompt |
| interactive_agent | instructions | interactive_agent_instructions |

### Phase 2 IaC Agents (iac_agent_instructions.yaml)

| Agent | Old Keys | New Keys |
|-------|----------|----------|
| service_analysis_agent | instructions<br>user_prompt_template | service_analysis_agent_instructions<br>service_analysis_agent_user_prompt |
| module_mapping_agent | instructions | module_mapping_agent_instructions |
| module_development_agent | terraform_instructions<br>bicep_instructions | module_development_agent_terraform_instructions<br>module_development_agent_bicep_instructions |
| deployment_wrapper_agent | terraform_instructions<br>bicep_instructions | deployment_wrapper_agent_terraform_instructions<br>deployment_wrapper_agent_bicep_instructions |

### Code Quality Agent (code_quality_agent.yaml)

| Agent | Old Keys | New Keys |
|-------|----------|----------|
| code_quality_agent | instructions | code_quality_agent_instructions |

## Total Changes

- **YAML Files**: 3 files
- **Total Agents**: 13 agents
- **Keys to Rename**: 23 keys
  - 15 × `instructions` → `{agent}_instructions`
  - 2 × `terraform_instructions` → `{agent}_terraform_instructions`
  - 2 × `bicep_instructions` → `{agent}_bicep_instructions`
  - 8 × `user_prompt_template` → `{agent}_user_prompt`
- **Python Files**: 1 file (`__init__.py`)
- **Agent Code Changes**: 0 (loader handles key construction)

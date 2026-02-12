# Hardcode Remediation Status

## Summary
Fixed 4 violations of "no prompts in code" architecture rule by moving hardcoded prompts to YAML configuration files.

## Progress: ✅ 100% COMPLETE

### ✅ All Tasks Completed

#### 1. Added Templates to YAML Files (100% Complete)
- ✅ **agent_instructions.yaml**:
  - description_agent.context_hints_template (line 647)
  - filter_agent.foundational_services_guidance (line 983)
  
- ✅ **iac_agent_instructions.yaml**:
  - deployment_wrapper templates in prompt_templates section (lines 1751-1829)
  - code_quality_agent.validation_analysis_prompt_template (line 1837)

**Status:** All YAML files parse correctly, all templates accessible

#### 2. Updated Python Code (100% Complete)
All Python files updated to load from YAML instead of hardcoding:

- ✅ **deployment_wrapper_agent.py**: Uses `get_iac_prompt_template()` for 4 templates
- ✅ **description_agent.py**: Loads context_hints_template from YAML
- ✅ **filter_agent.py**: Loads foundational_services_guidance from YAML
- ✅ **code_quality_agent.py**: Loads validation_analysis_prompt_template from YAML

**Status:** All files compile successfully, all templates load correctly

#### 3. Validation Complete (100% Complete)
```
Phase 1 Agents:
  ✓ description_agent.context_hints_template (532 chars)
  ✓ filter_agent.foundational_services_guidance (623 chars)

Phase 2 Agents (IaC):
  ✓ deployment_wrapper.categorization (993 chars)
  ✓ deployment_wrapper.category_file_generation (900 chars)
  ✓ deployment_wrapper.main_file_generation (680 chars)
  ✓ deployment_wrapper.supporting_files_generation (554 chars)
  ✓ code_quality_agent.validation_analysis (722 chars)

✅ All 7 templates loaded successfully!
```

## Architecture Decision

**Template Location Strategy:**
- **Phase 1 agent templates**: Stored as keys within each agent's section in `agent_instructions.yaml`
- **Phase 2 deployment_wrapper templates**: Stored in global `prompt_templates` section in `iac_agent_instructions.yaml`
- **Phase 2 code_quality_agent template**: Stored as key within agent's section in `iac_agent_instructions.yaml`

**Rationale:**
The iac_agent_instructions.yaml file uses escaped string format for historical reasons. Rather than refactor the entire file (600+ lines of escaped strings), templates were added using the existing `prompt_templates` section pattern for deployment_wrapper_agent, while code_quality_agent follows the per-agent template pattern.

## Files Modified

### YAML Configuration Files
1. ✅ `synthforge/prompts/agent_instructions.yaml`
   - Added context_hints_template to description_agent
   - Added foundational_services_guidance to filter_agent
   - Status: Valid YAML, all templates accessible

2. ✅ `synthforge/prompts/iac_agent_instructions.yaml`
   - Added 4 templates to prompt_templates section (deployment_wrapper)
   - Added 1 template to code_quality_agent section
   - Status: Valid YAML, all templates accessible

### Python Source Files
3. ✅ `synthforge/prompts/__init__.py`
   - Added get_prompt_template() function (line 224)
   - Fixed duplicate function name (renamed to get_iac_prompt_template)
   - Status: Compiles successfully

4. ✅ `synthforge/agents/deployment_wrapper_agent.py`
   - Updated 4 methods to load prompts from YAML using get_iac_prompt_template()
   - Status: Compiles successfully

5. ✅ `synthforge/agents/description_agent.py`
   - Updated to_context_hints() to load template from YAML
   - Status: Compiles successfully

6. ✅ `synthforge/agents/filter_agent.py`
   - Updated filter() to load guidance from YAML
   - Status: Compiles successfully

7. ✅ `synthforge/agents/code_quality_agent.py`
   - Updated _build_fix_prompt_fallback() to load template from YAML
   - Status: Compiles successfully

## Validation Complete

### Compilation
```bash
python -m py_compile synthforge/agents/deployment_wrapper_agent.py \
                     synthforge/agents/description_agent.py \
                     synthforge/agents/filter_agent.py \
                     synthforge/agents/code_quality_agent.py \
                     synthforge/prompts/__init__.py
# ✅ All files compile successfully
```

### Template Loading
```python
from synthforge.prompts import get_prompt_template, get_iac_prompt_template

# All 7 templates load without errors
# Phase 1: description_agent, filter_agent
# Phase 2: deployment_wrapper (4 templates), code_quality_agent
```

### YAML Parsing
```bash
python -c "import yaml; yaml.safe_load(open('synthforge/prompts/agent_instructions.yaml', encoding='utf-8'))"
# ✅ Valid YAML

python -c "import yaml; yaml.safe_load(open('synthforge/prompts/iac_agent_instructions.yaml', encoding='utf-8'))"
# ✅ Valid YAML
```

## Architecture Compliance

✅ **100% compliant** with the "no prompts in code" rule:

- ✅ All agent instructions in YAML
- ✅ All prompt templates in YAML
- ✅ No static service mappings
- ✅ Agent-first decision making preserved
- ✅ Position-based resource matching maintained
- ✅ No hardcoded prompts remain in Python code

## Next Steps

With hardcode remediation complete, the system is ready for:

1. **Phase 1 Pipeline Testing**: Verify detection → filter → interactive → network → security
2. **Phase 2 Pipeline Testing**: Verify service analysis → module mapping → module development → deployment wrappers
3. **Behavioral Validation**: Confirm categorization, file generation, and code quality validation produce expected outputs
4. **Documentation**: Update developer guide with template loading patterns for future additions

### ✅ Completed

#### 1. Added Templates to agent_instructions.yaml (100% Complete)
- ✅ **description_agent.context_hints_template** - Line 647
- ✅ **filter_agent.foundational_services_guidance** - Line 983

**Status:** YAML parses correctly, templates accessible

#### 2. Updated Python Code (100% Complete)
All 4 Python files updated to load from YAML instead of hardcoding:

- ✅ **deployment_wrapper_agent.py**:
  - Line ~363: Loads categorization_prompt_template
  - Line ~463: Loads category_file_generation_prompt_template
  - Line ~632: Loads main_file_generation_prompt_template
  - Line ~704: Loads supporting_files_generation_prompt_template

- ✅ **description_agent.py**:
  - Line ~114: Loads context_hints_template from YAML

- ✅ **filter_agent.py**:
  - Line ~145: Loads foundational_services_guidance from YAML

- ✅ **code_quality_agent.py**:
  - Line ~328: Loads validation_analysis_prompt_template from YAML

**Status:** All files compile successfully

#### 3. Added Helper Function (100% Complete)
- ✅ Added `get_prompt_template(agent_name, template_key, from_iac=False)` to prompts/__init__.py (line 224)
- ✅ Fixed duplicate function name: Renamed second `get_prompt_template` to `get_iac_prompt_template`

**Status:** Function works correctly for agent_instructions.yaml templates

### ⚠️ Remaining Issue

#### iac_agent_instructions.yaml Parse Error
**Problem:** YAML parsing error at line 1768
```
yaml.parser.ParserError: while parsing a block mapping
  in "synthforge/prompts/iac_agent_instructions.yaml", line 1445, column 3
expected <block end>, but found '<scalar>'
  in "synthforge/prompts/iac_agent_instructions.yaml", line 1768, column 8
```

**Root Cause:** When adding templates to deployment_wrapper_agent section, they were accidentally inserted INSIDE the `deployment_wrapper_agent_bicep_instructions` string literal instead of as separate YAML keys.

**What Needs to Happen:**
The 4 templates need to be added as proper YAML keys at the same indentation level as `deployment_wrapper_agent_bicep_instructions`.

### Required Fix for iac_agent_instructions.yaml

Find the end of the `deployment_wrapper_agent` section (after `deployment_wrapper_agent_bicep_instructions`), then add these 4 keys:

```yaml
deployment_wrapper_agent:
  name: DeploymentWrapperAgent
  description: ...
  deployment_wrapper_agent_terraform_instructions: "..."
  deployment_wrapper_agent_bicep_instructions: "..."
  
  # Add these 4 templates here (proper YAML keys, not inside strings):
  
  categorization_prompt_template: |
    Analyze these Azure services and categorize them into logical groups for infrastructure code organization.

    **Services to categorize:**
    {services_json}

    **Your task:**
    1. Group services into categories based on their ARM resource types and purposes
    2. Use standard Azure service categories (compute, data, ai, security, networking, monitoring, etc.)
    3. Each service should belong to exactly ONE category
    4. Return ONLY a JSON object mapping service names to categories

    **Response format (ONLY JSON, no other text):**
    ```json
    {
      "service-name-1": "category-name",
      "service-name-2": "category-name",
      ...
    }
    ```

    **Example categories:**
    - compute: App Services, Functions, Container Apps, VMs
    - data: Storage, Databases, Data Lakes, Search
    - ai: OpenAI, AI Foundry, Cognitive Services
    - security: Key Vault, Managed Identity, Encryption
    - networking: App Gateway, Firewall, VNet, Load Balancers
    - monitoring: Log Analytics, Application Insights, Diagnostics

    Return ONLY the JSON mapping.

  category_file_generation_prompt_template: |
    Generate {category}.{file_ext} file for {env_name} deployment.

    **CRITICAL INSTRUCTIONS**:
    1. **Learn from AVM first**: Use MCP tools to research Azure Verified Module patterns for these services
    2. **Validate parameters**: Ensure all parameters match Azure API and {iac_format} provider exactly
    3. **Generate ONLY this category**: Do not include resources from other categories
    4. **File structure**: Clear comments, grouped by service, 100-300 lines maximum
    5. **Module calls**: Use relative paths like ../modules/{{folder-name}}
    6. **Environment logic**: Use locals from main.{file_ext} for environment-specific values

    **Modules to include in this file**:
    {modules_json}

    **Phase 1 Recommendations** (apply as applicable):
    {recommendations_json}

    **Return ONLY** the file content (pure {iac_format} code, no JSON wrapper, no markdown fences).
    Start with category header comment and module calls.

  main_file_generation_prompt_template: |
    Generate main.{file_ext} entry point file for {env_name} deployment.

    **CRITICAL INSTRUCTIONS**:
    1. **Entry point ONLY**: 50 lines maximum
    2. **Include**:
       - Resource group creation
       - Naming module call (available: {naming_module_available})
       - Local variables for environment-specific logic (SKUs, sizes, HA settings)
       - Environment variable with validation
    3. **DO NOT include**: Module calls for services (those go in {category_files})
    4. **Environment logic**: Map environment to SKUs, backup retention, HA flags
    5. **Learn from AVM**: Use MCP tools to research naming patterns

    **Return ONLY** the file content (pure {iac_format} code, no JSON, no markdown fences).

  supporting_files_generation_prompt_template: |
    Generate supporting files for {env_name} deployment.

    **Files to generate:**
    1. variables.{file_ext} - All input parameters with descriptions and validation
    2. outputs.{file_ext} - Resource IDs, endpoints, connection strings
    3. backend.{file_ext} - Remote state configuration (Azure Storage)
    4. providers.{file_ext} - Provider version and configuration
    5. README.md - Deployment guide with prerequisites and steps

    **Required variables:**
    {required_vars_json}

    **Return ONLY** the file content (pure {iac_format} code for tf files, markdown for README).
```

**Location:** Add these between the end of `deployment_wrapper_agent_bicep_instructions` and the start of `code_quality_agent:` section (around line 1831).

### Validation Steps After Fix

```powershell
# 1. Validate YAML parses
python -c "import yaml; data = yaml.safe_load(open('synthforge/prompts/iac_agent_instructions.yaml', encoding='utf-8')); print('✓ YAML parses correctly'); print('deployment_wrapper_agent keys:', list(data['deployment_wrapper_agent'].keys()))"

# Expected output should include:
# ['name', 'description', 'deployment_wrapper_agent_terraform_instructions', 'deployment_wrapper_agent_bicep_instructions', 'categorization_prompt_template', 'category_file_generation_prompt_template', 'main_file_generation_prompt_template', 'supporting_files_generation_prompt_template']

# 2. Test template loading
python -c "from synthforge.prompts import get_prompt_template; t1 = get_prompt_template('deployment_wrapper_agent', 'categorization_prompt_template', from_iac=True); print(f'✓ categorization template ({len(t1)} chars)')"

# 3. Test all 4 templates load
python -c "
from synthforge.prompts import get_prompt_template
t1 = get_prompt_template('deployment_wrapper_agent', 'categorization_prompt_template', from_iac=True)
t2 = get_prompt_template('deployment_wrapper_agent', 'category_file_generation_prompt_template', from_iac=True)
t3 = get_prompt_template('deployment_wrapper_agent', 'main_file_generation_prompt_template', from_iac=True)
t4 = get_prompt_template('deployment_wrapper_agent', 'supporting_files_generation_prompt_template', from_iac=True)
t5 = get_prompt_template('description_agent', 'context_hints_template')
t6 = get_prompt_template('filter_agent', 'foundational_services_guidance')
t7 = get_prompt_template('code_quality_agent', 'validation_analysis_prompt_template', from_iac=True)
print('✓ All 7 templates loaded successfully')
"

# 4. Compile all Python files
python -m py_compile synthforge/agents/deployment_wrapper_agent.py synthforge/agents/description_agent.py synthforge/agents/filter_agent.py synthforge/agents/code_quality_agent.py synthforge/prompts/__init__.py

# 5. Run Phase 1 test (if input available)
# python main.py input/baseline-microsoft-foundry-landing-zone.png

# 6. Run Phase 2 test (if Phase 1 output available)
# python main.py --skip-phase1
```

### Post-Fix Verification Checklist

- [ ] iac_agent_instructions.yaml parses without errors
- [ ] deployment_wrapper_agent has 4 prompt template keys
- [ ] code_quality_agent.validation_analysis_prompt_template exists
- [ ] All 7 templates load successfully via get_prompt_template()
- [ ] All Python files compile without errors
- [ ] Phase 1 pipeline runs successfully (if test input available)
- [ ] Phase 2 pipeline runs successfully (if test data available)
- [ ] Categorization produces expected output
- [ ] File generation produces valid IaC code
- [ ] No hardcoded prompts remain in Python code

## Files Modified

### YAML Configuration Files
1. ✅ `synthforge/prompts/agent_instructions.yaml`
   - Added context_hints_template to description_agent
   - Added foundational_services_guidance to filter_agent
   - Status: Valid YAML

2. ⚠️ `synthforge/prompts/iac_agent_instructions.yaml`
   - Attempted to add 4 templates to deployment_wrapper_agent
   - Attempted to add 1 template to code_quality_agent
   - Status: Parse error - needs manual fix

### Python Source Files
3. ✅ `synthforge/prompts/__init__.py`
   - Added get_prompt_template() function
   - Fixed duplicate function name (renamed to get_iac_prompt_template)
   - Status: Compiles successfully

4. ✅ `synthforge/agents/deployment_wrapper_agent.py`
   - Updated 4 methods to load prompts from YAML
   - Status: Compiles successfully

5. ✅ `synthforge/agents/description_agent.py`
   - Updated to_context_hints() to load template from YAML
   - Status: Compiles successfully

6. ✅ `synthforge/agents/filter_agent.py`
   - Updated filter() to load guidance from YAML
   - Status: Compiles successfully

7. ✅ `synthforge/agents/code_quality_agent.py`
   - Updated _build_fix_prompt_fallback() to load template from YAML
   - Status: Compiles successfully

## Next Steps

1. **Fix iac_agent_instructions.yaml** (PRIORITY)
   - Manually correct the YAML structure
   - Ensure templates are proper keys, not embedded in strings
   - Validate it parses correctly

2. **Run validation tests**
   - Verify all templates load
   - Test Phase 1 and Phase 2 pipelines
   - Confirm no behavioral changes

3. **Update documentation**
   - Mark task as complete
   - Document the new template loading pattern
   - Add examples for future template additions

## Architecture Compliance

After fix is complete, the system will be **100% compliant** with the "no prompts in code" rule:

- ✅ All agent instructions in YAML
- ✅ All prompt templates in YAML
- ✅ No static service mappings
- ✅ Agent-first decision making preserved
- ✅ Position-based resource matching maintained

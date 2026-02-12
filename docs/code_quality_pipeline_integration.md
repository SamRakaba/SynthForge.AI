# Code Quality Pipeline Integration

## Overview

Implemented automated validation loop for generated IaC code to ensure production readiness.

**Status**: ✅ **IMPLEMENTED** (January 5, 2026)

## Pipeline Flow

```
Module Development Agent
         ↓
    Generate Code
         ↓
    Save Files
         ↓
   🔍 VALIDATION PIPELINE (IMPLEMENTED)
         ↓
    ┌─────────────────────┐
    │ Stage 1: Validate   │ ← terraform validate / bicep build
    └─────────────────────┘
             ↓
    ┌─────────────────────┐
    │ Stage 2: Parse      │ ← Extract errors with file/line/column
    │ Errors              │
    └─────────────────────┘
             ↓
    ┌─────────────────────┐
    │ Stage 3: Fix        │ ← Code Quality Agent ✅ IMPLEMENTED
    │ (if errors)         │
    └─────────────────────┘
             ↓
    ┌─────────────────────┐
    │ Stage 4: Re-validate│ ← Repeat until pass or max iterations
    └─────────────────────┘
             ↓
    Save Validated Code + Report
```

## Files Created

### 1. `synthforge/code_quality_pipeline.py`
**Purpose**: Core validation pipeline implementation

**Key Classes**:
- `ValidationIssue`: Structured error/warning representation
- `ValidationResult`: Summary of validation run
- `CodeFix`: Suggested fix with confidence level
- `TerraformValidator`: Runs `terraform validate -json`
- `BicepValidator`: Runs `bicep build`
- `CodeQualityPipeline`: Main orchestration class

**Features**:
- ✅ Terraform validation with JSON output parsing
- ✅ Bicep validation with error parsing
- ✅ Validation report generation (JSON)
- ✅ Fix iteration loop (max 3 attempts)
- ✅ Code Quality Agent integration (IMPLEMENTED)
- ✅ Automatic fix application with confidence levels

## Files Modified

### 1. `synthforge/agents/module_development_agent.py`
**Changes**:
- ✅ Added `enable_validation` parameter (default: `True`)
- ✅ Added `max_fix_iterations` parameter (default: `3`)
- ✅ Integrated `CodeQualityPipeline` in constructor
- ✅ Added validation step in `_generate_single_module()`
- ✅ Added validation status to `GeneratedModule` dataclass:
  - `validation_status`: "pass" | "warning" | "fail" | "not_validated"
  - `validation_errors`: int
  - `validation_warnings`: int
- ✅ Added validation summary logging
- ✅ Added `validation_report.json` generation per module
- ✅ Added validation summary to `ModuleDevelopmentResult`

**Integration Point**:
```python
# After files are saved, before returning module
if self.enable_validation and self.validation_pipeline:
    validated_code, validation_result = self.validation_pipeline.run(
        generated_code=generated_files,
        output_dir=module_dir
    )
```

### 2. `synthforge/prompts/iac_agent_instructions.yaml`
**Changes**:
- ✅ Added `code_quality_rules` section (lines 46-60):
  - Terraform best practices (explicit booleans, try(), dynamic blocks)
  - Bicep best practices (null-conditional, empty(), decorators)
- ✅ Added `validation_pipeline` section (lines 65-128):
  - 5-stage workflow documentation
  - Integration points for agents
  - Break conditions and error handling

## Usage

### Automatic (Default)
Validation runs automatically after every module generation:
```python
module_dev_agent = ModuleDevelopmentAgent(
    agents_client=agents_client,
    model_name="gpt-4.1",
    iac_format="terraform",
    # Validation enabled by default
)
```

### Disable Validation
```python
module_dev_agent = ModuleDevelopmentAgent(
    agents_client=agents_client,
    model_name="gpt-4.1",
    iac_format="terraform",
    enable_validation=False  # Skip validation
)
```

### Custom Fix Iterations
```python
module_dev_agent = ModuleDevelopmentAgent(
    agents_client=agents_client,
    model_name="gpt-4.1",
    iac_format="terraform",
    enable_validation=True,
    max_fix_iterations=5  # Try up to 5 fix attempts
)
```

## Validation Reports

Each module gets a `validation_report.json`:

```json
{
  "overall_status": "fail",
  "validation_summary": {
    "total_files": 3,
    "files_with_errors": 2,
    "files_with_warnings": 1,
    "error_count": 5,
    "warning_count": 2
  },
  "issues": [
    {
      "file": "main.tf",
      "line": 45,
      "column": 12,
      "severity": "error",
      "type": "syntax",
      "rule": "invalid_syntax",
      "message": "Missing required argument: location",
      "current_code": "resource \"azurerm_storage_account\" \"this\" {"
    }
  ],
  "issues_by_file": {
    "main.tf": [...],
    "locals.tf": [...]
  }
}
```

## Output Logs

### Success Case
```
📦 [1/5] Module Type: storage-account
   ARM Type: Microsoft.Storage/storageAccounts
   Service: mystorage
   AVM Source: avm/res/storage/storage-account
   🔍 Validating module: storage-account
   ✅ Validation passed: storage-account
   📄 Validation report: validation_report.json
   ✅ [1/5] Module: storage-account complete
```

### Failure Case
```
📦 [2/5] Module Type: key-vault
   🔍 Validating module: key-vault
   ❌ Validation failed (3 errors): key-vault
   📄 Validation report: validation_report.json
   ✅ [2/5] Module: key-vault complete
```

### Summary
```
================================================================================
CODE QUALITY VALIDATION SUMMARY
================================================================================
✅ Passed:        3/5
⚠️  With Warnings: 1/5 (2 warnings)
❌ Failed:        1/5 (3 errors)

⚠️  Modules requiring attention:
   • modules/key-vault (3 errors)
     Report: c:\...\iac\terraform\modules\key-vault\validation_report.json
```

## Next Steps (TODO)

### Phase 1: Complete Basic Validation
- [x] Implement validation pipeline class
- [x] Integrate with Module Development Agent
- [x] Add validation reporting
- [x] Update instruction files
- [x] Create Code Quality Agent
- [x] Integrate agent with pipeline
- [ ] **Test with real Terraform modules**
- [ ] **Verify error parsing accuracy**
- [ ] **Test fix generation and application**

### Phase 2: Test and Refine Fix Automation (CURRENT)
- [x] Create Code Quality Agent (from `synthforge/prompts/code_quality_agent.yaml`)
- [x] Integrate agent with pipeline's `_get_fixes()` method
- [x] Add confidence scoring for auto-fix decisions
- [ ] **Test fix iteration loop with real validation errors**
- [ ] **Verify high-confidence fixes are applied correctly**
- [ ] **Improve fix application logic (consider AST-based approach)**

### Phase 3: Enhance Validation
- [ ] Add `tflint` integration (best practices)
- [ ] Add `checkov` integration (security)
- [ ] Add custom validation rules
- [ ] Create validated pattern library

### Phase 4: Metrics & Continuous Improvement
- [ ] Track validation pass/fail rates
- [ ] Monitor fix success rates
- [ ] Build quality scoring dashboard
- [ ] Generate pattern templates from validated code

## Dependencies

### Required Tools
- **Terraform**: `terraform` CLI (>=1.6)
- **Bicep**: `bicep` CLI (latest)

### Python Packages
```python
# Already in requirements.txt
pathlib
json
subprocess
dataclasses
logging
```

## Configuration

Pipeline can be configured per-agent:

```python
# In Module Development Agent
self.validation_pipeline = CodeQualityPipeline(
    iac_type=iac_format,           # "terraform" or "bicep"
    max_fix_iterations=3,          # Max retry attempts
    quality_agent=code_qa_agent    # Agent for fix generation
)
```

## Troubleshooting

### Validation Times Out
- Check `terraform` / `bicep` CLI is installed
- Verify module syntax before running pipeline
- Increase timeout in validator classes

### No Errors Detected
- Ensure `terraform validate -json` returns valid JSON
- Check error parsing regex patterns
- Verify file paths in validation results

### Fixes Not Applied
- Code Quality Agent not yet implemented (`quality_agent=None`)
- Currently logs validation errors only
- Manual fix required until Phase 2 complete

## References

- [Code Quality Improvement Guide](./code_quality_improvement_guide.md)
- [Code Quality Agent Definition](../synthforge/prompts/code_quality_agent.yaml)
- [IaC Agent Instructions](../synthforge/prompts/iac_agent_instructions.yaml)
- [Terraform Validation Docs](https://developer.hashicorp.com/terraform/cli/commands/validate)
- [Bicep Build Docs](https://learn.microsoft.com/azure/azure-resource-manager/bicep/bicep-cli)

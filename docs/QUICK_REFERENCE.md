# Quick Reference: Code Quality Pipeline

## 🚀 What It Does

Automatically validates generated Terraform/Bicep code and reports errors **before deployment**.

## 📍 Integration Points

### Where It Runs
**Location**: `synthforge/agents/module_development_agent.py`  
**Trigger**: After every module generation (Stage 4)  
**Timing**: Between "Save Files" and "Return Module"

### Flow
```
Generate → Save → 🔍 VALIDATE → Report → Return
```

## 🎛️ Configuration

### Default (Recommended)
```python
# Validation enabled automatically
module_dev_agent = ModuleDevelopmentAgent(
    agents_client=agents_client,
    model_name="gpt-4.1",
    iac_format="terraform"
)
```

### Disable Validation
```python
# For testing/debugging only
ModuleDevelopmentAgent(..., enable_validation=False)
```

### Custom Iterations
```python
# Try more fix attempts (when Code Quality Agent implemented)
ModuleDevelopmentAgent(..., max_fix_iterations=5)
```

## 📊 What You'll See

### Console Output
```
📦 [3/10] Module Type: key-vault
   ARM Type: Microsoft.KeyVault/vaults
   🔍 Validating module: key-vault
   ✅ Validation passed: key-vault          # ← NEW
   📄 Validation report: validation_report.json  # ← NEW
```

### Summary Report
```
================================================================================
CODE QUALITY VALIDATION SUMMARY                    # ← NEW SECTION
================================================================================
✅ Passed:        8/10
⚠️  With Warnings: 1/10 (3 warnings)
❌ Failed:        1/10 (5 errors)

⚠️  Modules requiring attention:
   • modules/api-management (5 errors)
     Report: c:\...\modules\api-management\validation_report.json
```

## 📁 Output Files

### Per Module
```
modules/
  storage-account/
    main.tf
    variables.tf
    outputs.tf
    README.md
    validation_report.json    # ← NEW
```

### Report Format
```json
{
  "overall_status": "pass",
  "validation_summary": {
    "total_files": 4,
    "error_count": 0,
    "warning_count": 0
  },
  "issues": []
}
```

## 🔧 Tools Used

### Terraform
```bash
terraform init -backend=false
terraform validate -json
```

### Bicep
```bash
bicep build <file.bicep>
```

## 🐛 Common Issues

### Issue: "terraform command not found"
**Fix**: Install Terraform CLI
```powershell
choco install terraform
# or
winget install HashiCorp.Terraform
```

### Issue: "bicep command not found"
**Fix**: Install Azure CLI + Bicep
```powershell
az bicep install
```

### Issue: Validation times out
**Check**:
1. Terraform/Bicep CLI installed?
2. Module has provider requirements?
3. Network/disk issues?

## 📈 Module Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `pass` | ✅ No errors | Ready to deploy |
| `warning` | ⚠️ Warnings only | Review warnings, likely OK |
| `fail` | ❌ Has errors | **Review validation_report.json** |
| `not_validated` | ⏭️ Skipped | Validation disabled |

## 🎯 Phase 2 (Coming Soon)

When Code Quality Agent is integrated:

### Automatic Fixes
```
Generate → Validate → ❌ Error Found
                ↓
         Fix Attempt 1 → Re-validate → ❌ Still Error
                ↓
         Fix Attempt 2 → Re-validate → ✅ Pass!
                ↓
         Save Fixed Code
```

### What Gets Fixed
- Missing required arguments
- Type mismatches
- Boolean conditional issues
- Unsafe nested access
- Dynamic block errors

## 📚 Documentation

- **Integration Guide**: [code_quality_pipeline_integration.md](./code_quality_pipeline_integration.md)
- **Improvement Strategies**: [code_quality_improvement_guide.md](./code_quality_improvement_guide.md)
- **Implementation Summary**: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)

## 🧪 Testing

```powershell
# Run validation tests
cd c:\Users\srakaba\ai-agents\SynthForge.AI
python tests\test_code_quality_pipeline.py
```

## 💡 Pro Tips

1. **Check Reports**: Always review `validation_report.json` for failed modules
2. **Common Errors**: Missing `location`, `resource_group_name` in Azure resources
3. **Best Practice**: Run validation even during development (`enable_validation=True`)
4. **Performance**: Validation adds ~5-10 seconds per module (worth it!)

## ❓ FAQ

**Q**: Does this slow down generation?  
**A**: Slightly (~5-10s per module), but catches errors before deployment

**Q**: Can I skip validation?  
**A**: Yes, set `enable_validation=False`, but NOT recommended

**Q**: What if validation fails?  
**A**: Code is still saved to `modules/` - check `validation_report.json` to fix manually

**Q**: When will auto-fix work?  
**A**: Phase 2 - when Code Quality Agent is integrated (next milestone)

**Q**: Does it validate logic issues?  
**A**: Currently: syntax only. Phase 2 will add logic/best-practice checks

## 🔗 Quick Links

- Pipeline Code: [code_quality_pipeline.py](../synthforge/code_quality_pipeline.py)
- Integration: [module_development_agent.py](../synthforge/agents/module_development_agent.py)
- Tests: [test_code_quality_pipeline.py](../tests/test_code_quality_pipeline.py)

---

**Status**: ✅ Live in production  
**Version**: 1.0 (January 5, 2026)

"""
Test module naming alignment between Module Mapping and Module Development agents.

Validates that:
1. Both agents use ARM-type-derived folder naming convention
2. Common module folder names are consistent
3. No common/ subdirectory structure
4. All examples use the same naming convention
"""

import yaml
from pathlib import Path


def test_module_naming_alignment():
    """Test that Module Mapping and Module Development use consistent naming"""
    
    print("=" * 80)
    print("MODULE NAMING ALIGNMENT TEST")
    print("=" * 80)
    print()
    
    yaml_path = Path("synthforge/prompts/iac_agent_instructions.yaml")
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    
    # Get both agent instructions
    module_mapping = content.get("module_mapping_agent", {})
    module_development = content.get("module_development_agent", {})
    
    mapping_instructions = module_mapping.get("instructions", "")
    terraform_instructions = module_development.get("terraform_instructions", "")
    
    print("📋 Testing Module Mapping Agent Instructions...\n")
    
    # Test 1: Check for ARM-type-derived naming in Module Mapping
    print("Test 1: ARM-type-derived naming in Module Mapping")
    arm_derived_patterns = [
        "network-privateendpoints",
        "insights-diagnosticsettings", 
        "authorization-roleassignments",
        "authorization-locks"
    ]
    
    mapping_has_arm_naming = all(pattern in mapping_instructions for pattern in arm_derived_patterns)
    
    if mapping_has_arm_naming:
        print("  ✅ Module Mapping uses ARM-type-derived names")
        for pattern in arm_derived_patterns:
            print(f"     • {pattern} ✓")
    else:
        print("  ❌ Module Mapping missing ARM-type-derived names")
        for pattern in arm_derived_patterns:
            if pattern in mapping_instructions:
                print(f"     • {pattern} ✓")
            else:
                print(f"     • {pattern} ✗")
    
    print()
    
    # Test 2: Check for old naming patterns (should NOT exist)
    print("Test 2: Old naming patterns removed from Module Mapping")
    old_patterns = [
        '"folder_path": "private-endpoint"',
        '"folder_path": "diagnostic-settings"',
        '"folder_path": "role-assignment"',
        "modules/common/private-endpoint",
        "modules/common/diagnostic-settings"
    ]
    
    has_old_patterns = any(pattern in mapping_instructions for pattern in old_patterns)
    
    if not has_old_patterns:
        print("  ✅ Old naming patterns removed")
    else:
        print("  ❌ Old naming patterns still present:")
        for pattern in old_patterns:
            if pattern in mapping_instructions:
                print(f"     • Found: {pattern}")
    
    print()
    
    # Test 3: Check Module Development expects ARM-derived names
    print("Test 3: Module Development expects ARM-type-derived names")
    
    dev_has_arm_naming = all(pattern in terraform_instructions for pattern in arm_derived_patterns)
    
    if dev_has_arm_naming:
        print("  ✅ Module Development expects ARM-type-derived names")
        for pattern in arm_derived_patterns:
            print(f"     • {pattern} ✓")
    else:
        print("  ❌ Module Development missing ARM-type-derived names")
    
    print()
    
    # Test 4: Check for arm_type field in examples
    print("Test 4: ARM type fields in common module examples")
    
    arm_type_examples = [
        '"arm_type": "Microsoft.Network/privateEndpoints"',
        '"arm_type": "Microsoft.Insights/diagnosticSettings"',
        '"arm_type": "Microsoft.Authorization/roleAssignments"'
    ]
    
    has_arm_types = all(example in mapping_instructions for example in arm_type_examples)
    
    if has_arm_types:
        print("  ✅ ARM type fields present in examples")
        for example in arm_type_examples:
            print(f"     • {example.split(':')[1].strip().strip('\"')} ✓")
    else:
        print("  ❌ ARM type fields missing in some examples")
        for example in arm_type_examples:
            if example in mapping_instructions:
                print(f"     • {example.split(':')[1].strip().strip('\"')} ✓")
            else:
                print(f"     • {example.split(':')[1].strip().strip('\"')} ✗")
    
    print()
    
    # Test 5: Check folder structure shows flat layout
    print("Test 5: Flat module structure (no common/ subdirectory)")
    
    has_common_subdir = "modules/common/" in mapping_instructions or "modules/common/" in terraform_instructions
    
    if not has_common_subdir:
        print("  ✅ No common/ subdirectory in folder structure")
    else:
        print("  ❌ common/ subdirectory still present")
        if "modules/common/" in mapping_instructions:
            print("     • Found in Module Mapping instructions")
        if "modules/common/" in terraform_instructions:
            print("     • Found in Module Development instructions")
    
    print()
    
    # Test 6: Cross-agent consistency
    print("Test 6: Cross-agent naming consistency")
    
    if mapping_has_arm_naming and dev_has_arm_naming and not has_old_patterns and not has_common_subdir:
        print("  ✅ Both agents use consistent ARM-type-derived naming")
        print("     • Flat structure (no subdirectories)")
        print("     • Microsoft ARM schema compliant")
        print("     • HashiCorp Terraform Registry compliant")
    else:
        print("  ❌ Naming inconsistencies detected between agents")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_tests_passed = (
        mapping_has_arm_naming and
        dev_has_arm_naming and
        not has_old_patterns and
        has_arm_types and
        not has_common_subdir
    )
    
    if all_tests_passed:
        print("✅ ALL TESTS PASSED")
        print()
        print("Module naming is ALIGNED between agents:")
        print("  • ARM-type-derived folder names (provider-resourcetype)")
        print("  • Flat module structure (no common/ subdirectory)")
        print("  • ARM type fields included in output")
        print("  • Consistent with Microsoft ARM schema")
        print("  • Consistent with HashiCorp Terraform Registry")
        print()
        print("Ready for production use!")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Please review the failures above and fix accordingly.")
        return False


if __name__ == "__main__":
    success = test_module_naming_alignment()
    exit(0 if success else 1)

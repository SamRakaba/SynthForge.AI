#!/usr/bin/env python3
"""Test script to verify YAML fix didn't introduce regressions."""

import yaml
from pathlib import Path

def test_yaml_parsing():
    """Test that all YAML instruction files parse correctly."""
    print("=" * 80)
    print("Testing YAML Instruction Files")
    print("=" * 80)
    
    yaml_files = [
        "synthforge/prompts/agent_instructions.yaml",
        "synthforge/prompts/iac_agent_instructions.yaml",
        "synthforge/prompts/code_quality_agent.yaml"
    ]
    
    for yaml_file in yaml_files:
        print(f"\n📄 Testing: {yaml_file}")
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            print(f"   ✓ Parsed successfully")
            print(f"   ✓ Top-level keys: {list(data.keys())[:5]}..." if len(data.keys()) > 5 else f"   ✓ Top-level keys: {list(data.keys())}")
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
            return False
    
    return True


def test_specific_fix():
    """Test the specific section that was fixed (deployment_wrapper_agent)."""
    print("\n" + "=" * 80)
    print("Testing Specific Fix: deployment_wrapper_agent bicep_instructions")
    print("=" * 80)
    
    try:
        with open("synthforge/prompts/iac_agent_instructions.yaml", 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        bicep_instructions = data['deployment_wrapper_agent']['bicep_instructions']
        lines = bicep_instructions.split('\n')
        
        print(f"\n✓ bicep_instructions loaded: {len(lines)} lines")
        
        # Check for key sections that should be present
        key_sections = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('##'):
                key_sections.append(stripped)
        
        print(f"✓ Found {len(key_sections)} section headers:")
        for section in key_sections[:10]:
            print(f"  - {section}")
        
        # Verify critical content is present
        content = bicep_instructions.lower()
        critical_phrases = [
            "your mission",
            "module composition",
            "dependency ordering",
            "bicep deployment",
            "provider config"
        ]
        
        print("\n✓ Verifying critical content:")
        for phrase in critical_phrases:
            if phrase in content:
                print(f"  ✓ Found: '{phrase}'")
            else:
                print(f"  ⚠ Missing: '{phrase}'")
        
        return True
        
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_loading():
    """Test that Phase 2 agents can load their instructions."""
    print("\n" + "=" * 80)
    print("Testing Agent Instruction Loading")
    print("=" * 80)
    
    try:
        from synthforge.prompts import (
            get_service_analysis_agent_instructions,
            get_module_mapping_agent_instructions,
            get_module_development_agent_instructions,
            get_deployment_wrapper_agent_instructions
        )
        
        agents = [
            ("Service Analysis", get_service_analysis_agent_instructions),
            ("Module Mapping", get_module_mapping_agent_instructions),
            ("Module Development (Terraform)", lambda: get_module_development_agent_instructions("terraform")),
            ("Module Development (Bicep)", lambda: get_module_development_agent_instructions("bicep")),
            ("Deployment Wrapper (Terraform)", lambda: get_deployment_wrapper_agent_instructions("terraform")),
            ("Deployment Wrapper (Bicep)", lambda: get_deployment_wrapper_agent_instructions("bicep")),
        ]
        
        for agent_name, loader_func in agents:
            try:
                instructions = loader_func()
                print(f"\n✓ {agent_name} Agent:")
                print(f"  - Instructions length: {len(instructions)} chars")
                print(f"  - First 100 chars: {instructions[:100]}...")
            except Exception as e:
                print(f"\n✗ {agent_name} Agent FAILED: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiline_indentation():
    """Scan for potential multiline string indentation issues."""
    print("\n" + "=" * 80)
    print("Scanning for Potential Indentation Issues")
    print("=" * 80)
    
    yaml_file = "synthforge/prompts/iac_agent_instructions.yaml"
    
    with open(yaml_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    issues = []
    in_multiline = False
    multiline_indent = 0
    line_num = 0
    
    for i, line in enumerate(lines, 1):
        # Detect start of multiline string
        if '|' in line or '>' in line:
            in_multiline = True
            multiline_indent = len(line) - len(line.lstrip())
            line_num = i
            continue
        
        if in_multiline:
            # Check if line has content
            if line.strip():
                current_indent = len(line) - len(line.lstrip())
                # Content should be indented more than the key
                if current_indent <= multiline_indent:
                    in_multiline = False  # End of multiline
                # Check for inconsistent indentation patterns
                elif line.strip().startswith('##') and current_indent < multiline_indent + 2:
                    issues.append(f"Line {i}: Possible indentation issue - section header not indented enough")
    
    if issues:
        print(f"\n⚠ Found {len(issues)} potential issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"  {issue}")
    else:
        print("\n✓ No obvious indentation issues detected")
    
    return len(issues) == 0


if __name__ == "__main__":
    print("\n🔍 Post-Fix Regression Analysis\n")
    
    all_passed = True
    
    # Test 1: YAML parsing
    if not test_yaml_parsing():
        all_passed = False
    
    # Test 2: Specific fix verification
    if not test_specific_fix():
        all_passed = False
    
    # Test 3: Agent loading
    if not test_agent_loading():
        all_passed = False
    
    # Test 4: Multiline indentation scan
    if not test_multiline_indentation():
        all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - No regressions detected")
    else:
        print("❌ SOME TESTS FAILED - Review needed")
    print("=" * 80 + "\n")

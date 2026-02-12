"""Test Bicep instructions fix for Stage 5 Phase 2"""
import yaml
from pathlib import Path

def test_yaml_parsing():
    """Test that YAML parses correctly after bicep_instructions fix"""
    yaml_path = Path("synthforge/prompts/iac_agent_instructions.yaml")
    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    
    print("✅ YAML parsed successfully")
    
    # Check bicep_instructions exists and is expanded
    bicep_instructions = content["deployment_wrapper_agent"]["bicep_instructions"]
    print(f"✅ bicep_instructions length: {len(bicep_instructions)} chars")
    
    # Verify critical components exist
    assert "**CRITICAL FIRST RULE**" in bicep_instructions, "Missing JSON-only directive"
    print("✅ Contains JSON-only directive")
    
    assert '"environments":' in bicep_instructions, "Missing environments in schema"
    print("✅ Contains complete JSON schema")
    
    assert "naming_module" in bicep_instructions, "Missing naming_module requirements"
    print("✅ Contains naming module requirements")
    
    assert "Your ENTIRE response must be this JSON object" in bicep_instructions, "Missing final reminder"
    print("✅ Contains final JSON-only reminder")
    
    print("\n✅ All validation checks passed!")
    print(f"   bicep_instructions expanded from ~46 to {len(bicep_instructions)} chars")

if __name__ == "__main__":
    test_yaml_parsing()

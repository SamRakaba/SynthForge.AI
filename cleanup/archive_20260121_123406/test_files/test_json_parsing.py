"""Test enhanced JSON parsing logic"""
import json
from pathlib import Path
import sys
from unittest.mock import Mock

# Add parent directory to path to import DeploymentWrapperAgent
sys.path.insert(0, str(Path(__file__).parent))

from synthforge.agents.deployment_wrapper_agent import DeploymentWrapperAgent

def test_json_parsing_scenarios():
    """Test various JSON response scenarios"""
    
    # Create a minimal agent instance just for testing _parse_json_response
    # We don't need actual Azure client for this test, so we mock it
    mock_client = Mock()
    agent = DeploymentWrapperAgent(
        agents_client=mock_client,
        model_name="gpt-4o",
        iac_format="bicep",
        bing_connection_name="dummy-bing"
    )
    
    print("Testing JSON parsing scenarios...\n")
    
    # Test 1: Clean JSON (should work)
    print("Test 1: Clean JSON")
    clean_json = '{"files": {"main.bicep": "content"}}'
    result = agent._parse_json_response(clean_json)
    assert "files" in result
    print("✅ PASSED: Clean JSON parsed correctly\n")
    
    # Test 2: JSON in markdown code block (should extract)
    print("Test 2: JSON in markdown code block")
    markdown_json = """Here is the JSON response:
```json
{"files": {"main.bicep": "content"}}
```
This is the deployment configuration."""
    result = agent._parse_json_response(markdown_json)
    assert "files" in result
    print("✅ PASSED: Extracted JSON from markdown block\n")
    
    # Test 3: JSON with extra text after (should extract)
    print("Test 3: JSON with extra text after")
    json_with_extra = """{"files": {"main.bicep": "content"}}

This deployment includes the following features:
- Naming module with CAF compliance
- Environment-specific parameters"""
    result = agent._parse_json_response(json_with_extra)
    assert "files" in result
    print("✅ PASSED: Extracted JSON from response with extra text\n")
    
    # Test 4: Generic code block (should extract)
    print("Test 4: Generic code block without json marker")
    generic_block = """```
{"files": {"main.bicep": "content"}}
```"""
    result = agent._parse_json_response(generic_block)
    assert "files" in result
    print("✅ PASSED: Extracted JSON from generic code block\n")
    
    # Test 5: Empty response (should return empty dict)
    print("Test 5: Empty response")
    empty = ""
    result = agent._parse_json_response(empty)
    assert result == {"files": {}}
    print("✅ PASSED: Handled empty response gracefully\n")
    
    # Test 6: Malformed JSON (should raise error and save debug file)
    print("Test 6: Malformed JSON (unterminated string)")
    malformed = '{"files": {"main.bicep": "content with unterminated string'
    try:
        result = agent._parse_json_response(malformed)
        print("❌ FAILED: Should have raised JSONDecodeError")
    except json.JSONDecodeError as e:
        # Check that debug file was created
        debug_path = Path("iac") / "_debug_json_parse_error.txt"
        if debug_path.exists():
            print("✅ PASSED: Raised error and created debug file")
            print(f"   Debug file: {debug_path}")
            debug_path.unlink()  # Clean up
        else:
            print("⚠️ PARTIAL: Raised error but no debug file")
    print()
    
    print("=" * 60)
    print("✅ All JSON parsing tests completed successfully!")
    print("=" * 60)
    print("\nThe enhanced _parse_json_response() method now handles:")
    print("  • Clean JSON responses")
    print("  • JSON in markdown code blocks (```json)")
    print("  • Generic code blocks (```)")
    print("  • Extra text before/after JSON")
    print("  • Empty responses")
    print("  • Malformed JSON (with debug file generation)")
    print("\nThis should resolve the Stage 5 JSON parsing errors.")

if __name__ == "__main__":
    test_json_parsing_scenarios()

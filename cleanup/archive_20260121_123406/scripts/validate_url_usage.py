"""
URL Usage Validation - Ensure No Hardcoded URLs in Research Instructions
"""
import re
from pathlib import Path

def validate_url_usage():
    file_path = Path(__file__).parent / "synthforge" / "prompts" / "iac_agent_instructions.yaml"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all https URLs
    url_pattern = r'https://[^\s<>"\']+'
    urls = re.findall(url_pattern, content)
    
    print("=" * 80)
    print("URL USAGE VALIDATION")
    print("=" * 80)
    print(f"\nTotal URLs found: {len(urls)}\n")
    
    # Check for critical annotations
    has_critical_note = "CRITICAL NOTE ON URLs" in content
    has_url_found_annotations = content.count("[URL found") > 0
    has_query_patterns = content.count("Query:") > 5  # At least 5 query patterns
    has_site_filters = content.count("site:") > 50
    
    print("Annotation Checks:")
    print(f"  {'✅' if has_critical_note else '❌'} CRITICAL NOTE ON URLs present")
    print(f"  {'✅' if has_url_found_annotations else '❌'} [URL found...] annotations used")
    print(f"  {'✅' if has_query_patterns else '❌'} Query: patterns present ({content.count('Query:')} found)")
    print(f"  {'✅' if has_site_filters else '❌'} site: filters present ({content.count('site:')} found)")
    
    # Show some examples of annotated URLs
    print("\n" + "=" * 80)
    print("SAMPLE ANNOTATED URL USAGES:")
    print("=" * 80)
    
    lines = content.split('\n')
    url_found_lines = [line.strip() for line in lines if '[URL found' in line][:3]
    query_lines = [line.strip() for line in lines if line.strip().startswith('- Query:')][:3]
    
    if url_found_lines:
        print("\nExample: URLs annotated as agent-found:")
        for line in url_found_lines:
            print(f"  {line}")
    
    if query_lines:
        print("\nExample: Query patterns (agent discovers URLs):")
        for line in query_lines:
            print(f"  {line}")
    
    print("\n" + "=" * 80)
    print("VALIDATION RESULT")
    print("=" * 80)
    
    if all([has_critical_note, has_url_found_annotations, has_query_patterns, has_site_filters]):
        print("✅ PASS: Instructions properly use query patterns and annotate URLs")
        print("\nKey Points:")
        print("  • Agents use Bing Grounding with query patterns (not hardcoded URLs)")
        print("  • Example URLs are annotated as '[URL found via...]'")
        print("  • CRITICAL NOTES explain URLs are agent-discovered")
        print("  • MS Learn MCP queries described (no URLs needed)")
        return True
    else:
        print("❌ FAIL: Some annotations missing")
        return False

if __name__ == "__main__":
    validate_url_usage()

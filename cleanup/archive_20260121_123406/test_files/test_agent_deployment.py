"""
Agent Deployment Test: Validate Real-World Knowledge Source Usage

This test runs a simplified deployment scenario to verify:
1. Agents can query all knowledge sources successfully
2. Generated IaC code is complete and follows best practices
3. Research patterns work in practice, not just theory
"""

import json
import os
from pathlib import Path

# Test scenario: Azure OpenAI deployment with security baseline
TEST_REQUIREMENT = """
Deploy Azure OpenAI Service with:
- GPT-4o model deployment
- Private endpoint connectivity
- Managed identity authentication
- Diagnostic logging to Log Analytics
- Compliance: Azure Security Baseline + Well-Architected Framework
"""

EXPECTED_KNOWLEDGE_SOURCES_USED = {
    "AVM": [
        "Should query: avm-res-cognitiveservices-account site:azure.github.io",
        "Should reference AVM parameter patterns for comprehensive configuration"
    ],
    "HashiCorp Registry": [
        "Should query: azurerm_cognitive_account site:registry.terraform.io",
        "Should verify current resource schema and API version"
    ],
    "Azure ARM API": [
        "Should query: Cognitive Services ARM template reference site:learn.microsoft.com",
        "Should verify Microsoft.CognitiveServices/accounts type properties"
    ],
    "MS Learn MCP": [
        "Should query for: Azure OpenAI security requirements",
        "Should query for: Private endpoint configuration",
        "Should query for: API versions and regional availability"
    ],
    "Security Baseline": [
        "Should query: Azure OpenAI security baseline site:learn.microsoft.com/security",
        "Should implement: Disable public network access by default",
        "Should implement: Managed identity for authentication"
    ],
    "Well-Architected Framework": [
        "Should query: Azure OpenAI Well-Architected site:learn.microsoft.com",
        "Should implement: Reliability patterns (availability zones if available)",
        "Should implement: Operational excellence (diagnostic logging)"
    ]
}

VALIDATION_CHECKLIST = {
    "Module Structure": [
        "✓ Native azurerm_cognitive_account resource (NOT sourced from AVM)",
        "✓ Calls common modules: private_endpoint, diagnostics, rbac",
        "✓ All parameters from HashiCorp registry documentation",
        "✓ Dynamic blocks for optional features (identity, network_acls)"
    ],
    "Security Implementation": [
        "✓ public_network_access_enabled = false (default)",
        "✓ identity with SystemAssigned or UserAssigned",
        "✓ disable_local_auth = true (follows security baseline)",
        "✓ private_endpoint module call with DNS configuration"
    ],
    "Monitoring & Governance": [
        "✓ diagnostic_settings with all log categories",
        "✓ role_assignments for managed identity",
        "✓ tags for governance and cost management",
        "✓ lifecycle management and lock configuration"
    ],
    "Research-Driven Patterns": [
        "✓ SKU selected based on requirement (Standard, not hardcoded)",
        "✓ kind = 'OpenAI' (researched, not assumed)",
        "✓ custom_subdomain_name configured (required for private endpoint)",
        "✓ All optional features from AVM pattern (not minimal subset)"
    ]
}

def create_test_input():
    """Create Phase 1 output as test input for agents"""
    
    phase1_output = {
        "architecture_overview": {
            "solution_name": "Azure OpenAI Secure Deployment",
            "description": "GPT-4o deployment with enterprise security controls",
            "deployment_model": "hub-spoke",
            "compliance_requirements": ["Azure Security Baseline", "Well-Architected Framework"]
        },
        "service_requirements": [
            {
                "service_name": "Azure OpenAI Service",
                "arm_type": "Microsoft.CognitiveServices/accounts",
                "kind": "OpenAI",
                "sku": "Standard",
                "deployment_models": ["gpt-4o"],
                "security_requirements": {
                    "aad_authentication": {
                        "required": True,
                        "configuration_property": "disable_local_auth",
                        "recommended_value": True
                    },
                    "network_isolation": {
                        "private_endpoint_required": True,
                        "public_network_access_enabled": False,
                        "service_endpoints_required": False
                    },
                    "encryption": {
                        "encryption_at_rest": True,
                        "infrastructure_encryption_enabled": True,
                        "customer_managed_key_required": False
                    }
                },
                "monitoring_requirements": {
                    "diagnostic_settings_required": True,
                    "log_categories": ["Audit", "RequestResponse", "Trace"],
                    "metric_categories": ["AllMetrics"]
                }
            }
        ],
        "common_patterns": {
            "private_endpoint": {
                "required": True,
                "count": 1,
                "arm_type": "Microsoft.Network/privateEndpoints",
                "justification": "Azure Security Baseline NS-2"
            },
            "diagnostics": {
                "required": True,
                "count": 1,
                "arm_type": "Microsoft.Insights/diagnosticSettings",
                "justification": "WAF Operational Excellence"
            },
            "rbac": {
                "required": True,
                "count": 1,
                "arm_type": "Microsoft.Authorization/roleAssignments",
                "justification": "Managed identity authentication"
            }
        }
    }
    
    return phase1_output


def print_test_scenario():
    """Display test scenario and expectations"""
    
    print("\n" + "=" * 80)
    print("AGENT DEPLOYMENT TEST SCENARIO")
    print("=" * 80)
    print(TEST_REQUIREMENT)
    print("\n" + "-" * 80)
    print("EXPECTED KNOWLEDGE SOURCE USAGE:")
    print("-" * 80)
    
    for source, expectations in EXPECTED_KNOWLEDGE_SOURCES_USED.items():
        print(f"\n{source}:")
        for expectation in expectations:
            print(f"  • {expectation}")
    
    print("\n" + "-" * 80)
    print("VALIDATION CHECKLIST:")
    print("-" * 80)
    
    for category, checks in VALIDATION_CHECKLIST.items():
        print(f"\n{category}:")
        for check in checks:
            print(f"  {check}")
    
    print("\n" + "=" * 80)


def save_test_input(output_file="test_input_phase1.json"):
    """Save test input for manual agent run"""
    
    test_input = create_test_input()
    output_path = Path(__file__).parent / output_file
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_input, f, indent=2)
    
    print(f"\n✅ Test input saved: {output_path}")
    return output_path


def print_manual_test_instructions():
    """Print instructions for running manual test"""
    
    print("\n" + "=" * 80)
    print("MANUAL TEST INSTRUCTIONS")
    print("=" * 80)
    print("""
To validate agent reliability and knowledge source integration:

STEP 1: Run SynthForge with test input
---------------------------------------
python main.py --skip-phase1 --phase1-output test_input_phase1.json --iac-format terraform

STEP 2: Review generated code
------------------------------
Check: output/modules/cognitive-services-account/

STEP 3: Validate against checklist
-----------------------------------
Module Structure:
  □ Native azurerm_cognitive_account resource (NOT module source)
  □ Calls to: ../network-privateendpoints, ../insights-diagnosticsettings
  □ All parameters from registry.terraform.io documentation
  □ Dynamic blocks for identity, network_acls

Security Implementation:
  □ public_network_access_enabled = false (default)
  □ identity block with type = "SystemAssigned" or "UserAssigned"
  □ disable_local_auth = true (from security baseline)
  □ private_endpoint module call with subnet_id, dns_zone_id

Monitoring & Governance:
  □ diagnostic_settings with log/metric categories
  □ role_assignments for managed identity RBAC
  □ tags map with governance metadata
  □ lifecycle and lock configuration

Research-Driven Patterns:
  □ SKU from requirement, not hardcoded
  □ kind = "OpenAI" (researched from ARM type)
  □ custom_subdomain_name (required for private endpoint)
  □ Comprehensive optional features from AVM pattern

STEP 4: Review agent execution logs
------------------------------------
Look for evidence of knowledge source queries:
  • Bing queries with site: filters
  • MS Learn MCP server calls
  • AVM pattern references
  • HashiCorp registry lookups
  • Security baseline consultations

STEP 5: Verify code quality
----------------------------
  □ No hardcoded values (environment-agnostic)
  □ Proper variable validation (constraints, types)
  □ Complete outputs (id, name, endpoint, identity)
  □ README with usage examples and requirements
  □ Following AVM conventions (locals for identity, dynamic blocks)

EXPECTED OUTCOMES:
------------------
✓ Agents query ALL knowledge sources (not just AVM)
✓ Generated code follows official HashiCorp provider documentation
✓ Security configurations from Azure Security Baseline
✓ Architecture patterns from Well-Architected Framework
✓ Complete, production-ready module (not minimal example)
""")
    print("=" * 80 + "\n")


def main():
    """Main test execution"""
    
    print("\n" + "#" * 80)
    print("# AGENT RELIABILITY & KNOWLEDGE SOURCE TEST")
    print("# Validating multi-source research and code generation quality")
    print("#" * 80)
    
    # Display test scenario
    print_test_scenario()
    
    # Create and save test input
    input_file = save_test_input()
    
    # Print manual test instructions
    print_manual_test_instructions()
    
    print("=" * 80)
    print("TEST PREPARATION COMPLETE")
    print("=" * 80)
    print(f"\n✓ Test input created: {input_file}")
    print("✓ Test scenario documented")
    print("✓ Validation checklist provided")
    print("✓ Manual test instructions ready")
    print("\n→ Run SynthForge with test input to validate agent behavior")
    print("→ Compare generated code against validation checklist")
    print("→ Verify knowledge sources are queried as expected")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()

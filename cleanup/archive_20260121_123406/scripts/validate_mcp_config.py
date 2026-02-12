"""
Validate SynthForge.AI Configuration

Phase 1 agents (Description, Vision, OCR):
- Bing Grounding (REQUIRED) - Fast Azure documentation lookups
- Microsoft Learn MCP (REQUIRED) - Recommendations, security, best practices

Phase 2 agents (IaC generation):
- Bing Grounding (REQUIRED) - Fast reference checks
- Microsoft Learn MCP (REQUIRED) - ARM schemas, AVM templates, API versions
- GitHub MCP (OPTIONAL) - Azure Verified Modules examples
- Terraform MCP (OPTIONAL) - Terraform provider documentation
"""

from synthforge.config import get_settings

settings = get_settings()

print('=' * 70)
print('SYNTHFORGE.AI CONFIGURATION VALIDATION')
print('=' * 70)
print()
print('PROJECT ENDPOINT:')
print(f'  {settings.project_endpoint}')
print()
print('PRIMARY TOOL (Required):')
if settings.bing_connection_id:
    print(f'  ✅ Bing Grounding: CONFIGURED')
    print(f'     Connection ID: {settings.bing_connection_id[:60]}...')
else:
    print(f'  ❌ Bing Grounding: NOT CONFIGURED')
    print(f'     ALL agents require Bing Grounding')
print()
print('OPTIONAL MCP SERVERS (Enhanced Documentation):')

# Microsoft Learn MCP
if settings.ms_learn_mcp_url:
    if settings.ms_learn_mcp_url == "https://learn.microsoft.com/api/mcp":
        print(f'  ✅ Microsoft Learn MCP: CONFIGURED')
        print(f'     URL: {settings.ms_learn_mcp_url}')
        print(f'     Provides: Official docs, ARM schemas, code samples')
    else:
        print(f'  ⚠️  Microsoft Learn MCP: INCORRECT URL')
        print(f'     Current: {settings.ms_learn_mcp_url}')
        print(f'     Expected: https://learn.microsoft.com/api/mcp')
else:
    print(f'  ⚪ Microsoft Learn MCP: Not configured (optional)')

# GitHub MCP
github_status = "CONFIGURED" if settings.github_mcp_url else "Not configured (optional)"
print(f'  {"✅" if settings.github_mcp_url else "⚪"} GitHub MCP: {github_status}')

# Terraform MCP
terraform_status = "CONFIGURED" if settings.terraform_mcp_url else "Not configured (optional)"
print(f'  {"✅" if settings.terraform_mcp_url else "⚪"} Terraform MCP: {terraform_status}')

print()
print('=' * 70)
print('SUMMARY')
print('=' * 70)
print()

if settings.bing_connection_id and settings.ms_learn_mcp_url == "https://learn.microsoft.com/api/mcp":
    print('✅ CONFIGURATION VALID - Ready to run')
    print()
    print('Tool Configuration:')
    print('  • Bing Grounding: PRIMARY (fast lookups) ✓')
    print('  • Microsoft Learn MCP: REQUIRED (recommendations, schemas) ✓')
    
    additional_mcp = sum([
        bool(settings.github_mcp_url),
        bool(settings.terraform_mcp_url)
    ])
    
    if additional_mcp > 0:
        print(f'  • Additional MCP Servers: {additional_mcp} configured (optional)')
        if settings.github_mcp_url:
            print('    - GitHub MCP ✓ (for Azure Verified Modules)')
        if settings.terraform_mcp_url:
            print('    - Terraform MCP ✓ (for Terraform generation)')
    
    print()
    print('Phase 1 Agents (Description, Vision, OCR):')
    print('  ✓ Bing Grounding + Microsoft Learn MCP')
    print('  ✓ Can provide recommendations and security analysis')
    print()
    print('Phase 2 Agents (IaC Generation):')
    print('  ✓ Bing Grounding + Microsoft Learn MCP')
    print('  ✓ Can generate ARM/Bicep with schemas and AVM patterns')
elif settings.bing_connection_id:
    print('⚠️ PARTIAL CONFIGURATION')
    print()
    print('Status:')
    print('  ✓ Bing Grounding: Configured')
    print('  ✗ Microsoft Learn MCP: NOT configured')
    print()
    print('Impact:')
    print('  • Phase 1: Limited to basic lookups (no deep recommendations)')
    print('  • Phase 2: Cannot generate IaC (missing ARM schemas)')
    print()
    print('Required Action:')
    print('  Set MS_LEARN_MCP_URL=https://learn.microsoft.com/api/mcp in .env')
else:
    print('❌ CONFIGURATION ERROR')
    print()
    print('Required Action:')
    print('  Set BING_CONNECTION_ID in .env file')
    print('  This is REQUIRED for all agents')
print()

all_checks_pass = (
    settings.project_endpoint and 
    settings.bing_connection_id and 
    settings.ms_learn_mcp_url == "https://mcp.ai.azure.com"
)

if all_checks_pass:
    print('✅ ALL CHECKS PASSED')
    print()
    print('Configuration Status:')
    print('  • Bing Grounding: Enabled for Azure documentation & best practices')
    print('  • Foundry MCP: Enabled for AI Foundry operations')
    print('  • Phase 1 Agents: Ready to run with both tools')
    print()
    print('Foundry MCP provides:')
    print('  • Model catalog browsing and details')
    print('  • Model deployment management')
    print('  • Evaluation operations and comparisons')
    print('  • Dataset management')
    print('  • Deployment monitoring and analytics')
else:
    print('❌ CONFIGURATION ISSUES DETECTED')
    print()
    print('Required Actions:')
    if not settings.project_endpoint:
        print('  1. Set PROJECT_ENDPOINT in .env')
    if not settings.bing_connection_id:
        print('  2. Set BING_CONNECTION_ID in .env')
    if settings.ms_learn_mcp_url != "https://mcp.ai.azure.com":
        print('  3. Set MS_LEARN_MCP_URL=https://mcp.ai.azure.com in .env')

print()


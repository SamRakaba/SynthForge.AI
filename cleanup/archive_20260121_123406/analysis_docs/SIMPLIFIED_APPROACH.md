# Simplified Approach - Agent Consultation, Not Hardcoding

## The Right Way

Instead of hardcoding DevOps patterns, add **concise instructions** in `synthforge/prompts/__init__.py`:

```python
DEVOPS_CONSULTATION = """

## Generate Production-Grade Deployment

Consult available tools for best practices BEFORE generating:
- Terraform: Use mcp_hashicorp_ter_* tools
- Bicep: Use mcp_bicep_experim_get_bicep_best_practices

Apply discovered patterns:
- Multiple naming modules for different workloads/locations
- Separate files by concern (infrastructure, applications, databases, security)  
- Configuration objects (network_config, dns_config, common_tags)
- Single parameterized template with environment logic
- Dynamic file generation based on detected services
"""

def get_deployment_wrapper_agent_instructions(iac_format: str = "terraform") -> str:
    instructions_data = load_iac_instructions()
    agent_config = instructions_data.get("deployment_wrapper_agent", {})
    
    if iac_format.lower() == "bicep":
        base_instructions = agent_config.get("bicep_instructions", "")
    else:
        base_instructions = agent_config.get("terraform_instructions", "")
    
    return base_instructions + DEVOPS_CONSULTATION
```

## Benefits
✅ Concise - 10 lines vs 400+ lines of hardcoded patterns
✅ Dynamic - Agent uses MCP tools to discover latest practices
✅ No YAML parsing issues - Just Python string
✅ Precise - Clear instruction to agent
✅ Follows your guidance - "craft the instructions to be precise, concise and instruct agent to use all tools available"

## Status
- Loader already updated to support this pattern
- Just need to add the DEVOPS_CONSULTATION constant

Ready to implement?

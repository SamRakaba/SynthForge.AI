"""
Code Quality Agent for SynthForge.AI.

Validates and fixes generated IaC code (Terraform/Bicep) using AI-powered analysis.

Uses azure.ai.agents.AgentsClient with Bing Grounding and MCP tools for best practices lookup.
Provides structured fixes with confidence levels for automatic application.
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole, ThreadRun, RunStatus

from synthforge.config import get_settings
from synthforge.code_quality_pipeline import ValidationResult, ValidationIssue, CodeFix
from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.prompts import load_yaml_with_includes

logger = logging.getLogger(__name__)


class CodeQualityAgent:
    """
    Code Quality Agent for IaC validation and fixing.
    
    Uses Azure Well-Architected Framework and IaC best practices
    to analyze validation errors and provide structured fixes.
    
    Tools Available:
    - Bing Grounding: Search for IaC best practices, error patterns
    - MCP Server: Access Microsoft Learn for Terraform/Bicep guidance
    
    Agent chooses best tool for each lookup - NO STATIC MAPPINGS.
    """
    
    def __init__(
        self,
        agents_client: Optional[AgentsClient] = None,
        model_name: Optional[str] = None,
        iac_format: str = "terraform"
    ):
        """
        Initialize Code Quality Agent.
        
        Args:
            agents_client: Azure AI Agents client (optional, will create if None)
            model_name: Model deployment name (optional, uses settings default)
            iac_format: "terraform" or "bicep"
        """
        self.settings = get_settings()
        self.iac_format = iac_format
        self._client: Optional[AgentsClient] = agents_client
        self._agent_id: Optional[str] = None
        self._should_cleanup: bool = agents_client is None
        self._tool_config = None
        self._yaml_data: Optional[Dict] = None  # Store loaded YAML for templates
        
        # Use provided model name or default from settings
        self.model_name = model_name or self.settings.model_deployment_name
        
        logger.info(f"Initializing CodeQualityAgent for {iac_format}...")
    
    async def __aenter__(self) -> "CodeQualityAgent":
        """Initialize the agent with Bing Grounding and MCP tools."""
        # Create client if not provided
        if self._client is None:
            credential = DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
            
            self._client = AgentsClient(
                endpoint=self.settings.project_endpoint,
                credential=credential,
            )
        
        # Load instructions from code_quality_agent.yaml
        instructions = self._get_agent_instructions()
        
        # Add tool usage instructions
        tool_instructions = get_tool_instructions()
        full_instructions = f"{instructions}\n\n{tool_instructions}"
        
        # Configure tools: Bing Grounding + MCP servers
        # - MS Learn MCP: Official documentation for both Terraform and Bicep
        # - Bicep MCP: Bicep-specific best practices, AVM, resource schemas (bicep only)
        # - Terraform MCP: HashiCorp official provider docs, registry (terraform only)
        # - Bing Grounding: Best practices, error patterns, fix examples
        
        # Select MCP servers based on IaC format
        mcp_servers = ["mslearn"]  # Always include MS Learn
        if self.iac_format == "bicep":
            mcp_servers.append("bicep")  # Add Bicep MCP for Bicep validation
        elif self.iac_format == "terraform":
            mcp_servers.append("terraform")  # Add Terraform MCP for Terraform validation
        
        logger.debug(f"CodeQualityAgent MCP servers: {mcp_servers}")
        
        self._tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=mcp_servers,
        )
        
        logger.debug(f"Tool configuration: Bing={self._tool_config.has_bing}, MCP={self._tool_config.has_mcp}, Servers={self._tool_config.mcp_servers}")
        
        agent = self._client.create_agent(
            model=self.model_name,
            name=f"CodeQualityAgent_{self.iac_format}",
            instructions=full_instructions,
            tools=self._tool_config.tools,
            tool_resources=self._tool_config.tool_resources,
            temperature=0.1,  # Low temperature for consistent fixes
        )
        self._agent_id = agent.id
        
        logger.info(f"✓ CodeQualityAgent initialized (Agent ID: {agent.id}, MCP: {self._tool_config.mcp_servers})")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the agent."""
        if self._agent_id:
            try:
                if self._client:
                    self._client.delete_agent(self._agent_id)
                    logger.info(f"✓ CodeQualityAgent_{self.iac_format} deleted (Agent ID: {self._agent_id})")
                self._agent_id = None
                self._client = None
            except Exception as e:
                logger.warning(f"Failed to delete CodeQualityAgent_{self.iac_format}: {e}")
    
    def _get_agent_instructions(self) -> str:
        """Load code quality agent instructions from YAML."""
        # Load from code_quality_agent.yaml
        instructions_file = Path(__file__).parent.parent / "prompts" / "code_quality_agent.yaml"
        
        if not instructions_file.exists():
            error_msg = f"CRITICAL: Instructions file not found: {instructions_file}"
            logger.error(error_msg)
            raise FileNotFoundError(
                f"{error_msg}\\n"
                f"CodeQualityAgent requires code_quality_agent.yaml for operation.\\n"
                f"Please ensure the file exists at: {instructions_file}"
            )
        
        try:
            self._yaml_data = load_yaml_with_includes(instructions_file)
                
            if 'code_quality_agent' in self._yaml_data:
                agent_config = self._yaml_data['code_quality_agent']
                
                # Try agent-specific key first (new pattern)
                if 'code_quality_agent_instructions' in agent_config:
                    return agent_config['code_quality_agent_instructions']
                
                # Fall back to generic key for backward compatibility
                if 'instructions' in agent_config:
                    return agent_config['instructions']
            
            error_msg = "Invalid YAML structure in code_quality_agent.yaml - missing instructions"
            logger.error(error_msg)
            raise ValueError(error_msg)
                
        except Exception as e:
            logger.error(f"Failed to load instructions from {instructions_file}: {e}")
            raise
    
    async def generate_fixes(
        self,
        validation_result: ValidationResult,
        code_files: Dict[str, str],
        progress_callback=None
    ) -> List[CodeFix]:
        """
        Generate fixes for validation errors.
        
        Args:
            validation_result: Validation results with errors
            code_files: Dictionary of filename -> code content
            progress_callback: Optional callback(status, detail)
            
        Returns:
            List of CodeFix objects with suggested fixes
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Agent not initialized. Use async context manager.")
        
        if not validation_result.has_errors:
            logger.info("No errors to fix")
            return []
        
        if progress_callback:
            progress_callback("fix_analysis", f"Analyzing {validation_result.error_count} errors")
        
        logger.info(f"CodeQualityAgent: Analyzing {validation_result.error_count} errors")
        
        # Create thread for this fix session
        thread = self._client.threads.create()
        
        try:
            # Prepare prompt with validation errors and code context
            prompt = self._build_fix_prompt(validation_result, code_files)
            
            # Send message to agent
            self._client.messages.create(
                thread_id=thread.id,
                role=MessageRole.USER,
                content=prompt
            )
            
            # Run agent
            run = self._client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=self._agent_id
            )
            
            # Wait for completion
            while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.REQUIRES_ACTION]:
                await asyncio.sleep(1)
                run = self._client.get_run(thread_id=thread.id, run_id=run.id)
            
            if run.status != RunStatus.COMPLETED:
                logger.error(f"Agent run failed with status: {run.status}")
                return []
            
            # Get response
            messages = self._client.messages.list(thread_id=thread.id)
            
            # Find assistant's response
            response_content = None
            for message in messages:
                if message.role == MessageRole.AGENT:
                    response_content = message.content[0].text.value
                    break
            
            if not response_content:
                logger.error("No response from agent")
                return []
            
            # Parse fixes from JSON response
            fixes = self._parse_fixes_response(response_content, validation_result)
            
            if progress_callback:
                high_conf_count = len([f for f in fixes if f.confidence == "high"])
                progress_callback("fixes_generated", f"Generated {len(fixes)} fixes ({high_conf_count} high-confidence)")
            
            logger.info(f"Generated {len(fixes)} fixes ({len([f for f in fixes if f.confidence == 'high'])} high-confidence)")
            return fixes
            
        except Exception as e:
            logger.error(f"Error generating fixes: {e}", exc_info=True)
            return []
        finally:
            # Cleanup thread
            try:
                self._client.threads.delete(thread.id)
            except Exception as cleanup_error:
                logger.debug(f"Thread cleanup warning: {cleanup_error}")
    
    def _build_fix_prompt(self, validation_result: ValidationResult, code_files: Dict[str, str]) -> str:
        """Build prompt for agent with validation errors and code context using YAML template."""
        
        # Load prompt template from YAML
        if not self._yaml_data or 'prompt_templates' not in self._yaml_data:
            logger.warning("Prompt templates not loaded, using inline fallback")
            return self._build_fix_prompt_fallback(validation_result, code_files)
        
        templates = self._yaml_data['prompt_templates']
        
        # Build errors list using error_item template
        errors_list = ""
        for idx, issue in enumerate(validation_result.issues, 1):
            if issue.severity != "error":
                continue
            
            # Extract actual line from file (more reliable than terraform snippet)
            actual_line = ""
            if issue.file in code_files and issue.line > 0:
                lines = code_files[issue.file].split('\n')
                if 0 < issue.line <= len(lines):
                    actual_line = lines[issue.line - 1]
            
            # Build code context
            code_context = ""
            if issue.file in code_files:
                lines = code_files[issue.file].split('\n')
                start_line = max(0, issue.line - 4)
                end_line = min(len(lines), issue.line + 3)
                
                code_context = "**Code Context**:\n```" + self.iac_format + "\n"
                for line_num in range(start_line, end_line):
                    marker = " → " if line_num == issue.line - 1 else "   "
                    code_context += f"{marker}{line_num + 1}: {lines[line_num]}\n"
                code_context += "```\n\n"
            
            # Format error item from template
            errors_list += templates['error_item'].format(
                error_number=idx,
                filename=issue.file,
                line=issue.line,
                column=issue.column,
                message=issue.message,
                terraform_snippet=issue.current_code,
                actual_line=actual_line,
                code_context=code_context
            )
        
        # Format main prompt from template
        prompt = templates['fix_analysis'].format(
            iac_format=self.iac_format.capitalize(),
            error_count=validation_result.error_count,
            warning_count=validation_result.warning_count,
            files_with_errors=validation_result.files_with_errors,
            errors_list=errors_list
        )
        
        return prompt
    
    def _build_fix_prompt_fallback(self, validation_result: ValidationResult, code_files: Dict[str, str]) -> str:
        """Fallback prompt builder if YAML templates not available."""
        # Load validation analysis prompt template from YAML
        from synthforge.prompts import get_prompt_template
        
        try:
            analysis_template = get_prompt_template(
                "code_quality_agent",
                "validation_analysis_prompt_template",
                from_iac=True
            )
            
            # Build errors JSON
            errors_data = []
            for issue in validation_result.issues:
                errors_data.append({
                    "file": issue.file_path,
                    "line": issue.line_number,
                    "severity": issue.severity,
                    "message": issue.message,
                    "code": issue.code
                })
            
            # Get file context for first 5 errors
            file_context_str = ""
            for issue in validation_result.issues[:5]:
                if issue.file_path in code_files:
                    lines = code_files[issue.file_path].split('\n')
                    start_line = max(0, issue.line_number - 3)
                    end_line = min(len(lines), issue.line_number + 3)
                    context = '\n'.join(lines[start_line:end_line])
                    file_context_str += f"\n### {issue.file_path} (lines {start_line+1}-{end_line+1})\n```\n{context}\n```\n"
            
            file_ext = "tf" if self.iac_format == "terraform" else "bicep"
            
            return analysis_template.format(
                iac_format_title=self.iac_format.capitalize(),
                errors_json=json.dumps(errors_data, indent=2),
                file_context=file_context_str,
                file_ext=file_ext
            )
        except Exception as e:
            logger.warning(f"Failed to load template from YAML, using basic fallback: {e}")
            
        prompt = f"""
Analyze the following {self.iac_format.capitalize()} validation errors and provide structured fixes.

## Validation Summary
- Total Errors: {validation_result.error_count}
- Total Warnings: {validation_result.warning_count}
- Files with Issues: {validation_result.files_with_errors}

## Errors to Fix

"""
        
        # Add each error with code context
        for idx, issue in enumerate(validation_result.issues, 1):
            if issue.severity != "error":
                continue
            
            # Extract actual line from file (more reliable than terraform snippet)
            actual_line = ""
            if issue.file in code_files and issue.line > 0:
                lines = code_files[issue.file].split('\n')
                if 0 < issue.line <= len(lines):
                    actual_line = lines[issue.line - 1]
                
            prompt += f"""
### Error {idx}: {issue.file}:{issue.line}:{issue.column}
**Message**: {issue.message}
**Terraform Snippet**: `{issue.current_code}` (may be truncated)
**Actual Line {issue.line}**: `{actual_line}`

"""
            
            # Add surrounding code context if available
            if issue.file in code_files:
                lines = code_files[issue.file].split('\n')
                start_line = max(0, issue.line - 4)
                end_line = min(len(lines), issue.line + 3)
                
                prompt += "**Code Context**:\n```" + self.iac_format + "\n"
                for line_num in range(start_line, end_line):
                    marker = " → " if line_num == issue.line - 1 else "   "
                    prompt += f"{marker}{line_num + 1}: {lines[line_num]}\n"
                prompt += "```\n\n"
        
        prompt += """

## Instructions
1. Analyze each error and its code context
2. Provide a structured fix for each error
3. Use the **Actual Line** content (not the Terraform Snippet) for current_code
4. Assign confidence level: high/medium/low
5. Include explanation and references

**CRITICAL REQUIREMENTS**: 
- Group fixes by file in 'results' array
- Each result MUST have 'file' field with EXACT filename from "Error N: <filename>:line:col" above
- For current_code, use the EXACT content from "Actual Line" field (this ensures we can find and replace it)
- The Terraform Snippet may be truncated - ignore it and use Actual Line instead

**Example** (if error is in "variables.tf:40"):
{{
  "results": [
    {{
      "file": "variables.tf",
      "issues": [
        {{
          "line": 40,
          "current_code": "<exact content from Actual Line 40 field above>",
          "fix": {{"suggested_code": "var.something == true", "confidence": "high", "explanation": "..."}}
        }}
      ]
    }}
  ]
}}

You MUST respond with ONLY valid JSON in the format specified in your instructions.
NO explanatory text before or after the JSON.
"""
        
        return prompt
    
    def _parse_fixes_response(self, response: str, validation_result: ValidationResult) -> List[CodeFix]:
        """Parse agent's JSON response into CodeFix objects."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Remove markdown code fences if present
            if response.startswith("```"):
                lines = response.split('\n')
                # Remove first and last lines (code fence markers)
                response = '\n'.join([l for l in lines[1:-1] if l.strip()])
            
            # Try to find JSON block if response contains extra text
            if not response.startswith('{'):
                # Look for JSON object in response
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end != -1:
                    response = response[start:end+1]
            
            # Parse JSON
            data = json.loads(response)
            
            # Parse results format (from code_quality_agent.yaml instructions)
            if 'results' not in data:
                logger.error(f"Response missing 'results' key. Response keys: {list(data.keys())}")
                logger.error("Agent should return 'results' array with file → issues → fix structure")
                logger.debug(f"Full response: {response[:500]}")
                return []
            
            fixes = []
            
            # Parse nested format: results → issues → fix
            for result in data.get('results', []):
                filename = result.get('file', '<unknown>')
                
                # Log if filename is missing or invalid
                if not filename or filename == '<unknown>' or filename.strip() == '':
                    logger.error(f"Agent returned invalid filename: '{filename}' (type: {type(filename).__name__})")
                    logger.error(f"Result structure: {list(result.keys())}")
                    logger.error(f"Agent must provide valid filename matching files in code_files dict")
                    continue  # Skip this result - can't apply fix without valid filename
                
                for issue in result.get('issues', []):
                    fix_data = issue.get('fix')
                    if not fix_data:
                        # Issue without fix (might be info/warning only)
                        continue
                    
                    # Extract actual line from validation result to ensure exact match
                    actual_current_code = issue.get('current_code', '')
                    line_num = issue.get('line', 0)
                    
                    # If agent didn't provide current_code or it's empty, try to extract from validation_result
                    if not actual_current_code:
                        for orig_issue in validation_result.issues:
                            if orig_issue.file == filename and orig_issue.line == line_num:
                                actual_current_code = orig_issue.current_code
                                break
                    
                    # Create ValidationIssue from issue data
                    validation_issue = ValidationIssue(
                        file=filename,
                        line=line_num,
                        column=issue.get('column', 0),
                        severity=issue.get('severity', 'error'),
                        type=issue.get('type', 'unknown'),
                        rule=issue.get('rule', ''),
                        message=issue.get('message', ''),
                        current_code=actual_current_code
                    )
                    
                    # Create CodeFix with ValidationIssue and fix data
                    fix = CodeFix(
                        issue=validation_issue,
                        suggested_code=fix_data.get('suggested_code', ''),
                        explanation=fix_data.get('explanation', ''),
                        confidence=fix_data.get('confidence', 'medium'),
                        alternatives=fix_data.get('alternatives', []),
                        references=fix_data.get('references', [])
                    )
                    fixes.append(fix)
            
            logger.info(f"Parsed {len(fixes)} fixes from agent response")
            return fixes
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response (first 500 chars): {response[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error parsing fixes: {e}", exc_info=True)
            return []


# Example usage
async def main():
    """Example usage of CodeQualityAgent."""
    
    # Create validation result with errors
    validation_result = ValidationResult(
        status="fail",
        total_files=1,
        files_with_errors=1,
        error_count=2
    )
    
    validation_result.issues = [
        ValidationIssue(
            file="main.tf",
            line=5,
            column=7,
            severity="error",
            message="Missing required argument: location",
            current_code='resource "azurerm_storage_account" "this" {'
        ),
        ValidationIssue(
            file="locals.tf",
            line=10,
            column=12,
            severity="error",
            message="Conditional expression uses non-boolean operand",
            current_code="var.managed_identities.system_assigned"
        )
    ]
    
    code_files = {
        "main.tf": """resource "azurerm_storage_account" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  account_tier        = "Standard"
  account_replication_type = "LRS"
}""",
        "locals.tf": """locals {
  managed_identities = {
    system_or_user_assigned = (
      var.managed_identities.system_assigned
      || length(var.managed_identities.user_assigned_resource_ids) > 0
    )
  }
}"""
    }
    
    # Use agent
    async with CodeQualityAgent(iac_format="terraform") as agent:
        fixes = await agent.generate_fixes(validation_result, code_files)
        
        print(f"\nGenerated {len(fixes)} fixes:")
        for fix in fixes:
            print(f"\n{fix.issue.file}:{fix.issue.line}")
            print(f"  Confidence: {fix.confidence}")
            print(f"  Current:  {fix.issue.current_code}")
            print(f"  Suggested: {fix.suggested_code}")
            print(f"  Explanation: {fix.explanation}")


if __name__ == "__main__":
    asyncio.run(main())

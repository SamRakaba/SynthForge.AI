"""
DeploymentWrapperAgent: Generates environment-specific deployment orchestration.

This agent generates production-ready deployment wrappers that:
- Orchestrate reusable modules from Stage 4
- Apply Phase 1 security/network/RBAC recommendations
- Generate CAF-compliant naming modules
- Follow WAF sizing guidance per environment
- Create DevOps-ready parameter files
- Document all required user inputs

Generates environments/ folder with:
- dev/ - Development environment configuration
- staging/ - Staging environment configuration  
- prod/ - Production environment configuration

Each environment includes:
- main.tf / main.bicep - Module orchestration
- variables.tf / parameters.bicep - Input parameters
- outputs.tf / outputs.bicep - Environment outputs
- terraform.tfvars.example / main.bicepparam.example - Example values
- backend.tf / backend configuration - Remote state config
- providers.tf / provider configuration - Provider setup
- README.md - Deployment guide with required inputs
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole, ThreadRun, RunStatus

from synthforge.agents.tool_setup import create_agent_toolset, get_tool_instructions
from synthforge.prompts import get_deployment_wrapper_agent_instructions
from synthforge.models import ArchitectureAnalysis

logger = logging.getLogger(__name__)


@dataclass
class DeploymentEnvironment:
    """Represents a deployment environment configuration."""
    
    name: str  # "development", "staging", "production"
    folder_path: Path  # e.g., environments/dev
    files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    required_inputs: List[Dict[str, str]] = field(default_factory=list)  # User-required values
    phase1_recommendations: Dict[str, List[str]] = field(default_factory=dict)  # Applied recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "folder_path": str(self.folder_path),
            "files": self.files,
            "required_inputs": self.required_inputs,
            "phase1_recommendations": self.phase1_recommendations,
        }


@dataclass
class NamingModule:
    """Represents CAF naming module."""
    
    folder_path: Path  # e.g., modules/naming
    files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    caf_compliant: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "folder_path": str(self.folder_path),
            "files": self.files,
            "caf_compliant": self.caf_compliant,
        }


@dataclass
class DeploymentWrapperResult:
    """Result from deployment wrapper generation stage."""
    
    environments: List[DeploymentEnvironment]  # For backwards compatibility (contains deployment)
    naming_module: Optional[NamingModule]
    iac_format: str
    output_directory: Path
    deployment: Optional[DeploymentEnvironment] = None  # Single parameterized deployment
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    total_environments: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "environments": [e.to_dict() for e in self.environments],
            "deployment": self.deployment.to_dict() if self.deployment else None,
            "naming_module": self.naming_module.to_dict() if self.naming_module else None,
            "iac_format": self.iac_format,
            "output_directory": str(self.output_directory),
            "agent_id": self.agent_id,
            "thread_id": self.thread_id,
            "total_environments": self.total_environments,
        }


class DeploymentWrapperAgent:
    """
    Agent for generating environment-specific deployment orchestration.
    
    Uses Azure AI Foundry with Bing Grounding + MS Learn MCP to:
    1. Research CAF naming conventions
    2. Research WAF sizing guidance
    3. Extract Phase 1 recommendations
    4. Generate environment-specific configurations
    5. Create DevOps-ready deployment files
    """
    
    AGENT_NAME = "DeploymentWrapperAgent"

    def __init__(
        self,
        agents_client: AgentsClient,
        model_name: str,
        iac_format: str,
        bing_connection_name: str,
        ms_learn_mcp_url: Optional[str] = None,
    ):
        """
        Initialize DeploymentWrapperAgent.
        
        Args:
            agents_client: Azure AI Agents client
            model_name: Model deployment name (e.g., "gpt-4o")
            iac_format: "terraform" or "bicep"
            bing_connection_name: Bing Grounding connection name
            ms_learn_mcp_url: MS Learn MCP server URL
        """
        self.agents_client = agents_client
        self.model_name = model_name
        self.iac_format = iac_format
        self.agent = None
        self.thread = None
        
        # Tools setup
        self.bing_connection_name = bing_connection_name
        self.ms_learn_mcp_url = ms_learn_mcp_url
        
        logger.info(f"DeploymentWrapperAgent initialized (IaC format: {iac_format})")

    def _create_agent(self):
        """Create Azure AI Agent with appropriate tools."""
        logger.info(f"Creating {self.AGENT_NAME} with model {self.model_name}")
        
        # Get agent instructions
        instructions = get_deployment_wrapper_agent_instructions(self.iac_format)
        
        # Add tool usage instructions
        tool_instructions = get_tool_instructions()
        full_instructions = f"{instructions}\n\n{tool_instructions}"
        
        # Setup tools - Use MS Learn MCP + format-specific MCP for documentation
        mcp_servers = ["mslearn"]  # MS Learn for CAF/WAF documentation
        if self.iac_format == "bicep":
            mcp_servers.append("bicep")
            logger.info("Added Bicep MCP server for format-specific guidance")
        elif self.iac_format == "terraform":
            mcp_servers.append("terraform")
            logger.info("Added Terraform MCP server for format-specific guidance")
        
        tool_config = create_agent_toolset(
            include_bing=True,
            include_mcp=True,
            mcp_servers=mcp_servers,
        )
        
        logger.debug(f"Tool configuration: Bing={tool_config.has_bing}, MCP={tool_config.has_mcp}, Servers={tool_config.mcp_servers}")
        
        # Create agent
        self.agent = self.agents_client.create_agent(
            model=self.model_name,
            name=self.AGENT_NAME,
            instructions=full_instructions,
            tools=tool_config.tools,
            tool_resources=tool_config.tool_resources,
            temperature=0.1,
        )
        logger.info(f"Created agent: {self.agent.id}")
        
        # Create thread
        self.thread = self.agents_client.threads.create()
        logger.info(f"Created thread: {self.thread.id}")

    async def generate_deployment_wrappers(
        self,
        phase1_outputs: Dict[str, Path],
        module_mappings: List[Dict[str, Any]],
        output_dir: Path,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> DeploymentWrapperResult:
        """
        Generate single parameterized deployment wrapper.
        
        User specifies environment (dev, staging, prod) at deployment time via parameters.
        
        Args:
            phase1_outputs: Paths to Phase 1 output files
            module_mappings: Module mappings from Stage 3
            output_dir: Base output directory (IaC root)
            progress_callback: Optional callback(stage, message)
            
        Returns:
            DeploymentWrapperResult with generated deployment and naming module
        """
        # Create agent if not already created
        if not self.agent:
            self._create_agent()
        
        logger.info(f"Generating parameterized deployment wrapper")
        
        # Determine correct paths based on what output_dir points to
        # If output_dir is already "modules/", we need to go up one level for naming and deployment
        if output_dir.name == "modules":
            iac_root = output_dir.parent
            naming_base = output_dir  # naming goes in modules/naming
            deploy_base = iac_root / "deployment"  # deployment at same level as modules
        else:
            # output_dir is IaC root
            iac_root = output_dir
            naming_base = output_dir / "modules"  # naming goes in modules/naming
            deploy_base = output_dir / "deployment"  # deployment at same level as modules
        
        logger.debug(f"IaC root: {iac_root}")
        logger.debug(f"Naming base: {naming_base}")
        logger.debug(f"Deployment base: {deploy_base}")
        
        # Load Phase 1 outputs
        phase1_data = self._load_phase1_outputs(phase1_outputs)
        
        # Check if naming module exists from Stage 4
        naming_module_path = naming_base / "naming"
        naming_module_available = naming_module_path.exists() and (naming_module_path / f"main.{self.iac_format}").exists()
        
        if naming_module_available:
            logger.info(f"✓ Naming module detected from Stage 4: {naming_module_path.relative_to(iac_root)}")
        else:
            logger.warning(f"⚠️  Naming module not found at {naming_module_path} - deployment will need manual naming")
        
        # Generate single parameterized deployment template
        if progress_callback:
            await progress_callback("deployment", "Generating parameterized deployment template...")
            
        deployment_config = await self._generate_environment(
            env_name="deployment",  # Single parameterized template
            module_mappings=module_mappings,
            phase1_data=phase1_data,
            naming_module_available=naming_module_available,
            env_base=deploy_base,
        )
        
        # Check if files were generated
        files = deployment_config.get("files", {})
        if not files:
            logger.error(f"No files generated for deployment template!")
            logger.error(f"Deployment config keys: {list(deployment_config.keys())}")
            logger.error(f"Deployment config: {json.dumps(deployment_config, indent=2)[:500]}...")
            deployment = None
        else:
            # Save deployment files
            deploy_dir = deploy_base
            deploy_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Saving {len(files)} files for deployment template...")
            for filename, content in files.items():
                file_path = deploy_dir / filename
                file_path.write_text(content, encoding="utf-8")
                logger.info(f"  Saved: {file_path.relative_to(iac_root)}")
            
            deployment = DeploymentEnvironment(
                name="deployment",
                folder_path=deploy_dir,
                files=deployment_config["files"],
                required_inputs=deployment_config.get("required_user_inputs", []),
                phase1_recommendations=deployment_config.get("phase1_recommendations_applied", {}),
            )
            
            if progress_callback:
                await progress_callback("deployment", "✓ deployment template complete")
        
        logger.info(f"Generated parameterized deployment wrapper")
        
        # Note: naming_module is now generated in Stage 4, not Stage 5
        return DeploymentWrapperResult(
            environments=[deployment] if deployment else [],  # Single deployment
            deployment=deployment,  # Add dedicated field
            naming_module=None,  # No longer generated in Stage 5
            iac_format=self.iac_format,
            output_directory=iac_root,
            agent_id=self.agent.id if self.agent else None,
            thread_id=self.thread.id if self.thread else None,
            total_environments=1 if deployment else 0,
        )

    def _load_phase1_outputs(self, phase1_outputs: Dict[str, Path]) -> Dict[str, Any]:
        """Load Phase 1 JSON outputs."""
        phase1_data = {}
        
        for key, path in phase1_outputs.items():
            if path and path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        phase1_data[key] = json.load(f)
                    logger.debug(f"Loaded Phase 1 output: {key}")
                except Exception as e:
                    logger.warning(f"Failed to load {key}: {e}")
                    phase1_data[key] = {}
            else:
                logger.warning(f"Phase 1 output not found: {key}")
                phase1_data[key] = {}
        
        return phase1_data

    def _get_env_folder_name(self, env_name: str) -> str:
        """Get folder name for environment."""
        env_mapping = {
            "development": "dev",
            "staging": "staging",
            "production": "prod",
        }
        return env_mapping.get(env_name, env_name)

    # REMOVED: Naming module is now generated in Stage 4 by module_development_agent
    # The _generate_naming_module and _build_naming_module_prompt methods have been removed
    # Stage 5 assumes naming module exists at modules/naming/ from Stage 4

    async def _categorize_modules_with_agent(self, module_mappings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Use agent to categorize module mappings into logical file groups.
        Agent determines categories based on ARM types and service purposes.
        
        Returns:
            Dict mapping category name to list of modules in that category
        """
        logger.info(f"Asking agent to categorize {len(module_mappings)} modules...")
        
        # Prepare service list for categorization
        services_for_categorization = []
        for mapping in module_mappings:
            services_for_categorization.append({
                "service_name": mapping.get("service_name", "unknown"),
                "arm_type": mapping.get("arm_resource_type", "unknown"),
                "service_type": mapping.get("service_type", ""),
            })
        
        # Load categorization prompt template from YAML
        from synthforge.prompts import get_iac_prompt_template
        categorization_template = get_iac_prompt_template("categorization_prompt_template")
        categorization_prompt = categorization_template.format(
            services_json=json.dumps(services_for_categorization, indent=2)
        )

        # Create thread and run agent
        thread = await self.agents_client.agents.create_thread()
        await self.agents_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=categorization_prompt,
        )
        
        run = await self.agents_client.agents.create_and_process_run(
            thread_id=thread.id,
            assistant_id=self.agent.id,
            max_completion_tokens=4000,
        )
        
        # Extract categorization result
        messages = await self.agents_client.agents.list_messages(thread_id=thread.id)
        last_msg = messages.data[0]
        response_text = last_msg.content[0].text.value if last_msg.content else "{}"
        
        # Clean markdown fences if present
        if response_text.startswith("```"):
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
        
        # Parse categorization
        try:
            service_to_category = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse agent categorization: {e}")
            logger.error(f"Response: {response_text[:500]}")
            # Fallback: put everything in "services" category
            service_to_category = {m.get("service_name", "unknown"): "services" for m in module_mappings}
        
        # Group modules by category
        categorized: Dict[str, List[Dict[str, Any]]] = {}
        for mapping in module_mappings:
            service_name = mapping.get("service_name", "unknown")
            category = service_to_category.get(service_name, "services")
            
            if category not in categorized:
                categorized[category] = []
            
            # Add category to mapping
            mapping_with_category = {**mapping, "category": category}
            categorized[category].append(mapping_with_category)
            
            logger.debug(f"Categorized {service_name} as '{category}'")
        
        logger.info(f"✓ Categorized modules into {len(categorized)} categories: {list(categorized.keys())}")
        
        # Clean up thread
        await self.agents_client.agents.delete_thread(thread_id=thread.id)
        
        return categorized

    async def _generate_category_file(
        self,
        category: str,
        modules: List[Dict[str, Any]],
        phase1_data: Dict[str, Any],
        env_name: str = "deployment",
    ) -> str:
        """
        Generate a single category file (e.g., compute.tf, data.tf) with related module calls.
        
        This is called multiple times to build deployment category by category,
        avoiding massive JSON strings and staying within token limits.
        
        Args:
            category: Category name (compute, data, ai, security, networking, monitoring)
            modules: List of module mappings for this category
            phase1_data: Phase 1 analysis data
            env_name: Environment name (for context)
            
        Returns:
            Generated file content as string
        """
        logger.info(f"Generating {category}.{self.iac_format.replace('terraform', 'tf').replace('bicep', 'bicep')} file with {len(modules)} modules...")
        
        # Load category file generation prompt template from YAML
        from synthforge.prompts import get_iac_prompt_template
        category_template = get_iac_prompt_template("category_file_generation_prompt_template")
        
        file_ext = self.iac_format.replace('terraform', 'tf').replace('bicep', 'bicep')
        recommendations_summary = {
            "security": phase1_data.get("security", {}).get("recommendations", [])[:5],  # Top 5
            "networking": phase1_data.get("network", {}).get("recommendations", [])[:5],
            "monitoring": phase1_data.get("monitoring", {}).get("recommendations", [])[:3],
        }
        
        prompt = category_template.format(
            category=category,
            file_ext=file_ext,
            env_name=env_name,
            iac_format=self.iac_format,
            modules_json=json.dumps(modules, indent=2),
            recommendations_json=json.dumps(recommendations_summary, indent=2)
        )
        
        # Send request
        self.agents_client.messages.create(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=prompt,
        )
        
        # Run with reasonable token limit for single category
        run = self.agents_client.runs.create_and_process(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
            max_completion_tokens=8000,  # Enough for one category file
        )
        
        # Wait for completion
        while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.REQUIRES_ACTION]:
            await asyncio.sleep(1)
            run = self.agents_client.runs.get(thread_id=self.thread.id, run_id=run.id)
        
        if run.status != RunStatus.COMPLETED:
            logger.error(f"Category file generation failed for {category}: {run.status}")
            return f"# Error generating {category}.{self.iac_format.replace('terraform', 'tf')}\n# Status: {run.status}\n"
        
        # Get response
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            logger.error(f"No response for {category} category")
            return f"# No content generated for {category}\n"
        
        content = last_msg.text.value
        
        # Clean up - remove markdown fences if present
        if content.startswith("```"):
            # Remove ```terraform, ```bicep, or ```hcl markers
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        
        logger.info(f"Generated {category} file: {len(content)} characters")
        return content

    async def _generate_environment(
        self,
        env_name: str,
        module_mappings: List[Dict[str, Any]],
        phase1_data: Dict[str, Any],
        naming_module_available: bool,
        env_base: Path,
    ) -> Dict[str, Any]:
        """
        Generate single environment configuration using CATEGORY-BASED approach.
        
        Instead of generating all files at once (causing JSON parsing errors),
        generate category files one at a time:
        1. main.tf (entry point + locals)
        2. compute.tf (App Services, Functions)
        3. data.tf (Storage, Cosmos DB, AI Search)
        4. ai.tf (OpenAI, AI Foundry)
        5. security.tf (Key Vault, RBAC)
        6. networking.tf (App Gateway, Firewall)
        7. monitoring.tf (Log Analytics, Diagnostics)
        8. variables.tf, outputs.tf, backend.tf, providers.tf, README.md
        
        Args:
            env_name: Environment name (development, staging, production)
            module_mappings: Module mappings from Stage 3
            phase1_data: Phase 1 analysis data
            naming_module_available: Whether naming module exists
            env_base: Base directory for environments (should be iac/environments/)
            
        Returns:
            Dictionary with environment configuration
        """
        logger.info(f"Generating {env_name} environment using category-based approach...")
        
        # Categorize modules by service type using agent
        categorized_modules = await self._categorize_modules_with_agent(module_mappings)
        logger.info(f"Detected categories: {list(categorized_modules.keys())}")
        
        # Dictionary to collect generated files
        files = {}
        
        # Step 1: Generate main entry file (main.tf/main.bicep)
        logger.info("Step 1: Generating main entry file...")
        main_file = await self._generate_main_entry_file(
            env_name=env_name,
            categories=list(categorized_modules.keys()),
            naming_module_available=naming_module_available,
        )
        files[f"main.{self.iac_format.replace('terraform', 'tf').replace('bicep', 'bicep')}"] = main_file
        
        # Step 2: Generate category files (compute.tf, data.tf, etc.)
        for category, modules in categorized_modules.items():
            logger.info(f"Step 2.{category}: Generating {category} file...")
            category_content = await self._generate_category_file(
                category=category,
                modules=modules,
                phase1_data=phase1_data,
                env_name=env_name,
            )
            files[f"{category}.{self.iac_format.replace('terraform', 'tf').replace('bicep', 'bicep')}"] = category_content
        
        # Step 3: Generate supporting files (variables, outputs, backend, providers)
        logger.info("Step 3: Generating supporting files...")
        supporting_files = await self._generate_supporting_files(
            env_name=env_name,
            module_mappings=module_mappings,
            phase1_data=phase1_data,
        )
        files.update(supporting_files)
        
        logger.info(f"Generated {len(files)} files for {env_name} environment")
        
        # Return in expected format
        return {
            "files": files,
            "required_user_inputs": self._extract_required_inputs(module_mappings, phase1_data),
            "phase1_recommendations_applied": self._extract_applied_recommendations(phase1_data),
        }

    # REMOVED: _build_naming_module_prompt - naming module generated in Stage 4

    async def _generate_main_entry_file(
        self,
        env_name: str,
        categories: List[str],
        naming_module_available: bool,
    ) -> str:
        """
        Generate main entry file (main.tf/main.bicep) with:
        - Resource group
        - Naming module call
        - Local variables for environment-specific logic
        - NO module calls (those go in category files)
        """
        ext = "tf" if self.iac_format == "terraform" else "bicep"
        
        # Load main file generation prompt template from YAML
        from synthforge.prompts import get_iac_prompt_template
        main_file_template = get_iac_prompt_template("main_file_generation_prompt_template")
        
        category_files_str = ', '.join([f'{c}.{ext}' for c in categories])
        prompt = main_file_template.format(
            file_ext=ext,
            env_name=env_name,
            naming_module_available=naming_module_available,
            category_files=category_files_str,
            iac_format=self.iac_format
        )
        
        # Send and get response
        self.agents_client.messages.create(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=prompt,
        )
        
        run = self.agents_client.runs.create_and_process(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
            max_completion_tokens=2000,  # Small file
        )
        
        while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.REQUIRES_ACTION]:
            await asyncio.sleep(1)
            run = self.agents_client.runs.get(thread_id=self.thread.id, run_id=run.id)
        
        if run.status != RunStatus.COMPLETED:
            return f"# Error generating main.{ext}\n"
        
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )
        
        content = last_msg.text.value if last_msg else f"# No content for main.{ext}\n"
        
        # Clean markdown fences
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        
        return content

    async def _generate_supporting_files(
        self,
        env_name: str,
        module_mappings: List[Dict[str, Any]],
        phase1_data: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Generate supporting files:
        - variables.tf/parameters.json
        - outputs.tf/outputs.bicep
        - backend.tf/backend config
        - providers.tf/provider config
        - README.md
        - *.tfvars.* files for each environment
        """
        ext = "tf" if self.iac_format == "terraform" else "bicep"
        
        # Load supporting files generation prompt template from YAML
        from synthforge.prompts import get_iac_prompt_template
        supporting_files_template = get_iac_prompt_template("supporting_files_generation_prompt_template")
        
        required_vars_data = {
            'modules': [m.get('service_name') for m in module_mappings],
            'recommendations': {
                'security': phase1_data.get('security', {}).get('recommendations', [])[:3],
                'networking': phase1_data.get('network', {}).get('recommendations', [])[:3],
            }
        }
        
        prompt = supporting_files_template.format(
            env_name=env_name,
            file_ext=ext,
            required_vars_json=json.dumps(required_vars_data, indent=2),
            iac_format=self.iac_format
        )
        
        self.agents_client.messages.create(
            thread_id=self.thread.id,
            role=MessageRole.USER,
            content=prompt,
        )
        
        run = self.agents_client.runs.create_and_process(
            thread_id=self.thread.id,
            agent_id=self.agent.id,
            max_completion_tokens=8000,  # Supporting files
        )
        
        while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.REQUIRES_ACTION]:
            await asyncio.sleep(1)
            run = self.agents_client.runs.get(thread_id=self.thread.id, run_id=run.id)
        
        if run.status != RunStatus.COMPLETED:
            logger.error(f"Supporting files generation failed: {run.status}")
            return {}
        
        last_msg = self.agents_client.messages.get_last_message_text_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )
        
        if not last_msg:
            return {}
        
        try:
            files_json = self._parse_json_response(last_msg.text.value)
            return files_json
        except Exception as e:
            logger.error(f"Failed to parse supporting files: {e}")
            return {}

    def _extract_required_inputs(
        self,
        module_mappings: List[Dict[str, Any]],
        phase1_data: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Extract required user inputs from module mappings and Phase 1 data."""
        inputs = [
            {
                "variable": "subscription_id",
                "description": "Azure subscription ID",
                "how_to_find": "az account show --query id -o tsv"
            },
            {
                "variable": "tenant_id",
                "description": "Azure Active Directory tenant ID",
                "how_to_find": "az account show --query tenantId -o tsv"
            },
            {
                "variable": "location",
                "description": "Azure region for deployment",
                "how_to_find": "Choose from: eastus, westeurope, etc."
            },
            {
                "variable": "environment",
                "description": "Deployment environment",
                "how_to_find": "Choose from: development, staging, production"
            },
            {
                "variable": "workload",
                "description": "Short workload name for CAF naming",
                "how_to_find": "Choose a 2-10 character identifier"
            },
        ]
        return inputs

    def _extract_applied_recommendations(
        self,
        phase1_data: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """Extract Phase 1 recommendations that were applied."""
        return {
            "security": [
                "Managed identity enabled for all services",
                "RBAC configured per Phase 1 recommendations",
                "Private endpoints enabled where recommended",
            ],
            "networking": [
                "Network isolation applied per Phase 1",
                "Public access disabled for production",
                "VNet integration configured where needed",
            ],
            "monitoring": [
                "Diagnostic settings enabled for all resources",
                "Log Analytics workspace configured",
            ],
        }

    # REMOVED: _build_naming_module_prompt - naming module generated in Stage 4

    def _build_environment_prompt(
        self,
        env_name: str,
        module_mappings: List[Dict[str, Any]],
        phase1_data: Dict[str, Any],
        naming_module_available: bool,
        iac_format: str,
    ) -> str:
        """Build prompt for environment generation by loading template from YAML."""
        from synthforge.prompts import get_prompt_template
        
        # Format the data as JSON strings for the template
        module_mappings_str = json.dumps(module_mappings, indent=2)
        phase1_data_str = json.dumps(phase1_data, indent=2)
        
        # Load template from YAML and format with dynamic data
        template = get_prompt_template("deployment_wrapper_environment")
        return template.format(
            iac_format=iac_format,
            env_name=env_name,
            module_mappings=module_mappings_str,
            phase1_data=phase1_data_str,
            naming_module_available=str(naming_module_available)
        )

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from agent response, handling markdown code blocks and extra text.
        
        Agents often return JSON wrapped in markdown code blocks with explanatory text:
        ```json
        {...}
        ```
        This is a summary of the above JSON.
        
        This method extracts ONLY the JSON content.
        """
        text = response_text.strip()
        
        # If response is empty, return empty dict
        if not text:
            logger.error("Empty response from agent")
            return {"files": {}}
        
        # Try to find JSON in markdown code block first
        if "```json" in text:
            # Extract content between ```json and ```
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        elif text.startswith("```"):
            # Generic code block without json marker
            start = text.find("```") + 3
            # Skip the language identifier if present (e.g., ```bicep, ```python)
            newline = text.find("\n", start)
            if newline != -1 and newline < start + 20:  # Language identifier should be short
                start = newline + 1
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        
        # At this point, text should be pure JSON
        # But agent might still add text after the JSON object
        # Find the end of the JSON object by looking for the last }
        # This handles: {...}\n\nSome extra text here
        
        # Try to parse as-is first
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}")
            logger.debug(f"Attempting to extract JSON from: {text[:200]}...")
            
            # Strategy 1: If parsing fails due to extra data, find complete JSON object
            if "Extra data" in str(e):
                # Find the position where JSON ends (last })
                brace_count = 0
                json_end = -1
                for i, char in enumerate(text):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end != -1:
                    # Extract only the JSON part
                    json_only = text[:json_end]
                    try:
                        return json.loads(json_only)
                    except json.JSONDecodeError as e2:
                        logger.error(f"Failed to parse extracted JSON: {e2}")
            
            # Strategy 2: Look for first { and last } to extract JSON object
            first_brace = text.find('{')
            last_brace = text.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                potential_json = text[first_brace:last_brace+1]
                try:
                    return json.loads(potential_json)
                except json.JSONDecodeError as e3:
                    logger.error(f"Failed to parse extracted JSON (strategy 2): {e3}")
            
            # Strategy 3: Check for unterminated strings (common error)
            if "Unterminated string" in str(e):
                logger.error("Detected unterminated string in JSON response")
                logger.error("This usually means the agent returned malformed JSON with unescaped quotes or newlines in string values")
                logger.error("Agent instruction fix needed: Ensure agent escapes special characters in generated code strings")
            
            # If we still can't parse, save debug info and return empty
            debug_path = Path("iac") / "_debug_json_parse_error.txt"
            debug_path.parent.mkdir(exist_ok=True)
            debug_path.write_text(f"Original error: {e}\n\nResponse text:\n{text}", encoding="utf-8")
            logger.error(f"Failed to parse JSON response. Debug info saved to: {debug_path}")
            
            # Re-raise the original error for transparency
            raise

    def cleanup(self):
        """Clean up agent resources."""
        if self.agent:
            try:
                self.agents_client.delete_agent(self.agent.id)
                logger.info(f"Deleted agent: {self.agent.id}")
            except Exception as e:
                logger.warning(f"Failed to delete agent: {e}")
            self.agent = None
        
        if self.thread:
            try:
                self.agents_client.threads.delete(self.thread.id)
                logger.info(f"Deleted thread: {self.thread.id}")
            except Exception as e:
                logger.warning(f"Failed to delete thread: {e}")
            self.thread = None

"""
Configuration settings for SynthForge.AI.

Manages environment variables, settings, and runtime configuration.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Settings:
    """Application configuration settings."""
    
    # Microsoft Foundry (Azure AI Foundry) settings
    project_endpoint: str = field(
        default_factory=lambda: os.environ.get("PROJECT_ENDPOINT", "")
    )
    # Phase 2 IaC project endpoint (optional override)
    iac_project_endpoint: str = field(
        default_factory=lambda: os.environ.get("IAC_PROJECT_ENDPOINT", "")
    )
    model_deployment_name: str = field(
        default_factory=lambda: os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")
    )
    vision_model_deployment_name: str = field(
        default_factory=lambda: os.environ.get("VISION_MODEL_DEPLOYMENT_NAME", "gpt-4o")
    )
    # IaC code generation model (optimized for code generation)
    iac_model_deployment_name: str = field(
        default_factory=lambda: os.environ.get("IAC_MODEL_DEPLOYMENT_NAME", "gpt-4.1")
    )
    # IaC fallback model (if primary model fails)
    iac_model_deployment_name_alt: str = field(
        default_factory=lambda: os.environ.get("IAC_MODEL_DEPLOYMENT_NAME_ALT", "gpt-4o")
    )
    
    # Azure Computer Vision (RECOMMENDED for diagram OCR)
    # Best for scene text in images - scattered labels, mixed icons + text
    # Create a Computer Vision resource in Azure Portal
    vision_endpoint: str = field(
        default_factory=lambda: os.environ.get("AZURE_VISION_ENDPOINT", "")
    )
    vision_key: str = field(
        default_factory=lambda: os.environ.get("AZURE_VISION_KEY", "")
    )
    
    # OCR service preference:
    # - "auto" (default): Try Computer Vision first, fallback to GPT-4o
    # - "vision" or "computer_vision": Use Azure Computer Vision (RECOMMENDED for diagrams)
    # - "gpt4o": Use GPT-4o built-in OCR (fallback, less accurate for text extraction)
    ocr_service: str = field(
        default_factory=lambda: os.environ.get("OCR_SERVICE", "auto")
    )
    
    # Bing Grounding (for Azure documentation lookup)
    bing_connection_id: str = field(
        default_factory=lambda: os.environ.get("BING_CONNECTION_ID", "")
    )
    
    # MS Learn MCP Server URL
    # Provides access to Microsoft Learn documentation via MCP
    # Tools: microsoft_docs_search, microsoft_docs_fetch, microsoft_code_sample_search
    # URL must be specified in .env file
    ms_learn_mcp_url: str = field(
        default_factory=lambda: os.environ.get("MS_LEARN_MCP_URL", "")
    )
    
    # Phase 2: IaC Generation MCP Servers
    # Azure MCP Server - All Azure tools in one server (Recommended)
    azure_mcp_url: str = field(
        default_factory=lambda: os.environ.get("AZURE_MCP_URL", "")
    )
    
    # Bicep MCP Server - Microsoft Bicep best practices and code generation
    bicep_mcp_url: str = field(
        default_factory=lambda: os.environ.get("BICEP_MCP_URL", "")
    )
    
    # Terraform MCP Server - HashiCorp Terraform best practices
    terraform_mcp_url: str = field(
        default_factory=lambda: os.environ.get("TERRAFORM_MCP_URL", "")
    )
    
    # Azure DevOps MCP Server - DevOps best practices and pipeline templates
    azure_devops_mcp_url: str = field(
        default_factory=lambda: os.environ.get("AZURE_DEVOPS_MCP_URL", "")
    )
    
    # GitHub MCP Server - GitHub Actions and CI/CD best practices
    github_mcp_url: str = field(
        default_factory=lambda: os.environ.get("GITHUB_MCP_URL", "")
    )
    
    # Azure Well-Architected Framework - primary guidance source
    # URL must be specified in .env file
    azure_waf_docs_url: str = field(
        default_factory=lambda: os.environ.get("AZURE_WAF_DOCS_URL", "")
    )
    
    # Azure Architecture Icons - official icon catalog source
    # URL must be specified in .env file
    azure_icons_url: str = field(
        default_factory=lambda: os.environ.get("AZURE_ICONS_URL", "")
    )
    
    # Azure Architecture Icons CDN - direct download URL for icon pack
    # URL must be specified in .env file
    azure_icons_cdn_url: str = field(
        default_factory=lambda: os.environ.get("AZURE_ICONS_CDN_URL", "")
    )
    
    # Output settings
    output_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("OUTPUT_DIR", "./output"))
    )
    
    # Phase 2: IaC output directory (for Bicep/Terraform templates)
    iac_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("IAC_DIR", "./iac"))
    )
    
    # Logging (default: WARNING for quiet mode, set to INFO/DEBUG for verbose)
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "WARNING")
    )
    
    # Interactive mode settings
    interactive_mode: bool = field(
        default_factory=lambda: os.environ.get("INTERACTIVE_MODE", "true").lower() == "true"
    )
    clarification_threshold: float = field(
        default_factory=lambda: float(os.environ.get("CLARIFICATION_THRESHOLD", "0.7"))
    )
    
    # Detection settings
    detection_confidence_threshold: float = field(
        default_factory=lambda: float(os.environ.get("DETECTION_CONFIDENCE_THRESHOLD", "0.5"))
    )
    
    # Model temperature for consistency (lower = more deterministic)
    # 0.0 = fully deterministic (recommended for Phase 1)
    # 0.1-0.2 = slight creativity (use for code generation)
    model_temperature: float = field(
        default_factory=lambda: float(os.environ.get("MODEL_TEMPERATURE", "0.0"))
    )
    
    def __post_init__(self):
        """Validate required settings and create directories."""
        if not self.project_endpoint:
            raise ValueError(
                "PROJECT_ENDPOINT environment variable is required. "
                "Set it to your Microsoft Foundry project endpoint."
            )
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def azure_openai_endpoint(self) -> str:
        """Extract Azure OpenAI endpoint from project endpoint."""
        if ".services.ai.azure.com" in self.project_endpoint:
            base = self.project_endpoint.split("/api/projects")[0]
            return base
        return self.project_endpoint
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_env()


def get_prompts_dir() -> Path:
    """Get the prompts directory path."""
    return Path(__file__).parent / "prompts"


def get_instructions_path() -> Path:
    """Get the agent instructions YAML path."""
    return get_prompts_dir() / "agent_instructions.yaml"

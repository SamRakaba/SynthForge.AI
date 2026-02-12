"""
SynthForge.AI - Azure Architecture Diagram Analyzer

A multi-agent system using Microsoft Agent Framework to analyze Azure
architecture diagrams, identify resources, and provide security recommendations.

NO STATIC MAPPINGS - All service identification is dynamic from official
Microsoft Azure Architecture Icons.
"""

__version__ = "2.0.0"
__author__ = "SynthForge Team"

from synthforge.config import Settings, get_settings
from synthforge.models import (
    AzureResource,
    ArchitectureAnalysis,
    DetectionResult,
    FilterResult,
    SecurityRecommendation,
)
from synthforge.workflow import (
    ArchitectureWorkflow,
    WorkflowResult,
    WorkflowProgress,
    run_analysis,
)
from synthforge.icon_catalog import (
    AzureIconCatalog,
    AzureServiceInfo,
    get_icon_catalog,
)
from synthforge.agents.azure_icon_matcher import (
    AzureIconMatcher,
    get_icon_matcher,
    IconInfo,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Models
    "AzureResource",
    "ArchitectureAnalysis",
    "DetectionResult",
    "FilterResult",
    "SecurityRecommendation",
    # Workflow
    "ArchitectureWorkflow",
    "WorkflowResult",
    "WorkflowProgress",
    "run_analysis",
    # Icon Catalog (facade)
    "AzureIconCatalog",
    "AzureServiceInfo",
    "get_icon_catalog",
    # Icon Matcher (source of truth)
    "AzureIconMatcher",
    "get_icon_matcher",
    "IconInfo",
]

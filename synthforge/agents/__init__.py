"""
Agents package for SynthForge.AI.

Contains all agent implementations using azure.ai.agents.AgentsClient.
Agents are async context managers - use with `async with` pattern.
"""

from synthforge.agents.vision_agent import VisionAgent
from synthforge.agents.filter_agent import FilterAgent
from synthforge.agents.security_agent import SecurityAgent
from synthforge.agents.interactive_agent import InteractiveAgent
from synthforge.agents.code_quality_agent import CodeQualityAgent

__all__ = [
    "VisionAgent",
    "FilterAgent",
    "SecurityAgent",
    "InteractiveAgent",
    "CodeQualityAgent",
]

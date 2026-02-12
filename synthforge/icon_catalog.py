"""
Azure Icon Catalog loader for SynthForge.AI.

Provides access to the Azure service icon catalog for enhanced icon identification.

NO STATIC MAPPINGS - All data is loaded dynamically from official Microsoft
Azure Architecture Icons via the AzureIconMatcher.

This module is a facade over the AzureIconMatcher for backward compatibility.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Import from the icon matcher - the actual source of truth
from synthforge.agents.azure_icon_matcher import (
    get_icon_matcher,
    AzureIconMatcher,
    IconInfo,
)


# Re-export IconInfo as AzureServiceInfo for compatibility
AzureServiceInfo = IconInfo


class AzureIconCatalog:
    """
    Azure icon catalog for enhanced service identification.
    
    NO STATIC MAPPINGS - All data loaded dynamically from official
    Microsoft Azure Architecture Icons.
    
    This is a facade over AzureIconMatcher for backward compatibility.
    """
    
    def __init__(self):
        """Initialize the catalog (loads icons on first use)."""
        self._matcher: Optional[AzureIconMatcher] = None
        self._loaded = False
    
    def _get_matcher(self) -> AzureIconMatcher:
        """Get or create the icon matcher."""
        if self._matcher is None:
            self._matcher = get_icon_matcher()
        return self._matcher
    
    @property
    def services(self) -> list[IconInfo]:
        """Get all services in the catalog (dynamically loaded)."""
        return self._get_matcher().get_all_services()
    
    def normalize_name(self, name: str) -> tuple[str, Optional[str]]:
        """
        Normalize a service name and return ARM type.
        
        NO STATIC MAPPING - Looks up from dynamically-loaded icon library.
        
        Args:
            name: The service name or abbreviation
            
        Returns:
            Tuple of (normalized_name, arm_type)
        """
        matcher = self._get_matcher()
        service_info = matcher.get_service_by_name(name)
        
        if service_info:
            return (service_info.name, service_info.arm_type or None)
        
        # Not found - add Azure prefix if needed
        name = name.strip()
        if not name.lower().startswith('azure ') and not name.lower().startswith('microsoft '):
            return (f"Azure {name}", None)
        
        return (name, None)
    
    def get_arm_type(self, name: str) -> Optional[str]:
        """Get ARM resource type for a service name (dynamically loaded)."""
        matcher = self._get_matcher()
        service_info = matcher.get_service_by_name(name)
        
        if service_info:
            return service_info.arm_type or None
        
        return None
    
    def get_service_info(self, name: str) -> Optional[IconInfo]:
        """Get full service info by name or alias (dynamically loaded)."""
        return self._get_matcher().get_service_by_name(name)
    
    def search(self, query: str) -> list[IconInfo]:
        """
        Search for services matching a query.
        
        Args:
            query: Search term (partial match on name)
            
        Returns:
            List of matching services
        """
        query_lower = query.lower()
        matches = []
        
        for service in self.services:
            if query_lower in service.name.lower():
                matches.append(service)
                continue
            
            if any(query_lower in alias for alias in service.aliases):
                matches.append(service)
        
        return matches


@lru_cache(maxsize=1)
def get_icon_catalog() -> AzureIconCatalog:
    """Get the singleton icon catalog instance."""
    return AzureIconCatalog()


def get_abbreviation_map() -> dict[str, str]:
    """
    Get abbreviation to official name mapping.
    
    NO STATIC MAP - Builds dynamically from icon library aliases.
    """
    catalog = get_icon_catalog()
    abbrev_map = {}
    
    for service in catalog.services:
        for alias in service.aliases:
            if alias != service.name.lower():
                abbrev_map[alias] = service.name
    
    return abbrev_map


def get_arm_type_map() -> dict[str, str]:
    """
    Get service name to ARM type mapping.
    
    NO STATIC MAP - Builds dynamically from icon library.
    """
    catalog = get_icon_catalog()
    arm_map = {}
    
    for service in catalog.services:
        if service.arm_type:
            arm_map[service.name.lower()] = service.arm_type
    
    return arm_map

"""
Data models for SynthForge.AI.

Pydantic models for Azure resources, detection results, and IaC-ready analysis output.
Aligned with Labfiles output format for IaC development.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ResourceConfidence(str, Enum):
    """Confidence levels for detected resources."""
    HIGH = "high"       # > 0.85
    MEDIUM = "medium"   # 0.7 - 0.85
    LOW = "low"         # 0.5 - 0.7
    UNCERTAIN = "uncertain"  # < 0.5


class FilterCategory(str, Enum):
    """Resource filter categories."""
    ARCHITECTURAL = "architectural"
    NON_ARCHITECTURAL = "non_architectural"
    NETWORK_ISOLATION_PATTERN = "network_isolation_pattern"  # Subnet/PE associated with service
    NEEDS_CLARIFICATION = "needs_clarification"


class ManagedIdentityType(str, Enum):
    """Types of managed identity."""
    NONE = "none"
    SYSTEM_ASSIGNED = "system_assigned"
    USER_ASSIGNED = "user_assigned"
    BOTH = "both"


class RBACScope(str, Enum):
    """RBAC assignment scope levels."""
    RESOURCE = "resource"
    RESOURCE_GROUP = "resource_group"
    SUBSCRIPTION = "subscription"


class NetworkAccessType(str, Enum):
    """Network access type for Azure resources."""
    PUBLIC = "public"
    PRIVATE_ENDPOINT = "private_endpoint"
    SERVICE_ENDPOINT = "service_endpoint"
    VNET_INTEGRATED = "vnet_integrated"
    HYBRID = "hybrid"


# =============================================================================
# POSITION & BOUNDING BOX
# =============================================================================

class Position(BaseModel):
    """Position in the image."""
    x: float = Field(description="X position (can be percentage or pixels)")
    y: float = Field(description="Y position (can be percentage or pixels)")
    width: Optional[float] = Field(default=None, description="Width")
    height: Optional[float] = Field(default=None, description="Height")


class BoundingBox(BaseModel):
    """Absolute bounding box coordinates."""
    x: int = Field(description="Left X coordinate in pixels")
    y: int = Field(description="Top Y coordinate in pixels")
    width: int = Field(description="Width in pixels")
    height: int = Field(description="Height in pixels")


# =============================================================================
# DETECTION MODELS
# =============================================================================

class DetectedIcon(BaseModel):
    """A single detected Azure icon from the diagram."""
    type: str = Field(description="Azure service type (e.g., 'Azure Functions')")
    name: Optional[str] = Field(default=None, description="Instance name if visible")
    position: Position = Field(description="Position in the image")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Pixel bounding box")
    confidence: float = Field(description="Detection confidence 0.0-1.0")
    reasoning: Optional[str] = Field(default=None, description="Why this was identified as this service")
    arm_resource_type: Optional[str] = Field(default=None, description="ARM resource type")
    resource_category: Optional[str] = Field(default=None, description="Azure service category from official documentation")
    connections: list[str] = Field(
        default_factory=list,
        description="Other services this connects to (from visible lines/arrows)",
    )
    needs_clarification: bool = Field(
        default=False, 
        description="Whether user input is needed to identify this resource"
    )
    clarification_options: Optional[list[str]] = Field(
        default=None,
        description="Suggested service options for user clarification"
    )
    
    @property
    def confidence_level(self) -> ResourceConfidence:
        """Get the confidence level category."""
        if self.confidence >= 0.85:
            return ResourceConfidence.HIGH
        elif self.confidence >= 0.7:
            return ResourceConfidence.MEDIUM
        elif self.confidence >= 0.5:
            return ResourceConfidence.LOW
        return ResourceConfidence.UNCERTAIN


class DetectedText(BaseModel):
    """A text block detected via OCR."""
    text: str = Field(description="The detected text content")
    position: Position = Field(description="Position in the image")
    confidence: float = Field(description="OCR confidence 0.0-1.0")
    classification: Optional[str] = Field(
        default=None, 
        description="Classification: azure_service, instance_label, network_element, noise"
    )


class VNetBoundary(BaseModel):
    """Virtual network or subnet boundary."""
    name: str = Field(description="VNet/Subnet name")
    type: str = Field(description="vnet or subnet")
    position: Position = Field(description="Bounding box position")
    address_space: Optional[str] = Field(default=None, description="CIDR if visible")
    contained_resources: list[str] = Field(default_factory=list)


class DataFlow(BaseModel):
    """Connection or data flow between resources (IaC-ready)."""
    source: str = Field(description="Source resource identifier")
    target: str = Field(description="Target resource identifier")
    flow_type: str = Field(default="data", description="Type: data, network, auth, event, api")
    direction: str = Field(default="unidirectional", description="unidirectional or bidirectional")
    protocol: Optional[str] = Field(default=None, description="Protocol: HTTPS, TCP, AMQP, etc.")
    port: Optional[int] = Field(default=None, description="Port number if applicable")
    description: Optional[str] = Field(default=None, description="Flow description")
    is_private: bool = Field(default=True, description="Uses private endpoint/vnet")
    label: Optional[str] = Field(default=None, description="Flow label if visible")
    rbac_implication: Optional[str] = Field(
        default=None, 
        description="RBAC implication: what role the source needs to access the target"
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "source": self.source,
            "target": self.target,
            "flow_type": self.flow_type,
            "direction": self.direction,
            "protocol": self.protocol,
            "port": self.port,
            "description": self.description,
            "is_private": self.is_private,
            "rbac_implication": self.rbac_implication,
        }


class DetectionResult(BaseModel):
    """Complete detection result from Vision Agent."""
    icons: list[DetectedIcon] = Field(default_factory=list, alias="components")
    texts: list[DetectedText] = Field(default_factory=list, alias="text_blocks")
    vnet_boundaries: list[VNetBoundary] = Field(default_factory=list, alias="vnets")
    data_flows: list[DataFlow] = Field(default_factory=list, alias="flows")
    image_dimensions: Optional[dict[str, int]] = Field(default=None)
    
    class Config:
        populate_by_name = True
    
    @property
    def needs_clarification(self) -> list[DetectedIcon]:
        """Get components that need user clarification."""
        return [c for c in self.icons if c.confidence < 0.7]


# =============================================================================
# FILTER MODELS
# =============================================================================

class FilterDecision(BaseModel):
    """Filter decision for a single resource."""
    resource_type: str = Field(description="The resource type being filtered")
    category: FilterCategory = Field(description="Filter category")
    reasoning: str = Field(description="Reasoning for the decision")
    confidence: float = Field(description="Confidence in the decision")
    foundational: bool = Field(default=False, description="Whether this is a foundational service (AI Foundry, OpenAI, Storage, Key Vault, etc.)")


class FilterResult(BaseModel):
    """Result of filtering resources."""
    architectural: list[DetectedIcon] = Field(default_factory=list)
    non_architectural: list[DetectedIcon] = Field(default_factory=list)
    network_isolation: list[DetectedIcon] = Field(default_factory=list, description="Network patterns that become recommendations")
    needs_clarification: list[DetectedIcon] = Field(default_factory=list)
    decisions: list[FilterDecision] = Field(default_factory=list)
    summary: str = Field(default="", description="Summary of filter decisions")


# =============================================================================
# CLARIFICATION MODELS
# =============================================================================

class ClarificationRequest(BaseModel):
    """Request for user clarification on an unclear resource."""
    resource: DetectedIcon = Field(description="The resource needing clarification")
    question: str = Field(description="Question to ask the user")
    options: list[str] = Field(description="Suggested options for the user")
    suggested_default: int = Field(default=0, description="Index of suggested option")
    context: Optional[str] = Field(default=None, description="Additional context")


class ClarificationResponse(BaseModel):
    """User's response to a clarification request."""
    original_resource: DetectedIcon = Field(description="The original detected resource")
    clarified_type: Optional[str] = Field(default=None, description="Resolved service type")
    clarified_arm_type: Optional[str] = Field(default=None, description="Resolved ARM type")
    clarified_name: Optional[str] = Field(default=None, description="Resolved name")
    should_include: bool = Field(default=True, description="Whether to include in analysis")
    user_notes: Optional[str] = Field(default=None, description="User's notes")


# =============================================================================
# SECURITY MODELS (IaC-ready)
# =============================================================================

class RBACAssignment(BaseModel):
    """RBAC role assignment recommendation (IaC-ready)."""
    role_name: str = Field(description="Azure built-in role name")
    role_definition_id: Optional[str] = Field(default=None, description="Azure role definition ID")
    principal_type: str = Field(default="ManagedIdentity", description="ServicePrincipal, User, Group, ManagedIdentity")
    principal_id: Optional[str] = Field(default=None, description="Will be filled by managed identity")
    scope: RBACScope = Field(default=RBACScope.RESOURCE)
    condition: Optional[str] = Field(default=None, description="ABAC condition")
    justification: str = Field(default="", description="Why this role is needed")
    source_service: Optional[str] = Field(default=None, description="Service needing access")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "role_name": self.role_name,
            "role_definition_id": self.role_definition_id,
            "principal_type": self.principal_type,
            "principal_id": self.principal_id,
            "scope": self.scope.value,
            "condition": self.condition,
            "justification": self.justification,
            "source_service": self.source_service,
        }


class PrivateEndpointConfig(BaseModel):
    """Private endpoint configuration recommendation (IaC-ready)."""
    enabled: bool = Field(default=True, description="Whether PE is enabled")
    recommended: bool = Field(default=True, description="Whether PE is recommended")
    private_dns_zone: Optional[str] = Field(default=None, description="Required Private DNS zone")
    group_ids: list[str] = Field(default_factory=list, description="PE group IDs e.g., ['blob', 'file']")
    inbound_access_required: bool = Field(default=False, description="True if resource receives PE traffic")
    guidance: Optional[str] = Field(default=None, description="Best practice guidance")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "enabled": self.enabled,
            "recommended": self.recommended,
            "private_dns_zone": self.private_dns_zone,
            "group_ids": self.group_ids,
            "inbound_access_required": self.inbound_access_required,
            "guidance": self.guidance,
        }


class VNetIntegrationConfig(BaseModel):
    """VNet integration recommendations for PaaS services (IaC-ready)."""
    enabled: bool = Field(default=False, description="Whether VNet integration is enabled")
    recommended: bool = Field(default=False, description="Whether VNet integration is recommended")
    subnet_delegation: Optional[str] = Field(default=None, description="e.g., Microsoft.Web/serverFarms")
    requires_dedicated_subnet: bool = Field(default=False)
    recommended_subnet_size: Optional[str] = Field(default=None, description="e.g., /27 or /28")
    guidance: Optional[str] = Field(default=None, description="Best practice guidance")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "enabled": self.enabled,
            "recommended": self.recommended,
            "subnet_delegation": self.subnet_delegation,
            "requires_dedicated_subnet": self.requires_dedicated_subnet,
            "recommended_subnet_size": self.recommended_subnet_size,
            "guidance": self.guidance,
        }


class ManagedIdentityConfig(BaseModel):
    """Managed identity configuration (IaC-ready)."""
    enabled: bool = Field(default=True, description="Whether MI is enabled")
    identity_type: ManagedIdentityType = Field(default=ManagedIdentityType.SYSTEM_ASSIGNED)
    user_assigned_identity_ids: list[str] = Field(default_factory=list)
    justification: str = Field(default="", description="Reasoning")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "enabled": self.enabled,
            "identity_type": self.identity_type.value,
            "user_assigned_identity_ids": self.user_assigned_identity_ids,
        }


class SecurityConfig(BaseModel):
    """Complete security configuration for a resource (IaC-ready)."""
    managed_identity: ManagedIdentityConfig = Field(default_factory=ManagedIdentityConfig)
    private_endpoint: PrivateEndpointConfig = Field(default_factory=PrivateEndpointConfig)
    vnet_integration: VNetIntegrationConfig = Field(default_factory=VNetIntegrationConfig)
    rbac_assignments: list[RBACAssignment] = Field(default_factory=list)
    network_access: NetworkAccessType = Field(default=NetworkAccessType.PRIVATE_ENDPOINT)
    disable_public_access: bool = Field(default=True)
    minimum_tls_version: str = Field(default="1.2")
    encryption_at_rest: bool = Field(default=True)
    encryption_in_transit: bool = Field(default=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "managed_identity": self.managed_identity.to_dict(),
            "private_endpoint": self.private_endpoint.to_dict(),
            "vnet_integration": self.vnet_integration.to_dict(),
            "rbac_assignments": [r.to_dict() for r in self.rbac_assignments],
            "network_access": self.network_access.value,
            "disable_public_access": self.disable_public_access,
            "minimum_tls_version": self.minimum_tls_version,
            "encryption_at_rest": self.encryption_at_rest,
            "encryption_in_transit": self.encryption_in_transit,
        }


class SecurityRecommendation(BaseModel):
    """Security recommendations for a resource."""
    resource_type: str = Field(description="The resource type")
    resource_name: Optional[str] = Field(default=None)
    rbac_assignments: list[RBACAssignment] = Field(default_factory=list)
    managed_identity: Optional[ManagedIdentityConfig] = Field(default=None)
    private_endpoint: Optional[PrivateEndpointConfig] = Field(default=None)
    vnet_integration: Optional[VNetIntegrationConfig] = Field(default=None)
    additional_recommendations: list[str] = Field(default_factory=list)
    documentation_urls: list[str] = Field(default_factory=list)


# =============================================================================
# AZURE RESOURCE (IaC-READY FINAL OUTPUT)
# =============================================================================

class AzureResource(BaseModel):
    """Complete Azure resource with all enrichments (IaC-ready)."""
    # Identification
    id: str = Field(description="Unique resource ID within the analysis")
    name: str = Field(description="Resource instance name")
    service_type: str = Field(description="Azure service type (e.g., Azure Functions)")
    resource_type: Optional[str] = Field(default=None, description="ARM resource type")
    
    # Location in diagram
    bounding_box: Optional[BoundingBox] = Field(default=None)
    detected_by: str = Field(default="gpt4o_vision")
    confidence: float = Field(default=1.0)
    user_verified: bool = Field(default=False)
    needs_user_validation: bool = Field(default=False)
    original_detection: Optional[str] = Field(default=None)
    
    # Network flows
    inbound_flows: list[DataFlow] = Field(default_factory=list)
    outbound_flows: list[DataFlow] = Field(default_factory=list)
    
    # Security configuration
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Best practice recommendations
    recommendations: list[str] = Field(default_factory=list)
    
    # IaC references
    terraform_resource: Optional[str] = Field(default=None)
    bicep_resource: Optional[str] = Field(default=None)
    
    # Configuration
    sku: Optional[str] = Field(default=None)
    region: Optional[str] = Field(default=None)
    resource_group: Optional[str] = Field(default=None)
    
    # Legacy compatibility
    position: Optional[Position] = Field(default=None)
    connections: list[str] = Field(default_factory=list, description="Connected resources")
    security_recommendations: list["SecurityRecommendation"] = Field(default_factory=list)
    vnet_name: Optional[str] = Field(default=None)
    subnet_name: Optional[str] = Field(default=None)
    
    # Aliases for backward compatibility
    @property
    def type(self) -> str:
        return self.service_type
    
    @property
    def arm_resource_type(self) -> Optional[str]:
        return self.resource_type
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "id": self.id,
            "name": self.name,
            "service_type": self.service_type,
            "resource_type": self.resource_type,
            "bounding_box": {"x": self.bounding_box.x, "y": self.bounding_box.y, 
                            "width": self.bounding_box.width, "height": self.bounding_box.height} if self.bounding_box else None,
            "detected_by": self.detected_by,
            "confidence": self.confidence,
            "user_verified": self.user_verified,
            "needs_user_validation": self.needs_user_validation,
            "original_detection": self.original_detection,
            "inbound_flows": [f.to_dict() for f in self.inbound_flows],
            "outbound_flows": [f.to_dict() for f in self.outbound_flows],
            "security": self.security.to_dict(),
            "recommendations": self.recommendations,
            "terraform_resource": self.terraform_resource,
            "bicep_resource": self.bicep_resource,
            "sku": self.sku,
            "region": self.region,
            "resource_group": self.resource_group,
        }


# =============================================================================
# ARCHITECTURE ANALYSIS (IaC-READY FINAL OUTPUT)
# =============================================================================

class ArchitectureAnalysis(BaseModel):
    """Complete architecture analysis result (IaC-ready)."""
    # Metadata
    image_path: str = Field(default="")
    analyzed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    caption: str = Field(default="")
    
    # Detection statistics
    total_detected: int = Field(default=0)
    total_identified: int = Field(default=0)
    detection_methods: dict = Field(default_factory=dict)
    
    # Detected resources
    resources: list[AzureResource] = Field(default_factory=list)
    
    # Network flows (edges between resources)
    network_flows: list[DataFlow] = Field(default_factory=list)
    
    # Network topology
    vnets: list[dict] = Field(default_factory=list)
    subnets: list[dict] = Field(default_factory=list)
    vnet_boundaries: Optional[list[VNetBoundary]] = Field(default=None)
    data_flows: Optional[list[DataFlow]] = Field(default=None)
    
    # Text elements
    detected_texts: Optional[list[DetectedText]] = Field(default=None)
    
    # Recommendations
    architecture_recommendations: list[str] = Field(default_factory=list)
    security_recommendations: list[str] = Field(default_factory=list)
    
    # Summary
    summary: str = Field(default="")
    
    # Any errors or warnings
    warnings: list[str] = Field(default_factory=list)
    
    def add_resource(self, resource: AzureResource) -> None:
        """Add a resource to the analysis."""
        self.resources.append(resource)
    
    def add_flow(self, flow: DataFlow) -> None:
        """Add a network flow and update resource references."""
        self.network_flows.append(flow)
        
        # Update source resource outbound flows
        for r in self.resources:
            if r.id == flow.source:
                r.outbound_flows.append(flow)
                break
        
        # Update target resource inbound flows
        for r in self.resources:
            if r.id == flow.target:
                r.inbound_flows.append(flow)
                break
    
    def get_resource_by_id(self, resource_id: str) -> Optional[AzureResource]:
        """Get a resource by its ID."""
        for r in self.resources:
            if r.id == resource_id:
                return r
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "metadata": {
                "image_path": self.image_path,
                "analyzed_at": self.analyzed_at,
                "caption": self.caption,
            },
            "total_detected": self.total_detected,
            "total_identified": self.total_identified,
            "detection_methods": self.detection_methods,
            "summary": self.summary,
            "resources": [r.to_dict() for r in self.resources],
            "network_flows": [f.to_dict() for f in self.network_flows],
            "vnets": self.vnets,
            "subnets": self.subnets,
            "recommendations": {
                "architecture": self.architecture_recommendations,
                "security": self.security_recommendations,
            },
            "warnings": self.warnings,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, output_path: str) -> None:
        """Save analysis to JSON file."""
        with open(output_path, "w") as f:
            f.write(self.to_json())
    
    @classmethod
    def from_json(cls, json_str: str) -> "ArchitectureAnalysis":
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)

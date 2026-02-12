# Resource Classification Flow in SynthForge.AI

## Current Flow (Stages 0-3)

### Stage 0: Description Agent
**Purpose:** Provides comprehensive component discovery BEFORE structured detection

**Resource Classification Categories:**
```python
@dataclass
class ArchitectureDescription:
    azure_components: List[str]      # Core Azure managed services (MUST detect)
    infrastructure: List[str]        # Compute/storage per-app (MUST detect)
    network_topology: List[str]      # Network boundaries (reference only)
    external_sources: List[str]      # External systems (reference only)
    supporting_services: List[str]   # Monitoring, DevOps, Identity (reference only)
    users_actors: List[str]          # User types shown (reference only)
    groupings: List[str]             # Zones, regions, labeled sections
```

**Key Classification Logic:**
```python
def get_all_components(self) -> List[str]:
    """Components that MUST be detected"""
    all_components = []
    all_components.extend(self.azure_components)      # Core services
    all_components.extend(self.infrastructure)        # Compute/storage
    # Excluded from critical requirements (reference only):
    # - network_topology: VNets, Subnets, NSGs
    # - external_sources: Non-Azure systems
    # - supporting_services: Monitoring, Identity, DevOps
    return self._deduplicate_components(all_components)
```

**Category Definitions:**
- **azure_components**: Core managed services (API Management, Cosmos DB, Functions, etc.)
- **infrastructure**: Compute/storage deployed per-app (App Service, VMs, Storage Accounts)
- **network_topology**: Network boundaries (VNets, Subnets, NSGs) - reference only
- **external_sources**: Non-Azure systems (SAP, CSV files, APIs) - reference only
- **supporting_services**: Shared services (Monitor, Entra ID, DevOps) - reference only

**How It Feeds Vision Agent:**
1. `to_context_hints()` creates a numbered checklist of mandatory components
2. Reference-only categories listed separately (network_topology, external_sources, supporting_services)
3. Vision agent receives: "CRITICAL REQUIREMENT: You MUST detect ALL {N} components"
4. Only azure_components + infrastructure are in the critical count

### Stage 1: Vision Agent (with Description Context)
**Purpose:** Structured icon detection using GPT-4o Vision

**Receives Description Context:**
```python
if description_context:
    prompt = f"""{description_context}

---

{prompt}

**IMPORTANT: The description above identified components to look for.**
**Make sure you detect ALL of them with their positions.**
"""
```

**Detection Output:**
- DetectedIcon objects with type, position, confidence
- All components from description should be detected
- Supporting services detected only if explicitly visible as icons

### Stage 3: Filter Agent
**Purpose:** Classify detected resources as architectural vs non-architectural

**Uses First-Principles Reasoning:**
- Does it have an ARM resource type? (Azure MCP - priority 1)
- Is it deployed per-application?
- Is it infrastructure or observability?
- Is it Azure-native or third-party?

**Tool Priority:**
1. **Azure MCP**: ARM resource type schemas (AUTHORITATIVE - wins in conflicts)
2. **Bing Grounding**: Azure WAF documentation
3. **MS Learn MCP**: Official documentation

**Description Hints Integration:**
- Receives classification hints from description agent via `to_filter_hints()`
- Hints are ADVISORY only
- **When MCP research conflicts with hints → MCP research wins**

---

## 🔧 Filter Hints Implementation (With MCP Priority)

### How to_filter_hints() Works

```python
def to_filter_hints(self) -> dict:
    """Format hints for FilterAgent - MCP research takes priority."""
    return {
        "architectural_components": [
            # azure_components + infrastructure
        ],
        "reference_only": {
            "network_topology": [...],      # VNets, Subnets, NSGs
            "external_sources": [...],      # Non-Azure systems
            "supporting_services": [...],   # Monitor, DevOps, Identity
            "users_actors": [...]           # User types
        },
        "classification_guidance": {
            # Human-readable explanation of each category
        },
        "mcp_research_priority": {
            "note": "If Azure MCP shows different pattern → TRUST MCP",
            "example": "Hint says 'supporting' but MCP shows per-app ARM type → architectural"
        }
    }
```

### Filter Agent Decision Logic

```
Step 1: Check description hints
  └─ Get suggested classification

Step 2: Use Azure MCP to research ARM resource type
  └─ Query: "Get ARM schema for [resource]"
  └─ Analyze: Is it per-app or shared?

Step 3: Apply conflict resolution
  ├─ If MCP result conflicts with hint → USE MCP RESULT
  ├─ If MCP confirms hint → CONFIRMED classification
  └─ If MCP unavailable → USE HINT with lower confidence

Step 4: Use Bing/MS Learn for additional context if needed
  └─ Deployment patterns, best practices
```

---

## 📊 Classification Decision Tree (Updated)

```
Detected Resource
    │
    ├─ Is it in users_actors hint?
    │   └─ YES → FILTER OUT (not an Azure resource)
    │
    ├─ Is it in external_sources hint?
    │   └─ YES → FILTER OUT (non-Azure system)
    │
    ├─ Use Azure MCP to get ARM resource type
    │   │
    │   ├─ NO ARM TYPE → FILTER OUT
    │   │   Exception: Network boundaries (VNet, NSG) may be logical groupings
    │   │
    │   └─ HAS ARM TYPE → Check deployment pattern via MCP
    │       │
    │       ├─ Per-app deployment → INCLUDE (architectural)
    │       │   Examples: App Service, Functions, Cosmos DB
    │       │   Override hint if hint says "supporting"
    │       │
    │       └─ Shared/multi-app deployment → Check hint
    │           │
    │           ├─ Hint says "architectural" → INCLUDE
    │           │   (Diagram may show per-app instance of typically-shared service)
    │           │
    │           └─ Hint says "supporting" → FILTER OUT
    │               Examples: Azure Monitor, Container Registry, DevOps
```

---

#### 1. Update ArchitectureDescription class

Add a method to format hints for the Filter Agent:

```python
def to_filter_hints(self) -> dict:
    """Format as hints for FilterAgent classification."""
    return {
        "architectural_components": list(set(
            self.azure_components + self.infrastructure + self.external_sources
        )),
        "supporting_services": list(set(self.supporting_services)),
        "users_actors": list(set(self.users_actors)),
        "classification_notes": {
            "architectural": "These are core application components that should be in IaC",
            "supporting": "These are shared services used for monitoring/identity - typically filter out",
            "users": "These are user types/actors - NOT Azure resources, filter out"
        }
    }
```

#### 2. Update workflow.py to pass hints

In `_run_filter_analysis()`:
```python
async def _run_filter_analysis(
    self, 
    detection_result: DetectionResult,
    description: Optional[ArchitectureDescription] = None,  # ADD THIS
) -> FilterResult:
    """Run filter analysis with optional description hints."""
    try:
        async with FilterAgent() as agent:
            filter_hints = None
            if description:
                filter_hints = description.to_filter_hints()
            
            result = await agent.filter_resources(
                detection_result,
                description_hints=filter_hints,  # PASS HINTS
            )
            return result
```

#### 3. Update FilterAgent.filter_resources()

```python
async def filter_resources(
    self, 
    detection_result: DetectionResult,
    description_hints: Optional[dict] = None,  # ADD THIS
) -> FilterResult:
    """
    Filter detected resources using first-principles reasoning.
    
    Args:
        detection_result: Result from vision agent
        description_hints: Optional classification hints from description agent
        
    Returns:
        FilterResult with categorized resources
    """
    if not self._client or not self._agent_id:
        raise RuntimeError("Agent not initialized. Use async context manager.")
    
    # Build resource data for analysis
    resources_json = json.dumps([...])
    
    # Add description hints to user prompt
    hints_context = ""
    if description_hints:
        hints_context = f"""

## Description Agent Classification Hints

The Description Agent pre-analyzed this architecture and classified components:

**Architectural Components (Core Application Services):**
{json.dumps(description_hints['architectural_components'], indent=2)}

**Supporting Services (Monitoring/Identity/DevOps):**
{json.dumps(description_hints['supporting_services'], indent=2)}

**Users/Actors (Not Azure Resources):**
{json.dumps(description_hints['users_actors'], indent=2)}

**Classification Notes:**
- Architectural components should typically be INCLUDED in IaC
- Supporting services are often shared across apps - consider filtering out
- Users/actors are visual representations only - FILTER OUT

**IMPORTANT:** Use these hints to inform your decision, but still apply first-principles 
reasoning. If you detect a resource type mismatch (e.g., something listed as 
"supporting" but has a per-app ARM resource type), use your judgment.
"""
    
    user_prompt = get_user_prompt_template("filter_agent").format(
        resources_json=resources_json,
    )
    
    user_prompt = hints_context + user_prompt
    
    # Continue with thread creation and processing...
```

#### 4. Update Description Agent Instructions

In the DESCRIPTION_PROMPT, enhance the supporting_services guidance:

```python
  "supporting_services": [
    "Services used for monitoring, identity, DevOps that are typically SHARED across applications",
    "These should generally be FILTERED OUT of IaC generation (not deployed per-app)",
    "Examples:",
    "  - Azure Monitor, Log Analytics, Application Insights (shared monitoring)",
    "  - Managed Identity, Azure Entra ID (identity services)",
    "  - Azure DevOps, Container Registry (DevOps infrastructure)",
    "  - Azure Backup, Site Recovery (business continuity)",
    "IMPORTANT: If a service is deployed PER APPLICATION (not shared), put it in azure_components instead"
  ],
```

---

## 📊 Classification Decision Tree

```
Detected Resource
    │
    ├─ Is it a USER/ACTOR label?
    │   └─ YES → FILTER OUT (not an Azure resource)
    │
    ├─ Does it have an ARM resource type?
    │   │
    │   ├─ YES → Is it deployed per-application?
    │   │   │
    │   │   ├─ YES → INCLUDE (architectural component)
    │   │   │       Examples: App Service, Functions, Cosmos DB, Key Vault
    │   │   │
    │   │   └─ NO → Is it shared across multiple apps?
    │   │           │
    │   │           ├─ YES → FILTER OUT (supporting service)
    │   │           │       Examples: Azure Monitor, DevOps, Container Registry
    │   │           │
    │   │           └─ MAYBE → Check description hints, use MCP/Bing for guidance
    │   │
    │   └─ NO → Is it an external system or network boundary?
    │           │
    │           ├─ External System → FILTER OUT
    │           │   Examples: SAP, CSV Extracts, Third-party APIs
    │           │
    │           └─ Network Boundary → INCLUDE as logical grouping
    │               Examples: VNet, Subnet, Resource Group
```

---

## 🎯 Benefits of Filter Hints (with MCP Priority)

1. **Faster Initial Classification:** Hints provide quick first-pass categorization
2. **Reduced Ambiguity:** Description context clarifies architect's intent
3. **MCP Verification:** Azure MCP provides authoritative ARM type information
4. **Conflict Resolution:** Clear priority (MCP > hints) eliminates guesswork
5. **Consistent Results:** Same service classified consistently when MCP available
6. **Graceful Degradation:** Falls back to hints when MCP unavailable

---

## 🔍 Example Scenarios

### Scenario 1: Hint and MCP Agree (Azure Monitor)

**Description Hint:** `supporting_services: ["Azure Monitor"]`

**Filter Agent Process:**
1. Check hint: "Azure Monitor" in supporting_services → suggested FILTER OUT
2. Query Azure MCP: `Microsoft.Insights/components`
3. MCP analysis: "Typically deployed as shared workspace resource"
4. **Decision: FILTER OUT** ✓ (hint and MCP agree)

---

### Scenario 2: Hint and MCP Conflict (App-specific Key Vault)

**Description Hint:** `supporting_services: ["Azure Key Vault"]`
*Note: Description agent may have misclassified thinking it's always shared*

**Filter Agent Process:**
1. Check hint: "Azure Key Vault" in supporting_services → suggested FILTER OUT
2. Query Azure MCP: `Microsoft.KeyVault/vaults`
3. MCP analysis: "Supports per-application deployment with isolated access policies"
4. Additional context from diagram: Shows dedicated Key Vault per app
5. **Decision: INCLUDE** ✓ (MCP research overrides hint)

**Result:** Correct classification despite initial misclassification

---

### Scenario 3: External Source (No ARM Type)

**Description Hint:** `external_sources: ["SAP System", "CSV Files"]`

**Filter Agent Process:**
1. Check hint: "SAP System" in external_sources → suggested FILTER OUT
2. Query Azure MCP: No ARM resource type found
3. **Decision: FILTER OUT** ✓ (hint confirmed by lack of ARM type)

---

### Scenario 4: Network Topology (Reference Only)

**Description Hint:** `network_topology: ["VNet", "App Service Subnet", "Private Endpoint Subnet"]`

**Filter Agent Process:**
1. Check hint: "VNet" in network_topology → suggested reference only
2. Query Azure MCP: `Microsoft.Network/virtualNetworks`
3. MCP analysis: "Infrastructure container - typically represents logical grouping"
4. Additional context: No standalone firewall/gateway deployment shown
5. **Decision: Include as logical grouping** ✓ (network boundary, not standalone resource)

*Note: If diagram showed Azure Firewall or Load Balancer in the VNet, those would be classified as architectural components*

---

## 🚀 Implementation Status

### ✅ Completed
1. **Split infrastructure category:**
   - `infrastructure`: Compute/storage per-app (MUST detect)
   - `network_topology`: Network boundaries (reference only)
2. **Made external_sources reference only** (not in critical count)
3. **Added `to_filter_hints()` method** with MCP priority guidance
4. **Updated `get_all_components()`** to exclude network_topology and external_sources
5. **Updated `to_context_hints()`** with separate reference sections
6. **Updated DESCRIPTION_PROMPT** with new category definitions

### 🔨 Ready to Implement
1. Update workflow to pass description to filter agent
2. Update FilterAgent to accept and use description hints with MCP priority
3. Add filter agent prompt instructions about hint vs MCP conflict resolution

### 📋 Testing Needed
1. Test with diagrams containing network topology (VNets, subnets)
2. Test with external sources (SAP, CSV files)
3. Test MCP override scenarios (Key Vault, App Insights)
4. Verify reference-only items don't inflate detection requirements

---

## 📝 Testing Scenarios

### Test Case 1: Network Topology (Reference Only)
- **Description:** Lists "VNet", "Subnets" in network_topology
- **Vision:** Detects VNet boundary with subnets
- **Filter:** Should classify as logical grouping (not standalone resource)
- **Expected:** Include in architecture but mark as container/boundary

### Test Case 2: External Source (Reference Only)
- **Description:** Lists "SAP System" in external_sources
- **Vision:** Detects "SAP" text label
- **Filter:** Should classify as NON_ARCHITECTURAL (no ARM type)
- **Expected:** Filter out - not Azure resource

### Test Case 3: MCP Override (Key Vault per-app)
- **Description:** Lists "Azure Key Vault" in supporting_services (misclassified)
- **Vision:** Detects Key Vault icon
- **Filter:** Azure MCP shows per-app ARM type → Override hint
- **Expected:** Classify as ARCHITECTURAL (MCP wins)

### Test Case 4: Shared Monitoring (Hint and MCP Agree)
- **Description:** Lists "Azure Monitor" in supporting_services
- **Vision:** Detects Azure Monitor icon
- **Filter:** Azure MCP confirms shared deployment pattern
- **Expected:** Classify as NON_ARCHITECTURAL (hint + MCP agree)

### Test Case 5: Infrastructure Split
- **Description:** 
  - infrastructure: ["App Service", "Function App"]
  - network_topology: ["VNet", "Integration Subnet"]
- **Vision:** Detects all 4 items
- **Filter:** App Service/Functions = architectural, VNet/Subnet = reference
- **Expected:** Only App Service and Function App in critical IaC output

### Test Case 6: Standalone Network Appliance
- **Description:**
  - infrastructure: ["Azure Firewall"]
  - network_topology: ["VNet", "Firewall Subnet"]
- **Vision:** Detects all items
- **Filter:** Firewall = architectural (deployed resource), VNet = boundary
- **Expected:** Azure Firewall included in IaC, VNet as logical container


# Knowledge Source Integration - Implementation Clarification

## ❓ **Question**: Do We Need to Provide URLs or Will Agents Find Them?

### ✅ **ANSWER**: Agents FIND URLs Dynamically - We Provide QUERY PATTERNS

---

## 🎯 **Precise Implementation Model**

### **What We Provide in Instructions**

1. **Bing Grounding Query Patterns** ✅
   - Format: `"[keywords] site:[domain]"`
   - Example: `"Azure OpenAI security baseline site:learn.microsoft.com/security"`
   - **Agent Action**: Executes Bing search, returns TOP results with URLs
   - **We DON'T**: Hardcode specific URLs like `https://learn.microsoft.com/azure/ai-services/openai/...`
   - **Agent FINDS**: Actual current URLs based on search results

2. **MS Learn MCP Server Queries** ✅
   - Format: Natural language query describing what to find
   - Example: "Azure Cognitive Services account resource schema"
   - **Agent Action**: Queries MCP tool, returns structured documentation
   - **We DON'T**: Provide URLs - MCP server handles lookups internally
   - **Agent RECEIVES**: Documentation content directly from MCP

3. **Tool Names and Parameters** ✅
   - Format: Specific tool name and what to query for
   - Example: `mcp_bicep_experim_get_bicep_best_practices` (no parameters needed)
   - **Agent Action**: Calls tool, receives best practices
   - **We DON'T**: Provide documentation - tool returns it
   - **Agent RECEIVES**: Current best practices from tool

---

## 🔍 **How It Works in Practice**

### **Example: Agent Researching Azure OpenAI**

#### **Instructions Say** (Query Pattern):
```yaml
## Bing Grounding - Query ALL Sources:

### AVM:
- Query: "avm-res-cognitiveservices-account site:github.com/Azure"
- Study: Parameter patterns, dynamic blocks

### HashiCorp:
- Query: "azurerm_cognitive_account site:registry.terraform.io"
- Verify: Latest properties, arguments

### Security:
- Query: "Azure OpenAI security baseline site:learn.microsoft.com/security"
- Implement: Secure defaults from baseline
```

#### **Agent Executes**:
1. **Bing Grounding Tool Call #1**:
   - Query: `"avm-res-cognitiveservices-account site:github.com/Azure"`
   - Returns: Top 5-10 GitHub URLs (e.g., `https://github.com/Azure/terraform-azurerm-avm-res-cognitiveservices-account`)
   - Agent reads: Pattern documentation from actual URLs

2. **Bing Grounding Tool Call #2**:
   - Query: `"azurerm_cognitive_account site:registry.terraform.io"`
   - Returns: Registry page URLs (e.g., `https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/cognitive_account`)
   - Agent reads: Current schema from actual URLs

3. **Bing Grounding Tool Call #3**:
   - Query: `"Azure OpenAI security baseline site:learn.microsoft.com/security"`
   - Returns: Security baseline URLs (e.g., `https://learn.microsoft.com/security/benchmark/azure/baselines/...`)
   - Agent reads: Security requirements from actual URLs

4. **MS Learn MCP Tool Call**:
   - Query: "Azure Cognitive Services ARM schema"
   - Returns: Structured ARM documentation
   - Agent uses: API versions, properties, configurations

---

## ⚠️ **Current Issue in Instructions**

### **Problem**: Some JSON Examples Have Hardcoded URLs

**Found in instructions** (these are OUTPUT EXAMPLES showing what agent should produce):
```json
{
  "documentation": "https://registry.terraform.io/modules/Azure/avm-res-cognitiveservices-account/azurerm/latest",
  "best_practice_url": "https://learn.microsoft.com/azure/security/fundamentals/network-best-practices#disable-rdpssh-access"
}
```

### **Clarification Needed**:
- ❓ Are these URLs what the agent should FIND and include in output?
- ❓ Or are they just placeholders in examples?

---

## ✅ **Correct Implementation Pattern**

### **In Instructions - Always Use Query Patterns**:

```yaml
# ✅ CORRECT - Query pattern for agent to execute
Research Security Baseline:
- Query: "Azure {service} security baseline site:learn.microsoft.com/security"
- Find: Specific baseline documentation
- Extract: NS-2 (network security), IM-1 (identity management) controls
- Document: Include URL in output's best_practice_url field
```

### **In Agent Output - URLs Are Research Results**:

```json
{
  "best_practices": [
    "Enable private endpoint for network isolation"
  ],
  "best_practices_sources": {
    "security_baseline": [
      "https://learn.microsoft.com/en-us/security/benchmark/azure/baselines/cognitive-services-security-baseline"
    ]
  }
}
```

**These URLs** were found by agent executing the query, NOT hardcoded in instructions.

---

## 📋 **Validation: What Instructions Should Contain**

### ✅ **SHOULD Include**:

1. **Query Patterns**:
   - `"[keywords] site:[domain]"`
   - Generic patterns with placeholders: `"{service}"`, `"{resource}"`

2. **Tool Names**:
   - `Bing Grounding`
   - `MS Learn MCP Server`
   - `mcp_bicep_experim_get_bicep_best_practices`

3. **What to Find**:
   - "Find: AVM parameter patterns"
   - "Verify: Current API versions"
   - "Extract: Security controls"

4. **Generic URL Patterns** (for OUTPUT format examples):
   - `"https://learn.microsoft.com/azure/[service]/..."`
   - `"https://github.com/Azure/[repo]/..."`
   - These show structure, not specific URLs

### ❌ **Should NOT Include**:

1. **Specific URLs in Research Instructions**:
   - ❌ "Research: https://github.com/Azure/terraform-azurerm-avm-res-apimanagement-service"
   - ✅ "Query: 'apimanagement AVM site:github.com/Azure'"

2. **Hardcoded Documentation Links**:
   - ❌ "See: https://registry.terraform.io/providers/hashicorp/azurerm/3.0.0/docs"
   - ✅ "Query: 'azurerm_{resource} site:registry.terraform.io'"

3. **Static Best Practice URLs**:
   - ❌ "Apply: https://learn.microsoft.com/azure/well-architected/..."
   - ✅ "Query: 'Azure {service} Well-Architected site:learn.microsoft.com'"

---

## 🔧 **Required Fix**

### **In OUTPUT FORMAT Examples**:

**Currently** (in JSON examples showing expected output structure):
```json
"documentation": "https://registry.terraform.io/modules/Azure/avm-res-cognitiveservices-account/azurerm/latest"
```

**Should Be** (to clarify these are agent-found, not hardcoded):
```json
"documentation": "[URL found via Bing: avm-res-cognitiveservices-account site:registry.terraform.io]"
```

OR add explicit note:
```yaml
# NOTE: URLs in output examples below are FOUND by agent via research queries above
# They are NOT hardcoded - agent executes queries and includes actual URLs in output
```

---

## 📊 **Summary**

| Component | Source | How Agent Gets It |
|-----------|--------|-------------------|
| **AVM Patterns** | GitHub | Bing query → URLs → Agent reads |
| **Provider Schema** | HashiCorp Registry | Bing query → URLs → Agent reads |
| **ARM API** | Microsoft Learn | Bing query + MCP → Documentation |
| **Security Baseline** | Microsoft Docs | Bing query → URLs → Agent reads |
| **Best Practices** | WAF | Bing query → URLs → Agent reads |
| **Bicep Guidance** | MCP Tool | Tool call → Returns practices |

**WE PROVIDE**: Query patterns and tool names  
**AGENT FINDS**: Actual URLs and documentation  
**AGENT OUTPUTS**: URLs in results (as proof of research)

---

## ✅ **Validation Checklist**

For instructions to be "precise and properly referenced":

- [ ] All research instructions use query patterns (not specific URLs)
- [ ] Tool names are explicit (Bing Grounding, MS Learn MCP)
- [ ] Query formats are clear (`"keywords site:domain"`)
- [ ] Output examples clarify URLs are agent-found
- [ ] No hardcoded documentation links in research steps
- [ ] Generic URL patterns show structure only
- [ ] Notes explain agent discovers current URLs dynamically

---

## 🎯 **Bottom Line**

**PRECISE ANSWER**: 
- ✅ We provide **QUERY PATTERNS**
- ✅ Agent **FINDS URLs** via Bing Grounding and MCP tools
- ✅ Agent **INCLUDES URLs** in output as evidence
- ❌ We do NOT hardcode specific URLs in instructions
- ✅ Output examples should clarify URLs are research results

**Current Status**: Instructions use query patterns correctly ✅  
**Fix Needed**: Clarify output examples show agent-found URLs, not hardcoded ones

# Instruction Consistency Review & Updates

**Date:** January 5, 2026  
**Scope:** Phase 1 and Phase 2 Agent Instructions  
**Purpose:** Ensure consistent WAF-based research patterns across all agents

---

## Summary of Changes

### ✅ Consistency Improvements

**1. Unified Research Approach Across Both Phases**
- Phase 1 Security Agent now uses same multi-source research pattern as Phase 2
- Phase 2 Service Analysis, Module Mapping, and Module Development agents all follow consistent patterns

**2. Well-Architected Framework as Primary Source**
- All agents now prioritize WAF guidance for recommendations
- Security Pillar, Reliability Pillar, Cost Optimization integrated
- Zero Trust principles derived from WAF documentation

**3. Multi-Source Evaluation Pattern**
All agents now research from these sources in priority order:
1. **Well-Architected Framework** - Primary authority for design principles
2. **Service-Specific Documentation** - Security baselines, best practices
3. **Azure Verified Modules** - Pattern learning (NOT module sourcing)
4. **Azure Security Benchmark** - Compliance requirements

**4. Dynamic vs Static Recommendations**
- ✅ **Before**: Static examples and hardcoded best practices
- ✅ **After**: Research-driven, service-specific recommendations with source URLs

---

## Instruction Pattern Changes

### Phase 1: Security Agent (`agent_instructions.yaml`)

#### BEFORE (Static Approach):
```yaml
**Common Services - Verify with tools:**

**Storage Accounts:**
- Disable shared key authentication (`allowSharedKeyAccess: false`)
- Use managed identity + Storage Blob Data Reader/Contributor roles
- Lookup: "Azure Storage disable shared key access site:learn.microsoft.com"
```

#### AFTER (Research-Driven Approach):
```yaml
**CRITICAL: DO NOT use static examples - RESEARCH for each service!**

You MUST:
1. Query WAF for the specific service
2. Query service security baseline
3. Query service-specific AAD auth documentation
4. Synthesize findings into recommendations

**Example Research Patterns:**
**Storage Accounts:**
- Research: "Storage Account security baseline AAD authentication site:learn.microsoft.com"
- Research: "Storage Account disable shared key access Well-Architected site:learn.microsoft.com"
- Synthesize: Configuration property, RBAC roles, security rationale
```

### Phase 2: Service Analysis Agent (`iac_agent_instructions.yaml`)

#### BEFORE:
```yaml
## Tool Usage Strategy
Use for service configuration and best practice lookups
```

#### AFTER:
```yaml
### Best Practice Research (CRITICAL - Multi-Source Evaluation)
For EACH service, research from ALL authoritative sources:

1. Well-Architected Framework (WAF) - PRIMARY SOURCE
2. Service-Specific Documentation
3. Azure Verified Modules (AVM) Patterns - LEARN PATTERNS ONLY
4. Security Benchmarks & Compliance

**CRITICAL Decision Criteria**:
- ✅ Secure by Default
- ✅ Network Isolation
- ✅ Zero Trust
- ✅ Service-Specific
- ✅ Production-Ready
- ✅ Cost-Aware
```

### Phase 2: Module Mapping Agent (`iac_agent_instructions.yaml`)

#### BEFORE (Static Best Practices):
```json
"best_practices": [
  "Use AVM modules to get built-in private endpoint support",
  "Leverage AVM's built-in role_assignments parameter",
  "Enable diagnostic settings via diagnostic_settings parameter"
]
```

#### AFTER (Research-Based):
```json
"best_practices": [
  "[Dynamically generated from WAF, service docs, AVM patterns, security benchmarks]",
  "[Example: From WAF - Enable private endpoint for network isolation]",
  "[Example: From service docs - Use managed identity for authentication]"
],
"best_practices_sources": {
  "waf_recommendations": ["URL from Well-Architected Framework"],
  "service_security": ["URL from service security documentation"],
  "avm_patterns": ["URL from AVM pattern documentation"],
  "security_benchmark": ["URL from Azure Security Benchmark"]
}
```

---

## Resolved Conflicts & Duplications

### 1. AVM Module Usage Confusion
**Conflict:** Phase 2 instructions mentioned "Use AVM modules" but also "generate native resources"

**Resolution:**
- Clarified AVM is for **PATTERN LEARNING ONLY**
- All agents now explicitly state: "DO NOT source from AVM modules"
- Consistent message: "Use AVM to learn parameters, generate native azurerm_*/Microsoft.* resources"

### 2. Best Practices Source
**Conflict:** Phase 1 used Bing grounding, Phase 2 mentioned AVM best practices

**Resolution:**
- Both phases now use same priority: WAF → Service Docs → AVM Patterns → Security Benchmark
- AVM referenced only for parameter patterns, not best practices

### 3. Static vs Dynamic Recommendations
**Conflict:** Phase 1 had static service examples, Phase 2 had dynamic research

**Resolution:**
- All agents now research dynamically
- Examples marked as "research patterns" not "static recommendations"
- Agents must synthesize from multiple sources, not copy examples

### 4. Tool Usage Guidance
**Duplication:** Both phases had separate tool guidance with slight differences

**Resolution:**
- Consolidated tool usage patterns
- Consistent Bing query formats: `"[ARM_TYPE] [capability] site:learn.microsoft.com"`
- Consistent MCP usage: Official docs, schemas, structured content

---

## Validation Checklist

### ✅ All Agents Now Follow These Patterns:

**1. Research Workflow:**
```
For each service:
├─ Query WAF (Primary)
├─ Query Service Security Baseline
├─ Query Service-Specific Documentation
├─ Review AVM Patterns (learning only)
├─ Check Security Benchmark
└─ Synthesize → Recommendations with URLs
```

**2. Decision Criteria:**
- ✅ Secure by Default (disable local auth, private endpoints)
- ✅ Network Isolation (private connectivity)
- ✅ Zero Trust (managed identity, RBAC, least privilege)
- ✅ Service-Specific (actual capabilities, not generic)
- ✅ WAF-Aligned (reliability, security, operations, cost)
- ✅ Compliance (security benchmark requirements)

**3. Output Requirements:**
- Include research source URLs
- Service-specific recommendations (no generic advice)
- Multiple sources synthesized
- Clear security rationale

---

## Agent-Specific Updates

### Phase 1: Security Agent
- ✅ Added WAF Security Pillar as primary source
- ✅ Added multi-source research workflow
- ✅ Converted static service examples to research patterns
- ✅ Added Zero Trust principles from WAF
- ✅ Added reliability integration (security + availability)

### Phase 2: Service Analysis Agent
- ✅ Added WAF-based research section
- ✅ Multi-source evaluation with decision criteria
- ✅ Security benchmarks integration
- ✅ Dynamic best practice generation

### Phase 2: Module Mapping Agent
- ✅ Replaced static best_practices with research instructions
- ✅ Added best_practices_sources object
- ✅ Service-specific research requirements
- ✅ WAF + Security Baseline + AVM patterns synthesis

### Phase 2: Module Development Agent
- ✅ Already had strong AVM pattern learning instructions
- ✅ Reinforced "native resources, not AVM sources" message
- ✅ Consistent with other agents' research patterns

---

## Benefits of Consistency

**1. Predictable Behavior**
- All agents follow same research workflow
- Users understand the pattern: WAF → Docs → AVM → Benchmark

**2. Quality Recommendations**
- Service-specific, not generic
- Backed by authoritative sources
- Multiple perspectives synthesized

**3. Maintainability**
- One pattern to update across all agents
- Changes propagate consistently
- Less duplication in instructions

**4. Transparency**
- Source URLs documented
- Research process visible
- Recommendations traceable to official docs

**5. Security-First**
- Zero Trust principles from WAF
- Secure-by-default configurations
- Network isolation prioritized

---

## Testing Recommendations

**1. Validation Tests:**
- Run Phase 1 with various services → Check WAF queries in logs
- Run Phase 2 Service Analysis → Verify multi-source research
- Run Phase 2 Module Mapping → Confirm best_practices are researched, not static

**2. Quality Checks:**
- Recommendations include source URLs?
- Recommendations are service-specific?
- No generic "enable monitoring" without context?
- Zero Trust principles applied?

**3. Consistency Checks:**
- Phase 1 Security recommendations → Phase 2 Service Analysis uses them
- Both phases reference same WAF documentation
- Same query patterns for same services

---

## Future Maintenance

**When updating instructions:**
1. Apply changes to BOTH Phase 1 and Phase 2 agents
2. Ensure WAF remains primary source
3. Keep research workflow consistent
4. Test across multiple services
5. Validate source URLs are generated

**Pattern to maintain:**
```
For each recommendation:
1. Query WAF
2. Query service-specific docs
3. Review AVM patterns (learning only)
4. Synthesize findings
5. Output with source URLs
```

---

## Conclusion

All agent instructions are now consistent and aligned with Azure Well-Architected Framework principles. Both Phase 1 and Phase 2 follow the same multi-source research pattern, eliminating conflicts and ensuring high-quality, service-specific, security-first recommendations backed by official documentation.

**Next Steps:**
1. Test with diverse service mix (compute, data, AI, networking)
2. Validate source URL generation
3. Verify recommendations are actionable and specific
4. Monitor for any instruction conflicts in practice

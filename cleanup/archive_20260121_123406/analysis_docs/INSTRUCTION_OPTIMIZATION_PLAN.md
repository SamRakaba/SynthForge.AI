# Instruction Optimization Plan - Phase 1 & 2 Agents

## Optimization Strategy
- **Remove**: Verbose JSON examples (agents know JSON format)
- **Consolidate**: Repeated research patterns
- **Simplify**: Hardcoded ARM type lists → dynamic research
- **Streamline**: Long examples → concise patterns
- **Target**: 20-30% overall reduction (6029 → 4500 lines)

## Agent-by-Agent Analysis

### 1. service_analysis_agent (648 lines)
**Current Issues:**
- Lines 665-700: Verbose JSON example with comments explaining what NOT to do (35 lines)
- Lines 420-520: Detailed common_patterns example (100 lines) - can be condensed
- Repeated research instructions

**Optimization Actions:**
-Remove verbose "❌ NEVER" / "✅ ALWAYS" JSON examples - agent knows JSON format
- Consolidate pattern detection instructions (currently scattered)
- Remove example outputs - agent can infer from schema
- **Target**: 648 → 450 lines (30% reduction, -198 lines)

### 2. module_mapping_agent (711 lines)
**Current Issues:**
- Lines 950-1100: Repeated AVM search patterns for Terraform/Bicep (150 lines)
- Lines 1100-1300: Verbose folder structure examples (200 lines)
- Common modules algorithm repeated with examples

**Optimization Actions:**
- Consolidate AVM search patterns into single template
- Remove redundant folder structure examples (shown 3+ times)
- Simplify common modules generation logic
- **Target**: 711 → 500 lines (30% reduction, -211 lines)

### 3. module_development_agent (3079 lines - LARGEST!)
**Current Issues:**
- Lines 1650-1850: Repeated AVM vs native resources explanation (200 lines)
- Lines 1900-2500: Extensive Terraform/Bicep examples (600 lines) - too verbose
- Lines 2600-3200: Repeated naming module instructions (600 lines)
- Lines 3200-3600: Duplicated best practices across TF/Bicep (400 lines)

**Optimization Actions:**
- Remove redundant "⚠️ CRITICAL" warnings (appears 15+ times)
- Consolidate terraform_instructions and bicep_instructions shared content
- Remove verbose code examples - rely on AVM research
- Condense naming module section (already in Stage 4, not Stage 5)
- **Target**: 3079 → 2000 lines (35% reduction, -1079 lines)

### 4. deployment_wrapper_agent (1591 lines)
**Already Optimized**: 1524 → 607 lines (60% reduction) in previous work
**Current State**: Instructions increased to 1591 after file edits
**Action**: Quick review for any remaining bloat
**Target**: 1591 → 1550 lines (minimal reduction, -41 lines)

## Total Impact Projection
- **Before**: 6029 lines
- **After**: 4500 lines
- **Reduction**: 1529 lines (25%)

## Implementation Order
1. service_analysis_agent: Remove verbose examples
2. module_mapping_agent: Consolidate AVM patterns
3. module_development_agent: Major consolidation (largest impact)
4. deployment_wrapper_agent: Quick cleanup
5. Final validation: Measure actual reduction

## Key Principles
✅ **Keep**: Core logic, requirements, validation rules
✅ **Keep**: Research instructions (Bing, MCP)
✅ **Keep**: Critical warnings for ambiguous behavior
❌ **Remove**: Verbose examples agents can infer
❌ **Remove**: Repeated patterns (DRY principle)
❌ **Remove**: Hardcoded lists (use research instead)

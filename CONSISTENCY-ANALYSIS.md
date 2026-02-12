# Model Consistency Analysis & Recommendations

## 🔍 Root Causes of Inconsistent Responses

### 1. **Inconsistent Temperature Settings**

| Agent | Temperature | Issue |
|-------|------------|-------|
| **DescriptionAgent** | `0.3` (hardcoded) | ❌ Higher than others, causes variability |
| VisionAgent | `0.1` (from config) | ✅ Consistent |
| FilterAgent | `0.1` (from config) | ✅ Consistent |
| OCRAgent | `0.1` (from config) | ✅ Consistent |
| NetworkFlowAgent | `0.1` (from config) | ✅ Consistent |
| SecurityAgent | `0.1` (from config) | ✅ Consistent |
| InteractiveAgent | `0.1` (from config) | ✅ Consistent |
| **ServiceAnalysisAgent** | `None` (missing) | ❌ Uses model default (~1.0) |
| **ModuleMappingAgent** | `None` (missing) | ❌ Uses model default (~1.0) |
| **ModuleDevelopmentAgent** | `None` (missing) | ❌ Uses model default (~1.0) |
| DeploymentWrapperAgent | `0.1` (hardcoded) | ✅ Consistent |

**Critical Issue**: DescriptionAgent at 0.3 causes 23→21→19 resource count variations.

### 2. **Missing top_p Parameter**

None of the agents set `top_p` (nucleus sampling), which defaults to `1.0` (100% probability mass).
- **Default behavior**: Model considers all possible tokens
- **Recommendation**: Set `top_p=0.95` for deterministic outputs while maintaining quality

### 3. **No Response Format Constraints**

Agents rely on prompt engineering alone, without structured output constraints:
- GPT-4o supports `response_format` for JSON mode
- Current: Agents return markdown-wrapped JSON (causes Phase 2 parsing errors)
- **Recommendation**: Use `response_format={"type": "json_object"}` for Phase 2 agents

### 4. **Vision Model Variance**

DescriptionAgent uses **vision model** (GPT-4o Vision) which has inherent variability in image interpretation:
- Different crops/focus each run
- Ambiguous visual elements interpreted differently
- No deterministic guarantee for vision models even at temperature=0.0

## 📊 Impact Analysis

### Phase 1 Variability Chain:
```
DescriptionAgent (temp=0.3) 
  → Detects 23 components one run, 21 the next
    → VisionAgent sees different "ground truth" context
      → FilterAgent classifies differently
        → Final count: 18→21 resource swing
```

### Phase 2 Variability:
```
ServiceAnalysisAgent (no temp setting, defaults to ~1.0)
  → High randomness in service extraction
    → Different services selected each run
      → ModuleMappingAgent (no temp, defaults to ~1.0)
        → Different modules mapped
          → Inconsistent IaC output
```

## ✅ Recommended Settings

### Configuration (config.py)
```python
# Phase 1: Detection & Analysis (Deterministic)
model_temperature: float = 0.0  # Fully deterministic (was 0.1)
top_p: float = 0.95  # Nucleus sampling for quality

# Phase 2: Code Generation (Slightly Creative)
phase2_temperature: float = 0.1  # Allow minor variation in code style
phase2_top_p: float = 0.95
```

### Agent-Specific Overrides

**DescriptionAgent** (currently 0.3):
- **Recommendation**: `temperature=0.0, top_p=0.95`
- **Rationale**: Description should be deterministic; vision model already has inherent variance

**ServiceAnalysisAgent** (currently missing):
- **Recommendation**: `temperature=0.0, top_p=0.95, response_format={"type": "json_object"}`
- **Rationale**: Extraction must be consistent, JSON mode prevents markdown wrapping

**ModuleMappingAgent** (currently missing):
- **Recommendation**: `temperature=0.1, top_p=0.95, response_format={"type": "json_object"}`
- **Rationale**: Some creativity helpful for module selection, but consistent structure

**ModuleDevelopmentAgent** (currently missing):
- **Recommendation**: `temperature=0.2, top_p=0.95`
- **Rationale**: Code generation benefits from slight creativity for idiomatic patterns

## 🎯 Implementation Priority

### CRITICAL (Fix Immediately):
1. ✅ **ServiceAnalysisAgent**: Add `temperature=0.0`
2. ✅ **ModuleMappingAgent**: Add `temperature=0.1`
3. ✅ **DescriptionAgent**: Change `0.3` → `0.0`

### HIGH (Next):
4. ⚠️ **Add response_format** to Phase 2 agents (fixes JSON wrapping)
5. ⚠️ **Add top_p=0.95** to all agents

### MEDIUM (Future):
6. 📝 Add seed parameter (GPT-4o supports deterministic seeding)
7. 📝 Cache DescriptionAgent results by image hash

## 🔬 Testing Recommendations

### Consistency Test:
```bash
# Run 5 times with same image
for i in {1..5}; do
    python main.py input/baseline.png > output_$i.json
done

# Compare resource counts
jq '.resources | length' output_*.json | sort | uniq -c
# Expected: All 5 runs show same count

# Compare service names
jq -r '.resources[].service_type' output_1.json | sort > services_1.txt
jq -r '.resources[].service_type' output_5.json | sort > services_5.txt
diff services_1.txt services_5.txt
# Expected: No differences
```

### Variance Metrics:
- **Acceptable**: ±0 resources across 10 runs
- **Warning**: ±1 resource (investigate)
- **Critical**: ±2+ resources (configuration issue)

## 📖 Additional Factors

### Non-Temperature Variability Sources:

1. **Tool Call Ordering**:
   - Bing search results may vary by timing/cache
   - **Mitigation**: Cache tool results per session

2. **Parallel Agent Execution**:
   - Race conditions in resource detection
   - **Mitigation**: Serialize critical stages (Description → Vision)

3. **Model Version Updates**:
   - Azure updates GPT-4o periodically
   - **Mitigation**: Pin to specific model version in deployment

4. **Context Window Limits**:
   - Large images may be cropped differently
   - **Mitigation**: Validate image preprocessing is deterministic

## 🎓 Best Practices for Consistency

1. **Always set temperature explicitly** (don't rely on defaults)
2. **Use temperature=0.0 for extraction tasks** (Phase 1, Phase 2 Stage 1)
3. **Use temperature=0.1-0.2 for generation tasks** (Phase 2 Stages 3-4)
4. **Add top_p=0.95** to balance quality and consistency
5. **Use response_format for JSON outputs** (prevents markdown wrapping)
6. **Log temperature in each agent's initialization** for debugging
7. **Include run_id/seed** in output for reproducibility tracking

## 📝 Implementation Checklist

- [ ] Update config.py with temperature and top_p defaults
- [ ] Fix DescriptionAgent temperature (0.3 → 0.0)
- [ ] Add temperature to ServiceAnalysisAgent
- [ ] Add temperature to ModuleMappingAgent
- [ ] Add temperature to ModuleDevelopmentAgent
- [ ] Add response_format to Phase 2 JSON-returning agents
- [ ] Add top_p to all agent create_agent calls
- [ ] Create consistency test script
- [ ] Document temperature settings in agent docstrings
- [ ] Add temperature validation in agent __init__

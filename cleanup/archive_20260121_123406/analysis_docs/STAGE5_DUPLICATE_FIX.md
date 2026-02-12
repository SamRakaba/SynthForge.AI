# Fixed: Duplicate Stage 5 Progress Messages

## Issue
Stage 5 (Deployment Wrappers) was displaying progress messages twice:

```
▶ Stage 5/6: Deployment Wrappers
  -> Generating deployment wrappers...
  -> Creating BICEP deployment orchestration...
  -> Deployment wrappers configured
  ✓ Deployment Wrappers completed

... (other stages continue)

✓ ✓ Phase 2 complete! Generated 14 modules
Output: iac\modules

▶ Stage 5/6: Deployment Wrappers    ← DUPLICATE!
  ->  Generating CAF naming module...
  ->  Generating development environment (1/3)...
  ->  ✓ development environment complete
  ->  Generating staging environment (2/3)...
  ->  ✓ staging environment complete
  ->  Generating production environment (3/3)...
  ->  ✓ production environment complete
```

## Root Cause
The workflow was emitting Stage 5 progress at TWO levels:

1. **Workflow Level** (`workflow_phase2.py` lines 597-606):
   - Emitted generic "Stage 5" start messages BEFORE calling the agent
   - `await self._emit_progress("deployment_wrappers", "Generating deployment wrappers...", 0.85)`
   - `await self._emit_progress("deployment_wrappers", "Creating BICEP...", 0.87)`
   - `await self._emit_progress("deployment_wrappers", "Deployment wrappers configured", 0.90)`

2. **Agent Level** (`deployment_wrapper_agent.py` via `wrapper_progress` callback):
   - Emitted detailed progress DURING agent execution
   - "Generating CAF naming module..."
   - "Generating development environment (1/3)..."
   - "✓ development environment complete"
   - etc.

Both sets of messages were being displayed, causing the duplicate "Stage 5" header.

## Fix
Commented out the premature workflow-level progress emissions for Stage 5, allowing ONLY the agent's detailed progress callback to report Stage 5 status.

### Changes Made

**File**: `synthforge/workflow_phase2.py`

#### Change 1: Removed Stage 5 start messages (lines 597-600)

**Before**:
```python
# Stage 5: Deployment Wrappers - Generate deployment orchestration (85-90%)
await self._emit_progress("deployment_wrappers", "Generating deployment wrappers...", 0.85)
await self._emit_progress("deployment_wrappers", f"Creating {self.iac_format.upper()} deployment orchestration...", 0.87)
```

**After**:
```python
# Stage 5: Deployment Wrappers - Generate deployment orchestration (85-90%)
# NOTE: Stage 5 progress is handled by the deployment wrapper agent's callback
# await self._emit_progress("deployment_wrappers", "Generating deployment wrappers...", 0.85)
# await self._emit_progress("deployment_wrappers", f"Creating {self.iac_format.upper()} deployment orchestration...", 0.87)
```

#### Change 2: Removed Stage 5 completion message (line 658)

**Before**:
```python
finally:
    wrapper_agent.cleanup()

await self._emit_progress("deployment_wrappers", "Deployment wrappers configured", 0.90)

# Stage 6: ADO Pipelines...
```

**After**:
```python
finally:
    wrapper_agent.cleanup()

# NOTE: Stage 5 completion is handled by wrapper_progress callback
# await self._emit_progress("deployment_wrappers", "Deployment wrappers configured", 0.90)

# Stage 6: ADO Pipelines...
```

## Expected Output After Fix

Stage 5 should now appear only ONCE with detailed progress:

```
▶ Stage 4/6: Module Generation
  -> Generating reusable IaC modules...
  -> [1/14] Generating datafactory-factories module...
  ... (all modules)
  ✓ Module Generation completed

▶ Stage 5/6: Deployment Wrappers
  ->  Generating CAF naming module...
  ->  Generating development environment (1/3)...
  ->  ✓ development environment complete
  ->  Generating staging environment (2/3)...
  ->  ✓ staging environment complete
  ->  Generating production environment (3/3)...
  ->  ✓ production environment complete
  ✓ Deployment Wrappers completed

▶ Stage 6/6: ADO Pipelines
  -> Generating CI/CD pipelines...
  -> Creating azure-devops pipeline configurations...
  -> CI/CD pipelines configured
  ✓ ADO Pipelines completed

✓ ✓ Phase 2 complete! Generated 14 modules
Output: iac\modules
```

## Pattern for Future Stages

**Rule**: When an agent provides its own detailed progress callback, the workflow should NOT emit generic start/completion messages for that stage.

**Good Pattern**:
```python
# Stage X: Agent with detailed progress
# NOTE: Stage X progress is handled by agent's callback
# await self._emit_progress("stage_name", "Starting...", progress)

agent_result = await agent.run(
    progress_callback=detailed_progress_callback
)

# NOTE: Stage X completion is handled by agent's callback
# await self._emit_progress("stage_name", "Complete", progress)
```

**Bad Pattern** (causes duplicates):
```python
# Stage X: Agent with detailed progress
await self._emit_progress("stage_name", "Starting...", progress)  # ❌ DUPLICATE!

agent_result = await agent.run(
    progress_callback=detailed_progress_callback  # Also emits "Starting..."
)

await self._emit_progress("stage_name", "Complete", progress)  # ❌ DUPLICATE!
```

## Testing
Run Phase 2 workflow and verify:
- [ ] Stage 5 appears only ONCE
- [ ] Detailed progress messages are shown (naming module, environments)
- [ ] No duplicate "Stage 5/6: Deployment Wrappers" headers
- [ ] Transitions cleanly from Stage 4 → Stage 5 → Stage 6

## Related Files
- `synthforge/workflow_phase2.py` - Phase 2 workflow orchestration
- `synthforge/agents/deployment_wrapper_agent.py` - Stage 5 agent with detailed progress
- `main.py` - Progress display callback

---

**Status**: ✅ Fixed
**Validated**: ✅ No syntax errors
**Testing**: Pending user verification

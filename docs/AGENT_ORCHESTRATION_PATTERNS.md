# Agent Orchestration Patterns for GitHub Copilot

**Document Version:** 1.0  
**Date:** February 14, 2026  
**Purpose:** Comprehensive patterns for orchestrating multi-agent workflows with GitHub Copilot Agents

---

## Table of Contents

1. [Orchestration Fundamentals](#1-orchestration-fundamentals)
2. [Sequential Pipeline Pattern](#2-sequential-pipeline-pattern)
3. [Parallel Execution Pattern](#3-parallel-execution-pattern)
4. [Event-Driven Pattern](#4-event-driven-pattern)
5. [Hierarchical Agent Pattern](#5-hierarchical-agent-pattern)
6. [Feedback Loop Pattern](#6-feedback-loop-pattern)
7. [State Management Patterns](#7-state-management-patterns)
8. [Error Handling & Recovery](#8-error-handling--recovery)
9. [Performance Optimization](#9-performance-optimization)
10. [Best Practices](#10-best-practices)

---

## 1. Orchestration Fundamentals

### 1.1 What is Agent Orchestration?

Agent orchestration is the coordination of multiple specialized agents to accomplish complex tasks that no single agent can handle alone.

**Key Concepts:**

```
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │ Agent A  │───▶│ Agent B  │───▶│ Agent C  │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│       │               │               │                    │
│       ▼               ▼               ▼                    │
│  ┌─────────────────────────────────────────┐             │
│  │         SHARED STATE / ARTIFACTS        │             │
│  └─────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Orchestration Responsibilities

**The orchestrator:**
1. **Sequences** agent execution
2. **Passes data** between agents
3. **Manages state** across workflow
4. **Handles errors** and retries
5. **Monitors progress** and performance
6. **Coordinates** parallel execution

**The agents:**
1. **Focus** on single responsibility
2. **Consume** typed inputs
3. **Produce** typed outputs
4. **Use tools** to accomplish tasks
5. **Report** confidence and errors

### 1.3 Orchestration Mechanisms

| Mechanism | Use Case | Example |
|-----------|----------|---------|
| **GitHub Actions Workflow** | Scheduled/triggered workflows | PR-triggered analysis |
| **Python Orchestrator** | Programmatic control, complex logic | CLI tool, API server |
| **Webhooks** | Real-time event processing | Image upload triggers analysis |
| **GitHub App** | Interactive user experiences | Copilot Chat integration |

---

## 2. Sequential Pipeline Pattern

### 2.1 Overview

Agents execute in strict order, each consuming output from the previous agent.

**When to Use:**
- Strong data dependencies between agents
- Simple, linear workflows
- Debugging and traceability are priorities

**SynthForge.AI Phase 1 Example:**

```
Vision → Filter → Interactive → Network Flow → Security
```

### 2.2 Implementation

**GitHub Actions Workflow:**

```yaml
name: Sequential Pipeline

on: workflow_dispatch

jobs:
  agent-1:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.run.outputs.result }}
    steps:
      - name: Run Agent 1
        id: run
        run: python -m agents.run vision input.png
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: agent-1-output
          path: output/result.json
  
  agent-2:
    needs: agent-1
    runs-on: ubuntu-latest
    steps:
      - name: Download previous result
        uses: actions/download-artifact@v4
        with:
          name: agent-1-output
      - name: Run Agent 2
        run: python -m agents.run filter result.json
```

**Python Orchestrator:**

```python
from typing import TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')
U = TypeVar('U')

@dataclass
class PipelineStage(Generic[T, U]):
    """A stage in the pipeline."""
    name: str
    agent_name: str
    input_type: type[T]
    output_type: type[U]


class SequentialPipeline:
    """
    Orchestrates agents in sequential order.
    
    Each agent's output becomes the next agent's input.
    """
    
    def __init__(self):
        self.stages: list[PipelineStage] = []
        self.logger = logging.getLogger(__name__)
    
    def add_stage(
        self, 
        name: str, 
        agent_name: str,
        input_type: type,
        output_type: type
    ):
        """Add a pipeline stage."""
        stage = PipelineStage(
            name=name,
            agent_name=agent_name,
            input_type=input_type,
            output_type=output_type
        )
        self.stages.append(stage)
    
    async def run(self, initial_input):
        """
        Run the pipeline.
        
        Args:
            initial_input: Input for first stage
        
        Returns:
            Output from final stage
        """
        current_data = initial_input
        
        for stage in self.stages:
            self.logger.info(f"Running stage: {stage.name}")
            
            # Validate input type
            if not isinstance(current_data, stage.input_type):
                raise TypeError(
                    f"Stage {stage.name} expected {stage.input_type}, "
                    f"got {type(current_data)}"
                )
            
            # Run agent
            agent = AgentFactory.create(stage.agent_name)
            async with agent:
                current_data = await agent.process(current_data)
            
            # Validate output type
            if not isinstance(current_data, stage.output_type):
                raise TypeError(
                    f"Stage {stage.name} produced {type(current_data)}, "
                    f"expected {stage.output_type}"
                )
            
            self.logger.info(f"✓ Stage {stage.name} completed")
        
        return current_data


# Usage
async def run_phase1_pipeline(image_path: Path):
    """Run Phase 1 analysis pipeline."""
    pipeline = SequentialPipeline()
    
    # Define stages
    pipeline.add_stage("Vision", "vision", Path, DetectionResult)
    pipeline.add_stage("Filter", "filter", DetectionResult, FilterResult)
    pipeline.add_stage("Network", "network_flow", FilterResult, NetworkFlowResult)
    pipeline.add_stage("Security", "security", NetworkFlowResult, SecurityRecommendation)
    
    # Run
    result = await pipeline.run(image_path)
    return result
```

### 2.3 Advantages & Disadvantages

**Advantages:**
- ✅ Simple to understand and debug
- ✅ Clear data flow and dependencies
- ✅ Easy error isolation
- ✅ Deterministic execution order

**Disadvantages:**
- ❌ Slower (no parallelization)
- ❌ Single point of failure (one agent fails, whole pipeline stops)
- ❌ Can't exploit independent work

---

## 3. Parallel Execution Pattern

### 3.1 Overview

Multiple agents execute simultaneously when they have no dependencies.

**When to Use:**
- Agents have independent inputs
- Need to minimize total execution time
- Have sufficient compute resources

**SynthForge.AI Opportunities:**

```
┌──────────────┐
│ Filter Agent │
└──────┬───────┘
       │
       ├─────────────┬─────────────┐
       ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Network  │  │ Security │  │ Cost Est │
│   Flow   │  │  Agent   │  │  Agent   │
└──────────┘  └──────────┘  └──────────┘
       │             │             │
       └─────────────┴─────────────┘
                     ▼
              ┌──────────────┐
              │   Combiner   │
              └──────────────┘
```

### 3.2 Implementation

**GitHub Actions Workflow:**

```yaml
name: Parallel Execution

on: workflow_dispatch

jobs:
  preparation:
    runs-on: ubuntu-latest
    outputs:
      data: ${{ steps.prep.outputs.data }}
    steps:
      - name: Prepare shared data
        id: prep
        run: echo "data=..." >> $GITHUB_OUTPUT
  
  # Run multiple agents in parallel
  parallel-agents:
    needs: preparation
    strategy:
      matrix:
        agent: [network_flow, security, cost_estimation]
      fail-fast: false  # Continue even if one fails
    runs-on: ubuntu-latest
    steps:
      - name: Run ${{ matrix.agent }}
        run: python -m agents.run ${{ matrix.agent }} ${{ needs.preparation.outputs.data }}
      - name: Upload result
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.agent }}-result
          path: output/result.json
  
  combine-results:
    needs: parallel-agents
    runs-on: ubuntu-latest
    steps:
      - name: Download all results
        uses: actions/download-artifact@v4
        with:
          pattern: '*-result'
      - name: Combine results
        run: python -m orchestration.combine_results
```

**Python Orchestrator:**

```python
import asyncio
from typing import List, Dict, Any

class ParallelOrchestrator:
    """
    Runs multiple agents in parallel and combines results.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def run_parallel(
        self, 
        agent_tasks: List[tuple[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run multiple agents in parallel.
        
        Args:
            agent_tasks: List of (agent_name, input_data) tuples
        
        Returns:
            Dictionary mapping agent_name to result
        """
        # Create tasks
        tasks = []
        for agent_name, input_data in agent_tasks:
            task = self._run_single_agent(agent_name, input_data)
            tasks.append((agent_name, task))
        
        # Run all concurrently
        results = {}
        completed = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )
        
        # Process results
        for (agent_name, _), result in zip(tasks, completed):
            if isinstance(result, Exception):
                self.logger.error(f"Agent {agent_name} failed: {result}")
                results[agent_name] = None
            else:
                self.logger.info(f"✓ Agent {agent_name} completed")
                results[agent_name] = result
        
        return results
    
    async def _run_single_agent(self, agent_name: str, input_data: Any) -> Any:
        """Run a single agent."""
        agent = AgentFactory.create(agent_name)
        async with agent:
            return await agent.process(input_data)


# Usage
async def run_analysis_parallel(filter_result: FilterResult):
    """Run multiple analysis agents in parallel."""
    orchestrator = ParallelOrchestrator()
    
    # Define parallel tasks
    tasks = [
        ("network_flow", filter_result),
        ("security", filter_result),
        ("cost_estimation", filter_result)
    ]
    
    # Run in parallel
    results = await orchestrator.run_parallel(tasks)
    
    # Combine results
    return {
        "network": results["network_flow"],
        "security": results["security"],
        "cost": results["cost_estimation"]
    }
```

### 3.3 Advantages & Disadvantages

**Advantages:**
- ✅ Faster total execution time
- ✅ Better resource utilization
- ✅ Isolated failures (one agent can fail without affecting others)

**Disadvantages:**
- ❌ More complex orchestration
- ❌ Harder to debug
- ❌ Need to combine results from multiple sources

---

## 4. Event-Driven Pattern

### 4.1 Overview

Agents react to events rather than being explicitly sequenced.

**When to Use:**
- Long-running workflows
- User interactions required
- Asynchronous processing
- Multiple trigger sources

**Event Flow:**

```
┌──────────┐
│ PR Event │
└─────┬────┘
      │
      ▼
┌──────────────┐
│  Event Bus   │
└──────┬───────┘
       │
       ├─────────────┬─────────────┬─────────────┐
       ▼             ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Handler 1 │  │Handler 2 │  │Handler 3 │  │Handler 4 │
└─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘
      │             │             │             │
      └─────────────┴─────────────┴─────────────┘
                           ▼
                    ┌──────────────┐
                    │   Results    │
                    └──────────────┘
```

### 4.2 Implementation

**Event Types:**

```python
from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict

class EventType(str, Enum):
    """Types of events in the system."""
    DIAGRAM_UPLOADED = "diagram.uploaded"
    DETECTION_COMPLETE = "detection.complete"
    FILTER_COMPLETE = "filter.complete"
    USER_REVIEW_COMPLETE = "user.review.complete"
    SECURITY_COMPLETE = "security.complete"
    ANALYSIS_COMPLETE = "analysis.complete"


class Event(BaseModel):
    """Base event structure."""
    event_type: EventType
    data: Dict[str, Any]
    correlation_id: str  # Track related events
    timestamp: str
```

**Event Handler:**

```python
from typing import Callable, Dict, List
import asyncio

class EventBus:
    """
    Event bus for agent coordination.
    """
    
    def __init__(self):
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        self.logger.info(f"Publishing event: {event.event_type}")
        
        handlers = self.handlers.get(event.event_type, [])
        if not handlers:
            self.logger.warning(f"No handlers for {event.event_type}")
            return
        
        # Run all handlers concurrently
        await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True
        )


# Event handlers
async def handle_diagram_uploaded(event: Event):
    """Handle diagram upload event."""
    diagram_url = event.data["diagram_url"]
    
    # Run vision agent
    async with VisionAgent() as agent:
        result = await agent.process(diagram_url)
    
    # Publish next event
    await event_bus.publish(Event(
        event_type=EventType.DETECTION_COMPLETE,
        data={"detection_result": result.model_dump()},
        correlation_id=event.correlation_id,
        timestamp=datetime.now().isoformat()
    ))


async def handle_detection_complete(event: Event):
    """Handle detection complete event."""
    detection_result = DetectionResult(**event.data["detection_result"])
    
    # Run filter agent
    async with FilterAgent() as agent:
        result = await agent.process(detection_result)
    
    # Publish next event
    await event_bus.publish(Event(
        event_type=EventType.FILTER_COMPLETE,
        data={"filter_result": result.model_dump()},
        correlation_id=event.correlation_id,
        timestamp=datetime.now().isoformat()
    ))


# Setup
event_bus = EventBus()
event_bus.subscribe(EventType.DIAGRAM_UPLOADED, handle_diagram_uploaded)
event_bus.subscribe(EventType.DETECTION_COMPLETE, handle_detection_complete)

# Trigger workflow
await event_bus.publish(Event(
    event_type=EventType.DIAGRAM_UPLOADED,
    data={"diagram_url": "https://example.com/diagram.png"},
    correlation_id="analysis-123",
    timestamp=datetime.now().isoformat()
))
```

**GitHub Actions Event-Driven:**

```yaml
# .github/workflows/event-detection-complete.yml
name: Handle Detection Complete

on:
  repository_dispatch:
    types: [detection_complete]

jobs:
  run-filter:
    runs-on: ubuntu-latest
    steps:
      - name: Download detection result
        run: |
          # Download from artifact storage
          
      - name: Run filter agent
        run: python -m agents.run filter detection.json
      
      - name: Trigger next event
        uses: peter-evans/repository-dispatch@v2
        with:
          event-type: filter_complete
          client-payload: ${{ toJson(steps.filter.outputs) }}
```

### 4.3 Advantages & Disadvantages

**Advantages:**
- ✅ Highly decoupled
- ✅ Easy to add new handlers
- ✅ Supports async workflows
- ✅ Scales well

**Disadvantages:**
- ❌ Harder to trace execution flow
- ❌ More complex debugging
- ❌ Need event infrastructure

---

## 5. Hierarchical Agent Pattern

### 5.1 Overview

A coordinator agent manages sub-agents, delegating work and aggregating results.

**When to Use:**
- Complex decision-making required
- Dynamic agent selection
- Need adaptive workflows

**Architecture:**

```
┌──────────────────────────────────────┐
│       COORDINATOR AGENT              │
│  (Decides which agents to call)      │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┬────────┐
    ▼                 ▼        ▼
┌────────┐      ┌────────┐  ┌────────┐
│Agent A │      │Agent B │  │Agent C │
└────────┘      └────────┘  └────────┘
    │                 │        │
    └────────┬────────┴────────┘
             ▼
      ┌─────────────┐
      │   Result    │
      └─────────────┘
```

### 5.2 Implementation

```python
class CoordinatorAgent(CopilotAgent):
    """
    Coordinator agent that manages sub-agents.
    
    Decides which agents to call based on the input.
    """
    
    def __init__(self):
        super().__init__(AgentConfig(
            name="CoordinatorAgent",
            model="gpt-4o",
            instructions=self._load_coordinator_instructions(),
            tools=["web_search", "file_search"]
        ))
        self.sub_agents = {
            "vision": VisionAgent,
            "filter": FilterAgent,
            "network": NetworkFlowAgent,
            "security": SecurityAgent
        }
    
    async def process(self, input_data: AnalysisRequest) -> AnalysisResult:
        """
        Process request by coordinating sub-agents.
        
        Args:
            input_data: Analysis request
        
        Returns:
            Combined analysis result
        """
        # Ask coordinator to create execution plan
        plan = await self._create_execution_plan(input_data)
        
        # Execute plan
        results = {}
        for step in plan.steps:
            agent_name = step.agent_name
            agent_input = step.input_data
            
            # Run sub-agent
            result = await self._run_sub_agent(agent_name, agent_input)
            results[agent_name] = result
            
            # Check if we should continue
            if step.conditional and not self._should_continue(result):
                break
        
        # Aggregate results
        return await self._aggregate_results(results)
    
    async def _create_execution_plan(
        self, 
        request: AnalysisRequest
    ) -> ExecutionPlan:
        """
        Use AI to create execution plan.
        
        The coordinator agent decides:
        - Which agents to call
        - In what order
        - What data to pass
        """
        prompt = f"""
        Create an execution plan for this analysis request:
        
        Request: {request.model_dump_json()}
        
        Available agents:
        - vision: Detect icons from diagram
        - filter: Classify resources
        - network: Analyze network topology
        - security: Generate security recommendations
        
        Return a JSON execution plan with:
        - steps: List of agent calls
        - conditionals: When to skip steps
        - data_flow: How to pass data between steps
        """
        
        response = await self._call_copilot_api(prompt)
        return ExecutionPlan.model_validate_json(response)
    
    async def _run_sub_agent(self, agent_name: str, input_data: Any) -> Any:
        """Run a sub-agent."""
        agent_class = self.sub_agents[agent_name]
        agent = agent_class()
        
        async with agent:
            return await agent.process(input_data)
```

### 5.3 Advantages & Disadvantages

**Advantages:**
- ✅ Adaptive workflows
- ✅ Handles complex decision logic
- ✅ Reuses existing agents
- ✅ Centralized control

**Disadvantages:**
- ❌ Coordinator becomes complex
- ❌ Additional overhead
- ❌ Coordinator is single point of failure

---

## 6. Feedback Loop Pattern

### 6.1 Overview

Agents can revisit previous steps based on validation or quality checks.

**When to Use:**
- Quality validation required
- Iterative improvement needed
- Self-correction capabilities

**Flow:**

```
┌─────────────┐
│   Agent A   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Validation  │──── Pass ───▶ [Continue]
└──────┬──────┘
       │
     Fail
       │
       ▼
┌─────────────┐
│ Fix Agent   │
└──────┬──────┘
       │
       └──────────▶ Back to Agent A (retry)
```

### 6.2 Implementation

```python
class FeedbackLoopOrchestrator:
    """
    Orchestrator with feedback loops for quality improvement.
    """
    
    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.logger = logging.getLogger(__name__)
    
    async def run_with_validation(
        self,
        agent_name: str,
        input_data: Any,
        validator_name: str,
        fixer_name: str = None
    ) -> Any:
        """
        Run agent with validation and retry loop.
        
        Args:
            agent_name: Main agent to run
            input_data: Input for agent
            validator_name: Agent to validate output
            fixer_name: Agent to fix issues (optional)
        
        Returns:
            Validated output
        """
        for iteration in range(self.max_iterations):
            self.logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")
            
            # Run main agent
            agent = AgentFactory.create(agent_name)
            async with agent:
                result = await agent.process(input_data)
            
            # Validate
            validator = AgentFactory.create(validator_name)
            async with validator:
                validation = await validator.process(result)
            
            # Check if valid
            if validation.is_valid:
                self.logger.info("✓ Validation passed")
                return result
            
            self.logger.warning(f"Validation failed: {validation.issues}")
            
            # Try to fix
            if fixer_name and iteration < self.max_iterations - 1:
                fixer = AgentFactory.create(fixer_name)
                async with fixer:
                    result = await fixer.process(result, validation.issues)
                
                # Use fixed result as input for next iteration
                input_data = result
            else:
                # No fixer or last iteration
                self.logger.error("Cannot fix issues, returning best attempt")
                return result
        
        raise RuntimeError(f"Failed to produce valid output after {self.max_iterations} iterations")


# Usage: Module Development with Code Quality Validation
async def generate_module_with_validation(service: ServiceRequirement):
    """Generate IaC module with quality validation loop."""
    orchestrator = FeedbackLoopOrchestrator(max_iterations=3)
    
    result = await orchestrator.run_with_validation(
        agent_name="module_development",
        input_data=service,
        validator_name="code_quality",
        fixer_name="code_quality_fixer"
    )
    
    return result
```

### 6.3 Advantages & Disadvantages

**Advantages:**
- ✅ Self-correcting
- ✅ Higher quality outputs
- ✅ Automated retry logic

**Disadvantages:**
- ❌ Longer execution time
- ❌ May not converge
- ❌ More complex logic

---

## 7. State Management Patterns

### 7.1 Artifact-Based State

**Store state in GitHub Actions artifacts:**

```python
class ArtifactStateManager:
    """Manage state via GitHub Actions artifacts."""
    
    async def save_state(self, key: str, data: BaseModel):
        """Save state to artifact."""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / f"{key}.json"
        with open(filepath, "w") as f:
            f.write(data.model_dump_json(indent=2))
    
    async def load_state(self, key: str, model_class: type[BaseModel]) -> BaseModel:
        """Load state from artifact."""
        filepath = Path("artifacts") / f"{key}.json"
        with open(filepath, "r") as f:
            return model_class.model_validate_json(f.read())
```

### 7.2 PR-Based State

**Store state in PR descriptions/comments:**

```python
class PRStateManager:
    """Manage state in PR descriptions."""
    
    def __init__(self, repo: str, pr_number: int):
        self.github = Github(os.environ["GITHUB_TOKEN"])
        self.repo = self.github.get_repo(repo)
        self.pr = self.repo.get_pull(pr_number)
    
    async def save_state(self, key: str, data: dict):
        """Save state to PR body."""
        # Append to PR body with special markers
        marker = f"<!-- STATE:{key} -->"
        state_json = json.dumps(data)
        
        body = self.pr.body
        if marker in body:
            # Update existing
            pattern = f"{marker}.*?<!-- /STATE:{key} -->"
            replacement = f"{marker}\n{state_json}\n<!-- /STATE:{key} -->"
            body = re.sub(pattern, replacement, body, flags=re.DOTALL)
        else:
            # Append new
            body += f"\n\n{marker}\n{state_json}\n<!-- /STATE:{key} -->"
        
        self.pr.edit(body=body)
    
    async def load_state(self, key: str) -> dict:
        """Load state from PR body."""
        marker = f"<!-- STATE:{key} -->"
        body = self.pr.body
        
        pattern = f"{marker}\\n(.*?)\\n<!-- /STATE:{key} -->"
        match = re.search(pattern, body, re.DOTALL)
        
        if match:
            return json.loads(match.group(1))
        return {}
```

### 7.3 Database State

**For production systems:**

```python
class DatabaseStateManager:
    """Manage state in PostgreSQL database."""
    
    async def save_state(self, workflow_id: str, state_data: dict):
        """Save state to database."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO workflow_state (workflow_id, state_data, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (workflow_id)
                DO UPDATE SET state_data = $2, updated_at = $3
            """, workflow_id, json.dumps(state_data), datetime.now())
    
    async def load_state(self, workflow_id: str) -> dict:
        """Load state from database."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT state_data FROM workflow_state
                WHERE workflow_id = $1
            """, workflow_id)
            
            return json.loads(row['state_data']) if row else {}
```

---

## 8. Error Handling & Recovery

### 8.1 Retry with Exponential Backoff

```python
import asyncio
from functools import wraps

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retrying failed agent calls."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    delay = base_delay * (2 ** attempt)
                    logging.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
        
        return wrapper
    return decorator


# Usage
@retry_with_backoff(max_retries=3, base_delay=2.0)
async def run_agent_with_retry(agent_name: str, input_data: Any):
    """Run agent with automatic retry."""
    agent = AgentFactory.create(agent_name)
    async with agent:
        return await agent.process(input_data)
```

### 8.2 Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for agent calls."""
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to recover."""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
```

---

## 9. Performance Optimization

### 9.1 Caching Agent Results

```python
from functools import wraps
import hashlib
import json

class AgentResultCache:
    """Cache agent results to avoid redundant work."""
    
    def __init__(self):
        self.cache = {}
    
    def cache_key(self, agent_name: str, input_data: Any) -> str:
        """Generate cache key."""
        data_str = json.dumps(
            input_data.model_dump() if hasattr(input_data, 'model_dump') else str(input_data),
            sort_keys=True
        )
        return hashlib.sha256(f"{agent_name}:{data_str}".encode()).hexdigest()
    
    async def get_or_compute(
        self,
        agent_name: str,
        input_data: Any,
        compute_func: Callable
    ) -> Any:
        """Get from cache or compute."""
        key = self.cache_key(agent_name, input_data)
        
        if key in self.cache:
            logging.info(f"Cache hit for {agent_name}")
            return self.cache[key]
        
        logging.info(f"Cache miss for {agent_name}, computing...")
        result = await compute_func()
        self.cache[key] = result
        return result


# Usage
cache = AgentResultCache()

async def run_with_cache(agent_name: str, input_data: Any):
    """Run agent with result caching."""
    async def compute():
        agent = AgentFactory.create(agent_name)
        async with agent:
            return await agent.process(input_data)
    
    return await cache.get_or_compute(agent_name, input_data, compute)
```

### 9.2 Batch Processing

```python
class BatchOrchestrator:
    """Process multiple items in batches."""
    
    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size
    
    async def process_batch(
        self,
        agent_name: str,
        items: List[Any]
    ) -> List[Any]:
        """Process items in batches."""
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # Process batch in parallel
            batch_results = await asyncio.gather(
                *[self._process_item(agent_name, item) for item in batch]
            )
            
            results.extend(batch_results)
        
        return results
    
    async def _process_item(self, agent_name: str, item: Any) -> Any:
        """Process single item."""
        agent = AgentFactory.create(agent_name)
        async with agent:
            return await agent.process(item)
```

---

## 10. Best Practices

### 10.1 Orchestration Design Principles

1. **Keep Agents Focused**
   - Each agent should have single, well-defined responsibility
   - Don't create "god agents" that do everything

2. **Use Typed Interfaces**
   - Define clear input/output types with Pydantic
   - Validate data at boundaries

3. **Handle Failures Gracefully**
   - Don't fail entire workflow for single agent failure
   - Provide fallback mechanisms
   - Log errors with context

4. **Make State Explicit**
   - Store intermediate results
   - Make workflows resumable
   - Enable debugging by examining state

5. **Monitor Performance**
   - Track agent execution times
   - Identify bottlenecks
   - Log resource usage

### 10.2 When to Use Each Pattern

| Pattern | Best For | Avoid When |
|---------|----------|------------|
| **Sequential** | Simple workflows, strong dependencies | Need speed, independent agents |
| **Parallel** | Independent agents, speed critical | Agents have dependencies |
| **Event-Driven** | Long workflows, async processing | Simple workflows, need simplicity |
| **Hierarchical** | Complex decision logic, adaptive | Simple workflows, avoid overhead |
| **Feedback Loop** | Quality validation, iterative | Simple tasks, time-sensitive |

### 10.3 Monitoring & Observability

```python
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def monitor_agent(agent_name: str):
    """Context manager for monitoring agent execution."""
    start = time.time()
    
    try:
        yield
        
        duration = time.time() - start
        logging.info(
            f"Agent {agent_name} completed in {duration:.2f}s",
            extra={
                "agent": agent_name,
                "duration": duration,
                "status": "success"
            }
        )
    except Exception as e:
        duration = time.time() - start
        logging.error(
            f"Agent {agent_name} failed after {duration:.2f}s: {e}",
            extra={
                "agent": agent_name,
                "duration": duration,
                "status": "error",
                "error": str(e)
            }
        )
        raise


# Usage
async with monitor_agent("vision"):
    result = await vision_agent.process(image)
```

---

## Conclusion

Effective orchestration is key to building robust multi-agent systems. Choose the pattern that best fits your use case:

- **Start simple** with sequential pipelines
- **Optimize** with parallel execution
- **Scale** with event-driven architecture
- **Adapt** with hierarchical coordination
- **Improve** with feedback loops

The SynthForge.AI conversion provides a real-world example of applying these patterns to build a production-grade multi-agent system on GitHub Copilot.

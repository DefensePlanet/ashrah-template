# Prompt Variant Optimization System - Architecture Design

**Designer:** System Architect
**Date:** 2026-01-19
**Status:** Architectural Blueprint

---

## Executive Summary

Lightweight prompt optimization system that integrates with Catalyst's existing quality.db, Agent Memory v2.0, and RLM infrastructure. Enables systematic testing and evolution of prompt variants across agents and depth levels with minimal new infrastructure.

**Core Value:** Automatically discover which prompt strategies work best for which tasks, then graduate winning patterns to defaults.

---

## System Architecture

```
                        Prompt Variant Optimization System

┌─────────────────────────────────────────────────────────────────────┐
│                        VARIANT TRACKING LAYER                       │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │ Variant Registry │    │ Task Classifier  │    │ Variant      │  │
│  │ • Variant defs   │───►│ • Complexity     │───►│ Selector     │  │
│  │ • Success rates  │    │ • Task type      │    │ • A/B testing│  │
│  │ • Token metrics  │    │ • Context size   │    │ • Adaptive   │  │
│  └──────────────────┘    └──────────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EXECUTION & MEASUREMENT                         │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │ RLM Integration  │    │ Agent Execution  │    │ Quality Gate │  │
│  │ • Root (depth=0) │───►│ • Task execution │───►│ • Code review│  │
│  │ • Recursive (1+) │    │ • Outcome        │    │ • Validation │  │
│  │ • Deep (2-3)     │    │ • Metrics        │    │ • Impact     │  │
│  └──────────────────┘    └──────────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE & LEARNING LOOP                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │ quality.db       │    │ Agent Memory v2  │    │ Learning Loop│  │
│  │ • variant_execs  │◄───│ • Successful     │◄───│ • Extract    │  │
│  │ • variant_metrics│    │   patterns       │    │   patterns   │  │
│  │ • variant_winners│    │ • Anti-patterns  │    │ • Graduate   │  │
│  └──────────────────┘    └──────────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GRADUATION PIPELINE                            │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │ Winner Detection │───►│ Validation Gate  │───►│ Auto-Graduate│  │
│  │ • Statistical    │    │ • Confidence >95%│    │ • Update     │  │
│  │   significance   │    │ • Sample size    │    │   defaults   │  │
│  │ • Success delta  │    │ • Quality checks │    │ • Notify     │  │
│  └──────────────────┘    └──────────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Database Schema Extensions (quality.db)

### New Tables

```sql
-- Variant definitions and metadata
CREATE TABLE prompt_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_name TEXT UNIQUE NOT NULL,
    agent_name TEXT,              -- NULL for system-wide variants
    depth_level INTEGER,          -- NULL for non-RLM variants, 0=root, 1-3=recursive
    variant_type TEXT NOT NULL,   -- 'system_prompt', 'instructions', 'examples', 'hybrid'
    variant_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    notes TEXT
);
CREATE INDEX idx_variants_agent_depth ON prompt_variants(agent_name, depth_level);
CREATE INDEX idx_variants_active ON prompt_variants(is_active);

-- Execution tracking
CREATE TABLE variant_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    task_type TEXT NOT NULL,      -- 'code_generation', 'debugging', 'research', etc.
    depth_level INTEGER,           -- NULL for non-RLM tasks
    complexity_score REAL,         -- 0.0-1.0, from task classifier
    context_tokens INTEGER,
    response_tokens INTEGER,
    success BOOLEAN,               -- Did task complete successfully?
    quality_score REAL,            -- From code review or validation
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_id INTEGER,             -- FK to reviews table
    FOREIGN KEY (variant_id) REFERENCES prompt_variants(id),
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);
CREATE INDEX idx_variant_execs_variant ON variant_executions(variant_id);
CREATE INDEX idx_variant_execs_agent_task ON variant_executions(agent_name, task_type);
CREATE INDEX idx_variant_execs_success ON variant_executions(success);

-- Aggregated metrics (computed periodically)
CREATE TABLE variant_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    agent_name TEXT,
    task_type TEXT,
    depth_level INTEGER,
    window_start DATE NOT NULL,   -- Metrics computed for this time window
    window_end DATE NOT NULL,
    total_executions INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    success_rate REAL,
    avg_quality_score REAL,
    avg_tokens_used INTEGER,
    avg_duration_ms INTEGER,
    token_efficiency REAL,        -- quality_score / (tokens_used / 1000)
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variant_id) REFERENCES prompt_variants(id),
    UNIQUE(variant_id, agent_name, task_type, window_start)
);
CREATE INDEX idx_variant_metrics_variant ON variant_metrics(variant_id);
CREATE INDEX idx_variant_metrics_success_rate ON variant_metrics(success_rate DESC);

-- Winner tracking (graduated variants)
CREATE TABLE variant_winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    agent_name TEXT,
    task_type TEXT,
    depth_level INTEGER,
    superseded_variant_id INTEGER, -- Previous default variant
    promotion_reason TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    sample_size INTEGER NOT NULL,
    performance_delta REAL,        -- Improvement over previous default
    promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    promoted_by TEXT DEFAULT 'auto',
    FOREIGN KEY (variant_id) REFERENCES prompt_variants(id),
    FOREIGN KEY (superseded_variant_id) REFERENCES prompt_variants(id)
);
CREATE INDEX idx_variant_winners_promoted ON variant_winners(promoted_at DESC);
```

### Linking to Existing Schema

- `variant_executions.review_id` → `reviews.id` (links to code review outcomes)
- `variant_executions` captures quality_score from code review findings
- Reuses existing `reviews` table for quality measurement

---

## 2. Module Design

### 2.1 Core Classes

```python
# {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class VariantType(Enum):
    SYSTEM_PROMPT = "system_prompt"      # Full system prompt replacement
    INSTRUCTIONS = "instructions"         # Instruction block modifications
    EXAMPLES = "examples"                 # Example-based variations
    HYBRID = "hybrid"                     # Combined approach


class TaskType(Enum):
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    RESEARCH = "research"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    TESTING = "testing"


@dataclass
class PromptVariant:
    """Definition of a prompt variant."""
    id: Optional[int]
    variant_name: str
    agent_name: Optional[str]     # None = system-wide
    depth_level: Optional[int]    # None = non-RLM, 0 = root, 1-3 = recursive
    variant_type: VariantType
    variant_content: str
    is_active: bool = True
    is_default: bool = False
    notes: Optional[str] = None


@dataclass
class VariantExecution:
    """Tracks a single execution of a variant."""
    variant_id: int
    agent_name: str
    task_type: TaskType
    depth_level: Optional[int]
    complexity_score: float       # 0.0-1.0
    context_tokens: int
    response_tokens: int
    success: bool
    quality_score: Optional[float]  # From code review
    duration_ms: int
    review_id: Optional[int] = None


@dataclass
class VariantMetrics:
    """Aggregated metrics for a variant."""
    variant_id: int
    success_rate: float
    avg_quality_score: float
    avg_tokens_used: int
    token_efficiency: float       # quality / (tokens / 1000)
    sample_size: int


class VariantRegistry:
    """
    Manages prompt variant definitions and selection.

    Responsibilities:
    - Store and retrieve variant definitions
    - Select variant based on task characteristics
    - Track which variant is default for each context
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def register_variant(self, variant: PromptVariant) -> int:
        """Register a new prompt variant."""
        pass

    def get_variant(self, variant_id: int) -> Optional[PromptVariant]:
        """Retrieve variant by ID."""
        pass

    def select_variant(
        self,
        agent_name: str,
        task_type: TaskType,
        depth_level: Optional[int] = None,
        complexity_score: Optional[float] = None,
        exploration_rate: float = 0.1  # Epsilon for epsilon-greedy
    ) -> PromptVariant:
        """
        Select best variant for given context.

        Uses epsilon-greedy strategy:
        - 90% of time: use highest-performing variant (exploit)
        - 10% of time: randomly select for exploration
        """
        pass

    def get_default_variant(
        self,
        agent_name: str,
        task_type: Optional[TaskType] = None,
        depth_level: Optional[int] = None
    ) -> PromptVariant:
        """Get current default variant for context."""
        pass

    def set_default_variant(
        self,
        variant_id: int,
        agent_name: str,
        task_type: Optional[TaskType] = None,
        depth_level: Optional[int] = None
    ):
        """Promote variant to default for context."""
        pass


class VariantExecutionTracker:
    """
    Tracks variant executions and outcomes.

    Responsibilities:
    - Log variant usage
    - Capture quality metrics
    - Link to code review outcomes
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def log_execution(self, execution: VariantExecution) -> int:
        """Record a variant execution."""
        pass

    def get_executions(
        self,
        variant_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        task_type: Optional[TaskType] = None,
        min_quality: Optional[float] = None,
        limit: int = 100
    ) -> List[VariantExecution]:
        """Query executions with filters."""
        pass


class VariantMetricsComputer:
    """
    Computes aggregated metrics for variants.

    Responsibilities:
    - Calculate success rates
    - Compute token efficiency
    - Detect statistical significance
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def compute_metrics(
        self,
        variant_id: int,
        window_days: int = 7
    ) -> VariantMetrics:
        """Compute metrics for variant over time window."""
        pass

    def compare_variants(
        self,
        variant_a_id: int,
        variant_b_id: int,
        min_sample_size: int = 30
    ) -> Dict[str, Any]:
        """
        Statistical comparison of two variants.

        Returns:
            confidence: float (0.0-1.0)
            delta: float (improvement of A over B)
            significant: bool (p < 0.05)
            sample_size_a: int
            sample_size_b: int
        """
        pass


class VariantGraduationPipeline:
    """
    Automatically graduates winning variants to defaults.

    Responsibilities:
    - Detect candidates for graduation
    - Validate statistical significance
    - Promote winners to default status
    - Notify about graduations
    """

    def __init__(
        self,
        db_path: str,
        min_sample_size: int = 30,
        min_confidence: float = 0.95,
        min_improvement: float = 0.05  # 5% improvement threshold
    ):
        self.db_path = db_path
        self.min_sample_size = min_sample_size
        self.min_confidence = min_confidence
        self.min_improvement = min_improvement

    def find_graduation_candidates(self) -> List[Dict[str, Any]]:
        """
        Find variants that meet graduation criteria.

        Criteria:
        - Sample size >= min_sample_size
        - Statistically significant improvement over default
        - Confidence >= min_confidence
        """
        pass

    def graduate_variant(
        self,
        variant_id: int,
        agent_name: str,
        task_type: Optional[TaskType],
        reason: str,
        auto: bool = True
    ) -> int:
        """
        Promote variant to default status.

        Returns:
            winner_id from variant_winners table
        """
        pass

    def run_graduation_cycle(self) -> List[Dict[str, Any]]:
        """
        Run full graduation cycle.

        Returns list of graduated variants.
        """
        pass


class PromptOptimizer:
    """
    Main facade for prompt optimization system.

    Integrates all components for easy use.
    """

    def __init__(self, db_path: str = "{{CATALYST_ROOT}}/metrics/quality.db"):
        self.registry = VariantRegistry(db_path)
        self.tracker = VariantExecutionTracker(db_path)
        self.metrics_computer = VariantMetricsComputer(db_path)
        self.graduation_pipeline = VariantGraduationPipeline(db_path)

    def select_and_track(
        self,
        agent_name: str,
        task_type: TaskType,
        depth_level: Optional[int] = None,
        complexity_score: Optional[float] = None
    ) -> tuple[PromptVariant, int]:
        """
        Select variant and create tracking record.

        Returns:
            (variant, execution_id) for later outcome logging
        """
        pass

    def log_outcome(
        self,
        execution_id: int,
        success: bool,
        quality_score: Optional[float],
        context_tokens: int,
        response_tokens: int,
        duration_ms: int,
        review_id: Optional[int] = None
    ):
        """Update execution record with outcome."""
        pass

    def get_best_variant(
        self,
        agent_name: str,
        task_type: TaskType,
        depth_level: Optional[int] = None
    ) -> PromptVariant:
        """Get current best-performing variant."""
        pass
```

---

## 3. RLM Integration Design

### 3.1 Depth-Level Variant System

RLM has three depth levels, each needing different prompt strategies:

| Depth | Context | Variant Focus |
|-------|---------|---------------|
| **Root (0)** | Full conversation history | Decomposition, orchestration, context management |
| **Recursive (1)** | Parent context + specific task | Task focus, tool usage, efficiency |
| **Deep (2-3)** | Narrow context, specific subtask | Precision, minimal context, direct answers |

### 3.2 Variant Categories per Depth

**Root Level (depth=0) Variants:**
- `root-decomposer-v1`: Emphasizes breaking down complex tasks
- `root-orchestrator-v1`: Focuses on coordinating sub-queries
- `root-efficient-v1`: Minimizes unnecessary recursion

**Recursive Level (depth=1) Variants:**
- `recursive-focused-v1`: Stays on-task, minimal tangents
- `recursive-tool-heavy-v1`: Aggressive tool usage
- `recursive-read-only-v1`: Read-only tools for safety

**Deep Level (depth=2-3) Variants:**
- `deep-precise-v1`: One-shot answers, no exploration
- `deep-minimal-v1`: Minimal token usage
- `deep-verify-v1`: Self-verification before response

### 3.3 Integration Points

```python
# In RLM orchestrator (tools/rlm-claude-code/src/orchestrator.py)

from global.rag.service.prompt_optimizer import PromptOptimizer

class RLMOrchestrator:
    def __init__(self):
        self.prompt_optimizer = PromptOptimizer()

    def execute_query(
        self,
        query: str,
        context: dict,
        depth: int,
        task_type: TaskType
    ):
        # Select variant based on depth and task
        variant, execution_id = self.prompt_optimizer.select_and_track(
            agent_name="rlm-orchestrator",
            task_type=task_type,
            depth_level=depth,
            complexity_score=self._classify_complexity(query, context)
        )

        # Apply variant to system prompt
        system_prompt = self._apply_variant(variant, context)

        # Execute LLM call
        start_time = time.time()
        response = self.llm_client.call(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
        )
        duration_ms = int((time.time() - start_time) * 1000)

        # Log outcome
        self.prompt_optimizer.log_outcome(
            execution_id=execution_id,
            success=response.get("success", False),
            quality_score=None,  # Filled in later by code review
            context_tokens=response.usage.prompt_tokens,
            response_tokens=response.usage.completion_tokens,
            duration_ms=duration_ms
        )

        return response
```

---

## 4. Agent Memory v2.0 Integration

### 4.1 Pattern Storage

Successful prompt variants get stored as patterns in Agent Memory:

```python
# After variant graduates to default
from global.rag.service.memory import MemoryCoordinator

coordinator = MemoryCoordinator()

# Store as system pattern
pattern_id = coordinator.create_system_pattern(
    pattern_name=f"prompt-variant-{variant.variant_name}",
    pattern_type=PatternType.OPTIMIZATION,
    description=f"Graduated prompt variant for {variant.agent_name} {variant.task_type}",
    implementation_guide=variant.variant_content,
    success_rate=metrics.success_rate,
    usage_count=metrics.sample_size,
    participating_agents=[variant.agent_name]
)
```

### 4.2 Anti-Pattern Detection

Failed variants become anti-patterns:

```python
# When variant consistently underperforms
coordinator.create_memory(
    agent_name="system",
    memory_type=MemoryType.ERROR,
    content=f"Prompt variant {variant.variant_name} underperformed: {failure_reason}",
    impact_score=0.3,  # Negative learning
    tags=["prompt-optimization", "anti-pattern", variant.task_type.value]
)
```

---

## 5. Learning Loop Integration

### 5.1 Extending learning_loops.py

Add new method to `LearningLoop` class:

```python
def extract_prompt_patterns(
    self,
    min_sample_size: int = 30
) -> List[Dict[str, Any]]:
    """
    Extract successful prompt patterns from variant executions.

    Algorithm:
    1. Query variant_metrics for high-performing variants
    2. Check sample size and statistical significance
    3. Extract common characteristics
    4. Generate pattern suggestions
    """
    from prompt_optimizer import PromptOptimizer

    optimizer = PromptOptimizer()
    candidates = optimizer.graduation_pipeline.find_graduation_candidates()

    patterns = []
    for candidate in candidates:
        variant = optimizer.registry.get_variant(candidate["variant_id"])
        metrics = optimizer.metrics_computer.compute_metrics(variant.id)

        # Extract pattern characteristics
        pattern = {
            "pattern_name": f"prompt-{variant.variant_name}",
            "variant_id": variant.id,
            "success_rate": metrics.success_rate,
            "token_efficiency": metrics.token_efficiency,
            "task_type": variant.task_type,
            "depth_level": variant.depth_level,
            "sample_size": metrics.sample_size
        }
        patterns.append(pattern)

    return patterns
```

### 5.2 Automatic Graduation via Learning Loop

```python
# In scheduled learning loop (could run daily/weekly)
def run_optimization_learning_cycle():
    """Automated learning cycle for prompt optimization."""

    optimizer = PromptOptimizer()
    learning_loop = LearningLoop(coordinator)

    # 1. Extract successful patterns
    patterns = learning_loop.extract_prompt_patterns()

    # 2. Run graduation pipeline
    graduated = optimizer.graduation_pipeline.run_graduation_cycle()

    # 3. Store patterns in Agent Memory
    for grad in graduated:
        variant = optimizer.registry.get_variant(grad["variant_id"])
        coordinator.create_system_pattern(
            pattern_name=f"prompt-{variant.variant_name}",
            pattern_type=PatternType.OPTIMIZATION,
            description=f"Graduated prompt variant: {grad['reason']}",
            implementation_guide=variant.variant_content,
            success_rate=grad["success_rate"],
            usage_count=grad["sample_size"]
        )

    return {
        "patterns_extracted": len(patterns),
        "variants_graduated": len(graduated)
    }
```

---

## 6. File Locations & Modifications

### New Files

```
{{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/
├── __init__.py
├── models.py              # Dataclasses and enums
├── registry.py            # VariantRegistry
├── tracker.py             # VariantExecutionTracker
├── metrics.py             # VariantMetricsComputer
├── graduation.py          # VariantGraduationPipeline
└── optimizer.py           # PromptOptimizer facade
```

### Modified Files

```
{{CATALYST_ROOT}}/global/rag/service/memory/learning_loops.py
+ Add extract_prompt_patterns() method

{{CATALYST_ROOT}}/tools/rlm-claude-code/src/orchestrator.py
+ Import PromptOptimizer
+ Integrate variant selection
+ Log execution outcomes

{{CATALYST_ROOT}}/metrics/quality.db
+ Run migration script to add new tables

{{CATALYST_ROOT}}/global/claude-config/hooks/pre_tool_use.py
+ (Optional) Hook to log variant usage before tool calls
```

### Migration Script

```sql
-- {{CATALYST_ROOT}}/metrics/migrations/add_prompt_variants.sql

-- Run with: sqlite3 {{CATALYST_ROOT}}/metrics/quality.db < migrations/add_prompt_variants.sql

BEGIN TRANSACTION;

-- [Include all CREATE TABLE statements from Section 1]

-- Seed with initial baseline variants
INSERT INTO prompt_variants (variant_name, agent_name, depth_level, variant_type, variant_content, is_default)
VALUES
  ('baseline-root', NULL, 0, 'system_prompt', 'Default root orchestration prompt', 1),
  ('baseline-recursive', NULL, 1, 'system_prompt', 'Default recursive task prompt', 1),
  ('baseline-deep', NULL, 2, 'system_prompt', 'Default deep precision prompt', 1);

COMMIT;
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Core infrastructure and data capture

**Deliverables:**
1. Database schema migration
2. Core classes: `PromptVariant`, `VariantExecution`, `VariantRegistry`
3. Basic variant selection (random for exploration)
4. Execution tracking integrated with quality.db

**Success Criteria:**
- [ ] Variants can be registered and retrieved
- [ ] Executions are logged to quality.db
- [ ] Linkage to reviews table works

**Value:** Start collecting data on which prompts are used for which tasks

---

### Phase 2: RLM Integration (Week 2)
**Goal:** Integrate with RLM depth-based routing

**Deliverables:**
1. Depth-level variant system (root/recursive/deep)
2. Integration with RLM orchestrator
3. Task complexity classifier
4. Epsilon-greedy variant selection

**Success Criteria:**
- [ ] RLM uses different variants per depth level
- [ ] Variant selection respects exploration rate
- [ ] Context tokens and task type captured

**Value:** Systematic testing of depth-specific prompt strategies

---

### Phase 3: Metrics & Comparison (Week 3)
**Goal:** Compute performance metrics and compare variants

**Deliverables:**
1. `VariantMetricsComputer` implementation
2. Statistical comparison functions
3. Token efficiency calculations
4. Dashboard/query interface for metrics

**Success Criteria:**
- [ ] Metrics computed for all active variants
- [ ] Can compare any two variants statistically
- [ ] Token efficiency trends visible

**Value:** Evidence-based variant selection instead of intuition

---

### Phase 4: Auto-Graduation (Week 4)
**Goal:** Automatically promote winning variants

**Deliverables:**
1. `VariantGraduationPipeline` implementation
2. Statistical significance testing
3. Automated promotion to default status
4. Integration with learning loops

**Success Criteria:**
- [ ] Winners detected with >95% confidence
- [ ] Auto-graduation runs daily
- [ ] Notifications on promotions

**Value:** System self-improves without manual intervention

---

### Phase 5: Agent Memory Integration (Week 5)
**Goal:** Store successful patterns as reusable knowledge

**Deliverables:**
1. Pattern extraction from graduated variants
2. Anti-pattern storage for failures
3. Cross-agent pattern sharing
4. Extended `learning_loops.py` functionality

**Success Criteria:**
- [ ] Graduated variants stored as patterns
- [ ] Patterns retrievable for similar tasks
- [ ] Anti-patterns prevent regression

**Value:** Organizational learning across all agents

---

## 8. Example Usage Scenarios

### Scenario 1: RLM Root-Level Optimization

```python
# User asks complex architectural question
# RLM orchestrator selects variant for root level

optimizer = PromptOptimizer()

variant, exec_id = optimizer.select_and_track(
    agent_name="rlm-orchestrator",
    task_type=TaskType.ARCHITECTURE,
    depth_level=0,  # Root level
    complexity_score=0.85  # High complexity
)

# Apply variant's system prompt
system_prompt = variant.variant_content.format(
    task_description="Design microservices architecture",
    available_tools="bash, read, grep, web_search"
)

# After execution completes and code review runs
optimizer.log_outcome(
    execution_id=exec_id,
    success=True,
    quality_score=0.92,  # From code review
    context_tokens=45000,
    response_tokens=8000,
    duration_ms=12500,
    review_id=12345  # Link to reviews table
)
```

### Scenario 2: Backend Dev Agent Optimization

```python
# Backend Dev agent working on API implementation

variant, exec_id = optimizer.select_and_track(
    agent_name="🏛️ Backend Developer",
    task_type=TaskType.CODE_GENERATION,
    depth_level=None,  # Not RLM context
    complexity_score=0.6
)

# Variant might include specific instructions like:
# "Use FastAPI best practices, include type hints, write docstrings"

# After code review detects quality issues
optimizer.log_outcome(
    execution_id=exec_id,
    success=False,  # Code review found critical issues
    quality_score=0.45,
    context_tokens=12000,
    response_tokens=3000,
    duration_ms=8000,
    review_id=12346
)

# This variant will rank lower in future selection
```

### Scenario 3: Auto-Graduation

```python
# Daily learning loop runs

results = run_optimization_learning_cycle()

# Output:
# {
#   "patterns_extracted": 3,
#   "variants_graduated": 1,
#   "graduated_variants": [
#     {
#       "variant_name": "backend-fastapi-focused-v2",
#       "agent_name": "🏛️ Backend Developer",
#       "task_type": "code_generation",
#       "success_rate": 0.94,
#       "improvement": 0.12,  # 12% better than previous default
#       "sample_size": 47,
#       "confidence": 0.97
#     }
#   ]
# }

# System automatically promotes variant to default
# Future Backend Dev tasks use the winning variant
```

---

## 9. Success Metrics

### System Health Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Variant Coverage** | 80% of agent+task combinations have ≥2 variants | `SELECT COUNT(DISTINCT agent_name, task_type) FROM prompt_variants` |
| **Exploration Rate** | 10% of executions use non-default variants | `SELECT AVG(CASE WHEN is_default = 0 THEN 1 ELSE 0 END) FROM variant_executions` |
| **Graduation Frequency** | 1-2 graduations per week initially | `SELECT COUNT(*) FROM variant_winners WHERE promoted_at > date('now', '-7 days')` |
| **Sample Size** | Average 50+ executions per variant | `SELECT AVG(total_executions) FROM variant_metrics` |

### Business Impact Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Quality Improvement** | 10% increase in avg code review score | Compare `avg_quality_score` before/after graduation |
| **Token Efficiency** | 15% reduction in tokens per task | Track `token_efficiency` trend |
| **Success Rate** | 5% increase in task completion rate | Compare `success_rate` across time windows |
| **Auto-Improvement** | 50% of graduations are automatic | `SELECT COUNT(*) WHERE promoted_by = 'auto'` |

---

## 10. Future Enhancements (Not in Initial Scope)

### Multi-Armed Bandit Optimization
Replace epsilon-greedy with contextual bandits for smarter exploration/exploitation tradeoff.

### Prompt Mutation System
Automatically generate new variant candidates by mutating successful prompts using LLM.

### A/B Testing Framework
Formalized A/B testing with statistical power calculations and early stopping rules.

### Cross-Agent Pattern Transfer
Detect when a variant works for Agent A on Task X, and test it for Agent B on similar Task Y.

### Semantic Variant Clustering
Use embeddings to cluster similar variants and prevent redundant testing.

---

## 11. Risk Mitigation

### Risk: Low Sample Sizes
**Mitigation:** Set minimum sample size thresholds (30+) before graduation, use Bayesian priors for small samples

### Risk: Overfitting to Recent Tasks
**Mitigation:** Use rolling time windows, weight older data less, require sustained performance

### Risk: Variant Explosion
**Mitigation:** Cap active variants per context (max 5), archive low-performers after 100 trials

### Risk: Quality Measurement Bias
**Mitigation:** Use multiple quality signals (code review + validation + manual spot-checks)

### Risk: Regression from Bad Graduation
**Mitigation:** Keep superseded variants active, easy rollback mechanism, confidence thresholds

---

## 12. Open Questions for Review

1. **Time window for metrics**: 7 days? 30 days? Rolling window?
2. **Graduation thresholds**: 95% confidence too strict? 90% better?
3. **Exploration rate**: 10% epsilon-greedy reasonable or too low?
4. **Agent-specific vs system-wide**: Start with system-wide variants or per-agent from day 1?
5. **Integration timing**: Hook into pre-commit review or separate scheduled job?

---

## Appendix A: Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Database** | SQLite (quality.db) | Already in use, supports WAL mode, sufficient for single-node |
| **Statistical Tests** | scipy.stats (t-test, chi-square) | Industry standard, minimal dependency |
| **Data Classes** | Python dataclasses | Simple, type-safe, integrates with Pydantic |
| **Metrics Computation** | SQL aggregations + Python | Leverage database for aggregation, Python for complex stats |
| **Learning Loop** | Existing learning_loops.py | Reuse proven infrastructure |
| **Scheduling** | cron job calling Python script | Simple, reliable, no new daemon |

---

## Appendix B: Sample Variant Definition

```python
# Example: Backend Dev FastAPI-focused variant

variant = PromptVariant(
    id=None,
    variant_name="backend-fastapi-focused-v2",
    agent_name="🏛️ Backend Developer",
    depth_level=None,  # Not RLM-specific
    variant_type=VariantType.INSTRUCTIONS,
    variant_content="""
You are implementing a FastAPI backend service.

**Required approach:**
1. Use type hints on all functions (Pydantic models for request/response)
2. Include comprehensive docstrings (Google style)
3. Implement error handling with HTTPException
4. Use dependency injection for database sessions
5. Follow RESTful conventions (proper status codes)

**Code structure:**
- Place routes in `/routes/{resource}.py`
- Models in `/models/{resource}.py`
- Business logic in `/services/{resource}.py`

**Quality checklist before responding:**
- [ ] All functions have type hints
- [ ] Docstrings present and complete
- [ ] Error cases handled
- [ ] Status codes appropriate
- [ ] Pydantic models validate input
    """,
    is_active=True,
    is_default=False,
    notes="Emphasizes FastAPI best practices and code quality"
)
```

---

**End of Architecture Design**

Next steps:
1. Review with stakeholders ({{ORCHESTRATOR_NAME}}, BOSS, Backend Dev)
2. Validate database schema with sample queries
3. Build Phase 1 prototype
4. Run pilot with RLM orchestrator

<tts-summary>🎙️ Designed a lightweight prompt variant optimization system that integrates with Catalyst's existing quality database, Agent Memory, and RLM infrastructure to automatically discover and graduate winning prompt strategies.</tts-summary>

# Prompt Variant Optimization System - Executive Summary

**Designer:** System Architect
**Date:** 2026-01-19
**Status:** Architecture Complete - Ready for Review

---

## 🎯 What This System Does

**Problem:** We don't know which prompt strategies work best for which tasks. Currently using one-size-fits-all prompts that may not be optimal.

**Solution:** Lightweight system that:
1. **Tests** multiple prompt variants for each agent/task combination
2. **Measures** which variants produce better quality and token efficiency
3. **Graduates** winning variants to become new defaults automatically
4. **Learns** patterns and shares knowledge across agents

**Result:** Catalyst continuously improves its own prompts through data-driven optimization.

---

## 🏗️ Architecture at a Glance

```
User Request → Task Classification → Variant Selection → Agent Execution
                                            ↓
                                    Track Outcome
                                            ↓
                          Compute Metrics ← Quality Review
                                            ↓
                                    Statistical Test
                                            ↓
                          Auto-Graduate Winner → Store as Pattern
```

**Key Innovation:** Integrates with existing Catalyst infrastructure (quality.db, Agent Memory, RLM) rather than building new systems.

---

## 📊 Database Design

### 4 New Tables in quality.db

| Table | Purpose | Size Estimate |
|-------|---------|---------------|
| **prompt_variants** | Variant definitions | ~50 rows (10 KB) |
| **variant_executions** | Track each usage | ~10,000 rows/month (500 KB) |
| **variant_metrics** | Aggregated stats | ~200 rows (10 KB) |
| **variant_winners** | Graduation history | ~5 rows/month (1 KB) |

**Total Storage Impact:** <1 MB per month

### Key Schema Features

- **Foreign Keys:** `variant_executions.review_id` → `reviews.id` (links to code review)
- **Indexes:** Optimized for common queries (variant selection, metrics computation)
- **Views:** Convenience views for performance summaries and graduation tracking

---

## 🔧 Module Architecture

### 5 Core Modules

```python
# {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/

1. models.py              # Data structures and enums
2. registry.py            # VariantRegistry - manage variants
3. tracker.py             # VariantExecutionTracker - log usage
4. metrics.py             # VariantMetricsComputer - calculate stats
5. graduation.py          # VariantGraduationPipeline - auto-promote winners
```

### Usage Pattern

```python
from prompt_optimizer import PromptOptimizer

# Initialize
optimizer = PromptOptimizer()

# Before task execution
variant, exec_id = optimizer.select_and_track(
    agent_name="🏛️ Backend Developer",
    task_type=TaskType.CODE_GENERATION,
    complexity_score=0.7
)

# Apply variant to system prompt
system_prompt = variant.variant_content

# After execution completes
optimizer.log_outcome(
    execution_id=exec_id,
    success=True,
    quality_score=0.85,  # From code review
    context_tokens=12000,
    response_tokens=3000,
    duration_ms=8000
)
```

---

## 🔄 RLM Integration

### Depth-Level Variants

RLM has 3 depth levels, each needing different strategies:

| Depth | Role | Variant Focus | Example Variants |
|-------|------|---------------|------------------|
| **0 (Root)** | Orchestrator | Task decomposition | decomposer, orchestrator, efficient |
| **1 (Recursive)** | Task executor | Tool usage, focus | tool-heavy, read-only, focused |
| **2-3 (Deep)** | Precision specialist | Minimal tokens | precise, minimal, verify |

### Integration Point

```python
# In RLM orchestrator
variant, exec_id = optimizer.select_and_track(
    agent_name="rlm-orchestrator",
    task_type=TaskType.ARCHITECTURE,
    depth_level=0,  # Root level
    complexity_score=0.85
)
```

---

## 📈 Learning Loop Integration

### Pattern Extraction

When a variant graduates:
1. **Store in Agent Memory** as a `SystemPattern`
2. **Tag** with agent, task type, depth level
3. **Share** pattern across similar contexts

### Anti-Pattern Detection

When a variant consistently fails:
1. **Store as error memory** in Agent Memory
2. **Deactivate** after 100 trials with <50% success
3. **Prevent** similar approaches in future

### Automatic Cycle

```python
# Runs daily/weekly
def run_optimization_learning_cycle():
    # 1. Find graduation candidates
    candidates = optimizer.graduation_pipeline.find_graduation_candidates()

    # 2. Graduate winners
    graduated = optimizer.graduation_pipeline.run_graduation_cycle()

    # 3. Store as patterns
    for grad in graduated:
        memory.create_system_pattern(...)

    return summary
```

---

## 🎯 Success Metrics

### 30-Day Targets

- ✅ 50+ variant executions logged
- ✅ Metrics computed for all active variants
- ✅ 2+ variants per major agent/task combination
- ✅ 10% exploration rate maintained

### 90-Day Targets

- ✅ 2000+ variant executions logged
- ✅ 3-5 successful graduations
- ✅ 5% improvement in system-wide quality score
- ✅ 15% improvement in token efficiency
- ✅ Cross-agent pattern sharing active

---

## 📅 Implementation Timeline

### Phase 1: Foundation (Week 1)
**Focus:** Core infrastructure and data capture

**Deliverables:**
- Database schema migration
- Core classes: `PromptVariant`, `VariantRegistry`, `VariantExecutionTracker`
- Basic variant selection (epsilon-greedy)

**Success:** Variants can be registered and executions logged

---

### Phase 2: RLM Integration (Week 2)
**Focus:** Integrate with RLM depth-based routing

**Deliverables:**
- Depth-level variant system (root/recursive/deep)
- Task complexity classifier
- RLM orchestrator integration

**Success:** RLM uses different variants per depth level

---

### Phase 3: Metrics & Comparison (Week 3)
**Focus:** Compute performance metrics

**Deliverables:**
- `VariantMetricsComputer` implementation
- Statistical comparison functions
- Metrics dashboard queries

**Success:** Can compare variants statistically

---

### Phase 4: Auto-Graduation (Week 4)
**Focus:** Automatically promote winners

**Deliverables:**
- `VariantGraduationPipeline` implementation
- Statistical validation
- Automated promotion mechanism

**Success:** Winners graduate without manual intervention

---

### Phase 5: Agent Memory Integration (Week 5)
**Focus:** Store patterns as reusable knowledge

**Deliverables:**
- Extended `learning_loops.py`
- Pattern extraction from graduated variants
- Anti-pattern storage

**Success:** Patterns retrievable for similar tasks

---

## 🔐 Key Design Decisions

### 1. Minimal New Infrastructure
**Decision:** Extend quality.db instead of creating new database
**Rationale:** Reduces complexity, leverages existing schema, maintains single source of truth

### 2. Epsilon-Greedy Selection
**Decision:** 90% exploit (best variant) + 10% explore (random)
**Rationale:** Balances performance with discovering better approaches

### 3. Conservative Graduation Criteria
**Decision:** Require 95% confidence, 30+ samples, 5% improvement
**Rationale:** Prevents noise-driven graduations, ensures statistical validity

### 4. Integration with Code Review
**Decision:** Use code review quality scores as primary metric
**Rationale:** Already validated quality measurement, no new quality gate needed

### 5. Pattern Storage in Agent Memory
**Decision:** Graduated variants become `SystemPattern` objects
**Rationale:** Reuses proven learning infrastructure, enables cross-agent sharing

---

## 🚧 Risks & Mitigations

### Low Sample Sizes
**Risk:** Not enough data to detect winners
**Mitigation:** 10% exploration rate, run for 2+ weeks, Bayesian priors for small samples

### Variant Explosion
**Risk:** Too many variants to manage
**Mitigation:** Cap at 5 active per context, auto-archive low performers

### Statistical False Positives
**Risk:** Noise graduates a poor variant
**Mitigation:** Conservative thresholds (95% confidence, sustained performance)

### Regression from Bad Graduation
**Risk:** New default performs worse
**Mitigation:** Keep superseded variant active, easy rollback, 7-day cooldown period

---

## 💡 Example Scenario

### Scenario: Backend Dev FastAPI Optimization

**Day 1-7:** System tracks baseline variant performance
- 15 FastAPI tasks executed
- Success rate: 73%
- Token efficiency: 0.65

**Day 8:** New variant introduced: "backend-fastapi-focused-v2"
- Emphasizes type hints, docstrings, error handling

**Day 8-30:** Epsilon-greedy selection tests both variants
- Baseline: 25 executions, 73% success, 0.65 efficiency
- New variant: 28 executions, 89% success, 0.82 efficiency

**Day 31:** Graduation criteria met
- Statistical significance: p=0.003 (high confidence)
- Improvement: 16 percentage points (22% relative)
- Sample size: 28 > 30 minimum

**Day 31:** Auto-graduation
- New variant promoted to default
- Stored as pattern in Agent Memory
- Notification sent to monitoring system

**Day 32+:** All Future FastAPI tasks use winning variant
- Continued monitoring for regression
- Baseline variant kept active as fallback

---

## 📁 Files Created

### Architecture Documents
- `{{CATALYST_ROOT}}/.claude-context/ARCH-prompt-variant-optimization.md` (full design)
- `{{CATALYST_ROOT}}/.claude-context/ARCH-prompt-variant-implementation-roadmap.md` (5-week plan)
- `{{CATALYST_ROOT}}/.claude-context/ARCH-prompt-variant-SUMMARY.md` (this file)

### Sample Implementation
- `{{CATALYST_ROOT}}/.claude-context/SAMPLE-prompt-variant-migration.sql` (database schema)

### To Be Created (Implementation)
```
{{CATALYST_ROOT}}/
├── global/rag/service/prompt_optimizer/
│   ├── __init__.py
│   ├── models.py
│   ├── registry.py
│   ├── tracker.py
│   ├── metrics.py
│   ├── graduation.py
│   └── optimizer.py
├── metrics/migrations/
│   └── add_prompt_variants.sql
└── scripts/
    ├── compute_variant_metrics.py
    └── run_graduation_cycle.py
```

---

## 🎬 Next Steps

### Immediate (Before Implementation)
1. **Review** architecture with {{ORCHESTRATOR_NAME}} and BOSS
2. **Validate** database schema with sample queries
3. **Test** migration script in staging environment
4. **Get approval** on design decisions

### Phase 1 Start (Week 1)
1. **Run migration** on quality.db (with backup)
2. **Implement** core classes (models, registry, tracker)
3. **Test** variant registration and execution logging
4. **Verify** integration with quality.db

### After Phase 1 Complete
1. **Review** learnings from prototype
2. **Adjust** design if needed
3. **Continue** to Phase 2 (RLM Integration)

---

## 📞 Questions for Review

1. **Time Windows:** 7-day window for metrics reasonable? Or prefer 30-day?
2. **Graduation Thresholds:** 95% confidence too strict? 90% acceptable?
3. **Exploration Rate:** 10% epsilon-greedy appropriate or adjust?
4. **Scope:** System-wide variants first, or per-agent from day 1?
5. **Scheduling:** Daily metrics computation sufficient? Or real-time?

---

## 🏆 Expected Outcomes

### Short-Term (30 days)
- Data collection infrastructure operational
- Baseline metrics established
- First variant experiments running

### Medium-Term (90 days)
- 3-5 successful graduations
- Measurable quality improvements (5%+)
- Token efficiency gains (15%+)
- System self-improving automatically

### Long-Term (6 months)
- 20+ graduated variants across agents
- 10%+ system-wide quality improvement
- 20%+ token efficiency improvement
- Cross-agent pattern sharing mature
- Continuous self-optimization operating

---

## 📖 Additional Context

**Related Catalyst Systems:**
- **quality.db** - Code review and quality tracking
- **Agent Memory v2.0** - Persistent learning and pattern storage
- **RLM** - Recursive Language Model with depth-based routing
- **Learning Loops** - Automatic pattern extraction and consolidation
- **Bifrost Gateway** - Model routing and provider selection

**Design Philosophy:**
- **Pragmatic:** Minimal new infrastructure, maximal value
- **Data-Driven:** Evidence-based decisions, not intuition
- **Self-Improving:** System evolves automatically
- **Integrated:** Leverages existing Catalyst capabilities

---

**End of Executive Summary**

For full details:
- **Architecture:** See `ARCH-prompt-variant-optimization.md`
- **Implementation:** See `ARCH-prompt-variant-implementation-roadmap.md`
- **Database Schema:** See `SAMPLE-prompt-variant-migration.sql`

<tts-summary>🎙️ Completed comprehensive architectural design for prompt variant optimization system with database schema, module design, RLM integration, learning loop integration, and 5-week implementation roadmap ready for review.</tts-summary>

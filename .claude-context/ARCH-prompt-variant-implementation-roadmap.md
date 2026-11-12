# Prompt Variant Optimization - Implementation Roadmap

**Designer:** System Architect
**Date:** 2026-01-19
**Estimated Duration:** 5 weeks
**Dependencies:** quality.db, Agent Memory v2.0, RLM system

---

## Quick Reference Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                    PROMPT VARIANT OPTIMIZATION                        │
│                                                                       │
│  USER REQUEST                                                        │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │ Task         │────►│ Variant      │────►│ Agent/RLM    │        │
│  │ Classifier   │     │ Selector     │     │ Execution    │        │
│  │              │     │ (ε-greedy)   │     │              │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                   │                  │
│                                                   ▼                  │
│                                          ┌──────────────┐            │
│                                          │ Quality Gate │            │
│                                          │ (Code Review)│            │
│                                          └──────────────┘            │
│                                                   │                  │
│       ┌───────────────────────────────────────────┘                  │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │ quality.db   │────►│ Metrics      │────►│ Graduation   │        │
│  │ • executions │     │ Computer     │     │ Pipeline     │        │
│  │ • metrics    │     │              │     │              │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                   │                  │
│                                                   ▼                  │
│                                          ┌──────────────┐            │
│                                          │ Agent Memory │            │
│                                          │ (Patterns)   │            │
│                                          └──────────────┘            │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Phase-by-Phase Breakdown

### Phase 1: Foundation (Week 1)

**Objective:** Core infrastructure and data capture

**Tasks:**

1. **Database Schema Migration** (Day 1)
   - [ ] Create migration script: `{{CATALYST_ROOT}}/metrics/migrations/add_prompt_variants.sql`
   - [ ] Add 4 new tables: `prompt_variants`, `variant_executions`, `variant_metrics`, `variant_winners`
   - [ ] Run migration on quality.db
   - [ ] Verify schema with test queries
   - [ ] Seed with baseline variants (root/recursive/deep)

2. **Core Data Models** (Day 2)
   - [ ] Create `{{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/models.py`
   - [ ] Define enums: `VariantType`, `TaskType`
   - [ ] Define dataclasses: `PromptVariant`, `VariantExecution`, `VariantMetrics`
   - [ ] Add Pydantic validation for data integrity

3. **Variant Registry** (Day 2-3)
   - [ ] Create `registry.py` with `VariantRegistry` class
   - [ ] Implement `register_variant()` - insert new variants
   - [ ] Implement `get_variant()` - retrieve by ID
   - [ ] Implement `get_default_variant()` - get current default
   - [ ] Implement `set_default_variant()` - promote to default
   - [ ] Unit tests for all registry operations

4. **Execution Tracker** (Day 3-4)
   - [ ] Create `tracker.py` with `VariantExecutionTracker` class
   - [ ] Implement `log_execution()` - record variant usage
   - [ ] Implement `get_executions()` - query with filters
   - [ ] Add foreign key linkage to reviews table
   - [ ] Unit tests for tracker operations

5. **Simple Variant Selection** (Day 4-5)
   - [ ] Implement `select_variant()` in `VariantRegistry`
   - [ ] Start with random selection (pure exploration)
   - [ ] Add epsilon-greedy selection (90% best, 10% random)
   - [ ] Test variant selection distribution

6. **Integration Test** (Day 5)
   - [ ] Create end-to-end test: register variant → select → log execution
   - [ ] Verify data persists correctly in quality.db
   - [ ] Verify foreign key constraints work
   - [ ] Performance test: 1000 executions should take <1s

**Success Criteria:**
- ✅ 4 new tables created and accessible
- ✅ Variants can be registered and retrieved
- ✅ Executions are logged with all required fields
- ✅ Random and epsilon-greedy selection working
- ✅ All unit tests pass

**Deliverables:**
```
{{CATALYST_ROOT}}/
├── metrics/
│   ├── quality.db (migrated with new tables)
│   └── migrations/
│       └── add_prompt_variants.sql
└── global/rag/service/prompt_optimizer/
    ├── __init__.py
    ├── models.py
    ├── registry.py
    └── tracker.py
```

---

### Phase 2: RLM Integration (Week 2)

**Objective:** Integrate with RLM depth-based routing

**Tasks:**

1. **Task Complexity Classifier** (Day 1)
   - [ ] Add `TaskClassifier` class to `models.py`
   - [ ] Implement complexity scoring (0.0-1.0 based on query length, keywords)
   - [ ] Add task type detection (code_generation, debugging, research, etc.)
   - [ ] Test classifier accuracy on sample queries

2. **Depth-Level Variant System** (Day 1-2)
   - [ ] Create variants for each RLM depth level:
     - [ ] Root (depth=0): decomposer, orchestrator, efficient
     - [ ] Recursive (depth=1): focused, tool-heavy, read-only
     - [ ] Deep (depth=2-3): precise, minimal, verify
   - [ ] Register variants in database with depth_level field
   - [ ] Test variant selection respects depth_level filter

3. **RLM Orchestrator Integration** (Day 2-3)
   - [ ] Modify `{{CATALYST_ROOT}}/tools/rlm-claude-code/src/orchestrator.py`
   - [ ] Import `PromptOptimizer`
   - [ ] Add variant selection before LLM calls
   - [ ] Apply variant content to system prompt
   - [ ] Log execution with depth_level and complexity_score

4. **Context Token Capture** (Day 3-4)
   - [ ] Capture `context_tokens` from LLM response
   - [ ] Capture `response_tokens` from LLM response
   - [ ] Add to execution logging
   - [ ] Verify token counts match LLM API response

5. **Epsilon-Greedy Tuning** (Day 4)
   - [ ] Implement exploration rate parameter (default 10%)
   - [ ] Test different rates: 5%, 10%, 20%
   - [ ] Add configuration option for exploration rate
   - [ ] Monitor distribution: 90% should use best variant

6. **Integration Tests** (Day 5)
   - [ ] End-to-end test: RLM query → variant selection → execution → logging
   - [ ] Test all 3 depth levels use different variants
   - [ ] Test task type classification
   - [ ] Test complexity scoring correlation with task difficulty

**Success Criteria:**
- ✅ RLM uses different variants per depth level
- ✅ Task complexity and type are classified correctly
- ✅ Token counts captured accurately
- ✅ Epsilon-greedy selection maintains 90/10 ratio
- ✅ All integration tests pass

**Deliverables:**
```
{{CATALYST_ROOT}}/
├── global/rag/service/prompt_optimizer/
│   ├── models.py (updated with TaskClassifier)
│   └── optimizer.py (PromptOptimizer facade)
└── tools/rlm-claude-code/src/
    └── orchestrator.py (integrated with PromptOptimizer)
```

---

### Phase 3: Metrics & Comparison (Week 3)

**Objective:** Compute performance metrics and compare variants

**Tasks:**

1. **Metrics Computation** (Day 1-2)
   - [ ] Create `metrics.py` with `VariantMetricsComputer` class
   - [ ] Implement `compute_metrics()` - aggregate executions over time window
   - [ ] Calculate success_rate, avg_quality_score, avg_tokens_used
   - [ ] Calculate token_efficiency = quality_score / (tokens / 1000)
   - [ ] Populate `variant_metrics` table

2. **Statistical Comparison** (Day 2-3)
   - [ ] Implement `compare_variants()` - statistical comparison of two variants
   - [ ] Use scipy.stats.ttest_ind for significance testing
   - [ ] Calculate confidence interval
   - [ ] Calculate delta (improvement percentage)
   - [ ] Require minimum sample size (30+) for valid comparison

3. **Metrics Dashboard Queries** (Day 3-4)
   - [ ] Create helper queries for common metrics:
     - [ ] Top variants by success rate
     - [ ] Top variants by token efficiency
     - [ ] Variants needing more samples
     - [ ] Variants underperforming baseline
   - [ ] Add to `{{CATALYST_ROOT}}/metrics/queries/variant_metrics.sql`

4. **Scheduled Metrics Computation** (Day 4)
   - [ ] Create cron job script: `{{CATALYST_ROOT}}/scripts/compute_variant_metrics.py`
   - [ ] Run daily to compute metrics for all active variants
   - [ ] Add logging for metrics computation runs
   - [ ] Test script execution

5. **Performance Optimization** (Day 5)
   - [ ] Add database indexes for common queries
   - [ ] Batch metrics computation for efficiency
   - [ ] Test with 10,000+ executions
   - [ ] Ensure queries complete in <5s

**Success Criteria:**
- ✅ Metrics computed for all variants
- ✅ Statistical comparison produces valid p-values
- ✅ Token efficiency trends visible
- ✅ Dashboard queries return results in <5s
- ✅ Scheduled job runs successfully

**Deliverables:**
```
{{CATALYST_ROOT}}/
├── global/rag/service/prompt_optimizer/
│   └── metrics.py
├── metrics/queries/
│   └── variant_metrics.sql
└── scripts/
    └── compute_variant_metrics.py
```

---

### Phase 4: Auto-Graduation (Week 4)

**Objective:** Automatically promote winning variants

**Tasks:**

1. **Graduation Criteria Detection** (Day 1-2)
   - [ ] Create `graduation.py` with `VariantGraduationPipeline` class
   - [ ] Implement `find_graduation_candidates()`:
     - [ ] Sample size >= 30
     - [ ] Confidence >= 95%
     - [ ] Improvement >= 5% over current default
     - [ ] Quality score >= 0.7 average
   - [ ] Test candidate detection logic

2. **Statistical Validation** (Day 2-3)
   - [ ] Implement statistical significance tests
   - [ ] Use t-test for success rate comparison
   - [ ] Use bootstrap confidence intervals
   - [ ] Require p < 0.05 for graduation
   - [ ] Add safety checks (min sample size, max age)

3. **Promotion Mechanism** (Day 3)
   - [ ] Implement `graduate_variant()`:
     - [ ] Update is_default flag on new variant
     - [ ] Unset is_default on previous default
     - [ ] Insert record into variant_winners table
     - [ ] Log promotion event
   - [ ] Add rollback mechanism if needed

4. **Automated Graduation Cycle** (Day 3-4)
   - [ ] Implement `run_graduation_cycle()` - full end-to-end cycle
   - [ ] Add to scheduled job (runs daily)
   - [ ] Generate summary report of graduations
   - [ ] Send notifications (log to monitoring system)

5. **Safety Mechanisms** (Day 4-5)
   - [ ] Add cooldown period (7 days between graduations for same context)
   - [ ] Add regression detection (if new default performs worse, rollback)
   - [ ] Add manual override capability
   - [ ] Test edge cases: ties, insufficient data, all variants poor

6. **Integration Tests** (Day 5)
   - [ ] End-to-end test: generate sample data → detect candidate → graduate
   - [ ] Test with multiple competing variants
   - [ ] Test rollback mechanism
   - [ ] Test notification system

**Success Criteria:**
- ✅ Candidates detected with correct criteria
- ✅ Statistical tests produce valid results
- ✅ Graduation updates database correctly
- ✅ Notifications sent on promotion
- ✅ Rollback mechanism works

**Deliverables:**
```
{{CATALYST_ROOT}}/
├── global/rag/service/prompt_optimizer/
│   └── graduation.py
└── scripts/
    └── run_graduation_cycle.py (daily cron job)
```

---

### Phase 5: Agent Memory Integration (Week 5)

**Objective:** Store successful patterns as reusable knowledge

**Tasks:**

1. **Learning Loop Extension** (Day 1-2)
   - [ ] Modify `{{CATALYST_ROOT}}/global/rag/service/memory/learning_loops.py`
   - [ ] Add `extract_prompt_patterns()` method
   - [ ] Extract characteristics from graduated variants
   - [ ] Generate pattern suggestions
   - [ ] Test pattern extraction

2. **Pattern Storage** (Day 2-3)
   - [ ] After graduation, store as `SystemPattern` in Agent Memory
   - [ ] Include variant content as implementation_guide
   - [ ] Set success_rate and usage_count from metrics
   - [ ] Tag with task_type, depth_level, agent_name
   - [ ] Test pattern retrieval

3. **Anti-Pattern Detection** (Day 3)
   - [ ] Detect consistently underperforming variants
   - [ ] Store as error memories in Agent Memory
   - [ ] Tag as anti-patterns
   - [ ] Deactivate poor variants after 100 trials with <50% success
   - [ ] Test anti-pattern storage

4. **Cross-Agent Pattern Sharing** (Day 4)
   - [ ] When variant succeeds for Agent A, suggest testing for Agent B
   - [ ] Query Agent Memory for similar task patterns
   - [ ] Generate variant suggestions based on similarity
   - [ ] Test pattern suggestion algorithm

5. **Full Learning Cycle** (Day 4-5)
   - [ ] Implement `run_optimization_learning_cycle()` function
   - [ ] Integrate pattern extraction + graduation + memory storage
   - [ ] Add to scheduled jobs (runs weekly)
   - [ ] Generate comprehensive learning report

6. **End-to-End Validation** (Day 5)
   - [ ] Full cycle test: execution → metrics → graduation → pattern storage → retrieval
   - [ ] Test with multiple agents and task types
   - [ ] Verify patterns are reusable
   - [ ] Performance test: full cycle should complete in <30s

**Success Criteria:**
- ✅ Graduated variants stored as patterns
- ✅ Patterns retrievable for similar tasks
- ✅ Anti-patterns prevent regression
- ✅ Cross-agent pattern sharing works
- ✅ Full learning cycle runs successfully

**Deliverables:**
```
{{CATALYST_ROOT}}/
├── global/rag/service/memory/
│   └── learning_loops.py (extended)
└── scripts/
    └── run_optimization_learning_cycle.py (weekly cron job)
```

---

## Post-Implementation Checklist

### Monitoring & Observability
- [ ] Add variant selection metrics to Grafana dashboards
- [ ] Create alerts for low sample sizes (fewer than 10 executions per week)
- [ ] Create alerts for graduation events
- [ ] Add variant performance trends to weekly reports

### Documentation
- [ ] Update `{{CATALYST_ROOT}}/README.md` with prompt optimization section
- [ ] Create user guide: how to create and test new variants
- [ ] Document variant naming conventions
- [ ] Create troubleshooting guide

### Testing
- [ ] Unit test coverage: >80% for all modules
- [ ] Integration test coverage: all key workflows
- [ ] Load test: 10,000+ executions per day
- [ ] Regression test: verify graduations don't break existing functionality

### Deployment
- [ ] Create backup of quality.db before migration
- [ ] Run migration in staging environment first
- [ ] Monitor for 48 hours after production deployment
- [ ] Have rollback plan ready

---

## Resource Requirements

### Development Time
- **System Architect**: 5 days (design + review)
- **Backend Developer**: 20 days (implementation)
- **Code Reviewer**: 5 days (review cycles)
- **Validator**: 3 days (testing)

**Total**: ~33 developer-days over 5 weeks

### Infrastructure
- **Database**: Existing quality.db (no new infrastructure)
- **Compute**: Negligible (scheduled jobs run in seconds)
- **Storage**: <10 MB additional database storage

### Dependencies
- Python packages: `scipy` (for statistical tests) - already installed
- No new external services required

---

## Risk Assessment & Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Low sample sizes prevent graduation | High | Medium | Set exploration rate to 10%, run for 2+ weeks before expecting graduations |
| Variant explosion (too many variants) | Medium | Low | Cap active variants per context at 5, auto-archive low performers |
| Statistical tests produce false positives | Low | High | Use conservative thresholds (95% confidence, 30+ samples) |
| RLM integration breaks existing functionality | Low | High | Extensive integration testing, feature flag for gradual rollout |
| Database migration fails | Low | High | Test migration in staging, have rollback script ready |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scheduled jobs fail silently | Medium | Medium | Add monitoring, send alerts on failure |
| Graduations happen too frequently | Low | Medium | Cooldown period (7 days), manual override capability |
| Poor variant graduates due to noise | Low | High | Require sustained performance (7-day window), statistical validation |
| Users confused by variant system | Medium | Low | Good documentation, transparent logging of variant usage |

---

## Success Criteria (System-Wide)

### After 30 Days
- [ ] 50+ variant executions logged
- [ ] Metrics computed for all active variants
- [ ] At least 2 variants per major agent/task combination
- [ ] Exploration rate maintains 10% (±2%)

### After 60 Days
- [ ] 500+ variant executions logged
- [ ] First successful graduation (variant promoted to default)
- [ ] Measurable quality improvement (5%+ in at least one context)
- [ ] Token efficiency improvement (10%+ in at least one context)

### After 90 Days
- [ ] 2000+ variant executions logged
- [ ] 3-5 graduations completed
- [ ] System-wide quality score improvement (5%+)
- [ ] Token efficiency improvement (15%+)
- [ ] Cross-agent pattern sharing active

---

## Next Steps

1. **Review** this roadmap with {{ORCHESTRATOR_NAME}} and BOSS
2. **Validate** database schema with sample queries
3. **Prototype** Phase 1 (Foundation) in 1 week
4. **Iterate** based on prototype learnings
5. **Deploy** incrementally (Phase 1 → Phase 2 → etc.)

---

**End of Implementation Roadmap**

<tts-summary>🎙️ Created a detailed 5-week implementation roadmap for the prompt variant optimization system, breaking down into Foundation, RLM Integration, Metrics, Auto-Graduation, and Agent Memory phases with clear deliverables and success criteria.</tts-summary>

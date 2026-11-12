-- Prompt Variant Optimization System - Database Migration
-- Target: {{CATALYST_ROOT}}/metrics/quality.db
-- Run with: sqlite3 {{CATALYST_ROOT}}/metrics/quality.db < migrations/add_prompt_variants.sql

-- IMPORTANT: Create backup before running
-- cp {{CATALYST_ROOT}}/metrics/quality.db {{CATALYST_ROOT}}/metrics/quality.db.backup-$(date +%Y%m%d)

BEGIN TRANSACTION;

-- ============================================================================
-- TABLE: prompt_variants
-- Purpose: Store variant definitions and metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS prompt_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_name TEXT UNIQUE NOT NULL,
    agent_name TEXT,              -- NULL for system-wide variants
    depth_level INTEGER,          -- NULL for non-RLM variants, 0=root, 1-3=recursive
    variant_type TEXT NOT NULL,   -- 'system_prompt', 'instructions', 'examples', 'hybrid'
    variant_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    notes TEXT,

    -- Constraints
    CHECK (variant_type IN ('system_prompt', 'instructions', 'examples', 'hybrid')),
    CHECK (depth_level IS NULL OR (depth_level >= 0 AND depth_level <= 3)),
    CHECK (is_active IN (0, 1)),
    CHECK (is_default IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_variants_agent_depth
ON prompt_variants(agent_name, depth_level);

CREATE INDEX IF NOT EXISTS idx_variants_active
ON prompt_variants(is_active);

CREATE INDEX IF NOT EXISTS idx_variants_default
ON prompt_variants(is_default);

-- ============================================================================
-- TABLE: variant_executions
-- Purpose: Track individual variant executions and outcomes
-- ============================================================================

CREATE TABLE IF NOT EXISTS variant_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    task_type TEXT NOT NULL,      -- 'code_generation', 'debugging', 'research', etc.
    depth_level INTEGER,           -- NULL for non-RLM tasks
    complexity_score REAL,         -- 0.0-1.0, from task classifier
    context_tokens INTEGER,
    response_tokens INTEGER,
    success BOOLEAN,               -- Did task complete successfully?
    quality_score REAL,            -- From code review or validation (0.0-1.0)
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_id INTEGER,             -- FK to reviews table

    -- Constraints
    CHECK (task_type IN (
        'code_generation', 'debugging', 'research', 'architecture',
        'code_review', 'testing', 'deployment', 'documentation'
    )),
    CHECK (complexity_score IS NULL OR (complexity_score >= 0.0 AND complexity_score <= 1.0)),
    CHECK (quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)),
    CHECK (success IN (0, 1)),

    FOREIGN KEY (variant_id) REFERENCES prompt_variants(id) ON DELETE CASCADE,
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_variant_execs_variant
ON variant_executions(variant_id);

CREATE INDEX IF NOT EXISTS idx_variant_execs_agent_task
ON variant_executions(agent_name, task_type);

CREATE INDEX IF NOT EXISTS idx_variant_execs_success
ON variant_executions(success);

CREATE INDEX IF NOT EXISTS idx_variant_execs_created
ON variant_executions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_variant_execs_quality
ON variant_executions(quality_score DESC);

-- ============================================================================
-- TABLE: variant_metrics
-- Purpose: Aggregated metrics computed periodically (daily/weekly)
-- ============================================================================

CREATE TABLE IF NOT EXISTS variant_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    agent_name TEXT,
    task_type TEXT,
    depth_level INTEGER,
    window_start DATE NOT NULL,   -- Metrics computed for this time window
    window_end DATE NOT NULL,
    total_executions INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    success_rate REAL,            -- success_count / total_executions
    avg_quality_score REAL,
    avg_tokens_used INTEGER,      -- (context_tokens + response_tokens) / total_executions
    avg_duration_ms INTEGER,
    token_efficiency REAL,        -- avg_quality_score / (avg_tokens_used / 1000)
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CHECK (success_rate IS NULL OR (success_rate >= 0.0 AND success_rate <= 1.0)),
    CHECK (total_executions >= 0),
    CHECK (success_count >= 0 AND success_count <= total_executions),

    FOREIGN KEY (variant_id) REFERENCES prompt_variants(id) ON DELETE CASCADE,
    UNIQUE(variant_id, agent_name, task_type, window_start)
);

CREATE INDEX IF NOT EXISTS idx_variant_metrics_variant
ON variant_metrics(variant_id);

CREATE INDEX IF NOT EXISTS idx_variant_metrics_success_rate
ON variant_metrics(success_rate DESC);

CREATE INDEX IF NOT EXISTS idx_variant_metrics_token_efficiency
ON variant_metrics(token_efficiency DESC);

CREATE INDEX IF NOT EXISTS idx_variant_metrics_computed
ON variant_metrics(computed_at DESC);

-- ============================================================================
-- TABLE: variant_winners
-- Purpose: Track graduated variants (promoted to default)
-- ============================================================================

CREATE TABLE IF NOT EXISTS variant_winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    agent_name TEXT,
    task_type TEXT,
    depth_level INTEGER,
    superseded_variant_id INTEGER, -- Previous default variant
    promotion_reason TEXT NOT NULL,
    confidence_score REAL NOT NULL, -- Statistical confidence (0.0-1.0)
    sample_size INTEGER NOT NULL,   -- Number of executions used for decision
    performance_delta REAL,         -- Improvement over previous default (e.g., 0.12 = 12% better)
    promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    promoted_by TEXT DEFAULT 'auto', -- 'auto' or user identifier

    -- Constraints
    CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CHECK (sample_size > 0),

    FOREIGN KEY (variant_id) REFERENCES prompt_variants(id) ON DELETE CASCADE,
    FOREIGN KEY (superseded_variant_id) REFERENCES prompt_variants(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_variant_winners_promoted
ON variant_winners(promoted_at DESC);

CREATE INDEX IF NOT EXISTS idx_variant_winners_variant
ON variant_winners(variant_id);

-- ============================================================================
-- SEED DATA: Baseline Variants
-- Purpose: Initialize system with baseline variants for each RLM depth level
-- ============================================================================

INSERT OR IGNORE INTO prompt_variants (variant_name, agent_name, depth_level, variant_type, variant_content, is_default, notes)
VALUES
  -- Root level (depth=0) - orchestration variants
  ('baseline-root-orchestrator', NULL, 0, 'system_prompt',
   'You are an orchestration agent. Break down complex tasks into smaller sub-queries. Use llm() for recursive calls. Focus on task decomposition and coordination.',
   1, 'Default root orchestration prompt for RLM'),

  ('root-decomposer-v1', NULL, 0, 'instructions',
   'Emphasize breaking down complex tasks into minimal viable sub-tasks. Prefer fewer, higher-quality recursive calls over many shallow calls. Validate decomposition before executing.',
   0, 'Experimental: aggressive decomposition'),

  ('root-efficient-v1', NULL, 0, 'instructions',
   'Minimize recursion depth. Attempt to solve tasks directly when possible. Only spawn sub-queries for genuinely complex sub-problems. Optimize for token efficiency.',
   0, 'Experimental: minimize recursion'),

  -- Recursive level (depth=1) - focused task execution
  ('baseline-recursive-focused', NULL, 1, 'system_prompt',
   'You are a focused task executor. Complete the specific task assigned. Use tools appropriately. Stay on-task and avoid unnecessary exploration.',
   1, 'Default recursive prompt for RLM'),

  ('recursive-tool-heavy-v1', NULL, 1, 'instructions',
   'Aggressively use tools (bash, read, grep) to gather information before responding. Prefer tool-based evidence over assumptions. Verify before answering.',
   0, 'Experimental: heavy tool usage'),

  ('recursive-read-only-v1', NULL, 1, 'instructions',
   'Use read-only tools only (read, grep, search). No write operations. Focus on information gathering and analysis. Return comprehensive findings.',
   0, 'Experimental: read-only constraint'),

  -- Deep level (depth=2-3) - precision and minimal context
  ('baseline-deep-precise', NULL, 2, 'system_prompt',
   'You are a precision specialist. Provide direct, minimal answers. No recursion. No unnecessary elaboration. Answer exactly what is asked.',
   1, 'Default deep precision prompt for RLM'),

  ('deep-minimal-v1', NULL, 2, 'instructions',
   'Minimize token usage. Use shortest possible responses while maintaining accuracy. No explanations unless explicitly requested. Direct answers only.',
   0, 'Experimental: extreme token efficiency'),

  ('deep-verify-v1', NULL, 2, 'instructions',
   'Before responding, verify your answer internally. Use self-questioning: "Is this correct? Is there a simpler answer? Did I miss anything?" Then respond concisely.',
   0, 'Experimental: self-verification');

-- ============================================================================
-- VIEWS: Convenience views for common queries
-- ============================================================================

-- View: Variant performance summary
CREATE VIEW IF NOT EXISTS variant_performance_summary AS
SELECT
    pv.id,
    pv.variant_name,
    pv.agent_name,
    pv.depth_level,
    pv.is_default,
    COUNT(ve.id) as total_executions,
    SUM(CASE WHEN ve.success = 1 THEN 1 ELSE 0 END) as success_count,
    ROUND(AVG(CASE WHEN ve.success = 1 THEN 1.0 ELSE 0.0 END), 3) as success_rate,
    ROUND(AVG(ve.quality_score), 3) as avg_quality,
    ROUND(AVG(ve.context_tokens + ve.response_tokens), 0) as avg_tokens,
    ROUND(AVG(ve.quality_score) / (AVG(ve.context_tokens + ve.response_tokens) / 1000.0), 3) as token_efficiency
FROM prompt_variants pv
LEFT JOIN variant_executions ve ON pv.id = ve.variant_id
GROUP BY pv.id;

-- View: Recent graduations
CREATE VIEW IF NOT EXISTS recent_graduations AS
SELECT
    vw.promoted_at,
    pv.variant_name,
    vw.agent_name,
    vw.task_type,
    vw.promotion_reason,
    vw.confidence_score,
    vw.sample_size,
    ROUND(vw.performance_delta * 100, 1) as improvement_pct
FROM variant_winners vw
JOIN prompt_variants pv ON vw.variant_id = pv.id
ORDER BY vw.promoted_at DESC;

-- View: Variants needing more data
CREATE VIEW IF NOT EXISTS variants_needing_data AS
SELECT
    pv.variant_name,
    pv.agent_name,
    pv.task_type,
    COUNT(ve.id) as execution_count,
    30 - COUNT(ve.id) as executions_needed
FROM prompt_variants pv
LEFT JOIN variant_executions ve ON pv.id = ve.variant_id
WHERE pv.is_active = 1
GROUP BY pv.id
HAVING COUNT(ve.id) < 30
ORDER BY execution_count ASC;

-- ============================================================================
-- HELPER FUNCTIONS (stored as metadata for query reference)
-- ============================================================================

-- Note: SQLite doesn't support stored procedures, but these are common queries
-- that can be referenced in application code

-- Example: Get best variant for context
-- SELECT * FROM variant_performance_summary
-- WHERE agent_name = '🏛️ Backend Developer'
--   AND task_type = 'code_generation'
-- ORDER BY token_efficiency DESC
-- LIMIT 1;

-- Example: Compare two variants
-- SELECT
--     v1.variant_name as variant_a,
--     v2.variant_name as variant_b,
--     v1.success_rate as success_rate_a,
--     v2.success_rate as success_rate_b,
--     v1.token_efficiency as efficiency_a,
--     v2.token_efficiency as efficiency_b,
--     ROUND((v1.success_rate - v2.success_rate) * 100, 1) as success_delta_pct
-- FROM variant_performance_summary v1, variant_performance_summary v2
-- WHERE v1.id = ? AND v2.id = ?;

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- Run after migration to verify success
-- ============================================================================

-- Check tables created
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'variant%';
-- Expected: variant_executions, variant_metrics, variant_winners, prompt_variants

-- Check seed data
SELECT variant_name, depth_level, is_default FROM prompt_variants ORDER BY depth_level;
-- Expected: 9 variants (3 per depth level)

-- Check views created
SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'variant%';
-- Expected: variant_performance_summary, recent_graduations, variants_needing_data

-- Check indexes created
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_variant%';
-- Expected: 13 indexes

-- ============================================================================
-- ROLLBACK SCRIPT (in case of issues)
-- Save this separately as rollback_prompt_variants.sql
-- ============================================================================

-- BEGIN TRANSACTION;
-- DROP VIEW IF EXISTS variants_needing_data;
-- DROP VIEW IF EXISTS recent_graduations;
-- DROP VIEW IF EXISTS variant_performance_summary;
-- DROP TABLE IF EXISTS variant_winners;
-- DROP TABLE IF EXISTS variant_metrics;
-- DROP TABLE IF EXISTS variant_executions;
-- DROP TABLE IF EXISTS prompt_variants;
-- COMMIT;

-- End of migration script

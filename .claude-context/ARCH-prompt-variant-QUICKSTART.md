# Prompt Variant Optimization - Quick Start Guide

**For:** Backend Developer (Implementation Lead)
**Date:** 2026-01-19
**Estimated Time:** Week 1 (Phase 1)

---

## Day 1: Database Setup

### Step 1: Backup Current Database

```bash
# Create timestamped backup
cp {{CATALYST_ROOT}}/metrics/quality.db \
   {{CATALYST_ROOT}}/metrics/quality.db.backup-$(date +%Y%m%d-%H%M%S)

# Verify backup
ls -lh {{CATALYST_ROOT}}/metrics/quality.db.backup-*
```

### Step 2: Run Migration Script

```bash
# Create migrations directory
mkdir -p {{CATALYST_ROOT}}/metrics/migrations

# Copy migration script
cp {{CATALYST_ROOT}}/.claude-context/SAMPLE-prompt-variant-migration.sql \
   {{CATALYST_ROOT}}/metrics/migrations/add_prompt_variants.sql

# Run migration
sqlite3 {{CATALYST_ROOT}}/metrics/quality.db < \
   {{CATALYST_ROOT}}/metrics/migrations/add_prompt_variants.sql

# Verify tables created
sqlite3 {{CATALYST_ROOT}}/metrics/quality.db \
  "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'variant%';"
```

**Expected Output:**
```
prompt_variants
variant_executions
variant_metrics
variant_winners
```

### Step 3: Verify Seed Data

```bash
sqlite3 {{CATALYST_ROOT}}/metrics/quality.db \
  "SELECT variant_name, depth_level, is_default FROM prompt_variants ORDER BY depth_level;"
```

**Expected Output:**
```
baseline-root-orchestrator|0|1
root-decomposer-v1|0|0
root-efficient-v1|0|0
baseline-recursive-focused|1|1
recursive-tool-heavy-v1|1|0
recursive-read-only-v1|1|0
baseline-deep-precise|2|1
deep-minimal-v1|2|0
deep-verify-v1|2|0
```

---

## Day 2: Core Models Setup

### Step 1: Create Module Structure

```bash
# Create prompt_optimizer module
mkdir -p {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer
cd {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer

# Create files
touch __init__.py models.py registry.py tracker.py metrics.py graduation.py optimizer.py
```

### Step 2: Implement models.py

**File:** `{{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/models.py`

```python
"""
Prompt Variant Optimization - Data Models

Core data structures for variant management.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from datetime import datetime


class VariantType(Enum):
    """Type of prompt variant."""
    SYSTEM_PROMPT = "system_prompt"
    INSTRUCTIONS = "instructions"
    EXAMPLES = "examples"
    HYBRID = "hybrid"


class TaskType(Enum):
    """Type of task being executed."""
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    RESEARCH = "research"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"


@dataclass
class PromptVariant:
    """
    Definition of a prompt variant.

    Attributes:
        id: Database ID (None for new variants)
        variant_name: Unique identifier
        agent_name: Target agent (None for system-wide)
        depth_level: RLM depth (None for non-RLM, 0=root, 1-3=recursive)
        variant_type: Type of variant
        variant_content: Actual prompt content
        is_active: Whether variant is active
        is_default: Whether variant is current default
        notes: Optional notes
    """
    variant_name: str
    variant_type: VariantType
    variant_content: str
    id: Optional[int] = None
    agent_name: Optional[str] = None
    depth_level: Optional[int] = None
    is_active: bool = True
    is_default: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class VariantExecution:
    """
    Tracks a single execution of a variant.

    Attributes:
        variant_id: ID of variant used
        agent_name: Agent that executed task
        task_type: Type of task
        depth_level: RLM depth (if applicable)
        complexity_score: Task complexity (0.0-1.0)
        context_tokens: Input tokens
        response_tokens: Output tokens
        success: Whether task succeeded
        quality_score: Quality from code review (0.0-1.0)
        duration_ms: Execution time
        review_id: Link to code review
    """
    variant_id: int
    agent_name: str
    task_type: TaskType
    context_tokens: int
    response_tokens: int
    success: bool
    duration_ms: int
    id: Optional[int] = None
    depth_level: Optional[int] = None
    complexity_score: Optional[float] = None
    quality_score: Optional[float] = None
    review_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class VariantMetrics:
    """
    Aggregated metrics for a variant.

    Attributes:
        variant_id: ID of variant
        success_rate: Proportion of successful executions
        avg_quality_score: Average quality score
        avg_tokens_used: Average total tokens
        token_efficiency: quality_score / (tokens / 1000)
        sample_size: Number of executions
    """
    variant_id: int
    success_rate: float
    avg_quality_score: float
    avg_tokens_used: int
    token_efficiency: float
    sample_size: int


@dataclass
class TaskComplexityScore:
    """
    Complexity classification for a task.

    Attributes:
        complexity_score: 0.0-1.0 (0=simple, 1=complex)
        task_type: Detected task type
        confidence: Confidence in classification
        factors: Factors contributing to complexity
    """
    complexity_score: float
    task_type: TaskType
    confidence: float
    factors: List[str]
```

### Step 3: Write Unit Tests

**File:** `{{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/tests/test_models.py`

```python
"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
from ..models import (
    PromptVariant, VariantExecution, VariantMetrics,
    VariantType, TaskType
)


def test_prompt_variant_creation():
    """Test creating a PromptVariant."""
    variant = PromptVariant(
        variant_name="test-variant",
        variant_type=VariantType.INSTRUCTIONS,
        variant_content="Test prompt content",
        agent_name="🏛️ Backend Developer"
    )

    assert variant.variant_name == "test-variant"
    assert variant.is_active is True
    assert variant.is_default is False


def test_variant_execution_creation():
    """Test creating a VariantExecution."""
    execution = VariantExecution(
        variant_id=1,
        agent_name="🏛️ Backend Developer",
        task_type=TaskType.CODE_GENERATION,
        context_tokens=12000,
        response_tokens=3000,
        success=True,
        duration_ms=8000,
        quality_score=0.85
    )

    assert execution.variant_id == 1
    assert execution.success is True
    assert execution.quality_score == 0.85


def test_variant_metrics_creation():
    """Test creating VariantMetrics."""
    metrics = VariantMetrics(
        variant_id=1,
        success_rate=0.89,
        avg_quality_score=0.85,
        avg_tokens_used=15000,
        token_efficiency=0.76,
        sample_size=47
    )

    assert metrics.success_rate == 0.89
    assert metrics.sample_size == 47


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Day 3: Implement Registry

### File Structure

```python
# {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/registry.py

"""
Variant Registry - Manages variant definitions and selection.
"""

import sqlite3
import random
from typing import Optional, List
from .models import PromptVariant, VariantType, TaskType


class VariantRegistry:
    """
    Manages prompt variant definitions and selection.

    Responsibilities:
    - Store and retrieve variant definitions
    - Select variant based on task characteristics
    - Track which variant is default for each context
    """

    def __init__(self, db_path: str = "{{CATALYST_ROOT}}/metrics/quality.db"):
        """
        Initialize registry.

        Args:
            db_path: Path to quality.db
        """
        self.db_path = db_path

    def register_variant(self, variant: PromptVariant) -> int:
        """
        Register a new prompt variant.

        Args:
            variant: PromptVariant to register

        Returns:
            Variant ID

        Raises:
            ValueError: If variant_name already exists
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO prompt_variants (
                    variant_name, agent_name, depth_level, variant_type,
                    variant_content, is_active, is_default, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                variant.variant_name,
                variant.agent_name,
                variant.depth_level,
                variant.variant_type.value,
                variant.variant_content,
                1 if variant.is_active else 0,
                1 if variant.is_default else 0,
                variant.notes
            ))

            variant_id = cursor.lastrowid
            conn.commit()
            return variant_id

        except sqlite3.IntegrityError:
            raise ValueError(f"Variant '{variant.variant_name}' already exists")
        finally:
            conn.close()

    def get_variant(self, variant_id: int) -> Optional[PromptVariant]:
        """
        Retrieve variant by ID.

        Args:
            variant_id: Variant ID

        Returns:
            PromptVariant or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, variant_name, agent_name, depth_level, variant_type,
                   variant_content, is_active, is_default, notes, created_at
            FROM prompt_variants
            WHERE id = ?
        """, (variant_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return PromptVariant(
            id=row[0],
            variant_name=row[1],
            agent_name=row[2],
            depth_level=row[3],
            variant_type=VariantType(row[4]),
            variant_content=row[5],
            is_active=bool(row[6]),
            is_default=bool(row[7]),
            notes=row[8]
        )

    def select_variant(
        self,
        agent_name: str,
        task_type: TaskType,
        depth_level: Optional[int] = None,
        exploration_rate: float = 0.1
    ) -> PromptVariant:
        """
        Select best variant using epsilon-greedy strategy.

        Args:
            agent_name: Agent name
            task_type: Task type
            depth_level: RLM depth (if applicable)
            exploration_rate: Probability of random selection (default 0.1)

        Returns:
            Selected PromptVariant
        """
        # Get all active variants for this context
        variants = self._get_active_variants(agent_name, task_type, depth_level)

        if not variants:
            # Fallback to system-wide default
            return self.get_default_variant(None, task_type, depth_level)

        # Epsilon-greedy selection
        if random.random() < exploration_rate:
            # Explore: random selection
            return random.choice(variants)
        else:
            # Exploit: select default (best performer)
            default = next((v for v in variants if v.is_default), None)
            return default if default else variants[0]

    def _get_active_variants(
        self,
        agent_name: str,
        task_type: TaskType,
        depth_level: Optional[int]
    ) -> List[PromptVariant]:
        """Get all active variants matching context."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, variant_name, agent_name, depth_level, variant_type,
                   variant_content, is_active, is_default, notes
            FROM prompt_variants
            WHERE is_active = 1
              AND (agent_name = ? OR agent_name IS NULL)
              AND (depth_level = ? OR depth_level IS NULL)
        """, (agent_name, depth_level))

        rows = cursor.fetchall()
        conn.close()

        return [
            PromptVariant(
                id=row[0],
                variant_name=row[1],
                agent_name=row[2],
                depth_level=row[3],
                variant_type=VariantType(row[4]),
                variant_content=row[5],
                is_active=bool(row[6]),
                is_default=bool(row[7]),
                notes=row[8]
            )
            for row in rows
        ]

    # Additional methods: get_default_variant, set_default_variant
    # (Full implementation in actual code)
```

---

## Day 4-5: Testing & Validation

### Integration Test Script

```python
# {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/tests/test_integration.py

"""
Integration tests for variant system.
"""

import pytest
import sqlite3
from ..registry import VariantRegistry
from ..models import PromptVariant, VariantType, TaskType


def test_end_to_end_flow():
    """Test complete flow: register → select → retrieve."""

    registry = VariantRegistry()

    # 1. Register a new variant
    variant = PromptVariant(
        variant_name="test-backend-focused",
        agent_name="🏛️ Backend Developer",
        variant_type=VariantType.INSTRUCTIONS,
        variant_content="Test prompt: Focus on type hints and error handling.",
        is_active=True,
        is_default=False
    )

    variant_id = registry.register_variant(variant)
    assert variant_id > 0

    # 2. Retrieve the variant
    retrieved = registry.get_variant(variant_id)
    assert retrieved is not None
    assert retrieved.variant_name == "test-backend-focused"

    # 3. Select a variant (should get default)
    selected = registry.select_variant(
        agent_name="🏛️ Backend Developer",
        task_type=TaskType.CODE_GENERATION,
        exploration_rate=0.0  # No exploration for deterministic test
    )

    assert selected is not None

    print(f"✅ Integration test passed!")
    print(f"   Registered variant ID: {variant_id}")
    print(f"   Retrieved variant: {retrieved.variant_name}")
    print(f"   Selected variant: {selected.variant_name}")


if __name__ == "__main__":
    test_end_to_end_flow()
```

### Run Tests

```bash
cd {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer

# Run unit tests
python -m pytest tests/test_models.py -v

# Run integration tests
python tests/test_integration.py
```

---

## Validation Checklist

After Day 5, verify:

- [ ] Database schema created (4 tables)
- [ ] Seed data present (9 baseline variants)
- [ ] Models module working (all tests pass)
- [ ] Registry module working (can register and retrieve)
- [ ] Variant selection working (epsilon-greedy functioning)
- [ ] Integration test passes end-to-end

**If all checked:** ✅ Phase 1 Complete! Proceed to Phase 2 (RLM Integration)

---

## Common Issues & Solutions

### Issue: Database locked

**Symptom:** `sqlite3.OperationalError: database is locked`

**Solution:**
```bash
# Check for processes holding lock
lsof {{CATALYST_ROOT}}/metrics/quality.db

# If needed, enable WAL mode for concurrent access
sqlite3 {{CATALYST_ROOT}}/metrics/quality.db "PRAGMA journal_mode=WAL;"
```

### Issue: Import errors

**Symptom:** `ModuleNotFoundError: No module named 'prompt_optimizer'`

**Solution:**
```bash
# Add __init__.py to package
touch {{CATALYST_ROOT}}/global/rag/service/prompt_optimizer/__init__.py

# Verify PYTHONPATH
export PYTHONPATH="{{CATALYST_ROOT}}:$PYTHONPATH"
```

### Issue: Foreign key constraint violation

**Symptom:** `FOREIGN KEY constraint failed`

**Solution:**
```bash
# Verify reviews table exists
sqlite3 {{CATALYST_ROOT}}/metrics/quality.db "SELECT COUNT(*) FROM reviews;"

# If needed, create test review first
sqlite3 {{CATALYST_ROOT}}/metrics/quality.db \
  "INSERT INTO reviews (timestamp, capsule, files_changed, severity, blocked) \
   VALUES (datetime('now'), 'test', 0, 'info', 0);"
```

---

## Next Steps (Week 2: Phase 2)

After Phase 1 completes:

1. **Implement Execution Tracker** (`tracker.py`)
2. **Integrate with RLM Orchestrator** (modify `orchestrator.py`)
3. **Add Task Complexity Classifier**
4. **Test depth-level variant selection**
5. **Capture token metrics from LLM responses**

**Reference:** See `ARCH-prompt-variant-implementation-roadmap.md` Phase 2 section

---

## Support & Questions

**Architecture Questions:** Ask System Architect (design decisions)
**Implementation Help:** Ask Backend Developer (code structure)
**Testing Issues:** Ask Validator (test strategy)
**Integration Issues:** Ask {{ORCHESTRATOR_NAME}} (coordination)

---

**End of Quick Start Guide**

<tts-summary>🎙️ Created quick-start implementation guide with day-by-day breakdown for Phase 1, including database setup, model implementation, registry code, testing scripts, and troubleshooting for common issues.</tts-summary>

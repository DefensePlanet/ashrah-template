# /remember - Store a Memory

Store information in the Agent Memory System for future retrieval.

## Usage

```
/remember <content to remember>
```

## Description

This command stores the provided content as a memory in BuilderOS's Agent Memory System. The memory will be:

1. **Validated** for quality (minimum content length, no duplicates)
2. **Embedded** using sentence-transformers for semantic search
3. **Stored** in both SQLite (structured) and ChromaDB (vector)
4. **Indexed** in FTS5 for hybrid BM25/vector search

## Examples

```
/remember The optimal chunk size for code embeddings is 50-200 lines for best context retention

/remember Anti-pattern: Never use wildcard imports in Python production code

/remember We decided to use Supabase RLS instead of application-level auth for the API

/remember Pattern: Always run migrations on a branch before merging to main
```

## Memory Types

Based on the content, the system automatically classifies memories:

- **semantic** - Facts and knowledge (default)
- **episodic** - Experiences and learnings
- **procedural** - Patterns and best practices

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| content | The information to store | Yes |

## Execution

When `/remember` is invoked:

1. Parse the user's content from the command arguments
2. Detect memory type from trigger phrases (if any)
3. Store via the Agent Memory MCP server or direct coordinator call
4. Confirm storage with memory ID

```python
# {{ORCHESTRATOR_NAME}} should execute this pattern:

import sys
sys.path.insert(0, '{{CATALYST_ROOT}}/global/rag/service')

from memory.coordinator import MemoryCoordinator
from memory_triggers import detect_triggers, TriggerType

content = "$ARGUMENTS"  # The user's content

# Detect if content has trigger phrases for type classification
triggers = detect_triggers(content, min_confidence=0.5)
memory_type = "semantic"  # default

if triggers:
    type_map = {
        TriggerType.PATTERN: "procedural",
        TriggerType.LEARNING: "episodic",
        TriggerType.ANTI_PATTERN: "semantic",
        TriggerType.DECISION: "semantic",
    }
    memory_type = type_map.get(triggers[0].trigger_type, "semantic")

# Store the memory
coordinator = MemoryCoordinator()
memory_id = coordinator.create_memory(
    agent_name="{{ORCHESTRATOR_NAME_LOWER}}",
    memory_type=memory_type,
    content=content,
    impact_score=0.7,
    tags=["manual", "remember-command"],
)

print(f"Memory stored with ID: {memory_id}")
print(f"Type: {memory_type}")
print(f"Content: {content[:100]}...")
```

## Notes

- Memories are attributed to "{{ORCHESTRATOR_NAME_LOWER}}" agent by default
- Use specific trigger phrases for better classification:
  - "Pattern:" or "Best practice:" → procedural
  - "I learned" or "TIL" → episodic
  - "Anti-pattern:" or "Don't do" → semantic (anti-pattern tagged)
  - "We decided" or "Decision:" → semantic (decision tagged)
- Memories can be searched later using semantic search in the Agent Memory System

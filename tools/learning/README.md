# Learning Tools

Scripts for Catalyst learning and continuous improvement systems.

## Scripts

| Script | Purpose |
|--------|---------|
| `auto_learner.py` | Automated learning from sessions |
| `install_learning_system.py` | Install/setup learning infrastructure |
| `{{ORCHESTRATOR_NAME_LOWER}}_learning_engine.py` | {{ORCHESTRATOR_NAME}}-specific learning engine |
| `learning_validator.py` | Validate learning system outputs |

## Related Locations

- **Core System**: `global/agent-loops/` (main learning infrastructure)
- **Feature Loop**: `tools/feature-loop/` (iterative feature development)
- **Databases**: `data/databases/active_learning.db`, `data/databases/learning_loops.db`
- **Logs**: `monitoring/learning-system.out`, `monitoring/learning-system.err`
- **Tests**: `testing/learning/`

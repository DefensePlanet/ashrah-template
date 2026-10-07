# Catalyst Tools Directory

**Purpose:** Centralized collection of tools that power the Catalyst's "build everything" mission.

## Quick Reference

### 🎯 **Most Used Tools**
- `{{ORCHESTRATOR_NAME_LOWER}}.py` - Main Builder interface and intelligent agent
- `bs.py` - Builder service utilities and CLI
- `things` - Things 3 CLI integration for task management
- `new-capsule.sh` - Create new project capsules
- `daily_audit.sh` - System health monitoring

### 🏗️ **Core Operations**
| Tool | Purpose | Usage |
|------|---------|-------|
| `{{ORCHESTRATOR_NAME_LOWER}}.py` | Intelligent Builder agent | `python {{ORCHESTRATOR_NAME_LOWER}}.py status` |
| `bs.py` | Builder service CLI | `python bs.py create capsule-name` |
| `intelligent_builder.py` | Core building logic | Imported by other tools |
| `capsule_pipeline_engine.py` | Capsule lifecycle | Imported by other tools |

### 📦 **Capsule Management**
| Tool | Purpose |
|------|---------|
| `new-capsule.sh` | Create new capsules from templates |
| `validate_capsules.sh` | Verify capsule integrity |
| `migrate_test_capsules.sh` | Move test capsules |
| `standardize_capsules.sh` | Apply consistent structure |

### 🔐 **Security & Secrets**
| Tool | Purpose |
|------|---------|
| `secretctl.py` | Secret management and rotation |
| `scan_secrets.sh` | Detect exposed secrets |
| `preflight_secrets.sh` | Pre-deployment security checks |
| `configure_rag_security.py` | RAG system security setup |

### 🧠 **Memory & Context**
| Tool | Purpose |
|------|---------|
| `memory_status.sh` | Check MCP memory health |
| `backup_memory.sh` | Export memory data |
| `clear_memory.sh` | Reset memory (kill-switch) |
| `setup_memory.sh` | Initialize memory system |

### 🔧 **System Maintenance**
| Tool | Purpose |
|------|---------|
| `daily_audit.sh` | Comprehensive health check |
| `fix_perms.sh` | Repair file permissions |
| `snapshot.sh` | Create system snapshots |
| `diagnose_builder.sh` | System diagnostics |

### 🧪 **Testing & Quality**
| Tool | Purpose |
|------|---------|
| `test_builder.sh` | Core system tests |
| `test_integration.sh` | Integration testing |
| `test_lane_features.sh` | Lane-specific tests |
| `test_system_integration.py` | Python test suite |

### 🔌 **MCP Integration**
| Tool | Purpose |
|------|---------|
| `mcp_audit.sh` | MCP server health check |
| `mcp_auto_configurator.py` | Auto-configure MCP servers |
| `consolidate_mcps.py` | Merge MCP configurations |
| `bridge-mcp/` | MCP bridge services |

### 📊 **Analytics & Monitoring**
| Tool | Purpose |
|------|---------|
| `metrics_rollup.py` | System metrics aggregation |
| `performance_analytics.py` | Performance monitoring |
| `cost_optimizer.py` | Resource optimization |
| `system_health_rollup.py` | Health metrics |

### 🚀 **Agent Framework**
| Tool | Purpose |
|------|---------|
| `agent_registry.py` | Agent discovery and routing |
| `agent_os_enforcer.py` | Agent OS compliance |
| `agent_test_framework.py` | Agent testing utilities |
| `unified_knowledge_graph.py` | Knowledge management |

### 📋 **Productivity & Task Management**
| Tool | Purpose | Usage |
|------|---------|-------|
| `things` | Things 3 CLI integration | `./tools/things focus` |
| `things3/` | Complete Things 3 integration | API + scripts |

## 📁 **Proposed Organization** 
*Future directory structure for improved discovery:*

```
/tools/
├── core/              # Essential Builder operations
│   ├── {{ORCHESTRATOR_NAME_LOWER}}.py
│   ├── bs.py
│   └── intelligent_builder.py
├── capsule/           # Capsule lifecycle management
│   ├── new-capsule.sh
│   ├── validate_capsules.sh
│   └── capsule_pipeline_engine.py
├── security/          # Security and secrets
│   ├── secretctl.py
│   ├── scan_secrets.sh
│   └── preflight_secrets.sh
├── maintenance/       # System health & cleanup  
│   ├── daily_audit.sh
│   ├── fix_perms.sh
│   └── snapshot.sh
├── testing/           # Test suites and QA
│   ├── test_builder.sh
│   ├── test_integration.sh
│   └── test_system_integration.py
├── integration/       # External system bridges
│   ├── mcp_audit.sh
│   ├── bridge-mcp/
│   └── n8n/
├── analytics/         # Monitoring and metrics
│   ├── metrics_rollup.py
│   ├── performance_analytics.py
│   └── cost_optimizer.py
├── agents/            # Agent framework
│   ├── agent_registry.py
│   ├── agent_os_enforcer.py
│   └── unified_knowledge_graph.py
├── productivity/      # Personal productivity tools
│   ├── things
│   └── things3/
└── common/            # Shared utilities
    ├── logger.py
    ├── builder_utils.py
    └── config_loader.py
```

## 🚦 **Usage Guidelines**

### **Before Running Any Tool:**
1. Ensure `BUILDER_ROOT` environment variable is set
2. Run from Builder root directory: `{{CATALYST_ROOT}}`
3. Check tool permissions: `chmod +x tool_name.sh`

### **Common Patterns:**
```bash
# Set environment
export BUILDER_ROOT="{{CATALYST_ROOT}}"
cd $BUILDER_ROOT

# Run core tools
python tools/{{ORCHESTRATOR_NAME_LOWER}}.py status
./tools/daily_audit.sh
./tools/new-capsule.sh my-project

# Task management & productivity
./tools/things focus          # Today's priorities
./tools/things daily-brief    # Morning summary
./tools/things catalyst       # Development tasks

# Check system health
./tools/memory/memory_status.sh
./tools/test_builder.sh
```

### **Tool Dependencies:**
- **Python tools**: Require Python 3.8+, may need `pip install -r requirements.txt`
- **Shell scripts**: Require bash, jq, and other standard Unix tools  
- **MCP tools**: Require active MCP server configuration

## 🔄 **Maintenance Notes**

### **Weekly Tasks:**
- Run `./tools/weekly_system_audit.sh`
- Clean up backup files with `find tools/ -name "*.backup" -delete`
- Review `tools/*.log` files for issues

### **Monthly Tasks:**
- Reorganize tools directory (planned improvement)
- Update documentation for new tools
- Archive obsolete tools

## 📝 **Contributing New Tools**

### **Naming Convention:**
- **Python scripts**: `tool_name.py` 
- **Shell scripts**: `tool_name.sh`
- **Executable**: Always set `chmod +x`

### **Required Headers:**
```python
#!/usr/bin/env python3
"""
Tool description and purpose
"""
from common.logger import setup_logging
logger = setup_logging("tool_name")
```

```bash
#!/bin/bash
# Tool description and purpose
set -e
source "$(dirname "$0")/load_config.sh"
```

### **Documentation:**
- Add tool to this README
- Include usage examples
- Document dependencies
- Add to appropriate category

---

*Last updated: $(date) - Auto-generated from Catalyst audit*
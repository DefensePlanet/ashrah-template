# iOS Shortcuts Pipeline - Catalyst

## Overview
Complete automation pipeline from Catalyst specifications to deployable iOS Shortcuts using Cherri language and Cursor IDE integration.

## Pipeline Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Capsule Spec   │───▶│   Generate       │───▶│   Cursor IDE    │
│ requirements.yaml│    │  .cherri Source  │    │   Validation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  macOS Import   │◀───│  Compile to      │◀───│   Cherri CLI    │
│ Shortcuts.app   │    │   .shortcut      │    │  Compilation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## IDE Integration Hierarchy

### 1. Primary IDE: Cursor IDE ✅
- **Extension**: Cherri language extension installed
- **Features**: 
  - Syntax highlighting for .cherri files
  - IntelliSense and autocompletion  
  - Real-time error checking and validation
  - Code formatting and linting
  - Direct compilation support
- **Integration**: Automatically opens generated .cherri files
- **Path**: `/Applications/Cursor.app`

### 2. Fallback IDE: Cherri IDE ✅  
- **Features**:
  - Native Cherri language support
  - Built-in compilation tools
  - Shortcut preview capabilities
- **Usage**: Used when Cursor IDE unavailable
- **Path**: `/Applications/Cherri.app`

### 3. System Default Editor
- **Usage**: Last resort when specialized IDEs unavailable
- **Limitation**: No syntax highlighting or validation

## Usage Examples

### 👤 Manual Development Mode (Human)
```bash
# Default: Cursor IDE for interactive development
python3 tools/generate_shortcuts.py /path/to/capsule

# Force Cherri IDE
python3 tools/generate_shortcuts.py /path/to/capsule cherri

# Terminal only (no IDE)
python3 tools/generate_shortcuts.py /path/to/capsule none
```

### 🤖 Agent Automation Mode  
```bash
# Agent mode: No IDE, minimal output, pure automation
python3 tools/generate_shortcuts.py /path/to/capsule --agent

# Also valid
python3 tools/generate_shortcuts.py /path/to/capsule none --agent
```

## Workflow Modes

### Manual Mode (Default)
- **Purpose**: Interactive development and refinement
- **IDE**: Opens generated .cherri files in Cursor IDE
- **Output**: Full verbose logging and status
- **Use Case**: Human developers creating/testing shortcuts

### Agent Mode (`--agent`)
- **Purpose**: Automated shortcut generation in workflows
- **IDE**: None - pure terminal operation
- **Output**: Minimal, structured logging
- **Use Case**: Catalyst automation agents

## Generated Files Structure

```
capsule/
├── spec/requirements.yaml          # Source specification
├── src/shortcuts/
│   ├── common.cherri              # Common Builder actions
│   └── generated/
│       └── ShortcutName.cherri    # Generated source
└── ops/shortcuts/
    └── ShortcutName.shortcut      # Compiled, signed shortcut
```

## Workflow Steps

1. **Spec Parsing**: Read `spec/requirements.yaml` shortcuts definitions
2. **Source Generation**: Create `.cherri` files with Catalyst patterns  
3. **IDE Opening**: Launch Cursor IDE for validation and editing
4. **Compilation**: Use Cherri CLI to compile to signed `.shortcut` files
5. **Auto-Import**: Open shortcuts in macOS Shortcuts app for installation

## Quality Assurance

- **Syntax Validation**: Cursor IDE Cherri extension catches errors pre-compilation
- **Builder Patterns**: Generated code follows Catalyst conventions
- **Signing**: All shortcuts are properly signed for iOS installation
- **Testing**: Complete test suite with sample shortcuts

## Benefits

✅ **Professional Development**: Full IDE support with syntax highlighting  
✅ **Error Prevention**: Real-time validation catches issues early  
✅ **Rapid Iteration**: IDE integration enables quick refinements  
✅ **Builder Integration**: Seamless workflow within Catalyst  
✅ **Quality Control**: Automated validation and signing  
✅ **Deployment Ready**: Direct import to Shortcuts app

This pipeline transforms the Catalyst into a complete iOS automation development environment.
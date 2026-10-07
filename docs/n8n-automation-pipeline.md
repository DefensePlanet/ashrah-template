# n8n Automation Pipeline - Catalyst

## Overview
The Catalyst provides comprehensive n8n workflow automation capabilities through specialized agents and the n8n-mcp server integration, enabling complete spec-to-workflow automation.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Capsule Spec   │───▶│   Generate       │───▶│   n8n-mcp       │
│ requirements.yaml│    │  Workflow JSON   │    │  Validation     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  n8n Instance   │◀───│  Deploy to       │◀───│   n8n-mcp       │
│   Execution     │    │   n8n Server     │    │   Deployment    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Agent Ecosystem

### 🤖 Automation Agent - n8n Workflow Specialist
**Primary Role**: n8n workflow creation and management
- **Workflow Planning**: Analyze requirements and design node-based workflows
- **JSON Generation**: Create complete n8n workflow configurations
- **MCP Integration**: Use n8n-mcp tools for deployment and management
- **Builder Patterns**: Implement Catalyst-specific automation patterns

### 🔍 Debugger Agent - n8n Workflow Troubleshooter  
**Primary Role**: n8n workflow debugging and optimization
- **Issue Investigation**: Root cause analysis of failing workflows
- **Performance Analysis**: Execution time and resource optimization
- **Validation**: Comprehensive workflow and node validation
- **Monitoring**: Health reporting and trend analysis

### 🏗️ System Architect Agent (Consulting)
**Supporting Role**: Large-scale n8n architecture decisions
- **Scalability Planning**: Multi-workflow system design
- **Integration Strategy**: Catalyst + n8n ecosystem planning
- **Best Practices**: Workflow architecture and patterns

## n8n-mcp Server Integration

### Available MCP Tools

#### Workflow Management
- `n8n_create_workflow` - Create new workflows in n8n
- `n8n_update_full_workflow` - Update complete workflow
- `n8n_update_partial_workflow` - Update specific nodes
- `n8n_list_workflows` - List existing workflows
- `n8n_get_workflow` - Get workflow details
- `n8n_delete_workflow` - Remove workflows

#### Discovery & Configuration  
- `search_nodes` - Find nodes by functionality
- `get_node_essentials` - Get core node properties
- `get_node_info` - Complete node documentation
- `list_nodes` - List all available nodes

#### Validation & Testing
- `n8n_validate_workflow` - Validate workflow structure
- `validate_workflow_connections` - Check node connections
- `validate_workflow_expressions` - Validate n8n expressions

#### Execution & Monitoring
- `n8n_trigger_webhook_workflow` - Execute webhook workflows
- `n8n_list_executions` - View execution history
- `n8n_get_execution` - Get execution details

#### Templates & Examples
- `get_templates_for_task` - Find workflow templates
- `search_templates` - Search template library
- `get_template` - Get specific template

## Workflow Generation Pipeline

### Command Usage

#### Agent Mode (Automation)
```bash
python3 tools/generate_n8n_workflow.py /path/to/capsule --agent
```
**Output**: `✅ Generated 1/1 workflows`

#### Manual Mode (Development)
```bash
python3 tools/generate_n8n_workflow.py /path/to/capsule
```
**Output**: Full verbose logging with file locations

### Specification Format

#### Basic Workflow Spec
```yaml
workflows:
  - name: "Builder Health Monitor"
    description: "Monitor capsule health via scheduled checks"
    triggers:
      - type: "schedule"
        name: "Daily Health Check"
        cron: "0 9 * * *"
    actions:
      - type: "http_request"
        name: "Check API"
        parameters:
          url: "{{$env.BUILDER_API_URL}}/health"
          method: "GET"
          headers:
            Authorization: "Bearer {{$env.BUILDER_API_KEY}}"
```

#### Advanced Workflow Spec
```yaml
workflows:
  - name: "Capsule Build Pipeline"
    description: "Automated build workflow"
    triggers:
      - type: "webhook" 
        name: "Build Trigger"
        path: "builder/capsule-build"
        method: "POST"
    actions:
      - type: "function"
        name: "Validate Request"
        parameters:
          code: |
            const request = $json;
            if (!request.capsule) {
              throw new Error('Missing capsule name');
            }
            return [{ json: request }];
      - type: "condition"
        name: "Check Build Lane"
        parameters:
          left_value: "={{$json.lane}}"
          right_value: "standard"
          operator: "equals"
      - type: "http_request"
        name: "Execute Build"
        parameters:
          url: "{{$env.BUILDER_API_URL}}/build"
          method: "POST"
```

### Generated Workflow Structure

#### Complete n8n Workflow JSON
```json
{
  "name": "Builder Health Monitor",
  "nodes": [
    {
      "name": "Daily Health Check",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [100, 200],
      "parameters": {
        "rule": {
          "interval": [{"field": "cronExpression", "value": "0 9 * * *"}]
        }
      }
    },
    {
      "name": "Check Builder API",
      "type": "n8n-nodes-base.httpRequest",
      "position": [400, 200],
      "parameters": {
        "url": "{{$env.BUILDER_API_URL}}/health",
        "method": "GET",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {"name": "Authorization", "value": "Bearer {{$env.BUILDER_API_KEY}}"}
          ]
        }
      }
    },
    {
      "name": "Log Builder Event", 
      "type": "n8n-nodes-base.function",
      "position": [700, 200],
      "parameters": {
        "functionCode": "// Catalyst event logging\nconst event = {\n  type: 'n8n_workflow_execution',\n  capsule: 'capsule-name',\n  status: 'completed',\n  timestamp: new Date().toISOString()\n};\nreturn [{ json: event }];"
      }
    }
  ],
  "connections": {
    "Daily Health Check": {
      "main": [[{"node": "Check Builder API", "type": "main", "index": 0}]]
    },
    "Check Builder API": {
      "main": [[{"node": "Log Builder Event", "type": "main", "index": 0}]]
    }
  },
  "settings": {
    "saveExecutionProgress": true,
    "saveManualExecutions": true
  },
  "tags": ["builder-system", "capsule-name"]
}
```

## Generated File Structure

```
capsule/
├── spec/requirements.yaml               # Source workflow specs
├── src/automation/n8n/
│   ├── builder_health_monitor.json     # Generated workflow JSON
│   └── capsule_build_pipeline.json     # Generated workflow JSON  
└── ops/n8n/
    ├── builder_health_monitor.json     # Deployed workflow JSON
    └── capsule_build_pipeline.json     # Deployed workflow JSON
```

## Catalyst Integration Patterns

### Standard Event Logging
Every generated workflow includes Catalyst event logging:
```javascript
const event = {
  type: 'n8n_workflow_execution',
  capsule: 'capsule-name',
  workflow: $workflow.name,
  status: $json.status || 'completed',
  timestamp: new Date().toISOString()
};

const logEntry = `${event.type}|${event.capsule}|${event.status}|${event.timestamp}`;
```

### Environment Variable Usage
```javascript
// Builder API integration
{{$env.BUILDER_API_URL}}/capsules/{{$json.name}}/health

// Authentication
Bearer {{$env.BUILDER_API_KEY}}

// File paths
{{$env.BUILDER_ROOT}}/capsules/{{$json.capsule}}
```

### Lane-Aware Processing
```json
{
  "name": "Determine Build Lane",
  "type": "n8n-nodes-base.if",
  "parameters": {
    "conditions": {
      "conditions": [
        {
          "leftValue": "={{$json.lane}}",
          "rightValue": "standard", 
          "operator": {"type": "string", "operation": "equals"}
        }
      ]
    }
  }
}
```

## Common Workflow Patterns

### Health Monitoring
- **Trigger**: Schedule (daily/hourly)
- **Actions**: API health checks, status validation
- **Output**: Health reports, alerts on failures

### Build Automation  
- **Trigger**: Webhook from build system
- **Actions**: Validation, lane determination, build execution
- **Output**: Build status, completion notifications

### Event Processing
- **Trigger**: Webhook from external systems
- **Actions**: Event parsing, routing, processing
- **Output**: Processed events, downstream notifications

### Data Synchronization
- **Trigger**: Schedule or webhook
- **Actions**: Data extraction, transformation, loading
- **Output**: Synchronized data, sync status reports

## Quality Assurance

### Automated Validation
- **Workflow Structure**: Node connections and flow validation
- **Expression Syntax**: n8n expression validation
- **Builder Integration**: Event logging and naming convention checks
- **Performance**: Timeout and resource usage validation

### Testing Strategy
- **Unit Testing**: Individual node configuration testing
- **Integration Testing**: Complete workflow execution testing
- **Builder Testing**: Catalyst integration validation
- **Performance Testing**: Execution time and resource optimization

## Deployment & Management

### Local Development
1. **Generate**: `python3 tools/generate_n8n_workflow.py /path/to/capsule`
2. **Validate**: Review generated JSON in `src/automation/n8n/`
3. **Deploy**: Use n8n-mcp tools for deployment to n8n instance
4. **Test**: Execute and monitor workflow performance

### Production Deployment
1. **Agent Generation**: `--agent` flag for automated deployment
2. **MCP Integration**: Direct deployment to n8n server
3. **Monitoring**: Automated health checks and performance monitoring
4. **Maintenance**: Debugger agent for ongoing optimization

The Catalyst n8n automation pipeline provides complete workflow lifecycle management from specification to production deployment, with specialized agents ensuring quality, performance, and Catalyst integration at every step.
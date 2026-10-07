# n8n Workflows Reference for Catalyst

## Overview
The Catalyst integrates with n8n (workflow automation platform) through the n8n-mcp server, enabling agents to create, validate, and deploy automation workflows from Builder capsule specifications.

## n8n Fundamentals for Agents

### What is n8n?
n8n is a fair-code licensed workflow automation tool for technical people. Key characteristics:
- **Node-based**: Workflows consist of connected nodes (like Zapier)
- **Self-hosted**: Runs on your infrastructure  
- **Extensible**: Custom nodes and integrations
- **Code-friendly**: JavaScript expressions, custom functions
- **API-first**: Full REST API for automation

### Core Concepts

#### Nodes
- **Trigger Nodes**: Start workflows (webhook, schedule, manual)
- **Action Nodes**: Perform operations (HTTP request, database, API calls)  
- **Logic Nodes**: Control flow (IF, Switch, Merge)
- **Transform Nodes**: Data manipulation (Set, Function, Code)

#### Connections
- **Main Flow**: Primary data path between nodes
- **Error Flow**: Error handling path (red connections)
- **Multiple Outputs**: Nodes can have multiple output paths

#### Data Structure
```json
{
  "items": [
    {
      "json": { "key": "value" },
      "binary": {},
      "pairedItem": { "item": 0 }
    }
  ]
}
```

## Catalyst Integration

### MCP Server Connection
The Catalyst uses the n8n-mcp server for direct n8n integration:
```
Builder Agent → n8n-mcp (MCP) → n8n Instance → Workflow Execution
```

### Available MCP Tools

#### Discovery & Search
- `search_nodes` - Find nodes by keyword/functionality
- `list_nodes` - List all available nodes  
- `get_node_essentials` - Get core properties for a node
- `get_node_info` - Get complete node documentation

#### Workflow Management
- `n8n_create_workflow` - Create new workflow
- `n8n_update_full_workflow` - Update complete workflow
- `n8n_update_partial_workflow` - Update specific nodes  
- `n8n_list_workflows` - List existing workflows
- `n8n_get_workflow` - Get workflow details
- `n8n_delete_workflow` - Remove workflow

#### Validation & Testing
- `n8n_validate_workflow` - Validate workflow structure
- `validate_workflow` - MCP-side validation
- `validate_workflow_connections` - Check node connections
- `validate_workflow_expressions` - Validate n8n expressions

#### Execution & Monitoring
- `n8n_trigger_webhook_workflow` - Execute webhook workflows
- `n8n_list_executions` - View execution history
- `n8n_get_execution` - Get execution details

#### Templates & Tasks
- `get_templates_for_task` - Find templates for specific tasks
- `get_template` - Get specific workflow template
- `search_templates` - Search template library

## Common n8n Node Types for Catalyst

### Essential Nodes

#### HTTP Request (`n8n-nodes-base.httpRequest`)
**Use Cases**: API calls, webhooks, external service integration
```json
{
  "parameters": {
    "url": "https://api.example.com/endpoint",
    "method": "POST",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Authorization",
          "value": "Bearer {{$node[\"Auth\"].json[\"token\"]}}"
        }
      ]
    },
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {
          "name": "data",
          "value": "{{$json.payload}}"
        }
      ]
    }
  }
}
```

#### Webhook (`n8n-nodes-base.webhook`)
**Use Cases**: Trigger workflows from external systems
```json
{
  "parameters": {
    "path": "builder-webhook",
    "httpMethod": "POST",
    "responseMode": "responseNode"
  }
}
```

#### Function (`n8n-nodes-base.function`)
**Use Cases**: Custom JavaScript logic
```json
{
  "parameters": {
    "functionCode": "const items = $input.all();\nreturn items.map(item => ({\n  json: {\n    ...item.json,\n    processed: true,\n    timestamp: new Date().toISOString()\n  }\n}));"
  }
}
```

#### Code (`n8n-nodes-base.code`)
**Use Cases**: Advanced JavaScript/Python code execution
```json
{
  "parameters": {
    "language": "javascript",
    "jsCode": "// Process Catalyst events\nfor (const item of $input.all()) {\n  const event = item.json;\n  \n  // Builder-specific processing\n  if (event.type === 'capsule_build') {\n    // Handle capsule build event\n    $return.push({\n      json: {\n        capsule: event.capsule,\n        status: 'processed',\n        timestamp: Date.now()\n      }\n    });\n  }\n}"
  }
}
```

#### Set (`n8n-nodes-base.set`)
**Use Cases**: Data transformation, variable setting
```json
{
  "parameters": {
    "mode": "manual",
    "values": {
      "string": [
        {
          "name": "builderSystem",
          "value": "capsule-automation"
        }
      ],
      "number": [
        {
          "name": "timestamp",
          "value": "={{Date.now()}}"
        }
      ]
    }
  }
}
```

#### IF (`n8n-nodes-base.if`)
**Use Cases**: Conditional logic, branching workflows
```json
{
  "parameters": {
    "conditions": {
      "options": {
        "caseSensitive": true,
        "leftValue": "",
        "typeValidation": "strict"
      },
      "conditions": [
        {
          "id": "condition1",
          "leftValue": "={{$json.status}}",
          "rightValue": "success",
          "operator": {
            "type": "string",
            "operation": "equals"
          }
        }
      ],
      "combinator": "and"
    }
  }
}
```

#### Schedule Trigger (`n8n-nodes-base.scheduleTrigger`)
**Use Cases**: Time-based automation (daily builds, health checks)
```json
{
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "cronExpression",
          "value": "0 9 * * *"
        }
      ]
    }
  }
}
```

### Catalyst Specific Patterns

#### Capsule Health Check Workflow
```json
{
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
      "name": "Get Capsule Status",
      "type": "n8n-nodes-base.httpRequest", 
      "position": [300, 200],
      "parameters": {
        "url": "http://builder-api.local/health",
        "method": "GET"
      }
    },
    {
      "name": "Process Results",
      "type": "n8n-nodes-base.function",
      "position": [500, 200],
      "parameters": {
        "functionCode": "return [{json: {status: $json.health, timestamp: Date.now()}}];"
      }
    }
  ],
  "connections": {
    "Daily Health Check": {"main": [[{"node": "Get Capsule Status", "type": "main", "index": 0}]]},
    "Get Capsule Status": {"main": [[{"node": "Process Results", "type": "main", "index": 0}]]}
  }
}
```

## Workflow Design Patterns

### Error Handling Pattern
```json
{
  "name": "HTTP with Error Handling",
  "type": "n8n-nodes-base.httpRequest",
  "onError": "continueErrorOutput",
  "parameters": {
    "url": "{{$json.endpoint}}",
    "method": "POST"
  }
}
```

### Data Transformation Pattern  
```json
{
  "name": "Transform Data",
  "type": "n8n-nodes-base.set",
  "parameters": {
    "mode": "manual",
    "values": {
      "string": [
        {
          "name": "transformed_data",
          "value": "={{JSON.stringify($json)}}"
        }
      ]
    }
  }
}
```

### Batch Processing Pattern
```json
{
  "name": "Split in Batches",
  "type": "n8n-nodes-base.splitInBatches",
  "parameters": {
    "batchSize": 10,
    "options": {}
  }
}
```

## n8n Expression Syntax

### Common Expressions
```javascript
// Access previous node data
{{$node["Node Name"].json["key"]}}

// Access current item
{{$json.fieldName}}

// Date functions
{{DateTime.now().toISO()}}

// String manipulation
{{$json.name.toUpperCase()}}

// Conditional expressions
{{$json.status === 'success' ? 'OK' : 'Failed'}}

// Array operations
{{$json.items.length}}

// Environment variables (for Builder secrets)
{{$env.BUILDER_API_KEY}}
```

### Catalyst Expressions
```javascript
// Builder capsule path
{{$env.BUILDER_ROOT}}/capsules/{{$json.capsuleName}}

// Event logging format
capsule_build|{{$json.capsule}}|{{$json.status}}|{{DateTime.now().toISO()}}

// Health check URL
{{$env.BUILDER_API_URL}}/capsules/{{$json.name}}/health
```

## Security & Best Practices

### Credential Management
- Use n8n credential system for API keys, tokens
- Store Builder system secrets as n8n credentials
- Never hardcode sensitive data in workflows

### Error Handling
- Always include error paths for HTTP requests
- Use meaningful error messages  
- Log errors to Builder event system

### Performance
- Use batch processing for large datasets
- Implement timeout handling for long operations
- Consider async patterns for parallel processing

### Testing
- Test workflows with sample data
- Validate all conditional branches
- Test error scenarios

### Builder Integration
- Log significant actions to Builder events
- Use Builder naming conventions
- Follow capsule-centric patterns
- Include Builder context in metadata

This comprehensive reference enables Catalyst agents to effectively create, validate, and deploy n8n workflows that integrate seamlessly with the Builder ecosystem.
# BridgeHub: Codex Communication Protocol

**Purpose:** Complete guide for using BridgeHub CLI tool to communicate between {{ORCHESTRATOR_NAME}} (Claude Code) and Codex.

---

## What BridgeHub Is

**CRITICAL:** BridgeHub is a **CLI-to-CLI bridge tool**, NOT an MCP server.

- **Type:** CLI tool for inter-agent communication
- **Location:** `{{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js`
- **Purpose:** Two-way communication between {{ORCHESTRATOR_NAME}} (Claude Code) and Codex
- **Usage:** Called directly via Bash tool

---

## When to Use BridgeHub

### Consultation Scenarios

{{USER_NAME}} will explicitly request Codex consultation:

- "Discuss with Codex"
- "Consult Codex"
- "Ask Codex about..."
- "Get Codex's opinion on..."
- "Have Codex review this"

### Available Actions

| Action | Purpose | Payload Fields |
|--------|---------|----------------|
| `freeform` | General questions/discussions | `message` |
| `peer_review` | Code review before writes | `file_path`, `code`, `operation` |
| `diff_summary` | Git diff analysis | `diff` |
| `spec_validate` | YAML spec validation | `spec_path` |
| `long_doc` | Document processing | `doc_path`, `query` |
| `qa_question` | Quality assurance queries | `question`, `target` |
| `codex_fix` | Automated fix suggestions | `issue`, `file_path`, `error_message` |

---

## Basic Invocation Pattern

```bash
node {{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js --request '{
  "version": "bridgehub/1.0",
  "action": "freeform",
  "capsule": "'"$(pwd)"'",
  "session": "{{ORCHESTRATOR_NAME_LOWER}}-codex-[topic]-[date]",
  "payload": {
    "message": "Your question or request for Codex here"
  }
}'
```

### Key Parameters

**Required:**
- `version`: Always `"bridgehub/1.0"`
- `action`: One of the available actions (see table above)
- `capsule`: Current working directory (use `$(pwd)` for dynamic)
- `session`: Session identifier (format: `{{ORCHESTRATOR_NAME_LOWER}}-codex-[topic]-[date]`)
- `payload`: Action-specific data (see action definitions)

---

## Usage Examples

### Example 1: Freeform Discussion

**Scenario:** Ask Codex about technical trade-offs

```bash
node {{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js --request '{
  "version": "bridgehub/1.0",
  "action": "freeform",
  "capsule": "{{CATALYST_ROOT}}/capsules/example",
  "session": "{{ORCHESTRATOR_NAME_LOWER}}-codex-rag-analysis-2025-10-20",
  "payload": {
    "message": "What are the trade-offs between using a vector database vs full-text search for RAG implementation?"
  }
}'
```

### Example 2: Code Review

**Scenario:** Get Codex review before committing changes

```bash
node {{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js --request '{
  "version": "bridgehub/1.0",
  "action": "peer_review",
  "capsule": "'"$(pwd)"'",
  "session": "{{ORCHESTRATOR_NAME_LOWER}}-codex-auth-review-2025-10-20",
  "payload": {
    "file_path": "src/auth/login.ts",
    "code": "export async function login(email: string, password: string) { ... }",
    "operation": "add"
  }
}'
```

### Example 3: Spec Validation

**Scenario:** Validate YAML spec before using it

```bash
node {{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js --request '{
  "version": "bridgehub/1.0",
  "action": "spec_validate",
  "capsule": "'"$(pwd)"'",
  "session": "{{ORCHESTRATOR_NAME_LOWER}}-codex-spec-check-2025-10-20",
  "payload": {
    "spec_path": "specs/current.yaml"
  }
}'
```

---

## Response Format

BridgeHub prints output to stdout in this format:

```
{{ORCHESTRATOR_NAME_UPPER}}_PAYLOAD=<json>
```

### Parsing Response

The JSON response contains:

```json
{
  "ok": true,
  "answer": "Codex's response text here...",
  "duration_ms": 1234
}
```

**On error:**
```json
{
  "ok": false,
  "reason": "Error description",
  "duration_ms": 1234
}
```

### Response Fields

- `ok` (boolean): Success/failure status
- `answer` (string): Codex's response text (if successful)
- `reason` (string): Error reason (if `ok=false`)
- `duration_ms` (number): Execution time in milliseconds

---

## Session Naming Convention

**Format:** `{{ORCHESTRATOR_NAME_LOWER}}-codex-[topic]-[date]`

**Examples:**
- `{{ORCHESTRATOR_NAME_LOWER}}-codex-rag-analysis-2025-10-20`
- `{{ORCHESTRATOR_NAME_LOWER}}-codex-auth-review-2025-10-20`
- `{{ORCHESTRATOR_NAME_LOWER}}-codex-architecture-2025-10-20`

**Guidelines:**
- Use descriptive topic (rag-analysis, auth-review, architecture)
- Include date (YYYY-MM-DD format)
- Lowercase with hyphens

---

## Key Constraints

### 1. NOT an MCP Server
- Never try to register BridgeHub as an MCP server
- Always invoke directly via Bash tool

### 2. Direct Invocation Only
- Call using `node /path/to/bridgehub.js`
- No MCP abstraction layer

### 3. Current Directory as Capsule
- BridgeHub uses {{ORCHESTRATOR_NAME}}'s current working directory
- Use `$(pwd)` for dynamic capsule path

### 4. Timeout Limits
- Default: 45 seconds
- Long document processing: up to 90 seconds
- Plan accordingly for complex queries

---

## Integration with {{ORCHESTRATOR_NAME}} Workflow

### Typical Flow

1. **User requests Codex consultation:**
   > "Ask Codex about the RAG architecture trade-offs"

2. **{{ORCHESTRATOR_NAME}} invokes BridgeHub:**
   ```bash
   node {{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js --request '{...}'
   ```

3. **Parse response:**
   ```bash
   # Extract JSON from {{ORCHESTRATOR_NAME_UPPER}}_PAYLOAD=<json>
   # Check ok field
   # Display answer to user
   ```

4. **Report back to user:**
   > "Codex suggests: [answer]..."

---

## Error Handling

### Common Errors

**Timeout:**
```json
{"ok": false, "reason": "Request timed out after 45s"}
```
**Solution:** Break query into smaller parts or increase timeout for long_doc action.

**Invalid Action:**
```json
{"ok": false, "reason": "Unknown action: xyz"}
```
**Solution:** Use one of the valid actions (see Available Actions table).

**Missing Payload Field:**
```json
{"ok": false, "reason": "Missing required field: message"}
```
**Solution:** Ensure all required payload fields are included.

### Error Recovery

When BridgeHub fails:
1. Check syntax of JSON request
2. Verify action name is valid
3. Confirm all required payload fields present
4. Consider simplifying query if timeout
5. Fallback to continuing without Codex input if necessary

---

## Best Practices

### 1. Clear Questions
Frame questions clearly and concisely for best Codex responses.

### 2. Appropriate Actions
Use the right action for the task:
- General questions → `freeform`
- Code review → `peer_review`
- YAML validation → `spec_validate`

### 3. Context in Payload
Include relevant context in payload for better responses.

### 4. Session Naming
Use descriptive session names for tracking and debugging.

### 5. Parse Responses
Always check `ok` field before using `answer`.

---

## Advanced Usage

### Chaining Requests

For complex consultations, chain multiple BridgeHub requests:

```bash
# 1. Ask about approach
# 2. Get code review
# 3. Validate final spec

# Each request builds on previous answer
```

### Integrating with Capsule Context

Use capsule-specific context in queries:

```bash
"message": "Given this capsule's current architecture in specs/current.yaml, should we migrate to microservices?"
```

---

*BridgeHub Protocol Guide - Catalyst Documentation*

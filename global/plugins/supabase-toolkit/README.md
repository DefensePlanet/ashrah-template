# Supabase Toolkit Plugin

Complete Supabase integration for Claude Code via Backend Dev agent with CLI-first approach.

## Overview

The Supabase Toolkit enables BuilderOS backend work with Supabase databases through:
- **Backend Dev agent** - Handles all database design and backend API work
- **Supabase CLI** - PRIMARY METHOD for direct, powerful database access
- **Official Supabase MCP server** - SECONDARY METHOD for programmatic operations

## Agent Integration

### Backend Dev + Supabase

The **Backend Dev** agent handles all Supabase database work using CLI-first approach:

**Supabase Capabilities:**
- PostgreSQL schema design and optimization
- Database migrations with rollback strategies
- Row Level Security (RLS) policy architecture
- TypeScript/Go/Swift type generation from schema
- Local development with full Supabase stack
- Schema diffing and migration management
- Performance analysis and indexing
- Security audits and compliance

**Available Tools:**
- **PRIMARY**: Supabase CLI via Bash tool (full feature set)
- **SECONDARY**: Supabase MCP (fallback for programmatic operations)
- Read, Write, Edit (for file operations)
- Context7 MCP (for language/framework expertise)

**{{ORCHESTRATOR_NAME}} automatically routes database work to Backend Dev:**
- "Design a database schema for..."
- "Create a migration to..."
- "Start local Supabase for testing"
- "Show me the schema diff"
- "Implement RLS policies for..."
- "Optimize the database performance..."
- "Generate TypeScript types from..."

### MCP Server Integration

The toolkit includes configuration for the official Supabase MCP server.

**Package**: `@supabase/mcp-server-supabase@latest`

**Configuration**:
```json
{
  "command": "npx",
  "args": [
    "-y",
    "@supabase/mcp-server-supabase@latest",
    "--read-only",
    "--project-ref=<your-project-ref>"
  ],
  "env": {
    "SUPABASE_ACCESS_TOKEN": "<your-access-token>"
  }
}
```

**Available MCP Tools** (used by agent):
- `list_tables` - List all database tables and schemas
- `list_extensions` - List installed PostgreSQL extensions
- `list_migrations` - Show migration history
- `apply_migration` - Execute DDL operations and schema changes
- `execute_sql` - Run SQL queries (read-only by default)
- `get_logs` - Fetch service logs (api, postgres, auth, storage, realtime)
- `get_advisors` - Get security and performance recommendations
- `generate_typescript_types` - Generate types from database schema
- Edge function management (list, get, deploy)
- Development branch operations (create, merge, rebase, reset)

## Setup

### 0. Install Supabase CLI (If Not Already Installed)

```bash
# macOS
brew install supabase/tap/supabase

# Update existing installation
brew upgrade supabase

# Verify installation
supabase --version
```

### 1. Get Supabase Credentials

**Project Reference:**
- Found in Supabase project settings
- Settings → General → Project Reference
- Format: `abcdefghijklmnop`

**Access Token:**
- Generated in Supabase dashboard
- Account Settings → Access Tokens → Generate New Token
- Store securely (use BuilderOS Strongbox)

### 2. Store Credentials in Strongbox

```bash
# Store project reference
tools/strongbox_cli.py set-api-key \
  --service supabase \
  --purpose "project-ref" \
  --api-key "your-project-ref"

# Store access token
tools/strongbox_cli.py set-api-key \
  --service supabase \
  --purpose "access-token" \
  --api-key "your-access-token"
```

### 3. Configure Capsule

**Create `.env.template` in capsule root:**
```bash
# capsules/your-project/.env.template
SUPABASE_PROJECT_REF=  # strongbox:supabase:project-ref
SUPABASE_ACCESS_TOKEN=  # strongbox:supabase:access-token
```

**Sync credentials:**
```bash
tools/sync_capsule_env.py your-capsule-name
```

**Create/update `.claude/config.json` in capsule:**
```json
{
  "mcp": {
    "profile": "default",
    "env": {
      "SUPABASE_PROJECT_REF": "${SUPABASE_PROJECT_REF}",
      "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
    },
    "include": ["supabase"]
  }
}
```

**Note:** Supabase is an optional MCP in the default profile, so you need to explicitly include it in capsules that use it.

### 4. Initialize Supabase in Capsule

```bash
cd capsules/your-project

# Ensure credentials are loaded
export $(grep -v '^#' .env | xargs)

# Initialize Supabase (creates supabase/ directory with config)
supabase init

# Link to your project
supabase link --project-ref $SUPABASE_PROJECT_REF

# Pull existing schema
supabase db pull
```

This creates:
- `supabase/` directory with config
- `supabase/migrations/` for migration files
- `supabase/config.toml` for project configuration

### 5. Restart Claude Code

The Supabase CLI is now ready. MCP server is available as fallback.

## Usage

### Natural Language (Recommended)

Just talk to {{ORCHESTRATOR_NAME}} naturally about database work. He'll automatically route to the Backend Dev agent:

```
"Design a database schema for a todo app with user authentication and RLS policies"

"Create a migration to add an email_verified column to the users table"

"Optimize the posts query - it's running slow"

"Generate TypeScript types from my current database schema"

"Run a security audit on the RLS policies"
```

The agent will:
1. Use MCP tools to introspect your database
2. Design/implement the requested changes
3. Create migration files
4. Generate types
5. Provide security recommendations

### Direct Agent Invocation (Optional)

If you want to explicitly use the Backend Dev for database work:

```
Use the Backend Dev to design a multi-tenant database schema
with proper RLS isolation for a Supabase backend
```

## Common Workflows

### New Database Schema

**You say:**
```
"Design a database schema for a SaaS app with organizations, users, and subscriptions"
```

**Agent does:**
1. Analyzes requirements
2. Designs normalized schema (3NF minimum)
3. Creates RLS policies for tenant isolation
4. Generates migration SQL files
5. Creates TypeScript type definitions
6. Runs security audit
7. Documents the schema

**You get:**
- Migration files ready to apply
- RLS policies defined and tested
- TypeScript types for your app
- Security audit report

### Schema Changes

**You say:**
```
"Add email verification to the authentication flow"
```

**Agent does:**
1. Plans schema changes (email_verified column, verification_token, etc.)
2. Creates migration with rollback procedure
3. Updates RLS policies if needed
4. Tests migration safety
5. Generates updated types
6. Documents the changes

### Performance Optimization

**You say:**
```
"The posts query is slow - optimize it"
```

**Agent does:**
1. Analyzes query using `get_logs` and `execute_sql`
2. Reviews current indexes
3. Suggests index additions
4. Optimizes RLS policy performance
5. Implements changes via migration
6. Tests performance improvements
7. Documents optimizations

### Security Audit

**You say:**
```
"Run a security audit on my database"
```

**Agent does:**
1. Checks RLS coverage using `list_tables`
2. Reviews authentication config via `get_advisors`
3. Audits API security settings
4. Validates storage permissions
5. Generates compliance report
6. Provides remediation recommendations

## Integration with BuilderOS

### Credential Storage

Supabase credentials are stored in Strongbox and synced to capsule `.env` files using the hybrid workflow:

1. **Strongbox** = Source of truth (encrypted, backed up)
2. **Capsule .env** = Local convenience (gitignored)
3. **Sync mechanism** = `tools/sync_capsule_env.py`

### MCP Profile

Supabase is available as an optional MCP in the `default` profile:

```json
{
  "default": {
    "mcps": ["filesystem", "git", "builder-memory", "context7"],
    "optional_mcps": ["playwright", "supabase"],
    "agents": ["backend-specialist", "..."]
  }
}
```

Backend projects include it explicitly in their capsule config.

### Agent Routing

{{ORCHESTRATOR_NAME}} automatically routes backend and database work to `Backend Dev` when you mention:
- Backend APIs
- Database schemas
- Migrations
- RLS policies
- Database optimization
- Type generation
- Supabase integration

## Best Practices

### Schema Design
- Use 3NF normalization minimum
- Follow snake_case naming convention
- Ensure comprehensive RLS coverage
- Performance-test all migrations

### Migration Management
- Always test in development first
- Create rollback procedures
- Use transactions for atomicity
- Document migration purpose

### Security
- Enable RLS on all sensitive tables
- Apply principle of least privilege
- Run regular security audits
- Monitor access patterns

### Performance
- Index commonly queried columns
- Optimize RLS policy performance
- Monitor query execution times
- Use connection pooling

## Troubleshooting

### MCP Server Not Connecting

**Symptoms:** Agent can't access database

**Solutions:**
1. Verify credentials in Strongbox
2. Check `.env` file exists and has values
3. Ensure network connectivity to Supabase
4. Verify project reference format is correct
5. Check access token hasn't expired

### Invalid Credentials

**Symptoms:** "Project not found" or "Access denied"

**Solutions:**
1. Verify project reference from dashboard
2. Ensure no extra spaces in credentials
3. Check project is active (not paused)
4. Regenerate access token if needed
5. Verify token has required permissions

### Migration Failures

**Symptoms:** Migration fails to apply

**Solutions:**
1. Test migration in development environment first
2. Check for constraint violations
3. Verify foreign key relationships
4. Review migration SQL syntax
5. Check database logs for details

## Advanced Usage

### Multiple Environments

Store different credentials for dev/staging/prod:

```bash
# Development
tools/strongbox_cli.py set-api-key \
  --service supabase-dev \
  --purpose "project-ref" \
  --api-key "dev-project-ref"

# Production
tools/strongbox_cli.py set-api-key \
  --service supabase-prod \
  --purpose "project-ref" \
  --api-key "prod-project-ref"
```

Use environment-specific configs in capsules.

### Read-Only vs Write Mode

By default, the MCP server runs in read-only mode:

```json
"args": ["--read-only", "--project-ref=${SUPABASE_PROJECT_REF}"]
```

To enable writes (for migrations), the agent uses specific MCP tools:
- `apply_migration` (always available for schema changes)
- `execute_sql` (respects read-only flag)

The agent knows when to use each tool appropriately.

## Files & Structure

```
supabase-toolkit/
├── mcps/
│   └── supabase.json                   # MCP configuration template
├── examples/
│   ├── database-capsule-config.json    # Example capsule config
│   └── QUICKSTART.md                   # Quick start guide
├── README.md                            # This file
└── INTEGRATION_SUMMARY.md               # Integration details
```

**Note:** Database capabilities are built into the Backend Dev agent (`/.claude/agents/backend-specialist.md`)

## Resources

**Official Supabase:**
- Documentation: https://supabase.com/docs
- MCP Server: https://github.com/supabase/supabase-mcp
- Dashboard: https://app.supabase.com

**BuilderOS:**
- Agent Matrix: `global/mcp/AGENT_MCP_MATRIX.md`
- Profile Configs: `global/mcp/profile-configs.json`
- Server Registry: `global/mcp/server-registry.json`
- Security Baseline: `global/docs/MCP_Security_Baseline.md`

**Tools:**
- Strongbox CLI: `tools/strongbox_cli.py --help`
- Capsule Sync: `tools/sync_capsule_env.py --help`
- MCP Profile Manager: `tools/mcp_profile_manager.py`

---

**Source**: Forked from `claude-code-templates@aitmpl` (supabase-toolkit plugin)
**Maintained**: `{{CATALYST_ROOT}}/global/plugins/supabase-toolkit/`

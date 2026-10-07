# Supabase Toolkit Quick Start

Get started with Supabase CLI integration in BuilderOS in 5 minutes.

## What You Get

- **Backend Dev agent** - Handles all backend and database design work
- **Supabase CLI** - PRIMARY METHOD for powerful database operations
- **Supabase MCP server** - SECONDARY METHOD for programmatic operations
- **Local development** - Full Supabase stack on your machine
- **Schema diffing** - Track and manage schema changes
- **Natural language usage** - Just talk about what you need

## Step 1: Get Supabase Credentials

### Project Reference

1. Open your Supabase dashboard
2. Go to **Settings** → **General**
3. Find **Project Reference** (looks like `abcdefghijklmnop`)
4. Copy this value

### Access Token

1. Go to **Account Settings** (click your profile)
2. Navigate to **Access Tokens**
3. Click **Generate New Token**
4. Give it a descriptive name (e.g., "BuilderOS Integration")
5. Copy the token immediately (you won't see it again)

## Step 2: Store Credentials Securely

Use BuilderOS Strongbox to store your credentials:

```bash
# Store project reference
tools/strongbox_cli.py set-api-key \
  --service supabase \
  --purpose "project-ref" \
  --api-key "your-project-ref-here"

# Store access token
tools/strongbox_cli.py set-api-key \
  --service supabase \
  --purpose "access-token" \
  --api-key "your-access-token-here"
```

## Step 3: Configure Your Capsule

### Create .env.template

In your capsule root, create `.env.template`:

```bash
# capsules/your-project/.env.template
SUPABASE_PROJECT_REF=  # strongbox:supabase:project-ref
SUPABASE_ACCESS_TOKEN=  # strongbox:supabase:access-token
```

### Sync Credentials

```bash
tools/sync_capsule_env.py your-capsule-name
```

This creates a `.env` file (automatically gitignored) with your credentials.

### Configure Claude Code

Create or update `capsules/your-project/.claude/config.json`:

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

**Note:** Supabase is optional in the default profile, so you must explicitly include it.

## Step 4: Restart Claude Code

Restart Claude Code to load the Supabase MCP server.

## Step 5: Start Using It

Just talk naturally to {{ORCHESTRATOR_NAME}} about database work:

```
"Design a database schema for a todo app with user authentication and RLS policies"
```

{{ORCHESTRATOR_NAME}} will automatically route to the Backend Dev agent, which will:
1. Use MCP tools to introspect your database
2. Design the schema
3. Create migration files
4. Set up RLS policies
5. Generate TypeScript types
6. Run security audit

## Common Requests

### Schema Design

```
"Design a database schema for a SaaS app with organizations, users, and subscriptions"
```

The agent will create a normalized schema with proper relationships and RLS policies.

### Migrations

```
"Create a migration to add email verification to users"
```

The agent will generate migration SQL with rollback procedures.

### Performance

```
"Optimize the posts query - it's running slow"
```

The agent will analyze queries, suggest indexes, and implement optimizations.

### Type Generation

```
"Generate TypeScript types from my current database schema"
```

The agent will use MCP tools to extract schema and create type definitions.

### Security Audit

```
"Run a security audit on my database"
```

The agent will check RLS coverage, authentication config, and provide recommendations.

## How It Works

### Behind the Scenes

1. **You**: Say something about database work
2. **{{ORCHESTRATOR_NAME}}**: Detects database/backend intent, routes to Backend Dev
3. **Backend Dev**: Uses Supabase MCP tools to:
   - List tables (`list_tables`)
   - Review migrations (`list_migrations`)
   - Execute SQL (`execute_sql`)
   - Apply migrations (`apply_migration`)
   - Generate types (`generate_typescript_types`)
   - Get recommendations (`get_advisors`)
4. **You**: Get migration files, types, and documentation

### No Commands Needed

You don't need to remember slash commands or special syntax. Just describe what you want in natural language, and the agent handles it.

## Troubleshooting

### MCP Server Not Connecting

**Error:** Supabase MCP server fails to start

**Check:**
1. Credentials are correct in Strongbox
2. `.env` file exists in capsule and has values
3. Network connectivity to Supabase
4. Project reference format is correct
5. Access token hasn't expired

**Fix:**
```bash
# Verify credentials
tools/strongbox_cli.py get-api-key --service supabase --purpose "project-ref"
tools/strongbox_cli.py get-api-key --service supabase --purpose "access-token"

# Re-sync if needed
tools/sync_capsule_env.py your-capsule-name

# Restart Claude Code
```

### Invalid Credentials

**Error:** "Project not found" or "Access denied"

**Fix:**
1. Verify project reference from Supabase dashboard
2. Ensure no extra spaces in credentials
3. Check project is active (not paused)
4. Generate new access token if needed

### Agent Not Responding

**Symptom:** {{ORCHESTRATOR_NAME}} doesn't route to Backend Dev for database work

**Check:**
1. Capsule config includes `supabase` in the `include` array
2. MCP server is loaded (check server list)
3. Phrasing mentions database/backend/schema/migration keywords

**Fix:**
Be explicit: "Use the Backend Dev to design a Supabase database..."

## Examples

### Multi-Tenant SaaS

```
"Design a database schema for a multi-tenant SaaS application with:
- Organizations (tenants)
- Users with role-based access
- Subscription plans
- Usage tracking
- Proper RLS for tenant isolation"
```

**Agent delivers:**
- Normalized schema
- RLS policies for each table
- Migration files
- TypeScript types
- Security audit

### E-Commerce

```
"Create a database schema for an e-commerce store with:
- Products and categories
- Shopping cart
- Orders and order items
- Customer accounts
- Inventory tracking"
```

**Agent delivers:**
- Schema with proper foreign keys
- RLS for customer data privacy
- Migrations ready to apply
- Type definitions
- Performance indexes

### Blog Platform

```
"Design a database for a blog platform with:
- Posts and drafts
- Comments with threading
- User profiles and following
- Tags and categories
- Full-text search"
```

**Agent delivers:**
- Optimized schema
- Full-text search indexes
- RLS for private drafts
- Migrations
- TypeScript types

## Advanced Usage

### Multiple Environments

Store separate credentials for dev/staging/prod:

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

Then use environment-specific `.env.template` files.

### Custom Workflows

The agent is proactive and flexible. You can request:

- **Schema reviews**: "Review my database schema for performance issues"
- **Migration planning**: "Plan a migration to split the users table"
- **RLS design**: "Design RLS policies for multi-tenant isolation"
- **Type updates**: "Update TypeScript types after schema changes"
- **Security**: "Audit database security and RLS coverage"

## Resources

- **Full README**: `{{CATALYST_ROOT}}/global/plugins/supabase-toolkit/README.md`
- **Integration Details**: `{{CATALYST_ROOT}}/global/plugins/supabase-toolkit/INTEGRATION_SUMMARY.md`
- **Supabase Docs**: https://supabase.com/docs
- **MCP Server**: https://github.com/supabase/supabase-mcp

## Getting Help

If you encounter issues:

1. Check BuilderOS logs
2. Verify credential configuration
3. Review MCP server status
4. Consult plugin README
5. Check Supabase documentation

---

**That's it!** You're ready to use Supabase with BuilderOS. Just start talking to {{ORCHESTRATOR_NAME}} about database work.

# Supabase Configuration for BuilderOS

**Date:** 2025-10-31
**Status:** ✅ Configured - CLI Primary + MCP Fallback

## Overview

Backend Developer agent uses **dual-method** Supabase integration:
1. **PRIMARY:** Supabase CLI (direct binary execution)
2. **FALLBACK:** Supabase MCP Server (programmatic access)

## Components Installed

### 1. Supabase CLI ✅ ACTIVE

**Installation:**
- Binary: `{{HOME_DIR}}/.local/bin/supabase`
- Version: 2.54.11
- Architecture: darwin_arm64
- Access: Available in PATH

**Verification:**
```bash
supabase --version
# Output: 2.54.11

which supabase
# Output: {{HOME_DIR}}/.local/bin/supabase
```

**Helper Functions:**
- Location: `tools/supabase_helpers.sh`
- 12 utility functions available
- Auto-sourced by Backend Developer agent

### 2. Supabase MCP Server ✅ CONFIGURED

**Configuration:**
- File: `.mcp.json` (line 140-151)
- Package: `@supabase/mcp-server-supabase@latest`
- Transport: stdio (npx-based)
- Role: Fallback method for programmatic operations

**MCP Tools Available:**
- `list_tables` - Database introspection
- `list_extensions` - PostgreSQL extensions
- `list_migrations` - Migration history
- `apply_migration` - Execute DDL operations
- `execute_sql` - Run SQL queries
- `get_logs` - Service logs (api, postgres, auth, storage, realtime)
- `get_advisors` - Security and performance recommendations
- `generate_typescript_types` - Generate types from schema
- Edge function operations (list, get, deploy)
- Development branch operations (create, merge, rebase, reset)

## Environment Variables Required

The MCP server requires these environment variables to be set in `{{CATALYST_ROOT}}/.env`:

```bash
# Supabase Project Configuration
SUPABASE_PROJECT_REF=<your-project-ref>      # Example: sfsrjtswrmyuifyaplac
SUPABASE_ACCESS_TOKEN=<your-access-token>    # Personal access token from dashboard

# Optional (for CLI usage in capsules)
SUPABASE_URL=<your-project-url>              # Example: https://xxx.supabase.co
```

**How to get credentials:**
1. Go to https://app.supabase.com
2. Select your project
3. Settings → API → Project Settings
4. Copy Project Ref (from URL or API settings)
5. Settings → Account → Access Tokens → Generate new token

**Current Status:**
- ✅ Credentials exist in capsule: `capsules/example-partners/.env`
- ✅ Project ref: `sfsrjtswrmyuifyaplac` (extracted from Supabase URL)
- ✅ Access token: Configured in capsule
- ⚠️ Note: Root `.env` file is protected by security hook (good practice)

## Backend Developer Agent Configuration

**Agent File:** `.claude/agents/backend-specialist.md`

**Lines 56-220: Complete Supabase Integration**

### Primary Method: CLI (Lines 61-146)
```bash
# Setup
supabase init
supabase link --project-ref $SUPABASE_PROJECT_REF

# Schema Management
supabase db pull          # Pull remote schema
supabase db diff          # Show differences
supabase db push          # Push migrations
supabase db lint          # Check for issues

# Migration Workflow
supabase migration new add_feature
supabase migration list
supabase migration squash

# Type Generation
supabase gen types typescript --linked > types/database.ts
supabase gen types go --linked > types/database.go
supabase gen types swift --linked > Types/Database.swift

# Local Development
supabase start           # Spin up local stack
supabase status          # Check status
supabase db reset        # Reset to migrations
supabase stop            # Stop local stack
```

### Secondary Method: MCP (Lines 164-184)
- Use when CLI is unavailable
- Use for programmatic operations requiring structured JSON responses
- Use for security advisors and recommendations
- Use for edge function management

**Helper Functions Available:**
```bash
source tools/supabase_helpers.sh

init_supabase_capsule     # Initialize Supabase in directory
link_project <ref>        # Connect to project
pull_schema               # Pull remote schema
push_migrations           # Push with confirmation
generate_types [file]     # Generate TypeScript types
show_diff                 # Show schema differences
new_migration <name>      # Create migration
start_local               # Start local stack
stop_local                # Stop local stack
reset_local               # Reset with confirmation
lint_database             # Lint database
show_migrations           # Migration history
squash_migrations         # Combine migrations
```

## Agent Workflow

### Schema Design Workflow
1. `supabase db pull` - Get current schema
2. `supabase migration new feature_name` - Create migration
3. Edit migration file with SQL
4. `supabase db reset` - Test locally
5. `supabase db lint` - Check for issues
6. `supabase db push` - Deploy to remote
7. `supabase gen types typescript --linked` - Generate types

### Local Development Workflow
1. `supabase start` - Spin up local stack
2. `supabase db diff` - Check differences
3. Edit migrations as needed
4. `supabase db reset` - Apply locally
5. Run application tests
6. `supabase db push` - Push when ready

### Production Workflow
1. `supabase db diff` - Verify no drift
2. `supabase migration list` - Review pending
3. `supabase db push --dry-run` - Preview changes
4. `supabase db push` - Apply migrations

## Orchestration & Routing

**{{ORCHESTRATOR_NAME}} Routing:**
- Database design tasks → Backend Developer
- Supabase operations → Backend Developer
- Backend Developer automatically has access to CLI + MCP

**Agent Coordination:**
- Backend Developer ← Designs schema, writes migrations
- Frontend Developer ← Consumes generated TypeScript types
- Security Analyst ← Reviews RLS policies
- Mobile Dev ← Uses Swift types for iOS apps

## Verification Checklist

- [x] Supabase CLI installed (v2.54.11)
- [x] CLI accessible in PATH
- [x] Helper functions exist (`tools/supabase_helpers.sh`)
- [x] MCP server configured in `.mcp.json`
- [x] Backend Developer agent has full documentation
- [x] Supabase toolkit plugin enabled
- [x] Environment variables documented
- [x] Both CLI and MCP methods available

## Testing

### Test CLI:
```bash
supabase --version
# Should output: 2.54.11

supabase help
# Should show command list

source tools/supabase_helpers.sh
# Should load 12 functions
```

### Test MCP:
- Restart Claude Code to load MCP configuration
- MCP server will connect when Backend Developer agent is invoked
- Check loaded servers in Claude Code status

## Troubleshooting

**CLI not found:**
```bash
# Verify installation
ls -la ~/.local/bin/supabase

# Check PATH
echo $PATH | grep ".local/bin"

# Manual test
~/.local/bin/supabase --version
```

**MCP not connecting:**
1. Check environment variables are set in root `.env`
2. Restart Claude Code to reload MCP configuration
3. Verify `npx @supabase/mcp-server-supabase` works manually
4. Check MCP logs in Claude Code

**Credentials missing:**
- Credentials are in `capsules/example-partners/.env`
- Project ref: `sfsrjtswrmyuifyaplac`
- Access token: Available in capsule .env
- For root .env setup, add the required variables manually

## Best Practices

1. **CLI First:** Always use CLI for schema operations (most powerful)
2. **Local Development:** Keep `supabase start` running during development
3. **Test Locally:** Use `db reset` to test migrations before pushing
4. **Track Drift:** Use `db diff` to catch manual schema changes
5. **Type Generation:** Regenerate types after every schema change
6. **Naming:** Use snake_case for tables/columns (PostgreSQL convention)
7. **Security:** Ensure RLS policies cover all sensitive tables
8. **Performance:** Index foreign keys and frequently queried columns
9. **Rollbacks:** Always create rollback migrations for safety

## Summary

✅ **CLI Primary Method:** Installed, working, preferred
✅ **MCP Fallback Method:** Configured, ready as backup
✅ **Backend Developer:** Fully equipped with both methods
✅ **Helper Functions:** Available for common operations
✅ **Documentation:** Complete in agent file
✅ **Orchestration:** Proper routing to Backend Developer

Backend Developer can now execute all Supabase operations with CLI as priority and MCP as fallback.

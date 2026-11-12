# Supabase CLI Migration Guide

## What Changed

**OLD**: MCP-first approach with Supabase MCP server as primary method
**NEW**: CLI-first approach with Supabase CLI as primary method

## Why CLI-First?

The Supabase CLI provides capabilities that MCP doesn't:

✅ **Local Development** - Full Supabase stack (Postgres + Auth + Storage + Realtime)
✅ **Schema Diffing** - Track manual schema changes and drift
✅ **Advanced Migrations** - Squash, repair, rollback capabilities
✅ **Multi-Language Types** - TypeScript, Go, Swift support
✅ **Database Linting** - SQL type checking and validation
✅ **Direct Access** - No abstraction layer, full feature set
✅ **Better DX** - Standard tooling, better documentation

MCP is still available as fallback for:
- Programmatic introspection (structured JSON responses)
- Security advisors (get_advisors)
- Edge function management
- When CLI isn't available

## What the Backend Dev Agent Does Now

### PRIMARY: CLI Commands (via Bash tool)

```bash
# Schema operations
supabase db pull          # Pull remote schema
supabase db push          # Push migrations
supabase db diff          # Show differences
supabase db lint          # Check for issues

# Migration workflow
supabase migration new    # Create migration
supabase migration list   # Show history
supabase migration squash # Combine migrations

# Local development
supabase start            # Start local stack
supabase stop             # Stop local stack
supabase db reset         # Reset to migrations

# Type generation
supabase gen types typescript
supabase gen types go
supabase gen types swift
```

### SECONDARY: MCP Tools (Fallback)

```
list_tables              # When need structured data
execute_sql              # For programmatic queries
get_advisors             # Security recommendations
apply_migration          # When CLI not available
```

## New Capabilities Unlocked

### 1. Local Development

Test everything locally before pushing to remote:

```bash
supabase start     # Full local Supabase
supabase db reset  # Test migrations
supabase stop      # Clean up
```

### 2. Schema Diffing

Catch manual changes made outside migrations:

```bash
supabase db diff                    # Show all changes
supabase db diff -f manual_changes  # Save as migration
```

### 3. Advanced Migration Management

```bash
supabase migration squash    # Combine multiple migrations
supabase migration repair    # Fix migration history
```

### 4. Multi-Language Types

Not just TypeScript anymore:

```bash
supabase gen types typescript > types/database.ts
supabase gen types go > types/database.go
supabase gen types swift > Types/Database.swift
```

### 5. Database Linting

Catch errors before deployment:

```bash
supabase db lint  # Type checking for SQL
```

## Migration Steps for Existing Capsules

### If You Were Using MCP

1. **Keep your existing setup** - MCP still works as fallback
2. **Add CLI initialization**:
   ```bash
   cd your-capsule
   export $(grep -v '^#' .env | xargs)
   supabase init
   supabase link --project-ref $SUPABASE_PROJECT_REF
   supabase db pull
   ```
3. **Start using CLI commands** - Backend Dev will use them automatically
4. **Optional**: Start local development with `supabase start`

### For New Capsules

1. Set up credentials in Strongbox (same as before)
2. Create `.env.template` (same as before)
3. Sync credentials (same as before)
4. **NEW**: Initialize Supabase:
   ```bash
   supabase init
   supabase link --project-ref $SUPABASE_PROJECT_REF
   supabase db pull
   ```
5. Done! Backend Dev uses CLI by default

## Backward Compatibility

✅ **All existing workflows still work**
✅ **MCP server still available**
✅ **No breaking changes to APIs**
✅ **Credentials stored the same way**
✅ **Natural language requests unchanged**

The only difference: Backend Dev now uses more powerful CLI commands under the hood.

## Helper Scripts Added

### 1. Setup Script

```bash
tools/setup_supabase_cli.sh
```
- Verifies CLI installation
- Authenticates using Strongbox credentials
- Tests connection
- Shows available projects

### 2. Helper Functions

```bash
source tools/supabase_helpers.sh
```

Loads convenient functions:
- `init_supabase_capsule` - Initialize Supabase
- `link_project <ref>` - Link to project
- `pull_schema` - Pull with feedback
- `push_migrations` - Push with confirmation
- `generate_types [file]` - Generate types
- `show_diff` - Schema differences
- `new_migration <name>` - Create migration
- `start_local` - Start local stack
- `stop_local` - Stop local stack
- `reset_local` - Reset with confirmation
- `lint_database` - Lint database
- `show_migrations` - Show history
- `squash_migrations` - Combine migrations

## Documentation Updates

### 1. Backend Dev Agent

`/.claude/agents/backend-specialist.md` - Lines 56-220

Now includes:
- CLI-first workflow documentation
- Complete command reference
- Helper function documentation
- When to use MCP (fallback scenarios)
- Recommended workflows for dev/staging/prod

### 2. Supabase Toolkit README

`/global/plugins/supabase-toolkit/README.md`

Updated to reflect:
- CLI as primary method
- MCP as secondary/fallback
- Local development emphasis
- Enhanced capabilities

### 3. New Documentation

**CLI_QUICK_REFERENCE.md** - Command cheatsheet
**CLI_MIGRATION_GUIDE.md** - This document
**QUICKSTART.md** - Updated for CLI-first

## Usage Examples

### Old Way (MCP)

```
User: "Generate TypeScript types from my database"

Backend Dev:
1. Uses MCP tool: generate_typescript_types
2. Returns TypeScript types
```

**Limited to TypeScript only**

### New Way (CLI)

```
User: "Generate types from my database"

Backend Dev:
1. Checks if linked project exists
2. Runs: supabase gen types typescript --linked > types/database.ts
3. Can also do Go, Swift, etc.
```

**Multi-language support + more reliable**

### New Capability: Local Dev

```
User: "I want to test this migration locally before pushing"

Backend Dev:
1. Runs: supabase start
2. Runs: supabase db reset (applies migrations)
3. User tests locally
4. When ready: supabase db push
```

**Not possible with MCP-only approach**

## Troubleshooting

### CLI Not Working

**Issue**: Backend Dev tries to use CLI but fails

**Solution**:
```bash
# Verify CLI installed
supabase --version

# Ensure credentials loaded
export $(grep -v '^#' .env | xargs)
echo $SUPABASE_ACCESS_TOKEN

# Test authentication
supabase projects list
```

### Not Linked

**Issue**: Commands fail with "not linked to project"

**Solution**:
```bash
cd your-capsule
supabase link --project-ref $SUPABASE_PROJECT_REF
```

### MCP Still Needed

**Issue**: Want to use MCP for specific operation

**Solution**: Backend Dev knows when to fall back to MCP:
- Structured introspection (list_tables)
- Security advisors (get_advisors)
- Programmatic operations
- Edge function management

Just ask naturally, agent will choose the right tool.

## Performance Comparison

### Type Generation

**MCP**: ~5-10 seconds (network round-trip)
**CLI**: ~2-3 seconds (direct connection)

### Schema Introspection

**MCP**: Multiple tool calls, structured but slower
**CLI**: Single command, complete output

### Local Testing

**MCP**: Not possible (requires remote project)
**CLI**: Full local stack, instant feedback

## Security Notes

✅ **Same credential storage** (Strongbox)
✅ **Same .env workflow** (sync_capsule_env.py)
✅ **CLI uses environment variables** (no stored tokens)
✅ **MCP still uses secure transport**
✅ **No reduction in security**

CLI actually improves security:
- Local testing reduces remote changes
- Diff detection catches unauthorized changes
- Linting catches SQL injection risks

## FAQ

**Q: Do I need to switch now?**
A: No, it's automatic. Backend Dev uses CLI by default but falls back to MCP when needed.

**Q: Will MCP be removed?**
A: No, it's kept as fallback for programmatic operations.

**Q: What if I don't have CLI installed?**
A: Install with: `brew install supabase/tap/supabase`

**Q: Do I need to change my natural language requests?**
A: No, talk to {{ORCHESTRATOR_NAME}} the same way. Backend Dev handles the rest.

**Q: Can I still use MCP exclusively?**
A: Yes, but you'll miss out on local dev, diffing, and advanced features.

**Q: What about Windows/Linux?**
A: CLI supports all platforms. Install instructions: https://supabase.com/docs/guides/cli

**Q: Does this affect other agents?**
A: No, only Backend Dev is affected (database work).

## Next Steps

1. **Verify CLI installed**: `supabase --version`
2. **Update to latest**: `brew upgrade supabase`
3. **Initialize existing capsules**: `supabase init && supabase link`
4. **Try local development**: `supabase start`
5. **Read CLI Quick Reference**: See `CLI_QUICK_REFERENCE.md`

## Resources

- **CLI Quick Reference**: `CLI_QUICK_REFERENCE.md`
- **Backend Dev Agent**: `/.claude/agents/backend-specialist.md`
- **Toolkit README**: `/global/plugins/supabase-toolkit/README.md`
- **Official CLI Docs**: https://supabase.com/docs/guides/cli
- **Helper Scripts**: `tools/setup_supabase_cli.sh`, `tools/supabase_helpers.sh`

---

**Summary**: CLI-first approach unlocks local development, schema diffing, advanced migrations, and multi-language type generation while keeping MCP as reliable fallback.

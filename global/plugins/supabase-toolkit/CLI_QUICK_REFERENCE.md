# Supabase CLI Quick Reference

Quick command reference for Backend Dev agent using Supabase CLI.

## Daily Workflow Commands

### Schema Development

```bash
# Start local Supabase
supabase start

# Check what's running
supabase status

# Pull remote schema
supabase db pull

# Show differences
supabase db diff

# Create new migration
supabase migration new add_feature_name

# Test migration locally
supabase db reset

# Push to remote
supabase db push

# Stop local
supabase stop
```

### Type Generation

```bash
# TypeScript from linked project
supabase gen types typescript --linked > types/database.ts

# TypeScript from local
supabase gen types typescript --local > types/database.ts

# Go types
supabase gen types go --linked > types/database.go

# Swift types
supabase gen types swift --linked > Types/Database.swift
```

### Migration Management

```bash
# List all migrations
supabase migration list

# Create new migration
supabase migration new migration_name

# Squash migrations into one
supabase migration squash

# Repair migration history
supabase migration repair --status reverted <version>
```

### Database Operations

```bash
# Dump data only
supabase db dump --data-only > backup.sql

# Dump schema only
supabase db dump --schema-only > schema.sql

# Lint database for issues
supabase db lint

# Reset to specific migration
supabase db reset --version 20231201000000
```

## First-Time Setup

```bash
# 1. Install CLI
brew install supabase/tap/supabase

# 2. Set environment variables (from .env)
export $(grep -v '^#' .env | xargs)

# 3. Initialize in capsule
supabase init

# 4. Link to project
supabase link --project-ref $SUPABASE_PROJECT_REF

# 5. Pull existing schema
supabase db pull

# 6. Start local development
supabase start
```

## Project Management

```bash
# List all projects
supabase projects list

# Link to project
supabase link --project-ref <project-ref>

# Unlink project
supabase unlink

# Check project status
supabase status
```

## Local Development

```bash
# Start all services
supabase start

# Start without specific services
supabase start --exclude storage-api,imgproxy

# Check what's running
supabase status

# View logs
supabase logs

# Stop all services
supabase stop

# Reset database
supabase db reset
```

## Edge Functions

```bash
# Create new function
supabase functions new function-name

# Serve functions locally
supabase functions serve

# Deploy function
supabase functions deploy function-name

# List functions
supabase functions list

# Delete function
supabase functions delete function-name
```

## Secrets Management

```bash
# Set secret
supabase secrets set SECRET_NAME=value

# List secrets
supabase secrets list

# Unset secret
supabase secrets unset SECRET_NAME
```

## Branching (Preview Branches)

```bash
# Create branch
supabase branches create branch-name

# List branches
supabase branches list

# Switch branch
supabase branches switch branch-name

# Delete branch
supabase branches delete branch-name
```

## Storage

```bash
# List buckets
supabase storage list

# Create bucket
supabase storage create bucket-name

# Upload file
supabase storage upload bucket-name/path/to/file local-file.txt

# Download file
supabase storage download bucket-name/path/to/file
```

## Debugging & Testing

```bash
# Enable debug output
supabase --debug <command>

# Test database connection
supabase db test

# Validate config
supabase config validate

# Run tests
supabase test run
```

## Helper Functions (BuilderOS)

Source the helper script first:
```bash
source tools/supabase_helpers.sh
```

Then use these functions:

```bash
init_supabase_capsule    # Initialize Supabase in current directory
link_project <ref>       # Link to Supabase project
pull_schema              # Pull remote schema
push_migrations          # Push with confirmation
generate_types [file]    # Generate TypeScript types
show_diff                # Show schema differences
new_migration <name>     # Create migration
start_local              # Start local stack
stop_local               # Stop local stack
reset_local              # Reset with confirmation
lint_database            # Lint database
show_migrations          # Migration history
squash_migrations        # Combine migrations
```

## Common Workflows

### New Feature Development

```bash
# 1. Start local
supabase start

# 2. Create migration
supabase migration new add_user_profiles

# 3. Edit migration file
# (use Write/Edit tools)

# 4. Test locally
supabase db reset

# 5. Check for issues
supabase db lint

# 6. Generate types
supabase gen types typescript --local > types/database.ts

# 7. Push to remote
supabase db push
```

### Schema Sync

```bash
# Pull latest from remote
supabase db pull

# Check for differences
supabase db diff

# If differences exist, create migration
supabase db diff -f manual_changes

# Review and apply
supabase db reset
supabase db push
```

### Local Testing

```bash
# Start fresh
supabase start

# Run migrations
supabase db reset

# Test your app
# (run application tests)

# Check status
supabase status

# Stop when done
supabase stop
```

### Production Deployment

```bash
# 1. Verify no drift
supabase db diff

# 2. Review pending migrations
supabase migration list

# 3. Dry run
supabase db push --dry-run

# 4. Deploy
supabase db push

# 5. Verify
supabase db diff
```

## Environment Variables

Required in `.env`:

```bash
SUPABASE_PROJECT_REF=your-project-ref
SUPABASE_ACCESS_TOKEN=your-access-token
```

Load with:
```bash
export $(grep -v '^#' .env | xargs)
```

## Useful Flags

```bash
--debug                  # Enable debug logging
--workdir <path>         # Specify project directory
--project-ref <ref>      # Specify project reference
--linked                 # Use linked project
--local                  # Use local database
--output <format>        # json, yaml, toml, env
--dry-run                # Preview changes
--yes                    # Skip confirmations
```

## Tips

1. **Always test locally first** - Use `supabase start` and `db reset`
2. **Use db diff** - Catch manual schema changes before they cause issues
3. **Lint regularly** - Run `db lint` to catch type errors early
4. **Generate types often** - After every schema change
5. **Keep local running** - Faster iteration with `supabase start`
6. **Use helper functions** - Source `tools/supabase_helpers.sh` for shortcuts
7. **Version control migrations** - Commit all migration files
8. **Document changes** - Add comments in migration files

## Troubleshooting

**CLI not authenticated:**
```bash
# Ensure token is set
echo $SUPABASE_ACCESS_TOKEN
# Or load from .env
export $(grep -v '^#' .env | xargs)
```

**Local services won't start:**
```bash
supabase stop
docker system prune
supabase start
```

**Migration conflicts:**
```bash
supabase migration repair --status reverted <version>
```

**Out of sync:**
```bash
supabase db pull
supabase db diff
```

## Documentation

- Official Docs: https://supabase.com/docs/guides/cli
- CLI Reference: https://supabase.com/docs/reference/cli
- GitHub: https://github.com/supabase/cli
- BuilderOS Integration: See `global/plugins/supabase-toolkit/README.md`

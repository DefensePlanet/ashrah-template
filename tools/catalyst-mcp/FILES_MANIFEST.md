# Catalyst MCP Server - Files Manifest

**Complete list of all files in the MCP server implementation**

---

## Source Files (TypeScript)

### `/src/index.ts` (Main Server)
- MCP server initialization
- Request handlers for tools and resources
- Error handling
- Graceful shutdown
- **Lines:** ~210

### `/src/tools.ts` (5 Tools)
- `create_task` - Create new tasks
- `update_task_status` - Update task status
- `get_task_tree` - Hierarchical task view
- `search_tasks` - Full-text search
- `link_document` - Link files to tasks
- Zod validation schemas
- **Lines:** ~270

### `/src/resources.ts` (4 Resources)
- `builderos://tasks/active` - All active tasks
- `builderos://tasks/active/{capsule}` - Active tasks per capsule
- `builderos://tasks/blocked` - Blocked tasks
- `builderos://tasks/{task_id}/context` - Full task context
- **Lines:** ~180

### `/src/database.ts` (Database Module)
- SQLite connection management
- Database initialization
- Query methods (10+)
- TypeScript interfaces
- **Lines:** ~450

---

## Configuration Files

### `/package.json`
- Dependencies and dev dependencies
- Build scripts
- Project metadata
- **Lines:** ~40

### `/tsconfig.json`
- TypeScript compiler configuration
- Strict mode enabled
- ES2022 target
- **Lines:** ~30

### `/.claude/mcp.json` (Project Root)
- Claude Code MCP server configuration
- Server command and environment
- **Lines:** ~10

---

## Build Outputs (Generated)

### `/dist/index.js` + `.map` + `.d.ts`
Compiled main server

### `/dist/tools.js` + `.map` + `.d.ts`
Compiled tools implementation

### `/dist/resources.js` + `.map` + `.d.ts`
Compiled resources implementation

### `/dist/database.js` + `.map` + `.d.ts`
Compiled database module

---

## Scripts

### `/start.sh`
- Executable startup script
- Sets PATH and environment
- Launches Node.js server
- **Lines:** ~15

### `/test-integration.sh`
- Integration test suite
- Verifies database, schema, build
- Tests queries and compilation
- **Lines:** ~60

---

## Documentation

### `/README.md` (Primary Documentation)
**Sections:**
- Overview and features
- Quick start guide
- Tool documentation (5 tools)
- Resource documentation (4 resources)
- Usage in Claude Code
- Database schema reference
- Environment variables
- Development guide
- Troubleshooting
- Architecture diagram
- **Lines:** ~550

### `/EXAMPLES.md` (Usage Examples)
**Contents:**
- 10 real-world examples
- Natural language patterns
- Expected tool calls
- Response formats
- Tips for best results
- Sample data reference
- **Lines:** ~450

### `/QUICK_REFERENCE.md` (Fast Lookup)
**Contents:**
- Common requests
- Tool summary table
- Resource URI patterns
- Status and priority enums
- Agent name formats
- Common capsules
- Troubleshooting quick tips
- **Lines:** ~150

### `/IMPLEMENTATION_SUMMARY.md` (Technical Details)
**Contents:**
- Complete deliverables list
- Architecture overview
- Testing results
- File structure
- Quality standards
- Performance metrics
- Success criteria
- **Lines:** ~600

### `/TESTING_GUIDE.md` (Testing Instructions)
**Contents:**
- 10 verification tests
- Manual server testing
- Integration test suite
- Database verification
- Troubleshooting tests
- Sample test sessions
- **Lines:** ~400

### `/FILES_MANIFEST.md` (This File)
**Contents:**
- Complete file listing
- File descriptions
- Line counts
- Organization
- **Lines:** ~200

---

## System Documentation (Project Root)

### `/docs/BUILDEROS_MCP_INTEGRATION.md`
**Contents:**
- MCP overview
- Catalyst capabilities
- Architecture
- Configuration
- Integration points
- Benefits
- Troubleshooting
- Future enhancements
- **Lines:** ~500

---

## Database

### `{{CATALYST_ROOT}}/tasks.db`
- SQLite database file
- Schema from `/api/db/schema.sql`
- Current size: ~136KB
- Tasks: 42+
- **Not in repository** (data file)

### `{{CATALYST_ROOT}}/api/db/schema.sql`
- Database schema definition
- Tables, indexes, triggers, views
- FTS5 configuration
- **Lines:** ~200
- **Referenced by MCP server**

---

## Dependencies (Installed)

### `/node_modules/` (~127 packages)
- `@modelcontextprotocol/sdk` and dependencies
- `better-sqlite3` and dependencies
- `zod` and dependencies
- TypeScript compiler and types
- **Not in repository** (dependencies)

### `/package-lock.json`
- Locked dependency versions
- **Lines:** ~5000+

---

## File Organization

```
tools/builderos-mcp/
├── src/                          # Source files (TypeScript)
│   ├── index.ts                 # Main server (210 lines)
│   ├── tools.ts                 # 5 tools (270 lines)
│   ├── resources.ts             # 4 resources (180 lines)
│   └── database.ts              # Database module (450 lines)
│
├── dist/                         # Build output (JavaScript)
│   ├── index.js                 # Compiled server
│   ├── tools.js                 # Compiled tools
│   ├── resources.js             # Compiled resources
│   ├── database.js              # Compiled database
│   └── *.d.ts, *.map            # Type definitions, source maps
│
├── node_modules/                 # Dependencies (127 packages)
│
├── package.json                  # NPM configuration
├── package-lock.json             # Locked dependencies
├── tsconfig.json                 # TypeScript config
│
├── start.sh                      # Startup script
├── test-integration.sh           # Integration tests
│
├── README.md                     # Primary documentation (550 lines)
├── EXAMPLES.md                   # Usage examples (450 lines)
├── QUICK_REFERENCE.md            # Fast lookup (150 lines)
├── IMPLEMENTATION_SUMMARY.md     # Technical details (600 lines)
├── TESTING_GUIDE.md              # Testing instructions (400 lines)
└── FILES_MANIFEST.md             # This file (200 lines)
```

---

## Total Line Counts

### Source Code (TypeScript)
- `src/index.ts`: ~210 lines
- `src/tools.ts`: ~270 lines
- `src/resources.ts`: ~180 lines
- `src/database.ts`: ~450 lines
- **Total source:** ~1,110 lines

### Documentation
- `README.md`: ~550 lines
- `EXAMPLES.md`: ~450 lines
- `QUICK_REFERENCE.md`: ~150 lines
- `IMPLEMENTATION_SUMMARY.md`: ~600 lines
- `TESTING_GUIDE.md`: ~400 lines
- `FILES_MANIFEST.md`: ~200 lines
- **Total docs:** ~2,350 lines

### Configuration & Scripts
- `package.json`: ~40 lines
- `tsconfig.json`: ~30 lines
- `start.sh`: ~15 lines
- `test-integration.sh`: ~60 lines
- **Total config:** ~145 lines

### Grand Total
**~3,605 lines** of source code, documentation, and configuration

---

## File Purposes

### For Development
- `src/*.ts` - Source code
- `tsconfig.json` - TypeScript config
- `package.json` - Dependencies

### For Deployment
- `dist/*.js` - Compiled code
- `start.sh` - Startup script
- `.claude/mcp.json` - Integration config

### For Testing
- `test-integration.sh` - Test suite
- Sample data in database

### For Users
- `README.md` - Complete reference
- `EXAMPLES.md` - How to use
- `QUICK_REFERENCE.md` - Fast lookup
- `TESTING_GUIDE.md` - Verification

### For Maintainers
- `IMPLEMENTATION_SUMMARY.md` - Technical overview
- `FILES_MANIFEST.md` - This file
- Source code comments

---

## File Relationships

```
.claude/mcp.json
    ↓ (references)
start.sh
    ↓ (launches)
dist/index.js
    ↓ (uses)
dist/database.js
    ↓ (connects to)
{{CATALYST_ROOT}}/tasks.db
    ↑ (schema from)
{{CATALYST_ROOT}}/api/db/schema.sql
```

---

## Maintenance Files

### To Update on Code Changes
- `src/*.ts` - Source code
- `dist/*.js` - Rebuild with `npm run build`
- `README.md` - Update if API changes
- `EXAMPLES.md` - Update for new features

### To Update on Schema Changes
- `/api/db/schema.sql` - Database schema
- `src/database.ts` - TypeScript interfaces
- `README.md` - Schema documentation
- Re-run database initialization

### To Update on Dependency Changes
- `package.json` - Add/remove dependencies
- `package-lock.json` - Lock versions
- Rebuild with `npm install && npm run build`

---

## Excluded from Repository

These files are generated or data files:

- `/dist/*` - Build output (regenerate with `npm run build`)
- `/node_modules/*` - Dependencies (install with `npm install`)
- `*.map` - Source maps (generated with build)
- `*.d.ts` - Type definitions (generated with build)
- `{{CATALYST_ROOT}}/tasks.db` - Database (data file)

---

## Critical Files for Production

**Must exist and be correct:**

1. `src/index.ts` - Server won't start without it
2. `src/database.ts` - Database access fails without it
3. `start.sh` - Claude Code can't start server
4. `.claude/mcp.json` - Claude Code won't recognize server
5. `{{CATALYST_ROOT}}/tasks.db` - No data without it
6. `dist/*.js` - Runtime code (build from src)

---

## File Checksums (for Integrity)

To verify files haven't been corrupted:

```bash
cd {{CATALYST_ROOT}}/tools/builderos-mcp
shasum -a 256 src/*.ts package.json tsconfig.json
```

---

**This manifest documents all files in the Catalyst MCP Server implementation.**

**Last updated:** 2025-11-04
**Version:** 1.0.0

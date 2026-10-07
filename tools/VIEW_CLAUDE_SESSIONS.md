# Claude Code Session Viewer Guide

**Created:** 2025-11-01
**Purpose:** Access and view your Claude Code sessions stored in iTerm2

---

## Storage Locations

### Primary Storage (Live Sessions)
```
~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/
```
- **Retention:** 7 days
- **Format:** .jsonl (JSON Lines)
- **Content:** Full conversation transcripts

### Backup Storage (Catalyst Sync)
```
{{CATALYST_ROOT}}/global/claude-config/projects/-Users-{{USER_NAME}}-Catalyst/
```
- Synced automatically on session end
- Same 7-day retention policy

### Session Metadata
```
{{CATALYST_ROOT}}/logs/claude-hooks/<session-id>/
```
- Contains `stop_event.json` with session metadata
- Includes timestamps, working directory, transcript path

---

## Current Session Statistics

**As of 2025-11-01:**
- **Today's sessions:** 153
- **Last 7 days:** 1,345 sessions
- **Largest session today:** 3d59cba5 (22MB, 1,663 messages)

---

## Quick Commands

### List Recent Sessions
```bash
find ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/ -name "*.jsonl" -newermt "2025-11-01" -type f | \
while read f; do
  id=$(basename "$f" .jsonl)
  time=$(stat -f "%Sm" -t "%H:%M:%S" "$f")
  msgs=$(wc -l < "$f" | xargs)
  size=$(ls -lh "$f" | awk '{print $5}')
  printf "%-40s | %s | %4s msgs | %6s\n" "$id" "$time" "$msgs" "$size"
done | sort -t'|' -k2 -r | head -20
```

### View a Specific Session
```bash
# Replace SESSION_ID with actual ID
jq -r '.[] | "\n[\(.timestamp // "N/A")]\n\(.type // "unknown"):\n\(.content // .text // "N/A")\n"' \
  ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/SESSION_ID.jsonl | less
```

### Find Largest Sessions
```bash
find ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/ -name "*.jsonl" -newermt "2025-11-01" -type f \
  -exec ls -lh {} \; | sort -k5 -hr | head -10
```

### Search Sessions by Content
```bash
# Search for specific text across all sessions
grep -l "search term" ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/*.jsonl
```

### Get Session Summary
```bash
# Show session message count and first/last timestamps
for f in ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/*.jsonl; do
  echo "=== $(basename $f) ==="
  echo "Messages: $(wc -l < "$f")"
  jq -r 'select(.timestamp) | .timestamp' "$f" | head -1 | xargs echo "Started:"
  jq -r 'select(.timestamp) | .timestamp' "$f" | tail -1 | xargs echo "Ended:"
  echo
done | head -50
```

---

## Today's Top 10 Largest Sessions

| Session ID | Size | Messages | Time |
|------------|------|----------|------|
| 3d59cba5-e214-421b-9804-e1b1b9e91934 | 22MB | 1,663 | 13:26 |
| 3dbdef99-ca0f-425c-ac47-4c3096e740ab | 3.8MB | 1,370 | 05:35 |
| 05fd28e9-b32b-4210-b014-11221a864809 | 1.5MB | 675 | 02:42 |
| 8517b793-110d-4300-9fbb-6c7df6ea3ae2 | 783K | 163 | 13:52 |
| agent-52c1c9d4 | 697K | 130 | 01:18 |
| agent-7fe59d48 | 678K | 93 | 01:27 |
| 5a50c901-da61-4f4a-bc21-bd7af9f255ea | 206K | 51 | 14:01 |
| cd5e25b9-7933-4b30-a42f-f63910ad99dd | 92K | 41 | 13:54 |
| ea361c7e-d3b2-4691-a99a-ff7f8a2c873f | 91K | 19 | 02:23 |
| 6825cf80-c3a8-4bdd-a979-31f175795584 | 87K | 22 | 13:50 |

---

## Session File Format

Sessions are stored as `.jsonl` (JSON Lines) files. Each line is a JSON object representing:
- User messages
- Assistant responses
- Tool calls and results
- System messages
- Timestamps

**Example viewing with jq:**
```bash
# Pretty print the first message
jq -r '.[0]' ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/SESSION_ID.jsonl

# Extract only user messages
jq -r 'select(.type == "user") | .content' SESSION_ID.jsonl

# Extract tool uses
jq -r 'select(.type == "tool_use") | "\(.name): \(.input)"' SESSION_ID.jsonl
```

---

## Helper Script

A session viewer script has been created at `/tmp/session_viewer.sh`:

```bash
# List 20 most recent sessions
/tmp/session_viewer.sh list

# View a specific session
/tmp/session_viewer.sh view SESSION_ID

# Show 10 largest sessions
/tmp/session_viewer.sh largest
```

**To install permanently:**
```bash
cp /tmp/session_viewer.sh ~/Catalyst/tools/session_viewer.sh
chmod +x ~/Catalyst/tools/session_viewer.sh
```

---

## Session Lifecycle

1. **Active Session** - While you're using Claude Code in iTerm2
2. **Stop Hook Fires** - When you close the session
3. **Export to Catalyst** - `export_session_transcript.py` copies to backup location
4. **Session Logging** - `simple_capsule_update.py` updates capsule context
5. **7-Day Retention** - Sessions older than 7 days are archived/deleted

---

## Advanced Usage

### Export Session to Markdown
```bash
#!/bin/bash
SESSION_ID="$1"
OUTPUT="${SESSION_ID}_export.md"

echo "# Session: $SESSION_ID" > "$OUTPUT"
echo "Exported: $(date)" >> "$OUTPUT"
echo >> "$OUTPUT"

jq -r '.[] | "## \(.timestamp // "N/A")\n**Type:** \(.type // "unknown")\n\n\(.content // .text // "N/A")\n\n---\n"' \
  ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/${SESSION_ID}.jsonl >> "$OUTPUT"

echo "✅ Exported to $OUTPUT"
```

### Analyze Session Activity
```bash
# Count tool usage across all sessions
find ~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/ -name "*.jsonl" -mtime -7 -type f \
  -exec jq -r 'select(.type == "tool_use") | .name' {} \; | \
  sort | uniq -c | sort -rn
```

### Find Sessions by Working Directory
```bash
# Find all sessions that worked on a specific project
grep -l '"cwd".*"capsules/your-project"' \
  {{CATALYST_ROOT}}/logs/claude-hooks/*/stop_event.json
```

---

## Troubleshooting

### Session Not Found
- Check if session is older than 7 days (may be archived)
- Verify you're looking in the correct scope directory
- Sessions might be in a different scope: `~/.claude/projects/-Users-{{USER_NAME}}/`

### Empty Session File
- Session may have been interrupted
- Check metadata in `{{CATALYST_ROOT}}/logs/claude-hooks/SESSION_ID/`

### Large Session Files
- Sessions over 1MB indicate long conversations
- Consider exporting important sessions before 7-day expiration
- Use `jq` with pagination: `jq -r '.[] | "\(.type): \(.content)"' file.jsonl | less`

---

## Integration with Catalyst

Catalyst automatically tracks sessions through hooks:

1. **`export_session_transcript.py`** - Copies transcripts to Catalyst
2. **`simple_capsule_update.py`** - Updates capsule session logs
3. **`on_session_end.py`** - Writes session metadata

**View capsule-specific sessions:**
```bash
cat capsules/YOUR_CAPSULE/context/session_log.md
```

---

## Summary

**Your sessions are stored and accessible for 7 days!**

**Primary Location:** `~/.claude/projects/-Users-{{USER_NAME}}-Catalyst/`
**Backup Location:** `{{CATALYST_ROOT}}/global/claude-config/projects/`
**Today's Count:** 153 sessions
**Last Week:** 1,345 sessions

Use the commands and scripts above to explore your session history, recover conversations, or analyze your Claude Code usage patterns.

---

**Created by:** {{ORCHESTRATOR_NAME}}
**Date:** 2025-11-01
**Catalyst Version:** Current

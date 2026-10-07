# Drafts Scripts Library

JavaScript actions for the Drafts app, managed by the 2nd Brain Wizard.

## Why JavaScript Actions?

Drafts' AppleScript support is limited to **creating drafts only** - you cannot query or modify existing drafts via AppleScript. The official method for programmatic access is JavaScript actions run inside the app.

## Usage

Scripts can be triggered via URL scheme:
```bash
open "drafts://runAction?action=Action%20Name"
```

Or installed as Drafts Actions and run from within the app.

## Installation

1. Open Drafts app
2. Go to Actions → Manage Actions → + (Create Action)
3. Add a "Script" step
4. Paste the JavaScript from the appropriate `.js` file
5. Save the action with the matching name

## Scripts

| Script | Purpose | Trigger URL |
|--------|---------|-------------|
| `remove-duplicates.js` | Find exact duplicates, trash newer copies | `drafts://runAction?action=Remove%20Duplicates` |
| `tag-workouts.js` | Find gym workout logs and tag them with "recorded workouts" | `drafts://runAction?action=Tag%20Workouts` |
| `cleanup-{{ORCHESTRATOR_NAME_LOWER}}-tests.js` | Remove test drafts created during Catalyst integration testing | `drafts://runAction?action=Cleanup%20{{ORCHESTRATOR_NAME}}%20Tests` |

## Important: SQLite vs JavaScript Actions

**READ Operations:** Can use SQLite database directly (fast, no UI required)
```
~/Library/Group Containers/GTFQ98J4YG.com.agiletortoise.Drafts/DraftStore.sqlite
```

**WRITE Operations:** Must use JavaScript Actions
- SQLite is a local cache that gets overwritten by iCloud/CloudKit sync
- Direct SQL writes will appear to work but will be reverted on next sync
- JavaScript Actions properly sync changes through Drafts' sync system

## API Reference

- [Drafts Scripting Reference](https://scripting.getdrafts.com/)
- [Draft Class](https://scripting.getdrafts.com/classes/Draft.html)
- [URL Schemes](https://docs.getdrafts.com/docs/automation/urlschemes)

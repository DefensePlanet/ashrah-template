# Schedule - Dynamic Task Scheduling

<schedule-skill>

## Purpose
Schedule reminders and tasks for future execution. Claude can now set things to happen at specific times.

## Trigger Phrases
- "Remind me to..."
- "At [time], do..."
- "Schedule..."
- "Every [day/morning/week], ..."
- "In [X] hours, check..."
- "Tomorrow at [time], ..."

## Location
**Automation directory:** `{{CATALYST_ROOT}}/automation/`

## Usage

### Quick Reminders
```bash
cd {{CATALYST_ROOT}}/automation/scheduler
./scheduler.py add "Call the dentist" --at "3pm"
```

### Recurring Tasks
```bash
./scheduler.py add "Check inbox" --every "day" --at "9am"
./scheduler.py add "Morning standup" --every "weekdays" --at "9:30am"
```

### Work Tasks (Claude executes, not just reminds)
```bash
./scheduler.py add "Review system health and report issues" --at "6pm" --type work
```

### Natural Language
```bash
./scheduler.py parse "Remind me to take a break at 3pm" --create
```

### Management
```bash
./scheduler.py list      # List all scheduled jobs
./scheduler.py remove <job_id>   # Remove a job
```

## Job Types

| Type | What Happens |
|------|--------------|
| `reminder` | Sends notification with the reminder text |
| `work` | Invokes Claude Code to actually do the task |

## Storage
- System jobs: `{{CATALYST_ROOT}}/automation/system-jobs.yaml`
- Dynamic jobs: `{{CATALYST_ROOT}}/automation/jobs.json`
- Logs: `{{CATALYST_ROOT}}/registry/automation/`

</schedule-skill>

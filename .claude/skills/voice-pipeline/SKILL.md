# /voice-pipeline — Voice Recording Processing

Process voice recordings from Apple Watch (Just Press Record + Voice Memos) into transcribed, categorized files on iCloud Drive.

## Commands

### Process New Recordings
```bash
{{CATALYST_ROOT}}/tools/voice-pipeline/.venv/bin/python {{CATALYST_ROOT}}/tools/voice-pipeline/pipeline.py process
```

### Process with Limit
```bash
{{CATALYST_ROOT}}/tools/voice-pipeline/.venv/bin/python {{CATALYST_ROOT}}/tools/voice-pipeline/pipeline.py process --limit 5
```

### Check Status
```bash
{{CATALYST_ROOT}}/tools/voice-pipeline/.venv/bin/python {{CATALYST_ROOT}}/tools/voice-pipeline/pipeline.py status
```

### Reprocess Failed
```bash
{{CATALYST_ROOT}}/tools/voice-pipeline/.venv/bin/python {{CATALYST_ROOT}}/tools/voice-pipeline/pipeline.py reprocess --failed
```

### Force Diarization
```bash
{{CATALYST_ROOT}}/tools/voice-pipeline/.venv/bin/python {{CATALYST_ROOT}}/tools/voice-pipeline/pipeline.py reprocess --file /path/to/recording.m4a --diarize
```

### Daemon Control
```bash
# Start watcher daemon
launchctl load ~/Library/LaunchAgents/com.catalyst.voice-pipeline.plist

# Stop watcher daemon
launchctl unload ~/Library/LaunchAgents/com.catalyst.voice-pipeline.plist

# Check daemon status
launchctl list | grep voice-pipeline
```

## Categories
- **prayer** — Direct communication with God (prayers/, on iCloud)
- **daily-log** — Personal reflections and daily updates (daily/, on iCloud)
- **meditation** — Breathing/centering exercises (meditation/, on iCloud)
- **ambient** — Accidental recordings, background noise (ambient/, on iCloud)

## Output
Organized archive at `~/Library/Mobile Documents/com~apple~CloudDocs/Voice Archive/`
Each recording produces: cleaned WAV + transcript .txt + metadata .json

## Source Directories
- Just Press Record: `~/Library/Mobile Documents/iCloud~com~openplanetsoftware~just-press-record/Documents/`
- Voice Memos: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/`

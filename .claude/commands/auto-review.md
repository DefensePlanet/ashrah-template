---
description: "Toggle automatic code review on/off"
---

Toggle the automatic code review hook. Check the current state and flip it.

## Instructions

1. Check if `/tmp/catalyst-auto-review-disabled` exists
2. If it exists → DELETE it (re-enable auto-review) → tell {{USER_NAME}}: "🟢 Auto code review ON"
3. If it doesn't exist → CREATE it (disable auto-review) → tell {{USER_NAME}}: "🔴 Auto code review OFF"

Use the Bash tool to check and toggle:
```bash
if [ -f /tmp/catalyst-auto-review-disabled ]; then
  rm /tmp/catalyst-auto-review-disabled
  echo "ENABLED"
else
  touch /tmp/catalyst-auto-review-disabled
  echo "DISABLED"
fi
```

Report the result with the appropriate emoji. Nothing else needed.

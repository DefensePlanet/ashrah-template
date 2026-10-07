---
description: "Manual Codex peer review consultation on specific files or changes"
---

# Codex Peer Review Command

You are being invoked to facilitate a manual Codex peer review consultation.

## Task

The user wants Codex's perspective on specific code, a design decision, or to validate findings from the automatic Code Reviewer.

## Your Role

1. **Understand the request:**
   - What file(s) or code sections need review?
   - What specific concerns or questions does the user have?
   - Is this about architecture, implementation, or both?

2. **Prepare BridgeHub request:**
   - Use `peer_review` action for general code review
   - Use `codex_fix` action if asking for specific fix suggestions
   - Include relevant code snippets (max 60 lines)
   - Provide clear context about what to review

3. **Invoke BridgeHub:**
   ```bash
   /opt/homebrew/bin/node {{CATALYST_ROOT}}/tools/bridgehub/dist/bridgehub.js --request '{
     "version": "bridgehub/1.0",
     "action": "peer_review",
     "capsule": "'"$(pwd)"'",
     "session": "peer-review-'"$(date +%Y-%m-%d-%H%M%S)"'",
     "payload": {
       "file_path": "...",
       "review_context": "...",
       "snippets": [...]
     }
   }'
   ```

4. **Synthesize perspectives:**
   - Present Codex's concerns and recommendations
   - Compare with Code Reviewer findings if available
   - Highlight areas of agreement and disagreement
   - Provide clear recommendations

5. **Log consultation:**
   - Document in quality.db if significant insights
   - Note any patterns for Phase 5 learning

## Example Usage

```bash
/codex-review path/to/file.py
```

This is a **manual, on-demand consultation** - not part of the automatic pre-commit workflow.

## When to Use

- Complex architectural decisions
- Critical code sections needing extra scrutiny
- Second opinion when Code Reviewer flags concerns
- Learning opportunity to understand different approaches
- Consensus building between AI perspectives

Proceed with facilitating the Codex consultation based on the user's request.

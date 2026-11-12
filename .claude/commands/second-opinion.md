---
description: "Codex second opinion on a finding before it goes out"
---

# Codex Second Opinion

Get an independent Codex critique of an investigation finding (not code) before it goes to a third party.

1. **Assemble the payload** from the current conversation. Write it to a file in your scratchpad directory (e.g. `<scratchpad>/second-opinion-payload.md`) with exactly these sections:
   - `# Claim` — the conclusion as you would state it to the third party, one or two sentences.
   - `# Evidence` — the concrete observations behind it: numbers, error codes, reproductions, what was ruled out, and what could not be tested. Facts only, no interpretation. Never include secrets, tokens, or credentials.
   - `# Question` — optional; what you most want checked. If {{USER_NAME}} passed arguments, use them here: $ARGUMENTS
2. **Run it:**
   ```bash
   python3 {{CATALYST_ROOT}}/tools/codex-second-opinion/second_opinion.py --payload-file <scratchpad>/second-opinion-payload.md
   ```
   Allow up to ~3 minutes. The script always exits 0; if stdout is empty, report the one-line reason from stderr and stop.
3. **Relay** Codex's critique verbatim under a `## Codex says` heading. Do not trim or paraphrase it.
4. **State whether you agree**, under `## {{ORCHESTRATOR_NAME}}'s take`: agree / partly agree / disagree, with brief reasoning, and how the claim should change (if at all) before it goes out. Include Codex's verdict line (SUPPORTED / PARTIALLY SUPPORTED / NOT SUPPORTED).

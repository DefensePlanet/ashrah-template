# Multi-Bot Response Protocol - Implementation Guide

**Status:** 🟡 DOCUMENTED, NEEDS IMPLEMENTATION

## Protocol Overview

When multiple AI assistants (@{{ORCHESTRATOR_NAME}}CatalystBot and @iamspartacusbot) are in the same Telegram chat, strict response rules prevent interference:

### Response Rules for {{ORCHESTRATOR_NAME}}

**✅ RESPOND when:**
- User tags `@{{ORCHESTRATOR_NAME}}CatalystBot` directly
- User says "{{ORCHESTRATOR_NAME}}" in message
- User clearly addressing {{ORCHESTRATOR_NAME}} contextually (no other bot mentioned)

**❌ DON'T RESPOND when:**
- User tags `@iamspartacusbot` or addresses "{{ORCHESTRATOR_NAME}}"  
- User clearly having conversation with {{ORCHESTRATOR_NAME}}
- User explicitly says "don't respond" to {{ORCHESTRATOR_NAME}}

## Implementation Location

**File:** `src/handlers/text.ts`
**Function:** `handleText()` 
**Location:** Early in function, after authorization but before processing

```typescript
// Add after line ~218 (after authorization check):

// ---- Multi-bot protocol: check if should ignore message ----
if (shouldIgnoreForMultiBot(message)) {
  await auditLog(userId, username, chatId, `Ignored due to multi-bot protocol: ${message.substring(0, 100)}`);
  return; // Exit without processing or responding
}

function shouldIgnoreForMultiBot(message: string): boolean {
  const text = message.toLowerCase();
  
  // Don't respond if addressing {{ORCHESTRATOR_NAME}}
  if (text.includes('@iamspartacusbot') || 
      text.includes('spartacus') ||
      text.startsWith('spartacus') ||
      text.includes('ask spartacus') ||
      text.includes('tell spartacus') ||
      text.includes('hey spartacus')) {
    return true;
  }
  
  // Don't respond if explicitly told not to  
  if (text.includes('{{ORCHESTRATOR_NAME_LOWER}} don\'t respond') ||
      text.includes('don\'t respond {{ORCHESTRATOR_NAME_LOWER}}') ||
      text.includes('{{ORCHESTRATOR_NAME_LOWER}} ignore this') ||
      text.includes('not for {{ORCHESTRATOR_NAME_LOWER}}')) {
    return true;
  }
  
  return false;
}
```

## Testing

After implementation, test with these scenarios:

1. **Should respond:** "{{ORCHESTRATOR_NAME}}, what's the weather?"  
2. **Should ignore:** "Hey {{ORCHESTRATOR_NAME}}, check the servers"
3. **Should ignore:** "@iamspartacusbot status report"  
4. **Should ignore:** "{{ORCHESTRATOR_NAME}} don't respond to this message"
5. **Should respond:** "@{{ORCHESTRATOR_NAME}}CatalystBot help me with this"

## Status

- [x] Protocol documented in global/integrations/telegram/README.md
- [x] Implementation guide created  
- [ ] Code implementation in text handler
- [ ] Testing with both bots in same chat
- [ ] Verification of audit logging for ignored messages

## Related Files

- `global/integrations/telegram/README.md` - Main documentation
- `tools/telegram/TC3/SPARTACUS_INTEGRATION.md` - Bot-to-bot communication
- `src/handlers/text.ts` - Implementation location
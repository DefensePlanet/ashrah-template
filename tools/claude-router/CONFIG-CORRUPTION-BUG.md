# Router Web UI Config Corruption Bug

**Status:** 🐛 Active Bug
**Severity:** High (breaks provider transformers)
**Affects:** Claude Code Router Web UI (`/router` dashboard)

## Issue

When editing providers through the Web UI, transformer configs get corrupted with metadata fields that break request transformation.

## Symptoms

After editing a provider via Web UI:
- Provider config has `transformer.endpoint` field (metadata)
- Provider config has `transformer.use` array **empty**
- Requests fail with 400 errors because transformer isn't applied

## Root Cause

### API Endpoint: `/api/transformers`

Returns transformer metadata for UI display:

```typescript
// src/server.ts line 86-96
server.app.get("/api/transformers", async () => {
  const transformers = server.app._server!.transformerService.getAllTransformers();
  const transformerList = Array.from(transformers.entries()).map(
    ([name, transformer]: any) => ({
      name,
      endpoint: transformer.endPoint || null,  // ← Metadata for display
    })
  );
  return { transformers: transformerList };
});
```

### API Endpoint: `/api/config` (POST)

Saves config without validation:

```typescript
// src/server.ts line 99-109
server.app.post("/api/config", async (req, reply) => {
  const newConfig = req.body;

  // Backup existing config file if it exists
  const backupPath = await backupConfigFile();

  await writeConfigFile(newConfig);  // ← Saves whatever UI sends!
  return { success: true, message: "Config saved successfully" };
});
```

### UI Component: Providers.tsx

The UI likely builds provider objects that include the `endpoint` metadata when saving. Needs investigation.

## Expected Behavior

**Transformer config should only contain:**
```json
{
  "transformer": {
    "use": ["bifrost-chat-endpoint"]
  }
}
```

**NOT:**
```json
{
  "transformer": {
    "endpoint": "bifrost-chat-endpoint",  // ← Metadata, should not be saved
    "use": []                              // ← Empty because metadata was used instead
  }
}
```

## Fix Required

### Option 1: Validate on API (Recommended)

In `src/server.ts`, validate/sanitize config before saving:

```typescript
server.app.post("/api/config", async (req, reply) => {
  const newConfig = req.body;

  // Sanitize provider transformer configs
  if (newConfig.Providers) {
    newConfig.Providers.forEach(provider => {
      if (provider.transformer && provider.transformer.endpoint) {
        // Remove metadata field, keep only use array
        delete provider.transformer.endpoint;
      }
    });
  }

  await writeConfigFile(newConfig);
  return { success: true };
});
```

### Option 2: Fix UI (Also needed)

In `ui/src/components/Providers.tsx`, ensure transformer config only includes `use` array when building provider objects to save.

## Impact

- **High:** Completely breaks transformer functionality
- **Silent:** No error when saving, only fails when using the provider
- **Data corruption:** Overwrites valid config with invalid config
- **Persistent:** Corrupted config survives router restarts

## Workaround

Until fixed:
1. **Don't use Web UI to edit providers**
2. **Edit source template:** `tools/claude-router/config/builderos.json`
3. **Sync to runtime:**
   ```bash
   docker exec builderos-claude-router cp /config/builderos.json /root/.claude-code-router/config.json
   docker restart builderos-claude-router
   ```

## Testing

After fix, verify:
1. Edit provider via Web UI
2. Save config
3. Check `~/.claude-code-router/config.json`
4. Verify transformer has only `{"use": [...]}` with no `endpoint` field
5. Test requests actually use the transformer

## Related Issues

- Kimi K2 400 error (caused by this bug)
- Any provider with transformers may be affected

---

**Reported:** 2025-11-10
**Needs:** Backend Developer or Frontend Developer to fix

import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { createHash } from "node:crypto";
import type { AgentIndexEntry, SyncManifest } from "./types.js";

const OUTPUT_DIR = join(process.env.CATALYST_ROOT ?? "{{CATALYST_ROOT}}", "tools", "telegram", "shared-core", "output");
const MANIFEST_PATH = join(OUTPUT_DIR, "sync-manifest.json");

/** Build a sync manifest from current state */
export function buildManifest(agents: AgentIndexEntry[]): SyncManifest {
  return {
    version: "0.1.0",
    generated_at: new Date().toISOString(),
    schema_version: 1,
    agents: agents.map(a => ({
      id: a.id,
      source_path: a.sourceFile,
      source_hash: a.sourceHash,
      index_hash: createHash("sha256")
        .update(JSON.stringify({ name: a.name, capabilities: a.capabilities, department: a.department }))
        .digest("hex")
        .slice(0, 12),
      pack_hash: null, // Set by condensation pipeline
      last_synced: new Date().toISOString(),
    })),
  };
}

/** Load existing manifest for drift detection */
export async function loadManifest(): Promise<SyncManifest | null> {
  try {
    const content = await readFile(MANIFEST_PATH, "utf-8");
    return JSON.parse(content);
  } catch {
    return null;
  }
}

/** Save manifest */
export async function saveManifest(manifest: SyncManifest): Promise<void> {
  await writeFile(MANIFEST_PATH, JSON.stringify(manifest, null, 2));
}

/** Check for drift between current agents and saved manifest */
export async function checkDrift(agents: AgentIndexEntry[]): Promise<{
  drifted: { id: string; name: string; oldHash: string; newHash: string }[];
  added: string[];
  removed: string[];
}> {
  const existing = await loadManifest();
  if (!existing) {
    return { drifted: [], added: agents.map(a => a.id), removed: [] };
  }

  const existingMap = new Map(existing.agents.map(a => [a.id, a]));
  const currentMap = new Map(agents.map(a => [a.id, a]));

  const drifted: { id: string; name: string; oldHash: string; newHash: string }[] = [];
  const added: string[] = [];
  const removed: string[] = [];

  for (const agent of agents) {
    const prev = existingMap.get(agent.id);
    if (!prev) {
      added.push(agent.id);
    } else if (prev.source_hash !== agent.sourceHash) {
      drifted.push({
        id: agent.id,
        name: agent.name,
        oldHash: prev.source_hash,
        newHash: agent.sourceHash,
      });
    }
  }

  for (const prev of existing.agents) {
    if (!currentMap.has(prev.id)) {
      removed.push(prev.id);
    }
  }

  return { drifted, added, removed };
}

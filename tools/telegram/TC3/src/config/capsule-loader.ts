/**
 * Capsule Loader — Multi-capsule registry for TC3 Telegram bot.
 *
 * Maps Telegram chat IDs to capsule configurations (working directory, name, mode).
 * DMs (positive chatIds) and unbound chats fall back to the default capsule.
 * Group chats (negative chatIds) can be bound to specific capsules via /capsule bind.
 */

import { readFileSync, writeFileSync, existsSync, renameSync } from "fs";
import { resolve, dirname } from "path";
import { homedir } from "os";

// ============== Types ==============

export interface CapsuleConfig {
  capsuleId?: string;
  workingDir: string;
  name: string;
  defaultMode: "pi" | "cli";
}

export interface CapsuleRegistry {
  defaultCapsule: CapsuleConfig;
  chats: Record<string, CapsuleConfig>;
}

// ============== Registry Path ==============

const REGISTRY_PATH = resolve(dirname(import.meta.dir), "config", "capsule-registry.json");

// ============== In-memory cache ==============

let cachedRegistry: CapsuleRegistry | null = null;

// ============== Functions ==============

/**
 * Load the capsule registry from disk.
 * Caches in memory after first load; call with force=true to re-read.
 */
export function loadCapsuleRegistry(force = false): CapsuleRegistry {
  if (cachedRegistry && !force) {
    return cachedRegistry;
  }

  try {
    if (!existsSync(REGISTRY_PATH)) {
      // Return sensible default
      cachedRegistry = {
        defaultCapsule: {
          workingDir: process.env.CATALYST_ROOT || resolve(homedir(), "Catalyst"),
          name: "Catalyst",
          defaultMode: "pi",
        },
        chats: {},
      };
      return cachedRegistry;
    }

    const raw = readFileSync(REGISTRY_PATH, "utf-8");
    const parsed = JSON.parse(raw) as CapsuleRegistry;

    // Validate required fields
    if (!parsed.defaultCapsule || !parsed.defaultCapsule.workingDir) {
      throw new Error("Invalid registry: missing defaultCapsule.workingDir");
    }

    cachedRegistry = parsed;
    return cachedRegistry;
  } catch (error) {
    console.error(`[CapsuleLoader] Failed to load registry: ${error}`);
    // Fallback to safe defaults
    cachedRegistry = {
      defaultCapsule: {
        workingDir: process.env.CATALYST_ROOT || resolve(homedir(), "Catalyst"),
        name: "Catalyst",
        defaultMode: "pi",
      },
      chats: {},
    };
    return cachedRegistry;
  }
}

/**
 * Get the capsule config for a specific chat ID.
 *
 * Returns the bound capsule config if one exists for this chat,
 * otherwise returns the default capsule (Catalyst root).
 */
export function getCapsuleConfig(chatId: number): CapsuleConfig {
  const registry = loadCapsuleRegistry();
  const chatKey = String(chatId);

  if (registry.chats[chatKey]) {
    return registry.chats[chatKey];
  }

  return registry.defaultCapsule;
}

/**
 * Bind a Telegram chat to a capsule.
 * Persists the binding to disk.
 */
export function bindCapsule(
  chatId: number,
  capsuleId: string,
  workingDir: string,
  name: string
): void {
  if (!existsSync(workingDir)) {
    console.warn(`[CapsuleLoader] Warning: workingDir does not exist: ${workingDir}`);
  }

  const registry = loadCapsuleRegistry();
  const chatKey = String(chatId);

  registry.chats[chatKey] = {
    capsuleId,
    workingDir,
    name,
    defaultMode: "pi",
  };

  writeRegistryToDisk(registry);
  console.log(`[CapsuleLoader] Bound chat ${chatId} -> ${name} (${workingDir})`);
}

/**
 * Unbind a Telegram chat from its capsule.
 * The chat will fall back to the default capsule.
 */
export function unbindCapsule(chatId: number): void {
  const registry = loadCapsuleRegistry();
  const chatKey = String(chatId);

  if (registry.chats[chatKey]) {
    const old = registry.chats[chatKey];
    delete registry.chats[chatKey];
    writeRegistryToDisk(registry);
    console.log(`[CapsuleLoader] Unbound chat ${chatId} (was: ${old.name})`);
  }
}

/**
 * List all registered capsules (default + all bound chats).
 */
export function listCapsules(): CapsuleConfig[] {
  const registry = loadCapsuleRegistry();
  const capsules: CapsuleConfig[] = [registry.defaultCapsule];

  for (const config of Object.values(registry.chats)) {
    capsules.push(config);
  }

  return capsules;
}

/**
 * Update the default mode (pi/cli) for a specific chat's capsule binding.
 * If the chat is not bound, this is a no-op (mode preference is transient for default capsule).
 */
export function updateCapsuleMode(chatId: number, mode: "pi" | "cli"): void {
  const registry = loadCapsuleRegistry();
  const chatKey = String(chatId);

  if (registry.chats[chatKey]) {
    registry.chats[chatKey].defaultMode = mode;
    writeRegistryToDisk(registry);
    console.log(`[CapsuleLoader] Updated mode for chat ${chatId}: ${mode}`);
  }
  // For unbound chats (using default capsule), mode is managed transiently in session pool
}

// ============== Internal ==============

function writeRegistryToDisk(registry: CapsuleRegistry): void {
  try {
    const tmpPath = REGISTRY_PATH + ".tmp";
    writeFileSync(tmpPath, JSON.stringify(registry, null, 2) + "\n", "utf-8");
    renameSync(tmpPath, REGISTRY_PATH);
    // Update cache with a fresh clone to prevent reference-mutation issues
    cachedRegistry = JSON.parse(JSON.stringify(registry));
  } catch (error) {
    console.error(`[CapsuleLoader] Failed to write registry: ${error}`);
    // Force re-read from disk on next access to restore consistency
    cachedRegistry = null;
  }
}

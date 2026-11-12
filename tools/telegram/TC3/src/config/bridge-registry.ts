/**
 * Bridge Registry — Types and config loader for the bot-to-bot bridge.
 *
 * Reads bridge-config.json and provides lookup functions for registered bots.
 */

import { readFileSync } from "fs";
import { resolve, dirname } from "path";

// ============== Types ==============

export type BotType = "tc3" | "tc2";

export interface RegisteredBot {
  username: string;
  botId: number;
  type: BotType;
  displayName: string;
}

export interface BridgeConfig {
  selfUsername: string; // Set at runtime from bot.api.getMe()
  bots: RegisteredBot[];
  maxTtl: number;
  dedupWindowMs: number;
  enabledGroups: number[];
}

// ============== Singleton State ==============

let bridgeConfig: BridgeConfig | null = null;

// ============== Config Loader ==============

/**
 * Load the bridge configuration from bridge-config.json.
 *
 * The config file is loaded once and cached. The `selfUsername` field
 * must be set separately via `setBridgeSelfUsername()` after getMe().
 */
export function loadBridgeConfig(): BridgeConfig {
  if (bridgeConfig) {
    return bridgeConfig;
  }

  try {
    const configPath = resolve(
      dirname(import.meta.dir),
      "config",
      "bridge-config.json"
    );
    const raw = readFileSync(configPath, "utf-8");
    const parsed = JSON.parse(raw) as {
      bots: RegisteredBot[];
      maxTtl: number;
      dedupWindowMs: number;
      enabledGroups: number[];
    };

    bridgeConfig = {
      selfUsername: "", // Set later via setBridgeSelfUsername
      bots: parsed.bots,
      maxTtl: parsed.maxTtl,
      dedupWindowMs: parsed.dedupWindowMs,
      enabledGroups: parsed.enabledGroups,
    };

    console.log(
      `Bridge config loaded: ${bridgeConfig.bots.length} registered bots`
    );
    return bridgeConfig;
  } catch (error) {
    console.warn(`Bridge config not found or invalid: ${error}`);
    // Return a safe default so the bot still works without bridge
    bridgeConfig = {
      selfUsername: "",
      bots: [],
      maxTtl: 3,
      dedupWindowMs: 300_000,
      enabledGroups: [],
    };
    return bridgeConfig;
  }
}

/**
 * Set the bot's own username (called after bot.api.getMe()).
 *
 * Must include the @ prefix: "@{{ORCHESTRATOR_NAME}}CatalystBot"
 */
export function setBridgeSelfUsername(username: string): void {
  const config = loadBridgeConfig();
  config.selfUsername = username;
  console.log(`Bridge self username set: ${username}`);
}

// ============== Lookup Functions ==============

/**
 * Find a registered bot by Telegram user ID.
 */
export function findBotById(botId: number): RegisteredBot | undefined {
  const config = loadBridgeConfig();
  return config.bots.find((b) => b.botId === botId);
}

/**
 * Find a registered bot by @username (case-insensitive).
 */
export function findBotByUsername(
  username: string
): RegisteredBot | undefined {
  const config = loadBridgeConfig();
  const normalized = username.toLowerCase();
  return config.bots.find((b) => b.username.toLowerCase() === normalized);
}

/**
 * Check if a bot ID belongs to a registered bridge bot.
 */
export function isRegisteredBot(botId: number): boolean {
  return findBotById(botId) !== undefined;
}

/**
 * Check if a bot ID is this bot itself.
 */
export function isSelf(botId: number): boolean {
  const config = loadBridgeConfig();
  if (!config.selfUsername) return false; // Not yet initialized
  const self = config.bots.find(
    (b) => b.username.toLowerCase() === config.selfUsername.toLowerCase()
  );
  return self?.botId === botId;
}

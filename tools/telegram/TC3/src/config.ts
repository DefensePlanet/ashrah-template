/**
 * Configuration for Claude Telegram Bot.
 *
 * All environment variables, paths, constants, and safety settings.
 */

import { homedir } from "os";
import { resolve, dirname } from "path";
import type { McpServerConfig } from "./types";

// ============== Environment Setup ==============

const HOME = homedir();

// Ensure necessary paths are available for Claude's bash commands
// LaunchAgents don't inherit the full shell environment
const EXTRA_PATHS = [
  `${HOME}/.local/bin`,
  `${HOME}/.bun/bin`,
  "/opt/homebrew/bin",
  "/opt/homebrew/sbin",
  "/usr/local/bin",
];

const currentPath = process.env.PATH || "";
const pathParts = currentPath.split(":");
for (const extraPath of EXTRA_PATHS) {
  if (!pathParts.includes(extraPath)) {
    pathParts.unshift(extraPath);
  }
}
process.env.PATH = pathParts.join(":");

// ============== Core Configuration ==============

export const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN || "";
export const ALLOWED_USERS: number[] = (
  process.env.TELEGRAM_ALLOWED_USERS || ""
)
  .split(",")
  .filter((x) => x.trim())
  .map((x) => parseInt(x.trim(), 10))
  .filter((x) => !isNaN(x));

export const WORKING_DIR = process.env.CLAUDE_WORKING_DIR || HOME;
export const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";

// ============== Claude CLI Path ==============

// Auto-detect from PATH, or use environment override
function findClaudeCli(): string {
  const envPath = process.env.CLAUDE_CLI_PATH;
  if (envPath) return envPath;

  // Try to find claude in PATH using Bun.which
  const whichResult = Bun.which("claude");
  if (whichResult) return whichResult;

  // Final fallback
  return "/usr/local/bin/claude";
}

export const CLAUDE_CLI_PATH = findClaudeCli();

// ============== MCP Configuration ==============

// MCP servers loaded from mcp-config.ts
let MCP_SERVERS: Record<string, McpServerConfig> = {};

try {
  // Dynamic import of MCP config
  const mcpConfigPath = resolve(dirname(import.meta.dir), "mcp-config.ts");
  const mcpModule = await import(mcpConfigPath).catch(() => null);
  if (mcpModule?.MCP_SERVERS) {
    MCP_SERVERS = mcpModule.MCP_SERVERS;
    console.log(
      `Loaded ${Object.keys(MCP_SERVERS).length} MCP servers from mcp-config.ts`
    );
  }
} catch {
  console.log("No mcp-config.ts found - running without MCPs");
}

export { MCP_SERVERS };

/**
 * Get MCP servers for Agent SDK
 */
export function getMCPServers(): Record<string, McpServerConfig> {
  return MCP_SERVERS;
}

/**
 * Validate MCP environment variables
 * Checks required vars and warns about missing optional ones
 */
export function validateMCPEnvironment(): void {
  console.log("🔍 Validating MCP environment...");

  // Required environment variables
  const required: string[] = [];

  // Optional but recommended for full functionality
  const optional: Record<string, string> = {
    OPENAI_API_KEY: "Voice transcription (Whisper)",
    CONTEXT7_API_KEY: "Context7 documentation lookup",
    SUPABASE_URL: "Supabase database operations",
    SUPABASE_SERVICE_ROLE_KEY: "Supabase admin operations",
    SUPABASE_PROJECT_REF: "Supabase project identification",
    N8N_API_URL: "n8n workflow automation",
    N8N_API_KEY: "n8n API access",
    OBS_WEBSOCKET_URL: "OBS Studio control",
    OBS_WEBSOCKET_PASSWORD: "OBS WebSocket authentication",
  };

  let hasErrors = false;
  const warnings: string[] = [];

  // Check required vars
  for (const key of required) {
    if (!process.env[key]) {
      console.error(`❌ Missing required env var: ${key}`);
      hasErrors = true;
    } else {
      console.log(`✅ ${key}: configured`);
    }
  }

  // Check optional vars
  for (const [key, description] of Object.entries(optional)) {
    if (!process.env[key]) {
      warnings.push(`${key} (${description})`);
    } else {
      console.log(`✅ ${key}: configured`);
    }
  }

  if (warnings.length > 0) {
    console.log("\n⚠️  Optional env vars not set (some MCPs may not work):");
    warnings.forEach((w) => console.log(`   - ${w}`));
  }

  if (hasErrors) {
    throw new Error("Missing required environment variables");
  }

  console.log("✅ MCP environment validation passed\n");
}

// ============== Security Configuration ==============

// Allowed directories for file operations
const defaultAllowedPaths = [
  WORKING_DIR,
  `${HOME}/Documents`,
  `${HOME}/Downloads`,
  `${HOME}/Desktop`,
  `${HOME}/.claude`, // Claude Code data (plans, settings)
  `${HOME}/.openclaw`, // OpenClaw configuration and agent data
  `${HOME}/Development`, // Development projects
  `${HOME}/.config/telegram-claude`, // Legacy telegram config
];

const allowedPathsStr = process.env.ALLOWED_PATHS || "";
export const ALLOWED_PATHS: string[] = allowedPathsStr
  ? allowedPathsStr
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean)
  : defaultAllowedPaths;

// Build safety prompt dynamically from ALLOWED_PATHS
function buildSafetyPrompt(allowedPaths: string[]): string {
  const pathsList = allowedPaths
    .map((p) => `   - ${p} (and subdirectories)`)
    .join("\n");

  return `
CRITICAL SAFETY RULES FOR TELEGRAM BOT:

1. NEVER delete, remove, or overwrite files without EXPLICIT confirmation from the user.
   - If user asks to delete something, respond: "Are you sure you want to delete [file]? Reply 'yes delete it' to confirm."
   - Only proceed with deletion if user replies with explicit confirmation like "yes delete it", "confirm delete"
   - This applies to: rm, trash, unlink, shred, or any file deletion

2. You can ONLY access files in these directories:
${pathsList}
   - REFUSE any file operations outside these paths

3. NEVER run dangerous commands like:
   - rm -rf (recursive force delete)
   - Any command that affects files outside allowed directories
   - Commands that could damage the system

4. For any destructive or irreversible action, ALWAYS ask for confirmation first.

You are running via Telegram, so the user cannot easily undo mistakes. Be extra careful!
`;
}

export const SAFETY_PROMPT = buildSafetyPrompt(ALLOWED_PATHS);

// ============== {{ORCHESTRATOR_NAME}} Identity Loading ==============

import { readFileSync } from "fs";

/**
 * Load {{ORCHESTRATOR_NAME}} identity from CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md
 * This is the full {{ORCHESTRATOR_NAME}} personality/instructions from Catalyst CLAUDE.md
 *
 * OPTIMIZATION: Also loads the lightweight capability index for specialist
 * routing awareness without loading all 30 agent prompts.
 */
export function load{{ORCHESTRATOR_NAME}}Identity(): string {
  try {
    const {{ORCHESTRATOR_NAME_LOWER}}mPath = resolve(dirname(import.meta.dir), "CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md");
    const {{ORCHESTRATOR_NAME_LOWER}}mContent = readFileSync({{ORCHESTRATOR_NAME_LOWER}}mPath, "utf-8");

    // Load capability index for lightweight specialist routing
    let capabilityIndex = "";
    try {
      const indexPath = resolve(
        process.env.CATALYST_ROOT ?? "{{CATALYST_ROOT}}",
        "tools/telegram/shared-core/output/capability-index.md"
      );
      capabilityIndex = readFileSync(indexPath, "utf-8");
      console.log(`📊 Capability index loaded (${capabilityIndex.length} chars)`);
    } catch {
      console.warn("⚠️  Capability index not found — run shared-core generate");
    }

    // Layer 0: {{ORCHESTRATOR_NAME}} identity (persistent base)
    // Layer 1: Capability index (lightweight routing, always present)
    // Layer 2: Safety rules
    // Layer 3: Specialist context (injected on activation — see injectSpecialistContext)
    const fullPrompt = [
      {{ORCHESTRATOR_NAME_LOWER}}mContent,
      capabilityIndex ? `\n\n${capabilityIndex}` : "",
      `\n\n${SAFETY_PROMPT}`,
    ].join("");

    return fullPrompt;
  } catch (error) {
    console.warn(`⚠️  Could not load CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md: ${error}`);
    console.warn("   Falling back to basic safety prompt");
    return SAFETY_PROMPT;
  }
}

/**
 * Inject specialist context into system prompt
 * @param basePrompt - Base prompt ({{ORCHESTRATOR_NAME}} identity)
 * @param specialistName - Name of specialist agent to inject
 * @returns Enhanced prompt with specialist context
 */
export function injectSpecialistContext(
  basePrompt: string,
  specialistName: string | null
): string {
  if (!specialistName) return basePrompt;

  try {
    const handler = getSpecialistHandler();
    const context = handler.loadSpecialistContext(specialistName);

    if (context) {
      return `${basePrompt}\n\n${context}`;
    }
  } catch (error) {
    console.warn(`⚠️  Could not inject specialist context: ${error}`);
  }

  return basePrompt;
}

// Dangerous command patterns to block (regex patterns)
// These are checked as regex, so use ^ for start, $ for end, \s for whitespace
export const BLOCKED_PATTERNS: Array<string | RegExp> = [
  /rm\s+-rf\s+\/\s*$/i,        // rm -rf / (root only, not /some/path)
  /rm\s+-rf\s+\/[^a-zA-Z]/i,   // rm -rf /  followed by non-letter (like rm -rf / &&)
  /rm\s+-rf\s+~\s*$/i,         // rm -rf ~ (home dir only)
  /rm\s+-rf\s+~\s+[^\/]/i,     // rm -rf ~ followed by non-path
  /rm\s+-rf\s+\$HOME\s*$/i,    // rm -rf $HOME
  /rm\s+(-\w*r\w*\s+-\w*f|-\w*f\w*\s+-\w*r|-\w*rf|-\w*fr)\s+/i, // Any rm -rf variant (separate or combined flags)
  ":(){ :|:& };:",              // Fork bomb
  "> /dev/sd",
  "mkfs.",
  /dd\s+if=\/dev\/(zero|random|urandom)\s+of=\/dev\/sd/i, // Disk wipe
];

// Query timeout (3 minutes)
export const QUERY_TIMEOUT_MS = 180_000;

// ============== Model Configuration ==============

// CLI mode uses Opus for full power; Fast mode uses Sonnet for speed
export const MODEL_CLI = "claude-opus-4-8";
export const MODEL_FAST = "claude-sonnet-4-20250514";

// ============== Voice Transcription ==============

const BASE_TRANSCRIPTION_PROMPT = `Transcribe this voice message accurately.
The speaker may use multiple languages (English, and possibly others).
Focus on accuracy for proper nouns, technical terms, and commands.`;

const TRANSCRIPTION_CONTEXT = process.env.TRANSCRIPTION_CONTEXT || "";

export const TRANSCRIPTION_PROMPT = TRANSCRIPTION_CONTEXT
  ? `${BASE_TRANSCRIPTION_PROMPT}\n\nAdditional context:\n${TRANSCRIPTION_CONTEXT}`
  : BASE_TRANSCRIPTION_PROMPT;

export const TRANSCRIPTION_AVAILABLE = !!OPENAI_API_KEY;

// ============== Thinking Keywords ==============

const thinkingKeywordsStr =
  process.env.THINKING_KEYWORDS || "think,pensa,ragiona";
const thinkingDeepKeywordsStr =
  process.env.THINKING_DEEP_KEYWORDS || "ultrathink,think hard,pensa bene";

export const THINKING_KEYWORDS = thinkingKeywordsStr
  .split(",")
  .map((k) => k.trim().toLowerCase());
export const THINKING_DEEP_KEYWORDS = thinkingDeepKeywordsStr
  .split(",")
  .map((k) => k.trim().toLowerCase());

// ============== Media Group Settings ==============

export const MEDIA_GROUP_TIMEOUT = 1000; // ms to wait for more photos in a group

// ============== Telegram Message Limits ==============

export const TELEGRAM_MESSAGE_LIMIT = 4096; // Max characters per message
export const TELEGRAM_SAFE_LIMIT = 4000; // Safe limit with buffer for formatting
export const STREAMING_THROTTLE_MS = 200; // Throttle streaming updates (5 updates/sec)
export const BUTTON_LABEL_MAX_LENGTH = 30; // Max chars for inline button labels

// ============== Audit Logging ==============

export const AUDIT_LOG_PATH =
  process.env.AUDIT_LOG_PATH || "/tmp/claude-telegram-audit.log";
export const AUDIT_LOG_JSON =
  (process.env.AUDIT_LOG_JSON || "false").toLowerCase() === "true";

// ============== Rate Limiting ==============

export const RATE_LIMIT_ENABLED =
  (process.env.RATE_LIMIT_ENABLED || "true").toLowerCase() === "true";
export const RATE_LIMIT_REQUESTS = parseInt(
  process.env.RATE_LIMIT_REQUESTS || "20",
  10
);
export const RATE_LIMIT_WINDOW = parseInt(
  process.env.RATE_LIMIT_WINDOW || "60",
  10
);

// ============== File Paths ==============

export const SESSION_FILE = "/tmp/claude-telegram-session.json";
export const RESTART_FILE = "/tmp/claude-telegram-restart.json";
export const TEMP_DIR = "/tmp/telegram-bot";

// Temp paths that are always allowed for bot operations
export const TEMP_PATHS = ["/tmp/", "/private/tmp/", "/var/folders/"];

// Ensure temp directory exists
await Bun.write(`${TEMP_DIR}/.keep`, "");

// ============== Catalyst Integration ==============

import {
  CatalystAgentLoader,
  CatalystSkillLoader,
  CatalystWatcher,
  SpecialistHandler,
} from "./catalyst-loader";
import { join } from "path";

// Initialize loaders
export const catalystAgentLoader = new CatalystAgentLoader();
export const catalystSkillLoader = new CatalystSkillLoader();
export const catalystWatcher = new CatalystWatcher();

// Specialist handler (initialized after loaders are ready)
let specialistHandlerInstance: SpecialistHandler | null = null;

export function getSpecialistHandler(): SpecialistHandler {
  if (!specialistHandlerInstance) {
    specialistHandlerInstance = new SpecialistHandler(catalystAgentLoader);
  }
  return specialistHandlerInstance;
}

/**
 * Get the Catalyst watcher instance
 */
export function getCatalystWatcher(): CatalystWatcher {
  return catalystWatcher;
}

/**
 * Initialize Catalyst resources (agents metadata, skills, watchers)
 *
 * OPTIMIZATION: Agent prompts are loaded lazily on first specialist activation.
 * Only metadata (name, description, capabilities) is loaded at startup.
 */
export async function initializeCatalyst(): Promise<void> {
  console.log("🚀 Initializing Catalyst integration (lazy mode)...");

  const agentsDir = join(import.meta.dir, "../catalyst-agents");
  const skillsDir = join(import.meta.dir, "../catalyst-skills");

  try {
    // Load agent metadata only (prompts loaded on demand)
    await catalystAgentLoader.loadAgents(agentsDir);

    // Load skills
    await catalystSkillLoader.loadSkills(skillsDir);

    // Start watchers (with specialist handler for cache invalidation)
    catalystWatcher.startWatching(
      { agents: agentsDir, skills: skillsDir },
      catalystAgentLoader,
      catalystSkillLoader,
      getSpecialistHandler()
    );

    console.log(`✅ Catalyst integration ready (lazy):`);
    console.log(`   - ${catalystAgentLoader.count} agents indexed (prompts: on-demand)`);
    console.log(`   - ${catalystSkillLoader.count} skills`);
  } catch (err) {
    console.error("❌ Failed to initialize Catalyst:", err);
    throw err;
  }
}

// ============== Validation ==============

if (!TELEGRAM_TOKEN) {
  console.error("ERROR: TELEGRAM_BOT_TOKEN environment variable is required");
  process.exit(1);
}

if (ALLOWED_USERS.length === 0) {
  console.error(
    "ERROR: TELEGRAM_ALLOWED_USERS environment variable is required"
  );
  process.exit(1);
}

console.log(
  `Config loaded: ${ALLOWED_USERS.length} allowed users, working dir: ${WORKING_DIR}`
);

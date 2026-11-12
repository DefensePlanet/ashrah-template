/**
 * Configuration for Claude iOS Bridge Service
 *
 * All environment variables, paths, and settings.
 */

import { homedir } from "os";
import type { McpServerConfig } from "./types";

// ============== Environment Setup ==============

const HOME = homedir();

// Ensure necessary paths are available for Claude's bash commands
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

export const PORT = parseInt(process.env.CLAUDE_BRIDGE_PORT || "5200", 10);
export const HOST = process.env.CLAUDE_BRIDGE_HOST || "0.0.0.0";
export const WORKING_DIR = process.env.CLAUDE_WORKING_DIR || `${HOME}/BuilderOS`;

// API Key for iOS app authentication
export const API_KEY = process.env.CLAUDE_BRIDGE_API_KEY || "ios-bridge-default-key";

// ============== Claude CLI Path ==============

function findClaudeCli(): string {
  const envPath = process.env.CLAUDE_CLI_PATH;
  if (envPath) return envPath;

  const whichResult = Bun.which("claude");
  if (whichResult) return whichResult;

  return "/usr/local/bin/claude";
}

export const CLAUDE_CLI_PATH = findClaudeCli();

// ============== MCP Configuration ==============

const BUILDEROS = `${HOME}/BuilderOS`;

export const MCP_SERVERS: Record<string, McpServerConfig> = {
  // Agent Memory - persistent learning and knowledge retention
  "agent-memory": {
    type: "http",
    url: "http://localhost:8080/sse",
  },

  // Builder Memory - knowledge graph for BuilderOS context
  "builder-memory": {
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-memory"],
  },

  // Context7 - up-to-date library documentation
  "context7": {
    command: "/opt/homebrew/bin/node",
    args: [
      `${HOME}/Development/context7/dist/index.js`,
      "--transport",
      "stdio",
    ],
  },

  // Supabase MCP - database operations
  "supabase": {
    command: "npx",
    args: ["-y", "@anthropic-ai/mcp-server-supabase"],
    env: {
      SUPABASE_URL: process.env.SUPABASE_URL || "",
      SUPABASE_SERVICE_KEY: process.env.SUPABASE_SERVICE_KEY || "",
    },
  },

  // Filesystem - scoped file access
  filesystem: {
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-filesystem"],
  },

  // Siri Shortcuts - macOS automation
  "siri-shortcuts": {
    command: "npx",
    args: ["-y", "mcp-server-siri-shortcuts"],
  },
};

// ============== Security Configuration ==============

// Allowed directories for file operations
const defaultAllowedPaths = [
  WORKING_DIR,
  `${HOME}/Documents`,
  `${HOME}/Downloads`,
  `${HOME}/Desktop`,
  `${HOME}/.claude`,
];

export const ALLOWED_PATHS: string[] = (process.env.ALLOWED_PATHS || "")
  .split(",")
  .filter(Boolean)
  .map((p) => p.trim()) || defaultAllowedPaths;

// System prompt for safety
export const SYSTEM_PROMPT = `
You are {{ORCHESTRATOR_NAME}}, {{USER_NAME}}'s AI assistant running on the BuilderOS mobile app.
You have access to the full BuilderOS system via this local bridge.

Working directory: ${WORKING_DIR}

You can:
- Browse and manage capsules
- Execute commands via bash
- Access BuilderOS documentation
- Query the knowledge graph
- Interact with Supabase databases

Be helpful, concise, and proactive. Format responses for mobile viewing.
`;

// ============== Session Management ==============

// Session file per device
export function getSessionFile(deviceId: string): string {
  const safeId = deviceId.replace(/[^a-zA-Z0-9-]/g, "");
  return `/tmp/claude-ios-bridge-session-${safeId}.json`;
}

// ============== Validation ==============

console.log(`Claude iOS Bridge config loaded:`);
console.log(`  Working dir: ${WORKING_DIR}`);
console.log(`  Port: ${PORT}`);
console.log(`  MCP servers: ${Object.keys(MCP_SERVERS).length}`);

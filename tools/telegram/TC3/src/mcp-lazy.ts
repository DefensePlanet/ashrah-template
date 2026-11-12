/**
 * MCP Lazy Initialization with LRU Hot Pool
 *
 * Instead of passing all 17+ MCP servers to every query() call,
 * this module provides filtered MCP configs based on the active specialist.
 *
 * - Always-hot: MCPs needed for core {{ORCHESTRATOR_NAME}} functionality
 * - Specialist-mapped: MCPs activated when a specific specialist is loaded
 * - LRU pool: Tracks recently-used MCPs and keeps them warm
 */

import type { McpServerConfig } from "./types";

/** MCP servers that are always passed to query() (core {{ORCHESTRATOR_NAME}} functionality) */
const ALWAYS_HOT: Set<string> = new Set([
  "context7",        // Documentation lookup — used constantly
  "supabase",        // Database — most capsules use it
  "git",             // Git operations — fundamental
  "applescript",     // macOS automation — general utility
]);

/**
 * Map specialist names to the MCP servers they need.
 * Only MCPs listed here are activated when the specialist is loaded.
 * MCPs in ALWAYS_HOT are always included regardless.
 */
const SPECIALIST_MCP_MAP: Record<string, string[]> = {
  // Engineering
  "🏛️ Backend Developer":     ["supabase", "context7"],
  "🎨 Frontend Developer":    ["context7", "playwright"],
  "📱 Mobile Developer":      ["context7", "apple-doc-mcp"],
  "💻 macOS Dev":             ["context7", "apple-doc-mcp"],
  "🛒 Shopify Exec":          ["context7"],
  "🏄🏼‍♂️ MCP Server Dude":      ["context7"],

  // Creative
  "🎨 Graphic Designer":      [],
  "📸 Camera Man":            [],
  "📐 UI Designer":           ["context7"],
  "🎬 Studio Engineer":       ["obs"],
  "🧊 3D Developer":          [],

  // Business
  "📣 Chief Marketing Officer": [],
  "📊 Business Analyst":      ["supabase"],
  "🎯 Product Strategist":    [],
  "🧭 Venture Analyst":       [],
  "🎯 Brand Specialist":      [],
  "🔍 SEO Analyzer":          [],

  // Quality
  "🧐 Code Reviewer":         ["context7"],
  "👾 Debugger":               ["context7", "supabase"],
  "🧪 Validator":              ["context7", "playwright"],
  "🛡️ Security Analyst":      ["context7", "supabase"],

  // Research
  "🔍 Research Agent":         [],
  "🤓 AI Nerd":                ["context7"],
  "🧠 2nd Brain Wizard":       [],
  "🧮 Algo Wizard":            ["context7"],

  // Operations
  "🤖 Automator":              ["n8n"],
  "🐲 Bowser":                 ["playwright"],
  "⛓️ Blockchain Agent":       ["context7"],

  // Command
  "👔 BOSS":                   [],
  "🏗️ System Architect":       ["context7"],
};

/** LRU tracking for recently-used MCPs */
class LRUPool {
  private accessOrder: string[] = [];
  private maxSize: number;

  constructor(maxSize: number = 6) {
    this.maxSize = maxSize;
  }

  /** Mark an MCP as recently used */
  touch(name: string): void {
    // Remove if exists
    const idx = this.accessOrder.indexOf(name);
    if (idx >= 0) this.accessOrder.splice(idx, 1);
    // Add to front
    this.accessOrder.unshift(name);
    // Evict oldest if over capacity
    if (this.accessOrder.length > this.maxSize) {
      const evicted = this.accessOrder.pop();
      console.log(`🔄 MCP LRU evicted: ${evicted}`);
    }
  }

  /** Get all MCPs in the pool */
  getAll(): string[] {
    return [...this.accessOrder];
  }

  /** Check if an MCP is in the pool */
  has(name: string): boolean {
    return this.accessOrder.includes(name);
  }
}

const lruPool = new LRUPool(6);

/**
 * Get filtered MCP servers for the current query based on active specialist.
 *
 * @param allServers - Full MCP server config map
 * @param activeSpecialist - Currently active specialist name (null = {{ORCHESTRATOR_NAME}} only)
 * @returns Filtered MCP config to pass to query()
 */
export function getFilteredMCPServers(
  allServers: Record<string, McpServerConfig>,
  activeSpecialist: string | null
): Record<string, McpServerConfig> {
  const result: Record<string, McpServerConfig> = {};

  // 1. Always include hot MCPs
  for (const name of ALWAYS_HOT) {
    if (allServers[name]) {
      result[name] = allServers[name];
    }
  }

  // 2. Include specialist-specific MCPs
  if (activeSpecialist && SPECIALIST_MCP_MAP[activeSpecialist]) {
    for (const name of SPECIALIST_MCP_MAP[activeSpecialist]) {
      if (allServers[name]) {
        result[name] = allServers[name];
        lruPool.touch(name);
      }
    }
  }

  // 3. Include LRU pool MCPs (recently used, stay warm)
  for (const name of lruPool.getAll()) {
    if (allServers[name] && !result[name]) {
      result[name] = allServers[name];
    }
  }

  const total = Object.keys(allServers).length;
  const active = Object.keys(result).length;
  if (active < total) {
    console.log(`⚡ MCP lazy: ${active}/${total} servers active (specialist: ${activeSpecialist ?? "{{ORCHESTRATOR_NAME}}"})`);
  }

  return result;
}

/**
 * Get the specialist-to-MCP mapping for diagnostics
 */
export function getMCPMapping(): Record<string, string[]> {
  return { ...SPECIALIST_MCP_MAP };
}

/**
 * Get current LRU pool state
 */
export function getLRUState(): string[] {
  return lruPool.getAll();
}

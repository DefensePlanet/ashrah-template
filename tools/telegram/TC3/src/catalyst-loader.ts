/**
 * Catalyst Loader - Integration with Catalyst agents and skills
 *
 * Loads all agents and skills from Catalyst directories (symlinked),
 * provides agent name resolution, specialist detection, and hot reload.
 */

import { existsSync, readdirSync, readFileSync, statSync, watch, type FSWatcher } from "fs";
import { join } from "path";
import { classifyMessage } from "../../shared-core/src/trigger-classifier.js";

// ============== Types ==============

export interface CatalystAgent {
  name: string;
  description?: string;
  model?: string;
  infinity_model?: string;
  prompt: string;
  filepath: string;
  color?: string;
  tools?: string | string[];
  mesh?: {
    can_request?: string[];
    provides?: string[];
  };
}

export interface CatalystSkill {
  name: string;
  path: string;
  hasPrompt: boolean;
  promptContent?: string;
}

export interface CatalystPaths {
  agents: string;
  skills: string;
}

export interface AgentNameMapping {
  agent_name_aliases: Record<string, string>;
  routing_instructions: string;
}

// ============== Agent Name Resolution ==============

class AgentNameResolver {
  private aliasMap: Map<string, string> = new Map();

  constructor() {
    this.loadAliasMap();
  }

  private loadAliasMap(): void {
    try {
      const mappingPath = "{{CATALYST_ROOT}}/.claude-context/agent-name-routing.json";
      if (existsSync(mappingPath)) {
        const data = JSON.parse(readFileSync(mappingPath, "utf-8")) as AgentNameMapping;

        // Load all aliases (case-insensitive)
        for (const [alias, canonicalName] of Object.entries(data.agent_name_aliases)) {
          this.aliasMap.set(alias.toLowerCase(), canonicalName);
        }

        console.log(`Loaded ${this.aliasMap.size} agent name aliases`);
      }
    } catch (err) {
      console.warn("Failed to load agent name mapping:", err);
    }
  }

  /**
   * Resolve a friendly name to the full emoji name
   * @param friendlyName - Name like "backend dev" or "Backend Developer"
   * @returns Full name like "🏛️ Backend Developer" or null if not found
   */
  resolve(friendlyName: string): string | null {
    const normalized = friendlyName.toLowerCase().trim();
    return this.aliasMap.get(normalized) || null;
  }

  /**
   * Try multiple resolution strategies
   */
  resolveBestMatch(name: string): string | null {
    // Direct lookup
    const direct = this.resolve(name);
    if (direct) return direct;

    // Try removing common suffixes
    const withoutDev = name.replace(/\s+(dev|developer|specialist)$/i, "");
    if (withoutDev !== name) {
      const attempt = this.resolve(withoutDev);
      if (attempt) return attempt;
    }

    return null;
  }
}

// ============== Catalyst Agent Loader (Lazy) ==============

/**
 * Lightweight agent metadata — loaded eagerly at startup (frontmatter only).
 * Full prompt is loaded lazily on first specialist activation.
 */
interface AgentMetadata {
  name: string;
  description?: string;
  model?: string;
  infinity_model?: string;
  filepath: string;
  color?: string;
  tools?: string | string[];
  mesh?: {
    can_request?: string[];
    provides?: string[];
  };
}

export class CatalystAgentLoader {
  private agents: Map<string, CatalystAgent> = new Map();
  /** Lightweight metadata (loaded eagerly) — no prompt content */
  private metadata: Map<string, AgentMetadata> = new Map();
  /** Cache for lazily-loaded full prompts */
  private promptCache: Map<string, string> = new Map();
  private resolver: AgentNameResolver = new AgentNameResolver();

  /**
   * Load agent metadata (frontmatter only) from the agents directory.
   * Full prompts are loaded lazily on first access via getAgent().
   */
  async loadAgents(agentsDir: string): Promise<void> {
    if (!existsSync(agentsDir)) {
      console.warn(`Agents directory not found: ${agentsDir}`);
      return;
    }

    const files = readdirSync(agentsDir);
    let loaded = 0;

    for (const file of files) {
      if (!file.endsWith(".md")) continue;

      try {
        const filepath = join(agentsDir, file);
        const meta = this.parseAgentMetadata(filepath);

        if (meta) {
          this.metadata.set(meta.name, meta);
          loaded++;
        }
      } catch (err) {
        console.warn(`Failed to load agent metadata ${file}:`, err);
      }
    }

    // Clear prompt cache on reload (source files may have changed)
    this.promptCache.clear();

    console.log(`✅ Indexed ${loaded} Catalyst agents (lazy — prompts loaded on demand)`);
  }

  /**
   * Parse ONLY the frontmatter from an agent file.
   * Note: Reads the full file but only parses/caches the frontmatter section.
   * The prompt body is discarded here and lazy-loaded later via loadFullPrompt().
   */
  private parseAgentMetadata(filepath: string): AgentMetadata | null {
    const content = readFileSync(filepath, "utf-8");

    // Extract just frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (!frontmatterMatch) {
      return null;
    }

    const frontmatter = this.parseFrontmatter(frontmatterMatch[1]);

    if (!frontmatter.name) return null;

    return {
      name: frontmatter.name,
      description: frontmatter.description,
      model: frontmatter.model,
      infinity_model: frontmatter.infinity_model,
      filepath,
      color: frontmatter.color,
      tools: frontmatter.tools,
      mesh: frontmatter.mesh,
    };
  }

  /**
   * Lazily load the full prompt for an agent (cached after first load).
   */
  private loadFullPrompt(name: string): string | null {
    // Check cache first
    const cached = this.promptCache.get(name);
    if (cached) return cached;

    const meta = this.metadata.get(name);
    if (!meta) return null;

    try {
      const content = readFileSync(meta.filepath, "utf-8");
      const match = content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)$/);
      const prompt = match ? match[1].trim() : content;

      this.promptCache.set(name, prompt);
      console.log(`📄 Lazy-loaded prompt for ${name} (${prompt.length} chars)`);
      return prompt;
    } catch (err) {
      console.warn(`Failed to load prompt for ${name}:`, err);
      return null;
    }
  }

  /**
   * Parse an agent markdown file (full — for backward compat)
   */
  private async parseAgentFile(filepath: string): Promise<CatalystAgent | null> {
    const content = readFileSync(filepath, "utf-8");

    // Extract frontmatter
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    if (!frontmatterMatch) {
      console.warn(`No frontmatter found in ${filepath}`);
      return null;
    }

    const [, frontmatterText, promptText] = frontmatterMatch;

    // Parse frontmatter (simple YAML parsing for our needs)
    const frontmatter = this.parseFrontmatter(frontmatterText);

    if (!frontmatter.name) {
      console.warn(`No name in frontmatter: ${filepath}`);
      return null;
    }

    return {
      name: frontmatter.name,
      description: frontmatter.description,
      model: frontmatter.model,
      infinity_model: frontmatter.infinity_model,
      prompt: promptText.trim(),
      filepath,
      color: frontmatter.color,
      tools: frontmatter.tools,
      mesh: frontmatter.mesh,
    };
  }

  /**
   * Simple YAML frontmatter parser (handles our agent files)
   */
  private parseFrontmatter(text: string): Record<string, any> {
    const result: Record<string, any> = {};

    let currentKey: string | null = null;
    let currentValue: any = null;
    let inArray = false;

    for (const line of text.split("\n")) {
      const trimmed = line.trim();

      // Skip empty lines
      if (!trimmed) continue;

      // Array items
      if (trimmed.startsWith("- ")) {
        const value = trimmed.slice(2).trim();

        if (inArray && currentKey) {
          if (!Array.isArray(result[currentKey])) {
            result[currentKey] = [];
          }
          result[currentKey].push(this.parseValue(value));
        }
        continue;
      }

      // Key-value pairs
      const match = trimmed.match(/^([a-z_]+):\s*(.*)$/);
      if (match) {
        const [, key, value] = match;

        if (!value || value === "") {
          // Start of array or object
          currentKey = key;
          inArray = true;
          result[key] = [];
        } else {
          // Direct value
          result[key] = this.parseValue(value);
          currentKey = key;
          inArray = false;
        }
      }
    }

    return result;
  }

  /**
   * Parse a value (handle strings, numbers, booleans)
   */
  private parseValue(value: string): any {
    // Remove quotes
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      return value.slice(1, -1);
    }

    // Boolean
    if (value === "true") return true;
    if (value === "false") return false;

    // Number
    if (/^-?\d+(\.\d+)?$/.test(value)) {
      return parseFloat(value);
    }

    // String
    return value;
  }

  /**
   * Get an agent by name (lazy-loads prompt on first access)
   */
  getAgent(name: string): CatalystAgent | undefined {
    // Check if already fully loaded
    const cached = this.agents.get(name);
    if (cached) return cached;

    // Try lazy load from metadata
    const meta = this.metadata.get(name);
    if (!meta) return undefined;

    const prompt = this.loadFullPrompt(name);
    if (!prompt) return undefined;

    // Promote to full agent and cache
    const agent: CatalystAgent = { ...meta, prompt };
    this.agents.set(name, agent);
    return agent;
  }

  /**
   * Get agent metadata without loading the full prompt
   */
  getAgentMetadata(name: string): AgentMetadata | undefined {
    return this.metadata.get(name);
  }

  /**
   * List all agent names (from metadata — no prompt loading)
   */
  listAgents(): string[] {
    return Array.from(this.metadata.keys());
  }

  /**
   * Resolve a friendly name to the full agent name
   * @param friendlyName - Name like "backend dev" or "Backend Developer"
   * @returns Full name like "🏛️ Backend Developer" or null if not found
   */
  resolveAgentName(friendlyName: string): string | null {
    // First try direct lookup (maybe it's already the full name)
    if (this.metadata.has(friendlyName)) {
      return friendlyName;
    }

    // Try resolution via alias map
    const resolved = this.resolver.resolveBestMatch(friendlyName);

    // Verify the resolved name exists in metadata
    if (resolved && this.metadata.has(resolved)) {
      return resolved;
    }

    return null;
  }

  /**
   * Get agent count (from metadata — lightweight)
   */
  get count(): number {
    return this.metadata.size;
  }

  /**
   * Get count of fully-loaded agents (prompts in memory)
   */
  get loadedCount(): number {
    return this.agents.size;
  }
}

// ============== Catalyst Skill Loader ==============

export class CatalystSkillLoader {
  private skills: Map<string, CatalystSkill> = new Map();

  /**
   * Load all skills from the skills directory
   */
  async loadSkills(skillsDir: string): Promise<void> {
    if (!existsSync(skillsDir)) {
      console.warn(`Skills directory not found: ${skillsDir}`);
      return;
    }

    this.scanDirectory(skillsDir, "");

    console.log(`✅ Loaded ${this.skills.size} Catalyst skills`);
  }

  /**
   * Recursively scan skills directory
   */
  private scanDirectory(dir: string, prefix: string): void {
    const entries = readdirSync(dir);

    for (const entry of entries) {
      const fullPath = join(dir, entry);
      const stat = statSync(fullPath);

      if (stat.isDirectory()) {
        // Check if this directory is a skill (has prompt.md or skill.md)
        const promptPath = join(fullPath, "prompt.md");
        const skillPath = join(fullPath, "skill.md");

        let hasPrompt = false;
        let promptContent: string | undefined;

        if (existsSync(promptPath)) {
          hasPrompt = true;
          promptContent = readFileSync(promptPath, "utf-8");
        } else if (existsSync(skillPath)) {
          hasPrompt = true;
          promptContent = readFileSync(skillPath, "utf-8");
        }

        const skillName = prefix ? `${prefix}/${entry}` : entry;

        this.skills.set(skillName, {
          name: skillName,
          path: fullPath,
          hasPrompt,
          promptContent,
        });

        // Recurse into subdirectories
        this.scanDirectory(fullPath, skillName);
      }
    }
  }

  /**
   * Get skill context (prompt content)
   */
  getSkillContext(skillName: string): string | null {
    const skill = this.skills.get(skillName);
    return skill?.promptContent || null;
  }

  /**
   * List all skill names
   */
  listSkills(): string[] {
    return Array.from(this.skills.keys());
  }

  /**
   * Get skill count
   */
  get count(): number {
    return this.skills.size;
  }
}

// ============== Specialist Detection Result ==============

export interface DetectionResult {
  specialist: string;
  confidence: number;
  method: string;
}

// ============== Specialist Handler ==============

export class SpecialistHandler {
  /** Cache of loaded specialist contexts to avoid re-reading files */
  private contextCache: Map<string, string> = new Map();
  /** Currently active specialist (persists across messages until cleared) */
  private activeSpecialist: string | null = null;
  private activatedAt: number | null = null;

  constructor(
    private agentLoader: CatalystAgentLoader,
  ) {}

  /**
   * Detect if user message requests a specialist.
   *
   * Two-tier detection:
   *   Tier 1 — Explicit delegation patterns (regex, 0.95 confidence)
   *   Tier 2 — Keyword trigger classifier (shared-core, variable confidence)
   *
   * Returns DetectionResult with specialist name, confidence, and method.
   */
  detectSpecialistRequest(message: string): DetectionResult | null {
    // Tier 1: Explicit delegation patterns ("have backend dev do X")
    // Character class includes digits for agents like "3D Developer", "2nd Brain Wizard"
    const patterns = [
      /have\s+(?:the\s+)?([a-z0-9\s]+?)\s+(?:do|implement|create|build|fix)/i,
      /ask\s+(?:the\s+)?([a-z0-9\s]+?)\s+to/i,
      /get\s+(?:the\s+)?([a-z0-9\s]+?)\s+to/i,
      /tell\s+(?:the\s+)?([a-z0-9\s]+?)\s+to/i,
      /(?:delegate|assign)\s+(?:this\s+)?to\s+(?:the\s+)?([a-z0-9\s]+)/i,
    ];

    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match) {
        const extractedName = match[1].trim();
        const resolvedName = this.agentLoader.resolveAgentName(extractedName);

        if (resolvedName) {
          return { specialist: resolvedName, confidence: 0.95, method: "explicit" };
        }
      }
    }

    // Tier 2: Shared-core keyword trigger classifier
    try {
      const classification = classifyMessage(message);
      if (classification.specialist && classification.confidence >= 0.65) {
        // Verify specialist exists in our agent registry
        const exists = this.agentLoader.getAgentMetadata(classification.specialist);
        if (exists) {
          console.log(`🎯 Classifier detected: ${classification.specialist} (${classification.confidence}, ${classification.method})`);
          return {
            specialist: classification.specialist,
            confidence: classification.confidence,
            method: classification.method,
          };
        }
      }
    } catch {
      // Classifier not available — shared-core may not be generated yet
    }

    return null;
  }

  /**
   * Load specialist's full prompt context (cached after first load).
   * Only reads from disk on the FIRST activation of each specialist.
   */
  loadSpecialistContext(specialistName: string): string {
    // Check cache first
    const cached = this.contextCache.get(specialistName);
    if (cached) {
      console.log(`⚡ Specialist context cache hit: ${specialistName}`);
      return cached;
    }

    // Lazy-load the agent (triggers file read only now)
    const agent = this.agentLoader.getAgent(specialistName);

    if (!agent) {
      return `(Specialist "${specialistName}" not found in Catalyst agents)`;
    }

    const header = [
      `## Specialist Mode: ${agent.name}`,
      ``,
      `A trigger classifier detected this message matches the ${agent.name} domain.`,
      `You are now operating with ${agent.name} expertise. Channel this specialist's knowledge when responding.`,
      ``,
      `**Rules for specialist mode:**`,
      `- For domain questions: answer with specialist-level depth and authority`,
      `- For implementation needing tools/MCP/file edits: tell {{USER_NAME}} this needs {{ORCHESTRATOR_NAME}} in Claude Code`,
      `- Do NOT mention that specialist context was injected. Just be the expert naturally.`,
      `- Say "back to {{ORCHESTRATOR_NAME}}" or "clear specialist" to exit specialist mode`,
      ``,
      `--- Specialist Knowledge ---`,
      ``,
    ].join("\n");

    const context = header + agent.prompt;
    this.contextCache.set(specialistName, context);
    console.log(`📄 Specialist context loaded and cached: ${specialistName} (${context.length} chars)`);

    return context;
  }

  /**
   * Set the active specialist (persists across messages)
   */
  setActive(name: string): void {
    this.activeSpecialist = name;
    this.activatedAt = Date.now();
    console.log(`🎯 Active specialist: ${name}`);
  }

  /**
   * Clear active specialist
   */
  clearActive(): void {
    if (this.activeSpecialist) {
      console.log(`🔄 Cleared active specialist: ${this.activeSpecialist}`);
    }
    this.activeSpecialist = null;
    this.activatedAt = null;
  }

  /**
   * Get active specialist name (null if none)
   */
  getActive(): string | null {
    return this.activeSpecialist;
  }

  /**
   * Get active specialist info for status display
   */
  getActiveInfo(): { name: string; activatedAt: number } | null {
    if (!this.activeSpecialist || !this.activatedAt) return null;
    return { name: this.activeSpecialist, activatedAt: this.activatedAt };
  }

  /**
   * Invalidate the context cache for a specific agent (e.g., after hot reload)
   */
  invalidateCache(name?: string): void {
    if (name) {
      this.contextCache.delete(name);
    } else {
      this.contextCache.clear();
    }
  }
}

// ============== Catalyst Watcher ==============

export class CatalystWatcher {
  private watchers: FSWatcher[] = [];
  private agentLoader?: CatalystAgentLoader;
  private skillLoader?: CatalystSkillLoader;
  private specialistHandler?: SpecialistHandler;
  private paths?: CatalystPaths;
  private reloadDebounceTimer: Timer | null = null;
  private changeCount = 0;

  /**
   * Start watching Catalyst directories for changes
   */
  startWatching(
    paths: CatalystPaths,
    agentLoader?: CatalystAgentLoader,
    skillLoader?: CatalystSkillLoader,
    specialistHandler?: SpecialistHandler,
  ): void {
    this.agentLoader = agentLoader;
    this.skillLoader = skillLoader;
    this.specialistHandler = specialistHandler;
    this.paths = paths;

    // Watch agents directory
    if (existsSync(paths.agents)) {
      const agentWatcher = watch(
        paths.agents,
        { recursive: false },
        (eventType, filename) => {
          if (filename && filename.endsWith(".md")) {
            console.log(`🔄 Agent file changed: ${filename} (${eventType})`);
            this.scheduleReload("agents");
          }
        }
      );
      this.watchers.push(agentWatcher);
      console.log(`👀 Watching agents: ${paths.agents}`);
    }

    // Watch skills directory
    if (existsSync(paths.skills)) {
      const skillWatcher = watch(
        paths.skills,
        { recursive: true },
        (eventType, filename) => {
          if (filename) {
            console.log(`🔄 Skill file changed: ${filename} (${eventType})`);
            this.scheduleReload("skills");
          }
        }
      );
      this.watchers.push(skillWatcher);
      console.log(`👀 Watching skills: ${paths.skills}`);
    }
  }

  /**
   * Schedule a reload with debouncing (wait for rapid changes to settle)
   */
  private scheduleReload(type: "agents" | "skills"): void {
    // Clear existing timer
    if (this.reloadDebounceTimer) {
      clearTimeout(this.reloadDebounceTimer);
    }

    // Schedule reload after 500ms of no changes
    this.reloadDebounceTimer = setTimeout(async () => {
      try {
        if (type === "agents" && this.agentLoader && this.paths) {
          await this.agentLoader.loadAgents(this.paths.agents);
          // Invalidate specialist context cache so re-activations get fresh content
          this.specialistHandler?.invalidateCache();
          console.log("✅ Agents hot-reloaded (specialist cache cleared)");
        } else if (type === "skills" && this.skillLoader && this.paths) {
          await this.skillLoader.loadSkills(this.paths.skills);
          console.log("✅ Skills hot-reloaded");
        }
        this.changeCount++;
      } catch (error) {
        console.error(`❌ Hot reload failed:`, error);
      }
    }, 500);
  }

  /**
   * Manually reload all Catalyst resources
   */
  async reloadAll(): Promise<{
    agents: { before: number; after: number };
    skills: { before: number; after: number };
  }> {
    const before = {
      agents: this.agentLoader?.count || 0,
      skills: this.skillLoader?.count || 0,
    };

    if (this.agentLoader && this.paths) {
      await this.agentLoader.loadAgents(this.paths.agents);
    }

    if (this.skillLoader && this.paths) {
      await this.skillLoader.loadSkills(this.paths.skills);
    }

    const after = {
      agents: this.agentLoader?.count || 0,
      skills: this.skillLoader?.count || 0,
    };

    console.log(`🔄 Manual sync complete: agents ${before.agents}→${after.agents}, skills ${before.skills}→${after.skills}`);

    return { agents: { before: before.agents, after: after.agents }, skills: { before: before.skills, after: after.skills } };
  }

  /**
   * Get watcher status
   */
  getStatus(): { watching: boolean; changeCount: number } {
    return {
      watching: this.watchers.length > 0,
      changeCount: this.changeCount,
    };
  }

  /**
   * Stop all watchers
   */
  stopWatching(): void {
    if (this.reloadDebounceTimer) {
      clearTimeout(this.reloadDebounceTimer);
    }
    for (const watcher of this.watchers) {
      watcher.close();
    }
    this.watchers = [];
    console.log("Stopped watching Catalyst directories");
  }
}

// ============== Exports ==============

export {
  AgentNameResolver,
};

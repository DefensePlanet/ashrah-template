/** Extracted from .claude/agents/*.md frontmatter */
export interface AgentFrontmatter {
  name: string;
  description: string;
  model: string;
  color?: string;
  tools?: string;
  infinity_model?: string;
  mesh?: {
    can_request?: string[];
    provides?: string[];
  };
}

/** Condensed agent entry for the capability index */
export interface AgentIndexEntry {
  id: string;           // filename without .md (e.g., "backend-specialist")
  name: string;         // full emoji name (e.g., "🏛️ Backend Developer")
  emoji: string;        // extracted emoji
  shortName: string;    // name without emoji (e.g., "Backend Developer")
  description: string;  // one-line description
  model: string;        // opus/sonnet/haiku
  capabilities: string[]; // mesh.provides or inferred from description
  collaborators: string[]; // mesh.can_request
  department: Department;
  sourceFile: string;   // absolute path to .claude/agents/*.md
  sourceHash: string;   // sha256 of source file for drift detection
}

/** Department clustering for team group chats */
export type Department =
  | "engineering"    // Backend, Frontend, Mobile, macOS, Shopify, MCP Server Dude
  | "creative"       // Graphic Designer, Camera Man, UI Designer, Studio Engineer, 3D Dev
  | "business"       // CMO, Business Analyst, Product Strategist, Venture Analyst, Brand Specialist
  | "quality"        // Code Reviewer, Debugger, Validator, Security Analyst
  | "research"       // Research Agent, AI Nerd, 2nd Brain Wizard, Algo Wizard
  | "operations"     // Automator, Bowser, Blockchain Agent
  | "command";       // BOSS, System Architect

/** Full capability index output */
export interface CapabilityIndex {
  version: string;
  generated_at: string;
  agent_count: number;
  departments: Record<Department, AgentIndexEntry[]>;
  agents: AgentIndexEntry[];
  capability_map: Record<string, string[]>; // capability -> agent names
}

/** Specialist pack — condensed agent context for TC2 bootstrap */
export interface SpecialistPack {
  agent_id: string;
  name: string;
  department: Department;
  /** Condensed prompt under budget (chars) */
  condensed_prompt: string;
  /** Char count */
  char_count: number;
  /** Source hash for drift detection */
  source_hash: string;
  generated_at: string;
}

/** Sync manifest tracking all generated artifacts */
export interface SyncManifest {
  version: string;
  generated_at: string;
  schema_version: number;
  agents: {
    id: string;
    source_path: string;
    source_hash: string;
    index_hash: string;
    pack_hash: string | null;
    last_synced: string;
  }[];
}

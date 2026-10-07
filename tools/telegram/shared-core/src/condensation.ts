import { readFile } from "node:fs/promises";
import type { AgentIndexEntry, SpecialistPack } from "./types.js";

/** Budget tiers for specialist packs */
const BUDGET_TIERS = {
  /** TC2 OpenClaw — tight bootstrap budget */
  compact: 4000,
  /** TC3 {{ORCHESTRATOR_NAME}} Hybrid — more room but still condensed */
  standard: 12000,
  /** Full agent context (no condensation) */
  full: Infinity,
} as const;

type BudgetTier = keyof typeof BUDGET_TIERS;

/** Extract the mission/core sections from an agent markdown file */
function extractCoreSections(content: string): {
  mission: string;
  techStack: string;
  boundaries: string;
  keyRules: string;
} {
  // Strip frontmatter
  const body = content.replace(/^---[\s\S]*?---\n*/, "");

  const sections: Record<string, string> = {};
  let currentSection = "_preamble";
  const lines = body.split("\n");

  for (const line of lines) {
    const headerMatch = line.match(/^##\s+(.+)/);
    if (headerMatch) {
      currentSection = headerMatch[1].toLowerCase();
      sections[currentSection] = "";
    } else {
      sections[currentSection] = (sections[currentSection] ?? "") + line + "\n";
    }
  }

  // Find mission-like sections
  const missionKeys = Object.keys(sections).filter(k =>
    k.includes("mission") || k.includes("role") || k.includes("identity") || k.includes("core")
  );
  const mission = missionKeys.map(k => sections[k]).join("\n").trim();

  // Find tech stack / tools sections
  const techKeys = Object.keys(sections).filter(k =>
    k.includes("tech") || k.includes("stack") || k.includes("tool") || k.includes("framework")
  );
  const techStack = techKeys.map(k => sections[k]).join("\n").trim();

  // Find boundary / rules sections
  const boundaryKeys = Object.keys(sections).filter(k =>
    k.includes("boundar") || k.includes("rule") || k.includes("scope") || k.includes("do not")
  );
  const boundaries = boundaryKeys.map(k => sections[k]).join("\n").trim();

  // Key rules or critical sections
  const ruleKeys = Object.keys(sections).filter(k =>
    k.includes("critical") || k.includes("important") || k.includes("protocol")
  );
  const keyRules = ruleKeys.map(k => sections[k]).join("\n").trim();

  return { mission, techStack, boundaries, keyRules };
}

/** Truncate text to fit budget, preserving complete lines */
function truncateToFit(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;

  const lines = text.split("\n");
  let result = "";
  for (const line of lines) {
    if (result.length + line.length + 1 > maxChars - 20) {
      result += "\n[condensed — full context in Catalyst]";
      break;
    }
    result += (result ? "\n" : "") + line;
  }
  return result;
}

/** Condense an agent file into a specialist pack */
export async function condenseAgent(
  entry: AgentIndexEntry,
  tier: BudgetTier = "compact"
): Promise<SpecialistPack> {
  const content = await readFile(entry.sourceFile, "utf-8");
  const budget = BUDGET_TIERS[tier];

  if (tier === "full") {
    // No condensation — strip frontmatter only
    const body = content.replace(/^---[\s\S]*?---\n*/, "");
    return {
      agent_id: entry.id,
      name: entry.name,
      department: entry.department,
      condensed_prompt: body,
      char_count: body.length,
      source_hash: entry.sourceHash,
      generated_at: new Date().toISOString(),
    };
  }

  const { mission, techStack, boundaries, keyRules } = extractCoreSections(content);

  // Build condensed prompt with priority ordering
  const parts: string[] = [
    `# ${entry.name}`,
    "",
    `**Role:** ${entry.description}`,
    "",
  ];

  let used = parts.join("\n").length;
  const remaining = budget - used;

  // Priority 1: Mission (40% of remaining budget)
  if (mission) {
    parts.push("## Mission");
    parts.push(truncateToFit(mission, Math.floor(remaining * 0.4)));
    parts.push("");
  }

  // Priority 2: Boundaries (20% of remaining budget)
  if (boundaries) {
    parts.push("## Boundaries");
    parts.push(truncateToFit(boundaries, Math.floor(remaining * 0.2)));
    parts.push("");
  }

  // Priority 3: Key Rules (20% of remaining budget)
  if (keyRules) {
    parts.push("## Key Rules");
    parts.push(truncateToFit(keyRules, Math.floor(remaining * 0.2)));
    parts.push("");
  }

  // Priority 4: Tech Stack (remaining budget)
  if (techStack) {
    const currentLen = parts.join("\n").length;
    const techBudget = budget - currentLen;
    if (techBudget > 200) {
      parts.push("## Tech Stack");
      parts.push(truncateToFit(techStack, techBudget));
      parts.push("");
    }
  }

  // Capabilities footer
  if (entry.capabilities.length > 0) {
    parts.push(`**Capabilities:** ${entry.capabilities.join(", ")}`);
  }

  const condensed = parts.join("\n");
  const finalPrompt = truncateToFit(condensed, budget);

  return {
    agent_id: entry.id,
    name: entry.name,
    department: entry.department,
    condensed_prompt: finalPrompt,
    char_count: finalPrompt.length,
    source_hash: entry.sourceHash,
    generated_at: new Date().toISOString(),
  };
}

/** Condense all agents into specialist packs */
export async function condenseAllAgents(
  agents: AgentIndexEntry[],
  tier: BudgetTier = "compact"
): Promise<SpecialistPack[]> {
  return Promise.all(agents.map(a => condenseAgent(a, tier)));
}

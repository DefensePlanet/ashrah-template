import { readdir, readFile } from "node:fs/promises";
import { join, basename } from "node:path";
import { createHash } from "node:crypto";
import { parse as parseYaml } from "yaml";
import type { AgentFrontmatter, AgentIndexEntry, Department } from "./types.js";

const AGENTS_DIR = join(process.env.CATALYST_ROOT ?? "{{CATALYST_ROOT}}", ".claude", "agents");

/** Extract YAML frontmatter from a markdown file */
function parseFrontmatter(content: string): AgentFrontmatter | null {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;

  let data: Record<string, unknown>;
  try {
    data = parseYaml(match[1]) ?? {};
  } catch {
    return null;
  }

  if (!data.name) return null;

  return {
    name: String(data.name),
    description: String(data.description ?? ""),
    model: String(data.model ?? "sonnet"),
    color: data.color != null ? String(data.color) : undefined,
    tools: data.tools != null ? String(data.tools) : undefined,
    infinity_model: data.infinity_model != null ? String(data.infinity_model) : undefined,
    mesh: data.mesh as AgentFrontmatter["mesh"],
  };
}

/** Map agent to department based on name/role */
function classifyDepartment(name: string, description: string): Department {
  const n = name.toLowerCase();
  const d = description.toLowerCase();

  // Command
  if (n.includes("boss") || n.includes("system architect")) return "command";

  // Quality
  if (n.includes("code reviewer") || n.includes("debugger") || n.includes("validator") || n.includes("security")) return "quality";

  // Creative
  if (n.includes("graphic") || n.includes("camera") || n.includes("ui designer") || n.includes("studio engineer") || n.includes("3d")) return "creative";

  // Business
  if (n.includes("marketing") || n.includes("business analyst") || n.includes("product strategist") || n.includes("venture") || n.includes("brand") || n.includes("seo")) return "business";

  // Research
  if (n.includes("research") || n.includes("ai nerd") || n.includes("2nd brain") || n.includes("algo wizard")) return "research";

  // Operations
  if (n.includes("automator") || n.includes("bowser") || n.includes("blockchain")) return "operations";

  // Engineering (default for dev agents)
  if (n.includes("backend") || n.includes("frontend") || n.includes("mobile") || n.includes("macos") || n.includes("shopify") || n.includes("mcp server")) return "engineering";

  return "engineering";
}

/** Extract emoji from agent name */
function extractEmoji(name: string): { emoji: string; shortName: string } {
  // Match emoji at the start (including compound emojis with ZWJ)
  const emojiMatch = name.match(/^([\p{Emoji_Presentation}\p{Emoji}\u200d\ufe0f\u{1f3fb}-\u{1f3ff}]+)\s*/u);
  if (emojiMatch) {
    return {
      emoji: emojiMatch[1].trim(),
      shortName: name.slice(emojiMatch[0].length).trim(),
    };
  }
  return { emoji: "", shortName: name };
}

/** Infer capabilities from description when mesh.provides is missing */
function inferCapabilities(description: string): string[] {
  const caps: string[] = [];
  const d = description.toLowerCase();

  if (d.includes("api")) caps.push("api-design");
  if (d.includes("database") || d.includes("schema")) caps.push("database");
  if (d.includes("react") || d.includes("frontend") || d.includes("web")) caps.push("web-frontend");
  if (d.includes("mobile") || d.includes("ios") || d.includes("swift")) caps.push("mobile-development");
  if (d.includes("macos") || d.includes("appkit")) caps.push("macos-development");
  if (d.includes("security") || d.includes("vulnerability")) caps.push("security-assessment");
  if (d.includes("test")) caps.push("testing");
  if (d.includes("debug")) caps.push("debugging");
  if (d.includes("design") || d.includes("ui") || d.includes("ux")) caps.push("design");
  if (d.includes("automat")) caps.push("automation");
  if (d.includes("marketing") || d.includes("seo")) caps.push("marketing");
  if (d.includes("research")) caps.push("research");
  if (d.includes("shopify") || d.includes("e-commerce")) caps.push("e-commerce");
  if (d.includes("video") || d.includes("image") || d.includes("photo")) caps.push("media-generation");
  if (d.includes("3d") || d.includes("blender") || d.includes("render")) caps.push("3d-modeling");
  if (d.includes("blockchain") || d.includes("web3") || d.includes("smart contract")) caps.push("blockchain");
  if (d.includes("mcp") || d.includes("protocol")) caps.push("mcp-servers");
  if (d.includes("knowledge") || d.includes("obsidian") || d.includes("pkm")) caps.push("knowledge-management");
  if (d.includes("brand")) caps.push("brand-integrity");
  if (d.includes("algorithm") || d.includes("data structure")) caps.push("algorithms");
  if (d.includes("obs") || d.includes("davinci") || d.includes("recording")) caps.push("av-production");
  if (d.includes("strategy") || d.includes("roadmap")) caps.push("product-strategy");
  if (d.includes("business") || d.includes("kpi") || d.includes("metric")) caps.push("business-analytics");
  if (d.includes("playwright") || d.includes("scraping") || d.includes("browser")) caps.push("web-automation");
  if (d.includes("model") || d.includes("ai") || d.includes("inference")) caps.push("ai-models");

  return caps.length > 0 ? caps : ["general"];
}

/** Parse all agent files and produce index entries */
export async function parseAllAgents(): Promise<AgentIndexEntry[]> {
  const files = await readdir(AGENTS_DIR);
  const mdFiles = files.filter(f => f.endsWith(".md")).sort();

  const entries: AgentIndexEntry[] = [];

  for (const file of mdFiles) {
    const filePath = join(AGENTS_DIR, file);
    const content = await readFile(filePath, "utf-8");
    const frontmatter = parseFrontmatter(content);

    if (!frontmatter) continue;

    const hash = createHash("sha256").update(content).digest("hex").slice(0, 12);
    const { emoji, shortName } = extractEmoji(frontmatter.name);
    const capabilities = frontmatter.mesh?.provides ?? inferCapabilities(frontmatter.description);
    const collaborators = frontmatter.mesh?.can_request ?? [];
    const department = classifyDepartment(frontmatter.name, frontmatter.description);

    entries.push({
      id: basename(file, ".md"),
      name: frontmatter.name,
      emoji,
      shortName,
      description: frontmatter.description,
      model: frontmatter.model,
      capabilities,
      collaborators,
      department,
      sourceFile: filePath,
      sourceHash: hash,
    });
  }

  return entries;
}

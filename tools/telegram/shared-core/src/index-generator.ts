import { writeFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { parseAllAgents } from "./agent-parser.js";
import type { CapabilityIndex, Department, AgentIndexEntry } from "./types.js";

const OUTPUT_DIR = join(process.env.CATALYST_ROOT ?? "{{CATALYST_ROOT}}", "tools", "telegram", "shared-core", "output");

/** Build the full capability index from all agents */
export async function buildCapabilityIndex(): Promise<CapabilityIndex> {
  const agents = await parseAllAgents();

  // Group by department
  const departments: Record<Department, AgentIndexEntry[]> = {
    engineering: [],
    creative: [],
    business: [],
    quality: [],
    research: [],
    operations: [],
    command: [],
  };

  for (const agent of agents) {
    departments[agent.department].push(agent);
  }

  // Build capability -> agent name map
  const capabilityMap: Record<string, string[]> = {};
  for (const agent of agents) {
    for (const cap of agent.capabilities) {
      if (!capabilityMap[cap]) capabilityMap[cap] = [];
      capabilityMap[cap].push(agent.name);
    }
  }

  return {
    version: "0.1.0",
    generated_at: new Date().toISOString(),
    agent_count: agents.length,
    departments,
    agents,
    capability_map: capabilityMap,
  };
}

/** Generate compact markdown for TC2 bootstrap injection (~3-4K chars) */
export function generateBootstrapMarkdown(index: CapabilityIndex): string {
  const lines: string[] = [
    "## Specialist Roster",
    "",
    `You have access to ${index.agent_count} Catalyst specialist agents. When a question matches a specialist's domain, channel their expertise.`,
    "",
  ];

  const deptLabels: Record<Department, string> = {
    engineering: "Engineering",
    creative: "Creative Studio",
    business: "Business & Strategy",
    quality: "Quality & Ops",
    research: "Research Lab",
    operations: "Operations",
    command: "Command",
  };

  for (const [dept, label] of Object.entries(deptLabels) as [Department, string][]) {
    const agents = index.departments[dept];
    if (!agents.length) continue;

    lines.push(`### ${label}`);
    for (const a of agents) {
      const caps = a.capabilities.slice(0, 4).join(", ");
      lines.push(`- **${a.name}** — ${caps}`);
    }
    lines.push("");
  }

  lines.push("### Capability Quick-Match");
  lines.push("");
  lines.push("| Domain | Route to |");
  lines.push("|--------|----------|");

  // Top capability mappings (deduplicated, most useful)
  const routingTable: [string, string][] = [
    ["API, database, deployment, DNS, Cloudflare", "🏛️ Backend Developer"],
    ["React, Next.js, CSS, animations, web UI", "🎨 Frontend Developer"],
    ["iOS, Swift, React Native, App Store", "📱 Mobile Developer"],
    ["macOS, AppKit, SwiftUI desktop", "💻 macOS Dev"],
    ["Shopify, e-commerce, Liquid themes", "🛒 Shopify Exec"],
    ["MCP servers, protocol, transport", "🏄🏼‍♂️ MCP Server Dude"],
    ["Logos, vectors, infographics, brand assets", "🎨 Graphic Designer"],
    ["Photorealistic images, video, Sora, Veo", "📸 Camera Man"],
    ["Wireframes, prototypes, design systems", "📐 UI Designer"],
    ["OBS, DaVinci Resolve, recording, streaming", "🎬 Studio Engineer"],
    ["3D, Blender, modeling, rendering", "🧊 3D Developer"],
    ["Marketing, ads, social, email campaigns", "📣 CMO"],
    ["KPIs, revenue, metrics, cohort analysis", "📊 Business Analyst"],
    ["Product roadmap, positioning, go-to-market", "🎯 Product Strategist"],
    ["Pre-build validation, market research", "🧭 Venture Analyst"],
    ["Brand consistency, visual identity", "🎯 Brand Specialist"],
    ["SEO, meta tags, Core Web Vitals", "🔍 SEO Analyzer"],
    ["Code quality, review, best practices", "🧐 Code Reviewer"],
    ["Bug investigation, root cause analysis", "👾 Debugger"],
    ["Testing, e2e, visual regression", "🧪 Validator"],
    ["Security audit, OWASP, threat modeling", "🛡️ Security Analyst"],
    ["n8n, macOS automation, workflows", "🤖 Automator"],
    ["Web scraping, Playwright, account creation", "🐲 Bowser"],
    ["Algorithms, data structures, optimization", "🧮 Algo Wizard"],
    ["Multi-source research, citations", "🔍 Research Agent"],
    ["AI models, Hugging Face, inference", "🤓 AI Nerd"],
    ["PKM, Obsidian, Apple Notes, photos", "🧠 2nd Brain Wizard"],
    ["Smart contracts, Solidity, Web3", "⛓️ Blockchain Agent"],
  ];

  for (const [domain, agent] of routingTable) {
    lines.push(`| ${domain} | ${agent} |`);
  }

  lines.push("");
  lines.push("To invoke: mention the specialist by name or describe the domain. Use `/specialist [name]` for explicit activation.");

  return lines.join("\n");
}

/** Generate full JSON index for programmatic use */
export async function writeOutputs(index: CapabilityIndex): Promise<{ jsonPath: string; mdPath: string }> {
  await mkdir(OUTPUT_DIR, { recursive: true });

  const jsonPath = join(OUTPUT_DIR, "capability-index.json");
  const mdPath = join(OUTPUT_DIR, "capability-index.md");

  await writeFile(jsonPath, JSON.stringify(index, null, 2));
  await writeFile(mdPath, generateBootstrapMarkdown(index));

  return { jsonPath, mdPath };
}

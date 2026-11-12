#!/usr/bin/env bun
import { writeFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { parseAllAgents } from "./agent-parser.js";
import { buildCapabilityIndex, generateBootstrapMarkdown, writeOutputs } from "./index-generator.js";
import { condenseAllAgents } from "./condensation.js";
import { buildManifest, saveManifest, checkDrift } from "./manifest.js";
import { classifyMessage } from "./trigger-classifier.js";
import { formatReport, closeTelemetry } from "./telemetry.js";

const OUTPUT_DIR = join(process.env.CATALYST_ROOT ?? "{{CATALYST_ROOT}}", "tools", "telegram", "shared-core", "output");

const args = process.argv.slice(2);
const command = args[0];

async function generate() {
  const indexOnly = args.includes("--index-only");
  const packsOnly = args.includes("--packs-only");

  console.log("🔍 Parsing all Catalyst agents...");
  const agents = await parseAllAgents();
  console.log(`   Found ${agents.length} agents\n`);

  if (!packsOnly) {
    // Build capability index
    console.log("📊 Building capability index...");
    const index = await buildCapabilityIndex();
    const { jsonPath, mdPath } = await writeOutputs(index);
    console.log(`   ✅ JSON: ${jsonPath}`);
    console.log(`   ✅ Markdown: ${mdPath}`);

    // Show department breakdown
    console.log("\n📋 Department breakdown:");
    for (const [dept, members] of Object.entries(index.departments)) {
      if (members.length === 0) continue;
      const names = members.map(m => m.emoji || "•").join(" ");
      console.log(`   ${dept}: ${names} (${members.length})`);
    }

    // Show capability count
    const capCount = Object.keys(index.capability_map).length;
    console.log(`\n🏷️  ${capCount} unique capabilities indexed`);

    // Bootstrap preview
    const bootstrap = generateBootstrapMarkdown(index);
    console.log(`\n📝 Bootstrap markdown: ${bootstrap.length} chars (target: <4000)`);
  }

  if (!indexOnly) {
    // Generate specialist packs
    console.log("\n📦 Generating specialist packs (compact tier)...");
    await mkdir(join(OUTPUT_DIR, "packs"), { recursive: true });

    const packs = await condenseAllAgents(agents, "compact");
    for (const pack of packs) {
      const packPath = join(OUTPUT_DIR, "packs", `${pack.agent_id}.md`);
      await writeFile(packPath, pack.condensed_prompt);
    }

    console.log(`   ✅ ${packs.length} packs generated`);

    // Show size distribution
    const sizes = packs.map(p => p.char_count).sort((a, b) => a - b);
    const avg = Math.round(sizes.reduce((a, b) => a + b, 0) / sizes.length);
    const overBudget = packs.filter(p => p.char_count > 4000);

    console.log(`   Size range: ${sizes[0]}–${sizes[sizes.length - 1]} chars`);
    console.log(`   Average: ${avg} chars`);
    if (overBudget.length > 0) {
      console.log(`   ⚠️  ${overBudget.length} packs over 4K budget:`);
      for (const p of overBudget) {
        console.log(`      ${p.name}: ${p.char_count} chars`);
      }
    } else {
      console.log(`   ✅ All packs within 4K budget`);
    }

    // Save pack hashes to manifest
    const manifest = buildManifest(agents);
    for (const entry of manifest.agents) {
      const pack = packs.find(p => p.agent_id === entry.id);
      if (pack) entry.pack_hash = pack.source_hash;
    }
    await saveManifest(manifest);
    console.log(`\n📋 Sync manifest saved`);
  }

  console.log("\n✨ Done!");
}

async function drift() {
  console.log("🔍 Checking for drift...\n");
  const agents = await parseAllAgents();
  const result = await checkDrift(agents);

  if (result.drifted.length === 0 && result.added.length === 0 && result.removed.length === 0) {
    console.log("✅ No drift detected — all agents in sync");
    return;
  }

  if (result.drifted.length > 0) {
    console.log(`⚠️  ${result.drifted.length} agents have changed since last sync:`);
    for (const d of result.drifted) {
      console.log(`   ${d.name} (${d.oldHash} → ${d.newHash})`);
    }
  }

  if (result.added.length > 0) {
    console.log(`\n➕ ${result.added.length} new agents:`);
    for (const id of result.added) {
      console.log(`   ${id}`);
    }
  }

  if (result.removed.length > 0) {
    console.log(`\n➖ ${result.removed.length} removed agents:`);
    for (const id of result.removed) {
      console.log(`   ${id}`);
    }
  }

  console.log("\nRun `bun run generate` to re-sync.");
}

async function classify() {
  const message = args.slice(1).join(" ");
  if (!message) {
    console.log("Usage: bun run src/cli.ts classify <message>");
    return;
  }

  console.log(`🔍 Classifying: "${message}"\n`);
  const result = classifyMessage(message);

  console.log(`Specialist: ${result.specialist ?? "(none — {{ORCHESTRATOR_NAME}} handles)"}`);
  console.log(`Confidence: ${result.confidence}`);
  console.log(`Method:     ${result.method}`);

  if (result.candidates.length > 0) {
    console.log(`\nCandidates:`);
    for (const c of result.candidates) {
      console.log(`  ${c.name}: ${c.score}`);
    }
  }
}

async function telemetryReport() {
  const days = parseInt(args[1] || "7", 10);
  console.log(formatReport(days));
  closeTelemetry();
}

// Main
switch (command) {
  case "generate":
    await generate();
    break;
  case "check-drift":
    await drift();
    break;
  case "classify":
    await classify();
    break;
  case "telemetry":
    await telemetryReport();
    break;
  default:
    console.log(`
@catalyst/telegram-shared-core

Usage:
  bun run src/cli.ts generate          Generate capability index + specialist packs
  bun run src/cli.ts generate --index-only   Index only (no packs)
  bun run src/cli.ts generate --packs-only   Packs only (no index)
  bun run src/cli.ts check-drift       Check for agent changes since last sync
  bun run src/cli.ts classify <msg>    Test the trigger classifier on a message
  bun run src/cli.ts telemetry [days]  Show specialist usage telemetry report
`);
}

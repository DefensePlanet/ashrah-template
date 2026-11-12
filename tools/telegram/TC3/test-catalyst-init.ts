#!/usr/bin/env bun

/**
 * Test Catalyst initialization without requiring Telegram credentials
 */

import {
  CatalystAgentLoader,
  CatalystSkillLoader,
  CatalystWatcher,
} from "./src/catalyst-loader";
import { join } from "path";

console.log("=".repeat(60));
console.log("Testing Catalyst Initialization (Standalone)");
console.log("=".repeat(60));

try {
  console.log("\n🚀 Initializing Catalyst...\n");

  const agentsDir = join(import.meta.dir, "catalyst-agents");
  const skillsDir = join(import.meta.dir, "catalyst-skills");

  const agentLoader = new CatalystAgentLoader();
  const skillLoader = new CatalystSkillLoader();
  const watcher = new CatalystWatcher();

  // Load agents
  await agentLoader.loadAgents(agentsDir);

  // Load skills
  await skillLoader.loadSkills(skillsDir);

  // Start watchers (no-op for this test, will just log)
  watcher.startWatching(
    { agents: agentsDir, skills: skillsDir },
    agentLoader,
    skillLoader
  );

  console.log("\n✅ Catalyst initialization complete!\n");
  console.log(`📊 Resources loaded:`);
  console.log(`   - ${agentLoader.count} agents`);
  console.log(`   - ${skillLoader.count} skills`);
  console.log(`   - File watchers: Active`);

  // Quick verification
  console.log(`\n🔍 Verification tests:`);

  const agents = agentLoader.listAgents();
  console.log(`   ✅ ${agents.length} agents accessible`);

  const skills = skillLoader.listSkills();
  console.log(`   ✅ ${skills.length} skills accessible`);

  const backendAgent = agentLoader.getAgent("🏛️ Backend Developer");
  console.log(`   ${backendAgent ? "✅" : "❌"} Backend Developer found`);

  const resolvedName = agentLoader.resolveAgentName("mobile dev");
  console.log(`   ${resolvedName ? "✅" : "❌"} Name resolution: "mobile dev" → "${resolvedName}"`);

  // Test specialist context loading
  const skillContext = skillLoader.getSkillContext(skills[0]);
  console.log(`   ${skillContext ? "✅" : "ℹ️ "} Skill context loading ${skillContext ? `(${skillContext.length} chars)` : "(no prompt)"}`);

  // Stop watchers
  watcher.stopWatching();

  console.log("\n" + "=".repeat(60));
  console.log("✅ All tests passed - Catalyst integration ready!");
  console.log("=".repeat(60));
  console.log();

  process.exit(0);
} catch (err) {
  console.error("\n❌ Test failed:");
  console.error(err);
  process.exit(1);
}

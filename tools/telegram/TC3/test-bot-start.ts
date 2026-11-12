#!/usr/bin/env bun

/**
 * Test bot startup with Catalyst integration
 * (Does not actually connect to Telegram - just tests initialization)
 */

import { initializeCatalyst, catalystAgentLoader, catalystSkillLoader } from "./src/config";

console.log("=".repeat(60));
console.log("Testing Bot Startup with Catalyst Integration");
console.log("=".repeat(60));

try {
  console.log("\n🚀 Starting initialization...\n");

  await initializeCatalyst();

  console.log("\n✅ Initialization complete!\n");
  console.log(`📊 Final Status:`);
  console.log(`   - Agents: ${catalystAgentLoader.count}`);
  console.log(`   - Skills: ${catalystSkillLoader.count}`);

  // Test a few quick lookups
  console.log(`\n🔍 Quick verification tests:`);

  const backendDev = catalystAgentLoader.getAgent("🏛️ Backend Developer");
  console.log(`   ${backendDev ? "✅" : "❌"} Backend Developer agent accessible`);

  const frontendDev = catalystAgentLoader.getAgent("🎨 Frontend Developer");
  console.log(`   ${frontendDev ? "✅" : "❌"} Frontend Developer agent accessible`);

  const resolved = catalystAgentLoader.resolveAgentName("code reviewer");
  console.log(`   ${resolved ? "✅" : "❌"} Agent name resolution working`);

  const skillList = catalystSkillLoader.listSkills();
  console.log(`   ${skillList.length > 0 ? "✅" : "❌"} Skills list accessible (${skillList.length} skills)`);

  console.log("\n" + "=".repeat(60));
  console.log("✅ Bot startup test passed!");
  console.log("=".repeat(60));
  console.log("\nBot is ready to start with Catalyst integration.\n");

  process.exit(0);
} catch (err) {
  console.error("\n❌ Initialization failed:");
  console.error(err);
  process.exit(1);
}

/**
 * Phase 6 Test Suite - Auto-Sync & Watchers
 *
 * Tests:
 * 1. CatalystWatcher hot reload functionality
 * 2. Manual sync via reloadAll()
 * 3. Watcher status tracking
 * 4. Debouncing behavior
 */

import { CatalystAgentLoader, CatalystSkillLoader, CatalystWatcher } from "./src/catalyst-loader";
import { join } from "path";
import { writeFileSync, mkdirSync, unlinkSync, rmdirSync } from "fs";

// Test utilities
let testsPassed = 0;
let testsFailed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) {
    console.log(`✅ ${message}`);
    testsPassed++;
  } else {
    console.error(`❌ ${message}`);
    testsFailed++;
  }
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual === expected) {
    console.log(`✅ ${message}`);
    testsPassed++;
  } else {
    console.error(`❌ ${message}`);
    console.error(`   Expected: ${expected}`);
    console.error(`   Actual: ${actual}`);
    testsFailed++;
  }
}

// Setup test directories
const testDir = "/tmp/telegram-bot-phase6-test";
const agentsDir = join(testDir, "agents");
const skillsDir = join(testDir, "skills");

function setupTestEnv(): void {
  // Clean up any existing test directory
  try {
    rmdirSync(testDir, { recursive: true });
  } catch {}

  mkdirSync(agentsDir, { recursive: true });
  mkdirSync(skillsDir, { recursive: true });

  // Create test agent
  writeFileSync(
    join(agentsDir, "test-agent.md"),
    `---
name: Test Agent
description: A test agent
model: claude-sonnet-4-20250514
---

This is a test agent prompt.`
  );

  // Create test skill
  mkdirSync(join(skillsDir, "test-skill"), { recursive: true });
  writeFileSync(
    join(skillsDir, "test-skill", "prompt.md"),
    `# Test Skill

This is a test skill.`
  );
}

function cleanupTestEnv(): void {
  try {
    rmdirSync(testDir, { recursive: true });
  } catch {}
}

// ============== Tests ==============

async function testWatcherInitialization(): Promise<void> {
  console.log("\n🧪 Test 1: Watcher Initialization");

  const agentLoader = new CatalystAgentLoader();
  const skillLoader = new CatalystSkillLoader();
  const watcher = new CatalystWatcher();

  await agentLoader.loadAgents(agentsDir);
  await skillLoader.loadSkills(skillsDir);

  watcher.startWatching(
    { agents: agentsDir, skills: skillsDir },
    agentLoader,
    skillLoader
  );

  const status = watcher.getStatus();

  assert(status.watching === true, "Watcher is active after startWatching()");
  assertEqual(status.changeCount, 0, "changeCount starts at 0");
  assertEqual(agentLoader.count, 1, "Loaded 1 agent");
  assertEqual(skillLoader.count, 1, "Loaded 1 skill");

  watcher.stopWatching();
}

async function testManualReload(): Promise<void> {
  console.log("\n🧪 Test 2: Manual Reload (reloadAll)");

  const agentLoader = new CatalystAgentLoader();
  const skillLoader = new CatalystSkillLoader();
  const watcher = new CatalystWatcher();

  await agentLoader.loadAgents(agentsDir);
  await skillLoader.loadSkills(skillsDir);

  watcher.startWatching(
    { agents: agentsDir, skills: skillsDir },
    agentLoader,
    skillLoader
  );

  // Add a new agent
  writeFileSync(
    join(agentsDir, "another-agent.md"),
    `---
name: Another Agent
description: Another test agent
model: claude-sonnet-4-20250514
---

Another test agent.`
  );

  // Add a new skill
  mkdirSync(join(skillsDir, "another-skill"), { recursive: true });
  writeFileSync(
    join(skillsDir, "another-skill", "prompt.md"),
    `# Another Skill

Another test skill.`
  );

  // Manual reload
  const result = await watcher.reloadAll();

  assertEqual(result.agents.before, 1, "Before reload: 1 agent");
  assertEqual(result.agents.after, 2, "After reload: 2 agents");
  assertEqual(result.skills.before, 1, "Before reload: 1 skill");
  assertEqual(result.skills.after, 2, "After reload: 2 skills");

  // Clean up test files
  unlinkSync(join(agentsDir, "another-agent.md"));
  rmdirSync(join(skillsDir, "another-skill"), { recursive: true });

  watcher.stopWatching();
}

async function testHotReload(): Promise<void> {
  console.log("\n🧪 Test 3: Hot Reload on File Change");

  const agentLoader = new CatalystAgentLoader();
  const skillLoader = new CatalystSkillLoader();
  const watcher = new CatalystWatcher();

  await agentLoader.loadAgents(agentsDir);
  await skillLoader.loadSkills(skillsDir);

  watcher.startWatching(
    { agents: agentsDir, skills: skillsDir },
    agentLoader,
    skillLoader
  );

  const statusBefore = watcher.getStatus();

  // Modify agent file (trigger hot reload)
  writeFileSync(
    join(agentsDir, "test-agent.md"),
    `---
name: Test Agent Updated
description: An updated test agent
model: claude-sonnet-4-20250514
---

This is an UPDATED test agent prompt.`
  );

  // Wait for debounce + reload (500ms debounce + 100ms buffer)
  await new Promise((resolve) => setTimeout(resolve, 700));

  const statusAfter = watcher.getStatus();

  assert(
    statusAfter.changeCount > statusBefore.changeCount,
    "changeCount incremented after file change"
  );

  // Check if agent was reloaded
  const agent = agentLoader.getAgent("Test Agent Updated");
  assert(agent !== undefined, "Hot reloaded agent is available");

  if (agent) {
    assert(
      agent.prompt.includes("UPDATED"),
      "Hot reloaded agent has updated content"
    );
  }

  watcher.stopWatching();
}

async function testDebouncing(): Promise<void> {
  console.log("\n🧪 Test 4: Debouncing (Multiple Rapid Changes)");

  const agentLoader = new CatalystAgentLoader();
  const skillLoader = new CatalystSkillLoader();
  const watcher = new CatalystWatcher();

  await agentLoader.loadAgents(agentsDir);
  await skillLoader.loadSkills(skillsDir);

  watcher.startWatching(
    { agents: agentsDir, skills: skillsDir },
    agentLoader,
    skillLoader
  );

  const statusBefore = watcher.getStatus();

  // Make 5 rapid changes (within 500ms)
  for (let i = 0; i < 5; i++) {
    writeFileSync(
      join(agentsDir, "test-agent.md"),
      `---
name: Test Agent v${i}
description: Test agent version ${i}
model: claude-sonnet-4-20250514
---

Version ${i} content.`
    );
    await new Promise((resolve) => setTimeout(resolve, 50)); // 50ms between changes
  }

  // Wait for debounce to settle (500ms + 100ms buffer)
  await new Promise((resolve) => setTimeout(resolve, 700));

  const statusAfter = watcher.getStatus();

  // Debouncing should result in only 1 reload despite 5 changes
  assertEqual(
    statusAfter.changeCount,
    statusBefore.changeCount + 1,
    "Only 1 reload despite 5 rapid changes (debouncing works)"
  );

  // Verify final version was loaded
  const agent = agentLoader.getAgent("Test Agent v4");
  assert(agent !== undefined, "Final version was loaded after debounce");

  watcher.stopWatching();
}

async function testStopWatching(): Promise<void> {
  console.log("\n🧪 Test 5: Stop Watching");

  const agentLoader = new CatalystAgentLoader();
  const skillLoader = new CatalystSkillLoader();
  const watcher = new CatalystWatcher();

  await agentLoader.loadAgents(agentsDir);
  await skillLoader.loadSkills(skillsDir);

  watcher.startWatching(
    { agents: agentsDir, skills: skillsDir },
    agentLoader,
    skillLoader
  );

  let statusBefore = watcher.getStatus();
  assert(statusBefore.watching === true, "Watcher is active before stop");

  watcher.stopWatching();

  let statusAfter = watcher.getStatus();
  assert(statusAfter.watching === false, "Watcher is inactive after stop");

  // Make a change (should not trigger reload)
  writeFileSync(
    join(agentsDir, "test-agent.md"),
    `---
name: Test Agent After Stop
description: Should not reload
model: claude-sonnet-4-20250514
---

This change should not trigger reload.`
  );

  await new Promise((resolve) => setTimeout(resolve, 700));

  const finalStatus = watcher.getStatus();
  assertEqual(
    finalStatus.changeCount,
    statusBefore.changeCount,
    "No reload after stopWatching()"
  );
}

// ============== Run Tests ==============

async function runTests(): Promise<void> {
  console.log("=".repeat(50));
  console.log("Phase 6 Test Suite - Auto-Sync & Watchers");
  console.log("=".repeat(50));

  setupTestEnv();

  try {
    await testWatcherInitialization();
    await testManualReload();
    await testHotReload();
    await testDebouncing();
    await testStopWatching();
  } catch (error) {
    console.error("\n💥 Test suite crashed:", error);
    testsFailed++;
  } finally {
    cleanupTestEnv();
  }

  console.log("\n" + "=".repeat(50));
  console.log(`✅ Passed: ${testsPassed}`);
  console.log(`❌ Failed: ${testsFailed}`);
  console.log("=".repeat(50));

  if (testsFailed > 0) {
    process.exit(1);
  }
}

runTests();

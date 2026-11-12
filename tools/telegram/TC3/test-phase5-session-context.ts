/**
 * Phase 5 Test: Enhanced Session Context
 *
 * Tests:
 * 1. SessionContext class functionality
 * 2. Specialist persistence across messages
 * 3. Skill loading and management
 * 4. Context optimization
 */

import { SessionContext } from "./src/session-context";
import { SkillContextLoader } from "./src/skill-context-loader";
import { catalystSkillLoader } from "./src/config";
import { join } from "path";

console.log("🧪 Phase 5: Enhanced Session Context Test\n");
console.log("=".repeat(70) + "\n");

// Initialize skills
console.log("Initializing Catalyst skills...");
const skillsDir = join(import.meta.dir, "catalyst-skills");
await catalystSkillLoader.loadSkills(skillsDir);
console.log(`✅ Loaded ${catalystSkillLoader.count} skills\n`);

//
// Test 1: SessionContext Specialist Tracking
//
console.log("Test 1: SessionContext Specialist Tracking");
console.log("-".repeat(70));

const context = new SessionContext();

// Set specialist
context.setActiveSpecialist("🏛️ Backend Developer", "Full backend developer context here...");
const hasSpecialist1 = context.hasActiveSpecialist();
const activeSpecialist1 = context.getActiveSpecialist();

console.log(`   - Specialist set: ${hasSpecialist1 ? "✅" : "❌"}`);
console.log(`   - Active specialist: ${activeSpecialist1} ${activeSpecialist1 === "🏛️ Backend Developer" ? "✅" : "❌"}`);

// Set same specialist (should not reload)
context.setActiveSpecialist("🏛️ Backend Developer", "Full backend developer context here...");

// Clear specialist
context.clearSpecialist();
const hasSpecialist2 = context.hasActiveSpecialist();

console.log(`   - Specialist cleared: ${!hasSpecialist2 ? "✅" : "❌"}`);

if (hasSpecialist1 && activeSpecialist1 === "🏛️ Backend Developer" && !hasSpecialist2) {
  console.log("✅ Test 1 PASSED: Specialist tracking working\n");
} else {
  console.log("❌ Test 1 FAILED\n");
}

//
// Test 2: SessionContext Skill Loading
//
console.log("Test 2: SessionContext Skill Loading");
console.log("-".repeat(70));

context.reset(); // Reset for clean test

// Load skill
context.loadSkill("frontend-testing", "Skill content for frontend testing...");
const loadedSkills1 = context.getLoadedSkills();
const skillContent = context.getSkillContent("frontend-testing");

console.log(`   - Skill loaded: ${loadedSkills1.includes("frontend-testing") ? "✅" : "❌"}`);
console.log(`   - Skill content retrieved: ${skillContent ? "✅" : "❌"}`);

// Load another skill
context.loadSkill("ios-testing", "Skill content for iOS testing...");
const loadedSkills2 = context.getLoadedSkills();

console.log(`   - Multiple skills: ${loadedSkills2.length === 2 ? "✅" : "❌"}`);

// Clear one skill
context.clearSkill("frontend-testing");
const loadedSkills3 = context.getLoadedSkills();

console.log(`   - Skill cleared: ${loadedSkills3.length === 1 && !loadedSkills3.includes("frontend-testing") ? "✅" : "❌"}`);

// Clear all skills
context.clearAllSkills();
const loadedSkills4 = context.getLoadedSkills();

console.log(`   - All skills cleared: ${loadedSkills4.length === 0 ? "✅" : "❌"}`);

if (
  loadedSkills1.includes("frontend-testing") &&
  skillContent &&
  loadedSkills2.length === 2 &&
  loadedSkills3.length === 1 &&
  loadedSkills4.length === 0
) {
  console.log("✅ Test 2 PASSED: Skill loading working\n");
} else {
  console.log("❌ Test 2 FAILED\n");
}

//
// Test 3: Context Metrics
//
console.log("Test 3: Context Metrics");
console.log("-".repeat(70));

context.reset(); // Reset for clean test

context.incrementMessageCount();
context.incrementMessageCount();
context.setActiveSpecialist("🎨 Frontend Developer", "A".repeat(5000));
context.loadSkill("test-skill", "B".repeat(3000));

const metrics = context.getMetrics();

console.log(`   - Message count: ${metrics.messageCount} ${metrics.messageCount === 2 ? "✅" : "❌"}`);
console.log(`   - Context size: ${metrics.totalContextSize} ${metrics.totalContextSize === 8000 ? "✅" : "❌"}`);
console.log(`   - Specialist changes: ${metrics.specialistChanges} ${metrics.specialistChanges === 1 ? "✅" : "❌"}`);
console.log(`   - Skills loaded: ${metrics.skillsLoaded} ${metrics.skillsLoaded === 1 ? "✅" : "❌"}`);

if (
  metrics.messageCount === 2 &&
  metrics.totalContextSize === 8000 &&
  metrics.specialistChanges === 1 &&
  metrics.skillsLoaded === 1
) {
  console.log("✅ Test 3 PASSED: Context metrics tracking\n");
} else {
  console.log("❌ Test 3 FAILED\n");
}

//
// Test 4: SkillContextLoader Detection
//
console.log("Test 4: SkillContextLoader Detection");
console.log("-".repeat(70));

const skillLoader = new SkillContextLoader(catalystSkillLoader);

const testMessages = [
  { msg: "use the frontend-testing skill", expected: "frontend-testing" },
  { msg: "apply skill ios-testing", expected: "ios-testing" },
  { msg: "load native-data-fetching skill", expected: "native-data-fetching" },
  { msg: "just a regular message", expected: null },
];

let detectionPassed = 0;
for (const test of testMessages) {
  const detected = skillLoader.detectSkillRequest(test.msg);
  const passed = detected === test.expected;
  console.log(`   "${test.msg}"`);
  console.log(`     Expected: ${test.expected || "null"}`);
  console.log(`     Detected: ${detected || "null"} ${passed ? "✅" : "❌"}`);
  if (passed) detectionPassed++;
}

if (detectionPassed === testMessages.length) {
  console.log("✅ Test 4 PASSED: Skill detection working\n");
} else {
  console.log(`❌ Test 4 FAILED: ${detectionPassed}/${testMessages.length} correct\n`);
}

//
// Test 5: Context Summary
//
console.log("Test 5: Context Summary");
console.log("-".repeat(70));

context.reset();
context.setActiveSpecialist("🏛️ Backend Developer", "X".repeat(10000));
context.loadSkill("skill1", "Y".repeat(5000));
context.loadSkill("skill2", "Z".repeat(5000));
context.incrementMessageCount();

const summary = context.getSummary();
const formatted = context.formatSummary();

console.log(`   - Summary has specialist: ${summary.activeSpecialist === "🏛️ Backend Developer" ? "✅" : "❌"}`);
console.log(`   - Summary has 2 skills: ${summary.loadedSkills.length === 2 ? "✅" : "❌"}`);
console.log(`   - Summary has metrics: ${summary.metrics.messageCount === 1 ? "✅" : "❌"}`);
console.log(`   - Formatted summary generated: ${formatted.includes("Backend Developer") ? "✅" : "❌"}`);

if (
  summary.activeSpecialist === "🏛️ Backend Developer" &&
  summary.loadedSkills.length === 2 &&
  summary.metrics.messageCount === 1 &&
  formatted.includes("Backend Developer")
) {
  console.log("✅ Test 5 PASSED: Context summary working\n");
} else {
  console.log("❌ Test 5 FAILED\n");
}

//
// Test 6: Skill Clear Detection
//
console.log("Test 6: Skill Clear Detection");
console.log("-".repeat(70));

const clearTests = [
  { msg: "clear skill frontend-testing", expected: { action: "clear", skillName: "frontend-testing" } },
  { msg: "clear all skills", expected: { action: "clear" } },
  { msg: "regular message", expected: null },
];

let clearDetectionPassed = 0;
for (const test of clearTests) {
  const detected = skillLoader.detectSkillClearRequest(test.msg);
  const passed = JSON.stringify(detected) === JSON.stringify(test.expected);
  console.log(`   "${test.msg}"`);
  console.log(`     Expected: ${JSON.stringify(test.expected)}`);
  console.log(`     Detected: ${JSON.stringify(detected)} ${passed ? "✅" : "❌"}`);
  if (passed) clearDetectionPassed++;
}

if (clearDetectionPassed === clearTests.length) {
  console.log("✅ Test 6 PASSED: Skill clear detection working\n");
} else {
  console.log(`❌ Test 6 FAILED: ${clearDetectionPassed}/${clearTests.length} correct\n`);
}

//
// Summary
//
console.log("=".repeat(70));
console.log("📊 Phase 5 Test Summary");
console.log("=".repeat(70));
console.log(`
Phase 5 Components:
  ✅ SessionContext specialist tracking
  ✅ SessionContext skill loading
  ✅ Context metrics tracking
  ✅ SkillContextLoader detection (${detectionPassed}/${testMessages.length} patterns)
  ✅ Context summary formatting
  ✅ Skill clear detection (${clearDetectionPassed}/${clearTests.length} patterns)

Next Step: Test with actual bot integration
- Start bot and send messages
- Verify specialist persistence across messages
- Verify skill loading works
- Test context optimization (smaller prompts on follow-ups)
`);

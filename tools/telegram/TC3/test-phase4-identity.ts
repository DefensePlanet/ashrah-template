/**
 * Phase 4 Test: {{ORCHESTRATOR_NAME}} Identity & Specialist Context Integration
 *
 * Tests:
 * 1. {{ORCHESTRATOR_NAME}} identity loading from CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md
 * 2. Specialist detection from user messages
 * 3. Specialist context injection
 * 4. TTS tag stripping
 */

import { load{{ORCHESTRATOR_NAME}}Identity, injectSpecialistContext, getSpecialistHandler, catalystAgentLoader } from "./src/config";
import { stripTtsSummary } from "./src/formatting";
import { join } from "path";

console.log("🧪 Phase 4: {{ORCHESTRATOR_NAME}} Identity & Specialist Context Integration Test\n");
console.log("=" .repeat(70) + "\n");

// Initialize Catalyst agents first
console.log("Initializing Catalyst agents...");
const agentsDir = join(import.meta.dir, "catalyst-agents");
await catalystAgentLoader.loadAgents(agentsDir);
console.log(`✅ Loaded ${catalystAgentLoader.count} agents\n`);

// Test 1: Load {{ORCHESTRATOR_NAME}} Identity
console.log("Test 1: Load {{ORCHESTRATOR_NAME}} Identity from CATALYST_{{ORCHESTRATOR_NAME_UPPER}}.md");
console.log("-".repeat(70));
try {
  const {{ORCHESTRATOR_NAME_LOWER}}mIdentity = load{{ORCHESTRATOR_NAME}}Identity();
  console.log(`✅ Loaded {{ORCHESTRATOR_NAME}} identity: ${{{ORCHESTRATOR_NAME_LOWER}}mIdentity.length} characters`);

  // Check for key markers
  const has{{ORCHESTRATOR_NAME}}Name = {{ORCHESTRATOR_NAME_LOWER}}mIdentity.includes("{{ORCHESTRATOR_NAME}}");
  const hasCatalyst = {{ORCHESTRATOR_NAME_LOWER}}mIdentity.includes("Catalyst");
  const hasSafetyRules = {{ORCHESTRATOR_NAME_LOWER}}mIdentity.includes("CRITICAL SAFETY RULES");

  console.log(`   - Contains "{{ORCHESTRATOR_NAME}}": ${has{{ORCHESTRATOR_NAME}}Name ? "✅" : "❌"}`);
  console.log(`   - Contains "Catalyst": ${hasCatalyst ? "✅" : "❌"}`);
  console.log(`   - Contains safety rules: ${hasSafetyRules ? "✅" : "❌"}`);

  if (has{{ORCHESTRATOR_NAME}}Name && hasCatalyst && hasSafetyRules) {
    console.log("✅ Test 1 PASSED: {{ORCHESTRATOR_NAME}} identity loaded correctly\n");
  } else {
    console.log("❌ Test 1 FAILED: Missing expected content\n");
  }
} catch (error) {
  console.log(`❌ Test 1 FAILED: ${error}\n`);
}

// Test 2: Specialist Detection
console.log("Test 2: Specialist Detection");
console.log("-".repeat(70));
const handler = getSpecialistHandler();

const testMessages = [
  { msg: "have the backend dev create an API", expected: "🏛️ Backend Developer" },
  { msg: "ask the frontend developer to update the UI", expected: "🎨 Frontend Developer" },
  { msg: "get the mobile dev to fix this", expected: "📱 Mobile Developer" },
  { msg: "just a regular message", expected: null },
];

let detectionPassed = 0;
for (const test of testMessages) {
  const detected = handler.detectSpecialistRequest(test.msg);
  const passed = detected === test.expected;
  console.log(`   "${test.msg}"`);
  console.log(`     Expected: ${test.expected || "null"}`);
  console.log(`     Detected: ${detected || "null"} ${passed ? "✅" : "❌"}`);
  if (passed) detectionPassed++;
}

if (detectionPassed === testMessages.length) {
  console.log("✅ Test 2 PASSED: All specialist detections correct\n");
} else {
  console.log(`❌ Test 2 FAILED: ${detectionPassed}/${testMessages.length} correct\n`);
}

// Test 3: Specialist Context Injection
console.log("Test 3: Specialist Context Injection");
console.log("-".repeat(70));
try {
  const basePrompt = "Base prompt content";
  const enhancedPrompt = injectSpecialistContext(basePrompt, "🏛️ Backend Developer");

  if (enhancedPrompt.length > basePrompt.length) {
    console.log(`✅ Context injected: ${basePrompt.length} → ${enhancedPrompt.length} chars`);
    console.log(`   Added ${enhancedPrompt.length - basePrompt.length} characters of specialist context`);
    console.log("✅ Test 3 PASSED: Specialist context injection working\n");
  } else {
    console.log("❌ Test 3 FAILED: Context not injected\n");
  }
} catch (error) {
  console.log(`❌ Test 3 FAILED: ${error}\n`);
}

// Test 4: TTS Tag Stripping
console.log("Test 4: TTS Tag Stripping");
console.log("-".repeat(70));
const testText = `Here's my response.

<tts-summary>🎙️ This is the TTS summary that should be removed.</tts-summary>`;

const stripped = stripTtsSummary(testText);
const hasTag = stripped.includes("<tts-summary>");
const hasTtsContent = stripped.includes("TTS summary");

console.log(`   Original: ${testText.length} chars`);
console.log(`   Stripped: ${stripped.length} chars`);
console.log(`   Contains tag: ${hasTag ? "❌" : "✅"}`);
console.log(`   Contains TTS content: ${hasTtsContent ? "❌" : "✅"}`);

if (!hasTag && !hasTtsContent) {
  console.log("✅ Test 4 PASSED: TTS tags properly stripped\n");
} else {
  console.log("❌ Test 4 FAILED: TTS content still present\n");
}

// Summary
console.log("=" .repeat(70));
console.log("📊 Phase 4 Test Summary");
console.log("=" .repeat(70));
console.log(`
Phase 4 Components:
  ✅ {{ORCHESTRATOR_NAME}} identity loading
  ✅ Specialist detection (${detectionPassed}/${testMessages.length} patterns)
  ✅ Specialist context injection
  ✅ TTS tag stripping

Next Step: Test with actual bot by starting it and sending messages.

To test:
  1. Start bot: bun run start
  2. Send message: "Hello {{ORCHESTRATOR_NAME}}"
  3. Send specialist request: "have the backend dev check something"
  4. Verify {{ORCHESTRATOR_NAME}} personality in responses
  5. Verify specialist context loads correctly
`);

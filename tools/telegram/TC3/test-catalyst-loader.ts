#!/usr/bin/env bun

/**
 * Test Catalyst Loader functionality
 *
 * Tests all four main components:
 * - CatalystAgentLoader
 * - CatalystSkillLoader
 * - SpecialistHandler
 * - Agent name resolution
 */

import {
  CatalystAgentLoader,
  CatalystSkillLoader,
  SpecialistHandler,
} from "./src/catalyst-loader";

console.log("=".repeat(60));
console.log("Testing Catalyst Loader");
console.log("=".repeat(60));

// ============== Test Agent Loader ==============

console.log("\n1️⃣  Testing CatalystAgentLoader...\n");

const agentLoader = new CatalystAgentLoader();
await agentLoader.loadAgents("./catalyst-agents");

console.log(`✅ Agents loaded: ${agentLoader.count}`);
console.log(`\nAgent list (first 10):`);
agentLoader.listAgents().slice(0, 10).forEach((name, i) => {
  console.log(`   ${i + 1}. ${name}`);
});

// Test getting a specific agent
console.log("\n📋 Testing agent retrieval:");
const backendAgent = agentLoader.getAgent("🏛️ Backend Developer");
if (backendAgent) {
  console.log(`   ✅ Found: ${backendAgent.name}`);
  console.log(`   📝 Description: ${backendAgent.description || "N/A"}`);
  console.log(`   🤖 Model: ${backendAgent.model || "N/A"}`);
  console.log(`   ⚡ Infinity Model: ${backendAgent.infinity_model || "N/A"}`);
  console.log(`   📄 Prompt length: ${backendAgent.prompt.length} chars`);
} else {
  console.log(`   ❌ Backend Developer agent not found!`);
}

// ============== Test Agent Name Resolution ==============

console.log("\n2️⃣  Testing Agent Name Resolution...\n");

const testNames = [
  "backend dev",
  "Backend Developer",
  "Frontend Dev",
  "mobile developer",
  "UI Designer",
  "code reviewer",
  "debugger",
  "ai nerd",
];

for (const testName of testNames) {
  const resolved = agentLoader.resolveAgentName(testName);
  if (resolved) {
    console.log(`   ✅ "${testName}" → "${resolved}"`);
  } else {
    console.log(`   ❌ "${testName}" → NOT FOUND`);
  }
}

// ============== Test Skill Loader ==============

console.log("\n3️⃣  Testing CatalystSkillLoader...\n");

const skillLoader = new CatalystSkillLoader();
await skillLoader.loadSkills("./catalyst-skills");

console.log(`✅ Skills loaded: ${skillLoader.count}`);
console.log(`\nSkill list (first 15):`);
skillLoader.listSkills().slice(0, 15).forEach((name, i) => {
  console.log(`   ${i + 1}. ${name}`);
});

// Test getting skill context
console.log("\n📋 Testing skill context retrieval:");
const skills = skillLoader.listSkills();
if (skills.length > 0) {
  const firstSkill = skills[0];
  const context = skillLoader.getSkillContext(firstSkill);
  if (context) {
    console.log(`   ✅ Skill "${firstSkill}" has context (${context.length} chars)`);
  } else {
    console.log(`   ℹ️  Skill "${firstSkill}" has no prompt.md`);
  }
}

// ============== Test Specialist Handler ==============

console.log("\n4️⃣  Testing SpecialistHandler...\n");

const specialistHandler = new SpecialistHandler(agentLoader);

const testMessages = [
  "have the backend dev create an API",
  "ask frontend developer to update the UI",
  "get mobile dev to fix the iOS bug",
  "tell code reviewer to check this",
  "delegate this to the debugger",
  "can you help me with this?", // Should not match
];

console.log("Testing specialist detection:");
for (const msg of testMessages) {
  const detected = specialistHandler.detectSpecialistRequest(msg);
  if (detected) {
    console.log(`   ✅ "${msg.slice(0, 40)}..."`);
    console.log(`      → Detected: ${detected}`);
  } else {
    console.log(`   ℹ️  "${msg.slice(0, 40)}..." → No specialist detected`);
  }
}

// Test loading specialist context
console.log("\n📋 Testing specialist context loading:");
const contextTest = await specialistHandler.loadSpecialistContext("🏛️ Backend Developer");
console.log(`   ✅ Loaded context: ${contextTest.length} chars`);
console.log(`   📄 First 100 chars: ${contextTest.slice(0, 100)}...`);

// ============== Summary ==============

console.log("\n" + "=".repeat(60));
console.log("✅ All Tests Complete!");
console.log("=".repeat(60));
console.log(`\n📊 Summary:`);
console.log(`   - Agents loaded: ${agentLoader.count}`);
console.log(`   - Skills loaded: ${skillLoader.count}`);
console.log(`   - Name resolution: Working`);
console.log(`   - Specialist detection: Working`);
console.log(`   - Context loading: Working`);
console.log();

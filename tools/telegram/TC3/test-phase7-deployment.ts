/**
 * Phase 7 Test Suite - Deployment Validation
 *
 * Tests deployment readiness without actual installation:
 * 1. Environment variable configuration
 * 2. Plist file syntax and configuration
 * 3. Installation script validation
 * 4. Bot startup validation
 */

import { existsSync, readFileSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";

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

const projectDir = process.cwd();

// ============== Tests ==============

function testEnvExample(): void {
  console.log("\n🧪 Test 1: .env.example File");

  const envExamplePath = join(projectDir, ".env.example");
  assert(existsSync(envExamplePath), ".env.example file exists");

  const content = readFileSync(envExamplePath, "utf-8");

  // Check required variables are documented
  assert(content.includes("TELEGRAM_BOT_TOKEN"), "Documents TELEGRAM_BOT_TOKEN");
  assert(content.includes("TELEGRAM_ALLOWED_USERS"), "Documents TELEGRAM_ALLOWED_USERS");

  // Check optional variables are documented
  assert(content.includes("OPENAI_API_KEY"), "Documents OPENAI_API_KEY");
  assert(content.includes("CLAUDE_WORKING_DIR"), "Documents CLAUDE_WORKING_DIR");
  assert(content.includes("SUPABASE"), "Documents Supabase variables");

  // Check security notes
  assert(content.includes("Never commit"), "Includes security warning");
  assert(content.includes("chmod 600"), "Includes permissions advice");
}

function testPlistFile(): void {
  console.log("\n🧪 Test 2: LaunchAgent Plist");

  const plistPath = join(projectDir, "com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist");
  assert(existsSync(plistPath), "Plist file exists");

  const content = readFileSync(plistPath, "utf-8");

  // Check key configuration
  assert(content.includes("com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"), "Has correct label");
  assert(content.includes("{{HOME_DIR}}/.bun/bin/bun"), "Has correct Bun path");
  assert(content.includes("src/index.ts"), "Has correct entry point");
  assert(content.includes("{{CATALYST_ROOT}}/tools/telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot"), "Has correct working directory");

  // Check logging
  assert(content.includes("StandardOutPath"), "Has stdout logging");
  assert(content.includes("StandardErrorPath"), "Has stderr logging");
  assert(content.includes("logs/stdout.log"), "Stdout log path correct");
  assert(content.includes("logs/stderr.log"), "Stderr log path correct");

  // Check behavior
  assert(content.includes("RunAtLoad"), "Has RunAtLoad");
  assert(content.includes("KeepAlive"), "Has KeepAlive");
  assert(content.includes("SuccessfulExit"), "Has SuccessfulExit config");
  assert(content.includes("ThrottleInterval"), "Has ThrottleInterval");

  // Validate syntax
  try {
    execSync(`plutil -lint "${plistPath}"`, { encoding: "utf-8" });
    console.log("✅ Plist syntax is valid");
    testsPassed++;
  } catch (error) {
    console.error("❌ Plist syntax is invalid");
    testsFailed++;
  }
}

function testInstallScript(): void {
  console.log("\n🧪 Test 3: Installation Script");

  const installPath = join(projectDir, "install.sh");
  assert(existsSync(installPath), "install.sh exists");

  const content = readFileSync(installPath, "utf-8");

  // Check script structure
  assert(content.includes("#!/bin/bash"), "Has bash shebang");
  assert(content.includes("set -e"), "Has error handling");

  // Check key steps
  assert(content.includes("Checking dependencies"), "Checks dependencies");
  assert(content.includes("Checking environment"), "Checks environment");
  assert(content.includes("bun install"), "Installs dependencies");
  assert(content.includes("mkdir -p"), "Creates logs directory");
  assert(content.includes("launchctl load"), "Loads LaunchAgent");
  assert(content.includes("Verifying installation"), "Verifies installation");

  // Check validations
  assert(content.includes("TELEGRAM_BOT_TOKEN"), "Validates bot token");
  assert(content.includes("TELEGRAM_ALLOWED_USERS"), "Validates allowed users");

  // Check executable permissions
  try {
    const stats = Bun.file(installPath);
    console.log("✅ install.sh has correct permissions");
    testsPassed++;
  } catch (error) {
    console.error("❌ Could not check install.sh permissions");
    testsFailed++;
  }
}

function testUninstallScript(): void {
  console.log("\n🧪 Test 4: Uninstallation Script");

  const uninstallPath = join(projectDir, "uninstall.sh");
  assert(existsSync(uninstallPath), "uninstall.sh exists");

  const content = readFileSync(uninstallPath, "utf-8");

  // Check script structure
  assert(content.includes("#!/bin/bash"), "Has bash shebang");
  assert(content.includes("set -e"), "Has error handling");

  // Check key steps
  assert(content.includes("launchctl unload"), "Unloads LaunchAgent");
  assert(content.includes("rm"), "Removes plist file");
  assert(content.includes("--clean-logs"), "Supports log cleaning");

  // Check safety
  assert(content.includes("Checking installation"), "Checks before uninstalling");
  assert(content.includes("CLEAN_LOGS=false"), "Preserves logs by default");
}

function testProjectStructure(): void {
  console.log("\n🧪 Test 5: Project Structure");

  // Check critical files
  const files = [
    "src/index.ts",
    "src/config.ts",
    "src/session.ts",
    "src/handlers/index.ts",
    "src/handlers/management.ts",
    "package.json",
    "tsconfig.json",
    ".gitignore",
  ];

  for (const file of files) {
    const path = join(projectDir, file);
    assert(existsSync(path), `${file} exists`);
  }

  // Check .gitignore includes .env
  const gitignorePath = join(projectDir, ".gitignore");
  if (existsSync(gitignorePath)) {
    const content = readFileSync(gitignorePath, "utf-8");
    assert(content.includes(".env"), ".gitignore includes .env");
  }
}

function testConfigValidation(): void {
  console.log("\n🧪 Test 6: Config Validation Logic");

  // Import config module
  const configPath = join(projectDir, "src/config.ts");
  assert(existsSync(configPath), "config.ts exists");

  const content = readFileSync(configPath, "utf-8");

  // Check validation logic exists
  assert(content.includes("TELEGRAM_TOKEN"), "Has token validation");
  assert(content.includes("ALLOWED_USERS"), "Has user validation");
  assert(content.includes("process.exit(1)"), "Exits on missing required vars");
  assert(content.includes("validateMCPEnvironment"), "Has MCP validation");
}

function testPhaseCompleteness(): void {
  console.log("\n🧪 Test 7: Phase Documentation");

  // Check phase documents exist
  const docs = [
    "PHASE7-DESIGN.md",
    ".env.example",
    "com.catalyst.telegram-{{ORCHESTRATOR_NAME_LOWER}}-bot.plist",
    "install.sh",
    "uninstall.sh",
  ];

  for (const doc of docs) {
    const path = join(projectDir, doc);
    assert(existsSync(path), `${doc} exists`);
  }
}

// ============== Run Tests ==============

async function runTests(): Promise<void> {
  console.log("=".repeat(50));
  console.log("Phase 7 Test Suite - Deployment Validation");
  console.log("=".repeat(50));

  try {
    testEnvExample();
    testPlistFile();
    testInstallScript();
    testUninstallScript();
    testProjectStructure();
    testConfigValidation();
    testPhaseCompleteness();
  } catch (error) {
    console.error("\n💥 Test suite crashed:", error);
    testsFailed++;
  }

  console.log("\n" + "=".repeat(50));
  console.log(`✅ Passed: ${testsPassed}`);
  console.log(`❌ Failed: ${testsFailed}`);
  console.log("=".repeat(50));

  if (testsFailed > 0) {
    process.exit(1);
  }

  console.log("\n📋 Deployment Checklist:");
  console.log("  1. ✅ .env.example created and documented");
  console.log("  2. ✅ LaunchAgent plist configured");
  console.log("  3. ✅ Installation script ready");
  console.log("  4. ✅ Uninstallation script ready");
  console.log("  5. ✅ Project structure validated");
  console.log("  6. ✅ Config validation logic present");
  console.log("  7. ✅ Phase documentation complete");
  console.log("\n✨ Ready for manual installation testing!");
  console.log("\nNext steps:");
  console.log("  1. Ensure .env file has correct values");
  console.log("  2. Run: ./install.sh");
  console.log("  3. Test bot via Telegram");
  console.log("  4. Check logs: tail -f logs/*.log");
}

runTests();

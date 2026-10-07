/**
 * Test MCP Integration
 *
 * Validates that all MCP servers are properly configured and environment is set up.
 */

import { getMCPServers, validateMCPEnvironment } from "./src/config";
import { MCP_SERVERS, getMCPServerCount, getMCPServerNames } from "./mcp-config";

console.log("🧪 Testing MCP Integration\n");
console.log("=" .repeat(80));

// ============== Test 1: Environment Validation ==============

console.log("\n📋 Test 1: Environment Validation\n");

try {
  validateMCPEnvironment();
  console.log("✅ Environment validation passed");
} catch (err) {
  console.error("❌ Environment validation failed:", err);
  process.exit(1);
}

// ============== Test 2: MCP Configuration Loading ==============

console.log("\n📋 Test 2: MCP Configuration Loading\n");

const mcpServers = getMCPServers();
const mcpCount = getMCPServerCount();
const mcpNames = getMCPServerNames();

console.log(`✅ Loaded ${mcpCount} MCP servers from mcp-config.ts`);
console.log(`✅ Config export function returns ${Object.keys(mcpServers).length} servers`);

if (mcpCount !== Object.keys(mcpServers).length) {
  console.error("❌ Server count mismatch!");
  process.exit(1);
}

// ============== Test 3: List All Configured MCPs ==============

console.log("\n📋 Test 3: Configured MCP Servers\n");

const categories = {
  "Core Tools": ["filesystem"],
  "Memory & Learning": ["builder-memory", "agent-memory"],
  "Documentation": ["context7"],
  "Collaboration": ["bridge-mcp"],
  "Apple Ecosystem": ["applescript", "siri-shortcuts", "apple-doc-mcp"],
  "Development": ["xcodebuildmcp"],
  "Browser": ["playwright"],
  "Database": ["supabase-toolkit"],
  "Automation": ["n8n-mcp"],
  "Git": ["git-mcp"],
  "UI Documentation": ["react-spring-mcp", "shadcn-ui"],
  "Video Production": ["obs"],
  "Terminal": ["iterm-mcp"],
  "Interactive": ["ask-user"],
};

for (const [category, servers] of Object.entries(categories)) {
  console.log(`\n${category}:`);
  for (const name of servers) {
    const config = mcpServers[name];
    if (config) {
      console.log(`  ✅ ${name}`);
      console.log(`     Command: ${config.command}`);
      console.log(`     Args: ${config.args?.slice(0, 2).join(" ")}${config.args && config.args.length > 2 ? "..." : ""}`);
      if (config.env && Object.keys(config.env).length > 0) {
        console.log(`     Env vars: ${Object.keys(config.env).join(", ")}`);
      }
    } else {
      console.log(`  ❌ ${name} - NOT CONFIGURED`);
    }
  }
}

// ============== Test 4: Environment Variable Coverage ==============

console.log("\n📋 Test 4: Environment Variable Coverage\n");

const requiredEnvVars = [
  { key: "OPENAI_API_KEY", purpose: "Voice transcription" },
];

const optionalEnvVars = [
  { key: "CONTEXT7_API_KEY", purpose: "Context7 documentation" },
  { key: "SUPABASE_URL", purpose: "Supabase database" },
  { key: "SUPABASE_SERVICE_ROLE_KEY", purpose: "Supabase admin" },
  { key: "SUPABASE_PROJECT_REF", purpose: "Supabase project ID" },
  { key: "N8N_API_URL", purpose: "n8n automation" },
  { key: "N8N_API_KEY", purpose: "n8n API key" },
  { key: "OBS_WEBSOCKET_URL", purpose: "OBS Studio" },
  { key: "OBS_WEBSOCKET_PASSWORD", purpose: "OBS auth" },
];

console.log("Required environment variables:");
let allRequiredPresent = true;
for (const { key, purpose } of requiredEnvVars) {
  const present = !!process.env[key];
  console.log(`  ${present ? "✅" : "❌"} ${key} (${purpose})`);
  if (!present) allRequiredPresent = false;
}

console.log("\nOptional environment variables:");
let optionalCount = 0;
for (const { key, purpose } of optionalEnvVars) {
  const present = !!process.env[key];
  console.log(`  ${present ? "✅" : "⚠️ "} ${key} (${purpose})`);
  if (present) optionalCount++;
}

console.log(`\n${optionalCount}/${optionalEnvVars.length} optional env vars configured`);

if (!allRequiredPresent) {
  console.error("\n❌ Missing required environment variables");
  process.exit(1);
}

// ============== Test 5: Path Validation ==============

console.log("\n📋 Test 5: Critical Path Validation\n");

import { existsSync } from "fs";

const criticalPaths = [
  { path: "{{CATALYST_ROOT}}", purpose: "Catalyst root" },
  { path: "{{HOME_DIR}}/Development/context7/dist/index.js", purpose: "Context7 MCP" },
  { path: "{{CATALYST_ROOT}}/global/apple-doc-mcp", purpose: "Apple Docs MCP" },
  { path: "{{CATALYST_ROOT}}/global/xcodebuildmcp", purpose: "XcodeBuild MCP" },
  { path: "/opt/homebrew/bin/node", purpose: "Node.js binary" },
  { path: "/opt/homebrew/bin/npx", purpose: "npx (for installing MCPs)" },
];

let allPathsExist = true;
for (const { path, purpose } of criticalPaths) {
  const exists = existsSync(path);
  console.log(`  ${exists ? "✅" : "❌"} ${path}`);
  console.log(`     Purpose: ${purpose}`);
  if (!exists) {
    allPathsExist = false;
    console.log(`     ⚠️  This MCP may not work without this path`);
  }
}

if (!allPathsExist) {
  console.warn("\n⚠️  Some critical paths are missing - some MCPs may not work");
}

// ============== Summary ==============

console.log("\n" + "=".repeat(80));
console.log("\n✅ MCP Integration Test Complete\n");
console.log(`Summary:`);
console.log(`  - ${mcpCount} MCP servers configured`);
console.log(`  - ${requiredEnvVars.length} required env vars present`);
console.log(`  - ${optionalCount}/${optionalEnvVars.length} optional env vars configured`);
console.log(`  - ${criticalPaths.filter(p => existsSync(p.path)).length}/${criticalPaths.length} critical paths exist`);
console.log(`\n✅ Ready for Phase 3 completion\n`);

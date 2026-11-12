/**
 * Claude Telegram Bot - TypeScript/Bun Edition
 *
 * Multi-capsule architecture: one bot serves multiple Telegram chats,
 * each scoped to a different capsule working directory.
 */

import { Bot } from "grammy";
import { run, sequentialize } from "@grammyjs/runner";
import dns from "node:dns";

// Bun can prefer IPv6 on some networks; Telegram Bot API IPv6 can be unreachable.
// Force IPv4-first resolution for long-polling stability.
dns.setDefaultResultOrder("ipv4first");
import {
  TELEGRAM_TOKEN,
  WORKING_DIR,
  ALLOWED_USERS,
  RESTART_FILE,
  initializeCatalyst,
} from "./config";
import { getCachedOAuthCredentials, isExpired } from "./oauth-credentials";
import { unlinkSync, readFileSync, existsSync } from "fs";
import { capsuleMiddleware, type CapsuleContext } from "./middleware/capsule";
import { bridgeMiddleware } from "./middleware/bridge";
import { setBridgeSelfUsername } from "./config/bridge-registry";
import {
  handleStart,
  handleNew,
  handleStop,
  handleStatus,
  handleResume,
  handleRestart,
  handleRetry,
  handleFast,
  handleCli,
  handleCapsule,
  handleText,
  handleVoice,
  handleVideo,
  handleAudio,
  handlePhoto,
  handleDocument,
  handleCallback,
} from "./handlers";
import {
  handleSyncCommand,
  handleContextCommand,
  handleSpecialistCommand,
  handleSkillsCommand,
} from "./handlers/management";
import { getCatalystWatcher } from "./config";

// Create bot instance
const bot = new Bot(TELEGRAM_TOKEN);

// Register capsule middleware FIRST — attaches per-chat session to context
bot.use(capsuleMiddleware());

// Register bridge middleware — intercepts bot-to-bot messages, attaches bridgeMessage
bot.use(bridgeMiddleware());

// Sequentialize non-command messages per user (prevents race conditions)
// Commands bypass sequentialization so they work immediately
bot.use(
  sequentialize((ctx) => {
    // Commands are not sequentialized - they work immediately
    if (ctx.message?.text?.startsWith("/")) {
      return undefined;
    }
    // Messages with ! prefix bypass queue (interrupt)
    if (ctx.message?.text?.startsWith("!")) {
      return undefined;
    }
    // Callback queries (button clicks) are not sequentialized
    if (ctx.callbackQuery) {
      return undefined;
    }
    // Other messages are sequentialized per chat
    return ctx.chat?.id.toString();
  })
);

// ============== Command Handlers ==============

// Session commands
bot.command("start", handleStart);
bot.command("new", handleNew);
bot.command("stop", handleStop);
bot.command("status", handleStatus);
bot.command("fast", handleFast);
bot.command("cli", handleCli);
bot.command("resume", handleResume);
bot.command("restart", handleRestart);
bot.command("retry", handleRetry);

// Capsule management
bot.command("capsule", handleCapsule);

// Management commands (Phase 6)
bot.command("sync", async (ctx) => {
  const watcher = getCatalystWatcher();
  await handleSyncCommand(ctx, watcher);
});

bot.command("context", async (ctx) => {
  const chatSession = (ctx as CapsuleContext).chatSession;
  await handleContextCommand(ctx, chatSession?.session as any);
});

bot.command("specialist", async (ctx) => {
  const chatSession = (ctx as CapsuleContext).chatSession;
  await handleSpecialistCommand(ctx, chatSession?.session as any);
});

bot.command("skills", async (ctx) => {
  const chatSession = (ctx as CapsuleContext).chatSession;
  await handleSkillsCommand(ctx, chatSession?.session as any);
});

// ============== Message Handlers ==============

// Text messages
bot.on("message:text", handleText);

// Voice messages
bot.on("message:voice", handleVoice);

// Video messages
bot.on("message:video", handleVideo);
bot.on("message:video_note", handleVideo);

// Audio files
bot.on("message:audio", handleAudio);

// Photo messages
bot.on("message:photo", handlePhoto);

// Document messages (also routes audio-as-document internally)
bot.on("message:document", handleDocument);

// ============== Callback Queries ==============

bot.on("callback_query:data", handleCallback);

// ============== Error Handler ==============

bot.catch((err) => {
  console.error("Bot error:", err);
  // Attempt to notify the user so errors aren't silent
  const ctx = err.ctx;
  if (ctx?.chat?.id) {
    ctx.reply("⚠️ An error occurred. Check bot logs for details.").catch(() => {});
  }
});

// ============== Startup ==============

console.log("=".repeat(50));
console.log("Claude Telegram Bot - Multi-Capsule Edition");
console.log("=".repeat(50));
console.log(`Default capsule: ${WORKING_DIR}`);
console.log(`Allowed users: ${ALLOWED_USERS.length}`);
console.log("Starting bot...");

// Get bot info first
const botInfo = await bot.api.getMe();
console.log(`Bot started: @${botInfo.username}`);

// Set bridge self-username for envelope creation
setBridgeSelfUsername(`@${botInfo.username}`);

// Initialize Catalyst integration
await initializeCatalyst();

// ============== Set Bot Menu Commands ==============
// Register commands for all scopes so the menu appears in private chats AND groups.
const BOT_COMMANDS = [
  { command: "start", description: "Show welcome message and help" },
  { command: "new", description: "Start a fresh session" },
  { command: "stop", description: "Stop current query" },
  { command: "status", description: "Show detailed bot status" },
  { command: "fast", description: "Switch to Fast (PI) mode" },
  { command: "cli", description: "Switch to CLI mode" },
  { command: "resume", description: "Resume a saved session" },
  { command: "retry", description: "Retry the last message" },
  { command: "restart", description: "Restart the bot process" },
  { command: "capsule", description: "Manage capsule bindings" },
  { command: "sync", description: "Reload agents and skills" },
  { command: "context", description: "View session context" },
  { command: "specialist", description: "Manage active specialist" },
  { command: "skills", description: "Manage loaded skills" },
];

try {
  await Promise.all([
    bot.api.setMyCommands(BOT_COMMANDS),
    bot.api.setMyCommands(BOT_COMMANDS, {
      scope: { type: "all_group_chats" },
    }),
    bot.api.setMyCommands(BOT_COMMANDS, {
      scope: { type: "all_chat_administrators" },
    }),
  ]);
  console.log(`Bot menu set: ${BOT_COMMANDS.length} commands (default + groups + admins)`);
} catch (err) {
  console.warn("Failed to set bot commands:", err);
}

// ============== OAuth Health Check ==============
// Quick read-only check of OAuth credentials at startup.
// We never refresh tokens ourselves — Claude Code handles that.
console.log("\nChecking OAuth credentials...");
const oauthCreds = getCachedOAuthCredentials();
if (oauthCreds && !isExpired(oauthCreds)) {
  const expiresInMin = Math.round((oauthCreds.expiresAt - Date.now()) / 60000);
  console.log(`[OAuth] Token valid (expires in ~${expiresInMin} min). PI mode ready.`);
} else if (oauthCreds) {
  console.warn("[OAuth] WARNING: Token expired. Run 'claude' to refresh. CLI fallback available.");
} else {
  console.warn("[OAuth] WARNING: No credentials found. PI mode will fail; CLI fallback available.");
}

// Check for pending restart message to update
if (existsSync(RESTART_FILE)) {
  try {
    const data = JSON.parse(readFileSync(RESTART_FILE, "utf-8"));
    const age = Date.now() - data.timestamp;

    // Only update if restart was recent (within 30 seconds)
    if (age < 30000 && data.chat_id && data.message_id) {
      await bot.api.editMessageText(
        data.chat_id,
        data.message_id,
        "✅ Bot restarted"
      );
    }
    unlinkSync(RESTART_FILE);
  } catch (e) {
    console.warn("Failed to update restart message:", e);
    try { unlinkSync(RESTART_FILE); } catch {}
  }
}

// Start with concurrent runner (commands work immediately)
// Explicitly set allowed_updates to include "message" — required for receiving
// bot-to-bot messages in groups (Telegram uses stale settings if not specified)
const runner = run(bot, {
  source: {
    // Retry on network errors with exponential backoff (default)
    // Allow up to 15 hours of retrying before giving up
    retryInterval: "exponential",
    maxRetryTime: 15 * 60 * 60 * 1000,
  },
  runner: {
    fetch: {
      allowed_updates: [
        "message",
        "edited_message",
        "callback_query",
        "channel_post",
        "my_chat_member",
        "chat_member",
      ],
    },
  },
});

// Monitor the runner task — if it crashes, exit non-zero so KeepAlive restarts us
const task = runner.task();
if (task) {
  task.then(() => {
    console.log("[Runner] Stopped cleanly");
  }).catch((err) => {
    console.error("[Runner] Crashed:", err.message ?? err);
    console.log("[Runner] Exiting non-zero for KeepAlive restart...");
    process.exit(1);
  });
}

console.log("[Runner] started (long polling)");

// Graceful shutdown
const stopRunner = () => {
  if (runner.isRunning()) {
    console.log("Stopping bot...");
    runner.stop();
  }
};

process.on("SIGINT", () => {
  console.log("Received SIGINT");
  stopRunner();
  process.exit(0);
});

process.on("SIGTERM", () => {
  console.log("Received SIGTERM");
  stopRunner();
  process.exit(0);
});

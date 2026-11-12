/**
 * Command handlers for Claude Telegram Bot.
 *
 * /start, /new, /stop, /status, /resume, /restart, /fast, /cli, /capsule
 */

import type { Context } from "grammy";
import type { CapsuleContext } from "../middleware/capsule";
import type { SessionMode } from "../types";
import { switchMode, getCurrentMode, cleanupSession } from "../session-wrapper";
import { ALLOWED_USERS, RESTART_FILE } from "../config";
import {
  getCapsuleConfig,
  bindCapsule,
  unbindCapsule,
  listCapsules,
} from "../config/capsule-loader";
import { isAuthorized, isPathAllowed } from "../security";
import { existsSync } from "fs";

/**
 * /start - Show welcome message and status.
 */
export async function handleStart(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized. Contact the bot owner for access.");
    return;
  }

  const chatSession = (ctx as CapsuleContext).chatSession;
  const session = chatSession?.session;
  const status = session?.isActive ? "Active session" : "No active session";
  const workDir = chatSession?.workingDir || "unknown";
  const capsuleName = chatSession?.capsuleName || "unknown";

  await ctx.reply(
    `\ud83e\udd16 <b>Claude Telegram Bot</b>\n\n` +
      `Status: ${status}\n` +
      `Capsule: <b>${capsuleName}</b>\n` +
      `Working directory: <code>${workDir}</code>\n\n` +
      `<b>Session Commands:</b>\n` +
      `/new - Start fresh session\n` +
      `/stop - Stop current query\n` +
      `/status - Show detailed status\n` +
      `/fast - ⚡️ Fast mode (PI)\n` +
      `/cli - 🔧 CLI mode (full Catalyst)\n` +
      `/resume - Resume last session\n` +
      `/retry - Retry last message\n` +
      `/restart - Restart the bot\n\n` +
      `<b>Capsule Commands:</b>\n` +
      `/capsule - Show current capsule\n` +
      `/capsule list - List all capsules\n` +
      `/capsule bind - Bind chat to capsule\n` +
      `/capsule unbind - Reset to default\n\n` +
      `<b>Context Management:</b>\n` +
      `/context - View session context\n` +
      `/specialist - Manage active specialist\n` +
      `/skills - Manage loaded skills\n` +
      `/sync - Sync Catalyst resources\n\n` +
      `<b>Tips:</b>\n` +
      `\u2022 Prefix with <code>!</code> to interrupt current query\n` +
      `\u2022 Use "think" keyword for extended reasoning\n` +
      `\u2022 Send photos, voice, or documents`,
    { parse_mode: "HTML" }
  );
}

/**
 * /new - Start a fresh session.
 */
export async function handleNew(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  const { session } = (ctx as CapsuleContext).chatSession;

  // Stop any running query
  if (session.isRunning) {
    const result = await session.stop();
    if (result) {
      await Bun.sleep(100);
      session.clearStopRequested();
    }
  }

  // Clear session
  await session.kill();

  await ctx.reply("\ud83c\udd95 Session cleared. Next message starts fresh.");
}

/**
 * /stop - Stop the current query.
 *
 * NOTE: This must be user-visible; silent stops read like the command was ignored.
 */
export async function handleStop(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  const { session } = (ctx as CapsuleContext).chatSession;

  if (!session.isRunning) {
    await ctx.reply("⛔️ Nothing running.");
    return;
  }

  const result = await session.stop();

  // Acknowledge immediately so {{USER_NAME}} knows the bot heard it.
  if (result) {
    await ctx.reply("🛑 Stopping…");
    // Wait for the abort to be processed, then clear stopRequested so next message can proceed
    await Bun.sleep(150);
    session.clearStopRequested();
    return;
  }

  // Fallback (shouldn't happen): session said it wasn't running or couldn't stop.
  await ctx.reply("⛔️ Couldn’t stop (no active query?).");
}

/**
 * /status - Show detailed status.
 */
export async function handleStatus(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const chatId = ctx.chat?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  const chatSession = (ctx as CapsuleContext).chatSession;
  const session = chatSession?.session;
  const lines: string[] = ["\ud83d\udcca <b>Bot Status</b>\n"];

  // Capsule
  lines.push(`\ud83d\udce6 Capsule: <b>${chatSession?.capsuleName || "unknown"}</b>`);

  // Mode
  const mode = chatId ? getCurrentMode(chatId) : "pi";
  const modeLabel = mode === "pi" ? "⚡️ Fast" : "🔧 CLI";
  lines.push(`\ud83d\udd0c Mode: ${modeLabel}`);

  // Session status
  if (session?.isActive) {
    lines.push(`\u2705 Session: Active (${session.sessionId?.slice(0, 8)}...)`);
  } else {
    lines.push("\u26aa Session: None");
  }

  // Query status
  if (session?.isRunning) {
    const elapsed = session.queryStarted
      ? Math.floor((Date.now() - session.queryStarted.getTime()) / 1000)
      : 0;
    lines.push(`\ud83d\udd04 Query: Running (${elapsed}s)`);
    if (session.currentTool) {
      lines.push(`   \u2514\u2500 ${session.currentTool}`);
    }
  } else {
    lines.push("\u26aa Query: Idle");
    if (session?.lastTool) {
      lines.push(`   \u2514\u2500 Last: ${session.lastTool}`);
    }
  }

  // Last activity
  if (session?.lastActivity) {
    const ago = Math.floor(
      (Date.now() - session.lastActivity.getTime()) / 1000
    );
    lines.push(`\n\u23f1\ufe0f Last activity: ${ago}s ago`);
  }

  // Usage stats
  if (session?.lastUsage) {
    const usage = session.lastUsage;
    lines.push(
      `\n\ud83d\udcc8 Last query usage:`,
      `   Input: ${usage.input_tokens?.toLocaleString() || "?"} tokens`,
      `   Output: ${usage.output_tokens?.toLocaleString() || "?"} tokens`
    );
    if (usage.cache_read_input_tokens) {
      lines.push(
        `   Cache read: ${usage.cache_read_input_tokens.toLocaleString()}`
      );
    }
  }

  // Error status
  if (session?.lastError) {
    const ago = session.lastErrorTime
      ? Math.floor((Date.now() - session.lastErrorTime.getTime()) / 1000)
      : "?";
    lines.push(`\n\u26a0\ufe0f Last error (${ago}s ago):`, `   ${session.lastError}`);
  }

  // Working directory
  lines.push(`\n\ud83d\udcc1 Working dir: <code>${chatSession?.workingDir || "unknown"}</code>`);

  await ctx.reply(lines.join("\n"), { parse_mode: "HTML" });
}

/**
 * /resume - Show list of sessions to resume with inline keyboard.
 */
export async function handleResume(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  const { session } = (ctx as CapsuleContext).chatSession;

  if (session.isActive) {
    await ctx.reply("Sessione gi\u00e0 attiva. Usa /new per iniziare da capo.");
    return;
  }

  // getSessionList only exists on ClaudeSession (CLI mode)
  if (!("getSessionList" in session)) {
    await ctx.reply("\u274c Session resume is only available in CLI mode. Use /cli first.");
    return;
  }

  // Get saved sessions
  const sessions = (session as any).getSessionList();

  if (sessions.length === 0) {
    await ctx.reply("\u274c Nessuna sessione salvata.");
    return;
  }

  // Build inline keyboard with session list
  const buttons = sessions.map((s: any) => {
    // Format date: "18/01 10:30"
    const date = new Date(s.saved_at);
    const dateStr = date.toLocaleDateString("it-IT", {
      day: "2-digit",
      month: "2-digit",
    });
    const timeStr = date.toLocaleTimeString("it-IT", {
      hour: "2-digit",
      minute: "2-digit",
    });

    // Truncate title for button (max ~40 chars to fit)
    const titlePreview =
      s.title.length > 35 ? s.title.slice(0, 32) + "..." : s.title;

    return [
      {
        text: `\ud83d\udcc5 ${dateStr} ${timeStr} - "${titlePreview}"`,
        callback_data: `resume:${s.session_id}`,
      },
    ];
  });

  await ctx.reply("\ud83d\udccb <b>Sessioni salvate</b>\n\nSeleziona una sessione da riprendere:", {
    parse_mode: "HTML",
    reply_markup: {
      inline_keyboard: buttons,
    },
  });
}

/**
 * /restart - Restart the bot process.
 */
export async function handleRestart(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const chatId = ctx.chat?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  const msg = await ctx.reply("\ud83d\udd04 Restarting bot...");

  // Save message info so we can update it after restart
  if (chatId && msg.message_id) {
    try {
      await Bun.write(
        RESTART_FILE,
        JSON.stringify({
          chat_id: chatId,
          message_id: msg.message_id,
          timestamp: Date.now(),
        })
      );
    } catch (e) {
      console.warn("Failed to save restart info:", e);
    }
  }

  // Give time for the message to send
  await Bun.sleep(500);

  // Exit - launchd will restart us
  process.exit(0);
}

/**
 * /retry - Retry the last message (resume session and re-send).
 */
export async function handleRetry(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  const { session } = (ctx as CapsuleContext).chatSession;

  // Check if there's a message to retry
  if (!session.lastMessage) {
    await ctx.reply("\u274c No message to retry.");
    return;
  }

  // Check if something is already running
  if (session.isRunning) {
    await ctx.reply("\u23f3 A query is already running. Use /stop first.");
    return;
  }

  const message = session.lastMessage;
  await ctx.reply(`\ud83d\udd04 Retrying: "${message.slice(0, 50)}${message.length > 50 ? "..." : ""}"`);

  // Simulate sending the message again by directly calling the text handler logic
  const { handleText } = await import("./text");

  // Create a modified context with the last message
  const fakeCtx = {
    ...ctx,
    message: {
      ...ctx.message,
      text: message,
    },
  } as Context;

  // Ensure chatSession is preserved (capsule middleware attaches it to ctx)
  (fakeCtx as any).chatSession = (ctx as any).chatSession;

  await handleText(fakeCtx);
}

/**
 * /fast - Switch to Fast (PI) mode.
 *
 * ⚡️ Fast Mode • Core tools • On-demand context
 */
export async function handleFast(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const chatId = ctx.chat?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  if (!chatId) return;

  const currentMode = getCurrentMode(chatId);

  if (currentMode === "pi") {
    await ctx.reply("⚡️ Already in Fast mode.");
    return;
  }

  const switching = await ctx.reply("🔄 Switching to Fast mode...");

  try {
    await switchMode(chatId, "pi");
    await ctx.api.editMessageText(
      chatId,
      switching.message_id,
      `⚡️ <b>Fast Mode</b>\nCore tools • On-demand context\n\nSession cleared — next message starts fresh.`,
      { parse_mode: "HTML" }
    );
  } catch (error) {
    console.error("[handleFast] switchMode failed:", error);
    try {
      await ctx.api.editMessageText(
        chatId,
        switching.message_id,
        `❌ Failed to switch: ${String(error).slice(0, 100)}`
      );
    } catch {}
  }
}

/**
 * /cli - Switch to CLI mode.
 *
 * 🔧 CLI Mode • Full Catalyst • All tools • MCPs • Specialists
 */
export async function handleCli(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const chatId = ctx.chat?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  if (!chatId) return;

  const currentMode = getCurrentMode(chatId);

  if (currentMode === "cli") {
    await ctx.reply("🔧 Already in CLI mode.");
    return;
  }

  const switching = await ctx.reply("🔄 Switching to CLI mode...");

  try {
    await switchMode(chatId, "cli");
    await ctx.api.editMessageText(
      chatId,
      switching.message_id,
      `🔧 <b>CLI Mode</b>\nFull Catalyst • All tools • MCPs • Specialists\n\nSession cleared — next message starts fresh.`,
      { parse_mode: "HTML" }
    );
  } catch (error) {
    console.error("[handleCli] switchMode failed:", error);
    try {
      await ctx.api.editMessageText(
        chatId,
        switching.message_id,
        `❌ Failed to switch: ${String(error).slice(0, 100)}`
      );
    } catch {}
  }
}

/**
 * /capsule - View or manage capsule bindings.
 *
 * /capsule           -> Show current capsule
 * /capsule list      -> List all capsules
 * /capsule bind <id> <path> [name] -> Bind this chat to a capsule
 * /capsule unbind    -> Unbind this chat (reset to default)
 */
export async function handleCapsule(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const chatId = ctx.chat?.id;

  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized.");
    return;
  }

  if (!chatId) return;

  const text = ctx.message?.text || "";
  const args = text.split(/\s+/).slice(1);
  const action = args[0]?.toLowerCase();

  // /capsule -- show current binding
  if (!action) {
    const capsule = getCapsuleConfig(chatId);
    const mode = getCurrentMode(chatId);
    await ctx.reply(
      `\ud83d\udce6 <b>Current Capsule</b>\n\n` +
        `Name: ${capsule.name}\n` +
        `Dir: <code>${capsule.workingDir}</code>\n` +
        `Mode: ${mode.toUpperCase()}\n\n` +
        `/capsule list \u2014 Show all capsules\n` +
        `/capsule bind &lt;id&gt; &lt;path&gt; &lt;name&gt; \u2014 Bind this chat\n` +
        `/capsule unbind \u2014 Reset to default`,
      { parse_mode: "HTML" }
    );
    return;
  }

  // /capsule list
  if (action === "list") {
    const capsules = listCapsules();
    if (capsules.length === 0) {
      await ctx.reply("No capsules registered.");
      return;
    }

    const lines = capsules.map((c, i) => {
      const label = i === 0 ? "(default)" : `[${c.capsuleId || "?"}]`;
      return `\u2022 <b>${c.name}</b> ${label}\n  <code>${c.workingDir}</code>\n  Mode: ${c.defaultMode.toUpperCase()}`;
    });

    await ctx.reply(
      `\ud83d\udce6 <b>Registered Capsules</b> (${capsules.length})\n\n${lines.join("\n\n")}`,
      { parse_mode: "HTML" }
    );
    return;
  }

  // /capsule bind <capsuleId> <workingDir> [name...]
  if (action === "bind") {
    const capsuleId = args[1];
    const workingDir = args[2];
    const name = args.slice(3).join(" ") || capsuleId;

    if (!capsuleId || !workingDir) {
      await ctx.reply("Usage: /capsule bind <id> <path> [name]");
      return;
    }

    // Validate path is within allowed directories (prevent traversal attacks)
    if (!isPathAllowed(workingDir)) {
      await ctx.reply(`\u274c Path outside allowed directories: ${workingDir}`);
      return;
    }

    // Validate path exists
    if (!existsSync(workingDir)) {
      await ctx.reply(`\u274c Path does not exist: ${workingDir}`);
      return;
    }

    bindCapsule(chatId, capsuleId, workingDir, name || capsuleId);
    // Clean up existing session for this chat so it picks up new config
    await cleanupSession(chatId);

    await ctx.reply(
      `\u2705 Bound this chat to capsule: <b>${name || capsuleId}</b>\nDir: <code>${workingDir}</code>`,
      { parse_mode: "HTML" }
    );
    return;
  }

  // /capsule unbind
  if (action === "unbind") {
    unbindCapsule(chatId);
    await cleanupSession(chatId);
    await ctx.reply("\u2705 Unbound \u2014 this chat now uses default Catalyst root.");
    return;
  }

  // Unknown subcommand
  await ctx.reply(
    `\u274c Unknown capsule command: <code>${action}</code>\n\nUse /capsule for help.`,
    { parse_mode: "HTML" }
  );
}

/**
 * Text message handler for Claude Telegram Bot.
 *
 * Handles three message flows:
 *   1. Inbound bridge messages (from registered bots via bridge middleware)
 *   2. Outbound delegation (user asks to send a message to another bot)
 *   3. Normal text messages (sent to Claude/PI session)
 */

import type { Context } from "grammy";
import type { CapsuleContext } from "../middleware/capsule";
import { ALLOWED_USERS } from "../config";
import { isAuthorized, rateLimiter } from "../security";
import {
  auditLog,
  auditLogRateLimit,
  checkInterrupt,
  startTypingIndicator,
} from "../utils";
import { StreamingState, createStatusCallback } from "./streaming";
import { sendWithAuthFallback } from "../session-wrapper";
import { sendTtsAudio } from "../services/tts-send";
import {
  createEnvelope,
  formatOutboundMessage,
  createResponseEnvelope,
  serializeEnvelope,
} from "../bridge/envelope";
import {
  loadBridgeConfig,
  findBotByUsername,
} from "../config/bridge-registry";

// ============== Delegation Detection ==============

/**
 * Pattern: "ask @bot to X", "tell @bot X", "delegate to @bot X",
 *          "message @bot X", "send to @bot X", "ping @bot X"
 */
const DELEGATION_RE =
  /^(?:ask|tell|send\s+to|message|delegate\s+to|ping)\s+(@\w+)\s+(?:to\s+|about\s+|that\s+)?(.+)/is;

// ============== Inbound Bridge Handler ==============

/**
 * Handle an inbound bridge message from another bot.
 *
 * Builds an enriched prompt for the PI session and optionally sends
 * a response envelope back to TC3 bots.
 */
async function handleInboundBridge(ctx: Context): Promise<void> {
  const capsuleCtx = ctx as CapsuleContext;
  const bridge = capsuleCtx.bridgeMessage!;
  const chatId = ctx.chat!.id;

  console.log(
    `[Bridge:Inbound] Processing ${bridge.envelope.type} from ${bridge.sourceBot.displayName}`
  );

  // Build enriched message for the PI session
  const headerLines = [
    `[BRIDGE MESSAGE from ${bridge.sourceBot.displayName} (${bridge.sourceBot.username})]`,
  ];

  if (bridge.isResponse) {
    headerLines.push("[This is a RESPONSE to your earlier request]");
  } else if (bridge.envelope.type === "request") {
    headerLines.push("[This is a new REQUEST from another bot]");
  } else {
    headerLines.push("[This is a NOTIFICATION from another bot]");
  }

  const enrichedMessage = `${headerLines.join("\n")}\n\n${bridge.rawPayload}`;

  // Get session and process
  const { session } = capsuleCtx.chatSession;
  const stopProcessing = session.startProcessing();
  const typing = startTypingIndicator(ctx);

  let state = new StreamingState();
  let statusCallback = createStatusCallback(ctx, state);

  try {
    const response = await session.sendMessageStreaming(
      enrichedMessage,
      bridge.sourceBot.username.replace("@", ""),
      bridge.sourceBot.botId,
      statusCallback,
      chatId,
      ctx
    );

    // If inbound was a "request" from a TC3 bot, send response back with envelope
    if (
      bridge.envelope.type === "request" &&
      bridge.sourceBot.type === "tc3"
    ) {
      const config = loadBridgeConfig();
      const responseEnvelope = createResponseEnvelope(
        bridge.envelope,
        config.selfUsername
      );
      const responseText = formatOutboundMessage(
        bridge.sourceBot.username,
        response,
        responseEnvelope
      );

      await ctx.api.sendMessage(chatId, responseText);
      console.log(
        `[Bridge:Inbound] Sent response envelope to ${bridge.sourceBot.displayName}`
      );
    }

    // Audit log
    await auditLog(
      bridge.sourceBot.botId,
      bridge.sourceBot.username,
      "BRIDGE_INBOUND",
      bridge.rawPayload,
      response
    );
  } catch (error) {
    console.error("[Bridge:Inbound] Error processing bridge message:", error);
    // Don't reply with error to the chat for bridge messages - just log
  } finally {
    stopProcessing();
    typing.stop();
  }
}

// ============== Outbound Delegation Handler ==============

/**
 * Detect and handle delegation requests (user asking to message another bot).
 *
 * Returns true if a delegation was handled, false otherwise.
 */
async function handleOutboundDelegation(
  ctx: Context,
  strippedMessage: string
): Promise<boolean> {
  const chatId = ctx.chat!.id;
  const userId = ctx.from!.id;
  const username = ctx.from?.username || "unknown";

  const match = strippedMessage.match(DELEGATION_RE);
  if (!match) {
    return false;
  }

  const targetUsername = match[1]!;
  const payload = match[2]!.trim();

  // Look up target bot in registry
  const targetBot = findBotByUsername(targetUsername);
  if (!targetBot) {
    // Not a registered bridge bot - fall through to normal handling
    return false;
  }

  console.log(
    `[Bridge:Outbound] Delegation to ${targetBot.displayName}: "${payload.slice(0, 80)}..."`
  );

  // Create envelope and format outbound message
  const config = loadBridgeConfig();
  const envelope = createEnvelope({
    from: config.selfUsername,
    type: "request",
    ttl: config.maxTtl,
    intent: "delegate",
  });

  const formattedMsg = formatOutboundMessage(
    targetBot.username,
    payload,
    envelope
  );

  // Send to the group chat
  await ctx.api.sendMessage(chatId, formattedMsg);

  // Acknowledge to the user
  await ctx.reply(
    `\ud83d\udce1 Sent to ${targetBot.displayName}. Waiting for response.`
  );

  // Audit log
  await auditLog(
    userId,
    username,
    "BRIDGE_OUTBOUND",
    `-> ${targetBot.displayName}: ${payload}`
  );

  return true;
}

// ============== Main Handler ==============

/**
 * Handle incoming text messages.
 */
export async function handleText(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const preview = (ctx.message?.text || "").slice(0, 120).replace(/\n/g, " ");
  console.log(`[Text] inbound chat=${ctx.chat?.id} from=${userId} text="${preview}"`);
  const username = ctx.from?.username || "unknown";
  const chatId = ctx.chat?.id;
  let message = ctx.message?.text;

  if (!userId || !message || !chatId) {
    return;
  }

  // ---- Bridge inbound: handle messages from registered bots ----
  // This must come BEFORE the auth check because bot IDs are not in ALLOWED_USERS
  const bridgeMessage = (ctx as CapsuleContext).bridgeMessage;
  if (bridgeMessage) {
    await handleInboundBridge(ctx);
    return;
  }

  // 1. Authorization check (human users only at this point)
  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized. Contact the bot owner for access.");
    return;
  }

  // 2. Check for interrupt prefix
  message = await checkInterrupt(message);
  if (!message.trim()) {
    return;
  }

  // ---- Bridge outbound: detect delegation intent ----
  // Strip self-mention before pattern matching
  // e.g. "@{{ORCHESTRATOR_NAME}}CatalystBot ask @{{TELEGRAM_BOT_USERNAME}} to check health"
  //   -> "ask @{{TELEGRAM_BOT_USERNAME}} to check health"
  const config = loadBridgeConfig();
  const selfMentionRe = config.selfUsername
    ? new RegExp(
        `^${config.selfUsername.replace("@", "@?")}\\s*`,
        "i"
      )
    : null;
  const strippedForDelegation = selfMentionRe
    ? message.replace(selfMentionRe, "").trim()
    : message;

  if (await handleOutboundDelegation(ctx, strippedForDelegation)) {
    return; // Delegation handled - don't send to PI session
  }

  // 3. Rate limit check
  const [allowed, retryAfter] = rateLimiter.check(userId);
  if (!allowed) {
    await auditLogRateLimit(userId, username, retryAfter!);
    await ctx.reply(
      `\u23f3 Rate limited. Please wait ${retryAfter!.toFixed(1)} seconds.`
    );
    return;
  }

  // 4. Get per-chat session from middleware context
  const { session } = (ctx as CapsuleContext).chatSession;

  // 4a. Group chat acknowledgment — instant 👀 reaction before processing
  if (chatId < 0) {
    ctx.react("👀").catch((err: unknown) =>
      console.debug("[Text] Failed to set reaction:", err)
    );
  }

  // 5. Store message for retry
  session.lastMessage = message;

  // 6. Set conversation title from first message (if new session)
  if (!session.isActive) {
    // Truncate title to ~50 chars
    const title =
      message.length > 50 ? message.slice(0, 47) + "..." : message;
    session.conversationTitle = title;
  }

  // 7. Mark processing started
  const stopProcessing = session.startProcessing();

  // 8. Start typing indicator
  const typing = startTypingIndicator(ctx);

  // 9. Create streaming state and callback
  let state = new StreamingState();
  let statusCallback = createStatusCallback(ctx, state);

  // 10. Send to Claude with retry logic for crashes and auth fallback
  const MAX_RETRIES = 1;
  const chatSession = (ctx as CapsuleContext).chatSession;

  // CLI mode cold start: send interim feedback while Opus session initializes
  // (43K token cache creation takes 65-119s; typing indicator only lasts ~5s)
  if (chatSession.mode === "cli" && !chatSession.session.isActive) {
    await statusCallback("tool", "\u23f3 Starting Opus session...").catch(() => {});
  }

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      // Use sendWithAuthFallback for transparent PI -> CLI fallback on auth errors
      const { response, usedFallback } = await sendWithAuthFallback(
        chatSession,
        message,
        username,
        userId,
        statusCallback,
        chatId,
        ctx
      );

      if (usedFallback) {
        console.log("[TC3] Response served via CLI fallback (auth issue with PI mode)");
      }

      // If streaming produced no visible messages (e.g. PI mode returned non-streaming),
      // fall back to a single reply so the user never sees "no response".
      if (state.textMessages.size === 0) {
        const safe = response.length > 3900 ? response.slice(0, 3900) + "..." : response;
        await ctx.reply(safe).catch((err: unknown) =>
          console.debug("[Text] Fallback reply failed:", err)
        );
      }

      // 11. Audit log
      await auditLog(userId, username, "TEXT", message, response);

      // 12. TTS — read out the full response (fire-and-forget, never blocks)
      sendTtsAudio(ctx, response).catch((err: unknown) =>
        console.debug("[TTS] Send failed:", err)
      );

      break; // Success - exit retry loop
    } catch (error) {
      const errorStr = String(error);
      const isClaudeCodeCrash = errorStr.includes("exited with code");

      // Clean up any partial messages from this attempt
      for (const toolMsg of state.toolMessages) {
        try {
          await ctx.api.deleteMessage(toolMsg.chat.id, toolMsg.message_id);
        } catch {
          // Ignore cleanup errors
        }
      }

      // Retry on Claude Code crash (not user cancellation)
      if (isClaudeCodeCrash && attempt < MAX_RETRIES) {
        console.log(
          `Claude Code crashed, retrying (attempt ${attempt + 2}/${MAX_RETRIES + 1})...`
        );
        await session.kill(true); // Preserve file for context recovery on retry
        await ctx.reply(`\u26a0\ufe0f Claude crashed, retrying...`);
        // Reset state for retry
        state = new StreamingState();
        statusCallback = createStatusCallback(ctx, state);
        continue;
      }

      // Final attempt failed or non-retryable error
      console.error("Error processing message:", error);

      // Check if it was a cancellation
      if (errorStr.includes("abort") || errorStr.includes("cancel")) {
        // Only show "Query stopped" if it was an explicit stop, not an interrupt from a new message
        const wasInterrupt = session.consumeInterruptFlag();
        if (!wasInterrupt) {
          await ctx.reply("\ud83d\uded1 Query stopped.");
        }
      } else {
        await ctx.reply(`\u274c Error: ${errorStr.slice(0, 200)}`);
      }
      break; // Exit loop after handling error
    }
  }

  // 12. Cleanup
  stopProcessing();
  typing.stop();
}

/**
 * Bridge Middleware — Intercepts bot-to-bot messages in group chats.
 *
 * Runs after capsuleMiddleware, before sequentialize.
 * Detects messages from registered bridge bots, parses envelopes,
 * and attaches bridge metadata to the context for downstream handlers.
 *
 * Non-bot messages pass through untouched.
 * Unregistered bot messages are silently dropped.
 */

import type { NextFunction } from "grammy";
import type { CapsuleContext } from "./capsule";
import type { BridgeMessageMeta } from "../types";
import { parseEnvelope, isDuplicate, isExpired } from "../bridge/envelope";
import {
  loadBridgeConfig,
  findBotById,
  isSelf,
} from "../config/bridge-registry";

/**
 * Bridge middleware factory.
 *
 * Returns a grammY middleware that:
 * 1. Passes non-bot messages through immediately
 * 2. Drops messages from unregistered bots
 * 3. Parses bridge envelopes from registered bots
 * 4. Attaches `ctx.bridgeMessage` for downstream handlers
 */
export function bridgeMiddleware() {
  return async (ctx: CapsuleContext, next: NextFunction) => {
    // Only process text messages from bots
    if (!ctx.from?.is_bot || !ctx.message?.text) {
      return next();
    }

    // Enforce enabledGroups whitelist (empty = allow all)
    // Compare by absolute value — Telegram supergroup IDs are negative in Bot API
    // but may be stored as positive (e.g. from Telethon)
    const config = loadBridgeConfig();
    if (config.enabledGroups.length > 0) {
      const chatId = ctx.chat?.id;
      if (!chatId) return next();
      const absChatId = Math.abs(chatId);
      const match = config.enabledGroups.some(
        (gid) => Math.abs(gid) === absChatId
      );
      if (!match) {
        return next(); // Not a bridge-enabled group — pass through
      }
    }

    const senderId = ctx.from.id;

    // Ignore our own messages (echo prevention)
    if (isSelf(senderId)) {
      return; // Drop silently
    }

    // Look up sender in the bridge registry
    const sourceBot = findBotById(senderId);
    if (!sourceBot) {
      // Unregistered bot - drop silently
      return;
    }

    const messageText = ctx.message.text;

    // Try to parse a bridge envelope
    const parsed = parseEnvelope(messageText);

    if (parsed) {
      const { envelope, payload } = parsed;

      // Dedup check
      if (isDuplicate(envelope.id, config.dedupWindowMs)) {
        console.log(`[Bridge] Duplicate envelope ${envelope.id} - dropping`);
        return;
      }

      // TTL check
      if (isExpired(envelope)) {
        console.log(`[Bridge] Expired envelope ${envelope.id} (TTL=0) - dropping`);
        return;
      }

      // Attach full bridge metadata
      const meta: BridgeMessageMeta = {
        envelope,
        rawPayload: payload,
        sourceBot: {
          username: sourceBot.username,
          botId: sourceBot.botId,
          type: sourceBot.type,
          displayName: sourceBot.displayName,
        },
        isResponse: envelope.type === "response",
      };

      ctx.bridgeMessage = meta;
      console.log(
        `[Bridge] Envelope from ${sourceBot.displayName}: type=${envelope.type}, id=${envelope.id}, intent=${envelope.intent ?? "none"}`
      );
    } else {
      // Registered bot, but no envelope (plain message).
      // Attach minimal context so handlers know it's from a bridge bot.
      const meta: BridgeMessageMeta = {
        envelope: {
          id: `plain-${Date.now().toString(36)}`,
          from: sourceBot.username,
          type: "notification",
          ttl: 0,
          hop: 0,
          ref: null,
          ts: Date.now(),
        },
        rawPayload: messageText,
        sourceBot: {
          username: sourceBot.username,
          botId: sourceBot.botId,
          type: sourceBot.type,
          displayName: sourceBot.displayName,
        },
        isResponse: false,
      };

      ctx.bridgeMessage = meta;
      console.log(
        `[Bridge] Plain message from ${sourceBot.displayName} (no envelope)`
      );
    }

    return next();
  };
}

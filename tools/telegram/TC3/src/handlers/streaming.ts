/**
 * Shared streaming callback for Claude Telegram Bot handlers.
 *
 * Provides a reusable status callback for streaming Claude responses.
 */

import type { Context } from "grammy";
import { GrammyError } from "grammy";
import type { Message } from "grammy/types";
import { InlineKeyboard } from "grammy";
import type { StatusCallback } from "../types";
import { convertMarkdownToHtml, escapeHtml, formatWithinLimit, stripHtmlTags, stripTtsSummary } from "../formatting";
import {
  TELEGRAM_MESSAGE_LIMIT,
  TELEGRAM_SAFE_LIMIT,
  STREAMING_THROTTLE_MS,
  BUTTON_LABEL_MAX_LENGTH,
} from "../config";

// Group chats have stricter rate limits than DMs.
// This multiplier is applied to STREAMING_THROTTLE_MS for group chat IDs.
const GROUP_THROTTLE_MULTIPLIER = 3;

// Polling interval (ms) when waiting for a segment message creation to complete.
const CREATION_POLL_INTERVAL_MS = 50;
// Maximum number of poll iterations before giving up (~2 seconds total).
const CREATION_POLL_MAX_ATTEMPTS = 40;

// Per-chat rate limit backoff: chatId -> earliest next attempt timestamp (epoch ms).
// When a 429 is received, ALL streaming edits for that chat are suppressed until the
// backoff expires. This prevents a "death spiral" where many queued edits each trigger
// their own 429 -> retry -> 429 chain.
const chatRateLimitUntil = new Map<number, number>();

/**
 * Create inline keyboard for ask_user options.
 */
export function createAskUserKeyboard(
  requestId: string,
  options: string[]
): InlineKeyboard {
  const keyboard = new InlineKeyboard();
  for (let idx = 0; idx < options.length; idx++) {
    const option = options[idx]!;
    // Truncate long options for button display
    const display =
      option.length > BUTTON_LABEL_MAX_LENGTH
        ? option.slice(0, BUTTON_LABEL_MAX_LENGTH) + "..."
        : option;
    const callbackData = `askuser:${requestId}:${idx}`;
    keyboard.text(display, callbackData).row();
  }
  return keyboard;
}

/**
 * Check for pending ask-user requests and send inline keyboards.
 */
export async function checkPendingAskUserRequests(
  ctx: Context,
  chatId: number
): Promise<boolean> {
  const glob = new Bun.Glob("ask-user-*.json");
  let buttonsSent = false;

  for await (const filename of glob.scan({ cwd: "/tmp", absolute: false })) {
    const filepath = `/tmp/${filename}`;
    try {
      const file = Bun.file(filepath);
      const text = await file.text();
      const data = JSON.parse(text);

      // Only process pending requests for this chat
      if (data.status !== "pending") continue;
      if (String(data.chat_id) !== String(chatId)) continue;

      const question = data.question || "Please choose:";
      const options = data.options || [];
      const requestId = data.request_id || "";

      if (options.length > 0 && requestId) {
        const keyboard = createAskUserKeyboard(requestId, options);
        await ctx.reply(`❓ ${question}`, { reply_markup: keyboard });
        buttonsSent = true;

        // Mark as sent
        data.status = "sent";
        await Bun.write(filepath, JSON.stringify(data));
      }
    } catch (error) {
      console.warn(`Failed to process ask-user file ${filepath}:`, error);
    }
  }

  return buttonsSent;
}

/**
 * Attempt to edit a Telegram message with retry on 429 (Too Many Requests).
 *
 * Telegram 429 responses include `parameters.retry_after` (seconds to wait).
 * Instead of silently dropping the edit, we wait the specified time and retry once.
 * This prevents the "partial then full duplicate" symptom in group chats.
 *
 * @returns true if the edit succeeded, false if it failed after retry.
 */
async function retryEditOnRateLimit(
  ctx: Context,
  chatId: number,
  messageId: number,
  text: string,
  parseMode?: "HTML"
): Promise<boolean> {
  const doEdit = async () => {
    if (parseMode) {
      await ctx.api.editMessageText(chatId, messageId, text, {
        parse_mode: parseMode,
      });
    } else {
      await ctx.api.editMessageText(chatId, messageId, text);
    }
  };

  try {
    await doEdit();
    return true;
  } catch (error) {
    // Check for 429 rate limit
    if (error instanceof GrammyError && error.error_code === 429) {
      const retryAfter = (error.parameters as { retry_after?: number })
        .retry_after ?? 30;
      // Set per-chat backoff so ALL streaming edits are suppressed for this chat
      chatRateLimitUntil.set(chatId, Date.now() + retryAfter * 1000);
      console.debug(
        `[Streaming] 429 rate limited for chat ${chatId}, backoff ${retryAfter}s (suppressing all edits)`
      );
      await new Promise((r) => setTimeout(r, retryAfter * 1000));
      chatRateLimitUntil.delete(chatId); // Clean up regardless of retry outcome
      try {
        await doEdit();
        return true;
      } catch (retryError) {
        console.debug("[Streaming] Edit failed after 429 retry:", retryError);
        return false;
      }
    }

    // Check for "message is not modified" — content is already correct, not an error
    if (
      error instanceof GrammyError &&
      error.description.includes("message is not modified")
    ) {
      return true; // Content already matches, treat as success
    }

    // Check for bad HTML entities (common when model output contains unbalanced tags)
    if (
      error instanceof GrammyError &&
      error.error_code === 400 &&
      error.description.includes("can't parse entities")
    ) {
      try {
        const plainText = stripHtmlTags(text);
        await ctx.api.editMessageText(chatId, messageId, plainText);
        return true;
      } catch (fallbackError) {
        console.debug("[Streaming] Edit fallback (plain text) failed:", fallbackError);
        return false;
      }
    }

    // Re-throw unexpected errors
    throw error;
  }
}

/**
 * Tracks state for streaming message updates.
 */
export class StreamingState {
  textMessages = new Map<number, Message>(); // segment_id -> telegram message
  toolMessages: Message[] = []; // ephemeral tool status messages
  lastEditTimes = new Map<number, number>(); // segment_id -> last edit time
  lastContent = new Map<number, string>(); // segment_id -> last sent content
  isGroupChat = false; // set by createStatusCallback based on chat id

  // Lock to prevent concurrent message creation for the same segment.
  // Fire-and-forget callbacks race through the async gap between has() check
  // and set() after ctx.reply(). This Set acts as a synchronous guard:
  // the first callback adds the segmentId before awaiting, blocking others.
  // Inspired by OpenClaw's inFlight pattern in TelegramDraftStream.
  segmentCreationPending = new Set<number>();
}

/**
 * Create a status callback for streaming updates.
 *
 * Group chats use a longer throttle interval (GROUP_THROTTLE_MULTIPLIER * base)
 * because Telegram imposes stricter rate limits on group messages.
 */
export function createStatusCallback(
  ctx: Context,
  state: StreamingState
): StatusCallback {
  // Detect group chat: Telegram group/supergroup IDs are negative
  const chatId = ctx.chat?.id ?? 0;
  state.isGroupChat = chatId < 0;
  const effectiveThrottle = state.isGroupChat
    ? STREAMING_THROTTLE_MS * GROUP_THROTTLE_MULTIPLIER
    : STREAMING_THROTTLE_MS;

  if (state.isGroupChat) {
    console.debug(
      `[Streaming] Group chat detected (${chatId}), throttle: ${effectiveThrottle}ms`
    );
  }

  return async (statusType: string, content: string, segmentId?: number) => {
    try {
      if (statusType === "thinking") {
        // Show thinking inline, compact (first 500 chars)
        const preview =
          content.length > 500 ? content.slice(0, 500) + "..." : content;
        const escaped = escapeHtml(preview);
        const thinkingMsg = await ctx.reply(`🧠 <i>${escaped}</i>`, {
          parse_mode: "HTML",
        });
        state.toolMessages.push(thinkingMsg);
      } else if (statusType === "tool") {
        // Suppress all tool status messages — they create visual noise on Telegram.
        // formatToolStatus output is still used for console logging upstream.
        return;
      } else if (statusType === "text" && segmentId !== undefined) {
        // Skip streaming updates entirely if this chat is in rate-limit backoff
        const backoffUntil = chatRateLimitUntil.get(chatId) ?? 0;
        if (Date.now() < backoffUntil) {
          return; // Rate limited — skip this streaming update silently
        }

        const now = Date.now();
        const lastEdit = state.lastEditTimes.get(segmentId) || 0;

        // Strip TTS summary tags - they're for terminal, not Telegram
        const cleanedContent = stripTtsSummary(content);
        if (!cleanedContent) return; // Skip if only TTS content

        if (!state.textMessages.has(segmentId)) {
          // Guard: if another callback is already creating this segment's message,
          // skip — it will be available for editing on the next throttled update.
          if (state.segmentCreationPending.has(segmentId)) {
            return;
          }
          // Mark creation as in-flight SYNCHRONOUSLY before any await
          state.segmentCreationPending.add(segmentId);

          // New segment - create message
          // Use plain text to avoid Telegram HTML entity parse failures
          const formatted = stripHtmlTags(
            formatWithinLimit(cleanedContent, TELEGRAM_SAFE_LIMIT)
          );
          try {
            const msg = await ctx.reply(formatted, { parse_mode: "HTML" });
            state.textMessages.set(segmentId, msg);
            state.lastContent.set(segmentId, formatted);
          } catch (htmlError) {
            // HTML parse failed, fall back to plain text (strip tags!)
            console.debug("HTML reply failed, using plain text:", htmlError);
            const plainText = stripHtmlTags(formatted);
            const msg = await ctx.reply(plainText);
            state.textMessages.set(segmentId, msg);
            state.lastContent.set(segmentId, plainText);
          } finally {
            state.segmentCreationPending.delete(segmentId);
          }
          state.lastEditTimes.set(segmentId, now);
        } else if (now - lastEdit > effectiveThrottle) {
          // Update existing segment message (throttled)
          const msg = state.textMessages.get(segmentId)!;
          const formatted = stripHtmlTags(
            formatWithinLimit(cleanedContent, TELEGRAM_SAFE_LIMIT)
          );
          // Skip if content unchanged
          if (formatted === state.lastContent.get(segmentId)) {
            return;
          }
          // Use retry-aware edit that handles 429 properly
          const ok = await retryEditOnRateLimit(
            ctx,
            msg.chat.id,
            msg.message_id,
            formatted,
            "HTML"
          );
          if (ok) {
            state.lastContent.set(segmentId, formatted);
          } else {
            // HTML edit failed even after retry — try plain text (strip tags!)
            const plainText = stripHtmlTags(formatted);
            const plainOk = await retryEditOnRateLimit(
              ctx,
              msg.chat.id,
              msg.message_id,
              plainText
            );
            if (plainOk) {
              state.lastContent.set(segmentId, plainText);
            }
          }
          state.lastEditTimes.set(segmentId, now);
        }
      } else if (statusType === "segment_end" && segmentId !== undefined) {
        // segment_end is the FINAL message — always deliver it, but respect backoff by waiting
        const segBackoffUntil = chatRateLimitUntil.get(chatId) ?? 0;
        const remaining = segBackoffUntil - Date.now();
        if (remaining > 0) {
          console.debug(
            `[Streaming] segment_end waiting ${Math.ceil(remaining / 1000)}s for rate limit backoff`
          );
          await new Promise((r) => setTimeout(r, remaining));
          chatRateLimitUntil.delete(chatId);
        }

        // Strip TTS summary tags from final content
        const cleanedContent = stripTtsSummary(content);
        if (!cleanedContent) return; // Skip if no content after stripping

        // Use HTML formatting for final messages; fallback to plain text is
        // handled by retryEditOnRateLimit (catches can't parse entities → stripHtmlTags)
        // and by the HTML error catch blocks below.
        const formatted = formatWithinLimit(cleanedContent, TELEGRAM_MESSAGE_LIMIT);

        if (state.textMessages.has(segmentId)) {
          // Edit existing message with final content
          const msg = state.textMessages.get(segmentId)!;

          // Skip if content unchanged (catches dedup across text/segment_end)
          if (formatted === state.lastContent.get(segmentId)) {
            return;
          }

          if (formatted.length <= TELEGRAM_MESSAGE_LIMIT) {
            // Use retry-aware edit for the final message
            const ok = await retryEditOnRateLimit(
              ctx,
              msg.chat.id,
              msg.message_id,
              formatted,
              "HTML"
            );
            if (ok) {
              state.lastContent.set(segmentId, formatted);
            }
          } else {
            // Too long - delete and split
            try {
              await ctx.api.deleteMessage(msg.chat.id, msg.message_id);
            } catch (error) {
              console.debug("Failed to delete message for splitting:", error);
            }
            for (let i = 0; i < formatted.length; i += TELEGRAM_SAFE_LIMIT) {
              const chunk = formatted.slice(i, i + TELEGRAM_SAFE_LIMIT);
              try {
                await ctx.reply(chunk, { parse_mode: "HTML" });
              } catch (htmlError) {
                console.debug(
                  "HTML chunk failed, using plain text:",
                  htmlError
                );
                await ctx.reply(stripHtmlTags(chunk));
              }
            }
          }
        } else {
          // No existing message for this segment - create one (PI mode sends segment_end directly)
          // Guard: if a text callback is already creating this segment, wait for it then edit
          if (state.segmentCreationPending.has(segmentId)) {
            // Poll until creation finishes (50ms intervals, up to 2s)
            for (let i = 0; i < CREATION_POLL_MAX_ATTEMPTS; i++) {
              await new Promise((r) => setTimeout(r, CREATION_POLL_INTERVAL_MS));
              if (!state.segmentCreationPending.has(segmentId)) break;
            }
            // After waiting, if the message was created, edit it instead
            if (state.textMessages.has(segmentId)) {
              const msg = state.textMessages.get(segmentId)!;
              const ok = await retryEditOnRateLimit(ctx, msg.chat.id, msg.message_id, formatted, "HTML");
              if (ok) state.lastContent.set(segmentId, formatted);
              return;
            }
          }
          // Final TOCTOU check: a racing text callback may have populated textMessages
          // between the poll timeout and this point. Re-check before creating a new message.
          if (state.textMessages.has(segmentId)) {
            const msg = state.textMessages.get(segmentId)!;
            const ok = await retryEditOnRateLimit(ctx, msg.chat.id, msg.message_id, formatted, "HTML");
            if (ok) state.lastContent.set(segmentId, formatted);
            return;
          }
          state.segmentCreationPending.add(segmentId);

          try {
            if (formatted.length <= TELEGRAM_MESSAGE_LIMIT) {
              try {
                const msg = await ctx.reply(formatted, { parse_mode: "HTML" });
                state.textMessages.set(segmentId, msg);
                state.lastContent.set(segmentId, formatted);
              } catch (htmlError) {
                console.debug("HTML reply failed, using plain text:", htmlError);
                const plainText = stripHtmlTags(formatted);
                const msg = await ctx.reply(plainText);
                state.textMessages.set(segmentId, msg);
                state.lastContent.set(segmentId, plainText);
              }
            } else {
              // Too long - split into chunks
              for (let i = 0; i < formatted.length; i += TELEGRAM_SAFE_LIMIT) {
                const chunk = formatted.slice(i, i + TELEGRAM_SAFE_LIMIT);
                try {
                  await ctx.reply(chunk, { parse_mode: "HTML" });
                } catch (htmlError) {
                  console.debug("HTML chunk failed, using plain text:", htmlError);
                  await ctx.reply(stripHtmlTags(chunk));
                }
              }
            }
          } finally {
            state.segmentCreationPending.delete(segmentId);
          }
        }
      } else if (statusType === "done") {
        // Delete tool messages - text messages stay
        for (const toolMsg of state.toolMessages) {
          try {
            await ctx.api.deleteMessage(toolMsg.chat.id, toolMsg.message_id);
          } catch (error) {
            console.debug("Failed to delete tool message:", error);
          }
        }
      }
    } catch (error) {
      console.error("Status callback error:", error);
    }
  };
}

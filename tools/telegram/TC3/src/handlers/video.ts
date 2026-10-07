/**
 * Video message handler for Claude Telegram Bot.
 *
 * Handles video messages and video notes (round videos).
 * Downloads the video file and passes the path to Claude for visual analysis.
 */

import type { Context } from "grammy";
import { unlinkSync } from "fs";
import type { CapsuleContext } from "../middleware/capsule";
import { ALLOWED_USERS, TEMP_DIR } from "../config";
import { isAuthorized, rateLimiter } from "../security";
import { auditLog, auditLogRateLimit, startTypingIndicator } from "../utils";
import { StreamingState, createStatusCallback } from "./streaming";
import { retryGetFile } from "../errors";

// Max video file size for download (50MB — Telegram Bot API limit is 20MB for getFile)
const MAX_VIDEO_SIZE = 50 * 1024 * 1024;

/**
 * Handle incoming video and video_note messages.
 */
export async function handleVideo(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const username = ctx.from?.username || "unknown";
  const chatId = ctx.chat?.id;
  const video = ctx.message?.video || ctx.message?.video_note;

  if (!userId || !video || !chatId) {
    return;
  }

  // 1. Authorization check
  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized. Contact the bot owner for access.");
    return;
  }

  // 2. Size check
  if (video.file_size && video.file_size > MAX_VIDEO_SIZE) {
    await ctx.reply("❌ Video too large. Maximum size is 50MB.");
    return;
  }

  // 3. Rate limit check
  const [allowed, retryAfter] = rateLimiter.check(userId);
  if (!allowed) {
    await auditLogRateLimit(userId, username, retryAfter!);
    await ctx.reply(
      `⏳ Rate limited. Please wait ${retryAfter!.toFixed(1)} seconds.`
    );
    return;
  }

  // 4. Get per-chat session from middleware context
  const { session } = (ctx as CapsuleContext).chatSession;

  // 5. Mark processing started
  const stopProcessing = session.startProcessing();

  // 6. Start typing indicator
  const typing = startTypingIndicator(ctx);

  let videoPath: string | null = null;

  try {
    // 7. Download video file
    const file = await retryGetFile(() => ctx.getFile());
    const timestamp = Date.now();
    const random = Math.random().toString(36).slice(2, 8);
    videoPath = `${TEMP_DIR}/video_${timestamp}_${random}.mp4`;

    const downloadUrl = `https://api.telegram.org/file/bot${ctx.api.token}/${file.file_path}`;
    const downloadRes = await fetch(downloadUrl).catch((err: unknown) => {
      throw new Error(`Video download failed: ${(err as Error).message}`);
    });
    const buffer = await downloadRes.arrayBuffer();
    await Bun.write(videoPath, buffer);

    // 8. Build prompt (include file path for Claude to read, same pattern as photo handler)
    const isVideoNote = !!ctx.message?.video_note;
    const caption = ctx.message?.caption;
    const duration = video.duration ? `${video.duration}s` : "unknown duration";
    const videoType = isVideoNote ? "video note (round video)" : "video";

    let prompt: string;
    if (caption) {
      prompt = `[Video (${videoType}, ${duration}): ${videoPath}]\n\n${caption}`;
    } else {
      prompt = `The user sent a ${videoType} (${duration}). Please describe and analyze what you see.\n\n[Video: ${videoPath}]`;
    }

    // 9. Set conversation title (if new session)
    if (!session.isActive) {
      const title = caption
        ? caption.length > 50
          ? caption.slice(0, 47) + "..."
          : caption
        : `[Video: ${duration}]`;
      session.conversationTitle = title;
    }

    // 10. Show status
    const statusMsg = await ctx.reply("\ud83c\udfac Processing video...");

    // 11. Create streaming state and callback
    const state = new StreamingState();
    const statusCallback = createStatusCallback(ctx, state);

    // 12. Send to Claude
    const claudeResponse = await session.sendMessageStreaming(
      prompt,
      username,
      userId,
      statusCallback,
      chatId,
      ctx
    );

    // 13. Delete status message
    try {
      await ctx.api.deleteMessage(statusMsg.chat.id, statusMsg.message_id);
    } catch {
      // Ignore deletion errors
    }

    // 14. Audit log
    await auditLog(userId, username, "VIDEO", prompt, claudeResponse);
  } catch (error) {
    console.error("Error processing video:", error);

    if (String(error).includes("abort") || String(error).includes("cancel")) {
      const wasInterrupt = session.consumeInterruptFlag();
      if (!wasInterrupt) {
        await ctx.reply("🛑 Query stopped.");
      }
    } else {
      await ctx.reply(`❌ Error: ${String(error).slice(0, 200)}`);
    }
  } finally {
    stopProcessing();
    typing.stop();

    // Clean up video file
    if (videoPath) {
      try {
        unlinkSync(videoPath);
      } catch (error) {
        console.debug("Failed to delete video file:", error);
      }
    }
  }
}

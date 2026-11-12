/**
 * Audio file handler for Claude Telegram Bot.
 *
 * Handles audio files (music, podcasts, voice memos sent as files).
 * Transcribes via Whisper and sends to Claude.
 *
 * Two entry points:
 *   1. Direct: bot.on("message:audio") — Telegram audio messages
 *   2. Routed: called from document.ts when audio MIME type detected
 */

import type { Context } from "grammy";
import { unlinkSync } from "fs";
import type { CapsuleContext } from "../middleware/capsule";
import { ALLOWED_USERS, TEMP_DIR, TRANSCRIPTION_AVAILABLE } from "../config";
import { isAuthorized, rateLimiter } from "../security";
import {
  auditLog,
  auditLogRateLimit,
  transcribeVoice,
  startTypingIndicator,
} from "../utils";
import { StreamingState, createStatusCallback } from "./streaming";
import { retryGetFile } from "../errors";

// Max audio file size (25MB — Whisper API limit)
const MAX_AUDIO_SIZE = 25 * 1024 * 1024;

// MIME type to file extension mapping
const MIME_TO_EXT: Record<string, string> = {
  "audio/mpeg": ".mp3",
  "audio/mp3": ".mp3",
  "audio/mp4": ".m4a",
  "audio/m4a": ".m4a",
  "audio/ogg": ".ogg",
  "audio/opus": ".opus",
  "audio/wav": ".wav",
  "audio/x-wav": ".wav",
  "audio/flac": ".flac",
  "audio/aac": ".aac",
  "audio/webm": ".webm",
  "video/ogg": ".ogg",
  "application/ogg": ".ogg",
};

/**
 * Check if a MIME type is an audio type.
 * Exported for use by document.ts to route audio-as-document.
 */
export function isAudioMimeType(mime: string): boolean {
  if (!mime) return false;
  const lower = mime.toLowerCase();
  return (
    lower.startsWith("audio/") ||
    lower === "video/ogg" ||
    lower === "application/ogg"
  );
}

/**
 * Handle incoming audio messages.
 *
 * @param ctx - Grammy context
 * @param overrideMimeType - MIME type override (when called from document.ts)
 * @param overrideFileName - Filename override (when called from document.ts)
 */
export async function handleAudio(
  ctx: Context,
  overrideMimeType?: string,
  overrideFileName?: string
): Promise<void> {
  const userId = ctx.from?.id;
  const username = ctx.from?.username || "unknown";
  const chatId = ctx.chat?.id;

  // Audio can come from message.audio (direct) or message.document (routed)
  const audio = ctx.message?.audio;
  const doc = ctx.message?.document;
  const fileSize = audio?.file_size || doc?.file_size || 0;
  const mimeType =
    overrideMimeType || audio?.mime_type || doc?.mime_type || "audio/mpeg";
  const fileName =
    overrideFileName ||
    audio?.file_name ||
    doc?.file_name ||
    `audio_${Date.now()}`;

  if (!userId || !chatId || (!audio && !doc)) {
    return;
  }

  // 1. Authorization check
  if (!isAuthorized(userId, ALLOWED_USERS)) {
    await ctx.reply("Unauthorized. Contact the bot owner for access.");
    return;
  }

  // 2. Check if transcription is available
  if (!TRANSCRIPTION_AVAILABLE) {
    await ctx.reply(
      "Audio transcription is not configured. Set OPENAI_API_KEY in .env"
    );
    return;
  }

  // 3. Size check
  if (fileSize && fileSize > MAX_AUDIO_SIZE) {
    await ctx.reply("❌ Audio file too large. Maximum size is 25MB (Whisper limit).");
    return;
  }

  // 4. Rate limit check
  const [allowed, retryAfter] = rateLimiter.check(userId);
  if (!allowed) {
    await auditLogRateLimit(userId, username, retryAfter!);
    await ctx.reply(
      `⏳ Rate limited. Please wait ${retryAfter!.toFixed(1)} seconds.`
    );
    return;
  }

  // 5. Get per-chat session from middleware context
  const { session } = (ctx as CapsuleContext).chatSession;

  // 6. Mark processing started
  const stopProcessing = session.startProcessing();

  // 7. Start typing indicator
  const typing = startTypingIndicator(ctx);

  let audioPath: string | null = null;

  try {
    // 8. Download audio file
    const file = await retryGetFile(() => ctx.getFile());
    const timestamp = Date.now();
    const random = Math.random().toString(36).slice(2, 8);
    const ext = MIME_TO_EXT[mimeType.toLowerCase()] || ".ogg";
    audioPath = `${TEMP_DIR}/audio_${timestamp}_${random}${ext}`;

    const downloadUrl = `https://api.telegram.org/file/bot${ctx.api.token}/${file.file_path}`;
    const downloadRes = await fetch(downloadUrl).catch((err: unknown) => {
      throw new Error(`Audio download failed: ${(err as Error).message}`);
    });
    const buffer = await downloadRes.arrayBuffer();
    await Bun.write(audioPath, buffer);

    // 9. Show transcription status
    const statusMsg = await ctx.reply(`🎵 Transcribing "${fileName}"...`);

    // 10. Transcribe via Whisper
    const transcript = await transcribeVoice(audioPath);
    if (!transcript) {
      await ctx.api.editMessageText(
        chatId,
        statusMsg.message_id,
        "❌ Transcription failed."
      );
      return; // finally block handles stopProcessing() + typing.stop()
    }

    // 11. Show transcript
    const displayTranscript =
      transcript.length > 300 ? transcript.slice(0, 297) + "..." : transcript;
    await ctx.api.editMessageText(
      chatId,
      statusMsg.message_id,
      `🎵 "${displayTranscript}"`
    );

    // 12. Set conversation title (if new session)
    if (!session.isActive) {
      const title =
        transcript.length > 50
          ? transcript.slice(0, 47) + "..."
          : transcript;
      session.conversationTitle = title;
    }

    // 13. Build prompt with transcript + file context
    const caption = ctx.message?.caption;
    const duration = audio?.duration ? `${audio.duration}s` : "";
    const durationStr = duration ? ` (${duration})` : "";

    let prompt: string;
    if (caption) {
      prompt = `The user sent an audio file "${fileName}"${durationStr} with caption: "${caption}"\n\nTranscription:\n${transcript}`;
    } else {
      prompt = `The user sent an audio file "${fileName}"${durationStr}.\n\nTranscription:\n${transcript}`;
    }

    // 14. Create streaming state and callback
    const state = new StreamingState();
    const statusCallback = createStatusCallback(ctx, state);

    // 15. Send to Claude
    const claudeResponse = await session.sendMessageStreaming(
      prompt,
      username,
      userId,
      statusCallback,
      chatId,
      ctx
    );

    // 16. Audit log
    await auditLog(
      userId,
      username,
      "AUDIO",
      `[${fileName}] ${transcript.slice(0, 100)}`,
      claudeResponse
    );
  } catch (error) {
    console.error("Error processing audio:", error);

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

    // Clean up audio file
    if (audioPath) {
      try {
        unlinkSync(audioPath);
      } catch (error) {
        console.debug("Failed to delete audio file:", error);
      }
    }
  }
}

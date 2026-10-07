/**
 * TTS Service - Connects to Kokoro TTS server for voice synthesis.
 *
 * Communicates with the pre-loaded Kokoro-82M model server via TCP socket.
 * Gracefully degrades if server is unavailable.
 *
 * Ported from TC1-gateway with full-message readout support.
 */

import { connect, type Socket } from "net";
import { existsSync, unlinkSync } from "fs";
import { execSync } from "child_process";

// Server configuration — shared Kokoro TTS server on localhost
const TTS_HOST = "127.0.0.1";
const TTS_PORT = 9876;
const CONNECTION_TIMEOUT_MS = 2000;
const RESPONSE_TIMEOUT_MS = 30000; // 30s for long messages (TC1 used 15s)

/**
 * Convert WAV to high-quality MP3 for Telegram audio messages.
 */
function convertToMp3(wavPath: string): string | null {
  const mp3Path = wavPath.replace(/\.wav$/, ".mp3");

  try {
    execSync(
      `ffmpeg -y -i "${wavPath}" -c:a libmp3lame -q:a 0 "${mp3Path}" 2>/dev/null`,
      { timeout: 15000 }
    );

    if (existsSync(mp3Path)) {
      console.debug(`[TTS] Converted to MP3: ${mp3Path}`);
      try { unlinkSync(wavPath); } catch {}
      return mp3Path;
    }
  } catch (error) {
    console.debug(`[TTS] MP3 conversion failed: ${error}`);
  }

  return wavPath;
}

/**
 * Response from TTS server.
 */
interface TTSResponse {
  status: "success" | "error";
  audio_path?: string;
  message?: string;
}

/**
 * Check if TTS server is available.
 */
export async function isTTSAvailable(): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = connect(TTS_PORT, TTS_HOST);
    const timeout = setTimeout(() => {
      socket.destroy();
      resolve(false);
    }, CONNECTION_TIMEOUT_MS);

    socket.on("connect", () => {
      clearTimeout(timeout);
      socket.destroy();
      resolve(true);
    });

    socket.on("error", () => {
      clearTimeout(timeout);
      resolve(false);
    });
  });
}

/**
 * Send text to TTS server and get audio file path.
 *
 * @returns Path to MP3 file, or null if failed
 */
export async function synthesizeSpeech(text: string): Promise<string | null> {
  if (!text || text.length < 5) {
    console.debug("[TTS] Text too short, skipping");
    return null;
  }

  return new Promise((resolve) => {
    let socket: Socket | null = null;
    let responseData = "";
    let resolved = false;

    const cleanup = () => {
      if (socket) {
        socket.removeAllListeners();
        socket.destroy();
        socket = null;
      }
    };

    const finish = (result: string | null) => {
      if (!resolved) {
        resolved = true;
        cleanup();
        resolve(result);
      }
    };

    const connectionTimeout = setTimeout(() => {
      clearTimeout(responseTimeout);
      console.debug("[TTS] Connection timeout");
      finish(null);
    }, CONNECTION_TIMEOUT_MS);

    const responseTimeout = setTimeout(() => {
      clearTimeout(connectionTimeout);
      console.debug("[TTS] Response timeout");
      finish(null);
    }, RESPONSE_TIMEOUT_MS);

    socket = connect(TTS_PORT, TTS_HOST);

    socket.on("connect", () => {
      clearTimeout(connectionTimeout);
      // 1.0x for natural Telegram voice (server default is 1.2x)
      const request = JSON.stringify({ text, speed: 1.0 }) + "\n\n";
      socket!.write(request);
    });

    socket.on("data", (chunk) => {
      responseData += chunk.toString();
    });

    socket.on("end", () => {
      clearTimeout(responseTimeout);

      try {
        const response: TTSResponse = JSON.parse(responseData);

        if (response.status === "success" && response.audio_path) {
          // Validate path is in expected temp directories
          const safePrefixes = ["/tmp/", "/Users/", "/private/tmp/"];
          const pathOk = safePrefixes.some((p) => response.audio_path!.startsWith(p));
          if (!pathOk) {
            console.debug(`[TTS] Rejected suspicious audio_path: ${response.audio_path}`);
            finish(null);
            return;
          }
          if (existsSync(response.audio_path)) {
            console.debug(`[TTS] Generated audio: ${response.audio_path}`);
            const optimizedPath = convertToMp3(response.audio_path);
            finish(optimizedPath);
          } else {
            console.debug(`[TTS] Audio file not found: ${response.audio_path}`);
            finish(null);
          }
        } else {
          console.debug(`[TTS] Server error: ${response.message || "unknown"}`);
          finish(null);
        }
      } catch (error) {
        console.debug(`[TTS] Parse error: ${error}`);
        finish(null);
      }
    });

    socket.on("error", (error) => {
      clearTimeout(connectionTimeout);
      clearTimeout(responseTimeout);
      console.debug(`[TTS] Socket error: ${error.message}`);
      finish(null);
    });

    socket.on("close", () => {
      clearTimeout(connectionTimeout);
      clearTimeout(responseTimeout);
      finish(null); // Ensure promise resolves on abrupt disconnect
    });
  });
}

/**
 * Clean up audio file after sending.
 */
export function cleanupAudioFile(path: string): void {
  try {
    if (existsSync(path)) {
      unlinkSync(path);
    }
  } catch (error) {
    console.debug(`[TTS] Cleanup error: ${error}`);
  }
}

/**
 * Clean text for TTS readout — strips formatting while keeping full content.
 *
 * Removes: HTML tags, code blocks, inline code backticks, markdown bold/italic,
 * URLs, bullet characters, excessive whitespace, emojis.
 */
export function cleanTextForTts(text: string): string {
  return text
    .replace(/<[^>]+>/g, "") // Strip HTML tags
    .replace(/```[\s\S]*?```/g, " (code omitted) ") // Replace code blocks with marker
    .replace(/`([^`]+)`/g, "$1") // Remove inline code backticks
    .replace(/\*\*(.*?)\*\*/g, "$1") // Remove bold
    .replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, "$1") // Remove italic
    .replace(/__([^_]+)__/g, "$1") // Remove underline bold
    .replace(/(?<!_)_([^_]+)_(?!_)/g, "$1") // Remove underline italic
    .replace(/^#{1,6}\s+/gm, "") // Remove heading markers
    .replace(/https?:\/\/\S+/g, "") // Remove URLs
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // Links: keep text, remove URL
    .replace(/[•–—]/g, ", ") // Replace bullets/dashes with pause
    .replace(/&amp;/g, "&") // Decode HTML entities
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/[^\p{L}\p{N}\s.,!?'"-:;()/]/gu, "") // Remove emojis and special chars
    .replace(/\n{2,}/g, ". ") // Paragraph breaks become sentence pauses
    .replace(/\n/g, " ") // Single newlines become spaces
    .replace(/\s+/g, " ") // Collapse whitespace
    .trim();
}

/**
 * Split text into chunks for TTS synthesis.
 * Splits on paragraph and sentence boundaries for natural speech.
 */
export function splitTextForTts(text: string, maxChunkChars = 900): string[] {
  const t = (text || "").trim();
  if (!t) return [];

  const paras = t.split(/\n\n+/).map((x) => x.trim()).filter(Boolean);
  const chunks: string[] = [];

  const push = (buf: string) => {
    const b = buf.trim();
    if (b.length >= 5) chunks.push(b);
  };

  let buf = "";
  const add = (part: string) => {
    if (!part) return;
    const next = buf ? buf + " " + part : part;
    if (next.length <= maxChunkChars) {
      buf = next;
      return;
    }
    if (buf) push(buf);
    if (part.length <= maxChunkChars) {
      buf = part;
      return;
    }
    // Hard split long parts
    for (let i = 0; i < part.length; i += maxChunkChars) {
      push(part.slice(i, i + maxChunkChars));
    }
    buf = "";
  };

  for (const para of paras) {
    const sentences = para.split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean);
    if (sentences.length <= 1) {
      add(para);
    } else {
      for (const sent of sentences) add(sent);
    }

    // Paragraph boundary: flush if buffer is getting large
    if (buf.length > maxChunkChars * 0.8) {
      push(buf);
      buf = "";
    }
  }

  if (buf) push(buf);
  return chunks;
}

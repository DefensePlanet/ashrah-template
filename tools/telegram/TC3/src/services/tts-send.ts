/**
 * TTS send helper — synthesizes and sends audio replies in Telegram.
 *
 * Generates TTS for the full Claude response, concatenates chunks into
 * a single MP3 for continuous playback, sends via ctx.replyWithAudio().
 *
 * Fire-and-forget: TTS failures never block the text response.
 */

import type { Context } from "grammy";
import { InputFile } from "grammy";
import {
  isTTSAvailable,
  synthesizeSpeech,
  cleanupAudioFile,
  cleanTextForTts,
  splitTextForTts,
} from "./tts";
import { mkdtempSync, writeFileSync, existsSync, unlinkSync, rmdirSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { execSync } from "child_process";

const MAX_PARTS = 25; // Safety cap on chunks
const SLUG_MAX_WORDS = 6;
const SLUG_MAX_LENGTH = 50;

/**
 * Derive a human-readable filename from the message text.
 * e.g. "Here's what I found about the API" → "heres-what-i-found-about-the.mp3"
 */
function ttsFilename(text: string): string {
  const slug = text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, "")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, SLUG_MAX_WORDS)
    .join("-")
    .slice(0, SLUG_MAX_LENGTH)
    .replace(/-$/, "");
  if (slug) return `${slug}.mp3`;
  // Non-Latin / emoji-only text — use a short timestamp so each file is still distinct
  return `{{ORCHESTRATOR_NAME_LOWER}}-voice-${Date.now()}.mp3`;
}

/**
 * Concatenate multiple MP3 files into one for continuous playback.
 */
/**
 * Tracks temp directory + list file for cleanup after the caller is done
 * with the combined MP3.
 */
let lastConcatDir: string | null = null;

function cleanupConcatDir(): void {
  if (!lastConcatDir) return;
  try { unlinkSync(join(lastConcatDir, "inputs.txt")); } catch {}
  try { rmdirSync(lastConcatDir); } catch {} // only succeeds if empty
  lastConcatDir = null;
}

function concatMp3Files(mp3Paths: string[]): string | null {
  if (mp3Paths.length === 0) return null;
  if (mp3Paths.length === 1) return mp3Paths[0] || null;

  // Clean up any leftover from a previous call
  cleanupConcatDir();

  const dir = mkdtempSync(join(tmpdir(), "tc3-tts-"));
  lastConcatDir = dir;
  const listPath = join(dir, "inputs.txt");
  const outPath = join(dir, "combined.mp3");

  const list = mp3Paths
    .filter(Boolean)
    .map((p) => `file "${p.replace(/"/g, '\\"')}"`)
    .join("\n");
  writeFileSync(listPath, list + "\n");

  try {
    execSync(
      `ffmpeg -y -f concat -safe 0 -i "${listPath}" -c:a libmp3lame -q:a 0 "${outPath}" 2>/dev/null`,
      { timeout: 30000 }
    );
    if (existsSync(outPath)) return outPath;
  } catch {
    cleanupConcatDir();
    return null;
  }

  cleanupConcatDir();
  return null;
}

/**
 * Generate and send TTS audio for a Claude response.
 *
 * Reads out the entire message (cleaned of formatting).
 * Gracefully degrades if TTS server is unavailable.
 *
 * @param ctx - Grammy context
 * @param responseText - Raw Claude response text (markdown/HTML)
 */
export async function sendTtsAudio(
  ctx: Context,
  responseText: string
): Promise<void> {
  const cleaned = cleanTextForTts(responseText);
  if (!cleaned || cleaned.length < 10) return;

  const available = await isTTSAvailable();
  if (!available) {
    console.debug("[TTS] Server not available, skipping");
    return;
  }

  const chunks = splitTextForTts(cleaned, 900);
  const limited = chunks.length > MAX_PARTS ? chunks.slice(0, MAX_PARTS) : chunks;

  console.debug(`[TTS] Synthesizing ${limited.length} chunks (${cleaned.length} chars)`);

  // Synthesize each chunk
  const audioPaths: string[] = [];
  for (const chunk of limited) {
    const audioPath = await synthesizeSpeech(chunk);
    if (audioPath) audioPaths.push(audioPath);
  }

  if (audioPaths.length === 0) {
    console.debug("[TTS] No audio generated");
    return;
  }

  const filename = ttsFilename(cleaned);

  let combined: string | null = null;
  try {
    // Concatenate into one MP3 for continuous playback
    combined = concatMp3Files(audioPaths);
    if (combined) {
      await ctx.replyWithAudio(new InputFile(combined, filename));
    } else if (audioPaths.length === 1) {
      // Single chunk — send directly
      await ctx.replyWithAudio(new InputFile(audioPaths[0]!, filename));
    } else {
      // Concat failed — send parts as fallback
      for (let i = 0; i < audioPaths.length; i++) {
        const base = filename.slice(0, -4); // strip .mp3
        const partName = `${base}-pt${i + 1}.mp3`;
        await ctx.replyWithAudio(new InputFile(audioPaths[i]!, partName));
      }
    }

    console.debug(`[TTS] Sent audio (${audioPaths.length} parts synthesized)`);
  } finally {
    if (combined) cleanupAudioFile(combined);
    cleanupConcatDir();
    for (const p of audioPaths) cleanupAudioFile(p);
  }
}

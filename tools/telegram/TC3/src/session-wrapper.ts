/**
 * Session Pool — Per-chat session management for multi-capsule architecture.
 *
 * Replaces the old singleton pattern. Each Telegram chat gets its own session
 * scoped to its bound capsule (working directory). Sessions are lazily created
 * and evicted when idle.
 *
 * Modes:
 * - "pi" (default) - Uses pi-coding-agent (clawdbot-style, fast ~3s)
 * - "cli" - Claude Agent SDK (spawns CLI, slower but full MCP/CLAUDE.md support)
 */

import type { Context } from "grammy";
import type { SessionMode, StatusCallback } from "./types";
import { getCapsuleConfig, updateCapsuleMode } from "./config/capsule-loader";
import { PiSession } from "./session-pi";
import { AuthError } from "./errors";
import { ClaudeSession } from "./session";

export type { SessionMode };
export type SessionLike = PiSession | ClaudeSession;

export interface ChatSession {
  session: SessionLike;
  mode: SessionMode;
  capsuleName: string;
  workingDir: string;
  lastActivity: number;
}

const MAX_POOL_SIZE = 20;
const IDLE_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

const sessionPool = new Map<number, ChatSession>();

/**
 * Get or create a session for a specific chat.
 */
export function getOrCreateSession(chatId: number): ChatSession {
  let entry = sessionPool.get(chatId);
  if (entry) {
    entry.lastActivity = Date.now();
    return entry;
  }

  // Evict idle sessions if pool is full
  if (sessionPool.size >= MAX_POOL_SIZE) {
    evictIdleSessions();
  }

  // Look up capsule config for this chat
  const capsule = getCapsuleConfig(chatId);
  const mode = capsule.defaultMode || "pi";

  // Create session based on mode
  const session = createSessionForMode(mode, capsule.workingDir, capsule.name);

  entry = {
    session,
    mode,
    capsuleName: capsule.name,
    workingDir: capsule.workingDir,
    lastActivity: Date.now(),
  };

  sessionPool.set(chatId, entry);
  console.log(`[SessionPool] [${capsule.name}] Created ${mode.toUpperCase()} session for chat ${chatId}`);
  return entry;
}

/**
 * Switch mode for a specific chat. Kills old session, creates new one.
 */
export async function switchMode(chatId: number, mode: SessionMode): Promise<boolean> {
  const entry = sessionPool.get(chatId);
  const currentMode = entry?.mode || "pi";

  if (mode === currentMode) return false;

  // Remove from pool FIRST to prevent concurrent access to zombie session
  sessionPool.delete(chatId);

  // Kill existing session (now safe — no one can get a reference to it)
  if (entry) {
    try {
      if (entry.session.isRunning) {
        await entry.session.stop();
        await Bun.sleep(100);
        if ('clearStopRequested' in entry.session) {
          entry.session.clearStopRequested();
        }
      }
      await entry.session.kill(true); // Preserve session file so history survives mode switch
    } catch (err) {
      console.warn("[SessionPool] Error cleaning up session during mode switch:", err);
    }
  }

  const capsule = getCapsuleConfig(chatId);
  const newSession = createSessionForMode(mode, capsule.workingDir, capsule.name);

  sessionPool.set(chatId, {
    session: newSession,
    mode,
    capsuleName: capsule.name,
    workingDir: capsule.workingDir,
    lastActivity: Date.now(),
  });

  // Persist mode preference
  updateCapsuleMode(chatId, mode);

  console.log(`[SessionPool] [${capsule.name}] Switched ${currentMode.toUpperCase()} -> ${mode.toUpperCase()}`);
  return true;
}

/**
 * Get current mode for a chat.
 */
export function getCurrentMode(chatId: number): SessionMode {
  return sessionPool.get(chatId)?.mode || getCapsuleConfig(chatId).defaultMode || "pi";
}

/**
 * Clean up session for a chat (e.g., after capsule rebind).
 */
export async function cleanupSession(chatId: number): Promise<void> {
  const entry = sessionPool.get(chatId);
  if (entry) {
    try { await entry.session.kill(); } catch {} // Intentional file deletion — rebind means fresh context
    sessionPool.delete(chatId);
    console.log(`[SessionPool] Cleaned up session for chat ${chatId}`);
  }
  // Also clean up any CLI fallback session for this chat
  const fallback = cliFallbackSessions.get(chatId);
  if (fallback) {
    try { await fallback.kill(); } catch {}
    cliFallbackSessions.delete(chatId);
    console.log(`[SessionPool] Cleaned up CLI fallback for chat ${chatId}`);
  }
}

/**
 * Get pool stats for diagnostics.
 */
export function getPoolStats(): { size: number; chats: number[] } {
  return {
    size: sessionPool.size,
    chats: Array.from(sessionPool.keys()),
  };
}

// ============== Internal ==============

function createSessionForMode(mode: SessionMode, workingDir: string, capsuleName: string): SessionLike {
  if (mode === "cli") {
    return new ClaudeSession({ workingDir, capsuleName });
  }
  return new PiSession(workingDir, capsuleName);
}

function evictIdleSessions(): void {
  const now = Date.now();
  for (const [chatId, entry] of sessionPool) {
    if (now - entry.lastActivity > IDLE_TIMEOUT_MS) {
      // Preserve session file so conversation history can be replayed when the user returns
      entry.session.kill(true).catch(() => {});
      sessionPool.delete(chatId);
      const fallback = cliFallbackSessions.get(chatId);
      if (fallback) {
        fallback.kill().catch(() => {}); // Fallback sessions don't need file preservation
        cliFallbackSessions.delete(chatId);
      }
      console.log(`[SessionPool] Evicted idle session for chat ${chatId} (${entry.capsuleName})`);
    }
  }
}

// ============== CLI Fallback ==============

/**
 * Temporary CLI sessions used as fallback when PI mode auth fails.
 * These are separate from the main pool and are cleaned up after use.
 */
const cliFallbackSessions = new Map<number, ClaudeSession>();

/**
 * Get or create a CLI fallback session for a chat.
 * Used when PI session cannot authenticate.
 */
function getCliFallbackSession(chatId: number): ClaudeSession {
  let session = cliFallbackSessions.get(chatId);
  if (session) return session;

  const capsule = getCapsuleConfig(chatId);
  session = new ClaudeSession({
    workingDir: capsule.workingDir,
    capsuleName: capsule.name,
  });

  cliFallbackSessions.set(chatId, session);
  console.log(`[SessionPool] Created CLI fallback session for chat ${chatId}`);
  return session;
}

/**
 * Send a message through the session with automatic CLI fallback on auth errors.
 *
 * When the primary session (typically PI mode) throws an AuthError,
 * this function transparently falls back to CLI mode for that request.
 * The user sees slightly slower responses but never sees auth errors.
 *
 * Returns the response string and whether fallback was used.
 */
export async function sendWithAuthFallback(
  chatSession: ChatSession,
  message: string,
  username: string,
  userId: number,
  statusCallback: StatusCallback,
  chatId: number,
  ctx?: Context
): Promise<{ response: string; usedFallback: boolean }> {
  // If already in CLI mode, no fallback needed — but still fail fast with a
  // clear message if auth isn't available.
  if (chatSession.mode === "cli") {
    try {
      const response = await chatSession.session.sendMessageStreaming(
        message,
        username,
        userId,
        statusCallback,
        chatId,
        ctx
      );
      return { response, usedFallback: false };
    } catch (error) {
      if (error instanceof AuthError) {
        await statusCallback("tool", "🔐 Auth required — unlock Mac and run `claude setup-token`.").catch(() => {});
        return { response: error.message, usedFallback: false };
      }
      throw error;
    }
  }

  try {
    const response = await chatSession.session.sendMessageStreaming(
      message,
      username,
      userId,
      statusCallback,
      chatId,
      ctx
    );
    return { response, usedFallback: false };
  } catch (error) {
    // Only fall back on AuthError — other errors should propagate
    if (!(error instanceof AuthError)) {
      throw error;
    }

    console.warn(
      `[SessionPool] PI session auth failed: ${error.message}. Falling back to CLI mode.`
    );

    // Get or create a CLI fallback session
    const cliSession = getCliFallbackSession(chatId);

    // Notify via status callback that we're falling back
    await statusCallback("tool", "Switching to CLI mode (auth refresh pending)...").catch(() => {});

    // Copy processing state
    const stopProcessing = cliSession.startProcessing();
    try {
      const response = await cliSession.sendMessageStreaming(
        message,
        username,
        userId,
        statusCallback,
        chatId,
        ctx
      );
      // Kill the PI session so next message starts fresh
      // (the fallback conversation is not in the PI session file)
      try { await chatSession.session.kill(); } catch {}
      return { response, usedFallback: true };
    } catch (error) {
      if (error instanceof AuthError) {
        await statusCallback(
          "tool",
          "🔐 Auth required — unlock Mac and run `claude setup-token` (preferred) or `claude auth login`."
        ).catch(() => {});
        return { response: error.message, usedFallback: true };
      }
      throw error;
    } finally {
      stopProcessing();
    }
  }
}

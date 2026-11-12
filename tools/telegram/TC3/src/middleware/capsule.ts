/**
 * Capsule Middleware — Attaches per-chat session to grammY context.
 *
 * Runs before all handlers. Looks up the capsule config for the current chat
 * and creates/retrieves a session from the session pool.
 */

import type { Context, NextFunction } from "grammy";
import { getOrCreateSession, type ChatSession } from "../session-wrapper";
import type { BridgeMessageMeta } from "../types";

/**
 * Extended grammY context with per-chat capsule session.
 */
export interface CapsuleContext extends Context {
  chatSession: ChatSession;
  bridgeMessage?: BridgeMessageMeta;
}

/**
 * Middleware that attaches a per-chat session to the context.
 *
 * After this middleware runs, handlers can access:
 *   - ctx.chatSession.session  — the PiSession or ClaudeSession instance
 *   - ctx.chatSession.mode     — current mode ("pi" or "cli")
 *   - ctx.chatSession.capsuleName — display name of the capsule
 *   - ctx.chatSession.workingDir — working directory for this capsule
 */
export function capsuleMiddleware() {
  return async (ctx: CapsuleContext, next: NextFunction) => {
    const chatId = ctx.chat?.id;
    if (!chatId) {
      return next();
    }

    // Attach per-chat session to context
    ctx.chatSession = getOrCreateSession(chatId);

    return next();
  };
}

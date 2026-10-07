/**
 * Session implementation using pi-coding-agent (clawdbot-style)
 *
 * This approach:
 * 1. Reads OAuth token from Claude Code keychain
 * 2. Sets ANTHROPIC_OAUTH_TOKEN environment variable
 * 3. Uses pi-coding-agent SDK with discoverAuthStorage/discoverModels
 * 4. Uses streamSimple from pi-ai for streaming responses
 * 5. Enables tools (Read, Write, Edit, Bash, Glob, Grep, etc.)
 *
 * This achieves ~2 second response times (vs ~22 seconds with CLI mode)
 */

import fs, { readFile, access } from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import type { Context } from "grammy";
import {
  createAgentSession,
  discoverAuthStorage,
  discoverModels,
  SessionManager,
  SettingsManager,
  createCodingTools,
  createGrepTool,
  createFindTool,
  createLsTool,
  type AgentSessionEvent,
} from "@mariozechner/pi-coding-agent";
import { streamSimple } from "@mariozechner/pi-ai";
import type { Model, Api } from "@mariozechner/pi-ai";
import {
  load{{ORCHESTRATOR_NAME}}Identity,
  SAFETY_PROMPT,
  STREAMING_THROTTLE_MS,
} from "./config";
import {
  ensureValidToken,
  isExpired,
  type OAuthCredentials,
} from "./oauth-credentials";
import type { StatusCallback, TokenUsage } from "./types";

import { AuthError } from "./errors";

// Agent directory (where pi-coding-agent stores config)
const AGENT_DIR = path.join(os.homedir(), ".claude");

// Sessions directory
const SESSIONS_DIR = path.join(os.homedir(), ".clawdbot", "telegram-sessions");

// OAuth credentials cache — avoids calling into credential manager on every message.
// 25-min TTL avoids Keychain subprocess on every message; isExpired() provides
// safety net for mid-window token expiry, triggering auto-refresh via ensureValidToken().
const OAUTH_CREDS_CACHE_TTL_MS = 25 * 60 * 1000; // 25 minutes
let cachedOAuthCreds: OAuthCredentials | null = null;
let oauthCredsCacheTime = 0;

/**
 * Ensure a valid OAuth token is set in the environment.
 * Uses a module-level cache with 25-minute TTL to avoid calling the
 * credential manager (and its Keychain subprocess) on every message.
 * Also checks isExpired() on cache hit so a token that expires mid-window
 * is detected immediately rather than waiting for the TTL to elapse.
 *
 * Auto-refreshes expired tokens using ensureValidToken() instead of throwing.
 * Throws AuthError only when refresh is impossible (no creds, revoked token).
 */
async function ensureOAuthToken(): Promise<void> {
  const now = Date.now();

  // Return cached credentials if still within TTL AND not expired
  if (
    cachedOAuthCreds &&
    now - oauthCredsCacheTime < OAUTH_CREDS_CACHE_TTL_MS &&
    !isExpired(cachedOAuthCreds)
  ) {
    process.env.ANTHROPIC_OAUTH_TOKEN = cachedOAuthCreds.accessToken;
    return;
  }

  // Cache miss, TTL expired, or token expired — get valid token (auto-refreshes if needed)
  const creds = await ensureValidToken();

  // Update local cache explicitly (finding #7: two-cache architecture)
  cachedOAuthCreds = creds;
  oauthCredsCacheTime = Date.now();
  process.env.ANTHROPIC_OAUTH_TOKEN = creds.accessToken;
  console.log("[PiSession] OAuth token set from credential manager (cache refreshed)");
}

/**
 * Create a system prompt override function (as expected by pi-coding-agent)
 */
function createSystemPromptOverride(prompt: string): () => string {
  const trimmed = prompt.trim();
  return () => trimmed;
}

/**
 * Format tool status for Telegram display
 */
function formatToolStatus(toolName: string, input: Record<string, unknown>): string {
  switch (toolName) {
    case "read":
    case "Read":
      return `📖 Reading ${input.file_path || input.path || "file"}`;
    case "write":
    case "Write":
      return `✍️ Writing ${input.file_path || input.path || "file"}`;
    case "edit":
    case "Edit":
      return `📝 Editing ${input.file_path || input.path || "file"}`;
    case "bash":
    case "Bash":
      const cmd = String(input.command || "").slice(0, 50);
      return `💻 ${cmd}${String(input.command || "").length > 50 ? "..." : ""}`;
    case "glob":
    case "Glob":
      return `🔍 Glob: ${input.pattern || ""}`;
    case "grep":
    case "Grep":
      return `🔎 Grep: ${input.pattern || ""}`;
    case "find":
    case "Find":
      return `📂 Find: ${input.pattern || input.path || ""}`;
    case "ls":
    case "Ls":
      return `📁 Listing ${input.path || "."}`;
    case "Task":
      return `🤖 Spawning agent: ${input.subagent_type || input.description || ""}`;
    default:
      return `🔧 ${toolName}`;
  }
}

/**
 * PiSession - Fast session using pi-coding-agent
 * Implements the same interface as ClaudeSession for handler compatibility
 */
class PiSession {
  // Per-capsule working directory and name
  readonly workingDir: string;
  readonly capsuleName: string;

  // Session state matching ClaudeSession interface
  sessionId: string | null = null;
  lastActivity: Date | null = null;
  queryStarted: Date | null = null;
  currentTool: string | null = null;
  lastTool: string | null = null;
  lastError: string | null = null;
  lastErrorTime: Date | null = null;
  lastUsage: TokenUsage | null = null;
  lastMessage: string | null = null;
  conversationTitle: string | null = null;

  private sessionFile: string | null = null;
  private _isProcessing = false;
  private _wasInterruptedByNewMessage = false;
  private stopRequested = false;
  private currentAbortController: AbortController | null = null;

  constructor(workingDir: string, capsuleName: string = "Catalyst") {
    this.workingDir = workingDir;
    this.capsuleName = capsuleName;
  }

  get isActive(): boolean {
    return this.sessionId !== null;
  }

  get isRunning(): boolean {
    return this._isProcessing;
  }

  /**
   * Check if the last stop was triggered by a new message interrupt.
   * Resets the flag when called.
   */
  consumeInterruptFlag(): boolean {
    const was = this._wasInterruptedByNewMessage;
    this._wasInterruptedByNewMessage = false;
    if (was) {
      this.stopRequested = false;
    }
    return was;
  }

  /**
   * Mark that this stop is from a new message interrupt.
   */
  markInterrupt(): void {
    this._wasInterruptedByNewMessage = true;
  }

  /**
   * Clear the stopRequested flag.
   */
  clearStopRequested(): void {
    this.stopRequested = false;
  }

  /**
   * Mark processing as started.
   * Returns a cleanup function to call when done.
   */
  startProcessing(): () => void {
    this._isProcessing = true;
    return () => {
      this._isProcessing = false;
    };
  }

  /**
   * Stop the currently running query or mark for cancellation.
   */
  async stop(): Promise<"stopped" | "pending" | false> {
    if (this._isProcessing) {
      this.stopRequested = true;
      // Abort the current session if running
      if (this.currentAbortController) {
        this.currentAbortController.abort();
      }
      console.log("[PiSession] Stop requested");
      return "pending";
    }
    return false;
  }

  /**
   * Send a message with streaming updates via callback.
   * Uses pi-coding-agent for fast (~2s) response times with full tool support.
   */
  async sendMessageStreaming(
    message: string,
    username: string,
    userId: number,
    statusCallback: StatusCallback,
    chatId?: number,
    ctx?: Context
  ): Promise<string> {
    const stopProcessing = this.startProcessing();
    try {
      const startTime = Date.now();

      // Set chat context for ask_user MCP tool
      if (chatId) {
        process.env.TELEGRAM_CHAT_ID = String(chatId);
      }

      // Ensure OAuth token is available (throws if not)
      await ensureOAuthToken();

      const isNewSession = !this.isActive;

      // Initialize session file if needed
      if (!this.sessionFile) {
        await fs.mkdir(SESSIONS_DIR, { recursive: true });
        this.sessionId = crypto.randomUUID();
        this.sessionFile = path.join(SESSIONS_DIR, `${this.sessionId}.jsonl`);
        console.log(`[PiSession] Created session: ${this.sessionId.slice(0, 8)}...`);
      }

      // Build system prompt — always load full identity so resumed sessions
      // retain {{ORCHESTRATOR_NAME}} context (lightweight SAFETY_PROMPT caused empty responses)
      // Append capsule context so the agent knows where it's working
      const capsuleContext = `\n\n## Current Capsule\nCapsule: ${this.capsuleName}\nWorking directory: ${this.workingDir}`;
      const systemPrompt = load{{ORCHESTRATOR_NAME}}Identity() + capsuleContext;
      if (isNewSession) {
        console.log(`[PiSession] Loaded {{ORCHESTRATOR_NAME}} identity (${systemPrompt.length} chars)`);
      } else {
        console.log(`[PiSession] Resumed session with full identity (${systemPrompt.length} chars)`);
      }

      // Add date/time context for new sessions
      let messageToSend = message;
      if (isNewSession) {
        const now = new Date();
        const datePrefix = `[Current date/time: ${now.toLocaleDateString("en-US", {
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          timeZoneName: "short",
        })}]\n\n`;
        messageToSend = datePrefix + message;
      }

      console.log(`[PiSession] Processing message (${message.length} chars)`);

      // Check if stop was requested
      if (this.stopRequested) {
        console.log("[PiSession] Query cancelled before starting");
        this.stopRequested = false;
        throw new Error("Query cancelled");
      }

      this.queryStarted = new Date();

      try {
        // Discover auth and models
        const authStorage = discoverAuthStorage(AGENT_DIR);
        const modelRegistry = discoverModels(authStorage, AGENT_DIR);

        // Find Claude model
        const model = modelRegistry.find("anthropic", "claude-sonnet-4-20250514") as Model<Api> | null;
        if (!model) {
          throw new Error("Claude model not found in registry. Is Claude Code set up?");
        }

        console.log(`[PiSession] Using model: ${model.provider}/${model.id}`);

        // Create session manager
        const sessionManager = SessionManager.open(this.sessionFile!);
        const settingsManager = SettingsManager.create(this.workingDir, AGENT_DIR);

        // Create coding tools + search tools for this workspace
        const tools = [
          ...createCodingTools(this.workingDir),
          createGrepTool(this.workingDir),
          createFindTool(this.workingDir),
          createLsTool(this.workingDir),
        ];
        console.log(`[PiSession] Enabled ${tools.length} tools: ${tools.map(t => t.name).join(", ")}`);

        // Discover capsule CLAUDE.md for project context (near-zero cost)
        const contextFiles: Array<{ path: string; content: string }> = [];
        const capsuleClaudeMd = path.join(this.workingDir, "CLAUDE.md");
        try {
          await access(capsuleClaudeMd);
          const content = await readFile(capsuleClaudeMd, "utf-8");
          contextFiles.push({ path: capsuleClaudeMd, content });
          console.log(`[PiSession] Loaded capsule CLAUDE.md (${content.length} chars)`);
        } catch (err) {
          // File doesn't exist or can't be read — skip (normal for non-capsule dirs)
          if ((err as NodeJS.ErrnoException).code !== "ENOENT") {
            console.warn(`[PiSession] Failed to load capsule CLAUDE.md: ${err}`);
          }
        }

        // Create agent session with tools
        const { session: agentSession } = await createAgentSession({
          cwd: this.workingDir,
          agentDir: AGENT_DIR,
          authStorage,
          modelRegistry,
          model,
          thinkingLevel: "none",
          systemPrompt: createSystemPromptOverride(systemPrompt),
          tools: tools,
          customTools: [],
          sessionManager,
          settingsManager,
          skills: [],
          contextFiles,
        });

        if (!agentSession) {
          throw new Error("Failed to create agent session");
        }

        // Force streamSimple as the stream function (like clawdbot does)
        agentSession.agent.streamFn = streamSimple;

        const sessionCreateTime = Date.now() - startTime;
        console.log(`[PiSession] Session created in ${sessionCreateTime}ms, sending prompt...`);

        // Check for abort again before sending
        if (this.stopRequested) {
          agentSession.dispose();
          this.stopRequested = false;
          throw new Error("Query cancelled");
        }

        // Track streaming text for token-level updates to Telegram.
        // streamedText = current segment buffer (reset on tool boundaries)
        // fullResponseText = complete accumulated text across all segments (never reset)
        let streamedText = "";
        let fullResponseText = "";
        let lastStreamUpdate = 0;
        let streamSegmentId = 0;

        // Subscribe to events for tool status AND text streaming
        const unsubscribe = agentSession.subscribe((event: AgentSessionEvent) => {
          if (event.type === "message_update") {
            const assistantEvent = event.assistantMessageEvent;

            // Text delta — stream text chunks to Telegram as they arrive
            if (assistantEvent.type === "text_delta") {
              streamedText += assistantEvent.delta;
              fullResponseText += assistantEvent.delta;

              // Throttle updates to avoid Telegram rate limits
              const now = Date.now();
              if (
                now - lastStreamUpdate > STREAMING_THROTTLE_MS &&
                streamedText.length > 20
              ) {
                lastStreamUpdate = now;
                // Fire and forget - don't await
                statusCallback("text", streamedText, streamSegmentId).catch(() => {});
              }
            }

            // Tool call end — flush current text segment, show tool status
            // Note: the original code checked for "tool_use" which doesn't exist
            // in AssistantMessageEvent — the correct event is "toolcall_end"
            if (assistantEvent.type === "toolcall_end") {
              // Emit segment_end for accumulated text before tool starts
              if (streamedText) {
                statusCallback("segment_end", streamedText, streamSegmentId).catch(() => {});
                streamSegmentId++;
                streamedText = "";
                lastStreamUpdate = 0;
              }

              const toolName = assistantEvent.toolCall.name;
              const toolInput = assistantEvent.toolCall.arguments as Record<string, unknown>;

              const toolDisplay = formatToolStatus(toolName, toolInput);
              this.currentTool = toolDisplay;
              this.lastTool = toolDisplay;
              console.log(`[PiSession] Tool: ${toolDisplay}`);
              // Fire and forget - don't await
              statusCallback("tool", toolDisplay).catch(() => {});
            }
          }
        });

        // Send the prompt and wait for complete response
        const promptStart = Date.now();
        try {
          await agentSession.prompt(messageToSend);
        } finally {
          unsubscribe();
        }
        const promptTime = Date.now() - promptStart;

        // After prompt completes, flush any remaining streamed text
        if (streamedText) {
          await statusCallback("segment_end", streamedText, streamSegmentId);
        } else {
          // Fallback: extract from messages (in case streaming didn't capture text)
          const messages = agentSession.messages;
          const lastAssistant = messages
            .slice()
            .reverse()
            .find((m) => m.role === "assistant");

          let response = "";
          if (lastAssistant && "content" in lastAssistant) {
            const content = lastAssistant.content;
            if (typeof content === "string") {
              response = content;
            } else if (Array.isArray(content)) {
              response = content
                .filter((c): c is { type: "text"; text: string } => c.type === "text")
                .map((c) => c.text)
                .join("");
            }
          }

          if (response) {
            await statusCallback("segment_end", response, 0);
          }
        }
        await statusCallback("done", "");

        // Determine final response text for return value.
        // Use fullResponseText (accumulates all segments) rather than streamedText
        // (which only holds text after the last tool call).
        let finalResponse = fullResponseText;
        if (!finalResponse) {
          const messages = agentSession.messages;
          const lastAssistant = messages
            .slice()
            .reverse()
            .find((m) => m.role === "assistant");

          if (lastAssistant && "content" in lastAssistant) {
            const content = lastAssistant.content;
            if (typeof content === "string") {
              finalResponse = content;
            } else if (Array.isArray(content)) {
              finalResponse = content
                .filter((c): c is { type: "text"; text: string } => c.type === "text")
                .map((c) => c.text)
                .join("");
            }
          }
        }

        // Cleanup
        agentSession.dispose();

        const elapsed = Date.now() - startTime;
        console.log(`[PiSession] Response complete in ${elapsed}ms (prompt: ${promptTime}ms, ${(finalResponse || "").length} chars)`);

        // Update session state
        this.lastActivity = new Date();
        this.lastError = null;
        this.lastErrorTime = null;

        return finalResponse || "No response from Claude.";
      } catch (error) {
        const elapsed = Date.now() - startTime;
        console.error(`[PiSession] Error after ${elapsed}ms:`, error);
        this.lastError = String(error).slice(0, 100);
        this.lastErrorTime = new Date();
        throw error;
      } finally {
        this.queryStarted = null;
        this.currentTool = null;
      }
    } finally {
      stopProcessing();
    }
  }

  /**
   * Kill the current session.
   * @param preserveFile - If true, keep the .jsonl file for potential history replay.
   *                       Use true for crash-retry and idle eviction.
   *                       Use false (default) for explicit /new commands.
   */
  async kill(preserveFile = false): Promise<void> {
    // Clean up session file only when explicitly starting fresh
    if (this.sessionFile && !preserveFile) {
      try {
        await fs.unlink(this.sessionFile);
      } catch {
        // Ignore cleanup errors
      }
    }

    if (!preserveFile) {
      this.sessionId = null;
      this.sessionFile = null;
    }
    this.lastActivity = null;
    this.conversationTitle = null;
    console.log(`[PiSession] Session cleared (file ${preserveFile ? "preserved — resumable" : "deleted"})`);
  }

  /**
   * Reset in-memory session state while preserving the .jsonl file on disk.
   * The next message will resume from the existing session file.
   * Fire-and-forget: kill(true) is async but called without await.
   */
  resetContext(): void {
    void this.kill(true); // Preserve file for context recovery
  }

  /**
   * Get session info
   */
  getSessionInfo(): {
    sessionId: string | null;
    workingDir: string | null;
    createdAt: Date | null;
  } {
    return {
      sessionId: this.sessionId,
      workingDir: this.workingDir,
      createdAt: this.lastActivity,
    };
  }
}

export { PiSession };
export { AuthError } from "./errors";

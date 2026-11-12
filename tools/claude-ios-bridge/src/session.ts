/**
 * Session management for Claude iOS Bridge.
 *
 * Wraps Claude Agent SDK V1 with streaming support.
 * Adapted from Telegram bot session.ts.
 */

import {
  query,
  type Options,
  type SDKMessage,
} from "@anthropic-ai/claude-agent-sdk";
import { readFileSync } from "fs";
import {
  WORKING_DIR,
  MCP_SERVERS,
  SYSTEM_PROMPT,
  ALLOWED_PATHS,
  getSessionFile,
} from "./config";
import type { SessionData, TokenUsage } from "./types";

/**
 * Extract text content from SDK message.
 */
function getTextFromMessage(msg: SDKMessage): string | null {
  if (msg.type !== "assistant") return null;

  const textParts: string[] = [];
  for (const block of msg.message.content) {
    if (block.type === "text") {
      textParts.push(block.text);
    }
  }
  return textParts.length > 0 ? textParts.join("") : null;
}

export type StreamCallback = (
  type: "session" | "chunk" | "tool" | "thinking" | "done" | "error",
  content?: string,
  sessionId?: string,
  usage?: TokenUsage
) => void;

/**
 * Manages Claude Code sessions using the Agent SDK V1.
 * One session per device.
 */
export class ClaudeSession {
  sessionId: string | null = null;
  deviceId: string;
  lastActivity: Date | null = null;
  lastUsage: TokenUsage | null = null;

  private abortController: AbortController | null = null;
  private isQueryRunning = false;

  constructor(deviceId: string) {
    this.deviceId = deviceId;
  }

  get isActive(): boolean {
    return this.sessionId !== null;
  }

  get isRunning(): boolean {
    return this.isQueryRunning;
  }

  /**
   * Stop the currently running query.
   */
  async stop(): Promise<boolean> {
    if (this.isQueryRunning && this.abortController) {
      this.abortController.abort();
      console.log(`[${this.deviceId}] Stop requested - aborting query`);
      return true;
    }
    return false;
  }

  /**
   * Send a message to Claude with streaming callbacks.
   */
  async sendMessageStreaming(
    message: string,
    callback: StreamCallback,
    conversationHistory?: Array<{ role: string; content: string }>
  ): Promise<string> {
    // BLOCK: Prevent concurrent queries on same session
    if (this.isQueryRunning) {
      console.log(`[${this.deviceId}] Query already running - blocking concurrent request`);
      callback("error", "Another query is in progress. Please wait for it to complete.");
      return "Another query is in progress.";
    }

    const isNewSession = !this.isActive;

    // Inject current date/time at session start
    let messageToSend = message;
    if (isNewSession) {
      const now = new Date();
      const datePrefix = `[Current date/time: ${now.toLocaleDateString(
        "en-US",
        {
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          timeZoneName: "short",
        }
      )}]\n\n`;
      messageToSend = datePrefix + message;
    }

    // Filter out ANTHROPIC vars to force CLI auth (subscription) instead of API auth (credits)
    const filteredEnv: Record<string, string | undefined> = {};
    for (const [key, value] of Object.entries(process.env)) {
      if (!key.startsWith("ANTHROPIC_")) {
        filteredEnv[key] = value;
      }
    }

    const options: Options = {
      model: "claude-sonnet-4-5",
      cwd: WORKING_DIR,
      settingSources: ["user", "project"],
      permissionMode: "bypassPermissions",
      allowDangerouslySkipPermissions: true,
      systemPrompt: SYSTEM_PROMPT,
      mcpServers: MCP_SERVERS,
      maxThinkingTokens: 0, // Default off, can be enabled via keyword
      additionalDirectories: ALLOWED_PATHS,
      resume: this.sessionId || undefined,
      env: filteredEnv,
    };

    // Add Claude Code executable path if set
    if (process.env.CLAUDE_CODE_PATH) {
      options.pathToClaudeCodeExecutable = process.env.CLAUDE_CODE_PATH;
    }

    if (this.sessionId && !isNewSession) {
      console.log(
        `[${this.deviceId}] RESUMING session ${this.sessionId.slice(0, 8)}...`
      );
    } else {
      console.log(`[${this.deviceId}] STARTING new Claude session`);
      this.sessionId = null;
    }

    // Create abort controller for cancellation
    this.abortController = new AbortController();
    this.isQueryRunning = true;

    // Response tracking
    const responseParts: string[] = [];
    let queryCompleted = false;

    try {
      console.log(`[${this.deviceId}] 🔍 DEBUG: Creating query instance...`);
      const queryInstance = query({
        prompt: messageToSend,
        options: {
          ...options,
          abortController: this.abortController,
        },
      });
      console.log(`[${this.deviceId}] 🔍 DEBUG: Query instance created, entering for-await loop...`);

      let eventCount = 0;
      for await (const event of queryInstance) {
        eventCount++;
        console.log(`[${this.deviceId}] 🔍 DEBUG: Event #${eventCount} received, type: ${event.type}`);

        // Capture session_id from first message
        if (!this.sessionId && event.session_id) {
          this.sessionId = event.session_id;
          console.log(
            `[${this.deviceId}] GOT session_id: ${this.sessionId!.slice(0, 8)}...`
          );
          this.saveSession();
          callback("session", undefined, this.sessionId);
        }

        // Handle different message types
        if (event.type === "assistant") {
          console.log(`[${this.deviceId}] 🔍 DEBUG: Processing assistant message with ${event.message.content.length} blocks`);
          for (const block of event.message.content) {
            // Thinking blocks
            if (block.type === "thinking") {
              const thinkingText = block.thinking;
              if (thinkingText) {
                callback("thinking", thinkingText);
              }
            }

            // Tool use blocks
            if (block.type === "tool_use") {
              const toolName = block.name;
              const toolInput = block.input as Record<string, unknown>;

              // Format tool status
              let toolDisplay = toolName;
              if (toolName === "Bash" && toolInput.command) {
                const cmd = String(toolInput.command);
                toolDisplay = `Running: ${cmd.slice(0, 50)}${cmd.length > 50 ? "..." : ""}`;
              } else if (["Read", "Write", "Edit"].includes(toolName) && toolInput.file_path) {
                toolDisplay = `${toolName}: ${toolInput.file_path}`;
              }

              callback("tool", toolDisplay);
            }

            // Text content
            if (block.type === "text") {
              responseParts.push(block.text);
              callback("chunk", block.text);
            }
          }
        }

        // Result message
        if (event.type === "result") {
          console.log(`[${this.deviceId}] 🔍 DEBUG: Result event received`);
          console.log(`[${this.deviceId}] Response complete`);
          queryCompleted = true;

          // Capture usage if available
          if ("usage" in event && event.usage) {
            this.lastUsage = event.usage as TokenUsage;
            callback("done", undefined, undefined, this.lastUsage);
          } else {
            callback("done");
          }
        }
      }

      console.log(`[${this.deviceId}] 🔍 DEBUG: Exited for-await loop after ${eventCount} events`);
    } catch (error) {
      console.log(`[${this.deviceId}] 🔍 DEBUG: Exception caught in try-catch: ${error}`);
      const errorStr = String(error).toLowerCase();
      const isCleanupError =
        errorStr.includes("cancel") || errorStr.includes("abort");

      if (isCleanupError && queryCompleted) {
        console.warn(`[${this.deviceId}] Suppressed post-completion error`);
      } else {
        console.error(`[${this.deviceId}] Error in query: ${error}`);
        callback("error", String(error).slice(0, 200));
        throw error;
      }
    } finally {
      this.isQueryRunning = false;
      this.abortController = null;
    }

    this.lastActivity = new Date();
    return responseParts.join("") || "No response from Claude.";
  }

  /**
   * Clear the current session.
   */
  async kill(): Promise<void> {
    this.sessionId = null;
    this.lastActivity = null;
    console.log(`[${this.deviceId}] Session cleared`);
  }

  /**
   * Save session to disk for resume after restart.
   */
  private saveSession(): void {
    if (!this.sessionId) return;

    try {
      const data: SessionData = {
        session_id: this.sessionId,
        saved_at: new Date().toISOString(),
        working_dir: WORKING_DIR,
        device_id: this.deviceId,
      };
      Bun.write(getSessionFile(this.deviceId), JSON.stringify(data));
      console.log(`[${this.deviceId}] Session saved`);
    } catch (error) {
      console.warn(`[${this.deviceId}] Failed to save session: ${error}`);
    }
  }

  /**
   * Resume the last persisted session for this device.
   */
  resumeLast(): [success: boolean, message: string] {
    try {
      const sessionFile = getSessionFile(this.deviceId);
      const file = Bun.file(sessionFile);
      if (!file.size) {
        return [false, "No saved session found"];
      }

      const text = readFileSync(sessionFile, "utf-8");
      const data: SessionData = JSON.parse(text);

      if (!data.session_id) {
        return [false, "Saved session file is empty"];
      }

      if (data.device_id && data.device_id !== this.deviceId) {
        return [false, `Session was for different device: ${data.device_id}`];
      }

      this.sessionId = data.session_id;
      this.lastActivity = new Date();
      console.log(
        `[${this.deviceId}] Resumed session ${data.session_id.slice(0, 8)}...`
      );
      return [
        true,
        `Resumed session ${data.session_id.slice(0, 8)}... (saved at ${data.saved_at})`,
      ];
    } catch (error) {
      console.error(`[${this.deviceId}] Failed to resume session: ${error}`);
      return [false, `Failed to load session: ${error}`];
    }
  }
}

// Session store - one per device
const sessions = new Map<string, ClaudeSession>();

export function getSession(deviceId: string): ClaudeSession {
  let session = sessions.get(deviceId);
  if (!session) {
    session = new ClaudeSession(deviceId);
    sessions.set(deviceId, session);

    // Try to resume existing session
    const [success, message] = session.resumeLast();
    if (success) {
      console.log(`[${deviceId}] ${message}`);
    }
  }
  return session;
}

export function clearSession(deviceId: string): void {
  const session = sessions.get(deviceId);
  if (session) {
    session.kill();
    sessions.delete(deviceId);
  }
}

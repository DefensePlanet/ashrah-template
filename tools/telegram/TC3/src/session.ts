/**
 * Session management for Claude Telegram Bot.
 *
 * ClaudeSession class manages Claude Code sessions using the Agent SDK V1.
 * V1 supports full options (cwd, mcpServers, settingSources, etc.)
 */

import {
  query,
  type Options,
  type SDKMessage,
} from "@anthropic-ai/claude-agent-sdk";
import { readFileSync } from "fs";
import type { Context } from "grammy";
import {
  ALLOWED_PATHS,
  MCP_SERVERS,
  MODEL_CLI,
  SAFETY_PROMPT,
  STREAMING_THROTTLE_MS,
  TEMP_PATHS,
  THINKING_DEEP_KEYWORDS,
  THINKING_KEYWORDS,
  load{{ORCHESTRATOR_NAME}}Identity,
  injectSpecialistContext,
  getSpecialistHandler,
  catalystSkillLoader,
} from "./config";
import { getFilteredMCPServers } from "./mcp-lazy";
import {
  ensureValidToken,
} from "./oauth-credentials";
import { AuthError } from "./errors";
import { recordActivation } from "../../shared-core/src/telemetry.js";
import { formatToolStatus } from "./formatting";
import { checkPendingAskUserRequests } from "./handlers/streaming";
import { checkCommandSafety, isPathAllowed } from "./security";
import { SessionContext } from "./session-context";
import { SkillContextLoader } from "./skill-context-loader";
import type {
  SavedSession,
  SessionHistory,
  StatusCallback,
  TokenUsage,
} from "./types";

/**
 * Determine thinking token budget based on message keywords.
 */
function getThinkingLevel(message: string): number {
  const msgLower = message.toLowerCase();

  // Check deep thinking triggers first (more specific)
  if (THINKING_DEEP_KEYWORDS.some((k) => msgLower.includes(k))) {
    return 50000;
  }

  // Check normal thinking triggers
  if (THINKING_KEYWORDS.some((k) => msgLower.includes(k))) {
    return 10000;
  }

  // Default: no thinking
  return 0;
}

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

/**
 * Manages Claude Code sessions using the Agent SDK V1.
 */
// Maximum number of sessions to keep in history
const MAX_SESSIONS = 5;

class ClaudeSession {
  // Per-capsule configuration
  readonly workingDir: string;
  readonly capsuleName: string;
  private readonly sessionFilePath: string;

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

  // Phase 5: Session context management
  sessionContext: SessionContext = new SessionContext();
  skillLoader: SkillContextLoader = new SkillContextLoader(catalystSkillLoader);

  private abortController: AbortController | null = null;
  private isQueryRunning = false;
  private stopRequested = false;
  private _isProcessing = false;
  private _wasInterruptedByNewMessage = false;

  constructor(config: { workingDir: string; capsuleName: string }) {
    this.workingDir = config.workingDir;
    this.capsuleName = config.capsuleName;
    // Per-capsule session file to avoid collisions
    const safeName = config.capsuleName.toLowerCase().replace(/[^a-z0-9-]/g, "-");
    this.sessionFilePath = `/tmp/claude-telegram-session-${safeName}.json`;
  }

  get isActive(): boolean {
    return this.sessionId !== null;
  }

  get isRunning(): boolean {
    return this.isQueryRunning || this._isProcessing;
  }

  /**
   * Check if the last stop was triggered by a new message interrupt (! prefix).
   * Resets the flag when called. Also clears stopRequested so new messages can proceed.
   */
  consumeInterruptFlag(): boolean {
    const was = this._wasInterruptedByNewMessage;
    this._wasInterruptedByNewMessage = false;
    if (was) {
      // Clear stopRequested so the new message can proceed
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
   * Clear the stopRequested flag (used after interrupt to allow new message to proceed).
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
   * Returns: "stopped" if query was aborted, "pending" if processing will be cancelled, false if nothing running
   */
  async stop(): Promise<"stopped" | "pending" | false> {
    // If a query is actively running, abort it
    if (this.isQueryRunning && this.abortController) {
      this.stopRequested = true;
      this.abortController.abort();
      console.log("Stop requested - aborting current query");
      return "stopped";
    }

    // If processing but query not started yet
    if (this._isProcessing) {
      this.stopRequested = true;
      console.log("Stop requested - will cancel before query starts");
      return "pending";
    }

    return false;
  }

  /**
   * Send a message to Claude with streaming updates via callback.
   *
   * @param ctx - grammY context for ask_user button display
   */
  async sendMessageStreaming(
    message: string,
    username: string,
    userId: number,
    statusCallback: StatusCallback,
    chatId?: number,
    ctx?: Context
  ): Promise<string> {
    // Set chat context for ask_user MCP tool
    if (chatId) {
      process.env.TELEGRAM_CHAT_ID = String(chatId);
    }

    // Ensure OAuth token is set for the Agent SDK subprocess.
    // Auto-refreshes expired tokens. Throws AuthError only when refresh is impossible.
    const creds = await ensureValidToken();
    process.env.ANTHROPIC_OAUTH_TOKEN = creds.accessToken;

    const isNewSession = !this.isActive;
    const thinkingTokens = getThinkingLevel(message);
    const thinkingLabel =
      { 0: "off", 10000: "normal", 50000: "deep" }[thinkingTokens] ||
      String(thinkingTokens);

    // Increment message count
    this.sessionContext.incrementMessageCount();

    // Phase 5: Enhanced context management with session state
    let systemPrompt: string;

    if (isNewSession) {
      // New session: Load full {{ORCHESTRATOR_NAME}} identity
      systemPrompt = load{{ORCHESTRATOR_NAME}}Identity();
      console.log(`Loaded {{ORCHESTRATOR_NAME}} identity (${systemPrompt.length} chars)`);

      // Reset session context for new session
      this.sessionContext.reset();
    } else {
      // Resumed session: Use lightweight prompt ({{ORCHESTRATOR_NAME}} already in context)
      systemPrompt = SAFETY_PROMPT;
      console.log(`Resumed session (lightweight prompt: ${systemPrompt.length} chars)`);
    }

    // Check for specialist clear patterns
    const lower = message.toLowerCase();
    const clearPatterns = [
      "back to {{ORCHESTRATOR_NAME_LOWER}}",
      "return to {{ORCHESTRATOR_NAME_LOWER}}",
      "exit specialist",
      "clear specialist",
    ];
    const shouldClearSpecialist = clearPatterns.some((p) => lower.includes(p));

    if (shouldClearSpecialist && this.sessionContext.hasActiveSpecialist()) {
      this.sessionContext.clearSpecialist();
      console.log("🔄 Specialist cleared - returning to {{ORCHESTRATOR_NAME}} mode");
    }

    // Specialist management with session persistence + trigger classifier
    const specialistHandler = getSpecialistHandler();
    const detection = specialistHandler.detectSpecialistRequest(message);

    if (detection && !this.sessionContext.hasActiveSpecialist()) {
      const { specialist: detectedSpecialist, confidence, method } = detection;
      const activationStart = Date.now();

      // New specialist detected - load and persist
      const specialistContext = specialistHandler.loadSpecialistContext(detectedSpecialist);
      if (specialistContext) {
        this.sessionContext.setActiveSpecialist(detectedSpecialist, specialistContext);

        // Only inject specialist context on first detection (new session OR new specialist)
        if (isNewSession) {
          systemPrompt = injectSpecialistContext(systemPrompt, detectedSpecialist);
          console.log(`🎯 Specialist loaded: ${detectedSpecialist} (${confidence}, ${method}, ${systemPrompt.length} chars)`);
        } else {
          // On resumed session, add specialist indicator (full context already in session history)
          systemPrompt += `\n\n## Specialist Mode: ${detectedSpecialist}\nYou are operating with ${detectedSpecialist} expertise. Channel this specialist's knowledge when responding.\n`;
          console.log(`🎯 Specialist activated: ${detectedSpecialist} (${confidence}, ${method})`);
        }

        // Record telemetry
        try {
          recordActivation({
            source: "tc3",
            specialist: detectedSpecialist,
            confidence,
            method,
            latencyMs: Date.now() - activationStart,
            messagePreview: message,
          });
        } catch {
          // Telemetry is non-critical
        }
      }
    } else if (this.sessionContext.hasActiveSpecialist() && !isNewSession) {
      // Specialist already active - reinforce mode
      const activeSpecialist = this.sessionContext.getActiveSpecialist();
      systemPrompt += `\n\n## Specialist Mode: ${activeSpecialist}\nYou are operating with ${activeSpecialist} expertise. Channel this specialist's knowledge when responding.\n`;
      console.log(`♻️  Reusing active specialist: ${activeSpecialist}`);
    }

    // Skill loading
    const detectedSkill = this.skillLoader.detectSkillRequest(message);
    if (detectedSkill) {
      const skillContent = await this.skillLoader.loadSkillContent(detectedSkill);
      if (skillContent) {
        this.sessionContext.loadSkill(detectedSkill, skillContent);
        const skillContext = this.skillLoader.buildSkillContext(detectedSkill, skillContent);
        systemPrompt += skillContext;
        console.log(`📚 Skill loaded: ${detectedSkill} (${skillContent.length} chars)`);
      }
    }

    // Check for skill clear patterns
    const skillClearRequest = this.skillLoader.detectSkillClearRequest(message);
    if (skillClearRequest) {
      if (skillClearRequest.skillName) {
        this.sessionContext.clearSkill(skillClearRequest.skillName);
      } else {
        this.sessionContext.clearAllSkills();
      }
    }

    // Inject loaded skills context
    const skillsContext = this.sessionContext.buildSkillContext();
    if (skillsContext) {
      systemPrompt += skillsContext;
      console.log(`📚 Active skills: ${this.sessionContext.getLoadedSkills().join(", ")}`);
    }

    // Inject current date/time at session start so Claude doesn't need to call a tool for it
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

    // Build SDK V1 options - supports all features
    const options: Options = {
      model: MODEL_CLI,
      cwd: this.workingDir,
      settingSources: [], // Headless bot — no hooks, no local settings
      permissionMode: "bypassPermissions",
      allowDangerouslySkipPermissions: true,
      systemPrompt: systemPrompt, // {{ORCHESTRATOR_NAME}} identity + specialist context
      mcpServers: getFilteredMCPServers(MCP_SERVERS, getSpecialistHandler().getActive()),
      maxThinkingTokens: thinkingTokens,
      additionalDirectories: [...ALLOWED_PATHS, this.workingDir],
      resume: this.sessionId || undefined,
    };

    // Add Claude Code executable path if set (required for standalone builds)
    if (process.env.CLAUDE_CODE_PATH) {
      options.pathToClaudeCodeExecutable = process.env.CLAUDE_CODE_PATH;
    }

    if (this.sessionId && !isNewSession) {
      console.log(
        `RESUMING session ${this.sessionId.slice(
          0,
          8
        )}... (thinking=${thinkingLabel})`
      );
    } else {
      console.log(`STARTING new Claude session (thinking=${thinkingLabel})`);
      this.sessionId = null;
    }

    // Check if stop was requested during processing phase
    if (this.stopRequested) {
      console.log(
        "Query cancelled before starting (stop was requested during processing)"
      );
      this.stopRequested = false;
      throw new Error("Query cancelled");
    }

    // Create abort controller for cancellation
    this.abortController = new AbortController();
    this.isQueryRunning = true;
    this.stopRequested = false;
    this.queryStarted = new Date();
    this.currentTool = null;

    // Response tracking
    const responseParts: string[] = [];
    let currentSegmentId = 0;
    let currentSegmentText = "";
    let lastTextUpdate = 0;
    let queryCompleted = false;
    let askUserTriggered = false;

    try {
      // Use V1 query() API - supports all options including cwd, mcpServers, etc.
      const queryInstance = query({
        prompt: messageToSend,
        options: {
          ...options,
          abortController: this.abortController,
        },
      });

      // Process streaming response
      for await (const event of queryInstance) {
        // Check for abort
        if (this.stopRequested) {
          console.log("Query aborted by user");
          break;
        }

        // Capture session_id from first message
        if (!this.sessionId && event.session_id) {
          this.sessionId = event.session_id;
          console.log(`GOT session_id: ${this.sessionId!.slice(0, 8)}...`);
          this.saveSession();
        }

        // Handle different message types
        if (event.type === "assistant") {
          for (const block of event.message.content) {
            // Thinking blocks — only forward to chat when the session actually requested thinking
            if (block.type === "thinking") {
              const thinkingText = block.thinking;
              if (thinkingText) {
                console.log(`THINKING BLOCK: ${thinkingText.slice(0, 100)}...`);
                if (thinkingTokens > 0) {
                  await statusCallback("thinking", thinkingText);
                }
              }
            }

            // Tool use blocks
            if (block.type === "tool_use") {
              const toolName = block.name;
              const toolInput = block.input as Record<string, unknown>;

              // Safety check for Bash commands
              if (toolName === "Bash") {
                const command = String(toolInput.command || "");
                const [isSafe, reason] = checkCommandSafety(command);
                if (!isSafe) {
                  console.warn(`BLOCKED: ${reason}`);
                  await statusCallback("tool", `BLOCKED: ${reason}`);
                  throw new Error(`Unsafe command blocked: ${reason}`);
                }
              }

              // Safety check for file operations
              if (["Read", "Write", "Edit"].includes(toolName)) {
                const filePath = String(toolInput.file_path || "");
                if (filePath) {
                  // Allow reads from temp paths and .claude directories
                  const isTmpRead =
                    toolName === "Read" &&
                    (TEMP_PATHS.some((p) => filePath.startsWith(p)) ||
                      filePath.includes("/.claude/"));

                  if (!isTmpRead && !isPathAllowed(filePath)) {
                    console.warn(
                      `BLOCKED: File access outside allowed paths: ${filePath}`
                    );
                    await statusCallback("tool", `Access denied: ${filePath}`);
                    throw new Error(`File access blocked: ${filePath}`);
                  }
                }
              }

              // Segment ends when tool starts
              if (currentSegmentText) {
                await statusCallback(
                  "segment_end",
                  currentSegmentText,
                  currentSegmentId
                );
                currentSegmentId++;
                currentSegmentText = "";
              }

              // Format and show tool status
              const toolDisplay = formatToolStatus(toolName, toolInput);
              this.currentTool = toolDisplay;
              this.lastTool = toolDisplay;
              console.log(`Tool: ${toolDisplay}`);

              // Don't show tool status for ask_user - the buttons are self-explanatory
              if (!toolName.startsWith("mcp__ask-user")) {
                await statusCallback("tool", toolDisplay);
              }

              // Check for pending ask_user requests after ask-user MCP tool
              if (toolName.startsWith("mcp__ask-user") && ctx && chatId) {
                // Small delay to let MCP server write the file
                await new Promise((resolve) => setTimeout(resolve, 200));

                // Retry a few times in case of timing issues
                for (let attempt = 0; attempt < 3; attempt++) {
                  const buttonsSent = await checkPendingAskUserRequests(
                    ctx,
                    chatId
                  );
                  if (buttonsSent) {
                    askUserTriggered = true;
                    break;
                  }
                  if (attempt < 2) {
                    await new Promise((resolve) => setTimeout(resolve, 100));
                  }
                }
              }
            }

            // Text content
            if (block.type === "text") {
              responseParts.push(block.text);
              currentSegmentText += block.text;

              // Stream text updates (throttled)
              const now = Date.now();
              if (
                now - lastTextUpdate > STREAMING_THROTTLE_MS &&
                currentSegmentText.length > 20
              ) {
                await statusCallback(
                  "text",
                  currentSegmentText,
                  currentSegmentId
                );
                lastTextUpdate = now;
              }
            }
          }

          // Break out of event loop if ask_user was triggered
          if (askUserTriggered) {
            break;
          }
        }

        // Result message
        if (event.type === "result") {
          console.log("Response complete");
          queryCompleted = true;

          // Capture usage if available
          if ("usage" in event && event.usage) {
            this.lastUsage = event.usage as TokenUsage;
            const u = this.lastUsage;
            console.log(
              `Usage: in=${u.input_tokens} out=${u.output_tokens} cache_read=${
                u.cache_read_input_tokens || 0
              } cache_create=${u.cache_creation_input_tokens || 0}`
            );
          }
        }
      }

      // V1 query completes automatically when the generator ends
    } catch (error) {
      const errorStr = String(error).toLowerCase();
      const isCleanupError =
        errorStr.includes("cancel") || errorStr.includes("abort");

      if (
        isCleanupError &&
        (queryCompleted || askUserTriggered || this.stopRequested)
      ) {
        console.warn(`Suppressed post-completion error: ${error}`);
      } else {
        console.error(`Error in query: ${error}`);
        this.lastError = String(error).slice(0, 100);
        this.lastErrorTime = new Date();
        throw error;
      }
    } finally {
      this.isQueryRunning = false;
      this.abortController = null;
      this.queryStarted = null;
      this.currentTool = null;
    }

    this.lastActivity = new Date();
    this.lastError = null;
    this.lastErrorTime = null;

    // If ask_user was triggered, return early - user will respond via button
    if (askUserTriggered) {
      await statusCallback("done", "");
      return "[Waiting for user selection]";
    }

    // Emit final segment
    if (currentSegmentText) {
      await statusCallback("segment_end", currentSegmentText, currentSegmentId);
    }

    await statusCallback("done", "");

    return responseParts.join("") || "No response from Claude.";
  }

  /**
   * Kill the current session (clear session_id).
   * @param preserveFile - unused in ClaudeSession (no .jsonl files), included for interface
   *                       consistency with PiSession so callers can use kill(true) uniformly.
   */
  async kill(preserveFile = false): Promise<void> {
    this.sessionId = null;
    this.lastActivity = null;
    this.conversationTitle = null;
    this.sessionContext.reset(); // Phase 5: Clear session context
    console.log("Session cleared (including context)");
  }

  /**
   * Save session to disk for resume after restart.
   * Saves to multi-session history format.
   */
  saveSession(): void {
    if (!this.sessionId) return;

    try {
      // Load existing session history
      const history = this.loadSessionHistory();

      // Create new session entry
      const newSession: SavedSession = {
        session_id: this.sessionId,
        saved_at: new Date().toISOString(),
        working_dir: this.workingDir,
        title: this.conversationTitle || "Sessione senza titolo",
      };

      // Remove any existing entry with same session_id (update in place)
      const existingIndex = history.sessions.findIndex(
        (s) => s.session_id === this.sessionId
      );
      if (existingIndex !== -1) {
        history.sessions[existingIndex] = newSession;
      } else {
        // Add new session at the beginning
        history.sessions.unshift(newSession);
      }

      // Keep only the last MAX_SESSIONS
      history.sessions = history.sessions.slice(0, MAX_SESSIONS);

      // Save
      Bun.write(this.sessionFilePath, JSON.stringify(history, null, 2));
      console.log(`Session saved to ${this.sessionFilePath}`);
    } catch (error) {
      console.warn(`Failed to save session: ${error}`);
    }
  }

  /**
   * Load session history from disk.
   */
  private loadSessionHistory(): SessionHistory {
    try {
      const file = Bun.file(this.sessionFilePath);
      if (!file.size) {
        return { sessions: [] };
      }

      const text = readFileSync(this.sessionFilePath, "utf-8");
      return JSON.parse(text) as SessionHistory;
    } catch {
      return { sessions: [] };
    }
  }

  /**
   * Get list of saved sessions for display.
   */
  getSessionList(): SavedSession[] {
    const history = this.loadSessionHistory();
    // Filter to only sessions for current working directory
    return history.sessions.filter(
      (s) => !s.working_dir || s.working_dir === this.workingDir
    );
  }

  /**
   * Resume a specific session by ID.
   */
  resumeSession(sessionId: string): [success: boolean, message: string] {
    const history = this.loadSessionHistory();
    const sessionData = history.sessions.find((s) => s.session_id === sessionId);

    if (!sessionData) {
      return [false, "Sessione non trovata"];
    }

    if (sessionData.working_dir && sessionData.working_dir !== this.workingDir) {
      return [
        false,
        `Sessione per directory diversa: ${sessionData.working_dir}`,
      ];
    }

    this.sessionId = sessionData.session_id;
    this.conversationTitle = sessionData.title;
    this.lastActivity = new Date();

    console.log(
      `Resumed session ${sessionData.session_id.slice(0, 8)}... - "${sessionData.title}"`
    );

    return [
      true,
      `Ripresa sessione: "${sessionData.title}"`,
    ];
  }

  /**
   * Resume the last persisted session (legacy method, now resumes most recent).
   */
  resumeLast(): [success: boolean, message: string] {
    const sessions = this.getSessionList();
    if (sessions.length === 0) {
      return [false, "Nessuna sessione salvata"];
    }

    return this.resumeSession(sessions[0]!.session_id);
  }
}

export { ClaudeSession };

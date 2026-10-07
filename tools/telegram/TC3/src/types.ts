/**
 * Shared TypeScript types for the Claude Telegram Bot.
 */

import type { Context } from "grammy";
import type { Message } from "grammy/types";

// Status callback for streaming updates
export type StatusCallback = (
  type: "thinking" | "tool" | "text" | "segment_end" | "done",
  content: string,
  segmentId?: number
) => Promise<void>;

// Rate limit bucket for token bucket algorithm
export interface RateLimitBucket {
  tokens: number;
  lastUpdate: number;
}

// Session persistence
export interface SavedSession {
  session_id: string;
  saved_at: string;
  working_dir: string;
  title: string; // First message truncated (max ~50 chars)
}

export interface SessionHistory {
  sessions: SavedSession[];
}

// Token usage from Claude
export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens?: number;
  cache_creation_input_tokens?: number;
}

// MCP server configuration types
export type McpServerConfig = McpStdioConfig | McpHttpConfig;

export interface McpStdioConfig {
  command: string;
  args?: string[];
  env?: Record<string, string>;
}

export interface McpHttpConfig {
  type: "http";
  url: string;
  headers?: Record<string, string>;
}

// Audit log event types
export type AuditEventType =
  | "message"
  | "auth"
  | "tool_use"
  | "error"
  | "rate_limit";

export interface AuditEvent {
  timestamp: string;
  event: AuditEventType;
  user_id: number;
  username?: string;
  [key: string]: unknown;
}

// Pending media group for buffering albums
export interface PendingMediaGroup {
  items: string[];
  ctx: Context;
  caption?: string;
  statusMsg?: Message;
  timeout: Timer;
}

// Session mode
export type SessionMode = "pi" | "cli";

// Bot context with optional message
export type BotContext = Context;

// ============== Bridge Types ==============

/** Envelope embedded in bot-to-bot messages as an HTML comment. */
export interface BridgeEnvelope {
  id: string;
  from: string;
  type: "request" | "response" | "notification";
  ttl: number;
  hop: number;
  ref: string | null;
  ts: number;
  intent?: string;
}

/** Metadata attached to context by bridge middleware. */
export interface BridgeMessageMeta {
  envelope: BridgeEnvelope;
  rawPayload: string;
  sourceBot: {
    username: string;
    botId: number;
    type: string;
    displayName: string;
  };
  isResponse: boolean;
}

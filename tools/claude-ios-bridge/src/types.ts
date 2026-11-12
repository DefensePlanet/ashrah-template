/**
 * Type definitions for Claude iOS Bridge Service
 */

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

export interface SessionData {
  session_id: string;
  saved_at: string;
  working_dir: string;
  device_id: string;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens?: number;
  cache_creation_input_tokens?: number;
}

export interface SSERequest {
  content: string;
  session_id: string;
  device_id: string;
  working_directory?: string;
  conversation_history?: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
  attachments?: Array<{
    id: string;
    filename: string;
    mime_type: string;
    size: number;
    type: string;
    url: string;
  }>;
}

export interface SSEEvent {
  type: "session" | "chunk" | "content" | "complete" | "done" | "error" | "tool" | "thinking";
  content?: string;
  sessionId?: string;
  usage?: TokenUsage;
}

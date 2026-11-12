/**
 * Claude iOS Bridge Service
 *
 * Local HTTP/SSE server that connects iOS app to Claude Code via Agent SDK.
 * Provides stable, direct connection using CLI auth (subscription-based).
 *
 * Routes: iOS App -> This Bridge -> Claude Agent SDK -> Claude Code CLI
 */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { streamSSE } from "hono/streaming";
import { readFile, appendFile, stat, mkdir, writeFile } from "fs/promises";
import { existsSync } from "fs";
import { PORT, HOST, API_KEY, WORKING_DIR } from "./config";
import { getSession, clearSession } from "./session";
import type { SSERequest } from "./types";

// ============== Health Sync Configuration ==============

const HEALTH_DATA_DIR = "{{CATALYST_ROOT}}/capsules/protect-the-asset/data";
const HEALTH_METRICS_FILE = `${HEALTH_DATA_DIR}/health_metrics.jsonl`;
const SYNC_LOG_FILE = `${HEALTH_DATA_DIR}/sync_log.json`;

// Health metric types
type HealthMetricType =
  | "steps"
  | "weight"
  | "heartRate"
  | "sleep"
  | "activeCalories"
  | "workoutMinutes"
  | "restingHeartRate"
  | "hrv"
  | "respiratoryRate"
  | "bloodOxygen"
  | "bodyFat"
  | "leanBodyMass"
  | "bmi"
  | "walkingHeartRateAverage"
  | "flightsClimbed"
  | "standHours"
  | "exerciseMinutes"
  | "mindfulMinutes"
  | "waterIntake"
  | "caffeine"
  | "alcohol";

interface HealthMetric {
  type: HealthMetricType | string;
  value: number;
  unit: string;
  timestamp: string;
  source: string;
}

interface HealthSyncPushRequest {
  device_id: string;
  metrics: HealthMetric[];
  sync_timestamp: string;
}

interface StoredHealthMetric extends HealthMetric {
  device_id: string;
  received_at: string;
  sync_id: string;
}

interface SyncLogEntry {
  sync_id: string;
  device_id: string;
  direction: "push" | "pull";
  metrics_count: number;
  timestamp: string;
}

interface SyncLog {
  last_push: string | null;
  last_pull: string | null;
  total_syncs: number;
  entries: SyncLogEntry[];
}

// Initialize sync log if not exists
async function ensureSyncLog(): Promise<SyncLog> {
  try {
    if (existsSync(SYNC_LOG_FILE)) {
      const content = await readFile(SYNC_LOG_FILE, "utf-8");
      return JSON.parse(content);
    }
  } catch (e) {
    console.error("Error reading sync log:", e);
  }
  return {
    last_push: null,
    last_pull: null,
    total_syncs: 0,
    entries: [],
  };
}

async function updateSyncLog(entry: SyncLogEntry): Promise<void> {
  const log = await ensureSyncLog();
  log.entries.push(entry);
  log.total_syncs++;
  if (entry.direction === "push") {
    log.last_push = entry.timestamp;
  } else {
    log.last_pull = entry.timestamp;
  }
  // Keep only last 100 entries
  if (log.entries.length > 100) {
    log.entries = log.entries.slice(-100);
  }
  await writeFile(SYNC_LOG_FILE, JSON.stringify(log, null, 2));
}

async function countTotalMetrics(): Promise<number> {
  try {
    if (!existsSync(HEALTH_METRICS_FILE)) return 0;
    const content = await readFile(HEALTH_METRICS_FILE, "utf-8");
    return content.trim().split("\n").filter(Boolean).length;
  } catch {
    return 0;
  }
}

const app = new Hono();

// Middleware
app.use("*", logger());
app.use(
  "*",
  cors({
    origin: "*", // Allow all origins (local service)
    allowMethods: ["GET", "POST", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "X-API-Key", "Authorization"],
  })
);

// API key validation middleware
const validateApiKey = (apiKey: string | undefined): boolean => {
  if (!apiKey) return false;
  return apiKey === API_KEY;
};

// Health check
app.get("/health", (c) => {
  return c.json({
    status: "ok",
    service: "claude-ios-bridge",
    working_dir: WORKING_DIR,
    timestamp: new Date().toISOString(),
  });
});

// Status endpoint
app.get("/api/status", (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  return c.json({
    status: "ready",
    service: "claude-ios-bridge",
    working_dir: WORKING_DIR,
    timestamp: new Date().toISOString(),
  });
});

// Main SSE endpoint for Claude communication
app.post("/api/claude/sse", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  let body: SSERequest;
  try {
    body = await c.req.json<SSERequest>();
  } catch (e) {
    return c.json({ error: "Invalid JSON body" }, 400);
  }

  const { content, session_id, device_id, conversation_history, attachments } =
    body;

  if (!content || !device_id) {
    return c.json({ error: "Missing required fields: content, device_id" }, 400);
  }

  console.log(`[${device_id}] SSE request received: ${content.slice(0, 50)}...`);

  // Get or create session for this device
  const session = getSession(device_id);

  // BLOCK: Prevent concurrent queries - return HTTP 429 if query already running
  if (session.isRunning) {
    console.log(`[${device_id}] Rejecting concurrent request - query already running`);
    return c.json({
      error: "Query in progress",
      code: "CONCURRENT_REQUEST",
      message: "Previous query still running. Wait for completion or call /stop endpoint.",
    }, 429);
  }

  // Stream SSE response
  return streamSSE(c, async (stream) => {
    try {
      // Send session confirmation
      // iOS parser expects "type" field inside JSON data (ignores SSE event: line)
      if (session.sessionId) {
        await stream.writeSSE({
          data: JSON.stringify({ type: "session", session_id: session.sessionId }),
        });
      }

      // Send message and stream response
      await session.sendMessageStreaming(
        content,
        async (type, eventContent, sessionId, usage) => {
          switch (type) {
            case "session":
              await stream.writeSSE({
                data: JSON.stringify({ type: "session", session_id: sessionId }),
              });
              break;

            case "chunk":
              // iOS expects type field in JSON, not in SSE event line
              await stream.writeSSE({
                data: JSON.stringify({ type: "chunk", content: eventContent }),
              });
              break;

            case "tool":
              await stream.writeSSE({
                data: JSON.stringify({ type: "tool", content: eventContent }),
              });
              break;

            case "thinking":
              await stream.writeSSE({
                data: JSON.stringify({ type: "thinking", content: eventContent }),
              });
              break;

            case "done":
              await stream.writeSSE({
                data: JSON.stringify({
                  type: "complete",
                  status: "complete",
                  usage: usage || null,
                }),
              });
              break;

            case "error":
              await stream.writeSSE({
                data: JSON.stringify({ type: "error", content: eventContent }),
              });
              break;
          }
        },
        conversation_history
      );
    } catch (error) {
      console.error(`[${device_id}] Stream error:`, error);
      await stream.writeSSE({
        data: JSON.stringify({ type: "error", content: String(error) }),
      });
    }
  });
});

// Clear session endpoint
app.delete("/api/session/:deviceId/close", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const deviceId = c.req.param("deviceId");
  clearSession(deviceId);
  console.log(`[${deviceId}] Session cleared via API`);

  return c.json({ status: "ok", message: "Session cleared" });
});

// New session endpoint
app.post("/api/session/:deviceId/new", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const deviceId = c.req.param("deviceId");
  clearSession(deviceId);
  const session = getSession(deviceId);
  console.log(`[${deviceId}] New session created via API`);

  return c.json({
    status: "ok",
    message: "New session created",
    session_id: session.sessionId,
  });
});

// Stop current query endpoint
app.post("/api/session/:deviceId/stop", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const deviceId = c.req.param("deviceId");
  const session = getSession(deviceId);
  const stopped = await session.stop();
  console.log(`[${deviceId}] Stop requested: ${stopped ? "success" : "no query running"}`);

  return c.json({
    status: "ok",
    stopped,
    message: stopped ? "Query stopped" : "No query running",
  });
});

// Session status endpoint
app.get("/api/session/:deviceId", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const deviceId = c.req.param("deviceId");
  const session = getSession(deviceId);

  return c.json({
    device_id: deviceId,
    session_id: session.sessionId,
    is_active: session.isActive,
    is_running: session.isRunning,
    last_activity: session.lastActivity?.toISOString() || null,
    last_usage: session.lastUsage,
  });
});

// ============== Health Sync Endpoints ==============

// POST /api/health-sync/push - Phone pushes health data to capsule
app.post("/api/health-sync/push", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  let body: HealthSyncPushRequest;
  try {
    body = await c.req.json<HealthSyncPushRequest>();
  } catch (e) {
    return c.json({ error: "Invalid JSON body" }, 400);
  }

  const { device_id, metrics, sync_timestamp } = body;

  if (!device_id || !metrics || !Array.isArray(metrics)) {
    return c.json(
      { error: "Missing required fields: device_id, metrics (array)" },
      400
    );
  }

  const syncId = crypto.randomUUID();
  const receivedAt = new Date().toISOString();
  let stored = 0;

  try {
    // Ensure data directory exists
    if (!existsSync(HEALTH_DATA_DIR)) {
      await mkdir(HEALTH_DATA_DIR, { recursive: true });
    }

    // Append each metric as a JSON line
    const lines: string[] = [];
    for (const metric of metrics) {
      const storedMetric: StoredHealthMetric = {
        ...metric,
        device_id,
        received_at: receivedAt,
        sync_id: syncId,
      };
      lines.push(JSON.stringify(storedMetric));
      stored++;
    }

    if (lines.length > 0) {
      await appendFile(HEALTH_METRICS_FILE, lines.join("\n") + "\n");
    }

    // Update sync log
    await updateSyncLog({
      sync_id: syncId,
      device_id,
      direction: "push",
      metrics_count: stored,
      timestamp: receivedAt,
    });

    console.log(
      `[health-sync] Push from ${device_id}: ${stored} metrics stored (sync_id: ${syncId})`
    );

    return c.json({
      status: "ok",
      received: metrics.length,
      stored,
      sync_id: syncId,
    });
  } catch (error) {
    console.error("[health-sync] Push error:", error);
    return c.json({ error: "Failed to store metrics", details: String(error) }, 500);
  }
});

// GET /api/health-sync/pull - Phone requests data from capsule
app.get("/api/health-sync/pull", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const deviceId = c.req.query("device_id");
  const since = c.req.query("since");
  const typesParam = c.req.query("types");

  if (!deviceId) {
    return c.json({ error: "Missing required query param: device_id" }, 400);
  }

  const types = typesParam ? typesParam.split(",").map((t) => t.trim()) : null;
  const sinceDate = since ? new Date(since) : null;

  try {
    const metrics: StoredHealthMetric[] = [];

    if (existsSync(HEALTH_METRICS_FILE)) {
      const content = await readFile(HEALTH_METRICS_FILE, "utf-8");
      const lines = content.trim().split("\n").filter(Boolean);

      for (const line of lines) {
        try {
          const metric = JSON.parse(line) as StoredHealthMetric;

          // Filter by device (return metrics NOT from this device, for bidirectional sync)
          // Or return all if device wants to see its own data
          // For now, return all metrics for the device to merge

          // Filter by timestamp if provided
          if (sinceDate && new Date(metric.timestamp) <= sinceDate) {
            continue;
          }

          // Filter by types if provided
          if (types && !types.includes(metric.type)) {
            continue;
          }

          metrics.push(metric);
        } catch (parseError) {
          // Skip malformed lines
          console.warn("[health-sync] Skipping malformed line:", line);
        }
      }
    }

    const syncLog = await ensureSyncLog();

    // Update sync log for pull
    const pullTimestamp = new Date().toISOString();
    await updateSyncLog({
      sync_id: crypto.randomUUID(),
      device_id: deviceId,
      direction: "pull",
      metrics_count: metrics.length,
      timestamp: pullTimestamp,
    });

    console.log(
      `[health-sync] Pull for ${deviceId}: ${metrics.length} metrics returned`
    );

    return c.json({
      status: "ok",
      metrics,
      last_sync: syncLog.last_push,
      has_more: false, // Simple implementation - no pagination yet
    });
  } catch (error) {
    console.error("[health-sync] Pull error:", error);
    return c.json({ error: "Failed to read metrics", details: String(error) }, 500);
  }
});

// GET /api/health-sync/status - Check sync status
app.get("/api/health-sync/status", async (c) => {
  const apiKey = c.req.header("X-API-Key") || c.req.header("Authorization");
  if (!validateApiKey(apiKey)) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  try {
    const syncLog = await ensureSyncLog();
    const totalMetrics = await countTotalMetrics();

    return c.json({
      status: "ok",
      capsule_path: HEALTH_DATA_DIR,
      last_push: syncLog.last_push,
      last_pull: syncLog.last_pull,
      total_metrics: totalMetrics,
      total_syncs: syncLog.total_syncs,
    });
  } catch (error) {
    console.error("[health-sync] Status error:", error);
    return c.json({ error: "Failed to get status", details: String(error) }, 500);
  }
});

// Start server
console.log(`
====================================
Claude iOS Bridge Service
====================================
Port:         ${PORT}
Host:         ${HOST}
Working Dir:  ${WORKING_DIR}
API Key:      ${API_KEY.slice(0, 8)}...

Endpoints:
  GET  /health                    - Health check
  GET  /api/status                - Service status
  POST /api/claude/sse            - Send message (SSE stream)
  GET  /api/session/:deviceId     - Session status
  POST /api/session/:deviceId/new - Create new session
  POST /api/session/:deviceId/stop - Stop current query
  DELETE /api/session/:deviceId/close - Close session

  Health Sync:
  POST /api/health-sync/push      - Push health metrics from phone
  GET  /api/health-sync/pull      - Pull health metrics to phone
  GET  /api/health-sync/status    - Check sync status
====================================
`);

export default {
  port: PORT,
  hostname: HOST,
  fetch: app.fetch,
  // Disable idle timeout entirely for SSE streaming
  // Telegram bot has no timeout because it uses a different transport
  // Setting to 0 or undefined should disable it
  idleTimeout: 0,
};

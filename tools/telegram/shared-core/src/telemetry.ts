/**
 * Telemetry Module — Lightweight specialist usage tracking
 *
 * SQLite-based tracking for:
 * - Specialist activations (which, when, source TC2/TC3)
 * - Response latency
 * - Routing accuracy (classifier confidence)
 * - Cache hits vs misses
 */

import { Database } from "bun:sqlite";
import { join } from "node:path";

const OUTPUT_DIR = join(process.env.CATALYST_ROOT ?? "{{CATALYST_ROOT}}", "tools", "telegram", "shared-core", "output");
const DB_PATH = join(OUTPUT_DIR, "telemetry.db");

let db: Database | null = null;

/** Initialize the telemetry database */
function getDb(): Database {
  if (db) return db;

  db = new Database(DB_PATH, { create: true });

  // WAL mode for concurrent writes from TC2 + TC3
  db.exec("PRAGMA journal_mode=WAL;");

  db.exec(`
    CREATE TABLE IF NOT EXISTS activations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT NOT NULL DEFAULT (datetime('now')),
      source TEXT NOT NULL,           -- 'tc2' or 'tc3'
      specialist TEXT NOT NULL,       -- full emoji name
      confidence REAL,                -- classifier confidence (0.0-1.0)
      method TEXT,                    -- 'exact', 'keyword', 'multi', 'fallback'
      cache_hit INTEGER DEFAULT 0,    -- 1 if specialist context was cached
      latency_ms INTEGER,             -- response time in ms
      message_preview TEXT            -- first 100 chars of user message
    );

    CREATE TABLE IF NOT EXISTS daily_stats (
      date TEXT PRIMARY KEY,
      total_activations INTEGER DEFAULT 0,
      unique_specialists INTEGER DEFAULT 0,
      avg_confidence REAL DEFAULT 0,
      avg_latency_ms REAL DEFAULT 0,
      tc2_count INTEGER DEFAULT 0,
      tc3_count INTEGER DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_activations_specialist ON activations(specialist);
    CREATE INDEX IF NOT EXISTS idx_activations_source ON activations(source);
    CREATE INDEX IF NOT EXISTS idx_activations_timestamp ON activations(timestamp);
  `);

  return db;
}

/** Record a specialist activation */
export function recordActivation(event: {
  source: "tc2" | "tc3";
  specialist: string;
  confidence?: number;
  method?: string;
  cacheHit?: boolean;
  latencyMs?: number;
  messagePreview?: string;
}): void {
  try {
    const d = getDb();
    d.run(
      `INSERT INTO activations (source, specialist, confidence, method, cache_hit, latency_ms, message_preview)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        event.source,
        event.specialist,
        event.confidence ?? null,
        event.method ?? null,
        event.cacheHit ? 1 : 0,
        event.latencyMs ?? null,
        event.messagePreview?.slice(0, 100) ?? null,
      ]
    );
  } catch (err) {
    console.warn("Telemetry write failed:", err);
  }
}

/** Get summary stats for a date range */
export function getStats(days: number = 7): {
  totalActivations: number;
  uniqueSpecialists: number;
  topSpecialists: { name: string; count: number }[];
  avgConfidence: number;
  avgLatencyMs: number;
  bySource: { tc2: number; tc3: number };
  cacheHitRate: number;
} {
  const d = getDb();

  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  const cutoffStr = cutoff.toISOString();

  const total = d.query<{ count: number }, [string]>(
    "SELECT COUNT(*) as count FROM activations WHERE timestamp >= ?"
  ).get(cutoffStr);

  const unique = d.query<{ count: number }, [string]>(
    "SELECT COUNT(DISTINCT specialist) as count FROM activations WHERE timestamp >= ?"
  ).get(cutoffStr);

  const top = d.query<{ specialist: string; count: number }, [string]>(
    `SELECT specialist, COUNT(*) as count FROM activations
     WHERE timestamp >= ? GROUP BY specialist ORDER BY count DESC LIMIT 10`
  ).all(cutoffStr);

  const avgConf = d.query<{ avg: number | null }, [string]>(
    "SELECT AVG(confidence) as avg FROM activations WHERE timestamp >= ? AND confidence IS NOT NULL"
  ).get(cutoffStr);

  const avgLat = d.query<{ avg: number | null }, [string]>(
    "SELECT AVG(latency_ms) as avg FROM activations WHERE timestamp >= ? AND latency_ms IS NOT NULL"
  ).get(cutoffStr);

  const tc2Count = d.query<{ count: number }, [string, string]>(
    "SELECT COUNT(*) as count FROM activations WHERE timestamp >= ? AND source = ?"
  ).get(cutoffStr, "tc2");

  const tc3Count = d.query<{ count: number }, [string, string]>(
    "SELECT COUNT(*) as count FROM activations WHERE timestamp >= ? AND source = ?"
  ).get(cutoffStr, "tc3");

  const cacheHits = d.query<{ hits: number; total: number }, [string]>(
    `SELECT SUM(cache_hit) as hits, COUNT(*) as total
     FROM activations WHERE timestamp >= ?`
  ).get(cutoffStr);

  return {
    totalActivations: total?.count ?? 0,
    uniqueSpecialists: unique?.count ?? 0,
    topSpecialists: top.map(r => ({ name: r.specialist, count: r.count })),
    avgConfidence: Math.round((avgConf?.avg ?? 0) * 100) / 100,
    avgLatencyMs: Math.round(avgLat?.avg ?? 0),
    bySource: {
      tc2: tc2Count?.count ?? 0,
      tc3: tc3Count?.count ?? 0,
    },
    cacheHitRate: cacheHits?.total
      ? Math.round(((cacheHits.hits ?? 0) / cacheHits.total) * 100)
      : 0,
  };
}

/** Format stats as a readable report */
export function formatReport(days: number = 7): string {
  const stats = getStats(days);

  const lines = [
    `📊 Specialist Telemetry Report (last ${days} days)`,
    ``,
    `Total activations: ${stats.totalActivations}`,
    `Unique specialists: ${stats.uniqueSpecialists}`,
    `Avg confidence: ${stats.avgConfidence}`,
    `Avg latency: ${stats.avgLatencyMs}ms`,
    `Cache hit rate: ${stats.cacheHitRate}%`,
    ``,
    `By source:`,
    `  TC2 (OpenClaw): ${stats.bySource.tc2}`,
    `  TC3 ({{ORCHESTRATOR_NAME}}):   ${stats.bySource.tc3}`,
    ``,
    `Top specialists:`,
  ];

  for (const s of stats.topSpecialists) {
    lines.push(`  ${s.name}: ${s.count}`);
  }

  return lines.join("\n");
}

/** Close the database connection */
export function closeTelemetry(): void {
  if (db) {
    db.close();
    db = null;
  }
}

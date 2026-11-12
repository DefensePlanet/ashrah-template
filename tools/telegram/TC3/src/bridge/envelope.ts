/**
 * Bridge Envelope — Creation, parsing, validation, and deduplication.
 *
 * Pure functions for the bot-to-bot bridge protocol.
 * Envelopes are embedded as HTML comments in Telegram messages:
 *   <!-- BRIDGE:v1 {"id":"abc12345","from":"@{{ORCHESTRATOR_NAME}}CatalystBot",...} -->
 */

import type { BridgeEnvelope } from "../types";

// ============== Constants ==============

const BRIDGE_MARKER = "BRIDGE:v1";
const ENVELOPE_RE = /<!-- BRIDGE:v1 ({.*?}) -->/s;

// ============== Dedup State ==============

/** In-memory dedup map: messageId -> timestamp */
const seenMessages = new Map<string, number>();

/** Cleanup interval handle */
let cleanupTimer: Timer | null = null;

// ============== ID Generation ==============

/**
 * Generate a short random ID (8 hex chars).
 */
function shortId(): string {
  const bytes = new Uint8Array(4);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// ============== Envelope Functions ==============

/**
 * Create a new bridge envelope.
 */
export function createEnvelope(opts: {
  from: string;
  type: BridgeEnvelope["type"];
  ttl?: number;
  ref?: string | null;
  intent?: string;
}): BridgeEnvelope {
  return {
    id: shortId(),
    from: opts.from,
    type: opts.type,
    ttl: opts.ttl ?? 3,
    hop: 1,
    ref: opts.ref ?? null,
    ts: Date.now(),
    ...(opts.intent ? { intent: opts.intent } : {}),
  };
}

/**
 * Serialize an envelope into the HTML comment format.
 *
 * Output: `<!-- BRIDGE:v1 {"id":"abc12345",...} -->`
 */
export function serializeEnvelope(envelope: BridgeEnvelope): string {
  return `<!-- ${BRIDGE_MARKER} ${JSON.stringify(envelope)} -->`;
}

/**
 * Parse a bridge envelope from message text.
 *
 * Returns the parsed envelope and the raw payload (text without the envelope block),
 * or null if no envelope is found.
 */
export function parseEnvelope(
  text: string
): { envelope: BridgeEnvelope; payload: string } | null {
  const match = text.match(ENVELOPE_RE);
  if (!match || !match[1]) {
    return null;
  }

  try {
    const envelope = JSON.parse(match[1]) as BridgeEnvelope;

    // Basic shape validation
    if (
      typeof envelope.id !== "string" ||
      typeof envelope.from !== "string" ||
      typeof envelope.type !== "string" ||
      typeof envelope.ttl !== "number" ||
      typeof envelope.hop !== "number" ||
      typeof envelope.ts !== "number"
    ) {
      return null;
    }

    // Extract payload: everything except the envelope comment
    const payload = text.replace(ENVELOPE_RE, "").trim();

    return { envelope, payload };
  } catch {
    return null;
  }
}

/**
 * Check if a message ID has been seen recently (dedup).
 *
 * Returns true if duplicate, false if new.
 * Automatically registers the ID if new.
 */
export function isDuplicate(
  messageId: string,
  dedupWindowMs: number
): boolean {
  // Start cleanup timer on first use
  if (!cleanupTimer) {
    cleanupTimer = setInterval(() => cleanupDedup(dedupWindowMs), 60_000);
    // Allow process to exit despite the timer
    if (typeof cleanupTimer === "object" && "unref" in cleanupTimer) {
      (cleanupTimer as NodeJS.Timeout).unref();
    }
  }

  const now = Date.now();

  if (seenMessages.has(messageId)) {
    const seenAt = seenMessages.get(messageId)!;
    if (now - seenAt < dedupWindowMs) {
      return true; // duplicate
    }
  }

  // Register as seen
  seenMessages.set(messageId, now);
  return false;
}

/**
 * Check if an envelope has expired (TTL exhausted).
 */
export function isExpired(envelope: BridgeEnvelope): boolean {
  return envelope.ttl <= 0;
}

/**
 * Format an outbound bridge message.
 *
 * Format: `@targetbot payload\n\n<!-- BRIDGE:v1 {...} -->`
 */
export function formatOutboundMessage(
  targetUsername: string,
  payload: string,
  envelope: BridgeEnvelope
): string {
  const envelopeStr = serializeEnvelope(envelope);
  return `${targetUsername} ${payload}\n\n${envelopeStr}`;
}

/**
 * Create a response envelope from an inbound envelope.
 *
 * Decrements TTL, increments hop, sets type to "response",
 * and references the original envelope ID.
 */
export function createResponseEnvelope(
  inbound: BridgeEnvelope,
  selfUsername: string
): BridgeEnvelope {
  return {
    id: shortId(),
    from: selfUsername,
    type: "response",
    ttl: inbound.ttl - 1,
    hop: inbound.hop + 1,
    ref: inbound.id,
    ts: Date.now(),
  };
}

// ============== Internal Helpers ==============

/**
 * Clean up expired entries from the dedup map.
 */
function cleanupDedup(windowMs: number): void {
  const now = Date.now();
  for (const [id, ts] of seenMessages) {
    if (now - ts >= windowMs) {
      seenMessages.delete(id);
    }
  }
}

/**
 * OAuth Credential Manager for Claude Code Max Subscription
 *
 * Reads and refreshes OAuth tokens from Claude Code's credential storage:
 * - macOS Keychain (primary)
 * - ~/.claude/.credentials.json (fallback)
 *
 * Auto-refreshes expired tokens using the OAuth refresh_token grant,
 * eliminating the need to manually run `claude` in a terminal.
 */

import { execSync, spawnSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { AuthError } from "./errors";

const CLAUDE_CLI_CREDENTIALS_PATH = join(homedir(), ".claude", ".credentials.json");
const CLAUDE_CLI_KEYCHAIN_SERVICE = "Claude Code-credentials";

// OAuth refresh constants (matches Claude Code's own config)
const TOKEN_URL = "https://console.anthropic.com/v1/oauth/token";
const CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e";

export interface OAuthCredentials {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  source: "keychain" | "file";
}

// ============== Keychain Blob Cache ==============

/** Keychain blob in-memory cache to avoid spawning `security` subprocess on every call.
 *  Note: a valid but partial blob (missing claudeAiOauth) is cached for the full TTL.
 *  This is acceptable because the Keychain is stable — partial blobs are extremely rare. */
const KEYCHAIN_BLOB_CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
let keychainBlobCache: Record<string, unknown> | null = null;
let keychainBlobCacheTime = 0;

/**
 * Read the raw keychain JSON blob (full structure, not just OAuth).
 * Caches result in memory for 5 minutes to avoid spawning a subprocess on every call.
 */
function readKeychainBlob(): Record<string, unknown> | null {
  if (process.platform !== "darwin") {
    return null;
  }

  const now = Date.now();

  // Return cached blob if still within TTL
  if (keychainBlobCache && now - keychainBlobCacheTime < KEYCHAIN_BLOB_CACHE_TTL_MS) {
    return keychainBlobCache;
  }

  try {
    const result = execSync(
      `security find-generic-password -s "${CLAUDE_CLI_KEYCHAIN_SERVICE}" -w`,
      { encoding: "utf8", timeout: 5000, stdio: ["pipe", "pipe", "pipe"] }
    );
    keychainBlobCache = JSON.parse(result.trim());
    keychainBlobCacheTime = now;
    return keychainBlobCache;
  } catch {
    return null;
  }
}

// ============== Credential Reading ==============

/**
 * Read OAuth credentials from macOS Keychain
 */
function readFromKeychain(): OAuthCredentials | null {
  const data = readKeychainBlob();
  if (!data) return null;

  const claudeOauth = data?.claudeAiOauth as Record<string, unknown> | undefined;
  if (!claudeOauth || typeof claudeOauth !== "object") {
    return null;
  }

  const accessToken = claudeOauth.accessToken;
  const refreshToken = claudeOauth.refreshToken;
  const expiresAt = claudeOauth.expiresAt;

  if (typeof accessToken !== "string" || !accessToken) {
    return null;
  }
  if (typeof expiresAt !== "number" || expiresAt <= 0) {
    return null;
  }

  return {
    accessToken,
    refreshToken: (refreshToken as string) || "",
    expiresAt,
    source: "keychain",
  };
}

/**
 * Read OAuth credentials from file
 */
function readFromFile(): OAuthCredentials | null {
  if (!existsSync(CLAUDE_CLI_CREDENTIALS_PATH)) {
    return null;
  }

  try {
    const raw = readFileSync(CLAUDE_CLI_CREDENTIALS_PATH, "utf-8");
    const data = JSON.parse(raw);
    const claudeOauth = data?.claudeAiOauth;

    if (!claudeOauth || typeof claudeOauth !== "object") {
      return null;
    }

    const accessToken = claudeOauth.accessToken;
    const refreshToken = claudeOauth.refreshToken;
    const expiresAt = claudeOauth.expiresAt;

    if (typeof accessToken !== "string" || !accessToken) {
      return null;
    }
    if (typeof expiresAt !== "number" || expiresAt <= 0) {
      return null;
    }

    return {
      accessToken,
      refreshToken: refreshToken || "",
      expiresAt,
      source: "file",
    };
  } catch (error) {
    console.warn("[OAuth] Failed to read credentials file:", error);
    return null;
  }
}

/**
 * Check if credentials are expired or about to expire (within 5 minutes)
 */
export function isExpired(credentials: OAuthCredentials): boolean {
  const bufferMs = 5 * 60 * 1000; // 5 minutes buffer
  return Date.now() >= (credentials.expiresAt - bufferMs);
}

/**
 * Get OAuth credentials for Claude API
 *
 * Tries:
 * 1. macOS Keychain (most secure, updated by Claude Code)
 * 2. File fallback (~/.claude/.credentials.json)
 */
export function getOAuthCredentials(): OAuthCredentials | null {
  // Try keychain first (macOS)
  const keychainCreds = readFromKeychain();
  if (keychainCreds) return keychainCreds;

  // Fall back to file
  const fileCreds = readFromFile();
  if (fileCreds) return fileCreds;

  console.error("[OAuth] No credentials found in Keychain or file");
  return null;
}

// Cache credentials to avoid repeated keychain/file reads
let cachedCredentials: OAuthCredentials | null = null;
let cacheTime = 0;
const CACHE_TTL_MS = 60 * 1000; // 1 minute cache

/**
 * Get cached OAuth credentials (reduces keychain/file reads)
 */
export function getCachedOAuthCredentials(): OAuthCredentials | null {
  const now = Date.now();

  // Return cached if still valid
  if (cachedCredentials && (now - cacheTime) < CACHE_TTL_MS) {
    return cachedCredentials;
  }

  // Refresh cache
  cachedCredentials = getOAuthCredentials();
  cacheTime = now;

  return cachedCredentials;
}

/**
 * Clear credential cache (call after token refresh or on auth errors).
 * Also clears the keychain blob cache so the next read goes to Keychain.
 */
export function clearCredentialCache(): void {
  cachedCredentials = null;
  cacheTime = 0;
  keychainBlobCache = null;
  keychainBlobCacheTime = 0;
}

// ============== Token Refresh ==============

/**
 * Refresh the OAuth access token using the refresh token.
 *
 * Differentiates error types:
 * - 400 invalid_grant → refresh token revoked, must re-auth (non-retryable)
 * - 429 rate limited → retryable
 * - 5xx server error → retryable
 * - Network error → retryable
 */
async function refreshOAuthToken(refreshToken: string): Promise<OAuthCredentials> {
  const maxRetries = 2;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(TOKEN_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          grant_type: "refresh_token",
          client_id: CLIENT_ID,
          refresh_token: refreshToken,
          // Note: no scope field on refresh — inherits from original grant (RFC 6749 §6)
        }),
      });

      if (response.ok) {
        const data = await response.json() as {
          access_token: string;
          refresh_token?: string;
          expires_in: number;
        };

        return {
          accessToken: data.access_token,
          refreshToken: data.refresh_token || refreshToken, // may be rotated
          expiresAt: Date.now() + data.expires_in * 1000, // raw expiry — isExpired() applies its own 5-min buffer
          source: "keychain",
        };
      }

      // 400 — likely invalid_grant (revoked/expired refresh token). Non-retryable.
      if (response.status === 400) {
        const body = await response.json().catch(() => ({} as Record<string, unknown>));
        const errorCode = (body as Record<string, unknown>).error || "unknown";
        throw new AuthError(
          `Refresh token invalid (${errorCode}). Re-authenticate: run \`claude auth login\` on the Mac.`
        );
      }

      // 429 or 5xx — retryable
      if (response.status === 429 || response.status >= 500) {
        if (attempt < maxRetries) {
          const backoffMs = Math.pow(2, attempt) * 1000; // 1s, 2s
          console.warn(`[OAuth] Refresh failed (${response.status}), retrying in ${backoffMs}ms...`);
          await new Promise(resolve => setTimeout(resolve, backoffMs));
          continue;
        }
        throw new AuthError(`Token refresh failed after ${maxRetries + 1} attempts (HTTP ${response.status})`);
      }

      // Other errors — non-retryable
      throw new AuthError(`Token refresh failed: ${response.status} ${response.statusText}`);
    } catch (error) {
      if (error instanceof AuthError) throw error;

      // Network error — retry
      if (attempt < maxRetries) {
        const backoffMs = Math.pow(2, attempt) * 1000;
        console.warn(`[OAuth] Network error on refresh, retrying in ${backoffMs}ms...`, error);
        await new Promise(resolve => setTimeout(resolve, backoffMs));
        continue;
      }
      throw new AuthError(`Token refresh network error after ${maxRetries + 1} attempts: ${error}`);
    }
  }

  // Should not reach here, but TypeScript needs it
  throw new AuthError("Token refresh failed: exhausted retries");
}

/**
 * Write refreshed credentials back to Keychain.
 * Uses spawnSync with args array to prevent shell injection.
 * Non-fatal: if write fails (e.g. screen locked), the in-memory token still works.
 */
function writeToKeychain(credentials: OAuthCredentials): void {
  try {
    // Read current blob and merge — preserve scopes, subscriptionType, rateLimitTier, etc.
    const currentBlob = readKeychainBlob() || {};
    const currentOauth = (currentBlob.claudeAiOauth as Record<string, unknown>) || {};

    currentBlob.claudeAiOauth = {
      ...currentOauth,
      accessToken: credentials.accessToken,
      refreshToken: credentials.refreshToken,
      expiresAt: credentials.expiresAt,
    };

    const json = JSON.stringify(currentBlob);

    // Use spawnSync with args array — no shell, no injection risk
    const result = spawnSync(
      "security",
      [
        "add-generic-password", "-U",
        "-s", CLAUDE_CLI_KEYCHAIN_SERVICE,
        "-a", process.env.USER ?? "claude",
        "-w", json,
      ],
      { encoding: "utf8", timeout: 5000 }
    );

    if (result.status !== 0) {
      console.warn("[OAuth] Keychain write-back failed (screen locked?):", result.stderr?.trim());
      return; // Non-fatal: in-memory token still works
    }

    // Bust the blob cache so the next read sees fresh data
    keychainBlobCache = null;
    keychainBlobCacheTime = 0;

    console.log("[OAuth] ✅ Token refreshed and written to Keychain");
  } catch (err) {
    console.warn("[OAuth] Keychain write-back error (non-fatal):", err);
  }
}

// ============== Ensure Valid Token (Auto-Refresh) ==============

/** In-flight refresh Promise — deduplicates concurrent refresh calls. */
let refreshInFlight: Promise<OAuthCredentials> | null = null;

/**
 * Get a valid (non-expired) OAuth token, auto-refreshing if needed.
 *
 * This is the primary entry point for callers. It:
 * 1. Reads cached/stored credentials
 * 2. If valid, returns them immediately
 * 3. If expired, refreshes using the refresh_token grant
 * 4. Writes refreshed token back to Keychain (best-effort)
 * 5. Deduplicates concurrent refresh calls via in-flight Promise
 *
 * Throws AuthError only when refresh is impossible (no creds, no refresh token,
 * or refresh token revoked).
 */
export async function ensureValidToken(): Promise<OAuthCredentials> {
  // Try reading credentials (uses 1-minute cache)
  let creds = getCachedOAuthCredentials();

  if (!creds) {
    throw new AuthError("No OAuth credentials found. Is Claude Code authenticated?");
  }

  // If not expired, return immediately
  if (!isExpired(creds)) {
    return creds;
  }

  // Token expired — clear cache and re-read from storage in case
  // Claude Code CLI refreshed it between our cache reads
  clearCredentialCache();
  creds = getOAuthCredentials();

  if (creds && !isExpired(creds)) {
    return creds;
  }

  // Still expired — we need to refresh
  if (!creds || !creds.refreshToken) {
    throw new AuthError("Token expired and no refresh token available. Run `claude auth login` on the Mac.");
  }

  // Deduplicate concurrent refresh calls
  if (!refreshInFlight) {
    const refreshToken = creds.refreshToken;
    refreshInFlight = refreshOAuthToken(refreshToken)
      .then(newCreds => {
        writeToKeychain(newCreds);
        clearCredentialCache();
        console.log(`[OAuth] Token refreshed successfully (expires ${new Date(newCreds.expiresAt).toLocaleTimeString()})`);
        return newCreds;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }

  return refreshInFlight;
}

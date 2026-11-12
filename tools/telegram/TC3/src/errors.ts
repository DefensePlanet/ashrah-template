/** Shared error types across session implementations. */

/**
 * Authentication failure.
 *
 * Throw this when OAuth credentials are missing/expired so callers can:
 * - fall back to CLI mode (PI -> CLI)
 * - or show a clear "unlock & re-auth" message instead of hanging.
 */
export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}

/**
 * Retry getFile() once on transient Telegram API failures.
 *
 * Two attempts total with a 500ms delay between them. No exponential backoff —
 * this is intentionally simple. The caller passes a zero-argument function that
 * wraps the ctx.getFile() call so the retry logic stays generic.
 */
export async function retryGetFile<T>(fn: () => Promise<T>): Promise<T> {
  try {
    return await fn();
  } catch (firstError: unknown) {
    // Don't retry client errors (4xx except 429 Too Many Requests) — they won't resolve on retry
    if (
      firstError instanceof Error &&
      "error_code" in firstError &&
      typeof (firstError as { error_code: unknown }).error_code === "number"
    ) {
      const code = (firstError as { error_code: number }).error_code;
      if (code >= 400 && code < 500 && code !== 429) {
        throw firstError;
      }
    }

    console.debug("[retryGetFile] First attempt failed, retrying in 500ms:", firstError);
    await new Promise((resolve) => setTimeout(resolve, 500));

    try {
      return await fn();
    } catch (retryError: unknown) {
      const msg = `retryGetFile failed after 2 attempts`;
      console.debug("[retryGetFile]", msg, retryError);
      throw new Error(msg, { cause: retryError });
    }
  }
}

/**
 * Formatting module for Claude Telegram Bot.
 *
 * Markdown conversion and tool status display formatting.
 */

/**
 * Strip TTS summary tags from text.
 * These tags are meant for terminal TTS hooks, not Telegram display.
 */
export function stripTtsSummary(text: string): string {
  // Remove <tts-summary>...</tts-summary> tags and their content
  return text.replace(/<tts-summary>[\s\S]*?<\/tts-summary>/gi, "").trim();
}

/**
 * Escape HTML special characters.
 */
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Convert standard markdown to Telegram-compatible HTML.
 *
 * HTML is more reliable than Telegram's Markdown which breaks on special chars.
 * Telegram HTML supports: <b>, <i>, <code>, <pre>, <a href="">
 *
 * Uses a placeholder-based approach to protect code blocks from processing,
 * then converts markdown patterns in the remaining text.
 * Fallback: retryEditOnRateLimit in streaming.ts catches `can't parse entities`
 * and falls back to stripHtmlTags plain text automatically.
 */
export function convertMarkdownToHtml(text: string): string {
  // Step 1: Extract code blocks and protect from processing
  const codeBlocks: string[] = [];
  let processed = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, _lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(escapeHtml((code as string).trimEnd()));
    return `\x00CB${idx}\x00`;
  });

  // Step 2: Extract inline code
  const inlineCodes: string[] = [];
  processed = processed.replace(/`([^`\n]+)`/g, (_match, code) => {
    const idx = inlineCodes.length;
    inlineCodes.push(escapeHtml(code as string));
    return `\x00IC${idx}\x00`;
  });

  // Step 2.5: Extract spoiler syntax ||text|| into placeholders.
  // Must run AFTER code block extraction (so spoilers inside code are preserved
  // literally) and BEFORE escapeHtml (so the | chars aren't mangled and the
  // injected <tg-spoiler> tags aren't escaped). Content is HTML-escaped at
  // extraction time, then the placeholder is restored after escapeHtml.
  // Non-greedy, single-line only — no multiline spoilers.
  const spoilers: string[] = [];
  processed = processed.replace(/\|\|(.+?)\|\|/g, (_match, inner) => {
    const idx = spoilers.length;
    spoilers.push(escapeHtml(inner as string));
    return `\x00SP${idx}\x00`;
  });

  // Step 3: Escape HTML in remaining text
  processed = escapeHtml(processed);

  // Step 4: Convert markdown patterns

  // Headers (## text → bold)
  processed = processed.replace(/^#{1,6}\s+(.+)$/gm, '<b>$1</b>');

  // Bold (**text**)
  processed = processed.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

  // Strikethrough (~~text~~)
  processed = processed.replace(/~~(.+?)~~/g, '<s>$1</s>');

  // Links [text](url) — restrict to http/https URLs to avoid matching file paths
  processed = processed.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    '<a href="$2">$1</a>'
  );

  // Blockquotes (&gt; text) — must come after escapeHtml since > becomes &gt;
  processed = convertBlockquotesInline(processed);

  // Step 5: Restore spoilers → <tg-spoiler> (content already HTML-escaped at extraction)
  processed = processed.replace(/\x00SP(\d+)\x00/g, (_match, idx) => {
    return `<tg-spoiler>${spoilers[Number(idx)]}</tg-spoiler>`;
  });

  // Step 6: Restore inline code → <code>
  processed = processed.replace(/\x00IC(\d+)\x00/g, (_match, idx) => {
    return `<code>${inlineCodes[Number(idx)]}</code>`;
  });

  // Step 7: Restore code blocks → <pre>
  processed = processed.replace(/\x00CB(\d+)\x00/g, (_match, idx) => {
    return `<pre>${codeBlocks[Number(idx)]}</pre>`;
  });

  // Collapse excessive newlines
  processed = processed.replace(/\n{3,}/g, '\n\n');

  return processed;
}

/**
 * Convert blockquotes inline (handles multi-line).
 * Operates on already-HTML-escaped text where > has become &gt;
 */
function convertBlockquotesInline(text: string): string {
  const lines = text.split('\n');
  const result: string[] = [];
  let inBlockquote = false;
  const blockquoteLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('&gt; ') || line === '&gt;') {
      const content = line === '&gt;' ? '' : line.slice(5);
      blockquoteLines.push(content);
      inBlockquote = true;
    } else {
      if (inBlockquote) {
        result.push('<blockquote>' + blockquoteLines.join('\n') + '</blockquote>');
        blockquoteLines.length = 0;
        inBlockquote = false;
      }
      result.push(line);
    }
  }

  if (inBlockquote) {
    result.push('<blockquote>' + blockquoteLines.join('\n') + '</blockquote>');
  }

  return result.join('\n');
}

/**
 * Strip all HTML tags and decode entities back to plain text.
 * Used when HTML send/edit fails and we need a clean plaintext fallback.
 */
export function stripHtmlTags(text: string): string {
  return text
    .replace(/<\/?[^>]+(>|$)/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&"); // &amp; must be last to avoid double-decode
}

/**
 * Convert markdown to HTML and ensure it fits within Telegram's message limit.
 *
 * HTML tags (<b>, <blockquote>, &amp; entities) inflate text beyond the raw
 * markdown length. Truncating raw markdown at 4000 chars can exceed 4096 after
 * conversion. This function converts first, checks length, and proportionally
 * shrinks if over limit.
 */
export function formatWithinLimit(rawMarkdown: string, limit = 4000): string {
  const html = convertMarkdownToHtml(rawMarkdown);
  if (html.length <= limit) return html;

  // Estimate scale factor: how much HTML inflates vs raw markdown
  const scaleFactor = rawMarkdown.length / html.length;
  const targetRawLength = Math.floor(limit * scaleFactor);
  const trimmed = rawMarkdown.slice(0, targetRawLength);
  const result = convertMarkdownToHtml(trimmed);

  // Strip any incomplete trailing HTML tag (e.g. "<blockqu" from mid-tag truncation)
  const safe = result.replace(/<[^>]*$/, "");

  // Second pass: if re-conversion still exceeds limit, hard-truncate the HTML output directly
  if (safe.length + 3 > limit) {
    const hardTruncated = safe.slice(0, limit - 3);
    return hardTruncated.replace(/<[^>]*$/, "") + "...";
  }
  return safe + "...";
}

// Legacy alias
export const convertMarkdownForTelegram = convertMarkdownToHtml;

// ============== Tool Status Formatting ==============

/**
 * Known Catalyst tools — maps command path fragments to friendly names.
 * Used by formatToolStatus to show rich status for Bash commands that invoke Catalyst tools.
 */
const CATALYST_TOOLS: ReadonlyArray<{
  pattern: string;
  name: string;
  emoji: string;
}> = [
  { pattern: "tools/product-sourcing/", name: "Product Sourcing", emoji: "🛍️" },
  { pattern: "tools/youtube-intel/", name: "YouTube Intel", emoji: "📊" },
  { pattern: "tools/tiktok.py", name: "TikTok", emoji: "🎵" },
  { pattern: "tools/canva_api", name: "Canva", emoji: "🎨" },
  { pattern: "tools/media-engine/", name: "Media Engine", emoji: "🎬" },
  { pattern: "tools/apple_provision", name: "Apple Provision", emoji: "🍎" },
  { pattern: "tools/obs_cli", name: "OBS Studio", emoji: "📹" },
  { pattern: "tools/davinci_resolve", name: "DaVinci Resolve", emoji: "🎞️" },
  { pattern: "tools/proton_mail", name: "Proton Mail", emoji: "📧" },
  { pattern: "tools/file-organizer/", name: "File Organizer", emoji: "📁" },
  { pattern: "tools/voice-pipeline/", name: "Voice Pipeline", emoji: "🎤" },
  { pattern: "tools/yt-transcript", name: "YouTube Transcript", emoji: "📝" },
  { pattern: "tools/mac-maintenance", name: "Mac Maintenance", emoji: "🧹" },
  { pattern: "tools/bridgehub/", name: "BridgeHub", emoji: "🌉" },
  { pattern: "tools/telegram/", name: "Telegram Tools", emoji: "📱" },
  { pattern: "gitnexus", name: "GitNexus", emoji: "🔗" },
];

/**
 * Shorten a file path for display (last 2 components).
 */
function shortenPath(path: string): string {
  if (!path) return "file";
  const parts = path.split("/");
  if (parts.length >= 2) {
    return parts.slice(-2).join("/");
  }
  return parts[parts.length - 1] || path;
}

/**
 * Truncate text with ellipsis.
 */
function truncate(text: string, maxLen = 60): string {
  if (!text) return "";
  // Clean up newlines for display
  const cleaned = text.replace(/\n/g, " ").trim();
  if (cleaned.length <= maxLen) return cleaned;
  return cleaned.slice(0, maxLen) + "...";
}

/**
 * Wrap text in HTML code tags, escaping special chars.
 */
function code(text: string): string {
  return `<code>${escapeHtml(text)}</code>`;
}

/**
 * Format tool use for display in Telegram with HTML formatting.
 */
export function formatToolStatus(
  toolName: string,
  toolInput: Record<string, unknown>
): string {
  const emojiMap: Record<string, string> = {
    Read: "📖",
    Write: "📝",
    Edit: "✏️",
    Bash: "▶️",
    Glob: "🔍",
    Grep: "🔎",
    WebSearch: "🔍",
    WebFetch: "🌐",
    Task: "🎯",
    TodoWrite: "📋",
    mcp__: "🔧",
  };

  // Find matching emoji
  let emoji = "🔧";
  for (const [key, val] of Object.entries(emojiMap)) {
    if (toolName.includes(key)) {
      emoji = val;
      break;
    }
  }

  // Format based on tool type
  if (toolName === "Read") {
    const filePath = String(toolInput.file_path || "file");
    const shortPath = shortenPath(filePath);
    const imageExtensions = [
      ".jpg",
      ".jpeg",
      ".png",
      ".gif",
      ".webp",
      ".bmp",
      ".svg",
      ".ico",
    ];
    if (imageExtensions.some((ext) => filePath.toLowerCase().endsWith(ext))) {
      return "👀 Viewing";
    }
    return `${emoji} Reading ${code(shortPath)}`;
  }

  if (toolName === "Write") {
    const filePath = String(toolInput.file_path || "file");
    return `${emoji} Writing ${code(shortenPath(filePath))}`;
  }

  if (toolName === "Edit") {
    const filePath = String(toolInput.file_path || "file");
    return `${emoji} Editing ${code(shortenPath(filePath))}`;
  }

  if (toolName === "Bash") {
    const cmd = String(toolInput.command || "");
    const desc = String(toolInput.description || "");

    // Detect known Catalyst tools by command path
    const catalystTool = CATALYST_TOOLS.find((t) => cmd.includes(t.pattern));
    if (catalystTool) {
      if (desc) {
        return `${catalystTool.emoji} <b>${escapeHtml(catalystTool.name)}</b>: ${escapeHtml(truncate(desc, 60))}`;
      }
      // Extract the part of the command after the tool pattern as a subcommand hint
      const idx = cmd.indexOf(catalystTool.pattern);
      const afterPattern = cmd.slice(idx + catalystTool.pattern.length);
      const subcommand = afterPattern.replace(/^\S*\s*/, "").trim(); // skip script filename, keep args
      if (subcommand) {
        return `${catalystTool.emoji} <b>${escapeHtml(catalystTool.name)}</b>: ${code(truncate(subcommand, 50))}`;
      }
      return `${catalystTool.emoji} <b>${escapeHtml(catalystTool.name)}</b>`;
    }

    if (desc) {
      return `${emoji} ${escapeHtml(desc)}`;
    }
    return `${emoji} ${code(truncate(cmd, 50))}`;
  }

  if (toolName === "Grep") {
    const pattern = String(toolInput.pattern || "");
    const path = String(toolInput.path || "");
    if (path) {
      return `${emoji} Searching ${code(truncate(pattern, 30))} in ${code(
        shortenPath(path)
      )}`;
    }
    return `${emoji} Searching ${code(truncate(pattern, 40))}`;
  }

  if (toolName === "Glob") {
    const pattern = String(toolInput.pattern || "");
    return `${emoji} Finding ${code(truncate(pattern, 50))}`;
  }

  if (toolName === "WebSearch") {
    const query = String(toolInput.query || "");
    return `${emoji} Searching: ${escapeHtml(truncate(query, 50))}`;
  }

  if (toolName === "WebFetch") {
    const url = String(toolInput.url || "");
    return `${emoji} Fetching ${code(truncate(url, 50))}`;
  }

  if (toolName === "Task") {
    const agentName = String(toolInput.subagent_type || "");
    const desc = String(toolInput.description || "");
    if (agentName && desc) {
      return `<b>${escapeHtml(agentName)}</b> is working on: ${escapeHtml(truncate(desc, 60))}`;
    }
    if (agentName) {
      return `<b>${escapeHtml(agentName)}</b> is working...`;
    }
    if (desc) {
      return `🤖 Agent is working on: ${escapeHtml(truncate(desc, 60))}`;
    }
    return `🤖 Agent is working...`;
  }

  if (toolName === "Skill") {
    const skillName = String(toolInput.skill || "");
    if (skillName) {
      return `💭 Using skill: ${escapeHtml(skillName)}`;
    }
    return `💭 Using skill...`;
  }

  if (toolName.startsWith("mcp__")) {
    // Generic MCP tool formatting
    const parts = toolName.split("__");
    if (parts.length >= 3) {
      const server = parts[1]!;
      let action = parts[2]!;
      // Remove redundant server prefix from action
      if (action.startsWith(`${server}_`)) {
        action = action.slice(server.length + 1);
      }
      action = action.replace(/_/g, " ");

      // Try to get meaningful summary
      const summary =
        toolInput.title ||
        toolInput.query ||
        toolInput.content ||
        toolInput.text ||
        toolInput.id ||
        "";

      if (summary) {
        return `🔧 ${server} ${action}: ${escapeHtml(
          truncate(String(summary), 40)
        )}`;
      }
      return `🔧 ${server}: ${action}`;
    }
    return `🔧 ${escapeHtml(toolName)}`;
  }

  return `${emoji} ${escapeHtml(toolName)}`;
}

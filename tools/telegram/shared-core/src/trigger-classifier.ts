/**
 * Trigger Classifier — Hybrid rules + keyword specialist routing
 *
 * Determines which specialist should handle a message using a fast,
 * pre-LLM gate. Used by both TC2 (OpenClaw) and TC3 ({{ORCHESTRATOR_NAME}} Hybrid).
 *
 * Three-tier matching:
 *   1. Exact mention — user explicitly names a specialist
 *   2. Keyword match — domain keywords map to specialists
 *   3. Fallback — no match, let {{ORCHESTRATOR_NAME}} handle it
 */

export interface ClassifierResult {
  specialist: string | null;
  confidence: number;      // 0.0 - 1.0
  method: "exact" | "keyword" | "multi" | "fallback";
  /** All candidates with scores (for disambiguation) */
  candidates: { name: string; score: number }[];
}

/** Keyword-to-specialist mapping with weights */
interface KeywordRule {
  keywords: string[];
  specialist: string;
  weight: number; // Higher = stronger signal
}

/**
 * Keyword rules derived from the capability routing table.
 * Ordered by specificity (more specific first).
 */
const KEYWORD_RULES: KeywordRule[] = [
  // Engineering — high specificity
  { keywords: ["supabase", "postgresql", "postgres", "migration", "rls", "row level"], specialist: "🏛️ Backend Developer", weight: 0.9 },
  { keywords: ["api endpoint", "rest api", "graphql", "backend", "server-side"], specialist: "🏛️ Backend Developer", weight: 0.85 },
  { keywords: ["cloudflare", "workers", "pages", "r2", "d1", "dns"], specialist: "🏛️ Backend Developer", weight: 0.9 },
  { keywords: ["deployment", "deploy", "ci/cd", "vercel", "netlify"], specialist: "🏛️ Backend Developer", weight: 0.8 },
  { keywords: ["database", "schema", "table", "query", "sql"], specialist: "🏛️ Backend Developer", weight: 0.75 },

  { keywords: ["react component", "next.js", "nextjs", "shadcn", "tailwind css"], specialist: "🎨 Frontend Developer", weight: 0.9 },
  { keywords: ["css", "styling", "animation", "framer motion", "web ui"], specialist: "🎨 Frontend Developer", weight: 0.8 },
  { keywords: ["accessibility", "a11y", "aria", "screen reader"], specialist: "🎨 Frontend Developer", weight: 0.85 },
  { keywords: ["react", "jsx", "tsx", "hook", "state management", "zustand", "redux"], specialist: "🎨 Frontend Developer", weight: 0.75 },

  { keywords: ["swift", "swiftui", "ios app", "xcode", "app store"], specialist: "📱 Mobile Developer", weight: 0.9 },
  { keywords: ["react native", "expo", "mobile app", "simulator"], specialist: "📱 Mobile Developer", weight: 0.85 },
  { keywords: ["ios", "iphone", "ipad"], specialist: "📱 Mobile Developer", weight: 0.7 },

  { keywords: ["macos app", "appkit", "mac app", "menubar", "dock"], specialist: "💻 macOS Dev", weight: 0.9 },

  { keywords: ["shopify", "liquid", "storefront", "e-commerce", "ecommerce"], specialist: "🛒 Shopify Exec", weight: 0.9 },

  { keywords: ["mcp server", "mcp tool", "model context protocol", "transport layer"], specialist: "🏄🏼‍♂️ MCP Server Dude", weight: 0.95 },

  // Creative
  { keywords: ["logo", "vector", "svg", "infographic", "brand asset", "icon design"], specialist: "🎨 Graphic Designer", weight: 0.9 },
  { keywords: ["graphic design", "template", "layout", "social media design"], specialist: "🎨 Graphic Designer", weight: 0.85 },

  { keywords: ["photo", "photorealistic", "product photography", "sora", "veo"], specialist: "📸 Camera Man", weight: 0.9 },
  { keywords: ["ai image", "image generation", "gemini image", "video generation"], specialist: "📸 Camera Man", weight: 0.85 },
  { keywords: ["upscale", "real-esrgan", "image to video"], specialist: "📸 Camera Man", weight: 0.8 },

  { keywords: ["wireframe", "prototype", "mockup", "user flow", "design system"], specialist: "📐 UI Designer", weight: 0.9 },
  { keywords: ["ux", "user experience", "user research", "figma"], specialist: "📐 UI Designer", weight: 0.85 },

  { keywords: ["obs", "obs studio", "davinci resolve", "streaming", "recording"], specialist: "🎬 Studio Engineer", weight: 0.9 },
  { keywords: ["video editing", "color grading", "lut"], specialist: "🎬 Studio Engineer", weight: 0.85 },

  { keywords: ["blender", "3d model", "3d render", "procedural", "mesh"], specialist: "🧊 3D Developer", weight: 0.9 },

  // Business
  { keywords: ["meta ads", "google ads", "facebook ads", "ad campaign", "roas"], specialist: "📣 Chief Marketing Officer", weight: 0.9 },
  { keywords: ["marketing", "content strategy", "email campaign", "social media"], specialist: "📣 Chief Marketing Officer", weight: 0.8 },
  { keywords: ["copywriting", "copy", "headline", "cta"], specialist: "📣 Chief Marketing Officer", weight: 0.75 },

  { keywords: ["kpi", "revenue", "metrics", "cohort", "growth rate", "churn"], specialist: "📊 Business Analyst", weight: 0.9 },
  { keywords: ["business metric", "investor report", "data analysis"], specialist: "📊 Business Analyst", weight: 0.85 },

  { keywords: ["product roadmap", "feature prioritization", "go-to-market", "gtm"], specialist: "🎯 Product Strategist", weight: 0.9 },
  { keywords: ["product strategy", "positioning", "competitive analysis"], specialist: "🎯 Product Strategist", weight: 0.85 },

  { keywords: ["validate idea", "market research", "lean startup", "customer discovery"], specialist: "🧭 Venture Analyst", weight: 0.9 },
  { keywords: ["business model", "tam", "sam", "som", "go/no-go"], specialist: "🧭 Venture Analyst", weight: 0.85 },

  { keywords: ["brand guideline", "brand consistency", "visual identity", "tone of voice"], specialist: "🎯 Brand Specialist", weight: 0.9 },

  { keywords: ["seo", "meta tag", "search ranking", "core web vitals", "lighthouse"], specialist: "🔍 SEO Analyzer", weight: 0.9 },
  { keywords: ["sitemap", "robots.txt", "structured data", "schema.org"], specialist: "🔍 SEO Analyzer", weight: 0.85 },

  // Quality
  { keywords: ["code review", "review this", "check this code", "pr review"], specialist: "🧐 Code Reviewer", weight: 0.9 },
  { keywords: ["code quality", "best practice", "maintainability"], specialist: "🧐 Code Reviewer", weight: 0.8 },

  { keywords: ["debug", "bug", "error", "crash", "stack trace", "root cause"], specialist: "👾 Debugger", weight: 0.85 },
  { keywords: ["broken", "not working", "fails", "exception"], specialist: "👾 Debugger", weight: 0.7 },

  { keywords: ["test", "e2e", "playwright test", "unit test", "integration test"], specialist: "🧪 Validator", weight: 0.85 },
  { keywords: ["visual regression", "snapshot", "test coverage"], specialist: "🧪 Validator", weight: 0.8 },

  { keywords: ["security audit", "owasp", "vulnerability", "penetration test", "pentest"], specialist: "🛡️ Security Analyst", weight: 0.9 },
  { keywords: ["threat model", "cve", "xss", "sql injection", "csrf"], specialist: "🛡️ Security Analyst", weight: 0.85 },

  // Research
  { keywords: ["research", "investigate", "find out", "look into", "deep dive"], specialist: "🔍 Research Agent", weight: 0.7 },
  { keywords: ["academic", "citation", "source", "literature"], specialist: "🔍 Research Agent", weight: 0.8 },

  { keywords: ["ai model", "hugging face", "transformer", "fine-tune", "inference"], specialist: "🤓 AI Nerd", weight: 0.9 },
  { keywords: ["llm", "embedding", "rag", "vector database"], specialist: "🤓 AI Nerd", weight: 0.85 },

  { keywords: ["obsidian", "apple notes", "pkm", "knowledge graph", "second brain"], specialist: "🧠 2nd Brain Wizard", weight: 0.9 },
  { keywords: ["goodreader", "photo library", "osxphotos", "vault"], specialist: "🧠 2nd Brain Wizard", weight: 0.85 },

  { keywords: ["algorithm", "data structure", "leetcode", "dynamic programming", "graph algorithm"], specialist: "🧮 Algo Wizard", weight: 0.9 },
  { keywords: ["complexity", "big-o", "optimization problem", "binary search"], specialist: "🧮 Algo Wizard", weight: 0.85 },

  // Operations
  { keywords: ["n8n", "workflow automation", "launchagent", "cron", "scheduled task"], specialist: "🤖 Automator", weight: 0.9 },
  { keywords: ["automate", "automation", "shortcut", "applescript"], specialist: "🤖 Automator", weight: 0.75 },

  { keywords: ["scrape", "scraping", "playwright", "headless browser", "account creation"], specialist: "🐲 Bowser", weight: 0.85 },
  { keywords: ["anti-detection", "captcha", "bot detection"], specialist: "🐲 Bowser", weight: 0.9 },

  { keywords: ["smart contract", "solidity", "ethereum", "web3", "blockchain", "nft"], specialist: "⛓️ Blockchain Agent", weight: 0.9 },
  { keywords: ["wallet", "defi", "dapp"], specialist: "⛓️ Blockchain Agent", weight: 0.8 },
];

/** Exact specialist name mentions (case-insensitive) */
/**
 * Exact specialist name aliases — ONLY true agent names/aliases belong here.
 * Generic domain words (marketing, seo, shopify, blockchain, etc.) belong
 * in KEYWORD_RULES where they score proportionally instead of 0.95.
 */
const EXACT_NAMES: Record<string, string> = {
  "backend dev": "🏛️ Backend Developer",
  "backend developer": "🏛️ Backend Developer",
  "frontend dev": "🎨 Frontend Developer",
  "frontend developer": "🎨 Frontend Developer",
  "mobile dev": "📱 Mobile Developer",
  "mobile developer": "📱 Mobile Developer",
  "macos dev": "💻 macOS Dev",
  "shopify exec": "🛒 Shopify Exec",
  "mcp server dude": "🏄🏼‍♂️ MCP Server Dude",
  "graphic designer": "🎨 Graphic Designer",
  "camera man": "📸 Camera Man",
  "ui designer": "📐 UI Designer",
  "studio engineer": "🎬 Studio Engineer",
  "3d developer": "🧊 3D Developer",
  "3d dev": "🧊 3D Developer",
  "cmo": "📣 Chief Marketing Officer",
  "business analyst": "📊 Business Analyst",
  "product strategist": "🎯 Product Strategist",
  "venture analyst": "🧭 Venture Analyst",
  "brand specialist": "🎯 Brand Specialist",
  "seo analyzer": "🔍 SEO Analyzer",
  "code reviewer": "🧐 Code Reviewer",
  "security analyst": "🛡️ Security Analyst",
  "research agent": "🔍 Research Agent",
  "ai nerd": "🤓 AI Nerd",
  "2nd brain wizard": "🧠 2nd Brain Wizard",
  "brain wizard": "🧠 2nd Brain Wizard",
  "algo wizard": "🧮 Algo Wizard",
  "blockchain agent": "⛓️ Blockchain Agent",
  "system architect": "🏗️ System Architect",
};

/** Escape special regex characters in a string */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Pre-compiled word-boundary regexes for every EXACT_NAMES entry.
 * Built once at module load — avoids constructing and GC-ing
 * a new RegExp per entry on every classifyMessage() / hasSpecialistSignal() call.
 */
const EXACT_NAME_PATTERNS: Map<string, RegExp> = new Map(
  Object.entries(EXACT_NAMES).map(([name]) => [
    name,
    new RegExp(`\\b${escapeRegex(name)}\\b`, "i"),
  ])
);

/**
 * Classify a message to determine which specialist should handle it.
 *
 * @param message - User's message text
 * @returns Classification result with specialist, confidence, and method
 */
export function classifyMessage(message: string): ClassifierResult {
  const lower = message.toLowerCase();

  // Tier 1: Exact name mention (pre-compiled word-boundary regexes)
  for (const [name, specialist] of Object.entries(EXACT_NAMES)) {
    const pattern = EXACT_NAME_PATTERNS.get(name)!;
    if (pattern.test(message)) {
      return {
        specialist,
        confidence: 0.95,
        method: "exact",
        candidates: [{ name: specialist, score: 0.95 }],
      };
    }
  }

  // Tier 2: Keyword matching — score all rules
  const scores: Map<string, number> = new Map();

  for (const rule of KEYWORD_RULES) {
    let matchCount = 0;
    for (const kw of rule.keywords) {
      if (lower.includes(kw)) {
        matchCount++;
      }
    }

    if (matchCount > 0) {
      // Score = weight * (base floor + coverage bonus)
      // A single keyword match from a high-weight rule should score ~0.72
      // Multiple matches push toward the full weight
      const coverage = matchCount / rule.keywords.length;
      const score = rule.weight * (0.75 + 0.25 * coverage);

      const existing = scores.get(rule.specialist) ?? 0;
      scores.set(rule.specialist, Math.max(existing, score));
    }
  }

  if (scores.size > 0) {
    // Sort by score descending
    const sorted = Array.from(scores.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([name, score]) => ({ name, score: Math.round(score * 100) / 100 }));

    const top = sorted[0];
    const runner = sorted[1];

    // Check if top match is clearly ahead
    if (runner && top.score - runner.score < 0.15) {
      // Ambiguous — multiple close candidates
      return {
        specialist: top.name,
        confidence: top.score * 0.8, // Penalize ambiguity
        method: "multi",
        candidates: sorted.slice(0, 3),
      };
    }

    return {
      specialist: top.name,
      confidence: top.score,
      method: "keyword",
      candidates: sorted.slice(0, 3),
    };
  }

  // Tier 3: No match
  return {
    specialist: null,
    confidence: 0,
    method: "fallback",
    candidates: [],
  };
}

/**
 * Quick check if a message mentions any specialist domain.
 * Cheaper than full classification — use as a pre-filter.
 */
export function hasSpecialistSignal(message: string): boolean {
  const lower = message.toLowerCase();

  // Check exact names (pre-compiled word-boundary regexes)
  for (const [name, pattern] of EXACT_NAME_PATTERNS) {
    if (pattern.test(message)) return true;
  }

  // Check high-weight keywords only (>= 0.85)
  for (const rule of KEYWORD_RULES) {
    if (rule.weight < 0.85) continue;
    for (const kw of rule.keywords) {
      if (lower.includes(kw)) return true;
    }
  }

  return false;
}

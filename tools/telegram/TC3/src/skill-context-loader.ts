/**
 * Skill Context Loader for Telegram {{ORCHESTRATOR_NAME}} Bot
 *
 * Detects skill invocation requests and loads skill content
 * for injection into conversation context.
 */

import type { CatalystSkillLoader } from "./catalyst-loader";

/**
 * Handles skill detection and loading
 */
export class SkillContextLoader {
  private skillLoader: CatalystSkillLoader;

  constructor(skillLoader: CatalystSkillLoader) {
    this.skillLoader = skillLoader;
  }

  /**
   * Detect skill invocation in user message
   *
   * Patterns:
   * - "use skill X"
   * - "apply skill X"
   * - "load skill X"
   * - "with skill X"
   * - "using X skill"
   * - "use the X skill"
   *
   * @param message - User message to analyze
   * @returns Skill name if detected, null otherwise
   */
  detectSkillRequest(message: string): string | null {
    const lower = message.toLowerCase();

    // Patterns for skill detection
    const patterns = [
      /(?:use|apply|load)\s+(?:the\s+)?([a-z0-9-]+)\s+skill/i,
      /(?:use|apply|load)\s+skill\s+([a-z0-9-]+)/i,
      /with\s+(?:the\s+)?([a-z0-9-]+)\s+skill/i,
      /using\s+(?:the\s+)?([a-z0-9-]+)\s+skill/i,
    ];

    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match) {
        const skillName = match[1]!.trim();

        // Verify skill exists
        const skillContext = this.skillLoader.getSkillContext(skillName);
        if (skillContext) {
          return skillName;
        }

        // Try fuzzy match (replace spaces with hyphens)
        const normalizedName = skillName.replace(/\s+/g, "-");
        const normalizedSkillContext = this.skillLoader.getSkillContext(normalizedName);
        if (normalizedSkillContext) {
          return normalizedName;
        }

        console.log(`[SkillContextLoader] Skill not found: ${skillName}`);
      }
    }

    return null;
  }

  /**
   * Detect skill clear request
   *
   * Patterns:
   * - "clear skill X"
   * - "unload skill X"
   * - "remove skill X"
   * - "clear all skills"
   *
   * @param message - User message to analyze
   * @returns { action: 'clear', skillName?: string } or null
   */
  detectSkillClearRequest(
    message: string
  ): { action: "clear"; skillName?: string } | null {
    const lower = message.toLowerCase();

    // Clear all skills
    if (
      lower.includes("clear all skills") ||
      lower.includes("unload all skills") ||
      lower.includes("remove all skills")
    ) {
      return { action: "clear" };
    }

    // Clear specific skill
    const patterns = [
      /(?:clear|unload|remove)\s+(?:the\s+)?([a-z0-9-]+)\s+skill/i,
      /(?:clear|unload|remove)\s+skill\s+([a-z0-9-]+)/i,
    ];

    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match) {
        const skillName = match[1]!.trim();
        return { action: "clear", skillName };
      }
    }

    return null;
  }

  /**
   * Load skill content
   *
   * @param skillName - Name of skill to load
   * @returns Skill content or null if not found
   */
  async loadSkillContent(skillName: string): Promise<string | null> {
    const skillContent = this.skillLoader.getSkillContext(skillName);

    if (!skillContent) {
      console.log(`[SkillContextLoader] Skill not found: ${skillName}`);
      return null;
    }

    return skillContent;
  }

  /**
   * Build formatted skill context for injection
   *
   * @param skillName - Name of skill
   * @param content - Skill prompt content
   * @returns Formatted context block
   */
  buildSkillContext(skillName: string, content: string): string {
    return `
# Active Skill: ${skillName}

${content}

---
`;
  }

  /**
   * Get list of available skills (for help/autocomplete)
   */
  listAvailableSkills(): string[] {
    return this.skillLoader.listSkills();
  }

  /**
   * Search for skills by keyword
   *
   * @param keyword - Search term
   * @param limit - Maximum results
   * @returns Array of matching skill names
   */
  searchSkills(keyword: string, limit = 10): string[] {
    const allSkills = this.listAvailableSkills();
    const lower = keyword.toLowerCase();

    return allSkills
      .filter((name) => name.toLowerCase().includes(lower))
      .slice(0, limit);
  }
}

/**
 * Session Context Management for Telegram {{ORCHESTRATOR_NAME}} Bot
 *
 * Tracks active specialist, loaded skills, and context metrics
 * across a conversation session.
 */

export interface ContextMetrics {
  totalContextSize: number;
  messageCount: number;
  specialistChanges: number;
  skillsLoaded: number;
}

export interface ContextSummary {
  activeSpecialist: string | null;
  loadedSkills: string[];
  metrics: ContextMetrics;
  sessionAge: number; // milliseconds
}

/**
 * Manages session-level context state
 */
export class SessionContext {
  // Specialist tracking
  activeSpecialist: string | null = null;
  specialistLoadedAt: Date | null = null;
  specialistContext: string | null = null;

  // Skill tracking
  private loadedSkills: Map<string, string> = new Map(); // skillName → content
  private skillsLoadedAt: Map<string, Date> = new Map();

  // Context metrics
  private totalContextSize = 0;
  private messageCount = 0;
  private specialistChanges = 0;

  // Session metadata
  private sessionStartedAt: Date = new Date();
  private lastActivity: Date = new Date();

  /**
   * Set active specialist (loads context if needed)
   * @param name - Full specialist name (e.g., "🏛️ Backend Developer")
   * @param context - Full specialist prompt content
   */
  setActiveSpecialist(name: string, context: string): void {
    const isNewSpecialist = this.activeSpecialist !== name;

    if (isNewSpecialist) {
      this.activeSpecialist = name;
      this.specialistContext = context;
      this.specialistLoadedAt = new Date();
      this.specialistChanges++;
      this.totalContextSize += context.length;

      console.log(`[SessionContext] Active specialist set: ${name}`);
    } else {
      console.log(`[SessionContext] Specialist already active: ${name}`);
    }

    this.lastActivity = new Date();
  }

  /**
   * Clear active specialist (return to {{ORCHESTRATOR_NAME}}-only mode)
   */
  clearSpecialist(): void {
    if (this.activeSpecialist) {
      console.log(
        `[SessionContext] Clearing specialist: ${this.activeSpecialist}`
      );
      this.activeSpecialist = null;
      this.specialistContext = null;
      this.specialistLoadedAt = null;
    }
    this.lastActivity = new Date();
  }

  /**
   * Load skill context on-demand
   * @param skillName - Name of skill (e.g., "frontend-testing")
   * @param content - Full skill prompt content
   */
  loadSkill(skillName: string, content: string): void {
    if (this.loadedSkills.has(skillName)) {
      console.log(`[SessionContext] Skill already loaded: ${skillName}`);
      return;
    }

    this.loadedSkills.set(skillName, content);
    this.skillsLoadedAt.set(skillName, new Date());
    this.totalContextSize += content.length;

    console.log(`[SessionContext] Skill loaded: ${skillName} (${content.length} chars)`);
    this.lastActivity = new Date();
  }

  /**
   * Clear a specific skill
   */
  clearSkill(skillName: string): void {
    if (this.loadedSkills.has(skillName)) {
      const content = this.loadedSkills.get(skillName)!;
      this.totalContextSize -= content.length;
      this.loadedSkills.delete(skillName);
      this.skillsLoadedAt.delete(skillName);
      console.log(`[SessionContext] Skill cleared: ${skillName}`);
    }
    this.lastActivity = new Date();
  }

  /**
   * Clear all loaded skills
   */
  clearAllSkills(): void {
    const skillCount = this.loadedSkills.size;
    if (skillCount > 0) {
      this.loadedSkills.clear();
      this.skillsLoadedAt.clear();
      console.log(`[SessionContext] Cleared ${skillCount} skills`);
    }
    this.lastActivity = new Date();
  }

  /**
   * Check if specialist is currently active
   */
  hasActiveSpecialist(): boolean {
    return this.activeSpecialist !== null;
  }

  /**
   * Get active specialist name
   */
  getActiveSpecialist(): string | null {
    return this.activeSpecialist;
  }

  /**
   * Get list of loaded skill names
   */
  getLoadedSkills(): string[] {
    return Array.from(this.loadedSkills.keys());
  }

  /**
   * Get skill content by name
   */
  getSkillContent(skillName: string): string | null {
    return this.loadedSkills.get(skillName) || null;
  }

  /**
   * Build combined skill context block for injection
   * @returns Formatted skill context string
   */
  buildSkillContext(): string {
    if (this.loadedSkills.size === 0) return "";

    const skillBlocks: string[] = [];

    for (const [skillName, content] of this.loadedSkills.entries()) {
      skillBlocks.push(`
# Skill Context: ${skillName}

${content}
`);
    }

    return `
## Loaded Skills

The following skills are active in this session:

${skillBlocks.join("\n---\n")}
`;
  }

  /**
   * Increment message count
   */
  incrementMessageCount(): void {
    this.messageCount++;
    this.lastActivity = new Date();
  }

  /**
   * Get current context metrics
   */
  getMetrics(): ContextMetrics {
    return {
      totalContextSize: this.totalContextSize,
      messageCount: this.messageCount,
      specialistChanges: this.specialistChanges,
      skillsLoaded: this.loadedSkills.size,
    };
  }

  /**
   * Get context summary for display
   */
  getSummary(): ContextSummary {
    const now = new Date();
    const sessionAge = now.getTime() - this.sessionStartedAt.getTime();

    return {
      activeSpecialist: this.activeSpecialist,
      loadedSkills: this.getLoadedSkills(),
      metrics: this.getMetrics(),
      sessionAge,
    };
  }

  /**
   * Format context summary as human-readable string
   */
  formatSummary(): string {
    const summary = this.getSummary();
    const ageMinutes = Math.floor(summary.sessionAge / 60000);

    let output = `📊 Session Context Summary\n\n`;
    output += `**Active Specialist:** ${summary.activeSpecialist || "None ({{ORCHESTRATOR_NAME}} mode)"}\n`;
    output += `**Loaded Skills:** ${summary.loadedSkills.length}\n`;

    if (summary.loadedSkills.length > 0) {
      output += `  - ${summary.loadedSkills.join("\n  - ")}\n`;
    }

    output += `\n**Metrics:**\n`;
    output += `  - Messages: ${summary.metrics.messageCount}\n`;
    output += `  - Context Size: ${(summary.metrics.totalContextSize / 1000).toFixed(1)}K chars\n`;
    output += `  - Specialist Changes: ${summary.metrics.specialistChanges}\n`;
    output += `  - Session Age: ${ageMinutes} minutes\n`;

    return output;
  }

  /**
   * Reset context (for /clear command or new session)
   */
  reset(): void {
    console.log("[SessionContext] Resetting context");

    this.activeSpecialist = null;
    this.specialistContext = null;
    this.specialistLoadedAt = null;

    this.loadedSkills.clear();
    this.skillsLoadedAt.clear();

    this.totalContextSize = 0;
    this.messageCount = 0;
    this.specialistChanges = 0;

    this.sessionStartedAt = new Date();
    this.lastActivity = new Date();
  }
}

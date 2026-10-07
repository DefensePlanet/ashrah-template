/**
 * Management Commands Handler
 *
 * Provides session management and Catalyst resource control:
 * - /sync - Manual reload of agents/skills
 * - /context - View session state
 * - /specialist - Manage active specialist
 * - /skills - Manage loaded skills
 */

import type { CommandContext } from "grammy";
import type { CatalystWatcher } from "../catalyst-loader";
import type { SessionContext } from "../session-context";
import type { SkillContextLoader } from "../skill-context-loader";

// Session interface that both CLI and Direct API sessions implement
interface SessionLike {
  sessionContext: SessionContext;
  skillLoader: SkillContextLoader;
}

/**
 * /sync - Manual reload of Catalyst agents and skills
 */
export async function handleSyncCommand(
  ctx: CommandContext<any>,
  watcher: CatalystWatcher,
): Promise<void> {
  try {
    await ctx.reply("🔄 Syncing Catalyst resources...");

    const result = await watcher.reloadAll();
    const status = watcher.getStatus();

    const agentsDelta = result.agents.after - result.agents.before;
    const skillsDelta = result.skills.after - result.skills.before;

    const agentsChange =
      agentsDelta === 0
        ? "unchanged"
        : agentsDelta > 0
          ? `+${agentsDelta}`
          : `${agentsDelta}`;
    const skillsChange =
      skillsDelta === 0
        ? "unchanged"
        : skillsDelta > 0
          ? `+${skillsDelta}`
          : `${skillsDelta}`;

    let response = `✅ **Sync Complete**\n\n`;
    response += `**Agents:** ${result.agents.before} → ${result.agents.after} (${agentsChange})\n`;
    response += `**Skills:** ${result.skills.before} → ${result.skills.after} (${skillsChange})\n`;
    response += `\n📊 **Watcher Status:**\n`;
    response += `- Watching: ${status.watching ? "Active" : "Inactive"}\n`;
    response += `- Hot reloads: ${status.changeCount}\n`;

    await ctx.reply(response, { parse_mode: "Markdown" });
  } catch (error) {
    console.error("Error in /sync command:", error);
    await ctx.reply(`❌ Sync failed: ${error}`);
  }
}

/**
 * /context - Display session context summary
 */
export async function handleContextCommand(
  ctx: CommandContext<any>,
  session: SessionLike | null,
): Promise<void> {
  try {
    if (!session) {
      await ctx.reply("❌ No active session. Start a conversation first.");
      return;
    }

    const summary = session.sessionContext.formatSummary();
    await ctx.reply(summary, { parse_mode: "Markdown" });
  } catch (error) {
    console.error("Error in /context command:", error);
    await ctx.reply(`❌ Failed to get context: ${error}`);
  }
}

/**
 * /specialist - Manage active specialist
 *
 * Usage:
 * - /specialist - Show active specialist
 * - /specialist clear - Clear active specialist
 */
export async function handleSpecialistCommand(
  ctx: CommandContext<any>,
  session: SessionLike | null,
): Promise<void> {
  try {
    if (!session) {
      await ctx.reply("❌ No active session. Start a conversation first.");
      return;
    }

    const args = ctx.message?.text?.split(" ").slice(1) || [];
    const action = args[0]?.toLowerCase();

    // Clear specialist
    if (action === "clear") {
      const activeSpecialist = session.sessionContext.getActiveSpecialist();

      if (!activeSpecialist) {
        await ctx.reply("ℹ️ No specialist is currently active.");
        return;
      }

      session.sessionContext.clearSpecialist();
      await ctx.reply(
        `✅ Cleared specialist: ${activeSpecialist}\n\nReturned to {{ORCHESTRATOR_NAME}} mode.`,
      );
      return;
    }

    // Show active specialist
    const activeSpecialist = session.sessionContext.getActiveSpecialist();

    if (!activeSpecialist) {
      await ctx.reply(
        "ℹ️ No specialist is currently active.\n\n**To activate a specialist**, say:\n- \"Have [specialist] do X\"\n- \"Ask [specialist] to Y\"",
      );
      return;
    }

    const loadedAt = session.sessionContext.specialistLoadedAt;
    const timeActive = loadedAt
      ? Math.floor((Date.now() - loadedAt.getTime()) / 60000)
      : 0;

    let response = `🎯 **Active Specialist**\n\n`;
    response += `**Name:** ${activeSpecialist}\n`;
    response += `**Active for:** ${timeActive} minutes\n`;
    response += `\n**To clear:** /specialist clear`;

    await ctx.reply(response, { parse_mode: "Markdown" });
  } catch (error) {
    console.error("Error in /specialist command:", error);
    await ctx.reply(`❌ Failed to manage specialist: ${error}`);
  }
}

/**
 * /skills - Manage loaded skills
 *
 * Usage:
 * - /skills - List loaded skills
 * - /skills clear - Clear all skills
 * - /skills clear <name> - Clear specific skill
 * - /skills search <query> - Search available skills
 */
export async function handleSkillsCommand(
  ctx: CommandContext<any>,
  session: SessionLike | null,
): Promise<void> {
  try {
    if (!session) {
      await ctx.reply("❌ No active session. Start a conversation first.");
      return;
    }

    const args = ctx.message?.text?.split(" ").slice(1) || [];
    const action = args[0]?.toLowerCase();
    const param = args.slice(1).join(" ");

    // Clear all skills
    if (action === "clear" && !param) {
      const loadedSkills = session.sessionContext.getLoadedSkills();

      if (loadedSkills.length === 0) {
        await ctx.reply("ℹ️ No skills are currently loaded.");
        return;
      }

      session.sessionContext.clearAllSkills();
      await ctx.reply(
        `✅ Cleared ${loadedSkills.length} skill(s):\n- ${loadedSkills.join("\n- ")}`,
      );
      return;
    }

    // Clear specific skill
    if (action === "clear" && param) {
      const loadedSkills = session.sessionContext.getLoadedSkills();

      if (!loadedSkills.includes(param)) {
        await ctx.reply(
          `❌ Skill "${param}" is not loaded.\n\n**Loaded skills:**\n- ${loadedSkills.join("\n- ")}`,
        );
        return;
      }

      session.sessionContext.clearSkill(param);
      await ctx.reply(`✅ Cleared skill: ${param}`);
      return;
    }

    // Search available skills
    if (action === "search" && param) {
      const results = session.skillLoader.searchSkills(param, 15);

      if (results.length === 0) {
        await ctx.reply(
          `❌ No skills found matching: "${param}"\n\nTry a different search term.`,
        );
        return;
      }

      let response = `🔍 **Skills matching "${param}"** (${results.length}):\n\n`;
      response += results.map((name) => `- ${name}`).join("\n");
      response += `\n\n**To load a skill**, say:\n"Use the [skill-name] skill"`;

      await ctx.reply(response);
      return;
    }

    // List loaded skills (default)
    const loadedSkills = session.sessionContext.getLoadedSkills();

    if (loadedSkills.length === 0) {
      await ctx.reply(
        `ℹ️ No skills are currently loaded.\n\n**To load a skill**, say:\n- "Use skill X"\n- "Apply the Y skill"\n\n**To search skills:** /skills search <query>`,
      );
      return;
    }

    let response = `📚 **Loaded Skills** (${loadedSkills.length}):\n\n`;
    response += loadedSkills.map((name) => `- ${name}`).join("\n");
    response += `\n\n**Commands:**\n`;
    response += `- /skills clear - Clear all skills\n`;
    response += `- /skills clear <name> - Clear specific skill\n`;
    response += `- /skills search <query> - Search available skills`;

    await ctx.reply(response, { parse_mode: "Markdown" });
  } catch (error) {
    console.error("Error in /skills command:", error);
    await ctx.reply(`❌ Failed to manage skills: ${error}`);
  }
}

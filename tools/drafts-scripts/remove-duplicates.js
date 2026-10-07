// Remove Duplicates - Drafts Action Script
// Finds exact duplicate drafts and trashes all but the oldest
//
// Installation:
//   1. Drafts → Actions → Manage Actions → +
//   2. Name: "Remove Duplicates"
//   3. Add Step → Script
//   4. Paste this code
//
// Trigger via URL: drafts://runAction?action=Remove%20Duplicates

(function() {
    // Get all non-trashed drafts
    let allDrafts = Draft.query("", "inbox", [], [], "created", false, false);
    let archivedDrafts = Draft.query("", "archive", [], [], "created", false, false);
    allDrafts = allDrafts.concat(archivedDrafts);

    // Group by content (trimmed to normalize whitespace)
    let contentMap = new Map();
    for (let d of allDrafts) {
        let content = d.content.trim();
        if (content.length === 0) continue; // Skip empty drafts

        if (!contentMap.has(content)) {
            contentMap.set(content, []);
        }
        contentMap.get(content).push(d);
    }

    // Find duplicates and trash newer copies
    let duplicateGroups = 0;
    let trashedCount = 0;
    let examples = [];

    for (let [content, drafts] of contentMap) {
        if (drafts.length > 1) {
            duplicateGroups++;

            // Sort by created date (oldest first)
            drafts.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());

            // Collect example (first 50 chars of first line)
            if (examples.length < 5) {
                let firstLine = content.split('\n')[0];
                let preview = firstLine.substring(0, 50);
                if (firstLine.length > 50) preview += "...";
                examples.push(`"${preview}" (${drafts.length} copies)`);
            }

            // Keep first (oldest), trash the rest
            for (let i = 1; i < drafts.length; i++) {
                drafts[i].isTrashed = true;
                drafts[i].update();
                trashedCount++;
            }
        }
    }

    // Build result message
    let message = `Duplicate Removal Complete\n\n`;
    message += `Total drafts scanned: ${allDrafts.length}\n`;
    message += `Duplicate groups found: ${duplicateGroups}\n`;
    message += `Drafts moved to trash: ${trashedCount}\n`;
    message += `Remaining unique drafts: ${allDrafts.length - trashedCount}\n`;

    if (examples.length > 0) {
        message += `\nExamples of duplicates:\n`;
        for (let ex of examples) {
            message += `• ${ex}\n`;
        }
    }

    if (trashedCount === 0) {
        message += `\nNo duplicates found!`;
    } else {
        message += `\nNote: Duplicates moved to Trash. Empty trash in Drafts to permanently delete.`;
    }

    alert(message);
})();

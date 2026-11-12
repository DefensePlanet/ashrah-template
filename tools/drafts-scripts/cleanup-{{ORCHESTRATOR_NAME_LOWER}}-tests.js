// Cleanup {{ORCHESTRATOR_NAME}} Test Drafts - Drafts Action Script
// Removes test drafts created during {{ORCHESTRATOR_NAME}}/BuilderOS integration testing
//
// Trigger via URL: drafts://runAction?action=Cleanup%20{{ORCHESTRATOR_NAME}}%20Tests

(function() {
    // Find drafts with {{ORCHESTRATOR_NAME_LOWER}} tag
    let {{ORCHESTRATOR_NAME_LOWER}}Drafts = Draft.query("", "all", ["{{ORCHESTRATOR_NAME_LOWER}}"], [], "created", false, false);

    let trashedCount = 0;
    let examples = [];

    for (let d of {{ORCHESTRATOR_NAME_LOWER}}Drafts) {
        // Check if it's a test draft
        if (d.content.includes("Test from {{ORCHESTRATOR_NAME}}") ||
            d.content.includes("integration test") ||
            d.content.includes("Direct integration test")) {

            if (examples.length < 5) {
                examples.push(d.title || d.content.substring(0, 40));
            }

            d.isTrashed = true;
            d.update();
            trashedCount++;
        }
    }

    let message = `Cleanup Complete\n\n`;
    message += `{{ORCHESTRATOR_NAME}} test drafts found: ${{{ORCHESTRATOR_NAME_LOWER}}Drafts.length}\n`;
    message += `Drafts moved to trash: ${trashedCount}\n`;

    if (examples.length > 0) {
        message += `\nTrashed:\n`;
        for (let ex of examples) {
            message += `• ${ex}\n`;
        }
    }

    if (trashedCount === 0) {
        message += `\nNo test drafts found to clean up.`;
    } else {
        message += `\nNote: Tags will be removed automatically once no drafts use them.`;
    }

    alert(message);
})();

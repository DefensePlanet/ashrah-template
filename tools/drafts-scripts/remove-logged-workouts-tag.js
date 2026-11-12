// Remove Logged Workouts Tag - Drafts Action Script
// Removes the "logged workouts" tag from the current draft
//
// Action Name: "Remove Logged Workouts Tag"
// Trigger: drafts://open?uuid=DRAFT-UUID&action=Remove%20Logged%20Workouts%20Tag

(function() {
    let d = draft;
    if (d.hasTag('logged workouts')) {
        d.removeTag('logged workouts');
        d.update();
        // No alert - silent operation for batch processing
    }
})();

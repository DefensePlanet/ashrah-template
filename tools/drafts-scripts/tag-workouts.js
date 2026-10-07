// Tag Workouts - Drafts Action Script
// Finds workout logs and tags them with "recorded workouts"
//
// Action Name: "Tag Workouts"
// Trigger: drafts://runAction?action=Tag%20Workouts

(function() {
    let allDrafts = Draft.query("", "inbox", [], [], "created", false, false);

    let taggedCount = 0;
    let alreadyTagged = 0;

    for (let d of allDrafts) {
        let content = d.content.toLowerCase();

        // Check for workout indicators
        let isWorkout = (
            content.includes('bench press') ||
            content.includes('bench:') ||
            content.includes('pec fly') ||
            content.includes('peck fly') ||
            content.includes('squat') ||
            content.includes('preacher curl') ||
            content.includes('bicep curl') ||
            content.includes('deadlift') ||
            content.includes('lat pull') ||
            content.includes('shoulder press') ||
            content.includes('tricep') ||
            content.includes('leg press') ||
            content.includes('leg curl') ||
            content.includes('cable row') ||
            content.includes('hip thrust') ||
            content.includes('backwards sled') ||
            content.includes('neck curl') ||
            content.includes('stair climber') ||
            (content.includes(' reps') && content.includes(' sets')) ||
            (content.includes(' lbs') && content.includes(' reps')) ||
            (content.includes(' pounds') && content.includes(' reps'))
        );

        if (isWorkout) {
            if (d.hasTag('recorded workouts')) {
                alreadyTagged++;
            } else {
                d.addTag('recorded workouts');
                d.update();
                taggedCount++;
            }
        }
    }

    alert(`Workout Tagging Complete\n\nNewly tagged: ${taggedCount}\nAlready tagged: ${alreadyTagged}\nTotal workouts: ${taggedCount + alreadyTagged}`);
})();

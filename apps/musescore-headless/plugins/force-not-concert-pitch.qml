import QtQuick 2.15
import MuseScore 3.0

MuseScore {
    menuPath: "Plugins.Divisi.Set Transposed Pitch"

    description: "Forces the score into transposed pitch mode"
    version: "1.0"
    requiresScore: true

    onRun: {
        if (!curScore) {
            console.log("No score open");
            Qt.quit();
            return;
        }

        try {
            // Force Concert Pitch OFF
            curScore.style.setValue("concertPitch", false);
            //curScore.styleB("concertPitch", false);
            //curScore.setStyleValue("concertPitch", false);

            // Save score
            curScore.save();

            console.log("Concert Pitch disabled successfully.");
        } catch (e) {
            console.log("Error: " + e);
        }

        Qt.quit();
    }
}
import QtQuick 2.15
import QtQuick.Controls 2.15
import MuseScore 3.0
import FileIO 3.0

MuseScore {
    id: root

    menuPath: "Plugins.Layout Analysis.Export System Layout JSON"

    version: "1.0.0"
    description: "Exports the rendered system layout of the current score"

    title: "System Layout Export"

    FileIO {
        id: outputFile
        source: "/tmp/system-layout-export.json"
    }

    onRun: {
        if (!curScore) {
            console.log("No score open")
            Qt.quit()
            return
        }

        var result = exportLayout(curScore)
        var payload = JSON.stringify(result, null, 2)

        if (!outputFile.write(payload)) {
            console.log("Failed to write layout export to " + outputFile.source)
            Qt.quit()
            return
        }

        console.log(payload)
        Qt.quit()
    }

    //----------------------------------------------------------------------
    // MAIN EXPORT
    //----------------------------------------------------------------------

    function exportLayout(score) {

        /*
            Desired format:

            {
              "staff_id": "1",
              "systems": [
                [0,1,2,3],
                [4,5,6]
              ]
            }
        */

        var output = {
            staff_id: "1",
            systems: []
        }

        var targetStaffIdx = 0
        var cursor = score.newCursor()

        cursor.rewind(0)

        var previousMeasureNo = -1

        var currentSystemObject = null
        var currentSystemMeasures = []

        while (cursor.segment) {

            if (cursor.staffIdx !== targetStaffIdx) {
                cursor.next()
                continue
            }

            var measure = cursor.measure

            //------------------------------------------------------------------
            // Skip duplicate visits to same measure
            //------------------------------------------------------------------

            if (measure.no === previousMeasureNo) {
                cursor.next()
                continue
            }

            previousMeasureNo = measure.no

            //------------------------------------------------------------------
            // Rendered system object
            //------------------------------------------------------------------

            var systemObject = getSystemObject(measure)

            //------------------------------------------------------------------
            // Detect system transition
            //------------------------------------------------------------------

            if (systemObject !== currentSystemObject) {

                if (currentSystemMeasures.length > 0) {
                    output.systems.push(currentSystemMeasures)
                }

                currentSystemMeasures = []
                currentSystemObject = systemObject
            }

            //------------------------------------------------------------------
            // Add zero-based measure index
            //------------------------------------------------------------------

            currentSystemMeasures.push(measure.no)

            cursor.next()
        }

        //----------------------------------------------------------------------
        // Push final system
        //----------------------------------------------------------------------

        if (currentSystemMeasures.length > 0) {
            output.systems.push(currentSystemMeasures)
        }

        return output
    }

    //----------------------------------------------------------------------
    // GET RENDERED SYSTEM OBJECT
    //----------------------------------------------------------------------

    /*
        In MuseScore Studio 4.x:

        measure.parent is typically the rendered System object.

        We intentionally use object identity instead of relying on
        undocumented index fields.

        This is more reliable across 4.x versions.
    */

    function getSystemObject(measure) {

        try {

            if (!measure)
                return null

            return measure.parent

        } catch (e) {

            console.log("Error retrieving system object:")
            console.log(e)

            return null
        }
    }
}
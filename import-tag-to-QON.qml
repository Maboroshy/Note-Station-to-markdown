/* It is the script for QOwnNotes to import tags from 'nsx2md.sh' generated markdown notes.
 * The script uses GNU utility "sed" to manipulate note text, so the script may not work under OS other that GNU/Linux.
 * This script will convert "Tags: tag1, tag2" line of note text into QOwnNotes tags. 
 * The script will run when you open a note in QOwnNotes. You'll need to go through all notes to convert their tags.
 * "Tag" line will be deleted from note text. I suggest disabling the script after you finish importing.
 */

import QtQml 2.0
import com.qownnotes.noteapi 1.0

QtObject {
    
    function noteOpenedHook(note) {
        
        var tagsList = note.noteText.match(/^Tags: .+/)
        
        if (tagsList) {
            
            var tags = tagsList[0].replace("Tags: ","").split(",")
            
            for (var n = 0; n < tags.length; n++) {
                script.tagCurrentNote(tags[n].trim())    
            }
            
            script.startSynchronousProcess("sed", ["-i","/^Tags: /d",note.fullNoteFilePath], "")
            script.startSynchronousProcess("sed", ["-i","/./,$!d",note.fullNoteFilePath], "")
       } 
    }
}

 

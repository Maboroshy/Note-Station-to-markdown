import QtQml 2.0
import QOwnNotesTypes 1.0

/* nsx2md script will produce .md notes which may have a tag data as 'Tags: tag1, tag2' line.
 * 
 * This script adds two buttons and menu items:
 * 1. Import tags - to import tags from the tag lines of all the notes in the current note folder;
 * 2. Remove tag lines - to remove the tag lines from all the notes in the current folder.
 * 
 * Use them in the according order.
 * 
 * This script is only supposed to be used in a note folder produced by nsx2md.
 * Any previous tag data will be lost.
 * This script should be disabled right after tags imported and tag lines removed. 
 */

Script {   

    property string scriptDirPath
    property bool enabled: false
    property var importedNotes: []
    
    function init() {
        script.registerCustomAction('importTags', '1. Import tags from notes', '1. Import tags')
        script.registerCustomAction('removeTagLines', '2. Remove tag lines from notes', '2. Remove tag lines')
    }
    
    function customActionInvoked(action) {
        if (action == 'importTags') {
            enabled = true
            mainWindow.buildNotesIndexAndLoadNoteDirectoryList(true, true)
            enabled = false
        }
        
        if (action == 'removeTagLines') {
            if (script.platformIsWindows())
                var pyBin = 'pythonw'
            else
                var pyBin = 'python3'
                
            const args = [scriptDirPath + script.dirSeparator() + 'remove_tag_line.py'].concat(importedNotes)
            
            script.startDetachedProcess(pyBin, args)
            
            script.informationMessageBox('Tag lines removed from ' + importedNotes.length + ' notes.\n' + 
                                         'Please, disable Import tags script now.\n' +
                                         'Otherwise you may loose tag data.', 
                                         'Import tags script')
        }
    }
    
    function noteTaggingHook(note, action, tagName, newTagName) {
        if (action == 'list') {
            if (enabled == false || importedNotes.indexOf(note.fullNoteFilePath) != -1)
                return note.tagNames()
                
            const tagLine = note.noteText.match(/^Tags: (.*)/m)
            importedNotes.push(note.fullNoteFilePath)
            
            if (tagLine == null) 
                return ''
            else            
                return tagLine[1].split(', ')
        }
    }
}

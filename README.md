This script will convert notes from Synology Note Station to plain-text markdown notes.
The script is written in Python and should work on any desktop platform. It's tested on Linux and Windows 7. 

After conversion you will get:
1) Directories named like exported notebooks;
2) Notes in those directories as markdown-syntax plain text files with all in-line images in-place;
3) Assigned tags and links to attachments at the beggining of note text;
3) All images and attached files in `media` sub-directories inside notebook directories.

# Installation
1) The script requires [Python 3.5+](https://www.python.org/downloads/) and [pandoc](http://pandoc.org/installing.html) installed on your system. Get the install package or use the package manager of your OS.
2) Put `nsx2md.py` to the directory, where you want to convert notes.
3) (Linux only, optional) Give `nsx2md.py` execute permission.

# Usage
1) Export your Synology Note Station notebooks by: Setting -> Import and Export -> Export. You will get .nsx file.
2) Adjust .nsx file permission if required. Mine was readable only by owner user.
3) Copy .nsx file(s) to the directory where you've put `nsx2md.py`.
4) Run `nsx2md.py` or `python nsx2md.py` to convert all .nsx files in the directory. It won't delete them.  
... or run `nsx2md.py path/to/export.nsx` to convert a specific file. Converted notes will appear where the file is.

That means `nsx2md.py` can be located anywhere if you specify the file you want to convert.

# Optional settings
Inside the script you can make some adjustments to the link format for local files. Default is `file://media/file.jpg` which is used by [QOwnNotes](https://github.com/pbek/QOwnNotes) and mostly works with other markdown editors.

# For [QOwnNotes](https://github.com/pbek/QOwnNotes) users
Tag data that `nsx2md.py` puts to note text can be imported to QOwnNotes:
1) Enable provided `import-tag-to-QON.qml` script in QOwnNotes (Note -> Settings -> Scripting);
2) Add `nsx2md.py` generated directories as "note folders";
3) Go through all notes (open each note) for `import-tag-to-QON.qml` script to import their tags.
4) Disable `import-tag-to-QON.qml` script, so it won't missfire when you'll want to start line with `Tags:` in your note.

# Known issues
In-line image links which target internet URLs doesn't work yet.

Sometimes `nsx2md.py` may write to console that it can't find an attachment of some notes. In my case that was because the attached file was missing from the .nsx file. Note Station just haven't exported it for a reason not known to me.  
The `nsx2md.py` will tell missing attachment name and a name of note which had it attached, so you can resolve it manually. It will also give the link to missing attachments `NOT FOUND` name.

This shell script for GNU/Linux will convert the .nsx export files of Synology Note Station to markdown notes.

After conversion you will get:
1) Directories named like exported notebooks;
2) Notes in those directories as markdown-syntax plain text files with all in-line images in-place;
3) Assigned tags and links to attachments at the beggining of note text;
3) All images and attached files in `media` sub-directories inside notebook directories.

# Installation
1) The script requires `unzip`, `jq` and `pandoc` packages. Please install them with you distribution package management tool. If the script won't find them, it will exit with an error.
2) Put `nsx2md.sh` to the directory, where you want to convert notes, and give it execute permission.

# Usage
1) Export your Synology Note Station notebooks by: Setting -> Import and Export -> Export. You will get .nsx file.
2) Adjust .nsx file permission if required. Mine was readable only by owner user.
3) Copy .nsx file(s) to the directory where you've put `nsx2md.sh`.
4) Run `nsx2md.sh` or `bash nsx2md.sh` to convert all .nsx files in the directory. It won't delete them.  
... or run `nsx2md.sh path/to/export.nsx` to convert a specific file. Converted notes will appear where the file is.

That means `nsx2md.sh` can be located anywhere if you specify the file you want to convert.

# Known issues
Sometimes `nsx2md.sh` may write to console that it can't find an attachment of some notes. In my case that was because the attached file was missing from the .nsx file. Note Station just haven't exported it for a reason not known to me.  
The `nsx2md.sh` will tell missing attachment name and a name of note which had it attached, so you can resolve it manually.

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

That means `nsx2md.py` can be located anywhere as long as you specify the file you want to convert.

# Optional settings
Inside the script you can make some adjustments to the link format and notes metadata:  
`links_as_URI` - `True` for `file://link%20target` style links, `False` for `/link target` style links;  
`absolute_links` - `True` for absolute links, `False` for relative links;  
`media_dir_name` - name of the directory inside the produced directory where all images and attachemnst will be stored;   
`md_file_ext` - extension for produced markdown syntax note files;  
`insert_title` - `True` to insert note title as a markdown heading at the first line, `False` to disable;  
`insert_ctime` - `True` to insert note creation time to the beggining of the note text, `False` to disable;  
`insert_mtime` - `True` to insert note modifictation time to the beggining of the note text, `False` to disable;  
`creation_date_in_filename` - `True` to insert note creation time to the note file name, `False` to disable.  

# For [QOwnNotes](https://github.com/pbek/QOwnNotes) users
Tag data that `nsx2md.py` puts to note text can be imported to QOwnNotes:  
1) Add notebook directories produced by `nsx2md.py` as QOwnNotes note folders;  
2) Set one of these note folders as current;  
3) Enable provided `import_tags.qml` script in QOwnNotes (Note -> Settings -> Scripting) (`remove_tag_line.py` should be at the same directory);  
4) The script will add 2 new buttons and menu items:  
    `1. Import tags` - to import tags from the tag lines of all the notes in the current note folder  
    `2. Remove tag lines` - to remove the tag lines from all the notes in the current folder  
5) Use the buttons in the according order, any previous QOwnNotes tag data for the note folder will be lost;  
6) Move to the next note folder produced by `nsx2md.py`, repeat #5;  
7) Disable `import_tags.qml` script. That is obligatory.
